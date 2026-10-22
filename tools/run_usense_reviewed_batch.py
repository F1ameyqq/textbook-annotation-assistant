"""Sequential existing-question updates followed by separate-process native reads.

This local execution harness consumes the published repository implementation.
Private raw evidence stays under the explicit output directory.
"""
import argparse, hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def write(p,v):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)

def main():
 p=argparse.ArgumentParser()
 for name in ('repo','dependency-dir','profile','baseline','reviewed','out','authorization-reference','tls-approval-reference'):
  p.add_argument('--'+name,required=True)
 p.add_argument('--orders',nargs='+',type=int,required=True)
 p.add_argument('--previous-acceptance-root')
 a=p.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
 sys.path.insert(0,str(repo/'src'))
 from annotation.runtime.usense_live.update import make_plan,validate_plan,from_captured_map,compare_readback,json_same
 from annotation.runtime.usense_live.config import endpoints
 if len(set(a.orders))!=len(a.orders) or not all(1<=q<=16 for q in a.orders):raise ValueError('FIRST_LESSON_EXPLICIT_UNIQUE_ORDERS_REQUIRED')
 baseline=Path(a.baseline).resolve();profile=Path(a.profile).resolve();ledger=profile.parent/'usense-existing-ledger';ledger.mkdir(exist_ok=True)
 native={f.stem:read(f) for f in baseline.glob('*.json') if f.stem!='capture-summary'}
 boot="import sys,runpy;sys.path.insert(0,sys.argv[1]);entry=sys.argv[2];sys.argv=[entry]+sys.argv[3:];runpy.run_path(entry,run_name='__main__')"
 def child(args,record):
  cmd=[sys.executable,'-B','-c',boot,str(Path(a.dependency_dir).resolve()),str(repo/'tools/run_usense_live.py'),*map(str,args)]
  started=datetime.now(timezone.utc).isoformat()
  process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8',errors='replace')
  try:stdout,stderr=process.communicate(timeout=150)
  except subprocess.TimeoutExpired:
   process.kill();process.communicate(timeout=10)
   write(record,{'pid':process.pid,'started_at':started,'status':'TIMEOUT_UNKNOWN_NO_RETRY','os_release_unproven':True})
   raise
  finished=datetime.now(timezone.utc).isoformat()
  try:value=json.loads(stdout.strip().splitlines()[-1])
  except Exception:
   write(record,{'pid':process.pid,'exit_code':process.returncode,'error':'CHILD_OUTPUT_NOT_JSON','stderr':stderr[-3000:]})
   raise RuntimeError('CHILD_OUTPUT_NOT_JSON')
  write(record,{'pid':process.pid,'started_at':started,'finished_at':finished,'exit_code':process.returncode,'result':value})
  return process.returncode,value
 summary={'schema':'UsenseReviewedBatch/v1','book_id':'46007447','orders':a.orders,'status':'RUNNING','results':[],'started_at':datetime.now(timezone.utc).isoformat()}
 try:
  for q in a.orders:
   qout=out/f'q{q}';qout.mkdir();reviewfile=Path(a.reviewed).resolve()/f'q{q}-reviewed-candidate.json';candidate=read(reviewfile)
   assert candidate['target']['question_order']==q and candidate['target']['lesson_directory_id']=='dir-1792063578574-2a6vq8zom'
   evidence={str(reviewfile):sha(reviewfile.read_bytes())}
   for rv in candidate['approved_changes'].values():
    for key in ('source_ref','review_ref'):
     ref=Path(rv[key]);evidence[str(ref)]=sha(ref.read_bytes())
   write(qout/'review-evidence-hashes.json',evidence)
   plan=make_plan(from_captured_map(native,f'q{q}_'),candidate['target'],candidate['approved_changes']);validate_plan(plan)
   planfile=qout/'plan.json';write(planfile,plan)
   pages=sorted({int(f['page_index']) for f in plan['before']['annotations']['data']})
   # Include all baseline page metadata used in the local source manifest.
   pages=sorted(set(pages)|{10,11,12,173})
   def configure(label):
    cfg=qout/(label+'-config.json')
    code,frozen=child(['configure','--profile',profile,'--output-root',out,'--config',cfg,
     '--coordinator','root-takeover','--executor',label+'-process','--reviewer','existing-update-reviewer',
     '--authorization-reference',a.authorization_reference,'--tls-approval-reference',a.tls_approval_reference,
     '--orders',q,'--pages',*pages,'--source'],qout/(label+'-configuration-result.json'))
    assert code==0
    return cfg,frozen['sha256']
   cfg,digest=configure('writer')
   for ref,d in evidence.items():assert sha(Path(ref).read_bytes())==d,'REVIEW_EVIDENCE_CHANGED'
   revision_args=['--previous-acceptance',Path(a.previous_acceptance_root).resolve()/f'q{q}'/'acceptance.json'] if a.previous_acceptance_root else []
   code,w=child(['--writer','--config',cfg,'--sha256',digest,'--plan',planfile,'--plan-sha256',sha(planfile.read_bytes()),
    '--baseline',baseline,'--ledger-root',ledger,'--authorization-reference',a.authorization_reference,*revision_args],qout/'writer-process-result.json')
   # A failed/unknown send is never retried. If released, read it once to establish the real state.
   if not w.get('release',{}).get('context_runtime_release_confirmed'):raise RuntimeError('WRITER_RELEASE_UNPROVEN')
   readcfg,readdigest=configure('independent-reader')
   rcode,r=child(['capture','--config',readcfg,'--sha256',readdigest],qout/'reader-process-result.json')
   rd=out/r['run_id'];aftermap={name:read(rd/(name+'.json')) for name in endpoints([q],pages,source=True)}
   comparison=compare_readback(plan,from_captured_map(aftermap,f'q{q}_'))
   source_same=all(json_same(native[name],aftermap[name]) for name in aftermap if name in ('source',*[f'page_{v}' for v in pages]))
   checks={'writer_exit_zero':code==0,'reader_exit_zero':rcode==0,
    'writer_expected_status':w['status'] in ('NO_OP_CURRENT_STATE_CONFIRMED','RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK'),
    'reader_success':r['status']=='NATIVE_GETS_CAPTURED','reader_writes_zero':r['save_attempts']==0,
    'reader_released':r['release']['context_runtime_release_confirmed'],
    'different_contexts':w['run_id']!=r['run_id'],
    'every_read_after_writer':all(datetime.fromisoformat(v['observed_at'])>datetime.fromisoformat(w['finished_at']) for v in r['captures'].values()),
    'native_full_state_matches':comparison['match'],'source_page_responses_unchanged':source_same,
    'one_send_or_noop':w['post_attempts']==(1 if plan['mutation_required'] else 0)}
   accepted=all(checks.values());item={'order':q,'status':'ACCEPTED' if accepted else 'FAILED_STOP','changed_zones':[c['zone'] for c in plan['changes']],
    'target':plan['target'],'writer_run':w['run_id'],'reader_run':r['run_id'],'post_attempts':w['post_attempts'],
    'checks':checks,'comparison':comparison,'plan_file_sha256':sha(planfile.read_bytes()),'reviewed_candidate_sha256':sha(reviewfile.read_bytes())}
   write(qout/'acceptance.json',item);summary['results'].append(item)
   if accepted and plan['mutation_required']:write(ledger/(w.get('intent_key',plan['ledger_key'])+'.accepted.json'),{'plan_sha256':plan['plan_sha256'],'writer_run':w['run_id'],'reader_run':r['run_id'],'acceptance_sha256':sha((qout/'acceptance.json').read_bytes())})
   print(json.dumps({'order':q,'status':item['status'],'post_attempts':w['post_attempts'],'changed_zones':item['changed_zones'],'writer_run':w['run_id'],'reader_run':r['run_id']},ensure_ascii=True),flush=True)
   if not accepted:raise RuntimeError('READBACK_ACCEPTANCE_FAILED')
  summary['status']='ALL_ACCEPTED'
 except BaseException as exc:
  summary['status']='STOPPED_NO_RETRY';summary['error_type']=type(exc).__name__;summary['error']=str(exc)
  raise
 finally:
  summary['finished_at']=datetime.now(timezone.utc).isoformat();write(out/'batch-summary.json',summary)

if __name__=='__main__':main()
