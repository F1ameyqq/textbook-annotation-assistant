"""Replayable, source-bound mathematical role OCR with unresolved pixel risks.

Every numerator and denominator is read, including roles that already have OCR.
Two fixed preprocessings are observations, never formula verification.  Injected
recognizers receive BGR pixels and the RapidOCR keyword flags and must return
``(raw_recognition_result, engine_elapsed_seconds)``; their receipts are always
SYNTHETIC_TEST, regardless of callable name or attributes.  No expected formula,
source-review transcription, selected answer, or graph is accepted as input.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import math
from pathlib import Path
import re
import time

import cv2
import numpy as np
from PIL import Image, ImageEnhance

from .baseline import code_digest, digest, file_digest, valid_bbox
from .recovery_apply import reference

EVIDENCE_SCHEMA = "b-math-role-evidence-trial/0.1"
READING_SCHEMA = "b-math-reading-trial/0.1"
CONFIG = {
    "role_padding_pixels": 2,
    "variants": [{"variant_id": "scale6", "scale": 6, "contrast": 1.0},
                 {"variant_id": "scale8-contrast15", "scale": 8, "contrast": 1.5}],
    "resize": "PIL_LANCZOS", "color": "BGR",
    "engine_flags": {"use_det": False, "use_cls": False, "use_rec": True},
    "risk_thresholds": [180, 190, 200, 210, 220],
    "risk_minimum_component_area": 2,
    "risk_minimum_component_height": 2,
    "risk_body_height_ratio": .65,
    "risk_maximum_raised_height_ratio": .8,
    "risk_minimum_baseline_offset_ratio": .22,
}
_HASH = re.compile(r"^[0-9a-f]{64}$")
_SUPPORTED = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-−—=×÷*/().,^{}[]²³√π≤≥<> ")


def _pixels(image):
    return hashlib.sha256(np.asarray(image, dtype=np.uint8).tobytes()).hexdigest()


def _identifier(prefix, value):
    return prefix + "-" + digest(value)[:24]


def _artifact(schema, kind, prefix, layout, inputs, producer, payload):
    return {"schema_version": schema, "kind": kind,
            "artifact_id": _identifier(prefix, [inputs, producer, payload]),
            "revision": 1, "run_id": layout.get("run_id"),
            "book_id": layout["book_id"], "scope_id": layout["scope_id"],
            "input_refs": inputs, "producer": producer,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": digest(payload), "payload": payload}


def _bound_layout(layout, crop_path):
    if (layout.get("schema_version") != "b-math-layout-trial/0.1"
            or layout.get("content_hash") != digest(layout.get("payload"))):
        raise ValueError("unsupported or changed mathematical layout")
    payload = layout["payload"]
    width, height = payload["source_size"]
    box = payload["crop_bbox"]
    if (not valid_bbox(box, width, height) or any(type(v) is not int for v in box)
            or not _HASH.fullmatch(payload["source_sha256"])
            or file_digest(Path(crop_path)) != payload["crop_sha256"]):
        raise ValueError("mathematical layout source crop changed")
    image = Image.open(crop_path).convert("RGB")
    if image.size != (box[2]-box[0], box[3]-box[1]):
        raise ValueError("mathematical layout source crop dimensions changed")
    seen = set()
    for fraction in payload["fraction_candidates"]:
        fid = fraction["fraction_id"]
        if fid in seen:
            raise ValueError("duplicate mathematical fraction")
        seen.add(fid)
        bar = fraction["bar_bbox"]
        if not valid_bbox(bar, width, height):
            raise ValueError("invalid mathematical fraction bar")
        for role in ("numerator", "denominator"):
            role_box = fraction[role]["pixel_bbox"]
            if (not valid_bbox(role_box, width, height)
                    or any(type(v) is not int for v in role_box)
                    or not (box[0] <= role_box[0] < role_box[2] <= box[2]
                            and box[1] <= role_box[1] < role_box[3] <= box[3])
                    or not (role_box[3] <= bar[1]+1 if role == "numerator"
                            else role_box[1] >= bar[3]-1)):
                raise ValueError("mathematical role lies outside its source side")
    return image


def _source(layout, image):
    payload = layout["payload"]
    result = {k: copy.deepcopy(payload[k]) for k in
              ("asset_id", "source_sha256", "source_size", "crop_bbox", "crop_sha256")}
    result.update(base_crop_rgb_sha256=_pixels(image), base_crop_size=list(image.size))
    return result


def _role_crop(layout, image, fraction, role):
    source_box, box = layout["payload"]["crop_bbox"], fraction[role]["pixel_bbox"]
    padding = CONFIG["role_padding_pixels"]
    padded = [max(source_box[0], box[0]-padding), max(source_box[1], box[1]-padding),
              min(source_box[2], box[2]+padding), min(source_box[3], box[3]+padding)]
    local = [padded[i]-source_box[i % 2] for i in range(4)]
    crop = image.crop(local)
    rid = _identifier("math-role", [reference(layout), fraction["fraction_id"], role, box])
    receipt = {"role_id": rid, "fraction_id": fraction["fraction_id"], "role": role,
               "pixel_bbox": list(box), "crop_bbox": padded, "crop_local_bbox": local,
               "role_crop_rgb_sha256": _pixels(crop), "role_crop_size": list(crop.size),
               "original_ocr_refs": copy.deepcopy(fraction[role]["ocr_refs"]),
               "original_raw_texts": copy.deepcopy(fraction[role]["raw_texts"])}
    return receipt, crop


def _preprocess(crop, definition, box):
    scale = definition["scale"]
    transformed = crop.resize((crop.width*scale, crop.height*scale), Image.Resampling.LANCZOS)
    transformed = ImageEnhance.Contrast(transformed).enhance(definition["contrast"])
    bgr = np.ascontiguousarray(np.asarray(transformed, dtype=np.uint8)[:, :, ::-1])
    receipt = {**definition, "resize": CONFIG["resize"], "color": CONFIG["color"],
               "transformed_size": list(transformed.size),
               "transformed_bgr_sha256": hashlib.sha256(bgr.tobytes()).hexdigest(),
               "transformed_to_source": [[1/scale, 0, box[0]], [0, 1/scale, box[1]], [0, 0, 1]]}
    return receipt, bgr


def _json_value(value):
    if isinstance(value, np.ndarray): return _json_value(value.tolist())
    if isinstance(value, np.generic): return _json_value(value.item())
    if isinstance(value, (list, tuple)): return [_json_value(v) for v in value]
    if isinstance(value, dict): return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite OCR result")
    if value is None or isinstance(value, (str, int, float, bool)): return value
    raise ValueError("non-JSON OCR result")


def _candidates(role_id, variant_id, raw):
    if raw is None: return []
    if not isinstance(raw, list): raise ValueError("recognition-only OCR must return a list")
    result = []
    for index, row in enumerate(raw):
        if (not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], str)
                or isinstance(row[1], bool) or not isinstance(row[1], (int, float))
                or not math.isfinite(row[1]) or not 0 <= row[1] <= 1):
            raise ValueError("recognition-only OCR row must be [text, score]")
        result.append({"candidate_id": _identifier("math-role-candidate", [role_id, variant_id, index, row]),
                       "text": row[0], "score": row[1], "raw_result_index": index})
    return result


def _dependency(distribution, module):
    spec = importlib.util.find_spec(module)
    dist = importlib.metadata.distribution(distribution)
    record = next((p for p in (dist.files or []) if str(p).replace("\\", "/").endswith(".dist-info/RECORD")), None)
    return {"distribution": distribution, "version": dist.version,
            "package_entry_sha256": file_digest(Path(spec.origin)),
            "distribution_record_sha256": file_digest(Path(dist.locate_file(record))) if record else None}


def _cpu_backend():
    # Lazy import: merely importing/replaying the module never loads an engine.
    from rapidocr_onnxruntime import RapidOCR
    import rapidocr_onnxruntime
    deps = {}
    for distribution, module in (("rapidocr-onnxruntime", "rapidocr_onnxruntime"),
                                 ("onnxruntime", "onnxruntime"), ("numpy", "numpy"), ("Pillow", "PIL")):
        deps[module] = _dependency(distribution, module)
    cvdist = next((d for d in ("opencv-python", "opencv-python-headless")
                   if importlib.metadata.packages_distributions().get("cv2") and
                   d in importlib.metadata.packages_distributions()["cv2"]), None)
    if cvdist: deps["cv2"] = _dependency(cvdist, "cv2")
    else: deps["cv2"] = {"version": cv2.__version__, "package_entry_sha256": file_digest(Path(cv2.__file__))}
    package = Path(rapidocr_onnxruntime.__file__).parent
    models = [{"name": str(p.relative_to(package)).replace("\\", "/"), "sha256": file_digest(p),
               "active_in_call": "rec_infer" in p.name} for p in sorted(package.rglob("*.onnx"))]
    if not models or not any(m["active_in_call"] for m in models):
        raise ValueError("CPU recognition model receipt unavailable")
    # Explicit provider flags prevent an installed accelerator from changing the
    # execution category. Detector and classifier are disabled at every call.
    engine = RapidOCR(det_use_cuda=False, det_use_dml=False, cls_use_cuda=False,
                      cls_use_dml=False, rec_use_cuda=False, rec_use_dml=False)
    return engine, {"execution_kind": "CPU_RAPIDOCR", "engine": "rapidocr_onnxruntime",
                    "device": "CPU", "dependencies": deps, "dependency_sha256": digest(deps),
                    "model_files": models, "models_sha256": digest(models)}


def collect_math_roles(layout, crop_path, *, recognizer=None):
    """Read both roles of every fraction twice, preserving actual engine output.

    Original pixels are padded by exactly two pixels and clamped to the bound
    base crop. No files or graphs are modified. Injected backends are test data,
    never CPU evidence. An OCR failure remains an explicit empty, unresolved
    variant; its text is not inferred from another preprocessing or old OCR.
    """
    image = _bound_layout(layout, crop_path)
    if recognizer is None:
        backend, backend_receipt = _cpu_backend()
    else:
        backend = recognizer
        backend_receipt = {"execution_kind": "SYNTHETIC_TEST", "engine": "injected_test_backend",
                           "device": "SYNTHETIC_TEST", "dependencies": {},
                           "dependency_sha256": digest({}), "model_files": [], "models_sha256": digest([])}
    producer = {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
                "configuration": copy.deepcopy(CONFIG), "configuration_sha256": digest(CONFIG),
                **backend_receipt}
    roles = []
    for fraction in layout["payload"]["fraction_candidates"]:
        for role in ("numerator", "denominator"):
            receipt, crop = _role_crop(layout, image, fraction, role)
            receipt["variants"] = []
            for definition in CONFIG["variants"]:
                variant, bgr = _preprocess(crop, definition, receipt["crop_bbox"])
                start = time.perf_counter()
                raw, elapsed, error = None, None, None
                try:
                    raw, elapsed = backend(bgr, **CONFIG["engine_flags"])
                    raw, elapsed = _json_value(raw), _json_value(elapsed)
                    candidates = _candidates(receipt["role_id"], definition["variant_id"], raw)
                except Exception as exc:
                    # Preserve a malformed raw result where it is serializable;
                    # never silently promote another variant to a correction.
                    raw, elapsed = _json_value(raw), _json_value(elapsed)
                    candidates, error = [], {"type": type(exc).__name__, "message": str(exc)}
                variant.update(raw_ocr_result=raw, engine_elapsed_seconds=elapsed,
                               wall_elapsed_seconds=time.perf_counter()-start,
                               candidates=candidates, recognition_error=error)
                receipt["variants"].append(variant)
            receipt["verification_status"] = "UNVERIFIED"
            roles.append(receipt)
    payload = {"layout_ref": reference(layout), "source": _source(layout, image), "roles": roles,
               "decision": "HOLD", "verification_status": "UNVERIFIED", "transcription_verified": False,
               "complete": False,
               "formula_text_reconstructed": False, "visual_formula_references_consumed": False,
               "platform_actions": []}
    return _artifact(EVIDENCE_SCHEMA, "MathRoleEvidenceTrial", "math-role-evidence", layout,
                     [reference(layout)], producer, payload)


def _bound_evidence(layout, evidence, image):
    if (evidence.get("schema_version") != EVIDENCE_SCHEMA
            or evidence.get("content_hash") != digest(evidence.get("payload"))):
        raise ValueError("unsupported or changed mathematical role evidence")
    payload, producer = evidence["payload"], evidence["producer"]
    if (payload["layout_ref"] != reference(layout) or evidence["input_refs"] != [reference(layout)]
            or payload["source"] != _source(layout, image)
            or (evidence["book_id"], evidence["scope_id"]) != (layout["book_id"], layout["scope_id"])
            or producer["configuration"] != CONFIG or producer["configuration_sha256"] != digest(CONFIG)):
        raise ValueError("mathematical role evidence source or configuration mismatch")
    if (payload.get("decision") != "HOLD" or payload.get("transcription_verified") is not False
            or payload.get("complete", False) is not False
            or payload.get("verification_status") != "UNVERIFIED"
            or payload.get("formula_text_reconstructed") is not False
            or payload.get("visual_formula_references_consumed") is not False or payload.get("platform_actions") != []):
        raise ValueError("mathematical role evidence falsely claims verification")
    kind = producer.get("execution_kind")
    if kind == "SYNTHETIC_TEST":
        if (producer.get("engine") != "injected_test_backend" or producer.get("device") != "SYNTHETIC_TEST"
                or producer.get("model_files") != [] or producer.get("dependencies") != {}):
            raise ValueError("injected recognizer cannot claim CPU evidence")
    elif kind == "CPU_RAPIDOCR":
        if (producer.get("device") != "CPU" or producer.get("engine") != "rapidocr_onnxruntime"
                or not producer.get("dependencies") or not producer.get("model_files")
                or not any(m.get("active_in_call") for m in producer["model_files"])
                or any(not _HASH.fullmatch(m.get("sha256", "")) for m in producer["model_files"])):
            raise ValueError("missing actual CPU dependency/model receipts")
    else:
        raise ValueError("unknown mathematical recognition execution kind")
    if (producer["dependency_sha256"] != digest(producer["dependencies"])
            or producer["models_sha256"] != digest(producer["model_files"])):
        raise ValueError("mathematical backend receipts changed")
    expected = [(f, r) for f in layout["payload"]["fraction_candidates"] for r in ("numerator", "denominator")]
    if len(payload["roles"]) != len(expected):
        raise ValueError("mathematical role coverage missing or duplicated")
    for actual, (fraction, role) in zip(payload["roles"], expected):
        basic, crop = _role_crop(layout, image, fraction, role)
        if any(actual.get(key) != value for key, value in basic.items()) or actual.get("verification_status") != "UNVERIFIED":
            raise ValueError("mathematical role source, order or pixel digest changed")
        if len(actual["variants"]) != len(CONFIG["variants"]):
            raise ValueError("mathematical preprocessing coverage missing or duplicated")
        for variant, definition in zip(actual["variants"], CONFIG["variants"]):
            basic_variant, _ = _preprocess(crop, definition, basic["crop_bbox"])
            if any(variant.get(key) != value for key, value in basic_variant.items()):
                raise ValueError("mathematical role preprocessing or transform changed")
            if (isinstance(variant["wall_elapsed_seconds"], bool)
                    or not isinstance(variant["wall_elapsed_seconds"], (int, float))
                    or not math.isfinite(variant["wall_elapsed_seconds"]) or variant["wall_elapsed_seconds"] < 0):
                raise ValueError("invalid OCR elapsed receipt")
            if variant["recognition_error"] is None:
                if variant["candidates"] != _candidates(basic["role_id"], definition["variant_id"], variant["raw_ocr_result"]):
                    raise ValueError("mathematical candidates disagree with raw CPU/test output")
            elif variant["candidates"]:
                raise ValueError("failed recognition cannot supply a selected candidate")


def _raised_pixel_risks(image, source_origin, role_box, search_box):
    """Witness small raised ink; no character prediction or expected text input.

    Faint superscripts may break at a dark threshold. Multiple original-pixel
    thresholds retain those components and combine overlapping witnesses. The
    baseline comes from taller local components, not from candidate strings.
    """
    # The layout's tight ink box can omit a faint superscript's upper pixels.
    # Inspect the actual padded OCR crop, and retain a whole component only when
    # it intersects the tight role. This closes that component over the margin
    # without turning a neighboring fraction bar outside the role into a glyph.
    local = [search_box[i]-source_origin[i % 2] for i in range(4)]
    tight = image.crop(local)
    gray = np.asarray(tight.convert("L"))
    witnesses = []
    for threshold in CONFIG["risk_thresholds"]:
        mask = (gray < threshold).astype(np.uint8)
        _, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        components = [(int(x), int(y), int(w), int(h), int(area)) for x, y, w, h, area in stats[1:]
                      if area >= CONFIG["risk_minimum_component_area"] and h >= CONFIG["risk_minimum_component_height"]]
        if len(components) < 2: continue
        maximum = max(c[3] for c in components)
        bodies = [c for c in components if c[3] >= max(5, maximum*CONFIG["risk_body_height_ratio"])]
        if not bodies: continue
        baseline = float(np.median([c[1]+c[3] for c in bodies]))
        body_height = float(np.median([c[3] for c in bodies]))
        for x, y, w, h, area in components:
            component_box = [x+search_box[0], y+search_box[1], x+w+search_box[0], y+h+search_box[1]]
            intersects_role = (min(component_box[2], role_box[2]) > max(component_box[0], role_box[0])
                               and min(component_box[3], role_box[3]) > max(component_box[1], role_box[1]))
            if (intersects_role and h <= body_height*CONFIG["risk_maximum_raised_height_ratio"]
                    and y+h <= baseline-max(2, body_height*CONFIG["risk_minimum_baseline_offset_ratio"])
                    and y+h/2 < baseline-body_height*.45):
                witnesses.append({"threshold": threshold,
                                  "component_bbox": component_box,
                                  "area": area, "body_baseline_y": baseline+search_box[1], "body_height": body_height})
    groups = []
    for witness in witnesses:
        box = witness["component_bbox"]
        linked = []
        for index, group in enumerate(groups):
            if any(min(box[2], other["component_bbox"][2])-max(box[0], other["component_bbox"][0]) >=
                   .5*min(box[2]-box[0], other["component_bbox"][2]-other["component_bbox"][0])
                   and max(box[1], other["component_bbox"][1])-min(box[3], other["component_bbox"][3]) <= 3
                   for other in group):
                linked.append(index)
        group = [witness]
        for index in reversed(linked): group.extend(groups.pop(index))
        groups.append(group)
    result = []
    for group in groups:
        box = [min(w["component_bbox"][0] for w in group), min(w["component_bbox"][1] for w in group),
               max(w["component_bbox"][2] for w in group), max(w["component_bbox"][3] for w in group)]
        local_box = [box[i]-source_origin[i % 2] for i in range(4)]
        result.append({"code": "SUPERSCRIPT_PIXEL_RISK", "component_bbox": box,
                       "threshold_votes": sorted({w["threshold"] for w in group}),
                       "body_baseline_y": float(np.median([w["body_baseline_y"] for w in group])),
                       "body_height": float(np.median([w["body_height"] for w in group])),
                       "component_pixel_sha256": _pixels(image.crop(local_box)),
                       "witnesses": sorted(group, key=lambda w: (w["threshold"], w["component_bbox"])),
                       "status": "UNRESOLVED", "transcription_verified": False})
    return sorted(result, key=lambda r: (r["component_bbox"][0], r["component_bbox"][1]))


def build_math_reading(layout, role_evidence, crop_path):
    """Keep nested roles, all raw hypotheses and source-pixel omission risks.

    Exact two-pass agreement is only an observation. Raised-ink witnesses remain
    unresolved even when OCR includes a superscript character, since recognizing
    the right glyph at the right location is a separate verification step.
    ``raised_symbol_slots`` expose source-bound regions for a future independent
    small-symbol backend; they contain no fabricated character or correction.
    """
    image = _bound_layout(layout, crop_path)
    _bound_evidence(layout, role_evidence, image)
    by_key = {(r["fraction_id"], r["role"]): r for r in role_evidence["payload"]["roles"]}
    fractions, issues = [], []
    for original in layout["payload"]["fraction_candidates"]:
        fraction = {"fraction_id": original["fraction_id"], "bar_bbox": copy.deepcopy(original["bar_bbox"]),
                    "ambiguous_ocr_refs": copy.deepcopy(original["ambiguous_ocr_refs"]),
                    "status": "ROLE_CANDIDATES_UNVERIFIED", "verification_status": "UNVERIFIED"}
        for role in ("numerator", "denominator"):
            evidence = by_key[(original["fraction_id"], role)]
            projected = copy.deepcopy(evidence)
            variants = projected["variants"]
            candidates = [c for v in variants for c in v["candidates"]]
            agreement = (all(v["recognition_error"] is None and len(v["candidates"]) == 1 for v in variants)
                         and len({v["candidates"][0]["text"] for v in variants if len(v["candidates"]) == 1}) == 1
                         and bool(candidates) and bool(candidates[0]["text"].strip()))
            projected.update(candidate_refs=[c["candidate_id"] for c in candidates],
                             exact_two_pass_agreement=agreement,
                             consensus_text=candidates[0]["text"] if agreement else None,
                             selected_candidate_refs=[], transcription_verified=False, complete=False,
                             status="ROLE_CANDIDATES_UNVERIFIED")
            pixel_risks = _raised_pixel_risks(image, layout["payload"]["crop_bbox"][:2],
                                             evidence["pixel_bbox"], evidence["crop_bbox"])
            projected["pixel_risks"] = pixel_risks
            projected["raised_symbol_slots"] = [
                {"slot_id": _identifier("math-raised-symbol", [evidence["role_id"], risk["component_bbox"], risk["component_pixel_sha256"]]),
                 "role_id": evidence["role_id"], "source_bbox": risk["component_bbox"],
                 "source_pixel_sha256": risk["component_pixel_sha256"], "status": "NOT_ATTEMPTED",
                 "candidate_refs": [], "transcription_verified": False} for risk in pixel_risks]
            recognition_risks = []
            if not all(v["candidates"] and any(c["text"].strip() for c in v["candidates"]) for v in variants):
                recognition_risks.append({"code": "MATH_ROLE_OCR_EMPTY_OR_FAILED", "status": "UNRESOLVED"})
            elif not agreement:
                recognition_risks.append({"code": "MATH_ROLE_OCR_DISAGREEMENT", "status": "UNRESOLVED"})
            unknown = sorted({char for c in candidates for char in c["text"] if char not in _SUPPORTED})
            if unknown:
                recognition_risks.append({"code": "MATH_UNSUPPORTED_SYMBOL_RISK", "symbols": unknown, "status": "UNRESOLVED"})
            projected["recognition_risks"] = recognition_risks
            fraction[role] = projected
            for risk in pixel_risks+recognition_risks:
                issues.append({"fraction_id": original["fraction_id"], "role_id": evidence["role_id"],
                               "role": role, **copy.deepcopy(risk)})
        fractions.append(fraction)
    payload = {"layout_ref": reference(layout), "role_evidence_ref": reference(role_evidence),
               "source": copy.deepcopy(role_evidence["payload"]["source"]), "fractions": fractions,
               "reading_groups": copy.deepcopy(layout["payload"]["reading_groups"]),
               "source_ocr": copy.deepcopy(layout["payload"]["source_ocr"]),
               "source_layout_issues": copy.deepcopy(layout["payload"]["issues"]), "issues": issues,
               "decision": "HOLD", "verification_status": "UNVERIFIED", "transcription_verified": False,
               "complete": False,
               "formula_text_reconstructed": False, "visual_formula_references_consumed": False,
               "graph_modified": False, "platform_actions": [],
               "limitations": ["Two preprocessing variants can agree while both omit a raised symbol.",
                               "Pixel components witness possible raised ink; they do not identify a mathematical character.",
                               "Candidates are not selected, formula-complete, human-verified or authorized for submission."]}
    producer = {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
                "method": "nested_all_role_ocr+multi_threshold_raised_ink_witnesses",
                "configuration": copy.deepcopy(CONFIG), "configuration_sha256": digest(CONFIG),
                "execution_kind": role_evidence["producer"]["execution_kind"]}
    return _artifact(READING_SCHEMA, "MathReadingTrial", "math-reading", layout,
                     [reference(layout), reference(role_evidence)], producer, payload)
