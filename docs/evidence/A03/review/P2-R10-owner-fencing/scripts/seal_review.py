# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys
import time
from archive_common import ROOT,OUT,REPORT,FIELD_RESET,load,sha,write,links,parents,git_records,nested_records
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
write(OUT/'seal-recorder-completion.json',wrapper);assert code==0 and not timed
own_parents=parents();helpers=git_records();nested=nested_records();assert len(own_parents)==6
total=len(own_parents)+len(helpers)+len(nested)+1
write(OUT/'process-release.json',{'status':'ALL_ACTUAL_REGISTERED_REVIEW_GIT_AND_BUSINESS_CHILDREN_WAITED_AND_EXITED',
 'review_and_functional_parents':own_parents,'parent_count':len(own_parents),'nested_business_and_observation_children':nested,'nested_count':len(nested),
 'git_children':helpers,'git_count':len(helpers),'seal_recorder_wrapper':wrapper,'seal_wrapper_count':1,'known_registered_child_count':total,
 'groups_rounds':{'C1':1,'C2':1},'functional_failures_timeouts_or_reruns':0,'post_functional_metadata_corrections':0,
 'preparation_failure_limit':'pre-functional tool transcript lacks PID/raw split streams; preserved separately, no fabricated process proof',
 'release_basis':'own Popen waits plus actual registration/start/completion and raw outputs; no OS/profile scan','background_jobs':0})
write(OUT/'final-verification.json',{'status':'ACCEPTED_OWNER_FENCING_TWO_CASES_ONLY','target':'1c26b4a8eb378af33e57668472d2071e9ea6afff',
 'base':'bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39','report_sha256':sha(REPORT),'process_release_sha256':sha(OUT/'process-release.json'),
 'final_checks_sha256':sha(OUT/'final-checks.json'),'final_check_exit_code':0,'inputs':356,'historical_files_preserved':8509,'source_files_unchanged':76,
 'generated_files':110,'C1_rounds':1,'C2_rounds':1,'effects':[0,0],'known_registered_children':total,'post_functional_failures_or_corrections':0,
 'actual_files_only_no_fabricated_exit_evidence':True,'manifest_excludes_only_itself':True,'post_write_body_and_inventory_recheck':'seal_review.py verifies all entries and links before successful exit',
 'whole_A03':'REWORK','I01_released':False,'INTEGRATED_state_written':False,'field_reset':FIELD_RESET})
paths=sorted([p for p in OUT.rglob('*') if p.is_file()]+[REPORT]);assert len(paths)==len(set(paths)) and manifest_path not in paths
write(manifest_path,{'status':'R10_TWO_OWNER_FENCING_CASES_REVIEW_FROZEN','root':str(ROOT),
 'scope':'only two bounded owner/fencing cases accepted; whole A03 REWORK; no integration/I01 release',
 'excluded_only':manifest_path.relative_to(ROOT).as_posix(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]})
manifest=load(manifest_path)
actual={p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and p!=manifest_path};actual.add(REPORT.relative_to(ROOT).as_posix())
assert actual=={r['path'] for r in manifest['files']}
for r in manifest['files']:
    p=ROOT/r['path'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
assert all(r['exists'] for r in links())
print(json.dumps({'status':'ACCEPTED_OWNER_FENCING_TWO_CASES_ONLY_SEALED_AND_REHASHED','manifest_files':len(manifest['files']),
 'report_sha256':sha(REPORT),'manifest_sha256':sha(manifest_path),'process_release_sha256':sha(OUT/'process-release.json'),
 'known_registered_children':total,'C1_C2_rounds_each':1,'whole_A03':'REWORK','I01_released':False}))
