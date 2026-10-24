"""A25 outer Windows holder. No imports from product or access to credentials."""
import ctypes as c
from ctypes import wintypes as w
from datetime import datetime, timezone
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import time

k = c.WinDLL('kernel32', use_last_error=True)
HANDLE, DWORD, BOOL = w.HANDLE, w.DWORD, w.BOOL
ULONG_PTR = c.c_size_t

class STARTUPINFO(c.Structure):
    _fields_ = [('cb', DWORD), ('lpReserved', w.LPWSTR), ('lpDesktop', w.LPWSTR), ('lpTitle', w.LPWSTR),
        ('dwX', DWORD), ('dwY', DWORD), ('dwXSize', DWORD), ('dwYSize', DWORD), ('dwXCountChars', DWORD),
        ('dwYCountChars', DWORD), ('dwFillAttribute', DWORD), ('dwFlags', DWORD), ('wShowWindow', w.WORD),
        ('cbReserved2', w.WORD), ('lpReserved2', c.POINTER(c.c_byte)), ('hStdInput', HANDLE), ('hStdOutput', HANDLE), ('hStdError', HANDLE)]
class PROCESSINFO(c.Structure):
    _fields_ = [('hProcess', HANDLE), ('hThread', HANDLE), ('dwProcessId', DWORD), ('dwThreadId', DWORD)]
class BASICLIMIT(c.Structure):
    _fields_ = [('PerProcessUserTimeLimit', c.c_int64), ('PerJobUserTimeLimit', c.c_int64), ('LimitFlags', DWORD),
        ('MinimumWorkingSetSize', c.c_size_t), ('MaximumWorkingSetSize', c.c_size_t), ('ActiveProcessLimit', DWORD),
        ('Affinity', ULONG_PTR), ('PriorityClass', DWORD), ('SchedulingClass', DWORD)]
class IOCOUNTERS(c.Structure):
    _fields_ = [(name, c.c_uint64) for name in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
class EXTENDEDLIMIT(c.Structure):
    _fields_ = [('BasicLimitInformation', BASICLIMIT), ('IoInfo', IOCOUNTERS), ('ProcessMemoryLimit', c.c_size_t),
        ('JobMemoryLimit', c.c_size_t), ('PeakProcessMemoryUsed', c.c_size_t), ('PeakJobMemoryUsed', c.c_size_t)]
class PIDLIST(c.Structure):
    _fields_ = [('NumberOfAssignedProcesses', DWORD), ('NumberOfProcessIdsInList', DWORD), ('ProcessIdList', ULONG_PTR * 1024)]

def api(name, restype, argtypes):
    f = getattr(k, name); f.restype = restype; f.argtypes = argtypes
    return f

CreateJob = api('CreateJobObjectW', HANDLE, [c.c_void_p, w.LPCWSTR])
SetJob = api('SetInformationJobObject', BOOL, [HANDLE, c.c_int, c.c_void_p, DWORD])
QueryJob = api('QueryInformationJobObject', BOOL, [HANDLE, c.c_int, c.c_void_p, DWORD, c.c_void_p])
CreateProcess = api('CreateProcessW', BOOL, [w.LPCWSTR,w.LPWSTR,c.c_void_p,c.c_void_p,BOOL,DWORD,c.c_void_p,w.LPCWSTR,c.POINTER(STARTUPINFO),c.POINTER(PROCESSINFO)])
AssignJob = api('AssignProcessToJobObject', BOOL, [HANDLE,HANDLE])
ResumeThread = api('ResumeThread', DWORD, [HANDLE])
Wait = api('WaitForSingleObject', DWORD, [HANDLE,DWORD])
GetExit = api('GetExitCodeProcess', BOOL, [HANDLE,c.POINTER(DWORD)])
OpenProcess = api('OpenProcess', HANDLE, [DWORD,BOOL,DWORD])
GetTimes = api('GetProcessTimes', BOOL, [HANDLE,c.POINTER(w.FILETIME),c.POINTER(w.FILETIME),c.POINTER(w.FILETIME),c.POINTER(w.FILETIME)])
ImageName = api('QueryFullProcessImageNameW', BOOL, [HANDLE,DWORD,w.LPWSTR,c.POINTER(DWORD)])
Close = api('CloseHandle', BOOL, [HANDLE])
TerminateJob = api('TerminateJobObject', BOOL, [HANDLE,w.UINT])
TerminateProcess = api('TerminateProcess', BOOL, [HANDLE,w.UINT])

def check(value):
    if not value: raise c.WinError(c.get_last_error())
    return value
def now(): return datetime.now(timezone.utc).isoformat()
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf-8') as f: json.dump(value,f,indent=2)

def run(command, cwd, prefix, seconds):
    prefix = Path(prefix)
    result = {'schema':'A25OwnedWindowsProcess/v1','argv':command,'cwd':str(cwd),'started_at':now(),
        'resumed':False,'job_assigned_before_resume':False,'observed_processes':[], 'errors':[]}
    job = thread = process = None
    held = {}
    try:
        job = check(CreateJob(None,None))
        limits = EXTENDEDLIMIT(); limits.BasicLimitInformation.LimitFlags = 0x2000
        check(SetJob(job,9,c.byref(limits),c.sizeof(limits)))
        with prefix.with_suffix('.stdout').open('xb') as stdout, prefix.with_suffix('.stderr').open('xb') as stderr, open(os.devnull,'rb') as stdin:
            si = STARTUPINFO(); si.cb=c.sizeof(si); si.dwFlags=0x100
            handles = [msvcrt.get_osfhandle(f.fileno()) for f in (stdin,stdout,stderr)]
            for h in handles: os.set_handle_inheritable(h,True)
            si.hStdInput, si.hStdOutput, si.hStdError = handles
            pi=PROCESSINFO()
            commandline=c.create_unicode_buffer(subprocess.list2cmdline(command))
            try:
                check(CreateProcess(command[0],commandline,None,None,True,0x08000004,None,str(cwd),c.byref(si),c.byref(pi)))
            finally:
                for h in handles: os.set_handle_inheritable(h,False)
            process,thread=pi.hProcess,pi.hThread
            result['pid']=pi.dwProcessId
            check(AssignJob(job,process));result['job_assigned_before_resume']=True
            require_resume=ResumeThread(thread)
            if require_resume==0xffffffff:raise c.WinError(c.get_last_error())
            result['resumed']=True
            start=time.monotonic();parent_finished=False
            while True:
                ids=PIDLIST();check(QueryJob(job,3,c.byref(ids),c.sizeof(ids),None))
                for pid in ids.ProcessIdList[:ids.NumberOfProcessIdsInList]:
                    if pid in held:continue
                    h=OpenProcess(0x1000|0x00100000,False,pid)
                    if not h:continue  # A transient child may already have exited.
                    created,exited,kernel,user=[w.FILETIME() for _ in range(4)]
                    check(GetTimes(h,c.byref(created),c.byref(exited),c.byref(kernel),c.byref(user)))
                    buf=c.create_unicode_buffer(32768);n=DWORD(len(buf));check(ImageName(h,0,buf,c.byref(n)))
                    item={'pid':pid,'creation_filetime':(created.dwHighDateTime<<32)|created.dwLowDateTime,'image':buf.value,'observed_at':now()}
                    held[pid]=(h,item);result['observed_processes'].append(item)
                if not parent_finished and Wait(process,0)==0:
                    code=DWORD();check(GetExit(process,c.byref(code)));result['exit_code']=code.value
                    result['process_finished_at']=now();parent_finished=True
                if parent_finished and ids.NumberOfProcessIdsInList==0:
                    result['job_active_processes_after']=0;break
                if time.monotonic()-start>seconds:
                    result['timeout']=True;check(TerminateJob(job,124));break
                time.sleep(.1)
    except BaseException as exc:
        result['errors'].append({'type':type(exc).__name__,'winerror':getattr(exc,'winerror',None)})
    finally:
        if process and not result['resumed']:
            check(TerminateProcess(process,125))
        if job:
            ids=PIDLIST();check(QueryJob(job,3,c.byref(ids),c.sizeof(ids),None))
            if ids.NumberOfProcessIdsInList:
                check(TerminateJob(job,126)); result['owned_job_cleanup_terminated']=True
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    check(QueryJob(job,3,c.byref(ids),c.sizeof(ids),None))
                    if not ids.NumberOfProcessIdsInList:break
                    time.sleep(.1)
            result['job_active_processes_after']=ids.NumberOfProcessIdsInList
        for h,item in held.values():
            item['exit_signaled']=Wait(h,0)==0
            if item['exit_signaled']:
                code=DWORD();check(GetExit(h,c.byref(code)));item['exit_code']=code.value
            item['handle_closed']=bool(Close(h))
        result['launcher_exit_signaled']=bool(process and Wait(process,0)==0)
        if process:
            code=DWORD();check(GetExit(process,c.byref(code)));result['exit_code']=code.value
        result['thread_handle_closed']=bool(thread and Close(thread))
        result['process_handle_closed']=bool(process and Close(process))
        result['job_handle_closed']=bool(job and Close(job))
        result['finished_at']=now()
        for name in ('stdout','stderr'):
            path=prefix.with_suffix('.'+name)
            if path.exists():result[name]={'bytes':path.stat().st_size,'sha256':digest(path)}
        result['owned_os_release_confirmed']=bool(result.get('job_active_processes_after')==0 and result['launcher_exit_signaled'] and
            result['job_handle_closed'] and result['process_handle_closed'] and result['thread_handle_closed'] and
            all(p['exit_signaled'] and p['handle_closed'] for p in result['observed_processes']) and not result['errors'])
        write(prefix.with_suffix('.process.json'),result)
    return result
