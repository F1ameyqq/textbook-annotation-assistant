"""Independent audit of offline batch scope, journal and retained artifacts.

No batch or recognition producer is imported or executed. SQL success flags and
report completeness are checked against current source bytes and real files.
An accepted integrity check is always HOLD for business acceptance.
"""
from __future__ import annotations

from collections import Counter
import ast
import copy
import importlib.util
import importlib.metadata
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import sqlite3

import cv2
from PIL import Image

from .baseline import code_digest, digest, file_digest, valid_bbox

SCHEMA = "b-batch-check-trial/0.1"


def _ref(value):
    return {key: value.get(key) for key in ("artifact_id", "revision", "content_hash")}


def _portable_path(root, relative):
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or PurePosixPath(relative).is_absolute() or PureWindowsPath(relative).drive
            or ".." in PurePosixPath(relative).parts):
        raise ValueError("nonportable or escaping artifact path")
    path = (root/relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("missing artifact or path outside run")
    return path


def _source(source_path):
    path = Path(source_path).resolve()
    source = json.loads(path.read_text(encoding="utf-8"))
    if (source.get("schema_version") != "b-source-trial/0.1"
            or any(not isinstance(source.get(k), str) or not source[k].strip()
                   for k in ("artifact_id", "book_id", "scope_id"))
            or not isinstance(source.get("assets"), list) or not source["assets"]):
        raise ValueError("unsupported or empty declared source")
    ids, orders = [], []
    for asset in source["assets"]:
        ids.append(asset.get("asset_id"))
        orders.append(asset.get("reading_order"))
        if (not isinstance(ids[-1], str) or not ids[-1]
                or type(orders[-1]) is not int or orders[-1] < 0):
            raise ValueError("invalid source asset identity or order")
        image_path = _portable_path(path.parent, asset.get("path"))
        if file_digest(image_path) != asset.get("sha256"):
            raise ValueError("current source bytes changed")
        with Image.open(image_path) as image:
            if (type(asset.get("width")) is not int or type(asset.get("height")) is not int
                    or image.size != (asset["width"], asset["height"])):
                raise ValueError("source dimensions changed")
    if len(ids) != len(set(ids)) or len(orders) != len(set(orders)):
        raise ValueError("duplicate source asset identity or order")
    return source, sorted(source["assets"], key=lambda a: a["reading_order"])


def _read_object(root, descriptor):
    if not isinstance(descriptor, dict) or set(descriptor) != {"path", "sha256", "artifact_ref"}:
        raise ValueError("invalid artifact descriptor")
    path = _portable_path(root, descriptor["path"])
    if descriptor["path"] != "objects/"+descriptor["sha256"]+".json" or file_digest(path) != descriptor["sha256"]:
        raise ValueError("immutable object bytes or address changed")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(value, dict) or not isinstance(value.get("payload"), dict)
            or value.get("content_hash") != digest(value["payload"])
            or descriptor["artifact_ref"] != _ref(value)):
        raise ValueError("object reference or payload hash changed")
    return value


def _page_integrity(result, asset, single_source, kind, use_ocr):
    """Return defects in an actual retained page, without invoking recognition."""
    defects = []
    if (result.get("schema_version") != "b-evidence-trial/0.1" or result.get("kind") != "EvidenceBundleTrial"
            or result.get("content_hash") != digest(result.get("payload"))
            or result.get("revision") != 1
            or any(result.get(k) != single_source.get(k) for k in ("book_id", "scope_id"))
            or result.get("input_refs") != [{"artifact_id": single_source["artifact_id"], "content_hash": digest(single_source)}]):
        defects.append("BATCH_PAGE_RESULT_BINDING_MISMATCH")
    pages = result.get("payload", {}).get("pages", [])
    if len(pages) != 1 or pages[0].get("asset_id") != asset["asset_id"] or pages[0].get("source") != asset:
        return defects+["BATCH_PAGE_SOURCE_OWNERSHIP_MISMATCH"]
    if result.get("producer", {}).get("ocr_enabled") is not use_ocr:
        defects.append("BATCH_EXECUTION_KIND_MISMATCH")
    page = pages[0]
    crops = page.get("crop_transforms", [])
    crop_ids = [c.get("crop_id") for c in crops]
    if len(crop_ids) != len(set(crop_ids)) or any(c.get("asset_id") != asset["asset_id"] for c in crops):
        defects.append("BATCH_PAGE_SOURCE_OWNERSHIP_MISMATCH")
    for crop in crops:
        box = crop.get("original_bbox", [])
        if (not valid_bbox(box, asset["width"], asset["height"])
                or crop.get("crop_to_original") != [[1,0,box[0]],[0,1,box[1]],[0,0,1]]):
            defects.append("BATCH_PAGE_SOURCE_OWNERSHIP_MISMATCH")
    for region in page.get("regions", []):
        if (region.get("asset_id") != asset["asset_id"] or region.get("crop_id") not in crop_ids
                or not valid_bbox(region.get("bbox", []), asset["width"], asset["height"])):
            defects.append("BATCH_PAGE_SOURCE_OWNERSHIP_MISMATCH")
        if region.get("verification_status") != "UNVERIFIED" or region.get("text_hint_is_final_transcription") is not False:
            defects.append("BATCH_FALSE_VERIFICATION")
    for line in page.get("ocr_lines", []):
        if (line.get("crop_id") not in crop_ids
                or not valid_bbox(line.get("bbox", []), asset["width"], asset["height"])):
            defects.append("BATCH_PAGE_SOURCE_OWNERSHIP_MISMATCH")
    if kind == "BASELINE_GEOMETRY" and page.get("ocr_lines") != []:
        defects.append("BATCH_EXECUTION_KIND_MISMATCH")
    result_payload = result.get("payload", {})
    if (result_payload.get("quality_decision") != "NOT_EVALUATED"
            or result_payload.get("transcription_verified", False) is not False
            or result_payload.get("business_acceptance", False) is not False
            or result_payload.get("platform_actions", []) != []):
        defects.append("BATCH_FALSE_VERIFICATION")
    return list(dict.fromkeys(defects))


def _audit_batch(source_path, workdir, report):
    """Return a deterministic, always-HOLD check of the supplied batch snapshot."""
    issues, summary = [], {}

    def issue(code, detail=None, asset_id=None):
        item = {"code": code, "severity": "ERROR", "detail": detail}
        if asset_id is not None:
            item["asset_id"] = asset_id
        if item not in issues:
            issues.append(item)

    def finish():
        payload = {"accepted": not issues, "decision": "HOLD", "issues": issues,
                   "summary": summary, "business_acceptance": False,
                   "transcription_verified": False, "platform_actions": []}
        inputs = [_ref(report)] if isinstance(report, dict) else []
        producer = {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__))}
        return {"schema_version": SCHEMA, "kind": "BatchCheckTrial",
                "artifact_id": "batch-check-"+digest([inputs, payload, producer])[:24],
                "revision": 1, "run_id": report.get("run_id") if isinstance(report, dict) else None,
                "book_id": report.get("book_id") if isinstance(report, dict) else None,
                "scope_id": report.get("scope_id") if isinstance(report, dict) else None,
                "input_refs": inputs, "producer": producer,
                "content_hash": digest(payload), "payload": payload}

    try:
        source, assets = _source(source_path)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        issue("BATCH_SOURCE_INVALID", str(exc))
        return finish()
    summary.update(declared_asset_count=len(assets), declared_asset_ids=[a["asset_id"] for a in assets])
    if (not isinstance(report, dict) or report.get("schema_version") != "b-batch-report-trial/0.1"
            or report.get("kind") != "BatchReportTrial" or report.get("revision") != 1
            or not isinstance(report.get("payload"), dict)
            or report.get("content_hash") != digest(report.get("payload"))):
        issue("BATCH_REPORT_INVALID")
        return finish()
    payload, root = report["payload"], Path(workdir).resolve()
    source_ref = {"artifact_id": source["artifact_id"], "content_hash": digest(source)}
    if (payload.get("source_manifest") != source or payload.get("source_ref") != source_ref
            or report.get("input_refs") != [source_ref]
            or any(report.get(k) != source[k] for k in ("book_id", "scope_id"))):
        issue("BATCH_SCOPE_BINDING_MISMATCH")
    if payload.get("declared_asset_ids") != [a["asset_id"] for a in assets]:
        issue("BATCH_DECLARED_SCOPE_INCOMPLETE")
    if (payload.get("decision") != "HOLD" or payload.get("business_acceptance") is not False
            or payload.get("transcription_verified") is not False or payload.get("platform_actions") != []):
        issue("BATCH_FALSE_VERIFICATION")
    recognizer = payload.get("recognizer", {})
    kind, use_ocr = recognizer.get("execution_kind"), recognizer.get("use_ocr")
    if (kind not in {"BASELINE_GEOMETRY", "BASELINE_CPU_OCR", "SYNTHETIC_TEST"}
            or type(use_ocr) is not bool or kind == "BASELINE_GEOMETRY" and use_ocr
            or kind == "BASELINE_CPU_OCR" and not use_ocr):
        issue("BATCH_EXECUTION_KIND_MISMATCH")
    fingerprint = digest({k:v for k,v in recognizer.items() if k != "fingerprint"})
    if recognizer.get("fingerprint") != fingerprint:
        issue("BATCH_RECOGNIZER_FINGERPRINT_MISMATCH")
    repo = Path(__file__).resolve().parents[3]
    paths = {"batch": Path(__file__).with_name("batch.py"), "baseline": Path(__file__).with_name("baseline.py"),
             "legacy": repo/"tools/route_a_layout.py"}
    code = recognizer.get("code", {})
    if not paths["batch"].is_file() or code.get("batch") != code_digest(paths["batch"]):
        issue("BATCH_CURRENT_VERSION_MISMATCH", "batch")
    if report.get("producer", {}).get("code_sha256") != code.get("batch"):
        issue("BATCH_CURRENT_VERSION_MISMATCH", "report producer")
    if kind == "SYNTHETIC_TEST":
        if code.get("baseline") is not None or code.get("legacy") is not None or not isinstance(code.get("worker"), str):
            issue("BATCH_EXECUTION_KIND_MISMATCH")
    else:
        if code.get("worker") is not None:
            issue("BATCH_EXECUTION_KIND_MISMATCH")
        for key in ("baseline", "legacy"):
            if code.get(key) != code_digest(paths[key]):
                issue("BATCH_CURRENT_VERSION_MISMATCH", key)
        # Read the literal configuration; importing the legacy backend would
        # mutate environment and risks loading recognition dependencies.
        tree = ast.parse(paths["legacy"].read_text(encoding="utf-8-sig"))
        cfg = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "CFG" for t in n.targets))
        if recognizer.get("configuration", {}).get("baseline") != cfg:
            issue("BATCH_CURRENT_VERSION_MISMATCH", "configuration")
    if recognizer.get("configuration", {}).get("single_asset_manifest_policy") != "context+asset+recognizer/0.1":
        issue("BATCH_RECOGNIZER_FINGERPRINT_MISMATCH", "manifest policy")
    try:
        def dependency(distribution, module):
            return {"version":importlib.metadata.version(distribution),
                    "package_entry_sha256":file_digest(Path(importlib.util.find_spec(module).origin))}
        expected_dependencies = {"Pillow":dependency("Pillow","PIL")}
        expected_models = []
        if kind != "SYNTHETIC_TEST":
            expected_dependencies.update(numpy=dependency("numpy","numpy"),
                opencv={"version":cv2.__version__,"package_entry_sha256":file_digest(Path(cv2.__file__))})
            if use_ocr:
                for distribution, module in (("rapidocr-onnxruntime","rapidocr_onnxruntime"),("onnxruntime","onnxruntime")):
                    expected_dependencies[module] = dependency(distribution,module)
                package = Path(importlib.util.find_spec("rapidocr_onnxruntime").origin).parent
                expected_models = [{"name":str(p.relative_to(package)).replace("\\","/"),"sha256":file_digest(p)}
                                   for p in sorted(package.rglob("*.onnx"))]
                if not expected_models:
                    issue("BATCH_CURRENT_VERSION_MISMATCH", "models absent")
        if recognizer.get("dependencies") != expected_dependencies or recognizer.get("model_files") != expected_models:
            issue("BATCH_CURRENT_VERSION_MISMATCH", "dependencies/models")
    except (OSError,ImportError,ValueError,TypeError,AttributeError) as exc:
        issue("BATCH_CURRENT_VERSION_MISMATCH", str(exc))
    worker_identity = recognizer.get("worker_identity")
    if kind == "SYNTHETIC_TEST":
        if (not isinstance(worker_identity,dict) or worker_identity.get("code_sha256") != code.get("worker")
                or worker_identity.get("cache_identity") != recognizer.get("configuration",{}).get("worker_cache_identity")
                or worker_identity.get("hash_method") not in {"python_source","python_code_object"}):
            issue("BATCH_EXECUTION_KIND_MISMATCH", "synthetic worker identity")
    elif worker_identity is not None:
        issue("BATCH_EXECUTION_KIND_MISMATCH", "unexpected injected worker")
    job_key = digest([digest(source), fingerprint])
    job_id = "batch-job-"+job_key[:24]
    if payload.get("job_key") != job_key or payload.get("job_id") != job_id:
        issue("BATCH_JOB_BINDING_MISMATCH")
    context = {k:v for k,v in source.items() if k not in {"assets", "artifact_id", "created_at"}}
    expected_keys = {a["asset_id"]: digest([context, a, fingerprint]) for a in assets}
    reported_items = payload.get("items", [])
    if [r.get("asset_id") for r in reported_items] != [a["asset_id"] for a in assets]:
        issue("BATCH_ITEM_SCOPE_MISMATCH")
    report_by_id = {item.get("asset_id"):item for item in reported_items}
    database = root/"batch.sqlite3"
    if not database.is_file():
        issue("BATCH_JOURNAL_MISSING")
        return finish()
    connection = None
    try:
        connection = sqlite3.connect(database.as_uri()+"?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        with connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("SQLite integrity check failed")
            job = connection.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            db_items = [dict(r) for r in connection.execute("SELECT * FROM items WHERE job_id=?", (job_id,))]
            attempts = [dict(r) for r in connection.execute("SELECT * FROM attempts WHERE job_id=? ORDER BY started_at,attempt_id", (job_id,))]
            all_attempts = [dict(r) for r in connection.execute("SELECT * FROM attempts")]
            all_jobs = {r["job_id"]:dict(r) for r in connection.execute("SELECT * FROM jobs")}
            all_events = [dict(r) for r in connection.execute("SELECT * FROM events")]
            events = [dict(r) for r in connection.execute("SELECT * FROM events WHERE job_id=? ORDER BY event_id", (job_id,))]
            cache = {r["item_key"]:dict(r) for r in connection.execute("SELECT * FROM cache_entries")}
        connection.close()
        if job is None:
            raise ValueError("declared job not recorded")
        job = dict(job)
        if (job["job_key"] != job_key or job["source_hash"] != digest(source)
                or job["recognizer_fingerprint"] != fingerprint
                or json.loads(job["source_json"]) != source or json.loads(job["recognizer_json"]) != recognizer
                or job["book_id"] != source["book_id"] or job["scope_id"] != source["scope_id"]):
            issue("BATCH_JOURNAL_JOB_MISMATCH")
        details = {event["event_id"]:json.loads(event["details_json"]) for event in events}
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError) as exc:
        issue("BATCH_JOURNAL_INVALID", str(exc))
        return finish()
    finally:
        if connection is not None:
            connection.close()
    if Counter(r["asset_id"] for r in db_items) != Counter(a["asset_id"] for a in assets):
        issue("BATCH_JOURNAL_ITEM_SCOPE_MISMATCH")
    if any(r["asset_id"] not in expected_keys or r["item_key"] != expected_keys.get(r["asset_id"]) for r in attempts):
        issue("BATCH_ATTEMPT_SOURCE_MISMATCH")
    attempt_ids = {a["attempt_id"] for a in attempts}
    if any((e["asset_id"] is not None and e["asset_id"] not in expected_keys)
           or (e["attempt_id"] is not None and e["attempt_id"] not in attempt_ids) for e in events):
        issue("BATCH_EVENT_OWNERSHIP_MISMATCH")
    run_events = [event for event in events if details[event["event_id"]].get("run_id") == report.get("run_id")]
    if (len([e for e in run_events if e["event_type"] == "RUN_STARTED"]) != 1
            or len([e for e in run_events if e["event_type"] == "RUN_FINISHED"]) != 1):
        issue("BATCH_RUN_EVENT_MISMATCH")
    else:
        started = next(e for e in run_events if e["event_type"] == "RUN_STARTED")
        ended = next(e for e in run_events if e["event_type"] == "RUN_FINISHED")
        start_detail, end_detail = details[started["event_id"]], details[ended["event_id"]]
        if (start_detail.get("declared_asset_ids") != [a["asset_id"] for a in assets]
                or started["event_id"] >= ended["event_id"] or end_detail.get("report_ref") != _ref(report)):
            issue("BATCH_RUN_EVENT_MISMATCH")
        budget = start_detail.get("max_items")
        if budget is not None and (type(budget) is not int or budget < 0
                or len([e for e in run_events if e["event_type"] == "ATTEMPT_STARTED"]) > budget):
            issue("BATCH_EXECUTION_BUDGET_MISMATCH")
        try:
            if _read_object(root,end_detail.get("report_artifact")) != report:
                issue("BATCH_REPORT_RECEIPT_MISMATCH")
        except (OSError,ValueError,TypeError,KeyError) as exc:
            issue("BATCH_REPORT_RECEIPT_MISMATCH", str(exc))
    pages, descriptors, completed = [], [], []
    db_by_id = {r["asset_id"]:r for r in db_items}
    all_region_ids = []
    for asset in assets:
        aid, item_key = asset["asset_id"], expected_keys[asset["asset_id"]]
        actual, item = db_by_id.get(aid), report_by_id.get(aid)
        if actual is None or item is None:
            continue
        if (actual["item_key"] != item_key or json.loads(actual["asset_json"]) != asset or item.get("item_key") != item_key):
            issue("BATCH_ITEM_SOURCE_MISMATCH", asset_id=aid)
        own_attempts = sorted([a for a in attempts if a["asset_id"] == aid], key=lambda a:a["attempt_number"])
        if ([a["attempt_number"] for a in own_attempts] != list(range(1,len(own_attempts)+1))
                or actual["attempt_count"] != len(own_attempts) or item.get("attempt_count") != len(own_attempts)):
            issue("BATCH_ATTEMPT_COUNT_MISMATCH", asset_id=aid)
        if any(a["state"] not in {"SUCCEEDED", "FAILED", "INTERRUPTED"} or not a["finished_at"] for a in own_attempts):
            issue("BATCH_ATTEMPT_NOT_TERMINAL", asset_id=aid)
        for attempt in own_attempts:
            related = [e for e in events if e["attempt_id"] == attempt["attempt_id"]]
            terminal_name = {"SUCCEEDED":"ATTEMPT_SUCCEEDED", "FAILED":"ATTEMPT_FAILED", "INTERRUPTED":"INTERRUPTED"}.get(attempt["state"])
            if (len([e for e in related if e["event_type"] == "ATTEMPT_STARTED"]) != 1
                    or len([e for e in related if e["event_type"] == terminal_name]) != 1):
                issue("BATCH_ATTEMPT_EVENT_MISMATCH", asset_id=aid)
            if any(e["asset_id"] != aid or e["job_id"] != job_id for e in related):
                issue("BATCH_ATTEMPT_EVENT_MISMATCH", asset_id=aid)
            for event in related:
                ed = details[event["event_id"]]
                if event["event_type"] == "ATTEMPT_STARTED" and (ed.get("item_key") != item_key or ed.get("attempt_number") != attempt["attempt_number"]):
                    issue("BATCH_ATTEMPT_EVENT_MISMATCH", asset_id=aid)
                if event["event_type"] == "ATTEMPT_SUCCEEDED" and ed.get("artifact") != json.loads(attempt["artifact_json"] or "null"):
                    issue("BATCH_ATTEMPT_ARTIFACT_MISMATCH", asset_id=aid)
            if attempt["state"] == "SUCCEEDED" and (not attempt["artifact_json"] or attempt["error"] is not None):
                issue("BATCH_ATTEMPT_ARTIFACT_MISMATCH", asset_id=aid)
            if attempt["state"] in {"FAILED", "INTERRUPTED"} and not attempt["error"]:
                issue("BATCH_ATTEMPT_FAILURE_UNRECORDED", asset_id=aid)
        invalidations = [e for e in events if e["asset_id"] == aid and e["event_type"] == "INVALIDATED"]
        if actual["invalidated_count"] != len(invalidations) or item.get("invalidated_count") != len(invalidations):
            issue("BATCH_INVALIDATION_COUNT_MISMATCH", asset_id=aid)
        hit = any(e["asset_id"] == aid and e["event_type"] == "CACHE_HIT" for e in run_events)
        if len([e for e in run_events if e["asset_id"] == aid and e["event_type"] == "CACHE_HIT"]) > 1:
            issue("BATCH_CACHE_EVENT_MISMATCH", asset_id=aid)
        if item.get("cache_hit") is not hit:
            issue("BATCH_CACHE_EVENT_MISMATCH", asset_id=aid)
        state = actual["state"]
        artifact = json.loads(actual["artifact_json"]) if actual["artifact_json"] else None
        if any(details[e["event_id"]].get("artifact") != artifact or details[e["event_id"]].get("item_key") != item_key
               for e in run_events if e["asset_id"] == aid and e["event_type"] == "CACHE_HIT"):
            issue("BATCH_CACHE_EVENT_MISMATCH", asset_id=aid)
        if item.get("state") != state or item.get("artifact") != artifact or item.get("last_error") != actual["last_error"]:
            issue("BATCH_REPORT_ITEM_JOURNAL_MISMATCH", asset_id=aid)
        if state not in {"DONE", "PENDING", "FAILED"}:
            issue("BATCH_ITEM_STATE_INVALID", asset_id=aid)
        if state != "DONE":
            if artifact is not None:
                issue("BATCH_INCOMPLETE_ITEM_HAS_ARTIFACT", asset_id=aid)
            if state == "FAILED" and (not own_attempts or own_attempts[-1]["state"] != "FAILED" or not actual["last_error"]):
                issue("BATCH_ATTEMPT_FAILURE_UNRECORDED", asset_id=aid)
            continue
        if not any(a["state"] == "SUCCEEDED" and a["item_key"] == item_key
                   and a["artifact_json"] and json.loads(a["artifact_json"]) == artifact for a in all_attempts):
            issue("BATCH_SUCCESS_PROVENANCE_MISSING", asset_id=aid)
        if item_key not in cache or json.loads(cache[item_key]["artifact_json"]) != artifact:
            issue("BATCH_CACHE_ARTIFACT_MISMATCH", asset_id=aid)
        try:
            retained = _read_object(root, artifact)
            sp = {**copy.deepcopy(context), "artifact_id":"batch-item-source-"+item_key[:24], "assets":[copy.deepcopy(asset)]}
            ip = retained["payload"]
            if (retained.get("schema_version") != "b-batch-item-trial/0.1" or retained.get("kind") != "BatchItemTrial"
                    or ip.get("item_key") != item_key or ip.get("asset") != asset or ip.get("source_manifest") != sp
                    or ip.get("source_ref") != {"artifact_id":sp["artifact_id"],"content_hash":digest(sp)}
                    or ip.get("recognizer") != recognizer or ip.get("execution_kind") != kind):
                issue("BATCH_ITEM_ARTIFACT_BINDING_MISMATCH", asset_id=aid)
            if (retained.get("revision") != 1 or retained.get("input_refs") != [{"artifact_id":sp["artifact_id"],"content_hash":digest(sp)}]
                    or any(retained.get(k) != source[k] for k in ("book_id","scope_id"))
                    or retained.get("producer",{}).get("code_sha256") != code.get("batch")):
                issue("BATCH_ITEM_ARTIFACT_BINDING_MISMATCH", asset_id=aid)
            origins = [a for a in all_attempts if a["attempt_id"] == ip.get("attempt_id")]
            if len(origins) != 1:
                issue("BATCH_SUCCESS_PROVENANCE_MISSING", asset_id=aid)
            else:
                origin_attempt = origins[0]
                origin_job = all_jobs.get(origin_attempt["job_id"],{})
                origin_source = json.loads(origin_job.get("source_json","{}"))
                origin_events = [e for e in all_events if e["attempt_id"] == origin_attempt["attempt_id"] and e["event_type"] == "ATTEMPT_SUCCEEDED"]
                if (origin_attempt["state"] != "SUCCEEDED" or origin_attempt["asset_id"] != aid or origin_attempt["item_key"] != item_key
                        or json.loads(origin_attempt["artifact_json"] or "null") != artifact
                        or {k:v for k,v in origin_source.items() if k not in {"assets","artifact_id","created_at"}} != context
                        or asset not in origin_source.get("assets",[])
                        or origin_job.get("recognizer_fingerprint") != fingerprint
                        or len(origin_events) != 1 or json.loads(origin_events[0]["details_json"]).get("artifact") != artifact):
                    issue("BATCH_SUCCESS_PROVENANCE_MISSING", asset_id=aid)
            if ip.get("decision") != "HOLD" or ip.get("verification_status") != "UNVERIFIED" or ip.get("platform_actions") != []:
                issue("BATCH_FALSE_VERIFICATION", asset_id=aid)
            result = ip["result"]
            for code_name in _page_integrity(result, asset, sp, kind, use_ocr):
                issue(code_name, asset_id=aid)
            if kind != "SYNTHETIC_TEST":
                expected_result_dependencies = {"numpy":recognizer["dependencies"]["numpy"]["version"],
                    "Pillow":recognizer["dependencies"]["Pillow"]["version"],
                    "opencv":recognizer["dependencies"]["opencv"]["version"]}
                if use_ocr:
                    expected_result_dependencies.update({"rapidocr-onnxruntime":recognizer["dependencies"]["rapidocr_onnxruntime"]["version"],
                        "onnxruntime":recognizer["dependencies"]["onnxruntime"]["version"]})
                pr = result.get("producer",{})
                if (pr.get("module") != "annotation.recognition.baseline" or pr.get("legacy_code_sha256") != code.get("legacy")
                        or pr.get("dependencies") != expected_result_dependencies
                        or pr.get("configuration") != recognizer.get("configuration",{}).get("baseline")):
                    issue("BATCH_PAGE_PRODUCER_MISMATCH",asset_id=aid)
            if len(result.get("payload", {}).get("pages", [])) == 1:
                page = result["payload"]["pages"][0]
                pages.append(page)
                all_region_ids.extend(r.get("region_id") for r in page.get("regions", []))
            descriptors.append({"asset_id":aid,"item_key":item_key,**artifact})
            completed.append(aid)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            issue("BATCH_ITEM_ARTIFACT_INVALID", str(exc), aid)
    if len(all_region_ids) != len(set(all_region_ids)) or any(not isinstance(v,str) or not v for v in all_region_ids):
        issue("BATCH_REGION_ID_REUSED")
    counts = Counter(item.get("state") for item in reported_items)
    expected_counts = {"declared":len(assets), "done":counts["DONE"], "pending":counts["PENDING"], "failed":counts["FAILED"],
                       "invalidated":sum(i.get("invalidated_count",0) for i in reported_items),
                       "cache_hits":sum(i.get("cache_hit") is True for i in reported_items)}
    if payload.get("counts") != expected_counts:
        issue("BATCH_COUNTS_MISMATCH")
    complete = len(completed) == len(assets) and len(db_items) == len(assets) and all(i["state"] == "DONE" for i in db_items)
    if payload.get("batch_complete") is not complete:
        issue("BATCH_FALSE_COMPLETENESS")
    expected_status = "COMPLETE" if complete else "FAILED" if counts["FAILED"] else "PARTIAL"
    if job["status"] != expected_status:
        issue("BATCH_JOB_STATUS_MISMATCH")
    summary.update(completed_asset_count=len(completed), execution_kind=kind, batch_complete=complete,
                   attempt_count=len(attempts), counts=expected_counts)
    bundle_descriptor = payload.get("bundle")
    journal_bundle = json.loads(job["bundle_json"]) if job["bundle_json"] else None
    if bundle_descriptor != journal_bundle:
        issue("BATCH_BUNDLE_JOURNAL_MISMATCH")
    if not complete:
        if bundle_descriptor is not None:
            issue("BATCH_PREMATURE_BUNDLE")
    else:
        try:
            bundle = _read_object(root, bundle_descriptor)
            bp = bundle["payload"]
            if (bundle.get("schema_version") != "b-evidence-trial/0.1" or bundle.get("kind") != "EvidenceBundleTrial"
                    or bp.get("pages") != pages or bp.get("quality_decision") != "NOT_EVALUATED"
                    or any(bundle.get(k) != source[k] for k in ("book_id", "scope_id"))):
                issue("BATCH_MERGED_PAGE_MISMATCH")
            if (bundle.get("revision") != 1 or bundle.get("input_refs") != [source_ref]
                    or bundle.get("producer",{}).get("code_sha256") != code.get("batch")
                    or bundle.get("producer",{}).get("execution_kind") != kind
                    or bundle.get("producer",{}).get("ocr_enabled") is not use_ocr
                    or bundle.get("producer",{}).get("recognizer_fingerprint") != fingerprint):
                issue("BATCH_BUNDLE_BINDING_MISMATCH")
            if (bp.get("transcription_verified",False) is not False or bp.get("business_acceptance",False) is not False
                    or bp.get("platform_actions",[]) != []):
                issue("BATCH_FALSE_VERIFICATION")
            binding = {"job_id":job_id,"source_ref":source_ref,"source_manifest":source,"per_page_refs":descriptors,
                       "recognizer":recognizer,"decision":"HOLD","transcription_verified":False,
                       "business_acceptance":False,"platform_actions":[]}
            if bp.get("batch_binding") != binding:
                issue("BATCH_BUNDLE_BINDING_MISMATCH")
        except (OSError,ValueError,TypeError,KeyError) as exc:
            issue("BATCH_BUNDLE_INVALID", str(exc))
    return finish()


def audit_batch(source_path, workdir, report):
    """Audit without writing the journal; malformed persisted data fails closed."""
    try:
        return _audit_batch(source_path,workdir,report)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,sqlite3.Error) as exc:
        payload = {"accepted":False,"decision":"HOLD",
                   "issues":[{"code":"BATCH_PERSISTED_DATA_INVALID","severity":"ERROR",
                              "detail":type(exc).__name__+": "+str(exc)}],
                   "summary":{},"business_acceptance":False,
                   "transcription_verified":False,"platform_actions":[]}
        inputs = [_ref(report)] if isinstance(report,dict) else []
        producer = {"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__))}
        return {"schema_version":SCHEMA,"kind":"BatchCheckTrial",
                "artifact_id":"batch-check-"+digest([inputs,payload,producer])[:24],"revision":1,
                "run_id":report.get("run_id") if isinstance(report,dict) else None,
                "book_id":report.get("book_id") if isinstance(report,dict) else None,
                "scope_id":report.get("scope_id") if isinstance(report,dict) else None,
                "input_refs":inputs,"producer":producer,"content_hash":digest(payload),"payload":payload}
