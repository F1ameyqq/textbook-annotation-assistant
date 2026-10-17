"""Read-only recovery comparison and result construction.

No runtime database, target effects, retries or pause-clearing live here. Runtime
commits a validated result only after checking its current complete book ledger.
"""
import json
from pathlib import Path

from annotation.contracts import artifact_ref, validate_bundle, seal_artifact
from annotation.delivery.planner import compare_action_effect
from annotation.quality.targetcheck import reject, resolve_artifact


def reconcile_action(action, before_observation, after_observation, *, comparator_version="a02-facts-1"):
    """Compare independent evidence with the single shared A02 authority."""
    result = compare_action_effect(action, before_observation, after_observation,
                                   comparator_version=comparator_version)
    result["resolution"] = {"MATCH": "RESOLVED_APPLIED", "ABSENT": "RESOLVED_NOT_APPLIED"}.get(
        result["effect_match"], "STILL_UNKNOWN")
    result["replay_allowed"] = False
    return result


def _plain(value):
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


def make_reconciliation_result(bundle, intent_ref, observation, comparison, *, obligation_id,
                               recovery_call_id, attempt_index, artifact_id,
                               original_receipt_ref=None, previous_resolution_ref=None,
                               observed_snapshot_ref=None):
    """Build a new immutable proposal; this function grants no commit authority."""
    bundle = validate_bundle(bundle)
    intent = resolve_artifact(bundle, intent_ref, "WriteIntent")
    if not 1 <= attempt_index <= 3:
        reject("RECONCILE_ATTEMPT_LIMIT", "at most three observations per intent per invocation")
    observation, comparison = _plain(observation), _plain(comparison)
    if (comparison["action_id"] != intent.payload.action_id or
            comparison["action_digest"] != intent.payload.action_digest):
        reject("ACTION_DIGEST_MISMATCH", "comparison is for a different committed action")
    match = comparison["effect_match"]
    conclusive = match in ("MATCH", "ABSENT")
    snapshot = _plain(observed_snapshot_ref) if observed_snapshot_ref is not None else observation.get("snapshot_ref")
    if conclusive and (snapshot is None or observation.get("read_sequence") is None or observation.get("read_status") != "OK"):
        reject("CONCLUSIVE_READBACK_REQUIRED", "a terminal resolution requires actual complete read and fresh snapshot")
    resource = observation.get("resource", observation.get("readback"))
    payload = {"plan_ref": _plain(intent.payload.plan_ref), "intent_ref": artifact_ref(intent),
               "obligation_id": obligation_id, "action_id": intent.payload.action_id,
               "action_digest": intent.payload.action_digest,
               "original_receipt_ref": _plain(original_receipt_ref),
               "previous_resolution_ref": _plain(previous_resolution_ref),
               "observed_snapshot_ref": snapshot, "observation_id": observation["observation_id"],
               "recovery_call_id": recovery_call_id, "attempt_index": attempt_index,
               "observed_at": observation["observed_at"], "read_sequence": observation.get("read_sequence"),
               "target_state_version": observation.get("target_state_version"),
               "target_state_hash": observation.get("target_state_hash"), "observation": match,
               "resolution": {"MATCH": "RESOLVED_APPLIED", "ABSENT": "RESOLVED_NOT_APPLIED"}.get(match, "STILL_UNKNOWN"),
               "platform_ids": comparison.get("platform_ids", []), "evidence_refs": [resource] if resource else [],
               "readback": resource, "comparator_version": comparison["comparator_version"],
               "reason_code": match, "replay_allowed": False}
    # Each consuming artifact declares every exact ordinary ref in its own
    # payload and recursively consumed JSON Resources; referenced Artifact
    # payloads are deliberately not inherited into this consumer's closure.
    refs = {}
    visited = set()
    root = getattr(bundle, "asset_root", None)
    def walk(value):
        if isinstance(value, list):
            for member in value:
                walk(member)
        elif isinstance(value, dict):
            if set(value) == {"artifact_id", "revision", "kind", "content_hash"}:
                refs[tuple(value[k] for k in ("artifact_id", "revision", "kind", "content_hash"))] = value
            elif {"path", "sha256", "media_type"}.issubset(value):
                token = (value["path"], value["sha256"])
                if token not in visited and value["media_type"] == "application/json":
                    visited.add(token)
                    if root is None:
                        reject("RESOURCE_MISSING", "resource closure needs fixed package root")
                    walk(json.loads((Path(root) / value["path"]).read_text(encoding="utf-8")))
            else:
                for member in value.values():
                    walk(member)
    walk(payload)
    return seal_artifact({"schema_version": intent.schema_version, "artifact_id": artifact_id,
                          "revision": 1, "kind": "ReconciliationResult", "run_id": intent.run_id,
                          "book_id": intent.book_id, "scope_id": intent.scope_id,
                          "input_refs": list(refs.values()), "producer": {
                              "module": "a03-reconciler", "implementation_version": "a03-1",
                              "config_version": intent.producer.config_version,
                              "policy_versions": [_plain(p) for p in intent.producer.policy_versions],
                              "model_version": None, "prompt_version": None, "evidence_mode": "SYNTHETIC"},
                          "created_at": observation["observed_at"], "payload": payload})


__all__ = ["reconcile_action", "make_reconciliation_result"]
