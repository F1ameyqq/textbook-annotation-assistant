"""A22 fixed actual-result archive audit. No product import/run or live access."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
LIVE = ROOT / 'docs/evidence/A22/session-reuse/live-delivery'
FROZEN = ROOT / 'docs/evidence/A22/session-reuse'
CHECKS = []


def document(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name, condition, facts):
    CHECKS.append({'name': name, 'result': 'PASS' if condition else 'FAIL', 'facts': facts})
    if not condition:
        raise ValueError('STATIC_ARCHIVE_MISMATCH: ' + name)


def same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is list:
        return len(actual) == len(expected) and all(same(a, e) for a, e in zip(actual, expected))
    if type(expected) is dict:
        return set(actual) == set(expected) and all(same(actual[k], v) for k, v in expected.items())
    return actual == expected


def instant(text):
    return datetime.fromisoformat(text.replace('Z', '+00:00'))


def filetime(value):
    delta = value - datetime(1601, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 10000000 + delta.microseconds * 10


candidate_path = FROZEN / 'candidate-manifest.json'
delivery_path = LIVE / 'delivery-manifest.json'
candidate, delivery = document(candidate_path), document(delivery_path)
check('fixed_manifest_digests', digest(candidate_path) == '264e7fd8120efc8dd8f95f6c66b28693104d82f47e3d68e3a91fd0c422b38141'
    and digest(delivery_path) == '7602eb7d04101047f161c3c392e1076e0b3600b8e5b21aacfc19b58232a7e006',
    {'candidate_members': len(candidate['members']), 'actual_delivery_members': len(delivery['members'])})
bound = set()
for manifest in (candidate, delivery):
    for member in manifest['members']:
        relative = Path(member['path'])
        check_path = not relative.is_absolute() and '..' not in relative.parts and ':' not in str(relative)
        if not check_path:
            raise ValueError('MANIFEST_PATH_REJECTED')
        raw = (ROOT / relative).read_bytes()
        size = member.get('size', member.get('bytes'))
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != member['sha256']:
            raise ValueError('MANIFEST_MEMBER_BYTES_REJECTED')
        if hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != member['blob']:
            raise ValueError('MANIFEST_MEMBER_BLOB_REJECTED')
        bound.add(member['path'])
bound |= {'docs/evidence/A22/session-reuse/candidate-manifest.json',
    'docs/evidence/A22/session-reuse/live-delivery/delivery-manifest.json'}
input_audit = document(OUT / 'input-audit.json')
check('input_dependency_delivery_closure', len(candidate['members']) == 28 and len(delivery['members']) == 28
    and len(bound) == 58 and bound == {m['path'] for m in input_audit['members']},
    {'input_members': 58, 'candidate_dependencies': 28, 'actual_members': 28, 'manifest_selves': 2})
copies = document(LIVE / 'raw-copy-manifest.json')
for member in copies['members']:
    path = LIVE / member['path']
    if len(path.read_bytes()) != member['bytes'] or digest(path) != member['sha256']:
        raise ValueError('RAW_COPY_BYTES_REJECTED')
check('raw_copy_archive', len(copies['members']) == 10 and copies['source_script_or_sidecar_copied'] is False
    and copies['source_profiles_or_credentials_copied'] is False,
    {'archived_raw_members': len(copies['members']), 'private_source_paths_accessed_by_reviewer': False})

activation = document(LIVE / 'activation.json')
authorization = document(LIVE / 'authorization.json')
preflight = document(LIVE / 'independent-result.json')
dispatch = document(LIVE / 'dispatch-intent.json')
prelaunch = document(LIVE / 'prelaunch-verification.json')
scope = {k: v for k, v in preflight.items() if k != 'result'}
check('fifty_field_authority_scope', len(scope) == 50 and preflight['result'] == 'ACCEPTED_OFFLINE_ONLY'
    and all(same(doc.get(k), v) for doc in (authorization, activation) for k, v in scope.items())
    and all(same(candidate.get(k), v) for k, v in scope.items() if k != 'candidate_manifest_sha256'),
    {'scope_members': len(scope), 'scope': scope['scope'], 'candidate_sha256': scope['candidate_manifest_sha256']})
hash_bindings = [('activation.json', 'activation_sha256'), ('authorization.json', 'decision_sha256'),
    ('independent-result.json', 'independent_report_sha256'), ('task.md', 'task_sha256')]
check('authority_raw_hashes', all(digest(LIVE / name) == dispatch[key] == prelaunch[key]
    for name, key in hash_bindings) and digest(LIVE / 'authorization.json') == activation['user_decision_sha256']
    and digest(LIVE / 'independent-result.json') == activation['independent_report_sha256']
    and digest(FROZEN / 'authority/standing-permission.json') == scope['standing_tls_permission_sha256'],
    {key: dispatch[key] for _, key in hash_bindings})
profile = document(LIVE / 'raw/profile-binding.json')['fingerprint']
check('readonly_profile_and_standing_permission', activation['profile_fingerprint'] == profile == scope['required_profile_fingerprint']
    and authorization['authorization_basis'] == 'A17_STANDING_READONLY_TLS_PERMISSION_BOUND_TO_A22'
    and authorization['live_authorized'] is True and authorization['certificate_exception_authorized'] is True
    and all(authorization[key] is False for key in ('login_submission_authorized', 'credential_transmission_authorized',
        'credential_tls_exception_authorized', 'local_credential_config_read_authorized')),
    {'profile_fingerprint': profile, 'tls_mode': activation['tls_mode'], 'A21_login_permission_reused': False})

launch_intent, launch_result = document(LIVE / 'launch-intent.json'), document(LIVE / 'launch-result.json')
actual = document(LIVE / 'live-result.json')
current = document(LIVE / 'raw/current-state.json')
launcher = document(LIVE / 'raw/launcher-release.json')
worker = document(LIVE / 'raw/worker-release.json')
occupancy = document(LIVE / 'raw/occupancy.json')
start, end = instant(activation['not_before']), instant(activation['expires_at'])
layers = [('envelope', launch_result), ('launcher', launcher), ('worker', worker)]
timing = []
for name, layer in layers:
    a, b = instant(layer['started_at']), instant(layer['finished_at'])
    wall = (b - a).total_seconds() * 1000
    timing.append({'layer': name, 'wall_ms': round(wall, 6), 'monotonic_ms': layer['duration_ms'],
        'wall_minus_monotonic_ms': round(wall-layer['duration_ms'], 6),
        'inside_activation_window': start <= a <= b <= end, 'difference_cause': 'UNKNOWN'})
check('bounded_window_and_recorded_single_launch', (end-start).total_seconds() == 900
    and all(item['inside_activation_window'] for item in timing)
    and dispatch['launch_limit'] == launch_intent['launch_limit'] == launch_result['launches'] == actual['launches_used'] == 1
    and dispatch['retry_limit'] == launch_result['retry_attempts'] == actual['retry_attempts'] == actual['live_remaining'] == 0
    and same(dispatch['argv'], launch_intent['argv']) and dispatch['cwd'] == launch_intent['cwd']
    and launch_intent['shell'] is False and instant(launch_intent['utc']) == instant(launch_result['started_at'])
    and launcher['total_deadline_exceeded'] is False and worker['hard_deadline_exceeded'] is False,
    {'not_before': activation['not_before'], 'expires_at': activation['expires_at'], 'timing': timing,
        'uniqueness_scope': 'Delivered fixed intent/markers/envelope; no OS-wide history inference'})
claims = [document(LIVE / ('raw/' + name)) for name in
    ('launcher-claimed.json', 'live-started.json', 'worker-claimed.json', 'occupancy-claimed.json')]
check('single_round_claim_bindings', all(claim['task'] == 'A22' and claim['run_id'] == scope['run_id']
    and claim['workflow_commit'] == scope['workflow_commit'] and claim['candidate_sha256'] == scope['candidate_manifest_sha256']
    and claim['activation_sha256'] == dispatch['activation_sha256'] and claim['profile_fingerprint'] == profile
    and claim['scope'] == scope['scope'] and claim['sample_limit'] == 0 and claim['certificate_exception'] is True for claim in claims),
    {'claim_members': 4, 'original_marker_paths_accessed_or_modified': False})

navigation = current['navigation_diagnostics']
authentication = current['authentication']
network = document(LIVE / 'network-audit.json')
events = current['network_audit']
session_events = [event for event in events if event['category'] == 'SESSION_GET']
check('fixed_navigation_and_unproven_authentication', navigation['goto']['http_status'] == 200
    and navigation['goto']['state'] == navigation['readiness']['state'] == 'DONE'
    and navigation['domcontentloaded_observed'] is True
    and navigation['association'] == 'ORIGINAL_MAIN_DOCUMENT_NETWORK_ID'
    and navigation['goto']['elapsed_ms'] == 12046 and navigation['readiness']['elapsed_ms'] == 47
    and current['outcome'] == 'ERROR' and current['error']['codes'] == ['PROTECTED_AUTHENTICATION_UNPROVEN']
    and current['viewer_access_confirmed'] is False and current['book_identity_confirmed'] is False
    and authentication['session_receipts'] == authentication['native_http_observations'] == []
    and authentication['navigation_intents'] == 1
    and authentication['navigation_reservations'] == {'context': 1, 'native': 1},
    {'failure': current['error'], 'goto_ms': navigation['goto']['elapsed_ms'],
        'readiness_ms': navigation['readiness']['elapsed_ms'], 'successful_session_projection_count': 0,
        'authentication_state_of_actual_account': 'UNPROVEN', 'missing_projection_cause': 'UNKNOWN',
        'exact_admission_branch_cause': 'UNKNOWN_NO_BRANCH_TRACE'})
successors = {key: value for key, value in current['steps'].items() if key != 'navigation'}
check('successors_not_run_and_no_write_claim', all(value == 'NOT_RUN' for value in successors.values())
    and current['sources'] == [] and current['login_submissions'] == current['local_credential_config_reads'] == current['business_writes'] == 0
    and authentication['actual_login_post_requests'] == authentication['native_post_reservations'] == authentication['context_post_reservations'] == 0
    and current['production_ready'] is False and current['write_eligible'] is False,
    {'successor_steps': successors, 'zero_credential_IO_evidence_basis': 'Frozen source control flow and serialized counters, not OS file auditing'})
check('guard_events_are_not_http_send_counts', network['event_count'] == len(events) == 13
    and same(network['events'], events) and len(session_events) == 2
    and {event['source'] for event in session_events} == {'FETCH_REQUEST_STAGE', 'CONTEXT_FIRST_REQUEST'}
    and all(event['known_route'] == 'SESSION_PERMISSIONS' and event['decision'] == 'ALLOW' for event in session_events)
    and not any(event['business_read'] or event['category'] == 'REGISTERED_ORIGINAL' for event in events)
    and not any(event['method'] != 'GET' for event in events)
    and current['version_check']['native_send_reservations'] == current['version_check']['context_pass_reservations'] == 1
    and current['version_check']['http_success'] == 'UNKNOWN'
    and current['excluded_static']['combined_guard_events'] == current['excluded_static']['completed_denial_calls'] == 1,
    {'guard_events': len(events), 'permission_guard_events': len(session_events),
        'session_actual_http_send_or_status': 'UNKNOWN', 'version_http_success': 'UNKNOWN',
        'auxiliary_http_send_total': 'UNKNOWN', 'CDN_necessity_and_DNS_TCP_TLS': 'UNKNOWN'})

identities = []
for role, record, handle, code in [('product', launcher, 'product_handle_closed', 2),
        ('worker', worker, 'worker_handle_closed', 2), ('occupancy', occupancy, 'handle_closed', 0)]:
    before, after = record['before'], record['after']
    matched = before['pid'] == after['pid'] and before['created_filetime'] == after['created_filetime']
    released = matched and after['exit_observed'] is True and after['exit_code'] == code and record[handle] is True
    within = filetime(start) <= before['created_filetime'] <= after['exited_filetime'] <= filetime(end)
    check('held_identity_release_' + role, released and within,
        {'role': role, 'before': before, 'after': after, 'creation_identity_match': matched,
            'held_handle_closed': record[handle], 'inside_activation_window': within})
    identities.append({'role': role, **after, 'creation_identity_match': matched, 'held_handle_closed': record[handle]})
check('jobs_context_runtime_and_callbacks', launcher['job_closed'] is True and worker['job_closed'] is True
    and launcher['job_active_final'] == worker['job_active_final'] == 0 and launcher['errors'] == worker['errors'] == []
    and current['release']['context_closed'] is True and current['release']['runtime_stopped'] is True
    and current['release']['errors'] == [] and current['release']['state'] == 'RELEASED'
    and current['guard_pre_shutdown']['pending_tasks'] == current['guard_at_serialization']['pending_tasks'] == 0
    and current['excluded_static']['pending_callbacks'] == 0,
    {'two_jobs_final_active': [0, 0], 'context_runtime': current['release'], 'pending_at_serialization': 0,
        'launcher_self_OS_creation_exit_identity': 'UNKNOWN'})
stdout = (LIVE / 'launcher-stdout.bin').read_bytes()
stdout_value = json.loads(stdout)
check('stdout_and_exit_layers', len(stdout) == launch_result['stdout_bytes'] == 135
    and hashlib.sha256(stdout).hexdigest() == launch_result['stdout_sha256']
    and set(stdout_value) == {'mode', 'release', 'product_exit_code', 'errors', 'launcher_own_os_exit_identity'}
    and stdout_value['product_exit_code'] == launch_result['tool_child_returncode'] == 2
    and actual['envelope_tool_command_exit'] == 0
    and launcher['stdout_bytes'] == 90 and len(launcher['stdout_sha256']) == 64
    and worker['stdout_bytes'] == worker['stderr_bytes'] == launch_result['stderr_bytes'] == launcher['stderr_bytes'] == 0,
    {'capture_tool_exit': '0 per fixed actual report and dispatch context', 'launcher_returncode': 2,
        'product_exit': 2, 'worker_exit': 2, 'occupancy_exit': 0,
        'outer_launcher_stdout_original_bytes': len(stdout), 'outer_launcher_stdout_sha256': hashlib.sha256(stdout).hexdigest(),
        'product_stdout_bytes': 90, 'product_stdout_sha256': launcher['stdout_sha256'],
        'product_stdout_original_bytes': 'NOT_SUPPLIED_NOT_RECONSTRUCTED'})

auth_tree = ast.parse((ROOT / 'src/annotation/source/usense/current_readonly/auth.py').read_bytes().decode())
probe_tree = ast.parse((ROOT / 'tools/a16_current_state_probe.py').read_bytes().decode())
functions = {node.name: node for node in auth_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
functions.update({node.name: node for node in probe_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))})
disabled = ('credentials_from_bytes', 'read_credentials', 'known_form', 'authenticate')
check('zero_config_claim_source_basis', all(len(functions[name].body) == 1 and isinstance(functions[name].body[0], ast.Raise)
    for name in disabled), {'disabled_entry_points': list(disabled), 'product_imports_or_execution': 0,
        'OS_private_file_access_audit': 'NOT_PERFORMED'})

result = {'task': 'A22', 'kind': 'STATIC_FIXED_ACTUAL_ARCHIVE_REVIEW',
    'result': 'ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY', 'check_count': len(CHECKS),
    'checks': CHECKS, 'held_identities': identities, 'timing': timing,
    'input_members': 58, 'candidate_members': 28, 'actual_members': 28, 'authority_scope_members': 50,
    'live_used': 1, 'live_remaining': 0,
    'product_imports_runs_suites_browser_network_profile_native_or_new_live': 0,
    'private_Script_or_sidecar_read_or_copied': False,
    'root_cause': 'UNKNOWN', 'authentication_and_book_source': 'UNPROVEN',
    'limitations': ['Root-provided preservation/parent-chain and original authority equality are referenced as fixed metadata, no new Git or original private-path scan',
        'Launcher own OS creation/exit identity UNKNOWN', 'Product stdout 90 bytes has digest only; original bytes absent',
        'Wall/monotonic duration differences preserved without cause attribution',
        'Optional missing prelaunch metadata file and pre-invocation capture path correction are author transcriptions, no original failed helper output supplied',
        'Final error code lacks a branch-level trace; no claim of actual logout or failed profile persistence']}
with (OUT / 'static-record.json').open('xb') as stream:
    stream.write((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps({k: v for k, v in result.items() if k not in ('checks', 'held_identities', 'timing', 'limitations')}))
