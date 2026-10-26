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
    "resolved_answer_character_geometry",
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


def _geometry_answers(questions, plan, evidence, by_number):
    """Expose only independently checked character groups already in the source.

    These groups can occupy one piece of a shared OCR row, but each has its own
    observed character boxes and blank gutters. A raw text span alone does not
    qualify. This path never changes the graph's selected answer or a frame.
    """
    by_question = {q["source_instance_id"]: q for q in questions}
    items = {item["item_id"]: item for item in plan["items"] if item["role"] == "answer"}
    spans = {span["item_id"]: span for span in evidence["payload"].get("character_geometry_spans", [])}
    for pairing in plan.get("pairing_status", []):
        if pairing.get("status") != "CUSTOMER_REVIEW":
            continue
        question = by_question.get(pairing.get("question_item_id"))
        item = items.get(pairing.get("answer_item_id"))
        span = spans.get(pairing.get("answer_item_id"))
        if not question or not item or not span or len(item.get("fragments", [])) != 1:
            continue
        part = item["fragments"][0]
        page = by_number.get(part.get("page"))
        if not page or page["page_role"] != "answer" or page["asset_id"] != span.get("asset_id"):
            continue
        source = page["source"]
        rows = part.get("row_indices", [])
        text_spans = part.get("text_spans", [])
        if (len(rows) != 1 or len(text_spans) != 1 or
                text_spans[0] != {"row_index": rows[0], "start": span.get("char_span", [None, None])[0],
                                  "end": span.get("char_span", [None, None])[1]} or
                part.get("geometry_group_id") != span.get("group_id") or
                part.get("geometry_observation_id") != span.get("observation_id") or
                part.get("bbox") != span.get("bbox") or
                part.get("observation_text") != span.get("text") or
                part.get("original_row_text") != span.get("original_row_text") or
                span.get("row") != rows[0] or span.get("source_sha256") != source.get("sha256") or
                not isinstance(span.get("char_boxes"), list) or not span["char_boxes"] or
                len(span["char_boxes"]) != len(span.get("text", ""))):
            continue
        parent = next((line for line in page["ocr_lines"]
                       if line.get("source_row_index") == rows[0]), None)
        detail = next((line for line in page.get("answer_detail_lines", [])
                       if line.get("line_id") == span.get("line_id")), None)
        proof = span.get("proof", {})
        if (not parent or parent.get("text") != span["original_row_text"] or
                not detail or detail.get("geometry_verified") is not True or
                detail.get("bbox") != span["bbox"] or detail.get("text") != span["text"] or
                detail.get("parent_line_id") != parent.get("line_id") or
                (proof.get("left_gap") or {}).get("passed") is not True or
                (proof.get("right_gap") or {}).get("passed") is not True):
            continue
        box = span["bbox"]
        if (not isinstance(box, (tuple, list)) or len(box) != 4 or
                not all(type(value) in (int, float) and math.isfinite(value) for value in box) or
                not 0 <= box[0] < box[2] <= source["width"] or
                not 0 <= box[1] < box[3] <= source["height"]):
            continue
        # Another independently observed answer must never share these pixels.
        if any(other is not span and other.get("asset_id") == page["asset_id"] and
               isinstance(other.get("bbox"), list) and len(other["bbox"]) == 4 and
               max(box[0], other["bbox"][0]) < min(box[2], other["bbox"][2]) and
               max(box[1], other["bbox"][1]) < min(box[3], other["bbox"][3])
               for other in spans.values()):
            continue
        match = re.fullmatch(r"\s*" + re.escape(str(item["label"])) + r"\s*[.．、]\s*(.+?)\s*", span["text"], re.S)
        if not match or item["label"] != question["printed_number"]:
            continue
        question["answer_source_candidates"].append({
            "candidate_id": item["item_id"], "question_item_id": question["source_instance_id"],
            "source_kind": "resolved_answer_character_geometry", "page": part["page"],
            "asset_id": page["asset_id"], "source_sha256": source["sha256"],
            "bbox": [math.floor(box[0]), math.floor(box[1]), math.ceil(box[2]), math.ceil(box[3])],
            "text": span["text"], "suggested_answer_text": match.group(1).strip(),
            "source_binding_status": "ORIGINAL_PAGE_BOUND", "direct_binding_allowed": True,
            "binding_note": "独立字符像素框及左右空白间隔已核对；答案内容仍须人工逐字检查",
            "original_ocr_row_index": rows[0], "observation_id": span["observation_id"],
            "requires_review": True, "selected": False, "content_approved": False,
            "proof": copy.deepcopy(proof),
            "source_record": {"answer_item_id": item["item_id"], "geometry_group_id": span["group_id"],
                              "parent_line_id": span["parent_line_id"],
                              "char_span": copy.deepcopy(span["char_span"]),
                              "original_row_text": span["original_row_text"]},
        })


def _shared_answer_previews(questions, plan, by_number):
    """Keep existing paired OCR spans visible when their pixels are shared.

    The raw row may contain several answers or a long worked solution. Its
    bbox is a reading aid only, never a direct answer frame.
    """
    by_question = {q["source_instance_id"]: q for q in questions}
    items = {item["item_id"]: item for item in plan["items"] if item["role"] == "answer"}
    for pairing in plan.get("pairing_status", []):
        if pairing.get("status") != "CUSTOMER_REVIEW":
            continue
        question = by_question.get(pairing.get("question_item_id"))
        item = items.get(pairing.get("answer_item_id"))
        if not question or not item or any(
                source["candidate_id"] == item["item_id"]
                for source in question["answer_source_candidates"]):
            continue
        for index, part in enumerate(item.get("fragments", [])):
            page = by_number.get(part.get("page"))
            if not page or page["page_role"] != "answer":
                continue
            source = page["source"]
            box = part.get("bbox")
            if (not isinstance(box, (list, tuple)) or len(box) != 4 or
                    not all(type(v) in (int, float) and math.isfinite(v) for v in box) or
                    not 0 <= box[0] < box[2] <= source["width"] or
                    not 0 <= box[1] < box[3] <= source["height"]):
                continue
            lines = {line.get("source_row_index"): line for line in page["ocr_lines"]}
            snippets = []
            valid = True
            for row in part.get("row_indices", []):
                line = lines.get(row)
                if line is None:
                    valid = False
                    break
                ranges = [(span["start"], span["end"])
                          for span in part.get("text_spans", []) if span.get("row_index") == row]
                if not ranges:
                    ranges = [(0, len(line["text"]))]
                for start, end in ranges:
                    if (type(start) is not int or type(end) is not int or
                            not 0 <= start < end <= len(line["text"])):
                        valid = False
                        break
                    snippets.append(line["text"][start:end])
                if not valid:
                    break
            if not valid or not snippets:
                continue
            question["answer_source_candidates"].append({
                "candidate_id": item["item_id"] + "/read-only/" + str(index),
                "question_item_id": question["source_instance_id"],
                "source_kind": "resolved_answer_item_shared_ocr",
                "page": part["page"], "asset_id": page["asset_id"],
                "source_sha256": source["sha256"],
                "bbox": [math.floor(box[0]), math.floor(box[1]),
                         math.ceil(box[2]), math.ceil(box[3])],
                "text": "\n".join(snippets), "suggested_answer_text": "",
                "source_binding_status": "ORIGINAL_PAGE_BOUND",
                "direct_binding_allowed": False,
                "binding_note": "共享识别行或长解答仅供对照原图，需精确画框后配答",
                "original_ocr_row_index": (part["row_indices"][0]
                                            if len(part.get("row_indices", [])) == 1 else None),
                "observation_id": part.get("geometry_observation_id"),
                "requires_review": True, "selected": False, "content_approved": False,
                "proof": {"source_item_id": item["item_id"], "fragment_index": index,
                          "pairing_status": pairing["status"], "pairing_reason": pairing.get("reason")},
                "source_record": copy.deepcopy(part),
            })


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
    _geometry_answers(questions, plan, evidence, by_number)
    _shared_answer_previews(questions, plan, by_number)
    for question in questions:
        question["answer_source_candidates"].sort(
            key=lambda p: (p["page"] or 0, p["bbox"][1] if p["bbox"] else 0,
                           p["source_kind"], p["candidate_id"] or ""))
