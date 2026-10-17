"""R3 reviewer-only sitecustomize; frozen product files remain unchanged."""
import atexit,ctypes,json,os,re,sys
from pathlib import Path
class T(ctypes.Structure):_fields_=[('lo',ctypes.c_uint32),('hi',ctypes.c_uint32)]
k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetProcessTimes.argtypes=[ctypes.c_void_p,*([ctypes.POINTER(T)]*4)]
c,e,a,b=T(),T(),T(),T();assert k.GetProcessTimes(ctypes.c_void_p(-1),ctypes.byref(c),ctypes.byref(e),ctypes.byref(a),ctypes.byref(b))
identity={'pid':os.getpid(),'creation_filetime':(c.hi<<32)|c.lo};blocked=[];starts=[]
def private(path):
    if not isinstance(path,(str,bytes,os.PathLike)):return False
    value=os.path.normcase(os.path.abspath(os.fsdecode(path)))
    root=os.path.normcase('D:\\1800\\.local')
    return value==root+'\\usense-login.json' or value==root+'\\browser-profiles' or value.startswith(root+'\\browser-profiles\\')
def stop(kind):blocked.append(kind);raise RuntimeError('R3_REVIEW_OFFLINE_BOUNDARY')
def audit(event,args):
    if event in ('socket.connect','socket.connect_ex','socket.bind','socket.getaddrinfo','http.client.connect','urllib.Request'):stop('NETWORK')
    if event in ('open','os.listdir','os.scandir') and args and private(args[0]):stop('AUTHORIZED_PRIVATE_PATH')
    if event=='subprocess.Popen':
        executable=args[0]
        if executable is None:
            cmd=args[1]
            if isinstance(cmd,str):
                m=re.match(r'^(?:"([^"]+)"|(\S+))',cmd);executable=(m.group(1) or m.group(2)) if m else ''
            else:executable=cmd[0] if cmd else ''
        name=os.path.basename(os.fsdecode(executable)).lower()
        if name not in ('python.exe','python','python3','python3.exe'):stop('NON_PYTHON:'+name)
        starts.append(name)
sys.addaudithook(audit)
def finish():
    path=os.environ.get('A04_R3_GUARD_LOG_DIR')
    if path:
        folder=Path(path);folder.mkdir(parents=True,exist_ok=True)
        (folder/(str(identity['pid'])+'-'+str(identity['creation_filetime'])+'.json')).write_text(json.dumps({**identity,
          'blocked_events':blocked,'local_python_starts':starts,'exit_hook_reached':True},indent=2)+'\n',encoding='utf-8')
atexit.register(finish)
