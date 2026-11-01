"""Versioned local per-asset recognition batches, with durable interruption recovery.

This is an offline B-side stage runner, not a platform runtime or a whole-book
acceptance check. A declared scope never shrinks with ``max_items``. SQLite
records intent before execution; immutable objects are published before a DONE
checkpoint. A killed process leaves a RUNNING attempt which the next exclusive
runner records as INTERRUPTED. Source files and cached outputs are revalidated.

Injected workers have the same signature as ``baseline.recognize``. They are
always SYNTHETIC_TEST; external parameters must be declared in their JSON-valued
``cache_identity`` attribute. Mutable test counters are deliberately not hashed.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import marshal
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
from uuid import uuid4

from . import baseline
from .baseline import code_digest, digest, file_digest, load_source, valid_bbox

REPORT_SCHEMA = "b-batch-report-trial/0.1"
ITEM_SCHEMA = "b-batch-item-trial/0.1"
POLICY = "context+asset+recognizer/0.1"
TABLES = """
CREATE TABLE IF NOT EXISTS jobs (
 job_id TEXT PRIMARY KEY, job_key TEXT UNIQUE NOT NULL,
 book_id TEXT NOT NULL, scope_id TEXT NOT NULL, source_hash TEXT NOT NULL,
 recognizer_fingerprint TEXT NOT NULL, source_json TEXT NOT NULL,
 recognizer_json TEXT NOT NULL, status TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, bundle_json TEXT);
CREATE TABLE IF NOT EXISTS items (
 job_id TEXT NOT NULL, asset_id TEXT NOT NULL, item_key TEXT NOT NULL,
 asset_json TEXT NOT NULL, state TEXT NOT NULL, artifact_json TEXT,
 last_error TEXT, attempt_count INTEGER NOT NULL DEFAULT 0,
 invalidated_count INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY (job_id,asset_id), FOREIGN KEY(job_id) REFERENCES jobs(job_id));
CREATE TABLE IF NOT EXISTS attempts (
 attempt_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, asset_id TEXT NOT NULL,
 item_key TEXT NOT NULL, attempt_number INTEGER NOT NULL, state TEXT NOT NULL,
 started_at TEXT NOT NULL, finished_at TEXT, error TEXT, artifact_json TEXT,
 FOREIGN KEY(job_id,asset_id) REFERENCES items(job_id,asset_id));
CREATE TABLE IF NOT EXISTS events (
 event_id INTEGER PRIMARY KEY, job_id TEXT NOT NULL, asset_id TEXT,
 attempt_id TEXT, event_type TEXT NOT NULL, details_json TEXT NOT NULL,
 created_at TEXT NOT NULL, FOREIGN KEY(job_id) REFERENCES jobs(job_id));
CREATE TABLE IF NOT EXISTS cache_entries (
 item_key TEXT PRIMARY KEY, artifact_json TEXT NOT NULL, created_at TEXT NOT NULL);
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _ref(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def _source_ref(source):
    return {"artifact_id": source["artifact_id"], "content_hash": digest(source)}


def _context(source):
    return {k: copy.deepcopy(v) for k, v in source.items() if k not in ("assets", "artifact_id", "created_at")}


def _item_key(source, asset, recognizer):
    return digest([_context(source), asset, recognizer["fingerprint"]])


def _single_source(source, asset, recognizer):
    key = _item_key(source, asset, recognizer)
    return {**_context(source), "artifact_id": "batch-item-source-"+key[:24], "assets": [copy.deepcopy(asset)]}


def _dependency(distribution, module):
    return {"version": importlib.metadata.version(distribution),
            "package_entry_sha256": file_digest(Path(importlib.util.find_spec(module).origin))}


def _worker_identity(worker):
    target = worker if inspect.isfunction(worker) or inspect.ismethod(worker) else type(worker).__call__
    try:
        code = inspect.getsource(target).replace("\r\n", "\n").encode("utf-8")
        method = "python_source"
    except (OSError, TypeError):
        if not hasattr(target, "__code__"):
            raise ValueError("an injected worker needs inspectable Python code")
        code, method = marshal.dumps(target.__code__), "python_code_object"
    config = copy.deepcopy(getattr(worker, "cache_identity", None))
    _json(config)
    return {"module": getattr(target, "__module__", None),
            "qualname": getattr(target, "__qualname__", type(worker).__qualname__),
            "code_sha256": hashlib.sha256(code).hexdigest(), "hash_method": method,
            "cache_identity": config}


def _recognizer(use_ocr, worker):
    code = {"batch": code_digest(Path(__file__)), "baseline": None, "legacy": None, "worker": None}
    configuration = {"baseline": None, "worker_cache_identity": None, "single_asset_manifest_policy": POLICY}
    dependencies = {"Pillow": _dependency("Pillow", "PIL")}
    models, identity = [], None
    if worker is None:
        backend = baseline.legacy_backend()
        code.update(baseline=code_digest(Path(baseline.__file__)), legacy=code_digest(baseline.LEGACY_PATH))
        configuration["baseline"] = copy.deepcopy(backend.CFG)
        dependencies.update(numpy=_dependency("numpy", "numpy"),
                            opencv={"version": backend.cv2.__version__,
                                    "package_entry_sha256": file_digest(Path(backend.cv2.__file__))})
        if use_ocr:
            for distribution, module in (("rapidocr-onnxruntime", "rapidocr_onnxruntime"), ("onnxruntime", "onnxruntime")):
                dependencies[module] = _dependency(distribution, module)
            package = Path(importlib.util.find_spec("rapidocr_onnxruntime").origin).parent
            models = [{"name": str(p.relative_to(package)).replace("\\", "/"), "sha256": file_digest(p)}
                      for p in sorted(package.rglob("*.onnx"))]
            if not models:
                raise ValueError("OCR model receipts unavailable")
        kind = "BASELINE_CPU_OCR" if use_ocr else "BASELINE_GEOMETRY"
    else:
        identity = _worker_identity(worker)
        code["worker"] = identity["code_sha256"]
        configuration["worker_cache_identity"] = identity["cache_identity"]
        kind = "SYNTHETIC_TEST"
    receipt = {"execution_kind": kind, "use_ocr": use_ocr, "code": code,
               "configuration": configuration, "dependencies": dependencies,
               "model_files": models, "worker_identity": identity}
    return {**receipt, "fingerprint": digest(receipt)}


@contextmanager
def _exclusive(workdir):
    """OS advisory lock, automatically released even when the process is killed."""
    path = workdir / "batch.lock"
    stream = path.open("a+b")
    stream.seek(0, os.SEEK_END)
    if stream.tell() == 0:
        stream.write(b"0")
        stream.flush()
    stream.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            try: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc: raise RuntimeError("another batch runner holds this workdir") from exc
        else:
            import fcntl
            try: fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc: raise RuntimeError("another batch runner holds this workdir") from exc
        yield
    finally:
        # Closing releases the OS lock, including after an exception. No stale
        # lock-file deletion or PID guessing can interfere with another runner.
        stream.close()


def _event(db, job_id, run_id, event_type, *, asset_id=None, attempt_id=None, **details):
    db.execute("INSERT INTO events(job_id,asset_id,attempt_id,event_type,details_json,created_at) VALUES(?,?,?,?,?,?)",
               (job_id, asset_id, attempt_id, event_type, _json({"run_id": run_id, **details}), _now()))


def _put_object(workdir, value):
    """Publish without replacement; existing bytes at a content address are immutable."""
    data = _json(value).encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    directory = workdir / "objects"
    directory.mkdir(exist_ok=True)
    target = directory / (sha+".json")
    if target.exists():
        if target.read_bytes() != data:
            raise ValueError("corrupt immutable object already occupies content address")
    else:
        temporary = directory / (".pending-"+uuid4().hex)
        try:
            with temporary.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            # Hard-link creation is atomic and cannot overwrite another object.
            # Both files are on the same filesystem inside this work directory.
            try: os.link(temporary, target)
            except FileExistsError:
                if target.read_bytes() != data:
                    raise ValueError("content-address collision or corrupted object")
        finally:
            temporary.unlink(missing_ok=True)
    return {"path": "objects/"+target.name, "sha256": sha, "artifact_ref": _ref(value)}


def _read_object(workdir, descriptor):
    relative = descriptor["path"]
    if (not isinstance(relative, str) or "\\" in relative or PurePosixPath(relative).is_absolute()
            or ".." in PurePosixPath(relative).parts or relative != "objects/"+descriptor["sha256"]+".json"):
        raise ValueError("invalid immutable object path")
    path = (workdir / relative).resolve()
    if not path.is_relative_to(workdir.resolve()) or file_digest(path) != descriptor["sha256"]:
        raise ValueError("cached artifact bytes changed or missing")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("content_hash") != digest(value.get("payload")) or _ref(value) != descriptor["artifact_ref"]:
        raise ValueError("cached artifact payload or reference changed")
    return value


def _validate_result(result, single, asset, recognizer):
    if (not isinstance(result, dict) or result.get("schema_version") != baseline.EVIDENCE_SCHEMA
            or result.get("kind") != "EvidenceBundleTrial" or result.get("revision") != 1
            or result.get("content_hash") != digest(result.get("payload"))
            or result.get("book_id") != single["book_id"] or result.get("scope_id") != single["scope_id"]
            or result.get("input_refs") != [_source_ref(single)]
            or result.get("producer", {}).get("ocr_enabled") is not recognizer["use_ocr"]):
        raise ValueError("worker result is stale, unsupported, wrong-mode or from another source")
    if recognizer["execution_kind"] != "SYNTHETIC_TEST":
        expected_dependencies = {"numpy": recognizer["dependencies"]["numpy"]["version"],
                                 "Pillow": recognizer["dependencies"]["Pillow"]["version"],
                                 "opencv": recognizer["dependencies"]["opencv"]["version"]}
        if recognizer["use_ocr"]:
            expected_dependencies.update({"rapidocr-onnxruntime": recognizer["dependencies"]["rapidocr_onnxruntime"]["version"],
                                          "onnxruntime": recognizer["dependencies"]["onnxruntime"]["version"]})
        producer = result["producer"]
        if (producer.get("module") != "annotation.recognition.baseline"
                or producer.get("legacy_code_sha256") != recognizer["code"]["legacy"]
                or producer.get("configuration") != recognizer["configuration"]["baseline"]
                or producer.get("dependencies") != expected_dependencies):
            raise ValueError("default worker producer code, configuration or dependencies changed")
    pages = result["payload"].get("pages")
    if (not isinstance(pages, list) or len(pages) != 1 or pages[0].get("asset_id") != asset["asset_id"]
            or pages[0].get("source") != asset):
        raise ValueError("worker must return exactly the declared single asset")
    page = pages[0]
    width, height = asset["width"], asset["height"]
    region_ids, crop_ids = set(), set()
    for crop in page.get("crop_transforms", []):
        if (crop.get("asset_id") != asset["asset_id"] or crop.get("crop_id") in crop_ids
                or not valid_bbox(crop.get("original_bbox", []), width, height)):
            raise ValueError("worker crop provenance invalid")
        crop_ids.add(crop["crop_id"])
        x, y = crop["original_bbox"][:2]
        if crop.get("crop_to_original") != [[1, 0, x], [0, 1, y], [0, 0, 1]]:
            raise ValueError("worker crop transform invalid")
    for region in page.get("regions", []):
        if (not region.get("region_id") or region["region_id"] in region_ids
                or region.get("asset_id") != asset["asset_id"]
                or not valid_bbox(region.get("bbox", []), width, height)
                or region.get("crop_id") not in crop_ids
                or region.get("verification_status") != "UNVERIFIED"
                or region.get("text_hint_is_final_transcription") is not False):
            raise ValueError("worker region geometry, ownership or verification invalid")
        region_ids.add(region["region_id"])
    for line in page.get("ocr_lines", []):
        if not valid_bbox(line.get("bbox", []), width, height) or line.get("crop_id") not in crop_ids:
            raise ValueError("worker OCR geometry or crop reference invalid")
    if (result["payload"].get("quality_decision") != "NOT_EVALUATED"
            or result["payload"].get("transcription_verified", False) is not False
            or result["payload"].get("business_acceptance", False) is not False
            or result["payload"].get("platform_actions", []) != []):
        raise ValueError("batch recognition cannot claim verification or platform actions")
    return page


def _validate_cached(workdir, descriptor, source, asset, recognizer):
    value = _read_object(workdir, descriptor)
    single = _single_source(source, asset, recognizer)
    payload = value["payload"]
    if (value.get("schema_version") != ITEM_SCHEMA
            or value.get("kind") != "BatchItemTrial" or value.get("revision") != 1
            or value.get("artifact_id") != "batch-item-"+digest(payload)[:24]
            or value.get("book_id") != source["book_id"] or value.get("scope_id") != source["scope_id"]
            or value.get("input_refs") != [_source_ref(single)]
            or payload.get("item_key") != _item_key(source, asset, recognizer)
            or payload.get("source_manifest") != single or payload.get("source_ref") != _source_ref(single)
            or payload.get("asset") != asset or payload.get("recognizer") != recognizer
            or payload.get("execution_kind") != recognizer["execution_kind"]
            or payload.get("decision") != "HOLD" or payload.get("verification_status") != "UNVERIFIED"
            or payload.get("platform_actions") != []):
        raise ValueError("cached single-asset source or recognizer binding changed")
    if value.get("producer") != {"module": __name__, "version": "0.1.0", "code_sha256": recognizer["code"]["batch"]}:
        raise ValueError("cached single-asset producer changed")
    _validate_result(payload["result"], single, asset, recognizer)
    return value


def _validate_origin(db, descriptor, value):
    """A reusable object must have a real successful origin, including cross-job hits."""
    payload = value["payload"]
    attempt = db.execute("SELECT * FROM attempts WHERE attempt_id=?", (payload.get("attempt_id"),)).fetchone()
    if (attempt is None or attempt["state"] != "SUCCEEDED" or not attempt["finished_at"]
            or attempt["asset_id"] != payload["asset"]["asset_id"] or attempt["item_key"] != payload["item_key"]
            or not attempt["artifact_json"] or json.loads(attempt["artifact_json"]) != descriptor):
        raise ValueError("cached artifact has no matching successful origin attempt")
    job = db.execute("SELECT * FROM jobs WHERE job_id=?", (attempt["job_id"],)).fetchone()
    if (job is None or job["book_id"] != value["book_id"] or job["scope_id"] != value["scope_id"]
            or json.loads(job["recognizer_json"]) != payload["recognizer"]
            or _single_source(json.loads(job["source_json"]), payload["asset"], payload["recognizer"]) != payload["source_manifest"]):
        raise ValueError("cached origin belongs to another source scope or recognizer")
    events = db.execute("SELECT * FROM events WHERE attempt_id=? AND job_id=? AND asset_id=? ORDER BY event_id",
                        (attempt["attempt_id"], attempt["job_id"], attempt["asset_id"])).fetchall()
    starts = [e for e in events if e["event_type"] == "ATTEMPT_STARTED"]
    ends = [e for e in events if e["event_type"] == "ATTEMPT_SUCCEEDED"]
    if (len(starts) != 1 or len(ends) != 1 or starts[0]["event_id"] >= ends[0]["event_id"]
            or json.loads(starts[0]["details_json"]).get("item_key") != payload["item_key"]
            or json.loads(ends[0]["details_json"]).get("artifact") != descriptor):
        raise ValueError("cached artifact lacks durable start/success event receipts")


def _item_artifact(source, asset, recognizer, result, attempt_id):
    single = _single_source(source, asset, recognizer)
    payload = {"item_key": _item_key(source, asset, recognizer), "source_manifest": single,
               "source_ref": _source_ref(single), "asset": copy.deepcopy(asset),
               "recognizer": copy.deepcopy(recognizer), "execution_kind": recognizer["execution_kind"],
               "result": copy.deepcopy(result), "attempt_id": attempt_id,
               "decision": "HOLD", "verification_status": "UNVERIFIED", "platform_actions": []}
    return {"schema_version": ITEM_SCHEMA, "kind": "BatchItemTrial",
            "artifact_id": "batch-item-"+digest(payload)[:24], "revision": 1,
            "book_id": source["book_id"], "scope_id": source["scope_id"],
            "input_refs": [_source_ref(single)], "created_at": _now(),
            "producer": {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__))},
            "content_hash": digest(payload), "payload": payload}


def _bundle(source, recognizer, job_id, items, objects):
    refs = [{"asset_id": item["asset_id"], "item_key": item["item_key"], **item["artifact"]} for item in items]
    payload = {"pages": [copy.deepcopy(obj["payload"]["result"]["payload"]["pages"][0]) for obj in objects],
               "quality_decision": "NOT_EVALUATED",
               "batch_binding": {"job_id": job_id, "source_ref": _source_ref(source),
                                 "source_manifest": copy.deepcopy(source), "per_page_refs": refs,
                                 "recognizer": copy.deepcopy(recognizer), "decision": "HOLD",
                                 "transcription_verified": False, "business_acceptance": False,
                                 "platform_actions": []},
               "limitations": ["This is B's provisional offline evidence, not A's platform runtime.",
                               "Successful stage execution is not transcription or business acceptance.",
                               "Declared asset completion does not establish a complete 214-page book."]}
    return {"schema_version": baseline.EVIDENCE_SCHEMA, "kind": "EvidenceBundleTrial",
            "artifact_id": "batch-evidence-"+digest(payload)[:24], "revision": 1,
            "book_id": source["book_id"], "scope_id": source["scope_id"],
            "input_refs": [_source_ref(source)], "producer": {"module": __name__, "version": "0.1.0",
                "code_sha256": code_digest(Path(__file__)), "ocr_enabled": recognizer["use_ocr"],
                "execution_kind": recognizer["execution_kind"], "recognizer_fingerprint": recognizer["fingerprint"]},
            "created_at": _now(), "content_hash": digest(payload), "payload": payload}


def run_batch(source_path, workdir, *, use_ocr=False, max_items=None, worker=None):
    """Run/resume an entire declared source scope, at most ``max_items`` attempts.

    All original files are checked before cache lookup or worker execution, even
    when no work is budgeted. DONE means the stage emitted source-bound evidence,
    never that its mathematical content or coverage has been accepted. Failures
    are durable and retried on a later call. Cache hits do not consume the budget.
    """
    if type(use_ocr) is not bool or (max_items is not None and (type(max_items) is not int or max_items < 0)):
        raise ValueError("use_ocr must be boolean; max_items must be a nonnegative integer or None")
    source_path, workdir = Path(source_path), Path(workdir)
    source, inputs = load_source(source_path)
    recognizer = _recognizer(use_ocr, worker)
    source_hash = digest(source)
    job_key = digest([source_hash, recognizer["fingerprint"]])
    job_id, run_id = "batch-job-"+job_key[:24], "batch-run-"+uuid4().hex
    workdir.mkdir(parents=True, exist_ok=True)
    with _exclusive(workdir):
        db = sqlite3.connect(workdir / "batch.sqlite3")
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.executescript(TABLES)
        try:
            with db:
                existing = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
                if existing is None:
                    prior = db.execute("SELECT job_id FROM jobs WHERE book_id=? AND scope_id=? ORDER BY updated_at DESC LIMIT 1",
                                       (source["book_id"], source["scope_id"])).fetchone()
                    old = {r["asset_id"]: r["item_key"] for r in db.execute("SELECT asset_id,item_key FROM items WHERE job_id=?", (prior[0],))} if prior else {}
                    db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL)",
                               (job_id, job_key, source["book_id"], source["scope_id"], source_hash, recognizer["fingerprint"],
                                _json(source), _json(recognizer), "RUNNING", _now(), _now()))
                    _event(db, job_id, run_id, "JOB_CREATED", source_ref=_source_ref(source), recognizer_fingerprint=recognizer["fingerprint"])
                    for asset, _ in inputs:
                        key = _item_key(source, asset, recognizer)
                        invalidated = int(asset["asset_id"] in old and old[asset["asset_id"]] != key)
                        db.execute("INSERT INTO items VALUES(?,?,?,?,?,NULL,NULL,0,?)",
                                   (job_id, asset["asset_id"], key, _json(asset), "PENDING", invalidated))
                        if invalidated:
                            _event(db, job_id, run_id, "INVALIDATED", asset_id=asset["asset_id"],
                                   reason="INPUT_OR_RECOGNIZER_CHANGED", previous_item_key=old[asset["asset_id"]], item_key=key)
                elif (existing["job_key"] != job_key or existing["source_json"] != _json(source)
                      or existing["recognizer_json"] != _json(recognizer)):
                    raise ValueError("persisted job identity changed")
                declared = {asset["asset_id"]: asset for asset, _ in inputs}
                rows = db.execute("SELECT * FROM items WHERE job_id=?", (job_id,)).fetchall()
                if (len(rows) != len(inputs) or any(r["asset_id"] not in declared
                        or r["asset_json"] != _json(declared[r["asset_id"]])
                        or r["item_key"] != _item_key(source, declared[r["asset_id"]], recognizer) for r in rows)):
                    raise ValueError("persisted asset set or item identity changed")
                for row in rows:
                    if row["state"] == "RUNNING":
                        attempts = db.execute("SELECT attempt_id FROM attempts WHERE job_id=? AND asset_id=? AND state='RUNNING'",
                                              (job_id, row["asset_id"])).fetchall()
                        for attempt in attempts:
                            db.execute("UPDATE attempts SET state='INTERRUPTED',finished_at=?,error=? WHERE attempt_id=?",
                                       (_now(), "Previous process ended before durable success", attempt[0]))
                            _event(db, job_id, run_id, "INTERRUPTED", asset_id=row["asset_id"], attempt_id=attempt[0],
                                   reason="RUNNING_WITHOUT_ACTIVE_EXCLUSIVE_RUNNER")
                        db.execute("UPDATE items SET state='PENDING',last_error=? WHERE job_id=? AND asset_id=?",
                                   ("Previous process interrupted", job_id, row["asset_id"]))
                    elif row["state"] not in ("DONE", "PENDING", "FAILED"):
                        raise ValueError("unknown persisted item state")
                db.execute("UPDATE jobs SET status='RUNNING',updated_at=? WHERE job_id=?", (_now(), job_id))
                _event(db, job_id, run_id, "RUN_STARTED", max_items=max_items, declared_asset_ids=[a["asset_id"] for a, _ in inputs])

            executed, cache_hits = 0, set()
            for asset, original_path in inputs:
                aid = asset["asset_id"]
                row = db.execute("SELECT * FROM items WHERE job_id=? AND asset_id=?", (job_id, aid)).fetchone()
                cached = db.execute("SELECT artifact_json FROM cache_entries WHERE item_key=?", (row["item_key"],)).fetchone()
                candidate = json.loads(row["artifact_json"]) if row["state"] == "DONE" and row["artifact_json"] else (json.loads(cached[0]) if cached else None)
                if candidate is not None:
                    try:
                        cached_object = _validate_cached(workdir, candidate, source, asset, recognizer)
                        _validate_origin(db, candidate, cached_object)
                        if file_digest(original_path) != asset["sha256"]:
                            raise ValueError("original source changed during cache validation")
                    except (ValueError, OSError, KeyError, TypeError) as exc:
                        with db:
                            db.execute("UPDATE items SET state='PENDING',artifact_json=NULL,last_error=?,invalidated_count=invalidated_count+1 WHERE job_id=? AND asset_id=?",
                                       (str(exc), job_id, aid))
                            db.execute("DELETE FROM cache_entries WHERE item_key=?", (row["item_key"],))
                            _event(db, job_id, run_id, "INVALIDATED", asset_id=aid, reason="CACHE_INVALID", error=str(exc), previous_artifact=candidate)
                    else:
                        with db:
                            db.execute("UPDATE items SET state='DONE',artifact_json=?,last_error=NULL WHERE job_id=? AND asset_id=?", (_json(candidate), job_id, aid))
                            db.execute("INSERT INTO cache_entries VALUES(?,?,?) ON CONFLICT(item_key) DO UPDATE SET artifact_json=excluded.artifact_json,created_at=excluded.created_at",
                                       (row["item_key"], _json(candidate), _now()))
                            _event(db, job_id, run_id, "CACHE_HIT", asset_id=aid, artifact=candidate, item_key=row["item_key"])
                        cache_hits.add(aid)
                        continue
                elif row["state"] == "DONE":
                    with db:
                        db.execute("UPDATE items SET state='PENDING',artifact_json=NULL,last_error=?,invalidated_count=invalidated_count+1 WHERE job_id=? AND asset_id=?",
                                   ("Missing durable artifact reference", job_id, aid))
                        _event(db, job_id, run_id, "INVALIDATED", asset_id=aid, reason="CACHE_MISSING")
                if max_items is not None and executed >= max_items:
                    continue
                executed += 1
                attempt_id = "batch-attempt-"+uuid4().hex
                with db:
                    count = db.execute("SELECT attempt_count FROM items WHERE job_id=? AND asset_id=?", (job_id, aid)).fetchone()[0]+1
                    db.execute("UPDATE items SET state='RUNNING',attempt_count=?,last_error=NULL WHERE job_id=? AND asset_id=?", (count, job_id, aid))
                    db.execute("INSERT INTO attempts VALUES(?,?,?,?,?,'RUNNING',?,NULL,NULL,NULL)",
                               (attempt_id, job_id, aid, row["item_key"], count, _now()))
                    _event(db, job_id, run_id, "ATTEMPT_STARTED", asset_id=aid, attempt_id=attempt_id, item_key=row["item_key"], attempt_number=count)
                try:
                    staging = workdir / "staging"
                    staging.mkdir(exist_ok=True)
                    with tempfile.TemporaryDirectory(prefix="attempt-", dir=staging) as directory:
                        directory = Path(directory)
                        copied = directory.joinpath(*PurePosixPath(asset["path"]).parts)
                        copied.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(original_path, copied)
                        if file_digest(copied) != asset["sha256"]:
                            raise ValueError("source changed before worker execution")
                        single = _single_source(source, asset, recognizer)
                        manifest = directory / "source.json"
                        # An asset named source.json is a permitted manifest path;
                        # choose a collision-free input manifest rather than erase it.
                        if manifest.exists(): manifest = directory / ("manifest-"+uuid4().hex+".json")
                        manifest.write_text(_json(single), encoding="utf-8")
                        load_source(manifest)
                        outcome = (worker or baseline.recognize)(manifest, use_ocr=use_ocr)
                        result = outcome[0] if isinstance(outcome, tuple) else outcome
                        _validate_result(result, single, asset, recognizer)
                        if file_digest(original_path) != asset["sha256"] or file_digest(copied) != asset["sha256"]:
                            raise ValueError("source changed during worker execution")
                    artifact = _item_artifact(source, asset, recognizer, result, attempt_id)
                    descriptor = _put_object(workdir, artifact)
                    with db:
                        db.execute("UPDATE attempts SET state='SUCCEEDED',finished_at=?,artifact_json=? WHERE attempt_id=?", (_now(), _json(descriptor), attempt_id))
                        db.execute("UPDATE items SET state='DONE',artifact_json=?,last_error=NULL WHERE job_id=? AND asset_id=?", (_json(descriptor), job_id, aid))
                        db.execute("INSERT INTO cache_entries VALUES(?,?,?) ON CONFLICT(item_key) DO UPDATE SET artifact_json=excluded.artifact_json,created_at=excluded.created_at",
                                   (row["item_key"], _json(descriptor), _now()))
                        _event(db, job_id, run_id, "ATTEMPT_SUCCEEDED", asset_id=aid, attempt_id=attempt_id, artifact=descriptor)
                except Exception as exc:
                    with db:
                        db.execute("UPDATE attempts SET state='FAILED',finished_at=?,error=? WHERE attempt_id=?", (_now(), str(exc), attempt_id))
                        db.execute("UPDATE items SET state='FAILED',artifact_json=NULL,last_error=? WHERE job_id=? AND asset_id=?", (str(exc), job_id, aid))
                        _event(db, job_id, run_id, "ATTEMPT_FAILED", asset_id=aid, attempt_id=attempt_id, error=str(exc), error_type=type(exc).__name__)

            # Repeat the entire declared-source check, so a changed later asset
            # cannot leave this invocation claiming a current successful scope.
            final_source, _ = load_source(source_path)
            if final_source != source:
                raise ValueError("source manifest changed during batch")
            items, objects = [], []
            for asset, _ in inputs:
                row = db.execute("SELECT * FROM items WHERE job_id=? AND asset_id=?", (job_id, asset["asset_id"])).fetchone()
                descriptor = json.loads(row["artifact_json"]) if row["artifact_json"] else None
                if row["state"] == "DONE":
                    cached_object = _validate_cached(workdir, descriptor, source, asset, recognizer)
                    _validate_origin(db, descriptor, cached_object)
                    objects.append(cached_object)
                items.append({"asset_id": row["asset_id"], "item_key": row["item_key"], "state": row["state"],
                              "artifact": descriptor, "attempt_count": row["attempt_count"],
                              "invalidated_count": row["invalidated_count"], "last_error": row["last_error"],
                              "cache_hit": row["asset_id"] in cache_hits})
            counts = {"declared": len(inputs), "done": sum(i["state"] == "DONE" for i in items),
                      "pending": sum(i["state"] == "PENDING" for i in items), "failed": sum(i["state"] == "FAILED" for i in items),
                      "invalidated": sum(i["invalidated_count"] for i in items), "cache_hits": len(cache_hits)}
            complete = counts["done"] == len(inputs)
            bundle = None
            if complete:
                previous = db.execute("SELECT bundle_json FROM jobs WHERE job_id=?", (job_id,)).fetchone()[0]
                desired = _bundle(source, recognizer, job_id, items, objects)
                if previous:
                    try:
                        descriptor = json.loads(previous)
                        saved = _read_object(workdir, descriptor)
                        if (saved["payload"] != desired["payload"] or any(saved.get(key) != desired.get(key)
                                for key in ("schema_version", "kind", "artifact_id", "revision", "book_id", "scope_id", "input_refs", "producer"))):
                            raise ValueError("merged bundle binding changed")
                        bundle = descriptor
                    except (ValueError, OSError, KeyError, TypeError): pass
                if bundle is None:
                    bundle = _put_object(workdir, desired)
                    with db: _event(db, job_id, run_id, "BUNDLE_CREATED", artifact=bundle)
            payload = {"job_id": job_id, "job_key": job_key, "source_ref": _source_ref(source),
                       "source_manifest": source, "recognizer": recognizer,
                       "declared_asset_ids": [asset["asset_id"] for asset, _ in inputs], "items": items,
                       "counts": counts, "batch_complete": complete, "bundle": bundle,
                       "decision": "HOLD", "transcription_verified": False, "business_acceptance": False,
                       "platform_actions": [],
                       "limitations": ["DONE means successful local stage execution, not correct OCR or accepted annotations.",
                                       "max_items bounds execution and never narrows the declared scope.",
                                       "This declared asset set does not establish whole-book or 214-page acceptance."]}
            producer = {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__))}
            report = {"schema_version": REPORT_SCHEMA, "kind": "BatchReportTrial",
                      "artifact_id": "batch-report-"+digest([[_source_ref(source)], producer, payload, run_id])[:24],
                      "revision": 1, "run_id": run_id, "book_id": source["book_id"], "scope_id": source["scope_id"],
                      "input_refs": [_source_ref(source)], "producer": producer, "created_at": _now(),
                      "content_hash": digest(payload), "payload": payload}
            descriptor = _put_object(workdir, report)
            with db:
                db.execute("UPDATE jobs SET status=?,updated_at=?,bundle_json=? WHERE job_id=?",
                           ("COMPLETE" if complete else "FAILED" if counts["failed"] else "PARTIAL", _now(), _json(bundle) if bundle else None, job_id))
                _event(db, job_id, run_id, "RUN_FINISHED", report_ref=_ref(report), report_artifact=descriptor)
            return report
        finally:
            db.close()
