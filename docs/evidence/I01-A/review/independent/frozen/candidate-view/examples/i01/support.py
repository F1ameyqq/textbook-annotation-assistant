"""I01 recording and immutable Git export; no product authority lives here."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

BASE = 'a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8'
PRODUCT = '6097a06de937fee8876feccedf46920510850b83'
WORKFLOW = '8b0fe38b3b520f0ff80801c98121acd3f335a1fc'
ROOT = Path(os.environ.get('I01_PROJECT', Path(__file__).resolve().parents[2])).resolve()
EVIDENCE = ROOT / 'docs/evidence/I01-A/execution'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def load(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False,
        sort_keys=True, indent=2, allow_nan=False, default=str) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def git(args, data=None):
    argv = ['git', '-c', 'core.longpaths=true', '-C', str(ROOT), *args]
    process = subprocess.Popen(argv, stdin=subprocess.PIPE if data is not None else None,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate(data, timeout=60)
    assert process.returncode == 0, (argv, err.decode('utf-8', 'replace'))
    return out


def export(commit, prefixes, destination):
    paths = git(['ls-tree', '-r', '--name-only', commit, *prefixes]).decode('utf-8').splitlines()
    packed = git(['cat-file', '--batch'], ''.join(commit + ':' + p + '\n' for p in paths).encode('utf-8'))
    offset, rows = 0, []
    for path in paths:
        end = packed.index(b'\n', offset)
        blob, kind, length = packed[offset:end].decode().split()
        assert kind == 'blob'
        length = int(length)
        offset = end + 1
        raw = packed[offset:offset + length]
        offset += length + 1
        write(destination / path, raw)
        rows.append(dict(path=path, bytes=length, sha256=sha(raw), git_blob=blob, source_commit=commit))
    assert offset == len(packed)
    return rows


def imports():
    import sys
    return {name: dict(path=str(Path(m.__file__).resolve()), sha256=sha(Path(m.__file__).read_bytes()))
        for name, m in sorted(sys.modules.items())
        if name.startswith('annotation') and getattr(m, '__file__', None)}


def run_child(folder, argv, *, env, timeout):
    folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'invocation.json', dict(argv=argv, cwd=str(ROOT), parent_pid=os.getpid(),
        timeout_seconds=timeout, PYTHONPATH=env.get('PYTHONPATH'), started_at_ns=time.time_ns()))
    started, timed_out = time.monotonic(), False
    with (folder / 'stdout.txt').open('xb') as out, (folder / 'stderr.txt').open('xb') as err:
        process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=out, stderr=err)
        write(folder / 'started.json', dict(pid=process.pid, parent_pid=os.getpid()))
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            # Windows: terminate the owned process tree, including bounded readers.
            killed = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
            write(folder / 'termination.json', dict(argv=['taskkill','/PID',str(process.pid),'/T','/F'],
                exit_code=killed.returncode, stdout=killed.stdout.decode('utf-8','replace'),
                stderr=killed.stderr.decode('utf-8','replace')))
            code = process.wait(timeout=5)
    result = dict(pid=process.pid, exit_code=code, timeout=timed_out, waited=True,
        alive=process.poll() is None, wall_seconds=time.monotonic()-started)
    write(folder / 'completed.json', result)
    return result
