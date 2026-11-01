"""New synthetic guard controls: no model import, model files or source ROI."""
from pathlib import Path
import importlib.util,sys,types,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('synthetic_formula_worker',ROOT/'tools/customer_formula_worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)

class WorkerGuard(unittest.TestCase):
 def test_local_hostname_is_only_readonly_socket_namespace_exception(self):
  state={'phase':'LOCAL_BACKEND_IMPORT'};guard=worker.LocalOnlyGuard(state)
  guard.audit('socket.gethostname',());guard.require_clean()
  self.assertEqual(guard.record['local_hostname_reads'],1);self.assertEqual(guard.record['blocked_attempts'],0)
  self.assertNotIn('rapid_latex_ocr',sys.modules)
 def test_real_network_and_child_event_classes_remain_denied_with_safe_metadata(self):
  state={'phase':'MODEL_INITIALIZATION'};guard=worker.LocalOnlyGuard(state)
  events=['socket.__new__','socket.bind','socket.connect','socket.getaddrinfo','socket.gethostbyname',
          'socket.gethostbyaddr','socket.sendto','subprocess.Popen','os.system','os.posix_spawn']
  for event in events:
   with self.assertRaisesRegex(RuntimeError,'FORBIDDEN'):guard.audit(event,('SYNTHETIC_SECRET_NOT_TO_RETAIN',))
  self.assertEqual(guard.record['blocked_attempts'],len(events))
  self.assertEqual(guard.record['blocked_events'],[{'event':event,'phase':'MODEL_INITIALIZATION'} for event in events])
  self.assertNotIn('SYNTHETIC_SECRET',repr(guard.record))
  with self.assertRaisesRegex(RuntimeError,'RETAINED'):guard.require_clean()
 def test_import_probe_is_disabled_only_inside_scope_and_restored_after_failure(self):
  fake_socket=types.SimpleNamespace(has_ipv6=True);guard=worker.LocalOnlyGuard({'phase':'LOCAL_BACKEND_IMPORT'})
  with patch.object(worker,'socket',fake_socket):
   with self.assertRaisesRegex(ValueError,'synthetic import failure'):
    with guard.local_imports():
     self.assertFalse(fake_socket.has_ipv6)
     with self.assertRaisesRegex(RuntimeError,'FORBIDDEN'):guard.audit('socket.__new__',())
     raise ValueError('synthetic import failure')
   self.assertTrue(fake_socket.has_ipv6)
  self.assertTrue(guard.record['ipv6_flag_restored'])
 def test_failure_keeps_phase_and_partial_initialization_distinct_from_inference(self):
  state={'phase':'MODEL_INITIALIZATION','model_initialization':'STARTED_NOT_CONFIRMED_COMPLETE',
         'engine_calls_started':0,'engine_calls_completed':0,'network':{'blocked_attempts':1}}
  with patch.object(worker,'WORKER_STATE',state):report=worker.failure_record(RuntimeError('synthetic blocked event'))
  self.assertEqual(report['phase'],'MODEL_INITIALIZATION');self.assertEqual(report['engine_calls_started'],0)
  self.assertEqual(report['model_initialization'],'STARTED_NOT_CONFIRMED_COMPLETE');self.assertEqual(report['status'],'FAILED_NO_RETRY')

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
