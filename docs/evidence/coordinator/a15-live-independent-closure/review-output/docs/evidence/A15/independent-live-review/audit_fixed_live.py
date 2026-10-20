"""Static fixed-record review only: no product imports, suites, live/profile/native access."""
import ast
import calendar
from collections import Counter
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path('D:/1800-worktrees/a15-independent-fixed')
OUT = ROOT / 'docs/evidence/A15/independent-live-review'
EVIDENCE = ROOT / 'docs/evidence/A15/certificate-exception'
LIVE = EVIDENCE / 'live-observation-delivery'
PRIOR = '7432122b9fd5602785ebfb2b3f24e407fdf76eda'
FINAL = '49e5ab4e804e0f35b665a61bd63343184eda0fdb'
MANIFEST_SHA = 'bcbfd3d043276c3cf580c1b1ba7b903d25e052e8ece8142416a06d2d6a458c51'
ACTIVATION_SHA = '45d418b27b55f5b3230ec431fbbe74d5ce99064440f6d35005cd72876135d3b2'
CANDIDATE_SHA = '78382e0b484ad46ab497217683fa3022440a1f570589f538c3d355670d552652'
INDEPENDENT_REPORT_SHA = 'a26530da782df64e29afce5f0749ec54e62f991926487fed70b28603c8fd94f9'
git_calls = []

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')

def save(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write(encode(value))

def read(path):
    return json.loads(path.read_bytes())

def git(*args):
    argv = ['git', '-c', 'core.longpaths=true', '-C', 'D:/1800', *args]
    result = subprocess.run(argv, env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'},
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    git_calls.append({'argv': argv, 'GIT_NO_LAZY_FETCH': '1', 'exit_code': result.returncode,
                      'stdout_bytes': len(result.stdout), 'stderr_bytes': len(result.stderr)})
    assert result.returncode == 0
    return result.stdout

def parse_tree(raw):
    entries = {}
    for item in raw.split(b'\0'):
        if item:
            identity, path = item.split(b'\t', 1)
            entries[path.decode('utf-8')] = identity.decode('ascii')
    return entries

def utc_ticks(text):
    """Exact 100ns UTC parser: retain all seven PowerShell fractional digits."""
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,7}))?(?:Z|\+00:00)', text)
    assert match, text
    base = datetime.strptime(match.group(1), '%Y-%m-%dT%H:%M:%S')
    seconds = calendar.timegm(base.timetuple())
    fraction = int((match.group(2) or '').ljust(7, '0'))
    return seconds * 10000000 + fraction

manifest_path = LIVE / 'delivery-raw-manifest.json'
manifest_raw = manifest_path.read_bytes()
assert sha(manifest_raw) == MANIFEST_SHA
manifest = json.loads(manifest_raw)
prior_tree = parse_tree(git('ls-tree', '-r', '-z', PRIOR))
final_tree = parse_tree(git('ls-tree', '-r', '-z', FINAL))
assert len(prior_tree) == 31259
assert not [path for path, identity in prior_tree.items() if final_tree.get(path) != identity]
additions = sorted(set(final_tree) - set(prior_tree))
assert len(additions) == 27 and all(path.startswith('docs/evidence/A15/certificate-exception/live-observation-delivery/') for path in additions)
verified = []
for item in manifest['members']:
    relative = Path(item['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    raw = (ROOT / relative).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    assert (len(raw), sha(raw), blob) == (item['size'], item['sha256'], item['git_blob_expected'])
    assert final_tree[item['path']] == '100644 blob ' + blob
    verified.append({'path': item['path'], 'size': len(raw), 'sha256': sha(raw), 'git_blob': blob})
assert len(verified) + 1 == 74
assert git('cat-file', 'blob', FINAL + ':' + manifest_path.relative_to(ROOT).as_posix()) == manifest_raw
old_independent = ROOT / 'docs/evidence/A15/independent-preflight'
old_manifest_raw = (old_independent / 'manifest.json').read_bytes()
assert sha(old_manifest_raw) == 'b5638f3a4287b945276a09c17b0bc9f183266e1616ce546248f806cf8fa8c3cb'
for item in json.loads(old_manifest_raw)['members']:
    assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
assert sha((ROOT / 'r1-reference.py').read_bytes()) == '3f1e4a425e18ed0e2a28893989f31677ba6b9b7f4b9c3da2800bc925443999c9'
assert sha((EVIDENCE / 'candidate-manifest.json').read_bytes()) == CANDIDATE_SHA
candidate = read(EVIDENCE / 'candidate-manifest.json')
assert len(candidate['members']) == 22
activation_raw = (LIVE / 'activation.json').read_bytes()
activation = json.loads(activation_raw)
assert sha(activation_raw) == ACTIVATION_SHA
fixed_fields = {'business_write_limit': 0, 'candidate_manifest_sha256': CANDIDATE_SHA,
 'certificate_exception': True, 'context_limit': 1,
 'coordinator_thread_id': '01a15768-1e2d-7781-b29f-1f7376270216',
 'independent_preflight': 'ACCEPTED_OFFLINE_ONLY', 'independent_report_sha256': INDEPENDENT_REPORT_SHA,
 'login_submission_limit': 0, 'navigation_limit': 1, 'new_live_limit': 1,
 'old_budgets_restored': False, 'output_directory': 'D:/1800/.local/stages/a15-cert-reuse-live',
 'proposal_sha256': 'eb6aea7ad9b01ccbcaf7710c9c45d7c5c3a80d6efcef4db857838d204d725656',
 'run_id': 'A15-cert-reuse-01a157fd-c8e7-71e1-881a-7f766b4af082',
 'schema': 'A15-live-activation/v1', 'target': 'https://www.usense.com/qieti/annotateUnified',
 'task': 'A15', 'user_decision_sha256': '36ffcbb42c030192313773b510c69598651b2c2ffe5fb54162c46b8041e40763',
 'workflow_commit': 'ec69a4bfd72b64e3bd6c6435ef0ec780fd109249'}
assert set(activation) == set(fixed_fields) | {'not_before', 'expires_at', 'profile_fingerprint'}
for key, value in fixed_fields.items():
    assert type(activation[key]) is type(value) and activation[key] == value
assert re.fullmatch('[0-9a-f]{64}', activation['profile_fingerprint'])
assert sha((LIVE / 'independent-offline-report.json').read_bytes()) == INDEPENDENT_REPORT_SHA
assert (LIVE / 'independent-offline-report.json').read_bytes() == (old_independent / 'report.json').read_bytes()
dispatch = read(LIVE / 'dispatch-intent.json')
acceptance = read(LIVE / 'coordinator-offline-acceptance.json')
assert acceptance['decision'] == 'ACCEPTED_OFFLINE_ONLY' and acceptance['report_sha256'] == INDEPENDENT_REPORT_SHA
for key in ('activation_sha256', 'candidate_sha256', 'profile_fingerprint'):
    assert dispatch[key] == {'activation_sha256': ACTIVATION_SHA, 'candidate_sha256': CANDIDATE_SHA,
                             'profile_fingerprint': activation['profile_fingerprint']}[key]
assert dispatch['execution_thread_id'] == '01a157fd-c8e7-71e1-881a-7f766b4af082'
assert dispatch['review_thread_id'] == '01a157fe-5cc9-7d91-8bbe-73b376cbe2a5'
assert dispatch['output'] == activation['output_directory'] and dispatch['new_live_limit'] == 1
assert dispatch['no_retries'] is True and dispatch['old_budgets_restored'] is False
command = read(LIVE / 'command-result.json')
assert command['invocations'] == 1 and command['exit_code'] == 2 and command['no_retry'] is True
assert command['candidate_modified'] is False and command['launcher_own_retained_os_identity'] == 'UNKNOWN'
expected_command = ('python -B tools/a15_observation_launcher.py --live --certificate-exception '
 '--activation-file D:/1800/.local/stages/a15-cert-reuse-activation.json --activation-sha256 ' + ACTIVATION_SHA +
 ' --candidate-sha256 ' + CANDIDATE_SHA + ' --profile-fingerprint ' + activation['profile_fingerprint'])
assert command['command'] == expected_command
window_start, window_end = utc_ticks(activation['not_before']), utc_ticks(activation['expires_at'])
start, finish = utc_ticks(command['started_at']), utc_ticks(command['finished_at'])
assert window_end - window_start == 900 * 10000000
assert window_start <= start < finish < window_end
assert finish - start < 90 * 10000000
records = {path.name: read(path) for path in (LIVE / 'live-records').iterdir()}
assert len(records) == 10
observation = records['observation.json']
launcher, worker, occupancy = [records[name] for name in ('launcher-release.json', 'worker-release.json', 'occupancy.json')]
intent = records['launcher-intent.json']
assert intent['shell'] is False and intent['activation_sha256'] == ACTIVATION_SHA
assert intent['candidate_sha256'] == CANDIDATE_SHA and intent['run_id'] == activation['run_id']
argv = intent['argv']
assert argv[1] == '-B' and argv[2].endswith('headless_cert_exception_reuse_probe.py')
assert argv[3:] == ['--_launched', '--live', '--certificate-exception', '--activation-file', dispatch['activation_file'],
 '--activation-sha256', ACTIVATION_SHA, '--candidate-sha256', CANDIDATE_SHA, '--profile-fingerprint', activation['profile_fingerprint']]
expected_marker = {'task': 'A15', 'run_id': activation['run_id'], 'candidate_sha256': CANDIDATE_SHA,
 'profile_fingerprint': activation['profile_fingerprint'], 'activation_sha256': ACTIVATION_SHA,
 'certificate_exception': True, 'target': activation['target'], 'context_limit': 1, 'navigation_limit': 1,
 'login_submission_limit': 0, 'business_write_limit': 0}
for name in ('launcher-claimed.json', 'live-started.json', 'worker-claimed.json', 'occupancy-claimed.json'):
    assert records[name] == expected_marker
assert records['profile-binding.json']['fingerprint'] == activation['profile_fingerprint']
assert records['profile-binding.json']['existing_directory_count'] == 1
assert observation['outcome'] == 'ERROR' and observation['error']['codes'] == ['NETWORK_GUARD_STOPPED']
assert observation['observation_error'] == observation['error'] and observation['guard_failure'] is None
assert observation['successors'] == 'NOT_RUN'
assert observation['navigation_intents'] == 1 and observation['login_submissions'] == observation['business_writes'] == 0
events = observation['network_audit']
assert len(events) == 8 and all(event['method'] == 'GET' for event in events)
assert [utc_ticks(event['time']) for event in events] == sorted(utc_ticks(event['time']) for event in events)
first_denial = next(event for event in events if event['decision'] == 'BLOCK')
assert first_denial['category'] == 'ORIGIN_BLOCKED'
assert all(set(event) == {'category', 'decision', 'method', 'redirect_hop', 'source', 'time'} for event in events)
assert Counter(event['category'] for event in events) == {'NAVIGATION': 2, 'STATIC': 2, 'ORIGIN_BLOCKED': 1, 'STOPPED': 3}
assert {event['source'] for event in events if event['category'] == 'NAVIGATION'} == {'FETCH_REQUEST_STAGE', 'CONTEXT_FIRST_REQUEST'}
assert all(event['redirect_hop'] is False for event in events)
for key in ('guard_state_pre_shutdown', 'guard_state_at_serialization'):
    state = observation[key]
    assert state['stopped'] is True and state['terminal_stopped'] is True and state['pending_tasks'] == 0 and state['failure'] is None
assert observation['guard_state_pre_shutdown']['shutdown_started'] is False
assert observation['guard_state_at_serialization']['shutdown_started'] is True
release = observation['release']
for key in ('context_created', 'context_close_attempted', 'context_closed', 'runtime_stop_attempted', 'runtime_stopped'):
    assert release[key] is True
assert release['state'] == 'RELEASED' and release['errors'] == []
identities = []
filetime_epoch = 116444736000000000
for role, record, expected_exit in (('product', launcher, 2), ('worker', worker, 2), ('occupancy', occupancy, 0)):
    before, after = record['before'], record['after']
    assert before['pid'] == after['pid'] and before['created_filetime'] == after['created_filetime'] > 0
    assert before['exit_observed'] is False and before['exit_code'] is None and before['exited_filetime'] is None
    assert after['exit_observed'] is True and after['exit_code'] == expected_exit
    assert after['exited_filetime'] >= before['created_filetime']
    assert start <= before['created_filetime'] - filetime_epoch <= after['exited_filetime'] - filetime_epoch <= finish
    identities.append({'role': role, 'pid': after['pid'], 'created_filetime': before['created_filetime'],
     'exited_filetime': after['exited_filetime'], 'exit_code': after['exit_code'],
     'same_retained_creation_identity': True, 'OS_exit_observed': True,
     'OS_lifetime_100ns': after['exited_filetime'] - before['created_filetime']})
assert len({row['pid'] for row in identities}) == 3
for record in (launcher, worker):
    assert record['job_assigned'] is True and record['job_closed'] is True
    assert record['job_active_before_final_cleanup'] == 1 and record['job_active_final'] == 0
    assert record['errors'] == [] and record['state'] == 'RELEASED'
assert launcher['product_handle_closed'] is True and worker['worker_handle_closed'] is True and occupancy['handle_closed'] is True
assert launcher['clock'] == 'OWN_PROCESS_MONOTONIC'
assert launcher['duration_ms'] == 6531 and launcher['total_deadline_exceeded'] is False
assert launcher['duration_ms'] < launcher['limit_seconds'] * 1000 == 90000
assert worker['duration_ms'] == 6031 and worker['hard_deadline_exceeded'] is False
assert worker['duration_ms'] < worker['limit_seconds'] * 1000 == 75000
assert worker['hard_limit_seconds'] == launcher['product_limit_seconds'] == 85
assert occupancy['matching_processes'] == 0 and occupancy['timeout'] is False and occupancy['limit_seconds'] == 4
assert launcher['launcher_own_os_exit_identity'] == 'UNKNOWN_NOT_OBSERVABLE_FROM_OWN_RUNNING_PROCESS'
assert launcher['activation_sha256'] == ACTIVATION_SHA
stdout, stderr = (LIVE / 'launcher-stdout.txt').read_bytes(), (LIVE / 'launcher-stderr.txt').read_bytes()
assert len(stdout) == 135 and stderr == b''
assert json.loads(stdout) == {'mode': 'LIVE_FINISHED', 'release': 'RELEASED', 'product_exit_code': 2,
                             'errors': False, 'launcher_own_os_exit_identity': 'UNKNOWN'}
capture = read(LIVE / 'raw-source-capture.json')
assert capture['source_file_count'] == len(capture['source_files']) == 10
for item in capture['source_files']:
    raw = (ROOT / item['archive']).read_bytes()
    assert len(raw) == item['size'] and sha(raw) == item['sha256']
assert capture['stdout_capture_sha256'] == sha(stdout) and capture['stderr_capture_sha256'] == sha(stderr)
packaging = read(LIVE / 'report-packaging-event.json')
original_helper = (LIVE / 'seal_observation.py').read_bytes()
new_helper = (LIVE / 'seal_observation_utc6.py').read_bytes()
assert sha(original_helper) == packaging['original_helper_sha256'] == '8fe0808eec6e223d5dea23cb1a468fdcaf34ed3f0f81a40577a025d223d3bf14'
assert packaging['phase'] == 'REPORT_PACKAGING_ONLY_AFTER_COMPLETED_LIVE'
assert packaging['exit_code'] == 1 and packaging['live_invocations_remain'] == 1 and packaging['live_remaining'] == 0
assert packaging['product_or_live_or_offline_suite_reexecuted'] is False
assert packaging['reports_generated_before_error'] == packaging['source_live_records_copied_before_error'] == 0
ast.parse(original_helper)
ast.parse(new_helper)
helper_diff = ''.join(difflib.unified_diff(original_helper.decode('utf-8').splitlines(True),
 new_helper.decode('utf-8').splitlines(True), fromfile='frozen/seal_observation.py', tofile='frozen/seal_observation_utc6.py')).encode('utf-8')
with (OUT / 'report-helper-only.diff').open('xb') as stream:
    stream.write(helper_diff)
coordinator = Path('D:/1800/docs/evidence/coordinator/a15-live-result-preflight')
snapshots = []
for name in ('raw-preflight.json', 'review-intent.json'):
    raw = (coordinator / name).read_bytes()
    with (OUT / ('coordinator-' + name)).open('xb') as stream:
        stream.write(raw)
    snapshots.append({'source': 'docs/evidence/coordinator/a15-live-result-preflight/' + name, 'sha256': sha(raw)})
summary = {'task': 'A15', 'phase': 'FIXED_LIVE_STATIC_REVIEW', 'at': datetime.now(timezone.utc).isoformat(),
 'author_final': FINAL, 'prior_author_final': PRIOR, 'author_manifest_sha256': MANIFEST_SHA,
 'raw_members_including_manifest': 74, 'raw_members': verified,
 'old_prior_final_members_preserved': 31259, 'new_paths': additions, 'new_paths_count': 27,
 'candidate_members_unchanged': 22, 'original_independent_outputs_unchanged': True,
 'original_independent_manifest_sha256': sha(old_manifest_raw),
 'activation_sha256': ACTIVATION_SHA, 'independent_report_binding_sha256': INDEPENDENT_REPORT_SHA,
 'activation_fields_bound_to_authority': True,
 'time_checks': {'precision': 'EXACT_100NS_INTEGER_NO_RAW_TIMESTAMP_NORMALIZATION',
  'window_start_raw': activation['not_before'], 'window_end_raw': activation['expires_at'],
  'command_start_raw': command['started_at'], 'command_finish_raw': command['finished_at'],
  'window_duration_100ns': window_end - window_start, 'command_duration_100ns': finish - start,
  'command_inside_window': True, 'launcher_duration_ms_own_clock': launcher['duration_ms'],
  'product_worker_supervision_duration_ms_own_clock': worker['duration_ms'],
  'observation_duration_100ns': utc_ticks(observation['finished_at']) - utc_ticks(observation['started_at']),
  'no_cross_process_monotonic_comparison': True},
 'observed_live_scope': {'launcher_invocations': 1, 'contexts_recorded_created': 1, 'navigation_intents': 1,
  'login_submissions': 0, 'business_writes': 0, 'new_live_used': 1, 'new_live_remaining': 0},
 'first_policy_denial': first_denial, 'terminal_outcome': 'ERROR', 'error_codes': ['NETWORK_GUARD_STOPPED'],
 'guard_pending_tasks_at_serialization': 0, 'successors': 'NOT_RUN',
 'audit_event_count': 8, 'audit_categories': dict(Counter(event['category'] for event in events)),
 'audit_is_not_unique_request_count': True, 'navigation_events_are_dual_guard_observations': True,
 'blocked_domain_URL_resource_type': 'UNKNOWN_NOT_RECORDED', 'root_cause': 'UNKNOWN',
 'three_retained_child_identities': identities, 'owned_jobs_final_active_counts': [0, 0],
 'owned_jobs_before_final_cleanup_counts': [1, 1], 'recorded_context_and_runtime_closed': True,
 'launcher_own_OS_exit_identity': 'UNKNOWN_PRESERVED',
 'report_packaging_event': {'original_helper_sha256': sha(original_helper), 'fixed_helper_sha256': sha(new_helper),
  'raw_command_time_has_seven_fractional_digits': True, 'original_error_preserved': True,
  'report_only_diff_sha256': sha(helper_diff), 'no_live_rerun_in_fixed_records': True},
 'archived_source_record_hashes_verified': 10, 'actual_local_source_profile_or_processes_read': False,
 'source_capture_claim_not_independently_refreshed': True,
 'static_git_commands': git_calls, 'coordinator_snapshots': snapshots,
 'reviewer_suite_or_live_executions': 0, 'reviewer_product_imports': 0,
 'reviewer_browser_network_profile_native_api_actual_occupancy_actions': 0}
save('fixed-record-audit.json', summary)
print(json.dumps({'raw_members': 74, 'old_members_preserved': 31259, 'new_paths': 27,
 'activation_matches': True, 'command_duration_seconds': (finish - start) / 10000000,
 'fixed_outcome': 'ERROR_NETWORK_GUARD_STOPPED', 'child_exit_codes': [row['exit_code'] for row in identities],
 'jobs_active_final': [0, 0], 'live_review_runs': 0, 'helper_diff_bytes': len(helper_diff)}))
