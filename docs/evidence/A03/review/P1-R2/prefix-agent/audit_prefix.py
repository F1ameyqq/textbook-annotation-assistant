"""Independent static prefix audit; no author modules, runtime or database imports.

Only reads a frozen selective Git export and writes this review's own evidence.
The assertions below come from the explicit acceptance/dispatch/fact contract;
author expected fields and check_design.py are never consulted.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

FINAL = "940a5de33a24b1a3a9ded6e69ade1dd0609ed83a"
REF_KEYS = ("artifact_id", "revision", "kind", "content_hash")
ZERO = "0" * 64


def h(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def ref(a):
    return {k: a[k] for k in REF_KEYS}


def eh(e):
    return h({k: v for k, v in e.items() if k != "event_hash"})


def unique_object(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError("duplicate key " + k)
        obj[k] = v
    return obj


class Audit:
    def __init__(self, base):
        self.base = base
        self.inputs = {}

    def load(self, relative):
        path = (self.base / relative).resolve()
        assert self.base in path.parents, relative
        data = path.read_bytes()
        self.inputs[relative] = hashlib.sha256(data).hexdigest()
        return json.loads(data, object_pairs_hook=unique_object,
            parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

    def resource(self, r):
        assert r["origin"] == "SYNTHETIC" and r["media_type"] == "application/json"
        value = self.load(r["path"])
        assert self.inputs[r["path"]] == r["sha256"], r["path"]
        return value

    def chain(self, prefix, plan, subject, bodies=True):
        """Full actual precommit content, without trusting complete=true."""
        errors = []
        check = lambda ok, code: None if ok else errors.append(code)
        events = prefix["events"]
        check(prefix["from_sequence"] == 1, "START_NOT_ONE")
        check(prefix["through_sequence"] == len(events), "LENGTH_MISMATCH")
        check(prefix["genesis_hash"] == ZERO, "GENESIS_MISMATCH")
        check(prefix["plan_ref"] == ref(plan), "PLAN_MISMATCH")
        check(prefix["scope_id"] == plan["scope_id"], "SCOPE_MISMATCH")
        check(prefix["target_key"]["book_id"] == plan["book_id"], "BOOK_MISMATCH")
        actions = plan["payload"]["actions"]
        binding = [{"action_id": a["action_id"], "action_digest": h(a)} for a in actions]
        check(bool(events) and events[0]["event"] == "PLAN_ACCEPTED", "ACCEPTANCE_MISSING")
        check([e["event"] for e in events[:3]] == ["PLAN_ACCEPTED", "PLAN_ACTIONS_RESERVED", "PLAN_STARTED"], "REGISTRATION_PREFIX_MISSING")
        previous = ZERO
        stages = {a["action_id"]: [] for a in actions}
        intent_refs = {}
        obligations = {}
        permits = {}
        outcomes = {}
        prior_time = None
        interrupted = False
        rows = []
        for seq, e in enumerate(events, 1):
            name, p = e["event"], e["payload"]
            check(e["sequence"] == seq, "SEQUENCE_BROKEN")
            check(e["previous_hash"] == previous and e["event_hash"] == eh(e), "HASH_BROKEN")
            check(all(e[k] == prefix[k] for k in ("journal_id", "target_key", "plan_ref", "owner_id", "generation")), "EVENT_IDENTITY_MISMATCH")
            check(prior_time is None or e["recorded_at"] >= prior_time, "TIME_REGRESSION")
            previous, prior_time = e["event_hash"], e["recorded_at"]
            if name == "PLAN_ACCEPTED":
                check(seq == 1 and p == {"plan_ref": ref(plan), "actions": binding}, "ACCEPTANCE_BINDING_MISMATCH")
                continue
            if name == "PLAN_ACTIONS_RESERVED":
                check(seq == 2 and p == {"reservations": binding}, "RESERVATION_MISMATCH")
                continue
            if name == "PLAN_STARTED":
                check(seq == 3 and p == {"plan_state": "RUNNING"}, "START_STATE_MISMATCH")
                continue
            aid = p["action_id"]
            check(aid in stages and p["action_digest"] == next(x["action_digest"] for x in binding if x["action_id"] == aid), "ACTION_DIGEST_MISMATCH")
            check(aid != subject, "SUBJECT_ATTEMPTED")
            check(not interrupted or name == "UNATTEMPTED_ABSENCE_COMMITTED", "DISPATCH_AFTER_UNKNOWN")
            if name == "WRITE_INTENT_COMMITTED":
                check(not stages[aid], "REPEATED_INTENT")
                dependency = next(a for a in actions if a["action_id"] == aid).get("depends_on", [])
                check(all(outcomes.get(a) == "APPLIED" for a in dependency), "DEPENDENCY_UNRESOLVED")
                intent_refs[aid] = p["intent_ref"]
                obligations[aid] = p["obligation_id"]
                if bodies:
                    intent = self.known[tuple(p["intent_ref"][k] for k in REF_KEYS)]
                    ip = intent["payload"]
                    check(ip["journal_id"] == e["journal_id"] and ip["journal_sequence"] == seq and ip["journal_head_hash"] == e["previous_hash"], "INTENT_HEAD_MISMATCH")
                    check(ip["action_id"] == aid and ip["action_digest"] == p["action_digest"] and ip["plan_ref"] == ref(plan), "INTENT_BODY_MISMATCH")
                    check(all(ip[k] == e[k] for k in ("target_key", "owner_id", "generation")) and ip["intent_committed_at"] == e["recorded_at"], "INTENT_IDENTITY_MISMATCH")
                    expected_obligation = "obl-" + h({"journal_id": ip["journal_id"], "target_key": ip["target_key"], "intent_ref": ref(intent), "journal_sequence": ip["journal_sequence"], "journal_head_hash": ip["journal_head_hash"]})
                    check(p["obligation_id"] == expected_obligation, "OBLIGATION_MISMATCH")
            elif name in ("DISPATCH_PERMIT_ISSUED", "DISPATCH_PERMIT_CONSUMED", "DISPATCH_STARTED"):
                required = {"DISPATCH_PERMIT_ISSUED": ["WRITE_INTENT_COMMITTED"], "DISPATCH_PERMIT_CONSUMED": ["WRITE_INTENT_COMMITTED", "DISPATCH_PERMIT_ISSUED"], "DISPATCH_STARTED": ["WRITE_INTENT_COMMITTED", "DISPATCH_PERMIT_ISSUED", "DISPATCH_PERMIT_CONSUMED"]}[name]
                check(stages[aid] == required, "PERMIT_STAGE_MISMATCH")
                check(p["intent_ref"] == intent_refs.get(aid), "PERMIT_INTENT_MISMATCH")
                if name == "DISPATCH_PERMIT_ISSUED":
                    check(p["permit_id"] not in permits.values(), "PERMIT_REUSED")
                    permits[aid] = p["permit_id"]
                check(p["permit_id"] == permits.get(aid), "PERMIT_ID_MISMATCH")
            elif name == "ACTION_RESULT_COMMITTED":
                check(stages[aid] == ["WRITE_INTENT_COMMITTED", "DISPATCH_PERMIT_ISSUED", "DISPATCH_PERMIT_CONSUMED", "DISPATCH_STARTED"], "RESULT_DISPATCH_MISSING")
                check(p["intent_ref"] == intent_refs.get(aid) and p["obligation_id"] == obligations.get(aid), "RESULT_INTENT_MISMATCH")
                outcomes[aid] = p["outcome"]
                interrupted = p["outcome"] == "UNKNOWN"
                check(p["plan_state"] == ("INTERRUPTED" if interrupted else "RUNNING"), "RESULT_STATE_MISMATCH")
            elif name == "UNATTEMPTED_ABSENCE_COMMITTED":
                check(interrupted and not stages[aid] and p["outcome"] == "NOT_APPLIED" and p["plan_state"] == "INTERRUPTED", "UNATTEMPTED_MISMATCH")
            else:
                check(False, "UNEXPECTED_EVENT")
            stages[aid].append(name)
            if name in ("ACTION_RESULT_COMMITTED", "UNATTEMPTED_ABSENCE_COMMITTED") and bodies:
                fact = self.resource(p["fact"])
                check(fact["journal_sequence"] == seq and fact["predecessor_hash"] == e["previous_hash"], "FACT_HEAD_MISMATCH")
                check(fact["plan_ref"] == e["plan_ref"] and fact["action_id"] == aid and fact["action_digest"] == p["action_digest"] and fact["result"]["outcome"] == p["outcome"], "FACT_CONTENT_MISMATCH")
                check((fact["intent_ref"], fact["obligation_id"]) == (p.get("intent_ref"), p.get("obligation_id")), "FACT_INTENT_MISMATCH")
                rows.append({"sequence": seq, "event": name, "action": aid, "outcome": p["outcome"], "fact": p["fact"]})
        check(previous == prefix["head_hash"], "HEAD_MISMATCH")
        check(interrupted, "NOT_INTERRUPTED")
        return {"errors": sorted(set(errors)), "event_names": [e["event"] for e in events], "through": len(events), "head": previous, "outcomes": outcomes, "facts": rows}

    def positive(self, name):
        case = self.load("cases/" + name + ".json")
        artifacts = case["bundle"]["artifacts"]
        self.known = {tuple(a[k] for k in REF_KEYS): a for a in artifacts}
        plan = next(a for a in artifacts if a["kind"] == "ApplyPlan")
        receipt = next(a for a in artifacts if a["kind"] == "ExecutionReceipt")
        progress = next((a for a in artifacts if a["kind"] == "ExecutionProgress"), None)
        facts = [self.resource(r) for r in receipt["payload"]["action_fact_refs"]]
        checks = []
        progress_rows = progress["payload"]["actions"] if progress else [None] * len(facts)
        for fact, result, row in zip(facts, receipt["payload"]["results"], progress_rows):
            assert fact["result"] == result, "receipt fact mismatch"
            if row:
                assert row["result_fact"] == receipt["payload"]["action_fact_refs"][facts.index(fact)]
                assert fact["action_id"] == row["action_id"]
            if fact["origin_phase"] == "UNATTEMPTED_ABSENCE":
                assert fact["intent_ref"] is fact["obligation_id"] is fact["resolution_ref"] is None
                if row:
                    assert row["intent_ref"] is row["resolution_head_ref"] is None
                assert result["intent_ref"] is None and result["attempt_fact"] == "NOT_ATTEMPTED"
                basis = self.resource(fact["unattempted_basis"])
                prefix = self.resource(basis["complete_uncalled_prefix"])
                assert basis["expected_event_head"] == {"sequence": prefix["through_sequence"], "hash": prefix["head_hash"]}
                assert (fact["journal_sequence"], fact["predecessor_hash"]) == (prefix["through_sequence"]+1, prefix["head_hash"])
                observed = self.resource(fact["readback"])
                audit = self.chain(prefix, plan, fact["action_id"])
                checks.append({"subject": fact["action_id"], "prefix_resource": basis["complete_uncalled_prefix"], "fact_sequence": fact["journal_sequence"], "fact_read_at": observed["observed_at"], "audit": audit})
        assert all(not x["audit"]["errors"] for x in checks), checks
        ledger = case["ledger_export"]
        result = {"case": name, "prefixes": checks, "ledger_head": {"sequence": ledger["event_head_sequence"], "hash": ledger["event_head_hash"]}, "receipt_outcomes": [r["outcome"] for r in receipt["payload"]["results"]], "progress_outcomes": [r["effective_outcome"] for r in progress["payload"]["actions"]] if progress else None, "pause": ledger["pause"], "pending": ledger["pending_action_ids"]}
        if progress:
            assert (ledger["event_head_sequence"], ledger["event_head_hash"]) == (progress["payload"]["journal_head_sequence"], progress["payload"]["journal_head_hash"])
        suffix_resource = case["runtime_claim"].get("post_prefix_events")
        if suffix_resource:
            suffix = self.resource(suffix_resource)
            last_prefix = self.resource(checks[-1]["prefix_resource"])
            assert (suffix["from_sequence"], suffix["through_sequence"], len(suffix["events"])) == (10, 11, 2)
            assert suffix["predecessor_hash"] == last_prefix["head_hash"]
            previous = last_prefix["head_hash"]
            rows = []
            for e in suffix["events"]:
                assert e["event_hash"] == eh(e) and e["previous_hash"] == previous
                assert all(e[k] == last_prefix[k] for k in ("journal_id", "target_key", "plan_ref", "owner_id", "generation"))
                previous = e["event_hash"]
                rows.append({k: e[k] for k in ("sequence", "event", "recorded_at", "event_hash")})
            cfact = facts[-1]
            cevent = suffix["events"][0]
            assert cevent["sequence"] == cfact["journal_sequence"] == 10
            assert cevent["payload"] == {"action_id": cfact["action_id"], "action_digest": cfact["action_digest"], "fact": receipt["payload"]["action_fact_refs"][-1], "outcome": "NOT_APPLIED", "plan_state": "INTERRUPTED"}
            assert previous == suffix["head_hash"] == ledger["event_head_hash"]
            final = suffix["events"][-1]
            assert final["event"] == "RECONCILIATION_COMMITTED"
            rp = self.known[tuple(final["payload"]["resolution_ref"][k] for k in REF_KEYS)]["payload"]
            assert all(final["payload"][k] == rp[k] for k in ("action_id", "action_digest", "intent_ref", "obligation_id", "observation_id", "resolution"))
            assert rp["intent_ref"] == facts[0]["intent_ref"] and rp["obligation_id"] == facts[0]["obligation_id"]
            assert rp["original_receipt_ref"] == ref(receipt) and receipt["payload"]["results"][0]["outcome"] == "UNKNOWN"
            if progress:
                assert progress["payload"]["actions"][0]["resolution_head_ref"] == final["payload"]["resolution_ref"]
            result["suffix"] = {"resource": suffix_resource, "events": rows, "time_regression": suffix["events"][1]["recorded_at"] < suffix["events"][0]["recorded_at"], "original_unknown_retained": True, "resolution_obligation": rp["obligation_id"]}
        else:
            assert len(ledger["unresolved"]) == 1 and ledger["pause"]["paused"] is True
            assert ledger["unresolved"][0]["intent_ref"] == facts[1]["intent_ref"] and ledger["unresolved"][0]["obligation_id"] == facts[1]["obligation_id"]
            assert progress["payload"]["actions"][1]["resolution_head_ref"] is None
            result["B_unknown_not_discharged_by_C"] = True
            prefix = self.resource(checks[-1]["prefix_resource"])
            cfact = facts[-1]
            # The source stores main precommit prefix1..13 and C fact14 but no
            # separate main event14 Resource. Reconstruct its claimed downstream
            # event using the same common envelope and C second observation time;
            # hash equality establishes internal consistency, not a real commit.
            cevent = {k: prefix[k] for k in ("journal_id", "target_key", "plan_ref", "owner_id", "generation")}
            cevent.update(sequence=14, event="UNATTEMPTED_ABSENCE_COMMITTED", recorded_at=checks[-1]["fact_read_at"], previous_hash=prefix["head_hash"], payload={"action_id": cfact["action_id"], "action_digest": cfact["action_digest"], "fact": receipt["payload"]["action_fact_refs"][-1], "outcome": "NOT_APPLIED", "plan_state": "INTERRUPTED"})
            cevent["event_hash"] = eh(cevent)
            assert cevent["event_hash"] == ledger["event_head_hash"]
            result["independently_derived_C14_event"] = cevent
        return result

    def neighbors(self, source_case, output):
        case = self.load("cases/" + source_case + ".json")
        plan = next(a for a in case["bundle"]["artifacts"] if a["kind"] == "ApplyPlan")
        receipt = next(a for a in case["bundle"]["artifacts"] if a["kind"] == "ExecutionReceipt")
        cfact = self.resource(receipt["payload"]["action_fact_refs"][-1])
        basis = self.resource(cfact["unattempted_basis"])
        prefix = self.resource(basis["complete_uncalled_prefix"])
        rows, mutants = [], []
        for name in ("prefix-missing-acceptance", "prefix-missing-dispatch", "prefix-broken-hash"):
            candidate_case = self.load("cases/" + name + ".json")
            claim = candidate_case["runtime_claim"]
            assert claim["candidate_prefix_role"] == "PRE_ADMISSION_INPUT"
            candidate = self.resource(claim["candidate_uncalled_prefix"])
            actual = self.chain(candidate, plan, candidate["subject_action_id"], bodies=False)
            assert actual["errors"], "authored neighbor incorrectly admitted"
            rows.append({"source": name, "actual": actual})
        for event_name, needed_error in (("PLAN_ACCEPTED", "ACCEPTANCE_MISSING"), ("DISPATCH_STARTED", "RESULT_DISPATCH_MISSING"), ("DISPATCH_PERMIT_CONSUMED", "PERMIT_STAGE_MISMATCH")):
            changed = copy.deepcopy(prefix)
            removed = next(i for i,e in enumerate(changed["events"]) if e["event"] == event_name)
            del changed["events"][removed]
            changed["complete"] = True
            previous = ZERO
            for seq, event in enumerate(changed["events"], 1):
                event["sequence"], event["previous_hash"] = seq, previous
                event["event_hash"] = eh(event)
                previous = event["event_hash"]
            changed["through_sequence"], changed["head_hash"] = len(changed["events"]), previous
            actual = self.chain(changed, plan, changed["subject_action_id"], bodies=False)
            assert needed_error in actual["errors"] and "HASH_BROKEN" not in actual["errors"]
            mutants.append({"mutation": "delete_first_"+event_name+"_then_renumber_rehash_complete_true", "source": basis["complete_uncalled_prefix"], "candidate": changed, "actual": actual})
        output.write_text(json.dumps({"design_only": True, "plan": plan, "mutants": mutants, "runtime_actual": "NOT_EXECUTED"}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        return {"authored": rows, "independent_rechain_mutants": [{"mutation": x["mutation"], "actual": x["actual"]} for x in mutants], "mutant_file": output.name}

    def affected_prefixes(self):
        mapping = self.load("r1-case-mapping.json")
        rows = []
        # Mapping chooses the review set only. Actual graph bytes and invariants
        # determine each result; expected/retained/static labels are not read.
        for item in mapping["mappings"]:
            if item["r1_sha256"] == item["r2_sha256"]:
                continue
            case = self.load(item["r2_path"])
            assert self.inputs[item["r2_path"]] == item["r2_sha256"]
            artifacts = case["bundle"]["artifacts"]
            self.known = {tuple(a[k] for k in REF_KEYS): a for a in artifacts}
            plans = {tuple(a[k] for k in REF_KEYS): a for a in artifacts if a["kind"] == "ApplyPlan"}
            resources = []
            for a in artifacts:
                if a["kind"] == "ExecutionReceipt":
                    resources.extend(a["payload"]["action_fact_refs"])
                if a["kind"] == "ExecutionProgress":
                    resources.extend(row["result_fact"] for row in a["payload"]["actions"] if row["result_fact"])
            prefixes, seen = [], set()
            for resource in resources:
                if resource["path"] in seen:
                    continue
                seen.add(resource["path"])
                fact = self.resource(resource)
                if fact["origin_phase"] != "UNATTEMPTED_ABSENCE":
                    continue
                basis = self.resource(fact["unattempted_basis"])
                prefix = self.resource(basis["complete_uncalled_prefix"])
                plan = plans[tuple(basis["plan_ref"][k] for k in REF_KEYS)]
                result = self.chain(prefix, plan, basis["action_id"])
                assert not result["errors"], (case["case_id"], result)
                prefixes.append({"resource": basis["complete_uncalled_prefix"], "through": result["through"], "errors": result["errors"]})
            rows.append({"case": case["case_id"], "prefixes": prefixes, "actual_recovery_admission": "NOT_EXECUTED"})
        return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    audit = Audit(args.root.resolve())
    result = {"final_commit": FINAL, "design_only": True, "author_checker_imports": 0,
        "runtime_recovery_database_platform_actual": "NOT_EXECUTED", "cases": []}
    for name in ("partial-with-complete-absent", "original-unknown-preserved", "recovered-report-binding"):
        result["cases"].append(audit.positive(name))
    result["neighbors"] = audit.neighbors("partial-with-complete-absent", args.output.parent/"independent-mutants.json")
    result["affected_case_prefixes"] = audit.affected_prefixes()
    result["input_hashes"] = audit.inputs
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"independent_cases": len(result["cases"]), "affected_cases_with_actual_prefix_walk": len(result["affected_case_prefixes"]), "source_files_hashed": len(audit.inputs), "authored_neighbors_rejected": len(result["neighbors"]["authored"]), "independent_rechained_neighbors_rejected": len(result["neighbors"]["independent_rechain_mutants"]), "suffix_time_regressions": [x["case"] for x in result["cases"] if x.get("suffix", {}).get("time_regression")], "runtime_actual": "NOT_EXECUTED"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
