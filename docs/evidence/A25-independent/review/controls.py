"""Independent A25 controls using synthetic fixture data only."""
import copy, importlib.util, json, os, subprocess, sys, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(os.environ['A25_REVIEW_SNAPSHOT'])
OUT=Path(os.environ['A25_REVIEW_RUNS'])
sys.path.insert(0,str(ROOT/'src'))
spec=importlib.util.spec_from_file_location('author_fixture',ROOT/'tests/test_a25_batch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Controls(unittest.TestCase):
 def setUp(self):
  self.fx=m.A25BatchTests('test_reordered_lesson_two_targets_use_stable_ids_and_actual_parent');self.fx.setUp()
 def tearDown(self):self.fx.tearDown()
 def run_chain(self,mode):
  fx=self.fx;prepared=fx.prepare();out=fx.root/'independent-chain';out.mkdir();calls=[];configs={};clock=datetime(2026,10,23,tzinfo=timezone.utc);wpid={}
  def child(args,record):
   nonlocal clock
   calls.append(args[0]);clock+=timedelta(seconds=1);started=clock.isoformat();clock+=timedelta(seconds=1);finished=clock.isoformat()
   if args[0]=='configure':
    configs[str(args[args.index('--config')+1])]=args[args.index('--orders')+1]
    return {'exit_code':0,'result':{'sha256':'a'*64}}
   q=configs[str(args[args.index('--config')+1])];item=next(x for x in prepared['targets'] if x['target']['question_order']==q);plan=item['plan'];rid='synthetic-'+args[0].strip('-')+'-'+str(q)
   pid=len(calls)
   if args[0]=='--writer':
    wpid[q]=pid
    if plan['mutation_required']:(fx.ledger/(plan['ledger_key']+'.json')).write_bytes(m.raw({'synthetic_intent':True}))
    result={'status':'RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK' if plan['mutation_required'] else 'NO_OP_CURRENT_STATE_CONFIRMED','run_id':rid,'post_attempts':int(plan['mutation_required']),'intent_key':plan['ledger_key'],'release':{'context_runtime_release_confirmed':mode!='release-failed'}}
   else:
    rd=out/rid;rd.mkdir();after=copy.deepcopy(plan['expected'])
    if mode=='readback-mismatch':after['zones']['question']['data']['ocr_result']='unexpected'
    values={'directory':after['directory'],'frames':after['frames'],f'q{q}_annotations':after['annotations'],f'q{q}_info':after['info'],**{f'q{q}_{z}':v for z,v in after['zones'].items()},**{n:fx.native[n] for n in ('source','page_12','page_173')}}
    for name,value in values.items():(rd/(name+'.json')).write_bytes(m.raw(value))
    if mode=='same-process':pid=wpid[q]
    if mode=='pending-unknown' and q==18:
     next_plan=prepared['targets'][1]['plan'];(fx.ledger/(next_plan['ledger_key']+'.json')).write_bytes(b'{"status":"UNKNOWN"}')
    result={'status':'NATIVE_GETS_CAPTURED','run_id':rid,'save_attempts':0,'release':{'context_runtime_release_confirmed':True},'captures':{n:{'observed_at':finished} for n in values}}
   return {'pid':pid,'started_at':started,'finished_at':finished,'exit_code':0,'result':result}
  result=m.entry.execute(prepared,out,fx.baseline,fx.profile,'SYNTHETIC_ONLY','SYNTHETIC_ONLY',child)
  return result,calls
 def test_01_actual_configure_foreign_cwd_and_package_no_runtime(self):
  fx=self.fx;foreign=fx.root/'annotation';foreign.mkdir();(foreign/'__init__.py').write_text("raise RuntimeError('foreign imported')",encoding='ascii')
  runs=fx.root/'offline-runs';runs.mkdir();cfg=fx.root/'portable.json'
  cmd=[sys.executable,'-B',str(ROOT/'tools/run_usense_live.py'),'configure','--profile',str(fx.profile),'--output-root',str(runs),'--config',str(cfg),'--coordinator','synthetic','--executor','synthetic','--reviewer','synthetic','--authorization-reference','SYNTHETIC_ONLY','--orders','18','19','20','21','22','--pages','12','173','--source']
  p=subprocess.run(cmd,cwd=str(fx.root),capture_output=True,timeout=20)
  (OUT/'portable-configure.stdout').write_bytes(p.stdout);(OUT/'portable-configure.stderr').write_bytes(p.stderr)
  self.assertEqual(p.returncode,0,p.stderr);v=json.loads(p.stdout);self.assertEqual(m.sha(cfg.read_bytes()),v['sha256']);self.assertEqual(list(runs.iterdir()),[])
  conf=json.loads(cfg.read_bytes());self.assertEqual(conf['operation'],'READONLY_CAPTURE');self.assertEqual(conf['tls']['mode'],'STRICT');self.assertEqual(len(conf['allowed_get']),41)
 def test_02_matching_candidate_wrong_actual_parent_is_rejected(self):
  fx=self.fx;item=fx.manifest['targets'][0];item['target']['lesson_directory_id']='semantic-lesson-title-is-not-parent'
  fx.change_candidate(item,lambda c:c['target'].update(lesson_directory_id=item['target']['lesson_directory_id']))
  with self.assertRaises(ValueError):fx.prepare()
  self.assertEqual(list(fx.ledger.iterdir()),[])
 def test_03_updated_source_claim_cannot_bypass_review_hash(self):
  fx=self.fx;item=fx.manifest['targets'][-1];p=next(Path(n) for n in item['review_evidence'] if '-source.' in n);p.write_bytes(b'{"different_source":true}')
  fx.change_candidate(item,lambda c:c['approved_changes']['question'].update(source_sha256=m.sha(p.read_bytes())))
  with self.assertRaisesRegex(ValueError,'BATCH_INPUT_HASH_MISMATCH'):fx.prepare()
  self.assertEqual(list(fx.ledger.iterdir()),[])
 def test_04_noop_still_requires_reader_and_never_marks_send(self):
  fx=self.fx
  for item in fx.manifest['targets']:
   fx.change_candidate(item,lambda c:c['approved_changes']['question'].update(text='old',reviewed_text_sha256=m.text_digest('old')))
  result,calls=self.run_chain('noop');self.assertEqual(result['status'],'ALL_ACCEPTED',result);self.assertEqual(calls,['configure','--writer','configure','capture']*5);self.assertTrue(all(r['post_attempts']==0 for r in result['results']));self.assertEqual(list(fx.ledger.iterdir()),[])
 def test_05_reader_mismatch_stops_successors_without_accepted_marker(self):
  result,calls=self.run_chain('readback-mismatch');self.assertEqual(result['error_code'],'READBACK_ACCEPTANCE_FAILED');self.assertEqual([r['status'] for r in result['results']],['FAILED_STOP']+['NOT_RUN']*4);self.assertEqual(calls,['configure','--writer','configure','capture']);self.assertEqual(list(self.fx.ledger.glob('*.accepted.json')),[])
 def test_06_same_reader_process_rejected(self):
  result,calls=self.run_chain('same-process');self.assertEqual(result['status'],'STOPPED_NO_RETRY');self.assertFalse(result['results'][0]['checks']['different_processes']);self.assertEqual(calls,['configure','--writer','configure','capture']);self.assertEqual(list(self.fx.ledger.glob('*.accepted.json')),[])
 def test_07_writer_release_failure_blocks_even_reader_configuration(self):
  result,calls=self.run_chain('release-failed');self.assertEqual(result['error_code'],'WRITER_UNKNOWN_OR_RELEASE_UNPROVEN_NO_RETRY');self.assertEqual(calls,['configure','--writer']);self.assertEqual([r['status'] for r in result['results']],['STOPPED_NO_RETRY']+['NOT_RUN']*4)
 def test_08_new_successor_unknown_preserves_first_acceptance_and_stops(self):
  result,calls=self.run_chain('pending-unknown');self.assertEqual(result['error_code'],'BATCH_PENDING_LEDGER_CHANGED_NO_RETRY');self.assertEqual(calls,['configure','--writer','configure','capture']);self.assertEqual([r['status'] for r in result['results']],['ACCEPTED','STOPPED_NO_RETRY']+['NOT_RUN']*3);self.assertEqual(len(list(self.fx.ledger.glob('*.accepted.json'))),1)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
