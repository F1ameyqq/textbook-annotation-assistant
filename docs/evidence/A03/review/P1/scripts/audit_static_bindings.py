"""Independent static identities/digest/reference audit; no effect classification."""
import hashlib
import json
from pathlib import Path

ROOT = Path("D:/1800")
BASE = ROOT / ".local/stages/A03-review-P1/2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9/examples/a03/P1"
OUT = ROOT / "docs/evidence/A03/review/P1/independent-bindings.json"
POSITIVE = {"normal", "intent-no-receipt-match", "intent-no-receipt-absent",
    "partial-without-absent", "partial-with-complete-absent", "conflict", "indeterminate",
    "original-unknown-preserved", "recovered-report-binding", "new-read-unchanged-state-version",
    "cross-scope-only-one-resolved", "legacy-unrecorded-no-intent", "source-only-zero-actions"}

def load(path):
    return json.loads(path.read_bytes())

def h(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()

def ref(a):
    return {k: a[k] for k in ("artifact_id", "revision", "kind", "content_hash")}

def walk(x):
    yield x
    if isinstance(x, dict):
        for child in x.values():
            yield from walk(child)
    elif isinstance(x, list):
        for child in x:
            yield from walk(child)

def main():
    rows, failures = [], []
    def check(case, artifact, condition, detail):
        if not condition:
            failures.append({"case": case, "artifact": artifact, "detail": detail})
    for entry in load(BASE / "case-manifest.json")["cases"]:
        name = entry["case_id"]
        if name not in POSITIVE:
            continue
        case = load(BASE / entry["path"])
        arts = case["bundle"]["artifacts"]
        known = {(a["artifact_id"], a["revision"]): a for a in arts}
        def resolve(r):
            return known[(r["artifact_id"], r["revision"])]
        intents = [a for a in arts if a["kind"] == "WriteIntent"]
        resolutions = [a for a in arts if a["kind"] == "ReconciliationResult"]
        for a in intents:
            p = a["payload"]
            plan = resolve(p["plan_ref"])["payload"]
            action = next(x for x in plan["actions"] if x["action_id"] == p["action_id"])
            check(name, a["artifact_id"], h(action) == p["action_digest"], "intent action_digest differs from exact action")
            check(name, a["artifact_id"], p["before_snapshot_ref"] == plan["snapshot"], "intent initial snapshot ref differs")
            dependency = {k: plan[k] for k in ("graph", "precheck", "targetcheck", "snapshot", "policy",
                "execution_mode", "session_mode", "required_capabilities")}
            computed = h({"plan_dependencies_digest": h(dependency), "source_ref": p["source_ref"],
                "target_session_id": p["target_session_id"], "comparator_version": "a02-facts-1",
                "prepared_before_sha256": p["prepared_before"]["sha256"]})
            check(name, a["artifact_id"], computed == p["plan_dependency_digest"], "plan_dependency_digest differs from frozen formula")
        for a in resolutions:
            p = a["payload"]
            intent = resolve(p["intent_ref"])
            ip = intent["payload"]
            obligation = "obl-" + h({"journal_id": ip["journal_id"], "target_key": ip["target_key"],
                "intent_ref": ref(intent), "journal_sequence": ip["journal_sequence"],
                "journal_head_hash": ip["journal_head_hash"]})
            check(name, a["artifact_id"], p["obligation_id"] == obligation, "obligation derivation differs")
            check(name, a["artifact_id"], p["action_digest"] == ip["action_digest"] and p["action_id"] == ip["action_id"], "resolution action identity differs")
            if p["observed_snapshot_ref"] is not None:
                snap = resolve(p["observed_snapshot_ref"])["payload"]
                check(name, a["artifact_id"], snap["observed_at"] == p["observed_at"], "snapshot/resolution observed_at differs")
                check(name, a["artifact_id"], snap["observed_version"] == p["target_state_version"], "snapshot/resolution target state version differs")
                check(name, a["artifact_id"], snap["observed_hash"] == p["target_state_hash"], "snapshot/resolution target state hash differs")
        nested_refs_checked = 0
        for a in arts:
            declared = [r for r in a["input_refs"]]
            for resource in (n for n in walk(a["payload"]) if isinstance(n, dict) and {"path", "sha256", "media_type"} <= n.keys()):
                if resource["media_type"] != "application/json":
                    continue
                data = load(BASE / resource["path"])
                for r in (n for n in walk(data) if isinstance(n, dict) and set(n) == {"artifact_id", "revision", "kind", "content_hash"}):
                    nested_refs_checked += 1
                    target = known.get((r["artifact_id"], r["revision"]))
                    check(name, a["artifact_id"], target is not None and ref(target) == r,
                        "resource nested ref absent/digest differs: " + r["artifact_id"])
                    if target is not None:
                        check(name, a["artifact_id"], (a["book_id"], a["scope_id"]) == (target["book_id"], target["scope_id"]),
                            "resource nested ref crosses book/scope: " + r["artifact_id"])
                    check(name, a["artifact_id"], r in declared,
                        "resource nested ref not declared by consumer: " + r["artifact_id"])
        rows.append({"case": name, "intents": len(intents), "resolutions": len(resolutions),
            "nested_resource_refs_checked": nested_refs_checked, "static_only": True})
    migration = load(BASE / "migration-map.json")
    assert (BASE / migration["archive"]).read_bytes() == (BASE.parents[2] / migration["original_path"]).read_bytes()
    assert (BASE / "archive/legacy/input.json").read_bytes() == (BASE.parents[2] / "tests/fixtures/contracts/unknown/input.json").read_bytes()
    result = {"check_kind": "INDEPENDENT_STATIC_FORMULA_AND_NESTED_REFERENCE_AUDIT",
        "recovery_or_effect_logic_implemented": False, "cases": rows, "failures": failures,
        "archive_original_bytes_equal_frozen_sources": True}
    with OUT.open("x", encoding="utf-8", newline="\n") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(json.dumps({"cases": len(rows), "failures": len(failures), "first_failures": failures[:6]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
