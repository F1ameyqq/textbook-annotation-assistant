"""Static frozen callback-body actual intake and finite record assessment."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
ACTUAL = ROOT / 'docs/evidence/A24/callback-current-body-actual'


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


raw = Path('D:/1800/docs/evidence/coordinator/a24-callback-body-actual-delivery/input-raw-manifest.json').read_bytes()
assert sha(raw) == 'ea5d849d326feb360649f4146933c39e4d6d378f28531b7faaa4d1192f523e4e'
with (OUT / 'input-raw-manifest.json').open('xb') as stream:
    stream.write(raw)
manifest = json.loads(raw)
verify(manifest['members'], 321, True)
assert len(manifest['private_references']) == 31
for row in manifest['private_references']:
    path = Path(row['snapshot_path']).resolve()
    assert ROOT / '.local/fixed-private' in path.parents
    data = path.read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
final_raw = (ACTUAL / 'delivery-final-manifest.json').read_bytes()
assert sha(final_raw) == 'b9246689ceee971f4b55a37f55a1851513f50922613b668c5391abf699836e97'
verify(json.loads(final_raw)['members'], 26)
with (OUT / 'actual-input-manifest.json').open('xb') as stream:
    stream.write(final_raw)
candidate = (ROOT / 'docs/evidence/A24/route-callback-minimum/candidate-manifest.json').read_bytes()
assert sha(candidate) == '79c4453822efc6e9b856d5859b6711157998291efe62d6f3d6aa15d0244f3574'
verify(json.loads(candidate)['dependencies'], 144)
task = Path('D:/1800/docs/tasks/A24-callback-body-fixed-actual-independent-review.md').read_bytes()
assert sha(task) == '198ecdcd8042b438eba4dfeeb1cc6dc98a4826c4392748c902d609d563e05601'
with (OUT / 'fixed-review-task.md').open('xb') as stream:
    stream.write(task)
write('intake-result.json', {'schema': 'A24CallbackBodyIndependentStaticIntake/v1', 'result': 'PASS_RAW_INTAKE_ONLY',
    'raw_members': 321, 'candidate_dependencies': 144, 'final_actual_members': 26, 'private_snapshots': 31,
    'all_raw_size_sha256_git_blob_checks': True, 'active_author_or_original_private_paths_read': False,
    'product_test_model_real_resource_runs': 0,
    'reviewer_metadata_error': {'chunk': 'f61112', 'exit': 1,
        'error': 'Read helper requested absent metadata-limitations.json; actual-result explicitly retains browser_profile_effects NOT_INSPECTED',
        'prior_result_read_succeeded': True, 'product_or_test_action': False}})


def read_ref(ref):
    paths = [ROOT / r['path'] for r in manifest['members'] if r['bytes'] == ref['bytes'] and r['sha256'] == ref['sha256']]
    paths += [Path(r['snapshot_path']) for r in manifest['private_references'] if r['bytes'] == ref['bytes'] and r['sha256'] == ref['sha256']]
    assert paths, ref['sha256']
    raw = paths[0].read_bytes()
    assert len(raw) == ref['bytes'] and sha(raw) == ref['sha256']
    return raw


authority, decision, acceptance = (load('inputs/' + name + '.json') for name in ('authority', 'decision', 'prewrite-acceptance-binding'))
worker, actual = load('raw/run/worker-result.json'), load('actual-result.json')
assert sha((ACTUAL / 'inputs/authority.json').read_bytes()) == '4148e2067353c538a686c9923ac01ca86f08093180fe58165b09b3154948e5f9'
assert authority['role'] == 'AUTHOR_SAVE' and authority['refs']['schema_profile'] is authority['refs']['author_release'] is None
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
plan = json.loads(read_ref(authority['refs']['plan']))
assert sha(canonical(plan)) == authority['scope_sha256'] == '87324f21901723a4282afc9d06bea243b5bdba72ac25ea7f0c1eea3c018493de'
assert plan['body_admission'] == 'CURRENT_SCHEMA_UNBOUND' and authority['old_budgets_restored'] is False
crops = json.loads(read_ref(authority['refs']['crop_manifest']))
for crop in crops['regions']:
    read_ref({'bytes': crop['jpeg_bytes'], 'sha256': crop['jpeg_sha256']})
start, end = (datetime.fromisoformat(authority[k]) for k in ('not_before', 'expires_at'))
assert end - start == timedelta(seconds=900)
held = []
for stage, pid, exit_code in [('launcher', 24748, 2), ('product', 54084, 2), ('worker', 60992, 2), ('occupancy', 54172, 0)]:
    record = load('raw/run/' + stage + '-held-release.json')
    before, after = record['before'], record['after']
    assert before['pid'] == after['pid'] == pid and before['created_filetime'] == after['created_filetime']
    assert type(before['created_filetime']) is int and before['created_filetime'] > 0
    assert not before['exit_observed'] and after['exit_observed'] and after['exit_code'] == exit_code
    assert record['creation_identity_match'] and record['handle_closed'] and record['job_closed']
    assert record['job_active_final'] == 0 and record['released'] and record['job_assigned']
    assert record['stdin_token_sent_after_job_assignment'] and record['authority_sha256'] == actual['authority_sha256']
    created = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=before['created_filetime'] // 10)
    exited = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=after['exited_filetime'] // 10)
    assert start <= created <= exited <= end
    claim = load('raw/run/' + stage + '-claimed.json')
    assert claim['authority_sha256'] == actual['authority_sha256'] and claim['run_id'] == authority['run_id']
    streams = {}
    for label in ('stdout', 'stderr'):
        ref = record['controlled_raw_output_refs'][label]
        content = read_ref(ref)
        assert len(content) == record[label + '_bytes'] and sha(content) == record[label + '_sha256']
        if label == 'stderr':
            assert content == b''
        streams[label] = {'bytes': len(content), 'sha256': sha(content), 'raw_snapshot_verified': True}
    assert json.loads(read_ref(record['controlled_raw_output_refs']['stdout'])) == record['child_projection'] if 'child_projection' in record else True
    held.append({'stage': stage, 'pid': pid, 'created_filetime': before['created_filetime'],
        'exited_filetime': after['exited_filetime'], 'creation_identity_match': True, 'exit': exit_code,
        'exit_observed': True, 'job_empty_closed': True, 'handle_closed': True,
        'stage_success': record['stage_success'], 'errors': record['errors'], 'streams': streams})
assert load('raw/outer/outer-result.json')['held_launcher'] == load('raw/run/launcher-held-release.json')
outer_claim = load('raw/outer/outer-claimed.json')
assert outer_claim['attempt_limit'] == 1 and outer_claim['dependencies_verified'] == 144
assert outer_claim['wrapper_sha256'] == sha((ACTUAL / 'raw/outer/held_launcher_once.py').read_bytes())
outputs = load('private-raw-manifest.json')['members']
assert len(outputs) == 10
for ref in outputs:
    read_ref(ref)
nav = worker['navigation']
assert nav == actual['navigation'] and worker['bootstrap_steps'] == actual['bootstrap_steps']
assert nav['goto']['state'] == 'DONE' and nav['goto']['http_status'] == 200 and nav['goto']['response_returned'] is True
assert nav['goto']['elapsed_ms'] == nav['domcontentloaded_elapsed_ms'] == 7094.0
assert nav['domcontentloaded_observed'] is True and nav['response_received']['elapsed_ms'] == 6922.0
assert nav['response_received']['http_status'] == 200 and nav['association'] == 'ORIGINAL_MAIN_DOCUMENT_NETWORK_ID'
assert worker['first_error'] == actual['first_error'] == {'code': 'OWNER_ERROR', 'type': 'OTHER'}
release = worker['release']
assert release == actual['worker_release'] and release['released'] and release['context_closed'] and release['runtime_stopped']
assert release['callback_pending'] == 0 and release['errors'] == []
assert release['guard_failure'] == actual['guard_first_failure'] == {'codes': ['ORIGIN_BLOCKED'], 'exception_type': 'Stop'}
assert actual['browser_profile_effects'] == 'NOT_INSPECTED'
assert all(actual[k] == 'NOT_RUN' for k in ('viewer_admission', 'book', 'directory', 'frames', 'natural_export',
    'signature', 'upload', 'commit', 'refresh', 'reopen'))
result = {'schema': 'A24CallbackBodyIndependentStaticAssessment/v1',
    'result': 'CONSISTENT_FIXED_HTTP200_DCL_ORIGIN_BLOCKED_FAILURE_AND_OWN_RELEASE_RECORDS',
    'method': 'Frozen file/hash/JSON/FILETIME consistency only; no product/test/native/library execution',
    'authority': {'sha256': actual['authority_sha256'], 'run_id': authority['run_id'], 'role': 'AUTHOR_SAVE',
        'schema_profile': None, 'body_admission': 'CURRENT_SCHEMA_UNBOUND', 'scope_sha256': authority['scope_sha256'],
        'window_Asia_Shanghai': [start.astimezone(timezone(timedelta(hours=8))).isoformat(), end.astimezone(timezone(timedelta(hours=8))).isoformat()],
        'main_refs_candidate_plan_request_decision_acceptance_crops': 'MATCH'},
    'worker_first_error': worker['first_error'], 'guard_first_failure': release['guard_failure'],
    'bootstrap_steps': worker['bootstrap_steps'], 'navigation': nav,
    'blocked_origin_path_kind_purpose_and_causal_chain': 'UNKNOWN_NOT_RETAINED',
    'authentication_viewer_admission': 'UNPROVEN', 'worker_release': release, 'held_records': held,
    'four_stage_stderr_empty_originals_verified': True, 'current_output_refs_verified': 10,
    'outer_supervisor_own_OS_identity': 'NOT_SELF_CERTIFIED',
    'outer_tool_exit1': 'AUTHOR_TRANSCRIPTION_RAW_TOOL_RESULT_NOT_SUPPLIED',
    'held_launcher_exit2': 'FROZEN_HELD_IDENTITY_RECORD',
    'body_schema_newness_legal_append_savepage': 'UNPROVEN_NO_BUSINESS_READS',
    'manual_profile_or_claim_mutation': 'RECORDED_FALSE; browser persistent effects NOT_INSPECTED',
    'historical_timeout_root_cause_fixed': False, 'reviewer_real_activity': 0}
write('evidence-assessment.json', result)
print(json.dumps({'result': result['result'], 'inputs': 321, 'private_snapshots': 31,
    'held_identity_Job_handle_records': 4, 'context_closed': True, 'runtime_stopped': True,
    'callback_pending': 0, 'blocked_source_and_cause': 'UNKNOWN', 'actual_save': 'NOT_RUN'}))
