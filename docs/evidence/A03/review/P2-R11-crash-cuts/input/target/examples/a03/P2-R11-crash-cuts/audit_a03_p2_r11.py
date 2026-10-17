"""Preregistered R11 process runner with exact inputs, source and raw output."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'docs/evidence/A03/execution/P2-R11-crash-cuts'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def run(label, argv):
    folder = EVIDENCE / 'runs' / label
    folder.mkdir(parents=True, exist_ok=False)
    timeout = int(os.environ.get('A03_P2_R11_TIMEOUT_SECONDS', '90'))
    assert 0 < timeout <= 90
    scripts = {}
    for item in list(argv) + ['tests/test_a03_r8_r3_post_hold.py', 'tests/test_a03_p2_r10_owner_fencing.py']:
        path = ROOT / item
        if path.is_file():
            raw = path.read_bytes()
            scripts[item] = sha(raw)
            snapshot = folder / 'script-snapshots' / path.name
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            with snapshot.open('xb') as stream:
                stream.write(raw)
    sources = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
        for p in sorted((ROOT / 'src/annotation').rglob('*')) if p.is_file() and p.suffix in ('.py', '.json')]
    write(folder / 'product-source-index.json', sources)
    fixture_index = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
        for p in sorted((ROOT / 'tests/fixtures/a03/P2-R8-R3-post-hold').rglob('*')) if p.is_file()]
    write(folder / 'fixture-index.json', fixture_index)
    package = ROOT / 'src/annotation/contracts/a03_native'
    profile = json.loads((package / 'data/profile.json').read_bytes())
    snapshot_files = list(package.rglob('*.json')) + list(package.glob('*.py'))
    snapshot_files += [ROOT / 'src/annotation' / name[len('@annotation/'):] for name, _ in profile['implementation_pins'] if name.startswith('@annotation/')]
    for path in set(snapshot_files):
        target = folder / 'product-snapshot' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(path.read_bytes())
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': timeout,
        'script_pins': scripts, 'input_index_sha256': sha((EVIDENCE / 'inputs.json').read_bytes()),
        'product_source_index_sha256': sha((folder / 'product-source-index.json').read_bytes()),
        'fixture_index_sha256': sha((folder / 'fixture-index.json').read_bytes()),
        'runner_sha256': sha(Path(__file__).read_bytes()), 'registered_at_ns': time.time_ns()})
    environment = os.environ.copy()
    environment['PYTHONPATH'] = str(ROOT / 'src')
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    with (folder / 'stdout.txt').open('xb') as stdout, (folder / 'stderr.txt').open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr)
        write(folder / 'started.json', {'pid': child.pid, 'parent_pid': os.getpid(), 'started_at_ns': time.time_ns()})
        timed_out = False
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            code = child.wait(timeout=10)
    result = {'pid': child.pid, 'exit_code': code, 'timed_out': timed_out, 'alive': child.poll() is None,
        'ended_at_ns': time.time_ns(), 'stdout_sha256': sha((folder / 'stdout.txt').read_bytes()),
        'stderr_sha256': sha((folder / 'stderr.txt').read_bytes())}
    write(folder / 'completed.json', result)
    print(json.dumps(result))
    return code


if __name__ == '__main__':
    if sys.argv[1] != 'run':
        raise SystemExit('only preregistered run is supported')
    raise SystemExit(run(sys.argv[2], sys.argv[3:]))
