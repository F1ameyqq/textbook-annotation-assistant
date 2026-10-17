# -*- coding: utf-8 -*-
"""First final byte reconciliation, not a rerun or repair of failed collector."""
import hashlib
from pathlib import Path
from datetime import datetime
from archive_common import OUT,REPORT,FIELD_RESET,load,sha,write,links,preservation,processes,git_processes,nested_records
from evidence import WORK,EV,TARGET,MAP,raw
index=load(OUT/'input-index.json')['exports'];assert len(index)==len({r['file'] for r in index})==585
for r in index:
    b=(OUT/r['file']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['raw_git_sha1']
assert {p.relative_to(OUT).as_posix() for p in (OUT/'input').rglob('*') if p.is_file()}=={r['file'] for r in index if r['file'].startswith('input/')}
source=load(OUT/'review-source-index.json')['files'];assert len(source)==78
for r in source:assert (OUT/r['file']).stat().st_size==r['bytes'] and sha(OUT/r['file'])==r['sha256']
identity=load(OUT/'independent-run.json');root=Path(identity['run_root']).resolve();assert root.is_relative_to(WORK)
generated={p.relative_to(OUT).as_posix() for p in root.rglob('*') if p.is_file()};assert len(generated)==403
assert {p.relative_to(OUT).as_posix() for p in WORK.rglob('*') if p.is_file()}=={r['file'] for r in source}|generated
delivery=load(OUT/'delivery-byte-index.json');assert delivery['old_entries']==31665 and delivery['old_entries_preserved']==31661 and len(delivery['modified_old_paths'])==4
assert delivery['changed_paths']==491 and delivery['manifest_entries']==490 and len(delivery['verified_input_pins'])==4 and len(delivery['verified_base_references'])==12
static=load(OUT/'static-review.json');assert static['legacy_body_text_unchanged'] and static['report_transactions_fenced']==3 and static['schema_pins']==6 and static['implementation_pins']==23
own=load(OUT/'independent-driver.json');assert own['frozen_before_first_product_run'] and not own['candidate_original_modified'] and own['product_calls_in_preparation']==0
assert sha(OUT/own['file'])==own['sha256']=='71357a70360ddd9228ff20fce908c790be7935ebcc8b63b63aad15a84f2805b4'
times=[]
for g in ('D1','standalone','borrow','D2'):
    result=load(OUT/('result-'+g+'.json'));assert result['exit_code']==0 and result['functional_rounds']==1 and not result['other_groups_or_prior_R3_R4_replayed']
    d=OUT/'runs'/('independent-'+g.lower()+'-01');pre=load(d/'registration.json');end=load(d/'completion.json')
    assert pre['entry_sha256']==own['sha256'] and pre['source_index_sha256']==sha(OUT/'review-source-index.json') and pre['input_index_sha256']==sha(OUT/'input-index.json')
    assert pre['timeout_seconds']==90;times.append((datetime.fromisoformat(pre['registered_at']),datetime.fromisoformat(end['finished_at'])))
assert all(times[i][1]<times[i+1][0] for i in range(3))
cases=load(OUT/'case-boundaries-review.json');assert cases['status']=='FOUR_INDEPENDENT_GROUPS_FORMAL_BINDINGS_VERIFIED'
assert len(cases['author_cases'])==3 and len(cases['independent_cases'])==4 and cases['unique_final_or_before_DB_copies']==18 and cases['original_DB_connections']==cases['product_calls_by_auditor']==0
assert [c['effect_count'] for c in cases['independent_cases']]==[1,1,1,0] and [c['report_read_count'] for c in cases['independent_cases']]==[1,1,1,0]
assert [c['plan_status'] for c in cases['independent_cases']]==['FINISHED','FINISHED','FINISHED','INTERRUPTED']
for case in cases['author_cases']+cases['independent_cases']:
    for role in ('runtime','target'):
        r=case[role];assert r['source_sha256_before_after']==r['copy_sha256_before_after'] and r['quick_check']=='ok' and r['copy_removed']
    assert case['native_API_calls_by_auditor']==0
for r in cases['independent_before_DB_copies']:assert r['source_sha256_before_after']==r['copy_sha256_before_after'] and r['copy_removed']
ownership=load(OUT/'ownership-boundaries-review.json');assert ownership['status']=='STANDALONE_AND_BORROWED_LIFECYCLES_AND_SINGLE_READ_VERIFIED' and ownership['extra_observations_reports_effects_after_refusal']==0
assert ownership['exact_error']['code']=='STORAGE_TRANSACTION_FAILED' and ownership['exact_error']['context_type']=='IntegrityError'
classification=load(OUT/'author-failure-classification.json');assert classification['status']=='AUTHOR_BORROW_DRIVER_EXCEPTION_EXPECTATION_ERROR_CONFIRMED' and classification['original_borrow']=='FAILED' and classification['original_D2']=='NOT_RUN'
author=load(OUT/'author-process-review.json');assert len(author['records'])==15 and author['author_borrow']=='FAILED_PRESERVED' and author['author_D2']=='NOT_RUN'
assert hashlib.sha256(raw(EV+'validation/owner-r1-01/processes/borrow-execute/stderr.txt')).hexdigest()=='bc895733e5e37d479f5da9c57f73b29f23694a30a5b09e02a833a11cc7436fb5'
correction=load(OUT/'metadata-audit-correction.json');assert correction['first_pid']==41640 and correction['extra_product_calls_or_reruns']==0
assert sha(OUT/'scripts/audit_cases.py')==sha(OUT/'runs/case-boundaries-review-02/entry-source.py')
limit=load(OUT/'archive-collector-limitation.json');assert limit['exit_code']==1 and limit['pid']==61204 and not limit['additional_correction_or_collector_rerun']
assert sha(OUT/'scripts/collect_release.py')==sha(OUT/'runs/release-review-01/entry-source.py')
# Existing records are archived as they are; no missing post-exit file is created.
post_exit=sorted((root/'imports').glob('*.json'));assert len(post_exit)==5
prefault=load(root/'cases/D2/before-run.json')['imports'];assert prefault['pid']==60824
module_records=[load(p) for p in post_exit]+[prefault]
for data in module_records:
    for name,m in data['modules'].items():
        p=Path(m['path']).resolve();assert p.is_relative_to(WORK);rel=p.relative_to(WORK).as_posix()
        expected=own['sha256'] if p==OUT/own['file'] else MAP[(TARGET,rel)]['sha256'];assert sha(p)==m['sha256']==expected
assert not (root/'imports/D2-execute.json').exists()
assert {p.name for p in (root/'cases').iterdir()}=={'D1','standalone','borrow','D2'}
for old in ('P2-R8-R3-post-hold','P2-R9-minimal-demos'):assert not (WORK/'docs/evidence/A03/execution'/old/'validation').exists()
assert not list(OUT.rglob('__pycache__')) and not (OUT/'immutable-case-copies').exists() and not (OUT/'classification-copies').exists()
for p in root.rglob('*'):
    if p.is_file() and p.name.endswith(('-wal','-journal')):assert p.stat().st_size==0
nested=nested_records();helpers=git_processes();parents=processes(skip=('final-verification-01',));assert len(parents)==10 and len(nested)==16
history=preservation();report=REPORT.read_text(encoding='utf8')
for c in cases['independent_cases']:
    for role in ('runtime','target'):assert c[role]['source_sha256_before_after'] in report
    for name in ('POST_ref','Batch_ref','resolution_ref'):
        if name in c:assert c[name]['artifact_id'] in report and c[name]['content_hash'] in report
assert FIELD_RESET in report and 'I01 未释放' in report and '未再修改或运行' in report
pending=tuple(OUT/n for n in ('process-release.json','final-verification.json','sha256-manifest.json'));refs=links(pending);assert sum(not r['exists'] for r in refs)==3
write(OUT/'final-checks.json',{'status':'FOUR_GROUPS_LIMITED_ACCEPTED_BYTES_VERIFIED_COLLECTOR_FAILURE_RETAINED','inputs':585,'source_driver_files':78,
 'generated_files':403,'historical_preservation':history,'four_groups_once':['D1','standalone','borrow','D2'],'own_checks_before_seal':10,
 'known_nested_children':16,'known_git_children':5,'review_failures_retained':['case-boundaries-review-01','release-review-01'],
 'post_functional_audit_corrections':1,'collector_corrected_or_rerun':False,'collector_did_not_pass':True,
 'actual_import_evidence':'five post-child records plus D2 before-run imports; no fabricated D2 exit record',
 'author_borrow':'FAILED_PRESERVED','author_D2':'NOT_RUN','overall_A03':'REWORK','I01_released':False,
 'report_sha256':sha(REPORT),'report_links':refs,'field_reset':FIELD_RESET})
print('{"status":"FOUR_GROUPS_LIMITED_ACCEPTED_BYTES_VERIFIED_COLLECTOR_FAILURE_RETAINED","inputs":585,"generated":403,"nested":16,"product_reruns":0}')
