"""One new integrated variant: same node/info/geometry, replaced rect ID."""
from pathlib import Path
import sys,copy,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(ROOT/'src'))
import test_a30_execution_scope_r1 as fixtures
from annotation.customer.production import _execution_plan

class RectIdentityR1(unittest.TestCase):
 setUp=fixtures.ExecutionScopeR1.setUp
 image_job=fixtures.ExecutionScopeR1.image_job
 fixture=fixtures.ExecutionScopeR1.fixture
 assert_stops_before_any_send_or_current_reuse=fixtures.ExecutionScopeR1.assert_stops_before_any_send_or_current_reuse
 def test_same_identity_geometry_but_replaced_rect_is_held_before_any_send(self):
  job,empty,current,scope=self.fixture();candidate=job['candidates'][1]
  expected=scope['selection'][1]['expected_rect_ids_by_zone']
  plan=_execution_plan(current,candidate,job['lesson'],scope)
  self.assertEqual({r['zone']:r['rect_ids'] for r in plan['payload']['ocr_submissions']},expected)
  changed=copy.deepcopy(current)
  for frame in changed['frames']['data']:
   if frame['type']=='question':frame['rect_id']='replacement-same-geometry'
  for frame in changed['questions']['server-node-704']['annotations']['data']:
   if frame['type']=='question':frame['rect_id']='replacement-same-geometry'
  self.assert_stops_before_any_send_or_current_reuse(changed,job,scope)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
