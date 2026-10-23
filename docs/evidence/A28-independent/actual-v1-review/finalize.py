import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
P=Path('D:/1800/.local/stages/a28-independent-20261023/actual-v1-review')
O=Path('D:/1800/docs/evidence/A28-independent/actual-v1-review')
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def put(p,v):
 b=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
 with p.open('xb') as f:f.write(b)
 return sha(b)
v=json.loads((O/'verification.json').read_bytes());assert v['status']=='PASS_FIXED_FOUR_SAVES_FRESH_READBACKS_AND_OWN_RELEASE'
private=[ref(p) for p in sorted(P.rglob('*')) if p.is_file()]
put(O/'private-artifact-manifest.json',{'schema':'A28IndependentActualPrivateManifest/v1','count':len(private),'members':private})
result={'schema':'A28IndependentActualResult/v1','status':'ACCEPTED_FIXED_FOUR_SAVES_FRESH_READBACKS_AND_OWN_RELEASE_ONLY',
 'completed_at':datetime.now(timezone.utc).isoformat(),'reviewer_thread_id':'01a16910-8c4e-7803-9347-87ab6798b358',
 'commit':v['commit'],'authority_id':v['authority_id'],'root_index_sha256':'faf288875e625d8331992641a264e533bb9d32d9b3c9d451c04202585cf81d77',
 'fixed_actual_sha256':'ef96bef35658cb61c9030981b6db5525de00098178b32719888c64f9543a493e',
 'actual_raw_manifest_sha256':'d81fc12ee2a2d8bf106835f77a04057648584e951fb8a0dea39b1873113c0d75',
 'root_raw_pairs':306,'actual_raw_members':304,'unique_posts':4,'fresh_complete_readbacks':4,'writer_business_gets':52,'reader_business_gets':122,
 'business_gets':174,'new_frames':14,'new_identity_and_content_preservation':'PASS','tail_shift_to_native27':'PASS',
 'old_five_content':'PRIOR_A25_A26_ACCEPTANCE_REUSED_NO_RESEND_NO_NEW_GET','cumulative_logical_units':9,
 'framework_releases':8,'held_process_identity_releases':121,'whole_job_active_processes_after':0,'production_wall_clock_seconds':42.639465,
 'per_question_command_continuations':0,'single_batch_launch':True,'user_zero_intervention_evidence':'AUTHOR_DECLARATION_AND_NO_AUTOMATIC_LOGIN_RECORD_NOT_INDEPENDENT_ACTIVITY_TELEMETRY',
 'old_ledger_preservation_evidence':'FINAL_BATCH_RECHECK_AND_FIXED_AUTHOR_POSTRUN_HASH_DECLARATION_NO_POSTRUN_OLD_LEDGER_RAW_COPIES',
 'native_export_display_and_package':'NOT_ACCEPTED_IN_THIS_ACTUAL_INCREMENT','old15_info_raw_limitation_preserved':True,
 'review_helper_errors_preserved':2,'helper_first_failure_successors':'NOT_RUN_UNTIL_HELPER_CORRECTION','product_failures_found':0,
 'platform_calls':0,'old_tests_rerun':0,'active_author_or_export_reads':0,'authority_remaining':0,
 'reports':{n:ref(O/n) for n in ('report.md','intake.json','root-binding.json','verification.json','verification-failure.json','verification-failure-corrected1.json','private-artifact-manifest.json')}}
result_sha=put(O/'result.json',result)
public=[ref(p) for p in sorted(O.iterdir()) if p.is_file() and p.name!='report-manifest.json']
manifest_sha=put(O/'report-manifest.json',{'schema':'A28IndependentActualReportManifest/v1','count':len(public),'members':public,'self_hash_excluded':True})
for r in private+public:
 b=Path(r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
print(json.dumps({'status':result['status'],'result_sha256':result_sha,'report_manifest_sha256':manifest_sha,'reports':len(public),'private_artifacts':len(private)}))
