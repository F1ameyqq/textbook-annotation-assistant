"""Independent static raw-object materialization; no product imports."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HOME = Path(__file__).resolve().parent
REPO = HOME / 'c'
SOURCE = Path('D:/1800')
TARGET = '699f748a124162b3118e3996c03757725daac363'
CANDIDATE = 'f111eb609d065a2506da52007c3b283928d537aa'
BASE = '1330047dd29890dea0e433ff01b991f615bf78f4'
TOOL = 'examples/a03/T1-capture/capture.py'
INPUT = 'examples/a03/T2-history/inputs.json'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)

def proc(name, args, cwd=SOURCE, data=None):
    folder = HOME / 'static-processes' / name
    folder.mkdir(parents=True, exist_ok=False)
    argv = ['git', '-c', 'core.longpaths=true'] + args
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(cwd), 'timeout_seconds': 45,
          'expected_exit': 0, 'script_sha256': sha(Path(__file__).read_bytes()), 'stdin_sha256': sha(data or b'')})
    if data is not None:
        write(folder / 'stdin.bin', data)
    with (folder / 'stdout.bin').open('xb') as stdout, (folder / 'stderr.bin').open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr)
        write(folder / 'started.json', {'pid': child.pid, 'parent_pid': os.getpid(), 'started_at_ns': time.time_ns()})
        timed_out = False
        try:
            child.communicate(data, timeout=45)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            child.communicate(timeout=5)
    write(folder / 'completed.json', {'pid': child.pid, 'exit_code': child.returncode, 'timeout': timed_out,
          'alive': child.poll() is None, 'ended_at_ns': time.time_ns(),
          'stdout_sha256': sha((folder / 'stdout.bin').read_bytes()), 'stderr_sha256': sha((folder / 'stderr.bin').read_bytes())})
    assert child.returncode == 0 and not timed_out, name
    return (folder / 'stdout.bin').read_bytes()

def main():
    REPO.mkdir(exist_ok=False)
    common = proc('common-dir', ['rev-parse', '--git-common-dir']).decode('utf-8').strip()
    object_dir = (SOURCE / common / 'objects').resolve()
    assert object_dir.is_dir()
    proc('own-init', ['init', '--quiet', str(REPO)])
    write(REPO / '.git/objects/info/alternates', (object_dir.as_posix() + '\n').encode('utf-8'))
    proc('own-detach', ['update-ref', '--no-deref', 'HEAD', TARGET], cwd=REPO)
    proc('own-head', ['rev-parse', 'HEAD'], cwd=REPO)
    proc('product-unchanged', ['diff', '--exit-code', BASE, TARGET, '--', 'src', 'pyproject.toml', 'requirements.txt', 'requirements-dev.txt'])
    proc('frozen-execution-unchanged', ['diff', '--exit-code', CANDIDATE, TARGET, '--', 'src', 'examples/a03/T2-history', TOOL, 'tests/test_a03_t2_history.py'])
    proc('four-file-repair', ['diff', '6affc61d2ab0b1f0d96bb2497c5ae969ebaf1df2', BASE, '--',
         'src/annotation/runtime/storage/__init__.py', 'src/annotation/contracts/recovery.py',
         'src/annotation/contracts/a03_native/__init__.py', 'src/annotation/contracts/validation.py',
         'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json'])
    tree_raw = proc('target-tree', ['ls-tree', '-r', '-z', TARGET])
    tree = {}
    for item in tree_raw.rstrip(b'\0').split(b'\0'):
        meta, path = item.split(b'\t', 1)
        mode, kind, oid = meta.decode('ascii').split()
        if kind == 'blob':
            tree[path.decode('utf-8')] = oid
    raw_input = proc('input', ['show', TARGET + ':' + INPUT])
    identity = json.loads(raw_input)
    expected = identity['files']
    assert len(expected) == 263
    selected = set(expected) | {INPUT, 'docs/tasks/A03-T2-execution-report.md',
            'docs/evidence/A03/T2/execution/manifest.json'}
    selected |= {p for p in tree if p.startswith('src/annotation/')}
    selected |= {p for p in tree if p.startswith('docs/evidence/A03/T2/execution/validation/author-01/')}
    selected |= {p for p in tree if p.startswith('docs/evidence/A03/T2/execution/sealing/')}
    selected |= {p for p in ('pyproject.toml', 'requirements.txt', 'requirements-dev.txt') if p in tree}
    paths = sorted(selected)
    stream = proc('selected-blobs', ['cat-file', '--batch'], data=''.join(TARGET + ':' + p + '\n' for p in paths).encode('utf-8'))
    offset = 0
    records = []
    for path in paths:
        end = stream.index(b'\n', offset)
        oid, kind, size_text = stream[offset:end].decode('ascii').split()
        assert oid == tree[path] and kind == 'blob'
        size = int(size_text)
        raw = stream[end + 1:end + 1 + size]
        assert len(raw) == size and stream[end + 1 + size:end + 2 + size] == b'\n'
        offset = end + 2 + size
        actual, representation = raw, 'RAW_GIT_BLOB'
        if path in expected and sha(raw) != expected[path]:
            # Reconstruct only the explicitly frozen execution representation, never change pins.
            crlf = raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
            assert sha(crlf) == expected[path], 'unreconstructible frozen input: ' + path
            actual, representation = crlf, 'EXPLICIT_FROZEN_CRLF_SHA256'
        if path in expected:
            assert sha(actual) == expected[path], path
        write(REPO / path, actual)
        records.append({'path': path, 'git_blob': oid, 'raw_sha256': sha(raw), 'raw_bytes': len(raw),
                        'execution_sha256': sha(actual), 'execution_bytes': len(actual), 'representation': representation,
                        'frozen_input': path in expected})
    assert offset == len(stream)
    native = REPO / 'examples/a03/T2-history/runtime-view/src/annotation/contracts/a03_native'
    view = REPO / 'examples/a03/T2-history/runtime-view/src/annotation'
    profile = json.loads((native / 'data/profile.json').read_bytes())
    pin_records = []
    for path, wanted in profile['implementation_pins']:
        loc = view / path[len('@annotation/'):] if path.startswith('@annotation/') else native / path
        actual = sha(loc.read_bytes())
        assert actual == wanted, path
        pin_records.append({'path': loc.relative_to(REPO).as_posix(), 'expected': wanted, 'actual': actual})
    adoption = json.loads((native / 'data/adoption.json').read_bytes())
    assert sha((native / 'data/profile.json').read_bytes()) == adoption['profile_sha256']
    for path, wanted in profile['schema_pins']:
        assert sha((native / 'data' / path).read_bytes()) == wanted
    sources = []
    for src in sorted((REPO / 'src/annotation').rglob('*')):
        if src.is_file():
            rel = src.relative_to(REPO / 'src/annotation')
            actual = view / rel
            assert src.read_bytes() == actual.read_bytes(), str(rel)
            sources.append(rel.as_posix())
    assert sha((REPO / TOOL).read_bytes()) == '3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b'
    manifest = REPO / 'docs/evidence/A03/T2/execution/manifest.json'
    assert sha(manifest.read_bytes()) == 'a64c32a7607d86eab259540e31e061c200c4db4e10a13db4d62b234fa60cf08e'
    compiled = []
    for path in expected:
        if path.endswith('.py'):
            compile((REPO / path).read_bytes().decode('utf-8', 'strict'), path, 'exec')
            compiled.append(path)
    result = {'target': TARGET, 'candidate': CANDIDATE, 'product_baseline': BASE, 'object_source': str(object_dir),
              'own_git_head': TARGET, 'input_sha256': sha(raw_input), 'files': records,
              'frozen_files': len(expected), 'compiled_without_execution': compiled,
              'implementation_pins': pin_records, 'schema_pins': profile['schema_pins'],
              'adoption_profile_sha256': adoption['profile_sha256'], 'raw_product_view_equal': sources,
              'product_imports_or_business_calls': 0, 'python': sys.version, 'executable': sys.executable}
    write(HOME / 'materialization.json', result)
    print(json.dumps({'status': 'STATIC_MATERIALIZATION_OK', 'frozen_files': len(expected),
          'raw_source_files': len(sources), 'pins': len(pin_records), 'compiled': len(compiled),
          'representations': [r['path'] for r in records if r['representation'] != 'RAW_GIT_BLOB'],
          'input_sha256': sha(raw_input)}))

if __name__ == '__main__':
    main()
