"""Persistent local draft editing over frozen, independently audited evidence.

No OCR, model, browser or platform operation is performed. A saved draft is a
new complete content-revision snapshot, never a verification decision. Source
selection intervals use Unicode code points, as in content_revision.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import sqlite3
import threading
from uuid import uuid4

from PIL import Image

from .baseline import code_digest, digest, load_source, valid_bbox
from . import content_revision
from .content_revision import (apply_content_revision, build_content_quality,
                               make_revision_plan, reference, validate_revision_plan)
from .content_revision_quality import audit_content_application, audit_content_quality


class ReviewConflict(ValueError):
    """The supplied optimistic head is no longer the current workspace head."""


class SourceChanged(ValueError):
    """A bound local source is missing, changed or no longer decodable."""


_LOCKS = {}
_ROLES = ("plan", "application", "graph", "check", "application_audit", "quality_audit")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _same(left, right):
    return digest(left) == digest(right)


def _ref(value):
    return reference(value) if "revision" in value else {"artifact_id": value["artifact_id"], "content_hash": digest(value)}


def _flags():
    return dict(decision="HOLD", complete=False, transcription_verified=False,
                business_acceptance=False, platform_actions=[])


def _author(value):
    if (not isinstance(value, dict) or set(value) != {"kind", "id", "note"}
            or not isinstance(value.get("kind"), str) or value["kind"] not in {"MODEL_DRAFT", "HUMAN_DRAFT", "SYNTHETIC_TEST"}
            or any(not isinstance(value.get(k), str) or not value[k].strip() for k in ("id", "note"))):
        raise ValueError("author must be an explicit draft kind, id and note, without approval claims")
    return copy.deepcopy(value)


def _implementation():
    names = ("content_review", "content_revision", "content_revision_quality", "baseline", "offline", "policy", "question_quality")
    return {"schema_version": "b-content-review-implementation-trial/0.1",
            "modules": {name: code_digest(Path(__file__).with_name(name+".py")) for name in names},
            "python": platform.python_version(), "dependencies": {"Pillow": importlib.metadata.version("Pillow")}}


def _block_key(answer_id, fragment_id=None, operation_id=None, block_id=None):
    if fragment_id is not None:
        return "review-fragment-"+digest([answer_id, fragment_id])[:24]
    return "review-region-"+digest([answer_id, operation_id, block_id])[:24]


class ReviewWorkspace:
    """An immutable input scope, append-only revision history and CAS head.

    ``source_paths`` contains B source manifests, not arbitrary image paths.
    Source roots may move on restart when all asset identities remain exact.
    The optional zero-argument ``before_commit`` hook runs only for save/restore
    after publication and before transaction commit; it is a fault-test seam.
    """

    def __init__(self, evidence, graph05, base_check05, review, initial_plan,
                 workdir, source_paths, *, before_commit=None):
        self.workdir = Path(workdir).resolve()
        self.workdir.mkdir(parents=True, exist_ok=True)
        self._guard = _LOCKS.setdefault(str(self.workdir), threading.RLock())
        self._source_paths = [Path(source_paths)] if isinstance(source_paths, (str, Path)) else [Path(p) for p in source_paths]
        if not self._source_paths:
            raise ValueError("at least one local source manifest is required")
        if before_commit is not None and not callable(before_commit):
            raise ValueError("before_commit must be callable")
        self.before_commit = before_commit
        self._inputs = copy.deepcopy(dict(evidence=evidence, graph=graph05, base_check=base_check05,
                                         review=review, initial_plan=initial_plan))
        self._implementation = _implementation()
        self._source_identity, self._paths = self._read_sources()
        self.db_path = self.workdir/"review.sqlite3"
        self._schema()
        with self._locked():
            with self._connect() as db:
                meta = self._meta(db)
                if meta:
                    if (not _same(meta.get("inputs_sha256"), digest(self._inputs))
                            or not _same(meta.get("implementation"), self._implementation)
                            or not _same(meta.get("source_identity"), self._source_identity)):
                        raise ValueError("workspace inputs, source identity or implementation differ; open a fresh workspace")
                    if not _same(self._read_object(meta["inputs_object"]), self._inputs):
                        raise ValueError("frozen workspace inputs differ from supplied objects")
                    self._inputs_object = meta["inputs_object"]
                    self._source_blobs = meta["source_blobs"]
                    self._verify_sources()
                    self._validate_history(db)
                    self._interrupt_attempts(db)
                else:
                    documents = self._build_documents(initial_plan)
                    self._verify_sources()
                    input_object = self._publish(self._inputs)
                    self._inputs_object = input_object
                    self._source_blobs = self._freeze_sources()
                    descriptors = self._publish_documents(documents)
                    head = self._head_id(None, descriptors)
                    meta = dict(inputs_sha256=digest(self._inputs), inputs_object=input_object,
                                implementation=self._implementation, source_identity=self._source_identity,
                                source_blobs=self._source_blobs)
                    self._verify_sources()
                    db.execute("BEGIN IMMEDIATE")
                    try:
                        db.execute("INSERT INTO workspace(key,value_json) VALUES('meta',?)", (_json(meta),))
                        self._insert_revision(db, head, None, descriptors, documents["plan"], "初始离线草稿")
                        db.execute("INSERT INTO current_head(singleton,head) VALUES(1,?)", (head,))
                        self._event(db, "INITIALIZED", head, None, {"documents": descriptors})
                        db.commit()
                    except BaseException:
                        db.rollback()
                        raise

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
        finally:
            db.close()

    def _schema(self):
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS workspace(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS revisions(
              head TEXT PRIMARY KEY,parent_head TEXT,documents_json TEXT NOT NULL,
              author_json TEXT NOT NULL,summary TEXT NOT NULL,created_at TEXT NOT NULL,
              implementation_sha256 TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS current_head(singleton INTEGER PRIMARY KEY CHECK(singleton=1),head TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts(
              attempt_id TEXT PRIMARY KEY,expected_head TEXT NOT NULL,new_head TEXT,
              state TEXT NOT NULL,details_json TEXT NOT NULL,started_at TEXT NOT NULL,finished_at TEXT);
            CREATE TABLE IF NOT EXISTS events(
              event_id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,head TEXT,
              attempt_id TEXT,details_json TEXT NOT NULL,created_at TEXT NOT NULL);
            """)

    @contextmanager
    def _locked(self):
        with self._guard:
            lock_path = self.workdir/"review.lock"
            with lock_path.open("a+b") as handle:
                if lock_path.stat().st_size == 0:
                    handle.write(b"\0"); handle.flush()
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    try:
                        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                    except OSError as exc:
                        raise ReviewConflict("workspace is busy; reload the current head") from exc
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    handle.seek(0)
                    if os.name == "nt":
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(handle, fcntl.LOCK_UN)

    def _meta(self, db):
        row = db.execute("SELECT value_json FROM workspace WHERE key='meta'").fetchone()
        return json.loads(row[0]) if row else None

    def _read_sources(self):
        assets, paths = {}, {}
        try:
            for manifest in self._source_paths:
                source, members = load_source(manifest)
                if source["book_id"] != self._inputs["evidence"]["book_id"]:
                    raise SourceChanged("source manifest belongs to a different book")
                for asset, path in members:
                    aid = asset["asset_id"]
                    if aid in assets:
                        raise SourceChanged("source manifests contain duplicate asset IDs")
                    assets[aid] = {k: asset[k] for k in ("asset_id", "sha256", "width", "height")}
                    paths[aid] = path
            pages = self._inputs["evidence"]["payload"]["pages"]
            ids = [p["asset_id"] for p in pages]
            if len(ids) != len(set(ids)):
                raise SourceChanged("evidence contains duplicate asset IDs")
            for page in pages:
                expected = {k: page["source"][k] for k in ("asset_id", "sha256", "width", "height")}
                if expected["asset_id"] != page["asset_id"] or not _same(assets.get(page["asset_id"]), expected):
                    raise SourceChanged("evidence page is missing or differs from the local source")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            if isinstance(exc, SourceChanged): raise
            raise SourceChanged("local source validation failed: "+str(exc)) from exc
        return [assets[aid] for aid in sorted(assets)], paths

    def _verify_sources(self):
        if not _same(_implementation(), self._implementation):
            raise ValueError("workspace implementation changed; open a fresh compatible workspace")
        identity, paths = self._read_sources()
        if not _same(identity, self._source_identity):
            raise SourceChanged("bound source identity changed")
        self._paths = paths
        if hasattr(self, "_inputs_object"):
            self._read_blob(self._inputs_object)
        for asset in getattr(self, "_source_blobs", []):
            raw = self._read_blob(asset["object"])
            if hashlib.sha256(raw).hexdigest() != asset["sha256"]:
                raise SourceChanged("frozen source bytes changed")

    def _write_bytes(self, raw, directory, extension):
        sha = hashlib.sha256(raw).hexdigest()
        folder = self.workdir/directory; folder.mkdir(exist_ok=True)
        destination = folder/(sha+extension)
        temporary = folder/("."+uuid4().hex+".tmp")
        if destination.exists():
            if destination.read_bytes() != raw:
                raise ValueError("immutable object already exists with corrupt bytes")
        else:
            try:
                with temporary.open("xb") as stream:
                    stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                try:
                    os.link(temporary, destination)
                except FileExistsError:
                    if destination.read_bytes() != raw:
                        raise ValueError("immutable object collision or corruption")
            finally:
                if temporary.exists(): temporary.unlink()
        return {"path": directory+"/"+destination.name, "sha256": sha, "bytes": len(raw)}

    def _publish(self, value):
        description = self._write_bytes(_json(value).encode("utf-8"), "objects", ".json")
        description["artifact_ref"] = _ref(value) if isinstance(value, dict) and "artifact_id" in value else None
        return description

    def _read_blob(self, description):
        if (not isinstance(description, dict) or not isinstance(description.get("path"), str)
                or description["path"].count("/") != 1 or "\\" in description["path"]
                or description["path"].split("/")[0] not in {"objects", "sources"}):
            raise ValueError("invalid immutable object descriptor")
        path = (self.workdir/description["path"]).resolve()
        if not path.is_relative_to(self.workdir): raise ValueError("object path escapes workspace")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ValueError("persisted immutable object is missing or unreadable") from exc
        if hashlib.sha256(raw).hexdigest() != description.get("sha256") or len(raw) != description.get("bytes"):
            raise ValueError("persisted immutable object bytes changed")
        if path.stem != description["sha256"]:
            raise ValueError("object filename is not its content address")
        return raw

    def _read_object(self, description):
        value = json.loads(self._read_blob(description))
        expected = _ref(value) if isinstance(value, dict) and "artifact_id" in value else None
        if not _same(description.get("artifact_ref"), expected):
            raise ValueError("immutable object reference differs from its bytes")
        return value

    def _freeze_sources(self):
        result = []
        for page in self._inputs["evidence"]["payload"]["pages"]:
            aid = page["asset_id"]; raw = self._paths[aid].read_bytes()
            if hashlib.sha256(raw).hexdigest() != page["source"]["sha256"]:
                raise SourceChanged("source changed while freezing workspace")
            result.append({"asset_id": aid, "sha256": page["source"]["sha256"],
                           "object": self._write_bytes(raw, "sources", ".bin")})
        return result

    def _build_documents(self, plan):
        e, g, c, r = [self._inputs[k] for k in ("evidence", "graph", "base_check", "review")]
        validate_revision_plan(plan, e, g, c)
        application = apply_content_revision(e, g, c, plan)
        check = build_content_quality(e, g, c, plan, application, r)
        result = dict(plan=copy.deepcopy(plan), application=application, graph=application["payload"]["graph"], check=check,
                      application_audit=audit_content_application(e, g, c, plan, application),
                      quality_audit=audit_content_quality(e, g, c, plan, application, r, check))
        self._accepted(result)
        return result

    @staticmethod
    def _accepted(documents):
        if any(documents[k].get("payload", {}).get("accepted") is not True for k in ("application_audit", "quality_audit")):
            raise ValueError("independent content audit rejected the draft projection")

    def _publish_documents(self, documents):
        return {name: self._publish(documents[name]) for name in _ROLES}

    def _head_id(self, parent, descriptors):
        return "review-head-"+digest([digest(self._inputs), digest(self._implementation), parent, descriptors])[:32]

    def _event(self, db, kind, head, attempt_id, details):
        db.execute("INSERT INTO events(kind,head,attempt_id,details_json,created_at) VALUES(?,?,?,?,?)",
                   (kind, head, attempt_id, _json(details), _now()))

    def _insert_revision(self, db, head, parent, descriptors, plan, summary):
        db.execute("INSERT INTO revisions VALUES(?,?,?,?,?,?,?)", (head, parent, _json(descriptors),
                   _json(plan["payload"]["author"]), summary, _now(), digest(self._implementation)))

    def _head(self, db):
        row = db.execute("SELECT head FROM current_head WHERE singleton=1").fetchone()
        if row is None: raise ValueError("workspace has no committed head")
        return row[0]

    def _load_documents(self, db, head):
        record = db.execute("SELECT * FROM revisions WHERE head=?", (head,)).fetchone()
        if record is None: raise ValueError("revision is not a member of this workspace history")
        descriptors = json.loads(record["documents_json"])
        if (set(descriptors) != set(_ROLES) or record["implementation_sha256"] != digest(self._implementation)
                or self._head_id(record["parent_head"], descriptors) != head):
            raise ValueError("persisted revision identity or implementation changed")
        documents = {name: self._read_object(descriptors[name]) for name in _ROLES}
        self._accepted(documents)
        if not _same(json.loads(record["author_json"]), documents["plan"]["payload"]["author"]):
            raise ValueError("persisted draft author changed")
        if not _same(documents["graph"], documents["application"]["payload"]["graph"]):
            raise ValueError("persisted graph is not the actual application graph")
        e, g, c, r = [self._inputs[k] for k in ("evidence", "graph", "base_check", "review")]
        validate_revision_plan(documents["plan"], e, g, c)
        application_check = audit_content_application(e, g, c, documents["plan"], documents["application"])
        quality_check = audit_content_quality(e, g, c, documents["plan"], documents["application"], r, documents["check"])
        if not _same(application_check, documents["application_audit"]) or not _same(quality_check, documents["quality_audit"]):
            raise ValueError("persisted audit differs from current independent checks")
        self._accepted(dict(application_audit=application_check, quality_audit=quality_check))
        return documents

    def _validate_history(self, db):
        rows = db.execute("SELECT * FROM revisions ORDER BY rowid").fetchall()
        if not rows: raise ValueError("workspace metadata exists without committed revisions")
        previous = None
        for row in rows:
            documents = self._load_documents(db, row["head"])
            if row["parent_head"] != previous:
                raise ValueError("workspace history chain changed")
            if previous is None:
                if not _same(documents["plan"], self._inputs["initial_plan"]):
                    raise ValueError("workspace initial plan changed")
            elif not _same(documents["plan"]["payload"]["previous_plan_archive"], old_plan):
                raise ValueError("saved plan does not archive the preceding committed plan")
            old_plan = documents["plan"]; previous = row["head"]
        if self._head(db) != previous:
            raise ValueError("workspace head is not the latest committed revision")

    def _interrupt_attempts(self, db):
        rows = db.execute("SELECT attempt_id,expected_head FROM attempts WHERE state='RUNNING'").fetchall()
        for row in rows:
            db.execute("UPDATE attempts SET state='INTERRUPTED',finished_at=? WHERE attempt_id=?", (_now(), row[0]))
            self._event(db, "ATTEMPT_INTERRUPTED", row[1], row[0], {"reason": "previous writer released its process lock before commit"})

    def documents(self, head=None):
        with self._locked():
            self._verify_sources()
            with self._connect() as db:
                documents = self._load_documents(db, head or self._head(db))
            self._verify_sources()
            return copy.deepcopy(documents)

    def _candidate_options(self, answer, fragment):
        inline = self._inputs["graph"]["payload"]["inline_content"]
        parent = fragment.get("parent_line_id"); result = []
        owners = [v for v in inline["bindings"] if v["line_id"] == parent]
        if (len(owners) != 1 or owners[0].get("unassigned") is not False
                or not any(v["fragment_id"] == fragment["fragment_id"] and v["answer_id"] == answer["answer_id"] and v["role"] == fragment["role"] for v in owners[0]["fragments"])
                or any(v["answer_id"] != answer["answer_id"] or v["role"] != fragment["role"] for v in owners[0]["fragments"])):
            return result
        calls = {v["plan"]["call_id"]: v for v in inline["calls"]}
        units = {v["unit_id"]: v for v in inline["units"]}
        for candidate in inline["candidates"]:
            call = calls.get(candidate["call_id"])
            if candidate["state"] != "DONE" or not call or call["state"] != "DONE" or not candidate["unit_bindings"]:
                continue
            if any(v["line_id"] != parent for v in candidate["unit_bindings"]): continue
            for unit in candidate["unit_bindings"]:
                bound = units.get(unit["unit_id"])
                if not bound or bound["asset_id"] != fragment["asset_id"] or bound["line_id"] != parent: continue
                option = {k: candidate[k] for k in ("candidate_id", "call_id", "raw_latex")}
                option.update(unit_id=unit["unit_id"], parse_supported=candidate["parse_result"]["supported"])
                if option not in result: result.append(option)
        return result

    def _answer_blocks(self, answer):
        original = next(v for v in self._inputs["graph"]["payload"]["answers"] if v["answer_id"] == answer["answer_id"])
        visible, _ = content_revision._visible(original)
        by_id = {f["fragment_id"]: f for f in visible}; blocks = []
        content = answer.get("content_fragments")
        if content is None:
            content = [{"source_fragment_id": f["fragment_id"], "text": f["text"], "pieces": [{"format": "plain", "text": f["text"]}]} for f in visible]
        for fragment in content:
            if fragment.get("kind") == "REGION_DRAFT":
                ids = fragment["source_fragment_ids"]
                blocks.append(dict(key=_block_key(answer["answer_id"], operation_id=fragment["operation_id"], block_id=fragment["block_id"]),
                    kind="REGION", role=fragment["role"], asset_id=fragment["asset_id"], bbox=copy.deepcopy(fragment["bbox"]), source_fragment_ids=copy.deepcopy(ids),
                    source_text="\n".join(by_id[fid]["text"] for fid in ids), text=fragment["text"], runs=copy.deepcopy(fragment["runs"]), candidates=[]))
            else:
                f = by_id[fragment["source_fragment_id"]]
                blocks.append(dict(key=_block_key(answer["answer_id"], fragment_id=f["fragment_id"]), kind="FRAGMENT", role=f["role"], asset_id=f["asset_id"],
                    bbox=copy.deepcopy(f["bbox"]), source_fragment_ids=[f["fragment_id"]], source_text=f["text"], text=fragment["text"],
                    runs=[{k: piece[k] for k in ("format", "text")} for piece in fragment["pieces"]], candidates=self._candidate_options(original, f)))
        return blocks

    def _state(self, db, documents, head):
        graph, check, plan = [documents[k] for k in ("graph", "check", "plan")]
        issues = check["payload"]["issues"]; answers = []
        lineage = {line["line_id"]: line.get("base_line_ids", []) for page in self._inputs["evidence"]["payload"]["pages"]
                   for line in page["ocr_lines"]+page.get("answer_detail_lines", [])}
        for answer in graph["payload"]["answers"]:
            questions = [q for q in graph["payload"]["questions"] if answer["answer_id"] in q["candidate_answer_ids"]]
            source_ids = set(answer["evidence_refs"]+answer["source_line_ids"]+[f["parent_line_id"] for f in answer["fragments"]])
            source_ids.update(base for current in tuple(source_ids) for base in lineage.get(current, []))
            scopes = {answer["answer_id"], *(q["question_id"] for q in questions)}
            linked = [i["issue_id"] for i in issues if i.get("scope_id") in scopes or any(isinstance(r, str) and r in source_ids for r in i.get("evidence_refs", []))]
            figures = [{k: copy.deepcopy(r[k]) for k in ("region_id", "asset_id", "bbox", "role")} for r in answer.get("render_regions", []) if r.get("content_type") == "image"]
            answers.append({k: copy.deepcopy(answer[k]) for k in ("answer_id", "printed_number", "section_path", "text", "explanation_text")})
            answers[-1].update(blocks=self._answer_blocks(answer), figures=figures, issue_ids=list(dict.fromkeys(linked)),
                               question_candidates=[{k: copy.deepcopy(q[k]) for k in ("question_id", "printed_number", "section_path", "text")} for q in questions])
        history = []
        for row in db.execute("SELECT * FROM revisions ORDER BY rowid"):
            refs = json.loads(row["documents_json"])
            history.append(dict(head=row["head"], parent_head=row["parent_head"], plan_ref=refs["plan"]["artifact_ref"], graph_ref=refs["graph"]["artifact_ref"],
                quality_ref=refs["check"]["artifact_ref"], author=json.loads(row["author_json"]), created_at=row["created_at"], summary=row["summary"]))
        return dict(schema_version="b-content-review-state-trial/0.1", head=head, book_id=graph["book_id"], scope_id=graph["scope_id"],
            plan_revision=plan["revision"], plan_ref=reference(plan), graph_ref=reference(graph), quality_ref=reference(check),
            base_refs={k: _ref(self._inputs[v]) for k, v in dict(evidence="evidence", graph="graph", base_check="base_check", review="review").items()},
            author=copy.deepcopy(plan["payload"]["author"]), counts=dict(questions=len(graph["payload"]["questions"]), answers=len(answers), issues=len(issues),
                unassigned=sum(r["status"] == "UNASSIGNED" for r in graph["payload"]["answer_coverage"])),
            assets=[{k: p["source"][k] for k in ("asset_id", "width", "height", "sha256")} for p in self._inputs["evidence"]["payload"]["pages"]],
            answers=answers, issues=copy.deepcopy(issues), history=history, **_flags())

    def state(self):
        with self._locked():
            self._verify_sources()
            with self._connect() as db:
                head = self._head(db); documents = self._load_documents(db, head)
                result = self._state(db, documents, head)
            self._verify_sources()
            return result

    def _edit_operations(self, documents, answer_id, changes, author):
        answer = next((a for a in documents["graph"]["payload"]["answers"] if a["answer_id"] == answer_id), None)
        if answer is None: raise ValueError("unknown answer ID")
        blocks = {b["key"]: b for b in self._answer_blocks(answer)}
        operations = copy.deepcopy(documents["plan"]["payload"]["operations"])
        original = next(a for a in self._inputs["graph"]["payload"]["answers"] if a["answer_id"] == answer_id)
        fragments = {f["fragment_id"]: f for f in original["fragments"]}
        changed, seen = [], set()
        for change in changes:
            if not isinstance(change, dict) or not isinstance(change.get("key"), str) or change["key"] not in blocks or change["key"] in seen:
                raise ValueError("changes require unique known block keys in the selected answer")
            seen.add(change["key"]); block = blocks[change["key"]]
            if block["kind"] == "REGION":
                if set(change) != {"key", "runs"} or not isinstance(change["runs"], list) or not change["runs"]:
                    raise ValueError("region changes may update only nonempty typed runs")
                for run in change["runs"]:
                    if (not isinstance(run, dict) or set(run) != {"format", "text"}
                            or not isinstance(run.get("format"), str) or run["format"] not in {"plain", "latex"}):
                        raise ValueError("invalid region run fields")
                    content_revision._replacement(run["text"])
                if _same(change["runs"], block["runs"]): continue
                found = False
                for op in operations:
                    if op["kind"] != "REBUILD_TEXT_REGION" or op["target"]["answer_id"] != answer_id: continue
                    for target in op["blocks"]:
                        if _block_key(answer_id, operation_id=op["operation_id"], block_id=target["block_id"]) == block["key"]:
                            target["runs"] = copy.deepcopy(change["runs"])
                            target["note"] += " Offline draft runs edited by "+author["id"]+"; unverified."
                            found = True
                if not found: raise ValueError("current region has no existing source-bound operation")
            else:
                fid = block["source_fragment_ids"][0]; f = fragments[fid]
                target = dict(answer_id=answer_id, fragment_id=fid, role=f["role"], fragment_span=[0, len(f["text"])], expected_text=f["text"])
                if set(change) == {"key", "text", "format"}:
                    content_revision._replacement(change["text"])
                    if not isinstance(change["format"], str) or change["format"] not in {"plain", "latex"}: raise ValueError("unknown explicit text format")
                    if change["text"] == block["text"] and all(run["format"] == change["format"] for run in block["runs"]): continue
                    operations = [op for op in operations if not (op["kind"] in {"EDIT_TEXT", "SELECT_INLINE"} and op["target"]["fragment_id"] == fid)]
                    operation = dict(kind="EDIT_TEXT", target=target, replacement=change["text"], format=change["format"])
                elif set(change) == {"key", "candidate_id", "call_id", "unit_id", "fragment_span"}:
                    match = [{k: c[k] for k in ("candidate_id", "call_id", "unit_id")} for c in block["candidates"]]
                    selection = {k: change[k] for k in ("candidate_id", "call_id", "unit_id")}
                    if not any(_same(selection, c) for c in match): raise ValueError("candidate does not bind this source row, answer and role")
                    span = change["fragment_span"]
                    if not content_revision._span(span, len(f["text"])): raise ValueError("candidate span must use original Unicode code point offsets")
                    removed = []
                    for op in operations:
                        if op["kind"] not in {"EDIT_TEXT", "SELECT_INLINE"} or op["target"]["fragment_id"] != fid: continue
                        interval = op["target"]["fragment_span"]
                        if max(span[0], interval[0]) < min(span[1], interval[1]):
                            if not span[0] <= interval[0] < interval[1] <= span[1]:
                                raise ValueError("candidate selection partially overlaps an existing source edit")
                            removed.append(op)
                    target.update(fragment_span=copy.deepcopy(span), expected_text=f["text"][span[0]:span[1]])
                    operation = dict(kind="SELECT_INLINE", target=target, **selection)
                    if len(removed) == 1 and _same({k: removed[0].get(k) for k in operation}, operation): continue
                    removed_ids = {op["operation_id"] for op in removed}
                    operations = [op for op in operations if op["operation_id"] not in removed_ids]
                else:
                    raise ValueError("fragment change fields are invalid or contain approval claims")
                operation.update(operation_id="review-operation-"+digest([reference(documents["plan"]), block["key"], operation])[:24],
                                 reason="Explicit offline draft edit by "+author["id"]+"; no human verification claimed.")
                operations.append(operation)
            changed.append(block["key"])
        return operations, changed

    def _mutate(self, expected_head, author, action, *, answer_id=None, changes=None, revision_head=None):
        if not isinstance(expected_head, str) or not expected_head: raise ValueError("expected_head is required")
        author = _author(author)
        with self._locked():
            self._verify_sources()
            with self._connect() as db:
                head = self._head(db)
                if head != expected_head: raise ReviewConflict("workspace head changed; reload before saving")
                current = self._load_documents(db, head)
                if action == "SAVE":
                    operations, changed = self._edit_operations(current, answer_id, changes, author)
                    if not changed:
                        result = self._state(db, current, head); self._verify_sources(); return result
                    summary = "保存 "+answer_id+"（"+str(len(changed))+" 项草稿修改）"
                else:
                    if not isinstance(revision_head, str): raise ValueError("revision_head is required")
                    target = self._load_documents(db, revision_head)
                    operations = copy.deepcopy(target["plan"]["payload"]["operations"])
                    changed = []; summary = "恢复历史草稿 "+revision_head
                attempt = "review-attempt-"+uuid4().hex
                details = dict(action=action, answer_id=answer_id, changed_keys=changed, revision_head=revision_head)
                db.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?,?)", (attempt, head, None, "RUNNING", _json(details), _now(), None))
                self._event(db, "ATTEMPT_STARTED", head, attempt, details)
                try:
                    plan = make_revision_plan(self._inputs["evidence"], self._inputs["graph"], self._inputs["base_check"], operations, author,
                                              previous_plan=current["plan"])
                    documents = self._build_documents(plan)
                    self._verify_sources()
                    descriptors = self._publish_documents(documents)
                    new_head = self._head_id(head, descriptors)
                    details["documents"] = descriptors
                    db.execute("UPDATE attempts SET new_head=?,details_json=? WHERE attempt_id=?", (new_head, _json(details), attempt))
                    self._event(db, "OBJECTS_PUBLISHED", new_head, attempt, {"documents": descriptors})
                    db.execute("BEGIN IMMEDIATE")
                    if self._head(db) != expected_head:
                        raise ReviewConflict("workspace head changed during draft preparation")
                    self._insert_revision(db, new_head, head, descriptors, plan, summary)
                    db.execute("UPDATE current_head SET head=? WHERE singleton=1 AND head=?", (new_head, expected_head))
                    self._event(db, "REVISION_COMMITTED", new_head, attempt, {"parent_head": head})
                    if self.before_commit is not None: self.before_commit()
                    self._verify_sources()
                    if not _same({name: self._read_object(descriptors[name]) for name in _ROLES}, documents):
                        raise ValueError("published draft objects changed before commit")
                    db.execute("UPDATE attempts SET state='COMMITTED',finished_at=? WHERE attempt_id=?", (_now(), attempt))
                    db.commit()
                    return self._state(db, documents, new_head)
                except BaseException as exc:
                    db.rollback()
                    db.execute("UPDATE attempts SET state='FAILED',finished_at=? WHERE attempt_id=?", (_now(), attempt))
                    self._event(db, "ATTEMPT_FAILED", head, attempt, {"error_type": type(exc).__name__, "error": str(exc)})
                    raise

    def save(self, request):
        if not isinstance(request, dict) or set(request) != {"expected_head", "answer_id", "changes", "author"}:
            raise ValueError("save request has unknown or missing fields")
        if not isinstance(request["answer_id"], str) or not isinstance(request["changes"], list):
            raise ValueError("save requires one answer and an ordered changes list")
        return self._mutate(request["expected_head"], request["author"], "SAVE", answer_id=request["answer_id"], changes=request["changes"])

    def restore(self, request):
        if not isinstance(request, dict) or set(request) != {"expected_head", "revision_head", "author"}:
            raise ValueError("restore request has unknown or missing fields")
        return self._mutate(request["expected_head"], request["author"], "RESTORE", revision_head=request["revision_head"])

    def source_png(self, asset_id, bbox=None):
        with self._locked():
            self._verify_sources()
            pages = [p for p in self._inputs["evidence"]["payload"]["pages"] if p["asset_id"] == asset_id]
            if len(pages) != 1: raise ValueError("source asset is outside the frozen evidence scope")
            size = pages[0]["source"]
            if bbox is not None and (not isinstance(bbox, (list, tuple)) or len(bbox) != 4 or not valid_bbox(list(bbox), size["width"], size["height"])):
                raise ValueError("source crop is outside the actual page")
            raw = self._paths[asset_id].read_bytes()
            if hashlib.sha256(raw).hexdigest() != size["sha256"]: raise SourceChanged("source changed before crop decoding")
            with Image.open(io.BytesIO(raw)) as image:
                rgb = image.convert("RGB")
                if bbox is not None:
                    rgb = rgb.crop([math.floor(bbox[0]), math.floor(bbox[1]), math.ceil(bbox[2]), math.ceil(bbox[3])])
                output = io.BytesIO(); rgb.save(output, format="PNG")
            self._verify_sources()
            return output.getvalue()
