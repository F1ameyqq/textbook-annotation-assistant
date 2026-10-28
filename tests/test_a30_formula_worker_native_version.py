"""New native-version fallback checks; no real dependency/model import."""
from pathlib import Path
import importlib.util,sys,types,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('version_fallback_formula_worker',ROOT/'tools/customer_formula_worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)

class NativeVersionFallback(unittest.TestCase):
 def test_builtin_fallback_preserves_arguments_and_restores_after_failure(self):
  calls=[]
  def original(*args):calls.append(args);raise AssertionError('shell version probe must not run')
  fake=types.SimpleNamespace(_syscmd_ver=original)
  guard=worker.LocalOnlyGuard({'phase':'LOCAL_BACKEND_IMPORT'})
  with patch.object(worker,'platform',fake),patch.object(worker,'sys',types.SimpleNamespace(platform='win32')):
   with self.assertRaisesRegex(ValueError,'synthetic import stop'):
    with guard.local_imports():
     self.assertEqual(fake._syscmd_ver(),('','',''))
     self.assertEqual(fake._syscmd_ver('win32','release','version'),('win32','release','version'))
     self.assertFalse(worker.socket.has_ipv6)
     with self.assertRaisesRegex(RuntimeError,'FORBIDDEN'):guard.audit('subprocess.Popen',())
     raise ValueError('synthetic import stop')
   self.assertIs(fake._syscmd_ver,original)
  self.assertEqual(calls,[]);self.assertTrue(guard.record['windows_version_function_restored'])
  self.assertEqual(guard.record['blocked_events'],[{'event':'subprocess.Popen','phase':'LOCAL_BACKEND_IMPORT'}])
 def test_non_windows_does_not_replace_version_resolver(self):
  resolver=object();fake=types.SimpleNamespace(_syscmd_ver=resolver)
  guard=worker.LocalOnlyGuard({'phase':'LOCAL_BACKEND_IMPORT'})
  with patch.object(worker,'platform',fake),patch.object(worker,'sys',types.SimpleNamespace(platform='linux')):
   with guard.local_imports():self.assertIs(fake._syscmd_ver,resolver)
  self.assertNotIn('windows_version_probe',guard.record)
  self.assertNotIn('rapid_latex_ocr',sys.modules)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
