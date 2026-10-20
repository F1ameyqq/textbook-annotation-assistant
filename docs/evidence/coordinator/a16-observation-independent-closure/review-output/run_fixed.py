"""Only the new18 observation suite and default static launcher, with raw wait/exit evidence."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('D:/1800-worktrees/a16-observation-review');OUT=ROOT/'docs/evidence/A16/independent-observation-review'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',GIT_NO_LAZY_FETCH='1')
records=[]
for name,args in [('observation-suite',['tests/a16_current_readonly/run_observation_only.py','--output',
    'docs/evidence/A16/current-readonly/revisions/observation-only/test-runs/independent-observation-01']),
    ('default-static-launcher',['tools/a16_current_state_launcher.py'])]:
    started=time.monotonic()
    child=subprocess.Popen([sys.executable,'-B']+args,cwd=str(ROOT),env=env,stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x08000000)
    out,err=child.communicate(timeout=30)
    for channel,raw in [('stdout',out),('stderr',err)]:
        with (OUT/(name+'.'+channel+'.raw.txt')).open('xb') as stream:stream.write(raw)
    record={'name':name,'argv':[sys.executable,'-B']+args,'pid':child.pid,'wait_completed':True,
        'exit_code':child.returncode,'duration_ms':round((time.monotonic()-started)*1000),
        'stdout_sha256':hashlib.sha256(out).hexdigest(),'stderr_bytes':len(err),
        'OS_creation_identity':'NOT_OBSERVED_NO_CLAIM'}
    records.append(record);print(json.dumps(record))
    if child.returncode:break
with (OUT/'fixed-command-results.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump({'task':'A16','commands':records,'only_new_observation18':True,'old_suites':0,'live_arguments':False},stream,indent=2);stream.write('\n')
