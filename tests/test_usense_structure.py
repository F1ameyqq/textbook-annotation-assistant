"""Synthetic whole-book structure tests; no browser/network or private content."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch
import zlib

from annotation.runtime.usense_live import structure as s, new_question as n, update as u
from annotation.runtime.usense_live.batch import file_ref
from annotation.runtime.usense_live.insertion import ROW_KEYS, INFO_KEYS


def response(data): return {"code":0,"message":"success","data":data}
def dump(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")
    return file_ref(path)
def png(width,height,color=0):
    def chunk(kind,data): return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,0,0,0,0))+chunk(b"IDAT",zlib.compress((b"\x00"+bytes([color])*width)*height))+chunk(b"IEND",b"")


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.now=datetime.now(timezone.utc)
        # Minimal synthetic JS containing the observed request-builder syntax.
        # Only the test constant is overridden; production binds the actual SHA.
        script='\n'.join(['Hr="/qieti/api/annotate_pic"',
          'gn.post(`${Hr}/directory/change-set/preview`,{file_id:e,original_directory_data:t,draft_directory_data:n})',
          'gn.post(`${Hr}/directory/change-set/apply`,{file_id:e,original_directory_data:t,draft_directory_data:n})',
          'gn.post(`${Hr}/commit_unified_submit`,e)',
          'function Eg(N){const O=xc(N);return C0(O),O}',
          'question_order:we?null:fn,is_new_question_insertion:we,insert_after_order:we?na.insertAfterOrder:null'])
        self.js=self.root/'synthetic-frontend.js';self.js.write_text(script,encoding='utf-8')
        self.sha_patch=patch.object(s,'FRONTEND_SHA',hashlib.sha256(self.js.read_bytes()).hexdigest());self.sha_patch.start();self.addCleanup(self.sha_patch.stop)
        self.protocol=s.protocol_evidence(self.js)
        self.source='synthetic-first';self.dest='synthetic-second';self.other='synthetic-other'
        nodes=[{'id':f'node-{q}','label':str(q),'isQuestion':True,'order_in_level':str(q)} for q in range(1,24)]
        self.before={'directory':response({'directory_data':[{'id':'root','children':[
            {'id':self.source,'children':nodes[:22]},{'id':self.dest,'children':[]},{'id':self.other,'children':nodes[22:]}]}],
            'opaque':{'typed':[None,False,1,1.0]}}),'source':response({'synthetic':True})}
        frames=[]
        for q in range(1,24):
            parent=self.source if q<=22 else self.other
            info=dict(zip(INFO_KEYS,[f'info-{q}','synthetic-answer',None,None,None,u.BOOK,str(q),'2026-10-15T00:00:00','2026-10-15T00:00:00']))
            self.before[f'q{q}_info']=response(info)
            rows=[]
            for zone in ('question','answer'):
                values=[zone,0,str(uuid.uuid5(uuid.NAMESPACE_DNS,f'SYNTHETIC-{q}-{zone}')),u.BOOK,'question_level',str(q),0,
                        '1,2,11,22',173 if zone=='answer' else 12,'https://synthetic.invalid/old.jpg',
                        '2026-10-15T00:00:00','2026-10-15T00:00:00',None,parent,'text','111',False,None]
                rows.append(dict(zip(ROW_KEYS,values)))
            frames+=rows;self.before[f'q{q}_annotations']=response(copy.deepcopy(rows))
            for zone in u.ZONES:
                ids=[row['rect_id'] for row in rows if row['type']==zone]
                self.before[f'q{q}_{zone}']=response({'rect_ids':ids,'ocr_result':f'SYNTHETIC old {q} {zone}','success':True} if ids else copy.deepcopy(u.ABSENT))
        self.before['frames']=response(frames)
        for page in (12,13,173,174):
            self.before[f'page_{page}']=response({'file_id':u.BOOK,'pages':[{'image':self.url(page),'page_index':page-1,'blocks':[]}]})
        ids=s.full_snapshot(self.before)
        self.targets=ids[17:22]
        self.move_scope={'schema':'b-usense-move-scope-review/0.1','book_id':u.BOOK,'targets':self.targets,
                         'source_directory_id':self.source,'destination_directory_id':self.dest,'decision':'SOURCE_LESSON_MEMBERSHIP_REVIEWED'}
        self.move=s.make_move_draft(self.before,self.targets,self.dest,self.move_scope,self.protocol,self.now.isoformat())
        self.moved=self.move['expected_full']
        self.ledger=self.root/'ledger';self.ledger.mkdir()

    def url(self,page):
        return f'https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com/upload_images/{u.BOOK}/{u.BOOK}_page_{page-1}.jpg'

    def blocked(self,code,fn):
        with self.assertRaises(ValueError) as cm:fn()
        self.assertEqual(getattr(cm.exception,'code',str(cm.exception)),code)

    def new_inputs(self):
        assets=[];sources={}
        for page in (13,173,174):
            path=self.root/f'viewer-{page}.png';path.write_bytes(png(100,100,page%256));sources[page]=file_ref(path)
            assets.append({'viewer_page':page,'source_page_index':page-1,'url':self.url(page),'file':path.name,'bytes':path.stat().st_size,'sha256':sources[page]['sha256']})
        binding=dump(self.root/'source-binding.json',{'schema':'CurrentPlatformSources/v1','book_id':u.BOOK,'pages':assets})
        frames=[]
        for key,zone,index,content,page in [('stem','question',0,'text',13),('figure','question',1,'image',13),('answer','answer',0,'text',173)]:
            bbox=[index*10,0,index*10+10,20];crop=self.root/(key+'.png');crop.write_bytes(png(10,20,page%256))
            url=self.url(page)+f'?x-oss-process=image/crop,x_{bbox[0]},y_0,w_10,h_20'
            proof={'schema':'b-usense-observed-frame-crop/0.1','book_id':u.BOOK,'viewer_page':page,'source':sources[page],
                   'source_url':self.url(page),'source_dimensions':[100,100],'bbox':bbox,'crop':file_ref(crop),'crop_url':url,'http_status':200,'dimensions':[10,20]}
            frames.append({'key':key,'rect_id':str(uuid.uuid5(uuid.NAMESPACE_DNS,'SYNTHETIC-new-'+key)),'zone':zone,'index':index,
                           'content_type':content,'viewer_page':page,'bbox':bbox,'source':sources[page],'source_binding':binding,
                           'crop':file_ref(crop),'crop_evidence':dump(self.root/(key+'-proof.json'),proof)})
        candidate={'schema':'b-usense-new-question-candidate/0.1','book_id':u.BOOK,'logical_key':'lesson2-q6','printed_number':'6','variant':'main',
                   'target_directory_id':self.dest,'server_identity':{'node_id':None,'info_id':None,'question_order':None},
                   'anchor':s.full_snapshot(self.moved)[21],'frames':frames,
                   'zone_values':{'question':'SYNTHETIC reviewed question <img src="'+self.url(13)+'?x-oss-process=image/crop,x_10,y_0,w_10,h_20" />','answer':'SYNTHETIC reviewed answer'},
                   'question_info':{'tishi':'synthetic-answer','tilei':None,'tihao':None}}
        scope={'schema':'b-usense-new-question-scope-review/0.1','book_id':u.BOOK,'source_lesson':'synthetic-lesson2','directory_id':self.dest,
               'existing_targets':[t for t in s.full_snapshot(self.moved) if t['lesson_directory_id']==self.dest],
               'allowed_new_items':[{'logical_key':'lesson2-q6','printed_number':'6','variant':'main'}],
               'completed_logical_keys':[],'allowed_pages_by_zone':{'question':[13],'answer':[173]},'decision':'SOURCE_LESSON_AND_EXISTING_BINDINGS_REVIEWED'}
        return candidate,scope,self.review(candidate,scope)

    def review(self,candidate,scope):
        return {'schema':'b-usense-new-question-content-review/0.1','candidate_object_sha256':u.digest(candidate),
                'scope_object_sha256':u.digest(scope),'decision':'SOURCE_CONTENT_AND_FRAME_BOUNDARIES_REVIEWED'}

    def new_plan(self):
        c,scope,review=self.new_inputs()
        return n.make_new_draft(self.moved,c,scope,review,self.protocol,self.now.isoformat())

    def new_after(self,plan):
        # Independent synthetic native response construction, not a platform result.
        after=copy.deepcopy(self.moved)
        for suffix in ('annotations','info',*u.ZONES):
            value=after.pop(f'q23_{suffix}')
            if suffix=='info':value['data']['order_in_level']='24'
            if suffix=='annotations':
                for row in value['data']:row['order_in_level']='24'
            after[f'q24_{suffix}']=value
        for row in after['frames']['data']:
            if row['order_in_level']=='23':row['order_in_level']='24'
        dirs=after['directory']['data']['directory_data'][0]['children']
        dirs[2]['children'][0]['order_in_level']='24';dirs[2]['children'][0]['label']='24'
        node={'isQuestion':True,'order_in_level':'23','id':'new-server-node','label':'23'}
        dirs[1]['children'].append(node)
        rows=[]
        for row in plan['request']['body']['annotations_upsert']:
            full={key:copy.deepcopy(row[key]) if key in row else None for key in ROW_KEYS}
            full.update(file_id=u.BOOK,verified=0,order_in_level='23',user_id='222',created_at='2026-10-23T22:00:00',updated_at='2026-10-23T22:00:00')
            rows.append(full)
        after['frames']['data']+=rows;after['q23_annotations']=response(copy.deepcopy(rows))
        info=dict(zip(INFO_KEYS,['new-server-info','synthetic-answer',None,None,None,u.BOOK,'23','2026-10-23T22:00:00','2026-10-23T22:00:00']))
        after['q23_info']=response(info)
        submissions={v['zone']:v for v in plan['request']['body']['ocr_submissions']}
        for zone in u.ZONES:
            sub=submissions.get(zone)
            after[f'q23_{zone}']=response({'rect_ids':sub['rect_ids'],'ocr_result':sub['ocr_result'],'success':True} if sub else copy.deepcopy(u.ABSENT))
        receipt=response({'inserted':True,'question_order':23,'inserted_question_node':node,'success':True,'append_at_global_end':False})
        actor={'runtime_actor_sha256':u.text_digest('synthetic actor'),'runtime_user_id_sha256':u.text_digest('222')}
        return after,receipt,actor

    def test_exact_five_move_draft_and_eighteen_protected_objects(self):
        self.assertEqual(self.move['protected_other_questions'],18)
        self.assertIsNone(self.move['apply_request']);self.assertFalse(self.move['write_authorized'])
        self.assertEqual(list(self.move['preview_request']['body']),['file_id','original_directory_data','draft_directory_data'])
        self.assertTrue(s.verify_move(self.move,self.moved)['match'])
        for q in (*range(1,18),23):
            for suffix in ('annotations','info',*u.ZONES):self.assertTrue(u.json_same(self.before[f'q{q}_{suffix}'],self.moved[f'q{q}_{suffix}']))

    def test_wrong_move_target_info_id_rejected(self):
        targets=copy.deepcopy(self.targets);targets[0]['info_id']='wrong'
        self.blocked('STRUCTURE_MOVE_STABLE_BINDING',lambda:s.make_move_draft(self.before,targets,self.dest,self.move_scope,self.protocol,self.now.isoformat()))

    def test_scope_review_is_required(self):
        self.blocked('STRUCTURE_MOVE_SCOPE_REVIEW_REQUIRED',lambda:s.make_move_draft(self.before,self.targets,self.dest,{},self.protocol,self.now.isoformat()))

    def test_nonempty_destination_and_order_changing_move_rejected(self):
        before=copy.deepcopy(self.before)
        dirs=before['directory']['data']['directory_data'][0]['children'];dirs[1],dirs[2]=dirs[2],dirs[1]
        # Putting the empty destination after the unrelated existing question
        # changes traversal order; the draft refuses unsupported reindexing.
        with self.assertRaises(ValueError):s.make_move_draft(before,self.targets,self.dest,self.move_scope,self.protocol,self.now.isoformat())

    def test_move_unrelated_text_or_timestamp_delta_holds(self):
        for path in ('text','timestamp'):
            after=copy.deepcopy(self.moved)
            if path=='text':after['q1_question']['data']['ocr_result']='changed'
            else:after['q18_info']['data']['updated_at']='2026-10-23T00:00:00'
            self.assertFalse(s.verify_move(self.move,after)['match'])

    def test_fresh_preflight_never_authorizes_a_write(self):
        report=s.preflight(self.move,self.before,self.ledger,now=self.now)
        self.assertFalse(report['write_authorized']);self.assertEqual(report['platform_requests'],0)

    def test_stale_full_book_and_expired_baseline_stop(self):
        changed=copy.deepcopy(self.before);changed['q1_info']['data']['updated_at']='2026-10-23T00:00:00'
        self.blocked('STRUCTURE_STALE_FULL_BOOK',lambda:s.preflight(self.move,changed,self.ledger,now=self.now))
        self.blocked('STRUCTURE_BASELINE_EXPIRED',lambda:s.preflight(self.move,self.before,self.ledger,now=self.now+timedelta(seconds=901)))

    def test_unknown_structural_or_stable_target_intent_blocks(self):
        for key in (self.move['ledger_key'],'usense-existing-'+u.digest({k:self.targets[0][k] for k in ('book_id','node_id','info_id')})):
            path=self.ledger/(key+'.json');dump(path,{'status':'UNKNOWN_DO_NOT_RETRY'})
            self.blocked('STRUCTURE_EXISTING_INTENT_NO_RETRY',lambda:s.preflight(self.move,self.before,self.ledger,now=self.now));path.unlink()

    def test_frontend_hash_or_fragment_change_rejected(self):
        self.js.write_text('different code',encoding='utf-8')
        self.blocked('BATCH_EVIDENCE_HASH_CHANGED',lambda:s.check_protocol(self.protocol))

    def test_generic_new_payload_and_complete_protection_match(self):
        plan=self.new_plan();after,receipt,actor=self.new_after(plan)
        self.assertEqual(plan['new_order'],23);self.assertFalse(plan['write_authorized'])
        self.assertIsNone(plan['request']['body']['question_order'])
        result=n.verify_new(plan,after,receipt,actor)
        self.assertTrue(result['match'],result['differences']);self.assertEqual(result['all_old_questions_checked'],23)
        self.assertFalse(result['platform_acceptance'])

    def test_unmigrated_directory_cannot_receive_a_new_plan(self):
        c,scope,review=self.new_inputs()
        self.blocked('NEW_DESTINATION_MUST_FIRST_HAVE_VERIFIED_EXISTING_BINDINGS',lambda:n.make_new_draft(self.before,c,scope,review,self.protocol,self.now.isoformat()))

    def test_unknown_server_identity_and_rect_reuse_rejected(self):
        c,scope,review=self.new_inputs();c['server_identity']['node_id']='predicted'
        self.blocked('NEW_SERVER_IDENTITY_MUST_BE_UNKNOWN',lambda:n.make_new_draft(self.moved,c,scope,self.review(c,scope),self.protocol,self.now.isoformat()))
        c,scope,review=self.new_inputs();c['frames'][0]['rect_id']=self.moved['frames']['data'][0]['rect_id']
        self.blocked('NEW_RECT_ID_ALREADY_EXISTS',lambda:n.make_new_draft(self.moved,c,scope,self.review(c,scope),self.protocol,self.now.isoformat()))

    def test_wrong_answer_viewer_page_and_wrong_local_source_rejected(self):
        c,scope,review=self.new_inputs();c['frames'][-1]['viewer_page']=174
        self.blocked('NEW_WRONG_SOURCE_PAGE_FOR_ZONE',lambda:n.make_new_draft(self.moved,c,scope,self.review(c,scope),self.protocol,self.now.isoformat()))
        c,scope,review=self.new_inputs();c['frames'][0]['source']=c['frames'][-1]['source']
        self.blocked('NEW_SOURCE_LOCAL_FILE_PAGE_URL_MISMATCH',lambda:n.make_new_draft(self.moved,c,scope,self.review(c,scope),self.protocol,self.now.isoformat()))

    def test_crop_bytes_and_metadata_binding_cannot_drift(self):
        c,scope,review=self.new_inputs();Path(c['frames'][0]['crop']['path']).write_bytes(b'changed')
        self.blocked('BATCH_EVIDENCE_HASH_CHANGED',lambda:n.make_new_draft(self.moved,c,scope,review,self.protocol,self.now.isoformat()))

    def test_unreviewed_item_or_missing_figure_is_rejected(self):
        c,scope,review=self.new_inputs();c['logical_key']='whole-book-unreviewed'
        self.blocked('NEW_ITEM_NOT_EXPLICITLY_REVIEWED_OR_ALREADY_DONE',lambda:n.make_new_draft(self.moved,c,scope,self.review(c,scope),self.protocol,self.now.isoformat()))
        c,scope,review=self.new_inputs();c['zone_values']['question']='figure removed'
        self.blocked('NEW_FIGURE_REFERENCE_NOT_BOUND_TO_REVIEWED_FRAMES',lambda:n.make_new_draft(self.moved,c,scope,self.review(c,scope),self.protocol,self.now.isoformat()))

    def test_new_readback_protects_old_content_and_metadata(self):
        plan=self.new_plan()
        for field in ('question','metadata'):
            after,receipt,actor=self.new_after(plan)
            if field=='question':after['q1_question']['data']['ocr_result']='changed'
            else:after['q24_info']['data']['updated_at']='2026-10-23T22:00:01'
            self.assertFalse(n.verify_new(plan,after,receipt,actor)['match'])

    def test_unknown_receipt_and_wrong_runtime_actor_rejected(self):
        plan=self.new_plan();after,receipt,actor=self.new_after(plan)
        bad=copy.deepcopy(receipt);bad['data']['inserted']=False
        self.blocked('NEW_RECEIPT_UNKNOWN_NO_RETRY',lambda:n.verify_new(plan,after,bad,actor))
        actor['runtime_user_id_sha256']=u.text_digest('wrong actor')
        self.assertFalse(n.verify_new(plan,after,receipt,actor)['match'])

    def test_next_new_question_requires_refreshed_existing_scope(self):
        plan=self.new_plan();after,receipt,actor=self.new_after(plan)
        c,scope,review=self.new_inputs();c['logical_key']='lesson2-q7';c['printed_number']='7'
        c['anchor']=s.full_snapshot(after)[22]
        self.blocked('NEW_SCOPE_BINDINGS_REQUIRE_CURRENT_DIRECTORY_READBACK',lambda:n.make_new_draft(after,c,scope,self.review(c,scope),self.protocol,self.now.isoformat()))

    def test_ledger_key_does_not_change_with_candidate_text(self):
        first=self.new_plan();c,scope,review=self.new_inputs();c['zone_values']['answer']+=' revised'
        second=n.make_new_draft(self.moved,c,scope,self.review(c,scope),self.protocol,self.now.isoformat())
        self.assertEqual(first['ledger_key'],second['ledger_key'])

    def test_offline_tool_help_is_portable(self):
        tool=Path(__file__).resolve().parents[1]/'tools/prepare_usense_structure.py'
        proc=subprocess.run([sys.executable,'-B',str(tool),'--help'],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertIn('prepare-move',proc.stdout);self.assertIn('prepare-new',proc.stdout)


if __name__=='__main__':unittest.main()
