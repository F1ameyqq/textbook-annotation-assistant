"""Portable synthetic Q7 finalization tests; no real captures, files or network.

Uses the published insertion fixture. Fixed production-scope IDs are imported
from contract constants, and all bodies, bounds, source hashes and actors are
synthetic. The fixed OSS crop host is required by the production contract; its
test crop coordinates are generated synthetic values and are never fetched.
"""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from test_usense_live_insertion import u,ins as i,synthetic_fixture,synthetic_readback,uid
from annotation.runtime.usense_live import finalize as f


def synthetic_main_frame_ids(before):
    """Bind six wholly synthetic old rows to the operation's fixed scope IDs."""
    layout={('question',0):f.REUSED['main-stem'],('question',1):f.REUSED['main-figure'],
        ('question',2):f.RETIRE[0],('choice',0):f.REUSED['main-choice-A'],
        ('choice',1):f.RETIRE[1],('answer',0):f.REUSED['main-answer']}
    mapping={row['rect_id']:layout[(row['type'],row['image_order_in_annotation_zone'])]
        for row in before['q7_annotations']['data']}
    for row in before['frames']['data']:
        row['rect_id']=mapping.get(row['rect_id'],row['rect_id'])
    before['frames']['data'].sort(key=lambda row:row['rect_id'])
    before['q7_annotations']['data']=[copy.deepcopy(row) for row in before['frames']['data']
        if row['order_in_level']=='7']
    for zone in u.ZONES:
        data=before['q7_'+zone]['data']
        if 'rect_ids' in data:data['rect_ids']=[mapping.get(rect,rect) for rect in data['rect_ids']]


def fixture(extra_source=False):
    before,payload,variant_approved=synthetic_fixture()
    synthetic_main_frame_ids(before)
    if extra_source:before['source']['future_field']={'opaque':[1,'2',False]}
    pp=i.make_insert_plan(before,payload_candidate=payload,approved_new_content=variant_approved)
    actual,receipt=synthetic_readback(before,payload)
    actors={'runtime_actor_sha256':u.text_digest('SYNTHETIC-username'),
        'runtime_user_id_sha256':u.text_digest('222')}
    comparison=i.compare_insert_readback(pp,actual,receipt,runtime_actor_hashes=actors)
    assert comparison['ok'],comparison['differences']
    refs={name:{'path':'SYNTHETIC-'+name+'.json','sha256':'a'*64}
        for name in ('plan','receipt','comparison','outer_acceptance')}
    evidence={name:{'path':'SYNTHETIC-'+name+'.json','sha256':'a'*64} for name in f.EVIDENCE_ROLES}
    evidence['raw_receipt']=refs['receipt'];evidence['comparison']=refs['comparison']
    outer={'schema':'Q7Phase1OuterAcceptance/v1','status':'ACCEPTED_COPY_FIRST_WITH_EXTERNAL_RELEASE',
        'writer_status':'INSERT_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK',
        **{flag:True for flag in f.OUTER_FLAGS},'writer_exit_code':0,'reader_exit_codes':[0,0,0,0],
        'post_attempts':1,'post_layers':{'context':1,'native':1},'reader_writes':0,
        'writer_run_id':'synthetic-writer','reader_run_ids':['synthetic-r1','synthetic-r2','synthetic-r3','synthetic-r4'],
        'phase1_plan_sha256':pp['plan_sha256'],'phase1_receipt_sha256':comparison['receipt_sha256'],
        'after_sha256':comparison['after_sha256'],'ledger_key':pp['ledger_key'],'evidence_refs':evidence}
    predecessor={'phase1_plan':pp,'phase1_receipt':receipt,'phase1_comparison':comparison,
        'runtime_actor_hashes':actors,'outer_acceptance':outer,'artifact_refs':refs}
    main=copy.deepcopy(variant_approved['candidate'])
    main.update(logical_owner='main',target={'node_id':i.OLD_Q7_NODE,'info_id':i.OLD_Q7_INFO,'question_order':7},
        root_review_status='PASS_SOURCE_CONTENT_AND_BOUNDARIES',root_review_ref='SYNTHETIC-review.json')
    for row,key in zip(main['frames'],f.MAIN_KEYS):
        row['key']=key;row['planned_rect_id']=f.REUSED[key] if key in f.REUSED else uid('SYNTHETIC-MAIN-'+key)
    main['planned_frames']=copy.deepcopy(main['frames'])
    main['zone_values']={'question':'SYNTHETIC MAIN ONLY <img src="'+main['frames'][1]['image_path']+'" />',
        'choice':'A. 1\nB. 2\nC. 3\nD. 4','answer':'C'}
    main['zone_text_sha256']={zone:u.text_digest(text) for zone,text in main['zone_values'].items()}
    approved=copy.deepcopy(variant_approved);approved['candidate']=main
    return actual,approved,predecessor


def phase2_result(plan):
    result=copy.deepcopy(plan['expected_template'])
    for row in result['frames']['data']:
        if row['rect_id'] in plan['new_main_rect_ids']:
            row['created_at']=row['updated_at']='2026-10-23T03:00:01';row['user_id']='222'
        elif row['rect_id'] in plan['reused_main_rect_ids']:
            row['updated_at']='2026-10-23T03:00:01'
    result['q7_info']['data']['updated_at']='2026-10-23T03:00:01'
    main_ids=set(plan['new_main_rect_ids'])|set(plan['reused_main_rect_ids'])
    result['q7_annotations']['data']=[copy.deepcopy(row) for row in result['frames']['data'] if row['rect_id'] in main_ids]
    receipt={'code':0,'message':'success','data':{'inserted':False,'question_order':7,
        'inserted_question_node':None,'success':True,'append_at_global_end':False}}
    clock={'send_intent_at':'2026-10-22T19:00:00+00:00','finished_at':'2026-10-22T19:00:02+00:00',
        'database_utc_offset_minutes':480,'tolerance_seconds':2}
    return result,receipt,clock


class FinalizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before,cls.approved,cls.prior=fixture()
        cls.plan=f.make_finalize_plan(cls.before,cls.approved,cls.prior)
    def plan_mutation_rejected(self,fn):
        plan=copy.deepcopy(self.plan);fn(plan)
        with self.assertRaises(ValueError):f.validate_finalize_plan(plan)
    def readback(self,fn=lambda a:None,receipt_fn=lambda r:None,clock_fn=lambda c:None):
        after,receipt,clock=phase2_result(self.plan);fn(after);receipt_fn(receipt);clock_fn(clock)
        return f.compare_finalize_readback(self.plan,after,receipt,runtime_actor_hashes=self.prior['runtime_actor_hashes'],write_clock=clock)
    def test_exact_shape_and_actor_preservation(self):
        p=self.plan['payload_candidate'];self.assertEqual(len(p['annotations_upsert']),7)
        self.assertEqual(p['annotations_delete_rect_ids'],list(f.RETIRE));self.assertEqual(len(p['ocr_submissions']),3)
        self.assertEqual(sum(r['user_id'] is None for r in p['annotations_upsert']),3)
        old={r['rect_id']:r for r in self.before['q7_annotations']['data']}
        for r in p['annotations_upsert']:
            if r['rect_id'] in old:self.assertEqual(r['user_id'],old[r['rect_id']]['user_id'])
        self.assertEqual(p['question_info'],{'tishi':'xuanze','tilei':None,'tihao':None})
    def test_happy_synthetic(self):self.assertTrue(self.readback()['ok'])
    def test_inputs_not_mutated(self):
        b,a,p=copy.deepcopy((self.before,self.approved,self.prior));f.make_finalize_plan(b,a,p)
        self.assertTrue(u.json_same(b,self.before) and u.json_same(a,self.approved) and u.json_same(p,self.prior))
    def test_predecessor_unknown(self):
        p=copy.deepcopy(self.prior);p['outer_acceptance']['writer_status']='UNKNOWN_DO_NOT_RETRY'
        with self.assertRaises(ValueError):f.make_finalize_plan(self.before,self.approved,p)
    def test_predecessor_absent(self):
        with self.assertRaises(ValueError):f.make_finalize_plan(self.before,self.approved,None)
    def test_predecessor_missing_exit(self):
        for flag in f.OUTER_FLAGS:
            with self.subTest(flag=flag):
                p=copy.deepcopy(self.prior);p['outer_acceptance'][flag]=False
                with self.assertRaises(ValueError):f.make_finalize_plan(self.before,self.approved,p)
    def test_predecessor_forged_server_id(self):
        p=copy.deepcopy(self.prior);p['phase1_receipt']['data']['inserted_question_node']['id']='fabricated'
        with self.assertRaises(ValueError):f.make_finalize_plan(self.before,self.approved,p)
    def test_predecessor_same_context(self):
        p=copy.deepcopy(self.prior);p['outer_acceptance']['reader_run_ids'][0]='synthetic-writer'
        with self.assertRaises(ValueError):f.make_finalize_plan(self.before,self.approved,p)
    def test_prewrite_rejects_other_question_drift(self):
        b=copy.deepcopy(self.before);b['q9_question']['data']['ocr_result']+='x'
        with self.assertRaises(ValueError):f.check_prewrite(self.plan,b)
    def test_prewrite_pass(self):self.assertTrue(f.check_prewrite(self.plan,self.before)['ok'])
    def test_plan_extra_delete(self):self.plan_mutation_rejected(lambda p:p['payload_candidate']['annotations_delete_rect_ids'].append('other'))
    def test_plan_wrong_retired_identity(self):
        self.plan_mutation_rejected(lambda p:p['payload_candidate']['annotations_delete_rect_ids'].__setitem__(0,f.REUSED['main-stem']))
    def test_plan_extra_upsert(self):self.plan_mutation_rejected(lambda p:p['payload_candidate']['annotations_upsert'].append(copy.deepcopy(p['payload_candidate']['annotations_upsert'][0])))
    def test_plan_actor_rebind_old(self):self.plan_mutation_rejected(lambda p:p['payload_candidate']['annotations_upsert'][0].update(user_id=None))
    def test_plan_wrong_answer(self):self.plan_mutation_rejected(lambda p:p['payload_candidate']['ocr_submissions'][2].update(ocr_result='B'))
    def test_plan_type_wrong(self):self.plan_mutation_rejected(lambda p:p['payload_candidate']['question_info'].update(tishi='duoxuan'))
    def test_candidate_geometry_outside_source(self):
        a=copy.deepcopy(self.approved)
        for key in ('frames','planned_frames'):a['candidate'][key][0]['bbox'][2]=1001
        with self.assertRaises(ValueError):f.make_finalize_plan(self.before,a,self.prior)
    def test_candidate_unverified_crop(self):
        a=copy.deepcopy(self.approved)
        for key in ('frames','planned_frames'):a['candidate'][key][0]['fetch_evidence']['http_status']=404
        with self.assertRaises(ValueError):f.make_finalize_plan(self.before,a,self.prior)
    def test_after_other_question_text_changed(self):self.assertFalse(self.readback(lambda a:a['q8_question']['data'].update(ocr_result='lost'))['ok'])
    def test_after_other_info_metadata_changed(self):self.assertFalse(self.readback(lambda a:a['q9_info']['data'].update(updated_at='2026-10-23T03:00:01'))['ok'])
    def test_after_directory_unknown_field_added(self):self.assertFalse(self.readback(lambda a:a['directory'].update(extra=1))['ok'])
    def test_after_other_unknown_field_added(self):self.assertFalse(self.readback(lambda a:a['q22_info']['data'].update(extra='silent'))['ok'])
    def test_after_original_owner_changed(self):
        def mutate(a):
            rid=f.REUSED['main-stem']
            for r in a['frames']['data']+a['q7_annotations']['data']:
                if r['rect_id']==rid:r['user_id']='other-owner'
        self.assertFalse(self.readback(mutate)['ok'])
    def test_after_original_creation_time_changed(self):
        def mutate(a):
            for r in a['frames']['data']+a['q7_annotations']['data']:
                if r['rect_id']==f.REUSED['main-stem']:r['created_at']='2026-10-23T03:00:01'
        self.assertFalse(self.readback(mutate)['ok'])
    def test_after_new_owner_changed(self):
        def mutate(a):
            for r in a['frames']['data']+a['q7_annotations']['data']:
                if r['rect_id']==self.plan['new_main_rect_ids'][0]:r['user_id']='wrong'
        self.assertFalse(self.readback(mutate)['ok'])
    def test_after_global_array_order_changed(self):self.assertFalse(self.readback(lambda a:a['frames']['data'].reverse())['ok'])
    def test_after_zone_rect_order_changed(self):self.assertFalse(self.readback(lambda a:a['q7_choice']['data']['rect_ids'].reverse())['ok'])
    def test_after_answer_wrong(self):self.assertFalse(self.readback(lambda a:a['q7_answer']['data'].update(ocr_result='B'))['ok'])
    def test_after_figure_mixed(self):self.assertFalse(self.readback(lambda a:a['q7_question']['data'].update(ocr_result='main+variant'))['ok'])
    def test_after_source_changed(self):self.assertFalse(self.readback(lambda a:a['source'].update(extra=True))['ok'])
    def test_after_missing_frame(self):self.assertFalse(self.readback(lambda a:a['frames']['data'].pop())['ok'])
    def test_receipt_inserted_true(self):self.assertFalse(self.readback(receipt_fn=lambda r:r['data'].update(inserted=True))['ok'])
    def test_receipt_wrong_order(self):self.assertFalse(self.readback(receipt_fn=lambda r:r['data'].update(question_order=8))['ok'])
    def test_receipt_unknown_field(self):self.assertFalse(self.readback(receipt_fn=lambda r:r['data'].update(unobserved=True))['ok'])
    def test_clock_wide_window_rejected(self):self.assertFalse(self.readback(clock_fn=lambda c:c.update(finished_at='2026-10-22T20:00:00+00:00'))['ok'])
    def test_clock_wrong_offset_rejected(self):self.assertFalse(self.readback(clock_fn=lambda c:c.update(database_utc_offset_minutes=0))['ok'])
    def test_clock_timestamp_outside_rejected(self):self.assertFalse(self.readback(clock_fn=lambda c:c.update(send_intent_at='2026-10-22T20:00:00+00:00',finished_at='2026-10-22T20:00:01+00:00'))['ok'])
    def test_existing_unknown_source_field_preserved(self):
        b,a,p=fixture(extra_source=True);plan=f.make_finalize_plan(b,a,p);after,receipt,clock=phase2_result(plan)
        self.assertTrue(f.compare_finalize_readback(plan,after,receipt,runtime_actor_hashes=p['runtime_actor_hashes'],write_clock=clock)['ok'])
        after['source'].pop('future_field')
        self.assertFalse(f.compare_finalize_readback(plan,after,receipt,runtime_actor_hashes=p['runtime_actor_hashes'],write_clock=clock)['ok'])


if __name__=='__main__':unittest.main(verbosity=2)
