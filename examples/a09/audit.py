"""Raw Git manifests and process identity for the bounded A09 driver."""
import ctypes
import hashlib
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone, timedelta


def utc():
    return datetime.now(timezone.utc).isoformat()


def git(root, *args):
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1")
    return subprocess.check_output(["git", "-c", "core.longpaths=true", *args], cwd=root, env=env)


def process_creation(pid):
    """Windows kernel creation time; no PID-only inference about liveness."""
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        values = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(v) for v in values)):
            raise ctypes.WinError(ctypes.get_last_error())
        ticks = values[0].dwLowDateTime + (values[0].dwHighDateTime << 32)
        return (datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=ticks // 10)).isoformat()
    finally:
        kernel.CloseHandle(handle)


def raw_manifest(root, revision, prefixes):
    entries = []
    raw = git(root, "ls-tree", "-r", "-z", revision)
    records = [r for r in raw.split(b"\0") if r and any(r.split(b"\t", 1)[1].decode("utf-8").startswith(p) for p in prefixes)]
    process = subprocess.Popen(["git", "-c", "core.longpaths=true", "cat-file", "--batch"], cwd=root,
                               env=dict(os.environ, GIT_NO_LAZY_FETCH="1"), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for record in records:
            meta, path_raw = record.split(b"\t", 1)
            mode, kind, oid = meta.decode().split()
            if kind != "blob":
                raise ValueError("unexpected non-blob member")
            process.stdin.write(oid.encode() + b"\n")
            process.stdin.flush()
            header = process.stdout.readline().decode().split()
            raw = process.stdout.read(int(header[2]))
            if process.stdout.read(1) != b"\n":
                raise ValueError("cat-file framing")
            p = path_raw.decode("utf-8")
            entries.append({"path": p, "git_blob": oid, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    finally:
        process.stdin.close()
        process.stdout.close()
        process.wait(timeout=10)
    if process.returncode:
        raise RuntimeError("cat-file failed")
    return entries
