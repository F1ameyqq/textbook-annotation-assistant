"""Static JSON/hash/AST review only. Never imports or invokes product code."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
DELIVERY = 'docs/evidence/A20/authenticated-source/live-delivery/'
INPUT = OUT / 'input-raw-manifest.json'
EXPECTED_INPUT = '7a0d0758424683549fe6aefb11cc18de5e7e09037b01c5083a96a37c2de873a8'
CANDIDATE = '91db377e44b5b864208cc27a078d25266b3375bba2fdee18b9c648f37b572a7b'
PROFILE = 'b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00'
WORKFLOW = '52be34a72c43a7331976aba4b286138b9183856b'
FINAL = 'f45fa86789b8f154d03e8c4807412a2161d678f6'
PRODUCT = '28203196b4f2dae27b1de4213b27da9a41ae3139'
BASE = 'b41e88d7756fde9d7f1b348ce5a300d1104e765b'
REVIEWER = '01a159ab-01ba-7093-89a6-69e7ce572c38'
CHECKS = []

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def check(name, fact, basis):
    if not fact:
        raise AssertionError('STATIC_EVIDENCE_MISMATCH:' + name)
    CHECKS.append({'id': name, 'result': 'MATCH', 'basis': basis})

manifest = json.loads(INPUT.read_bytes())
check('input_manifest_digest', sha(INPUT.read_bytes()) == EXPECTED_INPUT, 'Dispatched SHA256')
members = {item['path']: item for item in manifest['members']}
check('56_unique_inputs', len(members) == len(manifest['members']) == 56, 'Frozen coordinator raw manifest')

def raw(path):
    if path not in members:
        raise AssertionError('READ_OUTSIDE_FIXED_MANIFEST')
    return (ROOT / path).read_bytes()

def load(path):
    return json.loads(raw(path))

def delivery(name):
    return load(DELIVERY + name)

def verify(item):
    content = raw(item['path'])
    blob = hashlib.sha1(b'blob ' + str(len(content)).encode('ascii') + b'\0' + content).hexdigest()
    return (len(content) == item['size'] and sha(content) == item['sha256']
        and blob == item['blob'] and item['mode'] == '100644'
        and item.get('type', 'blob') == 'blob')

check('all_raw_sha_size_Git_blob', all(verify(item) for item in members.values()), 'Independent bytes/hash read before interpretation')
check('fixed_final_base', manifest['base'] == BASE and manifest['final'] == FINAL, 'Dispatched commit labels; no Git or active author read')
candidate_raw = raw('docs/evidence/A20/authenticated-source/candidate-manifest.json')
candidate = json.loads(candidate_raw)
check('candidate_digest_and_product', sha(candidate_raw) == CANDIDATE and candidate['product_commit'] == PRODUCT,
    'Unchanged candidate manifest digest')
check('27_dependencies_preserved', len(candidate['members']) == 27 and all(verify(item) for item in candidate['members']),
    'Every dependency including regular package initializers matches fixed candidate bytes')
author_manifest = delivery('sha256-manifest.json')
check('55_author_members_plus_self', author_manifest['member_count'] == len(author_manifest['members']) == 55
    and {x['path'] for x in author_manifest['members']} | {DELIVERY + 'sha256-manifest.json'} == set(members)
    and all(verify(item) for item in author_manifest['members']), 'Exact fixed delivery closure, no normalization')
check('author_manifest_digest', sha(raw(DELIVERY + 'sha256-manifest.json')) ==
    '13e4b6ebc91ae36d0734fc0438564ee65d593064f890cf6e363066256fe71714', 'Dispatched author manifest SHA')
check('author_report_release_digests', sha(raw(DELIVERY + 'report.md')) ==
    '0daa4d425c59b5c895b2ba1f21c70c512fa854fe1610afbf94f7756290e980d4'
    and sha(raw(DELIVERY + 'session-release.json')) ==
    '21049df50a9198bd35c439603562e1b10ae52db573690cc1a35b292e252c7323', 'Dispatched fixed report and release SHA')

source_capture = delivery('source-raw-capture.json')
for name, description in source_capture['members'].items():
    path = DELIVERY + (name if name.startswith('authority/') else 'raw/' + name)
    content = raw(path)
    check('provenance_' + name.replace('/', '_'), len(content) == description['size']
        and sha(content) == description['sha256'], 'Source-capture record compared to fixed copies; original .local source NOT read')

activation = delivery('authority/activation.json')
decision = delivery('authority/decision.json')
offline = delivery('authority/independent-result.json')
dispatch = delivery('authority/dispatch-intent.json')
scope_names = ('task run_id workflow_commit scope candidate_manifest_sha256 sample_limit '
    'automatic_schema_confirmation fixed_business_get_count original_get_count new_live_limit '
    'context_limit navigation_limit total_seconds business_get_limit_per_url original_limit_per_viewer '
    'navigation_sequence login_post_url login_json_keys credential_config required_profile_fingerprint '
    'session_get_limit_per_path_per_phase session_phase_limit refresh_post_limit automatic_request_resend_limit '
    'credential_transmission_requires_direct_A20_decision login_submission_limit business_write_limit '
    'upload_limit ocr_limit old_budgets_restored executor_thread_id output_directory activation_path '
    'decision_path report_path excluded_static_event_limit version_check_limit standing_tls_permission_path '
    'standing_tls_permission_sha256').split()
check('39_scope_fields', len(scope_names) == 39, 'Frozen A20 scope field set')
scope = {name: decision[name] for name in scope_names}
for name, value in scope.items():
    expected = CANDIDATE if name == 'candidate_manifest_sha256' else candidate[name]
    check('scope_' + name, type(value) is type(expected) and value == expected and
        all(type(doc[name]) is type(value) and doc[name] == value for doc in (activation, offline)),
        'Candidate, actual decision, activation, prior independent report; typed equality')
check('direct_A20_user_decision', decision['authorization_basis'] == 'DIRECT_A20_USER_DECISION'
    and all(decision[key] is True for key in ('live_authorized', 'direct_user_decision',
        'certificate_exception_authorized', 'login_submission_authorized',
        'credential_transmission_authorized', 'credential_tls_exception_authorized'))
    and decision['direct_answer'] == '\u6279\u51c6\u672c\u8f6e\u4e00\u6b21\u767b\u5f55\u53ca\u8bfb\u53d6',
    'Exact direct answer recorded in fixed A20 decision; A17 is only referenced')
check('TLS_mode', activation['tls_mode'] == decision['tls_mode'] == 'CONTEXT_EXCEPTION', 'This fixed original context only')
check('activation_decision_report_hashes', activation['user_decision_sha256'] ==
    sha(raw(DELIVERY + 'authority/decision.json')) == dispatch['decision_sha256']
    and activation['independent_report_sha256'] == sha(raw(DELIVERY + 'authority/independent-result.json')) ==
    dispatch['independent_report_sha256'] and sha(raw(DELIVERY + 'authority/activation.json')) ==
    dispatch['activation_sha256'], 'Exact raw authority linkage')
check('offline_report_limited_only', offline['result'] == 'ACCEPTED_OFFLINE_ONLY'
    and offline['candidate_manifest_sha256'] == CANDIDATE, 'Prior report is an offline preflight, not actual success')
check('dispatch_task_hash', sha(raw(DELIVERY + 'authority/task.md')) == dispatch['task_sha256'], 'Fixed task/dispatch linkage')
check('dispatch_identity', dispatch['candidate_sha256'] == CANDIDATE and dispatch['product_commit'] == PRODUCT
    and dispatch['final_commit'] == BASE and dispatch['product_workflow'] == WORKFLOW
    and dispatch['profile_fingerprint'] == PROFILE, 'Exact approved product, workflow, profile, base')
for name in ('proposal_sha256', 'answer_record_sha256'):
    check('decision_dispatch_' + name, decision[name] == dispatch[name],
        'Hash references match; referenced proposal/answer original not in 56-file input, not reread')
launch = delivery('author-launch-intent.json')
launcher_intent = delivery('raw/launcher-intent.json')
check('one_fixed_launch_intent', launch['argv'] == dispatch['argv'] and launch['cwd'] == dispatch['cwd']
    and launch['launch_intents'] == 1 and launch['retry_limit'] == 0
    and launch['dispatch_intent_sha256'] == sha(raw(DELIVERY + 'authority/dispatch-intent.json')),
    'Fixed author launch intent, exact argv; not an exhaustive OS process trace')
check('internal_launcher_binding', launcher_intent['candidate_sha256'] == CANDIDATE
    and launcher_intent['activation_sha256'] == dispatch['activation_sha256']
    and launcher_intent['profile_fingerprint'] == PROFILE and launcher_intent['shell'] is False
    and launcher_intent['argv'][4:] == dispatch['argv'][3:], 'Internal probe mode is _launched with same live args')
marker_names = ['launcher-claimed.json', 'live-started.json', 'worker-claimed.json', 'occupancy-claimed.json']
markers = [delivery('raw/' + name) for name in marker_names]
check('four_irreversible_markers_match', all(marker == markers[0] for marker in markers)
    and markers[0]['candidate_sha256'] == CANDIDATE
    and markers[0]['activation_sha256'] == dispatch['activation_sha256']
    and markers[0]['profile_fingerprint'] == PROFILE and markers[0]['workflow_commit'] == WORKFLOW,
    'Fixed marker copies; no mark was reset or recreated in review')
check('fixed_profile_receipt', delivery('raw/profile-binding.json')['fingerprint'] == PROFILE ==
    activation['profile_fingerprint'], 'Recorded fingerprint only, no real profile probe')

actual = delivery('actual-result.json')
current = delivery('raw/current-state.json')
tool = delivery('author-tool-result.json')
launcher = delivery('raw/launcher-release.json')
worker = delivery('raw/worker-release.json')
occupancy = delivery('raw/occupancy.json')
released = delivery('session-release.json')
audit = current['network_audit']
check('projection_network', delivery('network-audit.json') == audit, 'Exact unamended projection')
check('projection_authentication', delivery('authentication-metadata.json') == current['authentication'], 'Exact unamended projection')
check('outcome_and_first_error', current['outcome'] == actual['outcome'] == 'ERROR'
    and current['error'] == actual['first_error'] == {'codes': ['API_BLOCKED'], 'exception_type': 'Stop'}, 'Fixed raw current-state')
fatal = [item for item in audit if item['decision'] == 'BLOCK' and not any(item[key] for key in
    ('expected_excluded_path_denial', 'expected_excluded_static_denial',
     'expected_excluded_version_repeat', 'expected_passive_denial'))][0]
check('first_fatal_Image_GET', fatal == actual['first_fatal_audit'] and fatal['category'] == 'API_BLOCKED'
    and fatal['method'] == 'GET' and fatal['resource_type'] == 'Image'
    and fatal['scheme'] == 'https' and fatal['hostname'] == 'www.usense.com'
    and fatal['source'] == 'FETCH_REQUEST_STAGE' and fatal['redirect_hop'] is False
    and fatal['path_sha256'] == '7f8d9b088e7dea613880ef32040bf2c15bda25cb7a672a7ae05a37137bac2eba',
    'Safe audit metadata only; no inference of path, use, captcha/logo, initiator or root cause')
check('11_audit_events_not_requests', len(audit) == actual['counts']['network_audit_events'] == 11,
    'Audit entries include dual barriers and STOPPED callbacks; auxiliary sent count UNKNOWN')
navigation = [item for item in audit if item['category'] == 'NAVIGATION']
check('one_login_navigation_both_layers', len(navigation) == 2
    and {item['source'] for item in navigation} == {'FETCH_REQUEST_STAGE', 'CONTEXT_FIRST_REQUEST'}
    and all(item['decision'] == 'ALLOW' and item['resource_type'] == 'Document' and
        item['path_sha256'] == sha(b'/qieti/login') for item in navigation)
    and current['authentication']['navigation_intents'] == 1
    and current['authentication']['navigation_reservations'] == {'native': 1, 'context': 1},
    'Fixed path hash and two barrier reservations; actual frame ID not stored in audit')
auth = current['authentication']
check('no_credential_fill_intent_or_POST', current['steps']['login_navigation'] == 'FAILED'
    and current['steps']['login_fill'] == current['steps']['login_submit'] == 'NOT_RUN'
    and auth['login_intent_recorded'] is False and auth['native_post_reservations'] == 0
    and auth['context_post_reservations'] == current['login_submissions'] == auth['actual_login_post_requests'] == 0
    and not auth['session_receipts'] and not auth['native_http_observations']
    and auth['login_response'] is None and auth['login_http_status'] is None,
    'Fixed current-state and no-entry control flow; no new OS file-access audit')
check('all_successors_NOT_RUN', all(value == 'NOT_RUN' for name, value in current['steps'].items()
    if name != 'login_navigation') and not current['sources'] and current['business_writes'] == 0
    and not any(item['business_read'] or item['category'] == 'REGISTERED_ORIGINAL' for item in audit),
    'Six GETs/two originals/mappings/sample/write successors absent and NOT_RUN')
check('auth_source_unproven', auth['protected_viewer_authenticated'] is False
    and actual['authentication'] == 'NOT_PROVEN' and current['write_eligible'] is False
    and current['schema_status'] == current['body_status'] == 'UNKNOWN', 'No authentication or source/inventory/first-save pass')
check('viewer_only_diagnostic', current['navigation_diagnostics']['phase'] == 'NOT_STARTED'
    and actual['login_main_document_HTTP_status'] == actual['login_DCL_observation'] == 'UNKNOWN_NOT_RECORDED',
    'Viewer diagnostic not started; no login Document HTTP/DCL observation in delivery')
check('CDN_still_denied', len([item for item in audit if item['category'] == 'EXPECTED_EXCLUDED_STATIC_DENIAL']) == 1
    and current['excluded_static']['combined_guard_events'] == 1
    and current['excluded_static']['completed_denial_calls'] == 1, 'Expected denial, never authorization')
check('version_reservation_only', current['version_check'] == {'context_pass_reservations': 0,
    'http_success': 'UNKNOWN', 'native_send_reservations': 1, 'send_limit': 1}, 'Native reservation is not proof of sent request')
check('first_error_pending_and_terminal', all(current[key]['failure'] == current['error']
    and current[key]['terminal_stopped'] is True and current[key]['stopped'] is True
    and current[key]['pending_tasks'] == 0 for key in ('guard_pre_shutdown', 'guard_at_serialization'))
    and current['guard_at_serialization']['shutdown_started'] is True
    and current['excluded_static']['pending_callbacks'] == 0,
    'Original API_BLOCKED retained before shutdown and at serialization, late callbacks settled')

# Parse source as data only. No eval/exec/import or runtime product entry point.
probe = ast.parse(raw('tools/a16_current_state_probe.py').decode('utf-8'))
functions = {node.name: node for node in probe.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
authenticate = functions['authenticate']
goto_lines = [node.lineno for node in ast.walk(authenticate) if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Attribute) and node.func.attr == 'goto']
credential_lines = [node.lineno for node in ast.walk(authenticate) if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Name) and node.func.id == 'read_credentials']
check('credential_zero_control_flow_basis', len(goto_lines) == len(credential_lines) == 1
    and goto_lines[0] < credential_lines[0], 'Static source order plus login_navigation FAILED; no actual config-file audit')

identities = []
for role, receipt, closed_key, expected_exit in (('product', launcher, 'product_handle_closed', 2),
    ('worker', worker, 'worker_handle_closed', 2), ('occupancy', occupancy, 'handle_closed', 0)):
    before, after = receipt['before'], receipt['after']
    check('held_identity_' + role, type(before['pid']) is int and before['pid'] > 0
        and type(before['created_filetime']) is int and before['created_filetime'] > 0
        and before['pid'] == after['pid'] and before['created_filetime'] == after['created_filetime']
        and after['exit_observed'] is True and after['exit_code'] == expected_exit
        and type(after['exited_filetime']) is int and after['exited_filetime'] >= before['created_filetime']
        and receipt[closed_key] is True, 'Fixed held-handle receipt only, no independent OS probe')
    row = next(item for item in released['held_process_identities'] if item['role'] == role)
    check('release_projection_' + role, row['before'] == before and row['after'] == after and row['handle_closed'] is True,
        'Author release projection agrees with raw producer receipt')
    identities.append({'role': role, 'pid': before['pid'], 'created_filetime': before['created_filetime'],
        'exit_code': after['exit_code'], 'exit_observed': True, 'handle_closed': True,
        'basis': 'FIXED_HELD_HANDLE_RECEIPT_ONLY'})
check('two_Jobs_closed_zero', all(receipt['job_active_final'] == 0 and receipt['job_closed'] is True
    and receipt['job_assigned'] is True and receipt['state'] == 'RELEASED' and receipt['errors'] == []
    for receipt in (launcher, worker)), 'Both before-final-cleanup active=1 values retained, final=0')
check('context_runtime_closed', current['release'] == released['context_runtime'] == actual['release']['context_runtime']
    and current['release']['state'] == 'RELEASED' and current['release']['errors'] == []
    and all(current['release'][key] is True for key in ('context_created', 'context_close_attempted',
        'context_closed', 'runtime_stop_attempted', 'runtime_stopped')), 'Fixed current-state release')
check('exit_layers_separate', tool['exit_code'] == tool['launcher_safe_result']['product_exit_code'] ==
    launcher['after']['exit_code'] == worker['after']['exit_code'] == 2
    and actual['execution_tool_wrapper_exit_code'] == 0 and occupancy['after']['exit_code'] == 0,
    'Capture wrapper exit0 from author summary is separate from launcher/product/worker exit2; original tool transcript not supplied')
check('stdout_limit_not_raw_transcript', tool['stdout_bytes'] == 135 and tool['stderr_bytes'] == 0
    and tool['launcher_safe_result']['release'] == 'RELEASED',
    'Outer stdout only safe projection plus hash; 135 original bytes not supplied, cannot independently rehash')
check('launcher_self_unknown', released['launcher_self_OS_identity'] == tool['launcher_own_OS_identity'] == 'UNKNOWN'
    and launcher['launcher_own_os_exit_identity'].startswith('UNKNOWN'), 'Self OS identity not inferred from completion')

def utc(value):
    return datetime.fromisoformat(value)

start, end = utc(activation['not_before']), utc(activation['expires_at'])
check('900_second_window', (end - start).total_seconds() == 900
    and dispatch['not_before'] == activation['not_before'] and dispatch['expires_at'] == activation['expires_at'],
    'Fixed approved UTC window; never extended')
time_layers = {}
for role, data in (('external_capture', tool), ('launcher_record', launcher), ('worker_record', worker), ('context_observation', current)):
    since, until = utc(data['started_at']), utc(data['finished_at'])
    check('inside_window_' + role, start <= since <= until < end,
        'This recorded UTC layer independently inside fixed activation window')
    time_layers[role] = {'started_at_utc': data['started_at'], 'finished_at_utc': data['finished_at'],
        'recorded_duration_ms': data.get('duration_ms', 'NOT_RECORDED'),
        'UTC_endpoint_arithmetic_ms': round((until - since).total_seconds() * 1000, 3),
        'duration_or_layer_gap_cause': 'UNKNOWN_NOT_INFERRED'}
check('deadline_flags', launcher['total_deadline_exceeded'] is False and worker['hard_deadline_exceeded'] is False,
    'Recorded monotonic deadline flags, no old timing claim expanded')
check('spent_budget', actual['live_budget'] == {'limit': 1, 'used': 1, 'remaining': 0, 'old_budgets_restored': False}
    and released['budget_limit'] == released['budget_used'] == 1 and released['budget_remaining'] == 0,
    'No retry, extension, restart or old budget restoration authorized')
failure = delivery('first-manifest-attempt-failure.json')
check('original_packaging_failure_retained', failure['status'] == 'FAILED_BEFORE_MANIFEST_CREATED'
    and failure['premature_evidence_commit'] == '28dc921c84bb4a6f043472337f3df9128c3b4d3f'
    and failure['actual_executed_raw_matches_Git'] is True and failure['live_retry'] is False
    and failure['full_original_tool_output_saved_to_delivery'] is False,
    'Explicit author error transcription and retained intermediate commit; not an original full stderr artifact')
preservation = delivery('preservation.json')
check('preservation_claim_scope', preservation['old_members'] == 31853
    and preservation['all_old_mode_type_blob_preserved'] is True and preservation['old_changed'] == []
    and preservation['deleted'] == [], 'Coordinator full-tree verification referenced; independent comparison limited to 56 raw inputs')

verification = {'schema': 'A20-static-actual-evidence-verification/v1', 'task': 'A20',
    'reviewer_thread_id': REVIEWER, 'review_dispatch_workflow': '90406699ad083a98efc0bd5a1c0eb94fb199c42f',
    'base_offline_final': BASE, 'actual_final': FINAL, 'product': PRODUCT,
    'result': 'FIXED_EVIDENCE_CONSISTENT_WITH_LIMITED_FAILURE_AND_RELEASE',
    'raw_inputs': 56, 'candidate_dependencies': 27, 'author_manifest_members': 55,
    'input_manifest_sha256': EXPECTED_INPUT, 'candidate_sha256': CANDIDATE,
    'bound_execution_scope': scope, 'scope_fields': len(scope_names),
    'checks': CHECKS, 'check_count': len(CHECKS), 'checks_are': 'STATIC_JSON_HASH_AST_COMPARISONS_NOT_PRODUCT_TESTS_OR_SUITE',
    'first_fatal': fatal, 'identity_receipts': identities, 'time_layers': time_layers,
    'credential_zero_basis': {'source': 'tools/a16_current_state_probe.py',
        'login_goto_line': goto_lines[0], 'reader_line': credential_lines[0],
        'raw_step': current['steps']['login_navigation'], 'OS_file_access_audit': 'NOT_AVAILABLE'},
    'product_imports': 0, 'product_runs': 0, 'new_suites': 0, 'old_suites': 0,
    'browser_network_profile_credential_native_occupancy_operations': 0,
    'reviewer_started_live': False, 'created_decision_or_activation': False,
    'verified_at_utc': datetime.now(timezone.utc).isoformat()}
with (OUT / 'static-verification.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(verification, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'result': verification['result'], 'static_comparisons': len(CHECKS),
    'scope_fields': len(scope_names), 'product_imports': 0, 'suites': 0,
    'held_process_receipts': len(identities), 'Jobs_final_active': [launcher['job_active_final'], worker['job_active_final']]}))
