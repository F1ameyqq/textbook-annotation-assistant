import datetime, hashlib, json
from pathlib import Path

PUBLIC=Path(__file__).resolve().parent
PRIVATE=Path('D:/1800/.local/stages/a27-independent-20261023')
CANDIDATE=PRIVATE/'candidate-23591811'
sha=lambda data:hashlib.sha256(data).hexdigest()
def write_new(path,data):
    with path.open('xb') as stream: stream.write(data)
def encode(data): return (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def ref(path):
    data=path.read_bytes()
    return {'path':str(path),'bytes':len(data),'sha256':sha(data)}

intake=json.loads((PUBLIC/'raw-manifest.json').read_bytes())
for item in intake['members']:
    for key in ('source','copy'):
        data=Path(item[key]).read_bytes()
        assert (len(data),sha(data))==(item['bytes'],item['sha256']),item[key]
delivery=json.loads((CANDIDATE/'delivery/manifest.json').read_bytes())
product=json.loads((CANDIDATE/'delivery/product-manifest.json').read_bytes())
assert len(delivery['members'])==112 and len(product['members'])==32
for name,manifest in [('delivery',delivery),('product',product)]:
    for item in manifest['members']:
        data=(CANDIDATE/name/item['path']).read_bytes()
        assert (len(data),sha(data))==(item['bytes'],item['sha256'])
        if 'git_blob' in item:
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==item['git_blob']
prep=PUBLIC.parent/'preparation'
for line in (prep/'review-files.sha256').read_text(encoding='utf-8').splitlines():
    digest,name=line.split('  ',1)
    assert sha((prep/name).read_bytes())==digest
self_digest,_=(prep/'review-files.sha256.self').read_text(encoding='utf-8').strip().split('  ',1)
assert sha((prep/'review-files.sha256').read_bytes())==self_digest

control_root=PRIVATE/'test-output/independent-02'
control_files=[ref(path) for path in sorted(control_root.rglob('*')) if path.is_file()]
witness=control_root/'profile-alias-witness.json'
w=json.loads(witness.read_bytes())
assert w['same_directory_by_os_samefile'] is True and w['dispatched_commands']==['configure','capture']
assert w['result']['status']=='READBACK_MATCHED_AFTER_OS_RELEASE'
assert [item['matching_profile_processes'] for item in w['observations']]==[0,0]
controls={'schema':'A27IndependentSyntheticArtifacts/v1','synthetic_only':True,'root':str(control_root),'members':control_files,
          'witness':ref(witness),'profile_alias_does_not_identify_a_real_user_profile':True}
write_new(PUBLIC/'control-artifacts.json',encode(controls))
result={
 'schema':'A27IndependentFixedReviewResult/v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'REWORK','decision':'REWORK_PROFILE_EXCLUSIVITY_GATE',
 'product_commit':'23591811be71f9598c07c09b6a25a2a5fb066db0','base_commit':'389d2e7a282d21efa25db8d01c02d115ce9e83b7',
 'delivery_manifest_sha256':'0c3df2aef1c79edf019829008e3b417adc40c560affe5202fe7aa0418d0395ab',
 'source_copy_pairs_verified_and_rechecked':147,'raw_git_blob_dependencies_verified':32,'delivery_members_verified':112,
 'original_preparation_members_unchanged':7,
 'candidate_new_tests':{'run':'commands/author-new20','passed':20,'failed':0,'seconds':2.996},
 'author_affected_tests':{'passed':9,'evidence':'VERIFIED_ORIGINAL_OUTPUT_NOT_RERUN'},
 'independent_controls':{'distinct':7,'passed':6,'failed':1,'helper_errors_preserved':1,
    'first_run':{'I01':'PASS','I02':'PASS','I03':'HELPER_ERROR_BEFORE_PRODUCT_SUBPROCESS','I04_I07':'NOT_RUN'},
    'second_run':{'I03_I06':'PASS','I07':'FAIL'},'passed_controls_replayed':False,
    'fixed_a25_raw_copies_replayed':51,'further_product_testing_after_counterexample':'NOT_RUN'},
 'blocking_findings':[{'id':'R1','priority':1,'title':'Equivalent profile directory path bypasses exclusivity gate',
    'file':str(CANDIDATE/'product/tools/run_usense_postsave_readback.py'),'start':111,'end':113,
    'cause':'Only slash replacement and casefolded substring matching; no command argument/path equivalence validation',
    'witness':ref(witness),'same_directory_by_os_samefile':True,'reported_matching_profile_processes':[0,0],
    'actual_dispatch':['configure','capture'],'actual_result':'READBACK_MATCHED_AFTER_OS_RELEASE',
    'expected':'Reject occupied equivalent profile before configure/capture',
    'repair_scope':'Parse Windows profile argument and validate canonical directory identity or reject ambiguity; retain both observations and add actual-entry alias rejection control'}],
 'finite_findings':{
    'key_order_normal_batch_path':'OBSERVED_PASS_WITH_EXACT_LIMITED_STATUS_AND_NO_STANDARD_MARKER',
    'cooperative_cleanup_and_writer_cli':'OBSERVED_OFFLINE_PASS_WITH_SYNTHETIC_RUNTIME_ONLY',
    'synchronous_blocking_and_os_release':'EXISTING_OUTER_SUPERVISOR_STILL_REQUIRED_NOT_LIVE_TESTED',
    'recovery_before_resource_wrong_receipt_intent_or_release_rejections':'PASS',
    'recovery_second_observation_occupied':'PASS_CONFIGURE_ONLY_READER_NOT_RUN',
    'recovery_new_sidecar_as_standard_revision':'REJECTED',
    'whole_product_offline_acceptance':False},
 'historical_preservation':{'q3_strict_FAIL':True,'q4_framework_false':True,'q4_timeout_root_cause':'UNKNOWN',
    'q3_q4_standard_accepted_marker_created':False,'original_ledger_repaired':False,'old_authority_budget_reused':False,
    'five_saves_replayed':False,'author_initial_failures_preserved':4,'A26_delivery_not_blocked_by_this_review':True},
 'helper_error':{'original_script':ref(PUBLIC/'independent_controls.py'),'corrected_script':ref(PUBLIC/'independent_controls_v2.py'),
    'reason':'Windows subprocess audit executable field was None; reviewer audit hook rejected before product process launch',
    'correction':'Only add executable=sys.executable to the synthetic subprocess; original outputs retained; run previously unexecuted I03-I07 only'},
 'actual_actions':{'real_platform_requests':0,'browser_starts':0,'live_OS_process_observations':0,'real_profile_or_ledger_access':0,
    'author_active_workspace_access':0,'product_modifications':0,'old_194_suite_runs':0,'OCR_runs':0,'git_commits':0,
    'root_state_or_AGENTS_writes':0,'automation_access_or_changes':0,'messages_to_other_chats':0},
 'future_real_verification':'NOT_RUN_NO_NEW_LIVE_AUTHORITY','automation_1800_a':'PAUSED_REQUIRED_UNCHANGED_NOT_LIVE_REOBSERVED',
 'review_complete_and_released':True,'next':'Root sends minimal frozen R1 correction to the same independent review; no platform retry or historical ledger repair',
 'evidence':{'report':ref(PUBLIC/'report.md'),'raw_manifest':ref(PUBLIC/'raw-manifest.json'),'control_artifacts':ref(PUBLIC/'control-artifacts.json')}
}
write_new(PUBLIC/'result.json',encode(result))
files=[path for path in sorted(PUBLIC.rglob('*')) if path.is_file() and path.name not in ('review-files.sha256','review-files.sha256.self')]
lines=[sha(path.read_bytes())+'  '+path.relative_to(PUBLIC).as_posix() for path in files]
manifest=('\n'.join(lines)+'\n').encode('utf-8')
write_new(PUBLIC/'review-files.sha256',manifest)
write_new(PUBLIC/'review-files.sha256.self',(sha(manifest)+'  review-files.sha256\n').encode('ascii'))
print(json.dumps({'status':result['status'],'public_members':len(files),'private_control_members':len(control_files),
    'source_copy_pairs_rechecked':147,'result_sha256':sha((PUBLIC/'result.json').read_bytes()),
    'report_sha256':sha((PUBLIC/'report.md').read_bytes()),'manifest_sha256':sha(manifest)}))
