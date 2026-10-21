"""Verify frozen inputs and exact installed source bytes before helper imports."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
DELIVERY = ROOT / 'docs/evidence/A24/route-callback-minimum'


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


raw = Path('D:/1800/docs/evidence/coordinator/a24-route-callback-minimum-delivery/input-raw-manifest.json').read_bytes()
assert sha(raw) == '85b3c11b5c6c4877e19ea0c6e83761abeb9a2dcfd4d8510069e53c4587ac329a'
with (OUT / 'input-raw-manifest.json').open('xb') as handle:
    handle.write(raw)
manifest = json.loads(raw)
verify(manifest['members'], 294, True)
assert len(manifest['private_references']) == 21
for row in manifest['private_references']:
    snapshot = Path(row['snapshot_path']).resolve()
    assert ROOT / '.local/fixed-external' in snapshot.parents
    data = snapshot.read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
candidate = (DELIVERY / 'candidate-manifest.json').read_bytes()
delivery = (DELIVERY / 'delivery-final-manifest.json').read_bytes()
assert sha(candidate) == '79c4453822efc6e9b856d5859b6711157998291efe62d6f3d6aa15d0244f3574'
assert sha(delivery) == '16999289344f82b973b80e10f896af9ac3737f23929afdea000c34c8bcc77725'
verify(json.loads(candidate)['dependencies'], 144)
verify(json.loads(delivery)['members'], 293)
provenance = json.loads((DELIVERY / 'library-provenance.json').read_bytes())
assert Path(sys.executable).resolve() == Path(provenance['python_executable']).resolve()
assert sys.version.split()[0] == '3.9.13' and importlib.metadata.version('playwright') == '1.58.0'
libraries = []
for row in provenance['sources']:
    library_raw = Path(row['path']).read_bytes()
    assert len(library_raw) == row['bytes'] and sha(library_raw) == row['sha256']
    snapshot = next(r for r in manifest['private_references'] if r['source_path'] == row['path'])
    assert Path(snapshot['snapshot_path']).read_bytes() == library_raw
    libraries.append({'installed_path': row['path'], 'snapshot_path': snapshot['snapshot_path'],
        'declared_private_copy_path': row['private_fixed_copy'], 'bytes': len(library_raw), 'sha256': sha(library_raw)})
task = Path('D:/1800/docs/tasks/A24-route-callback-fixed-independent-review.md').read_bytes()
assert sha(task) == '3c09a0bd44dbe0da124d8f4953f734dcec338bc6abf9fb228eb21466eca12d73'
with (OUT / 'fixed-review-task.md').open('xb') as handle:
    handle.write(task)
result = {'schema': 'A24RouteCallbackIndependentIntake/v1', 'result': 'PASS_RAW_INTAKE_BEFORE_HELPER_IMPORT',
    'raw_members': 294, 'candidate_dependencies': 144, 'delivery_members': 293, 'private_snapshots': 21,
    'all_raw_size_sha256_git_blob_checks': True, 'actual_local_libraries_verified_before_import': libraries,
    'python': sys.version.split()[0], 'playwright': '1.58.0', 'active_author_or_business_original_paths_read': False,
    'task_sha256': sha(task), 'product_or_library_helper_imports_before_verification': 0,
    'source_inspection_no_match': {'chunk': 'c20b54', 'exit': 1,
        'meaning': 'rg literal mapper call pattern absent in generated source; earlier source reads succeeded; exact _wrap_handler spelling inspected subsequently',
        'product_or_control_failure': False}}
with (OUT / 'intake-result.json').open('xb') as handle:
    handle.write((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps({k: v for k, v in result.items() if k not in ('actual_local_libraries_verified_before_import',)}))
