"""Mechanical immutable-Git/input preservation check; no product import/run."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
REPO = Path('D:/1800')
BASE = '003f862065a2d630e666323c0d158e33bcee91e9'
PRODUCT = 'e7ee24245ffaf4d4b81cbddae8b3720aac214c1b'
FINAL = '1d2ba3766558fe9cc911756666d962184cc1de57'
ALLOW = {
    'src/annotation/source/usense/current_readonly/gate.py',
    'src/annotation/source/usense/current_readonly/policy.py',
    'tools/a16_current_state_probe.py', 'tools/a16_current_state_launcher.py'}
env = dict(os.environ, GIT_NO_LAZY_FETCH='1')
commands = []


def git(*args):
    command = ['git', '-c', 'core.longpaths=true', *args]
    result = subprocess.run(command, cwd=str(REPO), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False, creationflags=0x08000000)
    commands.append({'argv': command, 'exit_code': result.returncode,
                     'stdout_bytes': len(result.stdout),
                     'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
                     'stderr': result.stderr.decode('utf-8', errors='replace')})
    if result.returncode:
        raise RuntimeError('IMMUTABLE_GIT_METADATA_READ_FAILED')
    return result.stdout


def tree(raw):
    result = {}
    for row in raw.split(b'\0'):
        if not row:
            continue
        identity, name = row.split(b'\t', 1)
        mode, kind, blob = identity.decode('ascii').split()
        name = name.decode('utf-8')
        assert name not in result
        result[name] = [mode, kind, blob]
    return result


def main():
    parents = git('show', '-s', '--format=%H %P', BASE, PRODUCT, FINAL).decode('ascii').splitlines()
    parent_map = {row.split()[0]: row.split()[1:] for row in parents if row.strip()}
    assert parent_map[PRODUCT] == [BASE] and parent_map[FINAL] == [PRODUCT]
    raw = {name: git('ls-tree', '-r', '-z', '--full-tree', commit)
           for name, commit in [('base', BASE), ('product', PRODUCT), ('final', FINAL)]}
    evidence = ROOT / 'docs/evidence/A17/excluded-static/preservation'
    assert raw['base'] == (evidence / 'base-tree.raw').read_bytes()
    assert raw['product'] == (evidence / 'product-tree.raw').read_bytes()
    before, product, after = [tree(raw[name]) for name in ('base', 'product', 'final')]
    changed = sorted(k for k in before if after.get(k) != before[k])
    deleted = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    old_evidence = [k for k in before if k.startswith('docs/evidence/')]
    assert set(changed) == ALLOW and not deleted and len(added) == 50
    assert all(after[k] == before[k] for k in old_evidence)
    assert all(k.startswith(('docs/evidence/A17/', 'tests/a17_excluded_static/'))
               or (k.startswith('tools/a17_') and k.endswith('.py')) for k in added)
    assert all(after[k] == product[k] for k in product)
    candidate = json.loads((ROOT / 'docs/evidence/A17/excluded-static/candidate-manifest.json').read_bytes())
    assert len(candidate['members']) == 18
    for member in candidate['members']:
        assert after[member['path']] == [member['mode'], member['type'], member['blob']]
        data = (ROOT / member['path']).read_bytes()
        assert len(data) == member['size'] and hashlib.sha256(data).hexdigest() == member['sha256']
    for namespace in candidate['package_initialization']['namespace_without_initializer']:
        assert namespace + '/__init__.py' not in after
    intake = json.loads((OUT / 'intake.json').read_bytes())
    for member in intake['members']:
        path = ROOT / member['path']
        data = path.read_bytes()
        assert len(data) == member['bytes']
        assert hashlib.sha256(data).hexdigest() == member['sha256']
        assert after[member['path']] == ['100644', 'blob', member['blob']]
    result = {
        'task': 'A17', 'result': 'PASS_MECHANICAL_ONLY',
        'git_parents': parent_map, 'commands': commands,
        'base_members': len(before), 'final_members': len(after),
        'old_members_unchanged': len(before) - len(changed),
        'allowed_changed_members': changed, 'added_members': added,
        'deleted_members': deleted, 'old_evidence_members_preserved': len(old_evidence),
        'raw_base_and_product_tree_bytes_equal_immutable_git': True,
        'product_tree_preserved_in_final': True,
        'candidate_dependency_members_verified': 18,
        'namespace_initialization_claims_verified': True,
        'fixed_input_members_bytes_hash_and_git_mode_type_blob_verified': len(intake['members']),
        'product_imports_or_controls': 0, 'old_suites': 0,
        'git_metadata_children': len(commands), 'product_children': 0,
        'network_profile_native_browser_occupancy_business_calls': 0}
    with (OUT / 'preservation.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('commands', 'added_members')}))


if __name__ == '__main__':
    main()
