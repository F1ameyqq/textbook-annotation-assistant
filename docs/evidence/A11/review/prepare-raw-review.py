"""A11 independent static export/integrity audit. No product invocation."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

REPO = Path('D:/1800')
REPORT = Path('D:/1800-worktrees/a11-r')
RUN = Path('D:/1800-worktrees/a11-rr')
EVIDENCE = REPORT / 'docs/evidence/A11/review'
FINAL = 'c580ca63ada9e452fd5ee71e5272cf0d047d4574'
PRODUCT = 'ea5b62fd593041c29c00831ddb0eb453b0230307'
BASE = '87f55ff636e463053f0b3c3ec97b0692511a06d0'
WORKFLOW = '6080aa6fea5dc9a9e8397ad97aef099e81848f70'
ENV = dict(os.environ, GIT_NO_LAZY_FETCH='1')

def git(*args):
    return subprocess.check_output(['git','-c','core.longpaths=true',*args], cwd=REPO, env=ENV)

def tree(ref):
    result = {}
    for row in git('ls-tree','-r','-z',ref).split(b'\0'):
        if not row:
            continue
        info, path = row.split(b'\t',1)
        mode, kind, blob = info.decode().split()
        result[path.decode('utf-8')] = {'mode':mode,'type':kind,'blob':blob}
    return result

def blob(ref,path):
    return git('show',ref+':'+path)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write_json(name,value):
    (EVIDENCE/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))

before, final, product = tree(BASE), tree(FINAL), tree(PRODUCT)
manifest_path = 'docs/evidence/A11/execution/delivery-raw-manifest.json'
manifest_raw = blob(FINAL,manifest_path)
assert sha(manifest_raw) == '161e8493d92f5a86712c60144f2b723d17354330f0f07c90136c071ae8676834'
manifest = json.loads(manifest_raw)
members = manifest['new_members_excluding_this_manifest']
assert len(members) == 442
assert all(final.get(p)==identity for p,identity in before.items())
added = set(final)-set(before)
assert added == {x['path'] for x in members}|{manifest_path}
total = 0
for item in members:
    p = item['path']
    raw = blob(FINAL,p)
    assert final[p] == {k:item[k] for k in ('mode','type','blob')}
    assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
    total += len(raw)
assert total == 8905388
runtime_paths = sorted(p for p in product if p.startswith('src/annotation/') or
    p.startswith('tests/fixtures/live_pilot/') or p in (
    'tests/test_live_pilot_admission.py','tests/test_live_pilot_journal.py','tests/test_live_pilot_readback.py',
    'docs/evidence/A11/execution/run-suite.py','docs/evidence/A11/execution/suite-catalog.json',
    'docs/evidence/A11/execution/fixture-manifest.json'))
assert all(final[p]==product[p] for p in runtime_paths)
exports = []
for p in runtime_paths:
    raw = blob(PRODUCT,p)
    target = RUN/p
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists()
    target.write_bytes(raw)
    assert target.read_bytes()==raw
    exports.append(dict(path=p,sha256=sha(raw),bytes=len(raw),**product[p]))
report_paths = sorted(set(added)|set(runtime_paths)|{
    'docs/contracts-v1.md','docs/architecture.md','项目交接说明.md','docs/coordination.md',
    'docs/development-plan.md','docs/evidence/coordinator/72h-live-runner/implementation-scope.md',
    'docs/tasks/A11-limited-live-runner-offline-core.md'})
for p in report_paths:
    if p not in final:
        continue
    raw = blob(FINAL,p)
    target = REPORT/p
    target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists()
    target.write_bytes(raw)
    assert target.read_bytes()==raw
# Review dispatch documents postdate the author final: keep their exact bytes as new evidence.
for p in ('docs/tasks/A11-limited-live-runner-independent-review.md',
          'docs/evidence/coordinator/a11-preflight-20261019/preflight.json'):
    (EVIDENCE/('dispatch-'+Path(p).name)).write_bytes(blob(WORKFLOW,p))
write_json('run-export-manifest.json', {'product':PRODUCT,'run_root':str(RUN),'members':exports})
write_json('integrity-preflight.json', {
    'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'baseline':BASE,'author_final':FINAL,'running_product':PRODUCT,'dispatch_workflow':WORKFLOW,
    'report_root':str(REPORT),'run_root':str(RUN),'manifest_sha256':sha(manifest_raw),
    'raw_members_verified':len(members),'raw_member_bytes':total,'added_paths':len(added),
    'old_mode_type_blob_preserved':len(before),'runtime_export_members':len(exports),
    'runtime_bytes_verified':True,'runtime_product_final_equal':True,'product_invocations':0,
    'report_branch':'codex/a11-live-pilot-review','run_head':PRODUCT})
print(json.dumps({'old_preserved':len(before),'new_paths':len(added),'raw_verified':len(members),
                  'raw_bytes':total,'exported_runtime_members':len(exports)}))
