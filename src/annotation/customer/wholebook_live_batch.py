"""One-session, one-POST-per-question insertion for an exact reviewed leaf scope.

Assumption: existing OCR outside the shifted suffix stays unchanged while the
book lock is held; the native writer checks the full prewrite endpoint set.
Importing this module never starts a platform request. ``run`` defaults to a
local preview and only the caller's sole executor may invoke its live branch.
"""
from __future__ import annotations

import copy
import io
from pathlib import Path
import re
from urllib.parse import urlsplit

from . import native_plan, wire
from .prepare import candidate_hash, utcnow
from .production import _check_execution_selection, _execution_plan
from .selection import select
from .source import verify_sources
from .store import Hold, byte_hash, digest


def _merge(base, incoming):
    """A multi-process GET batch must see the same global inventory."""
    from annotation.runtime.usense_live.update import json_same
    for name, value in incoming.items():
        if name in base and not json_same(base[name], value):
            raise Hold("分批读取期间全书目录或题框变化，停止后续写入。")
        base[name] = value


def _page_bindings(transport, job, flat):
    from PIL import Image
    pages = {}
    for source in job["pages"]:
        if source["kind"] != "image":
            continue
        number = source["viewer_page"]
        native_plan.require(type(number) is int and 1 <= number <= 9999,
                            "来源图像缺少平台页码。")
        data = native_plan._response(flat[f"page_{number}"])
        native_plan.require(data.get("file_id") == job["book_id"] and
                            type(data.get("pages")) is list and len(data["pages"]) == 1,
                            "来源页记录不属于当前书。")
        page = data["pages"][0]
        url = page.get("image", "")
        parsed = urlsplit(url)
        native_plan.require(page.get("page_index") == number - 1 and
                            parsed.scheme == "https" and parsed.netloc.endswith(".aliyuncs.com") and
                            not parsed.query and not parsed.fragment and not parsed.username and
                            ("/" + job["book_id"] + "/") in parsed.path,
                            "来源图像不是当前书对应的官方原图。")
        raw = transport._source_image(url, source)
        with Image.open(io.BytesIO(raw)) as image:
            dimensions = list(image.size)
        native_plan.require(dimensions == [source["width"], source["height"]],
                            "来源图像尺寸已变化。")
        pages[source["raw_sha256"]] = {
            "book_id": job["book_id"], "sha256": byte_hash(raw),
            "dimensions": dimensions, "viewer_page": number, "image_url": url,
        }
    return pages


def capture_initial(transport, job):
    """One complete baseline; no 128-question limit and no save."""
    flat = transport._capture()
    _, questions = native_plan.directory_rows(flat["directory"])
    for first in range(1, len(questions) + 1, 6):
        _merge(flat, transport._capture(range(first, min(first + 6, len(questions) + 1))))
    numbers = sorted({p["viewer_page"] for p in job["pages"] if p["kind"] == "image"})
    for first in range(0, len(numbers), 8):
        _merge(flat, transport._capture(pages=numbers[first:first + 8]))
    pages = _page_bindings(transport, job, flat)
    return wire.snapshot(flat, job["book_id"], pages), flat


def capture_after(transport, job, before, before_flat, plan):
    """Refresh the inserted order and shifted suffix, then bind by node ID.

    Question URLs are order based. An insertion in an early lesson shifts every
    later order, so all affected records are fetched; only the prefix is reused.
    """
    old_count = plan["before_count"]
    start = plan["new_order"]
    native_plan.require(1 <= start <= old_count + 1, "插入位置无效。")
    global_state = transport._capture()
    _, rows = native_plan.directory_rows(global_state["directory"])
    native_plan.require(len(rows) == old_count + 1, "保存后题数不是原题数加一。")
    refreshed = {}
    for first in range(start, old_count + 2, 6):
        _merge(refreshed, transport._capture(range(first, min(first + 6, old_count + 2))))
    for name in ("directory", "frames", "source"):
        if name in refreshed:
            _merge(global_state, {name: refreshed.pop(name)})
    prefix = {name: value for name, value in before_flat.items()
              if name.startswith("q") and name.split("_", 1)[0][1:].isdigit()
              and int(name.split("_", 1)[0][1:]) < start}
    # The prefix's cached bytes are immutable; suffix records are fresh native GETs.
    prefix_hashes = {name: digest(value) for name, value in prefix.items()}
    flat = {**global_state, **prefix, **refreshed,
            **{name: value for name, value in before_flat.items() if name.startswith("page_")}}
    native_plan.require(all(digest(flat[name]) == sha for name, sha in prefix_hashes.items()),
                        "未顺延题目的本地基线已变化。")
    after = wire.snapshot(flat, job["book_id"], before["pages"])
    old_ids = set(before["questions"])
    native_plan.require(len(set(after["questions"]) - old_ids) == 1 and
                        old_ids <= set(after["questions"]), "目录节点身份出现缺失或重用。")
    return after, flat


def dispatch_one(transport, job, current, flat, plan):
    """Exactly one native writer invocation, then fresh identity-bound readback."""
    sent = transport.write_once(plan, flat, job)
    after, after_flat = capture_after(transport, job, current, flat, plan)
    writer = sent["writer"]
    comparison = native_plan.compare_readback(plan, after, sent["receipt"],
        runtime_actor_hashes=writer.get("runtime_actor_hashes"),
        send_window={"start": writer["send_intent_at"], "end": writer["finished_at"]})
    native_plan.require(comparison["runtime_actor_and_send_window_checked"],
                        "写入身份或读回时间窗不完整。")
    return sent, after, after_flat, comparison


def _scope_selection(store, job, scope):
    native_plan.require(type(scope) is dict and scope.get("book_id") == job["book_id"] and
                        type(scope.get("directory_path")) is list and scope["directory_path"] and
                        all(type(part) is str and part for part in scope["directory_path"]) and
                        type(scope.get("directory_id")) is str and scope["directory_id"] and
                        type(scope.get("expected_initial_native_count")) is int and
                        scope["expected_initial_native_count"] >= 0,
                        "全书批次缺少明确的书籍及末级目录身份。")
    bound = scope.get("selection")
    native_plan.require(type(bound) is list and bound and
                        all(type(row) is dict and type(row.get("key")) is str and row["key"] and
                            type(row.get("content_hash")) is str and
                            re.fullmatch(r"[0-9a-f]{64}", row["content_hash"]) and
                            type(row.get("source_key")) is str and
                            re.fullmatch(r"[0-9a-f]{64}", row["source_key"]) and
                            row.get("intended_operation") == "INSERT_NEW_NATIVE_QUESTION" and
                            type(row.get("zones")) is list and row["zones"] and
                            all(type(zone) is str and zone for zone in row["zones"]) and
                            type(row.get("source_frames")) is list and row["source_frames"]
                            for row in bound),
                        "批次缺少逐题身份和内容摘要。")
    keys = [row["key"] for row in bound]
    native_plan.require(len(set(keys)) == len(keys), "批次题目身份重复。")
    selected = select(store, job, keys)
    _check_execution_selection(job, selected, scope)
    native_plan.require(job.get("directory_path", job["lesson"]) == scope["directory_path"],
                        "任务目录与批次目录不一致。")
    for candidate, row in zip(selected, bound):
        native_plan.require(candidate_hash(candidate) == candidate["content_hash"] == row["content_hash"] and
                            native_plan.source_key(job["book_id"], candidate) == row["source_key"] and
                            candidate["frames"] == row["source_frames"] and
                            len(row["zones"]) == len(set(row["zones"])) and
                            set(candidate["zones"]) == set(row["zones"]),
                            "本批次来源题目、分区或内容摘要已变化。")
    return selected


def run(store, identity, settings, scope, *, dry_run=True,
        approved_question_ids=(), executor_session_id=None):
    """Preview locally by default; live requires the caller's exact grant.

    ``approved_question_ids`` are candidate keys, never printed numbers or
    native order. The caller must own the unique platform session named in
    ``scope['executor_session_id']`` and the durable book lock.
    """
    job, _ = store.job(identity)
    selected = _scope_selection(store, job, scope)
    keys = [candidate["key"] for candidate in selected]
    if dry_run:
        return {"status": "DRY_RUN", "book_id": job["book_id"],
                "directory_path": scope["directory_path"], "directory_id": scope["directory_id"],
                "question_ids": keys, "content_hashes": [candidate_hash(q) for q in selected],
                "writes": 0}
    native_plan.require(type(executor_session_id) is str and
                        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}", executor_session_id) and
                        executor_session_id == scope.get("executor_session_id") and
                        type(scope.get("sole_executor")) is bool and scope["sole_executor"] is True,
                        "真实写入仅限已指定的唯一平台执行会话。")
    approved = tuple(approved_question_ids)
    native_plan.require(set(approved) == set(keys) and len(approved) == len(keys),
                        "真实写入缺少本批次全部题目的明确授权。")
    from .legacy_ledger import bootstrap, guard
    from .transport import UsenseTransport
    kind = "save:" + job["book_id"]
    with store.book_lock(job["book_id"]):
        job, head = store.job(identity)
        selected = _scope_selection(store, job, scope)
        verify_sources(job["pages"])
        with store.connect() as db:
            unresolved = db.execute("SELECT key FROM operations WHERE kind=? AND state<>'COMPLETE'",
                                    (kind,)).fetchall()
        native_plan.require(not unresolved, "该书有待对账的写入操作。")
        for candidate in selected:
            native_plan.require(store.operation(kind, native_plan.source_key(job["book_id"], candidate)) is None,
                                "题目已有保存记录，请先按身份对账。")
        bootstrap(store, job["book_id"])
        guard(store, Path(settings["profile"]).resolve().parent / "usense-existing-ledger",
              job["book_id"])
        transport = UsenseTransport(store, settings, job["book_id"])
        current, flat = capture_initial(transport, job)
        native_plan.require(len(native_plan.directory_rows(current["directory"])[1]) ==
                            scope["expected_initial_native_count"], "批次初始库存已变化。")
        for candidate in selected:
            check = _execution_plan(current, candidate, scope["directory_path"], scope)
            native_plan.require(check["schema"] == "CustomerNativeInsertPlan/v1",
                                "本入口只执行新增题。")
        accepted = []
        for candidate in selected:
            verify_sources(job["pages"])
            plan = _execution_plan(current, candidate, scope["directory_path"], scope)
            native_plan.require(plan["schema"] == "CustomerNativeInsertPlan/v1" and
                                plan["payload"]["target_directory_id"] == scope["directory_id"] and
                                plan["payload"]["is_new_question_insertion"] is True and
                                plan["payload"]["question_order"] is None and
                                plan["payload"]["insert_after_order"] == plan["new_order"] - 1,
                                "新增题目录或插入位置已变化。")
            key = plan["key"]
            sent = None
            candidate["pending_plan_ref"] = store.put(plan)
            store.begin(kind, key)
            try:
                candidate["platform_status"] = "INTENT_UNKNOWN_UNTIL_READBACK"
                head = store.save_job(job, head, "SAVE_INTENT")
                sent, after, after_flat, comparison = dispatch_one(
                    transport, job, current, flat, plan)
                receipt = {"schema": "CustomerSaveReadback/v1", "book_id": job["book_id"],
                           "candidate_hash": candidate_hash(candidate), "plan": plan,
                           "writer": sent, "comparison": comparison, "after": after,
                           "accepted_at": utcnow(), "processes": copy.deepcopy(transport.processes)}
                ref = store.finish(kind, key, "COMPLETE", receipt)
                candidate.update(platform_status="SAVED_AND_INDEPENDENTLY_READ_BACK",
                                 acceptance_ref=ref)
                head = store.save_job(job, head, "READBACK_ACCEPTED")
                accepted.append({"question_id": candidate["key"],
                                 "node_id": comparison["new_node_id"],
                                 "info_id": comparison["new_info_id"],
                                 "order": plan["new_order"], "receipt_ref": ref})
                current, flat = after, after_flat
            except BaseException as exc:
                if store.operation(kind, key)["state"] == "INTENT":
                    store.finish(kind, key, "UNKNOWN_NO_RETRY", {
                        "error_type": type(exc).__name__, "message": str(exc),
                        "plan_ref": candidate["pending_plan_ref"], "sent": sent,
                        "processes": copy.deepcopy(transport.processes), "at": utcnow()})
                job["platform_status"] = "UNKNOWN_NO_RETRY"
                job["last_message"] = str(exc)
                store.save_job(job, head, "WHOLEBOOK_BATCH_STOPPED")
                raise
        job["platform_status"] = "SELECTED_ITEMS_SAVED_AND_READ_BACK"
        store.save_job(job, head, "WHOLEBOOK_BATCH_COMPLETE")
        return {"status": "COMPLETE", "book_id": job["book_id"],
                "directory_path": scope["directory_path"], "accepted": accepted,
                "native_count": len(native_plan.directory_rows(current["directory"])[1])}


def _fake_transport_selftest():
    """Check one dispatch, shifted GETs, identity and exception stop offline."""
    from unittest.mock import patch
    class Fake:
        calls = []
        writes = 0
        def _capture(self, orders=(), pages=()):
            self.calls.append(tuple(orders))
            return {"directory": {"count": 4}, "frames": {}, "source": {},
                    **{f"q{i}_info": {"node_id": f"n{i-1}" if i > 2 else "new"}
                       for i in orders}}
        def write_once(self, plan, flat, job):
            self.writes += 1
            return {"receipt": {"inserted_question_node": {"id": "new"}},
                    "writer": {"runtime_actor_hashes": {"runtime_user_id_sha256": "actor"},
                               "send_intent_at": "start", "finished_at": "end"}}
    fake = Fake()
    before = {"pages": {}, "questions": {"n1": {}, "n2": {}, "n3": {}}}
    old_flat = {"q1_info": {"node_id": "n1"}, "q2_info": {"node_id": "n2"},
                "q3_info": {"node_id": "n3"}}
    after = {"questions": {"n1": {}, "new": {}, "n2": {}, "n3": {}}}
    plan = {"before_count": 3, "new_order": 2}
    with patch.object(native_plan, "directory_rows", return_value=([], [1, 2, 3, 4])), \
         patch.object(wire, "snapshot", return_value=after), \
         patch.object(native_plan, "compare_readback", return_value={
             "runtime_actor_and_send_window_checked": True, "new_node_id": "new"}):
        sent, result, flat, matched = dispatch_one(fake, {"book_id": "46007447"},
                                                   before, old_flat, plan)
    assert result is after and fake.calls == [(), (2, 3, 4)] and fake.writes == 1
    assert matched["new_node_id"] == sent["receipt"]["inserted_question_node"]["id"]
    assert flat["q1_info"]["node_id"] == "n1" and flat["q2_info"]["node_id"] == "new"
    with patch.object(native_plan, "directory_rows", side_effect=Hold("readback failed")):
        try:
            dispatch_one(fake, {"book_id": "46007447"}, before, old_flat, plan)
        except Hold:
            pass
        else:
            raise AssertionError("readback failure must stop")
    assert fake.writes == 2  # One per explicit invocation; no automatic retry.
    candidate = {"key": "candidate-1", "content_hash": "a" * 64,
                 "frames": [{"zone": "question"}], "zones": {"question": "text"}}
    job = {"book_id": "46007447", "directory_path": ["第1章", "第1课"],
           "lesson": "第1课"}
    scope = {"book_id": job["book_id"], "directory_path": job["directory_path"],
             "directory_id": "native-leaf", "expected_initial_native_count": 3,
             "selection": [{"key": candidate["key"], "content_hash": "a" * 64,
                            "source_key": "b" * 64, "zones": ["question"],
                            "source_frames": candidate["frames"],
                            "intended_operation": "INSERT_NEW_NATIVE_QUESTION"}]}
    with patch.dict(_scope_selection.__globals__, {
             "select": lambda *_: [candidate],
             "_check_execution_selection": lambda *_: None,
             "candidate_hash": lambda *_: "a" * 64}), \
         patch.object(native_plan, "source_key", return_value="b" * 64):
        assert _scope_selection(None, job, scope) == [candidate]
        damaged = copy.deepcopy(scope)
        damaged["selection"][0]["source_key"] = "c" * 64
        try:
            _scope_selection(None, job, damaged)
        except Hold:
            pass
        else:
            raise AssertionError("changed source key must fail before platform GET")
    return "fake dispatch/shifted-readback/stop/scope passed; 0 platform requests"


if __name__ == "__main__":
    print(_fake_transport_selftest())
