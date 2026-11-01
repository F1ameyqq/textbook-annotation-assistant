"""Versioned draft content materialization over immutable OCR/image sources.

Selections and explicit edits change active text, never historical OCR. Source
fragments, coverage and image regions remain intact. Draft authorship is not a
human verification claim; all output stays HOLD and creates no platform action.

All fragment, source and output intervals are left-closed/right-open Unicode
code point offsets (Python str), never UTF-16 code units or UTF-8 byte offsets.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import re

from .baseline import code_digest, digest, file_digest, load_source, valid_bbox
from .offline import scope_key, scalar_issues
from .policy import classify
from .question_quality import audit_questions

PLAN_SCHEMA = "b-content-revision-plan-trial/0.1"
REGION_PLAN_SCHEMA = "b-content-revision-plan-trial/0.2"
GEOMETRY_PLAN_SCHEMA = "b-content-revision-plan-trial/0.3"
APPLICATION_SCHEMA = "b-content-revision-application-trial/0.1"
REGION_APPLICATION_SCHEMA = "b-content-revision-application-trial/0.2"
GEOMETRY_APPLICATION_SCHEMA = "b-content-revision-application-trial/0.3"
GRAPH_SCHEMA = "b-graph-trial/0.6"
REGION_GRAPH_SCHEMA = "b-graph-trial/0.7"
GEOMETRY_GRAPH_SCHEMA = "b-graph-trial/0.8"
CHECK_SCHEMA = "b-check-trial/0.6"
REGION_CHECK_SCHEMA = "b-check-trial/0.7"
GEOMETRY_CHECK_SCHEMA = "b-check-trial/0.8"
IDENTITY_POLICY = "CURRENT_REFS_WITH_EXECUTION_TIME_IN_JOURNAL/0.1"
GEOMETRY_DARK_THRESHOLD = 170
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def reference(value):
    return {k: value[k] for k in ("artifact_id", "revision", "content_hash")}


def _docref(value):
    return {"artifact_id": value["artifact_id"], "content_hash": digest(value)}


def _flags():
    return dict(decision="HOLD", complete=False, transcription_verified=False,
                business_acceptance=False, platform_actions=[], new_model_calls=0)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _same(left, right):
    return digest(left) == digest(right)


def _ref_valid(value):
    return (isinstance(value, dict) and set(value) == {"artifact_id", "revision", "content_hash"}
            and _text(value["artifact_id"]) and type(value["revision"]) is int and value["revision"] >= 1
            and isinstance(value["content_hash"], str) and bool(_HASH.fullmatch(value["content_hash"])))


def _checked(value, schema, kind):
    if (not isinstance(value, dict) or value.get("schema_version") not in schema or value.get("kind") != kind
            or not _ref_valid({k: value.get(k) for k in ("artifact_id", "revision", "content_hash")}) or not _text(value.get("book_id")) or not _text(value.get("scope_id"))
            or not isinstance(value.get("payload"), dict) or value.get("content_hash") != digest(value["payload"])):
        raise ValueError("content revision artifact schema, identity or payload changed")


def _inputs(evidence, graph, check):
    _checked(evidence, {"b-evidence-trial/0.2", "b-evidence-trial/0.3"}, "EvidenceBundleTrial")
    _checked(graph, {"b-graph-trial/0.5"}, "QuestionGraphTrial")
    _checked(check, {"b-check-trial/0.5"}, "CheckReportTrial")
    if (any((v["book_id"], v["scope_id"]) != (evidence["book_id"], evidence["scope_id"]) for v in (graph, check))
            or not any(_same(reference(evidence), ref) for ref in graph.get("input_refs", []))
            or not _same(check["payload"].get("evidence_ref"), reference(evidence)) or not _same(check["payload"].get("graph_ref"), reference(graph))
            or not _same(check.get("input_refs", [])[:2], [reference(evidence), reference(graph)])
            or "content_revision" in graph["payload"]):
        raise ValueError("content revision requires the exact current E/G05/Check05")
    if not _same({k: check["payload"].get(k) for k in _flags()}, _flags()):
        raise ValueError("content revision cannot consume acceptance or action claims")
    inline = graph["payload"].get("inline_content")
    if not isinstance(inline, dict) or not _same({k: inline.get(k) for k in _flags()}, _flags()):
        raise ValueError("content revision requires unselected inline source evidence")
    base = inline.get("base_graph_archive")
    _checked(base, {"b-graph-trial/0.2", "b-graph-trial/0.3", "b-graph-trial/0.4"}, "QuestionGraphTrial")
    if not _same({k: v for k, v in graph["payload"].items() if k != "inline_content"}, base["payload"]):
        raise ValueError("G05 business core is not its immutable inline base")


def _span(value, limit):
    return (isinstance(value, list) and len(value) == 2 and all(type(n) is int for n in value)
            and 0 <= value[0] < value[1] <= limit)


def _visible(answer):
    """Visible original fragments in render order, retaining image barriers."""
    fragments = answer["fragments"]
    by_id = {f["fragment_id"]: f for f in fragments}
    if len(by_id) != len(fragments):
        raise ValueError("duplicate original answer fragment")
    order, blocks = [], []
    if "render_regions" in answer:
        seen = set()
        for region in answer["render_regions"]:
            if region.get("content_type") != "text":
                blocks.append(("BARRIER", region.get("region_id")))
                continue
            ids = region.get("source_fragment_ids", [])
            if not ids or len(ids) != len(set(ids)):
                raise ValueError("text region lacks unique original fragments")
            roles = set()
            for fid in ids:
                f = by_id.get(fid)
                if f is None or fid in seen:
                    raise ValueError("text source fragment missing or multiply rendered")
                seen.add(fid)
                if f.get("structural_marker") is True:
                    blocks.append(("BARRIER", fid)); continue
                if (f.get("content_type") != "text" or f.get("role") not in {"answer", "explanation"}
                        or f.get("represented_by_image_region") is not None or f.get("render_as_separate_region") is False
                        or f.get("asset_id") != region.get("asset_id") or f.get("role") != region.get("role")):
                    raise ValueError("mixed, diagnostic or nontext fragment in a body region")
                roles.add(f["role"]); order.append(f)
            if len(roles) > 1:
                raise ValueError("mixed roles in a text region")
            blocks.append(("TEXT", tuple(fid for fid in ids if not by_id[fid].get("structural_marker"))))
    else:
        for f in fragments:
            if (f.get("content_type") == "text" and f.get("role") in {"answer", "explanation"}
                    and not f.get("structural_marker") and f.get("represented_by_image_region") is None
                    and f.get("render_as_separate_region") is not False):
                order.append(f); blocks.append(("TEXT", (f["fragment_id"],)))
            else: blocks.append(("BARRIER", f["fragment_id"]))
    return order, blocks


def _source(evidence, graph, answer_id, fragment_id, role):
    answers = [a for a in graph["payload"]["answers"] if a["answer_id"] == answer_id]
    if len(answers) != 1:
        raise ValueError("target answer is missing or ambiguous")
    answer = answers[0]
    matches = [f for a in graph["payload"]["answers"] for f in a["fragments"] if f["fragment_id"] == fragment_id]
    if len(matches) != 1 or matches[0] not in answer["fragments"]:
        raise ValueError("target fragment is missing, duplicated or belongs to another answer")
    f = matches[0]
    visible, _ = _visible(answer)
    if role not in {"answer", "explanation"} or f.get("role") != role or f not in visible:
        raise ValueError("target is not visible nonstructural text in the declared role")
    pages = [p for p in evidence["payload"]["pages"] if p["asset_id"] == f["asset_id"]]
    if len(pages) != 1:
        raise ValueError("target fragment source page is not unique")
    page = pages[0]
    raw = {l["line_id"]: l for l in page["ocr_lines"]}
    elements = page["ocr_lines"]+page.get("answer_detail_lines", [])
    refs = f.get("evidence_refs")
    matches = [l for l in elements if isinstance(refs, list) and len(refs) == 1 and l["line_id"] == refs[0]]
    if len(matches) != 1:
        raise ValueError("target requires one exact raw/detail source element")
    line = matches[0]
    if not _text(line.get("text")) or not isinstance(line.get("bbox"), list) or not valid_bbox(line["bbox"], page["source"]["width"], page["source"]["height"]):
        raise ValueError("target source text or original page geometry is invalid")
    parent = line["line_id"] if line["line_id"] in raw else line.get("parent_line_id")
    span = f.get("text_span")
    if (parent not in raw or f.get("parent_line_id") != parent or not _span(span, len(line["text"]))
            or f.get("raw_text") != line["text"] or f["text"] != line["text"][span[0]:span[1]]
            or not _same(f["bbox"], line["bbox"]) or f.get("source_sha256", page["source"]["sha256"]) != page["source"]["sha256"]
            or not _same(f.get("section_path"), answer["section_path"])
            or any(not _same(f.get(k), raw[parent].get("location", {}).get(k)) for k in ("column", "window_index"))
            or not _same(raw[parent].get("location", {}).get("section_path"), answer["section_path"])):
        raise ValueError("target text/span/parent/geometry differs from its actual source")
    rows = [r for r in graph["payload"]["answer_coverage"] if r.get("line_id") == parent and r.get("asset_id") == page["asset_id"]]
    allocation = {"answer_id": answer_id, "fragment_id": fragment_id, "evidence_refs": refs, "text_span": span}
    if (len(rows) != 1 or rows[0].get("status") != "CONSUMED"
            or answer_id not in rows[0].get("answer_ids", []) or fragment_id not in rows[0].get("fragment_ids", [])
            or sum(_same(a, allocation) for a in rows[0].get("allocations", [])) != 1):
        raise ValueError("target is not exactly allocated to the current source owner")
    return answer, f, page, line, parent


def _source_span(f, line, parent, span):
    return {"fragment_id": f["fragment_id"], "fragment_span": copy.deepcopy(span), "source_element_ref": line["line_id"],
            "source_element_span": [f["text_span"][0]+span[0], f["text_span"][0]+span[1]], "parent_line_id": parent}


def _replacement(text):
    if not isinstance(text, str) or not text or "\r" in text or "\0" in text:
        raise ValueError("replacement must be nonempty exact text without CR/NUL")


def _integer_box(value):
    return (isinstance(value, list) and len(value) == 4 and all(type(n) is int for n in value)
            and 0 <= value[0] < value[2] and 0 <= value[1] < value[3])


def _contains(outer, inner):
    return outer[0] <= inner[0] < inner[2] <= outer[2] and outer[1] <= inner[1] < inner[3] <= outer[3]


def _intersects(left, right):
    return max(left[0], right[0]) < min(left[2], right[2]) and max(left[1], right[1]) < min(left[3], right[3])


def _geometry_syntax(operation):
    revisions = operation.get("source_geometry_revisions")
    if not isinstance(revisions, list) or not revisions:
        raise ValueError("source geometry revisions must be a nonempty explicit list")
    seen = set()
    for value in revisions:
        keys = {"revision_id", "fragment_id", "source_sha256", "original_bbox", "revised_bbox",
                "trimmed_bbox", "trimmed_crop_rgb_sha256", "dark_threshold", "trimmed_dark_pixels",
                "affected_fragment_overlaps", "affected_ocr_overlaps", "reason", "verification_status"}
        if (not isinstance(value, dict) or set(value) != keys or not _text(value.get("revision_id"))
                or value["revision_id"] in seen or not _text(value.get("fragment_id"))
                or value.get("source_sha256") != operation["source_region"]["source_sha256"]
                or not isinstance(value.get("trimmed_crop_rgb_sha256"), str)
                or not _HASH.fullmatch(value["trimmed_crop_rgb_sha256"])
                or type(value.get("dark_threshold")) is not int or value["dark_threshold"] != GEOMETRY_DARK_THRESHOLD
                or type(value.get("trimmed_dark_pixels")) is not int or value["trimmed_dark_pixels"] != 0
                or value.get("verification_status") != "UNVERIFIED" or not _text(value.get("reason"))):
            raise ValueError("source geometry revision identity, fixed pixel policy or status is invalid")
        seen.add(value["revision_id"])
        original, revised, trimmed = value["original_bbox"], value["revised_bbox"], value["trimmed_bbox"]
        if not all(_integer_box(box) for box in (original, revised, trimmed)):
            raise ValueError("geometry revision may only remove one exact edge rectangle")
        edge_trims = [
            original[0] == revised[0] and original[2:] == revised[2:] and original[1] < revised[1] < original[3]
            and trimmed == [original[0], original[1], original[2], revised[1]],
            original[:3] == revised[:3] and original[1] == revised[1] and original[1] < revised[3] < original[3]
            and trimmed == [original[0], revised[3], original[2], original[3]],
            original[1:] == revised[1:] and original[0] < revised[0] < original[2]
            and trimmed == [original[0], original[1], revised[0], original[3]],
            original[:2] == revised[:2] and original[3] == revised[3] and original[0] < revised[2] < original[2]
            and trimmed == [revised[2], original[1], original[2], original[3]],
        ]
        if sum(edge_trims) != 1 or _intersects(trimmed, revised):
            raise ValueError("geometry revision may only remove one exact edge rectangle")
        overlaps = value.get("affected_fragment_overlaps")
        overlap_keys = {"owner_kind", "owner_id", "fragment_id", "original_bbox"}
        ocr = value.get("affected_ocr_overlaps"); ocr_keys = {"asset_id", "line_id", "original_bbox", "coverage_status"}
        if (not isinstance(overlaps, list)
                or any(not isinstance(item, dict) or set(item) != overlap_keys
                       or item.get("owner_kind") not in {"answer", "question"}
                       or not _text(item.get("owner_id")) or not _text(item.get("fragment_id"))
                       or not _integer_box(item.get("original_bbox")) for item in overlaps)
                or len({(item["owner_kind"], item["owner_id"], item["fragment_id"]) for item in overlaps}) != len(overlaps)
                or not isinstance(ocr, list) or any(not isinstance(item, dict) or set(item) != ocr_keys
                    or not _text(item.get("asset_id")) or not _text(item.get("line_id"))
                    or not _integer_box(item.get("original_bbox")) or item.get("coverage_status") not in {"CONSUMED", "EXCLUDED", "UNASSIGNED"} for item in ocr)
                or len({(item["asset_id"], item["line_id"]) for item in ocr}) != len(ocr) or not overlaps and not ocr):
            raise ValueError("geometry revision must enumerate unique affected source overlaps")
    if len({value["fragment_id"] for value in revisions}) != len(revisions):
        raise ValueError("a target fragment may have only one source geometry revision")


def _region_syntax(operation):
    target, source, blocks = operation["target"], operation["source_region"], operation["blocks"]
    if (not isinstance(target, dict) or set(target) != {"answer_id", "role", "source_fragment_ids"}
            or not _text(target.get("answer_id")) or target.get("role") not in {"answer", "explanation"}
            or not isinstance(target.get("source_fragment_ids"), list) or not target["source_fragment_ids"]
            or not all(_text(fid) for fid in target["source_fragment_ids"])
            or len(set(target["source_fragment_ids"])) != len(target["source_fragment_ids"])):
        raise ValueError("region target requires unique original source fragments")
    if (not isinstance(source, dict) or set(source) != {"asset_id", "source_sha256", "source_size", "bbox"}
            or not _text(source.get("asset_id")) or not isinstance(source.get("source_sha256"), str)
            or not _HASH.fullmatch(source["source_sha256"]) or not _integer_box(source.get("bbox"))
            or not isinstance(source.get("source_size"), list) or len(source["source_size"]) != 2
            or not all(type(v) is int and v > 0 for v in source["source_size"])
            or not valid_bbox(source["bbox"], *source["source_size"])):
        raise ValueError("region source requires an integer box and exact page identity")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("region rebuild requires ordered draft blocks")
    seen, allocated = set(), []
    for block in blocks:
        if (not isinstance(block, dict) or set(block) != {"block_id", "bbox", "source_fragment_ids", "runs", "note"}
                or not _text(block.get("block_id")) or block["block_id"] in seen or not _text(block.get("note"))
                or not _integer_box(block.get("bbox")) or not _contains(source["bbox"], block["bbox"])
                or not isinstance(block.get("source_fragment_ids"), list)
                or not all(_text(fid) for fid in block["source_fragment_ids"])
                or not isinstance(block.get("runs"), list) or not block["runs"]):
            raise ValueError("region block has invalid identity, source box or runs")
        seen.add(block["block_id"]); allocated.extend(block["source_fragment_ids"])
        for run in block["runs"]:
            if not isinstance(run, dict) or set(run) != {"format", "text"} or run.get("format") not in {"plain", "latex"}:
                raise ValueError("region run must explicitly retain plain or LaTeX text")
            _replacement(run["text"])
    if len(allocated) != len(set(allocated)) or set(allocated) != set(target["source_fragment_ids"]):
        raise ValueError("each region target fragment must belong to exactly one block")
    for block in blocks:
        if [fid for fid in target["source_fragment_ids"] if fid in block["source_fragment_ids"]] != block["source_fragment_ids"]:
            raise ValueError("block source IDs must retain their original relative order")
    if any(_intersects(left["bbox"], right["bbox"]) for i, left in enumerate(blocks) for right in blocks[i+1:]):
        raise ValueError("draft region blocks overlap")
    if "source_geometry_revisions" in operation:
        _geometry_syntax(operation)


def _region_boxes(graph, answer, selected, operation):
    """Return explicit effective boxes without mutating immutable fragments."""
    revisions = operation.get("source_geometry_revisions", [])
    by_id = {value[1]["fragment_id"]: value[1] for value in selected}
    effective = {fid: copy.deepcopy(fragment["bbox"]) for fid, fragment in by_id.items()}
    wanted = set(by_id)
    actual_all = []
    page = selected[0][2]; parents = {value[4] for value in selected}
    for revision in revisions:
        fid = revision["fragment_id"]
        if fid not in by_id or revision["original_bbox"] != by_id[fid]["bbox"]:
            raise ValueError("geometry revision original box differs from its immutable target fragment")
        effective[fid] = copy.deepcopy(revision["revised_bbox"])
        actual = []
        for collection_name in ("answers", "questions"):
            for owner in graph["payload"][collection_name]:
                for fragment in owner.get("fragments", []):
                    if (fragment.get("asset_id", owner.get("asset_id")) != operation["source_region"]["asset_id"]
                            or not fragment.get("bbox") or collection_name == "answers"
                            and owner.get("answer_id") == answer["answer_id"] and fragment.get("fragment_id") in wanted):
                        continue
                    if _intersects(revision["original_bbox"], fragment["bbox"]) and not _intersects(revision["revised_bbox"], fragment["bbox"]):
                        actual.append({"owner_kind": "answer" if collection_name == "answers" else "question",
                            "owner_id": owner["answer_id"] if collection_name == "answers" else owner["question_id"],
                            "fragment_id": fragment["fragment_id"], "original_bbox": copy.deepcopy(fragment["bbox"])})
        if sorted(actual, key=lambda item: (item["owner_kind"], item["owner_id"], item["fragment_id"])) != sorted(
                revision["affected_fragment_overlaps"], key=lambda item: (item["owner_kind"], item["owner_id"], item["fragment_id"])):
            raise ValueError("geometry revision affected overlaps are not the complete current conflict set")
        actual_ocr = []
        for line in page["ocr_lines"]:
            if line["line_id"] in parents or not _intersects(revision["original_bbox"], line["bbox"]) or _intersects(revision["revised_bbox"], line["bbox"]):
                continue
            rows = [row for row in graph["payload"]["answer_coverage"] if row.get("asset_id") == page["asset_id"] and row.get("line_id") == line["line_id"]]
            if len(rows) != 1:
                raise ValueError("geometry revision conflicting OCR line has no exact coverage row")
            actual_ocr.append({"asset_id": page["asset_id"], "line_id": line["line_id"],
                "original_bbox": copy.deepcopy(line["bbox"]), "coverage_status": rows[0]["status"]})
        if sorted(actual_ocr, key=lambda item: (item["asset_id"], item["line_id"])) != sorted(
                revision["affected_ocr_overlaps"], key=lambda item: (item["asset_id"], item["line_id"])):
            raise ValueError("geometry revision affected OCR overlaps are not the complete current conflict set")
        actual_all.extend(actual); actual_all.extend(actual_ocr)
    if revisions and not actual_all:
        raise ValueError("geometry revision does not resolve an actual current source conflict")
    if revisions:
        boxes = list(effective.values())
        union = [min(box[0] for box in boxes), min(box[1] for box in boxes),
                 max(box[2] for box in boxes), max(box[3] for box in boxes)]
        if operation["source_region"]["bbox"] != union:
            raise ValueError("geometry-revised source region must be the exact effective target union")
    return effective


def _region(evidence, graph, operation):
    """Bind a draft to current source geometry without inventing OCR characters."""
    target, source = operation["target"], operation["source_region"]
    selected = [_source(evidence, graph, target["answer_id"], fid, target["role"]) for fid in target["source_fragment_ids"]]
    answer, page = selected[0][0], selected[0][2]
    if "render_regions" not in answer and any(v.get("content_type") == "image" or v.get("represented_by_image_region") is not None
            for v in answer["fragments"]+answer.get("regions", [])):
        raise ValueError("legacy image presentation needs a proven typed migration before region reconstruction")
    effective = _region_boxes(graph, answer, selected, operation)
    if (any(v[2]["asset_id"] != source["asset_id"] for v in selected)
            or source["source_sha256"] != page["source"]["sha256"]
            or not _same(source["source_size"], [page["source"]["width"], page["source"]["height"]])
            or any(not _contains(source["bbox"], effective[v[1]["fragment_id"]]) for v in selected)):
        raise ValueError("draft region does not exactly bind its current source page and fragments")
    locations = [v[3].get("location") for v in selected]
    loc = locations[0]
    if (not isinstance(loc, dict) or any(not _same(loc, other) for other in locations)
            or any(type(loc.get(k)) is not int or loc[k] < 0 for k in ("column", "window_index"))
            or not isinstance(loc.get("section_path"), list) or not loc["section_path"] or not all(_text(v) for v in loc["section_path"])):
        raise ValueError("draft region crosses or lacks a proven source location")
    ids = target["source_fragment_ids"]; wanted = set(ids)
    visible, rendering = _visible(answer)
    if [f["fragment_id"] for f in visible if f["fragment_id"] in wanted] != ids:
        raise ValueError("draft region target must retain the original visible fragment order")
    positions = [i for i, (_, members) in enumerate(rendering) if isinstance(members, tuple) and wanted.intersection(members)]
    if not positions:
        raise ValueError("draft region has no original visible rendering interval")
    interval = rendering[positions[0]:positions[-1]+1]
    if any(kind != "TEXT" or not members or not set(members).issubset(wanted) for kind, members in interval):
        raise ValueError("draft region crosses a picture, structural, role or untargeted text barrier")
    for collection_name in ("answers", "questions"):
        collection = graph["payload"][collection_name]
        for owner in collection:
            for f in owner.get("fragments", []):
                if f.get("asset_id", owner.get("asset_id")) != source["asset_id"] or not f.get("bbox"):
                    continue
                is_target = collection_name == "answers" and owner.get("answer_id") == answer["answer_id"] and f.get("fragment_id") in wanted
                if _intersects(source["bbox"], f["bbox"]) and not is_target:
                    raise ValueError("draft region overlaps other visible, structural or diagnostic source text")
            for region in owner.get("render_regions", []):
                if region.get("asset_id") == source["asset_id"] and region.get("content_type") != "text" and _intersects(source["bbox"], region["bbox"]):
                    raise ValueError("draft region overlaps an original picture")
    parents = {v[4] for v in selected}
    for line in page["ocr_lines"]:
        if not _intersects(source["bbox"], line["bbox"]): continue
        rows = [r for r in graph["payload"]["answer_coverage"] if r.get("asset_id") == page["asset_id"] and r.get("line_id") == line["line_id"]]
        if (line["line_id"] not in parents or len(rows) != 1 or rows[0].get("status") != "CONSUMED"
                or not rows[0].get("allocations") or any(a.get("fragment_id") not in wanted or a.get("answer_id") != answer["answer_id"] for a in rows[0]["allocations"])):
            raise ValueError("draft region swallows an untargeted, unassigned or excluded OCR line")
    for block in operation["blocks"]:
        if any(not _contains(block["bbox"], effective[fid]) for fid in block["source_fragment_ids"]):
            raise ValueError("draft block clips an assigned original fragment")
    spans = [_source_span(v[1], v[3], v[4], [0, len(v[1]["text"])]) for v in selected]
    return answer, spans


def _select(graph, target, f, parent, operation):
    inline = graph["payload"]["inline_content"]
    candidates = [c for c in inline["candidates"] if c["candidate_id"] == operation["candidate_id"]]
    calls = [c for c in inline["calls"] if c["plan"]["call_id"] == operation["call_id"]]
    units = {u["unit_id"]: u for u in inline["units"]}
    if len(units) != len(inline["units"]) or len(candidates) != 1 or len(calls) != 1 or operation["unit_id"] not in units:
        raise ValueError("selected inline candidate/call/unit is not unique")
    candidate, call, unit = candidates[0], calls[0], units[operation["unit_id"]]
    observed = call.get("observation")
    if isinstance(observed, dict):
        _checked(observed, {"b-inline-formula-call-trial/0.1"}, "InlineFormulaCallTrial")
    if (candidate["call_id"] != operation["call_id"] or candidate["state"] != "DONE" or call["state"] != "DONE"
            or not isinstance(call.get("observation"), dict) or candidate["raw_latex"] != call["observation"]["payload"]["raw_latex"]
            or candidate["parse_result"].get("raw_latex") != candidate["raw_latex"]
            or not _same(candidate["observation_ref"], reference(call["observation"]))
            or not _same(call["observation"]["payload"]["plan"], call["plan"])
            or call["observation"]["payload"].get("recognition_error") is not None
            or not _same(candidate["unit_bindings"], call["plan"]["unit_bindings"])
            or not any(b["unit_id"] == operation["unit_id"] and b["line_id"] == parent for b in candidate["unit_bindings"])
            or any(b["line_id"] != parent for b in candidate["unit_bindings"])
            or unit["line_id"] != parent or unit["asset_id"] != f["asset_id"]):
        raise ValueError("selected candidate does not bind this source row and current owner")
    owners = [b for b in inline["bindings"] if b["line_id"] == parent]
    if (len(owners) != 1 or owners[0].get("unassigned") is not False
            or not any(b["fragment_id"] == f["fragment_id"] and b["answer_id"] == target["answer_id"] and b["role"] == target["role"] for b in owners[0]["fragments"])
            or any(b["answer_id"] != target["answer_id"] or b["role"] != target["role"] for b in owners[0]["fragments"])):
        raise ValueError("selected inline row has no unique compatible current owner")
    _replacement(candidate["raw_latex"])
    return candidate["raw_latex"]


def _join(evidence, graph, operation):
    proposals = [p for p in graph["payload"]["inline_content"]["continuity"]["payload"]["proposals"] if p["proposal_id"] == operation["proposal_id"]]
    if len(proposals) != 1:
        raise ValueError("join requires an existing unique current wrap proposal")
    proposal = proposals[0]
    if len(proposal.get("bindings", [])) != 2 or len(proposal.get("source_spans", [])) != 2:
        raise ValueError("join requires exactly two source spans and bindings")
    selected, spans = [], []
    for binding, source in zip(proposal["bindings"], proposal["source_spans"]):
        if len(binding.get("fragments", [])) != 1:
            raise ValueError("join requires one source fragment per rendering block")
        bf = binding["fragments"][0]
        a, f, page, line, parent = _source(evidence, graph, binding["answer_id"], bf["fragment_id"], binding["role"])
        interval = source.get("text_span")
        if (line["line_id"] != parent or source.get("line_id") != parent or source.get("asset_id") != f["asset_id"]
                or not _span(interval, len(line["text"])) or source.get("text") != line["text"][interval[0]:interval[1]]
                or not _same(bf.get("text_span"), f["text_span"]) or not _same(bf.get("overlap_span"), interval)
                or not f["text_span"][0] <= interval[0] < interval[1] <= f["text_span"][1]):
            raise ValueError("join proposal is not literal current raw source spans")
        local = [interval[0]-f["text_span"][0], interval[1]-f["text_span"][0]]
        spans.append(_source_span(f, line, parent, local)); selected.append((a, f, page, line))
    left, right = selected
    if (left[0]["answer_id"] != right[0]["answer_id"] or left[1]["role"] != right[1]["role"] or left[1]["asset_id"] != right[1]["asset_id"]
            or spans[0]["fragment_span"][1] != len(left[1]["text"]) or spans[1]["fragment_span"][0] != 0
            or left[1]["fragment_id"] == right[1]["fragment_id"]):
        raise ValueError("join crosses an answer/role/source or is not an end-to-start separator")
    _, blocks = _visible(left[0]); pair = [("TEXT", (left[1]["fragment_id"],)), ("TEXT", (right[1]["fragment_id"],))]
    if not any(blocks[i:i+2] == pair for i in range(len(blocks)-1)):
        raise ValueError("join blocks are not adjacent visible text with no image/role barrier")
    lrow, rrow = left[3], right[3]
    loc = lrow.get("location")
    if (not isinstance(loc, dict) or not _same(loc, rrow.get("location"))
            or any(type(loc.get(k)) is not int or loc[k] < 0 for k in ("column", "window_index"))
            or not isinstance(loc.get("section_path"), list) or not loc["section_path"] or not all(_text(v) for v in loc["section_path"])):
        raise ValueError("join source rows cross a column/window or lack exact scope")
    if re.match(r"^\s*(?:\d+\s*[.、](?!\d)|[A-G]\s*[.、]|[（(]\d+[）)]|[①②③④⑤⑥⑦⑧⑨⑩])", rrow["text"]):
        raise ValueError("join next row looks like a new question or subquestion")
    order = lambda row: ((row["bbox"][1]+row["bbox"][3])/2, row["bbox"][0], row["line_id"])
    if (order(lrow) >= order(rrow) or any(_same(r.get("location"), loc) and order(lrow) < order(r) < order(rrow) for r in left[2]["ocr_lines"])):
        raise ValueError("join skips or reverses an intervening raw source row")
    lb, rb = lrow["bbox"], rrow["bbox"]
    lh, rh = lb[3]-lb[1], rb[3]-rb[1]
    overlap = max(0, min(lb[2], rb[2])-max(lb[0], rb[0]))
    if (not 0 <= rb[1]-lb[3] <= 2.5*max(lh, rh)
            or overlap < .5*min(lb[2]-lb[0], rb[2]-rb[0])):
        raise ValueError("join source rows lack adjacent overlapping geometry")
    lt, rt = [source["text"] for source in proposal["source_spans"]]
    valid = (proposal.get("kind") == "OPEN_EQUATION_LINE_WRAP" and lt[-1:] in "=+−-×÷*/^_(（<≤≥>:："
             or proposal.get("kind") == "CHAINED_RELATION_LINE_WRAP" and rt[:1] in "<>≤≥" and any(c in lt for c in "<>≤≥"))
    if not valid or not any(c.isalnum() for c in lt) or not any(c.isalnum() for c in rt) or proposal.get("joined_raw_text") != lt+rt:
        raise ValueError("join proposal is not a literal mathematical continuation")
    return left[0], left[1]["role"], [left[1]["fragment_id"], right[1]["fragment_id"]], spans


def _syntax(plan, depth=0):
    if depth >= 32 or not isinstance(plan, dict):
        raise ValueError("revision plan lineage exceeds 32 versions or is invalid")
    keys = {"schema_version", "kind", "artifact_id", "revision", "book_id", "scope_id", "payload", "content_hash"}
    if set(plan) != keys:
        raise ValueError("revision plan has unrecognized envelope fields")
    _checked(plan, {PLAN_SCHEMA, REGION_PLAN_SCHEMA, GEOMETRY_PLAN_SCHEMA}, "ContentRevisionPlanTrial")
    body = {k: v for k, v in plan.items() if k not in {"artifact_id", "content_hash"}}
    if plan["artifact_id"] != "content-revision-plan-"+digest(body)[:24]:
        raise ValueError("revision plan deterministic identity changed")
    p = plan["payload"]
    if set(p) != {"evidence_ref", "graph_ref", "base_check_ref", "previous_plan_archive", "author", "operations"}|set(_flags()):
        raise ValueError("revision plan has unrecognized payload fields")
    if not _same({k: p[k] for k in _flags()}, _flags()) or not all(_ref_valid(p[k]) for k in ("evidence_ref", "graph_ref", "base_check_ref")):
        raise ValueError("revision plan has invalid refs or approval claims")
    author = p["author"]
    if (not isinstance(author, dict) or set(author) != {"kind", "id", "note"} or author["kind"] not in {"MODEL_DRAFT", "HUMAN_DRAFT", "SYNTHETIC_TEST"}
            or not _text(author["id"]) or not _text(author["note"])):
        raise ValueError("revision plan needs explicit draft authorship")
    if not isinstance(p["operations"], list):
        raise ValueError("revision operations must be an ordered list")
    seen = set()
    for operation in p["operations"]:
        if not isinstance(operation, dict) or not _text(operation.get("operation_id")) or operation["operation_id"] in seen or not _text(operation.get("reason")):
            raise ValueError("revision operation needs a unique ID and reason")
        seen.add(operation["operation_id"])
        kind = operation.get("kind")
        expected = {"EDIT_TEXT": {"target", "replacement", "format"}, "SELECT_INLINE": {"target", "candidate_id", "call_id", "unit_id"},
                    "JOIN_RAW_WRAP": {"proposal_id"}, "REBUILD_TEXT_REGION": {"target", "source_region", "blocks"}}
        fields = expected.get(kind)
        if kind == "REBUILD_TEXT_REGION" and "source_geometry_revisions" in operation:
            if plan["schema_version"] != GEOMETRY_PLAN_SCHEMA:
                raise ValueError("source geometry revisions require revision plan 0.3")
            fields = fields|{"source_geometry_revisions"}
        if kind not in expected or set(operation) != {"operation_id", "kind", "reason"}|fields:
            raise ValueError("unknown revision operation or fields")
        if kind == "REBUILD_TEXT_REGION":
            if plan["schema_version"] not in {REGION_PLAN_SCHEMA, GEOMETRY_PLAN_SCHEMA}:
                raise ValueError("region reconstruction requires revision plan 0.2 or 0.3")
            _region_syntax(operation)
            continue
        if kind != "JOIN_RAW_WRAP":
            target = operation["target"]
            if (not isinstance(target, dict) or set(target) != {"answer_id", "fragment_id", "role", "fragment_span", "expected_text"}
                    or not all(_text(target.get(k)) for k in ("answer_id", "fragment_id", "role"))
                    or not isinstance(target.get("expected_text"), str) or not target["expected_text"]
                    or target["role"] not in {"answer", "explanation"}):
                raise ValueError("invalid exact revision target")
        if kind == "EDIT_TEXT":
            _replacement(operation["replacement"])
            if operation["format"] not in {"plain", "latex"}: raise ValueError("unknown revision text format")
        else:
            for key in expected[kind]-{"target"}:
                if not _text(operation[key]): raise ValueError("missing revision selection/join identity")
    previous = p["previous_plan_archive"]
    if plan["revision"] == 1:
        if previous is not None: raise ValueError("first revision cannot have an earlier plan")
    else:
        _syntax(previous, depth+1)
        if (previous["revision"]+1 != plan["revision"] or any(previous[k] != plan[k] for k in ("book_id", "scope_id"))
                or not _same(previous["payload"]["evidence_ref"], p["evidence_ref"])
                or not _same(previous["payload"]["graph_ref"], p["graph_ref"])
                or previous["schema_version"] in {REGION_PLAN_SCHEMA, GEOMETRY_PLAN_SCHEMA}
                and plan["schema_version"] not in {REGION_PLAN_SCHEMA, GEOMETRY_PLAN_SCHEMA}
                or previous["schema_version"] == GEOMETRY_PLAN_SCHEMA and plan["schema_version"] != GEOMETRY_PLAN_SCHEMA):
            raise ValueError("revision lineage must retain its original current E/G05")


def _operations(plan, evidence, graph):
    bindings, intervals, joins = [], {}, set()
    for op in plan["payload"]["operations"]:
        b = {"operation_id": op["operation_id"], "kind": op["kind"], "answer_id": None, "role": None,
             "fragment_ids": [], "source_spans": [], "replacement": None, "format": None,
             "candidate_id": None, "call_id": None, "unit_id": None, "proposal_id": None}
        if op["kind"] == "REBUILD_TEXT_REGION":
            a, spans = _region(evidence, graph, op)
            b.update(answer_id=a["answer_id"], role=op["target"]["role"], fragment_ids=copy.deepcopy(op["target"]["source_fragment_ids"]),
                source_spans=spans, replacement="\n".join("".join(run["text"] for run in block["runs"]) for block in op["blocks"]),
                format="mixed", region_operation=copy.deepcopy(op))
        elif op["kind"] == "JOIN_RAW_WRAP":
            a, role, ids, spans = _join(evidence, graph, op)
            pair = tuple(ids)
            if pair in joins: raise ValueError("duplicate join separator")
            joins.add(pair)
            b.update(answer_id=a["answer_id"], role=role, fragment_ids=ids, source_spans=spans, proposal_id=op["proposal_id"])
        else:
            target = op["target"]
            a, f, _, line, parent = _source(evidence, graph, target["answer_id"], target["fragment_id"], target["role"])
            span = target["fragment_span"]
            if not _span(span, len(f["text"])) or target["expected_text"] != f["text"][span[0]:span[1]]:
                raise ValueError("target interval is not an exact original fragment substring")
            prior = intervals.setdefault(f["fragment_id"], [])
            if any(max(span[0], old[0]) < min(span[1], old[1]) for old in prior):
                raise ValueError("overlapping content revision target intervals")
            prior.append(span)
            replacement = op["replacement"] if op["kind"] == "EDIT_TEXT" else _select(graph, target, f, parent, op)
            b.update(answer_id=a["answer_id"], role=f["role"], fragment_ids=[f["fragment_id"]],
                     source_spans=[_source_span(f, line, parent, span)], replacement=replacement,
                     format=op.get("format", "latex"))
            if op["kind"] == "SELECT_INLINE": b.update({k: op[k] for k in ("candidate_id", "call_id", "unit_id")})
        bindings.append(b)
    regions = [b for b in bindings if b["kind"] == "REBUILD_TEXT_REGION"]
    for region in regions:
        if any(set(region["fragment_ids"]).intersection(other["fragment_ids"]) for other in bindings if other is not region):
            raise ValueError("region target overlaps another edit, selection, join or region")
    for i, left in enumerate(regions):
        for right in regions[i+1:]:
            ls, rs = left["region_operation"]["source_region"], right["region_operation"]["source_region"]
            if ls["asset_id"] == rs["asset_id"] and _intersects(ls["bbox"], rs["bbox"]):
                raise ValueError("source regions of separate draft operations overlap")
    return bindings


def validate_revision_plan(plan, evidence, graph, check):
    _inputs(evidence, graph, check)
    _syntax(plan)
    p = plan["payload"]
    if ((plan["book_id"], plan["scope_id"]) != (evidence["book_id"], evidence["scope_id"])
            or not _same(p["evidence_ref"], reference(evidence)) or not _same(p["graph_ref"], reference(graph)) or not _same(p["base_check_ref"], reference(check))):
        raise ValueError("revision plan is stale for current E/G05/Check05")
    _operations(plan, evidence, graph)


def _validate_geometry_pixels(plan, evidence, source_path):
    revisions = [(op, revision) for op in plan["payload"]["operations"]
                 for revision in op.get("source_geometry_revisions", [])]
    if not revisions:
        return []
    if source_path is None:
        raise ValueError("source geometry revision requires the original source manifest at execution")
    manifest, assets = load_source(Path(source_path))
    if manifest["book_id"] != evidence["book_id"]:
        raise ValueError("source geometry manifest belongs to a different book")
    pages = {page["asset_id"]: page for page in evidence["payload"]["pages"]}
    available = {asset["asset_id"]: (asset, path) for asset, path in assets}
    receipts = []
    from PIL import Image
    for operation, revision in revisions:
        aid = operation["source_region"]["asset_id"]
        if aid not in available or aid not in pages:
            raise ValueError("source geometry image is absent from current manifest/evidence")
        asset, path = available[aid]; source = pages[aid]["source"]
        if (revision["source_sha256"] != asset["sha256"] or source["sha256"] != asset["sha256"]
                or operation["source_region"]["source_size"] != [asset["width"], asset["height"]]):
            raise ValueError("source geometry image identity differs from current evidence")
        with Image.open(path) as image:
            crop = image.convert("RGB").crop(tuple(revision["trimmed_bbox"]))
            raw = crop.tobytes()
            dark = sum(1 for r, g, b in crop.get_flattened_data()
                       if 299*r+587*g+114*b < GEOMETRY_DARK_THRESHOLD*1000)
        crop_sha = hashlib.sha256(raw).hexdigest()
        if (crop_sha != revision["trimmed_crop_rgb_sha256"] or type(revision["trimmed_dark_pixels"]) is not int
                or dark != revision["trimmed_dark_pixels"] or type(revision["dark_threshold"]) is not int
                or revision["dark_threshold"] != GEOMETRY_DARK_THRESHOLD or dark != 0):
            raise ValueError("source geometry trimmed pixels differ from the fixed zero-dark receipt")
        if file_digest(path) != asset["sha256"]:
            raise ValueError("source geometry image changed during execution")
        receipts.append({"revision_id": revision["revision_id"], "fragment_id": revision["fragment_id"],
            "source_sha256": asset["sha256"], "trimmed_bbox": copy.deepcopy(revision["trimmed_bbox"]),
            "trimmed_crop_rgb_sha256": crop_sha, "dark_threshold": GEOMETRY_DARK_THRESHOLD,
            "trimmed_dark_pixels": dark})
    return receipts


def make_revision_plan(evidence, graph, check, operations, author, *, previous_plan=None):
    if previous_plan is not None: _syntax(previous_plan)
    payload = {"evidence_ref": reference(evidence), "graph_ref": reference(graph), "base_check_ref": reference(check),
               "previous_plan_archive": copy.deepcopy(previous_plan), "author": copy.deepcopy(author), "operations": copy.deepcopy(operations), **_flags()}
    geometry_requested = isinstance(operations, list) and any(isinstance(o, dict) and o.get("source_geometry_revisions") for o in operations)
    region_requested = isinstance(operations, list) and any(isinstance(o, dict) and o.get("kind") == "REBUILD_TEXT_REGION" for o in operations)
    version = (GEOMETRY_PLAN_SCHEMA if geometry_requested or previous_plan and previous_plan["schema_version"] == GEOMETRY_PLAN_SCHEMA
               else REGION_PLAN_SCHEMA if region_requested or previous_plan and previous_plan["schema_version"] == REGION_PLAN_SCHEMA else PLAN_SCHEMA)
    body = {"schema_version": version, "kind": "ContentRevisionPlanTrial", "revision": previous_plan["revision"]+1 if previous_plan else 1,
            "book_id": evidence["book_id"], "scope_id": evidence["scope_id"], "payload": payload}
    result = {**body, "artifact_id": "content-revision-plan-"+digest(body)[:24], "content_hash": digest(payload)}
    validate_revision_plan(result, evidence, graph, check)
    return result


def _producer(operation):
    return {"module": __name__, "version": "0.1.0", "operation": operation, "code_sha256": code_digest(Path(__file__)),
            "dependency_code_sha256": {n: code_digest(Path(__file__).with_name(n+".py")) for n in ("baseline", "policy", "question_quality", "offline")},
            "identity_policy": IDENTITY_POLICY}


def _artifact(schema, kind, prefix, source, inputs, payload, operation, revision=1):
    body = {"schema_version": schema, "kind": kind, "revision": revision, "book_id": source["book_id"], "scope_id": source["scope_id"],
            "input_refs": inputs, "producer": _producer(operation), "payload": payload}
    return {**body, "artifact_id": prefix+"-"+digest(body)[:24], "content_hash": digest(payload)}


def _source_layer(graph):
    p = graph["payload"]
    return {"questions": [{k: v for k, v in q.items() if k not in {"candidate_answer_ids", "selected_answer_id", "type_candidate"}} for q in p["questions"]],
            "answers": [{"answer_id": a["answer_id"], "fragments": a["fragments"], "source_line_ids": a["source_line_ids"],
                "evidence_refs": a["evidence_refs"], "images": [r for r in a.get("render_regions", []) if r.get("content_type") == "image"]} for a in p["answers"]],
            "answer_coverage": p["answer_coverage"], "inline_content": p["inline_content"]}


def _content_fragment(evidence, graph, plan, f, bindings):
    edits = sorted([b for b in bindings if b["fragment_ids"] == [f["fragment_id"]] and b["kind"] != "JOIN_RAW_WRAP"],
                   key=lambda b: b["source_spans"][0]["fragment_span"])
    pieces, cursor, output = [], 0, 0
    def append(kind, lo, hi, text, operation_id=None, format="plain"):
        nonlocal output
        pieces.append({"kind": kind, "source_fragment_span": [lo, hi], "output_span": [output, output+len(text)],
                       "text": text, "operation_id": operation_id, "format": format})
        output += len(text)
    for b in edits:
        lo, hi = b["source_spans"][0]["fragment_span"]
        if lo > cursor: append("SOURCE", cursor, lo, f["text"][cursor:lo])
        append("REVISION", lo, hi, b["replacement"], b["operation_id"], b["format"])
        cursor = hi
    if cursor < len(f["text"]): append("SOURCE", cursor, len(f["text"]), f["text"][cursor:])
    value = {"source_fragment_id": f["fragment_id"], "role": f["role"], "asset_id": f["asset_id"], "source_element_ref": f["evidence_refs"][0],
        "source_text_span": copy.deepcopy(f["text_span"]), "source_fragment_text_sha256": _sha(f["text"]), "text": "".join(p["text"] for p in pieces),
        "pieces": pieces, "verification_status": "UNVERIFIED", "complete": False, "transcription_verified": False, "business_acceptance": False}
    return {"content_fragment_id": "content-fragment-"+digest([reference(evidence), reference(graph), reference(plan), value])[:24], **value}


def _region_fragment(evidence, graph, plan, binding, block):
    source = binding["region_operation"]["source_region"]
    value = {"kind": "REGION_DRAFT", "source_fragment_ids": copy.deepcopy(block["source_fragment_ids"]),
        "role": binding["role"], "asset_id": source["asset_id"], "bbox": copy.deepcopy(block["bbox"]),
        "source_region": copy.deepcopy(source), "block_id": block["block_id"], "text": "".join(run["text"] for run in block["runs"]),
        "runs": copy.deepcopy(block["runs"]), "operation_id": binding["operation_id"],
        **({"source_geometry_revisions": copy.deepcopy(binding["region_operation"]["source_geometry_revisions"])}
           if binding["region_operation"].get("source_geometry_revisions") else {}), "verification_status": "UNVERIFIED",
        "complete": False, "transcription_verified": False, "business_acceptance": False}
    return {"content_fragment_id": "content-fragment-"+digest([reference(evidence), reference(graph), reference(plan), value])[:24], **value}


def _text_region(evidence, graph, plan, content, original):
    source_ids = content["source_fragment_ids"] if content.get("kind") == "REGION_DRAFT" else [content["source_fragment_id"]]
    box = content["bbox"] if content.get("kind") == "REGION_DRAFT" else original[content["source_fragment_id"]]["bbox"]
    return {"region_id": "content-region-"+digest([reference(evidence), reference(graph), reference(plan), content["content_fragment_id"]])[:24],
        "content_type": "text", "role": content["role"], "asset_id": content["asset_id"], "bbox": copy.deepcopy(box), "text": content["text"],
        "source_fragment_ids": copy.deepcopy(source_ids), "content_fragment_ids": [content["content_fragment_id"]],
        "verification_status": "UNVERIFIED", "complete": False, "transcription_verified": False, "business_acceptance": False}


def _render_content(evidence, graph, plan, answer, content, region_bindings):
    old_regions = copy.deepcopy(answer.get("render_regions"))
    original = {f["fragment_id"]: f for f in answer["fragments"]}
    by_source = {c["source_fragment_id"]: c for c in content if "source_fragment_id" in c}
    if old_regions is None:
        if region_bindings:
            answer["render_regions"] = [_text_region(evidence, graph, plan, c, original) for c in content]
    else:
        by_target = {fid: b for b in region_bindings for fid in b["fragment_ids"]}
        rebuilt, emitted = [], set()
        for region in old_regions:
            operation = next((by_target[fid] for fid in region.get("source_fragment_ids", []) if fid in by_target), None)
            if operation is not None:
                if operation["operation_id"] not in emitted:
                    rebuilt.extend(_text_region(evidence, graph, plan, c, original) for c in content
                                   if c.get("operation_id") == operation["operation_id"] and c.get("kind") == "REGION_DRAFT")
                    emitted.add(operation["operation_id"])
                continue
            current = copy.deepcopy(region)
            if current.get("content_type") == "text":
                selected = [by_source[fid] for fid in current["source_fragment_ids"] if fid in by_source]
                if selected: current["text"] = "\n".join(c["text"] for c in selected)
            rebuilt.append(current)
        answer["render_regions"] = rebuilt
    if region_bindings or old_regions is not None and _same(answer.get("regions"), old_regions):
        answer["regions"] = copy.deepcopy(answer["render_regions"])


def _graph(evidence, graph, check, plan):
    bindings = _operations(plan, evidence, graph)
    payload = copy.deepcopy(graph["payload"])
    affected = {b["answer_id"] for b in bindings}
    for answer in payload["answers"]:
        if answer["answer_id"] not in affected: continue
        visible, _ = _visible(answer)
        region_bindings = [b for b in bindings if b["kind"] == "REBUILD_TEXT_REGION" and b["answer_id"] == answer["answer_id"]]
        by_target = {fid: b for b in region_bindings for fid in b["fragment_ids"]}
        content, emitted = [], set()
        for f in visible:
            region = by_target.get(f["fragment_id"])
            if region is None:
                content.append(_content_fragment(evidence, graph, plan, f, bindings))
            elif region["operation_id"] not in emitted:
                content.extend(_region_fragment(evidence, graph, plan, region, block) for block in region["region_operation"]["blocks"])
                emitted.add(region["operation_id"])
        joins = {tuple(b["fragment_ids"]): b["operation_id"] for b in bindings if b["kind"] == "JOIN_RAW_WRAP" and b["answer_id"] == answer["answer_id"]}
        separators = []
        for role, field in (("answer", "text"), ("explanation", "explanation_text")):
            selected = [c for c in content if c["role"] == role]
            text = selected[0]["text"] if selected else ""
            for left, right in zip(selected, selected[1:]):
                join = joins.get((left.get("source_fragment_id"), right.get("source_fragment_id")))
                separator = "" if join else "\n"
                separators.append({"role": role, "left_content_fragment_id": left["content_fragment_id"], "right_content_fragment_id": right["content_fragment_id"],
                                   "separator": separator, "join_operation_id": join})
                text += separator+right["text"]
            answer[field] = text
        _render_content(evidence, graph, plan, answer, content, region_bindings)
        projection = {"schema_version": ("b-content-projection-trial/0.3" if plan["schema_version"] == GEOMETRY_PLAN_SCHEMA
                      else "b-content-projection-trial/0.2" if plan["schema_version"] == REGION_PLAN_SCHEMA else "b-content-projection-trial/0.1"),
            "source_graph_ref": reference(graph), "plan_ref": reference(plan), "source_fragment_order": [f["fragment_id"] for f in visible],
            "separators": separators, "verification_status": "UNVERIFIED"}
        if plan["schema_version"] in {REGION_PLAN_SCHEMA, GEOMETRY_PLAN_SCHEMA}: projection["region_operations"] = [b["operation_id"] for b in region_bindings]
        answer.update(content_fragments=content, content_projection=projection, explanation_present=any(c["role"] == "explanation" for c in content),
            complete=False, transcription_verified=False, verification_status="UNVERIFIED")
    affected_questions = []
    for q, old in zip(payload["questions"], graph["payload"]["questions"]):
        key = scope_key(q["book_id"], q["section_path"], q["printed_number"])
        candidates = [a for a in payload["answers"] if scope_key(a["book_id"], a["section_path"], a["printed_number"]) == key]
        q["candidate_answer_ids"] = [a["answer_id"] for a in candidates]
        q["selected_answer_id"] = candidates[0]["answer_id"] if len(candidates) == 1 else None
        q["type_candidate"] = classify(q["text"], [f["option_label"] for f in q["fragments"] if f.get("option_start")], candidates[0]["text"] if len(candidates) == 1 else None)
        dependent = set(q["candidate_answer_ids"]+old["candidate_answer_ids"]+[q["selected_answer_id"], old["selected_answer_id"]]) & affected
        if dependent or not _same({k: q[k] for k in ("candidate_answer_ids", "selected_answer_id", "type_candidate")},
                                  {k: old[k] for k in ("candidate_answer_ids", "selected_answer_id", "type_candidate")}):
            affected_questions.append(q["question_id"])
    payload["unmatched_answer_ids"] = [a["answer_id"] for a in payload["answers"] if not any(a["answer_id"] in q["candidate_answer_ids"] for q in payload["questions"])]
    payload.update(_flags())
    proof = {"base_sha256": digest(_source_layer(graph)), "derived_sha256": digest(_source_layer({"payload": payload})), "equal": True}
    if proof["base_sha256"] != proof["derived_sha256"]: raise ValueError("content materialization changed a raw/image/source layer")
    payload["content_revision"] = {"schema_version": ("b-content-revision-state-trial/0.3" if plan["schema_version"] == GEOMETRY_PLAN_SCHEMA
        else "b-content-revision-state-trial/0.2" if plan["schema_version"] == REGION_PLAN_SCHEMA else "b-content-revision-state-trial/0.1"), "evidence_ref": reference(evidence),
        "base_graph_ref": reference(graph), "base_check_ref": reference(check), "plan_ref": reference(plan),
        "base_graph_archive": copy.deepcopy(graph), "base_check_archive": copy.deepcopy(check), "plan_archive": copy.deepcopy(plan),
        "operation_bindings": bindings, "affected_answer_ids": [a["answer_id"] for a in graph["payload"]["answers"] if a["answer_id"] in affected],
        "affected_question_ids": affected_questions, "source_layer_proof": proof,
        "matching_derivation": {"rule": "book+section_path+printed_number; unique candidate only",
            "questions": [{k: copy.deepcopy(q[k]) for k in ("question_id", "candidate_answer_ids", "selected_answer_id", "type_candidate")} for q in payload["questions"]],
            "unmatched_answer_ids": copy.deepcopy(payload["unmatched_answer_ids"]), "policy_code_sha256": code_digest(Path(__file__).with_name("policy.py"))}, **_flags()}
    graph_schema = (GEOMETRY_GRAPH_SCHEMA if plan["schema_version"] == GEOMETRY_PLAN_SCHEMA
                    else REGION_GRAPH_SCHEMA if plan["schema_version"] == REGION_PLAN_SCHEMA else GRAPH_SCHEMA)
    return _artifact(graph_schema, "QuestionGraphTrial", "content-graph", evidence,
        [reference(v) for v in (evidence, graph, check, plan)], payload, "graph", revision=graph["revision"]+1)


def apply_content_revision(evidence, graph, check, plan, *, source_path=None):
    validate_revision_plan(plan, evidence, graph, check)
    geometry_receipts = _validate_geometry_pixels(plan, evidence, source_path)
    derived = _graph(evidence, graph, check, plan)
    application_schema = (GEOMETRY_APPLICATION_SCHEMA if plan["schema_version"] == GEOMETRY_PLAN_SCHEMA
                          else REGION_APPLICATION_SCHEMA if plan["schema_version"] == REGION_PLAN_SCHEMA else APPLICATION_SCHEMA)
    return _artifact(application_schema, "ContentRevisionApplicationTrial", "content-revision-application", evidence,
        [reference(v) for v in (evidence, graph, check, plan)],
        {"evidence_ref": reference(evidence), "base_graph_ref": reference(graph), "base_check_ref": reference(check),
         "plan_ref": reference(plan), "graph": derived, **({"source_geometry_receipts": geometry_receipts} if geometry_receipts else {}), **_flags()}, "apply")


def rollback_content_revision(evidence, derived, *, expected_graph_ref, source_path=None):
    _checked(derived, {GRAPH_SCHEMA, REGION_GRAPH_SCHEMA, GEOMETRY_GRAPH_SCHEMA}, "QuestionGraphTrial")
    if not _ref_valid(expected_graph_ref) or not _same(expected_graph_ref, reference(derived)):
        raise ValueError("rollback differs from the independently retained graph version")
    state = derived["payload"].get("content_revision", {})
    base, check, plan = [state[k] for k in ("base_graph_archive", "base_check_archive", "plan_archive")]
    expected = apply_content_revision(evidence, base, check, plan, source_path=source_path)["payload"]["graph"]
    if not _same(expected, derived):
        raise ValueError("rollback would discard later graph edits or changed archives")
    return copy.deepcopy(base)


def _review(evidence, graph, check, review):
    base = check["payload"]["base_check_archive"]
    old_graph = graph["payload"]["inline_content"]["base_graph_archive"]
    _checked(base, {"b-check-trial/0.2", "b-check-trial/0.3", "b-check-trial/0.4"}, "CheckReportTrial")
    if base["schema_version"] == "b-check-trial/0.4":
        selected = base["payload"]["derived_review"]
        if (not _same(base["payload"].get("input_review_ref"), _docref(review)) or not _same(base["payload"].get("derived_review_ref"), _docref(selected))
                or not _same(base["payload"].get("evidence_ref"), reference(evidence)) or not _same(base["payload"].get("graph_ref"), reference(old_graph))):
            raise ValueError("current Check04 review/source basis is stale")
        selection = "CHECK04_ARCHIVED_DERIVED_REVIEW"
    else:
        if not _same(base["input_refs"], [reference(evidence), reference(old_graph), _docref(review)]):
            raise ValueError("current Check02/03 review/source basis is stale")
        selected, selection = review, "CHECK02_03_INPUT_REVIEW"
    if selected.get("book_id") != evidence["book_id"] or selected.get("scope_id") != evidence["scope_id"] or selected.get("schema_version") != "b-review-trial/0.1":
        raise ValueError("content quality review has a different semantic scope")
    return selected, {"input_review_ref": _docref(review), "selected_review_ref": _docref(selected), "base_core_check_ref": reference(base), "selection": selection}


def _core(issue):
    return [issue[k] for k in ("code", "scope_id", "evidence_refs", "severity")]+[issue.get("detail")]


def _issue(code, scope, refs, severity, detail, evidence, graph):
    assets = {p["asset_id"] for p in evidence["payload"]["pages"]}
    body = {"code": code, "scope_type": "question" if scope.startswith("q-") else "answer" if scope.startswith("a-") else "asset" if scope in assets else "scope",
            "scope_id": scope, "evidence_refs": list(refs), "severity": severity, "detail": copy.deepcopy(detail),
            "blocks": ["PRE_APPLY"], "suggested_strategy": "REVIEW_OFFLINE", "evidence_ref": reference(evidence), "graph_ref": reference(graph)}
    return {"issue_id": "issue-"+digest(body)[:24], **body}


def build_content_quality(evidence, graph, check, plan, application, review, *, source_path=None):
    expected = apply_content_revision(evidence, graph, check, plan, source_path=source_path)
    if not _same(application, expected): raise ValueError("content application differs from actual current projection")
    derived = application["payload"]["graph"]
    selected_review, review_basis = _review(evidence, graph, check, review)
    prior, _ = audit_questions(evidence, graph, selected_review, scope_key=scope_key, scalar_issues=scalar_issues)
    fresh, coverage = audit_questions(evidence, derived, selected_review, scope_key=scope_key, scalar_issues=scalar_issues)
    findings = [_issue(f["code"], f["scope_id"], f["evidence_refs"], f["severity"], f["detail"], evidence, derived) for f in fresh]
    prior_keys, issues, dispositions = {digest(_core(f)) for f in prior}, [], []
    for old in check["payload"]["issues"]:
        if digest(_core(old)) in prior_keys:
            dispositions.append({"prior_issue": copy.deepcopy(old), "origin_check_ref": reference(check), "status": "FRESH_QUESTION_RULES_RECHECKED",
                "current_finding_issue_ids": [f["issue_id"] for f in findings if (f["code"], f["scope_id"]) == (old["code"], old["scope_id"])]})
        else:
            issues.append({**copy.deepcopy(old), "origin_check_ref": reference(check), "carry_basis": {"source_layer_unchanged": True, "remaining_risk_unverified": True}})
    issues.extend(findings)
    state = derived["payload"]["content_revision"]
    def append(code, refs, detail, scope=None):
        issues.append(_issue(code, scope or evidence["scope_id"], refs, "REVIEW", detail, evidence, derived))
    append("CONTENT_REVISION_DRAFT_UNVERIFIED", [], {"operation_ids": [o["operation_id"] for o in plan["payload"]["operations"]],
        "affected_answer_ids": state["affected_answer_ids"], "human_verified": False})
    candidates = {c["candidate_id"]: c for c in graph["payload"]["inline_content"]["candidates"]}
    diagnostics = graph["payload"]["inline_content"]["continuity"]["payload"]["diagnostics"]
    for op, binding in zip(plan["payload"]["operations"], state["operation_bindings"]):
        refs = list(dict.fromkeys(s["source_element_ref"] for s in binding["source_spans"]))
        if op["kind"] == "EDIT_TEXT":
            append("CONTENT_EDIT_DRAFT_UNVERIFIED", refs, {"operation_id": op["operation_id"], "author": plan["payload"]["author"],
                "format": op["format"], "source_span": op["target"], "replacement_sha256": _sha(op["replacement"])}, binding["answer_id"])
        elif op["kind"] == "SELECT_INLINE":
            c = candidates[op["candidate_id"]]
            append("CONTENT_INLINE_SELECTION_DRAFT_UNVERIFIED", refs, {"operation_id": op["operation_id"], "candidate_id": c["candidate_id"],
                "unit_id": op["unit_id"], "call_id": c["call_id"], "raw_latex": c["raw_latex"],
                "parse_supported": c["parse_result"]["supported"], "transcription_verified": False}, binding["answer_id"])
            if c["parse_result"]["supported"] is not True:
                append("CONTENT_SELECTED_FORMULA_SYNTAX_UNSUPPORTED", refs, {"operation_id": op["operation_id"], "candidate_id": c["candidate_id"], "parse_result": c["parse_result"]}, binding["answer_id"])
            relevant = [d for d in diagnostics if d.get("candidate_id") == c["candidate_id"] and d.get("call_id") == c["call_id"]]
            if relevant: append("CONTENT_SELECTED_FORMULA_CLOSURE_CONFLICT", refs, {"operation_id": op["operation_id"], "diagnostics": relevant}, binding["answer_id"])
        elif op["kind"] == "REBUILD_TEXT_REGION":
            append("CONTENT_REGION_REBUILD_DRAFT_UNVERIFIED", refs, {"operation_id": op["operation_id"], "author": plan["payload"]["author"],
                "source_region": op["source_region"], "block_ids": [b["block_id"] for b in op["blocks"]],
                "source_fragment_ids": op["target"]["source_fragment_ids"], "unverified_runs": sum(len(b["runs"]) for b in op["blocks"])}, binding["answer_id"])
            if op.get("source_geometry_revisions"):
                append("CONTENT_REGION_SOURCE_GEOMETRY_DRAFT_UNVERIFIED", refs, {"operation_id": op["operation_id"],
                    "source_geometry_revisions": copy.deepcopy(op["source_geometry_revisions"]),
                    "zero_dark_policy": {"dark_threshold": GEOMETRY_DARK_THRESHOLD,
                        "meaning": "trimmed crop has no pixels below the fixed darkness threshold; not human geometry or glyph approval"}}, binding["answer_id"])
        else:
            append("CONTENT_RAW_WRAP_DRAFT_UNVERIFIED", refs, {"operation_id": op["operation_id"], "proposal_id": op["proposal_id"], "source_spans": binding["source_spans"]}, binding["answer_id"])
    payload = {"stage": "content_quality", "evidence_ref": reference(evidence), "graph_ref": reference(derived), "plan_ref": reference(plan),
        "application_ref": reference(application), "base_check_ref": reference(check), "review_ref": _docref(review), "review_basis": review_basis,
        "base_check_archive": copy.deepcopy(check), "source_layer_proof": copy.deepcopy(state["source_layer_proof"]),
        "prior_question_findings": prior, "fresh_question_findings": fresh, "rule_dispositions": dispositions, "issues": issues, "page_coverage": coverage,
        "summary": {"questions": len(derived["payload"]["questions"]), "answers": len(derived["payload"]["answers"]),
            "unique_candidate_links": sum(q["selected_answer_id"] is not None for q in derived["payload"]["questions"]), "issues": len(issues),
            "affected_answers": len(state["affected_answer_ids"]), "affected_questions": len(state["affected_question_ids"]),
            "operations": len(plan["payload"]["operations"]), "source_assets": len(evidence["payload"]["pages"])}, **_flags()}
    check_schema = (GEOMETRY_CHECK_SCHEMA if plan["schema_version"] == GEOMETRY_PLAN_SCHEMA
                    else REGION_CHECK_SCHEMA if plan["schema_version"] == REGION_PLAN_SCHEMA else CHECK_SCHEMA)
    return _artifact(check_schema, "CheckReportTrial", "content-check", evidence,
        [reference(evidence), reference(derived), reference(check), reference(plan), reference(application), _docref(review)], payload, "quality")
