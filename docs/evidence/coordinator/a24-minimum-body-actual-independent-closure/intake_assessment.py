"""Frozen metadata and actual-record consistency only; no product/test/native imports."""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
ACTUAL = ROOT / 'docs/evidence/A24/minimum-gate-current-body-actual'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def load(name):
    return json.loads((ACTUAL / name).read_bytes())


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, indent=2) + '\n').encode())


def verify(rows, count, git=False):
    assert len(rows) == len({r['path'] for r in rows}) == count
    for row in rows:
        path = (ROOT / row['path']).resolve()
        assert ROOT in path.parents
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
        if git:
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['blob']


raw = Path('D:/1800/docs/evidence/coordinator/a24-minimum-body-actual-delivery/input-raw-manifest.json').read_bytes()
assert sha(raw) == '6812bb2a2c5ea2dc3c70d866b2693a1f8eef33bcec379bee16d601daf75e1e73'
with (OUT / 'input-raw-manifest.json').open('xb') as stream:
    stream.write(raw)
manifest = json.loads(raw)
verify(manifest['members'], 313, True)
assert len(manifest['private_references']) == 27
for row in manifest['private_references']:
    path = Path(row['snapshot_path']).resolve()
    assert ROOT / '.local/fixed-private' in path.parents
    data = path.read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
final_raw = (ACTUAL / 'delivery-final-manifest.json').read_bytes()
assert sha(final_raw) == 'f81a1eade0a0487f3b8795d07402d3b526118915c3c91f8842a403bd20836c12'
verify(json.loads(final_raw)['members'], 28)
with (OUT / 'actual-input-manifest.json').open('xb') as stream:
    stream.write(final_raw)
task = Path('D:/1800/docs/tasks/A24-minimum-body-fixed-actual-independent-review.md').read_bytes()
assert sha(task) == '6978777c4c588ca9d02a0b0963bfa17206163e35412c58b94032ab5251822989'
with (OUT / 'fixed-review-task.md').open('xb') as stream:
    stream.write(task)
candidate_raw = (ROOT / 'docs/evidence/A24/first-save-minimum-gate/candidate-manifest.json').read_bytes()
assert sha(candidate_raw) == 'e4ca6b3b6f90fffbf9a67866d977a70db08d99a6496c307ce113a839f475b0cf'
verify(json.loads(candidate_raw)['dependencies'], 136)
write('intake-result.json', {'schema': 'A24MinimumBodyIndependentStaticIntake/v1', 'result': 'PASS_RAW_INTAKE_ONLY',
    'raw_members': 313, 'final_delivery_members': 28, 'candidate_dependencies': 136,
    'private_snapshots': 27, 'all_raw_size_sha256_git_blob_checks': True,
    'task_sha256': sha(task), 'final_actual_manifest_sha256': sha(final_raw),
    'active_author_or_original_private_paths_read': False, 'product_test_or_actual_runs': 0,
    'old_actual_manifest': 'Preserved historical member, not sole final intake authority'})


def read_ref(ref):
    paths = [ROOT / r['path'] for r in manifest['members'] if r['bytes'] == ref['bytes'] and r['sha256'] == ref['sha256']]
    paths += [Path(r['snapshot_path']) for r in manifest['private_references'] if r['bytes'] == ref['bytes'] and r['sha256'] == ref['sha256']]
    assert paths, ref['sha256']
    data = paths[0].read_bytes()
    assert len(data) == ref['bytes'] and sha(data) == ref['sha256']
    return data


authority = load('inputs/authority.json')
decision = load('inputs/decision.json')
acceptance = load('inputs/prewrite-acceptance-binding.json')
worker = load('raw/run/worker-result.json')
actual = load('actual-result.json')
assert sha((ACTUAL / 'inputs/authority.json').read_bytes()) == '960f729175f836755ab2af81d6a36baa4d8357ae6a61df495842f3494fc54d81'
assert authority['role'] == 'AUTHOR_SAVE' and authority['refs']['schema_profile'] is authority['refs']['author_release'] is None
plan = json.loads(read_ref(authority['refs']['plan']))
assert sha(canonical(plan)) == authority['scope_sha256'] == '87324f21901723a4282afc9d06bea243b5bdba72ac25ea7f0c1eea3c018493de'
assert plan['body_admission'] == 'CURRENT_SCHEMA_UNBOUND' and authority['old_budgets_restored'] is False
for key, ref in authority['refs'].items():
    if ref is not None:
        read_ref(ref)
    if key not in ('decision', 'independent_report'):
        value = None if ref is None else ref['sha256']
        assert decision[key + '_sha256'] == acceptance[key + '_sha256'] == value
for key in ('task', 'mode', 'run_id', 'role', 'coordinator', 'executor', 'scope_sha256', 'not_before', 'expires_at'):
    assert type(authority[key]) is type(decision[key]) is type(acceptance[key])
    assert authority[key] == decision[key] == acceptance[key]
assert decision['effective_current_branch'] == acceptance['effective_current_branch']
assert not decision['conditional_save_authorized'] and not decision['independent_reopen_authorized']
crops = json.loads(read_ref(authority['refs']['crop_manifest']))
for crop in crops['regions']:
    read_ref({'bytes': crop['jpeg_bytes'], 'sha256': crop['jpeg_sha256']})
request = json.loads(read_ref(authority['refs']['request']))
assert request['approval'] is request['body_schema_profile'] is None and not request['current_write_eligible']
start, end = (datetime.fromisoformat(authority[k]) for k in ('not_before', 'expires_at'))
assert end - start == timedelta(seconds=900)
held = []
for stage, pid, exit_code in [('launcher', 30632, 2), ('product', 64920, 2), ('worker', 60660, 2), ('occupancy', 54456, 0)]:
    record = load('raw/run/' + stage + '-held-release.json')
    before, after = record['before'], record['after']
    assert before['pid'] == after['pid'] == pid and before['created_filetime'] == after['created_filetime']
    assert type(before['created_filetime']) is int and before['created_filetime'] > 0
    assert before['exit_observed'] is False and after['exit_observed'] is True and after['exit_code'] == exit_code
    assert record['creation_identity_match'] and record['handle_closed'] and record['job_closed']
    assert record['job_active_final'] == 0 and record['released'] and record['job_assigned']
    assert record['stdin_token_sent_after_job_assignment']
    assert record['authority_sha256'] == actual['authority_sha256']
    created = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=before['created_filetime'] // 10)
    exited = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=after['exited_filetime'] // 10)
    assert start <= created <= exited <= end
    claim = load('raw/run/' + stage + '-claimed.json')
    assert claim['authority_sha256'] == actual['authority_sha256'] and claim['run_id'] == authority['run_id']
    streams = {}
    for name in ('stdout', 'stderr'):
        ref = record['controlled_raw_output_refs'][name]
        content = read_ref(ref)
        assert len(content) == record[name + '_bytes'] and sha(content) == record[name + '_sha256']
        streams[name] = {'bytes': len(content), 'sha256': sha(content), 'raw_snapshot_verified': True}
    if 'child_projection' in record:
        assert json.loads(read_ref(record['controlled_raw_output_refs']['stdout'])) == record['child_projection']
    held.append({'stage': stage, 'pid': pid, 'creation_identity_match': True,
        'created_filetime': before['created_filetime'], 'exited_filetime': after['exited_filetime'],
        'held_exit_observed': True, 'exit': exit_code, 'job_empty_closed': True, 'handle_closed': True,
        'stage_success': record['stage_success'], 'errors': record['errors'], 'streams': streams})
outer = load('raw/outer/outer-result.json')
assert outer['held_launcher'] == load('raw/run/launcher-held-release.json')
outer_claim = load('raw/outer/outer-claimed.json')
assert outer_claim['wrapper_sha256'] == sha((ACTUAL / 'raw/outer/held_launcher_once.py').read_bytes())
assert outer_claim['attempt_limit'] == 1 and outer_claim['authority_sha256'] == actual['authority_sha256']
private_outputs = load('private-raw-manifest.json')
assert len(private_outputs['members']) == 10
for ref in private_outputs['members']:
    read_ref(ref)
stderr_ref = load('raw/run/worker-held-release.json')['controlled_raw_output_refs']['stderr']
stderr = read_ref(stderr_ref)
assert len(stderr) == 1027 and sha(stderr) == '4705a16315a41a311c7de3faa45dfd96cde2afe17c32d5df2fd9549b5301deb4'
text = stderr.decode('utf-8')
message = 'TypeError: route() takes 2 positional arguments but 3 were given'
assert message in text and 'usense.py' in text and 'tracked' in text
raw_frames = re.findall(r'File "([^"]+)", line (\d+), in ([^\r\n]+)', text)
frames = []
for path, line, function in raw_frames:
    normalized = path.replace('\\', '/')
    allowed = ('site-packages/playwright/_impl/_browser_context.py', 'site-packages/playwright/_impl/_helper.py')
    suffix = next((p for p in allowed if normalized.endswith(p)), None)
    if normalized.endswith('/usense.py'):
        suffix = 'usense.py'
    if suffix:
        frames.append({'file_suffix': suffix, 'line': int(line), 'function': function.strip()})
assert {'file_suffix': 'usense.py', 'line': 121, 'function': 'tracked'} in frames
assert worker['first_error'] == actual['first_error'] == {'code': 'OWNER_ERROR', 'type': 'TimeoutError'}
assert worker['bootstrap_steps'] == actual['bootstrap_steps']
assert worker['navigation'] == actual['navigation']
nav = worker['navigation']
assert nav['goto']['elapsed_ms'] == 45031.0 and nav['goto']['state'] == 'FAILED'
assert nav['goto']['http_status'] is None and not nav['response_received']['observed']
assert not nav['loading_failed']['observed'] and not nav['domcontentloaded_observed']
assert worker['release'] == actual['worker_release'] and worker['release']['context_created']
assert not worker['release']['context_closed'] and not worker['release']['released'] and worker['release']['runtime_stopped']
assert all(actual[k] == 'NOT_RUN' for k in ('session_completion', 'viewer_admission', 'book', 'directory', 'frames',
    'natural_export', 'signature', 'upload', 'commit', 'refresh', 'reopen'))
result = {'schema': 'A24MinimumBodyIndependentStaticAssessment/v1',
    'result': 'CONSISTENT_FIXED_GOTO_TIMEOUT_CALLBACK_TYPEERROR_AND_PARTIAL_RELEASE_ONLY',
    'method': 'Frozen byte/hash/JSON/FILETIME consistency only; no product tests or real observations',
    'authority': {'sha256': actual['authority_sha256'], 'role': 'AUTHOR_SAVE', 'schema_profile': None,
        'body_admission': 'CURRENT_SCHEMA_UNBOUND', 'scope_sha256': authority['scope_sha256'],
        'window_Asia_Shanghai': [start.astimezone(timezone(timedelta(hours=8))).isoformat(), end.astimezone(timezone(timedelta(hours=8))).isoformat()],
        'main_references_candidate_request_six_crops_decision_acceptance': 'SNAPSHOT_SIZE_SHA_MATCH'},
    'worker_first_error': worker['first_error'], 'bootstrap_steps': worker['bootstrap_steps'], 'navigation': nav,
    'stderr_safe_facts': {'exception': 'TypeError', 'signature_message': message.split(': ', 1)[1],
        'frames': frames, 'bytes': 1027, 'sha256': sha(stderr), 'raw_exported': False,
        'causal_chain_to_goto_timeout_or_context_close': 'NOT_FULLY_PROVEN', 'historical_missing_stderr_reconstructed': False},
    'held_records': held, 'all_four_stage_streams_verified': True, 'outer_raw_stream_refs_verified': 2,
    'worker_release': worker['release'], 'full_release': 'UNPROVEN_CONTEXT_CLOSE_FALSE',
    'outer_supervisor_own_OS_exit': 'NOT_SELF_CERTIFIED',
    'tool_exit1': 'Author actual-result transcription; raw tool result not supplied',
    'held_launcher_exit2': 'Independent frozen held identity record',
    'business_GETs_and_effects': 'NOT_RUN', 'body_schema_current_identity_savepage_completeness': 'UNPROVEN_NO_NEW_FACTS',
    'profile_or_lock_changed_false_meaning': load('metadata-limitations.json')['meaning'],
    'persistent_browser_state_unchanged': 'NOT_INSPECTED_NOT_CLAIMED',
    'product_tests_model_native_browser_profile_network_reviewer_runs': 0}
write('evidence-assessment.json', result)
print(json.dumps({'result': result['result'], 'raw_inputs': 313, 'private_refs': 27,
    'held_identity_Job_handle_records': 4, 'worker_stderr_original_verified': True,
    'full_release': result['full_release'], 'actual_save': 'NOT_RUN'}))
