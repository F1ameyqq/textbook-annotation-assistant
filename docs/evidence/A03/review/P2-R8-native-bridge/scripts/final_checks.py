# -*- coding: utf-8 -*-
"""Reconcile only frozen bytes, source identities and existing review records."""
import hashlib
import json
import subprocess
from archive_common import ROOT,OUT,REPORT,load,sha,write,links,preservation,own_processes
from evidence import EV,TARGET,raw,document

initial=load(OUT/'input-index.json')['exports'];supp=load(OUT/'supplemental-input-index.json')['files']
assert len(initial)==296 and len(supp)==10
rows=initial+supp
assert len({r['file'] for r in rows})==306
for row in rows:
    path=OUT/row['file'];body=path.read_bytes()
    assert len(body)==row['bytes'] and hashlib.sha256(body).hexdigest()==row['sha256']
    assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==row['raw_git_sha1']
assert {p.relative_to(OUT).as_posix() for p in (OUT/'input').rglob('*') if p.is_file()}=={r['file'] for r in rows}
assert sha(OUT/'input/workflow/docs/tasks/A03-P2-R8-native-bridge-implementation.md')=='b7dbf94ff06d8ba272b1bd20bf61afbe09fa1dd99c501dcb70f865ab36737721'
assert hashlib.sha256(raw(EV+'inputs/task.md')).hexdigest()=='b7dbf94ff06d8ba272b1bd20bf61afbe09fa1dd99c501dcb70f865ab36737721'
test='tests/test_a03_r8_native_bridge.py';test_digest=hashlib.sha256(raw(test)).hexdigest()
for group,label in [('N1-initial','bounded-01'),('N1-local-fix','bounded-02')]:
    pre=document(EV+'runs/'+group+'/preregistered.json')
    assert pre['script_pins'][test]==test_digest
    assert hashlib.sha256(raw(EV+'runs/'+group+'/script-snapshots/test_a03_r8_native_bridge.py')).hexdigest()==test_digest
    child=EV+'validation/'+label+'/processes/n1-child/'
    assert document(child+'preregistered.json')['script_sha256']==test_digest
    assert hashlib.sha256(raw(child+'script-snapshot.py')).hexdigest()==test_digest
    assert document(child+'started.json')['parent_pid']==document(EV+'runs/'+group+'/completed.json')['pid']
lineage_argv=['git','-c','core.longpaths=true','rev-list','--parents','--max-count=3',TARGET]
lineage=subprocess.run(lineage_argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.decode().splitlines()
expected=['fa6edeb7e9dd0c9502781747e5fce012931d9441 334577d922d224789191a8b4d7127513692ada95',
 '334577d922d224789191a8b4d7127513692ada95 352b1475fff85a034b839a712ee499ba4c1ec5e6',
 '352b1475fff85a034b839a712ee499ba4c1ec5e6 8ad45dd07214ae406a3fab28d76a4b5abd6eef03']
assert lineage==expected
history=preservation();parents=own_processes(skip=('final-verification-01',));assert len(parents)==6
assert load(OUT/'static-review.json')['status']=='REWORK_CONFIRMED_BY_STATIC_SOURCE_SCHEMA_AND_ACTUAL_LOGS'
assert load(OUT/'database-review.json')['status']=='THREE_FROZEN_DATABASES_IMMUTABLY_VERIFIED'
assert load(OUT/'database-review.json')['removed']
assert load(OUT/'process-and-compatibility-review.json')['record_count']==28
assert load(OUT/'artifact-boundary-review.json')['status']=='COMPUTED_UNADMITTED_RUN_AND_PREFIX_ARTIFACTS_CONFIRMED'
pending=tuple(OUT/name for name in ('process-release.json','final-verification.json','sha256-manifest.json'))
report_links=links(pending);assert sum(not r['exists'] for r in report_links)==3
assert not list(OUT.rglob('__pycache__'))
assert 'REWORK' in REPORT.read_text(encoding='utf8') and TARGET in REPORT.read_text(encoding='utf8')
value={'status':'R8_FINAL_BYTE_AND_EVIDENCE_RECONCILIATION_PASSED','input_files':len(rows),
 'raw_author_input_pins':89,'author_manifest_entries':462,'changed_raw_blobs_including_manifest':463,
 'historical_preservation':history,'own_runs_before_seal':len(parents),'author_processes':28,
 'N1_parent_and_child_script_identity_verified':test_digest,'commit_lineage':lineage,'lineage_argv':lineage_argv,
 'report_sha256':sha(REPORT),'report_links':report_links,
 'candidate_imports_native_API_compatibility_or_N1_reruns':0,
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'final-checks.json',value)
print(json.dumps({'status':value['status'],'inputs':len(rows),'historical_files':history['count'],'own_runs_before_seal':len(parents),'author_processes':28}))
