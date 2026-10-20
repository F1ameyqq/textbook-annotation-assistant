"""Run only fixed revision75 and default static launcher; capture own wait/exit."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('D:/1800-worktrees/a16-r1-review')
OUT=ROOT/'docs/evidence/A16/independent-r1-review'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',GIT_NO_LAZY_FETCH='1')
commands=[('revision-suite',['tests/a16_current_readonly/run_offline.py','--output',
    'docs/evidence/A16/current-readonly/revisions/frame-binding-r1/test-runs/independent-r1-01']),
    ('static-launcher',['tools/a16_current_state_launcher.py'])]
results=[]
for name,args in commands:
    start=time.monotonic()
    child=subprocess.Popen([sys.executable,'-B']+args,cwd=str(ROOT),env=env,
        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x08000000)
    stdout,stderr=child.communicate(timeout=40)
    for kind,value in [('stdout',stdout),('stderr',stderr)]:
        with (OUT/(name+'.'+kind+'.raw.txt')).open('xb') as stream:stream.write(value)
    record={'name':name,'argv':[sys.executable,'-B']+args,'pid':child.pid,'wait_completed':True,
        'exit_code':child.returncode,'duration_ms':round((time.monotonic()-start)*1000),
        'stdout_sha256':hashlib.sha256(stdout).hexdigest(),'stderr_bytes':len(stderr),
        'OS_creation_identity':'NOT_OBSERVED_NO_CLAIM'}
    results.append(record);print(json.dumps(record))
    if child.returncode:break
with (OUT/'revision-command-results.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump({'task':'A16','candidate_manifest_sha256':'071340237c76a7159bd90485e17a774c2f870114baef0199172a2fc5f9547efc',
        'commands':results,'old_suites_run':False,'live_arguments':False},stream,indent=2);stream.write('\n')
