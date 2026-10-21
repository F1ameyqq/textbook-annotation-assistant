"""Static evidence checks only. No product imports, tests or real resources."""
import ast
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
LIVE = ROOT / 'docs/evidence/A24/current-contract/live-delivery'
RAW = LIVE / 'raw'
AUTHOR = ROOT / 'docs/evidence/A24/current-contract'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write_new(name, raw):
    with (OUT / name).open('xb') as stream:
        stream.write(raw)


def write_json(name, data):
    write_new(name, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def verify_members(document, count):
    assert len(document['members']) == count
    assert len({row['path'] for row in document['members']}) == count
    for row in document['members']:
        path = (ROOT / row['path']).resolve()
        assert ROOT.resolve() in path.parents
        raw = path.read_bytes()
        assert len(raw) == row.get('size', row.get('bytes')) and sha(raw) == row['sha256'], row['path']
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
        assert blob == row['blob'] and row['type'] == 'blob' and row['mode'] == '100644', row['path']


manifest_raw = Path('D:/1800/docs/evidence/coordinator/a24-live-delivery/input-raw-manifest.json').read_bytes()
assert sha(manifest_raw) == '5d4058dca8106214a14f1bfacf908133e69eaadb8fe6ee5e052f389041762bb5'
manifest = json.loads(manifest_raw)
assert manifest['final'] == 'a1250758d0fc14e8c7d5c827ece2c207a4d99aac'
verify_members(manifest, 70)
write_new('root-input-manifest.json', manifest_raw)
task_raw = Path('D:/1800/docs/tasks/A24-single-live-fixed-independent-review.md').read_bytes()
assert sha(task_raw) == 'd6e9fcc0d901a02daa3c49dcdcfdb8086092b6134fa76a10dab7d8da8b5443eb'
write_new('fixed-review-task.md', task_raw)
candidate_raw = (AUTHOR / 'candidate-manifest.json').read_bytes()
assert sha(candidate_raw) == 'd10e30b4567ba5c4a81b8aa53396e35619e05f191e457a40c371866499161753'
verify_members(json.loads(candidate_raw), 37)
delivery_raw = (LIVE / 'delivery-manifest.json').read_bytes()
assert sha(delivery_raw) == '1ceb1550050ccde34277e6bdb9c11ca7b809bf0a0de3441001526de455722e3d'
verify_members(json.loads(delivery_raw), 31)
copies = load(LIVE / 'raw-copy-manifest.json')['members']
assert len(copies) == 12
for row in copies:
    raw = (LIVE / row['path']).read_bytes()  # Never open the private 'source' paths.
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']

dispatch = load(LIVE / 'authority/dispatch-intent.json')
activation = load(LIVE / 'authority/activation_sha256.json')
decision = load(LIVE / 'authority/decision_sha256.json')
report = load(LIVE / 'authority/independent_report_sha256.json')
for name, field in (('activation', 'activation_sha256'), ('decision', 'decision_sha256'),
        ('independent_report', 'independent_report_sha256'), ('standing_permission', 'standing_permission_sha256')):
    assert sha((LIVE / ('authority/' + name + '_sha256.json')).read_bytes()) == dispatch[field]
assert activation['user_decision_sha256'] == dispatch['decision_sha256']
assert activation['independent_report_sha256'] == dispatch['independent_report_sha256']
assert dispatch['independent_report_sha256'] == '391dff86c7a963b6195fdd0d3d61de1d47d8e26ed05b9a125b70e93cf8b23770'
assert report['result'] == 'ACCEPTED_OFFLINE_ONLY' and decision['live_authorized'] is True
assert activation['candidate_manifest_sha256'] == sha(candidate_raw)
assert dispatch['launch_limit'] == 1 and dispatch['retry_limit'] == 0
launch_intent = load(LIVE / 'launch-intent.json')
launch = load(LIVE / 'launch-result.json')
assert launch_intent['argv'] == dispatch['argv'] and launch_intent['cwd'] == dispatch['cwd']
assert launch['launch_count'] == 1 and launch['retry_count'] == 0 and launch['second_product_launch'] is False
assert launch['outer_launcher_exit_code'] == 2
stdout = (LIVE / 'launcher-stdout.txt').read_bytes()
assert len(stdout) == launch['stdout_bytes'] == 135 and sha(stdout) == launch['stdout_sha256']
stdout_record = json.loads(stdout)
assert stdout_record['product_exit_code'] == 2 and stdout_record['release'] == 'RELEASED'
assert stdout_record['errors'] is False and stdout_record['launcher_own_os_exit_identity'] == 'UNKNOWN'

state = load(RAW / 'current-state.json')
facts = load(RAW / 'response-facts-book.json')
http = load(RAW / 'response-http-book.json')
actual = load(LIVE / 'live-result.json')
assert http['http_status'] == facts['http_status'] == 200
assert facts['business_code'] == 0 and facts['business_code_type'] == 'integer'
contract = facts['book_contract']
assert contract['selected_container'] == 'records' and contract['branch'] == 'BOOK_TARGET_ABSENT'
assert contract['data_type'] == 'object' and contract['item_count'] == contract['target_match_count'] == 0
assert contract['non_object_item_count'] == 0 and contract['target_fields'] == []
assert contract['containers'] == {name: {'length': 0, 'type': 'array'} for name in ('records', 'books', 'list')}
assert facts['structure']['fields']['data']['fields']['total'] == {'type': 'integer'}
assert facts['server_schema_confirmed'] is False and facts['raw_body_exported'] is False
assert state['outcome'] == 'ERROR' and state['error'] == actual['first_failure']
assert state['error']['codes'] == ['BOOK_TARGET_ABSENT'] and state['steps']['book'] == 'FAILED'
assert state['book_identity_confirmed'] is False and state['sources'] == []
downstream = ('directory', 'frames', 'source', 'page14', 'page173', 'original14', 'original173',
    'mapping14', 'mapping173', 'sample_frames', 'sample_info', 'content_question', 'content_choice', 'content_answer')
assert all(state['steps'][name] == 'NOT_RUN' for name in downstream)
assert state['steps']['navigation'] == state['steps']['session_completion'] == 'DONE'
navigation = state['navigation_diagnostics']
assert navigation['association'] == 'ORIGINAL_MAIN_DOCUMENT_NETWORK_ID'
assert navigation['goto']['http_status'] == 200 and navigation['domcontentloaded_observed'] is True
assert navigation['readiness']['state'] == 'DONE' and navigation['readiness']['wait_until'] == 'VISIBLE_CONTAINER'
auth = state['authentication']
assert state['viewer_access_confirmed'] is True and auth['phase'] == 'VIEWER'
assert auth['active_profile_intents'] == 0 and state['account_identity_fields_available'] == 'NOT_OBSERVED'
assert auth['native_http_observations'] == [{'association': 'ORIGINAL_FRAME_RESERVED_NETWORK_ID',
    'http_status': 200, 'route': 'permissions'}]
assert len(auth['session_receipts']) == 1
assert auth['session_receipts'][0]['business_decode'] == 'ACCEPTED_NUMERIC_CODE'
assert auth['session_receipts'][0]['authenticated_profile_fields_present'] is False
assert state['login_submissions'] == state['local_credential_config_reads'] == state['business_writes'] == 0
assert state['sample_limit'] == 0 and state['sample']['status'] == 'NOT_RUN'
assert state['body_status'] == state['schema_status'] == 'UNKNOWN'
assert not state['production_ready'] and not state['write_eligible'] and not state['automatic_schema_confirmation']

audit = load(LIVE / 'network-audit.json')['events']
assert audit == state['network_audit'] and len(audit) == 16
assert all(row['method'] == 'GET' for row in audit)
book_sends = [row for row in audit if row['category'] == 'BUSINESS_BOOK' and row['source'] == 'FETCH_REQUEST_STAGE']
assert len(book_sends) == 1
assert not [row for row in audit if row.get('business_read') and row.get('known_route') != 'book']
assert state['version_check']['http_success'] == 'UNKNOWN'
assert state['excluded_static']['combined_guard_events'] == state['excluded_static']['completed_denial_calls'] == 1

launcher = load(RAW / 'launcher-release.json')
worker = load(RAW / 'worker-release.json')
occupancy = load(RAW / 'occupancy.json')
release = load(LIVE / 'release.json')
held = []
window_start = datetime.fromisoformat(activation['not_before'])
window_end = datetime.fromisoformat(activation['expires_at'])
assert (window_end - window_start).total_seconds() == 900
assert activation['not_before'] == dispatch['not_before'] == '2026-10-21T06:19:45.162040+00:00'
assert activation['expires_at'] == dispatch['expires_at'] == '2026-10-21T06:34:45.162040+00:00'
def in_window(value):
    moment = datetime.fromisoformat(value)
    assert window_start <= moment < window_end, value
for value in (launch_intent['utc'], launch['finished_at'], launcher['started_at'], launcher['finished_at'],
        worker['started_at'], worker['finished_at'], state['started_at'], state['finished_at']):
    in_window(value)
for role, record, pid, exit_code, handle_key in (
        ('product', launcher, 55316, 2, 'product_handle_closed'),
        ('worker', worker, 19348, 2, 'worker_handle_closed'),
        ('occupancy', occupancy, 25836, 0, 'handle_closed')):
    before, after = record['before'], record['after']
    assert before['pid'] == after['pid'] == pid and before['created_filetime'] == after['created_filetime']
    assert before['exit_observed'] is False and after['exit_observed'] is True
    assert after['exit_code'] == exit_code and after['exited_filetime'] >= after['created_filetime']
    assert record[handle_key] is True
    for ticks in (after['created_filetime'], after['exited_filetime']):
        moment = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=ticks // 10)
        assert window_start <= moment < window_end
    held.append({'role': role, **after, 'creation_identity_match': True, 'handle_closed': True})
for record in (launcher, worker):
    assert record['job_active_final'] == 0 and record['job_assigned'] and record['job_closed']
    assert record['errors'] == [] and record['state'] == 'RELEASED'
assert launcher['total_deadline_exceeded'] is False and worker['hard_deadline_exceeded'] is False
assert state['release']['context_closed'] and state['release']['runtime_stopped']
assert state['release']['errors'] == [] and state['release']['state'] == 'RELEASED'
for name in ('guard_pre_shutdown', 'guard_at_serialization'):
    assert state[name]['pending_tasks'] == 0 and state[name]['failure'] == state['error']
assert release['pending_callbacks'] == 0 and release['live_used'] == 1 and release['live_remaining'] == 0
assert release['retained_author_helpers'] == []
for name in ('launcher-claimed.json', 'worker-claimed.json', 'occupancy-claimed.json', 'live-started.json'):
    marker = load(RAW / name)
    for field in ('task', 'run_id', 'workflow_commit', 'scope', 'sample_limit'):
        assert type(marker[field]) is type(activation[field]) and marker[field] == activation[field]
    assert marker['activation_sha256'] == dispatch['activation_sha256']
    assert marker['candidate_sha256'] == sha(candidate_raw)

# Include additive finite stop vocabulary; do not import/evaluate product code.
tree = ast.parse((ROOT / 'tools/a16_current_state_probe.py').read_text(encoding='utf-8'))
vocabulary = set()
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SAFE_STOP_CODES' for t in node.targets):
        vocabulary = set(ast.literal_eval(node.value.args[0]))
    if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == 'SAFE_STOP_CODES':
        vocabulary.update(ast.literal_eval(node.value.args[0]))
assert 'BOOK_TARGET_ABSENT' in vocabulary
timings = []
for role, record in (('launcher', launcher), ('worker', worker)):
    wall_ms = (datetime.fromisoformat(record['finished_at']) - datetime.fromisoformat(record['started_at'])).total_seconds() * 1000
    timings.append({'role': role, 'own_monotonic_duration_ms': record['duration_ms'],
        'UTC_endpoint_interval_ms': round(wall_ms, 3),
        'numeric_difference_ms': round(record['duration_ms'] - wall_ms, 3), 'cause_or_exact_decomposition': 'UNKNOWN'})

write_json('static-checks.json', {
    'mode': 'STATIC_METADATA_ONLY_NO_PRODUCT_IMPORT_OR_SUITE', 'result': 'PASS_BOUNDED_FIXED_EVIDENCE_CHECKS',
    'input_members': 70, 'candidate_dependencies': 37, 'delivery_members': 31, 'raw_copy_members': 12,
    'all_size_sha256_git_blob_mode_type_checks': True,
    'actual_final': manifest['final'], 'product': manifest['product'], 'candidate_sha256': sha(candidate_raw),
    'authority_digests_and_immutable_markers': 'MATCHED',
    'window': [activation['not_before'], activation['expires_at']], 'all_retained_times_in_window': True,
    'exits': {'outer_launcher': 2, 'held_product': 2, 'held_worker': 2, 'occupancy': 0,
        'capture_envelope': 'AUTHOR_RECORDED_0_NOT_PRODUCT_SUCCESS'},
    'outer_stdout': {'bytes': 135, 'sha256': sha(stdout), 'original_verified': True},
    'product_stdout': {'bytes': launcher['stdout_bytes'], 'sha256': launcher['stdout_sha256'], 'original': 'UNAVAILABLE'},
    'finite_viewer_admission': {'navigation': navigation, 'session': auth, 'account_identity': 'NOT_OBSERVED'},
    'book_query_facts': facts, 'book_total_value': 'UNKNOWN_NOT_PROJECTED',
    'downstream_NOT_RUN': list(downstream), 'sources': 0,
    'audit_event_count': 16, 'book_native_send_reservations': 1,
    'auxiliary_HTTP_send_total': 'UNKNOWN', 'version_HTTP_success': 'UNKNOWN',
    'DNS_TCP_TLS_activity': 'UNKNOWN', 'held_processes': held,
    'two_jobs_final_zero_and_closed': True, 'context_runtime_closed': True,
    'release_errors': [], 'pending_callbacks': 0, 'timing_records': timings,
    'launcher_own_OS_creation_identity': 'UNKNOWN',
    'prior_preflight_vocabulary_note': 'Prior review inspection considered initial Assign but omitted later SAFE_STOP_CODES AugAssign. Fixed source includes BOOK_TARGET_ABSENT, and actual top-level failure is consistent. Prior report preserved, no product change or rerun.',
    'current_reviewer_product_imports_suites_launchers_real_resources': 0,
    'live_used': 1, 'live_remaining': 0, 'retry': 0
})
print(json.dumps({'result': 'PASS_STATIC_FIXED_CHECKS', 'input_members': 70,
    'candidate_dependencies': 37, 'delivery_members': 31, 'raw_copies': 12,
    'book_branch': contract['branch'], 'held_processes_verified': 3, 'jobs_verified': 2}))
