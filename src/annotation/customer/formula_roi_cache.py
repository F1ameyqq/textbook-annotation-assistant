"""Thin ROI intent/cache gate over existing customer Store; no model imports.

No file reads, crop generation, network or model runtime. The owned worker must
verify original source bytes, crop pixels and model files before its ONE call.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re

KIND = "customer-formula-roi-v1"
MODEL_FILES = {"image_resizer.onnx", "encoder.onnx", "decoder.onnx", "tokenizer.json"}
HASH = re.compile(r"[0-9a-f]{64}\Z")
POLICY = "ORIGINAL_RGB_SINGLE_ROI_NO_EXTRA_VARIANTS/v1"


class FormulaHold(ValueError):
    pass


def _need(value, message):
    if not value:
        raise FormulaHold(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def build_request(source, bbox, roi_bytes, roi_rgb_bytes, model_identity):
    """Pure identity builder. Pixel/source authenticity is a worker boundary.

    source: {book_id, asset_id, sha256, width, height}. ROI bytes are the exact
    newly prepared lossless crop; RGB bytes are its canonical decoded pixels.
    model_identity includes backend/version, four model files and worker/code/
    preprocessing/runtime identity. No path, answer or expected TeX is accepted.
    """
    _need(set(source) == {"book_id", "asset_id", "sha256", "width", "height"}, "SOURCE_FIELDS")
    _need(all(isinstance(source[k], str) and source[k] for k in ("book_id", "asset_id")), "SOURCE_IDENTITY")
    _need(HASH.fullmatch(source["sha256"] or ""), "SOURCE_HASH")
    _need(all(type(source[k]) is int and source[k] > 0 for k in ("width", "height")), "SOURCE_SIZE")
    w, h = source["width"], source["height"]
    _need(isinstance(bbox, list) and len(bbox) == 4 and all(type(v) is int for v in bbox), "ROI_BOX")
    _need(0 <= bbox[0] < bbox[2] <= w and 0 <= bbox[1] < bbox[3] <= h, "ROI_OUTSIDE_SOURCE")
    _need(bbox != [0, 0, w, h], "WHOLE_PAGE_FORMULA_REPLAY_FORBIDDEN")
    _need(type(roi_bytes) is bytes and bool(roi_bytes), "ROI_ORIGINAL_BYTES_REQUIRED")
    _need(type(roi_rgb_bytes) is bytes and len(roi_rgb_bytes) == (bbox[2]-bbox[0])*(bbox[3]-bbox[1])*3, "ROI_RGB_SIZE")
    model = copy.deepcopy(model_identity)
    _need(set(model) == {"backend", "version", "files", "code_sha256", "runtime", "configuration"}, "MODEL_IDENTITY_FIELDS")
    _need(model["backend"] == "rapid-latex-ocr" and model["version"] == "0.0.9", "PINNED_LOCAL_BACKEND_REQUIRED")
    _need(isinstance(model["files"], list) and len(model["files"]) == 4 and {f["name"] for f in model["files"]} == MODEL_FILES, "FOUR_MODELS_REQUIRED")
    _need(all(type(f.get("bytes")) is int and f["bytes"] > 0 and HASH.fullmatch(f.get("sha256", "")) for f in model["files"]), "MODEL_FILE_IDENTITIES")
    _need(isinstance(model["code_sha256"], dict) and bool(model["code_sha256"]) and all(HASH.fullmatch(v) for v in model["code_sha256"].values()), "BACKEND_AND_WORKER_CODE_HASHES_REQUIRED")
    _need(isinstance(model["runtime"], dict) and bool(model["runtime"]) and isinstance(model["configuration"], dict) and bool(model["configuration"]), "RUNTIME_AND_CONFIGURATION_REQUIRED")
    model["files"].sort(key=lambda f: f["name"])
    # Independent of model/encoding/asset display name: changing those cannot
    # silently re-run a consumed geometric ROI from the same original source.
    roi_identity = {"book_id": source["book_id"], "source_sha256": source["sha256"],
                    "source_size": [w, h], "source_bbox": list(bbox), "roi_rgb_sha256": _hash(roi_rgb_bytes)}
    cache_identity = {"roi_identity": roi_identity, "roi_original_sha256": _hash(roi_bytes),
                      "roi_original_bytes": len(roi_bytes), "model_identity_sha256": digest(model), "policy": POLICY}
    return {"schema": "CustomerFormulaROIRequest/v1", "source": copy.deepcopy(source),
            "roi_identity": roi_identity, "roi_key": digest(roi_identity), "cache_identity": cache_identity,
            "cache_key": digest(cache_identity), "model_identity": model, "model_calls_max": 1}


def _check_request(request):
    _need(request.get("schema") == "CustomerFormulaROIRequest/v1" and request.get("model_calls_max") == 1, "REQUEST_SCHEMA")
    _need(request["roi_key"] == digest(request["roi_identity"]), "ROI_KEY_CHANGED")
    _need(request["cache_key"] == digest(request["cache_identity"]), "CACHE_KEY_CHANGED")
    _need(request["cache_identity"]["roi_identity"] == request["roi_identity"] and
          request["cache_identity"]["model_identity_sha256"] == digest(request["model_identity"]) and
          request["cache_identity"]["policy"] == POLICY, "REQUEST_BINDING_CHANGED")
    source, roi = request["source"], request["roi_identity"]
    _need((source["book_id"], source["sha256"], [source["width"], source["height"]]) ==
          (roi["book_id"], roi["source_sha256"], roi["source_size"]), "SOURCE_BINDING_CHANGED")
    box = roi["source_bbox"]
    _need(isinstance(box, list) and len(box) == 4 and all(type(v) is int for v in box) and
          0 <= box[0] < box[2] <= source["width"] and 0 <= box[1] < box[3] <= source["height"], "ROI_BOX_CHANGED")
    _need(HASH.fullmatch(roi["source_sha256"]) and HASH.fullmatch(roi["roi_rgb_sha256"]) and
          HASH.fullmatch(request["cache_identity"]["roi_original_sha256"]), "REQUEST_HASH_FIELDS")
    _need(roi["source_bbox"] != [0, 0, *roi["source_size"]], "WHOLE_PAGE_FORMULA_REPLAY_FORBIDDEN")


def _candidate(request, observation, *, allow_synthetic=False):
    _need(observation.get("schema") == "CustomerFormulaROIObservation/v1", "WORKER_OBSERVATION_SCHEMA")
    for field in ("roi_key", "cache_key"):
        _need(observation.get(field) == request[field], "WORKER_ROI_OR_CACHE_MISMATCH")
    _need(observation.get("model_identity_sha256") == request["cache_identity"]["model_identity_sha256"], "WORKER_MODEL_MISMATCH")
    _need(observation.get("source_verified") is True and observation.get("roi_verified") is True,
          "WORKER_MUST_VERIFY_SOURCE_AND_ROI")
    _need(observation.get("owned_os_release_confirmed") is True, "WORKER_RELEASE_UNPROVEN")
    _need(observation.get("recognition_error") is None and observation.get("engine_calls") == 1,
          "ONE_SUCCESSFUL_LOCAL_CALL_REQUIRED")
    execution = observation.get("execution_kind")
    _need(execution == "LOCAL_CPU_FORMULA_ROI" or (allow_synthetic and execution == "SYNTHETIC_TEST"), "LOCAL_EXECUTION_KIND_REQUIRED")
    raw = observation.get("raw_latex")
    _need(isinstance(raw, str) and bool(raw.strip()), "EMPTY_OR_NONSTRING_FORMULA_RESULT")
    _need(isinstance(observation.get("raw_record"), dict) and HASH.fullmatch(observation["raw_record"].get("sha256", "")), "ORIGINAL_WORKER_RECORD_REQUIRED")
    return {"schema": "CustomerFormulaROICandidate/v1", "cache_key": request["cache_key"],
            "source": copy.deepcopy(request["source"]), "source_bbox": copy.deepcopy(request["roi_identity"]["source_bbox"]),
            "roi_original_sha256": request["cache_identity"]["roi_original_sha256"],
            "model_identity_sha256": request["cache_identity"]["model_identity_sha256"],
            "raw_latex": raw, "execution_kind": execution, "status": "TEX_CANDIDATE_PENDING_REVIEW",
            "apply_to_content_automatically": False, "content_approved": False,
            "observation": copy.deepcopy(observation)}


def obtain_candidate(store, request, *, allow_first_local_call=False, run_once=None, allow_synthetic=False):
    """Reuse COMPLETE or call one owned worker after durable unique INTENT.

    Uses Store.operation/begin/finish/get only; atomic begin prevents duplicate
    callers. It does not need a second database or a manually prepared manifest.
    The stable ROI operation key also blocks engine/encoding changes after any
    previous attempt. Same-source full-page OCR is never accepted as an ROI.
    """
    request = copy.deepcopy(request)
    _check_request(request)
    key = request["roi_key"]
    old = store.operation(KIND, key)
    if old is not None:
        _need(old["state"] == "COMPLETE", "PRIOR_ROI_INTENT_OR_FAILURE_NO_RESEND")
        retained = store.get(old["output"])
        _need(retained.get("cache_key") == request["cache_key"], "CONSUMED_ROI_MODEL_OR_BYTES_CHANGED_NO_RESEND")
        value = _candidate(request, retained["observation"], allow_synthetic=allow_synthetic)
        return {"candidate": value, "reused": True, "new_worker_invocations": 0, "operation_ref": old["output"]}
    _need(allow_first_local_call is True and callable(run_once), "FIRST_NEW_ROI_CALL_NOT_ENABLED")
    # Existing Store.begin is a unique SQL INSERT; a concurrent loser raises
    # before invoking its callback. No automatic failed/INTENT reset exists.
    store.begin(KIND, key)
    try:
        observation = run_once(copy.deepcopy(request))
        value = _candidate(request, observation, allow_synthetic=allow_synthetic)
        record = {"cache_key": request["cache_key"], "request": request, "observation": copy.deepcopy(observation)}
        ref = store.finish(KIND, key, "COMPLETE", record)
        return {"candidate": value, "reused": False, "new_worker_invocations": 1, "operation_ref": ref}
    except BaseException as exc:
        # Process death may leave INTENT; neither that nor this failure retries.
        current = store.operation(KIND, key)
        if current is not None and current["state"] == "INTENT":
            store.finish(KIND, key, "FAILED_NO_RETRY", {"cache_key": request["cache_key"], "request": request,
                "error_type": type(exc).__name__, "error": str(exc), "automatic_retry": False})
        raise
