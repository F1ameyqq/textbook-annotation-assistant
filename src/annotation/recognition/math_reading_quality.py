"""Independent source-pixel and raw-OCR audit of provisional math readings.

No recognition or reading producer is imported. Acceptance means that the
retained observations are traceable; it never certifies a mathematical text.
The raised-ink detector is a local warning heuristic, not a glyph classifier.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re

import cv2
import numpy as np
from PIL import Image, ImageEnhance

from .baseline import code_digest, digest, file_digest

SCHEMA = "b-math-reading-check-trial/0.1"
_VARIANTS = (("scale6", 6, 1.0), ("scale8-contrast15", 8, 1.5))
_HASH = re.compile(r"^[0-9a-f]{64}$")
_SUPPORTED = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-−—=×÷*/().,^{}[]²³√π≤≥<> ")


def _ref(value):
    return {key: value.get(key) for key in ("artifact_id", "revision", "content_hash")}


def _pixels(value):
    return hashlib.sha256(np.asarray(value).tobytes()).hexdigest()


def _overlap(a, b):
    return max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))


def _inside(inner, outer):
    return all(math.isfinite(float(v)) for v in inner) and (
        outer[0] <= inner[0] < inner[2] <= outer[2]
        and outer[1] <= inner[1] < inner[3] <= outer[3])


def raised_ink_observations(image, pixel_bbox, origin):
    """Find small components ending substantially above neighboring body ink.

    Threshold 210 deliberately retains faint/split high ink in the real 40x14
    counterexample. A high *top* alone, a one-pixel rule, or an isolated dot is
    insufficient. This cannot prove that all mathematical symbols were read.
    """
    x1, y1, x2, y2 = (int(pixel_bbox[i]-origin[i % 2]) for i in range(4))
    tile = np.asarray(image.convert("L"))[y1:y2, x1:x2]
    if not tile.size:
        return []
    count, labels, stats, _ = cv2.connectedComponentsWithStats((tile < 210).astype("uint8"), 8)
    components = [(int(x), int(y), int(w), int(h), int(n))
                  for x, y, w, h, n in stats[1:] if n >= 2 and h >= 2]
    if len(components) < 2:
        return []
    # Body components have nontrivial vertical extent. Use their lower edges,
    # weighted by ink, so a small detached high glyph cannot set the baseline.
    body = [c for c in components if c[3] >= max(4, tile.shape[0]*.42)]
    if len(body) < 2:
        return []
    bottoms = sorted((y+h, n) for _, y, _, h, n in body)
    total, cumulative, baseline = sum(n for _, n in bottoms), 0, bottoms[-1][0]
    for bottom, weight in bottoms:
        cumulative += weight
        if cumulative >= total*.6:
            baseline = bottom
            break
    body_height = float(np.median([h for _, y, _, h, _ in body if y+h >= baseline-1]))
    risks = []
    for x, y, w, h, area in components:
        if (baseline-(y+h) >= max(2, body_height*.24)
                and h <= body_height*.78 and area >= 3 and w <= 2*h
                and any(abs((bx+bw/2)-(x+w/2)) <= body_height*2.5
                        and by+bh >= baseline-1 for bx, by, bw, bh, _ in body)):
            bbox = [pixel_bbox[0]+x, pixel_bbox[1]+y,
                    pixel_bbox[0]+x+w, pixel_bbox[1]+y+h]
            risks.append({"code": "RAISED_INK_UNRESOLVED", "component_bbox": bbox,
                          "threshold": 210, "body_baseline_y": pixel_bbox[1]+baseline,
                          "body_height": body_height,
                          "component_pixel_sha256": _pixels(tile[y:y+h, x:x+w]),
                          "status": "UNRESOLVED", "transcription_verified": False})
    return risks


def audit_math_reading(layout, evidence, reading, crop_path):
    """Check all roles, raw alternatives, coordinates and unresolved source ink.

    Input ``layout`` is the supplied independent layout revision, not rebuilt
    from a candidate reading. No OCR engine is imported or executed here.
    """
    issues, pixel_risks = [], []
    summary = {"fraction_count": 0, "role_count": 0, "missing_reading_count": 0,
               "raised_ink_risk_count": 0, "two_pass_agreement_count": 0}

    def issue(code, role_id=None, detail=None):
        item = {"code": code, "severity": "ERROR", "detail": detail}
        if role_id is not None:
            item["role_id"] = role_id
        if item not in issues:
            issues.append(item)

    def finish():
        summary["raised_ink_risk_count"] = len(pixel_risks)
        payload = {"accepted": not issues, "decision": "HOLD", "issues": issues,
                   "pixel_risks": pixel_risks, "summary": summary,
                   "transcription_verified": False, "business_acceptance": False,
                   "platform_actions": [],
                   "limitations": ["Raised-ink geometry is a local warning, not a symbol recognizer.",
                                   "Repeated OCR agreement cannot establish complete transcription."]}
        inputs = [_ref(value) for value in (layout, evidence, reading)]
        return {"schema_version": SCHEMA, "kind": "MathReadingCheckTrial",
                "artifact_id": "mathreadingcheck-"+digest([inputs, payload])[:24], "revision": 1,
                "book_id": layout.get("book_id"), "scope_id": layout.get("scope_id"),
                "run_id": layout.get("run_id"), "input_refs": inputs,
                "producer": {"module": __name__, "version": "0.1.0",
                             "code_sha256": code_digest(Path(__file__))},
                "content_hash": digest(payload), "payload": payload}

    for value, schema, kind, label in (
            (layout, "b-math-layout-trial/0.1", "MathLayoutTrial", "layout"),
            (evidence, "b-math-role-evidence-trial/0.1", "MathRoleEvidenceTrial", "evidence"),
            (reading, "b-math-reading-trial/0.1", "MathReadingTrial", "reading")):
        try:
            valid = (isinstance(value, dict) and value.get("schema_version") == schema
                     and value.get("kind") == kind and value.get("revision") == 1
                     and isinstance(value.get("artifact_id"), str) and bool(value["artifact_id"])
                     and isinstance(value.get("payload"), dict)
                     and value.get("content_hash") == digest(value["payload"]))
        except (ValueError, TypeError):
            valid = False
        if not valid:
            issue("MATH_READING_ARTIFACT_INVALID", detail=label)
    if issues:
        return finish()
    lp, ep, rp = layout["payload"], evidence["payload"], reading["payload"]
    for value in (evidence, reading):
        if any(value.get(k) != layout.get(k) for k in ("book_id", "scope_id", "run_id")):
            issue("MATH_READING_IDENTITY_MISMATCH")
    if (ep.get("layout_ref") != _ref(layout) or rp.get("layout_ref") != _ref(layout)
            or rp.get("role_evidence_ref") != _ref(evidence)):
        issue("MATH_READING_STALE_REFERENCE")
    if evidence.get("input_refs") != [_ref(layout)] or reading.get("input_refs") != [_ref(layout), _ref(evidence)]:
        issue("MATH_READING_STALE_REFERENCE")
    producer = evidence.get("producer", {})
    dependencies, models = producer.get("dependencies"), producer.get("model_files")
    if (not isinstance(dependencies, dict) or not isinstance(models, list)
            or producer.get("dependency_sha256") != digest(dependencies)
            or producer.get("models_sha256") != digest(models)):
        issue("MATH_READING_BACKEND_RECEIPT_INVALID")
    if producer.get("execution_kind") == "SYNTHETIC_TEST":
        if (producer.get("device") != "SYNTHETIC_TEST" or producer.get("engine") != "injected_test_backend"
                or dependencies != {} or models != []):
            issue("MATH_READING_BACKEND_RECEIPT_INVALID")
    elif producer.get("execution_kind") == "CPU_RAPIDOCR":
        if (producer.get("device") != "CPU" or producer.get("engine") != "rapidocr_onnxruntime"
                or not dependencies or not models or not any(m.get("active_in_call") for m in models)
                or any(not _HASH.fullmatch(m.get("sha256", "")) for m in models)):
            issue("MATH_READING_BACKEND_RECEIPT_INVALID")
    else:
        issue("MATH_READING_BACKEND_RECEIPT_INVALID")
    if reading.get("producer", {}).get("execution_kind") != producer.get("execution_kind"):
        issue("MATH_READING_BACKEND_RECEIPT_INVALID")
    for current in (producer, reading.get("producer", {})):
        config = current.get("configuration", {})
        if (current.get("configuration_sha256") != digest(config)
                or config.get("role_padding_pixels") != 2
                or [(v.get("variant_id"), v.get("scale"), v.get("contrast")) for v in config.get("variants", [])] != list(_VARIANTS)
                or config.get("resize") != "PIL_LANCZOS" or config.get("color") != "BGR"
                or config.get("engine_flags") != {"use_det": False, "use_cls": False, "use_rec": True}
                or not _HASH.fullmatch(current.get("code_sha256", ""))):
            issue("MATH_READING_CONFIGURATION_INVALID")
    for payload in (ep, rp):
        if (payload.get("decision") != "HOLD" or payload.get("transcription_verified") is not False
                or payload.get("verification_status") != "UNVERIFIED"
                or payload.get("formula_text_reconstructed") is not False
                or payload.get("visual_formula_references_consumed") is not False
                or payload.get("platform_actions") != []):
            issue("MATH_READING_FALSE_VERIFICATION")
        for name in ("complete", "formula_text_reconstructed", "business_acceptance", "human_reviewed", "graph_modified"):
            if payload.get(name) not in (None, False):
                issue("MATH_READING_FALSE_VERIFICATION", detail=name)
    allowed_evidence = {"layout_ref", "source", "roles", "decision", "verification_status", "transcription_verified",
                        "formula_text_reconstructed", "visual_formula_references_consumed", "platform_actions", "complete"}
    allowed_reading = {"layout_ref", "role_evidence_ref", "source", "fractions", "reading_groups", "source_ocr",
                       "source_layout_issues", "issues", "decision", "verification_status", "transcription_verified",
                       "formula_text_reconstructed", "visual_formula_references_consumed", "graph_modified",
                       "platform_actions", "limitations", "complete"}
    if set(ep)-allowed_evidence or set(rp)-allowed_reading:
        issue("MATH_READING_UNKNOWN_FIELD", detail=sorted((set(ep)-allowed_evidence) | (set(rp)-allowed_reading)))
    if rp.get("reading_groups") != lp.get("reading_groups") or rp.get("source_ocr") != lp.get("source_ocr"):
        issue("MATH_READING_LAYOUT_ORDER_CHANGED")
    if rp.get("source_layout_issues") != lp.get("issues"):
        issue("MATH_READING_LAYOUT_ISSUES_CHANGED")
    try:
        with Image.open(crop_path) as opened:
            image = opened.convert("RGB")
        crop = lp["crop_bbox"]
        if (list(image.size) != [crop[2]-crop[0], crop[3]-crop[1]]
                or file_digest(Path(crop_path)) != lp["crop_sha256"]):
            issue("MATH_READING_SOURCE_PIXELS_MISMATCH")
        expected_source = {"asset_id": lp["asset_id"], "source_sha256": lp["source_sha256"],
            "source_size": lp["source_size"], "crop_bbox": crop, "crop_sha256": lp["crop_sha256"],
            "base_crop_rgb_sha256": _pixels(image), "base_crop_size": list(image.size)}
        if ep.get("source") != expected_source or rp.get("source") != expected_source:
            issue("MATH_READING_SOURCE_BINDING_MISMATCH")
    except (OSError, KeyError, TypeError, ValueError):
        issue("MATH_READING_SOURCE_PIXELS_MISMATCH")
        return finish()
    fractions = lp.get("fraction_candidates", [])
    summary["fraction_count"], summary["role_count"] = len(fractions), 2*len(fractions)
    expected_roles = [(f["fraction_id"], role) for f in fractions for role in ("numerator", "denominator")]
    roles = ep.get("roles", [])
    if [(r.get("fraction_id"), r.get("role")) for r in roles] != expected_roles:
        issue("MATH_READING_ROLE_COVERAGE_MISMATCH")
    if len({r.get("role_id") for r in roles}) != len(roles):
        issue("MATH_READING_ROLE_ID_REUSED")
    role_fields = {"role_id", "fraction_id", "role", "pixel_bbox", "crop_bbox", "crop_local_bbox",
                   "role_crop_rgb_sha256", "role_crop_size", "original_ocr_refs", "original_raw_texts",
                   "variants", "verification_status"}
    if any(set(role) != role_fields for role in roles):
        issue("MATH_READING_UNKNOWN_FIELD", detail="evidence role")
    read_fractions = rp.get("fractions", [])
    if [f.get("fraction_id") for f in read_fractions] != [f["fraction_id"] for f in fractions]:
        issue("MATH_READING_FRACTION_COVERAGE_MISMATCH")
    pairmap = {(r.get("fraction_id"), r.get("role")): r for r in roles}
    fmap = {f.get("fraction_id"): f for f in read_fractions}
    candidate_ids = []
    all_reading_issues = []
    for fraction in fractions:
        fid, bar = fraction["fraction_id"], fraction["bar_bbox"]
        projected = fmap.get(fid, {})
        if projected.get("bar_bbox") != bar or projected.get("ambiguous_ocr_refs") != fraction.get("ambiguous_ocr_refs"):
            issue("MATH_READING_FRACTION_GEOMETRY_MISMATCH", detail=fid)
        if projected.get("status") != "ROLE_CANDIDATES_UNVERIFIED" or projected.get("verification_status") != "UNVERIFIED":
            issue("MATH_READING_FALSE_VERIFICATION", detail=fid)
        if set(projected) != {"fraction_id", "bar_bbox", "ambiguous_ocr_refs", "status", "verification_status", "numerator", "denominator"}:
            issue("MATH_READING_UNKNOWN_FIELD", detail=fid)
        for position in ("numerator", "denominator"):
            role = pairmap.get((fid, position))
            if role is None:
                continue
            rid, source_role = role.get("role_id"), fraction[position]
            target = projected.get(position, {})
            pixel_box = source_role["pixel_bbox"]
            expected_rid = "math-role-"+digest([_ref(layout), fid, position, pixel_box])[:24]
            if rid != expected_rid:
                issue("MATH_READING_ROLE_PROJECTION_MISMATCH", rid)
            extra = {"candidate_refs", "exact_two_pass_agreement", "consensus_text", "selected_candidate_refs",
                     "transcription_verified", "status", "pixel_risks", "raised_symbol_slots", "recognition_risks", "complete"}
            if set(target) != set(role) | extra or any(target.get(k) != v for k, v in role.items()):
                issue("MATH_READING_ROLE_PROJECTION_MISMATCH", rid)
            if (target.get("selected_candidate_refs") != [] or target.get("status") != "ROLE_CANDIDATES_UNVERIFIED"
                    or target.get("transcription_verified") is not False):
                issue("MATH_READING_FALSE_VERIFICATION", rid)
            if (role.get("pixel_bbox") != pixel_box or target.get("pixel_bbox") != pixel_box
                    or not _inside(pixel_box, crop)
                    or (pixel_box[3] > bar[1]+1 if position == "numerator" else pixel_box[1] < bar[3]-1)):
                issue("MATH_READING_ROLE_GEOMETRY_MISMATCH", rid)
                continue
            for key, expected in (("original_ocr_refs", source_role["ocr_refs"]),
                                  ("original_raw_texts", source_role["raw_texts"])):
                if role.get(key) != expected or target.get(key) != expected:
                    issue("MATH_READING_ORIGINAL_OCR_CHANGED", rid, key)
            if role.get("verification_status") != "UNVERIFIED" or target.get("role_id") != rid:
                issue("MATH_READING_ROLE_PROJECTION_MISMATCH", rid)
            # A producer may retain pad context, but cannot silently omit edge
            # pixels, sample another role or use a crop outside the base image.
            wanted = [max(crop[0], math.floor(pixel_box[0])-2), max(crop[1], math.floor(pixel_box[1])-2),
                      min(crop[2], math.ceil(pixel_box[2])+2), min(crop[3], math.ceil(pixel_box[3])+2)]
            local = [wanted[i]-crop[i % 2] for i in range(4)]
            tile = image.crop(local)
            if (role.get("crop_bbox") != wanted or role.get("crop_local_bbox") != local
                    or role.get("role_crop_size") != list(tile.size)
                    or role.get("role_crop_rgb_sha256") != _pixels(tile)):
                issue("MATH_READING_ROLE_PIXELS_MISMATCH", rid)
            variants = role.get("variants", [])
            if [(v.get("variant_id"), v.get("scale"), v.get("contrast")) for v in variants] != list(_VARIANTS):
                issue("MATH_READING_VARIANT_COVERAGE_MISMATCH", rid)
            if target.get("variants") != variants:
                issue("MATH_READING_RAW_VARIANTS_CHANGED", rid)
            flattened, texts = [], []
            for variant in variants:
                if set(variant) != {"variant_id", "scale", "contrast", "resize", "color", "transformed_size",
                        "transformed_bgr_sha256", "transformed_to_source", "raw_ocr_result", "engine_elapsed_seconds",
                        "wall_elapsed_seconds", "candidates", "recognition_error"}:
                    issue("MATH_READING_UNKNOWN_FIELD", rid, "variant")
                scale, contrast = variant.get("scale"), variant.get("contrast")
                if not isinstance(scale, (int, float)) or not isinstance(contrast, (int, float)) or scale <= 0:
                    issue("MATH_READING_TRANSFORM_MISMATCH", rid)
                    continue
                transformed = tile.resize((int(tile.width*scale), int(tile.height*scale)), Image.Resampling.LANCZOS)
                transformed = ImageEnhance.Contrast(transformed).enhance(contrast)
                bgr = np.asarray(transformed)[:, :, ::-1].copy()
                if (variant.get("resize") != "PIL_LANCZOS" or variant.get("color") != "BGR"
                        or variant.get("transformed_size") != list(transformed.size)
                        or variant.get("transformed_bgr_sha256") != _pixels(bgr)
                        or variant.get("transformed_to_source") != [[1/scale, 0, wanted[0]], [0, 1/scale, wanted[1]], [0, 0, 1]]):
                    issue("MATH_READING_TRANSFORM_MISMATCH", rid)
                raw, candidates = variant.get("raw_ocr_result"), variant.get("candidates", [])
                if variant.get("recognition_error") is not None:
                    if candidates or not isinstance(variant["recognition_error"], dict):
                        issue("MATH_READING_FAILURE_WITH_CANDIDATES", rid)
                    texts.append([])
                    continue
                if raw is None:
                    raw = []
                if not isinstance(raw, list) or len(candidates) != len(raw):
                    issue("MATH_READING_RAW_CANDIDATE_COVERAGE_MISMATCH", rid)
                    continue
                for index, (row, candidate) in enumerate(zip(raw, candidates)):
                    if (not isinstance(row, (list, tuple)) or len(row) != 2
                            or not isinstance(row[0], str) or not isinstance(row[1], (int, float))
                            or isinstance(row[1], bool) or not math.isfinite(row[1])
                            or not 0 <= row[1] <= 1
                            or candidate.get("text") != row[0] or candidate.get("score") != float(row[1])
                            or candidate.get("raw_result_index") != index
                            or set(candidate) != {"candidate_id", "text", "score", "raw_result_index"}
                            or candidate.get("candidate_id") != "math-role-candidate-"+digest([rid, variant.get("variant_id"), index, row])[:24]):
                        issue("MATH_READING_RAW_TRANSCRIPTION_MISMATCH", rid)
                    candidate_ids.append(candidate.get("candidate_id"))
                    flattened.append(candidate.get("candidate_id"))
                texts.append([c.get("text") for c in candidates])
            if target.get("candidate_refs") != flattened:
                issue("MATH_READING_CANDIDATE_COVERAGE_MISMATCH", rid)
            agreement = (len(texts) == 2 and len(texts[0]) == 1 and texts[0] == texts[1]
                         and bool(texts[0][0].strip()) and all(v.get("recognition_error") is None for v in variants))
            consensus = texts[0][0] if agreement else None
            if target.get("exact_two_pass_agreement") is not agreement or target.get("consensus_text") != consensus:
                issue("MATH_READING_FALSE_CONSENSUS", rid)
            summary["two_pass_agreement_count"] += int(agreement)
            summary["missing_reading_count"] += int(not all(v.get("candidates") and any(c["text"].strip() for c in v["candidates"]) for v in variants))
            # The layout's tight role box can itself clip raised ink. Its
            # retained two-pixel context is source evidence too: inspect the
            # complete component there, retaining only ink touching this role.
            independent = [r for r in raised_ink_observations(image, wanted, crop[:2])
                           if _overlap(r["component_bbox"], pixel_box) > 0]
            for observed in independent:
                observed["role_id"] = rid
                pixel_risks.append(observed)
            risks = target.get("pixel_risks", [])
            if not isinstance(risks, list):
                issue("MATH_READING_PIXEL_RISK_MISMATCH", rid)
                continue
            for risk in risks:
                box = risk.get("component_bbox", [])
                if (risk.get("code") != "SUPERSCRIPT_PIXEL_RISK" or len(box) != 4
                        or not _inside(box, wanted) or _overlap(box, pixel_box) <= 0
                        or risk.get("status") != "UNRESOLVED"
                        or risk.get("transcription_verified") is not False):
                    issue("MATH_READING_PIXEL_RISK_MISMATCH", rid)
                    continue
                if set(risk) != {"code", "component_bbox", "threshold_votes", "body_baseline_y", "body_height",
                                 "component_pixel_sha256", "witnesses", "status", "transcription_verified"}:
                    issue("MATH_READING_PIXEL_RISK_MISMATCH", rid)
                risk_tile = image.crop([box[i]-crop[i % 2] for i in range(4)])
                if risk.get("component_pixel_sha256") != _pixels(risk_tile):
                    issue("MATH_READING_PIXEL_RISK_MISMATCH", rid)
                votes, witnesses = risk.get("threshold_votes", []), risk.get("witnesses", [])
                if (not votes or votes != sorted(set(votes)) or any(v not in (180, 190, 200, 210, 220) for v in votes)
                        or set(votes) != {w.get("threshold") for w in witnesses}):
                    issue("MATH_READING_PIXEL_RISK_MISMATCH", rid)
                for witness in witnesses:
                    wb = witness.get("component_bbox", [])
                    if len(wb) != 4 or not _inside(wb, box):
                        issue("MATH_READING_PIXEL_RISK_MISMATCH", rid)
                        continue
                    # Match a complete source component, not merely the ink
                    # count inside a conveniently truncated witness box.
                    _, _, stats, _ = cv2.connectedComponentsWithStats(
                        (np.asarray(tile.convert("L")) < witness.get("threshold", 0)).astype("uint8"), 8)
                    found = [(wanted[0]+int(x), wanted[1]+int(y), wanted[0]+int(x+w), wanted[1]+int(y+h), int(n))
                             for x,y,w,h,n in stats[1:]]
                    if not any(list(item[:4]) == wb and item[4] == witness.get("area") and item[4] >= 2 for item in found):
                        issue("MATH_READING_PIXEL_RISK_MISMATCH", rid)
            for observed in independent:
                if not any(_overlap(observed["component_bbox"], risk.get("component_bbox", [0, 0, 0, 0]))
                           >= (observed["component_bbox"][2]-observed["component_bbox"][0])
                           *(observed["component_bbox"][3]-observed["component_bbox"][1])
                           for risk in risks):
                    issue("MATH_READING_RAISED_INK_RISK_DROPPED", rid)
            slots = target.get("raised_symbol_slots")
            expected_slots = [{"slot_id": "math-raised-symbol-"+digest([rid, r["component_bbox"], r["component_pixel_sha256"]])[:24],
                "role_id": rid, "source_bbox": r["component_bbox"], "source_pixel_sha256": r["component_pixel_sha256"],
                "status": "NOT_ATTEMPTED", "candidate_refs": [], "transcription_verified": False} for r in risks]
            if slots != expected_slots:
                issue("MATH_READING_RAISED_SLOT_MISMATCH", rid)
            expected_recognition_risks = []
            if not all(v.get("candidates") and any(c["text"].strip() for c in v["candidates"]) for v in variants):
                expected_recognition_risks.append({"code": "MATH_ROLE_OCR_EMPTY_OR_FAILED", "status": "UNRESOLVED"})
            elif not agreement:
                expected_recognition_risks.append({"code": "MATH_ROLE_OCR_DISAGREEMENT", "status": "UNRESOLVED"})
            unknown = sorted({char for v in variants for c in v.get("candidates", []) for char in c["text"] if char not in _SUPPORTED})
            if unknown:
                expected_recognition_risks.append({"code": "MATH_UNSUPPORTED_SYMBOL_RISK", "symbols": unknown, "status": "UNRESOLVED"})
            if target.get("recognition_risks") != expected_recognition_risks:
                issue("MATH_READING_RECOGNITION_RISK_DROPPED", rid)
            all_reading_issues.extend({"fraction_id": fid, "role_id": rid, "role": position, **risk}
                                     for risk in risks+expected_recognition_risks)
            if target.get("complete", False) is not False or target.get("transcription_verified", False) is not False:
                issue("MATH_READING_FALSE_VERIFICATION", rid)
    if len(candidate_ids) != len(set(candidate_ids)) or any(not value for value in candidate_ids):
        issue("MATH_READING_CANDIDATE_ID_REUSED")
    if rp.get("issues") != all_reading_issues:
        issue("MATH_READING_RISK_LEDGER_MISMATCH")
    return finish()
