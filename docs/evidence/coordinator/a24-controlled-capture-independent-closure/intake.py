"""Read-only frozen-byte intake, before product imports or controls."""
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[3]
DELIVERY=ROOT/'docs/evidence/A24/controlled-capture-integration'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def verify(rows,count,git=False):
    assert len(rows)==len({row['path'] for row in rows})==count
    for row in rows:
        target=(ROOT/row['path']).resolve();assert ROOT in target.parents
        raw=target.read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
        if git:assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['blob']


raw=Path('D:/1800/docs/evidence/coordinator/a24-controlled-capture-integration-delivery/input-raw-manifest.json').read_bytes()
assert sha(raw)=='53e6959b6e213bdd89443c1654b75a25ad065d665c121114c2edf0ac80cf02e9'
with (OUT/'input-raw-manifest.json').open('xb') as handle:handle.write(raw)
manifest=json.loads(raw);verify(manifest['members'],322,True)
assert len(manifest['private_references'])==41
for row in manifest['private_references']:
    path=Path(row['snapshot_path']).resolve();assert ROOT/'.local' in path.parents
    value=path.read_bytes();assert len(value)==row['bytes'] and sha(value)==row['sha256']
candidate=(DELIVERY/'candidate-manifest.json').read_bytes();delivery=(DELIVERY/'delivery-final-manifest.json').read_bytes()
assert sha(candidate)=='f1b31fe4e27b9cb47e5476805e00fc56ce49d33666fd8353c67ce43bd4d9326a'
assert sha(delivery)=='8abdacaf11329d62e2ad1e56ae95cf527689d3310cadaecc749298766f8949a9'
verify(json.loads(candidate)['dependencies'],158);verify(json.loads(delivery)['members'],321)
task=Path('D:/1800/docs/tasks/A24-controlled-capture-fixed-independent-review.md').read_bytes()
with (OUT/'fixed-review-task.md').open('xb') as handle:handle.write(task)
rel='src/annotation/runtime/live_pilot/owner.py'
before=(Path('D:/1800-worktrees/a24-bootstrap-body-actual-review')/rel).read_text(encoding='utf-8')
after=(ROOT/rel).read_text(encoding='utf-8')
delta=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='fixed-prior/'+rel,tofile='fixed-product/'+rel))
with (OUT/'owner-delta.patch').open('xb') as handle:handle.write(delta.encode())
result=dict(schema='A24ControlledCaptureIndependentIntake/v1',at=datetime.now(timezone.utc).isoformat(),
    result='PASS_FROZEN_RAW_INTAKE_ONLY',raw_git_inputs=322,candidate_dependencies=158,delivery_members=321,
    private_snapshots=41,task_sha256=sha(task),all_raw_size_sha256_git_blob_checks=True,
    historical_tree_audit='ROOT_FIXED_33352_ONLY_OWNER_CHANGED_NOT_RERUN',product_imports_before_intake=0,
    active_author_reads=False,original_private_paths_read=False)
with (OUT/'intake-result.json').open('xb') as handle:handle.write((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps(result));print(delta)
