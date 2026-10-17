# -*- coding: utf-8 -*-
"""First final seal; does not modify or rerun the failed collector."""
import json
import os
import subprocess
import sys
import time
from archive_common import ROOT,OUT,REPORT,FIELD_RESET,load,sha,write,links,processes,git_processes,nested_records
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
assert code==0 and not timed,'No further metadata correction authorized; retain failed final check if any'
parents=processes();assert len(parents)==11;helpers=git_processes();nested=nested_records()
write(OUT/'process-release.json',{'status':'ALL_KNOWN_REGISTERED_CHILDREN_WAITED_AND_EXITED_WITH_REVIEW_FAILURES_PRESERVED',
 'review_checks':parents,'review_check_count':11,'functional_and_observation_children':nested,'nested_count':16,
 'git_children':helpers,'git_child_count':5,'seal_recorder_wrapper':wrapper,'seal_wrapper_count':1,'known_registered_child_count':33,
 'functional_group_rounds':{'D1':1,'standalone':1,'borrow':1,'D2':1},'functional_failures_or_reruns':0,
 'corrected_review_assertion':'case-boundaries-review-01 retained; one static audit correction, then case-boundaries-review-02 exit0',
 'uncorrected_collector_failure':'release-review-01 retained; no script change or rerun; no success claimed',
 'release_basis':'actual saved preregistration/start/wait-completion and raw streams only, no OS/profile scan','background_jobs':0})
write(OUT/'final-verification.json',{'status':'OWNER_LIFECYCLE_AND_FOUR_DEMOS_LIMITED_ACCEPTED_OVERALL_A03_REWORK',
 'target':'bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39','report_sha256':sha(REPORT),'process_release_sha256':sha(OUT/'process-release.json'),
 'final_checks_sha256':sha(OUT/'final-checks.json'),'final_check_exit_code':0,'inputs':585,'historical_files_preserved':7383,
 'source_driver_files_unchanged':78,'new_run_files':403,'functional_group_rounds':{'D1':1,'standalone':1,'borrow':1,'D2':1},
 'functional_failures_or_reruns':0,'author_borrow':'FAILED_PRESERVED','author_D2':'NOT_RUN','known_registered_children':33,
 'reviewer_failures_retained':2,'post_functional_audit_static_corrections':1,'failed_collector_unchanged_and_not_rerun':True,
 'actual_import_evidence':'five post-child records and D2 pre-fault before-run.json; D2 post-exit imports not created',
 'manifest_excludes_only_itself':True,'post_write_body_and_inventory_recheck':'seal_review.py checks all entries before successful exit',
 'overall_A03':'REWORK','I01_released':False,'INTEGRATED_state_written':False,'field_reset':FIELD_RESET})
paths=sorted([p for p in OUT.rglob('*') if p.is_file()]+[REPORT]);assert len(paths)==len(set(paths)) and manifest_path not in paths
write(manifest_path,{'status':'R9_R1_REVIEW_FROZEN_WITH_DISCLOSED_REVIEW_COLLECTOR_FAILURE','root':str(ROOT),
 'scope':'four ownership groups limited accepted; author borrow FAILED/D2 NOT_RUN preserved; collector assertion retained uncorrected; overall REWORK',
 'excluded_only':manifest_path.relative_to(ROOT).as_posix(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]})
manifest=load(manifest_path)
actual={p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and p!=manifest_path};actual.add(REPORT.relative_to(ROOT).as_posix())
assert actual=={r['path'] for r in manifest['files']}
for r in manifest['files']:
    p=ROOT/r['path'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
assert all(r['exists'] for r in links())
print(json.dumps({'status':'SEALED_BODY_AND_INVENTORY_REHASHED_WITH_DISCLOSED_COLLECTOR_FAILURE','manifest_files':len(manifest['files']),
 'report_sha256':sha(REPORT),'manifest_sha256':sha(manifest_path),'process_release_sha256':sha(OUT/'process-release.json'),
 'functional_groups_each_once':4,'own_registered_children':33,'overall_A03':'REWORK','I01_released':False}))
