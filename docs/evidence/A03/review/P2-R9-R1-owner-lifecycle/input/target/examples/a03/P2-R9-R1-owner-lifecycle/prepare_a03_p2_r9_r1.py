"""Freeze R9-R1 exact authority, source and fixed-input identities; no product calls."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle'
BASE = 'c83f956c5c29c64ab10735ba11c153201d3f3f4b'
WORKFLOW = '2aabd591695e73ecd4024c95e06fe0b71a2a9267'


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
    # Product edits are authorized; verify all other old paths during sealing.
    attributes = b'* -text whitespace=trailing-space,space-before-tab,cr-at-eol\n**/stdout.txt -whitespace\n**/stderr.txt -whitespace\n'
    write(OUT / '.gitattributes', attributes)
    write(Path(__file__).parent / '.gitattributes', attributes)
    pins = []
    for name, expected in (
        ('A03-P2-R9-R1-owner-lifecycle-repair.md', 'eb375839b834126f8a72be6a60a21d45b00fad83925de0e2d71cd6b0abe80191'),
        ('A03-P2-R9-failure-coordinator-decision.md', None),
        ('A03-P2-R9-failure-review-report.md', '8c8302ff0ca1e4adb69d4c22de4131ca8ba713494a485f02d7fd89d2448e3a0e'),
        ('A03-P2-R9-minimal-demos.md', None)):
        raw = git('show', WORKFLOW + ':docs/tasks/' + name)
        assert expected is None or sha(raw) == expected, name
        write(OUT / 'inputs' / name, raw)
        pins.append({'workflow': WORKFLOW, 'path': 'docs/tasks/' + name, 'bytes': len(raw), 'sha256': sha(raw)})
    references = []
    names = ['tests/test_a03_p2_r9_minimal_demos.py', 'tests/test_a03_r8_r3_post_hold.py', 'src/annotation/runtime/storage/native.py',
        'src/annotation/runtime/recovery/__init__.py', 'src/annotation/runtime/recovery/native_quality.py',
        'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json']
    names += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / 'tests/fixtures/a03/P2-R8-R3-post-hold').rglob('*')) if p.is_file()]
    for name in names:
        raw = git('show', BASE + ':' + name)
        if name not in ('src/annotation/runtime/recovery/__init__.py', 'src/annotation/runtime/recovery/native_quality.py', 'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json'):
            assert (ROOT / name).read_bytes() == raw, name
        references.append({'base': BASE, 'path': name, 'bytes': len(raw), 'sha256': sha(raw)})
    tree = git('ls-tree', '-r', BASE)
    write(OUT / 'inputs.json', {'base': BASE, 'workflow': WORKFLOW, 'files': pins,
        'unchanged_references_and_copied_fixture_sources': references,
        'base_entries': len(tree.splitlines()), 'base_tree_sha256': sha(tree)})
    print(json.dumps({'pins': len(pins), 'references': len(references), 'base_entries': len(tree.splitlines()), 'product_calls': 0}))
