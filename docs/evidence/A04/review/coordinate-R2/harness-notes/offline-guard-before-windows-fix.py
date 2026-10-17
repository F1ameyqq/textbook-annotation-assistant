"""Reviewer-only audit guard. Copied as sitecustomize into temporary test path.
No frozen product file is replaced. Reject real network, non-Python children,
actual credential/profile access. Synthetic temp credentials remain test data.
"""
import atexit,json,os,sys
from pathlib import Path
events=[];children=[]
ROOT=Path('D:/1800').resolve()
def restricted_path(p):
    if not isinstance(p,(str,bytes,os.PathLike)):return False
    try:
        value=os.path.normcase(os.path.abspath(os.fsdecode(p)))
        config=os.path.normcase(str(ROOT/'.local/usense-login.json'))
        profiles=os.path.normcase(str(ROOT/'.local/browser-profiles'))
        return value==config or value==profiles or value.startswith(profiles+os.sep)
    except (OSError,ValueError):return False
def reject(kind):
    events.append({'kind':kind,'decision':'BLOCK'})
    raise RuntimeError('R2_REVIEW_OFFLINE_BOUNDARY')
def audit(event,args):
    if event in ('socket.connect','socket.connect_ex','socket.bind','socket.getaddrinfo','http.client.connect','urllib.Request'):
        reject('NETWORK')
    if event in ('open','os.listdir','os.scandir') and args and restricted_path(args[0]):reject('AUTHORIZED_PRIVATE_PATH')
    if event=='subprocess.Popen':
        exe=os.path.basename(os.fsdecode(args[0])).lower()
        if exe not in ('python.exe','python','python3','python3.exe','python3.9.exe'):
            reject('NON_PYTHON_PROCESS:'+exe)
        children.append({'executable':exe,'decision':'ALLOW_LOCAL_PYTHON'})
sys.addaudithook(audit)
def write_record():
    folder=os.environ.get('A04_R2_GUARD_LOG_DIR')
    if folder:
        p=Path(folder);p.mkdir(parents=True,exist_ok=True)
        (p/(str(os.getpid())+'.json')).write_text(json.dumps({'pid':os.getpid(),'parent_pid':os.getppid(),
          'blocked_events':events,'local_python_starts':children,'exit_hook_reached':True,
          'mode':'R2_REVIEW_LOCAL_PYTHON_ONLY'},indent=2)+'\n',encoding='utf-8')
atexit.register(write_record)
