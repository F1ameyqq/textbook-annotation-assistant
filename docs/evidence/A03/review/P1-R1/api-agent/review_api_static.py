"""Independent P1-R1 static inspection. Never imports author checkers or runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def refs(value):
    found = []
    if isinstance(value, dict):
        if set(value) == {"path", "sha256", "media_type", "origin"}:
            found.append(value)
        for child in value.values():
            found.extend(refs(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(refs(child))
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    stage = Path(args.stage).resolve()
    out = Path(args.out).resolve()
    allowed = Path("D:/1800/docs/evidence/A03/review/P1-R1/api-agent").resolve()
    if out != allowed:
        raise ValueError("Output must be the assigned new api-agent evidence directory")
    package = stage / "examples/a03/P1-R1"
    data = package / "data"
    api = load(package / "api-proposal.json")
    manifest = load(data / "case-manifest.json")
    case = load(data / "cases/unattempted-absence-commit.json")
    receipt = next(a for a in case["bundle"]["artifacts"] if a["kind"] == "ExecutionReceipt")
    progress = next(a for a in case["bundle"]["artifacts"] if a["kind"] == "ExecutionProgress")
    all_facts = [(r, load(data / r["path"])) for r in receipt["payload"]["action_fact_refs"]]
    fact_ref, fact = next((r, f) for r, f in all_facts if f["origin_phase"] == "UNATTEMPTED_ABSENCE")
    basis_ref = fact["unattempted_basis"]
    basis = load(data / basis_ref["path"])
    prefix_ref = basis["complete_uncalled_prefix"]
    prefix = load(data / prefix_ref["path"])
    first = load(data / basis["first_observation_ref"]["path"])
    second = load(data / basis["second_observation_ref"]["path"])
    prepared = load(data / basis["readonly_prepared_ref"]["path"])
    tail_id = fact["action_id"]
    tail_result = next(r for r in receipt["payload"]["results"] if r["action_id"] == tail_id)
    tail_progress = next(r for r in progress["payload"]["actions"] if r["action_id"] == tail_id)
    checks = {
        "all_fact_resources_have_correct_bytes": all(digest((data / r["path"]).read_bytes()) == r["sha256"] for r, _ in all_facts),
        "basis_and_prefix_resource_bytes_match": all(digest((data / r["path"]).read_bytes()) == r["sha256"] for r in [basis_ref, prefix_ref]),
        "origin_is_unattempted_absence": fact["origin_phase"] == "UNATTEMPTED_ABSENCE",
        "tail_intent_obligation_resolution_are_null": all(fact[k] is None for k in ["intent_ref", "obligation_id", "resolution_ref"]) and fact["result"]["intent_ref"] is None,
        "result_is_not_attempted_not_applied_absent_recheck": [fact["result"][k] for k in ["attempt_fact", "outcome", "effect_match", "next_step", "replay_allowed"]] == ["NOT_ATTEMPTED", "NOT_APPLIED", "ABSENT", "RECHECK_TARGET", False],
        "fact_and_receipt_result_equal": fact["result"] == tail_result,
        "fact_and_progress_resource_equal": fact_ref == tail_progress["result_fact"],
        "event_sequence_is_requested_head_plus_one": fact["journal_sequence"] == basis["expected_event_head"]["sequence"] + 1,
        "event_predecessor_equals_requested_head": fact["predecessor_hash"] == basis["expected_event_head"]["hash"],
        "new_read_static_identities_differ": first["observation_id"] != second["observation_id"] and first["read_sequence"] < second["read_sequence"],
        "prepared_uses_first_read": prepared["first_observation_ref"] == basis["first_observation_ref"] and prepared["observation_id"] == first["observation_id"],
        "fact_readback_uses_second_read": fact["readback"] == basis["second_observation_ref"] == fact["result"]["readback"],
        "B_unknown_stays_in_receipt": any(r["outcome"] == "UNKNOWN" for r in receipt["payload"]["results"]),
        "book_pause_stays_true": case["ledger_export"]["pause"]["paused"] is True,
        "receipt_pause_reconcile": receipt["payload"]["write_disposition"] == "PAUSE_RECONCILE",
        "source_profile_schema_hashes_match": all(digest((package / info["path"]).read_bytes()) == info["sha256"] for info in api["candidate_profile"]["schema_files"].values()),
    }
    events = prefix["events"]
    names = [e["event"] for e in events]
    applied = [e["action_id"] for e in events if e.get("outcome") == "APPLIED"]
    missing_dispatch = [a for a in applied if not any(e.get("action_id") == a and e.get("event") == "DISPATCH_STARTED" for e in events)]
    success_manifest = next(c for c in manifest["cases"] if c["case_id"] == "unattempted-absence-commit")
    api_cases = []
    for item in manifest["cases"]:
        if item["case_id"].startswith("unattempted-") and item["expected_layer"] == "RUNTIME_TRANSACTION":
            obj = load(data / item["path"])
            claim = obj["runtime_claim"]
            api_cases.append({
                "case_id": item["case_id"],
                "expected_code": item["expected_code"],
                "semantic_execution": item["semantic_execution"],
                "claim_keys": sorted(claim),
                "separate_prefix_resource": claim.get("candidate_uncalled_prefix"),
                "note": "Constructed static premise only; current runtime store was not created or inspected.",
            })
    finding = {
        "finding_id": "A03-P1-R1-PREFIX-01",
        "classification": "P1-07 design success fixture contradicts its new full-prefix precondition; NOT a P2 runtime failure",
        "success_expected_code": success_manifest["expected_code"],
        "prefix_path": prefix_ref["path"],
        "prefix_complete": prefix.get("complete"),
        "prefix_from": prefix.get("from_sequence"),
        "prefix_through": prefix.get("through_sequence"),
        "event_names": names,
        "contains_required_PLAN_ACCEPTED": "PLAN_ACCEPTED" in names,
        "applied_actions_without_DISPATCH_STARTED": missing_dispatch,
        "prefix_nested_resource_declarations": refs(prefix),
        "prefix_top_level_keys": sorted(prefix),
        "separate_complete_event_resource_or_summary_marker_found": False,
        "basis_declares_complete_prefix_not_diagnostic_summary": api["unattempted_absence_protocol"]["unattempted_basis"]["required_fields"]["complete_uncalled_prefix"],
        "required_repair": "Preserve old failure. Supply a structurally complete successful event/hash prefix with PLAN_ACCEPTED, reservations and all preceding dispatch-authority/dispatch events; adjust hashes/CAS/sequence downstream. Keep a missing-required-event neighbor rejection. Do not weaken current-store authority or full-prefix admission.",
    }
    out.mkdir(parents=True, exist_ok=True)
    copy_sources = [
        data / "cases/unattempted-absence-commit.json",
        data / fact_ref["path"],
        data / basis_ref["path"],
        data / prefix_ref["path"],
    ]
    preserved = []
    for source in copy_sources:
        relative = source.relative_to(stage)
        target = out / "counterexample" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        blob = source.read_bytes()
        if target.exists() and target.read_bytes() != blob:
            raise ValueError("Never overwrite differing preserved evidence")
        target.write_bytes(blob)
        preserved.append({"source": relative.as_posix(), "copy": target.relative_to(out).as_posix(), "length": len(blob), "sha256": digest(blob)})
    report = {
        "review_mode": "INDEPENDENT_STATIC_DESIGN_ONLY",
        "final_commit": "ca4fba4f505467228a8164c3999e0cecc54ffc4e",
        "design_commit": "095ed4aa18a56100ce3aabc4a0d6885ad37ab520",
        "stage": str(stage),
        "argv": sys.argv,
        "author_checker_imported_or_run": False,
        "src_imported": False,
        "static_positive_field_checks": checks,
        "static_positive_field_checks_all_pass": all(checks.values()),
        "finding": finding,
        "api_cases_inspected": api_cases,
        "preserved_sources": preserved,
        "runtime_behavior": "NOT_RUN / EXPECTED_NOT_EXECUTED",
        "network_platform_browser_profile_credentials_ocr_model_api_operations": 0,
        "own_processes_remaining_after_synchronous_script": 0,
    }
    (out / "independent-api-static.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"field_checks_pass": all(checks.values()), "API_premise_cases": len(api_cases), "finding": finding["finding_id"], "runtime_behavior": "NOT_RUN"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
