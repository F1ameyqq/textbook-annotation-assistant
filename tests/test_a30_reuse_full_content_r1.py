"""New formal-review counterexample: native reuse must retain required images."""
from pathlib import Path
import sys,copy,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import test_a30_customer as fixtures
from annotation.customer.store import Hold
from annotation.customer.native_plan import make_plan
from annotation.customer.legacy_ledger import existing_candidate
from annotation.customer.review import CustomerReviewWorkspace

class CompleteReuseR1(unittest.TestCase):
 setUp=fixtures.OrdinaryInputs.setUp
 image_job=fixtures.ImageAndProduction.image_job
 def test_missing_candidate_figure_never_becomes_completed_text_reuse(self):
  job,empty=self.image_job();q=job['candidates'][0]
  old,_=fixtures.apply_native(empty,make_plan(empty,q,job['lesson']),507)
  ws=CustomerReviewWorkspace(self.store,job['id']);state=ws.state()
  state=ws.bind_region({'expected_head':state['head'],'answer_id':q['key'],'asset_id':q['frames'][0]['asset_id'],
   'bbox':[320,30,450,70],'zone':'question','source_checked':True})
  ws.confirm({'expected_head':state['head'],'answer_id':q['key'],'source_checked':True,'content_checked':True})
  updated=self.store.job(job['id'])[0]['candidates'][0]
  with self.assertRaises(Hold):existing_candidate(old,updated)
  self.assertFalse(updated.get('acceptance_ref'));self.assertEqual(updated['platform_status'],'NOT_RUN')
  correct,_=fixtures.apply_native(empty,make_plan(empty,updated,job['lesson']),508)
  self.assertEqual(existing_candidate(correct,updated)['node_id'],'server-node-508')
  changed=copy.deepcopy(correct);record=changed['questions']['server-node-508']
  record['zones']['question']['data']['ocr_result']=record['zones']['question']['data']['ocr_result'].split('<br><img')[0]
  with self.assertRaises(Hold):existing_candidate(changed,updated)
  changed=copy.deepcopy(correct);changed['questions']['server-node-508']['zones']['answer']['data']['ocr_result']='$x^3$'
  with self.assertRaises(Hold):existing_candidate(changed,updated)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
