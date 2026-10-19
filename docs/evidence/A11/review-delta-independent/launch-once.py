"""One frozen six-case delta invocation. The unmodified driver owns its 180s worker."""
import datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
E=Path(__file__).resolve().parent
ROOT=Path('D:/1800-worktrees/a11-delta-run')
DEST=ROOT/'docs/evidence/A11/review-delta-execution/independent-attempt-1'
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name,value):
    with (E/name).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')
manifest=json.loads((E/'run-export-manifest.json').read_bytes())
for member in manifest['members']:
    raw=(ROOT/member['path']).read_bytes()
    assert len(raw)==member['bytes'] and hashlib.sha256(raw).hexdigest()==member['sha256']
assert not DEST.exists()
env=dict(os.environ,GIT_NO_LAZY_FETCH='1',PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
command=[sys.executable,'docs/evidence/A11/review-delta-execution/run-delta.py',
         'docs/evidence/A11/review-delta-execution/independent-attempt-1']
save('launch-intent.json',{'at':now(),'command':command,'cwd':str(ROOT),
     'product_commit':manifest['product_commit'],'verified_raw_members':len(manifest['members']),
     'delta_attempt':1,'max_delta_attempts':1,'frozen_driver_worker_timeout_seconds':180,
     'old_17_case_suite_runs':0})
process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
save('supervisor-created.json',{'at':now(),'pid':process.pid,'wrapper_pid':os.getpid(),
     'source':'this wrapper owns original Popen object','command':command,'cwd':str(ROOT)})
stdout,stderr=process.communicate()
(E/'supervisor-stdout.log').write_bytes(stdout)
(E/'supervisor-stderr.log').write_bytes(stderr)
save('supervisor-release.json',{'at':now(),'pid':process.pid,'returncode':process.returncode,
     'original_popen_wait_completed':process.poll() is not None,
     'stdout_pipe_closed':process.stdout.closed,'stderr_pipe_closed':process.stderr.closed,
     'retry_performed':False})
print(stdout.decode('utf-8'))
if stderr: print(stderr.decode('utf-8'),file=sys.stderr)
raise SystemExit(process.returncode)
