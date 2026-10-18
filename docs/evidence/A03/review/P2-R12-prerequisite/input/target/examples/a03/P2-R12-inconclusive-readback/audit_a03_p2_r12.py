"""Preregistered static-only process; zero product imports, no business execution."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R12-inconclusive-readback'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


if __name__ == '__main__':
    folder = OUT / 'runs/static-prerequisite'
    folder.mkdir(parents=True, exist_ok=False)
    argv = [sys.executable, '-X', 'utf8', '-B', 'tests/test_a03_p2_r12_inconclusive_readback.py']
    source_index = [{'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
        for path in sorted((ROOT / 'src/annotation').rglob('*')) if path.is_file() and path.suffix in ('.py', '.json')]
    write(folder / 'product-source-index.json', source_index)
    write(folder / 'script-snapshot.py', (ROOT / argv[-1]).read_bytes())
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 45,
        'script_sha256': sha((ROOT / argv[-1]).read_bytes()), 'inputs_sha256': sha((OUT / 'inputs.json').read_bytes()),
        'source_index_sha256': sha((folder / 'product-source-index.json').read_bytes()), 'scope': 'STATIC_ONLY_NO_PRODUCT_CALLS'})
    with (folder / 'stdout.txt').open('xb') as stdout, (folder / 'stderr.txt').open('xb') as stderr:
        process = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr)
        write(folder / 'started.json', {'pid': process.pid, 'parent_pid': os.getpid(), 'started_at_ns': time.time_ns()})
        timed_out = False
        try:
            code = process.wait(timeout=45)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait(timeout=5)
    completed = {'pid': process.pid, 'exit_code': code, 'timed_out': timed_out, 'alive': process.poll() is None,
        'ended_at_ns': time.time_ns(), 'stdout_sha256': sha((folder / 'stdout.txt').read_bytes()),
        'stderr_sha256': sha((folder / 'stderr.txt').read_bytes())}
    write(folder / 'completed.json', completed)
    print(json.dumps(completed))
    raise SystemExit(code)
