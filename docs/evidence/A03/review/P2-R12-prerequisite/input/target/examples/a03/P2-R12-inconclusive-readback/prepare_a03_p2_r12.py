"""Exact raw authority and minimal source export for static R12 prerequisite review."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R12-inconclusive-readback'
BASE = 'cc5966dc58c62017a27266c40ca0cedc5c68485c'
WORKFLOW = '7593f880ebec191ed55e03b2d3893d68b00ab0ca'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


if __name__ == '__main__':
    assert git('rev-parse', 'HEAD').decode().strip() == BASE
    assert not git('status', '--porcelain', '--untracked-files=no')
    attributes = b'* -text whitespace=trailing-space,space-before-tab,cr-at-eol\n**/stdout.txt -whitespace\n**/stderr.txt -whitespace\n'
    write(OUT / '.gitattributes', attributes)
    write(Path(__file__).parent / '.gitattributes', attributes)
    inputs = []
    for name, expected in (
        ('A03-P2-R12-inconclusive-readback-validation.md', '15c4f65a698a86ffeb0bbde8a6c97465905bcb0fb5f9bfc1856aec522161f1df'),
        ('A03-P2-R11-crash-cuts-coordinator-decision.md', None),
        ('A03-runtime-recovery.md', None), ('A03-independent-review.md', None)):
        path = 'docs/tasks/' + name
        raw = git('show', WORKFLOW + ':' + path)
        assert expected is None or sha(raw) == expected
        write(OUT / 'inputs' / name, raw)
        inputs.append({'workflow': WORKFLOW, 'path': path, 'bytes': len(raw), 'sha256': sha(raw)})
    sources = []
    for path in ('src/annotation/runtime/storage/__init__.py', 'src/annotation/runtime/storage/native.py',
        'src/annotation/runtime/recovery/__init__.py', 'src/annotation/delivery/mock/persistent.py',
        'src/annotation/delivery/planner/__init__.py', 'src/annotation/contracts/a03_native/__init__.py',
        'src/annotation/contracts/a03_native/_closure.py', 'src/annotation/contracts/a03_native/data/schemas/exchange.json',
        'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json'):
        raw, actual = git('show', BASE + ':' + path), (ROOT / path).read_bytes()
        write(OUT / 'inputs/base' / path, raw)
        sources.append({'base': BASE, 'path': path, 'bytes': len(raw), 'raw_Git_sha256': sha(raw),
            'worktree_bytes': len(actual), 'worktree_sha256': sha(actual), 'raw_bytes_identical': raw == actual})
    tree = git('ls-tree', '-r', BASE)
    write(OUT / 'inputs.json', {'base': BASE, 'workflow': WORKFLOW, 'files': inputs, 'sources': sources,
        'base_entries': len(tree.splitlines()), 'base_tree_sha256': sha(tree)})
    drivers = []
    paths = [ROOT / 'tests/test_a03_p2_r12_inconclusive_readback.py'] + list(Path(__file__).parent.glob('*.py'))
    for path in paths:
        raw = path.read_bytes()
        text = raw.decode('utf-8', errors='strict')
        compile(text, str(path), 'exec')
        ast.parse(text)
        drivers.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)})
    write(OUT / 'driver-preregistered.json', {'utf8_strict_compile_checked': True, 'drivers': drivers,
        'functional_calls': 0, 'scope': 'Static prerequisite stop only; no U1-U5 functional driver is run.',
        'expected_static_finding': 'Legacy UNKNOWN diagnostic POST fields conflict with current native POST schema.'})
    print(json.dumps({'authority_files': len(inputs), 'source_files': len(sources), 'base_entries': len(tree.splitlines()), 'product_calls': 0}))
