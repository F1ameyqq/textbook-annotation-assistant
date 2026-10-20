"""Immutable Git metadata/AST and fixed raw checks; no product import/run."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = '1d2ba3766558fe9cc911756666d962184cc1de57'
PRODUCT = '1168a75eb35f319c3ced270b6c515adbdb38603f'
FINAL = '8bffd88dacc146fc3f061ed0863b299fa5dabd30'
PREFIX = 'docs/evidence/A17/revisions/first-cause-r1/'
PROBE = 'tools/a16_current_state_probe.py'
GATE = 'src/annotation/source/usense/current_readonly/gate.py'
env = dict(os.environ, GIT_NO_LAZY_FETCH='1')
commands = []


def git(*args):
    command = ['git', '-c', 'core.longpaths=true', *args]
    value = subprocess.run(command, cwd='D:/1800', env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, check=False, creationflags=0x08000000)
    commands.append({'argv': command, 'exit_code': value.returncode,
                     'stdout_sha256': hashlib.sha256(value.stdout).hexdigest(),
                     'stdout_bytes': len(value.stdout), 'stderr': value.stderr.decode('utf-8', errors='replace')})
    assert value.returncode == 0
    return value.stdout


def tree(raw):
    result = {}
    for row in raw.split(b'\0'):
        if row:
            identity, name = row.split(b'\t', 1)
            mode, kind, blob = identity.decode('ascii').split()
            result[name.decode('utf-8')] = [mode, kind, blob]
    return result


def strip_nodes(raw, names):
    module = ast.parse(raw.decode('utf-8'))
    def name(node):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            return node.name
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            return node.targets[0].id
        return None
    module.body = [node for node in module.body if name(node) not in names]
    return ast.dump(module, include_attributes=False)


def main():
    parent_rows = git('show', '-s', '--format=%H %P', PRODUCT, FINAL).decode('ascii').splitlines()
    parents = {row.split()[0]: row.split()[1:] for row in parent_rows if row.strip()}
    assert parents[PRODUCT] == [BASE] and parents[FINAL] == [PRODUCT]
    raw = {n: git('ls-tree', '-r', '-z', '--full-tree', c)
           for n, c in [('base', BASE), ('product', PRODUCT), ('final', FINAL)]}
    for name in ('base', 'product'):
        assert raw[name] == (ROOT / PREFIX / 'preservation' / (name + '-tree.raw')).read_bytes()
    before, product, after = [tree(raw[n]) for n in ('base', 'product', 'final')]
    changed = sorted(k for k in before if before[k] != after.get(k))
    added = sorted(set(after) - set(before))
    assert set(changed) == {PROBE, GATE}
    assert not set(before) - set(after) and len(added) == 45
    old_evidence = [k for k in before if k.startswith('docs/evidence/')]
    assert all(after[k] == before[k] for k in old_evidence)
    assert all(after[k] == v for k, v in product.items())
    new_probe = (ROOT / PROBE).read_bytes()
    old_probe = git('show', BASE + ':' + PROBE)
    old_gate = git('show', BASE + ':' + GATE)
    assert strip_nodes(old_probe, {'MANIFEST', 'observe_live'}) == strip_nodes(new_probe, {'MANIFEST', 'observe_live'})
    assert strip_nodes(old_gate, {'WORKFLOW'}) == strip_nodes((ROOT / GATE).read_bytes(), {'WORKFLOW'})
    diff = git('diff', '--no-ext-diff', '--no-textconv', BASE, PRODUCT, '--', PROBE, GATE)
    with (OUT / 'product-diff.patch').open('xb') as stream:
        stream.write(diff)
    candidate_raw = (ROOT / PREFIX / 'candidate-manifest.json').read_bytes()
    assert hashlib.sha256(candidate_raw).hexdigest() == '4ed38cb1f703c3d0b5e94d601f2f267c05ead871b9a26004e2e44e5d6eeb31dd'
    candidate = json.loads(candidate_raw)
    assert candidate['workflow_commit'] == 'd137a1bba49550f661b110ee14c9541a1dc4fb19'
    assert len(candidate['members']) == 18
    for m in candidate['members']:
        data = (ROOT / m['path']).read_bytes()
        assert len(data) == m['size'] and hashlib.sha256(data).hexdigest() == m['sha256']
        assert after[m['path']] == [m['mode'], m['type'], m['blob']]
    for namespace in candidate['package_initialization']['namespace_without_initializer']:
        assert namespace + '/__init__.py' not in after
    for m in json.loads((OUT / 'intake.json').read_bytes())['members']:
        data = (ROOT / m['path']).read_bytes()
        assert len(data) == m['bytes'] and hashlib.sha256(data).hexdigest() == m['sha256']
        assert after[m['path']] == [m['mode'], m['type'], m['blob']]
    result = {'result': 'PASS_STATIC_AND_PRESERVATION_ONLY', 'parents': parents,
        'base_members': len(before), 'unchanged_old_members': len(before) - 2,
        'changed_members': changed, 'added_members': added, 'deletions': 0,
        'old_evidence_members_preserved': len(old_evidence), 'fixed_inputs_verified': 56,
        'candidate_dependencies_verified': 18, 'raw_tree_bytes_equal_git': True,
        'probe_outside_manifest_and_observe_live_AST_identical': True,
        'gate_outside_workflow_AST_identical': True,
        'unchanged_safety_nodes': ['ReadPolicy', 'CurrentGuard', 'settle_callbacks', 'collect',
                                 'open_owned', 'occupancy', 'supervise', 'worker_main', 'launcher', 'native_reference'],
        'manual_observe_live_diff_review': 'Only error-field selection helper/call sites change; '
                                         'ERROR assignment, terminal gate, release checks and return codes retained.',
        'commands': commands, 'product_imports': 0, 'old_suites': 0,
        'git_metadata_children': len(commands), 'product_children': 0}
    with (OUT / 'static-result.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('commands', 'added_members')}))


if __name__ == '__main__':
    main()
