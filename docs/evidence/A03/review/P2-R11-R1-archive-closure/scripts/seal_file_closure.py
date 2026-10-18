# -*- coding: utf-8 -*-
"""Decode/compile first; run one bounded file-only child and seal actual records."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/tasks/A03-P2-R11-R1-archive-closure-review-report.md'
OLD=ROOT/'docs/evidence/A03/review/P2-R11-crash-cuts'
OLD_REPORT=ROOT/'docs/tasks/A03-P2-R11-crash-cuts-review-report.md'
TARGET='cc5966dc58c62017a27266c40ca0cedc5c68485c'
WF='188fed05cd51789521b27efb04b2426f630571d0'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(v if isinstance(v,bytes) else (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
assert not REPORT.exists() and not (OUT/'runs').exists() and not (OUT/'sha256-manifest.json').exists()
sources=[]
for path in sorted((OUT/'scripts').glob('*.py')):
    body=path.read_bytes();decoded=body.decode('utf8',errors='strict');compile(decoded,str(path),'exec')
    sources.append({'path':path.relative_to(ROOT).as_posix(),'bytes':len(body),'sha256':sha(body),
      'strict_UTF8_decode':'PASS','compile_only':'PASS','candidate_or_old_script_executed':False})
write(OUT/'source-preflight.json',{'status':'NEW_SOURCES_UTF8_DECODED_AND_COMPILED_BEFORE_SINGLE_CHILD',
 'at_ns':time.time_ns(),'executable':sys.executable,'python_version':sys.version,'files':sources,
 'product_imports':0,'functional_calls':0,'SQL_connections':0,'old_scripts_executed_or_compiled':0})
d=OUT/'runs/archive-closure-01';d.mkdir(parents=True,exist_ok=False)
entry=OUT/'scripts/close_archive.py';body=entry.read_bytes();write(d/'entry-source.py',body)
argv=[sys.executable,'-X','utf8','-B',str(entry)]
write(d/'preregistered.json',{'argv':argv,'cwd':str(ROOT),'timeout_seconds':45,'registered_at_ns':time.time_ns(),
 'entry_sha256':sha(body),'source_preflight_sha256':sha((OUT/'source-preflight.json').read_bytes()),
 'workflow':WF,'target':TARGET,'task_raw_sha256':'9565f3e8cd86373ddda5cdf728cf5e07ec07347dfa1824319a53b20fcc5cf7c1',
 'functional_calls_authorized':0,'closure_round':1,'corrections_or_retries_authorized':0})
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
start=time.monotonic();timed=False
with (d/'stdout.log').open('xb') as stdout,(d/'stderr.log').open('xb') as stderr:
    child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
    write(d/'started.json',{'pid':child.pid,'parent_pid':os.getpid(),'started_at_ns':time.time_ns()})
    try:code=child.wait(timeout=45)
    except subprocess.TimeoutExpired:timed=True;child.kill();code=child.wait()
end={'pid':child.pid,'exit_code':code,'timed_out':timed,'alive':child.poll() is None,'ended_at_ns':time.time_ns(),
 'elapsed_seconds':time.monotonic()-start,'stdout_sha256':sha((d/'stdout.log').read_bytes()),'stderr_sha256':sha((d/'stderr.log').read_bytes())}
write(d/'completed.json',end)
status='ACCEPTED_FOUR_CRASH_CUTS_ONLY' if code==0 and not timed else 'BLOCKED'
failure=None
if status=='BLOCKED':
    failure={'kind':'FIRST_AND_ONLY_CLOSURE_CHILD_FAILURE','pid':child.pid,'exit_code':code,'timed_out':timed,
      'stderr_sha256':end['stderr_sha256'],'corrections_or_retries':0}
    write(OUT/'first-closure-failure.json',failure)
    if not REPORT.exists():
        write(REPORT,('# A03 P2-R11-R1 archive closure\n\nVerdict: **BLOCKED**.\n\nThe first and only file-only closure child failed. No correction or retry was made. Original evidence and REWORK history remain unchanged. Functional calls0; SQL connections0.\n\nTarget `'+TARGET+'`. Whole A03/I01 remain unreleased. Field reset: `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`.\n').encode('utf8'))
if status=='ACCEPTED_FOUR_CRASH_CUTS_ONLY':
    result=load(OUT/'closure-result.json')
    assert result['status']==status and result['functional_calls']==result['SQL_connections']==result['corrections_or_retries']==0
    assert result['closure_rounds']==1 and result['report_sha256']==sha(REPORT.read_bytes())
    prior=load(OUT/'original-preservation-before.json');after=[]
    for r in prior['files']:
        p=ROOT/r['path'];b=p.read_bytes();digest=sha(b);oid=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        assert digest==r['sha256'] and len(b)==r['bytes'] and oid==r['workflow_git_blob'];after.append(dict(r))
    actual={p.relative_to(ROOT).as_posix() for p in OLD.rglob('*') if p.is_file()}|{OLD_REPORT.relative_to(ROOT).as_posix()}
    assert actual=={r['path'] for r in after} and len(after)==1209
    assert sha(canon(after))==prior['inventory_sha256']
    write(OUT/'original-preservation.json',{'status':'ALL_ORIGINAL_PACKAGE_BYTES_UNCHANGED','workflow':WF,
      'files_verified_before_and_after':len(after),'total_bytes':prior['total_bytes'],'inventory_sha256_before':prior['inventory_sha256'],
      'inventory_sha256_after':sha(canon(after)),'changed_or_added_or_removed_original_paths':[],
      'before_file':'original-preservation-before.json','before_file_sha256':sha((OUT/'original-preservation-before.json').read_bytes()),
      'old_report_sha256':sha(OLD_REPORT.read_bytes()),'old_manifest_sha256':sha((OLD/'sha256-manifest.json').read_bytes()),
      'old_process_release_sha256':sha((OLD/'process-release.json').read_bytes()),'old_REWORK_unchanged':True})
    refs=[]
    for reference in re.findall(r'\[[^\]]+\]\(([^)]+)\)',REPORT.read_bytes().decode('utf8',errors='strict')):
        p=(REPORT.parent/reference).resolve();assert p.is_relative_to(ROOT)
        pending=p in (OUT/'process-release.json',OUT/'sha256-manifest.json')
        assert p.exists() or pending
        refs.append({'ref':reference,'exists_at_check':p.exists(),'pending_seal':pending})
    write(OUT/'report-link-check.json',{'links':refs,'new_report_strict_UTF8_decode':'PASS','source_files_unchanged':True})

records=[{'record':d.relative_to(OUT).as_posix(),'argv':argv,'cwd':str(ROOT),'timeout_seconds':45,**end}]
for folder in sorted((OUT/'git-processes').glob('*')) if (OUT/'git-processes').exists() else []:
    pre=load(folder/'preregistered.json');started=load(folder/'started.json');completed=load(folder/'completed.json')
    assert started['pid']==completed['pid'] and completed['exit_code']==0 and not completed['alive'] and not completed['timed_out']
    assert pre['source_sha256']==sha(entry.read_bytes()) and pre['stdin_sha256']==sha((folder/'stdin.bin').read_bytes())
    assert completed['stdout_sha256']==sha((folder/'stdout.bin').read_bytes()) and completed['stderr_sha256']==sha((folder/'stderr.bin').read_bytes())
    records.append({'record':folder.relative_to(OUT).as_posix(),'argv':pre['argv'],'cwd':pre['cwd'],'timeout_seconds':pre['timeout_seconds'],**completed})
write(OUT/'process-release.json',{'status':'ALL_ACTUAL_CURRENT_ROUND_POPEN_CHILDREN_WAITED_AND_EXITED','records':records,
 'known_registered_child_count':len(records),'closure_child_rounds':1,'corrections_or_retries':0,'functional_calls':0,'SQL_connections':0,
 'basis':'Actual Popen wait/communicate completions with raw streams; primary seal command completion is returned by the execution tool.',
 'old_33_processes_are_historical_only':True,'OS_PID_scan':False,'background_jobs':0})
for r in sources:assert sha((ROOT/r['path']).read_bytes())==r['sha256']
write(OUT/'final-verification.json',{'status':status,'target':TARGET,'workflow':WF,
 'report_sha256':sha(REPORT.read_bytes()),'process_release_sha256':sha((OUT/'process-release.json').read_bytes()),
 'original_preservation_sha256':sha((OUT/'original-preservation.json').read_bytes()) if (OUT/'original-preservation.json').exists() else None,
 'functional_calls':0,'SQL_connections':0,'closure_rounds':1,'corrections_or_retries':0,'known_registered_children':len(records),
 'original_REWORK_and_two_archive_failures_preserved':True,'old_static_correction_count':1,
 'author_F2_F3_binary_limit_remains':True,'whole_A03':'REWORK','product_integration_released':False,'I01_released':False,
 'state_written':False,'B_mapping_jointly_confirmed':False,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
manifest=OUT/'sha256-manifest.json'
paths=sorted([p for p in OUT.rglob('*') if p.is_file()]+[REPORT])
write(manifest,{'status':status,'root':str(ROOT),'excluded_only':manifest.relative_to(ROOT).as_posix(),
 'workflow':WF,'target':TARGET,'functional_calls':0,
 'frozen_reference_hashes':{'original_manifest':sha((OLD/'sha256-manifest.json').read_bytes()),
  'original_report':sha(OLD_REPORT.read_bytes()),'original_case_audit':sha((OLD/'case-and-boundary-review.json').read_bytes()),
  'original_process_import_audit':sha((OLD/'process-and-import-review.json').read_bytes()),
  'original_process_release':sha((OLD/'process-release.json').read_bytes())},
 'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in paths]})
m=load(manifest);actual={p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and p!=manifest};actual.add(REPORT.relative_to(ROOT).as_posix())
assert actual=={r['path'] for r in m['files']}
for r in m['files']:
    p=ROOT/r['path'];assert p.stat().st_size==r['bytes'] and sha(p.read_bytes())==r['sha256']
print(json.dumps({'status':status,'manifest_files':len(m['files']),'report_sha256':sha(REPORT.read_bytes()),
 'manifest_sha256':sha(manifest.read_bytes()),'process_release_sha256':sha((OUT/'process-release.json').read_bytes()),
 'original_preservation_sha256':sha((OUT/'original-preservation.json').read_bytes()) if (OUT/'original-preservation.json').exists() else None,
 'known_registered_children':len(records),'functional_calls':0,'SQL_connections':0,'corrections_or_retries':0}))
raise SystemExit(0 if status=='ACCEPTED_FOUR_CRASH_CUTS_ONLY' else 1)
