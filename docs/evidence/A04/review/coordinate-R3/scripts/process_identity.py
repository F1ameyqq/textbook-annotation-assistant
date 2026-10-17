"""Windows identities for known own-process handles/PIDs only; no enumeration."""
import ctypes,os
K=ctypes.WinDLL('kernel32',use_last_error=True)
class Time(ctypes.Structure):_fields_=[('low',ctypes.c_uint32),('high',ctypes.c_uint32)]
K.GetProcessTimes.argtypes=[ctypes.c_void_p,*([ctypes.POINTER(Time)]*4)];K.GetProcessTimes.restype=ctypes.c_int
K.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)];K.GetExitCodeProcess.restype=ctypes.c_int
K.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];K.OpenProcess.restype=ctypes.c_void_p
K.CloseHandle.argtypes=[ctypes.c_void_p]
def from_handle(pid,handle):
    created,ended,kernel,user=Time(),Time(),Time(),Time();code=ctypes.c_uint32()
    assert K.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kernel),ctypes.byref(user))
    assert K.GetExitCodeProcess(handle,ctypes.byref(code))
    return {'pid':pid,'creation_filetime':(created.high<<32)|created.low,'exit_code':code.value,'running':code.value==259}
def own():return from_handle(os.getpid(),ctypes.c_void_p(-1))
def child(process):return from_handle(process.pid,int(process._handle))
def probe(identity):
    h=K.OpenProcess(0x1000,False,identity['pid'])
    if not h:
        code=ctypes.get_last_error();assert code==87,(identity,code)
        return {**identity,'original_process_exited':True,'observation':'NO_SUCH_PROCESS'}
    try:now=from_handle(identity['pid'],h)
    finally:K.CloseHandle(h)
    if now['creation_filetime']!=identity['creation_filetime']:
        assert now['creation_filetime']>identity['creation_filetime']
        return {**identity,'original_process_exited':True,'observation':'PID_REUSED_LATER_NO_ACTION','current_creation_filetime':now['creation_filetime']}
    return {**identity,'original_process_exited':not now['running'],'observation':'SAME_CREATION_TIME','exit_code':now['exit_code']}
