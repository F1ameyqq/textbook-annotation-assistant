"""Create-only process and retained-copy evidence for the six bounded scenes."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'docs/evidence/A03/execution/P2-R12-R1-unknown-projection'
TEST = ROOT / 'tests/test_a03_p2_r12_r1_unknown_projection.py'
BASE = '394fe51f5ed14c5ed312073a20faac0f5cbb9990'
GROUPS = ('L1', 'U1', 'U2', 'U3', 'U4', 'U5')
FAULTS = {'L1': ('partial', None, None, 'CONFLICT'),
          'U1': ('partial', None, None, 'CONFLICT'),
          'U2': (None, 'unavailable', 'duplicate', 'CONFLICT'),
          'U3': (None, 'unavailable', 'contradictory', 'INDETERMINATE'),
          'U4': (None, 'unavailable', 'truncated', 'INDETERMINATE'),
          'U5': (None, 'unavailable', 'unavailable', 'INDETERMINATE')}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, sort_keys=True,
        indent=2, allow_nan=False) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)


def index(paths):
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted(set(paths)) if p.is_file()}


def frozen_files():
    return [*ROOT.joinpath('src').rglob('*'), *HERE.rglob('*'), TEST,
        ROOT / 'tests/test_a03_r8_r3_post_hold.py',
        *ROOT.joinpath('tests/fixtures/a03/P2-R8-R3-post-hold').rglob('*')]


def check_frozen():
    frozen = json.loads((HERE / 'inputs.json').read_bytes())['files']
    for name, expected in frozen.items():
        assert sha((ROOT / name).read_bytes()) == expected, 'frozen bytes changed: ' + name
    return sha((HERE / 'inputs.json').read_bytes())


def sql_copy(path):
    before = sha(path.read_bytes())
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    db.row_factory = sqlite3.Row
    try:
        assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows = {name: [dict(r) for r in db.execute('SELECT * FROM "' + name.replace('"', '""') + '" ORDER BY rowid')]
                for name in tables}
        result = {'application_id': db.execute('PRAGMA application_id').fetchone()[0],
                  'user_version': db.execute('PRAGMA user_version').fetchone()[0], 'tables': rows}
    finally:
        db.close()
    assert sha(path.read_bytes()) == before, 'immutable copy changed'
    return result


def capture(case, stage, *, store=None, keeper=None):
    """Sequential raw copies, never a claim of cross-database atomicity."""
    folder = case / 'captures' / stage
    folder.mkdir(parents=True, exist_ok=False)
    records, values = [], {}
    for kind, source in (('runtime', case / 'runtime/runtime.sqlite3'), ('target', case / 'target/target.sqlite3')):
        record = {'kind': kind, 'source': str(source), 'writer_process_pid': os.getpid(),
            'writer_in_business_call': False, 'keeper_alive': bool(keeper and keeper.thread.is_alive()),
            'captured_at_ns': time.time_ns(), 'sequential_non_atomic': True}
        if not source.exists():
            record['missing'] = True
            records.append(record)
            continue
        sidecars = {suffix: sha(Path(str(source) + suffix).read_bytes())
            for suffix in ('-journal', '-wal', '-shm') if Path(str(source) + suffix).exists()}
        assert not sidecars, 'active SQLite sidecar at raw capture: ' + str(source)
        raw = source.read_bytes()
        destination = folder / (kind + '.sqlite3')
        write(destination, raw)
        record.update(sha256=sha(raw), size=len(raw), retained=destination.relative_to(ROOT).as_posix(),
            source_sha256_after_copy=sha(source.read_bytes()), sidecars=sidecars)
        assert record['sha256'] == record['source_sha256_after_copy'], 'source changed during copy'
        values[kind] = sql_copy(destination)
        assert sha(source.read_bytes()) == record['sha256'], 'source changed during immutable SQL audit'
        records.append(record)
    write(folder / 'capture.json', {'stage': stage, 'process_pid': os.getpid(), 'records': records,
        'SQL_reads_only_retained_immutable_copies': True, 'cross_database_atomic': False})
    write(folder / 'SQL.json', values)
    return values


def imports():
    result = {}
    for name, module in sorted(sys.modules.items()):
        source = getattr(module, '__file__', None)
        if source and (name.startswith('annotation') or 'r12' in name or name == 'r8_fixed_helper'):
            path = Path(source).resolve()
            assert path.is_relative_to(ROOT), 'foreign product/helper import: ' + name
            result[name] = {'path': str(path), 'sha256': sha(path.read_bytes())}
    return result


def process(folder, argv, timeout):
    folder.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(ROOT / 'src'), str(HERE))), PYTHONDONTWRITEBYTECODE='1',
        A03_R12_R1_IMPORT_AUDIT=str(folder.parents[1] / 'import-processes'))
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': timeout,
        'input_sha256': check_frozen(), 'source_index': str(HERE / 'inputs.json'), 'retries': 0,
        'script_sha256': {str(Path(arg)): sha(Path(arg).read_bytes()) for arg in argv if arg.endswith('.py')},
        'expected_exit': 0, 'PYTHONPATH': env['PYTHONPATH']})
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


def group(root, name):
    for phase in (('execute',) if name == 'L1' else ('execute', 'recover')):
        process(root / 'processes' / (name + '-' + phase),
            [sys.executable, '-X', 'utf8', '-B', str(TEST), name, phase, str(root)], 45)
    write(root / (name + '-result.json'), {'group': name, 'status': 'REVIEW', 'functional_assertions': 'PASS',
        'runs': 1, 'expected': FAULTS[name], 'case': str(root / 'cases' / name)})


if __name__ == '__main__':
    group(Path(sys.argv[2]).resolve(), sys.argv[1])
