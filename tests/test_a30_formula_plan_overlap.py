"""New planning-only connected-row and cross-owner conflict controls."""
from pathlib import Path
import copy,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.formula_regions import _merge_clear_regions
from annotation.customer import formula_batch
from annotation.customer.store import Store,Hold

def row(identity,box,zone='answer',candidate='new-candidate'):
 return {'proposal_id':identity,'candidate_key':candidate,'zone':zone,'asset_id':'new-page','source_sha256':'a'*64,
  'source_dimensions':[500,400],'bbox':box,'adjustment_bounds':[10,10,450,200],'origin':'RETAINED_OCR_LINE',
  'uncertainty':'OBSERVED_MATH_ROW','evidence_refs':[identity],'layout_ref':None,'model_called':False,'content_approved':False}

class OverlapPlan(unittest.TestCase):
 def test_three_connected_math_rows_become_one_source_bound_candidate(self):
  original=[row('new-a',[20,20,180,50]),row('new-b',[30,44,190,80]),row('new-c',[40,75,210,110])]
  before=copy.deepcopy(original);merged=_merge_clear_regions(original,{})
  self.assertEqual(len(merged),1);self.assertEqual(merged[0]['bbox'],[20,20,210,110])
  self.assertEqual([r['proposal_id'] for r in merged[0]['source_regions']],['new-a','new-b','new-c'])
  self.assertEqual(merged[0]['evidence_refs'],['new-a','new-b','new-c']);self.assertEqual(original,before)
  self.assertEqual(merged[0]['uncertainty'],'OBSERVED_MATH_ROW');self.assertFalse(merged[0]['content_approved'])
 def test_mixed_text_in_merged_box_is_not_automatic_clear_candidate(self):
  regions=[row('new-d',[20,20,200,60]),row('new-e',[50,55,220,100])]
  lines={'new-chinese':({'asset_id':'new-page'},{'text':'继续证明','bbox':[25,68,45,82]})}
  merged=_merge_clear_regions(regions,lines)
  self.assertEqual(len(merged),1);self.assertEqual(merged[0]['uncertainty'],'MIXED_TEXT_COARSE_REGION')
 def test_cross_zone_collision_is_manual_before_batch_intent(self):
  regions=[row('new-f',[20,20,180,55]),row('new-g',[25,50,200,85],zone='question')]
  self.assertEqual(len(_merge_clear_regions(regions,{})),2)
  class FixtureStore(Store):
   def job(self,identity):return self.fixture,'new-head'
  with tempfile.TemporaryDirectory() as directory:
   store=FixtureStore(Path(directory));store.fixture={'book_id':'792671','graph_ref':store.put({'graph':'new'}),
     'evidence_ref':store.put({'evidence':'new'}),'candidates':[{'key':'new-candidate','printed_number':'49','platform_status':'NOT_RUN'}]}
   with patch.object(formula_batch,'propose',return_value={'regions':regions}),patch.object(formula_batch,'recognize_proposal',side_effect=AssertionError('No worker')):
    scope=formula_batch.plan(store,'new-job','new-head')
    self.assertFalse(scope['clear_regions']);self.assertEqual(len(scope['manual_region_review']),2)
    self.assertTrue(all(r['uncertainty']=='CROSS_ROLE_BOUNDARY_REVIEW' for r in scope['manual_region_review']))
    self.assertEqual(formula_batch.run(store,'new-job','new-head',{'runtime':{'formula_inference_activated':True}},lambda value:None)['status'],'NO_CLEAR_REGIONS')
   with store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM operations').fetchone()[0],0)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
