# -*- coding: utf-8 -*-
"""Final byte-only seal. No candidate import, AST rerun, SQL or subprocess."""
import hashlib
import json
from pathlib import Path
import re
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/tasks/A03-P2-R12-prerequisite-review-report.md'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def write(p,v):
    with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
body=Path(__file__).read_bytes();compile(body.decode('utf8',errors='strict'),str(Path(__file__)),'exec')
write(OUT/'seal-source-preflight.json',{'path':str(Path(__file__)),'sha256':sha(body),'strict_UTF8_decode':'PASS','compile_only':'PASS',
 'candidate_imports_or_calls':0,'SQL_connections':0,'new_subprocesses':0})
for r in load(OUT/'source-preflight.json')['sources']:assert sha((ROOT/r['path']).read_bytes())==r['sha256']
index=load(OUT/'input-index.json');assert index['target']=='394fe51f5ed14c5ed312073a20faac0f5cbb9990'
for r in index['exports']:
    b=(OUT/r['file']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['raw_git_sha1']
assert {p.relative_to(OUT).as_posix() for p in (OUT/'input').rglob('*') if p.is_file()}=={r['file'] for r in index['exports']}
delivery=load(OUT/'delivery-byte-review.json');assert delivery['old_tree_entries_preserved']==32993 and delivery['changed_old_entries']==[]
assert delivery['new_files']==39 and delivery['manifest_entries']==38 and not delivery['functional_databases_in_added_paths']
chain=load(OUT/'class-scoped-chain.json');result=load(OUT/'static-result.json')
assert len(chain['missing_required'])==6 and len(chain['extra_forbidden'])==4 and chain['old_POST_constructor_line']==793
assert [r['line'] for r in chain['old_POST_ancestor_conditions_nearest_first']]==[790,786,770]
assert result['functional_calls']==result['SQL_connections']==0 and not result['U1_U5_functionally_validated']
assert result['status']=='\u963b\u65ad\u8bc1\u636e\u786e\u8ba4'
assert not list(OUT.rglob('*.sqlite3')) and not list(OUT.rglob('*.db')) and not list(OUT.rglob('__pycache__'))
text=REPORT.read_bytes().decode('utf8',errors='strict')
assert '\u963b\u65ad\u8bc1\u636e\u786e\u8ba4' in text and 'NOT_OBSERVED' in text and 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION' in text
d=OUT/'runs/static-review-01';pre=load(d/'preregistered.json');start=load(d/'started.json');end=load(d/'completed.json')
assert start['pid']==end['pid']==67384 and end['exit_code']==0 and not end['alive'] and not end['timed_out']
assert pre['source_sha256']==sha((d/'entry-source.py').read_bytes())==sha((OUT/'scripts/review_static.py').read_bytes())
assert pre['timeout_seconds']==45
for stream in ('stdout','stderr'):assert end[stream+'_sha256']==sha((d/(stream+'.log')).read_bytes())
records=[{'record':d.relative_to(OUT).as_posix(),'argv':pre['argv'],'cwd':pre['cwd'],'timeout_seconds':pre['timeout_seconds'],**end}]
for d in sorted((OUT/'git-processes').iterdir()):
    pre=load(d/'preregistered.json');start=load(d/'started.json');end=load(d/'completed.json')
    assert start['pid']==end['pid'] and end['exit_code']==0 and not end['alive'] and not end['timed_out']
    assert pre['argv'][:3]==['git','-c','core.longpaths=true'] and pre['timeout_seconds']==10
    assert pre['source_sha256']==sha((OUT/'scripts/review_static.py').read_bytes()) and pre['stdin_sha256']==sha((d/'stdin.bin').read_bytes())
    for stream in ('stdout','stderr'):assert end[stream+'_sha256']==sha((d/(stream+'.bin')).read_bytes())
    records.append({'record':d.relative_to(OUT).as_posix(),'argv':pre['argv'],'cwd':pre['cwd'],'timeout_seconds':pre['timeout_seconds'],**end})
write(OUT/'process-release.json',{'status':'ALL_ACTUAL_REGISTERED_CURRENT_REVIEW_CHILDREN_WAITED_AND_EXITED','records':records,
 'registered_current_children':len(records),'static_review_rounds':1,'failures':0,'timeouts':0,'reruns_or_corrections':0,
 'product_imports_or_calls':0,'SQL_connections':0,'current_OS_PID_scan':False,'author_PID54248_record':'HISTORICAL_WAIT_ONLY',
 'background_jobs':0,'primary_seal_command_completion':'Returned by execution tool; no fabricated child PID.'})
refs=[]
for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',text):
    p=(REPORT.parent/link).resolve();assert p.is_relative_to(ROOT) and (p.exists() or p==OUT/'sha256-manifest.json')
    refs.append({'reference':link,'exists':p.exists(),'pending_manifest':p==OUT/'sha256-manifest.json'})
write(OUT/'final-verification.json',{'status':result['status'],'target':index['target'],'base':index['base'],'workflow':index['workflow'],
 'report_sha256':sha(REPORT.read_bytes()),'process_release_sha256':sha((OUT/'process-release.json').read_bytes()),
 'input_exports':len(index['exports']),'old_tree_entries_preserved':32993,'target_added_files':39,'author_manifest_entries':38,
 'class_scoped_chain_verified':True,'missing_native_fields':6,'extra_legacy_fields':4,'new_registered_children':len(records),
 'functional_calls':0,'SQL_connections':0,'R12_functional_acceptance':False,'U1_U5_executed':False,
 'actual_runtime_error_or_transaction_effects':'NOT_OBSERVED','whole_A03':'REWORK','I01_released':False,'state_written':False,
 'report_links':refs,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
manifest=OUT/'sha256-manifest.json';assert not manifest.exists()
paths=sorted([p for p in OUT.rglob('*') if p.is_file()]+[REPORT])
write(manifest,{'status':result['status'],'root':str(ROOT),'excluded_only':manifest.relative_to(ROOT).as_posix(),
 'target':index['target'],'base':index['base'],'workflow':index['workflow'],'functional_acceptance':False,
 'frozen_reference_hashes':delivery['expected_hashes'],
 'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in paths]})
actual={p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and p!=manifest};actual.add(REPORT.relative_to(ROOT).as_posix())
m=load(manifest);assert actual=={r['path'] for r in m['files']}
for r in m['files']:
    p=ROOT/r['path'];assert p.stat().st_size==r['bytes'] and sha(p.read_bytes())==r['sha256']
print(json.dumps({'status':'STATIC_BLOCKER_EVIDENCE_CONFIRMED_SEALED','target':index['target'],'manifest_files':len(m['files']),
 'report_sha256':sha(REPORT.read_bytes()),'manifest_sha256':sha(manifest.read_bytes()),
 'process_release_sha256':sha((OUT/'process-release.json').read_bytes()),'registered_children':len(records),
 'functional_calls':0,'SQL_connections':0,'R12_functional_acceptance':False}))
