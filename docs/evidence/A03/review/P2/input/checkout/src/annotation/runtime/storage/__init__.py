"""A03 controlled local ledger, immutable files and single-use authority.

SQLite transactions never include target effects. The common OS book gate is
held by the target around authorization and its independent effect transaction.
Opening a missing state is always an error; only explicit init creates a store.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time

from .common import (RuntimeFailure, Handle, canonical, digest, exclusive_bytes,
                     fail, now, plain, reference, unique, FaultController)
from .holds import HoldSupport

DB_VERSION = "a03-runtime-db-1"
ZERO = "0" * 64
CURRENT = ContextVar("a03_current_runtime", default=None)


class ClosingConnection(sqlite3.Connection):
    """A read transaction context also releases its Windows file handle."""

    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


SQL = """
CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE files(path TEXT PRIMARY KEY,sha TEXT NOT NULL,size INTEGER NOT NULL);
CREATE TABLE books(key TEXT PRIMARY KEY,target_key TEXT NOT NULL,journal TEXT NOT NULL,
 owner TEXT,generation INTEGER NOT NULL DEFAULT 0,phase TEXT NOT NULL DEFAULT 'IDLE',
 pid INTEGER,process_id TEXT,lease REAL NOT NULL DEFAULT 0,head_sequence INTEGER NOT NULL DEFAULT 0,
 head_hash TEXT NOT NULL,hold TEXT);
CREATE TABLE registrations(id TEXT PRIMARY KEY,book TEXT NOT NULL,scope TEXT NOT NULL,
 source TEXT NOT NULL,session TEXT NOT NULL,target_dir TEXT NOT NULL,package_root TEXT NOT NULL,
 bundle_path TEXT NOT NULL,config TEXT NOT NULL);
CREATE TABLE artifacts(identity TEXT PRIMARY KEY,book TEXT NOT NULL,scope TEXT NOT NULL,
 ref TEXT NOT NULL,path TEXT NOT NULL);
CREATE TABLE events(book TEXT NOT NULL,sequence INTEGER NOT NULL,body TEXT NOT NULL,
 PRIMARY KEY(book,sequence));
CREATE TABLE plans(id TEXT PRIMARY KEY,book TEXT NOT NULL,registration TEXT NOT NULL,
 ref TEXT NOT NULL,status TEXT NOT NULL,cursor INTEGER NOT NULL DEFAULT 0);
CREATE TABLE actions(book TEXT NOT NULL,id TEXT NOT NULL,digest TEXT NOT NULL,plan TEXT NOT NULL,
 position INTEGER NOT NULL,state TEXT NOT NULL,intent TEXT,fact TEXT,PRIMARY KEY(book,id));
CREATE TABLE intents(id TEXT PRIMARY KEY,book TEXT NOT NULL,plan TEXT NOT NULL,action TEXT NOT NULL,
 ref TEXT NOT NULL,obligation TEXT UNIQUE NOT NULL,prepared TEXT NOT NULL,state TEXT NOT NULL,
 owner TEXT NOT NULL,generation INTEGER NOT NULL,receipt TEXT);
CREATE TABLE permits(token TEXT PRIMARY KEY,intent TEXT NOT NULL,state TEXT NOT NULL,head TEXT NOT NULL);
CREATE TABLE resolutions(id TEXT PRIMARY KEY,intent TEXT NOT NULL,ref TEXT NOT NULL,outcome TEXT NOT NULL);
CREATE TABLE legacy(id TEXT PRIMARY KEY,book TEXT NOT NULL,scope TEXT NOT NULL,classification TEXT NOT NULL,resource TEXT NOT NULL);
CREATE TABLE calls(id TEXT PRIMARY KEY,book TEXT NOT NULL,queue TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE attempts(call_id TEXT NOT NULL,intent TEXT NOT NULL,number INTEGER NOT NULL,
 status TEXT NOT NULL,resource TEXT,PRIMARY KEY(call_id,intent,number));
CREATE TABLE attempt_windows(call_id TEXT NOT NULL,intent TEXT NOT NULL,started REAL NOT NULL,
 PRIMARY KEY(call_id,intent));
"""


def init_state(anchor_path, *, state_dir, expected_ledger_id, expected_target_store_id):
    anchor, directory = Path(anchor_path).resolve(), Path(state_dir).resolve()
    if anchor.exists() or directory.exists():
        fail("STATE_INIT_TARGET_EXISTS", "explicit init requires a new state directory", 5)
    directory.mkdir(parents=True)
    database = directory / "runtime.sqlite3"
    connection = sqlite3.connect(str(database), timeout=1)
    try:
        connection.execute("PRAGMA application_id=1093677906")
        connection.execute("PRAGMA user_version=1")
        connection.executescript(SQL)
        for key, value in {"version": DB_VERSION, "ledger_id": expected_ledger_id,
                           "target_store_id": expected_target_store_id, "state_dir": str(directory)}.items():
            connection.execute("INSERT INTO meta VALUES(?,?)", (key, value))
        connection.commit()
    finally:
        connection.close()
    descriptor = {"format_version": "a03-runtime-anchor-1", "state_dir": str(directory),
        "anchor_path": str(anchor), "ledger_id": expected_ledger_id,
        "target_store_id": expected_target_store_id, "db_version": DB_VERSION}
    exclusive_bytes(anchor, canonical(descriptor))
    return open_state(anchor, expected_ledger_id=expected_ledger_id,
                      expected_target_store_id=expected_target_store_id)


def open_state(anchor_path, *, expected_ledger_id, expected_target_store_id):
    store = RuntimeStore(anchor_path, expected_ledger_id=expected_ledger_id,
                         expected_target_store_id=expected_target_store_id)
    CURRENT.set(store)
    return store


class RuntimeStore(HoldSupport):
    def __init__(self, anchor_path, *, expected_ledger_id, expected_target_store_id):
        self.anchor_path = Path(anchor_path).resolve()
        try:
            self.anchor = json.loads(self.anchor_path.read_bytes())
        except (OSError, ValueError) as error:
            fail("STATE_DIRECTORY_IDENTITY_MISMATCH", str(error), 5)
        self.directory = Path(self.anchor.get("state_dir", "")).resolve()
        if (self.anchor.get("anchor_path") != str(self.anchor_path) or self.anchor.get("ledger_id") != expected_ledger_id
                or self.anchor.get("target_store_id") != expected_target_store_id or self.anchor.get("db_version") != DB_VERSION):
            fail("STATE_DIRECTORY_IDENTITY_MISMATCH", "anchor/config identities differ", 5)
        self.database = self.directory / "runtime.sqlite3"
        if not self.database.is_file() or self.database.is_symlink():
            fail("LEDGER_MISSING", "open never initializes missing data", 5)
        self.ledger_id, self.target_store_id = expected_ledger_id, expected_target_store_id
        self.instance = unique("process")
        self.owner_id = self.instance
        self.current_claim = None
        self._issued = {}
        self._observations = {}
        self._observation_deadlines = {}
        self._observers = {}
        self._prepared_intents = {}
        self._gates = {}
        self.fault = FaultController()
        self.verify_integrity()

    def connect(self):
        try:
            connection = sqlite3.connect(self.database.as_uri() + "?mode=rw", uri=True, timeout=1,
                                         factory=ClosingConnection)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=1000")
            return connection
        except sqlite3.Error as error:
            fail("LEDGER_CORRUPT", str(error), 5)

    @contextmanager
    def transaction(self):
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except sqlite3.Error as error:
            connection.rollback()
            fail("STORAGE_TRANSACTION_FAILED", str(error), 5)
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def verify_integrity(self):
        try:
            with self.connect() as connection:
                meta = dict(connection.execute("SELECT key,value FROM meta"))
                if meta != {"version": DB_VERSION, "ledger_id": self.ledger_id, "target_store_id": self.target_store_id,
                            "state_dir": str(self.directory)}:
                    fail("LEDGER_VERSION_UNSUPPORTED", "metadata mismatch", 5)
                if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    fail("LEDGER_CORRUPT", "SQLite integrity check failed", 5)
                if connection.execute("PRAGMA application_id").fetchone()[0] != 0x41303352 or connection.execute("PRAGMA user_version").fetchone()[0] != 1:
                    fail("LEDGER_VERSION_UNSUPPORTED", "SQLite application/user version mismatch", 5)
                if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='attempt_windows'").fetchone():
                    fail("LEDGER_VERSION_UNSUPPORTED", "runtime schema is incomplete", 5)
                for row in connection.execute("SELECT * FROM files"):
                    path = self.directory / row["path"]
                    if not path.is_file() or path.is_symlink():
                        fail("RESOURCE_MISSING", row["path"], 5)
                    raw = path.read_bytes()
                    if len(raw) != row["size"] or hashlib.sha256(raw).hexdigest() != row["sha"]:
                        fail("RESOURCE_HASH_MISMATCH", row["path"], 5)
                for book in connection.execute("SELECT * FROM books"):
                    previous, sequence = ZERO, 0
                    for row in connection.execute("SELECT body FROM events WHERE book=? ORDER BY sequence", (book["key"],)):
                        event = json.loads(row["body"])
                        sequence += 1
                        if (event["sequence"] != sequence or event["previous_hash"] != previous or
                            event["event_hash"] != digest({k: v for k, v in event.items() if k != "event_hash"})):
                            fail("LEDGER_CORRUPT", "event chain mismatch", 5)
                        previous = event["event_hash"]
                    if (sequence, previous) != (book["head_sequence"], book["head_hash"]):
                        fail("LEDGER_INCOMPLETE", "event head differs", 5)
        except sqlite3.Error as error:
            fail("LEDGER_CORRUPT", str(error), 5)
        return True

    def _file(self, path, data, connection=None):
        path = exclusive_bytes(path, data).resolve()
        if self.directory not in path.parents:
            fail("STATE_DIRECTORY_IDENTITY_MISMATCH", str(path), 5)
        args = (path.relative_to(self.directory).as_posix(), hashlib.sha256(data).hexdigest(), len(data))
        if connection is None:
            with self.transaction() as current:
                current.execute("INSERT OR IGNORE INTO files VALUES(?,?,?)", args)
        else:
            connection.execute("INSERT OR IGNORE INTO files VALUES(?,?,?)", args)
        return path

    def object(self, value, connection=None):
        data = canonical(value)
        return self._file(self.directory / "objects" / (hashlib.sha256(data).hexdigest() + ".json"), data, connection)

    def resource(self, value, registration_id, connection=None):
        reg = self.registration(registration_id)
        data = canonical(value)
        relative = "assets/runtime/" + hashlib.sha256(data).hexdigest() + ".json"
        self._file(Path(reg["package_root"]) / relative, data, connection)
        return {"path": relative, "sha256": hashlib.sha256(data).hexdigest(),
                "media_type": "application/json", "origin": "SYNTHETIC"}

    def read_resource(self, resource, registration_id):
        root = Path(self.registration(registration_id)["package_root"])
        path = (root / resource["path"]).resolve()
        if root not in path.parents or not path.is_file():
            fail("RESOURCE_MISSING", resource["path"], 5)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != resource["sha256"]:
            fail("RESOURCE_HASH_MISMATCH", resource["path"], 5)
        return json.loads(raw)

    def registration(self, registration_id=None):
        with self.connect() as connection:
            if registration_id:
                row = connection.execute("SELECT * FROM registrations WHERE id=?", (registration_id,)).fetchone()
            else:
                rows = connection.execute("SELECT * FROM registrations").fetchall()
                row = rows[0] if len(rows) == 1 else None
        if row is None:
            fail("REGISTRATION_BINDING_MISMATCH", "explicit registration required")
        return dict(row)

    def bundle(self, registration_id):
        reg = self.registration(registration_id)
        return json.loads(Path(reg["bundle_path"]).read_bytes())

    def book_id(self, target_key):
        if not isinstance(target_key, dict) or set(target_key) != {"platform_namespace", "target_id", "book_id"}:
            fail("TARGET_IDENTITY_MISMATCH", "canonical three-part book key required")
        return digest(target_key)

    def register_book(self, bundle, *, target_key, target_dir, target_session_id, source_ref,
                      asset_root, config=None, registration_id=None):
        from annotation.contracts import validate_recovery_bundle
        validated = validate_recovery_bundle(bundle, asset_root=asset_root)
        value, root = plain(validated), Path(asset_root).resolve()
        key = self.book_id(target_key)
        source = next((a for a in value["artifacts"] if reference(a) == plain(source_ref)), None)
        if source is None or source["book_id"] != target_key["book_id"]:
            fail("SOURCE_BINDING", "registered source missing")
        package_root = self.directory / "packages" / digest(value)
        package_root.mkdir(parents=True, exist_ok=True)
        seen = set()

        def resources(node):
            if isinstance(node, dict):
                if {"path", "sha256"} <= set(node):
                    path = (root / node["path"]).resolve()
                    if root not in path.parents or path.is_symlink() or not path.is_file():
                        fail("RESOURCE_MISSING", str(node["path"]), 5)
                    raw = path.read_bytes()
                    if hashlib.sha256(raw).hexdigest() != node["sha256"]:
                        fail("RESOURCE_HASH_MISMATCH", node["path"], 5)
                    if node["path"] not in seen:
                        seen.add(node["path"])
                        self._file(package_root / node["path"], raw)
                        if node.get("media_type") == "application/json":
                            resources(json.loads(raw))
                for item in node.values():
                    resources(item)
            elif isinstance(node, list):
                for item in node:
                    resources(item)
        resources(value)
        stored = self._file(package_root / ("bundle-" + digest(value) + ".json"), canonical(value))
        rid = registration_id or unique("registration")
        with self.transaction() as connection:
            existing = connection.execute("SELECT * FROM registrations WHERE book=?", (key,)).fetchone()
            if existing:
                if (existing["scope"] != source["scope_id"] or json.loads(existing["source"]) != plain(source_ref)
                        or existing["session"] != target_session_id or existing["target_dir"] != str(Path(target_dir).resolve())):
                    fail("TARGET_SCOPE_SWITCH_UNSUPPORTED", "fixed registered session/source/scope")
                fail("TARGET_ALREADY_REGISTERED", "registration never resets history")
            connection.execute("INSERT INTO books(key,target_key,journal,head_hash) VALUES(?,?,?,?)",
                (key, canonical(target_key).decode(), unique("journal"), ZERO))
            connection.execute("INSERT INTO registrations VALUES(?,?,?,?,?,?,?,?,?)",
                (rid, key, source["scope_id"], canonical(source_ref).decode(), target_session_id,
                 str(Path(target_dir).resolve()), str(package_root), str(stored), canonical(config or {}).decode()))
            for artifact in value["artifacts"]:
                self._artifact(connection, artifact)
        return Handle(registration_id=rid, target_key=target_key, package_root=str(package_root))

    def _artifact(self, connection, artifact):
        artifact = plain(artifact)
        identity = canonical({k: artifact[k] for k in
            ("schema_version", "book_id", "scope_id", "artifact_id", "revision")}).decode()
        ref_text = canonical(reference(artifact)).decode()
        old = connection.execute("SELECT ref FROM artifacts WHERE identity=?", (identity,)).fetchone()
        if old and old["ref"] != ref_text:
            fail("HISTORY_ID_CONFLICT", identity)
        path = self.object(artifact, connection)
        connection.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?,?,?)",
            (identity, artifact["book_id"], artifact["scope_id"], ref_text, str(path)))
        return reference(artifact)

    def _event(self, connection, key, name, payload):
        book = connection.execute("SELECT * FROM books WHERE key=?", (key,)).fetchone()
        event = {"sequence": book["head_sequence"] + 1, "event": name, "journal_id": book["journal"],
            "target_key": json.loads(book["target_key"]), "plan_ref": plain(payload.get("plan_ref")),
            "owner_id": book["owner"], "generation": book["generation"], "recorded_at": now(),
            "payload": plain(payload), "previous_hash": book["head_hash"]}
        event["event_hash"] = digest(event)
        connection.execute("INSERT INTO events VALUES(?,?,?)", (key, event["sequence"], canonical(event).decode()))
        connection.execute("UPDATE books SET head_sequence=?,head_hash=? WHERE key=?",
            (event["sequence"], event["event_hash"], key))
        return event

    def effect_gate(self, target_key):
        from annotation.delivery.mock.persistent import BookEffectGate
        key = self.book_id(target_key)
        if key not in self._gates:
            self._gates[key] = BookEffectGate(self.directory / "gates" / (key + ".lock"), target_key, timeout=5)
        return self._gates[key]

    def _lease(self, connection, key, owner_id, generation, *, pending_ok=False):
        row = connection.execute("SELECT * FROM books WHERE key=?", (key,)).fetchone()
        if row is None or row["owner"] != owner_id or row["generation"] != generation or row["phase"] != "ACTIVE" or row["lease"] < time.time() or row["process_id"] != self.instance or row["pid"] != os.getpid():
            fail("OWNER_GENERATION_STALE", "current ACTIVE lease required", 4)
        if not pending_ok and self._pending(connection, key):
            fail("BOOK_WRITE_PAUSED", "current complete ledger has pending obligations", 3)
        if not pending_ok and row["hold"]:
            fail("TARGET_DRIFT_HOLD", row["hold"], 3)
        return row

    def _pending(self, connection, key, except_intent=None):
        rows = [dict(row) for row in connection.execute("SELECT * FROM intents WHERE book=? AND state='PENDING'", (key,))
                if row["id"] != except_intent]
        rows += [dict(row) for row in connection.execute("SELECT * FROM legacy WHERE book=?", (key,))]
        return rows

    def _handle(self, kind, **value):
        handle = Handle(kind=kind, instance=self.instance, **value)
        self._issued[id(handle)] = (handle, digest(handle))
        return handle

    def _opaque(self, handle, kind):
        saved = self._issued.get(id(handle))
        if not isinstance(handle, Handle) or saved is None or saved[0] is not handle or saved[1] != digest(handle) or handle.get("kind") != kind:
            fail("DISPATCH_PERMIT_INVALID", "opaque current-process handle required")
        return handle

    def _gate_check(self, gate, key):
        import threading
        if (gate is None or gate is not self._gates.get(key) or not getattr(gate, "held", False)
                or self.book_id(plain(gate.target_key)) != key
                or gate._local.get("thread") != threading.get_ident() or gate._local.get("depth", 0) < 1):
            fail("EFFECT_GATE_REQUIRED", "canonical held book gate required", 4)
        expected = (self.directory / "gates" / (key + ".lock")).resolve()
        if Path(gate.path).resolve() != expected or getattr(gate, "pid", os.getpid()) != os.getpid():
            fail("EFFECT_GATE_REQUIRED", "wrong gate identity", 4)

    @staticmethod
    def _pid_alive(pid):
        if pid == os.getpid():
            return True
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            process = kernel.OpenProcess(0x1000, False, int(pid or 0))
            if not process:
                # Only a nonexistent PID proves exit; access denied is unknown.
                return ctypes.get_last_error() != 87 and bool(pid)
            code = wintypes.DWORD()
            ok = kernel.GetExitCodeProcess(process, ctypes.byref(code))
            kernel.CloseHandle(process)
            return not ok or code.value == 259
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def claim(self, target_key, *, observer, owner_id=None):
        key, owner = self.book_id(target_key), owner_id or self.owner_id
        self.fault("BEFORE_CLAIM")
        with self.effect_gate(target_key).acquire() as gate:
            with self.transaction() as connection:
                row = connection.execute("SELECT * FROM books WHERE key=?", (key,)).fetchone()
                if row is None:
                    fail("REGISTRATION_BINDING_MISMATCH")
                if row["owner"]:
                    # Explicit release is allowed only by the original instance.
                    if row["lease"] > time.time() or self._pid_alive(row["pid"]):
                        fail("OWNER_BUSY", "lease expired AND previous process exited required", 4)
                generation = row["generation"] + 1
                if row["generation"]:
                    connection.execute("UPDATE plans SET status='INTERRUPTED' WHERE book=? AND status='RUNNING'", (key,))
                connection.execute("UPDATE books SET owner=?,generation=?,phase='CLAIMING',pid=?,process_id=?,lease=? WHERE key=?",
                    (owner, generation, os.getpid(), self.instance, time.time() + 10, key))
                event = self._event(connection, key, "OWNER_CLAIM_RESERVED", {})
                reservation = self._handle("claim", ledger_id=self.ledger_id, target_key=target_key,
                    owner_id=owner, generation=generation, target_store_id=self.target_store_id,
                    target_session_id=observer.target_session_id, predecessor_event_head=event)
                self.current_claim = reservation
            observer.activate_fence(target_key, target_session_id=observer.target_session_id,
                owner_id=owner, generation=generation, authority=self)
            with self.transaction() as connection:
                row = connection.execute("SELECT * FROM books WHERE key=?", (key,)).fetchone()
                if row["owner"] != owner or row["generation"] != generation or row["phase"] != "CLAIMING":
                    fail("OWNER_GENERATION_STALE", "claim CAS changed", 4)
                connection.execute("UPDATE books SET phase='ACTIVE' WHERE key=?", (key,))
                self._event(connection, key, "OWNER_ACTIVE", {})
            self._observers[key] = observer
        return Handle(owner_id=owner, generation=generation, target_key=target_key)

    def verify_claim(self, reservation, *, effect_gate):
        self._opaque(reservation, "claim")
        key = self.book_id(reservation["target_key"])
        self._gate_check(effect_gate, key)
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM books WHERE key=?", (key,)).fetchone()
            if row["phase"] != "CLAIMING" or row["owner"] != reservation["owner_id"] or row["generation"] != reservation["generation"]:
                fail("OWNER_GENERATION_STALE", "claim no longer current", 4)
        return reservation

    def renew(self, target_key, *, owner_id, generation):
        key = self.book_id(target_key)
        with self.effect_gate(target_key).acquire(), self.transaction() as connection:
            self._lease(connection, key, owner_id, generation, pending_ok=True)
            connection.execute("UPDATE books SET lease=? WHERE key=?", (time.time() + 10, key))

    def release(self, target_key, *, owner_id, generation):
        key = self.book_id(target_key)
        with self.effect_gate(target_key).acquire(), self.transaction() as connection:
            self._lease(connection, key, owner_id, generation, pending_ok=True)
            connection.execute("UPDATE books SET phase='RELEASED',lease=0,owner=NULL,pid=NULL WHERE key=?", (key,))
            self._event(connection, key, "OWNER_RELEASED", {})

    def accept_plan(self, registration_id, plan_ref, *, owner_id, generation):
        from annotation.contracts import assert_recovery_plan_ready, validate_recovery_bundle
        reg = self.registration(registration_id)
        self._guard_target_effect(reg["book"], owner_id, generation)
        bundle = validate_recovery_bundle(self.bundle(registration_id), asset_root=reg["package_root"])
        plan = plain(next(a for a in plain(bundle)["artifacts"] if reference(a) == plain(plan_ref)))
        key, plan_key = reg["book"], digest(plan_ref)
        with self.effect_gate(self.target_key(registration_id)).acquire(), self.transaction() as connection:
            self._lease(connection, key, owner_id, generation)
            if connection.execute("SELECT 1 FROM plans WHERE id=?", (plan_key,)).fetchone():
                fail("REPLAY_FORBIDDEN", "accepted plan is permanently reserved")
            assert_recovery_plan_ready(bundle, plan_ref, plan["payload"]["snapshot"])
            actions = plan["payload"]["actions"]
            for index, action in enumerate(actions):
                existing = connection.execute("SELECT digest FROM actions WHERE book=? AND id=?", (key, action["action_id"])).fetchone()
                if existing:
                    fail("INTENT_CONFLICT" if existing[0] != digest(action) else "REPLAY_FORBIDDEN")
                connection.execute("INSERT INTO actions VALUES(?,?,?,?,?,'RESERVED',NULL,NULL)",
                    (key, action["action_id"], digest(action), plan_key, index))
            connection.execute("INSERT INTO plans VALUES(?,?,?,?,?,0)",
                (plan_key, key, registration_id, canonical(plan_ref).decode(), "RUNNING"))
            bindings = [{"action_id": a["action_id"], "action_digest": digest(a)} for a in actions]
            self._event(connection, key, "PLAN_ACCEPTED", {"plan_ref": plan_ref, "actions": bindings})
            self._event(connection, key, "PLAN_ACTIONS_RESERVED", {"plan_ref": plan_ref, "reservations": bindings})
            self._event(connection, key, "PLAN_STARTED", {"plan_ref": plan_ref, "plan_state": "RUNNING"})
        return Handle(plan_ref=plan_ref, plan_id=plan_key, action_count=len(actions))

    def target_key(self, registration_id):
        reg = self.registration(registration_id)
        with self.connect() as connection:
            return json.loads(connection.execute("SELECT target_key FROM books WHERE key=?", (reg["book"],)).fetchone()[0])

    def _new_artifact(self, plan, kind, payload, dependencies, artifact_id=None):
        value = {key: copy.deepcopy(plan[key]) for key in
            ("schema_version", "run_id", "book_id", "scope_id", "producer")}
        value.update(artifact_id=artifact_id or unique(kind.lower()), revision=1, kind=kind,
            payload=plain(payload), input_refs=list({canonical(reference(a)): reference(a) for a in dependencies}.values()), created_at=now())
        value["producer"].update(module="a03-runtime", implementation_version="a03-p2")
        value["content_hash"] = digest(value)
        return value

    def _save_bundle(self, connection, registration_id, bundle):
        reg = self.registration(registration_id)
        path = self._file(Path(reg["package_root"]) / ("bundle-" + digest(bundle) + ".json"), canonical(bundle), connection)
        connection.execute("UPDATE registrations SET bundle_path=? WHERE id=?", (str(path), registration_id))

    def _append(self, connection, registration_id, *artifacts):
        current_path = connection.execute("SELECT bundle_path FROM registrations WHERE id=?", (registration_id,)).fetchone()[0]
        value = json.loads(Path(current_path).read_bytes())
        for artifact in artifacts:
            self._artifact(connection, artifact)
            if not any(reference(a) == reference(artifact) for a in value["artifacts"]):
                value["artifacts"].append(plain(artifact))
        self._save_bundle(connection, registration_id, value)

    def _evidence(self, connection, registration_id, resource):
        path = connection.execute("SELECT bundle_path FROM registrations WHERE id=?", (registration_id,)).fetchone()[0]
        bundle = json.loads(Path(path).read_bytes())
        identity = "proof-runtime-" + resource["sha256"][:40]
        record = {"evidence_id": identity, "resource": resource,
            "description": "SYNTHETIC actual controlled local observation; no platform evidence", "mode": "SYNTHETIC"}
        found = next((r for r in bundle["evidence"] if r["evidence_id"] == identity), None)
        if found and found != record:
            fail("HISTORY_ID_CONFLICT", "evidence identity differs")
        if not found:
            bundle["evidence"].append(record)
            self._save_bundle(connection, registration_id, bundle)
        return identity

    def import_resource(self, resource, source_root, registration_id, connection=None):
        source = Path(source_root).resolve()
        path = (source / resource["path"]).resolve()
        if source not in path.parents or not path.is_file() or path.is_symlink():
            fail("RESOURCE_MISSING", str(path), 5)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != resource["sha256"]:
            fail("RESOURCE_HASH_MISMATCH", str(path), 5)
        if resource["media_type"] != "application/json":
            fail("RESOURCE_FORMAT", "runtime observations require JSON")
        body = json.loads(raw)
        # Capture nested content before making a portable immutable copy.
        def visit(value):
            if isinstance(value, dict):
                if {"path", "sha256", "media_type"} <= set(value):
                    return self.import_resource(value, source, registration_id, connection)
                return {k: visit(v) for k, v in value.items() if k != "asset_root"}
            if isinstance(value, list):
                return [visit(v) for v in value]
            return value
        body = visit(body)
        return self.resource(body, registration_id, connection)

    def capture_observation(self, observation, observer, registration_id, connection=None):
        value = plain(observation)
        raw_resource = value.get("resource") or value.get("readback")
        resource = self.import_resource(raw_resource, value.get("asset_root", observer.asset_root), registration_id, connection)
        result = Handle(value)
        result["resource"] = result["readback"] = resource
        snapshot = None
        if value.get("read_status") == "OK" and value.get("scope_complete"):
            snapshot = plain(observer.snapshot_from_observation(observation))
            # An actual duplicate-identity read is retained as evidence, but
            # cannot be projected into a valid canonical PlatformSnapshot.
            from annotation.contracts import validate_recovery_bundle
            identities = [q["platform_question_id"] for q in snapshot["payload"]["questions"]]
            if len(identities) != len(set(identities)):
                snapshot = None
            else:
                candidate = self.bundle(registration_id)
                candidate["artifacts"].append(snapshot)
                validate_recovery_bundle(candidate, asset_root=self.registration(registration_id)["package_root"])
            if snapshot is not None:
                result["snapshot_ref"] = reference(snapshot)
        self._observations[value["observation_id"]] = (observation, observer, registration_id, resource, snapshot)
        return result, snapshot

    def _guard_target_effect(self, key, owner_id, generation):
        with self.connect() as connection:
            book = self._lease(connection, key, owner_id, generation, pending_ok=True)
            target_key = json.loads(book["target_key"])
        self.detect_target_drift(target_key, owner_id=owner_id, generation=generation)
        with self.connect() as connection:
            row = connection.execute("SELECT hold FROM books WHERE key=?", (key,)).fetchone()
            if row["hold"]:
                fail("TARGET_DRIFT_HOLD", row["hold"], 3)

    def _verify_prepared(self, prepared, registration, plan_ref, *, observation_binding=None):
        from annotation.runtime.recovery import configuration
        observer = self._observers.get(registration["book"])
        if observer is None:
            fail("PREPARED_ACTION_UNVERIFIED", "current controlled observer is required")
        checked = observer.verify_prepared_action(prepared, observation_binding=observation_binding,
            expected_config_version=configuration(json.loads(registration["config"])).version, expected_plan_ref=plan_ref)
        if (checked.target_store_id != self.target_store_id or checked.target_session_id != registration["session"]
                or checked.target_key != self.target_key(registration["id"])
                or checked.scope_id != registration["scope"] or checked.source_ref != json.loads(registration["source"])):
            fail("INTENT_BINDING_MISMATCH", "native preparation differs from registered target")
        return checked

    def _verify_intent_prepared(self, intent, plan, *, prepared_action=None, observation_binding=None):
        native = self._prepared_intents.get(intent["id"])
        if native is None or (prepared_action is not None and native[0] is not prepared_action):
            fail("PREPARED_ACTION_UNVERIFIED", "persisted intent copies do not recreate dispatch authority")
        checked = self._verify_prepared(native[0], self.registration(plan["registration"]),
            json.loads(plan["ref"]), observation_binding=observation_binding)
        if checked.attestation_digest != native[1] or checked.action_id != intent["action"]:
            fail("OBSERVATION_BINDING_MISMATCH", "native preparation differs from committed intent")
        return checked

    def commit_intent(self, prepared_action, *, owner_id, generation):
        p = prepared_action
        key, action_id = self.book_id(plain(p["target_key"])), p["action_id"]
        self._guard_target_effect(key, owner_id, generation)
        self.fault("BEFORE_INTENT_COMMIT")
        with self.effect_gate(plain(p["target_key"])).acquire(), self.transaction() as connection:
            book = self._lease(connection, key, owner_id, generation)
            action = connection.execute("SELECT * FROM actions WHERE book=? AND id=?", (key, action_id)).fetchone()
            if action is None or action["digest"] != p["action_digest"]:
                fail("PLAN_ACTION_MISMATCH")
            plan_row = connection.execute("SELECT * FROM plans WHERE id=?", (action["plan"],)).fetchone()
            if plan_row["status"] != "RUNNING":
                fail("PLAN_INTERRUPTED")
            if action["state"] != "RESERVED" or action["position"] != plan_row["cursor"]:
                fail("REPLAY_FORBIDDEN")
            reg = self.registration(plan_row["registration"])
            checked = self._verify_prepared(p, reg, json.loads(plan_row["ref"]))
            prepared = self.import_resource(plain(p["prepared_before"]), p["asset_root"], reg["id"], connection)
            plan = plain(p["plan"])
            fresh_snapshot = plain(p.get("snapshot"))
            if fresh_snapshot:
                self._append(connection, reg["id"], fresh_snapshot)
            action_value = plain(p["action"])
            payload = {"plan_ref": plain(p["plan_ref"]), "action_id": action_id, "action_digest": p["action_digest"],
                "target_key": plain(p["target_key"]), "question_id": action_value["target"]["question_id"],
                "source_entity_ids": action_value["source_entity_ids"], "before_snapshot_ref": plain(p["before_snapshot_ref"]),
                "target_session_id": reg["session"], "source_ref": json.loads(reg["source"]),
                "prepared_before": prepared, "execution_mode": "SIMULATED", "journal_id": book["journal"],
                "journal_sequence": book["head_sequence"] + 1, "journal_head_hash": book["head_hash"],
                "owner_id": owner_id, "generation": generation, "intent_committed_at": now(),
                "plan_dependency_digest": ""}
            from annotation.contracts.recovery import plan_dependency_digest
            payload["plan_dependency_digest"] = plan_dependency_digest(plan, payload["source_ref"], reg["session"], prepared)
            dependencies = [a for a in self.bundle(reg["id"])["artifacts"] if a["book_id"] == plan["book_id"] and a["scope_id"] == plan["scope_id"]]
            if fresh_snapshot:
                dependencies.append(fresh_snapshot)
            artifact = self._new_artifact(plan, "WriteIntent", payload, dependencies)
            intent_ref = self._artifact(connection, artifact)
            self._append(connection, reg["id"], artifact)
            obligation = "obl-" + digest({k: payload[k] for k in ("journal_id", "target_key", "journal_sequence", "journal_head_hash")} | {"intent_ref": intent_ref})
            iid = unique("intent")
            path = self.object({"prepared": {k: plain(v) for k, v in p.items() if k not in ("bundle",)}, "intent": artifact}, connection)
            connection.execute("INSERT INTO intents VALUES(?,?,?,?,?,?,?,?,?,?,NULL)",
                (iid, key, action["plan"], action_id, canonical(intent_ref).decode(), obligation, str(path), "PENDING", owner_id, generation))
            connection.execute("UPDATE actions SET state='INTENT',intent=? WHERE book=? AND id=?", (iid, key, action_id))
            self._event(connection, key, "WRITE_INTENT_COMMITTED", {"plan_ref": p["plan_ref"], "action_id": action_id,
                "action_digest": p["action_digest"], "intent_ref": intent_ref, "obligation_id": obligation})
        self._prepared_intents[iid] = (p, checked.attestation_digest)
        self.fault("AFTER_INTENT_COMMIT")
        return self._handle("intent", id=iid, intent_ref=intent_ref, artifact=artifact, obligation_id=obligation,
            target_key=plain(p["target_key"]), owner_id=owner_id, generation=generation, registration_id=reg["id"])

    def _plan(self, registration_id, plan_id=None):
        bundle = self.bundle(registration_id)
        plans = [a for a in bundle["artifacts"] if a["kind"] == "ApplyPlan" and (not plan_id or digest(reference(a)) == plan_id)]
        if not plans:
            fail("MISSING_REFERENCE", "ApplyPlan absent")
        return plans[-1]

    def _fact(self, connection, reg, plan, action_id, result, *, intent=None, prepared=None,
              snapshot_ref=None, readback=None, basis=None):
        book = connection.execute("SELECT * FROM books WHERE key=?", (reg["book"],)).fetchone()
        action = next(a for a in plan["payload"]["actions"] if a["action_id"] == action_id)
        fact = {"format_version": "a03-action-fact-1", "design_only": False,
            "origin_phase": "UNATTEMPTED_ABSENCE" if intent is None else "EXECUTION", "resolution_ref": None,
            "plan_ref": reference(plan), "intent_ref": json.loads(intent["ref"]) if intent else None,
            "obligation_id": intent["obligation"] if intent else None, "action_id": action_id,
            "action_digest": digest(action), "prepared_before": prepared,
            "observed_snapshot_ref": snapshot_ref, "readback": readback, "comparator_version": "a02-facts-1",
            "result": result, "journal_sequence": book["head_sequence"] + 1,
            "predecessor_hash": book["head_hash"], "unattempted_basis": basis}
        return fact, self.resource(fact, reg["id"], connection)

    @staticmethod
    def _comparison(comparison):
        comparison = plain(comparison)
        classification = comparison.get("classification") or comparison.get("observation") or comparison.get("effect_match")
        if classification is None:
            classification = {"APPLIED": "MATCH", "NOT_APPLIED": "ABSENT", "UNKNOWN": "INDETERMINATE"}.get(comparison.get("outcome"), "INDETERMINATE")
        outcome = {"MATCH": "APPLIED", "ABSENT": "NOT_APPLIED"}.get(classification, "UNKNOWN")
        return classification, outcome, comparison.get("platform_ids", []), comparison.get("reason", comparison.get("reason_code", classification))

    def commit_action_result(self, committed_intent, prepared_action, observation, comparison, *, owner_id, generation):
        handle = self._opaque(committed_intent, "intent")
        reg = self.registration(handle["registration_id"])
        key, plan = reg["book"], plain(prepared_action["plan"])
        observer = self._observers[key]
        captured, snapshot = self.capture_observation(observation, observer, reg["id"])
        classification, outcome, platform_ids, reason = self._comparison(comparison)
        with self.effect_gate(handle["target_key"]).acquire(), self.transaction() as connection:
            self._lease(connection, key, owner_id, generation, pending_ok=True)
            intent = connection.execute("SELECT * FROM intents WHERE id=?", (handle["id"],)).fetchone()
            plan_row = connection.execute("SELECT * FROM plans WHERE id=?", (intent["plan"],)).fetchone()
            if intent["owner"] != owner_id or intent["generation"] != generation or intent["state"] != "PENDING" or plan_row["status"] != "RUNNING":
                fail("PLAN_INTERRUPTED", "original current RUNNING intent required")
            self._verify_intent_prepared(intent, plan_row, prepared_action=prepared_action)
            from annotation.delivery.mock import compare_action
            original_before = self.read_resource(handle["artifact"]["payload"]["prepared_before"], reg["id"])
            checked = self._comparison(compare_action(prepared_action["action"], original_before, observation))
            if checked[:3] != (classification, outcome, platform_ids):
                fail("OBSERVATION_BINDING_MISMATCH", "caller comparison differs from public comparator")
            if observation["observed_at"] <= handle["artifact"]["payload"]["intent_committed_at"]:
                fail("OBSERVATION_NOT_FRESH", "result read predates committed intent")
            if snapshot:
                self._append(connection, reg["id"], snapshot)
            prepared = handle["artifact"]["payload"]["prepared_before"]
            before_id = self._evidence(connection, reg["id"], prepared)
            after_id = self._evidence(connection, reg["id"], captured["readback"])
            result = {"action_id": intent["action"], "outcome": outcome, "platform_ids": platform_ids,
                "before_evidence_refs": [before_id], "after_evidence_refs": [after_id], "readback": captured["readback"],
                "effect_match": "INDETERMINATE" if outcome == "UNKNOWN" else classification,
                "next_step": {"APPLIED": "POSTCHECK", "NOT_APPLIED": "RECHECK_TARGET", "UNKNOWN": "RECONCILE"}[outcome],
                "replay_allowed": False, "reason": classification + ": " + str(reason), "attempt_fact": "MAY_HAVE_BEEN_ATTEMPTED" if outcome == "UNKNOWN" else "ATTEMPTED",
                "attempt_evidence_refs": [captured["resource"]], "intent_ref": handle["intent_ref"]}
            fact, resource = self._fact(connection, reg, plan, intent["action"], result, intent=intent,
                prepared=prepared, snapshot_ref=reference(snapshot) if snapshot else None, readback=captured["resource"])
            connection.execute("UPDATE actions SET state=?,fact=? WHERE book=? AND id=?", (outcome, canonical(resource).decode(), key, intent["action"]))
            connection.execute("UPDATE intents SET state=? WHERE id=?", ("PENDING" if outcome == "UNKNOWN" else outcome, intent["id"]))
            if outcome == "APPLIED":
                connection.execute("UPDATE plans SET cursor=cursor+1 WHERE id=?", (intent["plan"],))
            else:
                connection.execute("UPDATE plans SET status='INTERRUPTED' WHERE id=?", (intent["plan"],))
            event = self._event(connection, key, "ACTION_RESULT_COMMITTED", {"plan_ref": reference(plan),
                "action_id": intent["action"], "action_digest": fact["action_digest"], "intent_ref": handle["intent_ref"],
                "obligation_id": intent["obligation"], "fact": resource, "outcome": outcome,
                "plan_state": "INTERRUPTED" if outcome != "APPLIED" else "RUNNING"})
        projection = self.project_plan(reg["id"], plan)
        if projection["receipt_ref"] is not None:
            self.fault("AFTER_RECEIPT_COMMIT")
        return Handle(fact=resource, event=event, result=result, progress=projection)

    def project_plan(self, registration_id, plan=None):
        with self.effect_gate(self.target_key(registration_id)).acquire():
            return self._project_plan_locked(registration_id, plan)

    def _project_plan_locked(self, registration_id, plan=None):
        reg, plan = self.registration(registration_id), plan or self._plan(registration_id)
        plan_id = digest(reference(plan))
        with self.transaction() as connection:
            rows = connection.execute("SELECT * FROM actions WHERE plan=? ORDER BY position", (plan_id,)).fetchall()
            if not rows:
                return {"actions": [], "state": "NO_ACTIONS"}
            bundle = self.bundle(registration_id)
            dependencies = [a for a in bundle["artifacts"] if a["book_id"] == plan["book_id"] and a["scope_id"] == plan["scope_id"]]
            receipt = None
            if all(row["fact"] for row in rows):
                resources = [json.loads(row["fact"]) for row in rows]
                facts = [self.read_resource(r, registration_id) for r in resources]
                unknown = [f for f in facts if f["result"]["outcome"] == "UNKNOWN"]
                issues = [{"issue_id": "issue-save-unknown-" + digest(f)[:32], "code": "SAVE_UNKNOWN",
                    "scope_type": "action", "scope_id": f["action_id"],
                    "evidence_refs": f["result"]["after_evidence_refs"] or f["result"]["before_evidence_refs"],
                    "severity": "blocking", "blocks": ["APPLY", "COMPLETE"],
                    "suggested_strategy": {"strategy_id": "RECONCILE", "max_attempts": 0, "max_cost": 0.0},
                    "reason": "Actual controlled read did not establish this action's effect; retain original UNKNOWN"}
                    for f in unknown]
                payload = {"plan": reference(plan), "execution_mode": "SIMULATED", "results": [f["result"] for f in facts],
                    "action_fact_refs": resources, "unresolved_issue_ids": [i["issue_id"] for i in issues],
                    "write_disposition": "PAUSE_RECONCILE" if any(f["result"]["outcome"] == "UNKNOWN" for f in facts) else "POSTCHECK" if all(f["result"]["outcome"] == "APPLIED" for f in facts) else "RECHECK_TARGET"}
                receipt = next((a for a in dependencies if a["kind"] == "ExecutionReceipt"
                    and a["payload"]["plan"] == reference(plan) and a["payload"].get("action_fact_refs") == resources), None)
                if receipt is None:
                    receipt = self._new_artifact(plan, "ExecutionReceipt", payload, dependencies)
                    self._append(connection, registration_id, receipt)
                    dependencies.append(receipt)
                    if issues:
                        pre = next(a for a in dependencies if reference(a) == plan["payload"]["precheck"])
                        proof = list(dict.fromkeys(e for i in issues for e in i["evidence_refs"]))
                        post = self._new_artifact(plan, "CheckReport", {"stage": "POST_APPLY",
                            "subject": reference(receipt), "graph": plan["payload"]["graph"],
                            "policy": plan["payload"]["policy"], "snapshot": facts[-1]["observed_snapshot_ref"],
                            "receipt": reference(receipt), "coverage": pre["payload"]["coverage"],
                            "checks": [{"check_id": name, "outcome": "UNAVAILABLE", "evidence_refs": proof,
                                "reason": "Original save result remains UNKNOWN"} for name in ("frame_structure", "final_content")],
                            "issues": issues, "decision": "HOLD", "reason": "Actual UNKNOWN facts require read-only reconciliation",
                            "recovery_refs": []}, dependencies)
                        self._append(connection, registration_id, post)
                        dependencies.append(post)
                for row in rows:
                    if row["intent"]:
                        connection.execute("UPDATE intents SET receipt=? WHERE id=? AND receipt IS NULL", (canonical(reference(receipt)).decode(), row["intent"]))
            book = connection.execute("SELECT * FROM books WHERE key=?", (reg["book"],)).fetchone()
            items = []
            for row in rows:
                intent = connection.execute("SELECT * FROM intents WHERE id=?", (row["intent"],)).fetchone() if row["intent"] else None
                resolution = connection.execute("SELECT * FROM resolutions WHERE intent=? ORDER BY rowid DESC LIMIT 1", (row["intent"],)).fetchone() if row["intent"] else None
                effective = {"RESOLVED_APPLIED": "APPLIED", "RESOLVED_NOT_APPLIED": "NOT_APPLIED"}.get(resolution["outcome"] if resolution else "", row["state"] if row["state"] in ("APPLIED", "NOT_APPLIED") else "UNDETERMINED" if not intent else "UNKNOWN")
                items.append({"action_id": row["id"], "intent_ref": json.loads(intent["ref"]) if intent else None,
                    "attempt_fact": "NOT_ATTEMPTED" if not intent else "MAY_HAVE_BEEN_ATTEMPTED" if row["state"] in ("INTENT", "UNKNOWN") else "ATTEMPTED",
                    "dependency_status": "SATISFIED" if row["position"] == 0 or all(x["state"] == "APPLIED" for x in rows[:row["position"]]) else "BLOCKED",
                    "attempt_evidence_refs": [], "receipt_ref": reference(receipt) if receipt else json.loads(intent["receipt"]) if intent and intent["receipt"] else None,
                    "resolution_head_ref": json.loads(resolution["ref"]) if resolution else None, "effective_outcome": effective,
                    "result_fact": json.loads(row["fact"]) if row["fact"] else None})
            progress = self._new_artifact(plan, "ExecutionProgress", {"plan_ref": reference(plan), "journal_id": book["journal"],
                "journal_head_sequence": book["head_sequence"], "journal_head_hash": book["head_hash"], "actions": items}, dependencies)
            self._append(connection, registration_id, progress)
            if all(row["state"] == "APPLIED" for row in rows):
                connection.execute("UPDATE plans SET status='FINISHED' WHERE id=?", (plan_id,))
        return {"progress_ref": reference(progress), "receipt_ref": reference(receipt) if receipt else None, "actions": items}

    def load_book_context(self, target_key, *, owner_id, generation):
        self.verify_integrity()
        key = self.book_id(target_key)
        with self.connect() as connection:
            book = self._lease(connection, key, owner_id, generation, pending_ok=True)
            histories = [dict(row) for row in connection.execute("SELECT * FROM registrations WHERE book=?", (key,))]
            refs = [json.loads(row[0]) for row in connection.execute("SELECT ref FROM artifacts WHERE book=?", (target_key["book_id"],))]
            progress = []
            for row in connection.execute("SELECT path FROM artifacts WHERE book=?", (target_key["book_id"],)):
                artifact = json.loads(Path(row[0]).read_bytes())
                if artifact["kind"] == "ExecutionProgress":
                    progress.append(reference(artifact))
            context = self._handle("context", ledger_id=self.ledger_id, target_key=target_key,
                owner_id=owner_id, generation=generation, event_head={"sequence": book["head_sequence"], "hash": book["head_hash"]},
                history_refs=refs, registrations=histories, pending=self._pending(connection, key),
                pause_reasons=[r.get("classification", "UNKNOWN") for r in self._pending(connection, key)], progress_refs=progress,
                target_store_id=self.target_store_id)
        return context

    def verify_context(self, context, *, target_key, expected_ledger_id, effect_gate):
        self._opaque(context, "context")
        key = self.book_id(target_key)
        self._gate_check(effect_gate, key)
        if expected_ledger_id != self.ledger_id or context["target_key"] != target_key:
            fail("BOOK_CONTEXT_UNVERIFIED")
        actual = self.load_book_context(target_key, owner_id=context["owner_id"], generation=context["generation"])
        if any(actual[k] != context[k] for k in ("event_head", "pending", "history_refs")):
            fail("BOOK_CONTEXT_UNVERIFIED", "current full scan differs")
        return actual

    def status(self, registration_id=None):
        reg = self.registration(registration_id)
        self.verify_integrity()
        with self.connect() as connection:
            book = dict(connection.execute("SELECT * FROM books WHERE key=?", (reg["book"],)).fetchone())
            pending = self._pending(connection, reg["book"])
            events = [json.loads(row[0]) for row in connection.execute("SELECT body FROM events WHERE book=? ORDER BY sequence", (reg["book"],))]
            actions = [dict(row) for row in connection.execute("SELECT * FROM actions WHERE book=? ORDER BY rowid", (reg["book"],))]
        return {"ledger_id": self.ledger_id, "registration_id": reg["id"], "target_key": json.loads(book["target_key"]),
            "owner_id": book["owner"], "generation": book["generation"], "owner_phase": book["phase"], "lease_until": book["lease"],
            "pending_count": len(pending), "pending": pending, "paused": bool(pending) or bool(book["hold"]),
            "events": events, "actions": actions, "event_head": {"sequence": book["head_sequence"], "hash": book["head_hash"]},
            "target_drift_hold": book["hold"]}

    def import_history_archive(self, package_path, *, expected_ledger_id, target_key):
        from annotation.contracts import load_archive_bundle
        if expected_ledger_id != self.ledger_id:
            fail("STATE_DIRECTORY_IDENTITY_MISMATCH")
        archive = load_archive_bundle(package_path)
        value = plain(archive)
        if "bundle" in value:
            value = value["bundle"]
        for snapshot in (a for a in value["artifacts"] if a["kind"] == "PlatformSnapshot" and a["book_id"] == target_key["book_id"]):
            if snapshot["payload"]["target_id"] != target_key["target_id"]:
                fail("TARGET_IDENTITY_MISMATCH", "archive target differs from requested canonical book")
        original_path = Path(package_path).resolve()
        original_bytes = original_path.read_bytes()
        archive_root = self.directory / "archives" / hashlib.sha256(original_bytes).hexdigest()
        self._file(archive_root / "input.json", original_bytes)
        seen = set()
        def copy_declared(node):
            if isinstance(node, list):
                for item in node:
                    copy_declared(item)
            elif isinstance(node, dict):
                if {"path", "sha256"} <= set(node) and node["path"] not in seen:
                    seen.add(node["path"])
                    source = (original_path.parent / node["path"]).resolve()
                    if original_path.parent not in source.parents or not source.is_file() or source.is_symlink():
                        fail("RESOURCE_MISSING", node["path"], 5)
                    raw = source.read_bytes()
                    if hashlib.sha256(raw).hexdigest() != node["sha256"]:
                        fail("RESOURCE_HASH_MISMATCH", node["path"], 5)
                    self._file(archive_root / node["path"], raw)
                    if node.get("media_type") == "application/json":
                        copy_declared(json.loads(raw))
                for child in node.values():
                    copy_declared(child)
        copy_declared(value)
        key = self.book_id(target_key)
        resource = self.object({"eligibility": "ARCHIVE_ONLY", "bundle": value,
            "archive_root": str(archive_root), "original_sha256": hashlib.sha256(original_bytes).hexdigest()})
        rows = []
        with self.transaction() as connection:
            if not connection.execute("SELECT 1 FROM books WHERE key=?", (key,)).fetchone():
                connection.execute("INSERT INTO books(key,target_key,journal,head_hash) VALUES(?,?,?,?)", (key, canonical(target_key).decode(), unique("journal"), ZERO))
            for artifact in value["artifacts"]:
                self._artifact(connection, artifact)
                if artifact["kind"] == "ExecutionReceipt" and artifact["book_id"] == target_key["book_id"]:
                    for result in artifact["payload"]["results"]:
                        if result["outcome"] == "UNKNOWN":
                            identity = digest({"receipt": reference(artifact), "action": result["action_id"]})
                            connection.execute("INSERT OR IGNORE INTO legacy VALUES(?,?,?,?,?)", (identity, key, artifact["scope_id"], "LEGACY_UNRECORDED", str(resource)))
                            rows.append(identity)
            self._event(connection, key, "HISTORY_ARCHIVE_IMPORTED", {"archive_sha256": digest(value), "legacy_ids": rows})
        return {"archive_only": True, "legacy_ids": rows, "classification": "LEGACY_UNRECORDED" if rows else "ARCHIVE_ONLY"}

    def begin_recovery_call(self, target_key, call_id=None):
        key, call_id = self.book_id(target_key), call_id or unique("recovery-call")
        with self.transaction() as connection:
            old = connection.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
            if old:
                if old["book"] != key:
                    fail("RECOVERY_CALL_CONFLICT")
                return dict(old)
            queue = [row["id"] for row in connection.execute("SELECT id FROM intents WHERE book=? AND state='PENDING' ORDER BY rowid", (key,))]
            connection.execute("INSERT INTO calls VALUES(?,?,?,?)", (call_id, key, canonical(queue).decode(), time.time()))
        return {"id": call_id, "book": key, "queue": canonical(queue).decode(), "created": time.time()}

    def register_attempt(self, call_id, intent_id, *, owner_id, generation):
        with self.transaction() as connection:
            call = connection.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
            if not call or intent_id not in json.loads(call["queue"]):
                fail("RECOVERY_CALL_CONFLICT")
            self._lease(connection, call["book"], owner_id, generation, pending_ok=True)
            if time.time() - call["created"] >= 60:
                fail("RECOVERY_DEADLINE_EXCEEDED", "persisted call deadline exhausted", 6)
            window = connection.execute("SELECT started FROM attempt_windows WHERE call_id=? AND intent=?", (call_id, intent_id)).fetchone()
            if window and time.time() - window[0] >= 8:
                fail("RECOVERY_DEADLINE_EXCEEDED", "persisted intent window exhausted", 6)
            connection.execute("INSERT OR IGNORE INTO attempt_windows VALUES(?,?,?)", (call_id, intent_id, time.time()))
            count = connection.execute("SELECT COUNT(*) FROM attempts WHERE call_id=? AND intent=?", (call_id, intent_id)).fetchone()[0]
            if count >= 3:
                fail("RECONCILE_ATTEMPT_LIMIT", "persisted per-call attempts exhausted", 3)
            number = count + 1
            connection.execute("INSERT INTO attempts VALUES(?,?,?,'STARTED',NULL)", (call_id, intent_id, number))
        return number

    def intent_remaining_seconds(self, call_id, intent_id):
        with self.connect() as connection:
            row = connection.execute("SELECT started FROM attempt_windows WHERE call_id=? AND intent=?", (call_id, intent_id)).fetchone()
        return 8 if not row else max(0, 8 - (time.time() - row[0]))

    def pending_intent(self, intent_id):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM intents WHERE id=?", (intent_id,)).fetchone()
        if row is None:
            fail("LOCAL_INTENT_COMMIT_REQUIRED")
        return dict(row)

    def fail_attempt(self, call_id, intent_id, number, failure, registration_id):
        with self.transaction() as connection:
            resource = self.resource({"origin": "SYNTHETIC", "execution_mode": "SIMULATED",
                "failure": plain(failure), "read_sequence": None, "target_state_version": None,
                "target_state_hash": None}, registration_id, connection)
            connection.execute("UPDATE attempts SET status='FAILED_READ',resource=? WHERE call_id=? AND intent=? AND number=?",
                (canonical(resource).decode(), call_id, intent_id, number))
        return resource

    def commit_reconciliation(self, result, *, owner_id, generation):
        from annotation.contracts import validate_recovery_bundle
        result = plain(result)
        payload = result["payload"]
        registered = self._observations.get(payload["observation_id"])
        if registered is None:
            fail("OBSERVATION_NOT_FRESH", "only current controlled target reads can be committed")
        original, observer, registration_id, resource, snapshot = registered
        reg = self.registration(registration_id)
        key = reg["book"]
        deadline = self._observation_deadlines.get(payload["observation_id"])
        if deadline is None or time.monotonic() >= deadline:
            fail("RECOVERY_DEADLINE_EXCEEDED", "actual observation call deadline absent/expired", 6)
        with self.effect_gate(self.target_key(registration_id)).acquire(), self.transaction() as connection:
            self._lease(connection, key, owner_id, generation, pending_ok=True)
            row = connection.execute("SELECT * FROM intents WHERE ref=?", (canonical(payload["intent_ref"]).decode(),)).fetchone()
            if not row or row["book"] != key or row["obligation"] != payload["obligation_id"] or row["state"] != "PENDING":
                fail("INTENT_BINDING_MISMATCH")
            attempt = connection.execute("SELECT * FROM attempts WHERE call_id=? AND intent=? AND number=?",
                (payload["recovery_call_id"], row["id"], payload["attempt_index"])).fetchone()
            if not attempt or attempt["status"] != "STARTED":
                fail("RECONCILE_ATTEMPT_LIMIT")
            previous = connection.execute("SELECT * FROM resolutions WHERE intent=? ORDER BY rowid DESC LIMIT 1", (row["id"],)).fetchone()
            if payload["previous_resolution_ref"] != (json.loads(previous["ref"]) if previous else None):
                fail("RESOLUTION_FORK")
            if payload["readback"] != resource or (snapshot and payload["observed_snapshot_ref"] != reference(snapshot)):
                fail("OBSERVATION_BINDING_MISMATCH")
            from annotation.delivery.reconciler import reconcile_action
            stored = json.loads(Path(row["prepared"]).read_bytes())
            before = self.read_resource(stored["intent"]["payload"]["prepared_before"], registration_id)
            recomputed = plain(reconcile_action(stored["prepared"]["action"], before, original))
            if (payload["observation"], payload["resolution"], payload["platform_ids"]) != (recomputed["effect_match"], recomputed["resolution"], recomputed["platform_ids"]):
                fail("OBSERVATION_BINDING_MISMATCH", "resolution differs from actual public comparator")
            bundle = self.bundle(registration_id)
            if snapshot and not any(reference(a) == reference(snapshot) for a in bundle["artifacts"]):
                bundle["artifacts"].append(snapshot)
            candidate = copy.deepcopy(bundle)
            candidate["artifacts"].append(result)
            validate_recovery_bundle(candidate, asset_root=reg["package_root"])
            if time.monotonic() >= deadline:
                fail("RECOVERY_DEADLINE_EXCEEDED", "deadline reached before terminal transaction", 6)
            self._append(connection, registration_id, *([snapshot] if snapshot else []), result)
            terminal = payload["resolution"] != "STILL_UNKNOWN"
            connection.execute("INSERT INTO resolutions VALUES(?,?,?,?)", (result["artifact_id"], row["id"], canonical(reference(result)).decode(), payload["resolution"]))
            connection.execute("UPDATE attempts SET status=?,resource=? WHERE call_id=? AND intent=? AND number=?",
                (payload["resolution"], canonical(resource).decode(), payload["recovery_call_id"], row["id"], payload["attempt_index"]))
            if terminal:
                connection.execute("UPDATE intents SET state=? WHERE id=?", (payload["resolution"], row["id"]))
            event = self._event(connection, key, "RECONCILIATION_COMMITTED", {"plan_ref": payload["plan_ref"],
                "action_id": payload["action_id"], "action_digest": payload["action_digest"], "intent_ref": payload["intent_ref"],
                "obligation_id": payload["obligation_id"], "resolution_ref": reference(result), "observation_id": payload["observation_id"],
                "resolution": payload["resolution"], "plan_state": "INTERRUPTED"})
        self.project_plan(registration_id, self._plan(registration_id, row["plan"]))
        return Handle(result_ref=reference(result), resolution=payload["resolution"], classification=payload["observation"], event=event)

    def export(self, registration_id=None):
        reg = self.registration(registration_id)
        result = self.status(reg["id"])
        result.update(bundle=self.bundle(reg["id"]), package_root=reg["package_root"], database=str(self.database))
        with self.connect() as connection:
            calls = [dict(row) for row in connection.execute("SELECT * FROM calls WHERE book=?", (reg["book"],))]
            for call in calls:
                call["intent_queue"] = []
                for iid in json.loads(call["queue"]):
                    attempts = [dict(row) for row in connection.execute("SELECT * FROM attempts WHERE call_id=? AND intent=? ORDER BY number", (call["id"], iid))]
                    call["intent_queue"].append({"intent_id": iid, "status": attempts[-1]["status"] if attempts else "NOT_VISITED", "attempts": attempts})
            result["recovery_calls"] = calls
        return result

    def commit_unattempted_absence(self, bundle, request, *, owner_id, generation, asset_root, observer):
        # Frozen R2 only models one same-plan journal from sequence one. Do not
        # rewrite real ledger coordinates or omit control events to fit it.
        fail("EVENT_PREFIX_CONTRACT_GAP", "P2 global prefix profile requires explicit coordinator approval", 2)


    def issue_first_dispatch(self, intent_ref, *, owner_id, generation, plan_ref, action_id, observation_binding):
        with self.connect() as connection:
            current = connection.execute("SELECT book FROM intents WHERE ref=?", (canonical(intent_ref).decode(),)).fetchone()
        if current is None:
            fail("LOCAL_INTENT_COMMIT_REQUIRED")
        self._guard_target_effect(current["book"], owner_id, generation)
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM intents WHERE ref=?", (canonical(intent_ref).decode(),)).fetchone()
            if row is None:
                fail("LOCAL_INTENT_COMMIT_REQUIRED")
            self._lease(connection, row["book"], owner_id, generation, pending_ok=True)
            if self._pending(connection, row["book"], row["id"]):
                fail("BOOK_WRITE_PAUSED")
            plan = connection.execute("SELECT * FROM plans WHERE id=?", (row["plan"],)).fetchone()
            if (row["owner"] != owner_id or row["generation"] != generation or plan["status"] != "RUNNING"
                    or row["action"] != action_id or json.loads(plan["ref"]) != plain(plan_ref)):
                fail("PLAN_INTERRUPTED")
            self._verify_intent_prepared(row, plan, observation_binding=observation_binding)
            if connection.execute("SELECT 1 FROM permits WHERE intent=?", (row["id"],)).fetchone():
                fail("REPLAY_FORBIDDEN")
            token = unique("permit")
            event = self._event(connection, row["book"], "DISPATCH_PERMIT_ISSUED", {"plan_ref": plan_ref,
                "action_id": action_id, "intent_ref": intent_ref, "permit_id": token})
            connection.execute("INSERT INTO permits VALUES(?,?,'ISSUED',?)", (token, row["id"], event["event_hash"]))
        return self._handle("permit", token=token, intent_id=row["id"], target_key=self.target_key(plan["registration"]),
            owner_id=owner_id, generation=generation, intent_ref=plain(intent_ref), obligation_id=row["obligation"])

    def consume_first_dispatch(self, permit, *, effect_gate, prepared_action, target_store_id, target_session_id):
        self._opaque(permit, "permit")
        key = self.book_id(permit["target_key"])
        self._gate_check(effect_gate, key)
        self._guard_target_effect(key, permit["owner_id"], permit["generation"])
        with self.transaction() as connection:
            self._lease(connection, key, permit["owner_id"], permit["generation"], pending_ok=True)
            row = connection.execute("SELECT * FROM permits WHERE token=?", (permit["token"],)).fetchone()
            intent = connection.execute("SELECT * FROM intents WHERE id=?", (permit["intent_id"],)).fetchone()
            if row is None or row["state"] != "ISSUED" or self._pending(connection, key, intent["id"]):
                fail("REPLAY_FORBIDDEN")
            plan = connection.execute("SELECT * FROM plans WHERE id=?", (intent["plan"],)).fetchone()
            reg = self.registration(plan["registration"])
            self._verify_intent_prepared(intent, plan, prepared_action=prepared_action)
            if (target_store_id != self.target_store_id or target_session_id != reg["session"] or
                prepared_action["action_id"] != intent["action"] or prepared_action["action_digest"] !=
                plain(json.loads(Path(intent["prepared"]).read_bytes())["intent"])["payload"]["action_digest"]):
                fail("INTENT_BINDING_MISMATCH")
            connection.execute("UPDATE permits SET state='CONSUMED' WHERE token=?", (permit["token"],))
            for name in ("DISPATCH_PERMIT_CONSUMED", "DISPATCH_STARTED"):
                event = self._event(connection, key, name, {"plan_ref": json.loads(plan["ref"]),
                    "action_id": intent["action"], "intent_ref": json.loads(intent["ref"]), "permit_id": permit["token"]})
        self.fault("AFTER_DISPATCH_STARTED")
        return self._handle("authorization", **{k: v for k, v in permit.items() if k not in ("kind", "instance")},
            action_digest=prepared_action["action_digest"], target_store_id=target_store_id,
            target_session_id=target_session_id, dispatch_event=event, used=False)

    def verify_target_authorization(self, authorization, *, effect_gate, target_key, target_store_id,
                                    target_session_id, generation, action_digest):
        self._opaque(authorization, "authorization")
        key = self.book_id(target_key)
        self._gate_check(effect_gate, key)
        if (authorization["used"] or authorization["target_key"] != plain(target_key)
            or authorization["generation"] != generation or authorization["action_digest"] != action_digest
            or authorization["target_store_id"] != target_store_id or authorization["target_session_id"] != target_session_id):
            fail("DISPATCH_PERMIT_INVALID")
        with self.connect() as connection:
            book = self._lease(connection, key, authorization["owner_id"], generation, pending_ok=True)
            if book["hold"]:
                fail("TARGET_DRIFT_HOLD", book["hold"], 3)
            if self._pending(connection, key, authorization["intent_id"]):
                fail("BOOK_WRITE_PAUSED")
        authorization["used"] = True
        # Retire the actual identity as well as its caller-visible diagnostic.
        self._issued.pop(id(authorization), None)
        return authorization


def _delegate(name, *args, **kwargs):
    store = CURRENT.get()
    if store is None:
        fail("STATE_DIRECTORY_IDENTITY_MISMATCH", "open an explicit store first", 5)
    return getattr(store, name)(*args, **kwargs)


def commit_intent(prepared_action, *, owner_id, generation):
    return _delegate("commit_intent", prepared_action, owner_id=owner_id, generation=generation)


def commit_action_result(committed_intent, prepared_action, observation, comparison, *, owner_id, generation):
    return _delegate("commit_action_result", committed_intent, prepared_action, observation, comparison,
                     owner_id=owner_id, generation=generation)


def commit_reconciliation(result, *, owner_id, generation):
    return _delegate("commit_reconciliation", result, owner_id=owner_id, generation=generation)


def load_book_context(target_key, *, owner_id, generation):
    return _delegate("load_book_context", target_key, owner_id=owner_id, generation=generation)


def import_history_archive(package_path, *, expected_ledger_id, target_key):
    return _delegate("import_history_archive", package_path, expected_ledger_id=expected_ledger_id, target_key=target_key)


def commit_unattempted_absence(bundle, request, *, owner_id, generation, asset_root, observer):
    return _delegate("commit_unattempted_absence", bundle, request, owner_id=owner_id,
                     generation=generation, asset_root=asset_root, observer=observer)


def clear_target_drift_hold(hold_id, snapshot_ref, precheck_ref, targetcheck_ref, candidate_plan_ref, *, owner_id, generation):
    return _delegate("clear_target_drift_hold", hold_id, snapshot_ref, precheck_ref, targetcheck_ref,
                     candidate_plan_ref, owner_id=owner_id, generation=generation)
