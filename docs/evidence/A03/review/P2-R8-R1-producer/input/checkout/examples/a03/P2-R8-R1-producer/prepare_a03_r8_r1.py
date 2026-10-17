"""Freeze exact R1 inputs and prepare new data/drivers; no product execution."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-R1-producer'
HERE = Path(__file__).parent
BASE = 'fa6edeb7e9dd0c9502781747e5fce012931d9441'
WORKFLOW = 'b9889efd29baa364bdd0ce9e356a8cde7054f8d9'


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
    return {k: value[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}


def main():
    actual = subprocess.check_output(['git', '-c', 'core.longpaths=true', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    if actual != BASE:
        raise RuntimeError('wrong base')
    rows = []
    for name, expected in (
        ('A03-P2-R8-R1-producer-rework.md', 'bc0063986d164bd0ca7caeddfb2ed358439fd14e3d9d80961f2f5c85f932ad7b'),
        ('A03-P2-R8-native-bridge-review-report.md', '66690c0e259635d770cc44d2265b979e813c7e72494c1cf9b87257ed5c8e5555')):
        raw = subprocess.check_output(['git', '-c', 'core.longpaths=true', 'show', WORKFLOW + ':docs/tasks/' + name], cwd=ROOT)
        if sha(raw) != expected:
            raise RuntimeError('workflow input pin mismatch')
        write(OUT / 'inputs' / name, raw)
        rows.append({'workflow': WORKFLOW, 'path': 'docs/tasks/' + name, 'sha256': sha(raw), 'bytes': len(raw)})
    for name in ('src/annotation/quality/synthetic_precheck.py', 'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json'):
        raw = (ROOT / name).read_bytes()
        write(OUT / 'inputs/base' / name, raw)
        rows.append({'base': BASE, 'path': name, 'sha256': sha(raw), 'bytes': len(raw)})
    tree = subprocess.check_output(['git', '-c', 'core.longpaths=true', 'ls-tree', '-r', BASE], cwd=ROOT)
    write(OUT / 'inputs.json', encoded({'base': BASE, 'workflow': WORKFLOW, 'files': rows,
        'base_tree_sha256': sha(tree), 'base_entries': len(tree.splitlines())}))
    attributes = b'* -text whitespace=trailing-space,space-before-tab,cr-at-eol\n**/stdout.txt -whitespace\n**/stderr.txt -whitespace\n'
    write(OUT / '.gitattributes', attributes)
    write(HERE / '.gitattributes', attributes)
    old_audit = (ROOT / 'examples/a03/P2-R8-native-bridge/audit.py').read_text(encoding='utf-8')
    old_audit = old_audit.replace("EVIDENCE = ROOT / 'docs/evidence/A03/execution/P2-R8-native-bridge'", "EVIDENCE = ROOT / 'docs/evidence/A03/execution/P2-R8-R1-producer'")
    old_audit = old_audit.replace("BASE = '8ad45dd07214ae406a3fab28d76a4b5abd6eef03'", "BASE = '" + BASE + "'")
    old_audit = old_audit.replace("WORKFLOW = '873d8151000430fc79e63b312ccd21978fc15f79'", "WORKFLOW = '" + WORKFLOW + "'")
    write(HERE / 'audit_a03_r8_r1.py', old_audit.encode('utf-8'))
    compat = (ROOT / 'examples/a03/P2-R8-native-bridge/compat.py').read_text(encoding='utf-8').replace('from audit import', 'from audit_a03_r8_r1 import')
    write(HERE / 'compat_a03_r8_r1.py', compat.encode('utf-8'))
    tests = (ROOT / 'tests/test_a03_r8_native_bridge.py').read_text(encoding='utf-8')
    tests = tests.replace('R8NativeBridgeTests', 'R8R1NativeBridgeTests').replace('P2-R8-native-bridge', 'P2-R8-R1-producer').replace('-r8', '-r8-r1')
    tests = tests.replace('A03_R8_RUN_ID', 'A03_R8_R1_RUN_ID').replace("'bounded-01'", "'native-r1-01'")
    write(ROOT / 'tests/test_a03_r8_r1_producer.py', tests.encode('utf-8'))
    fixture = ROOT / 'tests/fixtures/a03/P2-R8-R1-producer'
    write(fixture / '.gitattributes', attributes)
    old_fixture = ROOT / 'tests/fixtures/a03/P2-R8-native-bridge'
    for name in ('assets/page.pgm', 'assets/proof.txt'):
        write(fixture / name, (old_fixture / name).read_bytes())
    data = json.loads((old_fixture / 'initial.json').read_bytes())
    def rename(value):
        if isinstance(value, str):
            return value.replace('-r8', '-r8-r1')
        if isinstance(value, dict):
            return {k: rename(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rename(v) for v in value]
        return value
    data = rename(data)
    inventory = rename(json.loads((old_fixture / 'assets/inventory.json').read_bytes()))
    inventory_raw = encoded(inventory)
    write(fixture / 'assets/inventory.json', inventory_raw)
    data['artifacts'][0]['payload']['scope_integrity']['proof']['sha256'] = sha(inventory_raw)
    policy = data['policies'][0]
    policy['content_hash'] = digest({k: v for k, v in policy.items() if k != 'content_hash'})
    policy_reference = {k: policy[k] for k in ('policy_id', 'revision', 'content_hash')}
    converted = {}
    def refs(value):
        if isinstance(value, dict):
            if set(value) == {'artifact_id', 'revision', 'kind', 'content_hash'}:
                return ref(converted[value['kind']])
            return {k: refs(v) for k, v in value.items()}
        if isinstance(value, list):
            return [refs(v) for v in value]
        return value
    for a in data['artifacts']:
        a.update(refs(a))
        a['producer']['policy_versions'] = [policy_reference]
        a['content_hash'] = digest({k: v for k, v in a.items() if k != 'content_hash'})
        converted[a['kind']] = a
    write(fixture / 'initial.json', encoded(data))
    print(json.dumps({'base': BASE, 'pins_verified': len(rows), 'fixture_artifacts': len(data['artifacts'])}))


if __name__ == '__main__':
    main()
