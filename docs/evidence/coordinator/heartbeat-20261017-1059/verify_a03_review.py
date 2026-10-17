"""Coordinator audit of the frozen R5 review, positive and target binding; data-only residual check."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('D:/1800')
OUT = Path(__file__).resolve().parent
REVIEW = ROOT / 'docs/evidence/A03/review/P2-R5-registration-context'
MANIFEST = REVIEW / 'sha256-manifest.json'
REPORT = ROOT / 'docs/tasks/A03-P2-R5-registration-context-review-report.md'
TARGET = '323013c4f0dbae75368e56db60147a8057368d1f'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def load(path):
    return json.loads(path.read_bytes())

def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')

def audit_manifest():
    manifest = load(MANIFEST)
    assert sha(MANIFEST.read_bytes()) == 'bff7b99b110f8c104317357460a41b05de72ec73f997d3c6c7dd19f65e60f496'
    assert sha(REPORT.read_bytes()) == 'f4831a2f8274f3cad718b440b0bd647ccd726ba997dafb5e0089028d2fb5ab5f'
    assert len(manifest['files']) == 309
    assert load(REVIEW / 'input-index.json')['delivery'] == TARGET
    expected = {row['path'] for row in manifest['files']}
    actual = {p.relative_to(ROOT).as_posix() for p in REVIEW.rglob('*') if p.is_file() and p != MANIFEST}
    actual.add(REPORT.relative_to(ROOT).as_posix())
    assert expected == actual
    for row in manifest['files']:
        path = (ROOT / row['path']).resolve()
        assert path.is_relative_to(ROOT)
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
    return manifest

def audit_inputs():
    rows = load(REVIEW / 'input-index.json')['files']
    assert len(rows) == 225
    requests = [row['commit'] + ':' + row['path'] for row in rows]
    result = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT,
                            input=('\n'.join(requests) + '\n').encode(), capture_output=True, timeout=30)
    assert result.returncode == 0
    data = result.stdout
    offset = 0
    for row in rows:
        end = data.index(b'\n', offset)
        oid, kind, size = data[offset:end].split()
        offset = end + 1
        raw = data[offset:offset + int(size)]
        offset += int(size)
        assert data[offset:offset + 1] == b'\n'
        offset += 1
        assert kind == b'blob' and oid.decode() == row['raw_git_sha1']
        assert raw == (REVIEW / row['file']).read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    assert offset == len(data)
    return len(rows)

def run(name, script, expected_exit, extra=()):
    command = [sys.executable, '-X', 'utf8', '-B', str(script), *extra]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    env.pop('PYTHONPATH', None)
    start = time.monotonic()
    with (OUT / (name + '.stdout.log')).open('xb') as stdout, (OUT / (name + '.stderr.log')).open('xb') as stderr:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        write(OUT / (name + '.start.json'), {'argv': command, 'cwd': str(ROOT), 'pid': process.pid,
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'timeout_seconds': 30, 'PYTHONPATH': 'REMOVED', 'source_sha256': sha(script.read_bytes())})
        timed_out = False
        try:
            code = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait(timeout=5)
    record = {'argv': command, 'cwd': str(ROOT), 'pid': process.pid, 'exit_code': code,
              'expected_exit_code': expected_exit, 'elapsed_seconds': time.monotonic() - start,
              'timed_out': timed_out, 'alive': process.poll() is None}
    write(OUT / (name + '.completion.json'), record)
    assert not timed_out and code == expected_exit
    return record

manifest = audit_manifest()
inputs = audit_inputs()
archive = run('archive-verification', REVIEW / 'scripts/archive.py', 0)
entry = REVIEW / 'input/checkout/examples/a03/P2-R5-registration-context/run_case.py'
positive = run('positive-replay', entry, 0, ['registration-positive', '--readonly'])
target = run('target-replay', entry, 0, ['target-tuple-negative', '--readonly'])
pos = load(OUT / 'positive-replay.stdout.log')
neg = load(OUT / 'target-replay.stdout.log')
assert pos['actual'] == 'STATIC_ACCEPTED' and pos['full_entry_returned']
assert pos['inherited_tail_trace'] == ['MIXED_DAG','CONSUMER_DECLARATIONS_BOOK_SCOPE','ARTIFACT_HASH','FULL_R2_TAIL_RETURN']
assert pos['none_book_real_consumers'] == 0
assert neg['actual'] == 'FRAME_REGISTRATION_TARGET'
assert neg['error']['path'] == 'r4-static/target-tuple-negative/prefix.json/registration/target'
assert pos['package_calls'] == neg['package_calls'] == 1
# Independently check frozen data, without another Package call or any mutation.
prefix_path = REVIEW / 'input/checkout/examples/a03/P2-R5-registration-context/cases/artifact-resource-frame-mixed-cycle/repair-01/resources/0.json'
raw = prefix_path.read_bytes()
assert sha(raw) == '4d153e82f0a75d233bb77bb7028a2a3dc2bdbcd4f22bda6514a15d0be4450de0'
prefix = json.loads(raw)
previous = prefix['predecessor']['hash']
mismatches = []
for frame in prefix['frames']:
    event = frame['event']
    assert event['previous_hash'] == previous
    canonical = json.dumps({k:v for k,v in event.items() if k != 'event_hash'}, ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    assert sha(canonical) == event['event_hash']
    if event['event'] == 'READONLY_ABSENCE_STARTED':
        expected = {'sequence': event['sequence'] - 1, 'hash': previous}
        if event['payload']['initial_event_head'] != expected:
            mismatches.append({'event': event['event'], 'sequence':event['sequence'], 'declared':event['payload']['initial_event_head'], 'expected':expected})
    previous = event['event_hash']
assert len(mismatches) == 1 and mismatches[0]['sequence'] == 8
assert mismatches[0]['expected']['hash'] == '28ef8b468d67a04e9ba75fe3e41a45fb96f280deb95ddcef4cdc2097d6c195f9'
release = load(REVIEW / 'process-release.json')
assert len(release['owned_runs']) == 9 and all(x['exit_code']==0 and not x['timed_out'] and not x['alive_after_wait'] for x in release['owned_runs'])
assert release['remaining_owned_background_workers'] == release['native_sessions'] == 0
audit_manifest()
checks = {'task_id':'A03','target_commit':TARGET,'decision':'REWORK_CONTROL_INPUT_PROOF',
 'accepted_scope':'Six specified R5 static scenarios only; registration context/target and formal-ref/global-resource regressions',
 'review_manifest_entries':len(manifest['files']),'review_files_including_manifest':len(manifest['files'])+1,
 'raw_git_inputs_verified':inputs,'review_archive_unchanged_after_reproduction':True,
 'report_sha256':sha(REPORT.read_bytes()),'manifest_sha256':sha(MANIFEST.read_bytes()),
 'archive_command':archive,'positive_command':positive,'target_command':target,'positive_result':pos,'target_result':neg,
 'mixed_control_data_only':{'prefix_sha256':sha(raw),'event_hash_chain_correct':True,'internal_head_mismatches':mismatches,'Package_calls':0},
 'independent_review_owned_runs':9,'independent_review_release_verified':True,
 'coordinator_Package_calls':2,'full_suite_rerun':False,'product_native_DB_platform_model_calls':0,
 'I01_released':False,'integrated':False,'remote_push':False,'oracle_adopted':False,
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
 'release_basis':'Completed independent-review turn plus frozen parent wait/return records; own three child processes synchronously exited; no OS/profile scan.'}
write(OUT / 'A03-R5-review-check.json', checks)
print(json.dumps({k:checks[k] for k in ['decision','accepted_scope','review_manifest_entries','raw_git_inputs_verified','coordinator_Package_calls','full_suite_rerun']}))
