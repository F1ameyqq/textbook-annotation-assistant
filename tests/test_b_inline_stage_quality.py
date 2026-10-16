"""Independent saved-evidence and additive graph consumer fault regressions."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from annotation.recognition import inline_stage as producer,offline
from annotation.recognition.baseline import digest
from annotation.recognition.inline_stage_quality import (audit_inline_preparation,audit_inline_application,audit_inline_quality,
    inspect_inline_package,_continuity)
from test_b_inline_stage import make_inline_fixture,refresh_inline_package
from test_b_inline_formula import FormulaWorker
from annotation.recognition.inline_formula import collect_inline_formula
import test_b_inline_continuity as continuity_cases


def resign(value):
    """Deliberately coordinate self hashes, rather than testing only stale hashes."""
    prefixes={'InlinePreparationTrial':'inline-preparation','InlineApplyStageTrial':'inline-apply-stage',
        'QuestionGraphTrial':'inline-graph','CheckReportTrial':'inline-check','InlineContinuityTrial':'inline-continuity'}
    body={k:v for k,v in value.items()if k not in {'artifact_id','content_hash'}}
    value['content_hash']=digest(value['payload']);value['artifact_id']=prefixes[value['kind']]+'-'+digest(body)[:24]
    return value


class InlineStageQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.d=make_inline_fixture(self.temp.name)
        self.p=producer.prepare_inline_stage(self.d['evidence'],self.d['graph'],self.d['package_path'],self.d['original'])
        self.a=producer.apply_inline_stage(self.p)
        self.c=producer.build_inline_quality(self.p,self.a,self.d['base_check'])

    def prepare_check(self,p=None,e=None,g=None):
        return audit_inline_preparation(e or self.d['evidence'],g or self.d['graph'],p or self.p,self.d['package_path'],self.d['original'])['payload']

    def apply_check(self,a=None,p=None):
        return audit_inline_application(p or self.p,a or self.a,self.d['package_path'],self.d['original'])['payload']

    def quality_check(self,c=None,base=None):
        return audit_inline_quality(self.p,self.a,base or self.d['base_check'],c or self.c,self.d['package_path'],self.d['original'])['payload']

    def rejected(self,result,code=None):
        self.assertFalse(result['accepted'],result)
        if code:self.assertIn(code,{i['code']for i in result['issues']},result)
        self.assertEqual(result['decision'],'HOLD');self.assertFalse(result['business_acceptance'])

    def test_all_three_independent_consumers_hold_and_do_not_execute_producers(self):
        with patch.object(producer,'prepare_inline_stage',side_effect=AssertionError('producer rerun')), \
             patch.object(producer,'apply_inline_stage',side_effect=AssertionError('producer rerun')), \
             patch.object(producer,'build_inline_quality',side_effect=AssertionError('producer rerun')), \
             patch('annotation.recognition.inline_candidates.build_inline_candidates',side_effect=AssertionError('candidate rerun')), \
             patch('annotation.recognition.inline_continuity.build_inline_continuity',side_effect=AssertionError('relation rerun')), \
             patch.dict(sys.modules,{'rapidocr_onnxruntime':None,'onnxruntime':None,'rapid_latex_ocr':None}), \
             patch('socket.socket',side_effect=AssertionError('network')):
            for result in (self.prepare_check(),self.apply_check(),self.quality_check()):
                self.assertTrue(result['accepted'],result);self.assertEqual(result['new_model_calls'],0)
        self.assertEqual(self.a['payload']['graph']['payload']['inline_content']['selected_candidate_refs'],[])
        self.assertEqual(self.c['payload']['issues'][:-1],self.d['base_check']['payload']['issues'])

    def test_new_current_identity_with_same_full_page_can_bind_old_observations(self):
        e=copy.deepcopy(self.d['evidence']);e['artifact_id']='independently-current-evidence'
        g=offline.assemble(e);p=producer.prepare_inline_stage(e,g,self.d['package_path'],self.d['original'])
        self.assertTrue(self.prepare_check(p,e,g)['accepted'])
        self.assertNotEqual(p['payload']['base_evidence_ref'],producer.reference(p['payload']['original_evidence_archive']))

    def test_full_page_score_or_context_changes_reject_even_with_new_current_refs(self):
        for fault in ('score','other_raw_row','context','boolean_descriptor'):
            e=copy.deepcopy(self.d['evidence'])
            if fault=='score':e['payload']['pages'][0]['ocr_lines'][0]['score']+=.01
            elif fault=='other_raw_row':e['payload']['pages'][0]['ocr_lines'].append(dict(e['payload']['pages'][0]['ocr_lines'][0],line_id='other/raw'))
            elif fault=='context':e['payload']['context']['new_configuration']='changed'
            else:e['payload']['pages'][0]['source']['reading_order']=False
            e['content_hash']=digest(e['payload']);e['artifact_id']='forged-current-'+fault
            g=offline.assemble(e);p=copy.deepcopy(self.p)
            p['payload'].update(base_evidence_archive=e,base_evidence_ref=producer.reference(e),base_graph_archive=g,base_graph_ref=producer.reference(g))
            p['input_refs'][:2]=[producer.reference(e),producer.reference(g)];resign(p)
            with self.subTest(fault=fault):self.rejected(self.prepare_check(p,e,g),'INLINE_SELECTED_PAGE_EQUIVALENCE_MISMATCH')

    def test_partial_and_honest_failed_observations_are_traceable_but_cannot_apply(self):
        for kwargs,state in (({'max_items':1},'PARTIAL'),({'fail':True},'FAILED')):
            with self.subTest(state=state),tempfile.TemporaryDirectory()as root:
                d=make_inline_fixture(root,**kwargs);p=producer.prepare_inline_stage(d['evidence'],d['graph'],d['package_path'],d['original'])
                result=audit_inline_preparation(d['evidence'],d['graph'],p,d['package_path'],d['original'])['payload']
                self.assertTrue(result['accepted'],result);self.assertEqual(result['summary']['execution_state'],state)
                fake=copy.deepcopy(self.a);fake['input_refs']=[producer.reference(p)]
                fake['payload']['prepared_ref']=producer.reference(p);resign(fake)
                self.rejected(audit_inline_application(p,fake,d['package_path'],d['original'])['payload'],'INLINE_APPLICATION_REQUIRES_READY')

    def test_missing_variant_or_raw_candidate_ast_rewrite_is_rejected_with_updated_stage_hash(self):
        for fault in ('candidate','raw','variant'):
            p=copy.deepcopy(self.p)
            if fault=='candidate':p['payload']['candidates']['payload']['candidates'][0]['parse_result']['normalized_ast']={'type':'symbol','value':'corrected'}
            elif fault=='raw':p['payload']['formula_observations_archive']['payload']['calls'][0]['observation']['payload']['raw_latex']='wrong'
            else:p['payload']['ocr_observations_archive']['payload']['rows'][0]['variants'].pop()
            resign(p)
            with self.subTest(fault=fault):self.rejected(self.prepare_check(p))

    def test_continuity_fake_approval_or_dropped_rejected_pair_cannot_self_sign(self):
        for field,value in (('transcription_verified',True),('diagnostics',[{'raw_latex':'fabricated'}]),('rejected_adjacent_pairs',[{'reason':'forged'}])):
            p=copy.deepcopy(self.p);p['payload']['continuity']['payload'][field]=value;resign(p['payload']['continuity']);resign(p)
            with self.subTest(field=field):self.rejected(self.prepare_check(p),'INLINE_PREPARATION_PROJECTION_MISMATCH')

    def test_claimed_binding_and_duplicate_owner_cannot_be_substituted(self):
        p=copy.deepcopy(self.p);p['payload']['bindings'][0]['unassigned']=not p['payload']['bindings'][0]['unassigned'];resign(p)
        self.rejected(self.prepare_check(p),'INLINE_PREPARATION_PROJECTION_MISMATCH')

    def test_core_answer_text_edit_is_rejected_after_inner_and_outer_rehash(self):
        a=copy.deepcopy(self.a);a['payload']['graph']['payload']['answers'][0]['text']='model correction';resign(a['payload']['graph']);resign(a)
        self.rejected(self.apply_check(a),'INLINE_GRAPH_CORE_CHANGED')

    def test_all_units_calls_and_not_inference_scope_must_be_preserved(self):
        for key in ('units','calls','not_inference_units'):
            a=copy.deepcopy(self.a);values=a['payload']['graph']['payload']['inline_content'][key]
            if values:values.pop()
            else:values.append({'invented':True})
            resign(a['payload']['graph']);resign(a)
            with self.subTest(field=key):self.rejected(self.apply_check(a),'INLINE_ATTACHMENT_SCOPE_OR_BINDING_MISMATCH')

    def test_false_selection_and_boolean_numeric_flags_cannot_self_sign(self):
        for key,value in (('selected_unit_ids',['chosen']),('complete',0),('business_acceptance',True),('new_model_calls',False)):
            a=copy.deepcopy(self.a);a['payload']['graph']['payload']['inline_content'][key]=value;resign(a['payload']['graph']);resign(a)
            with self.subTest(field=key):self.rejected(self.apply_check(a),'INLINE_ATTACHMENT_SCOPE_OR_BINDING_MISMATCH')

    def test_strict_new_header_keys_and_cpu_or_human_receipt_forgery(self):
        for artifact,check in ((self.p,self.prepare_check),(self.a,self.apply_check),(self.c,self.quality_check)):
            for fault in ('human','precision','producer'):
                value=copy.deepcopy(artifact)
                if fault=='human':value['human_verified']=True
                elif fault=='precision':value['precise_glyph_localization']=True
                else:value['producer']['new_model_calls']=False
                resign(value)
                with self.subTest(kind=value['kind'],fault=fault):self.rejected(check(value),'INLINE_STAGE_HEADER_OR_IDENTITY_MISMATCH')

    def test_quality_cannot_drop_base_findings_change_metrics_or_clear_risks(self):
        for fault in ('drop','metrics','false_verified','risk'):
            c=copy.deepcopy(self.c)
            if fault=='drop':c['payload']['issues'].pop(0)
            elif fault=='metrics':c['payload']['summary']['answers']+=1
            elif fault=='false_verified':c['payload']['transcription_verified']=True
            else:c['payload']['inline_risks'].append({'invented_risk':True})
            resign(c)
            with self.subTest(fault=fault):self.rejected(self.quality_check(c),'INLINE_CHECK_PRESERVATION_OR_RISK_MISMATCH')

    def test_quality_rejects_old03_refs_permuted_even_if_present(self):
        base=copy.deepcopy(self.d['base_check']);base['input_refs'][0],base['input_refs'][1]=base['input_refs'][1],base['input_refs'][0]
        self.rejected(self.quality_check(base=base),'INLINE_BASE_CHECK_SOURCE_MISMATCH')

    def test_unknown_syntax_group_preserves_every_call_and_cannot_silently_shrink(self):
        # Deliberately unsupported model strings are observations, not bad pixels.
        worker=FormulaWorker(outputs=(r'\unknowncommand{x}',))
        observations,report=collect_inline_formula(self.d['evidence'],self.d['layout'],self.d['original'],self.d['journal_dir'],line_ids=self.d['line_ids'],recognizer=worker)
        self.d['documents'].update(formula_observations=observations,formula_report=report);refresh_inline_package(self.d)
        self.p=producer.prepare_inline_stage(self.d['evidence'],self.d['graph'],self.d['package_path'],self.d['original'])
        self.a=producer.apply_inline_stage(self.p);self.c=producer.build_inline_quality(self.p,self.a,self.d['base_check'])
        checked=self.quality_check();self.assertTrue(checked['accepted'],checked)
        groups=[i for i in self.c['payload']['issues']if i['code']=='INLINE_FORMULA_SYNTAX_UNSUPPORTED']
        self.assertEqual(len(groups),1)
        self.assertEqual(groups[0]['detail']['call_ids'],[c['plan']['call_id']for c in observations['payload']['calls']])
        self.assertFalse(self.c['payload']['transcription_verified'])
        groups[0]['detail']['call_ids'].pop();resign(self.c)
        self.rejected(self.quality_check(),'INLINE_CHECK_PRESERVATION_OR_RISK_MISMATCH')

    def test_package_actual_journal_bytes_and_source_pixels_are_not_replaceable(self):
        journal=self.d['journal_dir']/'inline-formula.sqlite3';journal.write_bytes(journal.read_bytes()+b'foreign')
        with self.assertRaises(ValueError):inspect_inline_package(self.d['package_path'],self.d['original'])
        self.rejected(self.prepare_check(),'INLINE_STAGE_DATA_INVALID')

    def test_relative_package_paths_cannot_escape_or_share_documents(self):
        m=copy.deepcopy(self.d['manifest']);m['documents']['rows']['path']='../rows.json'
        self.d['package_path'].write_text(json.dumps(m),encoding='utf8')
        self.rejected(self.prepare_check(),'INLINE_STAGE_DATA_INVALID')


class ContinuityIndependentReconstructionTests(unittest.TestCase):
    def fixture(self):
        # Independently specified synthetic raw spans/ledger, not producer gold.
        d=continuity_cases.InlineContinuityTests();d.setUp();return d

    def test_open_equation_retains_literal_right_operand_and_wrong_model_closures(self):
        d=self.fixture();v=_continuity(d.e,d.g,d.l,d.c,'p',d.ids)['payload']
        self.assertEqual(v['proposals'][0]['joined_raw_text'],'a=7')
        self.assertEqual(v['proposals'][0]['source_spans'][0]['text_span'],[2,4])
        self.assertEqual([x['raw_latex']for x in v['diagnostics']],['a=1','a=1'])
        self.assertEqual(v['selected_proposal_ids'],[])

    def test_intervening_raw_row_boolean_location_and_missing_allocation_reject_relation(self):
        for fault,expected in (('intervening','INTERVENING_RAW_SOURCE_ROW'),('boolean','SOURCE_LOCATION_UNKNOWN'),('ledger','FRAGMENT_ALLOCATION_MISMATCH')):
            d=self.fixture()
            if fault=='intervening':d.rows.append(dict(d.rows[0],line_id='intermediate',bbox=[0,11,100,12]))
            elif fault=='boolean':d.rows[1]['location']['column']=False
            else:d.g['payload']['answer_coverage'][0]['allocations']=[]
            v=_continuity(d.e,d.g,d.l,d.c,'p',d.ids)['payload']
            with self.subTest(fault=fault):self.assertEqual(v['proposals'],[]);self.assertEqual(v['rejected_adjacent_pairs'][0]['reason'],expected)


if __name__=='__main__':unittest.main()
