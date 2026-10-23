import datetime,hashlib,json
from pathlib import Path
PUBLIC=Path(__file__).resolve().parent
PRIVATE=Path('D:/1800/.local/stages/a27-independent-20261023')
sha=lambda b:hashlib.sha256(b).hexdigest()
def encode(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def write_new(path,value):
    with path.open('xb') as stream:stream.write(value)
def ref(path):
    data=path.read_bytes();return {'path':str(path),'bytes':len(data),'sha256':sha(data)}
intake=json.loads((PUBLIC/'raw-manifest.json').read_bytes())
prior=PUBLIC.parent/'fixed-review'
old=json.loads((prior/'raw-manifest.json').read_bytes())
for manifest in (intake,old):
    for item in manifest['members']:
        for key in ('source','copy'):
            data=Path(item[key]).read_bytes()
            assert (len(data),sha(data))==(item['bytes'],item['sha256'])
preserved_reports={}
for root in (prior,PUBLIC.parent/'preparation'):
    lines=(root/'review-files.sha256').read_text(encoding='utf-8').splitlines()
    for line in lines:
        digest,name=line.split('  ',1);assert sha((root/name).read_bytes())==digest
    digest,_=(root/'review-files.sha256.self').read_text(encoding='utf-8').strip().split('  ',1)
    assert sha((root/'review-files.sha256').read_bytes())==digest
    preserved_reports[root.name]=len(lines)
old_controls=json.loads((prior/'control-artifacts.json').read_bytes())
for item in old_controls['members']:
    data=Path(item['path']).read_bytes();assert (len(data),sha(data))==(item['bytes'],item['sha256'])
prior_result=json.loads((prior/'result.json').read_bytes());assert prior_result['status']=='REWORK'
source=PRIVATE/'candidate-ebca4c71'
bound=source/'delivery/frozen-review-inputs'
for leaf in ('report.md','result.json','independent_controls_v2.py','control-artifacts.json'):
    assert (bound/leaf).read_bytes()==(prior/leaf).read_bytes()
original_witness=PRIVATE/'test-output/independent-02/profile-alias-witness.json'
assert (bound/'profile-alias-witness.json').read_bytes()==original_witness.read_bytes()
assert sha(original_witness.read_bytes())=='616fd5b65ed843a4446bd0651696281c9d766cccebccd5bb273f8eaf22fe5824'
witness_path=PRIVATE/'r1-test-output/r1-original-i07/profile-alias-witness.json'
w=json.loads(witness_path.read_bytes())
assert w['same_directory_by_os_samefile'] is True and w['dispatched_commands']==[] and w['raised']=='RECOVERY_PROFILE_IN_USE'
assert w['result'] is None and w['intent_unchanged'] is True
proof_path=PRIVATE/'r1-test-output/r1-independent3/different-profile-entry-result.json'
proof=json.loads(proof_path.read_bytes())
assert proof['calls']==['configure','capture'] and proof['posts']==0 and proof['ledger_unchanged'] is True and proof['repeat_dispatch_blocked'] is True
controls=[]
for label in ('r1-new8','r1-original-i07','r1-independent3'):
    process=json.loads((PUBLIC/'commands'/label/'process.json').read_bytes())
    assert process['exit_code']==0 and process['timeout'] is False
    for name in ('stdout','stderr'):
        assert sha((PUBLIC/'commands'/label/name).read_bytes())==process[name+'_sha256']
    controls.extend(ref(path) for path in sorted((PRIVATE/'r1-test-output'/label).rglob('*')) if path.is_file())
write_new(PUBLIC/'control-artifacts.json',encode({'schema':'A27IndependentR1SyntheticArtifacts/v1','synthetic_only':True,
    'members':controls,'original_I07_new_candidate':ref(witness_path),'distinct_directory_actual_entry':ref(proof_path)}))
result={
 'schema':'A27IndependentR1AndTotalFiniteResult/v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'ACCEPTED_OFFLINE_ONLY','decision':'ACCEPTED_A27_TOTAL_FINITE_OFFLINE_SCOPE_AFTER_R1',
 'product_commit':'ebca4c71a70bdfb5fbccc023d00e0207ae532470','previous_candidate_commit':'23591811be71f9598c07c09b6a25a2a5fb066db0',
 'original_task_base_commit':'389d2e7a282d21efa25db8d01c02d115ce9e83b7',
 'delivery_manifest_sha256':'1aaa90ff70d6cdb788c174d3dbc683f90310e0e656defed341376335bbc57c50',
 'source_copy_pairs_verified_and_rechecked':109,'delivery_members_verified':72,'raw_git_blob_dependencies_verified':34,
 'prior_product_dependencies_byte_identical':30,'prior_source_copy_pairs_unchanged':147,'prior_report_members_unchanged':preserved_reports,
 'prior_private_control_members_unchanged':len(old_controls['members']),'new_control_artifacts':len(controls),
 'r1':{'status':'CLOSED_FOR_NEW_CANDIDATE_ONLY','original_report':ref(prior/'report.md'),'original_result':ref(prior/'result.json'),
    'original_witness':ref(original_witness),'original_outcome':'REWORK_AND_I07_FAIL_PRESERVED',
    'new_witness':ref(witness_path),'new_error':'RECOVERY_PROFILE_IN_USE','configure_calls':0,'capture_calls':0,
    'same_directory_by_os_samefile':True,'new_result_is_historical_failure_rewrite':False},
 'validation':{'new_candidate_suite':{'passed':8,'failed':0,'seconds':0.612},
    'independent_original_I07':{'passed':1,'failed':0,'seconds':0.091},
    'independent_additional_controls':{'passed':3,'failed':0,'seconds':0.249},
    'author_affected_two':'VERIFIED_FIXED_2_PASS_OUTPUT_NOT_RERUN',
    'prior_new20_and_independent6':'REUSED_WITH_BYTE_IDENTICAL_IMPLEMENTATIONS_AND_UNCHANGED_EXECUTE_AST_NOT_RERUN',
    'old_194_runs':0,'r1_independent_helper_failures':0,'r1_independent_product_failures':0},
 'accepted_finite_scope':[
    'Normal batch strict-first comparison and exact first-created question/answer direct three-field order fallback',
    'Distinct limited evidence status; no standard accepted marker or revision predecessor promotion',
    'Cooperatively bounded framework cleanup and standalone writer CLI exit; original business/framework/OS layers remain separate',
    'Original exact success receipt and intent/plan/guard/holder chain gates before a new single readonly recovery reader',
    'Windows argument parsing and directory device/inode identity for profile observations at both resource gates',
    'Full readback comparison, no recovery writer/POST dispatch, repeat dispatch rejection, unchanged historical ledger'],
 'limits':{'actual_platform_or_browser_validation':'NOT_RUN','live_OS_process_enumeration':'NOT_RUN_SYNTHETIC_QUERY_RETURNS_ONLY',
    'Windows_parameter_parser_and_synthetic_directory_metadata':'EXECUTED_OFFLINE',
    'synchronous_blocking_or_runtime_threads':'EXISTING_OUTER_SUPERVISOR_REQUIRED_NOT_PROVEN_BY_COOPERATIVE_TEST',
    'old_q4_timeout_cause':'UNKNOWN','new_live_authority_granted':False,'old_budget_restored':False},
 'historical_preservation':{'q3_strict_FAIL':True,'q4_framework_false':True,'q3_q4_standard_markers_created':False,
    'original_ledger_repaired':False,'prior_author_failures_preserved':4,'prior_independent_helper_error_preserved':1,
    'prior_product_counterexample_failure_preserved':1,'R1_author_baseline_failure_preserved':True,'R1_author_quoting_fixture_failure_preserved':True,
    'five_saves_or_readbacks_replayed':False,'A26_delivery_unchanged':True},
 'actions':{'real_profile_or_ledger_access':0,'real_platform_requests':0,'browser_starts':0,'real_OS_queries':0,
    'author_active_workspace_access':0,'product_changes':0,'root_state_or_AGENTS_changes':0,'git_commits':0,
    'OCR_runs':0,'automation_access_or_changes':0,'messages_to_other_chats':0},
 'automation_1800_a':'PAUSED_REQUIRED_UNCHANGED_NOT_LIVE_REOBSERVED','review_complete_and_released':True,
 'blocking_findings':[],
 'evidence':{'report':ref(PUBLIC/'report.md'),'intake':ref(PUBLIC/'raw-manifest.json'),'static_delta':ref(PUBLIC/'static-result.json'),
             'control_artifacts':ref(PUBLIC/'control-artifacts.json')}
}
write_new(PUBLIC/'result.json',encode(result))
files=[p for p in sorted(PUBLIC.rglob('*')) if p.is_file() and p.name not in ('review-files.sha256','review-files.sha256.self')]
lines=[sha(p.read_bytes())+'  '+p.relative_to(PUBLIC).as_posix() for p in files]
manifest=('\n'.join(lines)+'\n').encode('utf-8')
write_new(PUBLIC/'review-files.sha256',manifest)
write_new(PUBLIC/'review-files.sha256.self',(sha(manifest)+'  review-files.sha256\n').encode('ascii'))
print(json.dumps({'status':result['status'],'public_members':len(files),'new_control_artifacts':len(controls),
    'new_source_copy_pairs_rechecked':109,'prior_source_copy_pairs_rechecked':147,
    'report_sha256':sha((PUBLIC/'report.md').read_bytes()),'result_sha256':sha((PUBLIC/'result.json').read_bytes()),
    'manifest_sha256':sha(manifest)}))
