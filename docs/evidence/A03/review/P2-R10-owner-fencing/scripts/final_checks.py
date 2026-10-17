# -*- coding: utf-8 -*-
"""Byte-only final check; no product imports, reruns, SQL or OS scan."""
import hashlib
from pathlib import Path
from datetime import datetime
from archive_common import OUT,REPORT,FIELD_RESET,load,sha,write,links,preservation,parents,git_records,nested_records
from evidence import WORK,EV,TARGET,MAP
index=load(OUT/'input-index.json')['exports'];assert len(index)==len({r['file'] for r in index})==356
for r in index:
    b=(OUT/r['file']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['raw_git_sha1']
assert {p.relative_to(OUT).as_posix() for p in (OUT/'input').rglob('*') if p.is_file()}=={r['file'] for r in index if r['file'].startswith('input/')}
source=load(OUT/'isolated-source-index.json')['files'];assert len(source)==76
for r in source:assert (OUT/r['file']).stat().st_size==r['bytes'] and sha(OUT/r['file'])==r['sha256']
identity=load(OUT/'independent-run.json');root=Path(identity['run_root']).resolve();assert root.is_relative_to(WORK)
generated={p.relative_to(OUT).as_posix() for p in root.rglob('*') if p.is_file()};assert len(generated)==110
assert {p.relative_to(OUT).as_posix() for p in WORK.rglob('*') if p.is_file()}=={r['file'] for r in source}|generated
delivery=load(OUT/'delivery-byte-index.json');assert delivery['old_entries']==delivery['old_entries_preserved']==32152 and delivery['modified_old_paths']==[]
assert delivery['changed_paths']==delivery['added_paths']==261 and delivery['manifest_entries']==260 and len(delivery['verified_input_pins'])==4 and len(delivery['verified_base_references'])==11
static=load(OUT/'static-review.json');assert static['exact_driver_unmodified'] and static['live_process_barriers_and_lifecycle_reviewed'] and static['schema_pins']==6 and static['implementation_pins']==23
driver=load(OUT/'driver-preregistration.json');assert driver['frozen_before_functional_execution'] and driver['driver_changes']==driver['product_changes']==driver['product_calls_in_preparation']==0
assert driver['driver_sha256']=='da15d84be77fb9be7b718ff28721647a6b3c4052b32531cae45768394c798a82'
times=[]
for group in ('C1','C2'):
    result=load(OUT/('result-'+group+'.json'));assert result['exit_code']==0 and result['functional_rounds']==1 and not result['other_groups_replayed']
    d=OUT/'runs'/('independent-'+group.lower()+'-01');pre=load(d/'registration.json');end=load(d/'completion.json')
    assert pre['entry_sha256']==driver['driver_sha256'] and pre['input_index_sha256']==sha(OUT/'input-index.json') and pre['source_index_sha256']==sha(OUT/'isolated-source-index.json') and pre['timeout_seconds']==90
    times.append((datetime.fromisoformat(pre['registered_at']),datetime.fromisoformat(end['finished_at'])))
assert times[0][1]<times[1][0]
audit=load(OUT/'case-and-timeline-review.json');assert audit['status']=='ACCEPTED_OWNER_FENCING_TWO_CASES_ONLY' and audit['unique_immutable_DB_copies']==8 and audit['original_DB_connections']==audit['auditor_product_calls']==0
assert {(c['label'],c['group']) for c in audit['cases']}=={(l,g) for l in ('author','independent') for g in ('C1','C2')}
for c in audit['cases']:
    assert c['effects']==0 and c['business_rows_plans_actions_intents_permits']==[0,0,0,0] and c['auditor_product_calls']==0
    for role in ('runtime','target'):
        r=c[role];assert r['source_sha256_before_after']==r['copy_sha256_before_after'] and r['copy_removed'] and r['quick_check']=='ok'
assert not (OUT/'immutable-audit-copies').exists()
author=load(OUT/'author-process-review.json');assert author['process_count']==len(author['records'])==8 and author['product_calls_by_auditor']==0
# Check only actual import evidence. No synthetic exit record or file count is created.
module_count=0
for path in sorted((root/'imports').glob('*.json')):
    data=load(path)
    for name,m in data['modules'].items():
        p=Path(m['path']).resolve();assert p.is_relative_to(WORK);source_path=p.relative_to(WORK).as_posix()
        assert sha(p)==m['sha256']==MAP[(TARGET,source_path)]['sha256'];module_count+=1
prep=load(OUT/'preparation-tool-failure.json');assert prep['product_calls']==prep['functional_processes_started']==0 and prep['pid'] is None and not prep['raw_separated_streams']
assert {p.name for p in (root/'cases').iterdir()}=={'C1','C2'}
assert not (WORK/'docs/evidence/A03/execution/P2-R8-R3-post-hold/validation').exists() and not list(OUT.rglob('__pycache__'))
for p in root.rglob('*'):
    if p.is_file() and p.name.endswith(('-wal','-journal')):assert p.stat().st_size==0
own_parents=parents(skip=('final-verification-01',));helpers=git_records();nested=nested_records()
assert len(own_parents)==5 and len(helpers)==6
history=preservation();report=REPORT.read_text(encoding='utf8')
for c in audit['cases']:
    if c['label']!='independent':continue
    for role in ('runtime','target'):assert c[role]['source_sha256_before_after'] in report
    for name in ('plan_ref','PRE_ref'):
        if name in c:assert c[name]['artifact_id'] in report and c[name]['content_hash'] in report
assert FIELD_RESET in report and 'ACCEPTED_OWNER_FENCING_TWO_CASES_ONLY' in report
pending=tuple(OUT/n for n in ('process-release.json','final-verification.json','sha256-manifest.json'));refs=links(pending);assert sum(not r['exists'] for r in refs)==3
write(OUT/'final-checks.json',{'status':'ACCEPTED_OWNER_FENCING_TWO_CASES_ONLY_BYTES_VERIFIED','inputs':356,'source_files_unchanged':76,'generated_files':110,
 'historical_preservation':history,'groups_each_once':['C1','C2'],'post_functional_failures_or_corrections':0,'own_checks_before_seal':len(own_parents),
 'actual_nested_children':len(nested),'actual_git_children':len(helpers),'actual_import_module_records_verified':module_count,
 'pre_functional_preparation_transcript_limit_preserved':True,'report_sha256':sha(REPORT),'report_links':refs,
 'whole_A03':'REWORK','I01_released':False,'field_reset':FIELD_RESET})
print('{"status":"ACCEPTED_OWNER_FENCING_TWO_CASES_ONLY_BYTES_VERIFIED","inputs":356,"generated":110,"post_functional_corrections":0}')
