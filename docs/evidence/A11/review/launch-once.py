"""One authorized frozen A11 suite invocation; no retries or product changes."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

EVIDENCE = Path(__file__).resolve().parent
ROOT = Path('D:/1800-worktrees/a11-rr')
DEST = ROOT/'docs/evidence/A11/execution/independent-attempt-1'
def save(name,value):
    with (EVIDENCE/name).open('x',encoding='utf-8',newline='\n') as handle:
        json.dump(value,handle,ensure_ascii=False,indent=2)
        handle.write('\n')
def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
manifest = json.loads((EVIDENCE/'run-export-manifest.json').read_bytes())
for item in manifest['members']:
    raw = (ROOT/item['path']).read_bytes()
    assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'],item['path']
assert not DEST.exists()
env = dict(os.environ,GIT_NO_LAZY_FETCH='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
command = [sys.executable,'docs/evidence/A11/execution/run-suite.py',
           'docs/evidence/A11/execution/independent-attempt-1']
save('suite-launch-intent.json',{'at':now(),'attempt':1,'command':command,'cwd':str(ROOT),
     'product_commit':manifest['product'],'runtime_members_verified':len(manifest['members']),
     'caller_pid':os.getpid(),'suite_retry_allowed':False})
process = subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
save('suite-process-created.json',{'at':now(),'pid':process.pid,'parent_pid':os.getpid(),
     'source':'owned subprocess.Popen object','command':command,'cwd':str(ROOT)})
stdout,stderr = process.communicate()
(EVIDENCE/'suite-stdout.txt').write_bytes(stdout)
(EVIDENCE/'suite-stderr.txt').write_bytes(stderr)
save('suite-process-exited.json',{'at':now(),'pid':process.pid,'exit_code':process.returncode,
     'source':'same owned Popen object after communicate returned','wait_completed':True})
print(stdout.decode('utf-8'))
if stderr: print(stderr.decode('utf-8'),file=sys.stderr)
raise SystemExit(process.returncode)
