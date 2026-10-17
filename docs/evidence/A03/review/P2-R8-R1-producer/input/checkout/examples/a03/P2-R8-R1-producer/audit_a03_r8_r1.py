"""R8 local evidence runner. No historical example module is imported."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'docs/evidence/A03/execution/P2-R8-R1-producer'
BASE = 'fa6edeb7e9dd0c9502781747e5fce012931d9441'
WORKFLOW = 'b9889efd29baa364bdd0ce9e356a8cde7054f8d9'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT)


def freeze():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    inventory = json.loads(git('show', WORKFLOW + ':docs/evidence/coordinator/heartbeat-20261017-1329/R8-input-pins.json'))
    checks = []
    for row in inventory['files']:
        raw = git('show', row['commit'] + ':' + row['path'])
        if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
            raise RuntimeError('input pin mismatch: ' + row['path'])
        checks.append(row)
    task = git('show', WORKFLOW + ':docs/tasks/A03-P2-R8-native-bridge-implementation.md')
    if sha(task) != 'b7dbf94ff06d8ba272b1bd20bf61afbe09fa1dd99c501dcb70f865ab36737721':
        raise RuntimeError('task pin mismatch')
    write(EVIDENCE / 'inputs.json', {'base': BASE, 'workflow': WORKFLOW, 'task_sha256': sha(task), 'files': checks})
    entries = []
    for line in git('ls-tree', '-r', BASE).decode('utf-8').splitlines():
        metadata, path = line.split('\t', 1)
        mode, kind, blob = metadata.split()
        entries.append({'path': path, 'mode': mode, 'type': kind, 'blob': blob})
    write(EVIDENCE / 'old-tree.json', entries)
    print(json.dumps({'input_files': len(checks), 'old_entries': len(entries), 'base': BASE}))


def run(name, argv, env=None):
    folder = EVIDENCE / 'runs' / name
    folder.mkdir(parents=True, exist_ok=False)
    script = Path(argv[-1]) if argv else None
    scripts = {}
    for item in argv:
        path = ROOT / item
        if path.is_file():
            scripts[item] = sha(path.read_bytes())
            snapshot = folder / 'script-snapshots' / path.name
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            with snapshot.open('xb') as stream:
                stream.write(path.read_bytes())
    source_index = []
    for path in sorted((ROOT / 'src/annotation').rglob('*')):
        if path.is_file() and path.suffix in ('.py', '.json'):
            source_index.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())})
    write(folder / 'product-source-index.json', source_index)
    fixture_index = []
    for path in sorted((ROOT / 'tests/fixtures/a03/P2-R8-R1-producer').rglob('*')):
        if path.is_file():
            fixture_index.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())})
    write(folder / 'fixture-index.json', fixture_index)
    native = ROOT / 'src/annotation/contracts/a03_native'
    if (native / 'data/profile.json').is_file():
        profile = json.loads((native / 'data/profile.json').read_bytes())
        snapshot_files = list(native.rglob('*.json')) + list(native.glob('*.py'))
        snapshot_files += [ROOT / 'src/annotation' / name[len('@annotation/'):] for name, _ in profile['implementation_pins'] if name.startswith('@annotation/')]
        for path in set(snapshot_files):
            target = folder / 'product-snapshot' / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(path.read_bytes())
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 60,
        'script_pins': scripts, 'input_index_sha256': sha((EVIDENCE / 'inputs.json').read_bytes()),
        'product_source_index_sha256': sha((folder / 'product-source-index.json').read_bytes()),
        'fixture_index_sha256': sha((folder / 'fixture-index.json').read_bytes()),
        'runner_sha256': sha(Path(__file__).read_bytes()), 'registered_at_ns': time.time_ns()})
    actual_env = os.environ.copy()
    actual_env['PYTHONDONTWRITEBYTECODE'] = '1'
    actual_env.pop('PYTHONPATH', None)
    actual_env.update(env or {})
    with (folder / 'stdout.txt').open('xb') as stdout, (folder / 'stderr.txt').open('xb') as stderr:
        process = subprocess.Popen(argv, cwd=ROOT, env=actual_env, stdout=stdout, stderr=stderr)
        write(folder / 'started.json', {'pid': process.pid, 'parent_pid': os.getpid(), 'started_at_ns': time.time_ns()})
        timed_out = False
        try:
            code = process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait(timeout=10)
    outcome = {'pid': process.pid, 'exit_code': code, 'timed_out': timed_out,
        'alive': process.poll() is None, 'ended_at_ns': time.time_ns(),
        'stdout_sha256': sha((folder / 'stdout.txt').read_bytes()),
        'stderr_sha256': sha((folder / 'stderr.txt').read_bytes())}
    write(folder / 'completed.json', outcome)
    print(json.dumps(outcome))
    return code


if __name__ == '__main__':
    if sys.argv[1] == 'freeze':
        freeze()
    elif sys.argv[1] == 'run':
        raise SystemExit(run(sys.argv[2], sys.argv[3:], {'PYTHONPATH': str(ROOT / 'src')}))
    else:
        raise SystemExit('unsupported audit operation')
