"""Geometry-only, source-bound figure proposals; no OCR/model or approval action.

The threshold160 and connectedComponentsWithStats primitive match the existing
layout baseline. This module does not import that script or its environment
side effects. Callers supply already observed section/column/question bounds.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import math
import re
import statistics

VERSION = "source-bound-figure-proposal/1"
REFERENCE = re.compile(r"如图|图中|图示|[上下左右]图|见图|第\s*[0-9一二三四五六七八九十百]+\s*题(?:的)?图|图\s*[0-9]+")
CAPTION = re.compile(r"^\s*(?:第\s*([0-9]+)\s*题(?:的)?图|图\s*[0-9一二三四五六七八九十A-Za-z]+)\s*$")
LABEL = re.compile(r"^\s*[A-Za-z](?:[0-9′']{0,2})\s*$")
MATH = re.compile(r"[=²³√≥≤∠△⊥]|\$|\\")
BLOCKER = "FIGURE_REFERENCE_MISSING_CONFIRMED_SOURCE_IMAGE"


def _require(test, message):
    if not test:
        raise ValueError(message)


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _box(value, width, height):
    _require(type(value) is list and len(value) == 4 and all(type(v) in (int, float) and math.isfinite(v) for v in value), "INVALID_SOURCE_BBOX")
    x1, y1, x2, y2 = math.floor(value[0]), math.floor(value[1]), math.ceil(value[2]), math.ceil(value[3])
    _require(0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height, "SOURCE_BBOX_OUT_OF_RANGE")
    return [x1, y1, x2, y2]


def _intersect(boxes):
    return [max(b[0] for b in boxes), max(b[1] for b in boxes), min(b[2] for b in boxes), min(b[3] for b in boxes)]


def _overlap(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def _near(a, b, gap):
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return dx <= gap and dy <= gap


def _union(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def required_figure_issues(zones, frames, *, source_bindings):
    """Blocking predicate, recomputed at review/confirm/production, never confirmable.

    source_bindings maps asset_id to {sha256, dimensions:[width,height]}. A
    proposal alone cannot satisfy this predicate. Existing bind_region creates
    the source_checked image binding after an explicit UI confirmation.
    """
    issues = []
    for zone, text in zones.items():
        refs = list(REFERENCE.finditer(text)) if isinstance(text, str) else []
        if not refs:
            continue
        eligible = {"question", "choice"} if zone in {"question", "choice"} else {"answer", "analysis"} if zone in {"answer", "analysis"} else {zone}
        found = False
        for frame in frames:
            source = source_bindings.get(frame.get("asset_id"))
            binding = frame.get("binding") or {}
            if (frame.get("content_type") != "image" or frame.get("zone") not in eligible
                    or not source or frame.get("source_sha256") != source.get("sha256")
                    or type(source.get("sha256")) is not str or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
                    or frame.get("source_dimensions") != source.get("dimensions")
                    or frame.get("coordinate_space") != "ORIGINAL_PIXELS"
                    or binding.get("source_checked") is not True
                    or binding.get("kind") not in {"CUSTOMER_SOURCE_REGION", "CUSTOMER_CONFIRMED_FIGURE_PROPOSAL", "REVIEWED_SOURCE_GEOMETRY"}):
                continue
            if binding.get('kind') == 'REVIEWED_SOURCE_GEOMETRY' and (binding.get('geometry_checked') is not True
                    or not isinstance(binding.get('visual_review_sha256'), str)
                    or not re.fullmatch(r'[0-9a-f]{64}', binding['visual_review_sha256'])):
                continue
            try:
                width, height = source["dimensions"]
                _box(frame.get("bbox"), width, height)
            except (ValueError, TypeError, KeyError):
                continue
            found = True
            break
        if not found:
            issues.append({"code": BLOCKER, "zone": zone, "reference_spans": [[m.start(), m.end()] for m in refs],
                           "blocking": True, "confirmable": False, "content_status": "NEEDS_REVIEW"})
    return issues


def propose_figures(raw, expected_sha256, *, ocr_lines, scope, maximum_proposals=8):
    """Return deterministic, unapproved source-pixel proposals for one closed scope.

    scope requires asset_id/question_key/section_path/column, section_bbox,
    column_bbox, question_bbox and boundary_refs{start:[...],end:[...]}. Its
    boundary_status must be OBSERVED_CLOSED; otherwise no region is guessed.
    No candidate frame, product record or file is modified by this function.
    """
    _require(type(raw) is bytes and len(raw) <= 64 * 1024 * 1024, "BOUNDED_ORIGINAL_BYTES_REQUIRED")
    actual_sha = hashlib.sha256(raw).hexdigest()
    _require(type(expected_sha256) is str and re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256)
             and actual_sha == expected_sha256.lower(), "ORIGINAL_SOURCE_HASH_CHANGED")
    _require(type(maximum_proposals) is int and 1 <= maximum_proposals <= 32, "FINITE_PROPOSAL_LIMIT_REQUIRED")
    from PIL import Image
    import numpy as np
    import cv2
    with Image.open(io.BytesIO(raw)) as image:
        _require(image.width * image.height <= 40_000_000 and getattr(image, "n_frames", 1) == 1, "BOUNDED_SINGLE_ORIGINAL_IMAGE_REQUIRED")
        width, height = image.size
        gray = np.asarray(image.convert("L"))
    result = {"schema": "CustomerFigureProposals/v1", "algorithm": VERSION, "source_sha256": actual_sha,
              "source_dimensions": [width, height], "proposals": [], "issues": [],
              "content_status": "NEEDS_REVIEW", "automatic_approval": False, "new_ocr_or_model_calls": 0}
    refs = scope.get("boundary_refs") or {}
    if (scope.get("boundary_status") != "OBSERVED_CLOSED"
            or any(type(refs.get(edge)) is not list or not refs[edge]
                   or not all(type(ref) is str and ref for ref in refs[edge]) for edge in ("start", "end"))
            or type(scope.get("asset_id")) is not str or not scope["asset_id"]
            or type(scope.get("question_key")) is not str or not scope["question_key"]
            or type(scope.get("column")) is not int or scope["column"] < 0
            or type(scope.get("section_path")) is not list or not scope["section_path"]
            or not all(type(part) is str and part for part in scope["section_path"])):
        result["issues"].append("FIGURE_SCOPE_UNVERIFIED")
        return result
    bounds = [_box(scope[name], width, height) for name in ("section_bbox", "column_bbox", "question_bbox")]
    region = _intersect(bounds)
    if not region[0] < region[2] or not region[1] < region[3]:
        result["issues"].append("FIGURE_SCOPE_EMPTY")
        return result
    result["scope"] = {key: copy.deepcopy(scope[key]) for key in ("asset_id", "question_key", "section_path", "column", "boundary_refs")}
    result["scope"]["bbox"] = region
    left, top, right, bottom = region
    ink = gray[top:bottom, left:right] < 160
    residual = ink.copy()
    lines = []
    for line in ocr_lines:
        box = _box(line.get("bbox"), width, height)
        _require(type(line.get("line_id")) is str and line["line_id"], "ORIGINAL_OCR_REFERENCE_REQUIRED")
        _require(type(line.get("text")) is str, "ORIGINAL_OCR_TEXT_REQUIRED")
        if _overlap(box, region):
            lines.append({"line_id": line["line_id"], "bbox": box, "text": line.get("text", "")})
    median = statistics.median([line["bbox"][3] - line["bbox"][1] for line in lines]) if lines else 16
    coarse, masked_refs = [], []
    labels = []
    for line in lines:
        box = line["bbox"]
        if CAPTION.fullmatch(line["text"].strip()) or LABEL.fullmatch(line["text"].strip()):
            labels.append(line)
        # An oversized OCR box may cover a diagram. Do not erase it and then
        # incorrectly claim there is no non-text ink; retain an extent warning.
        if box[3] - box[1] > max(36, median * 2.5):
            coarse.append(line)
            continue
        x1, y1, x2, y2 = max(left, box[0] - 2), max(top, box[1] - 2), min(right, box[2] + 2), min(bottom, box[3] + 2)
        residual[y1 - top:y2 - top, x1 - left:x2 - left] = False
        masked_refs.append(line["line_id"])
    radius = max(1, min(3, round(median * .1)))
    connected = cv2.dilate(residual.astype(np.uint8), np.ones((radius * 2 + 1, radius * 2 + 1), dtype=np.uint8))
    count, components, stats, _ = cv2.connectedComponentsWithStats(connected, connectivity=8)
    min_side = max(12, round(median * .8))
    found, seen = [], set()
    forbidden = [_box(box, width, height) for box in scope.get("forbidden_bboxes", [])]
    for index in range(1, count):
        x, y, w, h, _ = map(int, stats[index])
        ys, xs = np.nonzero((components[y:y+h, x:x+w] == index) & residual[y:y+h, x:x+w])
        if not len(xs):
            continue
        box = [left + x + int(xs.min()), top + y + int(ys.min()), left + x + int(xs.max()) + 1, top + y + int(ys.max()) + 1]
        if box[2] - box[0] < min_side or box[3] - box[1] < min_side or len(xs) < max(24, round(median * 2)):
            continue
        notes, near_refs = [], []
        if box[0] <= left + 2 or box[1] <= top + 2 or box[2] >= right - 2 or box[3] >= bottom - 2:
            notes.append("FIGURE_TOUCHES_SCOPE_BOUNDARY")
        for line in labels:
            if _near(box, line["bbox"], max(6, median * 1.25)):
                box = _union(box, line["bbox"])
                near_refs.append(line["line_id"])
                caption = CAPTION.fullmatch(line["text"].strip())
                if caption and caption[1] and scope.get("printed_number") and caption[1] != str(scope["printed_number"]):
                    notes.append("CAPTION_NUMBER_SCOPE_MISMATCH")
        if any(_overlap(box, line["bbox"]) for line in coarse):
            notes.append("COARSE_OCR_MAY_COVER_FIGURE")
        if any(_overlap(box, other) for other in forbidden):
            notes.append("FIGURE_OVERLAPS_OTHER_SCOPE")
        if any(MATH.search(line["text"]) and _near(box, line["bbox"], max(4, median * .5)) for line in lines):
            notes.append("FORMULA_OR_DIAGRAM_UNRESOLVED")
        clipped = _intersect([box, region])
        if clipped != box:
            notes.append("FIGURE_LABEL_EXTENDS_BEYOND_SCOPE")
        box = clipped
        if tuple(box) in seen:
            continue
        seen.add(tuple(box))
        identity = _hash([VERSION, actual_sha, result["scope"], box])
        found.append({"proposal_id": "figure-" + identity, "kind": "FIGURE_REGION_PROPOSAL",
            "asset_id": scope["asset_id"], "question_key": scope["question_key"], "bbox": box,
            "source_sha256": actual_sha, "source_dimensions": [width, height], "coordinate_space": "ORIGINAL_PIXELS",
            "status": "PROPOSED_UNREVIEWED", "approved": False, "content_status": "NEEDS_REVIEW",
            "confidence": "LOW" if notes else "GEOMETRY_SUPPORTED_REVIEW_ONLY",
            "can_confirm_extent_without_adjustment": not notes,
            "suggested_action": "VIEW_AND_ADJUST" if notes else "REVIEW_AND_CONFIRM",
            "issues": sorted(set(notes)), "residual_ink_pixels": int(len(xs)),
            "ocr_mask_refs": list(masked_refs), "near_label_or_caption_refs": near_refs,
            "boundary_refs": copy.deepcopy(scope["boundary_refs"]), "content_inference": "NONE"})
    found.sort(key=lambda proposal: (proposal["bbox"][1], proposal["bbox"][0], proposal["proposal_id"]))
    if len(found) > maximum_proposals:
        result["issues"].append("FIGURE_PROPOSAL_LIMIT_REACHED")
    result["proposals"] = found[:maximum_proposals]
    result["issues"].append("FIGURE_PROPOSALS_REQUIRE_SOURCE_CONFIRMATION" if found else "FIGURE_DISCOVERY_UNCERTAIN")
    result["geometry"] = {"threshold": 160, "ocr_mask_padding": 2, "join_radius": radius,
                          "minimum_component_side": min_side, "masked_ocr_refs": masked_refs,
                          "coarse_ocr_unmasked_refs": [line["line_id"] for line in coarse]}
    return result
