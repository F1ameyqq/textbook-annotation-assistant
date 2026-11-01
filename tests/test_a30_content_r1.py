"""New ordinary-input R1 controls; no old OCR, graph, platform or model rerun."""
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.store import Store,Hold
from annotation.customer.prepare import prepare
from annotation.customer.review import CustomerReviewWorkspace

class ContentR1(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.store=Store(self.root/'state');self.q=self.root/'q.txt';self.a=self.root/'a.txt'
 def job(self,q,a):
  self.q.write_text(q,encoding='utf-8');self.a.write_text(a,encoding='utf-8')
  return prepare(self.store,book='825731',lesson='New ordinary R1 lesson',question_files=[self.q],answer_files=[self.a])
 def test_numbered_numeric_answer_at_new_page(self):
  job=self.job('21. 春季后是什么季节？\n22. 选择字母。\nA. A\nB. B\nC. C\nD. D\n\f23. 写出一周的天数。\n',
               '21. 夏季\n22. A\n\f23. 7\n')
  self.assertEqual([q['zones']['answer'] for q in job['candidates']],['夏季','A','7'])
  self.assertEqual(job['issues'],[]);self.assertEqual(job['status'],'PREPARED_OFFLINE')
 def test_numbered_english_answer_at_new_page(self):
  job=self.job('31. Name a colour.\n','31. Purple\n')
  self.assertEqual(job['candidates'][0]['zones']['answer'],'Purple');self.assertEqual(job['status'],'PREPARED_OFFLINE')
 def test_unassigned_source_can_be_bound_without_fabricated_frame(self):
  job=self.job('45. Name a colour.\n','Purple\n')
  ws=CustomerReviewWorkspace(self.store,job['id']);state=ws.state();q=job['candidates'][0]
  lines=state['customer']['unassigned_sources'];self.assertEqual(len(lines),1)
  self.assertEqual(q['zones']['answer'],'')
  request={'expected_head':state['head'],'answer_id':q['key'],'line_ids':[lines[0]['line_id']],'source_checked':True}
  state=ws.assign(request);updated,_=self.store.job(job['id'])
  self.assertEqual(updated['candidates'][0]['zones']['answer'],'Purple')
  self.assertEqual(updated['issues'],[]);self.assertEqual(state['customer']['unassigned_sources'],[])
  self.assertEqual(updated['graph_ref'],job['graph_ref'])
  frame=updated['candidates'][0]['frames'][-1]
  self.assertEqual(frame['source_sha256'],job['pages'][1]['raw_sha256'])
  self.assertEqual(frame['bbox'],[int(v) for v in lines[0]['bbox']])
  state=ws.confirm({'expected_head':state['head'],'answer_id':q['key'],'source_checked':True,'content_checked':True})
  self.assertEqual(state['customer']['job_status'],'PREPARED_OFFLINE')
 def test_edit_rechecks_choice_structure(self):
  job=self.job('1. Select one.\nA. Red\nB. Blue\nC. Green\nD. Gold\n','1. E\n')
  q=job['candidates'][0];self.assertIn('CHOICE_OR_ANSWER_STRUCTURE',q['issues'])
  ws=CustomerReviewWorkspace(self.store,job['id']);state=ws.state()
  state=ws.save({'expected_head':state['head'],'answer_id':q['key'],'changes':[{'key':q['key']+':answer','format':'plain','text':'B'}]})
  edited,_=self.store.job(job['id']);self.assertNotIn('CHOICE_OR_ANSWER_STRUCTURE',edited['candidates'][0]['issues'])
  state=ws.confirm({'expected_head':state['head'],'answer_id':q['key'],'source_checked':True,'content_checked':True})
  self.assertEqual(state['customer']['job_status'],'PREPARED_OFFLINE')
 def test_typed_answer_without_source_does_not_clear_missing_binding(self):
  job=self.job('1. Name a colour.\n','Purple\n');q=job['candidates'][0]
  ws=CustomerReviewWorkspace(self.store,job['id']);state=ws.state()
  state=ws.save({'expected_head':state['head'],'answer_id':q['key'],'changes':[{'key':q['key']+':answer','format':'plain','text':'Purple'}]})
  with self.assertRaises(Hold):ws.confirm({'expected_head':state['head'],'answer_id':q['key'],'source_checked':True,'content_checked':True})
  self.assertTrue(state['customer']['unassigned_sources'])
 def test_source_assignment_through_local_review_http(self):
  import threading,http.client,json
  from annotation.recognition.content_review_server import make_server
  job=self.job('46. Name a colour.\n','Violet\n');q=job['candidates'][0]
  server=make_server(CustomerReviewWorkspace(self.store,job['id']))
  thread=threading.Thread(target=server.serve_forever);thread.start()
  try:
   port=server.server_address[1];connection=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
   connection.request('GET','/api/state');response=connection.getresponse();self.assertEqual(response.status,200)
   value=json.loads(response.read());state=value.get('state',value)
   body={'expected_head':state['head'],'answer_id':q['key'],'source_checked':True,
         'line_ids':[state['customer']['unassigned_sources'][0]['line_id']]}
   connection.request('POST','/api/assign',json.dumps(body),headers={'Content-Type':'application/json',
         'Origin':'http://127.0.0.1:'+str(port),'X-Review-Token':state['csrf_token']})
   response=connection.getresponse();payload=json.loads(response.read());self.assertEqual(response.status,200,payload)
   self.assertEqual(payload['state']['answers'][0]['text'],'Violet');self.assertEqual(server.request_counts['POST /api/assign'],1)
   connection.close()
  finally:server.shutdown();server.server_close();thread.join(timeout=5)
  self.assertFalse(thread.is_alive())

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
