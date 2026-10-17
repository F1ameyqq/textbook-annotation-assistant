"""DESIGN_ONLY bounded R2 JSON conversion. Standard library, no business imports.

Read the frozen R1 data and write one previously absent output directory. No
database, runtime, target, model or recovery API is imported or called.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASELINE = "ca4fba4f505467228a8164c3999e0cecc54ffc4e"
ZERO = "0" * 64


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))


def ref(value):
    return {key: value[key] for key in ("artifact_id", "revision", "kind", "content_hash")}


def is_ref(value):
    return isinstance(value, dict) and set(value) == {"artifact_id", "revision", "kind", "content_hash"}


def is_resource(value):
    return isinstance(value, dict) and {"path", "sha256", "media_type"} <= set(value)


def rehash(artifact):
    artifact["content_hash"] = digest({key: value for key, value in artifact.items() if key != "content_hash"})


def obligation(intent):
    p = intent["payload"]
    return "obl-" + digest({"journal_id": p["journal_id"], "target_key": p["target_key"], "intent_ref": ref(intent),
                             "journal_sequence": p["journal_sequence"], "journal_head_hash": p["journal_head_hash"]})


class Package:
    def __init__(self, root):
        self.root = root

    def resource(self, value):
        data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
        sha = hashlib.sha256(data).hexdigest()
        path = self.root / "assets/r2" / (sha + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != data:
            raise ValueError("resource digest collision")
        path.write_bytes(data)
        return {"path": "assets/r2/" + sha + ".json", "sha256": sha, "media_type": "application/json", "origin": "SYNTHETIC"}

    def load_resource(self, resource):
        data = (self.root / resource["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != resource["sha256"]:
            raise ValueError("resource bytes mismatch in selected positive fixture")
        return json.loads(data)

    def references(self, value, seen=None):
        seen = set() if seen is None else seen
        if is_ref(value):
            yield value
        elif is_resource(value):
            if value["path"] not in seen:
                seen.add(value["path"])
                if value["media_type"] == "application/json":
                    yield from self.references(self.load_resource(value), seen)
        elif isinstance(value, dict):
            for child in value.values():
                yield from self.references(child, seen)
        elif isinstance(value, list):
            for child in value:
                yield from self.references(child, seen)


def replace(value, refs, resources, obligations):
    if is_ref(value):
        return deepcopy(refs.get((value["artifact_id"], value["revision"]), value))
    if is_resource(value):
        return deepcopy(resources.get(value["path"], value))
    if isinstance(value, dict):
        return {key: replace(child, refs, resources, obligations) for key, child in value.items()}
    if isinstance(value, list):
        return [replace(child, refs, resources, obligations) for child in value]
    if isinstance(value, str):
        return obligations.get(value, value)
    return value


def refresh_nested(value, package, refs, resources, obligations):
    """Retain strict DAG declarations while recomputing changed Resource bytes."""
    if is_resource(value):
        if value["path"] in resources:
            return deepcopy(resources[value["path"]])
        if value["media_type"] != "application/json":
            return deepcopy(value)
        original = package.load_resource(value)
        rebuilt = refresh_nested(original, package, refs, resources, obligations)
        if rebuilt == original:
            return deepcopy(value)
        resource = package.resource(rebuilt)
        resources[value["path"]] = resource
        return resource
    if is_ref(value):
        return deepcopy(refs.get((value["artifact_id"], value["revision"]), value))
    if isinstance(value, dict):
        return {key: refresh_nested(child, package, refs, resources, obligations) for key, child in value.items()}
    if isinstance(value, list):
        return [refresh_nested(child, package, refs, resources, obligations) for child in value]
    if isinstance(value, str):
        return obligations.get(value, value)
    return value


def finalize_artifacts(package, artifacts, refs, resources, obligations, events):
    """Topological refresh after an event head or consumed Resource changes."""
    frozen_intents = {a["artifact_id"] for a in artifacts if a["kind"] == "WriteIntent"}
    pending = {a["artifact_id"]: a for a in artifacts if a["artifact_id"] not in frozen_intents}
    done = set(frozen_intents)
    all_ids = {a["artifact_id"] for a in artifacts}
    while pending:
        progress = False
        for aid, artifact in list(pending.items()):
            adjusted = replace(artifact, refs, resources, obligations)
            needs = {r["artifact_id"] for r in package.references(adjusted["payload"]) if r["artifact_id"] in all_ids}
            if not needs <= done:
                continue
            if adjusted["kind"] == "ExecutionProgress":
                adjusted["payload"]["journal_head_sequence"] = len(events)
                adjusted["payload"]["journal_head_hash"] = events[-1]["event_hash"]
            declarations = {canonical(r): r for r in adjusted["input_refs"]}
            for r in package.references(adjusted["payload"]):
                declarations[canonical(r)] = r
            adjusted["input_refs"] = list(declarations.values())
            rehash(adjusted)
            artifact.clear()
            artifact.update(adjusted)
            refs[(aid, artifact["revision"])] = ref(artifact)
            done.add(aid)
            del pending[aid]
            progress = True
        if not progress:
            raise ValueError("selected positive dependency graph failed to close: " + str(sorted(pending)))


def convert(case, package):
    """Only selected valid fact/basis graphs; malicious old cases stay byte exact."""
    case = deepcopy(case)
    artifacts = case["bundle"]["artifacts"]
    plan = next(a for a in artifacts if a["kind"] == "ApplyPlan")
    receipt = next(a for a in artifacts if a["kind"] == "ExecutionReceipt")
    old_fact_resources = receipt["payload"]["action_fact_refs"]
    old_facts = [package.load_resource(r) for r in old_fact_resources]
    intents = {a["payload"]["action_id"]: a for a in artifacts if a["kind"] == "WriteIntent"}
    exemplar = next(iter(intents.values()))["payload"]
    event_header = {key: deepcopy(exemplar[key]) for key in ("journal_id", "target_key", "plan_ref", "owner_id", "generation")}
    events, refs, resources, obligations, bases = [], {}, {}, {}, []

    def event(name, payload, time):
        obj = {"sequence": len(events) + 1, "event": name, **deepcopy(event_header), "recorded_at": time,
               "payload": deepcopy(payload), "previous_hash": events[-1]["event_hash"] if events else ZERO}
        obj["event_hash"] = digest(obj)
        events.append(obj)
        return obj

    def prefix(subject):
        return {"format_version": "a03-event-prefix-1", "design_only": True, **deepcopy(event_header),
                "scope_id": plan["scope_id"], "subject_action_id": subject, "genesis_hash": ZERO,
                "from_sequence": 1, "through_sequence": len(events), "head_hash": events[-1]["event_hash"],
                "events": deepcopy(events)}

    actions = [{"action_id": a["action_id"], "action_digest": digest(a)} for a in plan["payload"]["actions"]]
    event("PLAN_ACCEPTED", {"plan_ref": ref(plan), "actions": actions}, "2026-10-17T00:00:00Z")
    event("PLAN_ACTIONS_RESERVED", {"reservations": actions}, "2026-10-17T00:00:00Z")
    event("PLAN_STARTED", {"plan_state": "RUNNING"}, "2026-10-17T00:00:00Z")
    for index, (old_resource, old_fact) in enumerate(zip(old_fact_resources, old_facts)):
        fact = deepcopy(old_fact)
        action_id, action_digest = fact["action_id"], fact["action_digest"]
        if fact["origin_phase"] == "EXECUTION":
            intent = intents[action_id]
            old_obligation = obligation(intent)
            p = intent["payload"]
            p["journal_sequence"], p["journal_head_hash"] = len(events) + 1, events[-1]["event_hash"]
            p["intent_committed_at"] = "2026-10-17T00:00:02Z" if index == 0 else "2026-10-17T00:00:05Z"
            intent["created_at"] = p["intent_committed_at"]
            rehash(intent)
            refs[(intent["artifact_id"], intent["revision"])] = ref(intent)
            obligation_id = obligation(intent)
            obligations[old_obligation] = obligation_id
            common = {"action_id": action_id, "action_digest": action_digest, "intent_ref": ref(intent)}
            event("WRITE_INTENT_COMMITTED", {**common, "obligation_id": obligation_id}, p["intent_committed_at"])
            permit_id = "permit-r2-" + str(index + 1)
            for name in ("DISPATCH_PERMIT_ISSUED", "DISPATCH_PERMIT_CONSUMED", "DISPATCH_STARTED"):
                event(name, {**common, "permit_id": permit_id}, p["intent_committed_at"])
            fact["intent_ref"] = ref(intent)
            fact["obligation_id"] = obligation_id
            fact["result"]["intent_ref"] = ref(intent)
            fact["journal_sequence"], fact["predecessor_hash"] = len(events) + 1, events[-1]["event_hash"]
            fact_ref = package.resource(fact)
            outcome = fact["result"]["outcome"]
            state = "INTERRUPTED" if outcome == "UNKNOWN" else "RUNNING"
            result_time = "2026-10-17T00:00:03Z" if index == 0 else "2026-10-17T00:00:06Z"
            event("ACTION_RESULT_COMMITTED", {**common, "obligation_id": obligation_id, "fact": fact_ref,
                  "outcome": outcome, "plan_state": state}, result_time)
        else:
            basis = package.load_resource(fact["unattempted_basis"])
            # The readonly prepared/observations can themselves consume an
            # already-applied fact. Rebuild these before basis/fact, rather
            # than merely refreshing top-level receipt references.
            for key in ("prepared_before", "readback"):
                fact[key] = refresh_nested(fact[key], package, refs, resources, obligations)
            for key in ("first_observation_ref", "readonly_prepared_ref", "second_observation_ref"):
                basis[key] = refresh_nested(basis[key], package, refs, resources, obligations)
            fact["result"] = replace(fact["result"], refs, resources, obligations)
            basis["expected_event_head"] = {"sequence": len(events), "hash": events[-1]["event_hash"]}
            basis["complete_uncalled_prefix"] = package.resource(prefix(action_id))
            fact["journal_sequence"], fact["predecessor_hash"] = len(events) + 1, events[-1]["event_hash"]
            fact["unattempted_basis"] = package.resource(basis)
            fact_ref = package.resource(fact)
            bases.append((fact_ref, fact, basis))
            read_at = package.load_resource(fact["readback"])["observed_at"]
            event("UNATTEMPTED_ABSENCE_COMMITTED", {"action_id": action_id, "action_digest": action_digest,
                  "fact": fact_ref, "outcome": "NOT_APPLIED", "plan_state": "INTERRUPTED"}, read_at)
        resources[old_resource["path"]] = fact_ref

    # Rebuild only the selected consumers in dependency order. Prefix/fact bytes
    # never point forward to receipt/progress, so this has no digest fixed point.
    finalize_artifacts(package, artifacts, refs, resources, obligations, events)
    resolutions = [a for a in artifacts if a["kind"] == "ReconciliationResult"]
    if resolutions:
        # Existing terminal resolution follows C10. Its bounded suffix explains
        # ledger/progress head11 and the resolved pause without putting a
        # forward reference into either precommit absence prefix.
        resolution = resolutions[0]
        p = resolution["payload"]
        event("RECONCILIATION_COMMITTED", {key: deepcopy(p[key]) for key in
              ("action_id", "action_digest", "intent_ref", "obligation_id", "observation_id", "resolution")}, p["observed_at"])
        events[-1]["payload"].update(resolution_ref=ref(resolution), plan_state="INTERRUPTED")
        events[-1]["event_hash"] = digest({key: value for key, value in events[-1].items() if key != "event_hash"})
        case["runtime_claim"]["post_prefix_events"] = package.resource({"format_version": "a03-post-prefix-events-1",
            "design_only": True, "from_sequence": 10, "through_sequence": 11,
            "predecessor_hash": events[-2]["previous_hash"], "head_hash": events[-1]["event_hash"], "events": deepcopy(events[-2:])})
        finalize_artifacts(package, artifacts, refs, resources, obligations, events)
    case = replace(case, refs, resources, obligations)
    case["ledger_export"]["event_head_sequence"] = len(events)
    case["ledger_export"]["event_head_hash"] = events[-1]["event_hash"]
    case["ledger_export"]["artifact_history"] = [ref(a) for a in case["bundle"]["artifacts"]]
    claim = case["runtime_claim"]
    if "request" in claim:
        claim["request"]["expected_event_head"] = deepcopy(bases[-1][2]["expected_event_head"])
    if "current_event_head" in claim:
        claim["current_event_head"]["sequence"] = bases[-1][2]["expected_event_head"]["sequence"] + 1
    if "candidate_uncalled_prefix" in claim:
        candidate = package.load_resource(bases[-1][2]["complete_uncalled_prefix"])
        candidate["events"] = candidate["events"][1:]
        rebuild_chain(candidate)
        claim["candidate_uncalled_prefix"] = package.resource(candidate)
    return case


def rebuild_chain(prefix):
    previous = ZERO
    for seq, event in enumerate(prefix["events"], 1):
        event["sequence"], event["previous_hash"] = seq, previous
        event["event_hash"] = digest({key: value for key, value in event.items() if key != "event_hash"})
        previous = event["event_hash"]
    prefix["through_sequence"], prefix["head_hash"] = len(prefix["events"]), previous


def primary_trigger(case, package):
    """Compare original semantic perturbations independently of derived digests."""
    claim = case["runtime_claim"]
    scalar_keys = ("plan_status", "old_tail_dispatches", "original_unknown_preserved", "original_B_unknown_preserved",
        "intent_for_tail", "obligation_for_tail", "resolution_for_tail", "independent_absent", "actual_new_read",
        "complete_uncalled_prefix", "supplied_generation", "current_generation", "current_plan_status", "current_action_dispatch_count",
        "readonly_prepared_action_id", "requested_action_belongs_to_plan", "same_committed_fact", "different_existing_fact")
    result = {"runtime_fields": {key: deepcopy(claim[key]) for key in scalar_keys if key in claim}}
    if "request" in claim:
        result["request_action"] = {key: claim["request"][key] for key in ("action_id", "action_digest")}
    if "current_event_head" in claim:
        result["stale_head_delta"] = claim["current_event_head"]["sequence"] - claim["request"]["expected_event_head"]["sequence"]
        result["stale_head_is_zero"] = claim["current_event_head"]["hash"] == ZERO
    if "candidate_uncalled_prefix" in claim:
        candidate = package.load_resource(claim["candidate_uncalled_prefix"])
        result["candidate_has_acceptance"] = any(event.get("event") == "PLAN_ACCEPTED" for event in candidate.get("events", []))
    if "candidate_second_observation" in claim:
        candidate = package.load_resource(claim["candidate_second_observation"])
        result["candidate_observation"] = {key: deepcopy(candidate[key]) for key in ("observation_id", "related_entities_complete", "read_sequence", "observed_at") if key in candidate}
    if "current_library_existing_fact_binding" in claim:
        binding = claim["current_library_existing_fact_binding"]
        result["existing_binding_action"] = {key: binding[key] for key in ("action_id", "action_digest")}
    for artifact in case["bundle"]["artifacts"]:
        p = artifact["payload"]
        if artifact["kind"] == "ExecutionReceipt":
            result["receipt"] = [{key: row[key] for key in ("action_id", "outcome", "effect_match", "attempt_fact", "next_step", "replay_allowed")} |
                {"has_intent": row["intent_ref"] is not None} for row in p["results"]]
        if artifact["kind"] == "ExecutionProgress":
            result["progress"] = [{key: row[key] for key in ("action_id", "attempt_fact", "dependency_status", "effective_outcome")} |
                {"has_intent": row["intent_ref"] is not None, "has_resolution": row["resolution_head_ref"] is not None,
                 "has_fact": row["result_fact"] is not None} for row in p["actions"]]
        if artifact["kind"] == "ReconciliationResult":
            result["resolution"] = {key: p[key] for key in ("action_id", "action_digest", "observation_id", "observation", "resolution", "replay_allowed")}
            result["resolution"]["original_receipt_id"] = p["original_receipt_ref"]["artifact_id"]
        if artifact["kind"] == "BatchReport":
            result["report"] = {key: deepcopy(p[key]) for key in ("submission_status", "content_check_status", "frame_check_status", "state", "total_expected", "questions", "unresolved_issue_ids")}
    result["pending_action_ids"] = case["ledger_export"]["pending_action_ids"]
    result["pause"] = case["ledger_export"]["pause"]
    result["unresolved_events"] = [{key: row[key] for key in ("event_id", "scope_id", "classification")} for row in case["ledger_export"]["unresolved"]]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=HERE.parent / "P1-R1/data")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists() or HERE not in output.parents:
        raise ValueError("output must be a previously absent child of P1-R2")
    shutil.copytree(source, output)
    package = Package(output)
    old_manifest = read(source / "case-manifest.json")
    selected = {row["case_id"] for row in old_manifest["cases"] if row["case_id"].startswith("unattempted-") and row["expected_static"] == "PASS"}
    selected |= {"partial-with-complete-absent", "original-unknown-preserved", "recovered-report-binding"}
    for cid in sorted(selected):
        file = output / "cases" / (cid + ".json")
        write(file, convert(read(source / "cases" / (cid + ".json")), package))
    success = read(output / "cases/unattempted-absence-commit.json")
    receipt = next(a for a in success["bundle"]["artifacts"] if a["kind"] == "ExecutionReceipt")
    fact = package.load_resource(receipt["payload"]["action_fact_refs"][-1])
    basis = package.load_resource(fact["unattempted_basis"])
    good_prefix = package.load_resource(basis["complete_uncalled_prefix"])
    manifest = deepcopy(old_manifest)
    manifest.update(candidate_revision="P1-R2", baseline_commit=BASELINE)
    for cid, missing, error in (("prefix-missing-acceptance", "PLAN_ACCEPTED", "PREFIX_ACCEPTANCE_MISSING"),
                                ("prefix-missing-dispatch", "DISPATCH_STARTED", "PREFIX_DISPATCH_MISSING"),
                                ("prefix-broken-hash", None, "PREFIX_HASH_BROKEN")):
        case = deepcopy(success)
        case["case_id"] = cid
        candidate = deepcopy(good_prefix)
        if missing:
            index = next(i for i, event in enumerate(candidate["events"]) if event["event"] == missing)
            del candidate["events"][index]
            rebuild_chain(candidate)
        else:
            candidate["events"][6]["previous_hash"] = "f" * 64
        case["runtime_claim"]["candidate_uncalled_prefix"] = package.resource(candidate)
        case["runtime_claim"]["candidate_prefix_role"] = "PRE_ADMISSION_INPUT"
        case["runtime_claim"]["complete_uncalled_prefix"] = False
        write(output / "cases" / (cid + ".json"), case)
        manifest["cases"].append({"case_id": cid, "path": "cases/" + cid + ".json", "expected_layer": "STATIC_EVENT_PREFIX",
            "expected_code": error, "expected_static": "PREFIX_FAIL", "semantic_execution": "EXPECTED_NOT_EXECUTED",
            "note": "Bounded R2 neighbor: actual supplied prefix bytes are checked independently; the valid proposed fact graph is retained for context, not a committed result."})
    write(output / "case-manifest.json", manifest)
    mapping = {"design_only": True, "candidate_revision": "P1-R2", "baseline_commit": BASELINE, "original_case_count": 69,
               "new_neighbor_count": 3, "mappings": []}
    for row in old_manifest["cases"]:
        old_bytes, new_bytes = (source / row["path"]).read_bytes(), (output / row["path"]).read_bytes()
        trigger = None
        if row["case_id"] in selected:
            old_trigger = primary_trigger(read(source / row["path"]), Package(source))
            new_trigger = primary_trigger(read(output / row["path"]), package)
            trigger = {"r1": old_trigger, "r2": new_trigger, "equal": old_trigger == new_trigger}
            if old_trigger != new_trigger:
                raise ValueError("original primary semantic trigger changed: " + row["case_id"])
        mapping["mappings"].append({"r1_case_id": row["case_id"], "r1_path": row["path"],
            "r1_sha256": hashlib.sha256(old_bytes).hexdigest(), "r2_case_id": row["case_id"], "r2_path": row["path"],
            "r2_sha256": hashlib.sha256(new_bytes).hexdigest(), "expected_layer": row["expected_layer"],
            "expected_code": row["expected_code"], "expected_static": row["expected_static"],
            "bytes_unchanged": old_bytes == new_bytes, "semantic_trigger_retained": True,
            "primary_trigger_comparison": trigger if trigger is not None else {"method": "byte-exact", "equal": old_bytes == new_bytes},
            "bounded_change": "complete event prefix and derived intent/obligation/fact/CAS/consumer refs only" if row["case_id"] in selected else "none; byte-exact R1 input"})
    write(output / "r1-case-mapping.json", mapping)
    # Keep the old 42-case mapping as evidence; add separate R2 fields rather
    # than changing its frozen P1/R1 digests or assertions.
    previous = read(output / "case-mapping.json")
    previous["r2_mapping"] = "r1-case-mapping.json"
    for row in previous["mappings"]:
        row["r2_path"] = row["r1_path"]
        row["r2_sha256"] = hashlib.sha256((output / row["r2_path"]).read_bytes()).hexdigest()
    write(output / "case-mapping.json", previous)
    print(json.dumps({"design_only": True, "baseline_commit": BASELINE, "source_files": len([p for p in source.rglob('*') if p.is_file()]),
        "selected_cases_rebuilt": sorted(selected), "original_cases": 69, "new_neighbors": 3,
        "runtime_or_recovery_executed": False, "output": output.name}, indent=2))


if __name__ == "__main__":
    main()
