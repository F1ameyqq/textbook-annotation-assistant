"""New synthetic pending-only flow; no old ROI, engine or platform is run."""
from pathlib import Path
import copy,sys,tempfile,unittest
from unittest.mock import patch
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.store import Store,Hold,digest
from annotation.customer import formula_batch
from annotation.customer.formula_roi_cache import KIND,MODEL_FILES,build_request

class FixtureStore(Store):
 def job(self,identity):return copy.deepcopy(self.fixture),'fresh-suffix-head'

class PendingOnly(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=FixtureStore(Path(self.tmp.name))
  self.store.fixture={'book_id':'973109','graph_ref':self.store.put({'synthetic':'graph'}),
   'evidence_ref':self.store.put({'synthetic':'evidence'}),'candidates':[{'key':'synthetic-candidate','printed_number':'51','platform_status':'NOT_RUN'}]}
  self.regions=[{'proposal_id':'synthetic-row-'+str(i),'candidate_key':'synthetic-candidate','zone':'answer','asset_id':'synthetic-page',
   'source_sha256':'1'*64,'bbox':[20+i*70,20,60+i*70,40],'uncertainty':'OBSERVED_MATH_ROW'} for i in range(3)]
  self.proposer=patch.object(formula_batch,'propose',side_effect=lambda *a,**k:{'regions':copy.deepcopy(self.regions)});self.proposer.start();self.addCleanup(self.proposer.stop)
  self.model={'backend':'rapid-latex-ocr','version':'0.0.9','files':[{'name':name,'bytes':1,'sha256':'2'*64} for name in sorted(MODEL_FILES)],
   'code_sha256':{'synthetic-worker':'3'*64},'runtime':{'synthetic':True},'configuration':{'synthetic':True}}
  self.updated=copy.deepcopy(self.model);self.updated['code_sha256']['synthetic-worker']='4'*64
  self.scope=formula_batch.plan(self.store,'synthetic-job','fresh-suffix-head')
  self.request=build_request({'book_id':'973109','asset_id':'synthetic-page','sha256':'1'*64,'width':600,'height':400},
    self.regions[0]['bbox'],b'new-synthetic-roi',bytes(40*20*3),self.model)
  self.store.begin(KIND,self.request['roi_key']);self.roi_ref=self.store.finish(KIND,self.request['roi_key'],'FAILED_NO_RETRY',
    {'request':self.request,'cache_key':self.request['cache_key'],'error':'synthetic retained failure'})
  self.batch_key=digest(self.scope['clear_regions']);self.store.begin('formula-batch:synthetic-job',self.batch_key)
  self.batch_ref=self.store.finish('formula-batch:synthetic-job',self.batch_key,'FAILED_NO_RETRY',
   {'schema':'CustomerFormulaBatchResult/v1','status':'FAILED_NO_RETRY','plan':self.scope,
    'items':[{'proposal_id':row['proposal_id'],'candidate_key':row['candidate_key'],
              'status':'FAILED_OR_NOT_COMPLETED' if index==0 else 'NOT_RUN'} for index,row in enumerate(self.scope['clear_regions'])]})
  self.settings={'runtime':{'formula_inference_activated':True}}
 def mock_result(self,*args,**kwargs):
  return {'new_worker_invocations':1,'proposal_id':args[4],'candidate_key':args[3],'synthetic':True}
 def count(self):
  with self.store.connect() as db:return db.execute('SELECT count(*) FROM operations').fetchone()[0]
 def test_updated_worker_only_calls_unrun_suffix_and_keeps_original_failures(self):
  scope=formula_batch.plan(self.store,'synthetic-job','fresh-suffix-head')
  self.assertEqual([r['proposal_id'] for r in scope['clear_regions']],['synthetic-row-1','synthetic-row-2'])
  failed=scope['manual_region_review'][0];self.assertTrue(failed['recognition_blocked']);self.assertTrue(failed['manual_resolution_required'])
  with patch('annotation.customer.formula_runtime.local_identity',return_value=(self.updated,None,None)),patch.object(formula_batch,'recognize_proposal',side_effect=self.mock_result) as call:
   result=formula_batch.run(self.store,'synthetic-job','fresh-suffix-head',self.settings,lambda value:'synthetic-record')
   self.assertEqual([args.args[4] for args in call.call_args_list],['synthetic-row-1','synthetic-row-2'])
   self.assertEqual(result['new_worker_invocations'],2);self.assertEqual(result['continuation_of_fixed_failed_batches'][0]['batch_output'],self.batch_ref)
   again=formula_batch.run(self.store,'synthetic-job','fresh-suffix-head',self.settings,lambda value:None)
   self.assertTrue(again['batch_reused']);self.assertEqual(call.call_count,2)
  self.assertEqual(self.store.operation(KIND,self.request['roi_key']),{'state':'FAILED_NO_RETRY','output':self.roi_ref})
  self.assertEqual(self.store.operation('formula-batch:synthetic-job',self.batch_key),{'state':'FAILED_NO_RETRY','output':self.batch_ref})
 def test_unchanged_worker_cannot_consume_next_region(self):
  before=self.count()
  with patch('annotation.customer.formula_runtime.local_identity',return_value=(self.model,None,None)),patch.object(formula_batch,'recognize_proposal',side_effect=AssertionError('No worker')):
   with self.assertRaisesRegex(Hold,'尚未更新'):formula_batch.run(self.store,'synthetic-job','fresh-suffix-head',self.settings,lambda value:None)
  self.assertEqual(self.count(),before)
 def test_unknown_unbound_attempt_stops_before_any_new_batch(self):
  self.store.begin(KIND,'f'*64);before=self.count()
  with patch.object(formula_batch,'recognize_proposal',side_effect=AssertionError('No worker')):
   with self.assertRaisesRegex(Hold,'范围未保留'):formula_batch.run(self.store,'synthetic-job','fresh-suffix-head',self.settings,lambda value:None)
  self.assertEqual(self.count(),before)
 def test_updated_program_cannot_expand_beyond_previous_not_run_set(self):
  extra=copy.deepcopy(self.regions[-1]);extra.update(proposal_id='new-outside-region',bbox=[300,20,340,40]);self.regions.append(extra)
  before=self.count()
  with patch('annotation.customer.formula_runtime.local_identity',return_value=(self.updated,None,None)),patch.object(formula_batch,'recognize_proposal',side_effect=AssertionError('No worker')):
   with self.assertRaisesRegex(Hold,'超出原批次'):formula_batch.run(self.store,'synthetic-job','fresh-suffix-head',self.settings,lambda value:None)
  self.assertEqual(self.count(),before)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
