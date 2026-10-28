import base64
import copy
import http.client
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from annotation.prebox.store import Workspace, ConflictError, image_info, read_json
from annotation.prebox.server import make_server


def picture(alternate=False):
    image=Image.new('RGB',(600,800),'white');draw=ImageDraw.Draw(image)
    for y in (60,90,120,240,270,300):draw.rectangle((50,y,450 if not alternate else 390,y+12),fill='black')
    stream=io.BytesIO();image.save(stream,format='PNG');return stream.getvalue()


def file(raw=None,name='书页.png'):
    return dict(name=name,data_base64=base64.b64encode(raw or picture()).decode())


def saved_pages(state):
    return [{k:copy.deepcopy(p[k])for k in('page_id','sha256','width','height','boxes')}for p in state['pages']]


class PreboxStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.w=Workspace(self.root/'one')

    def populated(self,two=False):
        self.w.import_images([file()]+([file(picture(True))]if two else []),0)
        return self.w.state()

    def test_geometry_candidates_without_models_and_repeat_import_preserves_edits(self):
        with patch.dict(sys.modules,{'rapidocr_onnxruntime':None,'onnxruntime':None,'rapid_latex_ocr':None}):
            state=self.populated();self.assertGreater(len(state['pages'][0]['boxes']),0)
            pages=saved_pages(state);pages[0]['boxes'][0]['kind']='stem';self.w.save(pages,1)
            self.w.import_images([file(name='另一名字.png')],2)
        current=self.w.state();self.assertEqual(len(current['pages']),1)
        self.assertEqual(current['pages'][0]['boxes'][0]['kind'],'stem')
        self.assertEqual(current['pages'][0]['boxes'][0]['origin'],'MANUAL')
        self.assertFalse(current['pages'][0]['detector']['can_identify_complete_questions'])

    def test_same_name_different_source_has_distinct_identity_and_page_isolation(self):
        state=self.populated(True);self.assertEqual(len({p['page_id']for p in state['pages']}),2)
        unchanged=copy.deepcopy(state['pages'][1]);pages=saved_pages(state)
        pages[0]['boxes'][0]['bbox']=[20,20,100,100];self.w.save(pages,1)
        self.assertEqual(self.w.state()['pages'][1],unchanged)
        self.assertEqual(self.w.state()['pages'][0]['boxes'][0]['origin'],'MANUAL')

    def test_cas_between_instances_and_reopen(self):
        self.populated();second=Workspace(self.w.root);pages=saved_pages(second.state())
        self.w.save(pages,1)
        with self.assertRaises(ConflictError):second.save(pages,1)
        self.assertEqual(second.state(),Workspace(self.w.root).state())

    def test_invalid_boxes_never_advance_revision(self):
        state=self.populated()
        for bbox in ([0,0,1,3],[-1,2,5,9],[0,0,601,10],[4,4,2,8],[0,0,float('nan'),8],[0,0,float('inf'),8],[False,0,10,10]):
            with self.subTest(bbox=bbox):
                pages=saved_pages(state);pages[0]['boxes'][0]['bbox']=bbox
                with self.assertRaises(ValueError):self.w.save(pages,1)
                self.assertEqual(self.w.state(),state)
        for key,value in [('status','APPROVED'),('kind','mystery'),('origin','HUMAN_VERIFIED')]:
            pages=saved_pages(state);pages[0]['boxes'][0][key]=value
            with self.assertRaises(ValueError):self.w.save(pages,1)
        pages=saved_pages(state);pages[0]['boxes'].append(copy.deepcopy(pages[0]['boxes'][0]))
        with self.assertRaises(ValueError):self.w.save(pages,1)

    def test_source_identity_cannot_be_changed_by_save(self):
        state=self.populated()
        for key,value in [('page_id','same-filename'),('sha256','0'*64),('width',599)]:
            pages=saved_pages(state);pages[0][key]=value
            with self.assertRaises(ValueError):self.w.save(pages,1)
        self.assertEqual(state,self.w.state())

    def test_self_contained_json_roundtrip_preserves_source_and_geometry(self):
        self.populated(True);doc=self.w.export_document();target=Workspace(self.root/'two')
        target.import_document(json.dumps(doc),0);new=target.export_document()
        for a,b in zip(doc['pages'],new['pages']):
            self.assertEqual(a['image_base64'],b['image_base64'])
            self.assertEqual(a['sha256'],b['sha256'])
            self.assertEqual([x['bbox']for x in a['boxes']],[x['bbox']for x in b['boxes']])
            self.assertTrue(all(x['origin']=='IMPORTED_DRAFT'for x in b['boxes']))
        self.assertEqual(new['decision'],'HOLD');self.assertFalse(new['human_verified'])

    def test_wrong_source_bad_hash_unknown_version_or_approval_json_rejected(self):
        state=self.populated();original=self.w.export_document()
        edits=[lambda d:d.update(schema_version='unknown/9'),lambda d:d.update(human_verified=True),
               lambda d:d['pages'][0].update(sha256='0'*64),lambda d:d['pages'][0].update(width=599),
               lambda d:d['pages'][0].update(image_base64=file(picture(True))['data_base64']),
               lambda d:d['pages'].append(copy.deepcopy(d['pages'][0])),
               lambda d:d['pages'][0]['boxes'][0].update(bbox=[0,0,float('nan'),7])]
        for edit in edits:
            doc=copy.deepcopy(original);edit(doc)
            with self.assertRaises(ValueError):self.w.import_document(doc,1)
            self.assertEqual(self.w.state(),state)
        raw=json.dumps(original);duplicate=raw.replace('"decision": "HOLD"','"decision":"HOLD","decision":"HOLD"')
        with self.assertRaises(ValueError):self.w.import_document(duplicate,1)

    def test_restore_is_new_revision_not_history_rewrite(self):
        self.populated();before=self.w.state();pages=saved_pages(before);pages[0]['boxes']=[]
        self.w.save(pages,1);self.w.restore(1,2)
        self.assertEqual(self.w.state()['pages'],before['pages'])
        self.assertEqual(self.w.state()['revision'],3);self.assertEqual(len(self.w.history()),4)
        self.assertEqual(Workspace(self.w.root).state(),self.w.state())

    def test_failed_sql_commit_keeps_last_saved_revision(self):
        state=self.populated()
        with self.w._connect()as db:
            db.execute("CREATE TRIGGER simulated_failure BEFORE INSERT ON revisions WHEN NEW.revision=2 BEGIN SELECT RAISE(ABORT,'simulated disk failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.w.save(saved_pages(state),1)
        self.assertEqual(self.w.state(),state);self.assertEqual(len(self.w.history()),2)

    def test_import_batch_failure_does_not_publish_partial_pages(self):
        with self.assertRaises(ValueError):self.w.import_images([file(),file(b'not an image')],0)
        self.assertEqual(self.w.state()['revision'],0);self.assertEqual(self.w.state()['pages'],[])
        self.assertEqual(Workspace(self.w.root).state()['pages'],[])

    def test_changed_asset_and_corrupted_snapshot_fail_closed(self):
        state=self.populated();asset=self.w.root/state['pages'][0]['asset_path'];raw=asset.read_bytes()
        asset.write_bytes(picture(True))
        with self.assertRaises(ValueError):self.w.state()
        with self.assertRaises(ValueError):self.w.export_document()
        asset.write_bytes(raw)
        with self.w._connect()as db:db.execute('UPDATE revisions SET pages=? WHERE revision=1',(b'[]',))
        with self.assertRaises(ValueError):Workspace(self.w.root)

    def test_malformed_and_rotated_images_and_workspace_capacity(self):
        with self.assertRaises(ValueError):self.w.import_images([dict(name='a',data_base64='@@')],0)
        image=Image.new('RGB',(20,30));exif=Image.Exif();exif[274]=6;stream=io.BytesIO();image.save(stream,format='JPEG',exif=exif)
        with self.assertRaises(ValueError):image_info(stream.getvalue())
        with patch('annotation.prebox.store.MAX_WORKSPACE_BYTES',10):
            with self.assertRaises(ValueError):self.w.import_images([file()],0)
        self.assertEqual(self.w.state()['revision'],0)

    def test_portrait_two_column_gutter_and_blank_page(self):
        image=Image.new('RGB',(1000,1500),'white');draw=ImageDraw.Draw(image)
        for y in range(100,1300,35):
            draw.rectangle((60,y,450,y+12),fill='black');draw.rectangle((550,y,940,y+12),fill='black')
        stream=io.BytesIO();image.save(stream,format='PNG')
        self.w.import_images([file(stream.getvalue())],0);page=self.w.state()['pages'][0]
        columns=page['detector']['columns'];self.assertEqual(len(columns),2)
        self.assertGreater(len(page['boxes']),4)
        cut=columns[0][1]
        self.assertTrue(all(b['bbox'][2]<=cut+1 or b['bbox'][0]>=cut-1 for b in page['boxes']))
        blank=io.BytesIO();Image.new('RGB',(600,800),'white').save(blank,format='PNG')
        self.w.import_images([file(blank.getvalue())],1)
        self.assertEqual(self.w.state()['pages'][1]['boxes'],[])
        self.assertEqual(self.w.state()['decision'],'HOLD')


class PreboxHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.w=Workspace(Path(self.temp.name));self.server=make_server(self.w,port=0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop);self.port=self.server.server_port

    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join(5)

    def call(self,path,body=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=30)
        data=None if body is None else json.dumps(body).encode()
        connection.request('GET'if body is None else'POST',path,body=data,headers=headers or {})
        response=connection.getresponse();raw=response.read();status=response.status;connection.close();return status,raw

    def test_http_import_save_export_reimport_and_static_assets(self):
        code,raw=self.call('/api/state');state=read_json(raw);self.assertEqual(code,200)
        headers={'Content-Type':'application/json','X-CSRF-Token':state['csrf_token']}
        code,raw=self.call('/api/import-images',dict(expected_revision=0,files=[file()]),headers)
        self.assertEqual(code,200);state=read_json(raw)
        pages=saved_pages(state);pages[0]['boxes'][0]['bbox']=[10,20,100,120]
        code,_=self.call('/api/save',dict(expected_revision=1,pages=pages),headers);self.assertEqual(code,200)
        code,raw=self.call('/api/export');document=read_json(raw);self.assertNotIn('csrf_token',document)
        self.assertEqual(base64.b64decode(document['pages'][0]['image_base64']),picture())
        self.assertEqual(document['pages'][0]['boxes'][0]['bbox'],[10,20,100,120])
        code,_=self.call('/api/import',dict(expected_revision=2,document_text=json.dumps(document)),headers);self.assertEqual(code,200)
        for path in ('/','/ui.js','/geometry.js','/ui.css','/assets/'+state['pages'][0]['page_id']):
            self.assertEqual(self.call(path)[0],200,path)

    def test_stale_missing_token_cross_origin_and_duplicate_json_rejected(self):
        state=read_json(self.call('/api/state')[1]);headers={'Content-Type':'application/json','X-CSRF-Token':state['csrf_token']}
        body=dict(expected_revision=0,files=[file()])
        self.assertEqual(self.call('/api/import-images',body,{'Content-Type':'application/json'})[0],403)
        self.assertEqual(self.call('/api/import-images',body,dict(headers,Origin='https://other.example'))[0],403)
        self.assertEqual(self.call('/api/import-images',body,headers)[0],200)
        self.assertEqual(self.call('/api/import-images',body,headers)[0],409)
        doc=json.dumps(self.w.export_document()).replace('"decision": "HOLD"','"decision":"HOLD","decision":"HOLD"')
        self.assertEqual(self.call('/api/import',dict(expected_revision=1,document_text=doc),headers)[0],422)
        self.assertEqual(self.w.state()['revision'],1)


if __name__=='__main__':unittest.main()
