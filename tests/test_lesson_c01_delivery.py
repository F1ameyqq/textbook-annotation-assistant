"""Synthetic portable C01 source/content mutation tests; no website or OCR."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

TOOLS=Path(__file__).resolve().parents[1]/'tools'
def load(name):
    spec=importlib.util.spec_from_file_location(name,TOOLS/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
p=load('export_lesson_c01_b');v=load('verify_lesson_c01_b')


class LessonDeliveryTests(unittest.TestCase):
    def test_synthetic_fixture_is_not_promoted_to_observed_evidence(self):
        bundle=json.loads(p.build_delivery(self.spec,self.images)['bundle.json'])
        self.assertTrue(all(record['mode']=='SYNTHETIC' for record in bundle['evidence']))
        self.assertTrue(all(a['producer']['evidence_mode']=='SYNTHETIC' for a in bundle['artifacts']))

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.folder=self.root/'delivery'
        image=Image.new('RGB',(160,150),'#ccc');stream=io.BytesIO();image.save(stream,format='JPEG');raw=stream.getvalue()
        self.images={'viewer-2':raw}
        self.spec={'schema':'b-private-lesson-source-export-input/0.1','book_id':'synthetic-book','scope_id':'synthetic-scope',
            'source_label':'Synthetic lesson','evidence_mode':'SYNTHETIC','source_input_sha256':'1'*64,'root_review_sha256':'2'*64,'crop_manifest_sha256':'3'*64,
            'review_kind':'B_MODEL_SOURCE_CONFIRMED','assets':[{'asset_id':'viewer-2','viewer_page':2,'path':'not-a-real-private-path.jpg','sha256':p.sha(raw),'width':160,'height':150}],
            'items':[{'item_key':'synthetic-q1','printed_number':'1','variant_index':None,'parent_item_key':None,'semantic_kind':'single_choice',
                      'fields':{'question':'Synthetic ____ question','choice':'A. one\nB. two\nC. three\nD. four','answer':'B','analysis':None},'review_kind':'B_MODEL_SOURCE_CONFIRMED','human_verified':False},
                     {'item_key':'synthetic-q2','printed_number':'2','variant_index':None,'parent_item_key':None,'semantic_kind':'worked_response',
                      'fields':{'question':'Synthetic second question','choice':None,'answer':'Synthetic answer','analysis':None},'review_kind':'B_MODEL_SOURCE_CONFIRMED','human_verified':False}],
            'blocks':[],'exclusions':[{'block_id':'unrelated-source','asset_id':'viewer-2','bbox':[100,100,140,140],'evidence_region':False,'reason':'Out of declared scope.'}],
            'raw_primary_observations':[],'scope_notes':['Synthetic fixture only.']}
        for item_index,item in enumerate(self.spec['items']):
            for field,value in item['fields'].items():
                if value is None:continue
                y=5+item_index*60+list(item['fields']).index(field)*10
                self.spec['blocks'].append({'block_id':item['item_key']+'-'+field,'item_key':item['item_key'],'field':field,
                    'role':{'question':'stem','choice':'option','answer':'answer','analysis':'explanation'}[field],
                    'asset_id':'viewer-2','bbox':[5,y,80,y+9],'content_type':'text','text':value})
        self.build()

    def build(self):
        self.blobs=p.build_delivery(self.spec,self.images)
        if self.folder.exists():
            for name,raw in self.blobs.items():
                path=self.folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        else:p.write_delivery(self.folder,self.blobs)

    def mutate(self,name,fn):
        path=self.folder/name;value=json.loads(path.read_bytes());fn(value);path.write_bytes(p.encode(value))

    def test_full_readback_confirms_answers_without_human_signature_gate(self):
        result=v.verify(self.folder)
        self.assertEqual(result['selected_answer_relations'],2)
        self.assertEqual(result['pending_option_geometry'],['synthetic-q1'])
        self.assertEqual(result['unfilled_question_blanks'],1)
        self.assertFalse(result['human_verified'])

    def test_frozen_rebuild_is_byte_identical(self):
        basis=json.loads(self.blobs['basis.json']);generation=json.loads(self.blobs['generation.json'])
        self.assertEqual(p.build_delivery(basis,self.images,generation),self.blobs)

    def test_all_excluded_clues_have_empty_region_ids(self):
        bundle=json.loads(self.blobs['bundle.json']);ev=next(a for a in bundle['artifacts'] if a['kind']=='EvidenceBundle')
        self.assertTrue(all(c['region_ids']==[] for c in ev['payload']['coverage_clues'] if c['disposition']=='EXCLUDED'))

    def test_fake_human_acceptance_is_rejected(self):
        self.mutate('delivery.json',lambda d:d.update(human_verified=True))
        with self.assertRaisesRegex(ValueError,'ACCEPTANCE_PROMOTION'):v.verify(self.folder)

    def test_changed_original_asset_is_rejected(self):
        path=self.folder/'assets/viewer-2.jpg';raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        with self.assertRaisesRegex(ValueError,'ORIGINAL_SOURCE_HASH'):v.verify(self.folder)

    def test_changed_crop_rejected_even_when_crop_digest_is_updated(self):
        delivery=json.loads((self.folder/'delivery.json').read_bytes());proof=delivery['source_proofs'][0]
        image=Image.new('RGB',(75,9),'white');stream=io.BytesIO();image.save(stream,format='PNG');raw=stream.getvalue()
        (self.folder/proof['path']).write_bytes(raw);proof['sha256']=p.sha(raw);proof['rgb_sha256']=p.sha(image.tobytes())
        (self.folder/'delivery.json').write_bytes(p.encode(delivery))
        with self.assertRaisesRegex(ValueError,'ORIGINAL_CROP_PIXELS'):v.verify(self.folder)

    def test_combined_option_cannot_be_claimed_resolved(self):
        self.mutate('delivery.json',lambda d:d.update(pending_option_geometry=[]))
        with self.assertRaisesRegex(ValueError,'PRECISE_OPTION'):v.verify(self.folder)

    def test_extra_valid_artifact_is_rejected(self):
        self.mutate('bundle.json',lambda b:b['artifacts'].append(copy.deepcopy(b['artifacts'][0])))
        with self.assertRaisesRegex(ValueError,'FOUR_ARTIFACT'):v.verify(self.folder)

    def test_personal_or_remote_paths_rejected(self):
        self.mutate('delivery.json',lambda d:d.update(unreviewed_reference='C:/Users/private/example.json'))
        with self.assertRaisesRegex(ValueError,'NONPORTABLE'):v.verify(self.folder)

    def test_unresolved_answers_cannot_erase_confirmed_b_associations(self):
        def change(bundle):
            graph=next(a for a in bundle['artifacts'] if a['kind']=='QuestionGraph');graph['payload']['answer_relations'][0]['selected_fragment_ids']=[]
            graph['payload']['answer_relations'][0]['status']='UNRESOLVED';graph.update(p.seal(graph))
            check=next(a for a in bundle['artifacts'] if a['kind']=='CheckReport');check['payload']['graph']=check['payload']['subject']=p.ref(graph);check.update(p.seal(check))
            self.mutate('delivery.json',lambda d:d.update(c01_graph_ref=p.ref(graph)))
        self.mutate('bundle.json',change)
        with self.assertRaisesRegex(ValueError,'CONFIRMED_ANSWER_PAIRING'):v.verify(self.folder)

    def test_separate_options_resolve_gap_and_old_group_is_diagnostic_only(self):
        old=next(b for b in self.spec['blocks'] if b['field']=='choice');old.update(field='choice-original-diagnostic',graph_fragment=False,bbox=[5,15,80,60])
        text=self.spec['items'][0]['fields']['choice'].splitlines();at=self.spec['blocks'].index(old)
        options=[]
        for index,line in enumerate(text):
            options.append({**old,'block_id':'derived-'+str(index),'field':'choice','text':line+('\n' if index<3 else ''),
                'bbox':[5,15+index*10,80,24+index*10],'graph_fragment':True,'derived_from_block_id':old['block_id']})
        self.spec['blocks'][at+1:at+1]=options;self.build()
        result=v.verify(self.folder);self.assertEqual(result['pending_option_geometry'],[])
        bundle=json.loads(self.blobs['bundle.json']);graph=next(a for a in bundle['artifacts'] if a['kind']=='QuestionGraph')
        self.assertEqual(sum(f['role']=='option' for f in graph['payload']['fragments']),4)
        check=next(a for a in bundle['artifacts'] if a['kind']=='CheckReport')
        self.assertFalse(any(i['code']=='OPTION_INCOMPLETE' for i in check['payload']['issues']))

    def test_child_outside_source_group_requires_explicit_review(self):
        old=next(b for b in self.spec['blocks'] if b['field']=='choice');old.update(field='choice-original-diagnostic',graph_fragment=False)
        self.spec['blocks'].append({**old,'block_id':'out-of-bounds-child','field':'choice','text':'A. one','bbox':[5,10,80,14],
            'graph_fragment':True,'derived_from_block_id':old['block_id']})
        with self.assertRaisesRegex(ValueError,'OUTSIDE_REVIEWED_CONTAINER'):p.build_delivery(self.spec,self.images)

    def test_duplicate_json_keys_and_nonfinite_numbers_are_rejected(self):
        path=self.root/'bad.json'
        for text in ('{"a":1,"a":1}','{"value":NaN}','{"value":1e9999}'):
            path.write_text(text,encoding='utf-8')
            with self.assertRaises(ValueError):v.read(path)


if __name__=='__main__':unittest.main()
