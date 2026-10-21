"""A23 actual archive review. JSON, bytes and AST only; no product imports."""
import ast
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path

ROOT = Path('D:/1800-worktrees/a23-live-review')
OUT = ROOT / 'docs/evidence/A23/independent-live-review'
DELIVERY = ROOT / 'docs/evidence/A23/session-completion/live-delivery'
CANDIDATE = ROOT / 'docs/evidence/A23/session-completion/candidate-manifest.json'


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def same_typed(a, b):
    if type(a) is not type(b):
        return False
    if type(b) is list:
        return len(a) == len(b) and all(same_typed(x, y) for x, y in zip(a, b))
    return a == b


candidate_sha = sha(CANDIDATE)
assert candidate_sha == '18921b3335809c0c0722dc1bf8bf1495d8628bab780ce95045079c82c1f615ad'
delivery_sha = sha(DELIVERY / 'delivery-manifest.json')
assert delivery_sha == '3984da49ce141aead2d314e80274d6b1eacf246de71c9b01f11d31cdd0628c4a'
closure = []
for path, prefix, size_key in ((CANDIDATE, ROOT, 'size'),
                               (DELIVERY / 'delivery-manifest.json', DELIVERY, 'bytes')):
    manifest = load(path)
    for entry in manifest['members']:
        member = prefix / entry['path']
        # Delivery manifests may retain repository-relative paths.
        if not member.is_file() and (ROOT / entry['path']).is_file():
            member = ROOT / entry['path']
        expected_size = entry.get(size_key, entry.get('size', entry.get('bytes')))
        assert member.stat().st_size == expected_size, entry['path']
        assert sha(member) == entry['sha256'], entry['path']
    closure.append({'manifest': str(path.relative_to(ROOT)).replace('\\', '/'),
                    'members_verified': len(manifest['members'])})
assert closure[0]['members_verified'] == 29 and closure[1]['members_verified'] == 30
copy_manifest = load(DELIVERY / 'raw-copy-manifest.json')
for entry in copy_manifest['members']:
    path = DELIVERY / entry['path']
    assert path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256']
assert not copy_manifest['script_or_sidecar_copied'] and not copy_manifest['profile_or_credentials_copied']
save('closure-verification.json', {'status': 'PASS', 'manifests': closure,
    'delivery_self_sha256': delivery_sha, 'raw_copy_members_verified': len(copy_manifest['members']),
    'source_local_paths_not_opened': True})

activation = load(DELIVERY / 'activation.json')
authorization = load(DELIVERY / 'authorization.json')
preflight_report = load(DELIVERY / 'independent-result.json')
dispatch = load(DELIVERY / 'dispatch-intent.json')
prelaunch = load(DELIVERY / 'prelaunch-verification.json')
launch_intent = load(DELIVERY / 'launch-intent.json')
launch = load(DELIVERY / 'launch-result.json')
assert sha(DELIVERY / 'independent-result.json') == '80e509a7b60d73bf39961e647bc4828176ee58651dfcdcfa353dfce5f1661066'
scope = {k: v for k, v in preflight_report.items() if k != 'result'}
assert len(scope) == 53 and preflight_report['result'] == 'ACCEPTED_OFFLINE_ONLY'
assert scope['task'] == 'A23' and scope['scope'] == 'CURRENT_SESSION_COMPLETION_AND_SOURCE_READONLY'
for document in (activation, authorization):
    assert all(same_typed(document.get(k), v) for k, v in scope.items())
for key, value in scope.items():
    if key != 'candidate_manifest_sha256':
        assert same_typed(load(CANDIDATE).get(key), value), key
assert activation['candidate_manifest_sha256'] == candidate_sha
assert activation['profile_fingerprint'] == scope['required_profile_fingerprint']
assert sha(DELIVERY / 'authorization.json') == activation['user_decision_sha256'] == dispatch['decision_sha256']
assert sha(DELIVERY / 'independent-result.json') == activation['independent_report_sha256'] == dispatch['independent_report_sha256']
assert sha(DELIVERY / 'activation.json') == dispatch['activation_sha256']
assert sha(DELIVERY / 'task.md') == dispatch['task_sha256'] == prelaunch['task_sha256']
assert scope['standing_tls_permission_sha256'] == sha(ROOT / 'docs/evidence/A23/session-completion/authority/standing-permission.json')
assert authorization['live_authorized'] is True and authorization['certificate_exception_authorized'] is True
assert authorization['authorization_basis'] == 'A17_STANDING_READONLY_TLS_PERMISSION_BOUND_TO_A23'
for name in ('login_submission_authorized', 'credential_transmission_authorized',
             'credential_tls_exception_authorized', 'local_credential_config_read_authorized'):
    assert authorization[name] is False
assert dispatch['launch_limit'] == 1 and dispatch['retry_limit'] == 0
assert launch['launches'] == 1 and launch['retry_attempts'] == 0
assert launch_intent['argv'] == dispatch['argv'] and launch_intent['cwd'] == dispatch['cwd']
start, finish = (datetime.fromisoformat(launch[name]) for name in ('started_at', 'finished_at'))
window_start, window_end = (datetime.fromisoformat(activation[name]) for name in ('not_before', 'expires_at'))
assert (window_end - window_start).total_seconds() == 900
assert window_start <= start < finish < window_end
markers = {}
for name in ('launcher-claimed', 'worker-claimed', 'occupancy-claimed', 'live-started'):
    marker = load(DELIVERY / ('raw/' + name + '.json'))
    assert marker['activation_sha256'] == dispatch['activation_sha256']
    assert marker['candidate_sha256'] == candidate_sha
    assert marker['profile_fingerprint'] == activation['profile_fingerprint']
    assert marker['run_id'] == scope['run_id'] and marker['workflow_commit'] == scope['workflow_commit']
    markers[name] = marker
profile = load(DELIVERY / 'raw/profile-binding.json')
assert profile['fingerprint'] == activation['profile_fingerprint']
save('authority-binding.json', {'status': 'PASS', 'scope_fields': 53, 'candidate_sha256': candidate_sha,
    'activation_sha256': sha(DELIVERY / 'activation.json'),
    'decision_sha256': sha(DELIVERY / 'authorization.json'),
    'preflight_report_sha256': sha(DELIVERY / 'independent-result.json'),
    'launches': 1, 'retries': 0, 'marker_files_bound': list(markers),
    'window_utc': {'start': activation['not_before'], 'end': activation['expires_at']},
    'actual_launch_start_utc': launch['started_at'], 'actual_launch_end_utc': launch['finished_at'],
    'profile_binding': 'Fixed fingerprint metadata only; actual profile files not read by reviewer',
    'no_new_login_or_write_authority': True})

raw = load(DELIVERY / 'raw/current-state.json')
events = raw['network_audit']
audit = load(DELIVERY / 'network-audit.json')
assert events == audit['events'] and len(events) == audit['event_count'] == 16
assert raw['outcome'] == 'ERROR' and raw['error']['codes'] == ['BOOK_IDENTITY_REJECTED']
assert raw['guard_pre_shutdown']['failure'] == raw['error'] == raw['guard_at_serialization']['failure']
assert raw['guard_pre_shutdown']['pending_tasks'] == raw['guard_at_serialization']['pending_tasks'] == 0
assert raw['steps']['navigation'] == raw['steps']['session_completion'] == raw['steps']['book'] == 'DONE'
assert raw['book_identity_confirmed'] is False and raw['viewer_access_confirmed'] is True
assert raw['account_identity_fields_available'] == 'NOT_OBSERVED'
auth = raw['authentication']
assert auth['navigation_intents'] == 1 and auth['navigation_reservations'] == {'context': 1, 'native': 1}
assert auth['phase'] == 'VIEWER' and auth['session_completion_mode'] == 'EXISTING_SESSION'
assert auth['active_profile_intents'] == 0 and auth['session_completion_timeout_seconds'] == 20
assert auth['native_http_observations'] == [{'association': 'ORIGINAL_FRAME_RESERVED_NETWORK_ID', 'http_status': 200, 'route': 'permissions'}]
assert auth['session_receipts'] == [{'authenticated_profile_fields_present': False,
    'business_decode': 'ACCEPTED_NUMERIC_CODE', 'credential_return_present': 'NOT_INSPECTED',
    'http_status': 200, 'phase': 'VIEWER', 'route': 'permissions'}]
assert auth['protected_viewer_authenticated'] is True and auth['reused_without_credentials'] is True
permissions = [event for event in events if event['known_route'] == 'SESSION_PERMISSIONS']
books = [event for event in events if event['category'] == 'BUSINESS_BOOK']
for pair in (permissions, books):
    assert len(pair) == 2
    assert {event['source'] for event in pair} == {'FETCH_REQUEST_STAGE', 'CONTEXT_FIRST_REQUEST'}
    assert all(event['method'] == 'GET' and event['decision'] == 'ALLOW' and not event['redirect_hop'] for event in pair)
assert all(event['path_template'] == '/qieti/api/user_login/config/permissions' for event in permissions)
assert all(event['path_template'] == '/qieti/api/claim_book/books' for event in books)
assert all(event['method'] == 'GET' for event in events)
assert not any(event['category'].startswith('BUSINESS_') and event['category'] != 'BUSINESS_BOOK' for event in events)
navigation = raw['navigation_diagnostics']
assert navigation['goto']['http_status'] == 200 and navigation['goto']['state'] == 'DONE'
assert navigation['domcontentloaded_observed'] is True and navigation['readiness']['state'] == 'DONE'
assert navigation['response_received']['http_status'] == 200 and navigation['response_received']['observed'] is True
later = {k: v for k, v in raw['steps'].items() if k not in ('navigation', 'session_completion', 'book')}
assert all(value == 'NOT_RUN' for value in later.values())
assert raw['sources'] == [] and raw['write_eligible'] is False and raw['production_ready'] is False
assert raw['body_status'] == raw['schema_status'] == 'UNKNOWN'
assert raw['sample']['status'] == 'NOT_RUN'
assert raw['local_credential_config_reads'] == raw['login_submissions'] == raw['business_writes'] == 0
assert raw['excluded_static']['combined_guard_events'] == raw['excluded_static']['completed_denial_calls'] == 1
assert raw['excluded_static']['pending_callbacks'] == 0
assert load(DELIVERY / 'session-projection.json')['session_receipts'] == auth['session_receipts']
save('actual-observations.json', {'status': 'SUPPORTED_WITH_LIMITS', 'first_failure': raw['error'],
    'navigation': navigation, 'current_session_finite_projection': auth,
    'association_limit': 'Recorded association labels and fixed original request/frame/network-ID guard branches support the bounded combination; raw frame/request/network identifiers were not separately retained for reviewer equality comparison',
    'viewer_combination_admitted': True, 'account_identity': 'NOT_OBSERVED',
    'profile_persistence': 'UNPROVEN', 'book_identity_confirmed': False, 'book_step': 'DONE',
    'book_native_allow_reservations': 1, 'book_context_allow_events': 1,
    'book_actual_response_HTTP_or_body': 'NOT_RETAINED',
    'book_static_control_flow_inference': 'get_once returned after internal business HTTP200/dict-body/integer-code0 checks; book_identity then rejected. This is fixed-code inference, not retained HTTP/body/code proof',
    'book_rejection_alternatives': ['no matching data.id46007447 projection', 'conflicting matching projections'],
    'which_rejection_alternative': 'UNKNOWN', 'wrong_book': 'UNPROVEN', 'parser_or_structure_mismatch': 'UNPROVEN',
    'later_steps': later, 'audit_event_count': 16, 'audit_event_count_is_not_HTTP_count': True,
    'total_auxiliary_or_session_HTTP_sends': 'UNKNOWN', 'version_check': raw['version_check'],
    'excluded_static': raw['excluded_static'], 'write_eligible': False, 'production_ready': False,
    'sources': [], 'login_submissions': 0, 'credential_config_reads': 0, 'business_writes': 0,
    'private_full_script_and_sidecar': 'Not opened or copied by reviewer'})

held_records = [('product', load(DELIVERY / 'raw/launcher-release.json')),
                ('worker', load(DELIVERY / 'raw/worker-release.json')),
                ('occupancy', load(DELIVERY / 'raw/occupancy.json'))]
held = []
for role, record in held_records:
    before, after = record['before'], record['after']
    assert before['pid'] == after['pid'] and before['created_filetime'] == after['created_filetime']
    assert before['exit_observed'] is False and after['exit_observed'] is True
    assert after['exited_filetime'] >= after['created_filetime']
    assert after['exit_code'] == (0 if role == 'occupancy' else 2)
    assert record['handle_closed'] if role == 'occupancy' else record[role + '_handle_closed']
    held.append({'role': role, **after, 'creation_identity_match': True, 'held_handle_closed': True})
launcher, worker = held_records[0][1], held_records[1][1]
for record in (launcher, worker):
    assert record['state'] == 'RELEASED' and record['job_assigned'] is True
    assert record['job_active_final'] == 0 and record['job_closed'] is True and record['errors'] == []
assert launcher['total_deadline_exceeded'] is False and worker['hard_deadline_exceeded'] is False
assert raw['release'] == {'context_close_attempted': True, 'context_closed': True, 'context_created': True,
    'errors': [], 'runtime_stop_attempted': True, 'runtime_stopped': True, 'state': 'RELEASED'}
assert launch['tool_child_returncode'] == 2
outer_raw = (DELIVERY / 'launcher-stdout.bin').read_bytes()
assert len(outer_raw) == launch['stdout_bytes'] == 135
assert hashlib.sha256(outer_raw).hexdigest() == launch['stdout_sha256']
outer = json.loads(outer_raw)
assert outer == {'mode': 'LIVE_FINISHED', 'release': 'RELEASED', 'product_exit_code': 2,
                 'errors': False, 'launcher_own_os_exit_identity': 'UNKNOWN'}
assert launcher['stdout_bytes'] == 90 and launcher['stdout_sha256'] == 'ed0b9d6b1782011eda49d407345fd5809ec7d103eec21edd2f0d8ec6e486a423'
assert launch['stderr_bytes'] == launcher['stderr_bytes'] == 0
release = load(DELIVERY / 'release.json')
for entry in held:
    matching = next(item for item in release['held_process_identities'] if item['role'] == entry['role'])
    assert all(matching[key] == entry[key] for key in ('pid', 'created_filetime', 'exited_filetime', 'exit_code', 'exit_observed', 'creation_identity_match'))
save('owned-release-verification.json', {'status': 'ACCEPTED_FIXED_OWNED_RESOURCES_ONLY',
    'held_processes': held, 'product_job': {k: launcher[k] for k in ('job_assigned', 'job_active_before_final_cleanup', 'job_active_final', 'job_closed')},
    'worker_job': {k: worker[k] for k in ('job_assigned', 'job_active_before_final_cleanup', 'job_active_final', 'job_closed')},
    'context_runtime': raw['release'], 'guard_pending_tasks_at_serialization': 0,
    'guard_pending_callbacks': raw['excluded_static']['pending_callbacks'],
    'launcher_self_OS_identity_and_exit': 'UNKNOWN', 'outer_child_returncode': 2,
    'product_and_worker_exit_codes': [2, 2], 'envelope_tool_exit_code_as_reported': 0,
    'outer_stdout_raw_bytes_and_SHA_verified': {'bytes': 135, 'sha256': launch['stdout_sha256']},
    'outer_errors_false_means': 'Release errors absent; product business outcome remains ERROR',
    'product_stdout': {'bytes': 90, 'sha256': launcher['stdout_sha256'], 'raw_available': False},
    'stderr': {'bytes': 0, 'digest': launch['stderr_sha256'], 'raw_saved': False},
    'no_deadline_overrun_recorded': True, 'scope_limit': 'Fixed retained held identities/Jobs/context/runtime only; no new native API, process census or global release assertion'})

timings = []
for name, record in [('envelope', launch), ('launcher_product_release', launcher), ('worker_release', worker)]:
    wall = (datetime.fromisoformat(record['finished_at']) - datetime.fromisoformat(record['started_at'])).total_seconds() * 1000
    entry = {'record': name, 'started_at': record['started_at'], 'finished_at': record['finished_at'],
             'recorded_monotonic_duration_ms': record['duration_ms'], 'wall_span_ms': round(wall, 6),
             'monotonic_minus_wall_ms': round(record['duration_ms'] - wall, 6)}
    if 'before' in record:
        entry['held_OS_lifetime_ms'] = str(Decimal(record['after']['exited_filetime'] - record['before']['created_filetime']) / Decimal(10000))
    timings.append(entry)
save('timing-and-stdout-limits.json', {'timings': timings, 'exact_difference_cause': 'UNKNOWN',
    'clock_scope': 'Each declared own-process monotonic measurement retained; wall and FILETIME spans are separate observations',
    'product_stdout_original_bytes': 'NOT_RETAINED; do not reconstruct from digest or outer 135-byte JSON',
    'launcher_self_OS_creation_exit_identity': 'UNKNOWN'})

source_refs = []
regions_needed = {
    'src/annotation/source/usense/current_readonly/auth.py': {'response_projection', 'AuthFlow.record_session', 'AuthFlow.admit_viewer'},
    'src/annotation/source/usense/current_readonly/decode.py': {'business', 'book_identity'},
    'tools/a16_current_state_probe.py': {'CurrentGuard.native_response', 'CurrentGuard.capture', 'check_current_viewer',
        'complete_current_session', 'admit_current_viewer', 'get_once', 'collect', 'supervise', 'occupancy'},
    'tools/a16_current_state_launcher.py': {'main'},
}
for relative, needed in regions_needed.items():
    source = (ROOT / relative).read_bytes().decode('utf-8')
    tree = ast.parse(source)
    nodes = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nodes[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    nodes[node.name + '.' + child.name] = child
    for name in sorted(needed):
        node = nodes[name]
        source_refs.append({'path': relative, 'name': name, 'start': node.lineno, 'end': node.end_lineno,
                            'source_region_sha256': hashlib.sha256(ast.get_source_segment(source, node).encode('utf-8')).hexdigest()})
save('fixed-source-references.json', {'product_imports': 0, 'method': 'AST source location and exact region bytes only', 'regions': source_refs})
print(json.dumps({'status': 'STATIC_ACTUAL_FACTS_AND_OWN_RELEASE_VERIFIED', 'raw_inputs': 64,
    'delivery_members': 30, 'candidate_dependencies': 29, 'typed_scope_fields': 53,
    'first_failure': 'BOOK_IDENTITY_REJECTED', 'held_processes': 3, 'closed_jobs': 2,
    'new_product_imports_or_suite_runs_or_live_requests': 0}))
