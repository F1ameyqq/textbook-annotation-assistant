"""R12 frozen preparation-stop handoff audit; no product or SQL execution."""
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path('D:/1800')
AUTHOR = Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
BASE = 'cc5966dc58c62017a27266c40ca0cedc5c68485c'
TARGET = '394fe51f5ed14c5ed312073a20faac0f5cbb9990'
WORKFLOW = '7593f880ebec191ed55e03b2d3893d68b00ab0ca'
PREFIX = 'docs/evidence/A03/execution/P2-R12-inconclusive-readback/'
MANIFEST = PREFIX + 'manifest.json'
REPORT = 'docs/tasks/A03-P2-R12-inconclusive-readback-report.md'

def git(*args, data=None):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=AUTHOR, input=data, timeout=45)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def tree(commit):
    result = {}
    for row in git('ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if row:
            info, path = row.split(b'\t', 1)
            result[path.decode('utf-8')] = info
    return result

assert git('rev-parse', 'HEAD').decode().strip() == TARGET
assert not git('status', '--porcelain')
old, new = tree(BASE), tree(TARGET)
assert len(old) == 32993 and all(new.get(p) == v for p, v in old.items())
added = set(new) - set(old)
allowed = [PREFIX, 'examples/a03/P2-R12-inconclusive-readback/']
assert all(p.startswith(tuple(allowed)) or p in [REPORT, 'tests/test_a03_p2_r12_inconclusive_readback.py'] for p in added)
batch = git('cat-file', '--batch', data=('\n'.join(TARGET + ':' + p for p in sorted(added)) + '\n').encode())
offset, blobs = 0, {}
for p in sorted(added):
    end = batch.index(b'\n', offset)
    oid, kind, size = batch[offset:end].decode().split()
    raw = batch[end + 1:end + 1 + int(size)]
    offset = end + int(size) + 2
    assert kind == 'blob' and oid.encode() == new[p].split()[2]
    assert raw == (AUTHOR / p).read_bytes(), p
    blobs[p] = raw
assert offset == len(batch) and len(blobs) == 39
assert sha(blobs[MANIFEST]) == 'b3f0483de0b007341a750963f3d71db92b8b9efec124c26b8394935bd6325f75'
assert sha(blobs[REPORT]) == 'cfb51c43f718349aa2c8d99fbb9bc3e145eb6b891e4d9507065648af9bd4fc04'
manifest = json.loads(blobs[MANIFEST])
entries = manifest['entries']
assert len(entries) == 38 and {r['path'] for r in entries} | {MANIFEST} == added
for r in entries:
    assert len(blobs[r['path']]) == r['bytes'] and sha(blobs[r['path']]) == r['sha256']
inputs = json.loads(blobs[PREFIX + 'inputs.json'])
for r in inputs['files']:
    assert r['workflow'] == WORKFLOW
    raw = git('show', WORKFLOW + ':' + r['path'])
    assert sha(raw) == r['sha256'] and len(raw) == r['bytes']
    assert raw == blobs[PREFIX + 'inputs/' + Path(r['path']).name]
for r in inputs['sources']:
    raw = git('show', BASE + ':' + r['path'])
    assert sha(raw) == r['raw_Git_sha256'] == r['worktree_sha256']
    assert raw == blobs[PREFIX + 'inputs/base/' + r['path']] == (AUTHOR / r['path']).read_bytes()
assert len(inputs['files']) == 4 and len(inputs['sources']) == 10
release = json.loads(blobs[PREFIX + 'process-release.json'])
assert release['all_recorded_owned_processes_waited_and_ended'] and len(release['records']) == 1
record = release['records'][0]
folder = PREFIX + 'runs/static-prerequisite/'
pre, start, done = (json.loads(blobs[folder + n]) for n in ['preregistered.json', 'started.json', 'completed.json'])
assert record['pid'] == start['pid'] == done['pid'] == 54248
assert record['exit_code'] == done['exit_code'] == 0
assert not any(d[k] for d in [record, done] for k in ['alive', 'timed_out'])
assert pre['scope'] == 'STATIC_ONLY_NO_PRODUCT_CALLS' and pre['timeout_seconds'] == 45
assert sha(blobs[folder + 'script-snapshot.py']) == pre['script_sha256'] == sha(blobs['tests/test_a03_p2_r12_inconclusive_readback.py'])
assert sha(blobs[PREFIX + 'inputs.json']) == pre['inputs_sha256']
assert sha(blobs[folder + 'product-source-index.json']) == pre['source_index_sha256']
for stream in ['stdout', 'stderr']:
    assert sha(blobs[folder + stream + '.txt']) == done[stream + '_sha256']
outcome = json.loads(blobs[PREFIX + 'bounded-outcome.json'])
assert outcome['functional_processes'] == outcome['init_register_PRE_dispatch_UNKNOWN_reconcile_calls'] == outcome['product_modifications'] == 0
assert outcome['runtime_target_databases'] == 'NOT_CREATED'
assert all(outcome[x].startswith('NOT_EXECUTED') for x in ['U1', 'U2', 'U3', 'U4', 'U5'])
assert not any(p.endswith(('.sqlite', '.sqlite3', '.db')) for p in added)
result = {'status': 'FROZEN_PREPARATION_STOP_DELIVERY_VERIFIED_NOT_FUNCTIONAL_ACCEPTANCE',
    'at': datetime.now().astimezone().isoformat(), 'base_commit': BASE, 'target_commit': TARGET, 'workflow_commit': WORKFLOW,
    'old_tree_entries_unchanged': len(old), 'new_raw_files_verified': len(blobs), 'manifest_entries': len(entries),
    'report': REPORT, 'report_sha256': sha(blobs[REPORT]), 'manifest': MANIFEST, 'manifest_sha256': sha(blobs[MANIFEST]),
    'process_release_sha256': sha(blobs[PREFIX + 'process-release.json']), 'raw_workflow_inputs': 4, 'raw_source_inputs': 10,
    'registered_static_child_exited': 1, 'functional_cases_executed': 0, 'coordinator_product_calls': 0,
    'coordinator_SQL_connections': 0, 'working_tree_clean': True, 'independent_review_required': True,
    'product_integration': False, 'I01_released': False, 'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
(ROOT / 'docs/evidence/coordinator/heartbeat-20261018-0830/r12-delivery-preflight.json').write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
print(json.dumps(result, ensure_ascii=False))
