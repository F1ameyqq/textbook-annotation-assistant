"""Read-only first-batch queue and exact local save manifest.

The queue is keyed by source instances and candidate keys. Printed labels are
display only. This module never contacts the platform or changes a job.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone

from .native_plan import source_key
from .prepare import candidate_hash
from .selection import select
from .store import Hold


def _source_regions(job, candidate):
    pages = {page["asset_id"]: page for page in job["pages"]}
    regions, missing = [], False
    for frame in candidate["frames"]:
        page = pages.get(frame.get("asset_id"))
        missing |= page is None or page.get("raw_sha256") != frame.get("source_sha256")
        regions.append({"zone": frame.get("zone"), "asset_id": frame.get("asset_id"),
                        "viewer_page": page.get("viewer_page") if page else None,
                        "source_sha256": frame.get("source_sha256"),
                        "bbox": copy.deepcopy(frame.get("bbox")),
                        "content_type": frame.get("content_type", "text")})
    return regions, missing


def _row(job, candidate):
    regions, missing = _source_regions(job, candidate)
    try:
        key = source_key(job["book_id"], candidate)
    except (KeyError, TypeError, ValueError):
        key, missing = None, True
    return {"job_id": job["id"], "key": candidate["key"],
            "candidate_key": candidate["key"],
            "source_instance_id": candidate.get("source_instance_id"),
            "source_item_kind": candidate.get("source_item_kind"),
            "lesson": job["lesson"],
            "directory_path": copy.deepcopy(job.get("directory_path", [job["lesson"]])),
            "directory_id": job.get("source_plan", {}).get("scope_id"),
            "printed_number": candidate["printed_number"],
            "content_status": candidate["content_status"],
            "platform_status": candidate["platform_status"],
            "content_hash": candidate_hash(candidate),
            "source_key": key,
            "zones": list(candidate["zones"]),
            "source_frames": copy.deepcopy(candidate["frames"]),
            "source_regions": regions,
            "source_binding_missing": missing}


def first_batch(store, result, limit=50, *, exclude_source_ids=()):
    """Return the first *prepared source instances* in directory/source order.

    The preparation result fixes scope order. Inside each job, the source plan
    fixes original item order; no printed-number sorting or deduplication occurs.
    Unprepared scopes stay visible in the manifest warnings, not as invented
    questions. The caller can pass a fresh prepare_book result after restart.
    """
    if type(limit) is not int or limit < 1:
        raise Hold("首批题数必须为正整数。")
    if (not isinstance(exclude_source_ids, (tuple, list, set, frozenset)) or
            any(type(identity) is not str or not identity for identity in exclude_source_ids)):
        raise Hold("历史排除清单必须包含精确来源题身份。")
    excluded = set(exclude_source_ids)
    if result.get("schema") != "CustomerWholebookPreparation/v1":
        raise Hold("缺少全书准备结果。")
    rows, identities = [], set()
    for item in result["results"]:
        identity = item.get("job")
        if not identity:
            continue
        job, _ = store.job(identity)
        if job["book_id"] != result["book_id"]:
            raise Hold("全书队列混入另一书籍任务。")
        source_order = {source["item_id"]: index for index, source in
                        enumerate(job.get("source_plan", {}).get("items", []))
                        if source.get("role") == "question"}
        candidates = sorted(enumerate(job["candidates"]),
                            key=lambda pair: (source_order.get(pair[1].get("source_instance_id"),
                                                               len(source_order) + pair[0]), pair[0]))
        for _, candidate in candidates:
            source_id = candidate.get("source_instance_id")
            if not source_id or source_id in identities:
                raise Hold("全书队列题源身份缺失或重复。")
            identities.add(source_id)
            if source_id in excluded:
                continue
            rows.append(_row(job, candidate))
            if len(rows) == limit:
                return rows
    return rows


def pending_manifest(store, batch):
    """Re-read each queued job; only currently confirmed, selectable items wait.

    A previous save, any uncertain book save, a changed candidate, missing
    figure, or an unreviewed answer makes an item non-pending. No state is
    upgraded here. The manifest is a local planning artifact, not a grant.
    """
    if type(batch) is not list:
        raise Hold("题目队列格式无效。")
    groups = {"pending_save": [], "preflight_required": [], "review_required": [],
              "already_saved": [], "blocked": [], "unknown": []}
    jobs = {}
    book = None
    seen = set()
    for old in batch:
        if type(old) is not dict or type(old.get("job_id")) is not str or type(old.get("key")) is not str:
            raise Hold("题目队列缺少任务与题目身份。")
        pair = (old["job_id"], old["key"])
        if pair in seen:
            raise Hold("题目队列重复。")
        seen.add(pair)
        if pair[0] not in jobs:
            jobs[pair[0]] = store.job(pair[0])[0]
        job = jobs[pair[0]]
        if book is None:
            book = job["book_id"]
        elif book != job["book_id"]:
            raise Hold("待保存清单混入另一书籍。")
        matches = [candidate for candidate in job["candidates"] if candidate["key"] == pair[1]]
        if len(matches) != 1 or (old.get("source_instance_id") and
                                  matches[0].get("source_instance_id") != old["source_instance_id"]):
            raise Hold("题目身份已变化，请重新生成首批队列。")
        candidate = matches[0]
        row = _row(job, candidate)
        review = candidate.get("review") or {}
        operation = store.operation("save:" + book, row["source_key"]) if row["source_key"] else None
        state = operation["state"] if operation else None
        status = candidate["platform_status"]
        if (state is not None and state != "COMPLETE") or "UNKNOWN" in status or "INTENT" in status:
            group, reason = "unknown", "原保存状态未完成只读对账"
        elif state == "COMPLETE" or status in {"SAVED_AND_INDEPENDENTLY_READ_BACK", "REUSED_ACCEPTED",
                                                  "REUSED_CURRENT_EXISTING"} or candidate.get("acceptance_ref"):
            group, reason = "already_saved", "已有平台保存或复用记录"
        elif row["source_binding_missing"]:
            group, reason = "blocked", "来源原图或题框身份缺失"
        elif status != "NOT_RUN":
            group, reason = "blocked", "平台状态不是未执行"
        elif candidate["content_status"] != "READY_CUSTOMER_REVIEWED":
            group, reason = "review_required", "题答及来源尚未经客户确认"
        elif (candidate_hash(candidate) != candidate.get("content_hash") or
              review.get("kind") != "CUSTOMER_SOURCE_REVIEW" or
              review.get("content_hash") != candidate_hash(candidate)):
            group, reason = "blocked", "确认后的内容摘要不一致"
        elif job.get("platform_directory_status") == "OFFLINE_VIRTUAL_DIRECTORY":
            group, reason = "blocked", "来源目录尚无平台目录绑定"
        else:
            try:
                select(store, job, [candidate["key"]])
                from .review_features import figure_requirements
                graph = store.get(job["graph_ref"]) if job.get("graph_ref") else None
                evidence = store.get(job["evidence_ref"]) if job.get("evidence_ref") else None
                if figure_requirements(candidate, job["pages"], graph, evidence):
                    raise Hold("题图或选项图仍需绑定")
            except (Hold, KeyError, ValueError) as exc:
                group, reason = "blocked", str(exc)
            else:
                group, reason = "preflight_required", "本地逐题审校已确认；待平台只读库存核对，尚未证明线上不存在"
        row["queue_status"] = group.upper()
        row["reason"] = reason
        groups[group].append(row)
    if book is not None:
        with store.connect() as db:
            unresolved = db.execute("SELECT COUNT(*) FROM operations WHERE kind=? AND state<>'COMPLETE'",
                                    ("save:" + book,)).fetchone()[0]
        if unresolved:
            for row in groups["preflight_required"]:
                row.update(queue_status="BLOCKED", reason="本书有待对账的保存操作")
            groups["blocked"].extend(groups["preflight_required"])
            groups["preflight_required"] = []
    return {"schema": "CustomerWholebookPendingManifest/v1", "book_id": book,
            "generated_at": datetime.now(timezone.utc).isoformat(), "batch_count": len(batch),
            "counts": {name: len(rows) for name, rows in groups.items()},
            **groups, "platform_inventory_checked": False,
            "platform_absence_proven": False,
            "pending_save_definition": "仅当前平台库存只读核对证明不存在后可列入；离线入口不作此证明",
            "platform_actions": [], "platform_write_authorized": False}


def build_scope(store, job_id, candidate_keys, *, directory_id, expected_initial_native_count):
    """Bind a locally reviewed selection for wholebook_live_batch.run(dry_run=True).

    The caller must enter the current native count and directory identity.
    This routine does not read the platform, and its result grants no write.
    """
    if (type(directory_id) is not str or not directory_id or
            type(expected_initial_native_count) is not int or expected_initial_native_count < 0):
        raise Hold("请填写当前平台末级目录 ID 与全书已有题数。")
    job, _ = store.job(job_id)
    if job.get("source_plan", {}).get("scope_id") != directory_id:
        raise Hold("目录 ID 与此课时题源不一致。")
    if type(candidate_keys) is not list or not candidate_keys or len(set(candidate_keys)) != len(candidate_keys):
        raise Hold("请选择不重复的明确题目身份。")
    selected = [candidate for candidate in job["candidates"] if candidate["key"] in candidate_keys]
    if len(selected) != len(candidate_keys):
        raise Hold("本批次题目身份已变化。")
    if len({source_key(job["book_id"], candidate) for candidate in selected}) != len(selected):
        raise Hold("本批次来源框身份重复，不能生成逐题写入计划。")
    current = pending_manifest(store, [_row(job, candidate) for candidate in selected])
    if len(current["preflight_required"]) != len(selected):
        raise Hold("所选题目并非全部处于已审校且待平台核对状态。")
    return {"schema": "CustomerWholebookExecutionScope/v1", "book_id": job["book_id"],
            "directory_path": copy.deepcopy(job["directory_path"]),
            "directory_id": directory_id,
            "expected_initial_native_count": expected_initial_native_count,
            "selection": [{"key": candidate["key"], "content_hash": candidate_hash(candidate),
                           "source_key": source_key(job["book_id"], candidate),
                           "intended_operation": "INSERT_NEW_NATIVE_QUESTION",
                           "zones": list(candidate["zones"]),
                           "source_frames": copy.deepcopy(candidate["frames"])}
                          for candidate in selected],
            "readonly_plan_ref": None,
            "sole_executor": False, "platform_absence_proven": False,
            "platform_write_authorized": False}
