# -*- coding: utf-8 -*-
"""Byte-only finalization. No database connections or product/AST reruns."""
import hashlib
import json
from pathlib import Path
import re
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/tasks/A03-P2-R12-R1-failure-review-report.md'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def write(p,v):
    with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
source_checks=[]
for p in sorted((OUT/'scripts').glob('*.py')):
    b=p.read_bytes();compile(b.decode('utf8',errors='strict'),str(p),'exec')
    source_checks.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(b),'UTF8_decode_compile':'PASS'})
write(OUT/'final-source-check.json',{'files':source_checks,'product_imports_or_calls':0,'SQL_connections':0})
index=load(OUT/'input-index.json');delivery=load(OUT/'delivery-byte-review.json')
assert index['target']=='6affc61d2ab0b1f0d96bb2497c5ae969ebaf1df2' and index['candidate']=='7694490ef25539d131b863bdcb2b21531c69dfae'
for r in index['exports']:
    b=(OUT/r['file']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['raw_git_sha1']
assert {p.relative_to(OUT).as_posix() for p in (OUT/'input').rglob('*') if p.is_file()}=={r['file'] for r in index['exports']}
db=load(OUT/'database-review.json');chain=load(OUT/'reference-chain-review.json');process=load(OUT/'process-source-review.json')
assert db['failed_checks']==chain['failed_checks']==process['failed_checks']==[]
assert db['exported_stage_originals']==db['own_immutable_SQL_copies']==12 and len(db['stages'])==6
for stage in db['stages']:
    for r in stage['databases']:
        assert sha(Path(r['own_SQL_copy']).read_bytes())==sha(Path(r['source_export']).read_bytes())==r['sha256_before_after']
        assert r['quick_check']=='ok' and not r['live_database_opened']
        assert all(q.lstrip().upper().startswith(('SELECT','PRAGMA')) for q in r['queries'])
assert len(list((OUT/'databases').rglob('*.sqlite3')))==12 and not list(OUT.rglob('__pycache__'))
assert process['count']==23 and delivery['checkout_source_index_count']==109 and delivery['checkout_only_EOL_differences']==5
error=load(OUT/'first-tool-error.json');assert error['correction_count']==1 and error['product_calls']==error['SQL_connections']==0 and error['pid'] is None
records=[]
for d in sorted((OUT/'runs').iterdir()):
    pre=load(d/'preregistered.json');start=load(d/'started.json');end=load(d/'completed.json')
    assert pre['source_sha256']==sha((d/'entry-source.py').read_bytes())
    assert start['pid']==end['pid'] and end['exit_code']==0 and not end['alive'] and not end['timed_out'] and pre['timeout_seconds']==60
    for stream in ('stdout','stderr'):assert sha((d/(stream+'.log')).read_bytes())==end[stream+'_sha256']
    records.append({'record':d.relative_to(OUT).as_posix(),'argv':pre['argv'],'cwd':pre['cwd'],'timeout_seconds':pre['timeout_seconds'],**end})
for d in sorted((OUT/'git-processes').iterdir()):
    pre=load(d/'preregistered.json');start=load(d/'started.json');end=load(d/'completed.json')
    assert pre['source_sha256']==sha((OUT/'scripts/freeze.py').read_bytes()) and pre['stdin_sha256']==sha((d/'stdin.bin').read_bytes())
    assert start['pid']==end['pid'] and end['exit_code']==0 and not end['alive'] and not end['timed_out']
    assert pre['argv'][:3]==['git','-c','core.longpaths=true'] and pre['timeout_seconds']==15
    for stream in ('stdout','stderr'):assert sha((d/(stream+'.bin')).read_bytes())==end[stream+'_sha256']
    records.append({'record':d.relative_to(OUT).as_posix(),'argv':pre['argv'],'cwd':pre['cwd'],'timeout_seconds':pre['timeout_seconds'],**end})
write(OUT/'process-release.json',{'status':'ALL_ACTUAL_REGISTERED_REVIEW_POPEN_CHILDREN_WAITED_AND_EXITED','records':records,
 'current_registered_children':len(records),'current_Popen_failures_timeouts_or_reruns':0,
 'first_tool_parser_error_preserved':'first-tool-error.json','one_tool_metadata_correction':1,
 'product_imports_or_calls':0,'SQL_connections_scope':'Twelve own immutable copies only, performed once; no runtime/author originals.',
 'historical_author_processes_verified':23,'current_PID_scan':False,'background_jobs':0,
 'primary_seal_command_completion':'Returned by execution tool; no synthetic self-completion PID.'})
text=REPORT.read_bytes().decode('utf8',errors='strict')
assert '\u5931\u8d25\u53ca\u8303\u56f4\u786e\u8ba4' in text and 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION' in text
refs=[]
for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',text):
    p=(REPORT.parent/link).resolve();assert p.is_relative_to(ROOT) and (p.exists() or p==OUT/'sha256-manifest.json')
    refs.append({'ref':link,'exists':p.exists(),'pending_manifest':p==OUT/'sha256-manifest.json'})
write(OUT/'final-verification.json',{'status':'\u5931\u8d25\u53ca\u8303\u56f4\u786e\u8ba4','target':index['target'],'candidate':index['candidate'],
 'base':index['base'],'workflow':index['workflow'],'report_sha256':sha(REPORT.read_bytes()),
 'process_release_sha256':sha((OUT/'process-release.json').read_bytes()),'input_exports':len(index['exports']),
 'protected_old_tree_entries':33028,'modified_old_files':4,'added_target_files':320,'author_manifest_entries':323,
 'own_immutable_SQL_copies_queried_once':12,'SQL_checks':len(db['checks']),'SQL_failed_checks':0,
 'source_and_process_checks':len(process['checks']),'source_and_process_failed_checks':0,'historical_author_processes':23,
 'actual_import_records':len(process['actual_import_records']),'checkout_source_index':109,'CRLF_only_source_differences':5,
 'current_registered_children':len(records),'new_product_or_functional_calls':0,'runtime_author_SQL_connections':0,
 'tool_metadata_corrections':1,'first_tool_error_preserved':True,'U1_recovery_and_U2_U5':'NOT_RUN',
 'coherent_repair_recommendation_only':True,'native_issue_ownership_bridge_decision_adopted':False,
 'whole_A03':'REWORK','I01_released':False,'INTEGRATED_state_written':False,'B_confirmation':False,
 'report_links':refs,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
manifest=OUT/'sha256-manifest.json';assert not manifest.exists()
paths=sorted([p for p in OUT.rglob('*') if p.is_file()]+[REPORT])
write(manifest,{'status':'\u5931\u8d25\u53ca\u8303\u56f4\u786e\u8ba4','root':str(ROOT),'excluded_only':manifest.relative_to(ROOT).as_posix(),
 'target':index['target'],'candidate':index['candidate'],'workflow':index['workflow'],'functional_acceptance':False,
 'frozen_reference_hashes':delivery['expected_hashes'],
 'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in paths]})
m=load(manifest);actual={p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and p!=manifest};actual.add(REPORT.relative_to(ROOT).as_posix())
assert actual=={r['path'] for r in m['files']}
for r in m['files']:
    p=ROOT/r['path'];assert p.stat().st_size==r['bytes'] and sha(p.read_bytes())==r['sha256']
print(json.dumps({'status':'FROZEN_FAILURE_AND_REPAIR_SCOPE_CONFIRMED_SEALED','manifest_files':len(m['files']),
 'target':index['target'],'report_sha256':sha(REPORT.read_bytes()),'manifest_sha256':sha(manifest.read_bytes()),
 'process_release_sha256':sha((OUT/'process-release.json').read_bytes()),'registered_children':len(records),
 'own_immutable_SQL_copies':12,'new_product_calls':0,'whole_A03':'REWORK','I01_released':False}))
