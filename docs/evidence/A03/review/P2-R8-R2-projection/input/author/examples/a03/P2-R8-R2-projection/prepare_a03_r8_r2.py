"""Freeze exact R2 inputs and prepare isolated drivers/data; no product runs."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-R2-projection'
BASE = 'a0c40886f3076f84c46377e03fc2206d2fdc5585'
WORKFLOW = '016e048669e5af1f193e71968d03bf3000cf16d1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def digest(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())


def ref(value):
    return {key: value[key] for key in ('artifact_id', 'revision', 'kind', 'content_hash')}


def main():
    def git(*args):
        return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT)
    if git('rev-parse', 'HEAD').decode().strip() != BASE or git('status', '--porcelain', '--untracked-files=no'):
        raise RuntimeError('expected exact clean tracked base')
    pins = []
    for name, expected in (
        ('A03-P2-R8-R2-projection-rework.md', 'c76ef2a47fa9bbfecb83b05e02cfe56a6599c68600786d2a86eb9547c35fb3e0'),
        ('A03-P2-R8-R1-producer-review-report.md', '37ad11cbecefcfc97c2c1487786f66418bd231c79e7b7654bd9d6c7a8fbf9cbf'),
        ('A03-P2-R8-R1-producer-coordinator-decision.md', None)):
        raw = git('show', WORKFLOW + ':docs/tasks/' + name)
        if expected is not None and sha(raw) != expected:
            raise RuntimeError('exact workflow pin mismatch: ' + name)
        write(OUT / 'inputs' / name, raw)
        pins.append({'workflow': WORKFLOW, 'path': 'docs/tasks/' + name, 'sha256': sha(raw), 'bytes': len(raw)})
    for name in ('src/annotation/runtime/storage/__init__.py', 'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json'):
        raw = (ROOT / name).read_bytes()
        write(OUT / 'inputs/base' / name, raw)
        pins.append({'base': BASE, 'path': name, 'sha256': sha(raw), 'bytes': len(raw)})
    tree = git('ls-tree', '-r', BASE)
    write(OUT / 'inputs.json', encoded({'base': BASE, 'workflow': WORKFLOW, 'files': pins,
        'base_tree_sha256': sha(tree), 'base_entries': len(tree.splitlines())}))
    attributes = b'* -text whitespace=trailing-space,space-before-tab,cr-at-eol\n**/stdout.txt -whitespace\n**/stderr.txt -whitespace\n'
    write(OUT / '.gitattributes', attributes)
    write(HERE / '.gitattributes', attributes)
    old = ROOT / 'examples/a03/P2-R8-R1-producer'
    audit = (old / 'audit_a03_r8_r1.py').read_text(encoding='utf-8')
    audit = audit.replace('P2-R8-R1-producer', 'P2-R8-R2-projection').replace('fa6edeb7e9dd0c9502781747e5fce012931d9441', BASE).replace('b9889efd29baa364bdd0ce9e356a8cde7054f8d9', WORKFLOW)
    write(HERE / 'audit_a03_r8_r2.py', audit.encode('utf-8'))
    compat = (old / 'compat_a03_r8_r1.py').read_text(encoding='utf-8').replace('audit_a03_r8_r1', 'audit_a03_r8_r2')
    write(HERE / 'compat_a03_r8_r2.py', compat.encode('utf-8'))
    tests = (ROOT / 'tests/test_a03_r8_r1_producer.py').read_text(encoding='utf-8')
    tests = tests.replace('R8R1NativeBridgeTests', 'R8R2NativeBridgeTests').replace('P2-R8-R1-producer', 'P2-R8-R2-projection').replace('-r8-r1', '-r8-r2')
    tests = tests.replace('A03_R8_R1_RUN_ID', 'A03_R8_R2_RUN_ID').replace('native-r1-01', 'native-r2-01')
    write(ROOT / 'tests/test_a03_r8_r2_projection.py', tests.encode('utf-8'))
    fixture = ROOT / 'tests/fixtures/a03/P2-R8-R2-projection'
    previous = ROOT / 'tests/fixtures/a03/P2-R8-R1-producer'
    write(fixture / '.gitattributes', attributes)
    for name in ('assets/page.pgm', 'assets/proof.txt'):
        write(fixture / name, (previous / name).read_bytes())
    def rename(value):
        if isinstance(value, str):
            return value.replace('-r8-r1', '-r8-r2')
        if isinstance(value, dict):
            return {key: rename(child) for key, child in value.items()}
        if isinstance(value, list):
            return [rename(child) for child in value]
        return value
    data = rename(json.loads((previous / 'initial.json').read_bytes()))
    inventory_raw = encoded(rename(json.loads((previous / 'assets/inventory.json').read_bytes())))
    write(fixture / 'assets/inventory.json', inventory_raw)
    data['artifacts'][0]['payload']['scope_integrity']['proof']['sha256'] = sha(inventory_raw)
    policy = data['policies'][0]
    policy['content_hash'] = digest({k: v for k, v in policy.items() if k != 'content_hash'})
    policy_ref = {k: policy[k] for k in ('policy_id', 'revision', 'content_hash')}
    converted = {}
    def references(value):
        if isinstance(value, dict):
            if set(value) == {'artifact_id', 'revision', 'kind', 'content_hash'}:
                return ref(converted[value['kind']])
            return {k: references(v) for k, v in value.items()}
        if isinstance(value, list):
            return [references(v) for v in value]
        return value
    for artifact in data['artifacts']:
        artifact.update(references(artifact))
        artifact['producer']['policy_versions'] = [policy_ref]
        artifact['content_hash'] = digest({k: v for k, v in artifact.items() if k != 'content_hash'})
        converted[artifact['kind']] = artifact
    write(fixture / 'initial.json', encoded(data))
    print(json.dumps({'base': BASE, 'pins_verified': len(pins), 'fresh_fixture_artifacts': len(data['artifacts'])}))


if __name__ == '__main__':
    main()
