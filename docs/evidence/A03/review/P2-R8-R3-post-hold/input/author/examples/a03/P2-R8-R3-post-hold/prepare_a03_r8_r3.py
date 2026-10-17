"""Freeze exact R3 task/review/decision and prepare new isolated inputs."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-R3-post-hold'
BASE = '58d8a64734271d15654bb00b03d760f0f3eccd10'
WORKFLOW = 'b79b12fe6a82f9d88b6533b54aea016c4f67f60b'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def digest(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())


def main():
    def git(*args):
        return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT)
    if git('rev-parse', 'HEAD').decode().strip() != BASE or git('status', '--porcelain', '--untracked-files=no'):
        raise RuntimeError('expected exact clean tracked base')
    pins = []
    for name, expected in (
        ('A03-P2-R8-R3-post-hold-rework.md', '8bb76c2cd713ec9af5386f3dcd547f443bbef42d6d4d19fc603ef0fcf5bd6a29'),
        ('A03-P2-R8-R2-projection-review-report.md', '0cd36afd8409ec75ef04be9baf1602dc089d85a0bc5e187b393aece17a519565'),
        ('A03-P2-R8-R2-projection-coordinator-decision.md', None)):
        raw = git('show', WORKFLOW + ':docs/tasks/' + name)
        if expected and sha(raw) != expected:
            raise RuntimeError('workflow input hash mismatch: ' + name)
        write(OUT / 'inputs' / name, raw)
        pins.append({'workflow': WORKFLOW, 'path': 'docs/tasks/' + name, 'bytes': len(raw), 'sha256': sha(raw)})
    for name in ('src/annotation/runtime/storage/native.py', 'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json'):
        raw = (ROOT / name).read_bytes()
        write(OUT / 'inputs/base' / name, raw)
        pins.append({'base': BASE, 'path': name, 'bytes': len(raw), 'sha256': sha(raw)})
    tree = git('ls-tree', '-r', BASE)
    write(OUT / 'inputs.json', encoded({'base': BASE, 'workflow': WORKFLOW, 'files': pins,
        'base_tree_sha256': sha(tree), 'base_entries': len(tree.splitlines())}))
    attributes = b'* -text whitespace=trailing-space,space-before-tab,cr-at-eol\n**/stdout.txt -whitespace\n**/stderr.txt -whitespace\n'
    write(OUT / '.gitattributes', attributes)
    write(HERE / '.gitattributes', attributes)
    previous = ROOT / 'examples/a03/P2-R8-R2-projection'
    compat = (previous / 'compat_a03_r8_r2.py').read_text(encoding='utf-8').replace('audit_a03_r8_r2', 'audit_a03_r8_r3')
    write(HERE / 'compat_a03_r8_r3.py', compat.encode('utf-8'))
    tests = (ROOT / 'tests/test_a03_r8_r2_projection.py').read_text(encoding='utf-8')
    for old, new in (('R8R2NativeBridgeTests', 'R8R3NativeBridgeTests'), ('P2-R8-R2-projection', 'P2-R8-R3-post-hold'),
                     ('-r8-r2', '-r8-r3'), ('A03_R8_R2_RUN_ID', 'A03_R8_R3_RUN_ID'), ('native-r2-01', 'native-r3-01')):
        tests = tests.replace(old, new)
    write(ROOT / 'tests/test_a03_r8_r3_post_hold.py', tests.encode('utf-8'))
    previous_fixture = ROOT / 'tests/fixtures/a03/P2-R8-R2-projection'
    fixture = ROOT / 'tests/fixtures/a03/P2-R8-R3-post-hold'
    write(fixture / '.gitattributes', attributes)
    for name in ('assets/page.pgm', 'assets/proof.txt'):
        write(fixture / name, (previous_fixture / name).read_bytes())
    def rename(value):
        if isinstance(value, str):
            return value.replace('-r8-r2', '-r8-r3')
        if isinstance(value, dict):
            return {key: rename(child) for key, child in value.items()}
        if isinstance(value, list):
            return [rename(child) for child in value]
        return value
    data = rename(json.loads((previous_fixture / 'initial.json').read_bytes()))
    inventory_raw = encoded(rename(json.loads((previous_fixture / 'assets/inventory.json').read_bytes())))
    write(fixture / 'assets/inventory.json', inventory_raw)
    data['artifacts'][0]['payload']['scope_integrity']['proof']['sha256'] = sha(inventory_raw)
    policy = data['policies'][0]
    policy['content_hash'] = digest({k: v for k, v in policy.items() if k != 'content_hash'})
    policy_ref = {k: policy[k] for k in ('policy_id', 'revision', 'content_hash')}
    converted = {}
    def references(value):
        if isinstance(value, dict):
            if set(value) == {'artifact_id', 'revision', 'kind', 'content_hash'}:
                return {key: converted[value['kind']][key] for key in ('artifact_id', 'revision', 'kind', 'content_hash')}
            return {key: references(child) for key, child in value.items()}
        if isinstance(value, list):
            return [references(child) for child in value]
        return value
    for artifact in data['artifacts']:
        artifact.update(references(artifact))
        artifact['producer']['policy_versions'] = [policy_ref]
        artifact['content_hash'] = digest({k: v for k, v in artifact.items() if k != 'content_hash'})
        converted[artifact['kind']] = artifact
    write(fixture / 'initial.json', encoded(data))
    print(json.dumps({'base': BASE, 'pins_verified': len(pins), 'fixture_artifacts': len(data['artifacts'])}))


if __name__ == '__main__':
    main()
