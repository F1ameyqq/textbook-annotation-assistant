"""Only the new transport tests and two new batch-transport cases."""
import importlib.util,os,unittest
from pathlib import Path
ROOT=Path(os.environ['A25_TRANSPORT_SNAPSHOT'])
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
if __name__=='__main__':
 t=load('transport_delta_author',ROOT/'tests/test_a25_transport.py');b=load('batch_delta_author',ROOT/'tests/test_a25_batch.py')
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(t.TransportTests)
 for name in ['test_proxy_transport_is_forwarded_to_writer_configuration','test_changed_transport_stops_before_first_configuration']:suite.addTest(b.A25BatchTests(name))
 result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
 raise SystemExit(0 if result.wasSuccessful() else 1)
