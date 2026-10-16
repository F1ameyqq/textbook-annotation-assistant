"""Durable local B recognition/refinement/assembly/check stage orchestration.

Stage completion is execution integrity, not business acceptance. The default
live geometry stage cannot enter refinement: that existing function makes new
CPU OCR calls, so an explicit use_ocr=True is required. Cached E0.2/0.3 imports
never run OCR and must exactly match the current source and context.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from . import batch, offline
from .baseline import code_digest, digest, file_digest, load_source, valid_bbox
from .batch_quality import audit_batch
from . import recovery_stage
from . import continuation_stage, continued_quality
from . import inline_stage

# Explicit bindings are also useful for synthetic fault tests; there is no
# alternate runtime or hidden production backend in this module.
run_batch = batch.run_batch
refine = offline.refine
assemble = offline.assemble
quality_check = offline.quality_check

SCHEMA = "b-pipeline-report-trial/0.1"
STAGE_SCHEMA = "b-pipeline-stage-trial/0.1"
CONTINUATION_STAGES = ("continuation_prepare", "continuation_proof", "continuation_apply", "continuation_quality")
INLINE_STAGES = ("inline_prepare", "inline_apply", "inline_quality")
SQL = """
CREATE TABLE IF NOT EXISTS stage_attempts (
 attempt_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, stage_id TEXT NOT NULL,
 expected_key TEXT NOT NULL, dependencies_json TEXT NOT NULL,
 implementation_json TEXT NOT NULL, state TEXT NOT NULL, started_at TEXT NOT NULL,
 finished_at TEXT, error TEXT, output_json TEXT, result_ref_json TEXT);
CREATE TABLE IF NOT EXISTS stage_events (
 event_id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, stage_id TEXT, attempt_id TEXT,
 event_type TEXT NOT NULL, details_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stage_cache (
 expected_key TEXT PRIMARY KEY, stage_id TEXT NOT NULL, output_json TEXT NOT NULL,
 result_ref_json TEXT NOT NULL, attempt_id TEXT NOT NULL, created_at TEXT NOT NULL);
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _ref(value):
    return {k: value[k] for k in ("artifact_id", "revision", "content_hash")}


def _receipt(path, value, *, artifact=False):
    return {"file_sha256": file_digest(Path(path)), "reference": _ref(value) if artifact else
            {"artifact_id": value["artifact_id"], "content_hash": digest(value)}}


def _event(db, run_id, event_type, *, stage_id=None, attempt_id=None, **details):
    cursor = db.execute("INSERT INTO stage_events(run_id,stage_id,attempt_id,event_type,details_json,created_at) VALUES(?,?,?,?,?,?)",
                        (run_id, stage_id, attempt_id, event_type, _json({"run_id": run_id, **details}), _now()))
    return {"run_id": run_id, "event_id": cursor.lastrowid, "event_type": event_type, "attempt_id": attempt_id}


def _function_sha(function):
    return hashlib.sha256(inspect.getsource(function).replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _dependencies():
    return {name: {"version": importlib.metadata.version(name),
                   "package_entry_sha256": file_digest(Path(importlib.util.find_spec(module).origin))}
            for name, module in (("numpy", "numpy"), ("Pillow", "PIL"))}


@contextmanager
def _pipeline_lock(workdir):
    stream = (workdir / "pipeline.lock").open("a+b")
    stream.seek(0, os.SEEK_END)
    if stream.tell() == 0:
        stream.write(b"0")
        stream.flush()
    stream.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            try: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc: raise RuntimeError("another pipeline runner holds this workdir") from exc
        else:
            import fcntl
            try: fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc: raise RuntimeError("another pipeline runner holds this workdir") from exc
        yield
    finally:
        stream.close()


def _implementation(stage, mode, kind, use_ocr, worker, *, continuation_enabled=False, inline_enabled=False):
    functions = {"recognition": run_batch, "evidence": _validate_evidence, "refine": refine,
                 "recover": recovery_stage.recover_evidence, "recovery_review": recovery_stage.build_recovery_review,
                 "assemble": assemble, "quality": quality_check}
    functions.update(continuation_prepare=continuation_stage.prepare_continuation_scope,
        continuation_proof=continuation_stage.build_continuation_stage_proof,
        continuation_apply=continuation_stage.apply_continuation_stage,
        continuation_quality=continued_quality.build_continued_quality)
    functions.update(inline_prepare=inline_stage.prepare_inline_stage, inline_apply=inline_stage.apply_inline_stage,
                     inline_quality=inline_stage.build_inline_quality)
    helpers, names = {}, []
    if stage == "recognition":
        names = ["batch", "baseline"]
    elif stage == "evidence":
        names = ["baseline"]
        helpers = {name: _function_sha(getattr(offline, name)) for name in ("check_artifact", "validate_context")}
    elif stage in INLINE_STAGES:
        names = ["inline_stage", "inline_continuity", "inline_ocr", "inline_ocr_quality", "inline_math", "inline_formula",
                 "inline_candidates", "inline_formula_quality", "formula_canvas", "formula_canvas_quality", "formula_syntax", "formula_quality", "baseline", "formula_backend", "batch"]
    elif stage in CONTINUATION_STAGES:
        names = ["continuation_stage", "continuation", "continuation_apply", "continuation_quality", "boundary", "image_regions", "baseline", "offline", "answer_assembly", "policy"]
        if stage == "continuation_prepare":
            helpers = {name: _function_sha(getattr(offline, name)) for name in ("artifact", "ref", "check_artifact", "assemble", "entity_id", "scope_key")}
        elif stage == "continuation_quality":
            names += ["continued_quality", "continuation_stage_quality", "question_quality", "answer_quality", "recovery_quality", "recovery_apply", "policy"]
            helpers = {name: _function_sha(getattr(offline, name)) for name in ("scalar_issues", "scope_key")}
    elif stage in ("recover", "recovery_review"):
        names = ["recovery_stage", "recovery_apply", "baseline"]
        helpers = {name: _function_sha(getattr(offline, name)) for name in ("artifact", "ref", "check_artifact")}
        if stage == "recover": helpers["validate_context"] = _function_sha(offline.validate_context)
    else:
        common = ["artifact", "ref", "check_artifact"]
        specific = {"refine": ["validate_context", "detect_columns", "locate"],
                    "assemble": ["entity_id", "scope_key"], "quality": ["scalar_issues", "scope_key"]}
        helpers = {name: _function_sha(getattr(offline, name)) for name in common+specific[stage]}
        names = {"refine": ["baseline"], "assemble": ["answer_assembly", "policy"],
                 "quality": ["question_quality", "answer_quality", "recovery_quality", "recovery_apply", "policy"]}[stage]
    modules = {name: code_digest(Path(__file__).with_name(name+".py")) for name in names}
    modules["baseline"] = code_digest(Path(batch.baseline.__file__))
    if stage == "refine": modules["legacy"] = code_digest(batch.baseline.LEGACY_PATH)
    synthetic_refine = stage == "refine" and kind == "SYNTHETIC_TEST" and refine is not offline.refine
    recognizer = (batch._recognizer(use_ocr, worker) if stage == "recognition"
                  else batch._recognizer(True, worker if synthetic_refine else None) if stage == "refine" else None)
    globals_by_stage = {"recognition": [], "evidence": ["CONTEXT_SCHEMA", "EVIDENCE_SCHEMA"], "refine": ["CONTEXT_SCHEMA", "EVIDENCE_SCHEMA", "ASTART"],
                        "recover": ["EVIDENCE_SCHEMA", "CONTEXT_SCHEMA"], "recovery_review": ["EVIDENCE_SCHEMA"],
                        "assemble": ["EVIDENCE_SCHEMA", "GRAPH_SCHEMA", "QSTART", "ASTART", "OPTION", "CAPTION", "DECORATION"],
                        "quality": ["EVIDENCE_SCHEMA", "GRAPH_SCHEMA", "CHECK_SCHEMA"]}
    globals_by_stage.update({name: [] for name in CONTINUATION_STAGES})
    globals_by_stage.update({name: [] for name in INLINE_STAGES})
    globals_by_stage["continuation_prepare"] = ["EVIDENCE_SCHEMA", "GRAPH_SCHEMA", "QSTART", "ASTART", "OPTION", "CAPTION", "DECORATION"]
    global_values = {}
    for name in globals_by_stage[stage]:
        value = getattr(offline, name)
        global_values[name] = {"pattern": value.pattern, "flags": value.flags} if hasattr(value, "pattern") else value
    configuration = {"stage_id": stage, "mode": mode, "execution_kind": kind, "use_ocr": use_ocr,
                     "offline_globals": global_values,
                     "refinement_mode": ("SYNTHETIC_TEST_OVERRIDE" if synthetic_refine else "CPU_OCR") if stage == "refine" else None}
    if stage in ("recover", "recovery_review"): configuration["recovery_policy"] = recovery_stage.POLICY
    if stage in CONTINUATION_STAGES: configuration["continuation_policy"] = continuation_stage.POLICY
    if stage in INLINE_STAGES: configuration["inline_policy"] = inline_stage.POLICY
    if (stage == "assemble" and (continuation_enabled or inline_enabled)) or (stage == "quality" and inline_enabled):
        configuration["artifact_time_policy"] = "EXECUTION_TIME_IN_STAGE_JOURNAL/0.1"
    dependencies = _dependencies()
    if stage in CONTINUATION_STAGES+INLINE_STAGES:
        import cv2
        native = Path(getattr(cv2, "_native", cv2).__file__)
        dependencies["opencv"] = {"version": cv2.__version__, "package_entry_sha256": file_digest(Path(cv2.__file__)),
                                  "native_module": {"name": native.name, "sha256": file_digest(native)}}
    return {"code": {"pipeline": code_digest(Path(__file__)), "entrypoint": _function_sha(functions[stage]),
                     "helpers": helpers, "modules": modules},
            "configuration": configuration,
            "dependencies": dependencies, "recognizer": recognizer}


def _validate_review(source, review):
    if (review.get("schema_version") != "b-review-trial/0.1" or not review.get("artifact_id")
            or (review.get("book_id"), review.get("scope_id")) != (source["book_id"], source["scope_id"])
            or not isinstance(review.get("question_census"), dict) or not isinstance(review.get("reference_quality"), str)):
        raise ValueError("review schema, identity or census is invalid")
    assets = {a["asset_id"]: a for a in source["assets"]}
    for aid, census in review["question_census"].items():
        if (aid not in assets or census.get("sha256") != assets[aid]["sha256"]
                or not isinstance(census.get("printed_numbers"), list)):
            raise ValueError("review census source hash or asset is stale")
    for case in review.get("answer_checks", []):
        if any(aid not in assets or assets[aid]["sha256"] != sha for aid, sha in case.get("asset_sha256", {}).items()):
            raise ValueError("review answer-check source hash is stale")


def _validate_evidence(value, source, context):
    offline.check_artifact(value, {"b-evidence-trial/0.2", "b-evidence-trial/0.3"})
    if (value.get("kind") != "EvidenceBundleTrial"
            or (value.get("book_id"), value.get("scope_id")) != (source["book_id"], source["scope_id"])
            or value["payload"].get("context") != context):
        raise ValueError("cached/refined evidence scope or context is stale")
    assets = sorted(source["assets"], key=lambda a: a["reading_order"])
    pages = value["payload"].get("pages", [])
    if [p.get("source") for p in pages] != assets or [p.get("asset_id") for p in pages] != [a["asset_id"] for a in assets]:
        raise ValueError("evidence must contain the exact full declared asset set in source order")
    seen = set()
    for page in pages:
        asset = page["source"]
        raw = page.get("ocr_lines", [])
        raw_ids = {line.get("line_id") for line in raw}
        if page.get("page_role") != context["pages"][asset["asset_id"]]["role"]:
            raise ValueError("evidence page role differs from reviewed context")
        for line in raw+page.get("answer_detail_lines", []):
            lid = line.get("line_id")
            if (not isinstance(lid, str) or not lid or lid in seen
                    or not valid_bbox(line.get("bbox", []), asset["width"], asset["height"])
                    or not isinstance(line.get("text"), str)):
                raise ValueError("evidence OCR identity, text or source geometry is invalid")
            seen.add(lid)
            if "parent_line_id" in line and line["parent_line_id"] not in raw_ids:
                raise ValueError("detail OCR parent belongs to another page or is missing")
            location = line.get("location")
            if location:
                windows = context["pages"][asset["asset_id"]]["windows"]
                index = location.get("window_index")
                if (type(index) is not int or not 0 <= index < len(windows)
                        or location.get("section_path") != windows[index]["path"]
                        or location.get("column") != windows[index]["column"]):
                    raise ValueError("evidence location does not match the supplied context")
    if (value["payload"].get("history_annotations_consumed") is not False
            or value["payload"].get("transcription_verified", False) is not False
            or value["payload"].get("business_acceptance", False) is not False
            or value["payload"].get("platform_actions", []) != []):
        raise ValueError("imported evidence cannot claim business acceptance or platform actions")


def _validate_result(stage, value, source, context, review, dependencies, recognition_dir, current_evidence=None):
    if stage in INLINE_STAGES:
        schema = {"inline_prepare": inline_stage.PREPARE_SCHEMA, "inline_apply": inline_stage.APPLY_SCHEMA, "inline_quality": "b-check-trial/0.5"}[stage]
        kind = {"inline_prepare": "InlinePreparationTrial", "inline_apply": "InlineApplyStageTrial", "inline_quality": "CheckReportTrial"}[stage]
        offline.check_artifact(value, {schema})
        p = value["payload"]
        if (value.get("kind") != kind or value["book_id"] != source["book_id"] or value["scope_id"] != dependencies["inline"]["scope_id"]
                or p.get("package_receipt") != inline_stage.content_receipt(dependencies["inline"])
                or digest({k: p.get(k) for k in inline_stage._flags()}) != digest(inline_stage._flags()) or "created_at" in value):
            raise ValueError("inline stage changed scope, package, nonacceptance or identity policy")
        if stage == "inline_prepare":
            if (p.get("base_evidence_ref") != dependencies["evidence"]["result_ref"]
                    or p.get("base_graph_ref") != dependencies["graph"]["result_ref"]
                    or p.get("execution_state") not in {"READY", "PARTIAL", "FAILED"}):
                raise ValueError("inline preparation is not bound to current E/G and declared execution scope")
        elif stage == "inline_apply":
            if p.get("prepared_ref") != dependencies["prepared"]["result_ref"]:
                raise ValueError("inline attachment is not bound to current preparation")
        elif (p.get("inline_basis", {}).get("prepared_ref") != dependencies["prepared"]["result_ref"]
                or p["inline_basis"].get("application_ref") != dependencies["application"]["result_ref"]
                or p["inline_basis"].get("base_check_ref") != dependencies["base_check"]["result_ref"]):
            raise ValueError("inline quality is not bound to current preparation/application/base check")
        return
    if stage in CONTINUATION_STAGES:
        schemas = {"continuation_prepare": "b-continuation-scope-trial/0.1",
            "continuation_proof": "b-continuation-proof-stage-trial/0.1",
            "continuation_apply": "b-continuation-apply-stage-trial/0.1",
            "continuation_quality": "b-check-trial/0.4"}
        offline.check_artifact(value, {schemas[stage]})
        kinds = {"continuation_prepare": "ContinuationScopeTrial", "continuation_proof": "ContinuationProofStageTrial",
            "continuation_apply": "ContinuationApplyStageTrial", "continuation_quality": "CheckReportTrial"}
        if (value.get("kind") != kinds[stage] or value.get("book_id") != source["book_id"]
                or value.get("scope_id") != dependencies["continuation"]["extended_scope_id"]
                or value["payload"].get("business_acceptance") is not False or value["payload"].get("transcription_verified") is not False
                or value["payload"].get("decision") != "HOLD" or value["payload"].get("platform_actions") != []):
            raise ValueError("continued stage must preserve its explicit expanded scope and HOLD")
        payload = value["payload"]
        if payload.get("package_receipt") != continuation_stage.content_receipt(dependencies["continuation"]):
            raise ValueError("continued stage is not bound to the actual package content")
        if stage == "continuation_prepare":
            if (payload.get("base_evidence_ref") != dependencies["evidence"]["result_ref"]
                    or payload.get("base_graph_ref") != dependencies["graph"]["result_ref"]):
                raise ValueError("continuation scope changed its actual base inputs")
        elif payload.get("scope_ref") != dependencies["scope"]["result_ref"]:
            raise ValueError("continued result refers to a different scope stage")
        if stage == "continuation_apply" and payload.get("proof_stage_ref") != dependencies["proof"]["result_ref"]:
            raise ValueError("continuation application uses a different proof stage")
        return
    if stage == "recognition":
        if value.get("payload", {}).get("source_manifest") != source:
            raise ValueError("recognition batch scope changed")
        # audit_batch takes a path. The caller performs this check with the
        # actual validated manifest, never a newly fabricated source alias.
        return
    if stage in ("evidence", "refine", "recover"):
        _validate_evidence(value, source, context)
        if stage == "refine" and value["input_refs"] != [dependencies["baseline"]["result_ref"], dependencies["context"]["reference"]]:
            raise ValueError("refined evidence does not reference its actual baseline/context inputs")
        if stage == "recover":
            migration = value["payload"].get("recovery_migration", {})
            document_refs = dependencies["recovery"]["documents"]
            if (value["schema_version"] != "b-evidence-trial/0.3" or migration.get("policy") != recovery_stage.POLICY
                    or value.get("producer", {}).get("identity_policy") != recovery_stage.IDENTITY_POLICY or "created_at" in value
                    or migration.get("current_base_ref") != dependencies["evidence"]["result_ref"]
                    or migration.get("package_receipt") != recovery_stage.content_receipt(dependencies["recovery"])
                    or migration.get("payloads_equal") is not True or migration.get("new_ocr_calls") != 0
                    or value.get("input_refs") != [dependencies["evidence"]["result_ref"], document_refs["base_evidence"]["artifact_ref"],
                        document_refs["recovery"]["artifact_ref"], document_refs["source_review"]["artifact_ref"],
                        dependencies["recovery"]["package"]["reference"]]):
                raise ValueError("recovery stage did not preserve exact current-base/package migration binding")
    elif stage == "recovery_review":
        offline.check_artifact(value, {recovery_stage.REVIEW_SCHEMA})
        document = value["payload"].get("review", {})
        if (value.get("kind") != "RecoveryReviewTrial" or value.get("input_refs") != [dependencies["review"]["reference"], dependencies["evidence"]["result_ref"]]
                or value.get("producer", {}).get("identity_policy") != recovery_stage.IDENTITY_POLICY or "created_at" in value
                or value["payload"].get("input_review_ref") != dependencies["review"]["reference"]
                or value["payload"].get("recovered_evidence_ref") != dependencies["evidence"]["result_ref"]
                or document.get("recovery_migration_ref") != dependencies["evidence"]["result_ref"]
                or current_evidence is None or value["payload"].get("package_receipt") != current_evidence["payload"]["recovery_migration"]["package_receipt"]
                or value["payload"].get("new_ocr_calls") != 0 or value["payload"].get("decision") != "HOLD"):
            raise ValueError("recovery review is not bound to current review and recovered evidence")
    elif stage == "assemble":
        offline.check_artifact(value, {"b-graph-trial/0.2", "b-graph-trial/0.3"})
        if value.get("kind") != "QuestionGraphTrial" or value.get("input_refs") != [dependencies["evidence"]["result_ref"]]:
            raise ValueError("graph not bound to its exact evidence revision")
    else:
        offline.check_artifact(value, {"b-check-trial/0.2", "b-check-trial/0.3"})
        if (value.get("kind") != "CheckReportTrial" or value.get("input_refs") != [dependencies["evidence"]["result_ref"],
                dependencies["graph"]["result_ref"], dependencies["review"]["reference"]]
                or value["payload"].get("decision") != "HOLD"):
            raise ValueError("quality report not bound to actual evidence, graph and review, or falsely released")
    if ((value.get("book_id"), value.get("scope_id")) != (source["book_id"], source["scope_id"])
            or value["payload"].get("business_acceptance", False) is not False
            or value["payload"].get("transcription_verified", False) is not False
            or value["payload"].get("platform_actions", []) != []):
        raise ValueError("stage result scope or nonacceptance invariant changed")


def _wrapper(source, mode, stage, key, dependencies, implementation, attempt_id, result):
    payload = {"mode": mode, "stage_id": stage, "expected_key": key, "dependencies": dependencies,
               "implementation": implementation, "attempt_id": attempt_id, "result": result,
               "decision": "HOLD", "transcription_verified": False, "business_acceptance": False,
               "platform_actions": []}
    return {"schema_version": STAGE_SCHEMA, "kind": "PipelineStageTrial",
            "artifact_id": "pipeline-stage-"+digest(payload)[:24], "revision": 1,
            "book_id": source["book_id"], "scope_id": source["scope_id"],
            "input_refs": [{"artifact_id": source["artifact_id"], "content_hash": digest(source)}],
            "producer": {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__))},
            "created_at": _now(), "payload": payload, "content_hash": digest(payload)}


def _read_stage(db, workdir, descriptor, source, mode, stage, key, dependencies, implementation):
    value = batch._read_object(workdir, descriptor)
    p = value["payload"]
    if (value.get("schema_version") != STAGE_SCHEMA or value.get("kind") != "PipelineStageTrial"
            or value.get("revision") != 1 or value.get("artifact_id") != "pipeline-stage-"+digest(p)[:24]
            or (value.get("book_id"), value.get("scope_id")) != (source["book_id"], source["scope_id"])
            or value.get("input_refs") != [{"artifact_id": source["artifact_id"], "content_hash": digest(source)}]
            or any(p.get(k) != expected for k, expected in (("mode", mode), ("stage_id", stage), ("expected_key", key),
                    ("dependencies", dependencies), ("implementation", implementation), ("decision", "HOLD"),
                    ("transcription_verified", False), ("business_acceptance", False), ("platform_actions", [])))
            or value.get("producer") != {"module": __name__, "version": "0.1.0", "code_sha256": implementation["code"]["pipeline"]}):
        raise ValueError("cached stage envelope or dependency version changed")
    origin = db.execute("SELECT * FROM stage_attempts WHERE attempt_id=?", (p.get("attempt_id"),)).fetchone()
    if (origin is None or origin["state"] != "SUCCEEDED" or origin["stage_id"] != stage or origin["expected_key"] != key
            or origin["dependencies_json"] != _json(dependencies) or origin["implementation_json"] != _json(implementation)
            or not origin["output_json"] or json.loads(origin["output_json"]) != descriptor
            or not origin["result_ref_json"] or json.loads(origin["result_ref_json"]) != _ref(p["result"])):
        raise ValueError("cached stage has no matching successful origin attempt")
    events = db.execute("SELECT * FROM stage_events WHERE attempt_id=? ORDER BY event_id", (origin["attempt_id"],)).fetchall()
    starts = [e for e in events if e["event_type"] == "STAGE_STARTED"]
    ends = [e for e in events if e["event_type"] == "STAGE_SUCCEEDED"]
    if (len(starts) != 1 or len(ends) != 1 or starts[0]["event_id"] >= ends[0]["event_id"]
            or json.loads(ends[0]["details_json"]).get("stage_state") != "DONE"
            or json.loads(ends[0]["details_json"]).get("output") != descriptor):
        raise ValueError("cached stage lacks durable successful execution receipts")
    return value


def run_pipeline(source_path, context_path, review_path, workdir, *, use_ocr=False, max_items=None,
                 stop_after=None, evidence_path=None, worker=None, recovery_path=None,
                 continuation_path=None, adjacent_source_path=None, inline_path=None, inline_source_path=None):
    """Resume source-bound local stages; READY still means HOLD for business use."""
    if type(use_ocr) is not bool or (max_items is not None and (type(max_items) is not int or max_items < 1)):
        raise ValueError("invalid pipeline OCR flag or batch budget")
    mode = "CACHED_INPUT" if evidence_path is not None else "LIVE_BATCH"
    stages = ["evidence", "assemble", "quality"] if evidence_path is not None else ["recognition", "refine", "assemble", "quality"]
    if recovery_path is not None:
        stages.insert(stages.index("assemble"), "recover")
        stages.insert(stages.index("quality"), "recovery_review")
    if (continuation_path is None) != (adjacent_source_path is None):
        raise ValueError("continuation package and adjacent original source are required together")
    if continuation_path is not None: stages.extend(CONTINUATION_STAGES)
    if (inline_path is None) != (inline_source_path is None):
        raise ValueError("inline package and explicit original source are required together")
    if inline_path is not None: stages.extend(INLINE_STAGES)
    if mode == "CACHED_INPUT" and stop_after == "recognition": stop_after = "evidence"
    if stop_after is not None and stop_after not in stages:
        raise ValueError("stop_after must name a stage present in this pipeline mode")
    if mode == "CACHED_INPUT" and (use_ocr or worker is not None):
        raise ValueError("cached input never executes an OCR worker; do not combine it with OCR flags")
    if mode == "CACHED_INPUT" and max_items is not None:
        raise ValueError("max_items only budgets live per-asset recognition, not cached stages")
    source_path, context_path, review_path, workdir = map(Path, (source_path, context_path, review_path, workdir))
    source, _ = load_source(source_path)
    context, review = [json.loads(p.read_text(encoding="utf-8")) for p in (context_path, review_path)]
    offline.validate_context(source, context)
    _validate_review(source, review)
    cached_evidence = None
    if evidence_path is not None:
        evidence_path = Path(evidence_path)
        cached_evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        _validate_evidence(cached_evidence, source, context)
        if recovery_path is not None and cached_evidence["schema_version"] != "b-evidence-trial/0.2":
            raise ValueError("recovery cannot be applied again to already recovered E0.3 evidence")
    package = None
    if recovery_path is not None:
        recovery_path = Path(recovery_path)
        if "recovery_migration_ref" in review:
            raise ValueError("recovery requires the original review, not an already migrated review")
        package = recovery_stage.load_recovery_package(recovery_path, source_path, context)
    receipts = {"source": _receipt(source_path, source), "context": _receipt(context_path, context),
                "review": _receipt(review_path, review),
                "evidence": _receipt(evidence_path, cached_evidence, artifact=True) if cached_evidence else None}
    if package is not None: receipts["recovery"] = package["receipt"]
    if continuation_path is not None:
        continuation_path, adjacent_source_path = Path(continuation_path), Path(adjacent_source_path)
        continuation_package = continuation_stage.load_continuation_package(continuation_path, source_path, adjacent_source_path)
        receipts["continuation"] = continuation_package["receipt"]
    if inline_path is not None:
        inline_path, inline_source_path = Path(inline_path), Path(inline_source_path)
        inline_package = inline_stage.load_inline_package(inline_path, inline_source_path)
        receipts["inline"] = inline_package["receipt"]
    source_ref = receipts["source"]["reference"]
    kind = "CACHED_INPUT" if cached_evidence else "SYNTHETIC_TEST" if worker else "LIVE_CPU_OCR" if use_ocr else "LIVE_GEOMETRY"
    run_id = "pipeline-run-"+uuid4().hex
    workdir.mkdir(parents=True, exist_ok=True)
    recognition_dir = workdir / "recognition"
    with _pipeline_lock(workdir):
        return _run(source_path, context_path, review_path, evidence_path, workdir, source, context, review,
                    receipts, source_ref, cached_evidence, mode, kind, stages, run_id, use_ocr, max_items, stop_after, worker, recognition_dir,
                    recovery_path=recovery_path, continuation_path=continuation_path, adjacent_source_path=adjacent_source_path,
                    inline_path=inline_path, inline_source_path=inline_source_path)


def _run(source_path, context_path, review_path, evidence_path, workdir, source, context, review,
         receipts, source_ref, cached_evidence, mode, kind, stages, run_id, use_ocr, max_items, stop_after, worker, recognition_dir,
         recovery_path=None, continuation_path=None, adjacent_source_path=None, inline_path=None, inline_source_path=None):
    db = sqlite3.connect(workdir / "pipeline.sqlite3")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.executescript(SQL)
    results, observations, entries, invalidated = {"active_review": review}, {}, [], 0
    try:
        with db:
            for prior in db.execute("SELECT * FROM stage_attempts WHERE state='RUNNING'").fetchall():
                db.execute("UPDATE stage_attempts SET state='INTERRUPTED',finished_at=?,error=? WHERE attempt_id=?",
                           (_now(), "Previous exclusive process interrupted", prior["attempt_id"]))
                _event(db, run_id, "STAGE_INTERRUPTED", stage_id=prior["stage_id"], attempt_id=prior["attempt_id"], origin_run_id=prior["run_id"])
            _event(db, run_id, "RUN_STARTED", mode=mode, source_ref=source_ref, input_receipts=receipts,
                   stage_ids=stages, max_items=max_items, stop_after=stop_after, execution_kind=kind)
        stopped, blocked = False, False
        for stage in stages:
            entry = {"stage_id": stage, "expected_key": None, "dependencies": {}, "implementation": None,
                     "state": "WAITING", "reason": None, "last_error": None, "cached": False,
                     "origin_attempt_id": None, "current_run_receipt": None, "output": None, "result_ref": None}
            entries.append(entry)
            if stopped or blocked:
                entry["reason"] = "STOP_AFTER" if stopped else "DEPENDENCY_NOT_READY"
                continue
            if stage == "refine" and not use_ocr:
                entry["reason"], blocked = "OCR_REQUIRED", True
                continue
            dep = {"source": receipts["source"]}
            if stage == "evidence": dep.update(context=receipts["context"], evidence=receipts["evidence"])
            elif stage == "refine":
                dep.update(context=receipts["context"], recognition=observations["recognition"], baseline={
                    "artifact": results["recognition"]["payload"]["bundle"], "result_ref": _ref(results["baseline"])})
            elif stage == "recover": dep.update(evidence=observations["evidence"], recovery=receipts["recovery"])
            elif stage == "assemble": dep["evidence"] = observations["evidence"]
            elif stage == "recovery_review": dep.update(evidence=observations["evidence"], review=receipts["review"])
            elif stage == "quality":
                review_dependency = receipts["review"]
                if recovery_path is not None:
                    active = results["active_review"]
                    review_dependency = {**observations["recovery_review"],
                                         "reference": {"artifact_id": active["artifact_id"], "content_hash": digest(active)}}
                dep.update(evidence=observations["evidence"], graph=observations["assemble"], review=review_dependency)
            elif stage == "continuation_prepare":
                dep.update(evidence=observations["evidence"], graph=observations["assemble"], continuation=receipts["continuation"])
            elif stage == "continuation_proof":
                dep.update(scope=observations["continuation_prepare"], continuation=receipts["continuation"])
            elif stage == "continuation_apply":
                dep.update(scope=observations["continuation_prepare"], proof=observations["continuation_proof"], continuation=receipts["continuation"])
            elif stage == "continuation_quality":
                review_dependency = receipts["review"]
                if recovery_path is not None:
                    active = results["active_review"]
                    review_dependency = {**observations["recovery_review"], "reference": {"artifact_id": active["artifact_id"], "content_hash": digest(active)}}
                dep.update(scope=observations["continuation_prepare"], proof=observations["continuation_proof"],
                    application=observations["continuation_apply"], review=review_dependency, continuation=receipts["continuation"])
            elif stage == "inline_prepare":
                if continuation_path is not None:
                    e = results["continuation_prepare"]["payload"]["evidence"]
                    g = results["continuation_apply"]["payload"]["graph"]
                    dep.update(evidence={**observations["continuation_prepare"], "result_ref": _ref(e)},
                               graph={**observations["continuation_apply"], "result_ref": _ref(g)}, inline=receipts["inline"])
                else: dep.update(evidence=observations["evidence"], graph=observations["assemble"], inline=receipts["inline"])
            elif stage == "inline_apply": dep.update(prepared=observations["inline_prepare"], inline=receipts["inline"])
            elif stage == "inline_quality":
                dep.update(prepared=observations["inline_prepare"], application=observations["inline_apply"],
                    base_check=observations["continuation_quality" if continuation_path is not None else "quality"], inline=receipts["inline"])
            entry["dependencies"] = dep
            try:
                implementation_options = {"continuation_enabled": continuation_path is not None}
                if inline_path is not None: implementation_options["inline_enabled"] = True
                implementation = _implementation(stage, mode, kind, use_ocr, worker, **implementation_options)
            except Exception as exc:
                with db:
                    event = _event(db, run_id, "STAGE_SETUP_FAILED", stage_id=stage,
                                   dependencies=dep, error=str(exc), error_type=type(exc).__name__)
                entry.update(state="FAILED", reason="STAGE_SETUP_FAILED", last_error=str(exc), current_run_receipt=event)
                blocked = True
                continue
            key = digest({"mode": mode, "stage_id": stage, "dependencies": dep, "implementation": implementation})
            entry.update(expected_key=key, dependencies=dep, implementation=implementation)
            cached = db.execute("SELECT * FROM stage_cache WHERE expected_key=?", (key,)).fetchone()
            if cached:
                try:
                    descriptor = json.loads(cached["output_json"])
                    value = _read_stage(db, workdir, descriptor, source, mode, stage, key, dep, implementation)
                    result = value["payload"]["result"]
                    if (cached["stage_id"] != stage or cached["attempt_id"] != value["payload"]["attempt_id"]
                            or json.loads(cached["result_ref_json"]) != _ref(result)):
                        raise ValueError("stage cache row differs from the immutable origin")
                    _validate_result(stage, result, source, context, results["active_review"], dep, recognition_dir, results.get("evidence"))
                    if stage == "recognition" and not audit_batch(source_path, recognition_dir, result)["payload"]["accepted"]:
                        raise ValueError("child recognition journal or source artifacts are invalid")
                except (ValueError, OSError, KeyError, TypeError) as exc:
                    invalidated += 1
                    with db:
                        db.execute("DELETE FROM stage_cache WHERE expected_key=?", (key,))
                        _event(db, run_id, "INVALIDATED", stage_id=stage, reason="CACHE_INVALID", error=str(exc), previous_output=dict(cached))
                else:
                    with db:
                        event = _event(db, run_id, "CACHE_HIT", stage_id=stage, attempt_id=value["payload"]["attempt_id"],
                                       expected_key=key, output=descriptor, result_ref=_ref(result))
                    entry.update(state="DONE", cached=True, origin_attempt_id=value["payload"]["attempt_id"],
                                 current_run_receipt=event, output=descriptor, result_ref=_ref(result))
            if entry["state"] != "DONE":
                attempt_id = "pipeline-attempt-"+uuid4().hex
                with db:
                    db.execute("INSERT INTO stage_attempts VALUES(?,?,?,?,?,?,'RUNNING',?,NULL,NULL,NULL,NULL)",
                               (attempt_id, run_id, stage, key, _json(dep), _json(implementation), _now()))
                    _event(db, run_id, "STAGE_STARTED", stage_id=stage, attempt_id=attempt_id, expected_key=key)
                try:
                    if stage == "recognition":
                        result = run_batch(source_path, recognition_dir, use_ocr=use_ocr, max_items=max_items, worker=worker)
                    elif stage == "evidence": result = copy.deepcopy(cached_evidence)
                    elif stage == "refine": result = refine(source_path, results["baseline"], context)
                    elif stage == "recover": result = recovery_stage.recover_evidence(results["evidence"], recovery_path, source_path, context)
                    elif stage == "assemble":
                        result = assemble(results["evidence"])
                        if continuation_path is not None or inline_path is not None:
                            # This result has not been published. Historical
                            # input objects and archives remain untouched.
                            result.pop("created_at", None)
                    elif stage == "recovery_review": result = recovery_stage.build_recovery_review(review, results["evidence"])
                    elif stage == "continuation_prepare":
                        result = continuation_stage.prepare_continuation_scope(results["evidence"], results["assemble"], continuation_path, source_path, adjacent_source_path)
                    elif stage == "continuation_proof":
                        result = continuation_stage.build_continuation_stage_proof(results["continuation_prepare"], continuation_path, source_path, adjacent_source_path)
                    elif stage == "continuation_apply":
                        result = continuation_stage.apply_continuation_stage(results["continuation_prepare"], results["continuation_proof"], continuation_path, source_path, adjacent_source_path)
                    elif stage == "continuation_quality":
                        result = continued_quality.build_continued_quality(results["continuation_prepare"], results["continuation_proof"],
                            results["continuation_apply"], results["active_review"], package_path=continuation_path,
                            source_path=source_path, adjacent_source_path=adjacent_source_path)
                    elif stage == "inline_prepare":
                        e = results["continuation_prepare"]["payload"]["evidence"] if continuation_path is not None else results["evidence"]
                        g = results["continuation_apply"]["payload"]["graph"] if continuation_path is not None else results["assemble"]
                        result = inline_stage.prepare_inline_stage(e, g, inline_path, inline_source_path)
                    elif stage == "inline_apply": result = inline_stage.apply_inline_stage(results["inline_prepare"])
                    elif stage == "inline_quality":
                        result = inline_stage.build_inline_quality(results["inline_prepare"], results["inline_apply"],
                            results["continuation_quality" if continuation_path is not None else "quality"])
                    else:
                        result = quality_check(results["evidence"], results["assemble"], results["active_review"])
                        if inline_path is not None:
                            # Only this newly produced, unpublished check loses
                            # its clock; historical input/archive objects do not.
                            result.pop("created_at", None)
                    _validate_result(stage, result, source, context, results["active_review"], dep, recognition_dir, results.get("evidence"))
                    if stage == "recognition" and not audit_batch(source_path, recognition_dir, result)["payload"]["accepted"]:
                        raise ValueError("child recognition run failed independent integrity audit")
                    state = "DONE"
                    if stage == "recognition" and not result["payload"]["batch_complete"]:
                        state = "FAILED" if result["payload"]["counts"]["failed"] else "PARTIAL"
                    if stage == "inline_prepare": state = {"READY": "DONE", "PARTIAL": "PARTIAL", "FAILED": "FAILED"}[result["payload"]["execution_state"]]
                    descriptor = batch._put_object(workdir, _wrapper(source, mode, stage, key, dep, implementation, attempt_id, result))
                    with db:
                        db.execute("UPDATE stage_attempts SET state='SUCCEEDED',finished_at=?,output_json=?,result_ref_json=? WHERE attempt_id=?",
                                   (_now(), _json(descriptor), _json(_ref(result)), attempt_id))
                        event = _event(db, run_id, "STAGE_SUCCEEDED", stage_id=stage, attempt_id=attempt_id,
                                       expected_key=key, stage_state=state, output=descriptor, result_ref=_ref(result))
                        if state == "DONE":
                            db.execute("INSERT INTO stage_cache VALUES(?,?,?,?,?,?) ON CONFLICT(expected_key) DO UPDATE SET output_json=excluded.output_json,result_ref_json=excluded.result_ref_json,attempt_id=excluded.attempt_id,created_at=excluded.created_at",
                                       (key, stage, _json(descriptor), _json(_ref(result)), attempt_id, _now()))
                    entry.update(state=state, origin_attempt_id=attempt_id, current_run_receipt=event, output=descriptor, result_ref=_ref(result))
                except Exception as exc:
                    with db:
                        db.execute("UPDATE stage_attempts SET state='FAILED',finished_at=?,error=? WHERE attempt_id=?", (_now(), str(exc), attempt_id))
                        event = _event(db, run_id, "STAGE_FAILED", stage_id=stage, attempt_id=attempt_id, expected_key=key, error=str(exc), error_type=type(exc).__name__)
                    entry.update(state="FAILED", last_error=str(exc), origin_attempt_id=attempt_id, current_run_receipt=event)
            if entry["state"] == "DONE":
                results[stage] = result
                observations[stage] = {"output": entry["output"], "result_ref": entry["result_ref"]}
                if stage == "recognition": results["baseline"] = batch._read_object(recognition_dir, result["payload"]["bundle"])
                if stage in ("refine", "recover"):
                    results["evidence"], observations["evidence"] = result, observations[stage]
                if stage == "recovery_review": results["active_review"] = result["payload"]["review"]
            else: blocked = True
            if stage == stop_after: stopped = True
        run_error = None
        try:
            current_source, _ = load_source(source_path)
            if (current_source != source or _receipt(source_path, source) != receipts["source"]
                    or _receipt(context_path, context) != receipts["context"] or _receipt(review_path, review) != receipts["review"]
                    or (evidence_path and _receipt(evidence_path, cached_evidence, artifact=True) != receipts["evidence"])):
                raise ValueError("pipeline input files changed during execution")
            if recovery_path is not None and recovery_stage.load_recovery_package(recovery_path, source_path, context)["receipt"] != receipts["recovery"]:
                raise ValueError("recovery package files changed during pipeline execution")
            if continuation_path is not None and continuation_stage.load_continuation_package(continuation_path, source_path, adjacent_source_path)["receipt"] != receipts["continuation"]:
                raise ValueError("continuation input files changed during pipeline execution")
            if inline_path is not None and inline_stage.load_inline_package(inline_path, inline_source_path)["receipt"] != receipts["inline"]:
                raise ValueError("inline package/journal/source files changed during pipeline execution")
        except Exception as exc:
            run_error = {"code": "INPUT_CHANGED_DURING_RUN", "error": str(exc), "error_type": type(exc).__name__}
            with db: _event(db, run_id, "RUN_INPUT_CHANGED", **run_error)
        counts = {"declared_stages": len(stages), "done": sum(e["state"] == "DONE" for e in entries),
                  "pending": sum(e["state"] in ("WAITING", "PARTIAL") for e in entries),
                  "failed": sum(e["state"] == "FAILED" for e in entries), "cache_hits": sum(e["cached"] for e in entries),
                  "invalidated": invalidated}
        state = "FAILED" if counts["failed"] or run_error else "READY" if counts["done"] == len(stages) else "PARTIAL"
        payload = {"mode": mode, "run_id": run_id, "execution_kind": kind, "source_ref": source_ref,
                   "source_assets": sorted(source["assets"], key=lambda a: a["reading_order"]), "source_manifest": source,
                   "input_receipts": receipts, "stages": entries, "counts": counts, "pipeline_state": state,
                   "run_error": run_error,
                   "decision": "HOLD", "transcription_verified": False, "business_acceptance": False, "platform_actions": [],
                   "limitations": ["READY means that local stages produced bound artifacts, never business acceptance.",
                                   "The declared asset scope is not a whole-book or 214-page acceptance claim.",
                                   "Geometry-only live runs wait before refinement because refinement performs new CPU OCR."]}
        if continuation_path is not None:
            payload["continuation_scope"] = {"package_receipt": receipts["continuation"],
                "base_source_ref": source_ref, "adjacent_coverage": "PREFIX_CROP_ONLY_WITH_BOUNDARY_AND_FIGURES",
                "full_adjacent_page_ocr": False, "viewer_page_mapping_verified": False}
            payload["final_outputs"] = None
            if state == "READY":
                payload["final_outputs"] = {"evidence_ref": _ref(results["continuation_prepare"]["payload"]["evidence"]),
                    "graph_ref": _ref(results["continuation_apply"]["payload"]["graph"]), "quality_ref": _ref(results["continuation_quality"])}
        if inline_path is not None:
            payload["inline_scope"] = {"package_receipt": receipts["inline"], "candidate_selection_performed": False,
                                       "entire_answer_reconstructed": False, "new_model_calls": 0}
            payload["final_outputs"] = None
            if state == "READY":
                payload["final_outputs"] = {"evidence_ref": results["inline_prepare"]["payload"]["base_evidence_ref"],
                    "graph_ref": _ref(results["inline_apply"]["payload"]["graph"]), "quality_ref": _ref(results["inline_quality"])}
        producer = {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__))}
        report = {"schema_version": SCHEMA, "kind": "PipelineReportTrial",
                  "artifact_id": "pipeline-report-"+digest([source_ref, producer, payload])[:24], "revision": 1,
                  "run_id": run_id, "book_id": source["book_id"], "scope_id": source["scope_id"],
                  "input_refs": [source_ref], "producer": producer, "created_at": _now(), "payload": payload, "content_hash": digest(payload)}
        descriptor = batch._put_object(workdir, report)
        with db: _event(db, run_id, "RUN_FINISHED", report_ref=_ref(report), report_artifact=descriptor)
        return report
    finally:
        db.close()
