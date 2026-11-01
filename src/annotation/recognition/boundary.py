"""Source-bound composition of OCR fragments in a reviewed heading window.

Only complete OCR elements from one explicitly scoped semantic heading window
are supported. Membership is independently checked against every active OCR
line in that window, and the geometric reading order must reproduce the window
title. A recognized keyword alone cannot turn a body fragment into a boundary.
Accepted results are structural evidence, always UNVERIFIED and never a site
action or business PASS. Partial OCR-element role splitting remains unsupported.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import re

from .baseline import code_digest, digest, valid_bbox

EVIDENCE_SCHEMAS = {"b-evidence-trial/0.2", "b-evidence-trial/0.3"}
CANDIDATE_SCHEMA = "b-boundary-candidate-trial/0.1"
REPORT_SCHEMA = "b-boundary-check-trial/0.1"
QUALITIES = {"SYNTHETIC_TEST", "MODEL_VISUAL_DEVELOPMENT_REVIEW"}


def _ref(value):
    return {key: value.get(key) for key in ("artifact_id", "revision", "content_hash")}


def _text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compact(text):
    return re.sub(r"\s+", "", text).replace("（", "(").replace("）", ")")


def _envelope(schema, kind, evidence, payload, inputs):
    producer = {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
                "policy": "one_reviewed_heading_window_whole_elements_horizontal_rows/0.1"}
    return {"schema_version": schema, "kind": kind,
            "artifact_id": kind.lower() + "-" + digest([schema, payload, inputs, producer])[:24],
            "revision": 1, "book_id": evidence.get("book_id"), "scope_id": evidence.get("scope_id"),
            "run_id": evidence.get("run_id"), "input_refs": copy.deepcopy(inputs), "producer": producer,
            "content_hash": digest(payload), "payload": copy.deepcopy(payload)}


def _asset(page, requested_id=None):
    source = page.get("source", {}) if page else {}
    return {"asset_id": page.get("asset_id") if page else requested_id,
            "sha256": source.get("sha256"), "width": source.get("width"), "height": source.get("height")}


def _window(evidence, asset_id, index):
    windows = evidence.get("payload", {}).get("context", {}).get("pages", {}).get(asset_id, {}).get("windows", [])
    return windows[index] if type(index) is int and 0 <= index < len(windows) else None


def _reading_order(members):
    """Compose same-baseline fragments left-to-right; separate rows top-to-bottom."""
    rows = []
    for member in sorted(members, key=lambda item: (item["bbox"][1], item["bbox"][0], item["line_id"])):
        box = member["bbox"]
        match = None
        for row in rows:
            anchor = row[0]["bbox"]
            overlap = min(anchor[3], box[3]) - max(anchor[1], box[1])
            if overlap >= .6 * min(anchor[3] - anchor[1], box[3] - box[1]):
                match = row
                break
        if match is None:
            rows.append([member])
        else:
            match.append(member)
    return [member for row in rows for member in sorted(row, key=lambda item: (item["bbox"][0], item["line_id"]))]


def build_boundary_candidate(evidence, *, asset_id, line_spans, source_bbox, review_basis):
    """Record a proposal, retaining exact original elements and selected spans.

    ``line_spans`` is a list of ``{line_id, text_span:[start,end]}``. Creation is
    not validation. Missing/foreign elements remain explicit invalid candidates
    so the validator can return useful issues without silently omitting them.
    """
    pages = evidence.get("payload", {}).get("pages", [])
    page = next((p for p in pages if p.get("asset_id") == asset_id), None)
    lines = {line.get("line_id"): (p, line) for p in pages for line in p.get("ocr_lines", [])}
    members = []
    for requested in line_spans:
        line_id, span = requested.get("line_id"), copy.deepcopy(requested.get("text_span"))
        pair = lines.get(line_id)
        if not pair:
            members.append({"line_id": line_id, "text_span": span, "missing": True})
            continue
        owner, line = pair
        text = line["text"]
        valid_span = (isinstance(span, list) and len(span) == 2 and all(type(n) is int for n in span)
                      and 0 <= span[0] < span[1] <= len(text))
        members.append({"fragment_id": "boundary-fragment-" + digest([_ref(evidence), line_id, span])[:24],
                        "line_id": line_id, "asset_id": owner["asset_id"], "text_span": span,
                        "text": text[span[0]:span[1]] if valid_span else None,
                        "raw_text": text, "raw_text_sha256": _text_sha(text),
                        "bbox": copy.deepcopy(line["bbox"]), "location": copy.deepcopy(line.get("location"))})
    located = next((member for member in members if member.get("location")), {})
    index = (located.get("location") or {}).get("window_index")
    usable = [member for member in members if isinstance(member.get("bbox"), list) and member.get("text") is not None]
    ordered = _reading_order(usable)
    payload = {"kind": "SECTION_HEADING", "asset": _asset(page, asset_id),
               "window_index": index, "window_snapshot": copy.deepcopy(_window(evidence, asset_id, index)),
               "source_bbox": copy.deepcopy(source_bbox), "members": members,
               "reading_order": [member["fragment_id"] for member in ordered],
               "assembled_text": " ".join(member["text"].strip() for member in ordered),
               "review_basis": copy.deepcopy(review_basis), "operation": "EVIDENCE_ONLY"}
    return _envelope(CANDIDATE_SCHEMA, "BoundaryCandidateTrial", evidence, payload, [_ref(evidence)])


def validate_boundary(evidence, candidate):
    """Validate composition and return a source-bound boundary or explicit HOLD."""
    issues = []
    evidence = evidence if isinstance(evidence, dict) else {}
    candidate = candidate if isinstance(candidate, dict) else {}

    def issue(code, refs=(), detail=None):
        issues.append({"code": code, "evidence_refs": list(refs), "detail": detail,
                       "severity": "ERROR", "blocks": ["PRE_APPLY"]})

    def result(boundary=None):
        return _envelope(REPORT_SCHEMA, "BoundaryCheckTrial", evidence,
                         {"accepted": not issues, "decision": "HOLD", "issues": issues,
                          "boundary": boundary, "verification_status": "UNVERIFIED",
                          "business_acceptance": False, "platform_actions": []},
                         [_ref(evidence), _ref(candidate)])

    def valid_artifact(value, schemas):
        return (value.get("schema_version") in schemas and isinstance(value.get("payload"), dict)
                and type(value.get("revision")) is int and value["revision"] >= 1
                and bool(value.get("artifact_id")) and value.get("content_hash") == digest(value["payload"]))

    if not valid_artifact(evidence, EVIDENCE_SCHEMAS):
        issue("BOUNDARY_EVIDENCE_INVALID")
    if not valid_artifact(candidate, {CANDIDATE_SCHEMA}):
        issue("BOUNDARY_CANDIDATE_INVALID")
    if issues:
        return result()
    data = candidate["payload"]
    if (candidate.get("input_refs") != [_ref(evidence)]
            or (candidate.get("book_id"), candidate.get("scope_id")) != (evidence.get("book_id"), evidence.get("scope_id"))):
        issue("BOUNDARY_STALE_OR_FOREIGN_EVIDENCE")
    if (data.get("kind") != "SECTION_HEADING" or data.get("operation") != "EVIDENCE_ONLY"
            or not isinstance(data.get("asset"), dict) or not isinstance(data.get("members"), list)):
        issue("BOUNDARY_CANDIDATE_SHAPE_INVALID")
        return result()
    pages = evidence["payload"].get("pages", [])
    page_matches = [p for p in pages if p.get("asset_id") == data["asset"].get("asset_id")]
    if len(page_matches) != 1:
        issue("BOUNDARY_ASSET_MISSING_OR_DUPLICATE")
        return result()
    page = page_matches[0]
    asset = _asset(page)
    if (data["asset"] != asset or not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sha256", "")))
            or page["source"].get("asset_id") != asset["asset_id"]):
        issue("BOUNDARY_ASSET_BINDING_MISMATCH")
    if any(type(asset.get(key)) is not int or asset[key] <= 0 for key in ("width", "height")):
        issue("BOUNDARY_ASSET_DIMENSIONS_INVALID")
        return result()
    window = _window(evidence, asset["asset_id"], data.get("window_index"))
    if not window or data.get("window_snapshot") != window:
        issue("BOUNDARY_WINDOW_BINDING_MISMATCH")
        return result()
    review = data.get("review_basis", {})
    if (not isinstance(review, dict) or review.get("kind") != "EXPLICIT_SOURCE_REVIEW"
            or review.get("reference_quality") not in QUALITIES
            or not isinstance(review.get("reason"), str) or not review.get("reason", "").strip()):
        issue("BOUNDARY_EXPLICIT_REVIEW_MISSING")
    if isinstance(review, dict):
        if review.get("reference_quality") == "HUMAN_REVIEWED":
            issue("BOUNDARY_HUMAN_REVIEW_RECEIPT_UNSUPPORTED", detail="A caller label cannot establish an independent human review receipt.")
        known_qualities = {page["source"].get("reference_quality"),
                           evidence["payload"].get("context", {}).get("reference_quality")}
        if "SYNTHETIC_TEST" in known_qualities and review.get("reference_quality") != "SYNTHETIC_TEST":
            issue("BOUNDARY_REFERENCE_QUALITY_PROMOTION")
    source_box = data.get("source_bbox")
    if not isinstance(source_box, list) or not valid_bbox(source_box, asset["width"], asset["height"]):
        issue("BOUNDARY_SOURCE_BBOX_INVALID")
        return result()
    lo, hi = window["y_range"]
    cut = page.get("layout", {}).get("cut_x")
    column = window.get("column")
    if not isinstance(cut, (int, float)) or type(column) is not int or column not in (0, 1):
        issue("BOUNDARY_WINDOW_GEOMETRY_UNSUPPORTED")
        return result()
    if (source_box[1] < lo or source_box[3] > hi or column == 0 and source_box[2] > cut
            or column == 1 and source_box[0] < cut):
        issue("BOUNDARY_SOURCE_BBOX_OUTSIDE_WINDOW")
    line_lookup = {}
    for owner in pages:
        for line in owner.get("ocr_lines", []):
            if line.get("line_id") in line_lookup:
                issue("BOUNDARY_DUPLICATE_SOURCE_LINE_ID", [line.get("line_id")])
            line_lookup[line.get("line_id")] = (owner, line)
    expected_lines = [line for line in page.get("ocr_lines", [])
                      if (line.get("location") or {}).get("window_index") == data.get("window_index")]
    if any(not isinstance(member, dict) or not isinstance(member.get("line_id"), str) for member in data["members"]):
        issue("BOUNDARY_MEMBER_INVALID")
        return result()
    actual_ids = [member.get("line_id") for member in data["members"] if isinstance(member, dict)]
    expected_ids = [line["line_id"] for line in expected_lines]
    if len(actual_ids) != len(set(actual_ids)):
        issue("BOUNDARY_MEMBER_REUSED", actual_ids)
    if set(actual_ids) != set(expected_ids) or not expected_ids:
        issue("BOUNDARY_MEMBER_COVERAGE_MISMATCH", sorted(set(actual_ids) | set(expected_ids)),
              {"expected": expected_ids, "actual": actual_ids})
    canonical = []
    for member in data["members"]:
        if not isinstance(member, dict):
            issue("BOUNDARY_MEMBER_INVALID")
            continue
        line_id = member.get("line_id")
        pair = line_lookup.get(line_id)
        if pair is None:
            issue("BOUNDARY_MEMBER_SOURCE_MISSING", [line_id])
            continue
        owner, line = pair
        loc = line.get("location") or {}
        if (owner["asset_id"] != asset["asset_id"] or member.get("asset_id") != asset["asset_id"]
                or loc.get("window_index") != data.get("window_index")
                or loc.get("column") != column or loc.get("section_path") != window.get("path")
                or member.get("location") != line.get("location")):
            issue("BOUNDARY_MEMBER_SCOPE_MISMATCH", [line_id])
        box, span, raw = line["bbox"], member.get("text_span"), line["text"]
        if (not valid_bbox(box, asset["width"], asset["height"]) or not lo <= (box[1] + box[3]) / 2 < hi
                or column == 0 and box[2] > cut or column == 1 and box[0] < cut
                or member.get("bbox") != box):
            issue("BOUNDARY_MEMBER_GEOMETRY_MISMATCH", [line_id])
        if not (source_box[0] <= box[0] < box[2] <= source_box[2]
                and source_box[1] <= box[1] < box[3] <= source_box[3]):
            issue("BOUNDARY_SOURCE_BBOX_TRUNCATES_MEMBER", [line_id])
        if (not isinstance(span, list) or len(span) != 2 or any(type(n) is not int for n in span)
                or not 0 <= span[0] < span[1] <= len(raw)):
            issue("BOUNDARY_TEXT_SPAN_INVALID", [line_id])
            continue
        if (member.get("raw_text") != raw or member.get("raw_text_sha256") != _text_sha(raw)
                or member.get("text") != raw[span[0]:span[1]]):
            issue("BOUNDARY_TEXT_SOURCE_MISMATCH", [line_id])
        if raw[:span[0]].strip() or raw[span[1]:].strip():
            issue("BOUNDARY_PARTIAL_OCR_ELEMENT_UNSUPPORTED", [line_id])
        fid = "boundary-fragment-" + digest([_ref(evidence), line_id, span])[:24]
        if member.get("fragment_id") != fid:
            issue("BOUNDARY_FRAGMENT_IDENTITY_MISMATCH", [line_id])
        canonical.append({**member, "bbox": box, "text": raw[span[0]:span[1]]})
    # A source region may not quietly include neighbouring body/diagram OCR.
    for line in page.get("ocr_lines", []):
        if line["line_id"] in actual_ids:
            continue
        box = line["bbox"]
        if max(source_box[0], box[0]) < min(source_box[2], box[2]) and max(source_box[1], box[1]) < min(source_box[3], box[3]):
            issue("BOUNDARY_OVERLAPS_NONMEMBER_CONTENT", [line["line_id"]])
    for i, first in enumerate(canonical):
        for second in canonical[i+1:]:
            a, b = first["bbox"], second["bbox"]
            if max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3]):
                issue("BOUNDARY_MEMBERS_OVERLAP", [first["line_id"], second["line_id"]])
    ordered = _reading_order(canonical)
    order = [member["fragment_id"] for member in ordered]
    assembled = " ".join(member["text"].strip() for member in ordered)
    if data.get("reading_order") != order or data.get("assembled_text") != assembled:
        issue("BOUNDARY_COMPOSITION_MISMATCH", [member["line_id"] for member in ordered])
    path = window.get("path") or []
    if not path or _compact(assembled) != _compact(path[-1]):
        issue("BOUNDARY_TITLE_CONTEXT_MISMATCH", actual_ids, {"assembled": assembled, "expected_title": path[-1] if path else None})
    if issues:
        return result()
    union = [min(m["bbox"][0] for m in ordered), min(m["bbox"][1] for m in ordered),
             max(m["bbox"][2] for m in ordered), max(m["bbox"][3] for m in ordered)]
    boundary = {"kind": "SECTION_HEADING", "asset": asset, "window_index": data["window_index"],
                "section_path": copy.deepcopy(window["path"]), "window_snapshot": copy.deepcopy(window),
                "line_ids": [member["line_id"] for member in ordered], "members": copy.deepcopy(ordered),
                "source_bbox": copy.deepcopy(source_box), "bbox_union": union, "text": assembled,
                "evidence_ref": _ref(evidence), "candidate_ref": _ref(candidate),
                "verification_status": "UNVERIFIED", "reference_quality": review["reference_quality"],
                "business_acceptance": False, "platform_actions": []}
    return result(boundary)
