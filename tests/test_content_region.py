"""Region draft materialization; source coverage is not content approval.

Generated fixtures use injected observations. Frozen book fixtures contain old
real observations, never new inference or human transcription gold.
"""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from annotation.recognition import content_revision as producer
from annotation.recognition import content_revision_quality as consumer
from annotation.recognition.baseline import digest
from content_revision_fixture import make_content_fixture,edit_target
from content_revision_observed import observed_inputs,observed_plan


def ref(value):return {k:value[k]for k in ('artifact_id','revision','content_hash')}


def resign(value):
    prefixes={'ContentRevisionPlanTrial':'content-revision-plan','ContentRevisionApplicationTrial':'content-revision-application',
        'QuestionGraphTrial':'content-graph','CheckReportTrial':'content-check'}
    body={k:v for k,v in value.items()if k not in {'artifact_id','content_hash'}}
    value.update(artifact_id=prefixes[value['kind']]+'-'+digest(body)[:24],content_hash=digest(value['payload']))
    return value


def box_union(boxes):return [math.floor(min(b[0]for b in boxes)),math.floor(min(b[1]for b in boxes)),math.ceil(max(b[2]for b in boxes)),math.ceil(max(b[3]for b in boxes))]


def region_operation(evidence,graph,*,number='9',role='answer',include_unread=True):
    answer=next(a for a in graph['payload']['answers']if a['printed_number']==number)
    fragments=[f for f in answer['fragments']if f['role']==role and not f.get('structural_marker')and f.get('represented_by_image_region')is None and f.get('render_as_separate_region')is not False]
    source=next(p['source']for p in evidence['payload']['pages']if p['asset_id']==fragments[0]['asset_id'])
    blocks=[]
    for i,f in enumerate(fragments):
        bbox=box_union([f['bbox']])
        blocks.append(dict(block_id='source-block-'+str(i),bbox=bbox,source_fragment_ids=[f['fragment_id']],
            runs=[dict(format='plain',text='解：'if i==0 else f['text']),dict(format='latex',text=r'\frac{a^{2}+1}{2}') ]if i==0 else[dict(format='plain',text=f['text'])],
            note='Explicit synthetic model draft, not verified OCR'))
        if i==0 and include_unread and len(fragments)>1:
            y0,y1=math.ceil(f['bbox'][3])+1,math.floor(fragments[1]['bbox'][1])-1
            if y0<y1:blocks.append(dict(block_id='unread-formula',bbox=[bbox[0],y0,bbox[2],y1],source_fragment_ids=[],
                runs=[dict(format='latex',text=r'\frac{a^{4}+2a^{2}+1}{4}')],note='Source-bounded draft block without an OCR fragment; no glyph proof claimed'))
    return dict(operation_id='region-'+number+'-'+role,kind='REBUILD_TEXT_REGION',reason='Rebuild explicit source-bounded content without modifying raw observations',
        target=dict(answer_id=answer['answer_id'],role=role,source_fragment_ids=[f['fragment_id']for f in fragments]),
        source_region=dict(asset_id=source['asset_id'],source_sha256=source['sha256'],source_size=[source['width'],source['height']],bbox=box_union([f['bbox']for f in fragments])),blocks=blocks)


def add_synthetic_raw_barrier(e,g,c,status):
    """New adversarial source versions, not mutations of any saved observation."""
    e,g,c=copy.deepcopy((e,g,c));page=next(p for p in e['payload']['pages']if p['asset_id']=='answer')
    lid='answer/synthetic-'+status.lower();line=copy.deepcopy(page['ocr_lines'][2])
    line.update(line_id=lid,text='Unowned synthetic material'if status=='UNASSIGNED'else'Synthetic excluded header',bbox=[10,92,220,96])
    page['ocr_lines'].append(line);e['content_hash']=digest(e['payload']);e['artifact_id']='synthetic-region-barrier-E-'+digest(e['payload'])[:16]
    row=dict(asset_id='answer',line_id=lid,status=status,answer_ids=[],fragment_ids=[],reason='Explicit synthetic unresolved/excluded source',allocations=[])
    g['payload']['answer_coverage'].append(row)
    base=g['payload']['inline_content']['base_graph_archive'];base['payload']['answer_coverage'].append(copy.deepcopy(row));base['input_refs']=[ref(e)]
    base['content_hash']=digest(base['payload']);base['artifact_id']='synthetic-region-barrier-base-'+digest(base['payload'])[:16]
    g['payload']['inline_content'].update(base_graph_ref=ref(base),base_evidence_ref=ref(e))
    g['input_refs'][:2]=[ref(e),ref(base)];g['content_hash']=digest(g['payload']);g['artifact_id']='synthetic-region-barrier-G05-'+digest(g['payload'])[:16]
    core=c['payload']['base_check_archive'];core['input_refs'][:2]=[ref(e),ref(base)]
    c['payload'].update(evidence_ref=ref(e),graph_ref=ref(g));c['input_refs'][:2]=[ref(e),ref(g)]
    c['content_hash']=digest(c['payload']);c['artifact_id']='synthetic-region-barrier-Check05-'+digest(c['payload'])[:16]
    return e,g,c


def synthetic_presentation_version(e,g,c,mutate):
    """Explicit generated presentation versions; saved observations stay intact."""
    e,g,c=copy.deepcopy((e,g,c));mutate(g['payload'])
    inline=g['payload']['inline_content'];base=inline['base_graph_archive'];old_base=ref(base)
    base['payload']=copy.deepcopy({k:v for k,v in g['payload'].items()if k!='inline_content'})
    base['content_hash']=digest(base['payload']);base['artifact_id']='synthetic-presentation-base-'+digest(base['payload'])[:16]
    inline['base_graph_ref']=ref(base)
    g['input_refs']=[ref(base)if r==old_base else r for r in g['input_refs']]
    g['content_hash']=digest(g['payload']);g['artifact_id']='synthetic-presentation-G05-'+digest(g['payload'])[:16]
    c['payload']['graph_ref']=ref(g);c['input_refs'][:2]=[ref(e),ref(g)]
    c['content_hash']=digest(c['payload']);c['artifact_id']='synthetic-presentation-Check05-'+digest(c['payload'])[:16]
    return e,g,c


class ContentRegionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.d=make_content_fixture(self.temp.name)
        self.e,self.g,self.c,self.review=[self.d[k]for k in ('evidence','graph','check','review')]
        self.operation=region_operation(self.e,self.g)
        self.author=dict(kind='MODEL_DRAFT',id='generated-fixture-development-author',note='Generated source and SYNTHETIC_TEST observations; no human gold')

    def build(self,operations=None,previous=None):
        p=producer.make_revision_plan(self.e,self.g,self.c,operations if operations is not None else[self.operation],self.author,previous_plan=previous)
        a=producer.apply_content_revision(self.e,self.g,self.c,p)
        q=producer.build_content_quality(self.e,self.g,self.c,p,a,self.review)
        return p,a,q

    def answer(self,graph):return next(a for a in graph['payload']['answers']if a['answer_id']==self.operation['target']['answer_id'])
    def audit_app(self,p,a):return consumer.audit_content_application(self.e,self.g,self.c,p,a)['payload']
    def audit_check(self,p,a,c):return consumer.audit_content_quality(self.e,self.g,self.c,p,a,self.review,c)['payload']
    def assert_reject(self,value):self.assertFalse(value['accepted'],value);self.assertEqual(value['decision'],'HOLD')

    def reject_plan(self,mutator):
        p,a,_=self.build();mutator(p);resign(p)
        with self.assertRaises((ValueError,KeyError,TypeError)):producer.validate_revision_plan(p,self.e,self.g,self.c)
        self.assert_reject(self.audit_app(p,a))

    def test_region_materializes_typed_runs_and_preserves_original_sources(self):
        original=copy.deepcopy((self.e,self.g,self.c));p,a,q=self.build();g=a['payload']['graph'];answer=self.answer(g)
        self.assertEqual(p['schema_version'],'b-content-revision-plan-trial/0.2');self.assertEqual(a['schema_version'],'b-content-revision-application-trial/0.2')
        self.assertEqual(g['schema_version'],'b-graph-trial/0.7');self.assertEqual(q['schema_version'],'b-check-trial/0.7')
        expected=[''.join(r['text']for r in b['runs'])for b in self.operation['blocks']]
        self.assertEqual(answer['text'],'\n'.join(expected));self.assertEqual(answer['explanation_text'],self.answer(self.g)['explanation_text'])
        region=[f for f in answer['content_fragments']if f.get('kind')=='REGION_DRAFT']
        self.assertEqual([f['text']for f in region],expected);self.assertEqual([f['runs']for f in region],[b['runs']for b in self.operation['blocks']])
        self.assertEqual([r['text']for r in answer['render_regions']if r.get('role')=='answer'],expected)
        self.assertEqual(answer['regions'],answer['render_regions'])
        self.assertEqual(answer['fragments'],self.answer(self.g)['fragments']);self.assertEqual(g['payload']['answer_coverage'],self.g['payload']['answer_coverage'])
        self.assertEqual(g['payload']['inline_content'],self.g['payload']['inline_content']);self.assertEqual((self.e,self.g,self.c),original)
        self.assertTrue(self.audit_app(p,a)['accepted']);self.assertTrue(self.audit_check(p,a,q)['accepted'])
        self.assertFalse(q['payload']['transcription_verified']);self.assertEqual(q['payload']['platform_actions'],[])

    def test_block_without_OCR_keeps_empty_provenance_not_invented_raw_span(self):
        p,a,q=self.build();region=next(f for f in self.answer(a['payload']['graph'])['content_fragments']if f.get('block_id')=='unread-formula')
        self.assertEqual(region['source_fragment_ids'],[]);self.assertEqual(region['source_region'],self.operation['source_region'])
        self.assertNotIn('source_text_span',region);self.assertNotIn('source_element_ref',region)
        self.assertFalse(region['transcription_verified']);self.assertTrue(self.audit_check(p,a,q)['accepted'])

    def test_existing_explanation_is_rebuilt_separately_without_inventing_E(self):
        self.operation=region_operation(self.e,self.g,role='explanation');p,a,q=self.build();answer=self.answer(a['payload']['graph'])
        self.assertEqual(answer['text'],self.answer(self.g)['text']);self.assertEqual(answer['explanation_text'],'\n'.join(''.join(r['text']for r in b['runs'])for b in self.operation['blocks']))
        self.assertTrue(answer['explanation_present']);self.assertTrue(self.audit_check(p,a,q)['accepted'])
        bad=copy.deepcopy(p);bad['payload']['operations'][0]['target']['role']='answer';resign(bad)
        self.assert_reject(self.audit_app(bad,a))

    def test_original_target_order_missing_and_duplicate_assignments_are_rejected(self):
        faults=[lambda op:op['target']['source_fragment_ids'].reverse(),
            lambda op:op['target']['source_fragment_ids'].append(op['target']['source_fragment_ids'][0]),
            lambda op:op['blocks'][-1].update(source_fragment_ids=[]),
            lambda op:op['blocks'][1].update(source_fragment_ids=op['blocks'][0]['source_fragment_ids'])]
        for mutate in faults:
            with self.subTest(fault=faults.index(mutate)):self.reject_plan(lambda p:mutate(p['payload']['operations'][0]))

    def test_wrong_asset_hash_size_answer_role_or_section_cannot_be_rebound(self):
        other=next(a for a in self.g['payload']['answers']if a['answer_id']!=self.operation['target']['answer_id'])
        faults=[lambda op:op['source_region'].update(asset_id='question'),lambda op:op['source_region'].update(source_sha256='0'*64),
            lambda op:op['source_region'].update(source_size=[241,300]),lambda op:op['target'].update(answer_id=other['answer_id']),
            lambda op:op['target'].update(role='explanation')]
        for i,mutate in enumerate(faults):
            with self.subTest(fault=i):self.reject_plan(lambda p:mutate(p['payload']['operations'][0]))

    def test_region_and_block_cropping_overlap_outside_geometry_and_bool_int_rejected(self):
        def clipped(op):op['source_region']['bbox'][0]+=1
        def block_clipped(op):op['blocks'][0]['bbox'][0]+=1
        def overlap(op):op['blocks'][1]['bbox'][1]=op['blocks'][0]['bbox'][3]-1
        def outside(op):op['blocks'][0]['bbox'][0]=op['source_region']['bbox'][0]-1
        def boolean(op):op['source_region']['source_size'][0]=True
        def floating(op):op['blocks'][0]['bbox'][0]=float(op['blocks'][0]['bbox'][0])
        for mutate in (clipped,block_clipped,overlap,outside,boolean,floating):
            with self.subTest(fault=mutate.__name__):self.reject_plan(lambda p:mutate(p['payload']['operations'][0]))

    def test_unknown_fields_empty_runs_duplicate_blocks_and_approval_claims_rejected(self):
        faults=[lambda op:op.update(human_verified=True),lambda op:op['target'].update(fragment_span=[0,1]),
            lambda op:op['blocks'][0].update(ocr_text='invented raw'),lambda op:op['blocks'][0].update(runs=[]),
            lambda op:op['blocks'][0]['runs'][0].update(text=''),lambda op:op['blocks'][0]['runs'][0].update(format='image'),
            lambda op:op['blocks'][-1].update(block_id=op['blocks'][0]['block_id'])]
        for i,mutate in enumerate(faults):
            with self.subTest(fault=i):self.reject_plan(lambda p:mutate(p['payload']['operations'][0]))
        self.reject_plan(lambda p:p['payload']['author'].update(human_verified=True))

    def test_region_cannot_swallow_another_answer_or_other_role(self):
        self.reject_plan(lambda p:p['payload']['operations'][0]['source_region'].update(bbox=[10,15,220,117]))
        self.reject_plan(lambda p:p['payload']['operations'][0]['source_region'].update(bbox=[10,71,220,173]))

    def test_disjoint_fragment_targets_cannot_claim_overlapping_source_frames(self):
        operations=[]
        for index in (0,-1):
            block=copy.deepcopy(self.operation['blocks'][index]);op=copy.deepcopy(self.operation)
            op['operation_id']='one-source-frame-'+str(index);op['blocks']=[block]
            op['target']['source_fragment_ids']=block['source_fragment_ids'][:]
            op['source_region']['bbox']=block['bbox'][:]
            operations.append(op)
        # Both frames include only their own OCR row, but share unobserved space.
        operations[0]['source_region']['bbox'][3]=98
        operations[1]['source_region']['bbox'][1]=90
        for op in operations:
            p,a,_=self.build([op]);self.assertTrue(self.audit_app(p,a)['accepted'])
        bad=copy.deepcopy(p);bad['payload']['operations']=operations;resign(bad)
        with self.assertRaisesRegex(ValueError,'source regions.*overlap'):producer.validate_revision_plan(bad,self.e,self.g,self.c)
        self.assert_reject(self.audit_app(bad,a))

    def test_partial_typed_region_cannot_consume_only_one_original_member(self):
        answer_id=self.operation['target']['answer_id']
        def combine_body(payload):
            answer=next(a for a in payload['answers']if a['answer_id']==answer_id)
            body=[f for f in answer['fragments']if f['role']=='answer'and not f.get('structural_marker')]
            other=[f for f in answer['fragments']if f['role']!='answer'and not f.get('structural_marker')]
            groups=[body]+[[f]for f in other]
            answer['render_regions']=[dict(region_id='synthetic-shared-text-'+str(i),content_type='text',role=fs[0]['role'],
                asset_id=fs[0]['asset_id'],bbox=box_union([f['bbox']for f in fs]),text='\n'.join(f['text']for f in fs),
                source_fragment_ids=[f['fragment_id']for f in fs])for i,fs in enumerate(groups)]
            answer['regions']=copy.deepcopy(answer['render_regions'])
        e,g,c=synthetic_presentation_version(self.e,self.g,self.c,combine_body)
        op=region_operation(e,g);p=producer.make_revision_plan(e,g,c,[op],self.author)
        app=producer.apply_content_revision(e,g,c,p)
        self.assertTrue(consumer.audit_content_application(e,g,c,p,app)['payload']['accepted'])
        bad=copy.deepcopy(p);target=bad['payload']['operations'][0]
        target['target']['source_fragment_ids']=target['target']['source_fragment_ids'][:1]
        target['blocks']=target['blocks'][:1];target['source_region']['bbox']=target['blocks'][0]['bbox'][:];resign(bad)
        with self.assertRaisesRegex(ValueError,'untargeted text barrier'):producer.validate_revision_plan(bad,e,g,c)
        self.assert_reject(consumer.audit_content_application(e,g,c,bad,app)['payload'])

    def test_unassigned_or_excluded_raw_row_cannot_be_swallowed_by_empty_OCR_block(self):
        p,a,_=self.build()
        for status in ('UNASSIGNED','EXCLUDED'):
            e,g,c=add_synthetic_raw_barrier(self.e,self.g,self.c,status);bad=copy.deepcopy(p)
            bad['payload'].update(evidence_ref=ref(e),graph_ref=ref(g),base_check_ref=ref(c));resign(bad)
            with self.subTest(status=status):
                with self.assertRaisesRegex(ValueError,'untargeted|unassigned|excluded|swallow'):producer.validate_revision_plan(bad,e,g,c)
                self.assert_reject(consumer.audit_content_application(e,g,c,bad,a)['payload'])

    def test_target_source_section_change_is_not_hidden_by_identical_text_and_boxes(self):
        p,a,_=self.build();e,g,c=copy.deepcopy((self.e,self.g,self.c))
        page=next(p for p in e['payload']['pages']if p['asset_id']=='answer');page['ocr_lines'][2]['location']['section_path']=['Other semantic section']
        e['content_hash']=digest(e['payload']);e['artifact_id']='synthetic-section-conflict'
        g['input_refs'][0]=ref(e);g['artifact_id']='synthetic-section-G05';c['payload'].update(evidence_ref=ref(e),graph_ref=ref(g));c['input_refs'][:2]=[ref(e),ref(g)]
        c['content_hash']=digest(c['payload']);c['artifact_id']='synthetic-section-Check05'
        bad=copy.deepcopy(p);bad['payload'].update(evidence_ref=ref(e),graph_ref=ref(g),base_check_ref=ref(c));resign(bad)
        with self.assertRaises(ValueError):producer.validate_revision_plan(bad,e,g,c)
        self.assert_reject(consumer.audit_content_application(e,g,c,bad,a)['payload'])

    def test_edit_select_or_join_cannot_overlap_region_sources(self):
        p,a,_=self.build();target=edit_target(self.g,answer_id=self.operation['target']['answer_id'])
        edit=dict(operation_id='same-source-edit',kind='EDIT_TEXT',target=target,replacement='other',format='plain',reason='Invalid overlap')
        join=dict(operation_id='same-source-join',kind='JOIN_RAW_WRAP',proposal_id=self.g['payload']['inline_content']['continuity']['payload']['proposals'][0]['proposal_id'],reason='Invalid overlap')
        candidate=self.g['payload']['inline_content']['candidates'][0]
        select=dict(operation_id='same-source-select',kind='SELECT_INLINE',target=target,candidate_id=candidate['candidate_id'],call_id=candidate['call_id'],unit_id=candidate['unit_bindings'][0]['unit_id'],reason='Invalid overlap')
        for op in (edit,join,select):
            bad=copy.deepcopy(p);bad['payload']['operations'].append(op);resign(bad)
            with self.subTest(kind=op['kind']):
                with self.assertRaises((ValueError,KeyError,TypeError)):producer.validate_revision_plan(bad,self.e,self.g,self.c)
                self.assert_reject(self.audit_app(bad,a))

    def test_disjoint_legacy_edit_still_rechecks_Q4_scalar(self):
        answer=next(a for a in self.g['payload']['answers']if a['printed_number']=='4')
        edit=dict(operation_id='q4-scalar',kind='EDIT_TEXT',target=edit_target(self.g,answer_id=answer['answer_id']),replacement='13',format='plain',reason='Independent synthetic scalar correction')
        p,a,q=self.build([self.operation,edit]);self.assertTrue(self.audit_check(p,a,q)['accepted'])
        self.assertFalse(any(f['code']=='ANSWER_VALUE_MISMATCH'for f in q['payload']['fresh_question_findings']))
        self.assertTrue(any(d['prior_issue']['code']=='ANSWER_VALUE_MISMATCH'for d in q['payload']['rule_dispositions']))

    def test_new_operation_is_not_accepted_under_old_schema_or_old_target_shape(self):
        p,a,_=self.build();bad=copy.deepcopy(p);bad['schema_version']='b-content-revision-plan-trial/0.1';resign(bad)
        with self.assertRaises(ValueError):producer.validate_revision_plan(bad,self.e,self.g,self.c)
        self.assert_reject(self.audit_app(bad,a))
        self.reject_plan(lambda p:p['payload']['operations'][0].update(kind='EDIT_TEXT'))

    def test_empty_revision_preserves_v2_history_and_reverts_materialized_body(self):
        p,a,q=self.build();p2,a2,q2=self.build([],p)
        self.assertEqual(p2['schema_version'],'b-content-revision-plan-trial/0.2');self.assertEqual(p2['revision'],2)
        self.assertEqual(p2['payload']['previous_plan_archive'],p);self.assertEqual(a2['payload']['graph']['schema_version'],'b-graph-trial/0.7')
        self.assertEqual(a2['payload']['graph']['payload']['answers'],self.g['payload']['answers']);self.assertTrue(self.audit_check(p2,a2,q2)['accepted'])
        self.assertEqual(producer.rollback_content_revision(self.e,a['payload']['graph'],expected_graph_ref=ref(a['payload']['graph'])),self.g)
        stale=copy.deepcopy(a['payload']['graph']);stale['payload']['answers'][0]['text']+='later edit';resign(stale)
        with self.assertRaises(ValueError):producer.rollback_content_revision(self.e,stale,expected_graph_ref=ref(a['payload']['graph']))

    def test_coordinated_projection_text_runs_region_or_source_tamper_is_rejected(self):
        p,a,q=self.build()
        for fault in ('text','runs','region','source','ledger','empty_source_claim'):
            bad=copy.deepcopy(a);g=bad['payload']['graph'];answer=self.answer(g);f=next(f for f in answer['content_fragments']if f.get('kind')=='REGION_DRAFT')
            if fault=='text':answer['text']='silently changed'
            elif fault=='runs':f['runs'][0]['text']='changed';f['text']=''.join(r['text']for r in f['runs'])
            elif fault=='region':answer['render_regions'][0]['bbox'][0]+=1
            elif fault=='source':answer['fragments'][0]['text']='invented OCR'
            elif fault=='ledger':g['payload']['answer_coverage'][0]['status']='EXCLUDED'
            else:next(f for f in answer['content_fragments']if f.get('block_id')=='unread-formula')['source_fragment_ids']=[self.operation['target']['source_fragment_ids'][0]]
            resign(g);resign(bad)
            with self.subTest(fault=fault):self.assert_reject(self.audit_app(p,bad))

    def test_current_check_cannot_drop_old_risks_or_use_old_graph_after_rebuild(self):
        p,a,q=self.build();self.assertEqual(q['payload']['graph_ref'],ref(a['payload']['graph']))
        prior={i['issue_id']for i in self.c['payload']['issues']};carried={i['issue_id']for i in q['payload']['issues']};rechecked={i['prior_issue']['issue_id']for i in q['payload']['rule_dispositions']}
        self.assertTrue(prior<=carried|rechecked);self.assertEqual(q['payload']['base_check_archive'],self.c)
        for fault in ('old_ref','drop','verified'):
            bad=copy.deepcopy(q)
            if fault=='old_ref':bad['payload']['graph_ref']=ref(self.g)
            elif fault=='drop':bad['payload']['issues'].pop(0)
            else:bad['payload']['transcription_verified']=True
            resign(bad)
            with self.subTest(fault=fault):self.assert_reject(self.audit_check(p,a,bad))

    def test_independent_audit_never_calls_producer_builder_parser_or_models(self):
        p,a,q=self.build()
        with patch.object(producer,'make_revision_plan',side_effect=AssertionError('plan builder')),patch.object(producer,'validate_revision_plan',side_effect=AssertionError('plan validator')), \
             patch.object(producer,'apply_content_revision',side_effect=AssertionError('producer apply')),patch.object(producer,'build_content_quality',side_effect=AssertionError('producer check')), \
             patch('annotation.recognition.formula_syntax.parse_inline_formula_latex',side_effect=AssertionError('parser')),patch.dict(sys.modules,{'onnxruntime':None,'rapidocr_onnxruntime':None,'rapid_latex_ocr':None}), \
             patch('socket.socket',side_effect=AssertionError('network')):
            self.assertTrue(self.audit_app(p,a)['accepted']);self.assertTrue(self.audit_check(p,a,q)['accepted'])

    def test_typed_picture_barrier_is_preserved_and_not_consumable_as_region_body(self):
        with tempfile.TemporaryDirectory()as root:
            d=make_content_fixture(root,with_images=True);e,g,c,r=[d[k]for k in ('evidence','graph','check','review')]
            answer=next(a for a in g['payload']['answers']if any(z.get('content_type')=='image'for z in a.get('render_regions',[])))
            text_region=next(z for z in answer['render_regions']if z['content_type']=='text')
            fid=text_region['source_fragment_ids'][0];f=next(f for f in answer['fragments']if f['fragment_id']==fid);source=next(p['source']for p in e['payload']['pages']if p['asset_id']==f['asset_id'])
            op=dict(operation_id='one-visible-text',kind='REBUILD_TEXT_REGION',reason='Generated image barrier preservation',target=dict(answer_id=answer['answer_id'],role=f['role'],source_fragment_ids=[fid]),
                source_region=dict(asset_id=f['asset_id'],source_sha256=source['sha256'],source_size=[source['width'],source['height']],bbox=box_union([f['bbox']])),
                blocks=[dict(block_id='text-only',bbox=box_union([f['bbox']]),source_fragment_ids=[fid],runs=[dict(format='plain',text='Explicit image-adjacent draft')],note='No picture content is changed')])
            p=producer.make_revision_plan(e,g,c,[op],self.author);a=producer.apply_content_revision(e,g,c,p);q=producer.build_content_quality(e,g,c,p,a,r)
            self.assertTrue(consumer.audit_content_quality(e,g,c,p,a,r,q)['payload']['accepted'])
            images=lambda graph:[z for aa in graph['payload']['answers']for z in aa.get('render_regions',[])if z['content_type']=='image']
            self.assertEqual(images(a['payload']['graph']),images(g))
            bad=copy.deepcopy(p);bad['payload']['operations'][0]['source_region']['bbox']=box_union([z['bbox']for z in answer['render_regions']if z['asset_id']==f['asset_id']]);resign(bad)
            with self.assertRaisesRegex(ValueError,'picture|diagnostic|overlap|structural'):producer.validate_revision_plan(bad,e,g,c)
            self.assert_reject(consumer.audit_content_application(e,g,c,bad,a)['payload'])

    def test_legacy_picture_answer_needs_a_proven_typed_migration(self):
        with tempfile.TemporaryDirectory()as root:
            d=make_content_fixture(root,with_images=True);e,g,c=[d[k]for k in ('evidence','graph','check')]
            answer=next(a for a in g['payload']['answers']if any(z.get('content_type')=='image'for z in a.get('render_regions',[])))
            text=next(z for z in answer['render_regions']if z['content_type']=='text')
            fid=text['source_fragment_ids'][0];f=next(f for f in answer['fragments']if f['fragment_id']==fid)
            source=next(p['source']for p in e['payload']['pages']if p['asset_id']==f['asset_id'])
            op=dict(operation_id='legacy-picture-text',kind='REBUILD_TEXT_REGION',reason='Generated legacy picture migration guard',
                target=dict(answer_id=answer['answer_id'],role=f['role'],source_fragment_ids=[fid]),
                source_region=dict(asset_id=f['asset_id'],source_sha256=source['sha256'],source_size=[source['width'],source['height']],bbox=box_union([f['bbox']])),
                blocks=[dict(block_id='one-text',bbox=box_union([f['bbox']]),source_fragment_ids=[fid],runs=[dict(format='plain',text='Unverified draft')],note='Picture must remain independently rendered')])
            p=producer.make_revision_plan(e,g,c,[op],self.author);app=producer.apply_content_revision(e,g,c,p)
            def legacy(payload):next(a for a in payload['answers']if a['answer_id']==answer['answer_id']).pop('render_regions')
            e,g,c=synthetic_presentation_version(e,g,c,legacy)
            bad=copy.deepcopy(p);bad['payload'].update(evidence_ref=ref(e),graph_ref=ref(g),base_check_ref=ref(c));resign(bad)
            with self.assertRaisesRegex(ValueError,'legacy image.*typed migration'):producer.validate_revision_plan(bad,e,g,c)
            self.assert_reject(consumer.audit_content_application(e,g,c,bad,app)['payload'])


class ObservedQ16RegionTests(unittest.TestCase):
    def test_real_Q16_three_blocks_cover_seventeen_raw_sources_without_fabricating_F5(self):
        docs,_=observed_inputs();e,g,c,r=[docs[k]for k in ('evidence','graph','base-check','review')]
        operations=json.loads((ROOT/'tests/fixtures/book46007447/content-region-operations.json').read_text(encoding='utf8'))
        region=next(o for o in operations if o['kind']=='REBUILD_TEXT_REGION')
        p=producer.make_revision_plan(e,g,c,operations,dict(kind='MODEL_DRAFT',id='q16-source-development-plan',note='Frozen source-based development draft, not human gold'),previous_plan=observed_plan(2))
        a=producer.apply_content_revision(e,g,c,p);q=producer.build_content_quality(e,g,c,p,a,r);graph=a['payload']['graph']
        before=next(aa for aa in g['payload']['answers']if aa['answer_id']==region['target']['answer_id']);after=next(aa for aa in graph['payload']['answers']if aa['answer_id']==before['answer_id'])
        self.assertEqual(len(before['fragments']),17);self.assertEqual(after['fragments'],before['fragments'])
        self.assertEqual([len(b['source_fragment_ids'])for b in region['blocks']],[7,3,7])
        bound=[fid for b in region['blocks']for fid in b['source_fragment_ids']];self.assertEqual(len(bound),len(set(bound)));self.assertEqual(set(bound),set(region['target']['source_fragment_ids']))
        self.assertEqual(after['text'],'\n'.join(''.join(run['text']for run in b['runs'])for b in region['blocks']))
        self.assertEqual(after['regions'],after['render_regions']);self.assertEqual(len(after['render_regions']),3)
        self.assertTrue(all(z['verification_status']=='UNVERIFIED'for z in after['render_regions']))
        source_by_id={f['parent_line_id']:f for f in before['fragments']}
        self.assertIn('recovery/unit2-q16/scale3/10',source_by_id)
        self.assertEqual(source_by_id['recovery/unit2-q16/scale3/10']['raw_text'],'a-la²+1')
        layout=json.loads((ROOT/'tests/fixtures/book46007447/formula-layout.json').read_text(encoding='utf8'))['payload']
        self.assertEqual(layout['fraction_candidates'][4]['numerator']['ocr_refs'],[]);self.assertEqual(layout['fraction_candidates'][4]['denominator']['ocr_refs'],[])
        self.assertEqual(graph['payload']['answer_coverage'],g['payload']['answer_coverage']);self.assertEqual(sum(x['status']=='UNASSIGNED'for x in graph['payload']['answer_coverage']),19)
        self.assertTrue(consumer.audit_content_application(e,g,c,p,a)['payload']['accepted'])
        self.assertTrue(consumer.audit_content_quality(e,g,c,p,a,r,q)['payload']['accepted'])
        self.assertEqual(q['payload']['decision'],'HOLD');self.assertFalse(q['payload']['transcription_verified'])
        self.assertEqual(q['payload']['graph_ref'],ref(graph));self.assertNotEqual(q['payload']['graph_ref'],ref(g))
        self.assertEqual(q['payload']['base_check_archive'],c)


if __name__=='__main__':unittest.main()
