# -*- coding: utf-8 -*-
"""Byte-only final reconciliation; no SQL reopening or product calls."""
import hashlib
import json
import subprocess
from archive_common import ROOT,OUT,REPORT,load,sha,write,links,preservation,own_processes
from evidence import WORK,EV,TARGET,BASE,raw
index=load(OUT/'input-index.json')['exports'];assert len(index)==407 and len({r['file'] for r in index})==407
for row in index:
    p=OUT/row['file'];b=p.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['raw_git_sha1']
seed=load(OUT/'isolated-source-index.json')['files'];assert len(seed)==75
output=load(OUT/'independent-output-index.json')['files'];assert len(output)==98
for row in output:
    p=OUT/row['file'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
assert {p.relative_to(OUT).as_posix() for p in WORK.rglob('*') if p.is_file()}=={r['file'] for r in seed+output}
assert {p.relative_to(OUT).as_posix() for p in (OUT/'input').rglob('*') if p.is_file()}=={r['file'] for r in index if r['file'].startswith('input/')}
history=preservation();assert history['count']==4645
author=load(OUT/'author-boundary-review.json');independent=load(OUT/'independent-boundary-review.json');test=load(OUT/'independent-test-result.json')
assert author['status']==independent['status']=='FORMAL_N1_BOUNDARIES_VERIFIED'
assert independent['effect_count']==author['effect_count']==1 and independent['formal_receipt_ref']!=author['formal_receipt_ref']
assert test['tests_run']==1 and test['successful'] and test['candidate_functional_rounds']==1 and not test['N2_N7_or_compatibility_run']
assert author['book']['hold'] and author['POST_HOLD_run_rows']==0 and independent['book']['hold'] is None
for label in ('author','independent'):
    audit=load(OUT/(label+'-database-review.json'));assert audit['removed'] and len(audit['copies'])==2
    for record in audit['copies']:
        assert record['copy_sha256_before']==record['copy_sha256_after']==record['source_sha256']==record['source_sha256_after']
nested=load(OUT/'independent-nested-release.json')['records'];assert len(nested)==4
source_checks=[]
for row in nested:
    d=OUT/row['record'];pre=load(d/'preregistered.json');end=load(d/'completed.json')
    script='tests/test_a03_r8_r2_projection.py' if row['exit_code']==87 else 'src/annotation/runtime/recovery/native_observation.py'
    expected=hashlib.sha256(raw(script)).hexdigest();assert pre['script_sha256']==expected
    assert sha(d/'script-snapshot.py')==expected
    assert not end['alive'] and not end.get('timed_out',end.get('timeout',True))
    if 'input_sha256' in pre:assert sha(d/'request.json')==pre['input_sha256']
    source_checks.append({'record':row['record'],'frozen_source':script,'sha256':expected})
bootstrap=load(OUT/'author-process-review.json')['bootstrap_failure_evidence_limit']
assert bootstrap['pid'] is None and 'not raw' in bootstrap['transcript_limit']
report=REPORT.read_text(encoding='utf8')
for name in ('plan_ref','formal_receipt_ref','terminal_head_ref','POST_ref','Batch_ref'):
    assert independent[name]['artifact_id'] in report and independent[name]['content_hash'] in report
assert '1f2eb8' in report and 'N2 阻断' in report and 'I01 未释放' in report
argv=['git','-c','core.longpaths=true','rev-list','--parents','--ancestry-path',BASE+'..'+TARGET]
lineage=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.decode().splitlines()
assert lineage[0].split()[0]==TARGET and '002c26795822fe8518117793f59598b3eceab02e' in {r.split()[0] for r in lineage}
parents=own_processes(skip=('final-verification-01',));assert len(parents)==6
pending=tuple(OUT/p for p in ('process-release.json','final-verification.json','sha256-manifest.json'));report_links=links(pending)
assert sum(not r['exists'] for r in report_links)==3 and not list(OUT.rglob('__pycache__'))
value={'status':'N1_LIMITED_ACCEPTED_N2_BLOCKED_FINAL_BYTES_VERIFIED','inputs':407,'source_package_files':68,'isolated_seed_files':75,
 'independent_output_files':98,'historical_preservation':history,'source_checks_for_nested_workers':source_checks,
 'N1_independent_rounds':1,'N2_N7_minimal_or_compatibility_reruns':0,'author_registered_processes':26,
 'own_checks_before_seal':len(parents),'own_N1_nested_children':4,'bootstrap_missing_PID_and_raw_streams_preserved':True,
 'overall_A03':'REWORK','I01_released':False,'report_sha256':sha(REPORT),'report_links':report_links,
 'commit_lineage':lineage,'lineage_argv':argv,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'final-checks.json',value)
print(json.dumps({'status':value['status'],'inputs':407,'generated':98,'history':history['count'],'own_parents_before_seal':len(parents),'nested':4}))
