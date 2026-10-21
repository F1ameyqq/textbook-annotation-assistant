"""Static frozen-byte intake only; no product, script, model or tests."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
A=ROOT/'docs/evidence/A24/controlled-capture-current-body-actual'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(name,value):
    with (OUT/name).open('xb') as h:h.write((json.dumps(value,indent=2)+'\n').encode())

raw=Path('D:/1800/docs/evidence/coordinator/a24-controlled-capture-body-actual-delivery/input-raw-manifest.json').read_bytes()
assert sha(raw)=='aa537bcf9ded57a655a417a23077d4f7729edb7d7b7767ff1b4e49b8159cca27'
with (OUT/'input-raw-manifest.json').open('xb') as h:h.write(raw)
m=json.loads(raw);assert len(m['members'])==len({r['path'] for r in m['members']})==349
for row in m['members']:
    p=(ROOT/row['path']).resolve();assert ROOT in p.parents
    b=p.read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['blob']
assert len(m['private_references'])==57
for row in m['private_references']:
    p=Path(row['snapshot_path']).resolve();assert ROOT/'.local' in p.parents
    b=p.read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256']
delivery=(A/'delivery-final-manifest.json').read_bytes()
assert sha(delivery)=='0542873bcfa6d6a9343a1786c059bca8a37d59cfa1297ded20b357acb6d5008b'
d=json.loads(delivery);assert len(d['members'])==26
for row in d['members']:
    b=(ROOT/row['path']).read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256']
task=Path('D:/1800/docs/tasks/A24-controlled-capture-body-fixed-actual-independent-review.md').read_bytes()
with (OUT/'fixed-review-task.md').open('xb') as h:h.write(task)
save('intake-result.json',dict(schema='A24ControlledBodyActualIndependentIntake/v1',at=datetime.now(timezone.utc).isoformat(),
    result='PASS_FROZEN_RAW_INTAKE_ONLY',raw_git=349,delivery_members=26,private_snapshots=57,
    all_size_sha256_git_blob_checks=True,task_sha256=sha(task),historical_33521_tree_audit='ROOT_REFERENCE_NOT_REPEATED',
    product_tests=0,captured_script_execution=0,model_content_review=0,real_resources=0,active_author_reads=False))
print('INTAKE_MATCHED 349 raw / 26 delivery / 57 private')
private=json.loads((A/'private-raw-manifest.json').read_bytes())['members']
print('CURRENT_PRIVATE_KINDS '+json.dumps(dict(Counter(row['kind'] for row in private))))
print('ROOT_PRIVATE_ROW_KEYS '+json.dumps(list(m['private_references'][-1])))
print('ACTUAL_PUBLIC_FILES '+json.dumps([row['path'] for row in d['members']]))
w=json.loads((A/'raw/run/worker-result.json').read_bytes())
print('WORKER_KEYS '+json.dumps(list(w)))
print('PREWRITE '+json.dumps(w.get('prewrite')))
