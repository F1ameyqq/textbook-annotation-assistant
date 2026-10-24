"""New generic absent-zone fill cases; no historical or current platform runs."""
from pathlib import Path
import sys,copy,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import test_a30_customer as fixtures
from annotation.customer.store import Hold
from annotation.customer.native_plan import make_plan,compare_readback,check_plan
from annotation.customer.existing_fill import decode
from annotation.customer.legacy_ledger import existing_candidate

class ExistingFillR1(unittest.TestCase):
 setUp=fixtures.OrdinaryInputs.setUp
 image_job=fixtures.ImageAndProduction.image_job
 def missing(self):
  job,before=self.image_job();candidate=job['candidates'][0];insert=make_plan(before,candidate,job['lesson'])
  before,_=fixtures.apply_native(before,insert,407)
  for zone in candidate['zones']:before['questions']['server-node-407']['zones'][zone]=fixtures.response({'message':'absent','success':False})
  return job,before,candidate
 def test_existing_empty_body_fills_same_identity_without_inserting_or_reframing(self):
  job,before,q=self.missing();self.assertIsNone(existing_candidate(before,q));plan=make_plan(before,q,job['lesson']);check_plan(plan)
  self.assertEqual(plan['schema'],'CustomerNativeExistingFillPlan/v1');self.assertEqual(plan['payload']['annotations_upsert'],[])
  self.assertFalse(plan['payload']['is_new_question_insertion']);after=copy.deepcopy(before)
  for submission in plan['payload']['ocr_submissions']:
   after['questions'][plan['target_node']]['zones'][submission['zone']]=fixtures.response({'success':True,'ocr_result':submission['ocr_result'],'rect_ids':submission['rect_ids']})
  receipt=fixtures.response({'inserted':False,'question_order':1,'inserted_question_node':None,'success':True,'append_at_global_end':False})
  self.assertTrue(decode(plan,receipt)['ok']);comparison=compare_readback(plan,after,receipt)
  self.assertTrue(comparison['existing_node_filled']);self.assertFalse(comparison['inserted'])
  self.assertEqual(after['directory'],before['directory']);self.assertEqual(after['frames'],before['frames'])
  self.assertEqual(existing_candidate(after,q)['node_id'],plan['target_node'])
  damaged=copy.deepcopy(after);damaged['frames']['data'][0]['verified']=1
  with self.assertRaises(Hold):compare_readback(plan,damaged,receipt)
 def test_existing_nonempty_different_body_cannot_be_overwritten(self):
  job,before,q=self.missing();record=before['questions']['server-node-407'];old=record['annotations']['data'][0]
  record['zones']['question']=fixtures.response({'success':True,'ocr_result':'Different preserved native text','rect_ids':[old['rect_id']]})
  with self.assertRaises(Hold):make_plan(before,q,job['lesson'])
 def test_existing_source_must_be_contained_not_only_intersecting(self):
  job,before,q=self.missing();before['frames']['data'][0]['rect_bbox']='31,41,35,45'
  before['questions']['server-node-407']['annotations']['data'][0]['rect_bbox']='31,41,35,45'
  with self.assertRaises(Hold):make_plan(before,q,job['lesson'])
 def test_existing_fill_is_consumed_by_actual_writer_preflight_without_rows(self):
  from annotation.customer import wire
  from annotation.customer.store import encoded
  from annotation.runtime.usense_live.insertion_writer import validate_inputs
  job,before,q=self.missing();plan=make_plan(before,q,job['lesson'])
  flat={'directory':before['directory'],'frames':before['frames'],'source':fixtures.response({'file_id':job['book_id'],'total_pages':180})}
  for page in before['pages'].values():flat['page_'+str(page['viewer_page'])]=fixtures.response({'file_id':job['book_id'],
   'pages':[{'page_index':page['viewer_page']-1,'image':page['image_url']}]})
  record=before['questions']['server-node-407'];flat['q1_info']=record['info'];flat['q1_annotations']=record['annotations']
  for zone,response in record['zones'].items():flat['q1_'+zone]=response
  source_refs=[{'path':p['raw_path'],'sha256':p['raw_sha256']} for p in job['pages']]
  product=wire.make_wire_plan(plan,flat,source_refs)
  baseline=self.root/'new-fill-baseline';baseline.mkdir();ledger=self.root/'new-fill-ledger';ledger.mkdir()
  for name,value in flat.items():(baseline/(name+'.json')).write_bytes(encoded(value))
  captured,paths,claim=validate_inputs(product,baseline,ledger,'synthetic-only-new-fill-check')
  self.assertEqual(captured,flat);self.assertEqual(product['operation'],'CUSTOMER_SOURCE_BOUND_EXISTING_FILL')
  self.assertEqual(product['payload_candidate']['annotations_upsert'],[]);self.assertFalse(claim.exists())
  changed=copy.deepcopy(flat);changed['q1_info']['data']=dict(reversed(list(changed['q1_info']['data'].items())))
  with self.assertRaises(Hold):wire.check_prewrite(product,changed)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
