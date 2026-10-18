"""Create-only subprocess recorder for this independent review."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HOME = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')

if __name__ == '__main__':
    name, seconds, cwd, *argv = sys.argv[1:]
    folder = HOME / 'launches' / name
    folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': cwd, 'timeout_seconds': float(seconds),
          'expected_exit': 0, 'retries': 0, 'source_sha256': {a: sha(Path(a)) for a in argv if a.endswith('.py')},
          'recorder_sha256': sha(Path(__file__))})
    with (folder / 'stdout.bin').open('xb') as stdout, (folder / 'stderr.bin').open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=cwd, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL)
        write(folder / 'started.json', {'pid': child.pid, 'parent_pid': os.getpid(), 'started_at_ns': time.time_ns()})
        timed_out = False
        try:
            code = child.wait(timeout=float(seconds))
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            code = child.wait(timeout=5)
    write(folder / 'completed.json', {'pid': child.pid, 'exit_code': code, 'timeout': timed_out,
          'alive': child.poll() is None, 'ended_at_ns': time.time_ns(),
          'stdout_sha256': sha(folder / 'stdout.bin'), 'stderr_sha256': sha(folder / 'stderr.bin')})
    print(json.dumps({'name': name, 'exit_code': code, 'timeout': timed_out, 'folder': str(folder)}))
    print((folder / 'stdout.bin').read_bytes().decode('utf-8', 'replace'))
    print((folder / 'stderr.bin').read_bytes().decode('utf-8', 'replace'), file=sys.stderr)
    sys.exit(code if not timed_out else 124)
