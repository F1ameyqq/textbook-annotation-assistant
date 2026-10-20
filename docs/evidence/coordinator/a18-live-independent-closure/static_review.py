"""Static JSON/byte review only. No product/native/browser imports or live I/O."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path('D:/1800-worktrees/a18-live-review')
OUT = Path(__file__).resolve().parent
LIVE = ROOT / 'docs/evidence/A18/current-frontend/live-delivery'
RAW = LIVE / 'raw'
INPUT = Path('D:/1800/docs/evidence/coordinator/a18-live-delivery/input-raw-manifest.json')
INPUT_SHA = '116c65b8ec1497d1e05a65a8c88139f76252162c08360239e163d36c407708fd'
CANDIDATE = 'c0f7ea30ee5a3484544524b5e8c609125113a474d901bd24fc600529509ae8e8'
ACTIVATION = '2401b8aa6c57f09fbdfa1aefb61d3c3663d362ca99e095f5a3339164498717e8'
sha = lambda b: hashlib.sha256(b).hexdigest()
load = lambda p: json.loads(p.read_bytes())
dt = lambda v: datetime.fromisoformat(v.replace('Z', '+00:00'))
now = datetime.now(timezone(timedelta(hours=8))).isoformat()


def write(name, value):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def verify(items):
    checked = []
    for entry in items:
        raw = (ROOT / entry['path']).read_bytes()
        assert len(raw) == entry['size'] and sha(raw) == entry['sha256'], entry['path']
        checked.append({'path': entry['path'], 'size': len(raw), 'sha256': sha(raw)})
    return checked


assert sha(INPUT.read_bytes()) == INPUT_SHA
inputs = load(INPUT)
assert len(inputs['members']) == 45
fixed = verify(inputs['members'])
candidate_path = ROOT / 'docs/evidence/A18/current-frontend/candidate-manifest.json'
assert sha(candidate_path.read_bytes()) == CANDIDATE
candidate = load(candidate_path)
assert len(candidate['members']) == 22
verify(candidate['members'])
author_manifest = load(LIVE / 'sha256-manifest.json')
assert sha((LIVE / 'sha256-manifest.json').read_bytes()) == '0fe6579613308291a5da6c7b2ae9863ee4b7a45a92ff4e168e608df34bb6f5fb'
assert len(author_manifest['members']) == 21
verify(author_manifest['members'])
assert sha((LIVE / 'REPORT.md').read_bytes()) == '6ef3e2d208abafd9af0078ba454b829db5b03bb1688dcdb1d80d102caaeadb5e'

current = load(RAW / 'current-state.json')
product = load(RAW / 'launcher-release.json')
worker = load(RAW / 'worker-release.json')
occupancy = load(RAW / 'occupancy.json')
dispatch = load(LIVE / 'authority/dispatch-intent.json')
bindings = load(LIVE / 'bindings.json')
intent = load(RAW / 'launcher-intent.json')
tool = load(LIVE / 'execution-tool-result.json')
projection = load(LIVE / 'result.json')
release_projection = load(LIVE / 'release.json')
network_projection = load(LIVE / 'network-audit.json')

# Four exclusive stage markers form the single retained start chain.
names = ['launcher-claimed.json', 'live-started.json', 'worker-claimed.json', 'occupancy-claimed.json']
markers = [load(RAW / name) for name in names]
assert all(m == markers[0] for m in markers)
expected_marker = {
    'activation_sha256': ACTIVATION, 'candidate_sha256': CANDIDATE,
    'certificate_exception': True, 'profile_fingerprint': dispatch['profile_fingerprint'],
    'run_id': candidate['run_id'], 'sample_limit': 0, 'scope': candidate['scope'],
    'task': 'A18', 'workflow_commit': candidate['workflow_commit']
}
assert markers[0] == expected_marker
assert load(RAW / 'profile-binding.json')['fingerprint'] == dispatch['profile_fingerprint']
assert dispatch['activation_sha256'] == ACTIVATION == product['activation_sha256'] == intent['activation_sha256']
assert dispatch['candidate_sha256'] == CANDIDATE == intent['candidate_sha256']
assert dispatch['thread_id'] == candidate['executor_thread_id']
assert dispatch['product_workflow'] == candidate['workflow_commit']
assert dispatch['launch_limit'] == 1 and dispatch['retry_limit'] == 0
assert dispatch['decision_sha256'] == 'a2939da9bb5e9601bdc020c28699669c982e2c2717d9c2291dd5132e21d87989'
assert dispatch['independent_report_sha256'] == '2aa02472228a65dc6d46d8576225c882c0f2aee4a8eaf9ba925da56046245230'
assert dispatch['standing_permission_sha256'] == 'f5ceacf9028f773ead882f3e6601004c2c3e28171be31abb85c5be99a1d67b46'
assert sha((LIVE / 'authority/dispatch-intent.json').read_bytes()) == bindings['dispatch_intent_sha256']
assert sha((LIVE / 'authority/task.md').read_bytes()) == dispatch['task_sha256']
for source in bindings['source_members']:
    data = (LIVE / source['archive_path']).read_bytes()
    assert len(data) == source['size'] and sha(data) == source['sha256']
assert len(bindings['source_members']) == 10

start, end = dt(dispatch['not_before']), dt(dispatch['expires_at'])
assert (end - start).total_seconds() == 900
for record in (current, worker, product):
    assert start <= dt(record['started_at']) <= dt(record['finished_at']) <= end
assert product['total_deadline_exceeded'] is False and worker['hard_deadline_exceeded'] is False
assert product['duration_ms'] == 14844 and worker['duration_ms'] == 14188

# The raw Error/UNKNOWN is not interpreted as TLS/CDN/PATH_BLOCKED/timeout.
assert current['outcome'] == 'ERROR'
assert current['error'] == {'exception_type': 'Error', 'codes': ['UNKNOWN']}
assert current['steps']['navigation'] == 'FAILED'
assert len(current['steps']) == 16
assert sum(v == 'NOT_RUN' for v in current['steps'].values()) == 15
assert current['guard_pre_shutdown'] == {'failure': None, 'pending_tasks': 0,
    'shutdown_started': False, 'stopped': False, 'terminal_stopped': False}
assert current['guard_at_serialization'] == {'failure': None, 'pending_tasks': 0,
    'shutdown_started': True, 'stopped': True, 'terminal_stopped': False}
assert current['excluded_static']['combined_guard_events'] == 0
assert current['excluded_static']['completed_denial_calls'] == 0
assert current['excluded_static']['pending_callbacks'] == 0
assert current['version_check']['native_send_reservations'] == 0
assert current['version_check']['context_pass_reservations'] == 0
events = current['network_audit']
assert len(events) == 2
assert {e['source'] for e in events} == {'FETCH_REQUEST_STAGE', 'CONTEXT_FIRST_REQUEST'}
assert all(e['category'] == 'NAVIGATION' and e['decision'] == 'ALLOW' and e['method'] == 'GET'
    and e['resource_type'] == 'Document' and e['main_navigation'] is True
    and not e['redirect_hop'] and not e['business_read'] for e in events)
assert len({e['path_sha256'] for e in events}) == 1
assert events[0]['path_sha256'] == sha(b'/qieti/annotateUnified')
assert network_projection['events'] == events
assert current['sources'] == [] and current['static_assets'] == []
assert current['sample']['status'] == 'NOT_RUN' and current['sample_limit'] == 0
assert current['automatic_schema_confirmation'] is False
assert current['body_status'] == current['schema_status'] == 'UNKNOWN'
assert current['production_ready'] is current['write_eligible'] is False
assert current['business_writes'] == current['login_submissions'] == 0
assert projection['business_gets_executed'] == projection['original_gets_executed'] == 0
assert projection['new_live_used'] == 1 and projection['new_live_remaining'] == 0

processes = []
for role, record, code, handle in (
    ('occupancy', occupancy, 0, 'handle_closed'),
    ('worker', worker, 2, 'worker_handle_closed'),
    ('product', product, 2, 'product_handle_closed')):
    before, after = record['before'], record['after']
    assert type(before['pid']) is int and before['pid'] > 0
    assert type(before['created_filetime']) is int and before['created_filetime'] > 0
    assert (before['pid'], before['created_filetime']) == (after['pid'], after['created_filetime'])
    assert after['exit_observed'] is True and after['exit_code'] == code
    assert after['exited_filetime'] >= after['created_filetime']
    assert record[handle] is True
    processes.append({'role': role, 'pid': before['pid'], 'created_filetime': before['created_filetime'],
        'exit_observed': True, 'exit_code': code, 'handle_closed': True, 'identity_match': True})
assert occupancy['matching_processes'] == 0
for record in (worker, product):
    assert record['state'] == 'RELEASED' and record['errors'] == []
    assert record['job_assigned'] is True and record['job_active_final'] == 0 and record['job_closed'] is True
assert worker['creation_identity_match'] is True
assert current['release'] == {'context_close_attempted': True, 'context_closed': True, 'context_created': True,
    'errors': [], 'runtime_stop_attempted': True, 'runtime_stopped': True, 'state': 'RELEASED'}
assert release_projection['context_runtime'] == current['release']
assert release_projection['worker'] == worker
assert release_projection['product_and_launcher_owned_job'] == product
assert release_projection['occupancy'] == occupancy
assert tool['completion_tool_exit_code'] == 1 and tool['retries'] == 0
assert json.loads(tool['completion_output']) == {'mode': 'LIVE_FINISHED', 'release': 'RELEASED',
    'product_exit_code': 2, 'errors': False, 'launcher_own_os_exit_identity': 'UNKNOWN'}

timing = []
for role, record in (('launcher_record', product), ('worker_record', worker), ('observation_record', current)):
    span = dt(record['finished_at']) - dt(record['started_at'])
    micros = span.days * 86400000000 + span.seconds * 1000000 + span.microseconds
    timing.append({'record': role, 'UTC_elapsed_microseconds': micros, 'monotonic_duration_ms': record.get('duration_ms'),
        'recorded_monotonic_minus_UTC_microseconds': record['duration_ms'] * 1000 - micros if 'duration_ms' in record else None,
        'difference_exact_breakdown': 'UNKNOWN'})

audit = {'task': 'A18', 'mode': 'STATIC_RECORD_REVIEW_ONLY', 'fixed_raw_verified': 45,
    'candidate_dependencies_verified': 22, 'author_delivery_members_verified': 21,
    'input_manifest_sha256': INPUT_SHA, 'fixed_members': fixed,
    'author_manifest_sha256': sha((LIVE / 'sha256-manifest.json').read_bytes()),
    'four_markers_equal': True, 'marker': expected_marker, 'source_raw_members_verified': 10,
    'binding_references_consistent': True, 'activation_decision_raw_reopened': False,
    'binding_limit': 'Activation/decision/old independent report are fixed digest references in this45raw package; original files and live/local source not reread',
    'window': {'not_before': dispatch['not_before'], 'expires_at': dispatch['expires_at'], 'seconds': 900,
        'recorded_start_finish_inside_window': True}, 'timing': timing,
    'failure': current['error'], 'navigation': 'FAILED', 'successors_NOT_RUN': 15,
    'audit_events': events, 'same_navigation_path_hash': True,
    'HTTP_total': 'UNKNOWN', 'navigation_HTTP_status': 'UNKNOWN', 'auxiliary_HTTP_sends': 'UNKNOWN',
    'business_gets': 0, 'original_gets': 0, 'version_reservations': 0, 'excluded_events': 0,
    'owned_processes': processes, 'owned_jobs_closed_and_active_zero': 2,
    'context_runtime_release_verified': True, 'launcher_own_OS_identity': 'UNKNOWN',
    'tool_completion_exit_code': 1, 'held_product_exit_code': 2, 'held_worker_exit_code': 2,
    'guard_first_cause': None, 'transport_root_cause': 'UNKNOWN',
    'product_imports_runs_suites_new_probes': 0,
    'preservation_reference': {'basis': 'Coordinator fixed raw Git verification stated in task/dispatch; no repeated whole-tree scan by reviewer',
        'baseline_members': 31655, 'preserved': 31655, 'new_members': 22, 'old_modifications': 0, 'deletions': 0,
        'final_direct_parent': 'a1dae2efb49f39700194f912bf4ce8404950699b'}}
write('input-evidence-audit.json', audit)
checks = [
    {'id': 'L0', 'result': 'PASS', 'claim': '45raw、候选22依赖、作者21成员+清单原bytes核证；10份原始结果复制hash匹配'},
    {'id': 'L1', 'result': 'PASS_REFERENCE_CONSISTENCY', 'claim': 'A18身份、四阶段标记、候选/activation/profile/workflow及固定窗口引用一致；未读原activation/决定'},
    {'id': 'L2', 'result': 'ACCEPT_FIXED_FAILURE', 'claim': 'navigation FAILED，Error/UNKNOWN；15后继NOT_RUN，无guard首错；不推断TLS/CDN/timeout'},
    {'id': 'L3', 'result': 'PASS_RECORDED_COUNTS_ONLY', 'claim': '双层同一导航2ALLOW；六GET/两图/version预留/共享排除0；HTTP发送总数和状态UNKNOWN'},
    {'id': 'L4', 'result': 'PASS_RECORDED_WINDOW_ONLY', 'claim': '固定UTC窗口900秒；launcher/worker/观测记录起止均在窗内；计时差组成UNKNOWN'},
    {'id': 'L5', 'result': 'ACCEPT_OWN_RELEASE_ONLY', 'claim': '3自有进程前后PID/creation一致、exit0/2/2及句柄关闭；2Job active0且关闭；context/runtime关闭；launcher自身OS身份UNKNOWN'},
    {'id': 'L6', 'result': 'PRESERVED_UNKNOWN_BOUNDARIES', 'claim': '认证/书身份未证，库存与覆盖UNKNOWN，正文/schemaUNKNOWN、sample0及写资格false；0重跑/新探测/产品导入'}
]
write('checks.json', {'task': 'A18', 'checks': checks, 'raw_basis': 'input-evidence-audit.json', 'product_or_suite_runs': 0})
result = {'schema': 'A18-independent-fixed-live-review/v1', 'task': 'A18',
    'result': 'ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY', 'acceptance_basis': 'STATIC_FIXED_RAW_RECORDS',
    'reviewer_thread_id': '01a15954-997c-7af2-9645-a4e2c2b25e76',
    'executor_thread_id': '01a15954-3ca1-76a3-a984-13229a985976',
    'review_dispatch_workflow_commit': '6c1bed640734c3cdf83743002b0021455a75ef7e',
    'review_task_sha256': '11a5148dbc69f07206697ff778bc4ecbc15013397291e52662864da3dbb231e9',
    'product_workflow_commit': candidate['workflow_commit'], 'live_dispatch_workflow_commit': '101ce7f1043a64df6e318775e3820b369fc6e60d',
    'product_commit': '45174e312ad23af349b3345be23eadb7f6a5e498',
    'offline_final': 'a1dae2efb49f39700194f912bf4ce8404950699b',
    'actual_final': '35ad2ef50088373435f48f530efe32b59824da8e',
    'candidate_manifest_sha256': CANDIDATE, 'activation_sha256_reference': ACTIVATION,
    'run_id': candidate['run_id'], 'scope': candidate['scope'], 'created_at': now,
    'input_raw_manifest_sha256': INPUT_SHA, 'input_raw_members_verified': 45,
    'author_delivery_members_verified': 21, 'candidate_dependencies_verified': 22,
    'new_live_used': 1, 'new_live_remaining': 0, 'retry_authorized': False,
    'recorded_launcher_startups': 1, 'recorded_contexts_created': 1, 'recorded_navigation_attempts': 1,
    'outcome': 'ERROR', 'navigation': 'FAILED', 'first_error': current['error'], 'successors_NOT_RUN': 15,
    'guard_failure': None, 'guard_pending_tasks': 0, 'pending_callbacks': 0,
    'audit_events': 2, 'audit_semantics': 'TWO_LAYERS_ONE_NAVIGATION',
    'business_gets': 0, 'original_gets': 0, 'version_native_reservations': 0,
    'version_context_reservations': 0, 'excluded_events': 0, 'denials_completed': 0,
    'HTTP_total': 'UNKNOWN', 'auxiliary_HTTP_sends': 'UNKNOWN', 'navigation_HTTP_status': 'UNKNOWN',
    'transport_root_cause': 'UNKNOWN', 'timing_difference_exact_breakdown': 'UNKNOWN',
    'authentication': 'NOT_PROVEN', 'book_identity': 'NOT_PROVEN',
    'directory': {'availability': 'UNKNOWN', 'coverage': 'UNKNOWN'},
    'frames': {'availability': 'UNKNOWN', 'coverage': 'UNKNOWN'},
    'original_images': 'NOT_RUN', 'page_mapping': 'NOT_PROVEN', 'new_script_capture_count': 0,
    'body_status': 'UNKNOWN', 'schema_status': 'UNKNOWN', 'sample_limit': 0, 'sample_status': 'NOT_RUN',
    'automatic_schema_confirmation': False, 'production_ready': False, 'write_eligible': False,
    'original_R02': 'REWORK_CAPABILITY_DISABLED_NOT_FIXED',
    'owned_release': 'ACCEPTED_AS_RECORDED', 'owned_processes': processes,
    'owned_jobs_active_zero_and_closed': 2, 'context_runtime_closed': True,
    'launcher_own_OS_creation_exit_identity': 'UNKNOWN', 'tool_completion_exit_code': 1,
    'held_product_exit_code': 2, 'held_worker_exit_code': 2, 'held_occupancy_exit_code': 0,
    'activation_decision_original_raw_revalidated': False, 'fixed_binding_references_consistent': True,
    'accepted': ['Fixed failure archive and recorded bounded counts', 'Three identity-bound owned process exits/handles, two Jobs and context/runtime release'],
    'not_proven': ['Authentication/current book/source inventory/original mapping', 'Transport or TLS/CDN/timeout root cause',
        'Launcher own OS identity', 'Actual HTTP send totals and navigation status', 'Timing difference decomposition',
        'First-question content/geometry/save/refresh-reopen readback or production/write qualification'],
    'reviewer_product_imports_runs_suites': 0, 'reviewer_new_browser_network_profile_native_occupancy_calls': 0,
    'reviewer_login_business_calls': 0, 'reviewer_released': True,
    'other_three_cases': 'HOLD', 'Q22_replayed': False, 'B_messages': 0, 'book_submission': False,
    'report': 'REPORT.md', 'checks': 'checks.json', 'raw_manifest': 'sha256-manifest.json', 'release': 'release.json',
    'next_dependency': 'Coordinator disposition only; spent unique A18 live not restarted, extended or replayed'}
write('independent-result.json', result)
write('release.json', {'task': 'A18', 'reviewer_thread_id': result['reviewer_thread_id'],
    'state': 'RELEASED_STATIC_REVIEW_NO_LIVE_RESOURCES_CREATED', 'released': True,
    'basis': 'Only fixed-file reads, JSON/hash/arithmetic and new report writes; no product import/run or persistent tool session',
    'product_imports': 0, 'product_runs': 0, 'suite_runs': 0, 'browser_network_profile_credentials_native_occupancy_calls': 0,
    'login_business_calls': 0, 'original_live_local_or_author_directory_accesses': 0,
    'new_product_processes_jobs_handles': 0, 'root_or_fixed_input_edits': 0,
    'activation_or_marker_changes': 0, 'process_kills_lock_clear_retry': 0,
    'B_messages': 0, 'Q22_replayed': False, 'other_three_cases': 'HOLD',
    'no_background_waiter_or_owned_live_session_retained': True})
print(json.dumps({'result': result['result'], 'fixed_raw_verified': 45, 'owned_processes': processes,
    'UTC_window_seconds': 900, 'timing': timing, 'reviewer_released': True}))
