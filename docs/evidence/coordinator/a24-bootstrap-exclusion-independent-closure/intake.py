"""Frozen denial/evidence delta intake; no product imports."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
DELIVERY = ROOT / 'docs/evidence/A24/bootstrap-exclusion-minimum'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(rows, count, git=False):
    assert len(rows) == len({r['path'] for r in rows}) == count
    for row in rows:
        target = (ROOT / row['path']).resolve()
        assert ROOT in target.parents
        raw = target.read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
        if git:
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['blob']


raw = Path('D:/1800/docs/evidence/coordinator/a24-bootstrap-exclusion-minimum-delivery/input-raw-manifest.json').read_bytes()
assert sha(raw) == 'b8b76362839d1d0ab688830044b165ef19c6979138d0a96a56dc4e102016c490'
with (OUT / 'input-raw-manifest.json').open('xb') as stream:
    stream.write(raw)
manifest = json.loads(raw)
verify(manifest['members'], 308, True)
assert len(manifest['private_references']) == 31
for row in manifest['private_references']:
    path = Path(row['snapshot_path']).resolve()
    assert ROOT / '.local' in path.parents
    content = path.read_bytes()
    assert len(content) == row['bytes'] and sha(content) == row['sha256']
candidate = (DELIVERY / 'candidate-manifest.json').read_bytes()
delivery = (DELIVERY / 'delivery-final-manifest.json').read_bytes()
assert sha(candidate) == 'a949fb89eba82b4b1e225764b1e07c1022e3052fa242e9c81635f4031af1dc62'
assert sha(delivery) == 'f384634367966762aba93a051aa2e4a2f3aa2b8d4cf965a2f14e755a164f00d9'
verify(json.loads(candidate)['dependencies'], 151)
verify(json.loads(delivery)['members'], 307)
task = Path('D:/1800/docs/tasks/A24-bootstrap-exclusion-fixed-independent-review.md').read_bytes()
assert sha(task) == '9971c900c6dd7bb9f9a6ca7e2f250c1cce24f55d46176c03457e75e57e843109'
with (OUT / 'fixed-review-task.md').open('xb') as stream:
    stream.write(task)
result = {'schema': 'A24ExclusionIndependentIntake/v1', 'result': 'PASS_RAW_INTAKE_ONLY',
    'raw_inputs': 308, 'candidate_dependencies': 151, 'delivery_members': 307, 'private_snapshots': 31,
    'all_raw_size_sha256_git_blob_checks': True, 'active_author_or_original_private_paths_read': False,
    'task_sha256': sha(task), 'product_or_tests_before_intake': 0,
    'source_inspection_no_match': {'chunk': '735f54', 'exit': 1,
        'meaning': 'diagnostic definition not in probe; source is imported unchanged from policy.py; earlier policy source read succeeded',
        'product_or_control_failure': False}}
with (OUT / 'intake-result.json').open('xb') as stream:
    stream.write((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result))
