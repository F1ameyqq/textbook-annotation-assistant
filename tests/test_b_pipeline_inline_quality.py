"""Durable inline audit: semantic faults survive coherent file/SQL re-signing."""
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from annotation.recognition import pipeline,inline_stage
from annotation.recognition.baseline import digest
from annotation.recognition.pipeline_quality import audit_pipeline
from test_b_inline_stage import make_inline_fixture
from test_b_inline_stage_quality import resign


def ref(value):return {k:value[k]for k in ('artifact_id','revision','content_hash')}


class PipelineInlineQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.d=make_inline_fixture(self.temp.name);self.work=Path(self.temp.name)/'pipeline'

    def run_case(self,**kwargs):
        return pipeline.run_pipeline(self.d['source_path'],self.d['context_path'],self.d['review_path'],self.work,
            evidence_path=self.d['evidence_path'],inline_path=self.d['package_path'],inline_source_path=self.d['original'],**kwargs)

    def check(self,r):
        return audit_pipeline(self.d['source_path'],self.d['context_path'],self.d['review_path'],r,self.work,
            evidence_path=self.d['evidence_path'],inline_path=self.d['package_path'],inline_source_path=self.d['original'])['payload']

    def rejected(self,result,code):
        self.assertFalse(result['accepted'],result);self.assertIn(code,{x['code']for x in result['issues']},result)
        self.assertEqual(result['decision'],'HOLD')

    def read(self,descriptor):return json.loads((self.work/descriptor['path']).read_text(encoding='utf8'))

    def put(self,value):
        value['content_hash']=digest(value['payload'])
        if value['kind']=='PipelineStageTrial':value['artifact_id']='pipeline-stage-'+digest(value['payload'])[:24]
        raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8');sha=hashlib.sha256(raw).hexdigest();path='objects/'+sha+'.json'
        (self.work/path).write_bytes(raw)
        return dict(path=path,sha256=sha,artifact_ref=ref(value))

    def publish(self,r):
        r['content_hash']=digest(r['payload']);r['artifact_id']='pipeline-report-'+digest([r['payload']['source_ref'],r['producer'],r['payload']])[:24]
        descriptor=self.put(r)
        with closing(sqlite3.connect(self.work/'pipeline.sqlite3'))as db:
            with db:
                for eid,raw in db.execute("SELECT event_id,details_json FROM stage_events WHERE run_id=? AND event_type='RUN_FINISHED'",(r['run_id'],)).fetchall():
                    d=json.loads(raw);d.update(report_ref=ref(r),report_artifact=descriptor)
                    db.execute('UPDATE stage_events SET details_json=? WHERE event_id=?',(json.dumps(d),eid))

    def rewrite_stage(self,r,stage,mutate,*,configuration=None):
        """Replace a terminal tested stage while keeping actual origin receipts coherent."""
        entry=next(s for s in r['payload']['stages']if s['stage_id']==stage);oldkey=entry['expected_key']
        wrapper=self.read(entry['output']);result=wrapper['payload']['result'];mutate(result)
        if configuration:configuration(entry['implementation']['configuration'])
        key=digest(dict(mode=r['payload']['mode'],stage_id=stage,dependencies=entry['dependencies'],implementation=entry['implementation']))
        wrapper['payload'].update(result=result,expected_key=key,implementation=copy.deepcopy(entry['implementation']))
        descriptor=self.put(wrapper);entry.update(output=descriptor,result_ref=ref(result),expected_key=key)
        with closing(sqlite3.connect(self.work/'pipeline.sqlite3'))as db:
            with db:
                db.execute('UPDATE stage_attempts SET expected_key=?,implementation_json=?,output_json=?,result_ref_json=? WHERE attempt_id=?',
                    (key,json.dumps(entry['implementation']),json.dumps(descriptor),json.dumps(ref(result)),entry['origin_attempt_id']))
                db.execute('UPDATE stage_cache SET expected_key=?,output_json=?,result_ref_json=? WHERE expected_key=?',(key,json.dumps(descriptor),json.dumps(ref(result)),oldkey))
                for eid,raw in db.execute('SELECT event_id,details_json FROM stage_events WHERE attempt_id=?',(entry['origin_attempt_id'],)).fetchall():
                    d=json.loads(raw)
                    if 'expected_key'in d:d['expected_key']=key
                    if 'output'in d:d['output']=descriptor
                    if 'result_ref'in d:d['result_ref']=ref(result)
                    db.execute('UPDATE stage_events SET details_json=? WHERE event_id=?',(json.dumps(d),eid))
        if stage=='inline_quality'and r['payload'].get('final_outputs'):r['payload']['final_outputs']['quality_ref']=ref(result)
        self.publish(r)

    def test_ready_current_graph05_and_check05_are_final_and_unselected(self):
        r=self.run_case();c=self.check(r);self.assertTrue(c['accepted'],c)
        self.assertEqual([s['stage_id']for s in r['payload']['stages']][-3:],['inline_prepare','inline_apply','inline_quality'])
        app=self.read(r['payload']['stages'][-2]['output'])['payload']['result'];check=self.read(r['payload']['stages'][-1]['output'])['payload']['result']
        self.assertEqual(r['payload']['final_outputs']['graph_ref'],ref(app['payload']['graph']))
        self.assertEqual(check['payload']['graph_ref'],ref(app['payload']['graph']))
        self.assertEqual(check['schema_version'],'b-check-trial/0.5');self.assertEqual(c['decision'],'HOLD')
        self.assertEqual(app['payload']['graph']['payload']['inline_content']['selected_candidate_refs'],[])

    def test_warm_cache_retains_original_attempts_and_current_run_cache_receipts(self):
        first=self.run_case();warm=self.run_case();self.assertTrue(self.check(warm)['accepted'])
        self.assertEqual(warm['payload']['counts']['cache_hits'],6)
        for old,new in zip(first['payload']['stages'],warm['payload']['stages']):
            self.assertEqual(old['origin_attempt_id'],new['origin_attempt_id']);self.assertEqual(new['current_run_receipt']['event_type'],'CACHE_HIT')
            self.assertEqual(new['current_run_receipt']['run_id'],warm['run_id'])

    def test_review_only_change_reuses_prepare_apply_but_quality_is_current(self):
        first=self.run_case();path=self.d['review_path'];review=json.loads(path.read_text(encoding='utf8'));review['explicit_test_revision']='new-review-only'
        path.write_text(json.dumps(review),encoding='utf8');r=self.run_case();c=self.check(r);self.assertTrue(c['accepted'],c)
        self.assertEqual([s['cached']for s in r['payload']['stages']],[True,True,False,True,True,False])
        self.assertEqual(first['payload']['stages'][-2]['output'],r['payload']['stages'][-2]['output'])

    def test_partial_keeps_full_saved_scope_and_has_no_final_outputs(self):
        with tempfile.TemporaryDirectory()as root:
            self.d=make_inline_fixture(root,max_items=1);self.work=Path(root)/'pipeline'
            r=self.run_case();c=self.check(r);self.assertTrue(c['accepted'],c)
            self.assertEqual(r['payload']['pipeline_state'],'PARTIAL');self.assertIsNone(r['payload']['final_outputs'])
            self.assertEqual([s['state']for s in r['payload']['stages']][-3:],['PARTIAL','WAITING','WAITING'])
            saved=self.read(r['payload']['stages'][-3]['output'])['payload']['result'];self.assertGreater(saved['payload']['counts']['declared_calls'],1)

    def test_honest_failed_raw_observation_is_integrity_checked_without_business_release(self):
        with tempfile.TemporaryDirectory()as root:
            self.d=make_inline_fixture(root,fail=True);self.work=Path(root)/'pipeline';r=self.run_case();c=self.check(r)
            self.assertTrue(c['accepted'],c);self.assertEqual(r['payload']['pipeline_state'],'FAILED');self.assertIsNone(r['payload']['final_outputs'])

    def test_consumer_never_runs_pipeline_inline_candidate_parser_models_or_network(self):
        r=self.run_case()
        with patch.object(pipeline,'run_pipeline',side_effect=AssertionError('runner')), \
             patch.object(inline_stage,'prepare_inline_stage',side_effect=AssertionError('prepare')), \
             patch.object(inline_stage,'apply_inline_stage',side_effect=AssertionError('apply')), \
             patch('annotation.recognition.inline_candidates.build_inline_candidates',side_effect=AssertionError('candidate')), \
             patch('annotation.recognition.formula_syntax.parse_inline_formula_latex',side_effect=AssertionError('parser')), \
             patch.dict(sys.modules,{'rapidocr_onnxruntime':None,'onnxruntime':None,'rapid_latex_ocr':None}),patch('socket.socket',side_effect=AssertionError('network')):
            self.assertTrue(self.check(r)['accepted'])

    def test_coherent_graph_core_change_is_rejected_beyond_object_SQL_and_report_hashes(self):
        r=self.run_case(stop_after='inline_apply')
        def mutate(value):
            value['payload']['graph']['payload']['answers'][0]['text']='corrected by model';resign(value['payload']['graph']);resign(value)
        self.rewrite_stage(r,'inline_apply',mutate)
        c=self.check(r);self.rejected(c,'PIPELINE_INLINE_STAGE_REJECTED')
        self.assertNotIn('PIPELINE_STAGE_ORIGIN_MISMATCH',{i['code']for i in c['issues']})
        self.assertIn('INLINE_GRAPH_CORE_CHANGED',str(c['issues']))

    def test_coherent_dropped_calls_in_attachment_is_rejected(self):
        r=self.run_case(stop_after='inline_apply')
        def mutate(value):
            value['payload']['graph']['payload']['inline_content']['calls'].pop();resign(value['payload']['graph']);resign(value)
        self.rewrite_stage(r,'inline_apply',mutate);self.rejected(self.check(r),'PIPELINE_INLINE_STAGE_REJECTED')

    def test_coherent_check_cannot_remove_prior_business_findings(self):
        r=self.run_case()
        def mutate(value):value['payload']['issues'].pop(0);value['payload']['summary']['issues']-=1;resign(value)
        self.rewrite_stage(r,'inline_quality',mutate);c=self.check(r);self.rejected(c,'PIPELINE_INLINE_STAGE_REJECTED')
        self.assertIn('INLINE_CHECK_PRESERVATION_OR_RISK_MISMATCH',str(c['issues']))

    def test_inline_implementation_policy_cannot_change_with_coherent_new_stage_key(self):
        r=self.run_case(stop_after='inline_prepare')
        self.rewrite_stage(r,'inline_prepare',lambda v:None,configuration=lambda c:c.update(inline_policy='relaxed-page-hash-only'))
        self.rejected(self.check(r),'PIPELINE_IMPLEMENTATION_VERSION_MISMATCH')

    def test_missing_original_success_event_rejects_current_cache_hit(self):
        self.run_case();r=self.run_case();entry=r['payload']['stages'][-3]
        with closing(sqlite3.connect(self.work/'pipeline.sqlite3'))as db:
            with db:db.execute("DELETE FROM stage_events WHERE attempt_id=? AND event_type='STAGE_SUCCEEDED'",(entry['origin_attempt_id'],))
        self.rejected(self.check(r),'PIPELINE_ATTEMPT_EVENT_MISMATCH')

    def test_claimed_final_G03_or_no_current_check_cannot_be_published(self):
        r=self.run_case();r['payload']['final_outputs']['graph_ref']=r['payload']['stages'][1]['result_ref'];self.publish(r)
        self.rejected(self.check(r),'PIPELINE_INLINE_FINAL_OUTPUTS_MISMATCH')

    def test_exact_report_header_rejects_false_human_claim_even_with_bound_immutable_receipt(self):
        r=self.run_case();r['human_verified']=True;self.publish(r);self.rejected(self.check(r),'PIPELINE_REPORT_INVALID')

    def test_source_journal_change_after_run_is_not_a_valid_cached_receipt(self):
        r=self.run_case();p=self.d['journal_dir']/'inline-formula.sqlite3';p.write_bytes(p.read_bytes()+b'changed')
        self.rejected(self.check(r),'PIPELINE_PERSISTED_DATA_INVALID')

    def test_continuation_children_are_bound_by_inner_E6_G4_not_outer_stage_refs(self):
        with tempfile.TemporaryDirectory()as root:
            d=make_inline_fixture(root,continuation=True);work=Path(root)/'pipeline'
            kwargs=dict(evidence_path=d['evidence_path'],continuation_path=d['continuation_path'],adjacent_source_path=d['adjacent_source_path'],
                inline_path=d['package_path'],inline_source_path=d['original'])
            r=pipeline.run_pipeline(d['source_path'],d['context_path'],d['review_path'],work,**kwargs)
            c=audit_pipeline(d['source_path'],d['context_path'],d['review_path'],r,work,**kwargs)['payload']
            self.assertTrue(c['accepted'],c)
            entries={s['stage_id']:s for s in r['payload']['stages']}
            read=lambda name:json.loads((work/entries[name]['output']['path']).read_text(encoding='utf8'))['payload']['result']
            e6=read('continuation_prepare')['payload']['evidence'];g4=read('continuation_apply')['payload']['graph'];p=read('inline_prepare')
            self.assertEqual(entries['inline_prepare']['dependencies']['evidence']['result_ref'],ref(e6))
            self.assertNotEqual(entries['inline_prepare']['dependencies']['evidence']['result_ref'],entries['continuation_prepare']['result_ref'])
            self.assertEqual(p['payload']['base_graph_ref'],ref(g4))
            self.assertEqual(read('inline_quality')['payload']['base_check_archive'],read('continuation_quality'))


if __name__=='__main__':unittest.main()
