# -*- coding: utf-8 -*-
"""Reconcile existing evidence bytes, never import candidate or reopen SQL."""
import hashlib
from archive_common import OUT,REPORT,FIELD_RESET,load,sha,write,links,preservation,processes,git_processes
from evidence import raw,EV,TARGET,BASE
index=load(OUT/'input-index.json')['exports'];assert len(index)==len({r['file'] for r in index})==273
for r in index:
    p=OUT/r['file'];b=p.read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['raw_git_sha1']
assert {p.relative_to(OUT).as_posix() for p in (OUT/'input').rglob('*') if p.is_file()}=={r['file'] for r in index}
delivery=load(OUT/'delivery-byte-index.json');assert delivery['old_entries']==delivery['old_entries_preserved']==31482 and not delivery['modified_old_paths']
assert delivery['added_paths']==183 and delivery['manifest_entries']==182 and len(delivery['verified_input_pins'])==5 and len(delivery['verified_base_references'])==11
db=load(OUT/'database-review.json');assert db['status']=='IMMUTABLE_OWN_COPIES_AND_FORMAL_FAILURE_BINDINGS_VERIFIED'
assert db['effects_before_after']==[0,1] and db['attempt_fact']=='ATTEMPTED' and db['POST_Batch_report_reads']==[0,0,0]
assert db['receipt_three_way_registration'] and db['native_API_calls']==db['original_DB_connections']==0
for r in db['copies'].values():
    assert r['source_sha256_before']==r['source_sha256_after']==r['copy_sha256_before_after']==hashlib.sha256(raw(r['source'])).hexdigest()
    assert r['copy_removed'] and r['quick_check']=='ok'
assert not (OUT/'immutable-copies').exists()
proc=load(OUT/'process-and-source-review.json');assert {r['pid']:r['exit_code'] for r in proc['records']}=={42924:1,61832:1,21684:0,22652:0}
assert proc['metadata_failure_PID_raw_stream_limit_preserved'] and proc['product_calls_by_reviewer']==0
assert proc['original_TypeError_transcript']['product_calls']==0 and proc['original_TypeError_transcript']['exit_code']==1
assert hashlib.sha256(raw(EV+'validation/r9-01/processes/D1-execute/stderr.txt')).hexdigest()=='0db6947c2321a6a6fe42b68486f7dc0f0cd7e5340a50a6f412f013fe9fc4852d'
fault=load(OUT/'fault-review.json');assert fault['status']=='PRODUCT_OWNERSHIP_LIFECYCLE_DEFECT_CONFIRMED_NO_REEXECUTION' and fault['D1_D2']=='NOT_ACCEPTED' and fault['overall_A03']=='REWORK' and not fault['I01_released']
assert len(fault['affected_existing_implementation_pins'])==2 and len(fault['necessary_future_revalidation_only'])==4
scope=load(OUT/'review-scope.json');assert scope['product_imports_calls_or_runs']==scope['D1_D2_replays']==scope['subagents']==0 and scope['field_reset']==FIELD_RESET
note=load(OUT/'reviewer-preparation-note.json');assert note['pid']==49088 and note['exit_code']==1 and note['follow_up_exit_code']==0 and note['extra_product_calls']==0
history=preservation();parents=processes(skip=('final-verification-01',));assert len(parents)==3;helpers=git_processes()
assert not list(OUT.rglob('__pycache__'))
report=REPORT.read_text(encoding='utf8')
for k in ('plan_ref','intent_ref','receipt_ref'):assert db[k]['artifact_id'] in report and db[k]['content_hash'] in report
assert db['action_id'] in report and db['action_digest'] in report and FIELD_RESET in report and 'I01未释放' in report
pending=tuple(OUT/n for n in ('process-release.json','final-verification.json','sha256-manifest.json'))
references=links(pending);assert sum(not r['exists'] for r in references)==3
write(OUT/'final-checks.json',{'status':'FROZEN_PRODUCT_FAULT_CONFIRMED_BYTES_VERIFIED','target':TARGET,'base':BASE,'inputs':273,
 'historical_preservation':history,'own_review_checks_before_seal':3,'owned_git_children':5,'retained_reviewer_assertion_failures':1,
 'original_registered_processes':4,'four_DB_copies_reconciled':True,'original_D1_failure_and_metadata_TypeError_preserved':True,
 'product_calls_D1_D2_reruns_or_subagents':0,'D1_D2':'NOT_ACCEPTED','overall_A03':'REWORK','I01_released':False,
 'report_sha256':sha(REPORT),'report_links':references,'field_reset':FIELD_RESET})
print('{"status":"FROZEN_PRODUCT_FAULT_CONFIRMED_BYTES_VERIFIED","inputs":273,"old_review_files":7030,"product_calls":0}')
