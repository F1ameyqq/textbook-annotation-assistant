"""Bounded controlled-target read process; never dispatches a business effect."""
import multiprocessing
import os
import time

from annotation.runtime.storage.common import plain, unique


def _worker(pipe, descriptor, target_dir, observation_id, read_fault):
    try:
        from annotation.delivery.mock.persistent import PersistentMockSession
        observer = PersistentMockSession.open(target_dir, expected_store_id=descriptor["store_id"],
            expected_target_session_id=descriptor["target_session_id"], expected_target_key=descriptor["target_key"],
            expected_scope_id=descriptor["fixed_scope_id"], expected_source_ref=descriptor["fixed_source_ref"])
        value = observer.observe_target(descriptor["target_key"], observation_id=observation_id, read_fault=read_fault)
        pipe.send({"ok": True, "observation": plain(value), "pid": os.getpid()})
    except Exception as error:
        pipe.send({"ok": False, "code": getattr(error, "code", "TARGET_READ_FAILED"),
                   "message": str(error), "pid": os.getpid()})
    finally:
        pipe.close()


def observe_bounded(observer, *, read_fault=None, timeout=2):
    if getattr(observer, '_native', False):
        from .native_observation import observe_native_bounded
        return observe_native_bounded(observer, read_fault=read_fault, timeout=timeout)
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(child, plain(observer.descriptor),
        str(observer.directory), unique("recovery-observation"), read_fault))
    started = time.monotonic()
    process.start()
    child.close()
    value = None
    forced = False
    try:
        if parent.poll(max(0, timeout - (time.monotonic() - started))):
            try:
                value = parent.recv()
            except EOFError:
                value = {"ok": False, "code": "TARGET_READ_PROCESS_EXIT"}
        else:
            forced = True
            process.terminate()
    finally:
        process.join(timeout=max(.01, timeout - (time.monotonic() - started)))
        if process.is_alive():
            forced = True
            process.kill()
            process.join(timeout=5)
        parent.close()
    result = value or {"ok": False, "code": "TARGET_READ_TIMEOUT"}
    result.update(read_elapsed_seconds=time.monotonic() - started, process_pid=process.pid,
        process_exit_code=process.exitcode, process_reaped=not process.is_alive(), forced_termination=forced)
    if result["process_reaped"]:
        process.close()
    return result
