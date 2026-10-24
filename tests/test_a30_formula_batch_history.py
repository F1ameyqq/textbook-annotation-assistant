"""New finite batch and retained-region controls; synthetic workers only."""
from pathlib import Path
import copy,json,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.store import Store,Hold,encoded,byte_hash
from annotation.customer import formula_batch,formula_history

class FixtureStore(Store):
 def job(self,identity):return copy.deepcopy(self.fixture),'fixed-head'

class FormulaBatchHistory(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.store=FixtureStore(self.root/'workspace');graph=self.store.put({'new_graph':self.id()});evidence=self.store.put({'new_evidence':self.id()})
  self.store.fixture={'book_id':'973188','graph_ref':graph,'evidence_ref':evidence,'candidates':[
   {'key':'candidate-new','printed_number':'37','platform_status':'NOT_RUN'},
   {'key':'candidate-completed','printed_number':'38','platform_status':'REUSED_ACCEPTED'}]}
  self.regions=[{'proposal_id':'r'+str(i),'zone':'answer','asset_id':'synthetic-source','source_sha256':'b'*64,
     'bbox':[10+i*20,20,20+i*20,35],'uncertainty':'OBSERVED_MATH_ROW' if i<3 else 'MIXED_TEXT_COARSE_REGION'} for i in range(4)]
  self.enabled={'runtime':{'formula_inference_activated':True}}
  self.propose=patch.object(formula_batch,'propose',return_value={'regions':self.regions});self.propose.start();self.addCleanup(self.propose.stop)
 def result(self,*args,**kwargs):
  return {'candidate_key':args[3],'proposal_id':args[4],'head':args[2],
          'candidate':{'raw_latex':'synthetic','content_approved':False},'new_worker_invocations':1,'reused':False,'operation_ref':'e'*64}
 def test_one_batch_prepares_clear_rows_and_leaves_mixed_and_completed(self):
  with patch.object(formula_batch,'recognize_proposal',side_effect=self.result) as worker:
   report=formula_batch.run(self.store,'new-job','fixed-head',self.enabled,lambda result:'retained-'+result['proposal_id'])
   self.assertEqual(worker.call_count,3);self.assertEqual(report['new_worker_invocations'],3)
   self.assertEqual(len(report['plan']['manual_region_review']),1);self.assertFalse(report['content_approved'])
   reused=formula_batch.run(self.store,'new-job','fixed-head',self.enabled,lambda result:None)
   self.assertTrue(reused['batch_reused']);self.assertEqual(worker.call_count,3);self.assertEqual(reused['new_worker_invocations'],0)
 def test_first_failure_retains_suffix_not_run_and_blocks_second_batch(self):
  calls=[]
  def worker(*args,**kwargs):
   calls.append(args[4])
   if len(calls)==2:raise Hold('new synthetic first failure')
   return self.result(*args,**kwargs)
  with patch.object(formula_batch,'recognize_proposal',side_effect=worker):
   with self.assertRaisesRegex(Hold,'synthetic first'):formula_batch.run(self.store,'new-job','fixed-head',self.enabled,lambda result:'one-record')
   with self.assertRaises(Hold):formula_batch.run(self.store,'new-job','fixed-head',self.enabled,lambda result:'no-new-record')
  self.assertEqual(calls,['r0','r1'])
  with self.store.connect() as db:state,ref=db.execute('SELECT state,output FROM operations WHERE kind=?',('formula-batch:new-job',)).fetchone()
  self.assertEqual(state,'FAILED_NO_RETRY');self.assertEqual([r['status'] for r in self.store.get(ref)['items']],
    ['CANDIDATE_RETAINED_PENDING_REVIEW','FAILED_OR_NOT_COMPLETED','NOT_RUN'])
 def test_batch_unactivated_has_no_durable_attempt(self):
  with self.assertRaisesRegex(Hold,'尚未启用'):formula_batch.run(self.store,'new-job','fixed-head',{'runtime':{'formula_inference_activated':False}},lambda result:None)
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM operations').fetchone()[0],0)
 def test_consumed_ordinary_ocr_blocks_overlap_without_becoming_tex_cache(self):
  package=self.root/'package';directory=package/'runtime/customer-formula-history/973188';directory.mkdir(parents=True)
  raw=b'new synthetic finite history origin';(directory/'origin.json').write_bytes(raw)
  record={'source_sha256':'a'*64,'bbox':[20,30,60,70],'consumed':True,'tex_cache':False,
    'original_status':'FAILED_NO_RETRY','evidence_sha256':[byte_hash(raw)]}
  registry={'schema':'CustomerConsumedSourceRegions/v1','book_id':'973188','regions':[record],
    'evidence_files':[{'filename':'origin.json','bytes':len(raw),'sha256':byte_hash(raw)}]}
  (directory/'registry.json').write_bytes(encoded(registry))
  with patch.object(formula_history,'APP',package):
   with self.assertRaisesRegex(Hold,'重叠'):formula_history.guard(self.store,'973188','a'*64,[55,65,80,90])
   formula_history.guard(self.store,'973188','a'*64,[61,30,80,70])
   with self.store.connect() as db:
    rows=db.execute('SELECT kind,state,output FROM operations').fetchall()
   self.assertEqual(len(rows),1);self.assertEqual(rows[0][0],'consumed-source-region:973188')
   self.assertEqual(self.store.get(rows[0][2]),record);self.assertFalse(self.store.get(rows[0][2])['tex_cache'])
   (directory/'origin.json').write_bytes(b'changed')
   with self.assertRaisesRegex(Hold,'已改变'):formula_history.guard(self.store,'973188','a'*64,[61,30,80,70])

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
