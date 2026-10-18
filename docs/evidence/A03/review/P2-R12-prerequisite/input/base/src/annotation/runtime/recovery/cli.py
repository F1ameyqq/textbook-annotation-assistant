"""Local JSON-request CLI. No network, browser or automatic recovery loop."""
import argparse
import json
import sys
from pathlib import Path

from annotation.runtime.storage import init_state, open_state
from annotation.runtime.storage.common import FaultController, RuntimeFailure, plain, reference, fail, unique
from . import open_observer, claim_current, configuration, run_plan, reconcile, publish_quality


def operate(request):
    from annotation.contracts import load_recovery_bundle
    from annotation.delivery.mock.persistent import PersistentMockSession
    operation = request["operation"]
    expected = {key: request[key] for key in ("expected_ledger_id", "expected_target_store_id")}
    if operation == "init":
        bundle = load_recovery_bundle(request["bundle_path"], asset_root=request.get("asset_root"))
        data = plain(bundle)
        source = request.get("source_ref") or reference(next(a for a in data["artifacts"] if a["kind"] == "SourceBundle"))
        snapshot = request.get("snapshot_ref") or reference(next(a for a in data["artifacts"] if a["kind"] == "PlatformSnapshot"))
        snapshot_value = next(a for a in data["artifacts"] if reference(a) == snapshot)
        namespace = request.get("platform_namespace", "a03-mock")
        key = {"platform_namespace": namespace, "target_id": snapshot_value["payload"]["target_id"], "book_id": snapshot_value["book_id"]}
        config = json.loads(Path(request["config_path"]).read_bytes())
        store = init_state(request["anchor_path"], state_dir=request["state_dir"], **expected)
        root = request.get("asset_root", str(Path(request["bundle_path"]).resolve().parent))
        session = request.get("target_session_id", "a03-p2-session")
        registered = store.register_book(bundle, target_key=key, target_dir=request["target_dir"], target_session_id=session,
            source_ref=source, asset_root=root, config=config, registration_id=request.get("registration_id"))
        observer = PersistentMockSession.create(request["target_dir"], bundle, snapshot, platform_namespace=namespace,
            source_ref=source, asset_root=registered["package_root"], expected_store_id=store.target_store_id, target_session_id=session)
        current = build_current_plan(store, registered["registration_id"], observer, config)
        result = plain(registered)
        result.update(plan_ref=reference(current), action_ids=[a["action_id"] for a in current["payload"]["actions"]],
                      snapshot_ref=current["payload"]["snapshot"])
        return result
    store = open_state(request["anchor_path"], **expected)
    rid = request.get("registration_id")
    fault = request.get("fault") or ({"point": request["fault_point"]} if request.get("fault_point") else None)
    store.fault = FaultController(fault)
    if operation == "status":
        return store.status(rid)
    if operation == "export":
        return store.export(rid)
    if operation == "target-status":
        observer = open_observer(store, rid)
        return plain(observer.export_book_context(store.target_key(store.registration(rid)["id"])))
    if operation == "run":
        return run_plan(store, rid, fault=fault, fault_action_index=request.get("fault_action_index", 0),
            effect_fault=request.get("effect_fault"), read_fault=request.get("read_fault"),
            owner_id=request.get("owner_id"), generation=request.get("generation"),
            config=json.loads(Path(request["config_path"]).read_bytes()) if request.get("config_path") else None)
    if operation == "reconcile":
        return reconcile(store, rid, call_id=request.get("call_id"), read_fault=request.get("read_fault"),
            owner_id=request.get("owner_id"), max_attempts=request.get("max_attempts", 3), intent_filter=request.get("intent_filter"))
    if operation == "quality":
        return publish_quality(store, store.registration(rid)["id"])
    if operation in ("detect-drift", "clear-hold"):
        from .lease import LeaseKeeper
        reg = store.registration(rid)
        observer = open_observer(store, reg["id"])
        key = store.target_key(reg["id"])
        claim = claim_current(store, observer, key, request.get("owner_id"))
        owner, generation = claim["owner_id"], claim["generation"]
        keeper = LeaseKeeper(store, key, owner, generation).start()
        try:
            if operation == "detect-drift":
                return plain(store.detect_target_drift(key, owner_id=owner, generation=generation, observer=observer))
            return plain(store.clear_target_drift_hold(request["hold_id"], request["snapshot_ref"],
                request["precheck_ref"], request["targetcheck_ref"], request["candidate_plan_ref"],
                owner_id=owner, generation=generation))
        finally:
            keeper.stop()
            store.release(key, owner_id=owner, generation=generation)
    if operation == "claim":
        observer = open_observer(store, rid)
        return plain(store.claim(store.target_key(store.registration(rid)["id"]), observer=observer, owner_id=request.get("owner_id")))
    if operation in ("import-history", "import_history_archive", "history-import", "historyimport"):
        return store.import_history_archive(request["package_path"], expected_ledger_id=store.ledger_id,
            target_key=request.get("target_key") or store.target_key(store.registration(rid)["id"]))
    if operation == "replan":
        reg = store.registration(rid)
        observer = open_observer(store, reg["id"])
        if store.status(reg["id"])["pending_count"]:
            fail("BOOK_WRITE_PAUSED")
        config = json.loads(Path(request["config_path"]).read_bytes()) if request.get("config_path") else json.loads(reg["config"])
        plan = build_current_plan(store, reg["id"], observer, config)
        return {"plan_ref": reference(plan), "action_ids": [a["action_id"] for a in plan["payload"]["actions"]],
                "snapshot_ref": plan["payload"]["snapshot"]}
    if operation in ("tail-absence", "commit-unattempted-absence", "tailabsence"):
        reg = store.registration(rid)
        observer = open_observer(store, reg["id"])
        claim = claim_current(store, observer, store.target_key(reg["id"]), request.get("owner_id"))
        try:
            status = store.status(reg["id"])
            plan = store._plan(reg["id"])
            action = next(a for a in plan["payload"]["actions"] if a["action_id"] == request["action_id"])
            return plain(store.commit_unattempted_absence(store.bundle(reg["id"]), {"registration_id": reg["id"],
                "plan_ref": reference(plan), "action_id": action["action_id"], "action_digest": __import__("annotation.runtime.storage.common", fromlist=["digest"]).digest(action),
                "expected_event_head": status["event_head"]}, owner_id=claim["owner_id"], generation=claim["generation"],
                asset_root=reg["package_root"], observer=observer))
        finally:
            store.release(store.target_key(reg["id"]), owner_id=claim["owner_id"], generation=claim["generation"])
    fail("INVALID_OPERATION", operation)


def build_current_plan(store, registration_id, observer, config):
    with store.effect_gate(store.target_key(registration_id)).acquire():
        if store.status(registration_id)["pending_count"]:
            fail("BOOK_WRITE_PAUSED")
        return _build_current_plan_locked(store, registration_id, observer, config)


def _build_current_plan_locked(store, registration_id, observer, config):
    """Read the actual target then reuse public A02 checks/planning authority.

    The immutable source/graph content PRE_APPLY stays exact; this does not
    pretend to implement B-side recognition or a new precheck algorithm.
    """
    from annotation.contracts import validate_recovery_bundle, policy_ref
    from annotation.delivery.planner import create_plan
    from annotation.quality.targetcheck import append_artifacts, check_target
    reg = store.registration(registration_id)
    observation = observer.observe_target(store.target_key(registration_id), observation_id=unique("plan-observation"))
    captured, snapshot = store.capture_observation(observation, observer, registration_id)
    bundle = validate_recovery_bundle(store.bundle(registration_id), asset_root=reg["package_root"])
    bundle = append_artifacts(bundle, snapshot, asset_root=reg["package_root"])
    graph = next(a for a in bundle.artifacts if a.kind == "QuestionGraph")
    pre = next(a for a in bundle.artifacts if a.kind == "CheckReport" and a.payload.stage == "PRE_APPLY")
    cfg = configuration(config)
    output = check_target(bundle, reference(graph), reference(snapshot), reference(snapshot), policy_ref(bundle.policies[0]),
        cfg, artifact_id=unique("targetcheck"), created_at=snapshot["created_at"])
    target = output.artifacts[-1]
    output = create_plan(output, reference(graph), reference(pre), reference(target), reference(snapshot), reference(snapshot),
        policy_ref(bundle.policies[0]), cfg, artifact_id=unique("plan"), created_at=snapshot["created_at"])
    with store.transaction() as connection:
        for artifact in plain(output)["artifacts"]:
            store._artifact(connection, artifact)
        store._save_bundle(connection, registration_id, plain(output))
    return plain(output.artifacts[-1])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    args = parser.parse_args(argv)
    operation = None
    try:
        request = json.loads(args.request.read_bytes())
        operation = request.get("operation")
        result = operate(request)
        print(json.dumps({"ok": True, "operation": operation, "result": plain(result)}, ensure_ascii=False, sort_keys=True))
        if result.get("deadline_exceeded"):
            return 6
        return 3 if operation in ("run", "reconcile") and result.get("pending_count", 0) else 0
    except RuntimeFailure as error:
        print(json.dumps({"ok": False, "operation": operation, "code": error.code, "message": str(error)}, ensure_ascii=False))
        return error.exit_code
    except Exception as error:
        errors = getattr(error, "issues", None)
        if errors is not None:
            code = errors[0].get("code", "INVALID_INPUT") if isinstance(errors, list) and errors else "INVALID_INPUT"
            print(json.dumps({"ok": False, "operation": operation, "code": code, "errors": errors}, ensure_ascii=False))
            return 7 if code in ("SYNTHETIC_ONLY", "SYNTHETIC_COMPLETE_REQUIRED") else 2
        print(json.dumps({"ok": False, "operation": operation, "code": "UNEXPECTED_IMPLEMENTATION_ERROR",
                          "message": str(error), "type": type(error).__name__}, ensure_ascii=False))
        return 5


if __name__ == "__main__":
    sys.exit(main())
