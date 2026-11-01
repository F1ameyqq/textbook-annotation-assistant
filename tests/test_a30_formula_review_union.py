"""New synthetic customer formula-route integration; no model or platform."""
import copy
import http.client
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.store import Store,Hold,byte_hash,encoded
from annotation.customer.prepare import prepare
from annotation.customer.review import CustomerReviewWorkspace
from annotation.customer.formula_regions import recognize_proposal


class FormulaReviewUnion(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  from PIL import Image,ImageDraw
  files=[]
  for role in ('question','answer'):
   path=self.root/(role+'.png');image=Image.new('RGB',(510,360),'white')
   ImageDraw.Draw(image).text((25,25),'NEW UNION '+role+' '+self.id(),fill='black');image.save(path);files.append(path)
  self.store=Store(self.root/'workspace')
  def lines(store,page,book,**kwargs):
   text='1. 计算 a+b=7 时的关系。' if page['role']=='question' else 'x=4+3'
   return [{'text':text,'bbox':[25,25,440,55],'score':.99}],'SYNTHETIC_ONLY_NO_MODEL'
  with patch('annotation.customer.prepare.ocr_page',side_effect=lines):
   self.job=prepare(self.store,book='872936',lesson='New formula review union',question_files=[files[0]],answer_files=[files[1]],question_first_page=31,answer_first_page=92)
  self.ws=CustomerReviewWorkspace(self.store,self.job['id'],settings_provider=lambda:{'runtime':{'formula_inference_activated':False}})
  self.state=self.ws.state();self.key=self.job['candidates'][0]['key']

 def test_assigned_answer_enters_source_and_formula_projection_without_graph_rewrite(self):
  lines=self.state['customer']['unassigned_sources'];self.assertEqual(len(lines),1)
  state=self.ws.assign({'expected_head':self.state['head'],'answer_id':self.key,'source_checked':True,'line_ids':[lines[0]['line_id']]})
  answer=state['answers'][0]
  projected=next(zone for zone in answer['source_projection']['zones'] if zone['zone']=='answer')
  self.assertEqual(projected['segments'][0]['source_text'],'x=4+3')
  self.assertTrue(any(region['zone']=='answer' for region in answer['formula_regions']['regions']))
  self.assertEqual(self.store.job(self.job['id'])[0]['graph_ref'],self.job['graph_ref'])
  changed=copy.deepcopy(self.store.job(self.job['id'])[0]['candidates'][0]);changed['manual_answer_binding']['raw_texts']=['invented']
  from annotation.customer.source_review_projection import project_candidate
  with self.assertRaisesRegex(ValueError,'MANUAL_ANSWER_SOURCE_CHANGED'):
   project_candidate(changed,self.store.get(self.job['graph_ref']),self.store.get(self.job['evidence_ref']))

 def test_formula_http_records_candidate_without_editing_or_confirming(self):
  from annotation.recognition.content_review_server import make_server
  region=self.state['answers'][0]['formula_regions']['regions'][0]
  value={'candidate':{'raw_latex':'a+b=7','source_bbox':region['bbox'],'status':'TEX_CANDIDATE_PENDING_REVIEW','content_approved':False},
         'operation_ref':'e'*64,'reused':False,'new_worker_invocations':1}
  server=make_server(self.ws);thread=threading.Thread(target=server.serve_forever);thread.start()
  try:
   port=server.server_address[1];connection=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
   connection.request('GET','/api/state');response=connection.getresponse();state=json.loads(response.read())
   body={'expected_head':state['head'],'answer_id':self.key,'proposal_id':region['proposal_id'],
         'source_checked':True,'adjusted_bbox':region['bbox'],'author':{'kind':'SYNTHETIC_TEST','id':'new-union-control'}}
   with patch('annotation.customer.formula_runtime.obtain_region',return_value=value) as worker:
    connection.request('POST','/api/formula',json.dumps(body),headers={'Content-Type':'application/json',
      'Origin':'http://127.0.0.1:'+str(port),'X-Review-Token':state['csrf_token']})
    response=connection.getresponse();payload=json.loads(response.read());self.assertEqual(response.status,200,payload)
    self.assertEqual(worker.call_count,1)
   self.assertEqual(payload['state']['head'],state['head'])
   observations=payload['state']['answers'][0]['formula_observations'];self.assertEqual(len(observations),1)
   self.assertEqual(observations[0]['candidate']['raw_latex'],'a+b=7');self.assertFalse(observations[0]['content_approved'])
   self.assertEqual(self.store.job(self.job['id'])[0]['candidates'],self.job['candidates']);connection.close()
  finally:server.shutdown();server.server_close();thread.join(timeout=5)
  self.assertFalse(thread.is_alive())

 def test_unchecked_stale_or_outside_region_never_reaches_worker(self):
  region=self.state['answers'][0]['formula_regions']['regions'][0]
  with patch('annotation.customer.formula_runtime.obtain_region',side_effect=AssertionError('worker must not run')):
   for head,checked,bbox in [('0'*64,True,None),(self.state['head'],False,None),(self.state['head'],True,[0,0,510,360])]:
    with self.assertRaises(Hold):recognize_proposal(self.store,self.job['id'],head,self.key,region['proposal_id'],{},source_checked=checked,adjusted_bbox=bbox)

 def test_inactive_runtime_does_not_create_spent_intent(self):
  from annotation.customer.formula_runtime import obtain_region
  request={'roi_key':'c'*64}
  with patch('annotation.customer.formula_runtime.request_for_region',return_value=(request,b'fake',Path('fake'),Path('fake'))):
   with self.assertRaisesRegex(Hold,'尚未启用'):obtain_region(self.store,{'raw_sha256':'d'*64},'872936',[1,2,3,4],{'runtime':{'formula_inference_activated':False}},allow_first_local_call=True)
  self.assertIsNone(self.store.operation('customer-formula-roi-v1','c'*64))

 def test_packaged_runtime_is_applied_only_in_customer_gui_memory(self):
  spec=importlib.util.spec_from_file_location('customer_union_entry',ROOT/'tools/customer.py');entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
  package=self.root/'package';(package/'runtime').mkdir(parents=True)
  python=self.root/'formula-runtime.bin';python.write_bytes(b'new synthetic runtime identity only')
  installed={'formula_python':{'path':str(python),'sha256':byte_hash(python.read_bytes())},'formula_inference_activated':True}
  (package/'runtime/customer-runtimes.json').write_bytes(encoded(installed))
  old={'expires_at':'spent-original-window','authorization_reference':'retained-original-authority','runtime':{'formula_inference_activated':False}}
  settings_path=self.store.root/'settings.json';settings_path.write_bytes(encoded(old));before=settings_path.read_bytes()
  with patch.object(entry,'ROOT',package):
   self.assertEqual(entry.settings(self.store),old);self.store.customer_start_mode=True
   current=entry.settings(self.store);self.assertEqual(current['runtime'],installed);self.assertNotIn('expires_at',current)
   self.assertEqual(settings_path.read_bytes(),before)
   python.write_bytes(b'changed-runtime')
   with self.assertRaises(Hold):entry.settings(self.store)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
