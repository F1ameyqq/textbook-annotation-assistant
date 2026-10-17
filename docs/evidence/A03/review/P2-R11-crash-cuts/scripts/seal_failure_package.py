"""Seal an explicit REWORK package including both archive failures unchanged."""
import os
import subprocess
import sys
import time
from failure_archive_common import ROOT,OUT,REPORT,load,sha,write,parents,git_records,nested_records,links
manifest=OUT/'sha256-manifest.json';assert not manifest.exists()
argv=[sys.executable,'-X','utf8','-B',str(OUT/'scripts/run_recorded.py'),'failure-package-check-01','45',str(OUT/'scripts/check_failure_package.py')]
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
write(OUT/'seal-recorder-registration.json',{'argv':argv,'cwd':str(ROOT),'timeout_seconds':55,'registered_at_ns':time.time_ns(),
 'runner_sha256':sha(OUT/'scripts/run_recorded.py'),'entry_sha256':sha(OUT/'scripts/check_failure_package.py')})
with (OUT/'seal-recorder.stdout.log').open('xb') as stdout,(OUT/'seal-recorder.stderr.log').open('xb') as stderr:
    p=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
    write(OUT/'seal-recorder-started.json',{'pid':p.pid,'started_at_ns':time.time_ns()});timed=False
    try:code=p.wait(timeout=55)
    except subprocess.TimeoutExpired:timed=True;p.kill();code=p.wait()
wrapper={'pid':p.pid,'exit_code':code,'timed_out':timed,'alive':p.poll() is None,'ended_at_ns':time.time_ns(),
 'stdout_sha256':sha(OUT/'seal-recorder.stdout.log'),'stderr_sha256':sha(OUT/'seal-recorder.stderr.log')}
write(OUT/'seal-recorder-completion.json',wrapper)
assert code==0 and not timed
par=parents();git=git_records();nested=nested_records();count=len(par)+len(git)+len(nested)+1
write(OUT/'process-release.json',{'status':'ALL_ACTUAL_REGISTERED_POPEN_CHILDREN_WAITED_AND_EXITED_WITH_FAILURES_PRESERVED',
 'review_and_functional_parents':par,'git_children':git,'nested_business_and_observation_children':nested,'seal_recorder_wrapper':wrapper,
 'known_registered_child_count':count,'parent_count':len(par),'git_count':len(git),'nested_count':len(nested),'seal_wrapper_count':1,
 'functional_rounds':{'F1':1,'F2':1,'F3':1,'F4':1},'functional_failures_timeouts_or_reruns':0,
 'archive_failure_exit1_records':['runs/process-audit-01','runs/report-01'],'static_metadata_corrections':1,
 'basis':'Actual owned Popen waits and recorded completion/raw streams; crash owner DB rows are not claimed released.',
 'OS_PID_scan':False,'unregistered_background_jobs':0})
check=load(OUT/'failure-package-check.json')
write(OUT/'final-verification.json',{'status':'REWORK','package_status':'FAILURE_PACKAGE_BYTES_VERIFIED_AND_SEALED',
 'target':'cc5966dc58c62017a27266c40ca0cedc5c68485c','base':'1c26b4a8eb378af33e57668472d2071e9ea6afff',
 'report_sha256':sha(REPORT),'process_release_sha256':sha(OUT/'process-release.json'),'failure_package_check_sha256':sha(OUT/'failure-package-check.json'),
 'input_files':check['input_files'],'source_seed_files_unchanged':check['source_seed_files_unchanged'],'generated_files':check['generated_files'],
 'historical_files_preserved':check['historical_preservation']['count'],'known_registered_children':count,
 'functional_cases_supported':['F1','F2','F3','F4'],'functional_failures_timeouts_or_reruns':0,'archive_failures_retained':2,'static_metadata_corrections':1,
 'second_archive_error_corrected_or_retried':False,'normal_acceptance_closure_stopped':True,
 'author_missing_binary_limit_remains':True,'whole_A03':'REWORK','I01_released':False,'INTEGRATED_state_written':False,
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
paths=sorted([p for p in OUT.rglob('*') if p.is_file()]+[REPORT])
write(manifest,{'status':'REWORK_FAILURE_PACKAGE_FROZEN','root':str(ROOT),'excluded_only':manifest.relative_to(ROOT).as_posix(),
 'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]})
m=load(manifest);actual={p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and p!=manifest};actual.add(REPORT.relative_to(ROOT).as_posix())
assert actual=={r['path'] for r in m['files']}
for r in m['files']:
    p=ROOT/r['path'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
assert all(r['exists'] for r in links())
print(__import__('json').dumps({'status':'REWORK_FAILURE_PACKAGE_SEALED_AND_REHASHED','manifest_files':len(m['files']),
 'report_sha256':sha(REPORT),'manifest_sha256':sha(manifest),'process_release_sha256':sha(OUT/'process-release.json'),
 'known_registered_children':count,'normal_acceptance_closure_stopped':True,'functional_reruns':0}))
