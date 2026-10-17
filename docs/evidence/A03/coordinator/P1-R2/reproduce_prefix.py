"""Read exact Git objects and reproduce the P1-R1 prefix inconsistency only."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
COMMIT = "ca4fba4f505467228a8164c3999e0cecc54ffc4e"
BASE = "examples/a03/P1-R1/"
FROZEN = ROOT / "docs/evidence/A03/review/P1-R1/inputs/frozen-R1"
bindings = {}


def read(path):
    data = subprocess.check_output(["git", "cat-file", "blob", COMMIT + ":" + path], cwd=ROOT)
    assert (FROZEN / path).read_bytes() == data, path
    bindings[path] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return json.loads(data)


def resources(value):
    if isinstance(value, dict):
        if {"path", "sha256", "media_type"} <= value.keys():
            yield value
        for item in value.values():
            yield from resources(item)
    elif isinstance(value, list):
        for item in value:
            yield from resources(item)


def resource(ref):
    path = BASE + "data/" + ref["path"]
    obj = read(path)
    assert bindings[path]["sha256"] == ref["sha256"]
    return obj


case = read(BASE + "data/cases/unattempted-absence-commit.json")
facts = {}
for ref in resources(case):
    if ref["media_type"] != "application/json":
        continue
    obj = resource(ref)
    if obj.get("origin_phase") == "UNATTEMPTED_ABSENCE":
        facts[ref["path"]] = obj
assert len(facts) == 1
fact = next(iter(facts.values()))
basis = resource(fact["unattempted_basis"])
prefix = resource(basis["complete_uncalled_prefix"])
api = read(BASE + "api-proposal.json")
api_text = json.dumps(api, ensure_ascii=False)
assert "PLAN_ACCEPTED" in api_text and "DISPATCH_STARTED" in api_text
events = prefix["events"]
names = [event["event"] for event in events]
applied_without_dispatch = [event["action_id"] for event in events
    if event.get("outcome") == "APPLIED" and not any(
        other["event"] == "DISPATCH_STARTED" and other.get("action_id") == event["action_id"]
        and other["sequence"] < event["sequence"] for other in events)]
assert case["runtime_claim"]["expected_event"] == "UNATTEMPTED_ABSENCE_COMMITTED"
assert prefix["complete"] and "PLAN_ACCEPTED" not in names and applied_without_dispatch
assert fact["intent_ref"] is None and fact["obligation_id"] is None
assert case["runtime_claim"]["original_B_unknown_preserved"]
result = {
    "decision": "REWORK_CONFIRMED", "finding": "A03-P1-R1-PREFIX-01",
    "target_commit": COMMIT, "scope": "Exact Git-bound static design/fixture inspection only",
    "runtime_executed": False, "input_bindings": bindings,
    "success_claim": case["runtime_claim"]["expected_event"],
    "prefix_resource": basis["complete_uncalled_prefix"],
    "event_names": names, "missing_acceptance_event": True,
    "applied_without_dispatch": applied_without_dispatch,
    "tail_intent_absent": True, "B_unknown_preserved": True,
    "no_P2_or_I01_release": True,
}
output = Path(__file__).with_name("coordinator-check.json")
with output.open("w", encoding="utf-8", newline="\n") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
print(json.dumps({"decision": result["decision"], "git_bound_inputs": len(bindings),
                  "events": names, "applied_without_dispatch": applied_without_dispatch}))
