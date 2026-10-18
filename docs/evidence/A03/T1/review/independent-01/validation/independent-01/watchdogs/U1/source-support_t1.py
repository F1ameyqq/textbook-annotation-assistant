"""Create-only bounded process evidence; no retries or business rules."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from capture import sha, write

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'runtime-view/src'
OUT = ROOT / 'docs/evidence/A03/T1/execution'
TEST = ROOT / 'tests/test_a03_t1_capture.py'
BASE = '1330047dd29890dea0e433ff01b991f615bf78f4'
WORKFLOW = 'f7084b2e8f2e9a1fcf758f9cba56ec9c9fb1f304'
GROUPS = ('L1', 'U1', 'U2', 'U3', 'U4', 'U5')
FAULTS = {'L1': ('partial', None, None, 'CONFLICT'),
          'U1': ('partial', None, None, 'CONFLICT'),
          'U2': (None, 'unavailable', 'duplicate', 'CONFLICT'),
          'U3': (None, 'unavailable', 'contradictory', 'INDETERMINATE'),
          'U4': (None, 'unavailable', 'truncated', 'INDETERMINATE'),
          'U5': (None, 'unavailable', 'unavailable', 'INDETERMINATE')}


def check_frozen():
    raw = (HERE / 'inputs.json').read_bytes()
    for name, entry in json.loads(raw)['files'].items():
        assert sha((ROOT / name).read_bytes()) == entry['execution_sha256'], 'changed frozen bytes: ' + name
    return sha(raw)


def imports():
    result = {}
    for name, module in sorted(sys.modules.items()):
        source = getattr(module, '__file__', None)
        if source and (name.startswith('annotation') or name in
                ('__main__', 'capture', 'support_t1', 'support', 'r12_fixed_helper', 'r8_fixed_helper', 'sitecustomize')):
            path = Path(source).resolve()
            assert path.is_relative_to(ROOT), 'foreign import: ' + name
            result[name] = {'path': str(path), 'sha256': sha(path.read_bytes())}
    return result


def process(folder, argv, timeout, *, stdin=None, frozen=True):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(SOURCE), str(HERE))),
        PYTHONDONTWRITEBYTECODE='1', A03_T1_IMPORT_AUDIT=str(folder / 'import-processes'))
    if Path(argv[0]).stem.lower() == 'git':
        assert argv[1:3] == ['-c', 'core.longpaths=true']
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': timeout,
        'expected_exit': 0, 'retries': 0, 'input_sha256': check_frozen() if frozen else None,
        'stdin_sha256': sha(stdin) if stdin is not None else None,
        'script_sha256': {arg: sha(Path(arg).read_bytes()) for arg in argv if arg.endswith('.py')},
        'PYTHONPATH': env['PYTHONPATH']})
    for arg in argv:
        if arg.endswith('.py'):
            write(folder / ('source-' + Path(arg).name), Path(arg).read_bytes())
    if stdin is not None:
        write(folder / 'stdin.bin', stdin)
    started = time.time_ns()
    with (folder / 'stdout.bin').open('xb') as stdout, (folder / 'stderr.bin').open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdin=subprocess.PIPE if stdin is not None else None,
                                 stdout=stdout, stderr=stderr)
        write(folder / 'started.json', {'pid': child.pid, 'parent_pid': os.getpid(), 'at_ns': started})
        timed_out = False
        try:
            child.communicate(input=stdin, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            child.communicate(timeout=5)
    write(folder / 'completed.json', {'pid': child.pid, 'exit_code': child.returncode,
        'timeout': timed_out, 'alive': child.poll() is None, 'wait_reaped': True,
        'ended_at_ns': time.time_ns(), 'stdout_sha256': sha((folder / 'stdout.bin').read_bytes()),
        'stderr_sha256': sha((folder / 'stderr.bin').read_bytes())})
    assert child.returncode == 0 and not timed_out, 'first process failure: ' + str(folder / 'stderr.bin')
    return (folder / 'stdout.bin').read_bytes()


def group(root, name):
    for phase in (('execute',) if name == 'L1' else ('execute', 'recover')):
        process(root / 'processes' / (name + '-' + phase),
            [sys.executable, '-X', 'utf8', '-B', str(TEST), name, phase, str(root)], 45)
    write(root / (name + '-result.json'), {'group': name, 'status': 'REVIEW', 'author_assertions': 'PASS',
        'runs': 1, 'dispatches': 1, 'reconcile_calls': 0 if name == 'L1' else 1,
        'max_attempts': 0 if name == 'L1' else 1, 'expected': FAULTS[name]})


if __name__ == '__main__':
    group(Path(sys.argv[2]).resolve(), sys.argv[1])
