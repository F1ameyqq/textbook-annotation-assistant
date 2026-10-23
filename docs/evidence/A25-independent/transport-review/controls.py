"""Independent fake-socket and batch-consumption controls for this delta."""
import copy,importlib.util,json,os,sys,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
ROOT=Path(os.environ['A25_TRANSPORT_SNAPSHOT']);sys.path.insert(0,str(ROOT/'src'))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
t=load('transport_fixture',ROOT/'tests/test_a25_transport.py');b=load('batch_fixture',ROOT/'tests/test_a25_batch.py')
from annotation.runtime.usense_live import core,transport,writer,insertion_writer,finalize_writer

class Controls(unittest.TestCase):
 def setUp(self):self.fx=t.TransportTests('test_proxy_probe_uses_one_fixed_connect_and_same_browser_proxy');self.fx.setUp()
 def tearDown(self):self.fx.tearDown()
 def test_01_header_read_stops_before_tunnel_tls_bytes(self):
  f=self.fx;sock=t.Socket(b'HTTP/1.1 200 OK\r\nX: value\r\n\r\nTLS_UNREAD');binding=f.binding();ctx=f.secure()
  with f.positive_pin(binding),patch.object(transport.socket,'create_connection',return_value=sock) as connect,patch.object(transport.ssl,'SSLContext',return_value=ctx):args=transport.launch_arguments(binding)
  self.assertEqual(bytes(sock.header),b'TLS_UNREAD');self.assertEqual(len(sock.sent),1);connect.assert_called_once_with(('127.0.0.1',7897),timeout=10);self.assertEqual(args[0],'--proxy-server=http://127.0.0.1:7897');ctx.wrap_socket.assert_called_once_with(sock,server_hostname='www.usense.com')
 def test_02_deadline_exhaustion_in_header_never_reconnects_or_starts_tls(self):
  f=self.fx;sock=t.Socket();ticks=iter([0,1,2,11])
  with patch.object(transport.time,'monotonic',side_effect=lambda:next(ticks)),patch.object(transport.socket,'create_connection',return_value=sock) as connect,patch.object(transport.ssl,'SSLContext') as tls,self.assertRaisesRegex(core.BindingError,'TLS_PROBE_DEADLINE'):transport.launch_arguments(f.binding())
  connect.assert_called_once();tls.assert_not_called();self.assertTrue(sock.closed);self.assertIn(b'TLS_PROBE_DEADLINE',(f.output/'tls-probe-error.traceback.txt').read_bytes());self.assertEqual(json.loads((f.output/'tls-probe.json').read_bytes())['status'],'FAILED_NO_RETRY')
 def test_03_oversized_header_stops_with_one_connect(self):
  f=self.fx;sock=t.Socket(b'HTTP/1.1 200 OK\r\nX: '+b'a'*8192)
  with patch.object(transport.socket,'create_connection',return_value=sock) as connect,patch.object(transport.ssl,'SSLContext') as tls,self.assertRaisesRegex(core.BindingError,'PROXY_CONNECT_HEADER_TOO_LARGE'):transport.launch_arguments(f.binding())
  connect.assert_called_once();tls.assert_not_called();self.assertTrue(sock.closed);self.assertEqual(len(sock.sent),1)
 def test_04_connect_error_keeps_exact_exception_without_second_route(self):
  f=self.fx
  with patch.object(transport.socket,'create_connection',side_effect=TimeoutError('independent exact connect timeout')) as connect,patch.object(transport.ssl,'SSLContext') as tls,self.assertRaisesRegex(TimeoutError,'independent exact connect timeout'):transport.launch_arguments(f.binding())
  connect.assert_called_once();tls.assert_not_called();v=json.loads((f.output/'tls-probe-error.json').read_bytes());self.assertEqual(v['phase'],'CONNECT');self.assertIn(b'independent exact connect timeout',(f.output/v['traceback_file']).read_bytes());self.assertFalse((f.output/'proxy-connect-request.raw').exists())
 def test_05_all_writer_variants_share_transport_helper(self):
  f=self.fx;binding=f.binding();sentinel=['synthetic-same-transport']
  for m in [writer,insertion_writer,finalize_writer]:self.assertIs(m.tls_launch_arguments,core.tls_launch_arguments)
  with patch.object(transport,'launch_arguments',return_value=sentinel) as shared:
   for helper in [core.tls_launch_arguments,writer.tls_launch_arguments,insertion_writer.tls_launch_arguments,finalize_writer.tls_launch_arguments]:self.assertIs(helper(binding),sentinel)
  self.assertEqual(shared.call_count,4)
 def test_06_each_writer_and_reader_configuration_receives_same_proxy(self):
  f=b.A25BatchTests('test_proxy_transport_is_forwarded_to_writer_configuration');f.setUp()
  try:
   f.manifest['targets']=f.manifest['targets'][:2];summarypath=f.baseline/'capture-summary.json';summary=json.loads(summarypath.read_bytes());summary['transport']={'mode':'HTTP_CONNECT_PROXY','proxy_server':'http://127.0.0.1:7897'};summarypath.write_bytes(b.raw(summary));f.manifest['baseline']['capture_summary_sha256']=b.sha(summarypath.read_bytes());prepared=f.prepare();out=f.root/'two-target-proxy-chain';out.mkdir();configs={};calls=[];clock=datetime(2026,10,23,tzinfo=timezone.utc)
   def child(args,record):
    nonlocal clock
    calls.append(args[0]);clock+=timedelta(seconds=1);started=clock.isoformat();clock+=timedelta(seconds=1);finished=clock.isoformat()
    if args[0]=='configure':
     self.assertEqual(args[args.index('--proxy-server')+1],'http://127.0.0.1:7897');configs[str(args[args.index('--config')+1])]=args[args.index('--orders')+1];return {'exit_code':0,'result':{'sha256':'a'*64}}
    q=configs[str(args[args.index('--config')+1])];item=next(x for x in prepared['targets'] if x['target']['question_order']==q);plan=item['plan'];rid='synthetic-'+args[0].strip('-')+'-'+str(q)
    if args[0]=='--writer':
     (f.ledger/(plan['ledger_key']+'.json')).write_bytes(b.raw({'synthetic':True}));result={'status':'RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK','run_id':rid,'post_attempts':1,'intent_key':plan['ledger_key'],'release':{'context_runtime_release_confirmed':True}}
    else:
     rd=out/rid;rd.mkdir();after=plan['expected'];values={'directory':after['directory'],'frames':after['frames'],f'q{q}_annotations':after['annotations'],f'q{q}_info':after['info'],**{f'q{q}_{z}':v for z,v in after['zones'].items()},**{n:f.native[n] for n in ('source','page_12','page_173')}}
     for name,value in values.items():(rd/(name+'.json')).write_bytes(b.raw(value))
     result={'status':'NATIVE_GETS_CAPTURED','run_id':rid,'save_attempts':0,'release':{'context_runtime_release_confirmed':True},'captures':{n:{'observed_at':finished} for n in values}}
    return {'exit_code':0,'result':result,'pid':len(calls),'started_at':started,'finished_at':finished}
   result=b.entry.execute(prepared,out,f.baseline,f.profile,'SYNTHETIC_ONLY','SYNTHETIC_ONLY',child,'http://127.0.0.1:7897');self.assertEqual(result['status'],'ALL_ACCEPTED',result);self.assertEqual(calls,['configure','--writer','configure','capture']*2)
  finally:f.tearDown()
if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
