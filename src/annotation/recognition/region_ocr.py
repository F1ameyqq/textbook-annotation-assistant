"""Source-bound observations of geometric body slots and whole-row fallbacks.

The collector reads pixels, not a graph, visual draft or expected text.  Its
recognition-only backend returns line hypotheses, not glyph coordinates.  Halo
crops may include neighboring fractions; their original slot and risk records
remain attached, and no text is removed to fit an expected formula.

Validation rechecks a supplied fixed plan, pixels and raw-result projection.
It does not run the planner or OCR, authenticate execution, select hypotheses,
or establish mathematical/transcription correctness.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import math
from pathlib import Path, PurePosixPath
import re
import time

import numpy as np
from PIL import Image, ImageEnhance

from .baseline import code_digest, digest, file_digest

SCHEMA = "b-region-ocr-observation-trial/0.1"
CHECK_SCHEMA = "b-region-ocr-check-trial/0.1"
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_HEADER = {"schema_version", "kind", "artifact_id", "revision", "book_id", "scope_id",
           "input_refs", "producer", "payload", "content_hash"}


def _configuration():
    return {"variants": [{"variant_id": "CORE_GAP_SCALE6", "scale": 6, "contrast": 1.0,
                          "crop_policy": "SOURCE_BODY_OR_FULL_ROW"},
                         {"variant_id": "CONTEXT_SCALE8_CONTRAST15", "scale": 8, "contrast": 1.5,
                          "crop_policy": "RECOGNITION_CONTEXT_OR_FULL_ROW"}],
            "resize": "PIL_LANCZOS", "color": "BGR", "dtype": "uint8",
            "engine_flags": {"use_det": False, "use_cls": False, "use_rec": True},
            "rapidocr_version": "1.4.4", "unit_order": "BODY_SLOTS_THEN_ROW_FALLBACKS",
            "elapsed_policy": "SCALAR_OR_RECOGNITION_ONLY_SINGLE_ELEMENT_LIST/0.1",
            "maximum_transformed_pixels": 16_777_216,
            "raw_policy": "PRESERVE_ALL_ROWS_AND_NONFINITE_TAGS/0.1",
            "localization_kind": "WHOLE_CROP_RECOGNITION_ONLY", "precise_glyph_localization": False,
            "spatial_role_verified": False}


CONFIG = _configuration()


def reference(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def _flags():
    return {"decision": "HOLD", "verification_status": "UNVERIFIED", "complete": False,
            "transcription_verified": False, "business_acceptance": False,
            "expected_text_consumed": False, "graph_modified": False,
            "platform_actions": [], "selected_candidate_refs": []}


def _limitations():
    return ["Recognition-only text is not a glyph position, spatial-role proof or verified transcription.",
            "Halo pixels may include neighboring fractions; all raw output and original slot risks are retained.",
            "Fixed-plan, pixel and raw-projection validation is not an execution signature or content acceptance.",
            "The caller must separately verify the complete source JPG against the declared crop."]


def _same(left, right):
    return digest(left) == digest(right)


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _rgb(image):
    return _sha(np.ascontiguousarray(np.asarray(image.convert("RGB"), dtype=np.uint8)).tobytes())


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _elapsed(value):
    # RapidOCR1.4.4 recognition-only returns [rec_elapsed].  Keep that exact
    # raw container while exposing its single measured duration separately.
    actual = value[0] if isinstance(value, list) and len(value) == 1 else value
    return float(actual) if _number(actual) and actual >= 0 else None


def _box(value, outer):
    return (isinstance(value, list) and len(value) == 4 and all(type(n) is int for n in value)
            and outer[0] <= value[0] < value[2] <= outer[2]
            and outer[1] <= value[1] < value[3] <= outer[3])


def _artifact(schema, kind, prefix, plan, inputs, producer, payload):
    body = {"schema_version": schema, "kind": kind, "revision": 1,
            "book_id": plan.get("book_id"), "scope_id": plan.get("scope_id"),
            "input_refs": inputs, "producer": producer, "payload": payload}
    return {**body, "artifact_id": prefix+"-"+digest(body)[:24], "content_hash": digest(payload)}


def _plan_source(plan, crop_path):
    """Check the fixed external plan and every actual crop, without replanning."""
    if (not isinstance(plan, dict) or set(plan) != _HEADER or plan.get("schema_version") != "b-region-runs-trial/0.1"
            or plan.get("kind") != "RegionRunsTrial" or type(plan.get("revision")) is not int or plan["revision"] != 1
            or not all(_text(plan.get(k)) for k in ("artifact_id", "book_id", "scope_id"))
            or not isinstance(plan.get("producer"), dict) or not isinstance(plan.get("payload"), dict)
            or plan.get("content_hash") != digest(plan["payload"])
            or plan["artifact_id"] != "region-runs-"+digest([plan["input_refs"], plan["producer"], plan["payload"]])[:24]):
        raise ValueError("region run plan identity or envelope changed")
    p = plan["payload"]
    required = {"layout_ref", "layout_archive", "source", "rows", "fraction_slots", "body_slots",
                "components_by_threshold", "coverage", "risks", "decision", "complete", "transcription_verified",
                "business_acceptance", "expected_text_consumed", "graph_modified", "platform_actions"}
    if set(p) != required:
        raise ValueError("region run plan has unknown or missing fields")
    if not _same({k: p.get(k) for k in ("decision", "complete", "transcription_verified", "business_acceptance",
                  "expected_text_consumed", "graph_modified", "platform_actions")},
                 {k: _flags()[k] for k in ("decision", "complete", "transcription_verified", "business_acceptance",
                  "expected_text_consumed", "graph_modified", "platform_actions")}):
        raise ValueError("region run plan cannot claim content acceptance")
    layout = p["layout_archive"]
    if (not isinstance(layout, dict) or layout.get("schema_version") != "b-math-layout-trial/0.1"
            or layout.get("kind") != "MathLayoutTrial" or layout.get("content_hash") != digest(layout.get("payload"))
            or not _same(p["layout_ref"], reference(layout)) or not _same(plan["input_refs"], [reference(layout)])
            or any(plan[k] != layout[k] for k in ("book_id", "scope_id"))):
        raise ValueError("region plan is not bound to its complete original layout")
    source = p["source"]
    source_keys = {"asset_id", "source_sha256", "source_size", "crop_bbox", "crop_sha256", "crop_rgb_sha256"}
    if (not isinstance(source, dict) or set(source) != source_keys
            or not _text(source.get("asset_id")) or not _HASH.fullmatch(source.get("source_sha256", ""))
            or not isinstance(source.get("source_size"), list) or len(source["source_size"]) != 2
            or any(type(n) is not int or n <= 0 for n in source["source_size"])
            or not _box(source.get("crop_bbox"), [0, 0, *source["source_size"]])
            or not _same({k: source[k] for k in source_keys-{"crop_rgb_sha256"}},
                         {k: layout["payload"].get(k) for k in source_keys-{"crop_rgb_sha256"}})):
        raise ValueError("region plan source differs from its archived layout")
    path = Path(crop_path)
    if not path.is_file() or file_digest(path) != source["crop_sha256"]:
        raise ValueError("region source crop bytes changed or are missing")
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    bounds = source["crop_bbox"]
    if image.size != (bounds[2]-bounds[0], bounds[3]-bounds[1]) or _rgb(image) != source["crop_rgb_sha256"]:
        raise ValueError("region crop dimensions or pixels changed")
    if not isinstance(p["rows"], list) or not p["rows"] or not isinstance(p["body_slots"], list) or not isinstance(p["fraction_slots"], list):
        raise ValueError("region plan must retain its complete declared row and slot scope")
    fraction_ids = {f["fraction_id"] for f in layout["payload"]["fraction_candidates"]}
    if (len(fraction_ids) != len(layout["payload"]["fraction_candidates"])
            or [f["fraction_id"] for f in p["fraction_slots"]] != [f["fraction_id"] for f in layout["payload"]["fraction_candidates"]]):
        raise ValueError("region plan fraction scope or order changed")
    row_ids, primary_ids, all_ids, unit_slots = set(), [], set(), []
    previous_y = bounds[1]
    for row in p["rows"]:
        if (not isinstance(row, dict) or set(row) != {"row_id", "baseline_y", "source_bbox", "slot_ids", "full_row_fallback"}
                or not _text(row["row_id"]) or row["row_id"] in row_ids or not _number(row["baseline_y"])
                or not _box(row["source_bbox"], bounds) or row["source_bbox"][:2] != [bounds[0], previous_y]
                or row["source_bbox"][2] != bounds[2] or not row["source_bbox"][1] <= row["baseline_y"] < row["source_bbox"][3]
                or not isinstance(row["slot_ids"], list) or not row["slot_ids"] or any(not _text(s) for s in row["slot_ids"])
                or len(set(row["slot_ids"])) != len(row["slot_ids"])):
            raise ValueError("region row geometry, identity or primary slot scope is invalid")
        row_ids.add(row["row_id"]); primary_ids.extend(row["slot_ids"]); previous_y = row["source_bbox"][3]
    if previous_y != bounds[3] or len(primary_ids) != len(set(primary_ids)):
        raise ValueError("region rows leave a gap or duplicate primary ownership")
    primaries = p["body_slots"]+p["fraction_slots"]
    if (any(not isinstance(s, dict) or not _text(s.get("slot_id")) or s.get("row_id") not in row_ids for s in primaries)
            or len({s["slot_id"] for s in primaries}) != len(primaries)
            or set(primary_ids) != {s["slot_id"] for s in primaries}):
        raise ValueError("region row references do not retain all body and fraction slots")
    rows_by_id = {row["row_id"]: row for row in p["rows"]}
    for slot in primaries:
        row = rows_by_id[slot["row_id"]]
        if slot["slot_id"] not in row["slot_ids"] or not _box(slot.get("source_bbox"), row["source_bbox"]):
            raise ValueError("region primary slot belongs to another row")
    body_keys = {"slot_id", "kind", "row_id", "source_bbox", "recognition_bbox", "crop_size", "crop_rgb_sha256",
                 "adjacent_fraction_ids", "component_ids", "risks"}
    fallback_keys = {"slot_id", "kind", "row_id", "source_bbox", "recognition_bbox", "crop_size", "crop_rgb_sha256"}
    for slot in p["body_slots"]:
        if (set(slot) != body_keys or slot["kind"] != "BODY_OR_WRAPPER"
                or not isinstance(slot["adjacent_fraction_ids"], list) or any(f not in fraction_ids for f in slot["adjacent_fraction_ids"])
                or not isinstance(slot["component_ids"], list) or not isinstance(slot["risks"], list)):
            raise ValueError("body slot metadata or adjacency changed")
        unit_slots.append(slot)
    for row in p["rows"]:
        slot = row["full_row_fallback"]
        if (not isinstance(slot, dict) or set(slot) != fallback_keys or slot.get("kind") != "FULL_ROW_FALLBACK"
                or slot.get("row_id") != row["row_id"] or not _same(slot.get("source_bbox"), row["source_bbox"])
                or not _same(slot.get("recognition_bbox"), row["source_bbox"])):
            raise ValueError("whole-row fallback changed or was truncated")
        unit_slots.append(slot)
    expected = []
    for slot in unit_slots:
        if slot["slot_id"] in all_ids or slot["slot_id"] in {f["slot_id"] for f in p["fraction_slots"]}:
            raise ValueError("duplicate or fraction-mislabelled OCR unit")
        all_ids.add(slot["slot_id"])
        row = rows_by_id[slot["row_id"]]
        box = slot["recognition_bbox"]
        if not _box(box, row["source_bbox"]) or not _box(slot["source_bbox"], box):
            raise ValueError("OCR crop clips its body source or crosses its row")
        local = [box[i]-bounds[i % 2] for i in range(4)]
        crop = image.crop(local)
        if not _same(slot["crop_size"], list(crop.size)) or slot["crop_rgb_sha256"] != _rgb(crop):
            raise ValueError("OCR unit crop dimensions or actual source pixels changed")
        if any(crop.width*crop.height*d["scale"]**2 > _configuration()["maximum_transformed_pixels"] for d in _configuration()["variants"]):
            raise ValueError("declared OCR transformation exceeds the fixed pixel allocation bound")
        unit_id = "region-ocr-unit-"+digest([reference(plan), slot["slot_id"], box])[:24]
        expected.append(({**copy.deepcopy(slot), "unit_id": unit_id}, crop))
    if file_digest(path) != source["crop_sha256"]:
        raise ValueError("region source changed while its pixels were read")
    return image, copy.deepcopy(source), expected


def _json_value(value):
    if isinstance(value, np.ndarray):
        return _json_value(value.tolist())
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise ValueError("backend raw mappings require string keys")
        return {k: _json_value(v) for k, v in value.items()}
    if type(value) is float and not math.isfinite(value):
        return {"__nonfinite_float__": "nan" if math.isnan(value) else "inf" if value > 0 else "-inf"}
    if value is None or type(value) in (str, bool, int, float):
        return value
    raise ValueError("backend returned an unsupported non-JSON value")


def _variant_source(unit, context_crop, definition):
    """Use real core pixels first; context is a separate retained observation."""
    box = unit["source_bbox"] if definition["crop_policy"] == "SOURCE_BODY_OR_FULL_ROW" else unit["recognition_bbox"]
    context = unit["recognition_bbox"]
    local = [box[i]-context[i % 2] for i in range(4)]
    return list(box), context_crop.crop(local)


def _preprocess(crop, definition, box):
    scale = definition["scale"]
    transformed = crop.resize((crop.width*scale, crop.height*scale), Image.Resampling.LANCZOS)
    transformed = ImageEnhance.Contrast(transformed).enhance(definition["contrast"])
    rgb = np.ascontiguousarray(np.asarray(transformed, dtype=np.uint8))
    bgr = np.ascontiguousarray(rgb[:, :, ::-1])
    return {**definition, "source_bbox": list(box), "crop_size": list(crop.size), "crop_rgb_sha256": _rgb(crop),
            "resize": "PIL_LANCZOS", "color": "BGR", "dtype": "uint8",
            "transformed_size": list(transformed.size), "transformed_rgb_sha256": _sha(rgb.tobytes()),
            "transformed_bgr_sha256": _sha(bgr.tobytes()),
            "transformed_to_source": [[1/scale, 0, box[0]], [0, 1/scale, box[1]], [0, 0, 1]]}, bgr


def _projection(unit_id, variant_id, raw):
    candidates, issues = [], []
    if raw is None or raw == []:
        return candidates, [{"code": "OCR_EMPTY"}]
    if not isinstance(raw, list):
        return candidates, [{"code": "RAW_OCR_ROWS_INVALID"}]
    for index, row in enumerate(raw):
        valid = isinstance(row, list) and len(row) == 2
        text = row[0] if isinstance(row, list) and row and isinstance(row[0], str) else None
        score = row[1] if valid and _number(row[1]) and 0 <= row[1] <= 1 else None
        if not valid or text is None:
            issues.append({"code": "RAW_OCR_ROW_INVALID", "raw_result_index": index})
        if score is None:
            issues.append({"code": "RAW_OCR_SCORE_INVALID", "raw_result_index": index})
        if text == "":
            issues.append({"code": "OCR_EMPTY", "raw_result_index": index})
        candidates.append({"candidate_id": "region-ocr-candidate-"+digest([unit_id, variant_id, index, row])[:24],
                           "raw_result_index": index, "raw_observation": copy.deepcopy(row),
                           "text": text, "score": score, "usable": valid and bool(text) and score is not None,
                           "verification_status": "UNVERIFIED"})
    return candidates, issues


def _synthetic_backend():
    return {"execution_kind": "SYNTHETIC_TEST", "engine": "injected_test_backend", "device": "SYNTHETIC_TEST",
            "dependencies": {}, "dependency_sha256": digest({}), "model_files": [], "models_sha256": digest([]),
            "session_providers": {}, "session_providers_sha256": digest({})}


def _actual_backend():
    if importlib.metadata.version("rapidocr-onnxruntime") != "1.4.4":
        raise ValueError("region OCR is locked to installed RapidOCR1.4.4")
    from .math_reading import _cpu_backend
    engine, receipt = _cpu_backend()
    providers = {}
    for role, attr in (("Det", "text_det"), ("Cls", "text_cls"), ("Rec", "text_rec")):
        stage = getattr(engine, attr)
        session = stage.session.session if role == "Rec" else stage.infer.session
        actual = session.get_providers()
        if actual != ["CPUExecutionProvider"]:
            raise ValueError("region OCR requires actual CPU-only sessions")
        providers[role] = list(actual)
    return engine, {**receipt, "session_providers": providers, "session_providers_sha256": digest(providers)}


def _counts(units, body_count, fallback_count):
    variants = [v for unit in units for v in unit["variants"]]
    return {"body_slots": body_count, "full_row_fallbacks": fallback_count, "units": len(units),
            "variants": len(variants), "failed_variants": sum(v["recognition_error"] is not None for v in variants),
            "empty_variants": sum(not v["candidates"] for v in variants),
            "raw_rows": sum(len(v["raw_ocr_result"]) if isinstance(v["raw_ocr_result"], list) else 0 for v in variants),
            "candidates": sum(len(v["candidates"]) for v in variants)}


def collect_region_observations(plan, crop_path, *, recognizer=None):
    """Explicitly collect every body and fallback crop; no implicit model download.

    The optional recognizer is injected test data regardless of its attributes.
    A failed or malformed call retains every JSON-representable returned value.
    No candidate is selected and no old source fragment is modified.
    """
    _, source, planned = _plan_source(plan, crop_path)
    backend, receipt = _actual_backend() if recognizer is None else (recognizer, _synthetic_backend())
    producer = {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
                "backend_adapter_code_sha256": code_digest(Path(__file__).with_name("math_reading.py")),
                "configuration": _configuration(), "configuration_sha256": digest(_configuration()), **receipt}
    units, findings = [], []
    for basic, crop in planned:
        unit = {**basic, "variants": [], "verification_status": "UNVERIFIED"}
        for definition in _configuration()["variants"]:
            actual_box, actual_crop = _variant_source(unit, crop, definition)
            variant, bgr = _preprocess(actual_crop, definition, actual_box)
            started = time.perf_counter()
            raw_call, raw, original_elapsed, elapsed, error = None, None, None, None, None
            try:
                raw_call = _json_value(backend(bgr, **_configuration()["engine_flags"]))
                if not isinstance(raw_call, list) or len(raw_call) != 2:
                    raise ValueError("recognizer must return the complete (raw_rows, elapsed_seconds) pair")
                raw, original_elapsed = raw_call
                elapsed = _elapsed(original_elapsed)
                if elapsed is None:
                    raise ValueError("recognizer elapsed seconds require one finite nonnegative duration")
            except Exception as exc:
                if isinstance(raw_call, list):
                    raw = raw_call[0] if raw_call else None
                    original_elapsed = raw_call[1] if len(raw_call) > 1 else None
                error = {"type": type(exc).__name__, "message": str(exc),
                         "status": "BACKEND_FAILED" if raw_call is None else "INVALID_BACKEND_RESULT"}
            candidates, issues = _projection(unit["unit_id"], definition["variant_id"], raw)
            if error:
                for candidate in candidates:
                    candidate["usable"] = False
                issues.append({"code": "OCR_BACKEND_FAILURE" if error["status"] == "BACKEND_FAILED" else "OCR_BACKEND_RESULT_INVALID"})
            variant.update(raw_call_result=raw_call, raw_ocr_result=copy.deepcopy(raw),
                           raw_backend_elapsed_seconds=copy.deepcopy(original_elapsed), engine_elapsed_seconds=elapsed,
                           wall_elapsed_seconds=time.perf_counter()-started, recognition_error=error,
                           candidates=candidates, issues=issues, verification_status="UNVERIFIED")
            unit["variants"].append(variant)
            findings.extend({"unit_id": unit["unit_id"], "slot_id": unit["slot_id"], "variant_id": definition["variant_id"], **copy.deepcopy(issue)} for issue in issues)
        units.append(unit)
    source_error = None
    try:
        if file_digest(Path(crop_path)) != source["crop_sha256"]:
            raise ValueError("region crop bytes changed during collection")
    except (ValueError, OSError) as exc:
        source_error = {"type": type(exc).__name__, "message": str(exc)}
        findings.append({"code": "SOURCE_CHANGED_DURING_COLLECTION"})
    payload = {"plan_ref": reference(plan), "plan_archive": copy.deepcopy(plan), "source": source, "units": units,
               "counts": _counts(units, len(plan["payload"]["body_slots"]), len(plan["payload"]["rows"])),
               "issues": findings, "source_unchanged": source_error is None, "source_revalidation_error": source_error,
               "localization_kind": "WHOLE_CROP_RECOGNITION_ONLY", "precise_glyph_localization": False,
               "spatial_role_verified": False,
               "limitations": _limitations(), **_flags()}
    return _artifact(SCHEMA, "RegionOCRObservationTrial", "region-ocr-observation", plan, [reference(plan)], producer, payload)


def _check_backend(producer):
    basic = {"module", "version", "code_sha256", "backend_adapter_code_sha256", "configuration", "configuration_sha256"}
    backend_keys = set(_synthetic_backend())
    if (not isinstance(producer, dict) or set(producer) != basic|backend_keys
            or producer.get("module") != __name__ or producer.get("version") != "0.1.0"
            or producer.get("code_sha256") != code_digest(Path(__file__))
            or producer.get("backend_adapter_code_sha256") != code_digest(Path(__file__).with_name("math_reading.py"))
            or not _same(producer.get("configuration"), _configuration())
            or producer.get("configuration_sha256") != digest(_configuration())):
        raise ValueError("region OCR implementation, configuration or producer fields changed")
    receipt = {k: producer[k] for k in backend_keys}
    if receipt["execution_kind"] == "SYNTHETIC_TEST":
        if not _same(receipt, _synthetic_backend()):
            raise ValueError("injected observations cannot claim CPU or reviewed provenance")
        return
    deps, models, providers = receipt["dependencies"], receipt["model_files"], receipt["session_providers"]
    if (receipt["execution_kind"] != "CPU_RAPIDOCR" or receipt["engine"] != "rapidocr_onnxruntime" or receipt["device"] != "CPU"
            or not isinstance(deps, dict) or not {"rapidocr_onnxruntime", "onnxruntime", "numpy", "PIL", "cv2"}.issubset(deps)
            or deps["rapidocr_onnxruntime"].get("version") != "1.4.4"
            or receipt["dependency_sha256"] != digest(deps)
            or not isinstance(models, list) or not models or receipt["models_sha256"] != digest(models)
            or not any(m.get("active_in_call") is True for m in models)
            or not _same(providers, {k: ["CPUExecutionProvider"] for k in ("Det", "Cls", "Rec")})
            or receipt["session_providers_sha256"] != digest(providers)):
        raise ValueError("CPU observations lack their complete dependency, model or actual provider receipts")
    for dependency in deps.values():
        if (not isinstance(dependency, dict) or not _text(dependency.get("version"))
                or not _HASH.fullmatch(dependency.get("package_entry_sha256", ""))
                or dependency.get("distribution_record_sha256") is not None and not _HASH.fullmatch(dependency["distribution_record_sha256"])):
            raise ValueError("CPU dependency identity is invalid")
    names = set()
    for model in models:
        name = model.get("name")
        if (set(model) != {"name", "sha256", "active_in_call"} or not _text(name) or name in names
                or "\\" in name or PurePosixPath(name).is_absolute() or ":" in name or ".." in PurePosixPath(name).parts
                or not _HASH.fullmatch(model.get("sha256", "")) or type(model.get("active_in_call")) is not bool
                or model["active_in_call"] != ("rec_infer" in name)):
            raise ValueError("CPU model identity, role or path is invalid")
        names.add(name)


def validate_region_observations(plan, observations, crop_path):
    """Return integrity findings for cached observations, never calling OCR.

    Correctly retained backend failures are observation risks, not an assertion
    that collection succeeded.  ``accepted`` only concerns the supplied fixed
    plan, actual source and faithful raw projection.  A coordinated rewrite of
    raw observations and their self-hashes cannot authenticate original model
    execution; no such signature or transcription correctness is claimed.
    """
    problems, summary = [], {}
    try:
        _, source, planned = _plan_source(plan, crop_path)
        if (not isinstance(observations, dict) or set(observations) != _HEADER or observations.get("schema_version") != SCHEMA
                or observations.get("kind") != "RegionOCRObservationTrial" or observations.get("revision") != 1 or type(observations["revision"]) is not int
                or any(observations.get(k) != plan[k] for k in ("book_id", "scope_id"))
                or not _same(observations.get("input_refs"), [reference(plan)])
                or observations.get("content_hash") != digest(observations.get("payload"))):
            raise ValueError("region OCR observation envelope or version binding changed")
        p = observations["payload"]
        expected_keys = {"plan_ref", "plan_archive", "source", "units", "counts", "issues", "source_unchanged", "source_revalidation_error",
                         "localization_kind", "precise_glyph_localization", "spatial_role_verified", "limitations"}|set(_flags())
        if (not isinstance(p, dict) or set(p) != expected_keys or not _same(p.get("plan_ref"), reference(plan))
                or not _same(p.get("plan_archive"), plan) or not _same(p.get("source"), source)
                or not _same({k: p.get(k) for k in _flags()}, _flags())
                or p.get("source_unchanged") is not True or p.get("source_revalidation_error") is not None
                or p.get("localization_kind") != "WHOLE_CROP_RECOGNITION_ONLY"
                or p.get("precise_glyph_localization") is not False or p.get("spatial_role_verified") is not False
                or not _same(p.get("limitations"), _limitations())):
            raise ValueError("region OCR plan/source archive, complete scope or unverified flags changed")
        _check_backend(observations["producer"])
        expected_id = _artifact(SCHEMA, "RegionOCRObservationTrial", "region-ocr-observation", plan, [reference(plan)], observations["producer"], p)["artifact_id"]
        if observations["artifact_id"] != expected_id:
            raise ValueError("region OCR deterministic identity changed")
        if not isinstance(p["units"], list) or len(p["units"]) != len(planned):
            raise ValueError("region OCR dropped, duplicated or added a declared unit")
        expected_findings = []
        variant_extra = {"raw_call_result", "raw_ocr_result", "raw_backend_elapsed_seconds", "engine_elapsed_seconds", "wall_elapsed_seconds",
                         "recognition_error", "candidates", "issues", "verification_status"}
        for unit, (basic, crop) in zip(p["units"], planned):
            if (not isinstance(unit, dict) or set(unit) != set(basic)|{"variants", "verification_status"}
                    or not _same({k: unit.get(k) for k in basic}, basic) or unit.get("verification_status") != "UNVERIFIED"
                    or not isinstance(unit.get("variants"), list) or len(unit["variants"]) != len(_configuration()["variants"])):
                raise ValueError("region OCR unit source, order or variant coverage changed")
            for variant, definition in zip(unit["variants"], _configuration()["variants"]):
                actual_box, actual_crop = _variant_source(basic, crop, definition)
                metadata, _ = _preprocess(actual_crop, definition, actual_box)
                if (not isinstance(variant, dict) or set(variant) != set(metadata)|variant_extra
                        or not _same({k: variant.get(k) for k in metadata}, metadata)
                        or variant.get("verification_status") != "UNVERIFIED"
                        or not _number(variant.get("wall_elapsed_seconds")) or variant["wall_elapsed_seconds"] < 0):
                    raise ValueError("region OCR actual preprocessing pixels, transform or timing changed")
                call, error = variant["raw_call_result"], variant["recognition_error"]
                if call is None:
                    if (not isinstance(error, dict) or error.get("status") != "BACKEND_FAILED"
                            or variant["raw_ocr_result"] is not None or variant["raw_backend_elapsed_seconds"] is not None
                            or variant["engine_elapsed_seconds"] is not None):
                        raise ValueError("failed backend observation invented returned content")
                    raw, original_elapsed = None, None
                else:
                    raw = call[0] if isinstance(call, list) and call else None
                    original_elapsed = call[1] if isinstance(call, list) and len(call) > 1 else None
                    if not _same(variant["raw_ocr_result"], raw) or not _same(variant["raw_backend_elapsed_seconds"], original_elapsed):
                        raise ValueError("region OCR raw return pair was not preserved")
                    valid_call = isinstance(call, list) and len(call) == 2 and _elapsed(original_elapsed) is not None
                    if valid_call:
                        if error is not None or not _same(variant["engine_elapsed_seconds"], _elapsed(original_elapsed)):
                            raise ValueError("region OCR elapsed or false failure differs from raw backend return")
                    elif (not isinstance(error, dict) or error.get("status") != "INVALID_BACKEND_RESULT"
                          or variant["engine_elapsed_seconds"] is not None):
                        raise ValueError("invalid backend return was promoted to a successful observation")
                if error is not None and (set(error) != {"type", "message", "status"} or not _text(error.get("type")) or not isinstance(error.get("message"), str)):
                    raise ValueError("region OCR backend failure receipt is incomplete")
                expected_candidates, expected_issues = _projection(basic["unit_id"], definition["variant_id"], raw)
                if error:
                    for candidate in expected_candidates:
                        candidate["usable"] = False
                    expected_issues.append({"code": "OCR_BACKEND_FAILURE" if error["status"] == "BACKEND_FAILED" else "OCR_BACKEND_RESULT_INVALID"})
                if not _same(variant["candidates"], expected_candidates) or not _same(variant["issues"], expected_issues):
                    raise ValueError("region OCR candidates or observation risks differ from actual raw rows")
                expected_findings.extend({"unit_id": basic["unit_id"], "slot_id": basic["slot_id"], "variant_id": definition["variant_id"], **copy.deepcopy(issue)} for issue in expected_issues)
        counts = _counts(p["units"], len(plan["payload"]["body_slots"]), len(plan["payload"]["rows"]))
        if not _same(p["counts"], counts) or not _same(p["issues"], expected_findings):
            raise ValueError("region OCR summary or complete observation risk list changed")
        summary = {**counts, "execution_kind": observations["producer"]["execution_kind"],
                   "verification_scope": "FIXED_PLAN_SOURCE_PREPROCESSING_AND_RAW_PROJECTION_ONLY"}
        if file_digest(Path(crop_path)) != source["crop_sha256"]:
            raise ValueError("source crop changed during cached observation validation")
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OSError, OverflowError, RecursionError) as exc:
        problems.append({"code": "REGION_OCR_INTEGRITY_INVALID", "severity": "ERROR", "detail": type(exc).__name__+": "+str(exc)})
    payload = {"accepted": not problems, "issues": problems, "summary": summary,
               "limitations": ["This is not an OCR execution signature, transcription correctness test or semantic-completeness claim."], **_flags()}
    producer = {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)), "operation": "VALIDATE_WITHOUT_OCR"}
    inputs = [reference(v) for v in (plan, observations) if isinstance(v, dict) and all(k in v for k in ("artifact_id", "revision", "content_hash"))]
    return _artifact(CHECK_SCHEMA, "RegionOCRCheckTrial", "region-ocr-check", plan if isinstance(plan, dict) else {}, inputs, producer, payload)
