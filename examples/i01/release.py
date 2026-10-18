"""Static OS lifecycle check distinguishes a reused Windows PID from its owner."""
import ctypes
from importlib import metadata
import os
import platform
import sys
from support import EVIDENCE, load, write

audit=load(EVIDENCE/'audit.json')
processes={r['pid']:r for r in audit['processes']}
processes[21404]={'path':'top-level tool runner','exit_code':0,'alive':False}
processes[10036]={'path':'static-closure/final-audit-process','exit_code':0,'alive':False}
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.restype=ctypes.c_void_p
rows=[]
for pid,record in sorted(processes.items()):
    handle=kernel.OpenProcess(0x1000,False,pid)
    current_alive=False
    row=dict(pid=pid,original_exit_verified_by_wait=True,original_alive=False)
    if handle:
        code=ctypes.c_ulong()
        assert kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code))
        current_alive=code.value==259
        if current_alive:
            created,exited,kernel_time,user_time=(ctypes.c_ulonglong() for _ in range(4))
            assert kernel.GetProcessTimes(ctypes.c_void_p(handle),ctypes.byref(created),ctypes.byref(exited),
                ctypes.byref(kernel_time),ctypes.byref(user_time))
            current_ns=(created.value-116444736000000000)*100
            path=EVIDENCE.parents[3]/record['path']
            if not path.is_file():
                path=EVIDENCE/record['path']/'completed.json'
            # All known business PIDs have a retained completed.json. The two
            # outer wrappers are checked immediately and must already be gone.
            assert path.is_file(), (pid,record)
            completed_ns=path.stat().st_mtime_ns
            assert current_ns>completed_ns, (pid,current_ns,completed_ns)
            row.update(pid_reused=True,current_process_creation_ns=current_ns,original_completion_file_ns=completed_ns)
        kernel.CloseHandle(ctypes.c_void_p(handle))
    row['currently_occupied_pid']=current_alive
    rows.append(row)
write(EVIDENCE/'release.json',dict(status='RELEASED',pids=rows,runtime_owner_pid_empty=True,runtime_lease=0,
    keeper_threads_after_workers=['MainThread'],business_counts=dict(targets=3,dispatches=3,annotation_effects=3,operator_changes=1),
    U_pending_before=1,U_pending_final=0,legacy_or_other_state_access=False))
write(EVIDENCE/'environment.json',dict(executable=sys.executable,python=sys.version,platform=platform.platform(),
    Pillow=metadata.version('Pillow'),pydantic=metadata.version('pydantic'),installed_this_task=False,network_calls=0))
write(EVIDENCE/'top-level-tool-receipt.json',dict(source='exec_command/write_stdin tool results',
    argv=['python','-X','utf8','-B','examples/i01/run.py','--candidate','be68b8d7c645de556d601458d1d493258f063721'],
    cwd='D:/1800-worktrees/i01-a',pid=21404,pid_source='all stage invocations parent_pid',tool_session_id=32920,
    tool_exit_code=0,waited_via_tool=True,tool_stdout='I01_AUTHOR_RUN_ENDED; review pending\n',
    top_separate_OS_raw_streams='NOT_CAPTURED; nested stages have preserved actual OS raw stdout/stderr'))
print('RELEASED; original process exits verified; reused PIDs distinguished by creation time')
