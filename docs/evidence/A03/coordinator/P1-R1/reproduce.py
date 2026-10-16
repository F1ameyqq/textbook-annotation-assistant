"""Bounded static coordinator reproduction; no recovery code is imported."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
COMMIT = "2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9"
FROZEN = ROOT / "docs/evidence/A03/review/P1/inputs/frozen-P1"
inputs = []


def read(relative, parse=True):
    raw = subprocess.check_output(["git", "show", COMMIT + ":" + relative], cwd=ROOT)
    archived = (FROZEN / relative).read_bytes()
    assert raw == archived, relative
    inputs.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    return json.loads(raw) if parse else raw.decode("utf-8")


api = read("examples/a03/P1/api-proposal.json")
case = read("examples/a03/P1/cases/normal.json")
fact = read("examples/a03/P1/assets/action-fact-normal-1.json")
tail = read("examples/a03/P1/assets/action-fact-partial-not-attempted-absent.json")
proposal = read("docs/a03-recovery-contract-v1-proposal.md", False)
normal_commit = api["groups"][1]["proposed"][3]
recovery_commit = api["runtime_authority_protocol"]["methods"][6]
assert "commit_action_result(" in normal_commit["signature"]
assert "commit_reconciliation(" in recovery_commit["signature"]
assert "RUNNING plan only" in normal_commit["responsibility"]
assert "Current original committed intent and plan cursor" in normal_commit["inputs"]
assert "original committed intent evidence" in " ".join(recovery_commit["inputs"])
assert tail["intent_ref"] is None and tail["obligation_id"] is None
assert tail["origin_phase"] == "EXECUTION" and tail["resolution_ref"] is None

artifacts = case["bundle"]["artifacts"]
consumers = [a for a in artifacts if a["artifact_id"] in ("receipt-design", "progress-design")]
assert len(consumers) == 2
missing = []
for consumer in consumers:
    reference = fact["observed_snapshot_ref"]
    declared = consumer["input_refs"]
    assert reference not in declared
    missing.append({"consumer": consumer["artifact_id"], "kind": consumer["kind"],
                    "declared_input_refs": declared, "undeclared_fact_snapshot_ref": reference})

result = {
    "reviewed_commit": COMMIT,
    "mode": "STATIC_DESIGN_ONLY",
    "input_git_and_archive_byte_checks": inputs,
    "API_01": {
        "decision": "DESIGN_GAP_CONFIRMED_BY_STATIC_INSPECTION",
        "scenario": "A APPLIED, B UNKNOWN, C NOT_ATTEMPTED; original plan INTERRUPTED",
        "tail_fact_null_intent_and_obligation": True,
        "normal_public_commit": normal_commit,
        "recovery_public_commit": recovery_commit,
        "reason": "The supplied tail fact has no intent/obligation; the listed normal entry requires a committed intent and RUNNING cursor, while reconciliation requires original intent evidence. A public transaction path for this permitted fact remains unspecified. This is a design reading, not an executed API result."
    },
    "REF_01": {"decision": "UNDECLARED_RESOURCE_REFERENCE_CONFIRMED", "occurrences_checked": missing},
    "result": "REWORK_CONFIRMED",
    "functional_tests_run": False,
    "recovery_behavior": "NOT_EXECUTED",
    "browser_platform_network_model_operations": 0,
}
target = OUT / "coordinator-check.json"
if target.exists():
    raise SystemExit("Refusing to overwrite a frozen coordinator check")
target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"result": result["result"], "git_archive_inputs": len(inputs), "missing_ref_consumers": len(missing), "recovery_behavior": "NOT_EXECUTED"}))
