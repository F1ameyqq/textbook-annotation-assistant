"""New finite operation-scope checks; synthetic sources, no platform/OCR."""
from pathlib import Path
import sys, copy, unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tests'))
import test_a30_customer as fixtures
from annotation.customer.native_plan import make_plan,source_key
from annotation.customer.prepare import candidate_hash
from annotation.customer.production import produce,_execution_plan
from annotation.customer.store import Hold


class ExecutionScopeR1(unittest.TestCase):
 setUp=fixtures.OrdinaryInputs.setUp
 image_job=fixtures.ImageAndProduction.image_job

 def fixture(self,complete=False):
  job,empty=self.image_job();q=job['candidates'][1]
  current,_=fixtures.apply_native(empty,make_plan(empty,q,job['lesson']),704)
  if not complete:
   for zone in q['zones']:current['questions']['server-node-704']['zones'][zone]=fixtures.response({'success':False})
  scope={'book_id':job['book_id'],'directory_id':'new-lesson','directory_path':job['lesson'],
   'expected_initial_native_count':1,'selection':[]}
  for i,candidate in enumerate(job['candidates']):
   scope['selection'].append({'key':candidate['key'],'content_hash':candidate_hash(candidate),
    'source_key':source_key(job['book_id'],candidate),'zones':list(candidate['zones']),
    'source_frames':copy.deepcopy(candidate['frames']),
    'intended_operation':'FILL_EXISTING_EMPTY_ZONES' if i else 'INSERT_NEW_NATIVE_QUESTION',
    'expected_existing_node':'server-node-704' if i else None,
    'expected_existing_info':'server-info-704' if i else None,
    'expected_rect_ids_by_zone':{zone:[f['rect_id'] for f in current['questions']['server-node-704']['annotations']['data'] if f['type']==zone] for zone in candidate['zones']} if i else None})
  return job,empty,current,scope

 def test_dynamic_identity_and_operation_cannot_drift(self):
  job,empty,current,scope=self.fixture();q=job['candidates'][1]
  plan=_execution_plan(current,q,job['lesson'],scope)
  self.assertEqual(plan['target_node'],'server-node-704');self.assertFalse(plan['payload']['is_new_question_insertion'])
  self.assertEqual(_execution_plan(current,job['candidates'][0],job['lesson'],scope)['schema'],'CustomerNativeInsertPlan/v1')
  with self.assertRaises(Hold):_execution_plan(empty,q,job['lesson'],scope)
  changed=copy.deepcopy(current);changed['questions']['server-node-704']['info']['data']['id']='replacement-info'
  with self.assertRaises(Hold):_execution_plan(changed,q,job['lesson'],scope)
  changed=copy.deepcopy(current);changed['questions']['replacement-node']=changed['questions'].pop('server-node-704')
  changed['directory']['data']['directory_data'][0]['children'][0]['children'][0]['id']='replacement-node'
  with self.assertRaises(Hold):_execution_plan(changed,q,job['lesson'],scope)

 def assert_stops_before_any_send_or_current_reuse(self,current,job,scope):
  class Platform:
   def __init__(self):self.processes=[];self.captures=0;self.sends=0
   def capture(self,*args,**kwargs):self.captures+=1;return copy.deepcopy(current),{}
   def write_once(self,*args):self.sends+=1;raise AssertionError('must stop before first send')
  platform=Platform()
  with self.assertRaises(Hold):
   produce(self.store,job['id'],{},transport_factory=lambda *args:platform,
    selected_keys=[q['key'] for q in job['candidates']],execution_scope=scope)
  self.assertEqual(platform.captures,1);self.assertEqual(platform.sends,0)
  with self.store.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM operations WHERE kind=?",('save:'+job['book_id'],)).fetchone()[0],0)
  self.assertTrue(all(not q.get('acceptance_ref') for q in self.store.job(job['id'])[0]['candidates']))

 def test_later_changed_target_blocks_earlier_valid_insert(self):
  job,empty,current,scope=self.fixture()
  current['questions']['server-node-704']['info']['data']['id']='replacement-info'
  self.assert_stops_before_any_send_or_current_reuse(current,job,scope)

 def test_complete_existing_target_holds_before_reuse_shortcut(self):
  job,empty,current,scope=self.fixture(complete=True)
  self.assert_stops_before_any_send_or_current_reuse(current,job,scope)


if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
