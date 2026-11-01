"""Independent current-content checks and coordinated revision fault cases."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from annotation.recognition import content_revision as producer
from annotation.recognition.content_revision_quality import audit_content_application,audit_content_quality
from annotation.recognition.baseline import digest
from content_revision_fixture import make_content_fixture,edit_target


def ref(v):return {k:v[k]for k in ('artifact_id','revision','content_hash')}


def resign(v):
    body={k:x for k,x in v.items()if k not in {'artifact_id','content_hash'}}
    prefix={'ContentRevisionPlanTrial':'content-revision-plan','ContentRevisionApplicationTrial':'content-revision-application',
        'QuestionGraphTrial':'content-graph','CheckReportTrial':'content-check'}[v['kind']]
    v.update(artifact_id=prefix+'-'+digest(body)[:24],content_hash=digest(v['payload']));return v


class ContentRevisionQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.d=make_content_fixture(self.temp.name)
        self.e,self.g,self.c,self.review=[self.d[k]for k in ('evidence','graph','check','review')]

    def answer(self,number):return next(a for a in self.g['payload']['answers']if a['printed_number']==number)

    def edit(self,number,text,*,role='answer',span=None,operation_id='edit'):
        return dict(operation_id=operation_id,kind='EDIT_TEXT',target=edit_target(self.g,answer_id=self.answer(number)['answer_id'],role=role,span=span),replacement=text,format='plain',reason='Explicit synthetic draft, no verification claim')

    def run_case(self,ops,previous=None):
        p=producer.make_revision_plan(self.e,self.g,self.c,ops,dict(kind='SYNTHETIC_TEST',id='test-author',note='Generated source and injected observations only'),previous_plan=previous)
        a=producer.apply_content_revision(self.e,self.g,self.c,p)
        c=producer.build_content_quality(self.e,self.g,self.c,p,a,self.review)
        return p,a,c

    def app_check(self,p,a):return audit_content_application(self.e,self.g,self.c,p,a)['payload']
    def check(self,p,a,c):return audit_content_quality(self.e,self.g,self.c,p,a,self.review,c)['payload']
    def rejected(self,result,code=None):
        self.assertFalse(result['accepted'],result)
        if code:self.assertIn(code,{i['code']for i in result['issues']},result)
        self.assertEqual(result['decision'],'HOLD');self.assertFalse(result['transcription_verified'])

    def mutate_graph(self,a,mutate):
        value=copy.deepcopy(a);mutate(value['payload']['graph']['payload']);resign(value['payload']['graph']);resign(value);return value

    def select(self):
        answer=self.answer('9');f=next(f for f in answer['fragments']if f['text'].endswith('AB='));candidate=next(c for c in self.g['payload']['inline_content']['candidates']if c['raw_latex']=='AB=1')
        unit=next(u for u in self.g['payload']['inline_content']['units']if u['unit_id']==candidate['unit_bindings'][0]['unit_id'])
        target=edit_target(self.g,answer_id=answer['answer_id'],fragment_id=f['fragment_id'],span=[len(f['text'])-3,len(f['text'])])
        return dict(operation_id='select-known-wrong-closure',kind='SELECT_INLINE',target=target,candidate_id=candidate['candidate_id'],call_id=candidate['call_id'],unit_id=unit['unit_id'],reason='Preserve complete known-wrong raw candidate as unverified regression')

    def join(self):
        proposal=self.g['payload']['inline_content']['continuity']['payload']['proposals'][0]
        return dict(operation_id='join-visible-wrap',kind='JOIN_RAW_WRAP',proposal_id=proposal['proposal_id'],reason='Join literal source separator without changing symbols')

    def test_scalar_and_choice_change_are_currently_rechecked_not_oldcheck_passed(self):
        p,a,c=self.run_case([self.edit('1','AB',operation_id='choice'),self.edit('4','13',operation_id='scalar')])
        checked=self.check(p,a,c);self.assertTrue(checked['accepted'],checked)
        q=next(q for q in a['payload']['graph']['payload']['questions']if q['printed_number']=='1')
        self.assertEqual(q['type_candidate']['selection_mode'],'multiple')
        self.assertEqual(c['payload']['fresh_question_findings'],[])
        disposition=next(d for d in c['payload']['rule_dispositions']if d['prior_issue']['code']=='ANSWER_VALUE_MISMATCH')
        self.assertEqual(disposition['current_finding_issue_ids'],[])
        self.assertIn(q['question_id'],a['payload']['graph']['payload']['content_revision']['affected_question_ids'])
        self.assertEqual(c['payload']['base_check_archive'],self.c)
        self.assertTrue(any(i['code']=='BUSINESS_REVIEW_REQUIRED'for i in c['payload']['issues']))

    def test_disjoint_variable_length_edits_preserve_all_untouched_source_and_offsets(self):
        first=self.edit('9','long',span=[0,1],operation_id='first');last=self.edit('9','短\n行',span=[3,4],operation_id='last')
        original=first['target']['expected_text']
        p,a,c=self.run_case([last,first]);f=next(f for f in self.answer('9')['fragments']if f['fragment_id']==first['target']['fragment_id'])
        expected='long'+f['text'][1:3]+'短\n行'+f['text'][4:]
        cf=a['payload']['graph']['payload']['answers'][2]['content_fragments'][0]
        self.assertEqual(cf['text'],expected);self.assertEqual(cf['pieces'][0]['output_span'],[0,4]);self.assertTrue(self.app_check(p,a)['accepted'])
        self.assertEqual(self.g['payload']['answers'][2]['fragments'][0]['text'][:1],original)

    def test_explanation_changes_are_separate_from_answer_and_cannot_invent_roles(self):
        p,a,c=self.run_case([self.edit('9','明确的解析草稿',role='explanation')]);answer=a['payload']['graph']['payload']['answers'][2]
        self.assertEqual(answer['text'],self.answer('9')['text']);self.assertIn('明确的解析草稿',answer['explanation_text'])
        self.assertTrue(answer['explanation_present']);self.assertTrue(self.check(p,a,c)['accepted'])
        bad=copy.deepcopy(p);bad['payload']['operations'][0]['target']['role']='answer';resign(bad)
        self.rejected(self.app_check(bad,a),'CONTENT_REVISION_DATA_INVALID')

    def test_selected_wrong_model_last_one_remains_and_closure_risk_is_current(self):
        p,a,c=self.run_case([self.select(),self.join()]);answer=a['payload']['graph']['payload']['answers'][2]
        self.assertEqual(answer['text'],'解：AB=125')
        self.assertTrue(any(i['code']=='CONTENT_SELECTED_FORMULA_CLOSURE_CONFLICT'for i in c['payload']['issues']))
        self.assertTrue(self.check(p,a,c)['accepted'])
        changed=self.mutate_graph(a,lambda payload:payload['answers'][2].update(text='解：AB=25'))
        self.rejected(self.app_check(p,changed),'CONTENT_REVISION_GRAPH_PROJECTION_MISMATCH')

    def test_unknown_selected_syntax_remains_an_explicit_draft_risk(self):
        # Change only a coherent synthetic backend fixture, never real model data.
        from annotation.recognition.inline_formula import collect_inline_formula
        from test_b_inline_formula import FormulaWorker
        from test_b_inline_stage import refresh_inline_package
        from annotation.recognition import inline_stage
        fo,fr=collect_inline_formula(self.e,self.d['inline_prepared']['payload']['layout_archive'],self.d['original'],self.d['journal_dir'],
            line_ids=self.d['line_ids'],recognizer=FormulaWorker(outputs=(r'\unknown{x}',)))
        self.d['documents'].update(formula_observations=fo,formula_report=fr);refresh_inline_package(self.d)
        prep=inline_stage.prepare_inline_stage(self.e,self.d['base_graph'],self.d['package_path'],self.d['original']);app=inline_stage.apply_inline_stage(prep)
        self.g=app['payload']['graph'];self.c=inline_stage.build_inline_quality(prep,app,self.d['check']['payload']['base_check_archive'])
        candidate=self.g['payload']['inline_content']['candidates'][0];f=next(f for f in self.answer('9')['fragments']if f['text'].endswith('AB='))
        op=dict(operation_id='unknown-selection',kind='SELECT_INLINE',target=edit_target(self.g,answer_id=self.answer('9')['answer_id'],fragment_id=f['fragment_id']),candidate_id=candidate['candidate_id'],call_id=candidate['call_id'],unit_id=candidate['unit_bindings'][0]['unit_id'],reason='Unknown syntax is retained, not approved')
        p,a,c=self.run_case([op]);self.assertTrue(self.check(p,a,c)['accepted'])
        risk=next(i for i in c['payload']['issues']if i['code']=='CONTENT_SELECTED_FORMULA_SYNTAX_UNSUPPORTED');self.assertEqual(risk['detail']['parse_result']['raw_latex'],r'\unknown{x}')
        c['payload']['issues'].remove(risk);resign(c);self.rejected(self.check(p,a,c),'CONTENT_REVISION_CURRENT_CHECK_MISMATCH')

    def test_consumer_does_not_execute_new_producer_plan_builder_parser_or_model(self):
        p,a,c=self.run_case([self.edit('4','13')])
        with patch.object(producer,'apply_content_revision',side_effect=AssertionError('producer')),patch.object(producer,'make_revision_plan',side_effect=AssertionError('plan builder')), \
             patch.object(producer,'build_content_quality',side_effect=AssertionError('quality producer')),patch('annotation.recognition.formula_syntax.parse_inline_formula_latex',side_effect=AssertionError('parser')), \
             patch.dict(sys.modules,{'rapidocr_onnxruntime':None,'onnxruntime':None,'rapid_latex_ocr':None}),patch('socket.socket',side_effect=AssertionError('network')):
            self.assertTrue(self.app_check(p,a)['accepted']);self.assertTrue(self.check(p,a,c)['accepted'])

    def test_source_fragments_ledger_and_archives_cannot_be_coordinately_changed(self):
        p,a,c=self.run_case([self.edit('4','13')])
        for fault in ('raw','ledger','archive'):
            def mutate(payload):
                if fault=='raw':payload['answers'][1]['fragments'][0]['text']='13'
                elif fault=='ledger':payload['answer_coverage'][0]['status']='UNASSIGNED'
                else:payload['content_revision']['base_graph_archive']['payload']['answers'][1]['text']='13'
            bad=self.mutate_graph(a,mutate)
            with self.subTest(fault=fault):self.rejected(self.app_check(p,bad),'CONTENT_REVISION_GRAPH_PROJECTION_MISMATCH')

    def test_current_text_pieces_regions_and_matching_cannot_disagree(self):
        p,a,c=self.run_case([self.edit('4','13')])
        for fault in ('text','piece','span','matching','type','explanation'):
            def mutate(payload):
                answer=payload['answers'][1]
                if fault=='text':answer['text']='12'
                elif fault=='piece':answer['content_fragments'][0]['pieces'][0]['text']='12'
                elif fault=='span':answer['content_fragments'][0]['pieces'][0]['output_span']=[0,1]
                elif fault=='matching':payload['questions'][0]['selected_answer_id']=answer['answer_id']
                elif fault=='type':payload['questions'][0]['type_candidate']['selection_mode']='multiple'
                else:answer['explanation_text']='invented explanation'
            with self.subTest(fault=fault):self.rejected(self.app_check(p,self.mutate_graph(a,mutate)),'CONTENT_REVISION_GRAPH_PROJECTION_MISMATCH')

    def test_external_plan_version_is_not_replaceable_by_internal_archive_or_ref(self):
        p,a,c=self.run_case([self.edit('4','13')]);new=copy.deepcopy(p);new['payload']['operations'][0]['replacement']='99';resign(new)
        bad=copy.deepcopy(a);bad['input_refs'][3]=ref(new);bad['payload']['plan_ref']=ref(new)
        graph=bad['payload']['graph'];graph['input_refs'][3]=ref(new)
        graph['payload']['content_revision'].update(plan_ref=ref(new),plan_archive=new)
        graph['payload']['content_revision']['operation_bindings'][0]['replacement']='99'
        resign(graph);resign(bad)
        self.rejected(self.app_check(new,bad),'CONTENT_REVISION_GRAPH_PROJECTION_MISMATCH')
        stale=copy.deepcopy(p);stale['payload']['graph_ref']['content_hash']='0'*64;resign(stale)
        self.rejected(self.app_check(stale,a),'CONTENT_REVISION_DATA_INVALID')

    def test_fragment_relative_interval_is_not_raw_element_or_CTC_coordinate(self):
        op=self.edit('4','13');p,a,c=self.run_case([op]);bad=copy.deepcopy(p)
        target=bad['payload']['operations'][0]['target'];f=self.answer('4')['fragments'][0]
        target['fragment_span']=f['text_span'];target['expected_text']=f['raw_text'][f['text_span'][0]:f['text_span'][1]];resign(bad)
        self.rejected(self.app_check(bad,a),'CONTENT_REVISION_DATA_INVALID')
        bad=copy.deepcopy(p);bad['payload']['operations'][0]['target']['char_span']=[0,1];resign(bad)
        self.rejected(self.app_check(bad,a),'CONTENT_REVISION_DATA_INVALID')
        bad=copy.deepcopy(p);bad['payload']['operations'][0]['target']['fragment_span']=[False,True];resign(bad)
        self.rejected(self.app_check(bad,a),'CONTENT_REVISION_DATA_INVALID')

    def test_overlap_and_duplicate_operations_are_rejected_after_resigning_plan(self):
        p,a,c=self.run_case([self.edit('9','longer',span=[0,2])])
        for fault in ('overlap','duplicate'):
            bad=copy.deepcopy(p);op=copy.deepcopy(bad['payload']['operations'][0])
            if fault=='overlap':op['operation_id']='overlap';op['target']['fragment_span']=[1,3];f=self.answer('9')['fragments'][0];op['target']['expected_text']=f['text'][1:3]
            bad['payload']['operations'].append(op);resign(bad)
            with self.subTest(fault=fault):self.rejected(self.app_check(bad,a),'CONTENT_REVISION_DATA_INVALID')

    def test_false_human_verification_unknown_header_and_boolean_number_cannot_self_sign(self):
        p,a,c=self.run_case([self.edit('4','13')])
        for level in ('plan','application','graph','check'):
            for fault in ('human','number'):
                pp,aa,cc=copy.deepcopy((p,a,c));value={'plan':pp,'application':aa,'graph':aa['payload']['graph'],'check':cc}[level]
                if fault=='human':value['human_verified']=True
                else:value['payload']['complete']=0
                resign(value)
                if level=='graph':resign(aa)
                with self.subTest(level=level,fault=fault):self.rejected(self.check(pp,aa,cc)if level=='check'else self.app_check(pp,aa))

    def test_fresh_check_cannot_reuse_old_graph_or_old_scalar_findings(self):
        p,a,c=self.run_case([self.edit('4','13')])
        for fault in ('graph','fresh','disposition','old_issue'):
            bad=copy.deepcopy(c)
            if fault=='graph':bad['payload']['graph_ref']=ref(self.g)
            elif fault=='fresh':bad['payload']['fresh_question_findings']=copy.deepcopy(bad['payload']['prior_question_findings'])
            elif fault=='disposition':bad['payload']['rule_dispositions'][0]['status']='ALL_ERRORS_RESOLVED'
            else:bad['payload']['issues'].pop(0)
            resign(bad)
            with self.subTest(fault=fault):self.rejected(self.check(p,a,bad),'CONTENT_REVISION_CURRENT_CHECK_MISMATCH')

    def test_q4_ratio_regression_stays_blocked_under_current_content_rules(self):
        p,a,c=self.run_case([self.edit('4','1:3')]);self.assertTrue(self.check(p,a,c)['accepted'])
        scalar=[f for f in c['payload']['fresh_question_findings']if f['code']=='ANSWER_SCALAR_FORMAT'];self.assertEqual(len(scalar),1)
        self.assertEqual(scalar[0]['detail']['actual'],'1:3');self.assertEqual(c['payload']['decision'],'HOLD')

    def test_only_exact_prior_question_finding_can_be_superseded(self):
        old=next(i for i in self.c['payload']['issues']if i['code']=='ANSWER_VALUE_MISMATCH')
        different=copy.deepcopy(old);different['detail']={**different['detail'],'extra_independent_review':'must remain pending'};different['issue_id']='independent-same-code-different-basis'
        self.c['payload']['issues'].append(different);self.c['payload']['summary']['issues']+=1;self.c['content_hash']=digest(self.c['payload'])
        self.c['artifact_id']='synthetic-check05-additional-independent-finding'
        p,a,c=self.run_case([self.edit('4','13')]);self.assertTrue(self.check(p,a,c)['accepted'])
        dispositions=c['payload']['rule_dispositions'];self.assertEqual([x['prior_issue']['issue_id']for x in dispositions],[old['issue_id']])
        carried=next(i for i in c['payload']['issues']if i['issue_id']==different['issue_id'])
        self.assertEqual(carried['detail'],different['detail']);self.assertEqual(carried['origin_check_ref'],ref(self.c))
        c['payload']['issues'].remove(carried);resign(c)
        self.rejected(self.check(p,a,c),'CONTENT_REVISION_CURRENT_CHECK_MISMATCH')

    def test_plan_lineage_and_explicit_empty_revision_remove_prior_edits_without_changing_source(self):
        p,a,c=self.run_case([self.edit('4','13')]);p2,a2,c2=self.run_case([],p)
        self.assertTrue(self.check(p2,a2,c2)['accepted']);self.assertEqual(p2['revision'],2)
        self.assertEqual(a2['payload']['graph']['payload']['answers'],self.g['payload']['answers'])
        bad=copy.deepcopy(p2);bad['payload']['previous_plan_archive']['payload']['author']['human_verified']=True;resign(bad['payload']['previous_plan_archive']);resign(bad)
        self.rejected(self.app_check(bad,a2),'CONTENT_REVISION_DATA_INVALID')

    def test_unmatched_answer_cannot_invent_a_question_pairing(self):
        p,a,c=self.run_case([self.edit('9','another scope')]);payload=a['payload']['graph']['payload']
        self.assertEqual(payload['questions'],self.g['payload']['questions'])
        self.assertEqual(payload['unmatched_answer_ids'],self.g['payload']['unmatched_answer_ids'])
        self.assertEqual(payload['content_revision']['affected_question_ids'],[]);self.assertTrue(self.check(p,a,c)['accepted'])

    def test_images_geometry_typed_text_and_diagnostics_are_independently_preserved(self):
        with tempfile.TemporaryDirectory()as root:
            d=make_content_fixture(root,with_images=True);e,g,c,r=[d[k]for k in ('evidence','graph','check','review')]
            target=edit_target(g);op=dict(operation_id='visible',kind='EDIT_TEXT',target=target,replacement='synthetic materialized body',format='plain',reason='Source image preservation test')
            p=producer.make_revision_plan(e,g,c,[op],dict(kind='SYNTHETIC_TEST',id='test',note='generated images'))
            a=producer.apply_content_revision(e,g,c,p);q=producer.build_content_quality(e,g,c,p,a,r)
            self.assertTrue(audit_content_quality(e,g,c,p,a,r,q)['payload']['accepted'])
            answer=next(v for v in a['payload']['graph']['payload']['answers']if v['answer_id']==target['answer_id'])
            text=next(v for v in answer['render_regions']if target['fragment_id']in v.get('source_fragment_ids',[]));self.assertEqual(text['text'],'synthetic materialized body')
            for fault in ('image','region_text','diagnostic'):
                bad=copy.deepcopy(a);aa=next(v for v in bad['payload']['graph']['payload']['answers']if v['answer_id']==target['answer_id'])
                if fault=='image':next(v for v in aa['render_regions']if v['content_type']=='image')['bbox'][0]+=1
                elif fault=='region_text':next(v for v in aa['render_regions']if target['fragment_id']in v.get('source_fragment_ids',[]))['text']='old OCR'
                else:next(f for f in aa['fragments']if f.get('represented_by_image_region'))['render_as_separate_region']=True
                resign(bad['payload']['graph']);resign(bad)
                with self.subTest(fault=fault):self.rejected(audit_content_application(e,g,c,p,bad)['payload'],'CONTENT_REVISION_GRAPH_PROJECTION_MISMATCH')


if __name__=='__main__':unittest.main()
