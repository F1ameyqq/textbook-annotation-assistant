"""Optional historical alignment of existing platform nodes to source items.

This is a frozen, read-only match against two local 42-node tables. A matching
source ID can be skipped in a *review queue* to avoid duplicate effort. The
tables are historical snapshots, not a fresh platform inventory or permission
to save any other item.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .store import Hold


ALIGN_SHA256 = "68fe769bdfda3b9cbb84d6dbeb696c31336f289a38bcb76266c983152a1d08b4"
GEOMETRY_SHA256 = "ef3e06345585a0275b3325729524e5ac6993c1927eaa69809c2afe4a1c0d4c07"


def _frozen_json(path, expected):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise Hold("42题历史对齐原件已变化，不能沿用排除清单。")
    return json.loads(data)


def aligned_existing_sources(store, result, align_path, geometry_path):
    """Return only exact source IDs supported by both frozen alignments.

    Geometry and candidate identity must agree on directory, printed label and
    question pages. A row failing any check is retained in ``held``. This does
    not assert that the platform still has the node today.
    """
    align = _frozen_json(align_path, ALIGN_SHA256)
    geometry = _frozen_json(geometry_path, GEOMETRY_SHA256)
    if (align.get("schema") != "Align42/v3-geometric" or
            geometry.get("schema") != "Align42Geometry/v1" or
            align.get("pairs") != 42 or geometry.get("checked") != 42 or
            len(align.get("rows", [])) != 42 or len(geometry.get("results", [])) != 42 or
            result.get("schema") != "CustomerWholebookPreparation/v1" or
            result.get("book_id") != "46007447"):
        raise Hold("42题历史对齐与当前书籍准备结果不匹配。")
    geom = {}
    for row in geometry["results"]:
        key = (row.get("scope_id"), str(row.get("platform_global_number")),
               str(row.get("printed")))
        if key in geom:
            raise Hold("42题几何对齐存在重复的平台题身份。")
        geom[key] = row
    jobs = {}
    for item in result["results"]:
        if not item.get("job"):
            continue
        job, _ = store.job(item["job"])
        scope = job.get("source_plan", {}).get("scope_id")
        if scope in jobs or job.get("book_id") != "46007447":
            raise Hold("当前全书任务含重复目录或其他书籍。")
        jobs[scope] = job
    records, held, seen_sources = [], [], set()
    for row in align["rows"]:
        scope = row.get("scope_id")
        number = str(row.get("platform_number"))
        label = str(row.get("source_label"))
        key = (scope, number, label)
        geo = geom.get(key)
        reason = None
        if (geo is None or row.get("directory_matches") is not True or
                geo.get("directory_matches") is not True or
                row.get("platform_directory") != scope):
            reason = "DIRECTORY_OR_PRINTED_IDENTITY_UNPROVEN"
        elif (type(row.get("score")) not in (int, float) or row["score"] < .6 or
              type(geo.get("coverage")) not in (int, float) or geo["coverage"] < .6):
            reason = "GEOMETRY_BELOW_CONSERVATIVE_THRESHOLD"
        job = jobs.get(scope)
        if reason is None and job is None:
            reason = "SCOPE_NOT_PREPARED"
        if reason is None:
            matches = [candidate for candidate in job["candidates"]
                       if candidate.get("printed_number") == label]
            if len(matches) != 1:
                reason = "SOURCE_LABEL_NOT_UNIQUE"
        if reason is None:
            candidate = matches[0]
            source_id = candidate.get("source_instance_id")
            sources = [item for item in job["source_plan"]["items"]
                       if item.get("item_id") == source_id and item.get("role") == "question"]
            pages = sorted({fragment["page"] for source in sources
                            for fragment in source.get("fragments", [])})
            if (len(sources) != 1 or pages != row.get("stem_pages") or
                    pages != geo.get("stem_pages") or source_id in seen_sources):
                reason = "SOURCE_INSTANCE_OR_PAGES_CHANGED"
        if reason:
            held.append({"scope_id": scope, "platform_number": number,
                         "source_label": label, "reason": reason})
            continue
        seen_sources.add(source_id)
        records.append({"scope_id": scope, "platform_number": number,
                        "source_label": label, "source_instance_id": source_id,
                        "candidate_key": candidate["key"], "stem_pages": pages,
                        "alignment_score": row["score"], "geometry_coverage": geo["coverage"],
                        "status": "HISTORICAL_HIGH_CONFIDENCE_ALIGNMENT"})
    return {"schema": "KnownSavedHistoricalAlignment/v1", "book_id": "46007447",
            "source_sha256": {"align42": ALIGN_SHA256, "geometry": GEOMETRY_SHA256},
            "aligned_source_ids": [record["source_instance_id"] for record in records],
            "records": records, "held": held,
            "platform_inventory_checked_now": False, "platform_actions": []}
