"""Actual frozen five-plan disk/writer boundary, with read-only path relocation.

Only private path reads are mapped to exact frozen copies. Plan bytes, hashes,
native objects, validators and runner code are unchanged. No live ledger used.
"""
import hashlib,importlib.util,json,os,socket,sys,types
from pathlib import Path,PureWindowsPath
PUB=Path(__file__).resolve().parent
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-readiness-review-20261023')
SNAP=STAGE/'snapshot';PROJECT=STAGE/'project';BASE=PROJECT/'post-manual-login-source';PACK=BASE/'five-candidates-v2';NATIVE=BASE/'runs/usense-readonly-20261023-103259-3becb927'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def norm(v):return PureWindowsPath(str(v)).as_posix().lower()
def main():
 def audit(event,args):
  if event in ('socket.connect','socket.getaddrinfo','socket.bind','subprocess.Popen'):raise RuntimeError('INDEPENDENT_NO_NETWORK_OR_CHILD_PROCESS')
 sys.addaudithook(audit)
 # Export omits the unchanged top-level package file. Route the namespace only;
 # each actual reviewed module still loads from its frozen snapshot file.
 for name,path in [('annotation',SNAP/'src/annotation'),('annotation.runtime',SNAP/'src/annotation/runtime')]:
  module=types.ModuleType(name);module.__path__=[str(path)];sys.modules[name]=module
 sys.path.insert(0,str(SNAP/'src'))
 from annotation.runtime.usense_live import batch,update,writer,core
 from annotation.runtime.usense_live.config import endpoints
 assert Path(writer.__file__).is_relative_to(SNAP) and Path(update.__file__).is_relative_to(SNAP)
 spec=importlib.util.spec_from_file_location('review_five_runner',SNAP/'tools/run_usense_reviewed_batch.py');entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
 registry=json.loads((STAGE/'registry.json').read_bytes());resolved=[]
 def frozen_path(value):
  key=norm(value)
  if key in registry:p=Path(registry[key]);resolved.append({'original':str(value),'copy':str(p)})
  else:
   p=Path(value)
   if not p.is_absolute() or not p.is_relative_to(STAGE):raise RuntimeError('UNFROZEN_PATH_REFUSED: '+str(value))
  return p
 # These are filesystem routing adapters, not altered validator decisions.
 batch.plain_path=frozen_path;writer.Path=frozen_path
 checks=STAGE/'controls';checks.mkdir(exist_ok=False);profile=checks/'isolated-profile';ledger=checks/'usense-existing-ledger';profile.mkdir();ledger.mkdir()
 original_manifest=next(k for k,v in registry.items() if Path(v)==PACK/'targets.json');manifest_raw=(PACK/'targets.json').read_bytes();manifest_sha=sha(manifest_raw)
 prepared=batch.prepare(original_manifest,manifest_sha,NATIVE,profile,'REVIEW_OFFLINE_ONLY_NOT_SAVE_AUTHORITY')
 assert len(prepared['targets'])==5 and [x['printed_question'] for x in prepared['targets']]==list(range(1,6)) and len({x['target']['node_id'] for x in prepared['targets']})==5 and all(x['plan']['mutation_required'] for x in prepared['targets'])
 out=checks/'runner-materialized';out.mkdir();calls=[]
 class ReviewStopBeforeChild(Exception):pass
 def no_child(args,record):calls.append(str(args[0]));raise ReviewStopBeforeChild('Expected reviewer stop before configure; no child launched')
 result=entry.execute(prepared,out,NATIVE,profile,'REVIEW_OFFLINE_ONLY_NOT_SAVE_AUTHORITY','FROZEN_EXISTING_TLS_REFERENCE_ONLY',no_child)
 assert calls==['configure'] and result['status']=='STOPPED_NO_RETRY' and result['error_type']=='ReviewStopBeforeChild'
 validation=json.loads((BASE/'five-plan-validation/validation.json').read_bytes());roundtrips=[]
 for item in prepared['targets']:
  i=item['printed_question'];q=item['target']['question_order'];path=item['qout']/'plan.json';raw=path.read_bytes();loaded=update.loads(raw)
  # The real runner above wrote every plan before the injected child stop.
  update.validate_plan(loaded)
  _,claim=writer.validate_inputs(loaded,NATIVE,endpoints([q],[12,173],source=True),ledger,'REVIEW_OFFLINE_ONLY_NOT_SAVE_AUTHORITY')
  candidate_plan=update.loads((PACK/f'printed-{i}-plan.json').read_bytes());assert update.json_same(loaded,candidate_plan) and update.json_same(loaded,item['plan'])
  author_file=BASE/f'five-plan-validation/printed-{i}-materialized-plan.json';assert raw==author_file.read_bytes()
  author_check=validation['actual_five_roundtrips'][i-1];assert sha(raw)==author_check['materialized_file_sha256'] and loaded['plan_sha256']==author_check['plan_sha256']
  assert claim.name==loaded['ledger_key']+'.json' and len(endpoints([q],[12,173],source=True))==12
  roundtrips.append({'printed_question':i,'native_order':q,'materialized_path':str(path),'materialized_sha256':sha(raw),'plan_sha256':loaded['plan_sha256'],'real_writer_validate_inputs':'PASS','old_complete_native_objects_and_hashes_preserved':True})
 first=prepared['targets'][0];existing=first['qout']/'plan.json';before=existing.read_bytes()
 try:entry.write_plan(existing,first['plan']);raise AssertionError('overwrite permitted')
 except FileExistsError:pass
 assert existing.read_bytes()==before
 sorted_path=checks/'old-sorted-plan.json';core.write_new(sorted_path,first['plan']);bad=update.loads(sorted_path.read_bytes())
 try:writer.validate_inputs(bad,NATIVE,endpoints([18],[12,173],source=True),ledger,'REVIEW_OFFLINE_ONLY_NOT_SAVE_AUTHORITY');raise AssertionError('old sorted defect not rejected')
 except update.UpdateError as exc:assert exc.code=='OCR_ABSENCE_NOT_PROVEN';old_error=exc.code
 assert list(ledger.iterdir())==[]
 value={'schema':'A25IndependentActualFivePlanBoundary/v1','status':'PASS_OFFLINE_ONLY','product_commit':'8990e1e3c7561bc7403eb29359f0d39ba3a54295','targets_manifest_sha256':manifest_sha,'actual_runner_materialized_all_five_before_child':True,'read_original_plan_bytes_then_real_writer_validate_inputs':roundtrips,'overwrite_rejected_original_bytes_unchanged':True,'old_sorted_counterexample_error':old_error,'injected_stop':'ReviewStopBeforeChild is an intentional harness boundary; not a product/live failure','child_calls_intercepted_before_launch':calls,'actual_children_started':0,'path_adapter':'Only maps original declared private file reads to exact frozen copies; native plan strings/bytes/hashes and validators unchanged','source_reads':resolved,'isolated_test_ledger_entries':0,'real_profile_or_ledger_touched':False,'network_browser_save_attempts':0,'old_successful_suites_rerun':False}
 save(PUB/'boundary-controls.json',value);print(json.dumps({'status':value['status'],'actual_five_roundtrips':5,'real_writer_validate_inputs_pass':5,'overwrite_rejection':True,'old_sorted_error':old_error,'network':0,'real_ledger_touched':False}))
if __name__=='__main__':main()
