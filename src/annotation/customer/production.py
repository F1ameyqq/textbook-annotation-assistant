"""Serial prepare/save/fresh-process-readback/export with durable no-retry states."""
from __future__ import annotations

import copy
from html import escape
from pathlib import Path
import time

from .native_plan import make_plan, compare_readback, source_key, check_prewrite
from .prepare import candidate_hash, utcnow
from .source import verify_sources
from .store import Hold, digest, encoded


def export_local(store, identity):
    job, head = store.job(identity)
    verify_sources(job["pages"])
    output = store.root / "exports" / identity / head
    if (output / "index.html").is_file():
        return output
    output.mkdir(parents=True, exist_ok=True)
    (output / "job.json").write_bytes(encoded(job))
    parts = ["<!doctype html><html lang='zh-CN'><meta charset='utf-8'>",
             "<meta name='viewport' content='width=device-width'><title>课时材料</title>",
             "<style>body{font:17px/1.7 system-ui;max-width:960px;margin:40px auto;padding:0 24px;color:#182330}"
             "article{border-top:1px solid #ccd4dd;padding:24px 0}pre{white-space:pre-wrap;font:inherit}small{color:#596577}</style>",
             "<h1>" + escape(job["lesson"]) + "</h1>",
             "<p>本地准备：" + escape(job["status"]) + "；平台：" + escape(job["platform_status"]) + "</p>",
             "<small>这是本地内容与读回记录导出；不冒充平台原生整书导出或整书完成。</small>"]
    for question in job["candidates"]:
        parts += ["<article><h2>第 " + escape(question["printed_number"]) + " 题</h2>",
                  "<small>" + escape(question["content_status"]) + " · " + escape(question["platform_status"]) + "</small>"]
        for zone, text in question["zones"].items():
            label = {"question": "题干", "choice": "选项", "answer": "答案", "analysis": "解析"}.get(zone, zone)
            parts += ["<h3>" + label + "</h3><pre>" + escape(text) + "</pre>"]
        parts.append("</article>")
    parts.append("</html>")
    (output / "index.html").write_text("\n".join(parts), encoding="utf-8")
    return output


def produce(store, identity, settings, *, transport_factory=None):
    """Only the explicit customer start action calls this function.

    Tests substitute a synthetic platform, while the application always uses
    the concrete existing Usense writer/capture transport. There is no agent
    callback, per-question developer artifact, or formal-review-chat input.
    """
    from .transport import UsenseTransport
    started = time.perf_counter()
    job, head = store.job(identity)
    with store.book_lock(job["book_id"]):
        job, head = store.job(identity)
        verify_sources(job["pages"])
        if job["status"] != "PREPARED_OFFLINE" or job["issues"] or not job["candidates"]:
            raise Hold("请先处理本任务的来源与内容异常。")
        for candidate in job["candidates"]:
            if candidate_hash(candidate) != candidate["content_hash"] or candidate["content_status"] not in {"READY_EXACT_TEXT", "READY_CUSTOMER_REVIEWED"}:
                raise Hold("候选内容需要重新审校。")
        kind = "save:" + job["book_id"]
        with store.connect() as db:
            unresolved = db.execute("SELECT key,state FROM operations WHERE kind=? AND state<>'COMPLETE'", (kind,)).fetchall()
        if unresolved:
            raise Hold("该书已有未知或失败保存。请保留原登录目录、账本和回执，先对账；不重发后继。")
        pending = []
        for candidate in job["candidates"]:
            key = source_key(job["book_id"], candidate)
            old = store.operation(kind, key)
            if old is None:
                pending.append(candidate)
            else:
                accepted = store.get(old["output"])
                if accepted["candidate_hash"] != candidate_hash(candidate):
                    raise Hold("已有成功保存的来源内容发生变化；需要显式修订对账，不能作为新题重发。")
                candidate["platform_status"] = "REUSED_ACCEPTED"
                candidate["acceptance_ref"] = old["output"]
        transport = None
        current_key = None
        plan = sent = None
        try:
            if pending:
                transport = (transport_factory or UsenseTransport)(store, settings, job["book_id"])
                current, flat = transport.capture(job)
                # Preflight all candidates against the same current inventory.
                # A later missing source must not be found after an earlier send.
                for candidate in pending:
                    make_plan(current, candidate, job["lesson"])
                for index, candidate in enumerate(pending):
                    verify_sources(job["pages"])
                    plan = make_plan(current, candidate, job["lesson"])
                    sent = None
                    current_key = plan["key"]
                    candidate["pending_plan_ref"] = store.put(plan)
                    store.begin(kind, current_key)
                    candidate["platform_status"] = "INTENT_UNKNOWN_UNTIL_READBACK"
                    job["platform_status"] = "RUNNING"
                    head = store.save_job(job, head, "SAVE_INTENT")
                    sent = transport.write_once(plan, flat, job)
                    # Concrete capture launches fresh owned child processes
                    # only after the writer's outer OS release has been proven.
                    after, after_flat = transport.capture(job, previous_pages=current["pages"])
                    writer = sent.get("writer", {})
                    window = {"start": writer["send_intent_at"], "end": writer["finished_at"]} if writer else None
                    comparison = compare_readback(plan, after, sent["receipt"],
                        runtime_actor_hashes=writer.get("runtime_actor_hashes"), send_window=window)
                    if transport_factory is None and not comparison["runtime_actor_and_send_window_checked"]:
                        raise Hold("缺少实际操作者和发送窗口证明，不能接受保存。")
                    receipt = {"schema": "CustomerSaveReadback/v1", "book_id": job["book_id"],
                               "candidate_hash": candidate_hash(candidate), "plan": plan,
                               "writer": sent, "comparison": comparison, "after": after,
                               "accepted_at": utcnow(), "processes": copy.deepcopy(transport.processes)}
                    ref = store.finish(kind, current_key, "COMPLETE", receipt)
                    candidate.update(platform_status="SAVED_AND_INDEPENDENTLY_READ_BACK", acceptance_ref=ref)
                    head = store.save_job(job, head, "READBACK_ACCEPTED")
                    current_key = None
                    current, flat = after, after_flat
            job["platform_status"] = "SELECTED_ITEMS_SAVED_AND_READ_BACK"
        except BaseException as exc:
            if current_key is not None and store.operation(kind, current_key)["state"] == "INTENT":
                store.finish(kind, current_key, "UNKNOWN_NO_RETRY", {"type": type(exc).__name__, "message": str(exc),
                    "processes": copy.deepcopy(transport.processes) if transport else [], "at": utcnow(),
                    "plan_ref": store.put(plan), "sent": sent,
                    "native_output": str(transport.out) if hasattr(transport, "out") else None})
            job["platform_status"] = "UNKNOWN_NO_RETRY" if current_key else "BLOCKED_BEFORE_SEND"
            job["last_message"] = str(exc)
            job["metrics"]["production_seconds"] = time.perf_counter() - started
            store.save_job(job, head, "PRODUCTION_STOPPED")
            export_local(store, identity)
            raise
        job["metrics"]["production_seconds"] = time.perf_counter() - started
        store.save_job(job, head, "PRODUCTION_COMPLETE")
    return export_local(store, identity)


def reconcile(store, identity, settings, *, transport_factory=None):
    """One explicit read-only recovery; no call to a writer on any branch."""
    from .transport import UsenseTransport
    job, head = store.job(identity)
    kind = "save:" + job["book_id"]
    with store.book_lock(job["book_id"]):
        job, head = store.job(identity)
        verify_sources(job["pages"])
        candidates = [q for q in job["candidates"] if q.get("pending_plan_ref") and q["platform_status"] == "INTENT_UNKNOWN_UNTIL_READBACK"]
        if len(candidates) != 1:
            raise Hold("当前没有唯一可对账的未知保存。保留原记录；不会重新发送。")
        candidate = candidates[0]
        plan = store.get(candidate["pending_plan_ref"])
        key = source_key(job["book_id"], candidate)
        previous = store.operation(kind, key)
        if previous is None or previous["state"] != "UNKNOWN_NO_RETRY":
            raise Hold("原保存状态不是可自动核对的 UNKNOWN；需要保留原始记录进一步核查。")
        unknown = store.get(previous["output"])
        sent = unknown.get("sent")
        if sent is None:
            raise Hold("缺少明确的原始保存回执；本次不启动新读取或重发。")
        writer = sent.get("writer", {})
        if transport_factory is None:
            if writer.get("post_attempts") != 1 or writer.get("release", {}).get("context_runtime_release_confirmed") is not True:
                raise Hold("原保存发送次数或释放未证，先保留原运行记录。")
            from annotation.runtime.usense_live.update import loads
            from .store import byte_hash
            # Only the original writer's process records, never a copied
            # accepted marker, establish exit before this read-only recovery.
            for process in sent["processes"]:
                path = Path(process["record"])
                if byte_hash(path.read_bytes()) != process["sha256"] or loads(path.read_bytes()).get("owned_os_release_confirmed") is not True:
                    raise Hold("原进程释放记录未证。")
        recovery_key = digest([identity, previous["output"]])
        if store.operation("reconcile", recovery_key) is not None:
            raise Hold("这条原记录已有一次对账；查看原结果，不能自动重读。")
        transport = (transport_factory or UsenseTransport)(store, settings, job["book_id"])
        store.begin("reconcile", recovery_key)
        try:
            after, _ = transport.capture(job, previous_pages=plan["before"]["pages"])
            window = {"start": writer["send_intent_at"], "end": writer["finished_at"]} if writer else None
            comparison = compare_readback(plan, after, sent["receipt"], runtime_actor_hashes=writer.get("runtime_actor_hashes"), send_window=window)
            if transport_factory is None and not comparison["runtime_actor_and_send_window_checked"]:
                raise Hold("缺少原发送窗口或操作者身份。")
            receipt = {"schema": "CustomerSaveReadback/v1", "book_id": job["book_id"], "candidate_hash": candidate_hash(candidate),
                       "plan": plan, "writer": sent, "comparison": comparison, "after": after,
                       "accepted_at": utcnow(), "processes": copy.deepcopy(transport.processes), "reconciled_readonly": True}
            store.finish("reconcile", recovery_key, "COMPLETE", receipt)
            candidate["acceptance_ref"] = store.resolve(kind, key, previous, receipt)
            candidate["platform_status"] = "SAVED_AND_INDEPENDENTLY_READ_BACK"
            job["platform_status"] = "RECONCILED_SUCCESSORS_NOT_RUN"
            store.save_job(job, head, "READONLY_RECONCILIATION")
        except BaseException as exc:
            if store.operation("reconcile", recovery_key)["state"] == "INTENT":
                store.finish("reconcile", recovery_key, "FAILED_NO_RETRY", {"type": type(exc).__name__, "message": str(exc)})
            raise
    return export_local(store, identity)
