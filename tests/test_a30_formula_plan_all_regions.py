"""Finite planning controls for mixed regions and union-created conflicts."""
from pathlib import Path
import copy,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.formula_regions import _merge_clear_regions,mark_boundary_conflicts,recognize_proposal
from annotation.customer import formula_batch
from annotation.customer.store import Store,Hold,digest

def row(identity,box,*,mixed=False,zone='answer'):
 return {'proposal_id':identity,'candidate_key':'fresh-candidate','zone':zone,'asset_id':'fresh-page','source_sha256':'b'*64,
  'source_dimensions':[500,400],'bbox':box,'adjustment_bounds':[10,10,450,250],'origin':'RETAINED_OCR_LINE',
  'uncertainty':'MIXED_TEXT_COARSE_REGION' if mixed else 'OBSERVED_MATH_ROW','evidence_refs':[identity],
  'layout_ref':None,'model_called':False,'content_approved':False}

class AllRegions(unittest.TestCase):
 def test_clear_mixed_connected_component_is_single_manual_region(self):
  original=[row('clear',[20,20,180,50]),row('mixed',[30,45,190,80],mixed=True),row('tail',[40,75,210,110])]
  before=copy.deepcopy(original);result=_merge_clear_regions(original,{})
  self.assertEqual(len(result),1);self.assertEqual(result[0]['bbox'],[20,20,210,110])
  self.assertEqual(result[0]['uncertainty'],'MIXED_TEXT_COARSE_REGION')
  self.assertEqual([r['proposal_id'] for r in result[0]['source_regions']],['clear','mixed','tail'])
  self.assertEqual(original,before);self.assertFalse(result[0]['content_approved'])
 def test_union_rectangle_absorbs_region_inside_newly_covered_gap(self):
  original=[row('upper',[20,20,200,60]),row('right',[180,50,220,150]),row('gap',[30,100,100,140],mixed=True)]
  result=_merge_clear_regions(original,{})
  self.assertEqual(len(result),1);self.assertEqual(result[0]['bbox'],[20,20,220,150])
  self.assertEqual(result[0]['evidence_refs'],['upper','right','gap'])
  self.assertEqual(result[0]['uncertainty'],'MIXED_TEXT_COARSE_REGION')
 def test_preexisting_intermediate_nonproposal_line_is_ordered_and_hashed(self):
  source={'a':({'asset_id':'fresh-page'},{'text':'x=2','bbox':[20,20,200,60]}),
          'between':({'asset_id':'fresh-page'},{'text':'所以原式成立','bbox':[25,66,45,82]}),
          'b':({'asset_id':'fresh-page'},{'text':'y=4','bbox':[50,55,220,100]})}
  result=_merge_clear_regions([row('a',[20,20,200,60]),row('b',[50,55,220,100])],source)[0]
  self.assertEqual(result['uncertainty'],'MIXED_TEXT_COARSE_REGION')
  self.assertEqual(result['evidence_refs'],['a','between','b'])
  self.assertEqual(result['covered_source_lines'][1],{'line_id':'between','line_sha256':digest(source['between'][1]),'line':source['between'][1]})
 def test_cross_role_mixed_collision_is_retained_outside_batch(self):
  regions=[row('answer',[20,20,180,55],mixed=True),row('question',[25,50,200,85],mixed=True,zone='question')]
  self.assertEqual(len(_merge_clear_regions(regions,{})),2)
  class FixtureStore(Store):
   def job(self,identity):return self.fixture,'fresh-head'
  with tempfile.TemporaryDirectory() as directory:
   store=FixtureStore(Path(directory));store.fixture={'book_id':'862731','graph_ref':store.put({}),
    'evidence_ref':store.put({'type':'source'}),'candidates':[{'key':'fresh-candidate','printed_number':'52','platform_status':'NOT_RUN'}]}
   with patch.object(formula_batch,'propose',return_value={'regions':regions}),patch.object(formula_batch,'recognize_proposal',side_effect=AssertionError('No worker')):
    scope=formula_batch.plan(store,'fresh-job','fresh-head')
    self.assertFalse(scope['clear_regions']);self.assertEqual(len(scope['manual_region_review']),2)
    self.assertTrue(all(r['boundary_review_required'] for r in scope['manual_region_review']))
    self.assertEqual(formula_batch.run(store,'fresh-job','fresh-head',{'runtime':{'formula_inference_activated':True}},lambda value:None)['status'],'NO_CLEAR_REGIONS')
   with store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM operations').fetchone()[0],0)
 def test_cross_question_only_excludes_conflicting_pair_and_keeps_provenance(self):
  first=row('first',[20,20,180,55]);second=row('second',[25,50,200,85]);second['candidate_key']='other-candidate'
  independent=row('independent',[20,100,100,125]);before=copy.deepcopy([first,second,independent])
  marked=mark_boundary_conflicts(before)
  self.assertEqual([r['uncertainty'] for r in marked],['CROSS_QUESTION_BOUNDARY_REVIEW','CROSS_QUESTION_BOUNDARY_REVIEW','OBSERVED_MATH_ROW'])
  for original,current in zip(before,marked):
   self.assertEqual(current['bbox'],original['bbox']);self.assertEqual(current['evidence_refs'],original['evidence_refs'])
  self.assertEqual(before,[first,second,independent])
 def test_boundary_adjustment_gate_is_on_normal_first_call_path(self):
  first=row('selected',[20,20,180,55]);second=row('peer',[25,50,200,85]);second['candidate_key']='other-candidate'
  selected=mark_boundary_conflicts([first,second])[0]
  class FixtureStore(Store):
   def job(self,identity):return self.fixture,'boundary-head'
  with tempfile.TemporaryDirectory() as directory:
   store=FixtureStore(Path(directory));store.fixture={'book_id':'862735','pages':[{'asset_id':'fresh-page'}],
    'graph_ref':store.put({}),'evidence_ref':store.put({'type':'boundary-source'}),
    'candidates':[{'key':'fresh-candidate','platform_status':'NOT_RUN'}]}
   with patch('annotation.customer.source.verify_sources'),patch('annotation.customer.formula_regions.propose_job',return_value={'fresh-candidate':{'regions':[selected]}}),patch('annotation.customer.formula_runtime.obtain_region',return_value={'new_worker_invocations':1}) as worker:
    for box in (None,[20,20,180,55],[20,20,180,53]):
     with self.assertRaisesRegex(Hold,'相邻题目'):recognize_proposal(store,'boundary-job','boundary-head','fresh-candidate','selected',{},source_checked=True,adjusted_bbox=box)
    self.assertEqual(worker.call_count,0)
    recognize_proposal(store,'boundary-job','boundary-head','fresh-candidate','selected',{},source_checked=True,adjusted_bbox=[20,20,180,49])
    self.assertEqual(worker.call_count,1);self.assertEqual(worker.call_args.args[3],[20,20,180,49])

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
