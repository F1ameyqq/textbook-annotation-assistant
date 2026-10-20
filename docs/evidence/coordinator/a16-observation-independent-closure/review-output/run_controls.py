"""Freeze this candidate's independent delta control script and execute once."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('D:/1800-worktrees/a16-observation-review');OUT=ROOT/'docs/evidence/A16/independent-observation-review'
raw=(OUT/'controls.py').read_bytes()
with (OUT/'independent-input-freeze.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump({'task':'A16','candidate_manifest_sha256':'e66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f',
        'script':'controls.py','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'frozen_before_execution':True,
        'control_groups':9,'input_data':'All synthetic variants fixed in script plus hash-bound59 input files',
        'old_suites_or_parser_evaluation':False},stream,indent=2);stream.write('\n')
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',GIT_NO_LAZY_FETCH='1')
cmd=[sys.executable,'-B',str(OUT/'controls.py')];started=time.monotonic()
child=subprocess.Popen(cmd,cwd=str(ROOT),env=env,stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x08000000)
stdout,stderr=child.communicate(timeout=40)
for name,data in [('controls.stdout.raw.txt',stdout),('controls.stderr.raw.txt',stderr)]:
    with (OUT/name).open('xb') as stream:stream.write(data)
record={'task':'A16','argv':cmd,'pid':child.pid,'wait_completed':True,'exit_code':child.returncode,
    'duration_ms':round((time.monotonic()-started)*1000),'stdout_sha256':hashlib.sha256(stdout).hexdigest(),
    'stderr_bytes':len(stderr),'OS_creation_identity':'NOT_OBSERVED_NO_CLAIM'}
with (OUT/'controls-command-result.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps(record))
