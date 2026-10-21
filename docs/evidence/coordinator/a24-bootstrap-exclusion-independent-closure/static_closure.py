"""Read-only AST delta and frozen-input closure checks; no product execution."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
OLD = Path('D:/1800-worktrees/a24-callback-body-actual-review')
REL = 'src/annotation/runtime/live_pilot/owner.py'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    with (OUT / name).open('xb') as handle:
        handle.write((json.dumps(value, indent=2)+'\n').encode('utf-8'))


before, after = (OLD / REL).read_bytes(), (ROOT / REL).read_bytes()
old_tree, new_tree = ast.parse(before), ast.parse(after)
new_tree.body = [node for node in new_tree.body if not (
    isinstance(node, ast.Import) and [v.name for v in node.names] == ['re']) and not (
    isinstance(node, ast.FunctionDef) and node.name == 'guard_evidence')]
checks = {}
for node in new_tree.body:
    if isinstance(node, ast.ClassDef) and node.name == 'BootstrapPolicy':
        method = next(v for v in node.body if isinstance(v, ast.FunctionDef) and v.name == 'decide')
        checks['exclusion_prefix_import'] = isinstance(method.body[0], ast.ImportFrom) and method.body[0].module == 'annotation.source.usense.current_readonly.policy'
        checks['exclusion_prefix_denial_only'] = ast.dump(method.body[1], include_attributes=False) == ast.dump(ast.parse(
            'if excluded_static(method, url, kind, redirected):\n    return False, EXCLUDED_STATIC').body[0], include_attributes=False)
        method.body = method.body[2:]
    if isinstance(node, ast.AsyncFunctionDef) and node.name == 'run_owned_worker':
        finalizer = next(v for v in node.body if isinstance(v, ast.Try)).finalbody
        removed = []
        for value in list(finalizer):
            if isinstance(value, ast.Assign) and len(value.targets) == 1:
                target = value.targets[0]
                if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and target.value.id == 'result' and isinstance(target.slice, ast.Constant) and target.slice.value in ('guard_evidence_before_release', 'guard_evidence_after_release'):
                    removed.append(target.slice.value)
                    finalizer.remove(value)
        checks['only_before_after_projection_statements_removed'] = removed == ['guard_evidence_before_release', 'guard_evidence_after_release']
checks['all_other_owner_ast_identical'] = ast.dump(old_tree, include_attributes=False) == ast.dump(new_tree, include_attributes=False)
with (OUT / 'owner-delta.patch').open('xb') as handle:
    handle.write(''.join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                          fromfile='frozen-actual/'+REL, tofile='frozen-product/'+REL)).encode())
save('static-delta-result.json', dict(schema='A24BootstrapIndependentStaticDelta/v1', checks=checks,
     passed=all(checks.values()), baseline_owner_sha256=sha(before), product_owner_sha256=sha(after),
     source_execution=False, extra_test_or_control=False))

manifest_raw = (OUT / 'input-raw-manifest.json').read_bytes()
assert sha(manifest_raw) == 'b8b76362839d1d0ab688830044b165ef19c6979138d0a96a56dc4e102016c490'
manifest = json.loads(manifest_raw)
for row in manifest['members']:
    raw = (ROOT / row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == row['blob']
for row in manifest['private_references']:
    raw = Path(row['snapshot_path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
save('input-preservation.json', dict(schema='A24BootstrapIndependentInputPreservation/v1',
     at=datetime.now(timezone.utc).isoformat(), result='ALL_FROZEN_INPUTS_UNCHANGED',
     raw_git_inputs=len(manifest['members']), private_snapshots=len(manifest['private_references']),
     input_manifest_sha256=sha(manifest_raw), product_or_input_edits=0,
     historical_33162_member_comparison='ROOT_FIXED_EVIDENCE_NOT_RERUN',
     source_execution=False, test_or_control_reruns=0))
print(json.dumps(dict(static_delta=checks, raw_inputs=len(manifest['members']), private_snapshots=len(manifest['private_references']))))
