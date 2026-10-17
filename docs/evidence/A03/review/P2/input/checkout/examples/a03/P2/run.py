"""Portable A03 process demonstrations and author V01--V10 evidence runner.

Each command uses a new Python process. Output directories are create-only and
failures remain in place. Only all-synthetic fixtures and the controlled mock are
used. Functional assertions read the target through a separate CLI process.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import traceback

from processes import ProcessHarness, write_new


ROOT = Path(__file__).resolve().parents[3]
FAULT_POINTS = (
    "BEFORE_INTENT_COMMIT", "AFTER_INTENT_COMMIT", "AFTER_DISPATCH_STARTED",
    "AFTER_TARGET_EFFECT_COMMIT", "AFTER_READBACK_CAPTURE", "AFTER_RECEIPT_COMMIT",
)


class Scenario:
    def __init__(self, output, *, fixture="normal", root=ROOT, book=None, scope=None):
        self.output = Path(output).resolve()
        self.root = Path(root).resolve()
        self.harness = ProcessHarness(self.root, self.output)
        self.common = {
            "anchor_path": str(self.output / "anchor.json"),
            "expected_ledger_id": "a03-p2-ledger",
            "expected_target_store_id": "a03-p2-target-store",
        }
        self.number = 0
        self.inputs = None
        self.fixture = fixture
        self.book = book
        self.scope = scope
        self.observations = []

    @staticmethod
    def response(completion, *, success=True, exit_code=0):
        if completion["exit_code"] != exit_code:
            raise AssertionError("unexpected process exit %r (expected %r), see %s" % (
                completion["exit_code"], exit_code, completion["name"]))
        if not completion["stdout_json"]:
            raise AssertionError("CLI returned no JSON: " + completion["name"])
        response = completion["stdout_json"][-1]
        if response.get("ok") is not success:
            raise AssertionError("unexpected CLI result: " + repr(response))
        return response.get("result", response)

    def command(self, operation, *, expect_ok=True, expect_exit=0, **fields):
        self.number += 1
        request = dict(self.common, operation=operation, **fields)
        process = self.harness.cli("%02d-%s" % (self.number, operation), request)
        completion = process.finish()
        self.observations.append(completion)
        return self.response(completion, success=expect_ok, exit_code=expect_exit)

    def command_raw(self, operation, **fields):
        self.number += 1
        request = dict(self.common, operation=operation, **fields)
        process = self.harness.cli("%02d-%s" % (self.number, operation), request)
        completion = process.finish()
        self.observations.append(completion)
        return completion

    def prepare(self):
        argv = [
            sys.executable, "-B", str(self.root / "examples/a03/P2/prepare.py"),
            "--root", str(self.root), "--output", str(self.output / "inputs"),
            "--fixture", self.fixture,
        ]
        if self.book:
            argv.extend(["--book", self.book])
        if self.scope:
            argv.extend(["--scope", self.scope])
        process = self.harness.launch("00-prepare", argv)
        self.inputs = self.response(process.finish())
        required = {"state_dir": str(self.output / "runtime"),
                    "target_dir": str(self.output / "target"),
                    "bundle_path": self.inputs["bundle_path"],
                    "asset_root": self.inputs["asset_root"],
                    "config_path": self.inputs["config_path"],
                    "source_ref": self.inputs["source_ref"],
                    "snapshot_ref": self.inputs["snapshot_ref"],
                    "platform_namespace": "a03-mock", "target_session_id": "a03-p2-session"}
        initialized = self.command("init", **required)
        self.registration = initialized
        # Initial creation now builds its plan from an actual fresh target read.
        # These exact identities replace the unexecuted converter/planner draft.
        for key in ("plan_ref", "action_ids", "snapshot_ref"):
            self.inputs[key] = initialized[key]
        return initialized

    def target(self):
        self.number += 1
        config = json.loads(Path(self.inputs["config_path"]).read_text(encoding="utf-8"))
        key = {"platform_namespace": "a03-mock", "target_id": config["target_id"],
               "book_id": config["book_id"]}
        request = {"target_dir": str(self.output / "target"),
                   "expected_store_id": self.common["expected_target_store_id"],
                   "expected_target_session_id": "a03-p2-session", "expected_target_key": key,
                   "expected_scope_id": config["scope_id"],
                   "expected_source_ref": self.inputs["source_ref"]}
        name = "%02d-independent-target" % self.number
        request_path = self.output / name / "request.json"
        completion = self.harness.launch(name, [
            sys.executable, "-B", str(self.root / "examples/a03/P2/probe_target.py"),
            "--request", str(request_path),
        ], request).finish()
        self.observations.append(completion)
        return self.response(completion)

    def status(self):
        return self.command("status")

    def assert_effects(self, expected):
        target = self.target()
        actual = target["effect_count"]
        if actual != expected:
            raise AssertionError("independently reopened target effects %r != %r" % (actual, expected))
        if sum(bool(item["mutated"]) for item in target["effect_log"]) != expected:
            raise AssertionError("independent mutated-effect log/count differs")
        return target

    def assert_refused(self, completion, codes):
        if completion["exit_code"] == 0:
            raise AssertionError("expected refused process: " + completion["name"])
        if not completion["stdout_json"]:
            raise AssertionError("refusal missing structured JSON")
        payload = completion["stdout_json"][-1]
        if payload.get("ok") is not False or payload.get("code") not in codes:
            raise AssertionError("wrong refusal: " + repr(payload))
        return payload

    def finish(self, name, assertions):
        exported = self.command("export")
        result = {"scenario": name, "status": "PASS", "assertions": assertions,
                  "process_count": len(self.harness.owned),
                  "pids": [p.pid for p in self.harness.owned],
                  "export": exported, "provenance": "SYNTHETIC",
                  "execution_mode": "SIMULATED"}
        write_new(self.output / "scenario-result.json", result)
        return result

    def close(self):
        return self.harness.close()


def normal(case):
    case.prepare()
    case.command("run")
    target = case.assert_effects(len(case.inputs["action_ids"]))
    status = case.status()
    if status["pending_count"] != 0:
        raise AssertionError("normal completed plan retains pending obligations")
    case.assert_refused(case.command_raw("run"), {"REPLAY_FORBIDDEN", "PLAN_ALREADY_ACCEPTED"})
    case.assert_effects(target["effect_count"])
    return case.finish("normal", ["independent multi-action effects survive reopen",
                                  "old plan replay refused without new target effect"])


def effect_crash(case):
    case.prepare()
    crashed = case.command_raw("run", effect_fault="after_effect_exit")
    if crashed["exit_code"] != 87:
        raise AssertionError("target after-effect exit did not occur at code 87")
    before = case.assert_effects(1)
    if case.status()["pending_count"] < 1:
        raise AssertionError("effect crash lost pending intent")
    resolved = case.command("reconcile")
    after = case.assert_effects(1)
    if after["read_sequence"] <= before["read_sequence"]:
        raise AssertionError("recovery did not persist a genuinely new read")
    if not any(r.get("classification") == "MATCH" or r.get("status") == "RESOLVED_APPLIED"
               for r in resolved["resolutions"]):
        raise AssertionError("effect-after-crash was not resolved through MATCH")
    case.assert_refused(case.command_raw("run"),
                        {"REPLAY_FORBIDDEN", "PLAN_ALREADY_ACCEPTED", "PLAN_INTERRUPTED", "BOOK_WRITE_PAUSED"})
    case.assert_effects(1)
    return case.finish("effect-crash", ["independent effect survives process exit without receipt",
                                        "new process observes MATCH", "read-only recovery adds zero effects"])


def absent(case):
    case.prepare()
    crashed = case.command_raw("run", fault_point="AFTER_INTENT_COMMIT")
    if crashed["exit_code"] != 90:
        raise AssertionError("after-intent fault did not exit 90")
    case.assert_effects(0)
    resolved = case.command("reconcile")
    if not any(r.get("classification") == "ABSENT" or r.get("status") == "RESOLVED_NOT_APPLIED"
               for r in resolved["resolutions"]):
        raise AssertionError("uncalled committed intent did not resolve through actual ABSENT")
    case.assert_effects(0)
    case.assert_refused(case.command_raw("run"),
                        {"REPLAY_FORBIDDEN", "PLAN_ALREADY_ACCEPTED", "PLAN_INTERRUPTED", "BOOK_WRITE_PAUSED"})
    case.assert_effects(0)
    return case.finish("absent", ["committed intent without target effect survives crash",
                                  "fresh actual ABSENT resolves only its obligation",
                                  "recovery and old plan replay add zero effects"])


def fault_window(case, point):
    case.prepare()
    receipt_window = point == "AFTER_RECEIPT_COMMIT"
    fault_index = len(case.inputs["action_ids"]) - 1 if receipt_window else 0
    crashed = case.command_raw("run", fault_point=point, fault_action_index=fault_index)
    if crashed["exit_code"] != 90:
        raise AssertionError("named fault did not terminate a real process with code 90: " + point)
    expected_effects = (len(case.inputs["action_ids"]) if receipt_window else
                        0 if point in FAULT_POINTS[:3] else 1)
    case.assert_effects(expected_effects)
    status = case.status()
    expected_pending = 0 if point in ("BEFORE_INTENT_COMMIT", "AFTER_RECEIPT_COMMIT") else 1
    if status["pending_count"] != expected_pending:
        raise AssertionError("wrong pending count at " + point + ": " + repr(status))
    if expected_pending:
        resolved = case.command("reconcile")
        wanted = "ABSENT" if expected_effects == 0 else "MATCH"
        if [r["classification"] for r in resolved["resolutions"]] != [wanted]:
            raise AssertionError("wrong fresh readback classification after " + point)
        case.assert_effects(expected_effects)
    if receipt_window:
        exported = case.command("export")
        receipts = [a for a in exported["bundle"]["artifacts"]
                    if a["kind"] == "ExecutionReceipt" and a["payload"]["plan"] == case.inputs["plan_ref"]]
        if len(receipts) != 1:
            raise AssertionError("receipt crash must follow one complete persisted receipt")
        receipt = receipts[0]
        results = receipt["payload"]["results"]
        if ([r["action_id"] for r in results] != case.inputs["action_ids"]
                or any(r["outcome"] != "APPLIED" for r in results)):
            raise AssertionError("receipt boundary cannot be proved by a partial action progress")
        receipt_ref = {key: receipt[key] for key in ("artifact_id", "revision", "kind", "content_hash")}
        connection = sqlite3.connect(str(case.output / "runtime/runtime.sqlite3"))
        try:
            indexed = [(ref, path) for ref, path in connection.execute("SELECT ref,path FROM artifacts")
                       if json.loads(ref) == receipt_ref]
            intent_receipts = [(action, json.loads(ref) if ref else None)
                               for action, ref in connection.execute("SELECT action,receipt FROM intents")
                               if action in case.inputs["action_ids"]]
            if len(indexed) != 1:
                raise AssertionError("complete receipt lacks one durable artifact index entry")
            receipt_path = Path(indexed[0][1]).resolve()
            state_root = (case.output / "runtime").resolve()
            if state_root not in receipt_path.parents:
                raise AssertionError("receipt index escaped this scene's runtime")
            relative = receipt_path.relative_to(state_root).as_posix()
            file_index = connection.execute("SELECT sha,size FROM files WHERE path=?", (relative,)).fetchone()
        finally:
            connection.close()
        if (len(intent_receipts) != expected_effects
                or any(ref != receipt_ref for _, ref in intent_receipts)):
            raise AssertionError("all committed intents must bind the complete receipt index")
        raw = receipt_path.read_bytes()
        if (file_index is None or file_index != (hashlib.sha256(raw).hexdigest(), len(raw))
                or json.loads(raw) != receipt):
            raise AssertionError("indexed complete receipt bytes are missing or differ")
        write_new(case.output / "receipt-commit-witness.json", {
            "receipt_ref": receipt_ref, "action_ids": case.inputs["action_ids"],
            "intent_receipts": intent_receipts, "indexed_path": str(receipt_path),
            "indexed_sha256": file_index[0], "indexed_size": file_index[1],
        })
        queried = case.command("reconcile")
        if queried["pending_count"] or queried["resolutions"]:
            raise AssertionError("complete receipt reopening must require no recovery dispatch or new resolution")
    else:
        case.assert_refused(case.command_raw("run"), {
            "REPLAY_FORBIDDEN", "PLAN_ALREADY_ACCEPTED", "PLAN_INTERRUPTED", "BOOK_WRITE_PAUSED",
        })
    case.assert_effects(expected_effects)
    return case.finish("fault-window-" + point, [
        "named boundary exit is from a real child process", "target independently reopened",
        "new-process recovery adds no target effects", "old plan is never resumed",
    ])


def readback_refusal(case, read_fault):
    case.prepare()
    crashed = case.command_raw("run", effect_fault="after_effect_exit")
    if crashed["exit_code"] != 87:
        raise AssertionError("required independent effect crash did not occur")
    case.assert_effects(1)
    before = case.status()
    resolved = case.command("reconcile", read_fault=read_fault, expect_exit=3)
    if len(resolved["resolutions"]) != 1:
        raise AssertionError("one exact pending intent must be compared")
    record = resolved["resolutions"][0]
    if record["classification"] not in ("CONFLICT", "INDETERMINATE"):
        raise AssertionError("incomplete/contradictory readback incorrectly resolved: " + repr(record))
    after = case.status()
    if before["pending_count"] != 1 or after["pending_count"] != 1 or not after["paused"]:
        raise AssertionError("refused readback cleared book pause")
    case.assert_effects(1)
    return case.finish("readback-" + read_fault, [
        "inadequate actual readback remains unresolved", "reconcile adds zero target effects",
        "same-book write pause survives independent reopening",
    ])


def partial_effect(case):
    case.prepare()
    case.command("run", effect_fault="partial", expect_exit=3)
    case.assert_effects(1)
    if case.status()["pending_count"] != 1:
        raise AssertionError("partial target effect must remain unknown")
    result = case.command("reconcile", expect_exit=3)
    if result["resolutions"][0]["classification"] != "CONFLICT":
        raise AssertionError("partial effect cannot be classified as MATCH or ABSENT")
    case.assert_effects(1)
    return case.finish("partial-effect", ["partial independent effect is CONFLICT", "no automatic resend"])


def owner_race(case):
    case.prepare()
    children = []
    for side in ("left", "right"):
        marker = case.output / ("claim-" + side + ".reached")
        release = case.output / "claim.release"
        request = dict(case.common, operation="claim", owner_id="race-" + side,
                       fault={"point": "BEFORE_CLAIM", "marker": str(marker),
                              "release": str(release), "mode": "barrier"})
        child = case.harness.cli("claim-" + side, request)
        children.append((child, marker))
    for child, marker in children:
        case.harness.wait_file(marker, process=child)
    write_new(case.output / "claim.release", {"release": True})
    claims = [child.finish() for child, _ in children]
    successful = [case.response(item) for item in claims if item["exit_code"] == 0]
    if not successful:
        raise AssertionError("no process acquired owner after explicit simultaneous barrier release")
    for item in claims:
        if item["exit_code"]:
            case.assert_refused(item, {"OWNER_BUSY", "OWNER_GENERATION_STALE", "BOOK_GATE_TIMEOUT"})
    current = case.status()
    generations = [claim["generation"] for claim in successful]
    if len(generations) != len(set(generations)):
        raise AssertionError("two successful claim transactions reused one generation")
    newest = max(successful, key=lambda claim: claim["generation"])
    if current["owner_id"] != newest["owner_id"] or current["generation"] != newest["generation"]:
        raise AssertionError("current ledger did not select the latest unique generation")
    old = min(successful, key=lambda claim: claim["generation"])
    # Even if only one process claimed, an explicitly older generation must fail.
    old_generation = old["generation"] if len(successful) > 1 else old["generation"] - 1
    case.assert_refused(case.command_raw("run", owner_id=old["owner_id"], generation=old_generation),
                        {"OWNER_GENERATION_STALE", "OWNER_PROCESS_MISMATCH"})
    case.assert_effects(0)
    return case.finish("owner-race", ["both independent processes reached explicit barrier",
                                       "one current owner/generation survives",
                                       "obsolete owner generation cannot produce a target effect"])


def damaged_state(case, kind):
    case.prepare()
    crashed = case.command_raw("run", effect_fault="after_effect_exit")
    if crashed["exit_code"] != 87:
        raise AssertionError("required pending effect state was not created")
    case.assert_effects(1)
    database = case.output / "runtime/runtime.sqlite3"
    old_database = database.read_bytes()
    (case.output / "runtime-before-fault.sqlite3").write_bytes(old_database)
    if kind == "unknown-version":
        connection = sqlite3.connect(str(database))
        try:
            connection.execute("UPDATE meta SET value='a03-runtime-db-unsupported' WHERE key='version'")
            connection.commit()
        finally:
            connection.close()
        codes = {"LEDGER_VERSION_UNSUPPORTED"}
    elif kind in ("unknown-user-version", "unknown-application-id"):
        connection = sqlite3.connect(str(database))
        try:
            pragma = "user_version" if kind == "unknown-user-version" else "application_id"
            connection.execute("PRAGMA " + pragma + "=999")
            connection.commit()
        finally:
            connection.close()
        codes = {"LEDGER_VERSION_UNSUPPORTED"}
    elif kind in ("missing-resource", "corrupt-resource"):
        connection = sqlite3.connect(str(database))
        try:
            relative = connection.execute("SELECT path FROM files ORDER BY path LIMIT 1").fetchone()[0]
        finally:
            connection.close()
        resource = (case.output / "runtime" / relative).resolve()
        state_root = (case.output / "runtime").resolve()
        if state_root not in resource.parents:
            raise AssertionError("refuse to fault a file outside this scene's runtime")
        original = resource.read_bytes()
        retained = case.output / ("resource-before-fault-" + resource.name)
        retained.write_bytes(original)
        if kind == "missing-resource":
            resource.rename(resource.with_name(resource.name + ".fault-retained"))
            codes = {"RESOURCE_MISSING"}
        else:
            resource.write_bytes(original + b"\nA03 AUTHOR CONTROLLED RESOURCE CORRUPTION\n")
            codes = {"RESOURCE_HASH_MISMATCH"}
    elif kind == "corrupt-db":
        database.write_bytes(b"A03 AUTHOR CONTROLLED CORRUPTION\n")
        codes = {"LEDGER_CORRUPT"}
    elif kind == "alternate-state-dir":
        anchor = case.output / "anchor.json"
        (case.output / "anchor-before-fault.json").write_bytes(anchor.read_bytes())
        contents = json.loads(anchor.read_bytes())
        contents["state_dir"] = str(case.output / "empty-alternate-directory")
        (case.output / "empty-alternate-directory").mkdir()
        anchor.write_text(json.dumps(contents), encoding="utf-8")
        codes = {"STATE_DIRECTORY_IDENTITY_MISMATCH", "LEDGER_MISSING"}
    else:
        raise ValueError(kind)
    case.assert_refused(case.command_raw("status"), codes)
    case.assert_effects(1)
    if (case.output / "runtime-before-fault.sqlite3").read_bytes() != old_database:
        raise AssertionError("fault backup changed")
    result = {"scenario": kind, "status": "PASS",
              "original_database_sha256": hashlib.sha256(old_database).hexdigest(),
              "assertions": ["damaged store fails closed", "runtime failure does not erase independent target effects",
                             "original pending database bytes retained as fault evidence"]}
    write_new(case.output / "scenario-result.json", result)
    return result


def database_busy(case):
    case.prepare()
    marker, release = case.output / "db-lock.reached", case.output / "db-lock.release"
    holder = case.harness.launch("database-lock-holder", [
        sys.executable, "-B", str(case.root / "examples/a03/P2/lock_db.py"),
        "--database", str(case.output / "runtime/runtime.sqlite3"),
        "--marker", str(marker), "--release", str(release),
    ])
    case.harness.wait_file(marker, process=holder)
    blocked = case.command_raw("run")
    case.assert_refused(blocked, {"LEDGER_CORRUPT", "LEDGER_BUSY", "SQLITE_BUSY", "LEDGER_IO",
                                 "STORAGE_TRANSACTION_FAILED"})
    if blocked["elapsed_seconds"] > 3:
        raise AssertionError("one-second SQLite busy gate did not exit within bounded overhead")
    write_new(release, {"release": True})
    case.response(holder.finish())
    case.assert_effects(0)
    return case.finish("database-busy", ["independent process actually held SQLite exclusive transaction",
                                         "bounded runtime refusal preceded any target effect"])


def make_history(case, book, scope):
    name = "legacy-" + scope
    process = case.harness.launch(name, [
        sys.executable, "-B", str(case.root / "examples/a03/P2/history.py"),
        "--root", str(case.root), "--output", str(case.output / (name + "-archive")),
        "--book", book, "--scope", scope,
    ])
    return case.response(process.finish())


def cross_scope_pending(case):
    case.book = "p2-current-book"
    case.scope = "p2-current-scope"
    case.prepare()
    history = make_history(case, case.book, "p2-other-scope")
    crashed = case.command_raw("run", effect_fault="after_effect_exit")
    if crashed["exit_code"] != 87:
        raise AssertionError("one real current-scope pending intent required")
    case.command("historyimport", package_path=history["archive_path"], target_key=history["target_key"])
    before = case.status()
    if before["pending_count"] != 2:
        raise AssertionError("cross-scope current scan omitted an unresolved item")
    resolved = case.command("reconcile", expect_exit=3)
    if [r["classification"] for r in resolved["resolutions"]] != ["MATCH"]:
        raise AssertionError("only current local intent is eligible for MATCH")
    after = case.status()
    if after["pending_count"] != 1 or not after["paused"]:
        raise AssertionError("resolving one scope illegally cleared other-scope UNKNOWN")
    case.assert_refused(case.command_raw("run"), {"BOOK_WRITE_PAUSED", "LEGACY_UNRECORDED"})
    case.assert_effects(1)
    if hashlib.sha256(Path(history["archive_path"]).read_bytes()).hexdigest() != history["archive_sha256"]:
        raise AssertionError("original legacy UNKNOWN archive changed")
    return case.finish("cross-scope-pending", ["current DB scans both scopes",
        "one MATCH cannot discharge other-scope legacy obligation", "original UNKNOWN bytes unchanged"])


def foreign_book_pending(case):
    case.prepare()
    history = make_history(case, "p2-foreign-book", "p2-foreign-scope")
    case.command("historyimport", package_path=history["archive_path"], target_key=history["target_key"])
    if case.status()["pending_count"] != 0:
        raise AssertionError("foreign book UNKNOWN incorrectly pauses current book")
    case.command("run")
    case.assert_effects(len(case.inputs["action_ids"]))
    if hashlib.sha256(Path(history["archive_path"]).read_bytes()).hexdigest() != history["archive_sha256"]:
        raise AssertionError("foreign UNKNOWN archive changed")
    return case.finish("foreign-book-pending", ["foreign UNKNOWN retained without own-book pause",
                                               "current book independently executes all planned effects"])


def tail_absence(case, read_fault):
    case.prepare()
    if len(case.inputs["action_ids"]) < 3:
        raise AssertionError("partial plan scenario needs A, B and C")
    case.command("run", effect_fault="lost_response", read_fault="unavailable", fault_action_index=1,
                 expect_exit=3)
    case.assert_effects(2)
    initial = case.status()
    if initial["pending_count"] != 1:
        raise AssertionError("middle B must remain one pending intent")
    tail = case.inputs["action_ids"][2]
    result = case.command_raw("tailabsence", action_id=tail, read_fault=read_fault)
    if read_fault is None:
        case.response(result)
    else:
        case.assert_refused(result, {"UNATTEMPTED_ABSENT_INSUFFICIENT", "UNATTEMPTED_ABSENCE_INSUFFICIENT",
                                    "NOT_ATTEMPTED_WITHOUT_ABSENT", "ABSENCE_NOT_PROVEN"})
    after = case.status()
    if after["pending_count"] != 1 or not after["paused"]:
        raise AssertionError("tail fact cannot resolve B UNKNOWN")
    tail_rows = [item for item in after["actions"] if item["id"] == tail]
    if len(tail_rows) != 1 or tail_rows[0]["intent"] is not None:
        raise AssertionError("unattempted C must never acquire an intent")
    if read_fault is None and not tail_rows[0]["fact"]:
        raise AssertionError("complete two-read ABSENT must commit the dedicated fact")
    if read_fault is not None and tail_rows[0]["fact"]:
        raise AssertionError("incomplete ABSENT must not invent a complete fact")
    case.assert_effects(2)
    return case.finish("tail-absence-" + str(read_fault), ["A APPLIED, B UNKNOWN, C never dispatched",
        "dedicated readonly absence fact requires sufficient observations", "B remains pending and book paused"])


def public_gates(case):
    case.prepare()
    checks = (
        ("wrong-exchange-version", "RECOVERY_VERSION_UNSUPPORTED"),
        ("resource-digest", "RESOURCE_HASH_MISMATCH"),
        ("reference-extra-field", "SCHEMA"),
        ("nested-original", "SYNTHETIC_ONLY"),
        ("nested-observed", "SYNTHETIC_ONLY"),
    )
    for operation, code in checks:
        name = "gate-" + operation
        request = {"input_path": case.inputs["bundle_path"], "asset_root": case.inputs["asset_root"],
                   "gate_operation": operation, "expected_code": code}
        request_path = case.output / name / "request.json"
        process = case.harness.launch(name, [sys.executable, "-B", str(case.root / "examples/a03/P2/gate.py"),
                                           "--request", str(request_path)], request)
        case.response(process.finish())
    original = case.root / "tests/fixtures/a02/normal/input.json"
    for operation in ("archive", "reject-old"):
        name = "gate-" + operation
        request = {"input_path": str(original), "gate_operation": operation,
                   "expected_code": "RECOVERY_VERSION_UNSUPPORTED"}
        request_path = case.output / name / "request.json"
        process = case.harness.launch(name, [sys.executable, "-B", str(case.root / "examples/a03/P2/gate.py"),
                                           "--request", str(request_path)], request)
        case.response(process.finish())
    history = make_history(case, "p2-unconvertible-history", "p2-unconvertible-scope")
    name = "gate-convert-history"
    request = {"input_path": history["archive_path"], "gate_operation": "convert-history",
               "conversion_output": str(case.output / "forbidden-history-conversion"),
               "expected_code": "LEGACY_UNRECORDED"}
    request_path = case.output / name / "request.json"
    process = case.harness.launch(name, [sys.executable, "-B", str(case.root / "examples/a03/P2/gate.py"),
                                       "--request", str(request_path)], request)
    case.response(process.finish())
    case.assert_effects(0)
    return case.finish("public-gates", ["actual new-process public validation refuses version/ref/hash faults",
        "nested real provenance cannot borrow synthetic envelope", "legacy remains archive-only with source bytes unchanged"])


def timeout_bound(case):
    case.prepare()
    crashed = case.command_raw("run", effect_fault="after_effect_exit")
    if crashed["exit_code"] != 87:
        raise AssertionError("required one pending effect crash did not occur")
    case.assert_effects(1)
    case.number += 1
    process = case.harness.cli("%02d-timeout-reconcile" % case.number,
                              dict(case.common, operation="reconcile", read_fault="timeout"))
    completion = process.finish()
    result = case.response(completion, exit_code=6)
    if len(result["resolutions"]) != 1 or result["resolutions"][0]["classification"] != "INDETERMINATE":
        raise AssertionError("timed-out observations resolved an unknown effect")
    resolution = result["resolutions"][0]
    if resolution["attempt_count"] != 3:
        raise AssertionError("per-intent recovery invocation must stop after three actual failed reads")
    # The process's elapsed time also includes the previous dead owner's lease.
    # The actual intent window starts after claim; allow 250ms only for OS process
    # reaping/accounting overhead and retain the measured value in the witness.
    intent_elapsed = resolution["intent_elapsed_seconds"]
    if not 5.5 <= intent_elapsed <= 8.25:
        raise AssertionError("actual three-read intent window exceeded its eight-second bound")
    if not intent_elapsed <= completion["elapsed_seconds"] < 60:
        raise AssertionError("whole recovery process exceeded its sixty-second call bound")
    database = case.output / "runtime/runtime.sqlite3"
    connection = sqlite3.connect(str(database))
    try:
        rows_before = connection.execute(
            "SELECT intent,number,status,resource FROM attempts WHERE call_id=? ORDER BY number",
            (result["call_id"],),
        ).fetchall()
    finally:
        connection.close()
    if len(rows_before) != 3 or [row[1] for row in rows_before] != [1, 2, 3]:
        raise AssertionError("persisted call must contain exactly three numbered attempts")
    witness = []
    package_root = Path(case.registration["package_root"]).resolve()
    for intent_id, number, status, serialized in rows_before:
        if status != "FAILED_READ" or intent_id != resolution["intent_id"]:
            raise AssertionError("timeout attempt was not persisted as a failed read")
        resource = json.loads(serialized)
        path = (package_root / resource["path"]).resolve()
        if package_root not in path.parents:
            raise AssertionError("failure resource escaped this scene's package")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != resource["sha256"]:
            raise AssertionError("actual failed-read resource digest differs")
        evidence = json.loads(raw)
        if any(evidence[key] is not None for key in ("read_sequence", "target_state_version", "target_state_hash")):
            raise AssertionError("timed-out read must not invent target observation metadata")
        failure = evidence["failure"]
        if (not failure["process_reaped"] or not failure["forced_termination"]
                or failure["process_exit_code"] is None):
            raise AssertionError("timed-out observation worker was not terminated and reaped")
        if not 1.8 <= failure["read_elapsed_seconds"] <= 2.25:
            raise AssertionError("actual observation worker exceeded its two-second read deadline")
        witness.append({"number": number, "resource": resource,
                        "process_pid": failure["process_pid"], "process_exit_code": failure["process_exit_code"],
                        "process_reaped": failure["process_reaped"], "forced_termination": failure["forced_termination"],
                        "read_elapsed_seconds": failure["read_elapsed_seconds"]})
    if len({item["process_pid"] for item in witness}) != 3:
        raise AssertionError("three timeout attempts must use independent observation processes")
    write_new(case.output / "timeout-failure-witness.json", {
        "call_id": result["call_id"], "intent_elapsed_seconds": intent_elapsed,
        "outer_process_elapsed_seconds": completion["elapsed_seconds"],
        "os_accounting_epsilon_seconds": 0.25, "attempts": witness,
    })
    after = case.status()
    if after["pending_count"] != 1 or not after["paused"]:
        raise AssertionError("read limit exhaustion cleared pause")
    before_retry = case.assert_effects(1)
    restarted = case.command_raw("reconcile", call_id=result["call_id"])
    payload = restarted["stdout_json"][-1] if restarted["stdout_json"] else {}
    if payload.get("ok"):
        retry_result = payload["result"]
        retry = case.response(restarted, exit_code=6 if retry_result.get("deadline_exceeded") else 3)
        if retry["call_id"] != result["call_id"] or retry["attempt_count"] != 0:
            raise AssertionError("restarting the same call reset the persisted attempt budget")
        if any(item["attempt_count"] != 0 for item in retry["resolutions"]):
            raise AssertionError("exhausted call performed a new per-intent attempt")
    else:
        case.assert_refused(restarted, {"RECONCILE_ATTEMPT_LIMIT", "RECOVERY_DEADLINE_EXCEEDED"})
    connection = sqlite3.connect(str(database))
    try:
        rows_after = connection.execute(
            "SELECT intent,number,status,resource FROM attempts WHERE call_id=? ORDER BY number",
            (result["call_id"],),
        ).fetchall()
    finally:
        connection.close()
    if rows_before != rows_after:
        raise AssertionError("same-call restart changed old attempts or added a fourth read")
    after_retry = case.assert_effects(1)
    if before_retry["read_sequence"] != after_retry["read_sequence"]:
        raise AssertionError("exhausted same-call restart performed an actual target observation")
    refused = case.command_raw("reconcile", max_attempts=4)
    case.assert_refused(refused, {"ATTEMPT_LIMIT", "RECOVERY_ATTEMPT_LIMIT", "INVALID_ATTEMPT_LIMIT",
                                  "RECONCILE_ATTEMPT_LIMIT"})
    case.assert_effects(1)
    return case.finish("timeout-bound", ["actual bounded target read timeout attempted exactly three times",
        "failed reads cannot resolve UNKNOWN or create business effects", "same-call restart retains its exhausted budget",
        "caller cannot widen approved attempt bound"])


def absent_replan(case):
    case.prepare()
    old_plan_ref = dict(case.inputs["plan_ref"])
    old_snapshot_ref = dict(case.inputs["snapshot_ref"])
    old_action_ids = list(case.inputs["action_ids"])
    crashed = case.command_raw("run", fault_point="AFTER_INTENT_COMMIT")
    if crashed["exit_code"] != 90:
        raise AssertionError("committed-intent crash was not reached")
    case.assert_effects(0)
    resolved = case.command("reconcile")
    if [item["classification"] for item in resolved["resolutions"]] != ["ABSENT"]:
        raise AssertionError("fresh independent observation did not prove ABSENT")
    case.assert_refused(case.command_raw("run"),
                        {"REPLAY_FORBIDDEN", "PLAN_ALREADY_ACCEPTED", "PLAN_INTERRUPTED", "BOOK_WRITE_PAUSED"})
    before_target = case.assert_effects(0)
    old_export = case.command("export")
    old_bundle = old_export["bundle"]

    def exact(artifacts, ref):
        found = [a for a in artifacts if all(a[key] == ref[key] for key in
                 ("artifact_id", "revision", "kind", "content_hash"))]
        if len(found) != 1:
            raise AssertionError("export lacks one exact immutable reference")
        return found[0]

    old_plan = exact(old_bundle["artifacts"], old_plan_ref)
    replanned = case.command("replan")
    if replanned["plan_ref"] == old_plan_ref or replanned["snapshot_ref"] == old_snapshot_ref:
        raise AssertionError("ABSENT continuation reused its old plan or historical snapshot")
    if set(replanned["action_ids"]) & set(old_action_ids):
        raise AssertionError("a genuinely new plan cannot reuse old reserved action identities")
    new_export = case.command("export")
    new_bundle = new_export["bundle"]
    new_plan = exact(new_bundle["artifacts"], replanned["plan_ref"])
    if new_plan["payload"]["graph"] != old_plan["payload"]["graph"]:
        raise AssertionError("continuation unexpectedly changed the immutable graph")
    if new_plan["payload"]["precheck"] != old_plan["payload"]["precheck"]:
        raise AssertionError("unchanged source/graph PRE_APPLY must retain its exact accepted reference")
    target_check = exact(new_bundle["artifacts"], new_plan["payload"]["targetcheck"])
    if (target_check["payload"]["snapshot"] != replanned["snapshot_ref"]
            or target_check["payload"]["graph"] != new_plan["payload"]["graph"]):
        raise AssertionError("new TARGET check does not bind the actual new snapshot and exact graph")
    after_target = case.assert_effects(0)
    if after_target["read_sequence"] <= before_target["read_sequence"]:
        raise AssertionError("replanning did not perform a genuinely new target observation")
    case.command("run")
    case.assert_effects(len(replanned["action_ids"]))
    if case.status()["pending_count"]:
        raise AssertionError("newly checked plan did not finish its permitted simulated actions")
    final_bundle = case.command("export")["bundle"]
    for original in old_bundle["artifacts"]:
        reference = {key: original[key] for key in ("artifact_id", "revision", "kind", "content_hash")}
        if exact(final_bundle["artifacts"], reference) != original:
            raise AssertionError("ABSENT continuation changed old intent/resolution/history bytes")
    return case.finish("absent-replan", ["old action replay rejected after fresh ABSENT",
        "actual new snapshot and public TARGET check build a genuinely new plan",
        "unchanged source/graph retains exact accepted PRE_APPLY reference",
        "new plan executes in a separate process while original intent and resolution history remain unchanged"])


DEMOS = {"normal": normal, "effect-crash": effect_crash, "absent": absent}


def run_scenario(name, output, *, fixture="normal", root=ROOT):
    case = Scenario(output, fixture=fixture, root=root)
    try:
        return DEMOS[name](case)
    except BaseException as error:
        failure = {"scenario": name, "status": "FAIL", "type": type(error).__name__,
                   "message": str(error), "traceback": traceback.format_exc()}
        if not (case.output / "scenario-result.json").exists():
            write_new(case.output / "scenario-result.json", failure)
        raise
    finally:
        case.close()


def run_check(function, output, *args, fixture="normal", root=ROOT):
    """Retain a failed bounded check exactly as the three portable demos do."""
    case = Scenario(output, fixture=fixture, root=root)
    try:
        return function(case, *args)
    except BaseException as error:
        if not (case.output / "scenario-result.json").exists():
            write_new(case.output / "scenario-result.json", {
                "scenario": function.__name__, "arguments": args, "status": "FAIL",
                "type": type(error).__name__, "message": str(error),
                "traceback": traceback.format_exc(),
            })
        raise
    finally:
        case.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=sorted(DEMOS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture", default="normal")
    args = parser.parse_args()
    value = run_scenario(args.scenario, args.output, fixture=args.fixture)
    print(json.dumps(value, ensure_ascii=False, sort_keys=True), flush=True)
