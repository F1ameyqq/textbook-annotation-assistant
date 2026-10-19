"""Only the probe's new Job and original Popen handle; no PID reopening."""
import ctypes as c
from ctypes import wintypes as w


class OwnedJob:
    def __init__(self):
        self.k = c.WinDLL('kernel32', use_last_error=True)
        signatures = {
            'CreateJobObjectW': ([w.LPVOID, w.LPCWSTR], w.HANDLE),
            'SetInformationJobObject': ([w.HANDLE, c.c_int, w.LPVOID, w.DWORD], w.BOOL),
            'QueryInformationJobObject': ([w.HANDLE, c.c_int, w.LPVOID, w.DWORD, w.LPVOID], w.BOOL),
            'AssignProcessToJobObject': ([w.HANDLE, w.HANDLE], w.BOOL),
            'TerminateJobObject': ([w.HANDLE, w.UINT], w.BOOL),
            'TerminateProcess': ([w.HANDLE, w.UINT], w.BOOL),
            'GetProcessId': ([w.HANDLE], w.DWORD),
            'GetProcessTimes': ([w.HANDLE, w.LPVOID, w.LPVOID, w.LPVOID, w.LPVOID], w.BOOL),
            'GetExitCodeProcess': ([w.HANDLE, w.LPVOID], w.BOOL),
            'WaitForSingleObject': ([w.HANDLE, w.DWORD], w.DWORD),
            'CloseHandle': ([w.HANDLE], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.k, name)
            fn.argtypes, fn.restype = args, result
        self.handle = None

    def create(self):
        # JOBOBJECT_EXTENDED_LIMIT_INFORMATION, native pointer-size alignment.
        class Basic(c.Structure):
            _fields_ = [('per_process', c.c_int64), ('per_job', c.c_int64),
                        ('flags', w.DWORD), ('min_ws', c.c_size_t),
                        ('max_ws', c.c_size_t), ('active_limit', w.DWORD),
                        ('affinity', c.c_size_t), ('priority', w.DWORD),
                        ('scheduling', w.DWORD)]
        class Extended(c.Structure):
            _fields_ = [('basic', Basic), ('io', c.c_uint64 * 6),
                        ('process_memory', c.c_size_t), ('job_memory', c.c_size_t),
                        ('peak_process', c.c_size_t), ('peak_job', c.c_size_t)]
        handle = self.k.CreateJobObjectW(None, None)
        if not handle:
            raise OSError()
        self.handle = handle
        limit = Extended()
        limit.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway.
        if not self.k.SetInformationJobObject(handle, 9, c.byref(limit), c.sizeof(limit)):
            raise OSError()

    def identity(self, child):
        handle = int(child._handle)
        pid = self.k.GetProcessId(handle)
        times = [c.c_uint64() for _ in range(4)]
        if not pid or pid != child.pid:
            raise OSError()
        if not self.k.GetProcessTimes(handle, *(c.byref(t) for t in times)):
            raise OSError()
        if not times[0].value or self.k.WaitForSingleObject(handle, 0) != 258:
            raise OSError()
        return {'pid': pid, 'creation_filetime': times[0].value}

    def assign(self, child):
        if not self.k.AssignProcessToJobObject(self.handle, int(child._handle)):
            raise OSError()

    def active_count(self):
        class Accounting(c.Structure):
            _fields_ = [('times', c.c_int64 * 4), ('faults', w.DWORD),
                        ('total', w.DWORD), ('active', w.DWORD), ('terminated', w.DWORD)]
        info = Accounting()
        if not self.k.QueryInformationJobObject(self.handle, 1, c.byref(info), c.sizeof(info), None):
            raise OSError()
        return info.active

    def exited(self, child):
        result = self.k.WaitForSingleObject(int(child._handle), 0)
        if result not in (0, 258):
            raise OSError()
        return result == 0

    def terminate(self, child, assigned):
        ok = (self.k.TerminateJobObject(self.handle, 72) if assigned
              else self.k.TerminateProcess(int(child._handle), 72))
        if not ok:
            raise OSError()

    def exit_code(self, child):
        if not self.exited(child):
            raise OSError()
        code = w.DWORD()
        if not self.k.GetExitCodeProcess(int(child._handle), c.byref(code)):
            raise OSError()
        child.returncode = code.value  # Prevent Popen.__del__ from polling a closed handle.
        return code.value

    def close(self):
        if self.handle is not None:
            if not self.k.CloseHandle(self.handle):
                raise OSError()
            self.handle = None
