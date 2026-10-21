"""Frozen actual intake only; no product import, tests or real resources."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
ACTUAL=ROOT/'docs/evidence/A24/bootstrap-current-body-actual'
MANIFEST=Path('D:/1800/docs/evidence/coordinator/a24-bootstrap-body-actual-delivery/input-raw-manifest.json')
TASK=Path('D:/1800/docs/tasks/A24-bootstrap-body-fixed-actual-independent-review.md')


def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(name,value):
    with (OUT/name).open('xb') as handle: handle.write((json.dumps(value,indent=2)+'\n').encode())


raw=MANIFEST.read_bytes()
assert sha(raw)=='909574bb4869b10205202dc6ddf74a802d7038e199f62db06d752d8018f11c6f'
with (OUT/'input-raw-manifest.json').open('xb') as handle: handle.write(raw)
manifest=json.loads(raw)
assert len(manifest['members'])==len({r['path'] for r in manifest['members']})==336
for row in manifest['members']:
    path=(ROOT/row['path']).resolve(); assert ROOT in path.parents
    value=path.read_bytes()
    assert len(value)==row['bytes'] and sha(value)==row['sha256']
    assert hashlib.sha1(b'blob '+str(len(value)).encode()+b'\0'+value).hexdigest()==row['blob']
assert len(manifest['private_references'])==41
for row in manifest['private_references']:
    path=Path(row['snapshot_path']).resolve(); assert ROOT/'.local' in path.parents
    value=path.read_bytes()
    assert len(value)==row['bytes'] and sha(value)==row['sha256']
final_raw=(ACTUAL/'delivery-final-manifest.json').read_bytes()
assert sha(final_raw)=='0797461bf4fb33f63fb288af962ffdedbfa7e59906decd23579f501b450b207c'
final=json.loads(final_raw)
assert len(final['members'])==27
for row in final['members']:
    value=(ROOT/row['path']).read_bytes()
    assert len(value)==row['bytes'] and sha(value)==row['sha256']
task_raw=TASK.read_bytes()
with (OUT/'fixed-review-task.md').open('xb') as handle: handle.write(task_raw)
result=dict(schema='A24BootstrapBodyActualIndependentIntake/v1',at=datetime.now(timezone.utc).isoformat(),
    result='PASS_FROZEN_RAW_INTAKE_ONLY',raw_git_inputs=336,actual_delivery_members=27,private_snapshots=41,
    root_manifest_sha256=sha(raw),actual_final_manifest_sha256=sha(final_raw),task_sha256=sha(task_raw),
    historical_tree_audit='ROOT_FIXED_33324_UNCHANGED_28_ADDED_NOT_RERUN',
    source_model_quality_review_repeated=False,tests_run=0,product_imports=0,real_resources=0,active_author_reads=False)
save('intake-result.json',result)
print(json.dumps(result))
print('NEW_ACTUAL_PUBLIC_FILES '+json.dumps([r['path'] for r in final['members']]))
for path in sorted((ACTUAL/'raw').rglob('*.json')):
    value=json.loads(path.read_bytes())
    print('PUBLIC_JSON_KEYS '+path.relative_to(ACTUAL).as_posix()+' '+json.dumps(list(value)))
