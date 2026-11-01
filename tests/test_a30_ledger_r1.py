from pathlib import Path
import copy,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.store import Store,encoded,digest,byte_hash,Hold
from annotation.customer.legacy_ledger import import_closure,guard

def fixture():
 target={'book_id':'825734','node_id':'node','info_id':'info','question_order':1,'lesson_directory_id':'other-lesson'}
 zones={z:{'code':0,'data':{'success':True,'ocr_result':'text','rect_ids':['r']}} for z in ['question','choice','answer','analysis','knowledge_point']}
 plan={'ledger_key':'old-key','target':target,'expected':{'zones':zones}};plan['plan_sha256']=digest(plan);plan_raw=encoded(plan)
 claim={'ledger_key':'old-key','plan_sha256':plan['plan_sha256'],'run_id':'writer','native_body_sha256':'body','target':target}
 receipt=encoded({'code':0,'data':{'success':True}})
 writer={'run_id':'writer','plan_sha256':plan['plan_sha256'],'plan_file_sha256':byte_hash(plan_raw),'native_body_sha256':'body',
         'receipt_sha256':byte_hash(receipt),'post_attempts':1,'post_layers':{'context':1,'native':1}}
 captures={'q1_info':encoded({'data':{'id':'info','file_id':'825734'}}),'q1_annotations':encoded({'data':[]}),**{'q1_'+z:encoded(v) for z,v in zones.items()}}
 reader={'run_id':'reader','status':'NATIVE_GETS_CAPTURED','save_attempts':0,'release':{'context_runtime_release_confirmed':True},
        'captures':{k:{'sha256':byte_hash(v),'status':200,'request_counts':{'context':1,'native':1}} for k,v in captures.items()}}
 closure={'status':'ACCEPTED','writer_run':'writer','reader_run':'reader','checks':{'all':True},'target':target,
          'comparison':{'match':True,'differences':[],'plan_sha256':plan['plan_sha256']}}
 return {'claim':encoded(claim),'plan':plan_raw,'writer':encoded(writer),'receipt':receipt,'closure':encoded(closure),'reader':encoded(reader),'captures':captures}

class LedgerR1(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.store=Store(self.root/'state');self.ledger=self.root/'ledger';self.ledger.mkdir()
 def test_closed_other_lesson_allows_same_book_without_ledger_mutation(self):
  raw=fixture();path=self.ledger/'old-key.json';path.write_bytes(raw['claim']);before=path.read_bytes()
  with self.assertRaises(Hold):guard(self.store,self.ledger,'825734')
  import_closure(self.store,raw);closed=guard(self.store,self.ledger,'825734')
  self.assertEqual(len(closed),1);self.assertEqual(path.read_bytes(),before)
  self.assertFalse(closed[0]['revision_predecessor_eligible'])
 def test_new_unknown_claim_elsewhere_blocks_whole_book(self):
  raw=fixture();(self.ledger/'old-key.json').write_bytes(raw['claim']);import_closure(self.store,raw)
  claim=json.loads(raw['claim']);claim['run_id']='unknown';claim['target']['lesson_directory_id']='third-lesson'
  (self.ledger/'another.json').write_bytes(encoded(claim))
  with self.assertRaises(Hold):guard(self.store,self.ledger,'825734')
 def test_tampered_raw_reader_cannot_close_old_intent(self):
  raw=fixture();raw['captures']['q1_answer']=encoded({'data':{'success':True,'ocr_result':'different'}})
  with self.assertRaises(Hold):import_closure(self.store,raw)
  self.assertIsNone(self.store.operation('legacy-closure:825734',byte_hash(raw['claim'])))

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
