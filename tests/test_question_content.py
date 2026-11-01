import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.recognition import question_content as producer
from annotation.recognition.question_content_quality import audit_question_content
from annotation.recognition.baseline import digest

def resign(app):
    app['content_hash']=digest(app['payload'])
    app['artifact_id']='question-content-application-'+digest({k:v for k,v in app.items()if k!='artifact_id'})[:24]

class QuestionContentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        with zipfile.ZipFile(ROOT/'tests/fixtures/book46007447/viewer15-question-draft-v4.zip')as z:
            manifest=json.loads(z.read('MANIFEST.json'))
            for name,entry in manifest.items():
                raw=z.read(name);self.assertEqual(hashlib.sha256(raw).hexdigest(),entry['sha256']);(self.root/name).write_bytes(raw)
        self.e=producer.read_json(self.root/'evidence.json');self.g=producer.read_json(self.root/'graph.json')
        self.plan=self.root/'plan.json';self.sha=hashlib.sha256(self.plan.read_bytes()).hexdigest();self.crops=self.root/'crops'
    def apply(self):return producer.apply_question_content(self.root/'source.json',self.e,self.g,self.plan,expected_plan_sha256=self.sha,output_dir=self.crops)
    def audit(self,app):return audit_question_content(self.root/'source.json',self.e,self.g,self.plan,app,expected_plan_sha256=self.sha,crop_dir=self.crops)
    def change_plan(self,edit):
        p=producer.read_json(self.plan);edit(p['payload']);p['content_hash']=digest(p['payload'])
        self.plan.write_text(json.dumps(p,ensure_ascii=False),encoding='utf-8');self.sha=hashlib.sha256(self.plan.read_bytes()).hexdigest()
    def test_real_page_projection_preserves_raw_and_all_separate_content_units(self):
        before=copy.deepcopy((self.e,self.g));app=self.apply();self.assertTrue(self.audit(app)['accepted'])
        self.assertEqual(before,(self.e,self.g));self.assertEqual(app['payload']['source_graph_archive'],self.g)
        blocks=[b for q in app['payload']['questions']for b in q['blocks']]
        self.assertEqual(len(blocks),23);self.assertEqual(sum(b['role']=='option'for b in blocks),12)
        self.assertEqual(sum(b['role']=='figure'for b in blocks),2);self.assertEqual(sum(b['role']=='task'for b in blocks),3)
        self.assertEqual(sum(r['format']=='blank'for b in blocks for r in b.get('runs',[])),7)
        self.assertEqual(len(app['payload']['source_ledger']),62);self.assertFalse(app['payload']['answer_matching_performed'])
        self.assertEqual(self.apply(),app)
    def test_independent_auditor_does_not_call_producer(self):
        app=self.apply()
        with patch.object(producer,'apply_question_content',side_effect=AssertionError('producer forbidden')):
            self.assertTrue(self.audit(app)['accepted'])
    def test_fixed_file_sha_rejects_even_resigned_plan(self):
        original_sha=self.sha
        self.change_plan(lambda p:p['questions'][0]['blocks'][0]['runs'][0].update(text='invented text'))
        self.sha=original_sha
        with self.assertRaisesRegex(ValueError,'fixed plan'):self.apply()
    def test_current_source_pixel_change_is_rejected(self):
        app=self.apply();path=self.root/'46007447_page_14.jpg'
        Image.new('RGB',(1219,1703),'white').save(path)
        with self.assertRaisesRegex(ValueError,'SHA'):self.apply()
        self.assertFalse(self.audit(app)['accepted'])
    def test_exported_figure_cannot_be_rescaled_or_changed(self):
        app=self.apply();path=self.crops/'q15-figure.png'
        with Image.open(path)as original:original.resize((20,20)).save(path)
        self.assertFalse(self.audit(app)['accepted'])
    def test_re_signed_projection_cannot_fill_blank_or_drop_risk(self):
        app=self.apply()
        for change in ('blank','risk','raw'):
            with self.subTest(change=change):
                forged=copy.deepcopy(app)
                if change=='blank':forged['payload']['questions'][0]['blocks'][0]['runs'][1]['value']='A'
                elif change=='risk':forged['payload']['risks']=[]
                else:forged['payload']['source_graph_archive']['payload']['questions'][0]['text']='changed raw'
                resign(forged);self.assertFalse(self.audit(forged)['accepted'])
    def test_bad_structural_plans_rejected_even_with_new_file_sha(self):
        raw=self.plan.read_bytes()
        def reverse_and_rebind(p):
            parts=p['questions'][5]['blocks'][2]['fraction_components'];parts.reverse()
            for component,index in zip(parts,[1,3,5,7]):component['run_index']=index
        mutations=[
          ('filled blank',lambda p:p['questions'][0]['blocks'][0]['runs'][1].update(value='A')),
          ('lost figure',lambda p:p['questions'][4]['blocks'].pop()),
          ('task order',lambda p:p['questions'][5]['blocks'].reverse()),
          ('cross question',lambda p:p['questions'][0].update(question_bbox=[58,120,592,625])),
          ('option source',lambda p:p['questions'][0]['blocks'][1].update(label='B')),
          ('missing fraction',lambda p:p['questions'][2]['blocks'][4].update(fraction_components=[])),
          ('false approval',lambda p:p.update(human_verification=True)),
          ('unknown flag',lambda p:p['questions'][0]['blocks'][0].update(verified=True)),
          ('raw rewrite',lambda p:p['page_ocr_snapshot'][3].update(text='different OCR')),
          ('float box',lambda p:p['questions'][0]['question_bbox'].__setitem__(0,58.0)),
          ('boolean box',lambda p:p['questions'][0]['question_bbox'].__setitem__(0,False)),
          ('badge approval',lambda p:p['questions'][0]['blocks'][0]['editorial_badges'][0].update(verification_status='VERIFIED')),
          ('duplicate fraction',lambda p:p['questions'][5]['blocks'][2]['fraction_components'].__setitem__(1,copy.deepcopy(p['questions'][5]['blocks'][2]['fraction_components'][0]))),
          ('reverse fraction',lambda p:p['questions'][5]['blocks'][2]['fraction_components'].reverse()),
          ('reverse and rebind fraction',reverse_and_rebind),
        ]
        for label,edit in mutations:
            with self.subTest(label=label):
                self.plan.write_bytes(raw);self.change_plan(edit)
                with self.assertRaises((ValueError,KeyError)):self.apply()
    def test_full_base_envelopes_are_bound_in_both_paths(self):
        app=self.apply();originals=copy.deepcopy((self.e,self.g))
        for target in ('e','g'):
            for field in ('kind','run_id','producer','input_refs','created_at','extra'):
                with self.subTest(target=target,field=field):
                    self.e,self.g=copy.deepcopy(originals);value=getattr(self,target)
                    if field=='input_refs':value[field].append({'artifact_id':'forged','content_hash':'0'*64})
                    elif field=='producer':value[field]={'module':'forged'}
                    else:value[field]='forged'
                    with self.assertRaisesRegex(ValueError,'base'):self.apply()
                    self.assertFalse(self.audit(app)['accepted'])
    def test_unknown_or_mixed_base_schemas_rejected(self):
        for schema in ('b-graph-trial/0.8','b-graph-trial/0.9','b-graph-trial/0.10','unknown'):
            with self.subTest(schema=schema):
                self.g['schema_version']=schema
                with self.assertRaisesRegex(ValueError,'base pair'):self.apply()
    def test_duplicate_json_is_rejected(self):
        self.plan.write_text('{"payload":{},"payload":{}}',encoding='utf-8');self.sha=hashlib.sha256(self.plan.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'duplicate JSON'):self.apply()
    def test_audit_is_bound_to_current_application_and_external_plan(self):
        app=self.apply();check=self.audit(app)
        self.assertEqual(check['application_ref'],producer.ref(app));self.assertEqual(check['plan_file_sha256'],self.sha)
        self.assertFalse(check['business_acceptance']);self.assertFalse(check['complete']);self.assertEqual(check['decision'],'HOLD')

if __name__=='__main__':unittest.main()
