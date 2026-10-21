"""Static consistency checks of frozen records, not product/control execution."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
A=ROOT/'docs/evidence/A24/bootstrap-current-body-actual'
AUTH='2dc9e2b06e0a6f7f62152b0ab0e8fef44d37362bdf7cb5684a3f3462175bc476'


def load(path): return json.loads(path.read_bytes())
def sha(raw): return hashlib.sha256(raw).hexdigest()
def filetime(value): return datetime.fromtimestamp(value/10000000-11644473600,timezone.utc)


authority=load(A/'inputs/authority.json')
decision=load(A/'inputs/decision.json')
acceptance=load(A/'inputs/prewrite-acceptance-binding.json')
claimed=load(A/'raw/outer/outer-claimed.json')
outer=load(A/'raw/outer/outer-result.json')
worker=load(A/'raw/run/worker-result.json')
actual=load(A/'actual-result.json')
root_manifest=load(OUT/'input-raw-manifest.json')
start=datetime.fromisoformat(authority['not_before']); end=datetime.fromisoformat(authority['expires_at'])
checks={}
checks['exact_authority_bytes']=sha((A/'inputs/authority.json').read_bytes())==AUTH
checks['decision_and_acceptance_hash_bound']=all(
    sha((A/'inputs'/name).read_bytes())==authority['refs'][key]['sha256'] and
    len((A/'inputs'/name).read_bytes())==authority['refs'][key]['bytes']
    for key,name in [('decision','decision.json'),('independent_report','prewrite-acceptance-binding.json')])
checks['same_narrow_null_schema_scope']=authority['refs']['schema_profile'] is None and authority['role']=='AUTHOR_SAVE' and decision['effective_current_branch']==acceptance['effective_current_branch'] and decision['effective_current_branch']['business_get']==4 and decision['effective_current_branch']['retry']==0 and not decision['conditional_save_authorized'] and not acceptance['conditional_save_admitted']
checks['one_frozen_claim_within_900s_window']=(end-start).total_seconds()==900 and claimed['attempt_limit']==1 and start<=datetime.fromisoformat(claimed['at'])<=datetime.fromisoformat(outer['at'])<=end and claimed['authority_sha256']==outer['authority_sha256']==AUTH and claimed['run_id']==authority['run_id']
checks['pre_import_dependency_and_library_checks_recorded']=claimed['dependencies_verified']==151 and claimed['resources_before_verification']==0 and actual['library_preflight']==dict(before_product_import=True,candidate_dependencies_hash_verified=151,installed_source_hashes_verified=4,python='3.9.13',playwright='1.58.0',dependency_replaced=False,old_tests_or_callback_regression_run=0)
checks['external_wrapper_hash']=sha((A/'raw/outer/held_launcher_once.py').read_bytes())==claimed['wrapper_sha256']

stages={}
for stage,exit_code in [('launcher',2),('product',2),('worker',2),('occupancy',0)]:
    held=load(A/('raw/run/'+stage+'-held-release.json'))
    claim=load(A/('raw/run/'+stage+'-claimed.json'))
    before,after=held['before'],held['after']
    valid=(claim['authority_sha256']==held['authority_sha256']==AUTH and claim['run_id']==authority['run_id'] and
           before['pid']==after['pid'] and before['created_filetime']==after['created_filetime'] and
           before['exit_observed'] is False and after['exit_observed'] is True and after['exit_code']==exit_code and
           start<=filetime(before['created_filetime'])<=filetime(after['exited_filetime'])<=end and
           held['creation_identity_match'] is True and held['job_assigned'] is True and
           held['stdin_token_sent_after_job_assignment'] is True and held['job_active_final']==0 and
           held['job_closed'] is True and held['handle_closed'] is True and held['released'] is True and
           held['errors']==[] and held['stderr_bytes']==0)
    stages[stage]=dict(valid=valid,pid=before['pid'],created_filetime=before['created_filetime'],
        exited_filetime=after['exited_filetime'],exit_code=exit_code)
    checks[stage+'_held_identity_exit_and_empty_job_handle_release']=valid
checks['external_holder_proves_actual_launcher_exit']=outer['held_launcher']==load(A/'raw/run/launcher-held-release.json') and outer['helper_own_exit_identity']=='NOT_SELF_CERTIFIED'

private=load(A/'private-raw-manifest.json')['members']
current=[row for row in root_manifest['private_references'] if row['kind']=='CURRENT_FIXED_RAW_OUTPUT']
checks['ten_current_stream_references_exact_and_opaque']=len(private)==len(current)==10 and all(any(
    row['path']==ref['bound_original_path'] and row['bytes']==ref['bytes'] and row['sha256']==ref['sha256']
    for ref in current) for row in private)
for stage in stages:
    held=load(A/('raw/run/'+stage+'-held-release.json'))
    checks[stage+'_raw_stdout_stderr_bound']=all(any(
        row['stage']==stage and row['kind']==kind and row['path']==ref['path'] and row['bytes']==ref['bytes'] and row['sha256']==ref['sha256']
        for row in private) for kind,ref in held['controlled_raw_output_refs'].items())
capture=load(A/'raw/outer/raw-capture.json')
checks['outer_capture_complete']=capture['complete'] is True and capture['stdout']['sha256']==outer['held_launcher']['stdout_sha256'] and capture['stderr']['bytes']==0

nav=worker['navigation']
checks['original_navigation_progress_only']=nav['association']=='ORIGINAL_MAIN_DOCUMENT_NETWORK_ID' and nav['response_received']['http_status']==200 and nav['response_received']['elapsed_ms']==5359 and nav['goto']['http_status']==200 and nav['goto']['elapsed_ms']==8984 and nav['domcontentloaded_observed'] is True and nav['readiness']['state']=='NOT_RUN'
failure=dict(codes=['SCRIPT_CONTROLLED_OUTPUT_REQUIRED'],exception_type='Stop')
snapshots=[]
for key in ('guard_evidence_before_release','guard_evidence_after_release'):
    snapshot=worker[key]; events=snapshot['events']
    blocks=[e for e in events if e['decision']=='BLOCK']
    checks[key+'_complete_safe_13']=snapshot['status']=='PROJECTED' and snapshot['complete'] is True and snapshot['truncated'] is False and len(events)==snapshot['total_events']==snapshot['retained_events']==13 and [e['index'] for e in events]==list(range(13)) and all(not set(e).intersection({'url','raw_url','body','token','exception','query_values'}) for e in events)
    checks[key+'_earliest_block_not_causal']=len(blocks)==1 and blocks[0]['index']==snapshot['earliest_block_index']==4 and blocks[0]['category']=='EXPECTED_EXCLUDED_STATIC_DENIAL' and blocks[0]['hostname']=='cdn.bootcdn.net' and blocks[0]['method']=='GET' and blocks[0]['resource_type']=='Script' and blocks[0]['source']=='FETCH_REQUEST_STAGE' and snapshot['first_failure']==failure and snapshot['first_failure_category_event_index'] is None and snapshot['failure_event_link']=='NOT_RECORDED' and not any(e['category'] in failure['codes'] for e in events)
    checks[key+'_one_denial_pending_zero']=snapshot['exclusions']['combined_guard_events']==snapshot['exclusions']['completed_denial_calls']==1 and snapshot['exclusions']['event_limit']==16 and snapshot['exclusions']['pending_callbacks']==0 and all(snapshot['exclusions'][k]=='UNKNOWN' for k in ('http_send_count','dns_tcp_tls_activity','script_necessity'))
    snapshots.append(snapshot)
checks['first_error_distinct_and_preserved']=worker['first_error']==dict(code='OWNER_ERROR',type='OTHER') and worker['status']=='ERROR_STOPPED_NO_RETRY' and worker['bootstrap_steps']['session_completion']=='STARTED' and snapshots[0]['first_failure']==snapshots[1]['first_failure']==worker['release']['guard_failure']
checks['context_runtime_callbacks_released']=worker['release']['released'] is True and worker['release']['context_closed'] is True and worker['release']['runtime_stopped'] is True and worker['release']['callback_pending']==0 and worker['release']['errors']==[] and snapshots[1]['settlement']==dict(pending_callbacks=0,sealed=True,shutdown_started=True,stopped=True) and worker['resend_allowed'] is False
checks['business_and_effects_not_run']=worker['steps']['prewrite']==worker['steps']['adapter']=='NOT_RUN' and all(actual[k]=='NOT_RUN' for k in ('book','directory','frames','natural_export','signature','upload','commit','refresh','reopen')) and actual['business_get_count']==0
checks['round_spent_no_retry']=actual['new_dispatch_attempts_spent']==1 and actual['new_dispatch_remaining']==0 and actual['retry_or_extension_allowed'] is False and actual['claims_cleared'] is False

finding=load(A/'static-output-integration-finding.json')
probe=(ROOT/'tools/a16_current_state_probe.py').read_text(encoding='utf-8')
owner=(ROOT/'src/annotation/runtime/live_pilot/owner.py').read_text(encoding='utf-8')
tree=ast.parse(owner); backend=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='WindowsBackend')
opened=next(n for n in backend.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='open')
checks['frozen_static_discrepancy_only']=probe.count("raise Stop('SCRIPT_CONTROLLED_OUTPUT_REQUIRED')")==1 and 'self.output = None' in probe and 'if self.output != LIVE_OUT:' in probe and not any(isinstance(n,ast.Assign) and any(ast.unparse(t)=='self.guard.output' for t in n.targets) for n in ast.walk(opened)) and finding['actual_guard_output_and_live_out_values']=='NOT_RETAINED' and finding['actual_request_causal_link']=='NOT_RECORDED'

value=dict(schema='A24BootstrapBodyActualIndependentStaticChecks/v1',at=datetime.now(timezone.utc).isoformat(),
    result='PASS_FIXED_ACTUAL_CONSISTENCY_ONLY' if all(checks.values()) else 'REVIEW_INCOMPLETE_PRESERVE_FIRST_MISMATCH',
    checks=checks,held_identities=stages,product_tests_or_controls=0,old_source_model_quality_reviews=0,
    raw_stream_contents_decoded_or_published=False,real_resources=0,new_authority=0,
    outer_tool_exit1='AUTHOR_TRANSCRIPTION_ONLY',outer_helper_os_identity='NOT_SELF_CERTIFIED',
    exact_script_response_causal_link='UNKNOWN_NOT_RECORDED',profile_effects='NOT_INSPECTED')
with (OUT/'static-checks.json').open('xb') as handle: handle.write((json.dumps(value,indent=2)+'\n').encode())
print(json.dumps({'result':value['result'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v],'tests':0,'real_resources':0}))
