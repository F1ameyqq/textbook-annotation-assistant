"""Group existing orphan lines for one source-visible review action, never infer answers."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import statistics


NUMBER_START = re.compile(r"^\s*\d{1,2}\s*[.．、]")
TIER = re.compile(r"^(?:[A-C]?基础题|[A-C]?中档题|[A-C]?综合题|针对训练|巩固训练)\s*$")
TITLE = re.compile(r"^(?:参考答案|第[一二三四五六七八九十\d]+章|第\d+课时|小专题|☆?问题解决策略)")
FORMULA = re.compile(r"[=²³√≥≤∠△]|^\s*[+\-]?\d+\s*$")


def _key(line, asset):
    loc = line.get("location")
    if (type(loc) is not dict or type(loc.get("column")) is not int
            or type(loc.get("window_index")) is not int or type(loc.get("section_path")) is not list
            or not loc["section_path"] or not all(type(x) is str for x in loc["section_path"])):
        return None
    return asset, loc["column"], loc["window_index"], tuple(loc["section_path"])


def _box(line):
    box = line.get("bbox")
    if (type(box) is not list or len(box) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in box)
            or not box[0] < box[2] or not box[1] < box[3]):
        return None
    return box


def group_unassigned_sources(sources, pages, head):
    """Return additive UI groups; raw single-line sources and ownership stay unchanged.

    Every non-orphan line, title/tier, numbered start, window/column change or
    paragraph gap ends a group. Formula atoms may share a vertical band across
    their own column. Their reading order and transcription remain unverified.
    """
    available = {line["line_id"]: line for line in sources}
    groups = []
    for page in pages:
        if page.get("page_role") != "answer":
            continue
        asset = page["asset_id"]
        windows = {}
        for line in page.get("ocr_lines", []):
            key = _key(line, asset)
            if key is not None and _box(line) is not None:
                windows.setdefault(key, []).append(line)
        for key, raw_lines in sorted(windows.items()):
            ordered = sorted(raw_lines, key=lambda x: (x["bbox"][1], x["bbox"][0], x["line_id"]))
            heights = [line["bbox"][3] - line["bbox"][1] for line in ordered]
            gap_limit = max(24, statistics.median(heights) * 2)
            selected, bottom = [], None

            def flush():
                nonlocal selected, bottom
                if len(selected) > 1:
                    ids = [line["line_id"] for line in selected]
                    box = [min(line["bbox"][0] for line in selected), min(line["bbox"][1] for line in selected),
                           max(line["bbox"][2] for line in selected), max(line["bbox"][3] for line in selected)]
                    identity = json.dumps([head, key, ids], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    groups.append({"group_id": "orphan-paragraph-" + hashlib.sha256(identity).hexdigest(),
                        "asset_id": asset, "location": copy.deepcopy(selected[0]["location"]),
                        "line_ids": ids, "bbox": box, "source_lines": copy.deepcopy(selected),
                        "basis": "SAME_ASSET_WINDOW_COLUMN_CONTIGUOUS_ORPHANS_WITHOUT_TITLE_OR_NUMBER_BREAK",
                        "reading_order_status": "UNVERIFIED", "inferred_question_number": None,
                        "formula_review_required": any(FORMULA.search(line["text"]) for line in selected),
                        "content_status": "NEEDS_REVIEW"})
                selected, bottom = [], None

            for line in ordered:
                text = line.get("text", "").strip()
                title = line.get("heading") is not None or TIER.fullmatch(text) or TITLE.match(text)
                if title or line["line_id"] not in available:
                    flush()
                    continue
                source = available[line["line_id"]]
                if (_key(source, source["asset_id"]) != key or _box(source) != _box(line)
                        or source.get("text") != line.get("text")):
                    flush()
                    continue
                if (NUMBER_START.match(text) or bottom is not None and line["bbox"][1] - bottom > gap_limit
                        or len(selected) >= 100):
                    flush()
                selected.append(source)
                bottom = max(bottom if bottom is not None else line["bbox"][3], line["bbox"][3])
            flush()
    return groups
