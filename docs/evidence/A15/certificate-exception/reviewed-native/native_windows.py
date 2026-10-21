"""Windows backend. Only explicit construction binds OS APIs; no CLI/log output."""
import ctypes as c
from ctypes import wintypes as w
import ntpath
import os

from process_check import CheckFailure


class Entry(c.Structure):
    _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('pid', w.DWORD),
                ('heap', c.c_size_t), ('module', w.DWORD), ('threads', w.DWORD),
                ('parent', w.DWORD), ('priority', w.LONG), ('flags', w.DWORD),
                ('name', w.WCHAR * 260)]


class UnicodeString(c.Structure):
    _fields_ = [('length', w.USHORT), ('maximum', w.USHORT), ('buffer', c.c_void_p)]


def filetime(value):
    return (value.dwHighDateTime << 32) | value.dwLowDateTime


class WindowsAPI:
    def __init__(self):
        if os.name != 'nt':
            raise CheckFailure('WINDOWS_REQUIRED')
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        self.nt = c.WinDLL('ntdll')
        signatures = {
            'CreateToolhelp32Snapshot': ([w.DWORD, w.DWORD], w.HANDLE),
            'Process32FirstW': ([w.HANDLE, c.POINTER(Entry)], w.BOOL),
            'Process32NextW': ([w.HANDLE, c.POINTER(Entry)], w.BOOL),
            'OpenProcess': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            'CloseHandle': ([w.HANDLE], w.BOOL),
            'GetProcessId': ([w.HANDLE], w.DWORD),
            'GetProcessTimes': ([w.HANDLE] + [c.POINTER(w.FILETIME)] * 4, w.BOOL),
            'QueryFullProcessImageNameW': ([w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)], w.BOOL),
            'WaitForSingleObject': ([w.HANDLE, w.DWORD], w.DWORD),
            'GetExitCodeProcess': ([w.HANDLE, c.POINTER(w.DWORD)], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = args, result
        self.nt.NtQueryInformationProcess.argtypes = [w.HANDLE, w.ULONG, c.c_void_p, w.ULONG, c.POINTER(w.ULONG)]
        self.nt.NtQueryInformationProcess.restype = w.LONG

    def close(self, handle):
        if not self.kernel.CloseHandle(handle):
            raise CheckFailure('HANDLE_CLOSE_FAILED')

    def enumerate(self):
        snapshot = self.kernel.CreateToolhelp32Snapshot(2, 0)
        if snapshot in (None, c.c_void_p(-1).value):
            raise CheckFailure('ENUMERATION_UNAVAILABLE')
        rows = []
        try:
            entry = Entry()
            entry.size = c.sizeof(entry)
            valid = self.kernel.Process32FirstW(snapshot, c.byref(entry))
            while valid:
                rows.append((int(entry.pid), entry.name))
                valid = self.kernel.Process32NextW(snapshot, c.byref(entry))
            if c.get_last_error() != 18 or not rows:
                raise CheckFailure('ENUMERATION_INCOMPLETE')
            return rows
        finally:
            self.close(snapshot)

    def open(self, pid):
        # Query-limited plus SYNCHRONIZE; no VM read, write, terminate or debug privilege.
        handle = self.kernel.OpenProcess(0x1000 | 0x100000, False, pid)
        if not handle:
            raise CheckFailure('PROCESS_UNREADABLE_OR_GONE')
        return handle

    def held_identity(self, handle):
        """Works on the exact retained Popen handle, including after process exit."""
        pid = int(self.kernel.GetProcessId(handle))
        created, exited, kernel, user = (w.FILETIME() for _ in range(4))
        if not pid or not self.kernel.GetProcessTimes(handle, c.byref(created), c.byref(exited), c.byref(kernel), c.byref(user)):
            raise CheckFailure('PROCESS_TIMES_UNAVAILABLE')
        wait = int(self.kernel.WaitForSingleObject(handle, 0))
        if wait not in (0, 258):
            raise CheckFailure('PROCESS_STATE_UNKNOWN')
        code = w.DWORD()
        if not self.kernel.GetExitCodeProcess(handle, c.byref(code)) or not filetime(created):
            raise CheckFailure('PROCESS_STATE_UNKNOWN')
        if wait == 0 and not filetime(exited):
            raise CheckFailure('PROCESS_EXIT_UNPROVEN')
        return {'pid': pid, 'created_filetime': filetime(created),
                'exited_filetime': filetime(exited) if wait == 0 else None,
                'exit_observed': wait == 0, 'exit_code': int(code.value) if wait == 0 else None}

    def identity(self, handle):
        state = self.held_identity(handle)
        if state['exit_observed']:
            raise CheckFailure('PROCESS_GONE')
        size = w.DWORD(32768)
        path = c.create_unicode_buffer(size.value)
        if not self.kernel.QueryFullProcessImageNameW(handle, 0, path, c.byref(size)) or not size.value:
            raise CheckFailure('PROCESS_NAME_UNAVAILABLE')
        return state['pid'], ntpath.basename(path.value).lower(), state['created_filetime']

    def commandline(self, handle):
        size = w.ULONG()
        query = self.nt.NtQueryInformationProcess
        status = query(handle, 60, None, 0, c.byref(size)) & 0xffffffff
        if status not in (0xc0000004, 0xc0000023) or not c.sizeof(UnicodeString) <= size.value <= 1048576:
            raise CheckFailure('COMMANDLINE_SIZE_UNAVAILABLE')
        buffer = c.create_string_buffer(size.value)
        status = query(handle, 60, buffer, len(buffer), c.byref(size)) & 0xffffffff
        if status:
            raise CheckFailure('COMMANDLINE_UNREADABLE')
        value = UnicodeString.from_buffer(buffer)
        start = c.addressof(buffer)
        if (not value.length or value.length % 2 or value.length > value.maximum or
                not value.buffer or value.buffer < start + c.sizeof(UnicodeString) or
                value.buffer + value.length > start + len(buffer)):
            raise CheckFailure('COMMANDLINE_BUFFER_INVALID')
        return c.wstring_at(value.buffer, value.length // 2)
