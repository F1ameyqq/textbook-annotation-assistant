"""Coordinator checks frozen Git archives only; never calls the receiver."""
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile

os.environ['GIT_NO_LAZY_FETCH'] = '1'
ROOT = Path('D:/1800')
AUTHOR = '83f119fae8e84b30332ac50288b74049514c9b4e'
REVIEW = 'c4b7575841ee1bed1320eb6351b90e4dcc25f092'
PRODUCT = '04762d78eae18449d7fcf3c0de20aec23b1f6881'
PREFIX = 'docs/evidence/A08/review/'

def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT, stderr=subprocess.PIPE)

def raw(path):
    return git('cat-file', 'blob', REVIEW + ':' + path)

def read(name):
    return json.loads(raw(PREFIX + name))

def tree(commit):
    result = {}
    for row in git('ls-tree', '-rz', commit).split(b'\0'):
        if row:
            meta, path = row.split(b'\t', 1)
            result[path.decode()] = meta.decode()
    return result

old, current = tree(AUTHOR), tree(REVIEW)
assert all(current.get(p) == meta for p, meta in old.items())
manifest = read('review-raw-manifest.json')
entries = manifest['entries']
assert len(entries) == 69
assert set(current) - set(old) == {e['path'] for e in entries} | {PREFIX + 'review-raw-manifest.json'}
assert all(e['path'].startswith(PREFIX) or e['path'] == 'docs/tasks/A08-review-report.md' for e in entries)
total = 0
for entry in entries:
    data = raw(entry['path'])
    assert len(data) == entry['bytes']
    assert hashlib.sha256(data).hexdigest() == entry['sha256']
    assert current[entry['path']].split()[-1] == entry['git_blob']
    total += len(data)
assert total == manifest['entry_bytes']
provenance = read('provenance.json')
assert hashlib.sha256(raw(PREFIX + 'independent_review.py')).hexdigest() == provenance['driver_sha256']
assert provenance['product'] == PRODUCT and provenance['delivery'] == AUTHOR

registry = json.loads((ROOT / 'docs/tasks/A08-inputs.json').read_text(encoding='utf-8'))
package = Path(registry['local_readonly_input']).read_bytes()
assert hashlib.sha256(package).hexdigest() == registry['zip_sha256']
archive = zipfile.ZipFile(io.BytesIO(package))
batch = json.loads(archive.read('staging/batch.json'))
source_cases = {c['case_id']: c for c in batch['cases']}
observed = read('R0-original.json')
assert observed['status'] == 'RECEIVED_READONLY_HOLD'
assert observed['summary'] == {'answer_evidence_only': 3, 'assets': 3, 'cases': 4, 'hold_cases': 4, 'question_answer_candidates': 1}
assert observed['decision'] == 'HOLD' and not observed['business_acceptance']
assert not observed['q1_authorization_transfer_allowed']
assert not observed['external_objects']['complete_G_Check_plan_objects_loaded']
for case in observed['cases']:
    source = source_cases[case['case_id']]
    assert case['source_snapshot'] == source
    assert json.loads(archive.read(case['source_case_member'])) == source
    assert hashlib.sha256(archive.read(case['source_case_member'])).hexdigest() == case['source_case_sha256']
    assert case['decision'] == 'HOLD' and not case['platform_eligible'] and not case['business_acceptance']
    if case['case_id'] == 'q4-first-lesson':
        assert case['candidate_relation']['status'] == 'B_DECLARED_CANDIDATE_ONLY'
        assert not case['candidate_relation']['a_selected_relation_created']
    else:
        assert case['question_id'] is None and case['candidate_relation'] is None
        assert source['question_snapshot'] is None

assets = {a['asset_id']: a for a in batch['assets']}
ledger = read('coordinate-ledger.json')
assert ledger['assets'] == batch['assets']
for row in ledger['coordinates']:
    parts = row['path'].split('/')
    value = source_cases[parts[0]]
    for part in parts[1:]:
        value = value[int(part)] if isinstance(value, list) else value[part]
    assert value == row['bbox']
    asset = assets[row['asset_id']]
    assert row['asset_sha256'] == asset['sha256'] and row['dimensions'] == [asset['width'], asset['height']]
    x1, y1, x2, y2 = row['bbox']
    assert 0 <= x1 < x2 <= asset['width'] and 0 <= y1 < y2 <= asset['height']
assert len(ledger['coordinates']) == 120
assert assets['resource-173']['external_refs']['viewer_page'] is None

finite = read('finite-results.json')
assert finite['status'] == 'PASS_INDEPENDENT_FINITE_READONLY'
assert finite['original_calls'] == 1 and finite['negative_calls'] == 11
assert not finite['author_driver_executed'] and finite['additional_api_calls'] == 0
for run in finite['results']:
    label = run['case']
    result = read(label + '.json')
    assert run['status'] == 'PASS' and run['joined'] and not run['timed_out']
    assert not any(result['actions'].values())
    assert json.loads(raw(PREFIX + label + '.stdout.txt')) == result
    assert raw(PREFIX + label + '.stderr.txt') == b''
    if label != 'R0-original':
        assert run['exit_code'] == 2 and result['status'] == 'REJECTED'
        assert (result['layer'], result['code'], result['path']) == (run['actual_layer'], run['actual_code'], run['actual_path'])
        variant = raw(PREFIX + 'variants/' + label + '.zip')
        assert hashlib.sha256(variant).hexdigest() == run['package_sha256']
    else:
        assert run['exit_code'] == 0

release = read('process-release.json')
assert release['all_owned_children_joined'] and release['driver_run_phase_returning']
assert release['children'] == [{'pid': r['pid'], 'exit_code': r['exit_code'], 'joined': True} for r in finite['results']]
assert release['owned_services_started'] == 0 and release['other_processes_stopped'] == 0
pids = ','.join(str(row['pid']) for row in release['children'])
script = "$ids=@(" + pids + "); @(Get-Process -Id $ids -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,@{Name='StartUtc';Expression={$_.StartTime.ToUniversalTime().ToString('o')}}) | ConvertTo-Json -Compress"
proc = subprocess.run(['powershell', '-NoProfile', '-Command', script], capture_output=True, text=True)
alive = json.loads(proc.stdout) if proc.stdout.strip() else []
if isinstance(alive, dict):
    alive = [alive]
completed_runs = {r['pid']: r for r in finite['results']}
for row in alive:
    owned = completed_runs[row['Id']]
    finished = (datetime.datetime.fromisoformat(owned['started_at_utc']) + datetime.timedelta(seconds=owned['elapsed_seconds'])).astimezone(datetime.timezone.utc).replace(tzinfo=None)
    # A PID may be reused after its child exits but before the reviewer writes the report.
    assert datetime.datetime.strptime(row['StartUtc'][:19], '%Y-%m-%dT%H:%M:%S') > finished

result = {
    'task_id': 'A08', 'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'PASS_COORDINATOR_FIXED_ARCHIVE_CHECK', 'product_commit': PRODUCT,
    'author_delivery_commit': AUTHOR, 'review_delivery_commit': REVIEW,
    'raw_manifest_entries': len(entries), 'raw_manifest_bytes': total,
    'review_added_paths_including_manifest': len(current) - len(old), 'review_old_paths_preserved': len(old),
    'independent_driver_pre_run_hash_verified': True, 'input_sha256': registry['zip_sha256'],
    'four_source_snapshots_equal_original': True, 'coordinate_occurrences_checked': 120,
    'all_cases_hold': True, 'external_full_objects_loaded': False,
    'recorded_original_receives': 1, 'recorded_negative_receives': 11,
    'negative_archive_sha_and_report_bindings_verified': True,
    'released_children': len(release['children']), 'current_pid_reuse': alive,
    'coordinator_new_receiver_runs': 0, 'coordinator_new_business_runs': 0,
    'platform_actions': 0, 'pushes': 0, 'scope': 'Fixed R0-R7 readonly reception only; not content or simulation admission'
}
destination = ROOT / 'docs/evidence/coordinator/a08-acceptance-20261019/saved-review-check.json'
destination.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
print(json.dumps(result, ensure_ascii=False))
