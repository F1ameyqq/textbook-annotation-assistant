"""Freeze R10 exact authority, source and fixed-input identities; no product calls."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R10-owner-fencing'
BASE = 'bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39'
WORKFLOW = '2d8357e040ee5c54494882bc175baf2579d07aed'


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
        ('A03-P2-R10-owner-fencing-validation.md', '5314105f2b1c8b773c4ceda21ed82904ea210258ecbb2406ce6cd29490c1510a'),
        ('A03-P2-R9-R1-owner-lifecycle-coordinator-decision.md', None),
        ('A03-runtime-recovery.md', None), ('A03-independent-review.md', None)):
        raw = git('show', WORKFLOW + ':docs/tasks/' + name)
        assert expected is None or sha(raw) == expected, name
        write(OUT / 'inputs' / name, raw)
        pins.append({'workflow': WORKFLOW, 'path': 'docs/tasks/' + name, 'bytes': len(raw), 'sha256': sha(raw)})
    references = []
    names = ['tests/test_a03_r8_r3_post_hold.py', 'src/annotation/runtime/storage/native.py',
        'src/annotation/runtime/recovery/__init__.py', 'src/annotation/runtime/recovery/native_quality.py',
        'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json']
    names += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / 'tests/fixtures/a03/P2-R8-R3-post-hold').rglob('*')) if p.is_file()]
    for name in names:
        raw = git('show', BASE + ':' + name)
        assert (ROOT / name).read_bytes() == raw, name
        references.append({'base': BASE, 'path': name, 'bytes': len(raw), 'sha256': sha(raw)})
    tree = git('ls-tree', '-r', BASE)
    write(OUT / 'inputs.json', {'base': BASE, 'workflow': WORKFLOW, 'files': pins,
        'unchanged_references_and_copied_fixture_sources': references,
        'base_entries': len(tree.splitlines()), 'base_tree_sha256': sha(tree)})
    print(json.dumps({'pins': len(pins), 'references': len(references), 'base_entries': len(tree.splitlines()), 'product_calls': 0}))
