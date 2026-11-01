"""Unselected inline-math source ROIs from raw CTC localization estimates.

This module never imports an OCR runtime or reads a transcription review.
All raw observations and every mathlike run survive alongside full-row crops.
Fixed context padding cannot prove that a missing glyph has been localized.
"""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path

from PIL import Image

from .baseline import code_digest, digest, file_digest, valid_bbox

SCHEMA = "b-inline-math-layout-trial/0.1"
CONFIG = {
    "policy": "ALL_RAW_MATHLIKE_RUNS_WITH_FULL_LINE_FALLBACK/0.1",
    "source_row_padding": 2,
    "variants": [{"variant_id": "scale3", "scale": 3}, {"variant_id": "scale4", "scale": 4}],
    "resampling": "PIL_LANCZOS",
    "horizontal_halo": {"minimum_source_pixels": 4, "full_crop_height_multiplier": 1},
    "vertical_policy": "ENTIRE_ORIGINAL_ROW_CROP_HEIGHT_NO_TRIM",
    "rounding": "FLOOR_MIN_CEIL_MAX_CLAMP_ORIGINAL_PAGE",
    "ambiguous_bridge": "DECIMAL_DIGIT_TEN_CHARACTER_DECIMAL_DIGIT_ONLY",
    "text_policy": "VERBATIM_NO_OPERATOR_OR_EXPONENT_CORRECTION",
    "overlap_policy": "RETAIN_ALL_NO_NMS_NO_SELECTION",
}
OPERATORS = frozenset("=+-−×÷*/<>≤≥≠≈±∓√∛∜^_%∞∑∏∫∂∇∈∉∪∩∠⊥∥°:＝＋－＜＞")
SUPERSCRIPTS = frozenset("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")
CONNECTORS = frozenset("()[]{}（）［］｛｝.．, ")
BASE_RISKS = ["CTC_ESTIMATED_POSITION", "MISSING_GLYPH_NOT_LOCALIZED", "COMPLETE_MATH_COVERAGE_UNPROVEN"]


def reference(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def _id(prefix, value):
    return prefix + "-" + digest(value)[:24]


def _rgb_sha(image):
    return hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _core(char):
    return (char.isdecimal() or "A" <= char <= "Z" or "a" <= char <= "z"
            or "\u0370" <= char <= "\u03ff" or char in OPERATORS or char in SUPERSCRIPTS)


def mathlike_spans(text):
    """Return all maximal verbatim spans; punctuation is not repaired.

    A Chinese 十 only bridges immediate decimal digits. It remains 十 and is
    explicitly uncertain, including when the original really meant ten.
    """
    if not isinstance(text, str):
        raise ValueError("mathlike input must be a string")
    allowed = [_core(c) or c in CONNECTORS or c.isspace()
               or (c == "十" and i > 0 and i+1 < len(text)
                   and text[i-1].isdecimal() and text[i+1].isdecimal()) for i, c in enumerate(text)]
    spans, index = [], 0
    while index < len(text):
        if not allowed[index]:
            index += 1
            continue
        end = index+1
        while end < len(text) and allowed[end]:
            end += 1
        start, stop = index, end
        while start < stop and text[start].isspace(): start += 1
        while stop > start and text[stop-1].isspace(): stop -= 1
        if any(_core(c) for c in text[start:stop]):
            spans.append([start, stop])
        index = end
    return spans


def _polygon(box, variant):
    if (not isinstance(box, list) or len(box) != 4
            or any(not isinstance(p, list) or len(p) != 2 or not all(_number(n) for n in p) for p in box)):
        return None, ["CTC_WORD_GEOMETRY_INVALID"]
    scale, transform = variant["scale"], variant["variant_to_original"]
    projected = [[p[0]/scale+transform[0][2], p[1]/scale+transform[1][2]] for p in box]
    risks = []
    if any(not 0 <= p[0] <= variant["size"][0] or not 0 <= p[1] <= variant["size"][1] for p in box):
        risks.append("CTC_WORD_OUTSIDE_INPUT")
    area = abs(sum(box[i][0]*box[(i+1) % 4][1]-box[(i+1) % 4][0]*box[i][1] for i in range(4)))/2
    if area == 0: risks.append("CTC_DEGENERATE_WORD_ESTIMATE")
    return projected, risks


def _checked_inputs(evidence, observations, original_path, line_ids):
    if (not isinstance(evidence, dict) or evidence.get("schema_version") not in {"b-evidence-trial/0.2", "b-evidence-trial/0.3"}
            or evidence.get("kind") != "EvidenceBundleTrial" or evidence.get("content_hash") != digest(evidence.get("payload"))):
        raise ValueError("invalid inline math source evidence")
    if (not isinstance(observations, dict) or observations.get("schema_version") != "b-inline-ocr-observation-trial/0.1"
            or observations.get("kind") != "InlineOCRObservationTrial"
            or observations.get("content_hash") != digest(observations.get("payload"))):
        raise ValueError("invalid inline OCR observations")
    if (not isinstance(line_ids, (list, tuple)) or not line_ids or any(not isinstance(x, str) or not x for x in line_ids)
            or len(set(line_ids)) != len(line_ids)):
        raise ValueError("explicit unique nonempty line_ids are required")
    p = observations["payload"]
    if (observations.get("book_id"), observations.get("scope_id")) != (evidence.get("book_id"), evidence.get("scope_id")):
        raise ValueError("inline math source scope mismatch")
    if p.get("evidence_ref") != reference(evidence) or observations.get("input_refs") != [reference(evidence)]:
        raise ValueError("inline math evidence reference mismatch")
    if p.get("requested_line_ids") != list(line_ids) or [r.get("line_id") for r in p.get("rows", [])] != list(line_ids):
        raise ValueError("inline math declared row scope or order mismatch")
    source = p["source"]
    pages = [page for page in evidence["payload"]["pages"] if page["asset_id"] == source["asset_id"]]
    if len(pages) != 1 or source.get("asset") != pages[0]["source"]:
        raise ValueError("inline math asset descriptor mismatch")
    asset = source["asset"]
    if source.get("original_sha256") != asset["sha256"] or file_digest(Path(original_path)) != asset["sha256"]:
        raise ValueError("inline math original source SHA mismatch")
    with Image.open(original_path) as opened:
        image = opened.convert("RGB")
    if (image.size != (asset["width"], asset["height"]) or (source.get("width"), source.get("height")) != image.size
            or source.get("original_rgb_sha256") != _rgb_sha(image)):
        raise ValueError("inline math original source pixels mismatch")
    by_id = {line["line_id"]: line for line in pages[0]["ocr_lines"]}
    if len(by_id) != len(pages[0]["ocr_lines"]):
        raise ValueError("duplicate original line identity")
    for row in p["rows"]:
        line, box = by_id.get(row["line_id"]), row.get("bbox")
        if (line is None or row.get("source_line") != line or box != line.get("bbox")
                or row.get("asset_id") != source["asset_id"] or not valid_bbox(box, image.width, image.height)):
            raise ValueError("inline math original row binding mismatch")
        pad = CONFIG["source_row_padding"]
        expected = [max(0, math.floor(box[0])-pad), max(0, math.floor(box[1])-pad),
                    min(image.width, math.ceil(box[2])+pad), min(image.height, math.ceil(box[3])+pad)]
        crop = image.crop(expected)
        if row.get("crop_bbox") != expected or row.get("crop_size") != list(crop.size) or row.get("crop_rgb_sha256") != _rgb_sha(crop):
            raise ValueError("inline math original row crop mismatch")
        if [v.get("variant_id") for v in row.get("variants", [])] != [v["variant_id"] for v in CONFIG["variants"]]:
            raise ValueError("inline math variant scope or order mismatch")
        for v, definition in zip(row["variants"], CONFIG["variants"]):
            scale = definition["scale"]
            rgb = crop.resize((crop.width*scale, crop.height*scale), Image.Resampling.LANCZOS)
            matrix = [[1/scale, 0, expected[0]], [0, 1/scale, expected[1]], [0, 0, 1]]
            if (v.get("scale") != scale or v.get("variant_to_original") != matrix or v.get("size") != list(rgb.size)
                    or v.get("rgb_sha256") != _rgb_sha(rgb) or v.get("bgr_sha256") != hashlib.sha256(rgb.tobytes("raw", "BGR")).hexdigest()
                    or v.get("dtype") != "uint8" or v.get("channel_order") != "BGR"):
                raise ValueError("inline math transformed row pixels mismatch")
            raw_call = v.get("raw_call_result")
            if v.get("recognition_error") is None and (not isinstance(raw_call, list) or len(raw_call) != 2
                    or v.get("raw_ocr_result") != raw_call[0] or v.get("engine_elapsed_seconds") != raw_call[1]):
                raise ValueError("inline math raw OCR call binding mismatch")
    return image, p


def _unit(observations, row, variant, image, *, raw_index=None, span=None, text=None,
          word_indices=None, polygons=None, risks=None):
    kind = "FULL_LINE_FALLBACK" if span is None else "MATHLIKE_RUN"
    issues = list(BASE_RISKS)+(risks or [])
    core = None
    crop_box = row["crop_bbox"]
    halo = max(CONFIG["horizontal_halo"]["minimum_source_pixels"], crop_box[3]-crop_box[1])
    roi = list(crop_box)
    if polygons is not None:
        if all(p is not None for p in polygons) and polygons:
            points = [point for polygon in polygons for point in polygon]
            core = [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]
            requested = [math.floor(core[0])-halo, crop_box[1], math.ceil(core[2])+halo, crop_box[3]]
            candidate_roi = [max(0, requested[0]), requested[1], min(image.width, requested[2]), requested[3]]
            if candidate_roi[2] > candidate_roi[0]:
                roi = candidate_roi
                if roi != requested: issues.append("SOURCE_EDGE_CONTEXT_CLAMPED")
                if roi[0] < crop_box[0] or roi[2] > crop_box[2]: issues.append("CONTEXT_OUTSIDE_RECOGNITION_CROP")
            else:
                issues.append("CTC_ROI_OUTSIDE_SOURCE_FULL_LINE_FALLBACK")
        else:
            issues.append("UNLOCATED_MATH_RUN_FULL_LINE_FALLBACK")
    cropped = image.crop(roi)
    payload = {"kind": kind, "line_id": row["line_id"], "row_id": row["row_id"], "asset_id": row["asset_id"],
               "variant_id": variant["variant_id"], "raw_result_index": raw_index, "char_span": span,
               "raw_text": text, "raw_word_indices": word_indices or [], "core_source_bbox": core,
               "source_bbox": roi, "crop_size": list(cropped.size), "crop_rgb_sha256": _rgb_sha(cropped),
               "horizontal_halo_source_pixels": halo, "variant_to_original": copy.deepcopy(variant["variant_to_original"]),
               "risks": sorted(set(issues)), "verification_status": "UNVERIFIED", "complete": False,
               "localization_kind": "CTC_TIMESTEP_ESTIMATE", "precise_glyph_localization": False,
               "spatial_role_verified": False, "selected": False}
    return {"unit_id": _id("inline-math-unit", [reference(observations), payload]), **payload}


def build_inline_math_layout(evidence, observations, original_path, *, line_ids):
    """Propose all source-bound mathlike ROIs without running any model.

    line_ids is an external declared scope, not inferred from recognized math.
    Full-row fallback candidates remain even when OCR fails or emits no maths.
    A run with unusable boxes is retained with the full row as its explicit ROI.
    """
    image, p = _checked_inputs(evidence, observations, original_path, line_ids)
    units, rows = [], []
    raw_row_count = 0
    for row in p["rows"]:
        summary = {key: copy.deepcopy(row[key]) for key in ("line_id", "row_id", "asset_id", "source_line", "bbox", "crop_bbox", "crop_size", "crop_rgb_sha256")}
        summary["variants"] = []
        for variant in row["variants"]:
            fallback = _unit(observations, row, variant, image,
                risks=["ROW_RECOGNITION_FAILED"] if variant.get("recognition_error") is not None else [])
            units.append(fallback)
            raw = variant.get("raw_ocr_result")
            variant_summary = {"variant_id": variant["variant_id"], "full_line_fallback_unit_id": fallback["unit_id"],
                               "mathlike_unit_ids": [], "raw_row_count": len(raw) if isinstance(raw, list) else 0, "issues": []}
            summary["variants"].append(variant_summary)
            if not isinstance(raw, list):
                variant_summary["issues"].append({"code": "RAW_ROWS_UNAVAILABLE_FULL_LINE_RETAINED"})
                continue
            raw_row_count += len(raw)
            for raw_index, entry in enumerate(raw):
                if not isinstance(entry, list) or len(entry) != 6:
                    variant_summary["issues"].append({"code": "RAW_ROW_INVALID_FULL_LINE_RETAINED", "raw_result_index": raw_index})
                    continue
                _, text, _, boxes, words, scores = entry
                if (not isinstance(text, str) or not all(isinstance(v, list) for v in (boxes, words, scores))
                        or not all(isinstance(w, str) for w in words) or not len(boxes) == len(words) == len(scores)
                        or "".join(words) != text):
                    variant_summary["issues"].append({"code": "RAW_CHARACTER_ALIGNMENT_UNRESOLVED_FULL_LINE_RETAINED", "raw_result_index": raw_index})
                    continue
                character_to_word = [index for index, word in enumerate(words) for _ in word]
                for span in mathlike_spans(text):
                    indices = list(dict.fromkeys(character_to_word[span[0]:span[1]]))
                    polygons, risks = [], []
                    for index in indices:
                        projected, geometry_risks = _polygon(boxes[index], variant)
                        polygons.append(projected)
                        risks.extend(geometry_risks)
                        if not _number(scores[index]) or not 0 <= scores[index] <= 1:
                            risks.append("CHARACTER_SCORE_INVALID")
                        elif scores[index] < .8:
                            risks.append("LOW_CHARACTER_SCORE")
                    raw_text = text[span[0]:span[1]]
                    if "十" in raw_text: risks.append("CHINESE_TEN_OPERATOR_LOOKALIKE_UNRESOLVED")
                    if len(indices) == 1: risks.append("SINGLE_ESTIMATED_TOKEN_MAY_BE_PROSE_OR_REFERENCE")
                    unit = _unit(observations, row, variant, image, raw_index=raw_index, span=span, text=raw_text,
                                 word_indices=indices, polygons=polygons, risks=risks)
                    units.append(unit)
                    variant_summary["mathlike_unit_ids"].append(unit["unit_id"])
        rows.append(summary)
    count = sum(unit["kind"] == "MATHLIKE_RUN" for unit in units)
    payload = {"evidence_ref": reference(evidence), "observation_ref": reference(observations),
               "observations_archive": copy.deepcopy(observations), "source": copy.deepcopy(p["source"]),
               "requested_line_ids": list(line_ids), "configuration": copy.deepcopy(CONFIG), "rows": rows, "units": units,
               "counts": {"declared_rows": len(rows), "variants": sum(len(r["variants"]) for r in rows),
                          "raw_rows": raw_row_count, "mathlike_runs": count, "full_line_fallbacks": len(units)-count, "units": len(units)},
               "selected_unit_ids": [], "decision": "HOLD", "verification_status": "UNVERIFIED", "complete": False,
               "business_acceptance": False, "transcription_verified": False, "platform_actions": [],
               "graph_modified": False, "expected_text_consumed": False, "model_calls": 0,
               "limitations": ["CTC boxes estimate time-step positions and full-line height, not glyph outlines or superscript roles.",
                               "A fixed halo and full-row fallback do not prove coverage of missing roots, powers or other mathematical ink.",
                               "All weak tokens, overlapping runs and both OCR variants are retained without selecting or correcting text.",
                               "Crop pixels beyond the saved whole-row height are not recovered by this proposal."]}
    producer = {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
                "dependency_code_sha256": {"baseline": code_digest(Path(__file__).with_name("baseline.py"))},
                "execution_kind": "GEOMETRIC_INLINE_PROPOSAL_NO_OCR", "configuration_sha256": digest(CONFIG)}
    inputs = [reference(evidence), reference(observations)]
    return {"schema_version": SCHEMA, "kind": "InlineMathLayoutTrial", "artifact_id": _id("inline-math-layout", [inputs, producer, payload]),
            "revision": 1, "book_id": evidence["book_id"], "scope_id": evidence["scope_id"], "input_refs": inputs,
            "producer": producer, "content_hash": digest(payload), "payload": payload}
