"""Explicit source-bound whole-row OCR observations, never a text correction.

RapidOCR's word coordinates derive from CTC time steps and perspective crops.
They are localization estimates, not exact glyph boxes or spatial-role proof.
No optional OCR package/model is imported or initialized on module import.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import importlib.util
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import time

import numpy as np
from PIL import Image

from .baseline import code_digest, digest, file_digest, valid_bbox

SCHEMA = "b-inline-ocr-observation-trial/0.1"
LOCALIZATION_KIND = "CTC_TIMESTEP_ESTIMATE"
CONFIG = {
    "padding": 2,
    "bbox_rounding": "FLOOR_MIN_CEIL_MAX_CLAMP_ORIGINAL_PAGE",
    "variants": [{"variant_id": "scale3", "scale": 3}, {"variant_id": "scale4", "scale": 4}],
    "resampling": "PIL_LANCZOS",
    "channel_order": "BGR",
    "dtype": "uint8",
    "engine_flags": {"use_det": True, "use_cls": False, "use_rec": True,
                     "return_word_box": True, "text_score": 0},
    "localization_kind": LOCALIZATION_KIND,
    "precise_glyph_localization": False,
    "spatial_role_verified": False,
    "rapidocr_version": "1.4.4",
    "candidate_policy": "PRESERVE_ALL_RAW_ROWS_AND_WORD_ARRAY_INDICES",
}


def reference(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def _id(prefix, value):
    return prefix + "-" + digest(value)[:24]


def _rgb_sha(image):
    return hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _checked_evidence(evidence):
    if (not isinstance(evidence, dict)
            or evidence.get("schema_version") not in {"b-evidence-trial/0.2", "b-evidence-trial/0.3"}
            or evidence.get("kind") != "EvidenceBundleTrial"
            or not isinstance(evidence.get("payload"), dict)
            or evidence.get("content_hash") != digest(evidence["payload"])):
        raise ValueError("unsupported or changed inline OCR source evidence")
    for field in ("artifact_id", "book_id", "scope_id"):
        if not isinstance(evidence.get(field), str) or not evidence[field].strip():
            raise ValueError("missing evidence identity: " + field)
    if type(evidence.get("revision")) is not int or evidence["revision"] < 1:
        raise ValueError("invalid evidence revision")
    pages = evidence["payload"].get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("evidence requires a nonempty declared page scope")
    seen_assets, seen_lines = set(), set()
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("invalid evidence page")
        asset = page.get("source")
        aid = page.get("asset_id")
        if (not isinstance(aid, str) or not aid or aid in seen_assets or not isinstance(asset, dict)
                or asset.get("asset_id") != aid):
            raise ValueError("missing, duplicate or inconsistent page asset")
        seen_assets.add(aid)
        for dimension in ("width", "height"):
            if type(asset.get(dimension)) is not int or asset[dimension] <= 0:
                raise ValueError("invalid source dimensions")
        if (not isinstance(asset.get("sha256"), str) or len(asset["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in asset["sha256"])):
            raise ValueError("invalid source SHA-256")
        if not isinstance(page.get("ocr_lines"), list):
            raise ValueError("missing raw OCR line scope")
        for line in page["ocr_lines"]:
            lid = line.get("line_id") if isinstance(line, dict) else None
            if not isinstance(lid, str) or not lid or lid in seen_lines:
                raise ValueError("missing or duplicate raw OCR line identity")
            seen_lines.add(lid)
            if line.get("asset_id", aid) != aid:
                raise ValueError("raw OCR line belongs to another asset")
    return pages


def plan_inline_rows(evidence, original_path, *, asset_id, line_ids):
    """Validate the supplied original and plan caller-selected complete rows.

    Other pages' descriptors/line identities are checked, but this API receives
    only one original image. It does not claim to revalidate other image files.
    The supplied row text is provenance only and never enters the OCR backend.
    """
    pages = _checked_evidence(evidence)
    if (not isinstance(line_ids, (list, tuple)) or not line_ids
            or any(not isinstance(lid, str) or not lid for lid in line_ids)
            or len(set(line_ids)) != len(line_ids)):
        raise ValueError("explicit nonempty unique raw line_ids are required")
    selected = [p for p in pages if p["asset_id"] == asset_id]
    if len(selected) != 1:
        raise ValueError("unknown inline OCR asset")
    page, original_path = selected[0], Path(original_path)
    asset = page["source"]
    if not original_path.is_file() or file_digest(original_path) != asset["sha256"]:
        raise ValueError("original source SHA-256 mismatch")
    with Image.open(original_path) as opened:
        if opened.size != (asset["width"], asset["height"]):
            raise ValueError("original source dimensions mismatch")
        image = opened.convert("RGB")
    source = {"asset_id": asset_id, "asset": copy.deepcopy(asset),
              "original_sha256": file_digest(original_path), "width": image.width,
              "height": image.height, "original_rgb_sha256": _rgb_sha(image)}
    by_id = {line["line_id"]: line for line in page["ocr_lines"]}
    plans = []
    for lid in line_ids:
        if lid not in by_id:
            raise ValueError("requested raw line is not on the selected asset: " + lid)
        line, pad = by_id[lid], CONFIG["padding"]
        box = line.get("bbox")
        if not isinstance(box, (list, tuple)) or not valid_bbox(box, image.width, image.height):
            raise ValueError("requested raw line has invalid source bbox: " + lid)
        crop_box = [max(0, math.floor(box[0])-pad), max(0, math.floor(box[1])-pad),
                    min(image.width, math.ceil(box[2])+pad), min(image.height, math.ceil(box[3])+pad)]
        crop = image.crop(crop_box)
        plans.append({"row_id": _id("inline-row", [reference(evidence), asset_id, lid]),
                      "line_id": lid, "asset_id": asset_id, "source_line": copy.deepcopy(line),
                      "bbox": copy.deepcopy(box), "crop_bbox": crop_box,
                      "crop_size": list(crop.size), "crop_rgb_sha256": _rgb_sha(crop)})
    return image, source, plans


def _dependency(distribution, module):
    spec = importlib.util.find_spec(module)
    dist = importlib.metadata.distribution(distribution)
    if spec is None or spec.origin is None:
        raise ValueError("required local dependency missing: " + module)
    record = next((f for f in dist.files or [] if str(f).replace("\\", "/").endswith(".dist-info/RECORD")), None)
    return {"distribution": distribution, "version": dist.version,
            "package_entry_sha256": file_digest(Path(spec.origin)),
            "distribution_record_sha256": file_digest(Path(dist.locate_file(record))) if record else None}


def _cpu_sessions(engine):
    result = {}
    for role, attr in (("Det", "text_det"), ("Cls", "text_cls"), ("Rec", "text_rec")):
        stage = getattr(engine, attr)
        # RapidOCR 1.4.4 names the detector/classifier OrtInferSession `infer`,
        # while the recognizer calls its OrtInferSession `session`.
        session = stage.session.session if role == "Rec" else stage.infer.session
        providers = session.get_providers()
        if providers != ["CPUExecutionProvider"]:
            raise ValueError("inline OCR requires CPU-only actual providers for " + role)
        result[role] = list(providers)
    return result


def _cpu_backend():
    """Preflight only installed models, then initialize an explicit CPU engine."""
    if importlib.metadata.version("rapidocr-onnxruntime") != CONFIG["rapidocr_version"]:
        raise ValueError("inline OCR requires installed RapidOCR 1.4.4")
    spec = importlib.util.find_spec("rapidocr_onnxruntime")
    if spec is None or spec.origin is None:
        raise ValueError("local RapidOCR package missing")
    root = Path(spec.origin).parent
    config_path = root / "config.yaml"
    if not config_path.is_file():
        raise ValueError("local RapidOCR configuration missing")
    import yaml
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    models, kwargs = [], {}
    for role in ("Det", "Cls", "Rec"):
        name = config[role]["model_path"]
        if (not isinstance(name, str) or "\\" in name or PurePosixPath(name).is_absolute()
                or PureWindowsPath(name).drive or ".." in PurePosixPath(name).parts):
            raise ValueError("model must already exist inside installed RapidOCR package")
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("installed local OCR model missing: " + str(name))
        models.append({"role": role, "name": name, "sha256": file_digest(path), "active_in_call": role != "Cls"})
        kwargs[role.lower()+"_model_path"] = str(path)
        kwargs[role.lower()+"_use_cuda"] = False
        kwargs[role.lower()+"_use_dml"] = False
    dependencies = {key: _dependency(dist, key) for key, dist in (
        ("rapidocr_onnxruntime", "rapidocr-onnxruntime"), ("onnxruntime", "onnxruntime"),
        ("numpy", "numpy"), ("PIL", "Pillow"), ("yaml", "PyYAML"))}
    cvdist = next((d for d in importlib.metadata.packages_distributions().get("cv2", [])
                   if d in ("opencv-python", "opencv-python-headless", "opencv-contrib-python", "opencv-contrib-python-headless")), None)
    if cvdist is None:
        raise ValueError("installed OpenCV distribution receipt missing")
    dependencies["cv2"] = _dependency(cvdist, "cv2")
    package_files = [{"path": p.relative_to(root).as_posix(), "sha256": code_digest(p)}
                     for p in sorted(root.rglob("*.py"))]
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR(config_path=str(config_path), **kwargs)
    providers = _cpu_sessions(engine)
    return engine, {"execution_kind": "CPU_RAPIDOCR_INLINE", "engine": "rapidocr_onnxruntime", "device": "CPU",
                    "dependencies": dependencies, "dependency_sha256": digest(dependencies),
                    "package_files": package_files, "package_code_sha256": digest(package_files),
                    "config_file": {"path": "config.yaml", "sha256": file_digest(config_path),
                                    "text_sha256": code_digest(config_path)},
                    "model_files": models, "models_sha256": digest(models),
                    "session_providers": providers, "session_providers_sha256": digest(providers)}


def _json_value(value):
    if isinstance(value, np.ndarray):
        return _json_value(value.tolist())
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise ValueError("raw OCR mappings require string keys")
        return {key: _json_value(item) for key, item in value.items()}
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ValueError("raw OCR output contains a non-JSON or nonfinite value")


def _preprocess(crop, definition, crop_box):
    scale = definition["scale"]
    rgb = crop.resize((crop.width*scale, crop.height*scale), Image.Resampling.LANCZOS)
    bgr = np.ascontiguousarray(np.asarray(rgb)[:, :, ::-1])
    meta = {**definition, "size": list(rgb.size), "rgb_sha256": _rgb_sha(rgb),
            "bgr_sha256": hashlib.sha256(bgr.tobytes()).hexdigest(), "dtype": "uint8", "channel_order": "BGR",
            "variant_to_original": [[1/scale, 0, crop_box[0]], [0, 1/scale, crop_box[1]], [0, 0, 1]]}
    return meta, bgr


def _polygon(polygon, meta):
    if (not isinstance(polygon, list) or len(polygon) != 4
            or any(not isinstance(p, list) or len(p) != 2 or not all(_number(n) for n in p) for p in polygon)):
        return None, "INVALID"
    scale = meta["scale"]
    tx, ty = meta["variant_to_original"][0][2], meta["variant_to_original"][1][2]
    projected = [[p[0]/scale+tx, p[1]/scale+ty] for p in polygon]
    area = abs(sum(polygon[i][0]*polygon[(i+1) % 4][1]-polygon[(i+1) % 4][0]*polygon[i][1] for i in range(4)))/2
    if area == 0:
        return projected, "DEGENERATE"
    if any(not 0 <= p[0] <= meta["size"][0] or not 0 <= p[1] <= meta["size"][1] for p in polygon):
        return projected, "OUTSIDE_INPUT"
    return projected, "USABLE"


def _projection(raw, row_id, meta):
    if raw is None:
        return [], [{"code": "OCR_EMPTY"}]
    if not isinstance(raw, list):
        return [], [{"code": "RAW_RESULT_INVALID"}]
    candidates, issues = [], []
    flags = {"localization_kind": LOCALIZATION_KIND, "precise_glyph_localization": False,
             "spatial_role_verified": False, "verification_status": "UNVERIFIED"}
    for index, entry in enumerate(raw):
        candidate = {"candidate_id": _id("inline-candidate", [row_id, meta["variant_id"], index]),
                     "raw_result_index": index, "raw_observation": copy.deepcopy(entry),
                     "text": None, "score": None, "polygon": None, "source_polygon": None,
                     "polygon_status": "INVALID", "word_estimates": [], "word_alignment_status": "INVALID", **flags}
        candidates.append(candidate)
        if not isinstance(entry, list) or len(entry) != 6:
            issues.append({"code": "RAW_ROW_INVALID", "raw_result_index": index})
            continue
        polygon, text, score, boxes, words, scores = entry
        source_polygon, status = _polygon(polygon, meta)
        candidate.update(text=text if isinstance(text, str) else None, score=score if _number(score) else None,
                         polygon=copy.deepcopy(polygon), source_polygon=source_polygon, polygon_status=status)
        if status != "USABLE":
            issues.append({"code": "POLYGON_"+status, "raw_result_index": index})
        if not isinstance(text, str):
            issues.append({"code": "RAW_ROW_INVALID", "raw_result_index": index})
        if not _number(score) or not 0 <= score <= 1:
            issues.append({"code": "SCORE_INVALID", "raw_result_index": index})
        if not all(isinstance(v, list) for v in (boxes, words, scores)):
            issues.append({"code": "WORD_ARRAYS_INVALID", "raw_result_index": index})
            continue
        aligned = len(boxes) == len(words) == len(scores)
        typed = all(isinstance(w, str) for w in words)
        sequence_agrees = typed and isinstance(text, str) and "".join(words) == text
        candidate["word_alignment_status"] = "ALIGNED" if aligned and sequence_agrees else "LENGTH_MISMATCH" if typed else "INVALID"
        if not aligned:
            issues.append({"code": "WORD_ARRAY_LENGTH_MISMATCH", "raw_result_index": index})
        if not sequence_agrees:
            issues.append({"code": "WORD_SEQUENCE_MISMATCH", "raw_result_index": index})
        for j in range(max(len(boxes), len(words), len(scores))):
            box = boxes[j] if j < len(boxes) else None
            source_box, word_status = _polygon(box, meta)
            word_score = scores[j] if j < len(scores) else None
            candidate["word_estimates"].append({"raw_word_index": j, "polygon": copy.deepcopy(box),
                "source_polygon": source_box, "polygon_status": word_status,
                "text": copy.deepcopy(words[j]) if j < len(words) else None,
                "score": copy.deepcopy(word_score), **flags})
            if word_status != "USABLE":
                issues.append({"code": "POLYGON_"+word_status, "raw_result_index": index, "raw_word_index": j})
            if not _number(word_score) or not 0 <= word_score <= 1:
                issues.append({"code": "SCORE_INVALID", "raw_result_index": index, "raw_word_index": j})
    if not raw:
        issues.append({"code": "OCR_EMPTY"})
    return candidates, issues


def collect_inline_observations(evidence, original_path, *, asset_id, line_ids, recognizer=None):
    """Run two declared whole-row variants and retain all raw engine results.

    Supplying any recognizer creates explicitly SYNTHETIC_TEST evidence. The
    default requires existing local models; it never downloads or uses a site.
    This function does not select/correct text or mutate the input evidence.
    """
    image, source, plans = plan_inline_rows(evidence, original_path, asset_id=asset_id, line_ids=line_ids)
    if recognizer is None:
        recognizer, backend = _cpu_backend()
    else:
        if not callable(recognizer):
            raise ValueError("injected recognizer must be callable")
        backend = {"execution_kind": "SYNTHETIC_TEST", "engine": "injected_test_backend", "device": "SYNTHETIC_TEST",
                   "dependencies": {}, "dependency_sha256": digest({}), "package_files": [], "package_code_sha256": digest([]),
                   "config_file": None, "model_files": [], "models_sha256": digest([]),
                   "session_providers": {}, "session_providers_sha256": digest({})}
    producer = {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
                "dependency_code_sha256": {"baseline": code_digest(Path(__file__).with_name("baseline.py"))},
                "configuration": copy.deepcopy(CONFIG), "configuration_sha256": digest(CONFIG), **backend}
    rows = []
    for plan in plans:
        row = copy.deepcopy(plan)
        crop = image.crop(plan["crop_bbox"])
        row["variants"] = []
        for definition in CONFIG["variants"]:
            variant, bgr = _preprocess(crop, definition, plan["crop_bbox"])
            raw_call, raw, elapsed, error, candidates, issues = None, None, None, None, [], []
            start = time.perf_counter()
            try:
                returned = recognizer(bgr, **copy.deepcopy(CONFIG["engine_flags"]))
                raw_call = _json_value(returned)
                if not isinstance(raw_call, list) or len(raw_call) != 2:
                    raise ValueError("OCR call must return [raw_result, elapsed]")
                raw, elapsed = raw_call
                if elapsed is not None and (not isinstance(elapsed, list) or any(not _number(t) or t < 0 for t in elapsed)):
                    raise ValueError("invalid raw engine elapsed array")
                candidates, issues = _projection(raw, plan["row_id"], variant)
            except Exception as exc:
                error = {"type": type(exc).__name__, "message": str(exc)}
            variant.update(raw_call_result=raw_call, raw_ocr_result=raw, engine_elapsed_seconds=elapsed,
                           wall_elapsed_seconds=time.perf_counter()-start, recognition_error=error,
                           candidates=candidates, issues=issues)
            row["variants"].append(variant)
        rows.append(row)
    payload = {"evidence_ref": reference(evidence), "source": source, "requested_line_ids": list(line_ids), "rows": rows,
               "decision": "HOLD", "verification_status": "UNVERIFIED", "complete": False,
               "transcription_verified": False, "business_acceptance": False, "platform_actions": [],
               "localization_kind": LOCALIZATION_KIND, "precise_glyph_localization": False,
               "spatial_role_verified": False, "graph_modified": False,
               "limitations": ["Character/word boxes are CTC timestep estimates, not precise glyph localization.",
                               "Raw engine order, low scores and degenerate estimates are retained; no text is selected.",
                               "Resampling can lose details. Two variants and model scores do not verify transcription.",
                               "Only the supplied asset image is revalidated; other pages remain declared source descriptors."]}
    inputs = [reference(evidence)]
    return {"schema_version": SCHEMA, "kind": "InlineOCRObservationTrial",
            "artifact_id": _id("inline-ocr-observation", {"source": reference(evidence), "inputs": inputs,
                                                        "producer": producer, "payload": payload}),
            "revision": 1, "book_id": evidence["book_id"], "scope_id": evidence["scope_id"],
            "input_refs": inputs, "producer": producer, "content_hash": digest(payload), "payload": payload}
