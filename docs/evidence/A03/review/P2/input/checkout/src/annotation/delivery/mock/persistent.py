"""Independent all-synthetic SQLite target, with controlled runtime fencing.

This database never shares a connection or transaction with runtime.sqlite3.
Public observations are evidence values; only runtime-issued opaque handles grant
effects, under the common book gate and the target's persisted fence.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from types import MappingProxyType

from annotation.contracts import artifact_ref, assert_plan_ready, content_digest, seal_artifact, validate_bundle
from annotation.delivery.planner import (PublicRecord, action_facts, bind_plan_observation,
                                         compare_action_effect, encoded)
from annotation.quality.targetcheck import reject, resolve_artifact

FORMAT = "a03-mock-state-1"
APPLICATION_ID = 0x41303354
EFFECT_FAULTS = {None, "applied", "not_applied", "partial", "lost_response",
                 "response_lost_readable", "after_effect_exit"}
READ_FAULTS = {None, "unavailable", "contradictory", "truncated", "duplicate", "timeout"}
_locks = {}
_locks_guard = threading.Lock()


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def _plain(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value) if isinstance(value, dict) else value


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _get(value, name, default=None):
    return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)


def _write_resource(root, value):
    root = Path(root).resolve()
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    relative = "assets/a03-target/" + digest + ".json"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.resolve().is_relative_to(root):
        reject("EVIDENCE_PATH", "target evidence path escapes asset root")
    try:
        with path.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        if path.read_bytes() != raw:
            reject("RESOURCE_HASH_MISMATCH", "immutable target evidence conflicts")
    return {"path": relative, "sha256": digest, "media_type": "application/json", "origin": "SYNTHETIC"}


def _copy_resources(value, source_root, destination_root):
    """Preserve exact evidence bytes when preparation uses a runtime package."""
    source_root, destination_root = Path(source_root).resolve(), Path(destination_root).resolve()
    if isinstance(value, list):
        for member in value:
            _copy_resources(member, source_root, destination_root)
    elif isinstance(value, dict):
        if {"path", "sha256", "media_type"}.issubset(value):
            source = (source_root / value["path"]).resolve()
            destination = (destination_root / value["path"]).resolve()
            if not source.is_relative_to(source_root) or not destination.is_relative_to(destination_root) or not source.is_file() or source.is_symlink():
                reject("RESOURCE_MISSING", "preparation evidence path is unsafe or missing")
            raw = source.read_bytes()
            if hashlib.sha256(raw).hexdigest() != value["sha256"]:
                reject("RESOURCE_HASH_MISMATCH", "preparation evidence bytes changed")
            if source != destination:
                destination.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with destination.open("xb") as handle:
                        handle.write(raw)
                        handle.flush()
                        os.fsync(handle.fileno())
                except FileExistsError:
                    if destination.read_bytes() != raw:
                        reject("RESOURCE_HASH_MISMATCH", "package evidence cannot overwrite existing bytes")
            if value["media_type"] == "application/json":
                _copy_resources(json.loads(raw), source_root, destination_root)
        else:
            for member in value.values():
                _copy_resources(member, source_root, destination_root)


class BookEffectGate:
    """Bounded host-local per-book cross-process byte lock.

    Every controlled takeover and dispatch uses the same fixed runtime path.
    Reentry in the same thread preserves the original OS lock and lease.
    """
    def __init__(self, path, target_key, timeout=5.0):
        self.path = str(Path(path).resolve())
        self.target_key = copy.deepcopy(_plain(target_key))
        self.timeout = min(float(timeout), 5.0)
        with _locks_guard:
            self._local = _locks.setdefault(self.path, {"lock": threading.RLock(), "depth": 0, "thread": None})
        self.held = False
        self.pid = os.getpid()

    def acquire(self, timeout=None):
        if timeout is not None:
            self.timeout = min(float(timeout), 5.0)
        return self

    def __enter__(self):
        deadline = time.monotonic() + max(0.0, self.timeout)
        if not self._local["lock"].acquire(timeout=max(0.0, self.timeout)):
            reject("EFFECT_GATE_TIMEOUT", "book gate deadline exhausted")
        if self._local["depth"]:
            self._local["depth"] += 1
            self.held = True
            return self
        path = Path(self.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path.open("a+b")
        self._file.seek(0, 2)
        if self._file.tell() == 0:
            self._file.write(b"0")
            self._file.flush()
        try:
            while True:
                try:
                    self._file.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except (OSError, BlockingIOError):
                    if time.monotonic() >= deadline:
                        reject("EFFECT_GATE_TIMEOUT", "book gate acquisition exceeded absolute deadline")
                    time.sleep(min(0.01, max(0, deadline - time.monotonic())))
            self._local.update(depth=1, thread=threading.get_ident(), file=self._file)
            self.held = True
            return self
        except BaseException:
            self._file.close()
            self._local["lock"].release()
            raise

    def __exit__(self, *_):
        self._local["depth"] -= 1
        if not self._local["depth"]:
            handle = self._local.pop("file")
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()
            self._local["thread"] = None
        self.held = self._local["depth"] > 0
        self._local["lock"].release()


def compare_action(action, before_observation, after_observation, *, comparator_version="a02-facts-1"):
    return compare_action_effect(action, before_observation, after_observation,
                                 comparator_version=comparator_version)


class PreparedAction(PublicRecord):
    """A value whose exact issued object must pass its observer's registry.

    A serialized/copy value is useful diagnostic evidence, not first-dispatch
    authority. Mutations are detected against the privately retained digest.
    """


class VerifiedPreparedAction:
    """Direct callback result, deliberately not a JSON dictionary or boolean."""
    def __init__(self, **data):
        self._data = MappingProxyType(copy.deepcopy(data))

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError as exc:
            raise AttributeError(key) from exc


def _prepared_digest(prepared):
    return content_digest({key: _plain(value) for key, value in prepared.items()})


def apply_synthetic_action(state, action, partial=False):
    payload = state["target"]
    pid = action["target"]["platform_question_id"]
    if pid is None:
        number = len(payload["questions"]) + 1
        existing = {q["platform_question_id"] for q in payload["questions"]}
        while "mock-question-" + str(number) in existing:
            number += 1
        pid = "mock-question-" + str(number)
        directory = action["expected_before"]["directory_id"]
        order = max([q["platform_order"] for q in payload["questions"] if q["directory_id"] == directory] + [0]) + 1
        payload["questions"].append({"platform_question_id": pid, "directory_id": directory, "platform_order": order})
    state["internal_bindings"][action["target"]["question_id"]] = pid
    projected = json.loads(action["expected_after"]["frames"])
    if partial:
        projected = projected[:-1]
    for frame in projected:
        number = len(payload["frames"]) + 1
        existing = {f["platform_frame_id"] for f in payload["frames"]}
        while "mock-frame-" + str(number) in existing:
            number += 1
        fid = "mock-frame-" + str(number)
        payload["frames"].append({"platform_frame_id": fid, "platform_question_id": pid,
                                  "box": frame["box"], "platform_role": frame["platform_role"]})
        state["frame_projections"][fid] = copy.deepcopy(frame)
    state["epoch"] += 1
    return pid


class PersistentMockSession:
    def __init__(self, directory, descriptor):
        self.directory = Path(directory).resolve()
        self.path = self.directory / "target.sqlite3"
        self.descriptor = PublicRecord(descriptor)
        self.asset_root = Path(descriptor["asset_root"]).resolve()
        self.target_session_id = descriptor["target_session_id"]
        self.store_id = descriptor["store_id"]
        self.target_key = copy.deepcopy(descriptor["target_key"])
        self.source_ref = copy.deepcopy(descriptor["fixed_source_ref"])
        self.scope_id = descriptor["fixed_scope_id"]
        self._prepared_actions = {}

    @classmethod
    def create(cls, target_dir, bundle, snapshot_ref, *, platform_namespace, source_ref,
               asset_root, expected_store_id, target_session_id):
        bundle = validate_bundle(bundle, asset_root=asset_root)
        snapshot = resolve_artifact(bundle, snapshot_ref, "PlatformSnapshot")
        source = resolve_artifact(bundle, source_ref, "SourceBundle")
        if snapshot.schema_version != "1.1.0-a-recovery-proposal":
            reject("RECOVERY_VERSION_UNSUPPORTED", "persistent target requires explicitly converted recovery input")
        if (snapshot.producer.evidence_mode != "SYNTHETIC" or source.producer.evidence_mode != "SYNTHETIC"):
            reject("SYNTHETIC_ONLY", "persistent target accepts all-synthetic inputs only")
        if (source.book_id, source.scope_id) != (snapshot.book_id, snapshot.scope_id):
            reject("SOURCE_BINDING", "target source book/scope differs")
        directory = Path(target_dir).resolve()
        path = directory / "target.sqlite3"
        directory.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb"):
                pass
        except FileExistsError:
            reject("TARGET_STORE_EXISTS", "explicit create cannot reset an existing target")
        key = {"platform_namespace": platform_namespace, "target_id": snapshot.payload.target_id,
               "book_id": snapshot.book_id}
        descriptor = {"format": FORMAT, "user_version": 1, "application_id": APPLICATION_ID,
                      "store_id": expected_store_id, "target_session_id": target_session_id,
                      "target_key": key, "book_id": snapshot.book_id,
                      "fixed_scope_id": snapshot.scope_id, "fixed_source_ref": artifact_ref(source),
                      "base_snapshot_ref": artifact_ref(snapshot), "directory": str(directory),
                      "asset_root": str(Path(asset_root).resolve())}
        state = {"base": _plain(snapshot), "target": _plain(snapshot.payload),
                 "internal_bindings": {}, "frame_projections": {}, "epoch": 0,
                 "read_sequence": 0, "fence_generation": 0, "fence_owner_id": None,
                 "context": None}
        from annotation.contracts import target_state_digest
        descriptor["initial_state_digest"] = target_state_digest({"target_key": key,
            "source_ref": artifact_ref(source), "scope_id": snapshot.scope_id,
            "target": state["target"], "internal_bindings": {}, "frame_projections": {}})
        try:
            with sqlite3.connect(str(path), timeout=1.0, factory=_ClosingConnection) as db:
                db.execute("PRAGMA application_id=" + str(APPLICATION_ID))
                db.execute("PRAGMA user_version=1")
                db.execute("PRAGMA synchronous=FULL")
                db.execute("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
                db.execute("CREATE TABLE effects(sequence INTEGER PRIMARY KEY AUTOINCREMENT,body TEXT NOT NULL)")
                db.execute("CREATE TABLE observations(observation_id TEXT PRIMARY KEY,body TEXT NOT NULL)")
                db.execute("INSERT INTO meta VALUES('descriptor',?)", (encoded(descriptor),))
                db.execute("INSERT INTO meta VALUES('state',?)", (encoded(state),))
            session = cls(directory, descriptor)
            return session
        except sqlite3.Error as exc:
            reject("TARGET_STORE_IO", str(exc))

    @classmethod
    def open(cls, target_dir, *, expected_store_id, expected_target_session_id,
             expected_target_key, expected_scope_id, expected_source_ref):
        directory = Path(target_dir).resolve()
        path = directory / "target.sqlite3"
        if not path.is_file():
            reject("TARGET_STORE_MISSING", "reopen never initializes a missing target store")
        try:
            with sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=1.0, factory=_ClosingConnection) as db:
                if db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID or db.execute("PRAGMA user_version").fetchone()[0] != 1:
                    reject("TARGET_STORE_VERSION_UNSUPPORTED", "target application or user version differs")
                if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    reject("TARGET_STORE_CORRUPT", "target integrity check failed")
                row = db.execute("SELECT value FROM meta WHERE key='descriptor'").fetchone()
                descriptor = json.loads(row[0])
                json.loads(db.execute("SELECT value FROM meta WHERE key='state'").fetchone()[0])
        except (sqlite3.Error, ValueError, TypeError, KeyError) as exc:
            reject("TARGET_STORE_CORRUPT", str(exc))
        if descriptor.get("directory") != str(directory):
            reject("STATE_DIRECTORY_IDENTITY_MISMATCH", "target directory differs from established identity")
        if descriptor.get("format") != FORMAT:
            reject("TARGET_STORE_VERSION_UNSUPPORTED", "target format differs")
        if descriptor.get("store_id") != expected_store_id or descriptor.get("target_key") != _plain(expected_target_key):
            reject("TARGET_IDENTITY_MISMATCH", "target store/key differs")
        if descriptor.get("target_session_id") != expected_target_session_id:
            reject("TARGET_SESSION_BINDING_MISMATCH", "target session differs")
        if descriptor.get("fixed_scope_id") != expected_scope_id:
            reject("TARGET_SCOPE_SWITCH_UNSUPPORTED", "fixed session scope cannot change")
        if descriptor.get("fixed_source_ref") != _plain(expected_source_ref):
            reject("SOURCE_BINDING", "fixed session source revision/hash cannot change")
        return cls(directory, descriptor)

    def _connect(self):
        if not self.path.is_file():
            reject("TARGET_STORE_MISSING", "target file is missing")
        try:
            db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=1.0, factory=_ClosingConnection)
            db.execute("PRAGMA synchronous=FULL")
            if db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID or db.execute("PRAGMA user_version").fetchone()[0] != 1:
                db.close()
                reject("TARGET_STORE_VERSION_UNSUPPORTED", "target version changed")
            descriptor = json.loads(db.execute("SELECT value FROM meta WHERE key='descriptor'").fetchone()[0])
            for name in ("store_id", "target_session_id", "target_key", "directory", "fixed_source_ref", "fixed_scope_id"):
                if descriptor.get(name) != self.descriptor.get(name):
                    db.close()
                    reject("TARGET_IDENTITY_MISMATCH", "opened target was replaced")
            return db
        except sqlite3.Error as exc:
            reject("TARGET_STORE_CORRUPT", str(exc))

    @staticmethod
    def _load(db):
        return json.loads(db.execute("SELECT value FROM meta WHERE key='state'").fetchone()[0])

    @staticmethod
    def _save(db, state):
        db.execute("UPDATE meta SET value=? WHERE key='state'", (encoded(state),))

    def _view(self, state):
        return {"provenance": "SYNTHETIC", "execution_mode": "SIMULATED",
                "target_key": copy.deepcopy(self.descriptor.target_key),
                "target_session_id": self.descriptor.target_session_id,
                "source_ref": copy.deepcopy(self.descriptor.fixed_source_ref),
                "scope_id": self.descriptor.fixed_scope_id,
                "book_id": self.descriptor.book_id, "epoch": state["epoch"],
                "target": copy.deepcopy(state["target"]),
                "internal_bindings": copy.deepcopy(state["internal_bindings"]),
                "frame_projections": copy.deepcopy(state["frame_projections"])}

    def _hash(self, state):
        from annotation.contracts import target_state_digest
        return target_state_digest(self._view(state))

    def _key(self, target_key):
        if _plain(target_key) != self.descriptor.target_key:
            reject("TARGET_IDENTITY_MISMATCH", "requested canonical book key differs")

    def read_target(self, book_id=None):
        if book_id is not None and book_id != self.descriptor.book_id:
            reject("TARGET_NOT_REGISTERED", "book differs from persistent target")
        with self._connect() as db:
            return self._view(self._load(db))

    def activate_fence(self, target_key, *, target_session_id, owner_id, generation, authority):
        self._key(target_key)
        if target_session_id != self.descriptor.target_session_id:
            reject("TARGET_IDENTITY_MISMATCH", "fence target session differs")
        with authority.effect_gate(target_key) as gate:
            reservation = getattr(authority, "current_claim", None)
            if reservation is None:
                reject("CLAIM_NOT_RESERVED", "runtime opaque claim reservation is required")
            claim = authority.verify_claim(reservation, effect_gate=gate)
            if any(_get(claim, k) != value for k, value in (("owner_id", owner_id), ("generation", generation), ("target_key", target_key))):
                reject("OWNER_GENERATION_STALE", "runtime claim differs from fence request")
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                state = self._load(db)
                if generation <= state["fence_generation"]:
                    reject("OWNER_GENERATION_STALE", "target fence generation must increase")
                state.update(fence_generation=generation, fence_owner_id=owner_id)
                self._save(db, state)
            return PublicRecord(store_id=self.descriptor.store_id, target_store_id=self.descriptor.store_id,
                                target_session_id=target_session_id, target_key=target_key, owner_id=owner_id,
                                generation=generation, commit_ref="target-fence-" + str(generation))

    def observe_target(self, target_key, *, observation_id, read_fault=None):
        self._key(target_key)
        if read_fault not in READ_FAULTS:
            reject("INVALID_FAULT", "unknown target read fault")
        timed_out = read_fault == "timeout"
        if timed_out:
            time.sleep(2.0)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM observations WHERE observation_id=?", (observation_id,)).fetchone():
                reject("OBSERVATION_ID_CONFLICT", "observation identity is permanently used")
            value = PublicRecord(format_version="a03-target-observation-1", origin="SYNTHETIC",
                                 provenance="SYNTHETIC", execution_mode="SIMULATED", observation_id=observation_id,
                                 store_id=self.descriptor.store_id, target_store_id=self.descriptor.store_id,
                                 target_session_id=self.descriptor.target_session_id, target_key=copy.deepcopy(target_key),
                                 scope_id=self.descriptor.fixed_scope_id, source_ref=copy.deepcopy(self.descriptor.fixed_source_ref),
                                 observed_at=_utc(), read_sequence=None, target_state_version=None,
                                 target_state_hash=None, read_status="UNAVAILABLE", relevant_scope_completeness=False,
                                 scope_complete=False, view=None, state=None, effect_log=[])
            if read_fault not in ("unavailable", "timeout"):
                state = self._load(db)
                state["read_sequence"] += 1
                self._save(db, state)
                view = self._view(state)
                effects = [json.loads(row[0]) for row in db.execute("SELECT body FROM effects ORDER BY sequence")]
                value.update(read_sequence=state["read_sequence"], target_state_version="a03-target-epoch-" + str(state["epoch"]),
                             target_state_hash=self._hash(state), read_status="OK", relevant_scope_completeness=True,
                             scope_complete=True, view=view, state=copy.deepcopy(view), effect_log=effects)
                if read_fault == "contradictory":
                    value["read_status"] = "CONTRADICTORY"
                elif read_fault == "truncated":
                    value.update(read_status="TRUNCATED", relevant_scope_completeness=False, scope_complete=False)
                elif read_fault == "duplicate":
                    if value["view"]["target"]["questions"]:
                        value["view"]["target"]["questions"].append(copy.deepcopy(value["view"]["target"]["questions"][0]))
                    else:
                        value.update(read_status="TRUNCATED", relevant_scope_completeness=False, scope_complete=False)
            if timed_out:
                value["failure_code"] = "TARGET_READ_TIMEOUT"
            db.execute("INSERT INTO observations VALUES(?,?)", (observation_id, encoded(value)))
        resource = _write_resource(self.asset_root, value)
        value.update(resource=resource, readback=resource, asset_root=str(self.asset_root))
        value["effect_log_resource"] = _write_resource(self.asset_root, {"origin": "SYNTHETIC", "effect_log": value["effect_log"]})
        return value

    def _verify_observation(self, observation):
        value = _plain(observation)
        with self._connect() as db:
            row = db.execute("SELECT body FROM observations WHERE observation_id=?", (value.get("observation_id"),)).fetchone()
        if row is None:
            reject("OBSERVATION_MISSING", "actual persisted observation does not exist")
        original = json.loads(row[0])
        resource = value.get("resource", value.get("readback"))
        if resource is None:
            reject("RESOURCE_MISSING", "observation resource is missing")
        path = (self.asset_root / resource["path"]).resolve()
        if not path.is_relative_to(self.asset_root) or not path.is_file() or path.is_symlink():
            reject("RESOURCE_MISSING", "observation resource path is missing or outside its root")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != resource["sha256"]:
            reject("RESOURCE_HASH_MISMATCH", "observation bytes differ from their resource digest")
        if json.loads(raw) != original:
            reject("OBSERVATION_BINDING_MISMATCH", "observation resource differs from independent persisted read")
        for name, member in original.items():
            if value.get(name) != member:
                reject("OBSERVATION_BINDING_MISMATCH", "observation differs from actual persisted target read")
        if original["read_status"] != "OK" or not original["relevant_scope_completeness"]:
            reject("READBACK_INCOMPLETE", "snapshot requires complete actual target read")
        return original

    def snapshot_from_observation(self, observation):
        value = self._verify_observation(observation)
        with self._connect() as db:
            state = self._load(db)
        snapshot = copy.deepcopy(state["base"])
        snapshot.pop("content_hash", None)
        snapshot.update(artifact_id="snapshot-a03-" + content_digest({"store_id": value["store_id"], "observation_id": value["observation_id"]})[:24],
                        revision=1, created_at=value["observed_at"])
        snapshot["payload"] = copy.deepcopy(value["view"]["target"])
        snapshot["payload"].update(observed_at=value["observed_at"], observed_hash=value["target_state_hash"],
                                   observed_version=value["target_state_version"])
        snapshot["producer"].update(module="a03-persistent-mock", implementation_version="a03-1")
        snapshot["input_refs"] = [copy.deepcopy(self.descriptor.fixed_source_ref)]
        return seal_artifact(snapshot)

    def prepare_action(self, bundle, plan_ref, action_id, config, *, current_snapshot_ref, asset_root):
        bundle = validate_bundle(bundle, asset_root=asset_root)
        plan = resolve_artifact(bundle, plan_ref, "ApplyPlan")
        if _plain(current_snapshot_ref) != _plain(plan.payload.snapshot):
            reject("TARGET_CHANGED", "preparation plan-initial snapshot reference differs")
        assert_plan_ready(bundle, plan_ref, current_snapshot_ref)
        action = next((a for a in plan.payload.actions if a.action_id == action_id), None)
        if action is None:
            reject("ACTION_DIGEST_MISMATCH", "action is absent from exact plan")
        if (plan.book_id != self.descriptor.book_id or plan.scope_id != self.descriptor.fixed_scope_id or
                action.target.target_id != self.descriptor.target_key["target_id"]):
            reject("TARGET_IDENTITY_MISMATCH", "plan is outside fixed target/session")
        graph = resolve_artifact(bundle, plan.payload.graph, "QuestionGraph")
        if _plain(graph.payload.source) != self.descriptor.fixed_source_ref:
            reject("SOURCE_BINDING", "plan graph source differs from fixed target session source")
        observation = self.observe_target(self.descriptor.target_key, observation_id="prepare-" + uuid.uuid4().hex)
        snapshot = self.snapshot_from_observation(observation)
        observation["snapshot_ref"] = artifact_ref(snapshot)
        before = dict(observation)
        before.update(format_version="a03-prepared-before-1", action_id=action_id,
                      action_digest=content_digest(_plain(action)), facts=action_facts(action, observation["view"]))
        _copy_resources(before, self.asset_root, asset_root)
        prepared_resource = _write_resource(asset_root, before)
        with self._connect() as db:
            context = self._load(db).get("context") or {}
        proposed_prefix = context.get("progress_refs", context.get("applied_prefix_refs", []))
        prefix = []
        for ref in proposed_prefix:
            progress = next((a for a in bundle.artifacts if artifact_ref(a) == ref and a.kind == "ExecutionProgress"), None)
            if progress is not None and _plain(progress.payload.plan_ref) == artifact_ref(plan):
                prefix.append(ref)
        initial = resolve_artifact(bundle, plan.payload.snapshot, "PlatformSnapshot")
        try:
            observation["plan_baseline_epoch"] = int(initial.payload.observed_version.rsplit("-", 1)[1])
        except (ValueError, AttributeError):
            reject("OBSERVATION_BINDING_MISMATCH", "plan snapshot has no genuine target state version")
        binding = bind_plan_observation(bundle, plan_ref, action_id, observation, config,
                                        prepared_before=prepared_resource, progress_refs=prefix)
        prepared = PreparedAction(bundle=bundle, plan=plan, action=action, plan_ref=artifact_ref(plan), action_id=action_id,
                            action_digest=content_digest(_plain(action)), expected_effect_digest=content_digest(_plain(action.expected_after)),
                            target_key=copy.deepcopy(self.descriptor.target_key), target_store_id=self.descriptor.store_id,
                            target_session_id=self.descriptor.target_session_id, source_ref=copy.deepcopy(self.descriptor.fixed_source_ref),
                            scope_id=self.descriptor.fixed_scope_id, comparator_version="a02-facts-1",
                            before_snapshot_ref=_plain(plan.payload.snapshot), prepared_before=prepared_resource,
                            observation=observation, snapshot=snapshot, observation_binding=binding,
                            asset_root=str(Path(asset_root).resolve()))
        self._prepared_actions[id(prepared)] = {"object": prepared, "digest": _prepared_digest(prepared),
            "config": copy.deepcopy(config), "config_version": config.version,
            "plan_ref": artifact_ref(plan), "observation_id": observation["observation_id"]}
        return prepared

    def verify_prepared_action(self, prepared, *, observation_binding=None,
                               expected_config_version=None, expected_plan_ref=None):
        """Verify the exact native object through the current controlled observer.

        Runtime calls this instance method on its currently registered observer;
        neither a caller dictionary nor a self-reported completeness flag can
        manufacture the registry entry. This method performs no target effect or
        new observation. Persisted intent copies never recreate the capability.
        """
        issued = self._prepared_actions.get(id(prepared))
        if not isinstance(prepared, PreparedAction) or issued is None or issued["object"] is not prepared:
            reject("PREPARED_ACTION_UNVERIFIED", "exact current-observer-issued PreparedAction is required")
        if _prepared_digest(prepared) != issued["digest"]:
            reject("OBSERVATION_BINDING_MISMATCH", "issued prepared action or observation binding was modified")
        if expected_config_version is not None and expected_config_version != issued["config_version"]:
            reject("AUTHORIZATION_CHANGED", "current runtime configuration differs from the actual preparation")
        if expected_plan_ref is not None and _plain(expected_plan_ref) != issued["plan_ref"]:
            reject("PLAN_CHANGED", "current accepted plan differs from the actual preparation")
        if observation_binding is not None and _plain(observation_binding) != _plain(prepared["observation_binding"]):
            reject("OBSERVATION_BINDING_MISMATCH", "dispatch binding differs from the native preparation")
        self._key(prepared["target_key"])
        if (prepared["target_store_id"] != self.store_id or prepared["target_session_id"] != self.target_session_id or
                prepared["source_ref"] != self.source_ref or prepared["scope_id"] != self.scope_id):
            reject("TARGET_IDENTITY_MISMATCH", "prepared target/source/session differs from the controlled observer")
        bundle = validate_bundle(prepared["bundle"], asset_root=prepared["asset_root"])
        observation = prepared["observation"]
        original = self._verify_observation(observation)
        if original["observation_id"] != issued["observation_id"]:
            reject("OBSERVATION_BINDING_MISMATCH", "prepared observation identity differs from its registry")
        snapshot = self.snapshot_from_observation(observation)
        if snapshot != prepared["snapshot"] or artifact_ref(snapshot) != prepared["observation_binding"]["observed_snapshot_ref"]:
            reject("OBSERVATION_BINDING_MISMATCH", "prepared snapshot is not from the exact persisted target observation")
        resource = prepared["prepared_before"]
        root = Path(prepared["asset_root"]).resolve()
        path = (root / resource["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
            reject("RESOURCE_MISSING", "prepared-before immutable resource is missing or unsafe")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != resource["sha256"]:
            reject("RESOURCE_HASH_MISMATCH", "prepared-before evidence bytes changed")
        before = json.loads(raw)
        if (before.get("format_version") != "a03-prepared-before-1" or
                any(before.get(name) != value for name, value in original.items() if name != "format_version")):
            reject("OBSERVATION_BINDING_MISMATCH", "prepared-before evidence differs from actual persisted target read")
        if (before.get("action_id") != prepared["action_id"] or before.get("action_digest") != prepared["action_digest"] or
                before.get("facts") != action_facts(prepared["action"], original["view"])):
            reject("PREPARED_BEFORE_MISMATCH", "prepared-before does not bind the exact action and actual relevant facts")
        binding = bind_plan_observation(bundle, prepared["plan_ref"], prepared["action_id"], observation,
            issued["config"], prepared_before=resource, progress_refs=prepared["observation_binding"]["applied_prefix"])
        if binding != prepared["observation_binding"]:
            reject("OBSERVATION_BINDING_MISMATCH", "public observation bridge no longer matches native preparation")
        return VerifiedPreparedAction(attestation_digest=issued["digest"], config_version=issued["config_version"],
            plan_ref=copy.deepcopy(issued["plan_ref"]), action_id=prepared["action_id"],
            action_digest=prepared["action_digest"], target_key=copy.deepcopy(self.target_key),
            target_store_id=self.store_id, target_session_id=self.target_session_id,
            source_ref=copy.deepcopy(self.source_ref), scope_id=self.scope_id,
            prepared_before=copy.deepcopy(resource), observation_id=original["observation_id"],
            read_sequence=original["read_sequence"], target_state_version=original["target_state_version"],
            target_state_hash=original["target_state_hash"])

    def dispatch_action(self, prepared_action, *, committed_intent, dispatch_permit, authority, effect_fault=None):
        if effect_fault not in EFFECT_FAULTS:
            reject("INVALID_FAULT", "unsupported synthetic target effect fault")
        prepared = prepared_action
        self._key(prepared["target_key"])
        if committed_intent is None:
            reject("LOCAL_INTENT_COMMIT_REQUIRED", "target requires genuinely committed runtime intent")
        with authority.effect_gate(prepared["target_key"]) as gate:
            checked = self.verify_prepared_action(prepared)
            authorization = authority.consume_first_dispatch(dispatch_permit, effect_gate=gate,
                                  prepared_action=prepared, target_store_id=self.descriptor.store_id,
                                  target_session_id=self.descriptor.target_session_id)
            generation = _get(authorization, "generation")
            owner = _get(authorization, "owner_id")
            authority.verify_target_authorization(authorization, effect_gate=gate,
                target_key=prepared["target_key"], target_store_id=self.descriptor.store_id,
                target_session_id=self.descriptor.target_session_id, generation=generation,
                action_digest=prepared["action_digest"])
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                state = self._load(db)
                if state["fence_generation"] != generation or state["fence_owner_id"] != owner:
                    reject("OWNER_GENERATION_STALE", "independent target fence differs")
                if (self._hash(state) != checked.target_state_hash or
                        "a03-target-epoch-" + str(state["epoch"]) != checked.target_state_version):
                    reject("TARGET_CHANGED", "complete business state changed after actual preparation")
                if action_facts(prepared["action"], self._view(state)) != _plain(prepared["action"])["expected_before"]:
                    reject("TARGET_CHANGED", "target relevant precondition changed before effect")
                action = _plain(prepared["action"])
                if content_digest(action) != prepared["action_digest"]:
                    reject("ACTION_DIGEST_MISMATCH", "prepared action digest changed")
                pid = None
                if effect_fault != "not_applied":
                    pid = apply_synthetic_action(state, action, effect_fault == "partial")
                log = {"origin": "SYNTHETIC", "execution_mode": "SIMULATED", "action_id": prepared["action_id"],
                       "action_digest": prepared["action_digest"], "plan_ref": prepared["plan_ref"],
                       "target_key": prepared["target_key"], "target_session_id": self.descriptor.target_session_id,
                       "owner_id": owner, "generation": generation, "epoch": state["epoch"],
                       "effect_fault": effect_fault or "applied", "mutated": effect_fault != "not_applied",
                       "recorded_at": _utc(), "target_state_hash": self._hash(state)}
                cursor = db.execute("INSERT INTO effects(body) VALUES(?)", (encoded(log),))
                self._save(db, state)
                log["sequence"] = cursor.lastrowid
            if hasattr(authority, "fault"):
                authority.fault("after_effect")
            if effect_fault == "after_effect_exit":
                os._exit(87)
            response = "TIMEOUT" if effect_fault in ("lost_response", "response_lost_readable") else "REJECTED" if effect_fault == "not_applied" else "OK"
            return PublicRecord(status=response, transport_response={"status": response, "platform_question_id": pid},
                                effect_log_ref=log, target_effect_committed=True,
                                outcome="UNKNOWN", reason="transport response requires independent readback")

    def import_book_context(self, verified_context, *, authority):
        key = self.descriptor.target_key
        with authority.effect_gate(key) as gate:
            ledger = _get(verified_context, "ledger_id", _get(verified_context, "journal_id"))
            checked = authority.verify_context(verified_context, target_key=key,
                                                expected_ledger_id=ledger, effect_gate=gate)
            context = copy.deepcopy(dict(checked))
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                state = self._load(db)
                old = state.get("context")
                if old and context.get("event_head", {}).get("sequence", 0) < old.get("event_head", {}).get("sequence", 0):
                    reject("HISTORY_INCOMPLETE", "cannot replace restored context with older history")
                state["context"] = context
                self._save(db, state)
        return PublicRecord(imported=True, pending_count=len(context.get("pending", [])),
                            pause_reasons=context.get("pause_reasons", []), target_key=key,
                            target_store_id=self.descriptor.store_id, target_session_id=self.descriptor.target_session_id)

    def export_book_context(self, target_key):
        self._key(target_key)
        with self._connect() as db:
            state = self._load(db)
            effects = [json.loads(row[0]) for row in db.execute("SELECT body FROM effects ORDER BY sequence")]
        result = PublicRecord(copy.deepcopy(state.get("context") or {}))
        result.update(target_key=copy.deepcopy(target_key), store_id=self.descriptor.store_id,
                      target_store_id=self.descriptor.store_id, target_session_id=self.descriptor.target_session_id,
                      source_ref=copy.deepcopy(self.descriptor.fixed_source_ref), scope_id=self.descriptor.fixed_scope_id,
                      effect_log=effects, effect_count=sum(e["mutated"] for e in effects), dispatch_count=len(effects),
                      read_sequence=state["read_sequence"], fence_generation=state["fence_generation"],
                      fence_owner_id=state["fence_owner_id"], internal_bindings=state["internal_bindings"],
                      frame_projections=state["frame_projections"], target_state_hash=self._hash(state))
        return result
