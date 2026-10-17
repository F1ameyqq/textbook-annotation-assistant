"""Independent old/new core-trigger comparison and classification of projection diffs.

Reads frozen JSON only. No generator, author checker, runtime, target or DB calls.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def markers(case, base):
    cid = case["case_id"]
    artifacts = case["bundle"]["artifacts"]
    def arts(kind):
        return [a for a in artifacts if a["kind"] == kind]
    def art(kind):
        return arts(kind)[0]
    def pay(kind):
        return art(kind)["payload"]
    def status(result):
        return {k: result[k] for k in ["attempt_fact", "outcome", "effect_match", "next_step", "replay_allowed"]}
    def receipts():
        return [[status(r) for r in a["payload"]["results"]] for a in arts("ExecutionReceipt")]
    def progress():
        return [[{k: r[k] for k in ["attempt_fact", "effective_outcome", "dependency_status"]} for r in a["payload"]["actions"]] for a in arts("ExecutionProgress")]
    def resolutions():
        return [{k: a["payload"][k] for k in ["observation", "resolution", "replay_allowed", "attempt_index", "observation_id", "read_sequence", "observed_at", "target_state_version"]} for a in arts("ReconciliationResult")]
    if cid == "normal":
        batch = pay("BatchReport")
        return {"receipt_results": receipts(), "progress": progress(), "batch": {k: batch[k] for k in ["state", "frame_check_status", "content_check_status", "submission_status"]}}
    if cid in {"intent-no-receipt-match", "intent-no-receipt-absent", "conflict", "indeterminate"}:
        return {"resolutions": resolutions(), "has_receipt": bool(arts("ExecutionReceipt")), "progress": progress()}
    if cid in {"partial-without-absent", "partial-with-complete-absent"}:
        return {"receipt_results": receipts(), "progress": progress(), "intent_count": len(arts("WriteIntent")),
                "tail_intent_ref": next((r["intent_ref"] for a in arts("ExecutionProgress") for r in a["payload"]["actions"][-1:]), None)}
    if cid == "partial-fabricated-receipt":
        p = pay("ExecutionReceipt")
        fact = read(base / p["action_fact_refs"][-1]["path"])
        return {"receipt_results": receipts(), "tail_receipt_readback_null": p["results"][-1]["readback"] is None,
                "tail_fact_readback_present": fact["result"]["readback"] is not None}
    if cid in {"original-unknown-preserved", "recovered-report-binding"}:
        out = {"raw_receipt_results": receipts(), "resolutions": resolutions(), "progress": progress(), "intent_count": len(arts("WriteIntent"))}
        if arts("BatchReport"):
            batch = pay("BatchReport")
            out["batch"] = {k: batch[k] for k in ["state", "frame_check_status", "content_check_status", "submission_status", "unresolved_issue_ids"]}
            out["post_decision"] = next(a["payload"]["decision"] for a in arts("CheckReport") if a["payload"]["stage"] == "POST_APPLY")
        return out
    if cid == "new-read-unchanged-state-version":
        snapshots = arts("PlatformSnapshot")
        return {"resolutions": resolutions(), "snapshot_observations": [{k: a["payload"].get(k) for k in ["observed_at", "observed_version"]} for a in snapshots],
                "claims": case["runtime_claim"]}
    if cid == "cross-scope-only-one-resolved":
        return {"unresolved": [{k: u[k] for k in ["event_id", "scope_id", "classification"]} for u in case["ledger_export"]["unresolved"]],
                "scope_ids": [s["scope_id"] for s in case["ledger_export"]["scopes"]], "claims": case["runtime_claim"]}
    if cid == "legacy-unrecorded-no-intent":
        return {"unresolved": [{k: u[k] for k in ["classification", "intent_ref"]} for u in case["ledger_export"]["unresolved"]], "intent_count": len(arts("WriteIntent"))}
    if cid == "wrong-schema-version":
        return {"intent_schema": art("WriteIntent")["schema_version"]}
    if cid == "wrong-exchange-version":
        return {"exchange": case["bundle"]["format_version"]}
    if cid == "wrong-action-digest":
        return {"action_digest": pay("WriteIntent")["action_digest"]}
    if cid == "wrong-target-identity":
        return {"target_key": pay("WriteIntent")["target_key"]}
    if cid == "wrong-book-identity":
        return {"intent_book": art("WriteIntent")["book_id"]}
    if cid == "wrong-scope-reference":
        return {"intent_scope": art("WriteIntent")["scope_id"]}
    if cid == "missing-plan-reference":
        return {"plan_count": len(arts("ApplyPlan")), "intent_plan_ref_id": pay("WriteIntent")["plan_ref"]["artifact_id"]}
    if cid == "wrong-resource-hash":
        resource = pay("ReconciliationResult")["readback"]
        return {"resource_declared_sha": resource["sha256"], "actual_bytes_mismatch": hashlib.sha256((base / resource["path"]).read_bytes()).hexdigest() != resource["sha256"]}
    if cid == "missing-readback":
        return {"readback": pay("ReconciliationResult")["readback"], "observation": pay("ReconciliationResult")["observation"]}
    if cid == "wrong-observed-state-hash":
        return {"target_state_hash": pay("ReconciliationResult")["target_state_hash"]}
    if cid == "wrong-obligation-identity":
        return {"obligation_id": pay("ReconciliationResult")["obligation_id"]}
    if cid == "real-original-rejected":
        asset = pay("SourceBundle")["assets"][0]
        return {k: asset[k] for k in ["provenance", "origin"]}
    if cid == "observed-producer-rejected":
        return {"evidence_mode": art("WriteIntent")["producer"]["evidence_mode"]}
    if cid == "observed-resource-rejected":
        return {"readback_origin": pay("ReconciliationResult")["readback"]["origin"]}
    if cid == "observed-evidence-rejected":
        return {"evidence_mode": case["bundle"]["evidence"][0]["mode"]}
    if cid == "real-policy-rejected":
        return {"applicability": case["bundle"]["policies"][0]["applicability"]}
    if cid == "platform-mode-rejected":
        return {"execution_mode": pay("ApplyPlan")["execution_mode"]}
    if cid == "unknown-scope-integrity":
        return {k: pay("SourceBundle")[k] for k in ["scope_manifest", "scope_integrity"]}
    if cid in {"stale-owner-generation", "wrong-state-directory", "fake-empty-ledger", "intent-not-locally-committed", "old-observation-reuse"}:
        return {"runtime_claim": case["runtime_claim"], "resolutions": resolutions()}
    if cid == "attempt-limit-four":
        return {"attempt_index": pay("ReconciliationResult")["attempt_index"]}
    if cid in {"resolved-chain-successor", "resolution-fork", "resolution-cycle"}:
        return {"resolutions": resolutions(), "chain": [{"id": a["artifact_id"], "previous_id": None if a["payload"]["previous_resolution_ref"] is None else a["payload"]["previous_resolution_ref"]["artifact_id"],
                    "intent_id": a["payload"]["intent_ref"]["artifact_id"]} for a in arts("ReconciliationResult")]}
    if cid in {"source-only-unknown-denominator", "source-only-zero-actions"}:
        coverage = {k: pay("SourceBundle").get(k) for k in ["scope_manifest", "scope_integrity"]}
        proof = coverage["scope_integrity"]["proof"]
        if proof is not None:
            coverage["scope_integrity"]["proof"] = {k: proof[k] for k in ["sha256", "media_type", "origin"]}
            coverage["scope_integrity"]["proof"]["actual_sha256"] = hashlib.sha256((base / proof["path"]).read_bytes()).hexdigest()
        return {"source_coverage": coverage, "plan_action_counts": [len(a["payload"]["actions"]) for a in arts("ApplyPlan")],
                "runtime_claim": case["runtime_claim"]}
    raise ValueError("unreviewed core case: " + cid)


def classify(change):
    path = change["path"]
    if all(isinstance(change.get(k), str) and re.fullmatch(r"(obl-)?[0-9a-f]{64}", change[k]) for k in ["old", "new"]):
        return "DERIVED_DIGEST_OR_OBLIGATION_RESEAL"
    if path.startswith("$.runtime_claim"):
        return "R1_EXPLICIT_INTERRUPTED_READONLY_BRANCH_METADATA"
    if path.startswith("$.ledger_export"):
        return "PARTIAL_B_UNKNOWN_BOOK_PAUSE_RETAINED_EXPLICITLY"
    if "snapshot-unattempted-" in path:
        return "NEW_UNATTEMPTED_ABSENCE_DESIGN_OBSERVATION"
    if ".RESOURCE_BODY" in path or ".payload.results[" in path:
        return "UNATTEMPTED_FACT_ORIGIN_DEDICATED_PREPARED_TWO_DESIGN_READS"
    return "UNCLASSIFIED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    out, stage = args.out.resolve(), args.stage.resolve()
    if out != Path("D:/1800/docs/evidence/A03/review/P1-R1/mapping-agent").resolve():
        raise SystemExit("wrong output scope")
    original, base = stage / "examples/a03/P1", stage / "examples/a03/P1-R1/data"
    audit = read(out / "audit-results.json")
    result = {"input_commit": audit["input_commit"], "design_only": True, "semantic_or_recovery_execution": "NOT_RUN", "case_markers": [], "projection_classification": []}
    for row in read(base / "case-mapping.json")["mappings"]:
        old, new = markers(read(original / row["old_path"]), original), markers(read(base / row["r1_path"]), base)
        result["case_markers"].append({"case_id": row["old_case_id"], "old_core_trigger": old, "new_core_trigger": new, "retained": old == new})
    for entry in audit["projection_diffs"]:
        classes = Counter(classify(change) for change in entry["differences"])
        result["projection_classification"].append({"case_id": entry["case_id"], "change_count": len(entry["differences"]), "categories": dict(classes),
                    "unclassified_changes": [x for x in entry["differences"] if classify(x) == "UNCLASSIFIED"]})
    result["summary"] = {"core_trigger_cases": len(result["case_markers"]), "core_triggers_retained": sum(x["retained"] for x in result["case_markers"]),
               "projection_cases_reviewed": len(result["projection_classification"]), "unclassified_changes": sum(len(x["unclassified_changes"]) for x in result["projection_classification"])}
    (out / "trigger-retention-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    return 0 if result["summary"]["core_triggers_retained"] == 42 and result["summary"]["unclassified_changes"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
