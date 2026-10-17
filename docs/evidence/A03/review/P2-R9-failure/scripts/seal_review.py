# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys
import time
from archive_common import ROOT,OUT,REPORT,FIELD_RESET,load,sha,write,links,processes,git_processes
manifest_path=OUT/'sha256-manifest.json';assert not manifest_path.exists()
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
argv=[sys.executable,'-X','utf8','-B',str(OUT/'scripts/run_recorded.py'),'final-verification-01','45',str(OUT/'scripts/final_checks.py')]
write(OUT/'seal-recorder-registration.json',{'argv':argv,'cwd':str(ROOT),'timeout_seconds':55,'registered_at_ns':time.time_ns(),
 'runner_sha256':sha(OUT/'scripts/run_recorded.py'),'entry_sha256':sha(OUT/'scripts/final_checks.py'),'input_index_sha256':sha(OUT/'input-index.json')})
with (OUT/'seal-recorder.stdout.log').open('xb') as stdout,(OUT/'seal-recorder.stderr.log').open('xb') as stderr:
    p=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
    write(OUT/'seal-recorder-started.json',{'pid':p.pid,'started_at_ns':time.time_ns()});timed=False
    try:code=p.wait(timeout=55)
    except subprocess.TimeoutExpired:timed=True;p.kill();code=p.wait()
wrapper={'pid':p.pid,'exit_code':code,'timed_out':timed,'alive':p.poll() is None,'ended_at_ns':time.time_ns(),
 'stdout_sha256':sha(OUT/'seal-recorder.stdout.log'),'stderr_sha256':sha(OUT/'seal-recorder.stderr.log')}
write(OUT/'seal-recorder-completion.json',wrapper)
assert code==0 and not timed,'Preserve first byte-check failure before any metadata correction'
parents=processes();assert len(parents)==4;helpers=git_processes()
write(OUT/'process-release.json',{'status':'OWN_REGISTERED_REVIEW_AND_GIT_CHILDREN_WAITED_AND_EXITED','review_checks':parents,'review_check_count':4,
 'git_children':helpers,'git_child_count':5,'seal_recorder_wrapper':wrapper,'seal_wrapper_count':1,'known_registered_child_count':10,
 'retained_reviewer_readonly_assertion_failure':'independent-review-01 exit1, then byte/immutable-copy review only',
 'candidate_product_calls_or_children':0,'D1_D2_reruns':0,'background_jobs':0,'release_basis':'own Popen waits, saved registration/start/completion and raw streams; no OS/profile scan'})
write(OUT/'final-verification.json',{'status':'PRODUCT_OWNERSHIP_DEFECT_CONFIRMED_REWORK_NO_REEXECUTION','target':'c83f956c5c29c64ab10735ba11c153201d3f3f4b',
 'report_sha256':sha(REPORT),'process_release_sha256':sha(OUT/'process-release.json'),'final_checks_sha256':sha(OUT/'final-checks.json'),
 'final_check_exit_code':0,'inputs':273,'historical_files_preserved':7030,'product_calls_or_D1_D2_replays':0,'subagents':0,
 'registered_review_checks':4,'registered_git_children':5,'seal_wrapper':1,'retained_reviewer_assertion_failures':1,
 'D1_restart_and_D2':'NOT_RUN','D1_D2':'NOT_ACCEPTED','overall_A03':'REWORK','I01_released':False,'INTEGRATED_state_written':False,
 'manifest_excludes_only_itself':True,'post_write_body_and_inventory_recheck':'seal_review.py checks before successful exit','field_reset':FIELD_RESET})
paths=sorted([p for p in OUT.rglob('*') if p.is_file()]+[REPORT]);assert len(paths)==len(set(paths)) and manifest_path not in paths
write(manifest_path,{'status':'R9_FAILURE_REVIEW_FROZEN','root':str(ROOT),'scope':'read-only first-failure diagnosis and bounded repair advice; no D1/D2 replay or acceptance',
 'excluded_only':manifest_path.relative_to(ROOT).as_posix(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]})
manifest=load(manifest_path)
actual={p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and p!=manifest_path};actual.add(REPORT.relative_to(ROOT).as_posix())
assert actual=={r['path'] for r in manifest['files']}
for r in manifest['files']:
    p=ROOT/r['path'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
assert all(r['exists'] for r in links())
print(json.dumps({'status':'SEALED_BODY_AND_INVENTORY_REHASHED','manifest_files':len(manifest['files']),
 'target':'c83f956c5c29c64ab10735ba11c153201d3f3f4b','report_sha256':sha(REPORT),'manifest_sha256':sha(manifest_path),
 'process_release_sha256':sha(OUT/'process-release.json'),'registered_review_checks':4,'git_children':5,'seal_wrapper':1,'product_calls':0,'overall_A03':'REWORK','I01_released':False}))
