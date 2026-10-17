"""Independent read-only R2 prefix/fact/intent/ledger binding audit (stdlib only).

Does not import the fixture generator, author checker, prefix rules, or business
code. Four positive design graphs are examined; future runtime is NOT_EXECUTED.
The final read-only event is reconstructed from the fact and readback time only
to compare the proposed ledger/progress head. This does not commit an event.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
DATA = ROOT / "examples/a03/P1-R2/data"
CASES = ("unattempted-absence-commit", "partial-with-complete-absent",
         "original-unknown-preserved", "recovered-report-binding")
REF_KEYS = ("artifact_id", "revision", "kind", "content_hash")


def h(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def ref(value):
    return {key: value[key] for key in REF_KEYS}


def event_hash(value):
    return h({key: child for key, child in value.items() if key != "event_hash"})


def audit(name):
    errors, resources, prefixes = [], set(), []

    def check(condition, code, context):
        if not condition:
            errors.append({"code": code, "context": context})

    def read(resource):
        path = (DATA / resource["path"]).resolve()
        check(DATA.resolve() in path.parents, "RESOURCE_OUTSIDE", resource["path"])
        raw = path.read_bytes()
        check(hashlib.sha256(raw).hexdigest() == resource["sha256"],
              "RESOURCE_BYTES", resource["path"])
        resources.add(resource["path"])
        return json.loads(raw)

    case = json.loads((DATA / "cases" / (name + ".json")).read_bytes())
    artifacts = case["bundle"]["artifacts"]
    by_ref = {tuple(a[key] for key in REF_KEYS): a for a in artifacts}
    plan = next(a for a in artifacts if a["kind"] == "ApplyPlan")
    receipt = next(a for a in artifacts if a["kind"] == "ExecutionReceipt")
    progress = next(a for a in artifacts if a["kind"] == "ExecutionProgress")
    actions = {a["action_id"]: a for a in plan["payload"]["actions"]}
    results = {a["action_id"]: a for a in receipt["payload"]["results"]}
    facts = [(r, read(r)) for r in receipt["payload"]["action_fact_refs"]]
    fact_map = {f["action_id"]: (r, f) for r, f in facts}
    obligations = {}
    for artifact in artifacts:
        check(artifact["content_hash"] == h({k: v for k, v in artifact.items() if k != "content_hash"}),
              "ARTIFACT_HASH", artifact["artifact_id"])
    for resource, fact in facts:
        action_id = fact["action_id"]
        check(fact["action_digest"] == h(actions[action_id]), "FACT_ACTION_DIGEST", action_id)
        check(fact["plan_ref"] == ref(plan), "FACT_PLAN", action_id)
        check(fact["result"] == results[action_id], "RECEIPT_RESULT", action_id)
        if fact["intent_ref"]:
            intent = by_ref[tuple(fact["intent_ref"][k] for k in REF_KEYS)]["payload"]
            obligation = "obl-" + h({"journal_id": intent["journal_id"],
                "target_key": intent["target_key"], "intent_ref": fact["intent_ref"],
                "journal_sequence": intent["journal_sequence"],
                "journal_head_hash": intent["journal_head_hash"]})
            obligations[action_id] = obligation
            check(fact["obligation_id"] == obligation, "OBLIGATION_DERIVATION", action_id)
        else:
            check(fact["origin_phase"] == "UNATTEMPTED_ABSENCE" and
                  fact["obligation_id"] is None and fact["resolution_ref"] is None and
                  fact["result"]["intent_ref"] is None, "TAIL_NULL_IDENTITIES", action_id)
            check(not any(a["kind"] == "WriteIntent" and a["payload"]["action_id"] == action_id
                          for a in artifacts), "TAIL_INTENT_FABRICATED", action_id)
            basis = read(fact["unattempted_basis"])
            prefix = read(basis["complete_uncalled_prefix"])
            events = prefix["events"]
            check(events[0]["event"] == "PLAN_ACCEPTED", "ACCEPTANCE", action_id)
            bindings = [{"action_id": a["action_id"], "action_digest": h(a)}
                        for a in plan["payload"]["actions"]]
            check(events[0]["payload"] == {"plan_ref": ref(plan), "actions": bindings},
                  "ACCEPTANCE_BINDING", action_id)
            check(events[1]["event"] == "PLAN_ACTIONS_RESERVED" and
                  events[1]["payload"] == {"reservations": bindings}, "RESERVATION", action_id)
            previous, interrupted, stages = "0" * 64, False, {}
            for sequence, event in enumerate(events, 1):
                check(event["sequence"] == sequence and event["previous_hash"] == previous and
                      event["event_hash"] == event_hash(event), "EVENT_CHAIN", sequence)
                previous = event["event_hash"]
                check(all(event[k] == prefix[k] for k in
                          ("journal_id", "target_key", "plan_ref", "owner_id", "generation")),
                      "EVENT_HEADER", sequence)
                payload, kind = event["payload"], event["event"]
                aid = payload.get("action_id")
                check(aid != action_id, "SUBJECT_HISTORY", sequence)
                if not aid:
                    continue
                check(payload["action_digest"] == h(actions[aid]), "EVENT_ACTION", sequence)
                check(not interrupted or kind == "UNATTEMPTED_ABSENCE_COMMITTED",
                      "DISPATCH_AFTER_UNKNOWN", sequence)
                stages.setdefault(aid, []).append(kind)
                if kind == "WRITE_INTENT_COMMITTED":
                    intent = by_ref[tuple(payload["intent_ref"][k] for k in REF_KEYS)]["payload"]
                    check(intent["journal_sequence"] == sequence and
                          intent["journal_head_hash"] == event["previous_hash"] and
                          intent["intent_committed_at"] == event["recorded_at"] and
                          intent["action_id"] == aid and intent["action_digest"] == payload["action_digest"] and
                          intent["plan_ref"] == event["plan_ref"] and
                          payload["obligation_id"] == obligations[aid], "INTENT_EVENT_BINDING", sequence)
                if kind in ("ACTION_RESULT_COMMITTED", "UNATTEMPTED_ABSENCE_COMMITTED"):
                    other = read(payload["fact"])
                    check(payload["fact"] == fact_map[aid][0] and other == fact_map[aid][1],
                          "EVENT_FACT_RESOURCE", sequence)
                    check(other["journal_sequence"] == sequence and other["predecessor_hash"] == event["previous_hash"]
                          and other["result"]["outcome"] == payload["outcome"], "FACT_EVENT_BINDING", sequence)
                    if kind == "ACTION_RESULT_COMMITTED":
                        check(stages[aid] == ["WRITE_INTENT_COMMITTED", "DISPATCH_PERMIT_ISSUED",
                            "DISPATCH_PERMIT_CONSUMED", "DISPATCH_STARTED", "ACTION_RESULT_COMMITTED"],
                            "REQUIRED_DISPATCH_ORDER", sequence)
                        check(payload["intent_ref"] == other["intent_ref"] and
                              payload["obligation_id"] == other["obligation_id"], "RESULT_IDENTITIES", sequence)
                    if other["readback"]:
                        check(read(other["readback"])["observed_at"] <= event["recorded_at"],
                              "RESULT_BEFORE_OBSERVATION", sequence)
                    interrupted = interrupted or payload["outcome"] == "UNKNOWN"
            check(interrupted, "UNKNOWN_MISSING", action_id)
            check(prefix["through_sequence"] == len(events) and prefix["head_hash"] == previous and
                  basis["expected_event_head"] == {"sequence": len(events), "hash": previous} and
                  fact["journal_sequence"] == len(events) + 1 and fact["predecessor_hash"] == previous,
                  "BASIS_FACT_CAS", action_id)
            prefixes.append({"action_id": action_id, "events": events, "resource": resource,
                             "fact": fact, "head": previous})
    latest = max(prefixes, key=lambda p: len(p["events"]))
    prefix = latest["events"]
    fact = latest["fact"]
    last = {key: prefix[-1][key] for key in
            ("journal_id", "target_key", "plan_ref", "owner_id", "generation")}
    last.update(sequence=fact["journal_sequence"], event="UNATTEMPTED_ABSENCE_COMMITTED",
        recorded_at=read(fact["readback"])["observed_at"], previous_hash=latest["head"],
        payload={"action_id": fact["action_id"], "action_digest": fact["action_digest"],
            "fact": latest["resource"], "outcome": "NOT_APPLIED", "plan_state": "INTERRUPTED"})
    final_hash = event_hash(last)
    ledger = case["ledger_export"]
    check(ledger["event_head_sequence"] == last["sequence"] and ledger["event_head_hash"] == final_hash,
          "LEDGER_FINAL_HEAD", name)
    check(progress["payload"]["journal_head_sequence"] == last["sequence"] and
          progress["payload"]["journal_head_hash"] == final_hash, "PROGRESS_FINAL_HEAD", name)
    check(ledger["artifact_history"] == [ref(a) for a in artifacts], "LEDGER_HISTORY", name)
    unknowns = {f["action_id"]: f for _, f in facts if f["result"]["outcome"] == "UNKNOWN"}
    check(set(ledger["pending_action_ids"]) == set(unknowns) and ledger["pause"]["paused"] is True,
          "UNKNOWN_PAUSE", name)
    check(len(ledger["unresolved"]) == len(unknowns) and all(
        row["intent_ref"] == f["intent_ref"] and row["obligation_id"] == f["obligation_id"]
        for f in unknowns.values() for row in ledger["unresolved"]), "UNKNOWN_OBLIGATION", name)
    for item in progress["payload"]["actions"]:
        r, f = fact_map[item["action_id"]]
        check(item["result_fact"] == r and item["effective_outcome"] == f["result"]["outcome"] and
              item["intent_ref"] == f["intent_ref"] and item["receipt_ref"] == ref(receipt),
              "PROGRESS_FACT_RESULT", item["action_id"])
    return {"case_id": name, "facts_checked": len(facts), "prefixes_checked": len(prefixes),
            "unique_resource_bytes_checked": len(resources), "final_sequence": last["sequence"],
            "final_hash": final_hash, "errors": errors, "passed": not errors}


def main():
    results = [audit(name) for name in CASES]
    passed = all(r["passed"] for r in results)
    print(json.dumps({"audit": "A03_P1_R2_INDEPENDENT_STATIC_BINDINGS", "results": results,
        "passed": passed, "runtime_or_recovery_executed": False}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
