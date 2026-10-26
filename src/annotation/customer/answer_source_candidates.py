"""Show fixed-source answer observations without silently selecting an answer."""
from __future__ import annotations

import copy
import json
import math
import re


TABLES = (
    "answer_choice_boundary_candidates",
    "supplemental_answer_candidates",
    "independent_roi_answer_sources",
    "numeric_boundary_answer_candidates",
    "visual_answer_sources",
    "missing_short_answer_candidates",
)
INDEPENDENT_PIXEL_SOURCES = {
    "independent_roi_answer_sources", "numeric_boundary_answer_candidates",
    "visual_answer_sources", "missing_short_answer_candidates",
}


def _decode(value):
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return value


def _bbox(record, table, line):
    if table == "answer_choice_boundary_candidates":
        return line.get("bbox") if line else None
    return _decode(record.get("bbox_json"))


def _preview_text(record, table, line):
    if table == "answer_choice_boundary_candidates":
        return line.get("text", "") if line else record.get("raw_token", "")
    return (record.get("raw_text") or record.get("group_text") or
            record.get("raw_token") or record.get("visual_reading") or
            record.get("answer_text") or "")


def _suggestion(record, table, printed_number):
    if table == "visual_answer_sources":
        return record.get("visual_reading") or record.get("latex") or ""
    if table == "missing_short_answer_candidates":
        return record.get("answer_text") or ""
    value = record.get("group_text") or record.get("raw_token") or ""
    label = str(record.get("label") or printed_number)
    match = re.match(r"^\s*" + re.escape(label) + r"\s*[.．、]\s*(.*)$", value, re.S)
    return match.group(1).strip() if match else ""


def attach(questions, plan, evidence):
    """Attach read-only previews by exact source question ID and original pixels.

    Independent ROI and visual observations deliberately carry no original OCR
    row binding. A displayed suggestion cannot become the graph's selected
    answer, a production frame, or a customer confirmation through this path.
    """
    pages = {p["asset_id"]: p for p in evidence["payload"]["pages"]}
    by_number = {int(n): pages[aid] for n, aid in plan["page_assets"].items() if aid in pages}
    lines = {(p["asset_id"], line.get("source_row_index")): line
             for p in pages.values() if p["page_role"] == "answer"
             for line in p["ocr_lines"] if type(line.get("source_row_index")) is int}
    by_question = {q["source_instance_id"]: q for q in questions}
    for question in questions:
        question["answer_source_candidates"] = []
    for table in TABLES:
        for original in plan.get(table, []):
            record = copy.deepcopy(original)
            question = by_question.get(record.get("question_item_id"))
            if question is None:
                continue
            number = record.get("answer_page", record.get("page"))
            page = by_number.get(number)
            aid = page["asset_id"] if page and page["page_role"] == "answer" else None
            row = record.get("row_index") if table in {
                "answer_choice_boundary_candidates", "supplemental_answer_candidates"} else None
            line = lines.get((aid, row)) if aid is not None and type(row) is int else None
            box = _bbox(record, table, line)
            source = page["source"] if aid is not None else {}
            raw_box_valid = (isinstance(box, (tuple, list)) and len(box) == 4 and
                all(type(v) in (int, float) and math.isfinite(v) for v in box) and
                0 <= box[0] < box[2] <= source.get("width", 0) and
                0 <= box[1] < box[3] <= source.get("height", 0))
            exact_source = aid is not None and record.get("source_sha256") == source.get("sha256")
            original_ocr_row = table == "answer_choice_boundary_candidates" or (
                table == "supplemental_answer_candidates" and type(row) is int and row >= 0)
            if original_ocr_row:
                exact_source = exact_source and line is not None
                start, end = record.get("start_offset"), record.get("end_offset")
                exact_source = (exact_source and type(start) is int and type(end) is int
                    and 0 <= start < end <= len(line["text"])
                    and line["text"][start:end] == record.get("raw_token"))
            if table == "supplemental_answer_candidates" and original_ocr_row:
                exact_source = exact_source and record.get("raw_text") == (line or {}).get("text")
            if table == "supplemental_answer_candidates" and not original_ocr_row:
                # Negative source rows refer to independent ROI observations,
                # never to the source page's OCR row array.
                fragments = _decode(record.get("fragments_json")) or []
                exact_source = (exact_source and record.get("origin") == "LOCAL_ROI_OBSERVATION"
                    and type(row) is int and row < 0 and type(fragments) is list
                    and any(f.get("roi_observation_id") and not f.get("row_indices")
                            for f in fragments if type(f) is dict))
            bound = bool(raw_box_valid and exact_source)
            direct_binding_allowed = bound and table in INDEPENDENT_PIXEL_SOURCES
            box = ([math.floor(box[0]), math.floor(box[1]),
                    math.ceil(box[2]), math.ceil(box[3])] if raw_box_valid else None)
            identity = record.get("candidate_id") or record.get("answer_item_id")
            preview = {
                "candidate_id": identity,
                "question_item_id": record["question_item_id"],
                "source_kind": table,
                "page": number,
                "asset_id": aid if bound else None,
                "source_sha256": record.get("source_sha256"),
                "bbox": box,
                "text": _preview_text(record, table, line),
                "suggested_answer_text": _suggestion(record, table, question["printed_number"]),
                "source_binding_status": "ORIGINAL_PAGE_BOUND" if bound else "SOURCE_MISMATCH_REVIEW",
                "direct_binding_allowed": direct_binding_allowed,
                "binding_note": ("独立像素框，仍须逐字核对原图" if direct_binding_allowed else
                                 "共享识别行或来源未核实，请在原图精确画框后再配答"),
                "original_ocr_row_index": row if original_ocr_row else None,
                "observation_id": record.get("observation_id") or (
                    (_decode(record.get("fragments_json")) or [{}])[0].get("roi_observation_id")
                    if table == "supplemental_answer_candidates" and not original_ocr_row else None),
                "requires_review": True,
                "selected": False,
                "content_approved": False,
                "proof": _decode(record.get("proof_json")),
                "source_record": record,
            }
            question["answer_source_candidates"].append(preview)
    for question in questions:
        question["answer_source_candidates"].sort(
            key=lambda p: (p["page"] or 0, p["bbox"][1] if p["bbox"] else 0,
                           p["source_kind"], p["candidate_id"] or ""))
