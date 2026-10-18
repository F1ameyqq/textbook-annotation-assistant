"""Account for native observation subprocesses as well as explicit waited records."""
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path

ROOT=Path('D:/1800-worktrees/a03-r1-review-54e86adf')
OUT=Path(__file__).resolve().parent
R=ROOT/'docs/evidence/A03/R1/review'
E=ROOT/'docs/evidence/A03/R1/execution'

def load(p):return json.loads(p.read_bytes())
def main():
    rows=[]
    expected=hashlib.sha256((ROOT/'src/annotation/runtime/recovery/native_observation.py').read_bytes()).hexdigest()
    for label,folder in [('author',E),('independent',R),('review-wrappers',OUT/'processes')]:
        for f in folder.rglob('completed.json'):
            if 'runtime-view' in f.parts:continue
            v=load(f)
            if not {'pid','alive','exit_code'}<=set(v):continue
            assert not v['alive'] and not v.get('timeout',False)
            if v.get('waited') is True:mode='EXPLICIT_WAITED_RECORD'
            elif 'process-audit' in f.parts:
                assert hashlib.sha256(f.with_name('script-snapshot.py').read_bytes()).hexdigest()==expected
                # The pinned real observer implementation records after wait(),
                # and poll() reports termination. No missing waited flag is invented.
                mode='PINNED_OBSERVER_WAIT_THEN_EXIT_POLL'
            else:raise AssertionError(str(f))
            rows.append(dict(group=label,path=str(f),pid=v['pid'],exit_code=v['exit_code'],wait_basis=mode))
    # Read only the registered task PIDs; never enumerate or signal unrelated processes.
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    current=[]
    for pid in sorted({r['pid'] for r in rows if r['group']!='author'}):
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:
            current.append(dict(pid=pid,state='NOT_OPENABLE_AS_LIVE_PROCESS',winerror=ctypes.get_last_error()))
            continue
        try:
            code=wintypes.DWORD()
            assert kernel.GetExitCodeProcess(handle,ctypes.byref(code))
            current.append(dict(pid=pid,state='STILL_ACTIVE_OR_PID_REUSED' if code.value==259 else 'EXITED',exit_code=code.value))
        finally:kernel.CloseHandle(handle)
    # An active/reused PID is reported, not killed or silently declared released.
    result=dict(completions=rows,counts={g:sum(r['group']==g for r in rows) for g in ('author','independent','review-wrappers')},
        native_observer_wait_source_sha256=expected,current_registered_PIDs=current,
        author_live_originals_inspected=False,signals_sent=0)
    (OUT/'release-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(counts=result['counts'],current_active_or_reused=[r for r in current if r['state']=='STILL_ACTIVE_OR_PID_REUSED'])))

if __name__=='__main__':main()
