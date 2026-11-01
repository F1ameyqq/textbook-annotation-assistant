"""Offline, conservative assembly experiment. No platform or history-box input.

Section windows are explicit, reviewed development input, not inferred directory
IDs. These formats must be adapted when the shared A/B contract is executable.
"""
from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .baseline import code_digest, digest, legacy_backend, load_source, valid_bbox
from .policy import classify, choice_answer_valid, option_set_valid
from .answer_assembly import assemble_answers
from .answer_quality import audit_answers
from .recovery_quality import audit_recovery
from .question_quality import audit_questions

CONTEXT_SCHEMA = "b-context-trial/0.1"
CONTEXT_STRUCTURED_SCHEMA = "b-context-trial/0.2"
EVIDENCE_SCHEMA = "b-evidence-trial/0.2"
EVIDENCE_STRUCTURED_SCHEMA = "b-evidence-trial/0.4"
GRAPH_SCHEMA = "b-graph-trial/0.2"
GRAPH_STRUCTURED_SCHEMA = "b-graph-trial/0.9"
CHECK_SCHEMA = "b-check-trial/0.2"
CHECK_STRUCTURED_SCHEMA = "b-check-trial/0.9"
REVIEWED_LAYOUT_POLICY = "EXACT_SOURCE_PARTITION/0.1"
QSTART = re.compile(r"^\s*(\d{1,2})\s*[.．、]\s*(?=[\u4e00-\u9fffA-Za-z（(])")
ASTART = re.compile(r"^\s*(\d{1,2})\s*[.．、]\s*(.+)$")
OPTION = re.compile(r"^\s*([A-G])[.．、]")
CAPTION = re.compile(r"^第\s*(\d{1,2})\s*题图$")
DECORATION = re.compile(r"^(?:[A-C]?基础题|[A-C]?中档题|[A-C]?综合题|知识点|易错点)")


def artifact(schema, kind, source, payload, inputs, producer):
    identity = digest({"schema": schema, "source": source, "payload": payload,
                       "inputs": inputs, "producer": producer})
    return {"schema_version": schema, "kind": kind,
            "artifact_id": kind.lower() + "-" + identity[:24], "revision": 1,
            "run_id": source.get("run_id") or "b-run-" + digest({"source": source, "inputs": inputs})[:24],
            "book_id": source["book_id"], "scope_id": source["scope_id"],
            "input_refs": inputs, "producer": producer,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": digest(payload), "payload": payload}


def ref(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def check_artifact(value, schemas):
    if value.get("schema_version") not in schemas:
        raise ValueError("unsupported provisional artifact schema")
    if value.get("content_hash") != digest(value.get("payload")):
        raise ValueError("artifact payload hash mismatch")
    if type(value.get("revision")) is not int or value["revision"] < 1:
        raise ValueError("invalid artifact revision")


def _reviewed_layout_syntax(asset, reviewed):
    group_keys = {"group_id", "kind", "section_path", "ordered_line_ids", "flow_segments",
                  "spanning_line_ids", "printed_number", "parent_group_id", "material_id", "label",
                  "response_kind", "counting_status", "reason"}
    kinds = {"QUESTION", "VARIANT", "MATERIAL_TITLE", "MATERIAL_BODY", "FIGURE_LABELS",
             "TASK_SECTION_HEADING", "TASK", "EXCLUDE"}
    snapshots = reviewed.get("line_snapshots") if isinstance(reviewed, dict) else None
    groups = reviewed.get("groups") if isinstance(reviewed, dict) else None
    if (not isinstance(reviewed, dict) or set(reviewed) != {"policy", "source_sha256", "source_size", "cut_x",
            "baseline_ref", "baseline_producer", "expected_line_count", "review_kind", "verification_status",
            "line_snapshots", "groups"}
            or reviewed.get("policy") != REVIEWED_LAYOUT_POLICY or reviewed.get("source_sha256") != asset["sha256"]
            or reviewed.get("source_size") != [asset["width"], asset["height"]]
            or type(reviewed.get("cut_x")) is not int or not 0 < reviewed["cut_x"] < asset["width"]
            or not isinstance(reviewed.get("baseline_ref"), dict)
            or set(reviewed["baseline_ref"]) != {"artifact_id", "revision", "content_hash"}
            or not isinstance(reviewed.get("baseline_producer"), dict) or not reviewed["baseline_producer"]
            or type(reviewed.get("expected_line_count")) is not int or reviewed["expected_line_count"] <= 0
            or reviewed.get("review_kind") != "MODEL_DRAFT" or reviewed.get("verification_status") != "UNVERIFIED"
            or not isinstance(snapshots, list) or not snapshots or not isinstance(groups, list) or not groups):
        raise ValueError("reviewed layout identity, source or draft status is invalid")
    snapshot_ids = []
    for row in snapshots:
        if (not isinstance(row, dict) or set(row) != {"line_id", "text", "bbox"}
                or not isinstance(row.get("line_id"), str) or not row["line_id"]
                or not isinstance(row.get("text"), str) or not valid_bbox(row.get("bbox", []), asset["width"], asset["height"])
                or any(isinstance(value, bool) for value in row["bbox"])):
            raise ValueError("reviewed layout line snapshot is invalid")
        snapshot_ids.append(row["line_id"])
    if len(snapshot_ids) != len(set(snapshot_ids)):
        raise ValueError("reviewed layout line snapshots must be unique")
    snapshot_map = {row["line_id"]: row for row in snapshots}
    allocated, group_ids, material_ids, semantic_keys = [], [], set(), []
    for group in groups:
        if (not isinstance(group, dict) or set(group) != group_keys or not isinstance(group.get("group_id"), str)
                or not group["group_id"] or group.get("kind") not in kinds
                or not isinstance(group.get("section_path"), list)
                or any(not isinstance(value, str) or not value for value in group["section_path"])
                or not isinstance(group.get("ordered_line_ids"), list) or not group["ordered_line_ids"]
                or not all(isinstance(value, str) and value for value in group["ordered_line_ids"])
                or len(group["ordered_line_ids"]) != len(set(group["ordered_line_ids"]))
                or not isinstance(group.get("flow_segments"), list) or not group["flow_segments"]
                or not isinstance(group.get("spanning_line_ids"), list)
                or not set(group["spanning_line_ids"]).issubset(group["ordered_line_ids"])
                or not isinstance(group.get("reason"), str) or not group["reason"]):
            raise ValueError("reviewed layout group syntax is invalid")
        flattened = []
        for segment in group["flow_segments"]:
            if (not isinstance(segment, dict) or set(segment) != {"column", "line_ids"}
                    or segment.get("column") not in (0, 1) or not isinstance(segment.get("line_ids"), list)
                    or not segment["line_ids"] or not all(isinstance(value, str) and value for value in segment["line_ids"])):
                raise ValueError("reviewed layout flow segment is invalid")
            flattened.extend(segment["line_ids"])
        if flattened != group["ordered_line_ids"]:
            raise ValueError("reviewed layout flow must exactly project ordered source lines")
        columns = [segment["column"] for segment in group["flow_segments"]]
        if (group["kind"] == "TASK" and len(columns) > 1 and columns != [0, 1]) or (
                group["kind"] not in {"TASK", "MATERIAL_TITLE"} and len(columns) != 1):
            raise ValueError("reviewed layout permits only an explicit one-time task column transition")
        if group["kind"] != "MATERIAL_TITLE" and group["spanning_line_ids"]:
            raise ValueError("only an explicit material title may cross the column cut")
        if group["kind"] == "MATERIAL_TITLE" and not group["spanning_line_ids"]:
            raise ValueError("material title must name its actual spanning source line")
        if group["kind"] == "QUESTION" and (not group.get("printed_number") or group.get("parent_group_id") is not None
                or group.get("counting_status") != "PRINTED_TOP_LEVEL"):
            raise ValueError("printed question group identity is invalid")
        if group["kind"] == "VARIANT" and (not group.get("parent_group_id") or group.get("counting_status") != "UNKNOWN"):
            raise ValueError("variant must remain an uncounted child draft")
        if group["kind"] == "TASK" and (not group.get("material_id") or not group.get("label")
                or not group.get("response_kind") or group.get("counting_status") != "UNKNOWN"):
            raise ValueError("shared-material task must retain unknown counting and response semantics")
        if group["kind"] in {"MATERIAL_TITLE", "MATERIAL_BODY", "FIGURE_LABELS", "TASK_SECTION_HEADING"}:
            if not group.get("material_id") or group.get("counting_status") != "NOT_A_QUESTION":
                raise ValueError("material group cannot claim question counting")
            material_ids.add(group["material_id"])
        if group["kind"] == "EXCLUDE" and group.get("counting_status") != "EXCLUDED":
            raise ValueError("source decoration exclusion is invalid")
        first_text = snapshot_map.get(group["ordered_line_ids"][0], {}).get("text", "")
        if group["kind"] == "QUESTION":
            match = QSTART.match(first_text)
            if (not match or group["printed_number"] != match[1] or group.get("material_id") is not None
                    or group.get("label") is not None or group.get("response_kind") is not None):
                raise ValueError("printed question metadata differs from its raw anchor")
        elif group["kind"] == "VARIANT":
            if (not first_text.startswith("【变式】") or group.get("material_id") is not None
                    or group.get("label") is not None or group.get("response_kind") is not None):
                raise ValueError("variant metadata differs from its raw anchor")
        elif group["kind"] == "TASK":
            label_match = re.match(r"^\s*([（(]\d+[）)])", first_text)
            if (not label_match or group.get("label") != label_match[1].replace("（","(").replace("）",")")
                    or group.get("response_kind") != "UNKNOWN" or group.get("printed_number") is not None
                    or group.get("parent_group_id") is not None):
                raise ValueError("task metadata differs from its raw anchor or claims a response type")
        elif group["kind"] in {"MATERIAL_TITLE","MATERIAL_BODY","FIGURE_LABELS","TASK_SECTION_HEADING"}:
            if (group.get("printed_number") is not None or group.get("parent_group_id") is not None
                    or group.get("label") is not None or group.get("response_kind") is not None):
                raise ValueError("material metadata contains question or response claims")
        elif any(group.get(key) is not None for key in ("printed_number","parent_group_id","material_id","label","response_kind")):
            raise ValueError("excluded decoration contains semantic identity claims")
        semantic_keys.append((group["kind"], group.get("label") if group["kind"] == "TASK" else None))
        group_ids.append(group["group_id"]); allocated.extend(group["ordered_line_ids"])
    if (len(group_ids) != len(set(group_ids)) or set(allocated) != set(snapshot_ids)
            or len(allocated) != len(set(allocated)) or len(semantic_keys) != len(set(semantic_keys))):
        raise ValueError("reviewed layout groups must partition every source line once in source order")
    by_group = {group["group_id"]: group for group in groups}
    for group in groups:
        if group["kind"] == "VARIANT" and by_group.get(group["parent_group_id"], {}).get("kind") != "QUESTION":
            raise ValueError("variant parent is not the reviewed printed question")
        if (group["kind"] == "VARIANT" and group.get("printed_number") !=
                by_group[group["parent_group_id"]].get("printed_number")+":variant"):
            raise ValueError("variant printed identity is not derived from its printed parent")
        if group["kind"] == "TASK" and group["material_id"] not in material_ids:
            raise ValueError("task belongs to an unknown reviewed material")


def validate_context(source, context):
    if context.get("schema_version") not in {CONTEXT_SCHEMA, CONTEXT_STRUCTURED_SCHEMA}:
        raise ValueError("unsupported context schema")
    if (context.get("book_id"), context.get("scope_id")) != (source["book_id"], source["scope_id"]):
        raise ValueError("context book/scope mismatch")
    assets = {a["asset_id"]: a for a in source["assets"]}
    if set(context.get("pages", {})) != set(assets):
        raise ValueError("context must explicitly cover every input asset")
    if context["schema_version"] == CONTEXT_STRUCTURED_SCHEMA:
        provenance=context.get("provenance")
        if (set(context)!={"schema_version","artifact_id","book_id","scope_id","pages","reference_quality","provenance"}
                or context.get("reference_quality")!="MODEL_VISUAL_DEVELOPMENT_REVIEW"
                or provenance!="Explicit model draft over the frozen 48-row OCR; not human review."):
            raise ValueError("structured context must remain an exact model-development draft")
    for aid, page in context["pages"].items():
        if page.get("sha256") != assets[aid]["sha256"]:
            raise ValueError("context asset hash mismatch")
        if context["schema_version"] == CONTEXT_STRUCTURED_SCHEMA and set(page)!={"sha256","role","windows","reviewed_layout"}:
            raise ValueError("structured context page has unknown or missing fields")
        windows = page.get("windows", [])
        if page.get("role") not in {"question", "answer"} or not windows:
            raise ValueError("context needs page role and section windows")
        for w in windows:
            if set(w)!={"column","y_range","path"} or not isinstance(w.get("y_range"),list) or len(w["y_range"])!=2:
                raise ValueError("invalid context window")
            lo, hi = w["y_range"]
            if (w["column"] not in (0, 1) or type(lo)is not int or type(hi)is not int
                    or not 0 <= lo < hi <= assets[aid]["height"]
                    or not w.get("path") or any(not isinstance(s, str) or not s for s in w["path"])):
                raise ValueError("invalid context window")
        for i, a in enumerate(windows):
            for b in windows[i + 1:]:
                if a["column"] == b["column"] and max(a["y_range"][0], b["y_range"][0]) < min(a["y_range"][1], b["y_range"][1]):
                    raise ValueError("overlapping context windows")
        reviewed = page.get("reviewed_layout")
        if context["schema_version"] == CONTEXT_STRUCTURED_SCHEMA:
            if page.get("role") == "question" and reviewed is None:
                raise ValueError("structured question context requires an explicit reviewed layout")
            if reviewed is not None:
                _reviewed_layout_syntax(assets[aid], reviewed)
        elif reviewed is not None:
            raise ValueError("context 0.1 cannot carry reviewed layout structure")


def detect_columns(mask, lines):
    """Central gutter candidate, confirmed by OCR boxes on both sides.

    Unlike the legacy aspect-ratio shortcut, portrait pages are eligible. This
    supports two columns only. Crossing body text rejects the split explicitly.
    """
    h, w = mask.shape
    band = mask[int(.18 * h):int(.94 * h)]
    ink = band.mean(axis=0)
    candidates = range(int(.46 * w), int(.54 * w))
    cut = min(candidates, key=lambda x: (float(ink[max(0, x-3):x+4].mean()), abs(x-w/2)))
    crossing = [a for a in lines if a["bbox"][0] < cut < a["bbox"][2]
                and a["bbox"][3] > .2 * h]
    left = sum(a["bbox"][2] <= cut for a in lines)
    right = sum(a["bbox"][0] >= cut for a in lines)
    accepted = ink[max(0, cut-3):cut+4].mean() < .015 and left >= 4 and right >= 4 and not crossing
    return {"mode": "two_columns" if accepted else "UNRESOLVED_LAYOUT",
            "cut_x": int(cut), "body_crossing_boxes": len(crossing),
            "left_ocr_boxes": left, "right_ocr_boxes": right,
            "method": "central_gutter+ocr_box_separation", "verified": False}


def locate(line, layout, windows):
    x1, y1, x2, y2 = line["bbox"]
    cut = layout["cut_x"]
    if x1 < cut < x2:
        return None
    column, y = int((x1 + x2) / 2 >= cut), (y1 + y2) / 2
    for i, window in enumerate(windows):
        if window["column"] == column and window["y_range"][0] <= y < window["y_range"][1]:
            return {"column": column, "window_index": i, "section_path": window["path"]}
    return None


def _locate_column(line, column, windows):
    y = (line["bbox"][1] + line["bbox"][3]) / 2
    matches = [(index, window) for index, window in enumerate(windows)
               if window["column"] == column and window["y_range"][0] <= y < window["y_range"][1]]
    if len(matches) != 1:
        return None
    index, window = matches[0]
    return {"column": column, "window_index": index, "section_path": window["path"]}


def _derive_reviewed_structure(asset, lines, cut):
    by_id = {line["line_id"]: line for line in lines}
    column = lambda line: int((line["bbox"][0] + line["bbox"][2]) / 2 >= cut)
    order = lambda values: sorted(values, key=lambda line: (line["bbox"][1], line["bbox"][0], line["line_id"]))
    only = lambda values, label: values[0] if len(values) == 1 else (_ for _ in ()).throw(ValueError("reviewed layout needs one "+label))
    qline = only([line for line in lines if QSTART.match(line["text"])], "printed question anchor")
    variant = only([line for line in lines if line["text"].startswith("【变式】")], "variant anchor")
    task_heading = only([line for line in lines if re.match(r"^\s*任务\s*[：:]", line["text"])], "task-section heading")
    task_anchors = {label: only([line for line in lines if re.match(r"^\s*[（(]"+label+r"[）)]", line["text"])], "task "+label)
                    for label in ("1", "2", "3")}
    title_left = only([line for line in lines if line["text"].startswith("漫话勾股世界")], "left title anchor")
    title_right = only([line for line in lines if "教材P6" in line["text"] and "阅读" in line["text"] and "思考" in line["text"]], "right title anchor")
    vertical_overlap = min(title_left["bbox"][3], title_right["bbox"][3]) - max(title_left["bbox"][1], title_right["bbox"][1])
    if (not title_left["bbox"][2] < title_right["bbox"][0] < cut < title_right["bbox"][2]
            or vertical_overlap < .5 * min(title_left["bbox"][3]-title_left["bbox"][1], title_right["bbox"][3]-title_right["bbox"][1])):
        raise ValueError("title anchors do not independently prove the reviewed spanning geometry")
    title_top = min(title_left["bbox"][1], title_right["bbox"][1])
    decoration = [line for line in lines if (line["bbox"][1] > .93*asset["height"]
                  and (re.fullmatch(r"\s*\d+\s*", line["text"]) or "数学" in line["text"]))]
    figure_labels = [line for line in lines if line["text"].strip() in {"图1", "图2", "剪开", "右边部分", "上下翻转"}]
    excluded = {line["line_id"] for line in decoration+figure_labels+[qline,variant,task_heading,*task_anchors.values(),title_left,title_right]}
    q_rows = order([line for line in lines if column(line) == 0 and qline["bbox"][1] <= line["bbox"][1] < title_top and line["line_id"] not in excluded])
    variant_rows = order([line for line in lines if column(line) == 1 and variant["bbox"][1] <= line["bbox"][1] < title_top and line["line_id"] not in excluded])
    task1_left = order([line for line in lines if column(line) == 0 and line["bbox"][1] >= task_anchors["1"]["bbox"][1]
                        and line["line_id"] not in {value["line_id"] for value in decoration}])
    task1_right = order([line for line in lines if column(line) == 1 and title_right["bbox"][3] < line["bbox"][1] < task_anchors["2"]["bbox"][1]])
    task2 = order([line for line in lines if column(line) == 1 and task_anchors["2"]["bbox"][1] <= line["bbox"][1] < task_anchors["3"]["bbox"][1]])
    task3 = order([line for line in lines if column(line) == 1 and task_anchors["3"]["bbox"][1] <= line["bbox"][1]
                   and line["line_id"] not in {value["line_id"] for value in decoration}])
    consumed = {line["line_id"] for line in decoration+figure_labels+[qline,variant,task_heading,title_left,title_right]
                +q_rows+variant_rows+task1_left+task1_right+task2+task3}
    body = order([line for line in lines if line["line_id"] not in consumed])
    def ids(values): return [line["line_id"] for line in values]
    # Same-band figure actions use horizontal order; other bands use vertical order.
    figure_rows = []
    for line in sorted(figure_labels, key=lambda value:(value["bbox"][1],value["bbox"][0])):
        center = (line["bbox"][1]+line["bbox"][3])/2
        target = next((row for row in figure_rows if abs(row[0]-center) <= 12), None)
        if target is None: figure_rows.append([center,line])
        else: target.append(line)
    ordered_figures = [line for row in figure_rows for line in sorted(row[1:],key=lambda value:value["bbox"][0])]
    number = QSTART.match(qline["text"])[1]
    result = {
        ("QUESTION", None): ([qline["line_id"], *ids(q_rows)], [(0,[qline["line_id"],*ids(q_rows)])]),
        ("VARIANT", None): ([variant["line_id"], *ids(variant_rows)], [(1,[variant["line_id"],*ids(variant_rows)])]),
        ("MATERIAL_TITLE", None): ([title_left["line_id"],title_right["line_id"]], [(0,[title_left["line_id"]]),(1,[title_right["line_id"]])]),
        ("MATERIAL_BODY", None): (ids(body), [(0,ids(body))]),
        ("FIGURE_LABELS", None): (ids(ordered_figures), [(0,ids(ordered_figures))]),
        ("TASK_SECTION_HEADING", None): ([task_heading["line_id"]], [(0,[task_heading["line_id"]])]),
        ("TASK", "(1)"): (ids(task1_left)+ids(task1_right), [(0,ids(task1_left)),(1,ids(task1_right))]),
        ("TASK", "(2)"): (ids(task2), [(1,ids(task2))]),
        ("TASK", "(3)"): (ids(task3), [(1,ids(task3))]),
        ("EXCLUDE", None): (ids(order(decoration)), [(1,ids(order(decoration)))])}
    if any(not line_ids or any(not segment_ids for _,segment_ids in segments) for line_ids,segments in result.values()):
        raise ValueError("independently derived reviewed structure contains an empty required group")
    if set(line_id for line_ids,_ in result.values() for line_id in line_ids) != set(by_id):
        raise ValueError("independently derived reviewed structure does not cover the exact OCR scope")
    return result, {"printed_number":number,"question_anchor":qline["line_id"],"variant_anchor":variant["line_id"],
                    "title_line_ids":[title_left["line_id"],title_right["line_id"]],
                    "task_anchor_line_ids":{label:task_anchors[label]["line_id"] for label in ("1","2","3")},
                    "task_section_heading_line_id":task_heading["line_id"]}


def _reviewed_layout_receipt(asset, lines, layout, windows, reviewed, baseline):
    _reviewed_layout_syntax(asset, reviewed)
    baseline_ref = {key:baseline[key] for key in ("artifact_id","revision","content_hash")}
    if (reviewed["baseline_ref"] != baseline_ref or reviewed["baseline_producer"] != baseline.get("producer")
            or reviewed["expected_line_count"] != len(lines)):
        raise ValueError("reviewed layout does not bind the exact baseline OCR artifact, producer and line count")
    snapshots = [{"line_id": line["line_id"], "text": line["text"], "bbox": line["bbox"]} for line in lines]
    if snapshots != reviewed["line_snapshots"] or layout["cut_x"] != reviewed["cut_x"]:
        raise ValueError("reviewed layout differs from the current frozen OCR or detected cut")
    cut, height = layout["cut_x"], asset["height"]
    actual_crossing = [line["line_id"] for line in lines
                       if line["bbox"][0] < cut < line["bbox"][2] and line["bbox"][3] > .2 * height]
    declared_crossing = [line_id for group in reviewed["groups"] for line_id in group["spanning_line_ids"]]
    if actual_crossing != declared_crossing:
        raise ValueError("actual crossing source lines differ from the exact reviewed title exception")
    derived, anchors = _derive_reviewed_structure(asset, lines, cut)
    claims = {}
    for group in reviewed["groups"]:
        key = (group["kind"],group["label"] if group["kind"] == "TASK" else None)
        claims[key] = (group["ordered_line_ids"],[(segment["column"],segment["line_ids"]) for segment in group["flow_segments"]])
    if claims != derived:
        raise ValueError("reviewed grouping claims differ from independently derived source structure")
    line_map = {line["line_id"]: line for line in lines}
    def source_order(values):
        bands = []
        for value in sorted(values,key=lambda line:(line["bbox"][1],line["bbox"][0],line["line_id"])):
            center=(value["bbox"][1]+value["bbox"][3])/2
            band=next((row for row in bands if abs(row[0]-center)<=12),None)
            if band is None: bands.append([center,value])
            else: band.append(value)
        return [value for row in bands for value in sorted(row[1:],key=lambda line:(line["bbox"][0],line["bbox"][1],line["line_id"]))]
    group_map, column_map = {}, {}
    for group in reviewed["groups"]:
        if group["section_path"] and not any(window["path"] == group["section_path"] for window in windows):
            raise ValueError("reviewed layout group uses an unknown semantic path")
        for segment in group["flow_segments"]:
            ordered = [line_map[line_id] for line_id in segment["line_ids"]]
            expected_order = source_order(ordered) if group["kind"] == "FIGURE_LABELS" else sorted(
                ordered,key=lambda line:(line["bbox"][1],line["bbox"][0],line["line_id"]))
            if ordered != expected_order:
                raise ValueError("reviewed segment is not in strict source y/x order")
            for line_id in segment["line_ids"]:
                line = line_map[line_id]
                midpoint_column = int((line["bbox"][0] + line["bbox"][2]) / 2 >= cut)
                if line_id not in declared_crossing and midpoint_column != segment["column"]:
                    raise ValueError("reviewed layout assigns a nonspanning source line to the wrong column")
                group_map[line_id] = group["group_id"]; column_map[line_id] = segment["column"]
    return {"policy": REVIEWED_LAYOUT_POLICY, "source_sha256": asset["sha256"], "baseline_ref":baseline_ref,
            "cut_x": cut, "actual_crossing_line_ids": actual_crossing,
            "group_by_line_id": group_map, "column_by_line_id": column_map,
            "derived_anchors":anchors,"reviewed_layout_hash": digest(reviewed), "verification_status": "UNVERIFIED",
            "review_kind": "MODEL_DRAFT"}


def refine(source_path, baseline, context):
    """Validate cached OCR against actual local bytes, then refine dense answers."""
    source, inputs = load_source(source_path)
    validate_context(source, context)
    check_artifact(baseline, {"b-evidence-trial/0.1"})
    if not baseline.get("producer", {}).get("ocr_enabled"):
        raise ValueError("baseline OCR evidence is required")
    if (baseline["book_id"], baseline["scope_id"]) != (source["book_id"], source["scope_id"]):
        raise ValueError("cached evidence book/scope mismatch")
    if baseline["input_refs"] != [{"artifact_id": source["artifact_id"], "content_hash": digest(source)}]:
        raise ValueError("cached evidence source binding mismatch")
    by_id = {p["asset_id"]: p for p in baseline["payload"]["pages"]}
    if len(by_id) != len(inputs) or set(by_id) != {a["asset_id"] for a, _ in inputs}:
        raise ValueError("cached evidence page set mismatch")
    backend, pages = legacy_backend(), []
    for asset, path in inputs:
        original = by_id[asset["asset_id"]]
        if original["source"] != asset:
            raise ValueError("cached evidence asset descriptor mismatch")
        rgb = np.array(Image.open(path).convert("RGB"))
        lines = copy.deepcopy(original["ocr_lines"])
        if any(not valid_bbox(a["bbox"], asset["width"], asset["height"]) for a in lines):
            raise ValueError("invalid OCR box")
        page_context = context["pages"][asset["asset_id"]]
        for i, line in enumerate(lines):
            line["line_id"] = f"{asset['asset_id']}/ocr/{i}"
        layout = detect_columns(np.array(Image.open(path).convert("L")) < 160, lines)
        reviewed = page_context.get("reviewed_layout")
        receipt = _reviewed_layout_receipt(asset, lines, layout, page_context["windows"], reviewed, baseline) if reviewed else None
        if receipt:
            layout = {**layout, "mode": "two_columns_with_reviewed_spanning_headers",
                      "reviewed_spanning_line_ids": receipt["actual_crossing_line_ids"],
                      "reviewed_layout_hash": receipt["reviewed_layout_hash"]}
        for line in lines:
            if receipt:
                line["location"] = _locate_column(line, receipt["column_by_line_id"][line["line_id"]], page_context["windows"])
                if line["location"] is None:
                    raise ValueError("reviewed source line is outside its declared semantic window")
            else:
                line["location"] = locate(line, layout, page_context["windows"]) if layout["mode"] == "two_columns" else None
        detail = []
        if page_context["role"] == "answer":
            for line in lines:
                # Re-detect a single row at 3x so printed marker 4.13 is not
                # fused with neighbours into '...244.135.640'. Never rewrite it.
                if not line["location"] or not ASTART.match(line["text"]):
                    continue
                x1, y1, x2, y2 = line["bbox"]
                box = [max(0, int(x1)-4), max(0, int(y1)-2),
                       min(asset["width"], int(x2)+5), min(asset["height"], int(y2)+2)]
                crop = Image.fromarray(rgb).crop(box)
                scale = 3
                crop = crop.resize((crop.width*scale, crop.height*scale), Image.Resampling.LANCZOS)
                atoms = backend.ocr_atoms(np.array(crop)[:, :, ::-1].copy())
                for j, atom in enumerate(sorted(atoms, key=lambda a: a["bbox"][0])):
                    atom["bbox"] = [round(atom["bbox"][k] / scale + box[k % 2], 3) for k in range(4)]
                    atom.update(line_id=f"{line['line_id']}/detail/{j}", parent_line_id=line["line_id"],
                                location=line["location"], crop_to_original=[[1/scale, 0, box[0]], [0, 1/scale, box[1]], [0, 0, 1]])
                    detail.append(atom)
        page = {"asset_id": asset["asset_id"], "source": asset, "page_role": page_context["role"],
                      "layout": layout, "ocr_lines": lines, "answer_detail_lines": detail,
                      "unscoped_line_ids": [a["line_id"] for a in lines if not a["location"]]}
        if receipt: page["reviewed_layout_receipt"] = receipt
        pages.append(page)
    payload = {"pages": pages, "quality_decision": "NOT_EVALUATED",
               "context": context, "history_annotations_consumed": False,
               "limitations": ["Reviewed section windows are development input, not automatic directory recognition.",
                               "OCR and figure candidates are unverified; two-column layouts only."]}
    schema = EVIDENCE_STRUCTURED_SCHEMA if context["schema_version"] == CONTEXT_STRUCTURED_SCHEMA else EVIDENCE_SCHEMA
    return artifact(schema, "EvidenceBundleTrial", source, payload,
                    [ref(baseline), {"artifact_id": context["artifact_id"], "content_hash": digest(context)}],
                    {"module": __name__, "version": "0.2.0", "code_sha256": code_digest(Path(__file__)),
                     "baseline_producer": baseline["producer"], "answer_row_scale": 3})


def entity_id(evidence, role, anchor):
    return role + "-" + digest({"evidence": ref(evidence), "role": role, "anchor": anchor})[:24]


def scope_key(book, path, number):
    return (book, tuple(path), str(number))


def _assemble_reviewed_question_page(evidence, page):
    context_page = evidence["payload"]["context"]["pages"][page["asset_id"]]
    reviewed, receipt = context_page["reviewed_layout"], page.get("reviewed_layout_receipt")
    if not receipt or receipt.get("reviewed_layout_hash") != digest(reviewed):
        raise ValueError("reviewed question page lacks its exact refinement receipt")
    lines = {line["line_id"]: line for line in page["ocr_lines"]}
    groups = {group["group_id"]: group for group in reviewed["groups"]}
    questions, materials, coverage = [], [], []

    def fragments(group, role, prefix):
        result = []
        for line_id in group["ordered_line_ids"]:
            line = lines[line_id]
            result.append({"fragment_id": entity_id(evidence, prefix, line_id), "role": role,
                           "content_type": "text", "option_label": None, "option_start": False,
                           "column": line["location"]["column"] if line.get("location") else receipt["column_by_line_id"][line_id],
                           "bbox": line["bbox"], "asset_id": page["asset_id"], "text": line["text"],
                           "evidence_refs": [line_id]})
        return result

    question_by_group = {}
    for group in reviewed["groups"]:
        if group["kind"] not in {"QUESTION", "VARIANT"}: continue
        anchor = group["ordered_line_ids"][0]
        parent = question_by_group.get(group["parent_group_id"])
        if group["kind"] == "VARIANT" and parent is None:
            raise ValueError("reviewed variant must follow its printed parent question")
        body = fragments(group, "stem", "f")
        question = {"question_id": entity_id(evidence, "q", anchor), "book_id": evidence["book_id"],
                    "section_path": group["section_path"], "printed_number": group["printed_number"],
                    "parent_question_id": parent["question_id"] if parent else None, "anchor_ref": anchor,
                    "asset_id": page["asset_id"], "fragments": body, "candidate_answer_ids": [],
                    "selected_answer_id": None, "verification_status": "UNVERIFIED",
                    "flags": ["FIGURE_EXTENT_UNVERIFIED"], "structure_group_id": group["group_id"],
                    "counting_status": group["counting_status"]}
        questions.append(question); question_by_group[group["group_id"]] = question

    material_ids = list(dict.fromkeys(group["material_id"] for group in reviewed["groups"] if group["material_id"]))
    for source_material_id in material_ids:
        title_groups = [group for group in reviewed["groups"] if group["kind"] == "MATERIAL_TITLE" and group["material_id"] == source_material_id]
        body_groups = [group for group in reviewed["groups"] if group["kind"] == "MATERIAL_BODY" and group["material_id"] == source_material_id]
        figure_groups = [group for group in reviewed["groups"] if group["kind"] == "FIGURE_LABELS" and group["material_id"] == source_material_id]
        heading_groups = [group for group in reviewed["groups"] if group["kind"] == "TASK_SECTION_HEADING" and group["material_id"] == source_material_id]
        task_groups = [group for group in reviewed["groups"] if group["kind"] == "TASK" and group["material_id"] == source_material_id]
        if any(len(values) != 1 for values in (title_groups,body_groups,figure_groups,heading_groups)) or not task_groups:
            raise ValueError("shared material requires one title, body, figure-label set, task heading and explicit tasks")
        title_group, body_group = title_groups[0], body_groups[0]
        title_fragments = fragments(title_group, "material_title", "mf")
        body_fragments = fragments(body_group, "material_body", "mf")
        figure_fragments = fragments(figure_groups[0], "figure_label", "mf")
        heading_fragments = fragments(heading_groups[0], "task_section_heading", "mf")
        material_id = entity_id(evidence, "material", title_group["ordered_line_ids"][0])
        tasks = []
        for group in task_groups:
            task_fragments = fragments(group, "task_prompt", "tf")
            tasks.append({"task_id": entity_id(evidence, "task", group["ordered_line_ids"][0]),
                          "material_id": material_id, "label": group["label"], "anchor_ref": group["ordered_line_ids"][0],
                          "section_path": group["section_path"], "asset_id": page["asset_id"],
                          "response_kind": group["response_kind"], "counting_status": "UNKNOWN",
                          "verification_status": "UNVERIFIED", "flow_segments": copy.deepcopy(group["flow_segments"]),
                          "fragments": task_fragments, "text": "\n".join(item["text"] for item in task_fragments),
                          "flags": ["BUSINESS_REVIEW_REQUIRED", "FIGURE_EXTENT_UNVERIFIED"]})
        materials.append({"material_id": material_id, "source_material_id": source_material_id,
                          "book_id": evidence["book_id"], "asset_id": page["asset_id"],
                          "section_path": title_group["section_path"], "verification_status": "UNVERIFIED",
                          "counting_status": "NOT_A_QUESTION", "title_fragments": title_fragments,
                          "body_fragments": body_fragments, "figure_label_fragments": figure_fragments,
                          "task_section_heading_fragments": heading_fragments,
                          "title": "\n".join(item["text"] for item in title_fragments),
                          "text": "\n".join(item["text"] for item in body_fragments), "tasks": tasks,
                          "flags": ["TITLE_SEPARATOR_UNCAPTURED", "FIGURE_EXTENT_UNVERIFIED", "BUSINESS_REVIEW_REQUIRED"]})

    owner_by_line = {}
    for group in reviewed["groups"]:
        if group["kind"] in {"QUESTION", "VARIANT"}:
            owner_kind, owner_id, status = "question", question_by_group[group["group_id"]]["question_id"], "CONSUMED_QUESTION"
        elif group["kind"] == "TASK":
            material = next(value for value in materials if value["source_material_id"] == group["material_id"])
            task = next(value for value in material["tasks"] if value["label"] == group["label"])
            owner_kind, owner_id, status = "task", task["task_id"], "CONSUMED_SHARED_TASK"
        elif group["kind"] in {"MATERIAL_TITLE", "MATERIAL_BODY", "FIGURE_LABELS", "TASK_SECTION_HEADING"}:
            material = next(value for value in materials if value["source_material_id"] == group["material_id"])
            owner_kind, owner_id = "shared_material", material["material_id"]
            status = {"MATERIAL_TITLE":"CONSUMED_SHARED_TITLE","MATERIAL_BODY":"CONSUMED_SHARED_BODY",
                      "FIGURE_LABELS":"CONSUMED_FIGURE_LABEL","TASK_SECTION_HEADING":"CONSUMED_TASK_SECTION_HEADING"}[group["kind"]]
        else:
            owner_kind, owner_id, status = "exclusion", group["group_id"], "EXCLUDED_DECORATION"
        for line_id in group["ordered_line_ids"]:
            owner_by_line[line_id] = {"asset_id": page["asset_id"], "line_id": line_id, "status": status,
                                     "owner_kind": owner_kind, "owner_id": owner_id, "group_id": group["group_id"]}
    coverage = [owner_by_line[line["line_id"]] for line in page["ocr_lines"]]
    return questions, materials, coverage


def assemble(evidence):
    check_artifact(evidence, {EVIDENCE_SCHEMA, "b-evidence-trial/0.3", EVIDENCE_STRUCTURED_SCHEMA})
    questions, answers, assembly_issues, shared_materials, question_source_coverage = [], [], [], [], []
    for page in evidence["payload"]["pages"]:
        lines = sorted((a for a in page["ocr_lines"] if a.get("location")),
                       key=lambda a: (a["location"]["column"], a["bbox"][1], a["bbox"][0]))
        if page["page_role"] == "question":
            if page.get("reviewed_layout_receipt"):
                current_questions, current_materials, current_coverage = _assemble_reviewed_question_page(evidence, page)
                questions.extend(current_questions); shared_materials.extend(current_materials)
                question_source_coverage.extend(current_coverage)
                continue
            current, captions = None, []
            for line in lines:
                text, loc = line["text"], line["location"]
                if CAPTION.fullmatch(text):
                    captions.append(line)
                    continue
                if DECORATION.match(text):
                    continue
                match = QSTART.match(text)
                variant = text.startswith("【变式】") and current is not None
                if match or variant:
                    number = match[1] if match else current["printed_number"] + ":variant"
                    parent_id = current["question_id"] if variant else None
                    current = {"question_id": entity_id(evidence, "q", line["line_id"]),
                               "book_id": evidence["book_id"], "section_path": loc["section_path"],
                               "printed_number": number, "parent_question_id": parent_id,
                               "anchor_ref": line["line_id"], "asset_id": page["asset_id"],
                               "fragments": [], "candidate_answer_ids": [], "selected_answer_id": None,
                               "verification_status": "UNVERIFIED", "flags": []}
                    questions.append(current)
                if current is None or current["section_path"] != loc["section_path"]:
                    assembly_issues.append({"code": "ORPHAN_TEXT", "evidence_refs": [line["line_id"]]})
                    continue
                if current["fragments"] and current["fragments"][-1]["column"] != loc["column"]:
                    current["flags"].append("CROSS_COLUMN_CONTINUATION")
                opt = OPTION.match(text)
                previous = current["fragments"][-1] if current["fragments"] else None
                continuation = (not opt and previous and previous["role"] == "option"
                                and previous["column"] == loc["column"]
                                and 0 <= line["bbox"][1] - previous["bbox"][3] <= 1.2 * (previous["bbox"][3]-previous["bbox"][1]))
                current["fragments"].append({"fragment_id": entity_id(evidence, "f", line["line_id"]),
                                             "role": "option" if opt or continuation else "stem", "content_type": "text",
                                             "option_label": opt[1] if opt else previous["option_label"] if continuation else None,
                                             "option_start": bool(opt), "column": loc["column"],
                                             "bbox": line["bbox"], "asset_id": page["asset_id"],
                                             "text": text, "evidence_refs": [line["line_id"]]})
            for caption in captions:
                number = CAPTION.fullmatch(caption["text"])[1]
                targets = [q for q in questions if q["asset_id"] == page["asset_id"] and
                           q["section_path"] == caption["location"]["section_path"] and q["printed_number"] == number]
                if len(targets) == 1:
                    targets[0]["fragments"].append({"fragment_id": entity_id(evidence, "caption", caption["line_id"]),
                                                   "role": "figure_caption", "content_type": "text",
                                                   "asset_id": page["asset_id"], "column": caption["location"]["column"],
                                                   "bbox": caption["bbox"], "text": caption["text"],
                                                   "evidence_refs": [caption["line_id"]]})
                    targets[0]["flags"].append("FIGURE_EXTENT_UNVERIFIED")
        else:
            continue
    answers, answer_issues, answer_coverage = assemble_answers(
        evidence, lambda role, anchor: entity_id(evidence, role, anchor))
    assembly_issues.extend(answer_issues)
    for q in questions:
        qkey = scope_key(q["book_id"], q["section_path"], q["printed_number"])
        candidates = [a for a in answers if scope_key(a["book_id"], a["section_path"], a["printed_number"]) == qkey]
        q["candidate_answer_ids"] = [a["answer_id"] for a in candidates]
        if len(candidates) == 1:
            q["selected_answer_id"] = candidates[0]["answer_id"]
        q["text"] = "\n".join(f["text"] for f in q["fragments"] if f["role"] != "figure_caption")
        q["type_candidate"] = classify(q["text"], [f["option_label"] for f in q["fragments"] if f.get("option_start")],
                                       candidates[0]["text"] if len(candidates) == 1 else None)
        if len(set(re.findall(r"[（(](\d+)[）)]", q["text"]))) > 1:
            q["flags"].append("SHARED_MATERIAL_STRUCTURE_REVIEW")
        q["flags"] = sorted(set(q["flags"]))
    payload = {"questions": questions, "answers": answers, "issues": assembly_issues,
               "answer_coverage": answer_coverage,
               "matching": "book+reviewed_section_path+printed_number; unique candidate only",
               "unmatched_answer_ids": [a["answer_id"] for a in answers if not any(
                   a["answer_id"] in q["candidate_answer_ids"] for q in questions)],
               "selection_status": "DRAFT_UNVERIFIED", "platform_actions": []}
    if evidence["schema_version"] == EVIDENCE_STRUCTURED_SCHEMA:
        payload.update(shared_materials=shared_materials, question_source_coverage=question_source_coverage)
    schema = (GRAPH_STRUCTURED_SCHEMA if evidence["schema_version"] == EVIDENCE_STRUCTURED_SCHEMA else
              "b-graph-trial/0.3" if evidence["schema_version"].endswith("/0.3") else GRAPH_SCHEMA)
    return artifact(schema, "QuestionGraphTrial", evidence, payload, [ref(evidence)],
                    {"module": __name__ + ".assemble", "version": "0.2.0", "code_sha256": code_digest(Path(__file__)),
                     "policy_code_sha256": code_digest(Path(__file__).with_name("policy.py")),
                     "answer_assembly_code_sha256": code_digest(Path(__file__).with_name("answer_assembly.py"))})


def scalar_issues(value, expected):
    # Whitespace is harmless; a colon changes mathematical meaning. No fuzzy
    # matching, ratio-to-number conversion or automatic repair is performed.
    normalized = re.sub(r"\s+", "", value)
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", normalized):
        return ["ANSWER_SCALAR_FORMAT"]
    return [] if abs(float(normalized) - float(expected)) < 1e-9 else ["ANSWER_VALUE_MISMATCH"]


def quality_check(evidence, graph, review):
    check_artifact(evidence, {EVIDENCE_SCHEMA, "b-evidence-trial/0.3", EVIDENCE_STRUCTURED_SCHEMA})
    expected_graph = (GRAPH_STRUCTURED_SCHEMA if evidence["schema_version"] == EVIDENCE_STRUCTURED_SCHEMA else
                      "b-graph-trial/0.3" if evidence["schema_version"].endswith("/0.3") else GRAPH_SCHEMA)
    check_artifact(graph, {expected_graph})
    if (graph["book_id"], graph["scope_id"], graph["input_refs"]) != (evidence["book_id"], evidence["scope_id"], [ref(evidence)]):
        raise ValueError("graph not bound to this evidence revision")
    if review.get("schema_version") != "b-review-trial/0.1":
        raise ValueError("unsupported review schema")
    if review.get("book_id") != evidence["book_id"] or review.get("scope_id") != evidence["scope_id"]:
        raise ValueError("review book/scope mismatch")
    if evidence["schema_version"] == EVIDENCE_STRUCTURED_SCHEMA:
        context=evidence["payload"]["context"]
        expected_census={page["asset_id"]:{"sha256":page["source"]["sha256"],"printed_numbers":[
            group["printed_number"] for group in context["pages"][page["asset_id"]]["reviewed_layout"]["groups"]
            if group["kind"]=="QUESTION"]} for page in evidence["payload"]["pages"]}
        if (set(review)!={"schema_version","artifact_id","book_id","scope_id","reference_quality","provenance",
                         "question_census","answer_checks"}
                or not isinstance(review.get("artifact_id"),str) or not review.get("artifact_id")
                or review.get("reference_quality")!="MODEL_VISUAL_DEVELOPMENT_REVIEW"
                or review.get("provenance")!=("Coordinator original-image observation before recognition. Top-level printed question 8, "
                    "its unnumbered variant, and separately unnumbered reading material with tasks (1)(2)(3). "
                    "The numeric census alone does not certify material coverage.")
                or review.get("question_census")!=expected_census or review.get("answer_checks")!=[]):
            raise ValueError("structured review must remain the exact model-development census")
    pages = {p["asset_id"]: p for p in evidence["payload"]["pages"]}
    for aid, census in review["question_census"].items():
        if aid not in pages or census["sha256"] != pages[aid]["source"]["sha256"]:
            raise ValueError("review asset hash mismatch")
    issues = []

    def add(code, scope, refs=(), severity="ERROR", detail=None):
        issues.append({"issue_id": "issue-" + digest([code, scope, refs, detail])[:24],
                       "code": code, "scope_type": "question" if scope.startswith("q-") else "answer" if scope.startswith("a-") else "asset" if scope in pages else "scope",
                       "scope_id": scope, "evidence_refs": list(refs), "severity": severity,
                       "blocks": ["PRE_APPLY"], "suggested_strategy": "REVIEW_OFFLINE", "detail": detail})

    questions, answers = graph["payload"]["questions"], graph["payload"]["answers"]
    question_findings, coverage = audit_questions(evidence, graph, review, scope_key=scope_key, scalar_issues=scalar_issues)
    for finding in question_findings:
        add(finding["code"], finding["scope_id"], finding["evidence_refs"], finding["severity"], finding["detail"])
    answer_findings, answer_metrics = audit_answers(evidence, graph, review)
    recovery_findings, recovery_metrics = audit_recovery(evidence, graph)
    answer_findings.extend(recovery_findings)
    answer_metrics.update(recovery_metrics)
    for finding in answer_findings:
        add(finding["code"], finding["scope_id"], finding["evidence_refs"], finding["severity"], finding["detail"])
    if evidence["schema_version"] == EVIDENCE_STRUCTURED_SCHEMA:
        for material in graph["payload"].get("shared_materials", []):
            material_fragments = (material["title_fragments"] + material["body_fragments"]
                                  + material["figure_label_fragments"] + material["task_section_heading_fragments"])
            refs = [ref for fragment in material_fragments for ref in fragment["evidence_refs"]]
            add("SHARED_MATERIAL_TRANSCRIPTION_UNVERIFIED", material["material_id"], refs, "REVIEW",
                {"tasks": len(material["tasks"]), "counting_status": material["counting_status"]})
            add("FIGURE_EXTENT_UNVERIFIED", material["material_id"], refs, "REVIEW")
            for task in material["tasks"]:
                task_refs = [ref for fragment in task["fragments"] for ref in fragment["evidence_refs"]]
                add("SHARED_TASK_COUNT_AND_SCORING_UNKNOWN", task["task_id"], task_refs, "REVIEW",
                    {"label": task["label"], "response_kind": task["response_kind"]})
    # This independent development census catches a removed whole question, but
    # does not certify diagram extents, formula transcription or business truth.
    add("BUSINESS_REVIEW_REQUIRED", evidence["scope_id"], severity="REVIEW",
        detail="Development visual references and shared OCR are not independent business acceptance.")
    for item in graph["payload"]["issues"]:
        if item["code"] == "UNASSIGNED_ANSWER_OCR_LINE":
            continue  # The independent ledger audit reports every such source line.
        add(item["code"], item.get("answer_id", evidence["scope_id"]), item["evidence_refs"], "REVIEW", item.get("detail"))
    payload = {"stage": "PRE_APPLY", "decision": "HOLD", "issues": issues, "page_coverage": coverage,
               "reason": "Unverified offline draft; blocking issues require review. No platform actions authorized.",
               "summary": {"questions": len(questions), "answers": len(answers),
                           "unique_candidate_links": sum(q["selected_answer_id"] is not None for q in questions),
                           "issues": len(issues), **answer_metrics}}
    if evidence["schema_version"] == EVIDENCE_STRUCTURED_SCHEMA:
        payload["summary"].update(shared_materials=len(graph["payload"].get("shared_materials", [])),
                                  shared_tasks=sum(len(value["tasks"]) for value in graph["payload"].get("shared_materials", [])),
                                  question_source_rows=len(graph["payload"].get("question_source_coverage", [])))
    schema = (CHECK_STRUCTURED_SCHEMA if evidence["schema_version"] == EVIDENCE_STRUCTURED_SCHEMA else
              "b-check-trial/0.3" if evidence["schema_version"].endswith("/0.3") else CHECK_SCHEMA)
    return artifact(schema, "CheckReportTrial", evidence, payload,
                    [ref(evidence), ref(graph), {"artifact_id": review["artifact_id"], "content_hash": digest(review)}],
                    {"module": __name__ + ".quality_check", "version": "0.2.0", "code_sha256": code_digest(Path(__file__)),
                     "answer_quality_code_sha256": code_digest(Path(__file__).with_name("answer_quality.py"))})


def draw_graph(source_path, graph):
    _, inputs = load_source(source_path)
    overlays = {}
    for asset, path in inputs:
        image = Image.open(path).convert("RGB")
        draw = ImageDraw.Draw(image)
        for q in graph["payload"]["questions"]:
            for f in q["fragments"]:
                if f["asset_id"] == asset["asset_id"]:
                    draw.rectangle(f["bbox"], outline="orange" if f["role"] == "figure_caption" else "red", width=2)
                    draw.text((f["bbox"][0], f["bbox"][1]-12), q["printed_number"], fill="blue")
        for answer in graph["payload"]["answers"]:
            for fragment in answer.get("fragments", []):
                if fragment["asset_id"] == asset["asset_id"]:
                    color = "purple" if fragment["role"] == "explanation" else "blue"
                    draw.rectangle(fragment["bbox"], outline=color, width=2)
                    label = ("E:" if fragment["role"] == "explanation" else "A:") + answer["printed_number"]
                    draw.text((fragment["bbox"][0], fragment["bbox"][1]-12), label, fill=color)
        overlays[asset["asset_id"]] = image
    return overlays
