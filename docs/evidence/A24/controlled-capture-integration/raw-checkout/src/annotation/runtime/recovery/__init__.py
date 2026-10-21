"""Finite local recovery orchestration; it never replays an old action."""
import copy
import json
from pathlib import Path
import time

from annotation.runtime.storage.common import Handle, RuntimeFailure, fail, plain, reference, unique, now


def configuration(value):
    from annotation.quality.targetcheck import SimulationConfig
    value = dict(value)
    value["allowed_operations"] = tuple(value.get("allowed_operations", ("CREATE_FRAMES",)))
    return SimulationConfig(**value)


def open_observer(store, registration_id=None):
    from annotation.delivery.mock.persistent import PersistentMockSession
    reg = store.registration(registration_id)
    return PersistentMockSession.open(reg["target_dir"], expected_store_id=store.target_store_id,
        expected_target_session_id=reg["session"], expected_target_key=store.target_key(reg["id"]),
        expected_scope_id=reg["scope"], expected_source_ref=json.loads(reg["source"]),
        bridge_context=store.bridge_for(store.bundle(reg["id"]), reg["package_root"]))


def publish_quality(store, registration_id, projection=None, *, owner_id=None, generation=None):
    """Append complete report consumers or return a full diagnostic scope."""
    if getattr(store, '_user_version', 1) == 4:
        from .native_quality import publish_native_quality
        return publish_native_quality(store, registration_id, projection,
            owner_id=owner_id, generation=generation)
    from .quality import build_quality_report
    from annotation.contracts import validate_recovery_bundle
    reg = store.registration(registration_id)
    with store.effect_gate(store.target_key(reg["id"])).acquire():
        bundle = store._validate(store.bundle(reg["id"]), asset_root=reg["package_root"])
        if projection is None:
            plan = store._plan(reg["id"])
            projection = store.project_plan(reg["id"], plan)
            bundle = store._validate(store.bundle(reg["id"]), asset_root=reg["package_root"])
        expected_path = store.registration(reg["id"])["bundle_path"]
        output = build_quality_report(bundle, target_key=store.target_key(reg["id"]),
            source_ref=json.loads(reg["source"]), receipt_ref=projection.get("receipt_ref"),
            progress_ref=projection.get("progress_ref"), config_version=configuration(json.loads(reg["config"])).version,
            postcheck_id=unique("postcheck"), batch_id=unique("batch"), created_at=now(), asset_root=reg["package_root"])
        if output.postcheck_ref is not None:
            with store.transaction() as connection:
                current = connection.execute("SELECT bundle_path FROM registrations WHERE id=?", (reg["id"],)).fetchone()
                if current["bundle_path"] != expected_path:
                    fail("REPORT_SOURCE_CHANGED", "history changed during report projection")
                for artifact in plain(output.bundle)["artifacts"]:
                    store._artifact(connection, artifact)
                store._save_bundle(connection, reg["id"], plain(output.bundle))
        return output.diagnostic


def claim_current(store, observer, target_key, owner_id=None, *, deadline=None):
    # A dead owner's unexpired lease is a real bound, not permission to steal.
    deadline = min(time.monotonic() + 11, deadline) if deadline is not None else time.monotonic() + 11
    while True:
        if time.monotonic() >= deadline:
            fail("RECOVERY_DEADLINE_EXCEEDED", "owner acquisition deadline exhausted", 6)
        try:
            with store.effect_gate(target_key).acquire(timeout=min(5, max(0, deadline - time.monotonic()))):
                return store.claim(target_key, observer=observer, owner_id=owner_id)
        except RuntimeFailure as error:
            if error.code != "OWNER_BUSY":
                raise
            with store.connect() as connection:
                previous = connection.execute("SELECT pid,lease FROM books WHERE key=?", (store.book_id(target_key),)).fetchone()
            if not previous or store._pid_alive(previous["pid"]) or time.monotonic() >= deadline:
                raise
            time.sleep(min(.1, max(.01, previous["lease"] - time.time())))


def run_plan(store, registration_id=None, *, fault=None, fault_action_index=0, effect_fault=None, read_fault=None,
             owner_id=None, generation=None, config=None):
    from annotation.contracts import validate_recovery_bundle
    from annotation.delivery.mock import compare_action
    from annotation.runtime.storage.common import FaultController
    reg = store.registration(registration_id)
    key = store.target_key(reg["id"])
    observer = open_observer(store, reg["id"])
    if generation is not None:
        with store.connect() as connection:
            store._lease(connection, reg["book"], owner_id, generation)
        claim = Handle(owner_id=owner_id, generation=generation)
        store._observers[reg["book"]] = observer
    else:
        claim = claim_current(store, observer, key, owner_id)
    owner_id, generation = claim["owner_id"], claim["generation"]
    config = configuration(config or json.loads(reg["config"]))
    plan = store._plan(reg["id"])
    completed = []
    from .lease import LeaseKeeper
    keeper = LeaseKeeper(store, key, owner_id, generation).start()
    try:
        store.accept_plan(reg["id"], reference(plan), owner_id=owner_id, generation=generation)
        for index, action in enumerate(plan["payload"]["actions"]):
            keeper.check()
            store.fault = FaultController(fault if index == fault_action_index else None)
            store.renew(key, owner_id=owner_id, generation=generation)
            context = store.load_book_context(key, owner_id=owner_id, generation=generation)
            observer.import_book_context(context, authority=store)
            bundle = store._validate(store.bundle(reg["id"]), asset_root=reg["package_root"])
            prepared = observer.prepare_action(bundle, reference(plan), action["action_id"], config,
                current_snapshot_ref=plan["payload"]["snapshot"], asset_root=reg["package_root"],
                bridge_context=getattr(bundle, "bridge_context", None))
            intent = store.commit_intent(prepared, owner_id=owner_id, generation=generation)
            permit = store.issue_first_dispatch(intent["intent_ref"], owner_id=owner_id, generation=generation,
                plan_ref=reference(plan), action_id=action["action_id"], observation_binding=prepared["observation_binding"])
            observer.dispatch_action(prepared, committed_intent=intent, dispatch_permit=permit,
                authority=store, effect_fault=effect_fault if index == fault_action_index else None)
            observed = observer.observe_target(key, observation_id=unique("execute-observation"),
                read_fault=read_fault if index == fault_action_index else None)
            store.fault("AFTER_READBACK_CAPTURE")
            comparison = compare_action(prepared["action"], prepared["observation"], observed)
            record = store.commit_action_result(intent, prepared, observed, comparison, owner_id=owner_id, generation=generation)
            completed.append(plain(record))
            if record["result"]["outcome"] != "APPLIED":
                break
        status = store.status(reg["id"])
        projection = store.project_plan(reg["id"], plan)
        quality = publish_quality(store, reg["id"], projection, owner_id=owner_id, generation=generation)
        return {"records": completed, "pending_count": status["pending_count"], "paused": status["paused"],
            "progress": projection, "quality": quality, "status": "HOLD_PENDING" if status["paused"] else "FINISHED",
            "target": plain(observer.export_book_context(key))}
    finally:
        # os._exit bypasses this deliberately; lease/OS gate recovery is tested.
        store.fault = FaultController()
        keeper.stop()
        store.release(key, owner_id=owner_id, generation=generation)


def reconcile(store, registration_id=None, *, call_id=None, read_fault=None, owner_id=None,
              max_attempts=3, intent_filter=None):
    from annotation.contracts import validate_recovery_bundle
    from annotation.delivery.reconciler import reconcile_action, make_reconciliation_result
    from .observation import observe_bounded
    if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
        fail("RECONCILE_ATTEMPT_LIMIT", "approved per-call maximum is three", 2)
    reg = store.registration(registration_id)
    key, observer = store.target_key(reg["id"]), open_observer(store, reg["id"])
    call = store.begin_recovery_call(key, call_id)
    deadline = time.monotonic() + min(60, max(0, call["created"] + 60 - time.time()))
    claim = claim_current(store, observer, key, owner_id, deadline=deadline)
    owner, generation = claim["owner_id"], claim["generation"]
    results = []
    attempts_total = 0
    from .lease import LeaseKeeper
    keeper = LeaseKeeper(store, key, owner, generation).start()
    try:
        for iid in json.loads(call["queue"]):
            keeper.check()
            row = store.pending_intent(iid)
            if row["state"] != "PENDING":
                continue
            if intent_filter and iid != intent_filter:
                results.append({"intent_id": iid, "status": "NOT_VISITED", "attempt_count": 0})
                continue
            intent_started = time.monotonic()
            per_intent = min(deadline, intent_started + store.intent_remaining_seconds(call["id"], iid))
            record = {"intent_id": iid, "status": "STILL_UNKNOWN", "classification": "INDETERMINATE", "attempt_count": 0}
            for _ in range(max_attempts):
                keeper.check()
                if time.monotonic() >= per_intent:
                    record["code"] = "RECOVERY_DEADLINE_EXCEEDED"
                    break
                try:
                    number = store.register_attempt(call["id"], iid, owner_id=owner, generation=generation)
                except RuntimeFailure as error:
                    if error.code == "RECONCILE_ATTEMPT_LIMIT":
                        record["code"] = error.code
                        break
                    raise
                store.renew(key, owner_id=owner, generation=generation)
                source = json.loads(Path(row["prepared"]).read_bytes())
                before = store.read_resource(source["intent"]["payload"]["prepared_before"], reg["id"])
                captured_process = observe_bounded(observer, read_fault=read_fault,
                    timeout=min(2, max(0, per_intent - time.monotonic())))
                elapsed = captured_process["read_elapsed_seconds"]
                if not captured_process["ok"] or elapsed > 2 or time.monotonic() >= per_intent:
                    failed = store.fail_attempt(call["id"], iid, number, captured_process, reg["id"])
                    attempts_total += 1
                    record.update(attempt_count=record["attempt_count"] + 1, last_attempt_index=number,
                        code=captured_process.get("code", "TARGET_READ_TIMEOUT"), failure_resource=failed)
                    continue
                observation = captured_process["observation"]
                store._observation_deadlines[observation["observation_id"]] = per_intent
                captured, snapshot = store.capture_observation(observation, observer, reg["id"])
                if snapshot:
                    with store.transaction() as connection:
                        store._append(connection, reg["id"], snapshot)
                comparison = reconcile_action(source["prepared"]["action"], before, observation)
                bundle = store._validate(store.bundle(reg["id"]), asset_root=reg["package_root"])
                with store.connect() as connection:
                    previous = connection.execute("SELECT ref FROM resolutions WHERE intent=? ORDER BY rowid DESC LIMIT 1", (iid,)).fetchone()
                result = make_reconciliation_result(bundle, json.loads(row["ref"]), captured, comparison,
                    obligation_id=row["obligation"], recovery_call_id=call["id"], attempt_index=number,
                    artifact_id=unique("resolution"), original_receipt_ref=json.loads(row["receipt"]) if row["receipt"] else None,
                    previous_resolution_ref=json.loads(previous[0]) if previous else None,
                    observed_snapshot_ref=reference(snapshot) if snapshot else None, bridge_context=getattr(bundle, "bridge_context", None))
                committed = store.commit_reconciliation(result, owner_id=owner, generation=generation)
                attempts_total += 1
                record.update(status=committed["resolution"], classification=committed["classification"],
                    attempt_count=record["attempt_count"] + 1, result_ref=committed["result_ref"], last_attempt_index=number)
                if committed["resolution"] != "STILL_UNKNOWN":
                    break
            record["intent_elapsed_seconds"] = time.monotonic() - intent_started
            results.append(record)
        status = store.status(reg["id"])
        return {"call_id": call["id"], "resolutions": results, "attempt_count": attempts_total,
            "pending_count": status["pending_count"], "paused": status["paused"],
            "deadline_exceeded": any(r.get("code") in ("TARGET_READ_TIMEOUT", "RECOVERY_DEADLINE_EXCEEDED") for r in results),
            "target_effects_during_reconcile": 0, "status": "HOLD_PENDING" if status["paused"] else "RESOLVED"}
    finally:
        keeper.stop()
        store.release(key, owner_id=owner, generation=generation)
