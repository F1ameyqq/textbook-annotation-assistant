"""Formula observations with a fixed, source-preserving encoder canvas.

The historical formula backend/configuration remains unchanged. This path
preserves the whole canvas while retaining learned sizing, with every resize,
padding operation, raw resizer output and final tensor available for replay.
Raw observations and all old/new candidates remain unselected and unverified.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import time

import numpy as np
from PIL import Image

from .baseline import code_digest, digest
from .formula_backend import _local_cpu_backend, plan_formula_units, reference, pixel_digest
from .formula_candidates import build_formula_candidates
from .formula_syntax import fraction_count, parse_formula_latex

OBSERVATION_SCHEMA = "b-formula-canvas-observation-trial/0.1"
CANDIDATE_SCHEMA = "b-formula-canvas-candidate-trial/0.1"
CONFIG = {
    "padding_pixels": 2,
    "variants": [
        {"variant_id": "gray-native", "scale": 1},
        {"variant_id": "gray-scale3", "scale": 3},
    ],
    "grayscale": "PIL_L", "resize": "PIL_LANCZOS", "color": "RGB",
    "canvas_multiple": 32, "canvas_alignment": "TOP_LEFT", "canvas_background": 255,
    "maximum_canvas_size": [672, 192], "minimum_canvas_size": [32, 32],
    "full_pad_normalization": "MINMAX_UINT8", "resizer_maximum_iterations": 10,
    "tensor_layout": "NCHW", "tensor_dtype": "float32",
    "tensor_channels": 1, "normalization_mean": .7931, "normalization_std": .1738,
    "normalization_max_pixel_value": 255, "seed": 0, "maximum_decode_tokens": 128,
    "temperature": .00001, "learned_resizer": True, "trim": False,
}


def plan_canvas_units(layout, crop_path):
    """Use the unchanged full-fraction source plan, including its two-pixel pad."""
    return plan_formula_units(layout, crop_path)


def _full_pad(image):
    """Normalize grayscale but retain every input pixel, including faint edges."""
    gray = np.asarray(image.convert("L"), dtype=np.float32)
    low, high = float(gray.min()), float(gray.max())
    if high > low:
        gray = (gray-low)/(high-low)*255
    tile = Image.fromarray(gray.astype(np.uint8)).convert("L")
    multiple = CONFIG["canvas_multiple"]
    size = tuple(((value+multiple-1)//multiple)*multiple for value in tile.size)
    padded = Image.new("L", size, CONFIG["canvas_background"])
    padded.paste(tile, (0, 0))
    return padded, {"input_size": list(image.size), "input_rgb_sha256": pixel_digest(image.convert("RGB")),
        "output_size": list(size), "output_gray_sha256": pixel_digest(padded), "min": low, "max": high,
        "threshold_crop": False}


def _minmax_size(image):
    """Match upstream resize/pad limits without cropping or thresholding."""
    original = image
    ratio = max(a/b for a, b in zip(image.size, CONFIG["maximum_canvas_size"]))
    if ratio > 1:
        size = np.maximum(np.array(image.size)//ratio, 1).astype(int)
        image = image.resize(tuple(size), Image.Resampling.BILINEAR)
    downscaled = image.size
    size = tuple(max(a, b) for a, b in zip(image.size, CONFIG["minimum_canvas_size"]))
    if size != image.size:
        padded = Image.new("L", size, CONFIG["canvas_background"])
        padded.paste(image, (0, 0))
        image = padded
    return image, {"input_size": list(original.size), "input_rgb_sha256": pixel_digest(original.convert("RGB")),
        "downscaled_size": list(downscaled), "output_size": list(image.size),
        "output_rgb_sha256": pixel_digest(image.convert("RGB"))}


def _tensor(canvas):
    gray = np.asarray(canvas.convert("L"), dtype=np.float32)
    maximum = np.float32(CONFIG["normalization_max_pixel_value"])
    mean = np.float32(CONFIG["normalization_mean"])*maximum
    std = np.float32(CONFIG["normalization_std"])*maximum
    normalized = (gray-mean)*np.reciprocal(std, dtype=np.float32)
    return np.ascontiguousarray(normalized[None, None, :, :], dtype="<f4")


def _source_matrix(unit, scale_x, scale_y):
    x, y = unit["source_bbox"][:2]
    return ([[scale_x, 0, -scale_x*x], [0, scale_y, -scale_y*y], [0, 0, 1]],
            [[1/scale_x, 0, x], [0, 1/scale_y, y], [0, 0, 1]])


def preprocess_canvas(image, unit, definition, *, resizer=None, recorded_trace=None):
    """Replay upstream learned sizing with full-canvas padding and exact traces.

    ``resizer`` uses the actual ONNX adapter signature ([tensor])->[logits].
    No resizer means a synthetic keep-current-width response. ``recorded_trace``
    is only for cached replay: logits remain observations, not model reruns.
    """
    if definition not in CONFIG["variants"] or (resizer is not None and recorded_trace is not None):
        raise ValueError("unknown canvas preprocessing or ambiguous resizer input")
    tile = image.crop(unit["crop_local_bbox"]).convert("L")
    scale = definition["scale"]
    transformed = tile.resize((tile.width*scale, tile.height*scale), Image.Resampling.LANCZOS).convert("RGB")
    padded, initial_pad = _full_pad(transformed)
    input_image, initial_minmax = _minmax_size(padded)
    input_image = input_image.convert("RGB")
    trace = {"initial_pad": initial_pad, "initial_minmax": initial_minmax,
        "input_image_size": list(input_image.size), "input_image_rgb_sha256": pixel_digest(input_image),
        "steps": [], "stop_reason": None}
    initial_x = scale*initial_minmax["downscaled_size"][0]/initial_minmax["input_size"][0]
    initial_y = scale*initial_minmax["downscaled_size"][1]/initial_minmax["input_size"][1]
    ratio, width, height = 1, input_image.width, input_image.height
    tensor = None
    for index in range(CONFIG["resizer_maximum_iterations"]):
        height = int(height*ratio)
        if width < 1 or height < 1 or width*height > 16_777_216:
            raise ValueError("resizer requested an invalid or excessive intermediate image")
        method = Image.Resampling.BILINEAR if ratio > 1 else Image.Resampling.LANCZOS
        resized = input_image.resize((width, height), method)
        limited, minmax = _minmax_size(resized)
        padded, pad = _full_pad(limited)
        canvas = padded.convert("RGB")
        tensor = _tensor(canvas)
        source_x = initial_x*width/input_image.width*minmax["downscaled_size"][0]/width
        source_y = initial_y*height/input_image.height*minmax["downscaled_size"][1]/height
        forward, inverse = _source_matrix(unit, source_x, source_y)
        step = {"step_index": index, "requested_ratio": ratio, "requested_size": [width, height],
            "resize_method": "PIL_BILINEAR" if ratio > 1 else "PIL_LANCZOS",
            "resized_rgb_sha256": pixel_digest(resized.convert("RGB")), "minmax": minmax, "pad": pad,
            "canvas_size": list(canvas.size), "canvas_rgb_sha256": pixel_digest(canvas),
            "tensor_shape": list(tensor.shape), "tensor_dtype": CONFIG["tensor_dtype"],
            "tensor_sha256": hashlib.sha256(tensor.tobytes()).hexdigest(),
            "source_to_canvas": forward, "canvas_to_source": inverse,
            "resizer_logits": None, "resizer_logits_shape": None, "resizer_logits_dtype": None,
            "argmax_index": None, "next_width": None, "terminated": False, "resizer_error": None}
        try:
            if recorded_trace is not None:
                saved = recorded_trace["steps"][index]
                if saved["resizer_error"] is not None:
                    step["resizer_error"] = copy.deepcopy(saved["resizer_error"])
                    trace["stop_reason"] = "RESIZER_FAILED"
                else:
                    logits = np.asarray(saved["resizer_logits"], dtype=saved["resizer_logits_dtype"])
            elif resizer is None:
                logits = np.zeros((1, CONFIG["maximum_canvas_size"][0]//32), dtype=np.float32)
                logits[0, canvas.width//32-1] = 1
            else:
                logits = np.asarray(resizer([tensor.astype(np.float32)])[0])
            if step["resizer_error"] is None:
                if logits.ndim != 2 or logits.shape[0] != 1 or not logits.shape[1] or not np.isfinite(logits).all():
                    raise ValueError("learned resizer must return finite logits for one image")
                argmax = int(np.argmax(logits, axis=-1).item())
                next_width = (argmax+1)*32
                step.update(resizer_logits=logits.tolist(), resizer_logits_shape=list(logits.shape),
                    resizer_logits_dtype=str(logits.dtype), argmax_index=argmax, next_width=next_width,
                    terminated=next_width == canvas.width)
        except Exception as exc:
            step["resizer_error"] = {"type": type(exc).__name__, "status": "RESIZER_FAILED"}
            trace["stop_reason"] = "RESIZER_FAILED"
        trace["steps"].append(step)
        if trace["stop_reason"] == "RESIZER_FAILED":
            break
        if step["terminated"]:
            trace["stop_reason"] = "WIDTH_STABLE"
            break
        width = step["next_width"]
        ratio = width/canvas.width
    else:
        trace["stop_reason"] = "MAX_ITERATIONS"
    final = trace["steps"][-1]
    metadata = {**copy.deepcopy(definition), "grayscale": CONFIG["grayscale"], "resize": CONFIG["resize"],
        "color": CONFIG["color"], "transformed_size": list(transformed.size),
        "transformed_rgb_sha256": pixel_digest(transformed),
        "transformed_to_source": [[1/scale, 0, unit["source_bbox"][0]], [0, 1/scale, unit["source_bbox"][1]], [0, 0, 1]],
        "preprocessing_trace": trace, "paste_offset": [0, 0],
        **{key: copy.deepcopy(final[key]) for key in ("canvas_size", "canvas_rgb_sha256", "tensor_shape", "tensor_dtype",
            "tensor_sha256", "source_to_canvas", "canvas_to_source")}}
    return metadata, tensor


def _envelope(schema, kind, prefix, layout, inputs, producer, payload):
    return {
        "schema_version": schema, "kind": kind,
        "artifact_id": prefix+"-"+digest([inputs, producer, payload])[:24], "revision": 1,
        "book_id": layout["book_id"], "scope_id": layout["scope_id"], "run_id": layout.get("run_id"),
        "input_refs": inputs, "producer": producer, "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload, "content_hash": digest(payload),
    }


def collect_canvas_observations(layout, crop_path, *, model_dir=None, recognizer=None):
    """Read every planned fraction twice; only explicit local models run.

    Test recognizers take one float32 NCHW tensor and return (text, seconds).
    They are always SYNTHETIC_TEST and cannot supply CPU execution provenance.
    """
    image, source, plans = plan_canvas_units(layout, crop_path)
    if recognizer is None:
        engine, backend = _local_cpu_backend(model_dir)
        backend = {**backend, "execution_kind": "CPU_RAPID_LATEX_OCR_PRESERVE_CANVAS",
                   "backend_adapter": "PRESERVE_CANVAS_LEARNED_RESIZER"}
        resizer = engine.image_resizer
        def recognize(tensor):
            started = time.perf_counter()
            tokens = engine.encoder_decoder(tensor, temperature=CONFIG["temperature"])
            decoded = engine.tokenizer.token2str(tokens)
            if not isinstance(decoded, list) or len(decoded) != 1 or not isinstance(decoded[0], str):
                raise ValueError("formula tokenizer must return one text sequence")
            return engine.post_process(decoded[0]), time.perf_counter()-started
    else:
        recognize = recognizer
        resizer = None
        backend = {"execution_kind": "SYNTHETIC_TEST", "backend": "injected-tensor-test-only"}
    producer = {
        "module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
        "configuration": copy.deepcopy(CONFIG), "configuration_sha256": digest(CONFIG),
        "legacy_backend_adapter_code_sha256": code_digest(Path(__file__).with_name("formula_backend.py")),
        **backend,
    }
    units = []
    for plan in plans:
        unit = {**copy.deepcopy(plan), "variants": []}
        for definition in CONFIG["variants"]:
            started = time.perf_counter()
            random_state = np.random.get_state()
            metadata = None
            raw, elapsed, error = None, None, None
            try:
                np.random.seed(CONFIG["seed"])
                metadata, tensor = preprocess_canvas(image, plan, definition, resizer=resizer)
                if metadata["preprocessing_trace"]["stop_reason"] == "RESIZER_FAILED":
                    error = {"type": metadata["preprocessing_trace"]["steps"][-1]["resizer_error"]["type"],
                             "status": "PREPROCESSING_FAILED"}
                else:
                    raw, elapsed = recognize(tensor)
                    if recognizer is None:
                        elapsed = time.perf_counter()-started
                    if (not isinstance(raw, str) or not isinstance(elapsed, (int, float, np.number))
                            or isinstance(elapsed, bool) or not math.isfinite(float(elapsed)) or elapsed < 0):
                        raise ValueError("canvas recognizer must return text and finite nonnegative seconds")
                    elapsed = float(elapsed)
            except Exception as exc:
                if metadata is None:
                    # No complete preprocessing receipt exists. Do not reuse a
                    # previous variant's metadata or invent a successful trace.
                    raise ValueError("canvas preprocessing failed before a complete receipt") from exc
                raw, elapsed = None, None
                error = {"type": type(exc).__name__, "status": "RECOGNITION_FAILED"}
            finally:
                np.random.set_state(random_state)
            unit["variants"].append({**metadata, "raw_latex": raw, "engine_elapsed_seconds": elapsed,
                "wall_elapsed_seconds": time.perf_counter()-started, "recognition_error": error,
                "seed": CONFIG["seed"], "verification_status": "UNVERIFIED"})
        units.append(unit)
    payload = {
        "layout_ref": reference(layout), "source": source, "units": units, "decision": "HOLD",
        "complete": False, "transcription_verified": False, "business_acceptance": False,
        "platform_actions": [], "expected_text_consumed": False, "graph_modified": False,
        "limitations": ["Full-canvas padding preserves source coverage, not mathematical correctness.",
                        "All old and new observations remain unselected; agreement is not verification.",
                        "Fraction observations do not reconstruct the entire answer or surrounding proof."],
    }
    return _envelope(OBSERVATION_SCHEMA, "FormulaCanvasObservationTrial", "formula-canvas-observations",
                     layout, [reference(layout)], producer, payload)


def _validate_observations(layout, observations, crop_path):
    image, source, plans = plan_canvas_units(layout, crop_path)
    payload, producer = observations.get("payload", {}), observations.get("producer", {})
    inputs = [reference(layout)]
    if (observations.get("schema_version") != OBSERVATION_SCHEMA or observations.get("kind") != "FormulaCanvasObservationTrial"
            or type(observations.get("revision")) is not int or observations["revision"] != 1
            or observations.get("input_refs") != inputs or observations.get("run_id") != layout.get("run_id")
            or any(observations.get(k) != layout[k] for k in ("book_id", "scope_id"))
            or observations.get("content_hash") != digest(payload)
            or observations.get("artifact_id") != "formula-canvas-observations-"+digest([inputs, producer, payload])[:24]
            or producer.get("module") != __name__ or producer.get("version") != "0.1.0"
            or producer.get("configuration") != CONFIG or producer.get("configuration_sha256") != digest(CONFIG)
            or producer.get("code_sha256") != code_digest(Path(__file__))
            or producer.get("legacy_backend_adapter_code_sha256") != code_digest(Path(__file__).with_name("formula_backend.py"))
            or payload.get("layout_ref") != reference(layout) or payload.get("source") != source):
        raise ValueError("canvas observation identity, implementation, scope or source changed")
    execution = producer.get("execution_kind")
    if execution == "SYNTHETIC_TEST":
        if (producer.get("backend") != "injected-tensor-test-only"
                or any(k in producer for k in ("model_files", "providers", "backend_version", "backend_adapter"))):
            raise ValueError("synthetic tensor recognizer cannot impersonate a CPU model")
    elif execution == "CPU_RAPID_LATEX_OCR_PRESERVE_CANVAS":
        # Use the unchanged legacy receipt validator without changing or
        # relabelling the retained observation itself.
        from .formula_candidates import _check_producer
        from .formula_backend import CONFIG as OLD_CONFIG
        compatible = copy.deepcopy(observations)
        p = compatible["producer"]
        p.update(module="annotation.recognition.formula_backend", execution_kind="CPU_RAPID_LATEX_OCR",
                 configuration=copy.deepcopy(OLD_CONFIG), configuration_sha256=digest(OLD_CONFIG))
        compatible.update(kind="FormulaObservationTrial",
            artifact_id="formula-observations-"+digest([inputs, p, payload])[:24])
        if producer.get("backend_adapter") != "PRESERVE_CANVAS_LEARNED_RESIZER":
            raise ValueError("canvas CPU path must preserve padding and retain learned sizing")
        _check_producer(compatible)
    else:
        raise ValueError("unknown canvas execution kind")
    if (payload.get("decision") != "HOLD" or any(payload.get(k) is not False for k in
            ("complete", "transcription_verified", "business_acceptance", "expected_text_consumed", "graph_modified"))
            or payload.get("platform_actions") != [] or len(payload.get("units", [])) != len(plans)):
        raise ValueError("canvas observation coverage or nonacceptance flags changed")
    for plan, unit in zip(plans, payload["units"]):
        if {k: v for k, v in unit.items() if k != "variants"} != plan or len(unit.get("variants", [])) != len(CONFIG["variants"]):
            raise ValueError("canvas observation unit source, order or variant coverage changed")
        for definition, variant in zip(CONFIG["variants"], unit["variants"]):
            metadata, _ = preprocess_canvas(image, plan, definition, recorded_trace=variant.get("preprocessing_trace"))
            if any(variant.get(k) != value for k, value in metadata.items()):
                raise ValueError("canvas pixels, tensor or source transform changed")
            if variant.get("seed") != CONFIG["seed"] or variant.get("verification_status") != "UNVERIFIED":
                raise ValueError("canvas seed or verification state changed")
            failed = variant.get("recognition_error") is not None
            if ((not failed and not isinstance(variant.get("raw_latex"), str))
                    or (failed and (variant.get("raw_latex") is not None or variant.get("engine_elapsed_seconds") is not None))):
                raise ValueError("canvas raw observation and execution error disagree")
            if (not isinstance(variant.get("wall_elapsed_seconds"), (int, float))
                    or not math.isfinite(variant["wall_elapsed_seconds"]) or variant["wall_elapsed_seconds"] < 0
                    or (not failed and (not isinstance(variant.get("engine_elapsed_seconds"), (int, float))
                        or not math.isfinite(variant["engine_elapsed_seconds"]) or variant["engine_elapsed_seconds"] < 0))):
                raise ValueError("canvas execution elapsed time is invalid")
    return source


def build_canvas_candidates(layout, observations, crop_path, legacy_observations):
    """Keep every raw path and lossless syntax projection; never select a value."""
    source = _validate_observations(layout, observations, crop_path)
    legacy = build_formula_candidates(layout, legacy_observations, crop_path)
    legacy_units = {unit["fraction_id"]: unit for unit in legacy["payload"]["units"]}
    units, issues = [], []
    for observed in observations["payload"]["units"]:
        unit = copy.deepcopy(observed)
        old = legacy_units[unit["fraction_id"]]
        for variant in unit["variants"]:
            parsed = parse_formula_latex(variant["raw_latex"])
            count = fraction_count(parsed["ast"])
            shape = bool(parsed["supported"] and parsed["normalized_ast"].get("type") == "fraction" and count == 1)
            matching = [v["candidate_id"] for v in old["variants"] if parsed["supported"] and v["parse_result"]["supported"]
                and parsed["normalized_ast"] == v["parse_result"]["normalized_ast"]]
            variant.update(candidate_id="formula-canvas-candidate-"+digest([reference(observations), unit["unit_id"],
                variant["variant_id"], variant["raw_latex"]])[:24], parse_result=parsed, fraction_node_count=count,
                source_fraction_shape_matches=shape, complete=False, transcription_verified=False,
                legacy_agreement_candidate_refs=matching)
            if not parsed["supported"]:
                issues.append(dict(code="FORMULA_CANVAS_SYNTAX_UNSUPPORTED", unit_id=unit["unit_id"], variant_id=variant["variant_id"]))
            elif not shape:
                issues.append(dict(code="FORMULA_CANVAS_SOURCE_FRACTION_SHAPE_MISMATCH", unit_id=unit["unit_id"], variant_id=variant["variant_id"]))
        all_variants = unit["variants"]
        agreement = (all(v["parse_result"]["supported"] for v in all_variants)
            and all(v["parse_result"]["normalized_ast"] == all_variants[0]["parse_result"]["normalized_ast"] for v in all_variants))
        combined = [*all_variants, *old["variants"]]
        cross = (all(v["parse_result"]["supported"] for v in combined)
            and all(v["parse_result"]["normalized_ast"] == combined[0]["parse_result"]["normalized_ast"] for v in combined))
        unit.update(exact_ast_agreement=agreement, cross_path_exact_ast_agreement=cross,
            selected_candidate_refs=[], complete=False, transcription_verified=False,
            status="FORMULA_CANVAS_CANDIDATES_UNVERIFIED")
        if not agreement:
            issues.append(dict(code="FORMULA_CANVAS_VARIANT_DISAGREEMENT_OR_UNPARSED", unit_id=unit["unit_id"]))
        if not cross:
            issues.append(dict(code="FORMULA_CANVAS_LEGACY_DISAGREEMENT_OR_UNPARSED", unit_id=unit["unit_id"]))
        units.append(unit)
    payload = {
        "layout_ref": reference(layout), "observation_ref": reference(observations),
        "legacy_observation_ref": reference(legacy_observations),
        "legacy_observations_archive": copy.deepcopy(legacy_observations),
        "legacy_candidate_ref": reference(legacy), "legacy_candidate_producer": copy.deepcopy(legacy["producer"]),
        "legacy_candidates_payload": copy.deepcopy(legacy["payload"]), "source": source, "units": units,
        "reading_groups": copy.deepcopy(layout["payload"]["reading_groups"]),
        "source_layout_issues": copy.deepcopy(layout["payload"]["issues"]), "issues": issues,
        "decision": "HOLD", "complete": False, "transcription_verified": False, "business_acceptance": False,
        "graph_modified": False, "platform_actions": [], "expected_text_consumed": False,
        "entire_answer_reconstructed": False,
    }
    producer = {
        "module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
        "syntax_code_sha256": code_digest(Path(__file__).with_name("formula_syntax.py")),
        "legacy_candidate_code_sha256": code_digest(Path(__file__).with_name("formula_candidates.py")),
        "execution_kind": observations["producer"]["execution_kind"],
    }
    inputs = [reference(layout), reference(observations), reference(legacy_observations)]
    return _envelope(CANDIDATE_SCHEMA, "FormulaCanvasCandidateTrial", "formula-canvas-candidates",
                     layout, inputs, producer, payload)
