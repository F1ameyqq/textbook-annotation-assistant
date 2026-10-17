# -*- coding: utf-8 -*-
"""Final byte-only reconciliation; no candidate/native/test reruns or database reopening."""
import hashlib
import json
import subprocess
from archive_common import ROOT,OUT,REPORT,load,sha,write,links,preservation,own_processes
from evidence import EV,TARGET,BASE,raw,document
index=load(OUT/'input-index.json')['exports'];assert len(index)==339
assert len({r['file'] for r in index})==339
for row in index:
    p=OUT/row['file'];b=p.read_bytes()
    assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['raw_git_sha1']
assert {p.relative_to(OUT).as_posix() for p in (OUT/'input').rglob('*') if p.is_file()}=={r['file'] for r in index}
history=preservation();assert history['count']==4252
delivery=load(OUT/'delivery-byte-index.json');assert delivery['manifest_entries']==507 and delivery['changed_paths']==508
assert delivery['old_entries_preserved']==29198 and len(delivery['modified_old_paths'])==3
static=load(OUT/'static-review.json');boundary=load(OUT/'boundary-and-binding-review.json');db=load(OUT/'database-review.json');process=load(OUT/'process-review.json')
assert static['status']=='PRODUCER_GAP_CLOSED_WITH_FROZEN_EVIDENCE_RUNTIME_BLOCKER_CONFIRMED_STATICALLY'
assert static['candidate_imports_native_API_or_tests']==0
assert boundary['status']=='ACTUAL_ADMISSION_EFFECT_UNKNOWN_HEAD_AND_MISMATCH_CONFIRMED'
assert boundary['actual_PRE']['status']=='ADMITTED' and boundary['effect_count']==1 and boundary['current_intent_receipt'] is None
assert boundary['guard_comparison']['inequality_terms']=={'plan_ref':False,'action_id':False,'intent_ref':False,'attempt_fact':True}
assert not boundary['guard_comparison']['failed_progress_persisted']
assert db['removed'] and len(db['copies'])==2 and db['candidate_API_calls']==0
for record in db['copies']:
    assert hashlib.sha256(raw(record['source'])).hexdigest()==record['source_sha256']==record['copy_sha256_before']==record['copy_sha256_after']
assert len(process['records'])==23 and len(process['C01_expected_rejections'])==3
assert [r['tests'] for r in process['compatibility']]==[70,52,13]
assert process['candidate_tests_or_native_API_rerun']==0
assert document(EV+'bounded-outcome.json')['N2_N7']=='NOT_RUN_AFTER_NEW_INDEPENDENT_PRODUCT_BLOCKER'
paths=[r['path'] for r in delivery['files']]
assert not [p for p in paths if p.startswith(EV+'validation/') and '/cases/N' in p and '/cases/N1/' not in p]
assert not [p for p in paths if p.startswith(EV) and p.endswith('/N1-result.json')]
argv=['git','-c','core.longpaths=true','rev-list','--parents','--ancestry-path',BASE+'..'+TARGET]
lineage=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.decode().splitlines()
assert lineage[0].split()[0]==TARGET and '613952f170167551b6f935d93cc9f007e6aa7221' in {r.split()[0] for r in lineage}
own=own_processes(skip=('final-verification-01',));assert len(own)==4
pending=tuple(OUT/name for name in ('process-release.json','final-verification.json','sha256-manifest.json'))
report_links=links(pending);assert sum(not r['exists'] for r in report_links)==3
assert not list(OUT.rglob('__pycache__'))
report=REPORT.read_text(encoding='utf8');assert '整体 REWORK' in report and TARGET in report
for a in boundary['persisted_progress']:
    assert a['ref']['artifact_id'] in report and a['ref']['content_hash'] in report
value={'status':'R8_R1_FINAL_BYTE_AND_EVIDENCE_RECONCILIATION_PASSED','input_files':len(index),
 'historical_preservation':history,'author_manifest_entries':507,'changed_blobs':508,'author_processes':23,
 'own_checks_before_seal':len(own),'producer_gap':'CLOSED_LIMITED_TO_COVERAGE_FIX','overall':'REWORK',
 'current_boundary':'ADMITTED PRE / 1 effect / UNKNOWN preserved / terminal head and RECOVERY fact persisted / new progress rejected',
 'lineage_argv':argv,'commit_lineage':lineage,'report_sha256':sha(REPORT),'report_links':report_links,
 'candidate_imports_native_API_or_tests_rerun':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'final-checks.json',value)
print(json.dumps({'status':value['status'],'inputs':len(index),'historical_files':history['count'],
 'author_processes':23,'own_checks_before_seal':len(own),'candidate_runs':0}))
