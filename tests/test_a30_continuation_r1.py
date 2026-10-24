"""New ordinary section discovery orchestration cases, all network substituted."""
from pathlib import Path
import copy,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.store import Store,Hold,digest
from annotation.customer.platform_source import prepare_section

class ContinuationR1(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.book='937126';flat={'source':{'code':0,'data':{'total_pages':90}}}
  self.value={'plan':{'book_id':self.book,'question_pages':[3],'answer_pages':[80]},'pages':[
   {'viewer_page':3,'role':'question','asset_id':'q3'},{'viewer_page':80,'role':'answer','asset_id':'a80'}],
   'snapshot_ref':self.store.put(flat)}
 def prepared(self,store,value,**kwargs):
  identity=digest(value['pages']);scope=[{'page':p,'continuation_at_end':p['role']=='question' and p['viewer_page']<4} for p in value['pages']]
  job={'id':identity,'book_id':self.book,'pages':value['pages'],'status':'NEEDS_REVIEW','platform_status':'NOT_RUN',
   'metrics':{'review_actions':0},'section_scope_ref':store.put(scope)}
  with store.connect() as db:row=db.execute('SELECT head FROM jobs WHERE id=?',(identity,)).fetchone()
  store.save_job(job,row[0] if row else None);return job
 def test_adjacent_cached_page_closes_question_without_reopening_answer(self):
  self.store.record_read('official-page',digest([self.book,4]),{'page':{'viewer_page':4,'asset_id':'q4','raw_sha256':'s4'},'page_metadata':{'observed':'new synthetic'}})
  with patch('annotation.customer.platform_source.prepare_acquired',side_effect=self.prepared):
   result=prepare_section(self.store,{},self.value,transport_factory=lambda *a:(_ for _ in ()).throw(AssertionError('cache first')))
  self.assertTrue(result['source_scope_complete']);self.assertEqual(result['remaining_source_roles'],[])
  self.assertEqual([p['viewer_page'] for p in result['pages']],[3,4,80]);self.assertEqual(len(result['source_discovery']['additional_pages']),1)
 def test_one_failed_adjacent_read_has_no_successors_or_retry(self):
  calls=[]
  class Failed:
   out='synthetic-failed-read'
   def _capture(self,**kwargs):calls.append(kwargs);raise TimeoutError('new synthetic one-shot')
  with patch('annotation.customer.platform_source.prepare_acquired',side_effect=self.prepared):
   with self.assertRaises(TimeoutError):prepare_section(self.store,{},self.value,transport_factory=lambda *a:Failed())
   with self.assertRaises(Hold):prepare_section(self.store,{},self.value,transport_factory=lambda *a:Failed())
  self.assertEqual(calls,[{'pages':[4]}]);self.assertEqual(self.store.operation('official-page',digest([self.book,4]))['state'],'FAILED_NO_RETRY')

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
