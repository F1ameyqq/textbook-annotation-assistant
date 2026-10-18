"""Bounded processes and a thin adapter to the accepted T1 capture module."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
VIEW = HERE / 'runtime-view/src'
OLD = ROOT / 'examples/a03/P2-R12-R2-issue-ownership'
TEST = ROOT / 'tests/test_a03_t2_history.py'
BOUNDARIES = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)


def configure():
    sys.path[:] = [p for p in sys.path if Path(p or '.').resolve() != ROOT / 'src']
    sys.path.insert(0, str(VIEW))


def frozen():
    path = HERE / 'inputs.json'
    for name, expected in json.loads(path.read_bytes())['files'].items():
        assert sha((ROOT / name).read_bytes()) == expected, 'frozen bytes changed: ' + name
    return sha(path.read_bytes())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


accepted = load('t2_accepted_capture', ROOT / 'examples/a03/T1-capture/capture.py')


def capture(case, stage, **unused):
    return accepted.capture(case, stage, boundary=BOUNDARIES.get(str(case.resolve())))


def inherited():
    # Import the fixed original functions, never execute their __main__ or suite.
    module = load('t2_inherited_r12_r2', ROOT / 'tests/test_a03_p2_r12_r2_issue_ownership.py')
    configure()  # The old module adds ROOT/src before any product import.
    module.capture = capture
    return module


def process(folder, argv, timeout):
    folder.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(VIEW), str(HERE), str(OLD))),
        PYTHONDONTWRITEBYTECODE='1', A03_T2_IMPORT_AUDIT=str(folder.parents[1] / 'import-processes'))
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': timeout,
        'expected_exit': 0, 'input_sha256': frozen(), 'source_index': str(HERE / 'inputs.json'),
        'PYTHONPATH': env['PYTHONPATH'], 'retries': 0,
        'script_sha256': {arg: sha(Path(arg).read_bytes()) for arg in argv if arg.endswith('.py')}})
    for arg in argv:
        if arg.endswith('.py'):
            write(folder / ('source-' + Path(arg).name), Path(arg).read_bytes())
    with (folder / 'stdout.txt').open('xb') as stdout, (folder / 'stderr.txt').open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        write(folder / 'started.json', {'pid': child.pid, 'parent_pid': os.getpid(), 'started_at_ns': time.time_ns()})
        timed_out = False
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            code = child.wait(timeout=5)
    write(folder / 'completed.json', {'pid': child.pid, 'exit_code': code, 'timeout': timed_out,
        'alive': child.poll() is None, 'ended_at_ns': time.time_ns(),
        'stdout_sha256': sha((folder / 'stdout.txt').read_bytes()), 'stderr_sha256': sha((folder / 'stderr.txt').read_bytes())})
    assert code == 0 and not timed_out, 'first process failure: ' + str(folder / 'stderr.txt')


def group(root):
    deadline = time.monotonic() + 85
    for phase in ('execute', 'recover', 'report'):
        remaining = deadline - time.monotonic()
        assert remaining > 0, 'H1 parent budget exhausted before next phase'
        process(root / 'processes' / ('H1-' + phase),
            [sys.executable, '-X', 'utf8', '-B', str(TEST), phase, str(root)], min(45, remaining))
    write(root / 'H1-result.json', {'status': 'REVIEW', 'author_assertions': 'PASS', 'runs': 1,
        'dispatches': 1, 'reconcile_calls': 1, 'report_calls': 1, 'case': str(root / 'cases/H1')})


if __name__ == '__main__':
    group(Path(sys.argv[1]).resolve())
