"""Verify preserved failure package bytes only; no corrective or functional work."""
import hashlib
from pathlib import Path
from failure_archive_common import ROOT,OUT,REPORT,load,sha,write,parents,git_records,nested_records,history,links
from evidence import WORK,TARGET,author_read
index=load(OUT/'input-index.json')['exports']
for r in index:
    p=OUT/r['file'];b=p.read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['raw_git_sha1']
seed=load(OUT/'isolated-source-index.json')['files'];root=Path(load(OUT/'independent-run.json')['run_root'])
for r in seed:assert sha(OUT/r['file'])==r['sha256']
generated={p.relative_to(OUT).as_posix() for p in root.rglob('*') if p.is_file()}
assert {p.relative_to(OUT).as_posix() for p in WORK.rglob('*') if p.is_file()}=={r['file'] for r in seed}|generated
pre=load(OUT/'driver-preregistration.json')
for name,digest in pre['scripts'].items():assert sha(OUT/'scripts'/name)==digest
assert {p.name for p in (root/'cases').iterdir()}=={'F1','F2','F3','F4'}
times=[]
for g in ('F1','F2','F3','F4'):
    r=load(OUT/('result-'+g+'.json'));assert r['functional_rounds']==1 and r['exit_code']==0
    d=OUT/'runs'/('independent-'+g.lower()+'-01');pr=load(d/'registration.json');end=load(d/'completion.json')
    assert pr['entry_sha256']==pre['driver_sha256'] and pr['timeout_seconds']==90
    times.append((pr['registered_at_ns'],end['finished_at_ns']))
assert all(times[i][1]<times[i+1][0] for i in range(3))
audit=load(OUT/'case-and-boundary-review.json');assert audit['independent_stage_raw_files']==32 and len(audit['all_SQL_audits'])==64
for r in audit['all_SQL_audits']:
    if r['label'].startswith('author-'):body=author_read(r['source'])
    else:
        p=Path(r['source']);p=p if p.is_absolute() else WORK/p;assert p.resolve().is_relative_to(root);body=p.read_bytes()
    assert hashlib.sha256(body).hexdigest()==r['sha256_before_after'] and r['quick_check']=='ok'
proc=load(OUT/'process-and-import-review.json');assert proc['author_process_count']==19 and proc['independent_nested_count']==14
correction=load(OUT/'post-functional-metadata-correction.json')
assert correction['correction_count']==1 and correction['product_calls']==correction['functional_reruns']==0
assert sha(OUT/'scripts/process_review.py')==correction['corrected_source_sha256']
assert sha(OUT/'scripts/write_report.py')==sha(OUT/'runs/report-01/entry-source.py')
assert 'SyntaxError' in (OUT/'runs/report-01/stderr.log').read_text(encoding='utf8')
assert not (OUT/'coverage-map.json').exists() and not list(OUT.rglob('__pycache__')) and not (OUT/'immutable-audit-copies').exists()
outcome=load(OUT/'final-outcome.json');assert outcome['status']=='REWORK' and not outcome['second_failure_corrected_or_retried']
report=REPORT.read_text(encoding='utf8');assert '**REWORK**' in report and 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION' in report
prior=history();par=parents(skip=('failure-package-check-01',));git=git_records();nested=nested_records()
pending=tuple(OUT/n for n in ('process-release.json','final-verification.json','sha256-manifest.json'))
write(OUT/'failure-package-check.json',{'status':'REWORK_FAILURE_PACKAGE_BYTES_VERIFIED','target':TARGET,'report_sha256':sha(REPORT),
 'input_files':len(index),'source_seed_files_unchanged':len(seed),'generated_files':len(generated),'historical_preservation':prior,
 'parent_records_before_check':len(par),'git_records':len(git),'nested_records':len(nested),'report_links':links(pending),
 'functional_failures':0,'functional_reruns':0,'metadata_failures_retained':2,'static_corrections':1,
 'normal_acceptance_closure_stopped':True,'auditor_product_calls':0})
print('{"status":"REWORK_FAILURE_PACKAGE_BYTES_VERIFIED","product_calls":0}')
