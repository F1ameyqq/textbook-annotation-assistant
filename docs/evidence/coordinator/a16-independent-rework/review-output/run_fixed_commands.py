"""Two explicitly authorized inert/offline commands; retain raw pipes and wait result."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('D:/1800-worktrees/a16-independent-fixed')
OUT = ROOT / 'docs/evidence/A16/independent-offline-review'
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', GIT_NO_LAZY_FETCH='1')
records = []
for name, args in [
    ('author-suite', ['tests/a16_current_readonly/run_offline.py', '--output',
        'docs/evidence/A16/current-readonly/test-runs/independent-01']),
    ('default-static-launcher', ['tools/a16_current_state_launcher.py'])]:
    started = time.monotonic()
    child = subprocess.Popen([sys.executable, '-B'] + args, cwd=str(ROOT), env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=0x08000000)
    out, err = child.communicate(timeout=30)
    for suffix, raw in [('stdout', out), ('stderr', err)]:
        with (OUT / (name + '.' + suffix + '.raw.txt')).open('xb') as stream:
            stream.write(raw)
    records.append({'name': name, 'argv': [sys.executable, '-B'] + args, 'pid': child.pid,
        'exit_code': child.returncode, 'wait_completed': True,
        'duration_ms': round((time.monotonic()-started)*1000),
        'stdout_sha256': hashlib.sha256(out).hexdigest(), 'stderr_bytes': len(err),
        'creation_identity': 'NOT_OBSERVED_NO_OS_IDENTITY_CLAIM'})
    print(json.dumps(records[-1]))
    if child.returncode:
        break
with (OUT / 'fixed-command-results.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump({'task':'A16', 'commands':records, 'live_arguments_supplied':False,
        'old_suite_run':False},stream,indent=2)
    stream.write('\n')
