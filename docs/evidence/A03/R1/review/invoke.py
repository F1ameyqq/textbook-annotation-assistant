"""Run one preregistered review child; retain argv, actual PID and raw streams."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ISOLATION = Path('D:/1800-worktrees/a03-r1-review-54e86adf')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--label', required=True)
    p.add_argument('--timeout', type=int, required=True)
    p.add_argument('--pythonpath', default='')
    p.add_argument('--env', action='append', default=[])
    p.add_argument('argv', nargs=argparse.REMAINDER)
    a = p.parse_args()
    argv = a.argv[1:] if a.argv[:1] == ['--'] else a.argv
    folder = OUT / 'processes' / a.label
    folder.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    env['PYTHONPATH'] = a.pythonpath or str(ISOLATION / 'src')
    overrides = {}
    for entry in a.env:
        key, value = entry.split('=', 1)
        overrides[key] = value
    env.update(overrides)
    request = dict(argv=argv, cwd=str(ISOLATION), timeout_seconds=a.timeout,
                   pythonpath=env['PYTHONPATH'], env_overrides=overrides,
                   start_time_ns=time.time_ns(), wrapper_pid=os.getpid())
    (folder / 'request.json').write_text(json.dumps(request, indent=2)+'\n', encoding='utf-8')
    start = time.monotonic()
    with (folder / 'stdout.txt').open('xb') as stdout, (folder / 'stderr.txt').open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=ISOLATION, env=env, stdout=stdout, stderr=stderr)
        (folder / 'started.json').write_text(json.dumps(dict(pid=child.pid, argv=argv), indent=2)+'\n', encoding='utf-8')
        timed_out = False
        try:
            child.wait(timeout=a.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            # Only this wrapper's own child is terminated. Business drivers have
            # their own 180/240 per-phase/case watchdog and cleanup protocol.
            child.kill()
            child.wait(timeout=10)
    result = dict(pid=child.pid, exit_code=child.returncode, waited=True,
                  alive=child.poll() is None, timeout=timed_out,
                  wall_seconds=time.monotonic()-start, end_time_ns=time.time_ns(),
                  streams={name:dict(bytes=(folder/name).stat().st_size,
                      sha256=hashlib.sha256((folder/name).read_bytes()).hexdigest())
                      for name in ('stdout.txt','stderr.txt')})
    (folder / 'completed.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(label=a.label, **result)))
    sys.exit(1 if timed_out else child.returncode)

if __name__ == '__main__':
    main()
