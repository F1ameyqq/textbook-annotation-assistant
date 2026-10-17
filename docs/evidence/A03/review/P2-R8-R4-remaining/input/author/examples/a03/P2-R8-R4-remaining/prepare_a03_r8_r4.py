"""Freeze exact R4 inputs without importing product or executing old drivers."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-R4-remaining'
BASE = 'd9ed692db9ab8e9277f8ffd09e040451e8b8f65f'
WORKFLOW = 'cb9c8f76e9eae40a8fda042c196705d7258b5107'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT)


if __name__ == '__main__':
    assert git('rev-parse', 'HEAD').decode().strip() == BASE
    assert not git('status', '--porcelain', '--untracked-files=no')
    attributes = b'* -text whitespace=trailing-space,space-before-tab,cr-at-eol\n**/stdout.txt -whitespace\n**/stderr.txt -whitespace\n'
    write(OUT / '.gitattributes', attributes)
    write(Path(__file__).parent / '.gitattributes', attributes)
    pins = []
    for name, expected in (
        ('A03-P2-R8-R4-remaining-validation.md', '5a93ea9012ad8d9d2f69e622235051cbf1ced23922e1e6fc021c4443657e184b'),
        ('A03-P2-R8-R3-post-hold-review-report.md', 'a39afab68c15837122a34fb0f75dca7cae339dd2ba1be13dde007971b99b9a17'),
        ('A03-P2-R8-R3-post-hold-coordinator-decision.md', None),
        ('A03-P2-R8-native-bridge-implementation.md', None),
        ('A03-runtime-recovery.md', None), ('A03-independent-review.md', None)):
        raw = git('show', WORKFLOW + ':docs/tasks/' + name)
        assert expected is None or sha(raw) == expected, name
        write(OUT / 'inputs' / name, raw)
        pins.append({'workflow': WORKFLOW, 'path': 'docs/tasks/' + name, 'bytes': len(raw), 'sha256': sha(raw)})
    originals = []
    for name in ('tests/test_a03_r8_r3_post_hold.py', 'tests/test_a03_r8_r3_local.py',
        'src/annotation/runtime/storage/native.py', 'src/annotation/contracts/a03_native/data/profile.json',
        'src/annotation/contracts/a03_native/data/adoption.json',
        'docs/evidence/A03/execution/P2-R8-R3-post-hold/runs/N7/stderr.txt'):
        raw = git('show', BASE + ':' + name)
        assert (ROOT / name).read_bytes() == raw, name
        originals.append({'path': name, 'bytes': len(raw), 'sha256': sha(raw)})
    tree = git('ls-tree', '-r', BASE)
    write(OUT / 'inputs.json', {'base': BASE, 'workflow': WORKFLOW, 'files': pins, 'unchanged_references': originals,
        'base_tree_sha256': sha(tree), 'base_entries': len(tree.splitlines())})
    write(OUT / 'routing.json', {'parent_entry': 'tests/test_a03_r8_r4_remaining.py',
        'normal_import': 'test_a03_r8_r3_post_hold', 'N1_method': 'R8R3NativeBridgeTests.test_N1',
        'only_test_module_globals_routed': ['EVIDENCE', 'BASE_EVIDENCE'],
        'N1_child_entry_unchanged': 'tests/test_a03_r8_r3_post_hold.py --n1-child <new R4 case path>',
        'output_root': 'docs/evidence/A03/execution/P2-R8-R4-remaining/validation/r4-native-01',
        'fixture': 'tests/fixtures/a03/P2-R8-R3-post-hold',
        'identity_note': 'Accepted fixed synthetic template labels retained; actual run/observation/intent/receipt/resolution IDs and artifact four-tuples generated afresh in empty new dual databases.',
        'no_old_validation_or_database_copied': True, 'AST_exec_import_slicing': False})
    print(json.dumps({'pins': len(pins), 'base_entries': len(tree.splitlines()), 'product_execution': False}))
