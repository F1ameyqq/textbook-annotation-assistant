"""Bounded cooperative framework cleanup; OS release remains an outer duty.

wait_for waits for cancellation to finish. A close coroutine which suppresses
cancellation can therefore outlive its timeout. Here a deadline only observes
the task; cancellation is requested once without joining it indefinitely.
Blocking synchronous code still requires the existing outer process deadline.
"""
import asyncio


async def close_framework(context, runtime, pending, *, close_seconds=15,
                          callback_seconds=5, stop_seconds=15):
    result = {"context_closed": context is None, "runtime_stopped": runtime is None,
              "errors": [], "os_process_release": "REQUIRES_OUTER_HOLDER",
              "cancellation_completion_awaited": False}
    unfinished = set()

    def consume(task):
        if not task.cancelled():
            task.exception()

    async def phase(factory, name, field, seconds):
        task = None
        try:
            task = asyncio.create_task(factory())
            done, _ = await asyncio.wait({task}, timeout=seconds)
            if task not in done:
                raise TimeoutError()
            task.result()
            result[field] = True
        except BaseException as exc:
            result["errors"].append({"phase": name, "type": type(exc).__name__})
            if task is not None and not task.done():
                unfinished.add(task)
                task.add_done_callback(consume)
                task.cancel()

    if context is not None:
        await phase(context.close, "context_close", "context_closed", close_seconds)
    callbacks = {task for task in pending if not task.done()}
    for task in callbacks:
        task.cancel()
    if callbacks:
        try:
            _, remaining = await asyncio.wait(callbacks, timeout=callback_seconds)
            if remaining:
                result["errors"].append({"phase": "callbacks", "type": "TimeoutError"})
        except BaseException as exc:
            result["errors"].append({"phase": "callbacks", "type": type(exc).__name__})
    if runtime is not None:
        await phase(runtime.stop, "runtime_stop", "runtime_stopped", stop_seconds)
    result["pending_callbacks"] = sum(not task.done() for task in pending)
    result["unfinished_cleanup_tasks"] = sum(not task.done() for task in unfinished)
    result["context_runtime_release_confirmed"] = bool(
        result["context_closed"] and result["runtime_stopped"] and not result["errors"]
        and result["pending_callbacks"] == 0 and result["unfinished_cleanup_tasks"] == 0)
    return result


def run_owned_writer(coroutine):
    """Do not enter asyncio.run's unbounded cancellation join after cleanup.

This entry is only for the standalone writer process. A failed release is
persisted by the coroutine and exits nonzero; the outer Job holder must still
prove that this process and all owned descendants have exited before recovery.
"""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coroutine)
    finally:
        asyncio.set_event_loop(None)
        loop.close()
