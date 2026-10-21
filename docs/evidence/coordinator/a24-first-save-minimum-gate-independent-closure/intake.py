"""Frozen minimum-delta intake; no product imports or active private sources."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
DELIVERY = ROOT / 'docs/evidence/A24/first-save-minimum-gate'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(rows, count, git=False):
    assert len(rows) == len({r['path'] for r in rows}) == count
    for row in rows:
        path = (ROOT / row['path']).resolve()
        assert ROOT in path.parents
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
        if git:
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['blob']


raw = Path('D:/1800/docs/evidence/coordinator/a24-first-save-minimum-gate-delivery/input-raw-manifest.json').read_bytes()
assert sha(raw) == '4fe96dd755f734fca61fe04f8ab93fd50879b62f038b10a00bedc89985a3d6bd'
with (OUT / 'input-raw-manifest.json').open('xb') as stream:
    stream.write(raw)
manifest = json.loads(raw)
verify(manifest['members'], 284, True)
assert len(manifest['private_references']) == 17
for row in manifest['private_references']:
    path = Path(row['snapshot_path']).resolve()
    assert ROOT / '.local/fixed-external' in path.parents
    data = path.read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
candidate = (DELIVERY / 'candidate-manifest.json').read_bytes()
delivery = (DELIVERY / 'delivery-final-manifest.json').read_bytes()
assert sha(candidate) == 'e4ca6b3b6f90fffbf9a67866d977a70db08d99a6496c307ce113a839f475b0cf'
assert sha(delivery) == 'a56c41e3c59c20d66d348ff9fd7959b556dd2b6089e15f2a7f46f34a6043ea14'
verify(json.loads(candidate)['dependencies'], 136)
verify(json.loads(delivery)['members'], 283)
task = Path('D:/1800/docs/tasks/A24-first-save-minimum-gate-fixed-independent-review.md').read_bytes()
assert sha(task) == '9052fe9c1915e1f49c9401b043870d4f18fad0ec98869e3dc232bc6697783346'
with (OUT / 'fixed-review-task.md').open('xb') as stream:
    stream.write(task)
result = {'schema': 'A24MinimumGateIndependentIntake/v1', 'result': 'PASS_RAW_INTAKE_ONLY',
    'raw_members': 284, 'candidate_dependencies': 136, 'delivery_members': 283, 'private_snapshots': 17,
    'all_raw_size_sha256_git_blob_checks': True, 'active_author_or_original_private_paths_read': False,
    'task_sha256': sha(task), 'input_manifest_sha256': sha(raw), 'product_or_test_runs_before_intake': 0,
    'root_historical_diff': 'FIXED_COORDINATOR_EVIDENCE_NOT_REPEATED'}
with (OUT / 'intake-result.json').open('xb') as stream:
    stream.write((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result))
