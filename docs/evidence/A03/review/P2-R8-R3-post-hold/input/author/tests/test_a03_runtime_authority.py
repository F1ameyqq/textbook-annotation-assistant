"""Real A03 runtime/observer capability refusals, entirely synthetic.

Fixture creation and independent target probes use real child processes. Every
authority call below uses the actual RuntimeStore and PersistentMockSession;
there is no stand-in authority and no registry replacement. The configuration
drift cases explicitly mutate this new test scene's SQLite fixture, rather than
claiming that a public configuration-update API exists.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import threading
import time
import unittest
import uuid

from annotation.contracts import ContractError, validate_recovery_bundle
from annotation.delivery.mock import BookEffectGate
from annotation.runtime.storage import open_state
from annotation.runtime.storage.common import RuntimeFailure
from annotation.runtime.recovery import configuration, open_observer
from annotation.runtime.recovery.lease import LeaseKeeper


ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = ROOT / "examples/a03/P2"
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))
spec = importlib.util.spec_from_file_location("a03_authority_process_scene", DEMO_ROOT / "run.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
from processes import write_new


class RuntimeAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        selected = os.environ.get("A03_AUTHORITY_EVIDENCE_ROOT")
        cls.evidence = Path(selected).resolve() if selected else (
            ROOT / "docs/evidence/A03/execution/P2" /
            ("runtime-authority-check-" + uuid.uuid4().hex[:12]))
        cls.evidence.mkdir(parents=True, exist_ok=True)
        imports = {}
        for name in ("annotation.contracts", "annotation.runtime.storage", "annotation.runtime.recovery",
                     "annotation.delivery.mock.persistent"):
            module = __import__(name, fromlist=["__file__"])
            path = Path(module.__file__).resolve()
            if ROOT not in path.parents:
                raise AssertionError("authority test imported from another checkout: " + name)
            imports[name] = str(path)
        write_new(cls.evidence / "environment.json", {
            "python": sys.version, "python_executable": sys.executable,
            "sqlite": sqlite3.sqlite_version, "cwd": str(Path.cwd()),
            "direct_api_process_pid": os.getpid(), "actual_imports": imports,
            "provenance": "SYNTHETIC", "execution_mode": "SIMULATED",
        })

    def setUp(self):
        self.scene = demo.Scenario(self.evidence / self._testMethodName, root=ROOT)
        self.claim = None
        self.store = None
        self.refusal_number = 0
        self.addCleanup(self.cleanup_scene)
        self.scene.prepare()
        self.open_runtime()
        self.claim = self.store.claim(self.key, observer=self.observer,
                                      owner_id="authority-" + uuid.uuid4().hex)
        self.store.accept_plan(self.registration["id"], self.scene.inputs["plan_ref"], **self.owner)
        context = self.store.load_book_context(self.key, **self.owner)
        self.observer.import_book_context(context, authority=self.store)
        self.bundle = validate_recovery_bundle(self.store.bundle(self.registration["id"]),
                                               asset_root=self.registration["package_root"])
        self.prepared = self.observer.prepare_action(
            self.bundle, self.scene.inputs["plan_ref"], self.scene.inputs["action_ids"][0],
            configuration(json.loads(self.registration["config"])),
            current_snapshot_ref=self.scene.inputs["snapshot_ref"],
            asset_root=self.registration["package_root"],
        )

    @property
    def owner(self):
        return {"owner_id": self.claim["owner_id"], "generation": self.claim["generation"]}

    def open_runtime(self):
        common = self.scene.common
        self.store = open_state(common["anchor_path"],
                                expected_ledger_id=common["expected_ledger_id"],
                                expected_target_store_id=common["expected_target_store_id"])
        self.registration = self.store.registration(self.scene.registration["registration_id"])
        self.key = self.store.target_key(self.registration["id"])
        self.observer = open_observer(self.store, self.registration["id"])

    def cleanup_scene(self):
        if self.store is not None and self.claim is not None:
            try:
                self.store.release(self.key, **self.owner)
            except (RuntimeFailure, ContractError) as error:
                write_new(self.scene.output / "cleanup-release-refusal.json", {
                    "type": type(error).__name__, "message": str(error),
                    "reason": "release only this test's exact claim; never clear another generation",
                })
        self.scene.close()

    def refused(self, code, action):
        try:
            action()
        except (ContractError, RuntimeFailure) as error:
            codes = [issue["code"] for issue in error.issues] if isinstance(error, ContractError) else [error.code]
            self.assertIn(code, codes)
            self.refusal_number += 1
            write_new(self.scene.output / ("refusal-%02d.json" % self.refusal_number), {
                "expected_code": code, "actual_codes": codes, "message": str(error),
                "direct_api_process_pid": os.getpid(),
            })
            return
        self.fail("actual runtime accepted the unverified capability: " + code)

    def native_intent(self):
        return self.store.commit_intent(self.prepared, **self.owner)

    def native_permit(self, intent, binding=None):
        return self.store.issue_first_dispatch(
            intent["intent_ref"], plan_ref=self.scene.inputs["plan_ref"],
            action_id=self.scene.inputs["action_ids"][0],
            observation_binding=self.prepared["observation_binding"] if binding is None else binding,
            **self.owner,
        )

    def consume(self, permit, prepared):
        with self.store.effect_gate(self.key) as gate:
            return self.store.consume_first_dispatch(
                permit, effect_gate=gate, prepared_action=prepared,
                target_store_id=self.scene.common["expected_target_store_id"],
                target_session_id="a03-p2-session",
            )

    def no_dispatch(self, *, intents, permits):
        status = self.store.status(self.registration["id"])
        events = [event["event"] for event in status["events"]]
        self.assertNotIn("DISPATCH_STARTED", events)
        self.assertNotIn("DISPATCH_PERMIT_CONSUMED", events)
        with self.store.connect() as connection:
            actual_intents = connection.execute("SELECT COUNT(*) FROM intents").fetchone()[0]
            actual_permits = [dict(row) for row in connection.execute("SELECT * FROM permits")]
        self.assertEqual(actual_intents, intents)
        self.assertEqual(len(actual_permits), permits)
        self.assertTrue(all(row["state"] == "ISSUED" for row in actual_permits))
        self.assertEqual(status["pending_count"], intents)
        target = self.scene.assert_effects(0)
        self.assertEqual(target["dispatch_count"], 0)
        write_new(self.scene.output / "authority-refusal-witness.json", {
            "status": "PASS", "expected_intents": intents, "actual_intents": actual_intents,
            "expected_permits": permits, "actual_permits": actual_permits,
            "event_names": events, "event_head": status["event_head"],
            "target_effect_count": target["effect_count"], "target_dispatch_count": target["dispatch_count"],
            "independent_target_process": self.scene.observations[-1]["pid"],
            "direct_api_process_pid": os.getpid(), "used_real_store_and_observer": True,
        })

    def change_current_configuration(self):
        data = json.loads(self.registration["config"])
        changed = copy.deepcopy(data)
        first = sorted(changed["directory_map"])[0]
        changed["directory_map"][first] += "-synthetic-configuration-drift"
        self.assertNotEqual(configuration(data).version, configuration(changed).version)
        write_new(self.scene.output / "synthetic-configuration-fixture-mutation.json", {
            "kind": "DIRECT_SYNTHETIC_TEST_DB_MUTATION", "public_configuration_update_api": False,
            "before": data, "after": changed,
        })
        with self.store.transaction() as connection:
            connection.execute("UPDATE registrations SET config=? WHERE id=?",
                               (json.dumps(changed, sort_keys=True), self.registration["id"]))

    def test_copied_dictionary_cannot_commit_native_preparation(self):
        self.refused("PREPARED_ACTION_UNVERIFIED",
                     lambda: self.store.commit_intent(dict(self.prepared), **self.owner))
        self.no_dispatch(intents=0, permits=0)

    def test_deep_copied_native_type_cannot_commit(self):
        copied = copy.deepcopy(self.prepared)
        self.assertIsNot(copied, self.prepared)
        self.refused("PREPARED_ACTION_UNVERIFIED",
                     lambda: self.store.commit_intent(copied, **self.owner))
        self.no_dispatch(intents=0, permits=0)

    def test_handmade_truthy_dictionary_cannot_commit(self):
        forged = {"target_key": copy.deepcopy(self.key), "action_id": self.prepared["action_id"],
                  "action_digest": self.prepared["action_digest"], "plan_ref": self.scene.inputs["plan_ref"],
                  "target_store_id": self.scene.common["expected_target_store_id"],
                  "target_session_id": "a03-p2-session", "scope_id": self.registration["scope"],
                  "source_ref": json.loads(self.registration["source"]),
                  "prepared_before": copy.deepcopy(self.prepared["prepared_before"]),
                  "observation_binding": {"verified": True}}
        self.refused("PREPARED_ACTION_UNVERIFIED",
                     lambda: self.store.commit_intent(forged, **self.owner))
        self.no_dispatch(intents=0, permits=0)

    def test_truthy_binding_cannot_issue_a_permit_after_real_intent(self):
        intent = self.native_intent()
        self.refused("OBSERVATION_BINDING_MISMATCH",
                     lambda: self.native_permit(intent, {"verified": True}))
        self.no_dispatch(intents=1, permits=0)

    def test_copied_prepared_cannot_consume_a_real_permit(self):
        intent = self.native_intent()
        permit = self.native_permit(intent)
        self.refused("PREPARED_ACTION_UNVERIFIED",
                     lambda: self.consume(permit, dict(self.prepared)))
        self.no_dispatch(intents=1, permits=1)

    def test_changed_native_prepared_cannot_consume_a_real_permit(self):
        intent = self.native_intent()
        permit = self.native_permit(intent)
        self.prepared["observation_binding"] = {"verified": True}
        self.refused("OBSERVATION_BINDING_MISMATCH", lambda: self.consume(permit, self.prepared))
        self.no_dispatch(intents=1, permits=1)

    def test_new_runtime_observer_cannot_redeem_old_native_prepared(self):
        old_prepared = self.prepared
        self.store.release(self.key, **self.owner)
        self.claim = None
        self.open_runtime()
        self.claim = self.store.claim(self.key, observer=self.observer,
                                      owner_id="new-observer-" + uuid.uuid4().hex)
        # The current public gate rejects the interrupted plan before minting a
        # new capability. Exact observer registry identity has separate target
        # tests; this case does not rewrite the private registry to reach it.
        self.refused("PLAN_INTERRUPTED",
                     lambda: self.store.commit_intent(old_prepared, **self.owner))
        self.no_dispatch(intents=0, permits=0)

    def test_current_configuration_drift_refuses_intent_commit(self):
        self.change_current_configuration()
        self.refused("AUTHORIZATION_CHANGED", lambda: self.native_intent())
        self.no_dispatch(intents=0, permits=0)

    def test_current_configuration_drift_refuses_permit_issue(self):
        intent = self.native_intent()
        self.change_current_configuration()
        self.refused("AUTHORIZATION_CHANGED", lambda: self.native_permit(intent))
        self.no_dispatch(intents=1, permits=0)

    def test_gate_lease_forged_held_gate_cannot_consume_permit(self):
        intent = self.native_intent()
        permit = self.native_permit(intent)
        canonical_gate = self.store.effect_gate(self.key)
        forged = BookEffectGate(canonical_gate.path, self.key)
        forged.held = True  # Deliberate test input: no __enter__/OS acquisition.
        self.assertIsNot(forged, canonical_gate)
        self.assertEqual(forged.path, canonical_gate.path)
        self.assertFalse(canonical_gate.held)
        self.refused("EFFECT_GATE_REQUIRED", lambda: self.store.consume_first_dispatch(
            permit, effect_gate=forged, prepared_action=self.prepared,
            target_store_id=self.scene.common["expected_target_store_id"],
            target_session_id="a03-p2-session",
        ))
        write_new(self.scene.output / "forged-gate-input.json", {
            "same_canonical_path": forged.path == canonical_gate.path,
            "forged_held_flag": forged.held, "canonical_gate_actually_held": canonical_gate.held,
            "forged_gate_enter_or_acquire_called": False,
        })
        self.no_dispatch(intents=1, permits=1)

    def test_gate_lease_keeper_really_renews_and_stops_its_thread(self):
        def actual_lease():
            with self.store.connect() as connection:
                return connection.execute("SELECT lease FROM books WHERE key=?",
                                          (self.registration["book"],)).fetchone()[0]

        before = actual_lease()
        started = time.monotonic()
        deadline = started + 4
        first_change = None
        samples = []
        keeper = LeaseKeeper(self.store, self.key, self.claim["owner_id"], self.claim["generation"]).start()
        poll = threading.Event()
        try:
            while True:
                keeper.check()
                elapsed = time.monotonic() - started
                current = actual_lease()
                samples.append({"elapsed_seconds": elapsed, "persisted_lease": current})
                if current > before and first_change is None:
                    first_change = elapsed
                if elapsed >= 2.2 and current > before:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self.fail("real persisted lease was not extended within the four-second observation bound")
                poll.wait(min(0.025, remaining))
        finally:
            try:
                keeper.stop()
            finally:
                write_new(self.scene.output / "lease-renewal-witness.json", {
                    "baseline_lease": before, "first_observed_change_seconds": first_change,
                    "samples": samples, "observed_for_seconds": time.monotonic() - started,
                    "configured_renewal_period_seconds": 2,
                    "owned_thread_name": keeper.thread.name, "owned_thread_alive_after_stop": keeper.thread.is_alive(),
                    "keeper_error": str(keeper.error) if keeper.error else None,
                    "direct_api_process_pid": os.getpid(),
                })
        keeper.check()
        self.assertIsNotNone(first_change)
        self.assertGreaterEqual(first_change, 1.8)
        self.assertLessEqual(first_change, 4)
        self.assertGreater(samples[-1]["persisted_lease"], before)
        self.assertFalse(keeper.thread.is_alive())
        self.no_dispatch(intents=0, permits=0)


if __name__ == "__main__":
    unittest.main()
