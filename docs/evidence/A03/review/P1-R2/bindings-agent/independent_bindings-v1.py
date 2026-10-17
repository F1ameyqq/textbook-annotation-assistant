"""Independent standard-library static review; never imports candidate checker/runtime."""
import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

FINAL = "940a5de33a24b1a3a9ded6e69ade1dd0609ed83a"
BASE = "ca4fba4f505467228a8164c3999e0cecc54ffc4e"
PACKAGE = "examples/a03/P1-R2/"
DATA = PACKAGE + "data/"
REF = ("artifact_id", "revision", "kind", "content_hash")
POSITIVE = ("unattempted-absence-commit", "partial-with-complete-absent",
            "original-unknown-preserved", "recovered-report-binding")
NEIGHBORS = ("nested-prepared-positive", "evidence-id-resource-closed",
             "nested-prepared-missing-declaration", "evidence-id-resource-missing-declaration",
             "nested-prepared-cross-book", "nested-prepared-cross-scope",
             "nested-prepared-bad-reference-hash", "nested-prepared-bad-resource-hash",
             "nested-resource-cycle", "mixed-artifact-resource-cycle",
             "observed-resource-rejected", "observed-evidence-rejected", "observed-producer-rejected")


def enc(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(enc(value)).hexdigest()


def ref(value):
    return {key: value[key] for key in REF}


def key(value):
    return tuple(value[k] for k in REF)


def strict_json(raw):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError("duplicate JSON key: " + k)
            out[k] = v
        return out
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


class Inputs:
    def __init__(self, source, gitroot):
        self.source, self.gitroot = source.resolve(), gitroot.resolve()
        self.cache, self.index = {}, {}

    def raw(self, rel):
        pp = PurePosixPath(rel)
        if pp.is_absolute() or ".." in pp.parts or "\\" in rel or ":" in rel:
            raise ValueError("unsafe relative path: " + rel)
        if rel not in self.cache:
            raw = (self.source / rel).read_bytes()
            proc = subprocess.run(["git", "cat-file", "blob", FINAL + ":" + rel],
                                  cwd=str(self.gitroot), capture_output=True, check=True)
            if proc.stdout != raw:
                raise ValueError("isolation input differs from exact Git: " + rel)
            self.cache[rel] = raw
            self.index[rel] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "exact_git_equal": True}
        return self.cache[rel]

    def json(self, rel):
        return strict_json(self.raw(rel))

    def resource(self, value):
        raw = self.raw(DATA + value["path"])
        if hashlib.sha256(raw).hexdigest() != value["sha256"]:
            raise ValueError("resource byte hash mismatch: " + value["path"])
        return strict_json(raw)


class Closure:
    def __init__(self, inp, case):
        self.inp, self.case = inp, case
        self.issues, self.graph, self.consumers = [], {}, []
        self.artifacts = case["bundle"]["artifacts"]
        self.known = {key(a): a for a in self.artifacts}
        self.evidence = {}
        for entry in case["bundle"]["evidence"]:
            if entry["evidence_id"] in self.evidence:
                self.issue("DUPLICATE_EVIDENCE_ID", entry["evidence_id"])
            self.evidence[entry["evidence_id"]] = entry
        for a in self.artifacts:
            self.graph[("A",) + key(a)] = set()

    def issue(self, code, location, **details):
        record = {"code": code, "location": location}
        record.update(details)
        if record not in self.issues:
            self.issues.append(record)

    def walk(self, value, parent, consumer, declared, refs, resources, active, location):
        if isinstance(value, dict):
            if set(value) == set(REF):
                k = key(value)
                target = self.known.get(k)
                self.graph.setdefault(parent, set()).add(("A",) + k)
                refs.add(k)
                if target is None:
                    self.issue("REFERENCE_EXACT_TUPLE_MISMATCH", location, reference=value)
                elif consumer is not None:
                    if (consumer["book_id"], consumer["scope_id"]) != (target["book_id"], target["scope_id"]):
                        self.issue("REFERENCE_SCOPE_MISMATCH", location, reference=value)
                    if consumer["schema_version"] != target["schema_version"]:
                        self.issue("CROSS_VERSION_REFERENCE", location)
                if consumer is not None and k not in declared:
                    self.issue("UNDECLARED_RESOURCE_REFERENCE", location, consumer=consumer["artifact_id"], reference=value)
                return
            if {"path", "sha256", "media_type"}.issubset(value):
                node = ("R", value["path"], value["sha256"], value["media_type"])
                self.graph.setdefault(parent, set()).add(node)
                self.graph.setdefault(node, set())
                if value.get("origin") != "SYNTHETIC":
                    self.issue("SYNTHETIC_ONLY", location)
                if node in active:
                    self.issue("RESOURCE_REFERENCE_CYCLE", location)
                    return
                if node in resources:
                    return
                resources.add(node)
                try:
                    raw = self.inp.raw(DATA + value["path"])
                except (OSError, ValueError) as exc:
                    self.issue("RESOURCE_PATH_OR_MISSING", location, reason=str(exc))
                    return
                if hashlib.sha256(raw).hexdigest() != value["sha256"]:
                    self.issue("RESOURCE_HASH_MISMATCH", location)
                    # Continue static graph analysis for diagnostics only; a bad hash is already rejecting.
                if value["media_type"] == "application/json":
                    try:
                        body = strict_json(raw)
                    except ValueError as exc:
                        self.issue("RESOURCE_JSON_INVALID", location, reason=str(exc))
                        return
                    self.walk(body, node, consumer, declared, refs, resources, active | {node}, value["path"])
                return
            for name, item in value.items():
                if name in ("origin", "provenance", "evidence_mode", "source") and isinstance(item, str) and item in ("ORIGINAL", "OBSERVED", "REAL"):
                    self.issue("SYNTHETIC_ONLY", location + "/" + name)
                if name.endswith("evidence_refs") and isinstance(item, list):
                    for eid in item:
                        if isinstance(eid, str):
                            entry = self.evidence.get(eid)
                            if entry is None:
                                self.issue("EVIDENCE_ID_MISSING", location + "/" + name, evidence_id=eid)
                            else:
                                if entry.get("mode") != "SYNTHETIC":
                                    self.issue("SYNTHETIC_ONLY", location + "/" + name)
                                self.walk(entry["resource"], parent, consumer, declared, refs, resources, active, location + "/evidence/" + eid)
                self.walk(item, parent, consumer, declared, refs, resources, active, location + "/" + name)
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                self.walk(item, parent, consumer, declared, refs, resources, active, location + "/" + str(idx))

    def run(self):
        if self.case["bundle"]["format_version"] != "a03-exchange-1":
            self.issue("CROSS_VERSION_REFERENCE", "bundle/format_version")
        for artifact in self.artifacts:
            aid = artifact["artifact_id"]
            if artifact["content_hash"] != digest({k: v for k, v in artifact.items() if k != "content_hash"}):
                self.issue("ARTIFACT_CONTENT_HASH_MISMATCH", aid)
            if artifact["schema_version"] != "1.1.0-a-recovery-proposal":
                self.issue("CROSS_VERSION_REFERENCE", aid)
            if artifact["producer"]["evidence_mode"] != "SYNTHETIC":
                self.issue("SYNTHETIC_ONLY", aid + "/producer")
            declared = {key(r) for r in artifact["input_refs"]}
            refs, resources = set(), set()
            node = ("A",) + key(artifact)
            for field, body in artifact.items():
                if field != "content_hash":
                    self.walk(body, node, artifact, declared, refs, resources, set(), aid + "/" + field)
            self.consumers.append({"artifact_id": aid, "declared_exact_refs": len(declared),
                                   "encountered_exact_refs": len(refs), "recursive_resources": len(resources)})
        # Runtime diagnostic resources have no Artifact input_refs requirement, but retain bytes/identity/graph checks.
        self.walk(self.case.get("runtime_claim", {}), ("runtime_claim",), None, set(), set(), set(), set(), "runtime_claim")
        for r in self.case["ledger_export"]["artifact_history"]:
            if key(r) not in self.known:
                self.issue("LEDGER_HISTORY_REFERENCE_MISMATCH", "ledger_export/artifact_history")
        color = {}
        def visit(node):
            if color.get(node) == 1:
                self.issue("DEPENDENCY_CYCLE", str(node))
                return
            if color.get(node) == 2:
                return
            color[node] = 1
            for nxt in self.graph.get(node, ()):
                visit(nxt)
            color[node] = 2
        for node in list(self.graph):
            visit(node)
        return {"issues": self.issues, "consumers": self.consumers,
                "graph_nodes": len(self.graph), "graph_edges": sum(map(len, self.graph.values()))}


def bindings(inp, case):
    issues, facts_out, prefixes_out = [], [], []
    def require(test, code, **details):
        if not test:
            issues.append(dict(code=code, **details))
    arts = case["bundle"]["artifacts"]
    known = {key(a): a for a in arts}
    plan = next(a for a in arts if a["kind"] == "ApplyPlan")
    actions = plan["payload"]["actions"]
    action_map = {a["action_id"]: a for a in actions}
    intents = {a["payload"]["action_id"]: a for a in arts if a["kind"] == "WriteIntent"}
    receipt = next(a for a in arts if a["kind"] == "ExecutionReceipt")
    ledger = case["ledger_export"]
    facts = []
    event_by_sequence = {}
    prefixes = []
    for rr, result in zip(receipt["payload"]["action_fact_refs"], receipt["payload"]["results"]):
        fact = inp.resource(rr)
        facts.append((rr, fact))
        aid = fact["action_id"]
        require(fact["plan_ref"] == ref(plan) and fact["action_digest"] == digest(action_map[aid]), "FACT_IDENTITY", action_id=aid)
        require(fact["result"] == result, "FACT_RECEIPT_RESULT", action_id=aid)
        if fact["origin_phase"] == "EXECUTION":
            intent = intents[aid]
            ip = intent["payload"]
            obligation = "obl-" + digest({"journal_id": ip["journal_id"], "target_key": ip["target_key"],
                                          "intent_ref": ref(intent), "journal_sequence": ip["journal_sequence"],
                                          "journal_head_hash": ip["journal_head_hash"]})
            require(fact["intent_ref"] == ref(intent) and fact["obligation_id"] == obligation, "INTENT_OBLIGATION_BINDING", action_id=aid)
            deps = {k: plan["payload"][k] for k in ("graph", "precheck", "targetcheck", "snapshot", "policy", "execution_mode", "session_mode", "required_capabilities")}
            expected_dependency = digest({"plan_dependencies_digest": digest(deps), "source_ref": ip["source_ref"],
                                          "target_session_id": ip["target_session_id"], "comparator_version": "a02-facts-1",
                                          "prepared_before_sha256": ip["prepared_before"]["sha256"]})
            require(ip["plan_dependency_digest"] == expected_dependency, "INTENT_PLAN_DEPENDENCY_BINDING", action_id=aid)
            require(ip["action_digest"] == digest(action_map[aid]) and ip["plan_ref"] == ref(plan), "INTENT_ACTION_PLAN_BINDING", action_id=aid)
        else:
            require(fact["origin_phase"] == "UNATTEMPTED_ABSENCE", "UNEXPECTED_FACT_ORIGIN", action_id=aid)
            require(all(fact[k] is None for k in ("intent_ref", "obligation_id", "resolution_ref")) and fact["result"]["intent_ref"] is None, "TAIL_MANUFACTURED_INTENT", action_id=aid)
            require((fact["result"]["attempt_fact"], fact["result"]["outcome"], fact["result"]["effect_match"], fact["result"]["replay_allowed"]) == ("NOT_ATTEMPTED", "NOT_APPLIED", "ABSENT", False), "TAIL_RESULT", action_id=aid)
            basis = inp.resource(fact["unattempted_basis"])
            prefix = inp.resource(basis["complete_uncalled_prefix"])
            prefixes.append(prefix)
            require(fact["journal_sequence"] == basis["expected_event_head"]["sequence"] + 1 and fact["predecessor_hash"] == basis["expected_event_head"]["hash"], "FACT_BASIS_CAS", action_id=aid)
            require(basis["plan_ref"] == ref(plan) and basis["action_id"] == aid and basis["action_digest"] == digest(action_map[aid]), "BASIS_ACTION_BINDING", action_id=aid)
            require((basis["owner_id"], basis["generation"], basis["target_key"]) == (ledger["owner_id"], ledger["generation"], ledger["book_key"]), "BASIS_LEDGER_BINDING", action_id=aid)
            require(basis["scope_id"] == plan["scope_id"] and basis["plan_status"] == "INTERRUPTED", "BASIS_SCOPE_STATE", action_id=aid)
            require(basis["expected_event_head"] == {"sequence": prefix["through_sequence"], "hash": prefix["head_hash"]}, "PREFIX_BASIS_HEAD", action_id=aid)
            require(fact["prepared_before"] == basis["readonly_prepared_ref"] and fact["readback"] == basis["second_observation_ref"] == fact["result"]["readback"], "READONLY_FACT_RESOURCE_BINDING", action_id=aid)
            first = inp.resource(basis["first_observation_ref"])
            second = inp.resource(basis["second_observation_ref"])
            prepared = inp.resource(basis["readonly_prepared_ref"])
            require(first["observation_id"] != second["observation_id"] and first["read_sequence"] < second["read_sequence"] and first["observed_at"] < second["observed_at"], "OBSERVATION_FRESHNESS_STATIC_BINDING", action_id=aid)
            require(prepared["first_observation_ref"] == basis["first_observation_ref"] and prepared["observation_id"] == first["observation_id"] and prepared["read_sequence"] == first["read_sequence"], "PREPARED_FIRST_OBSERVATION_BINDING", action_id=aid)
            for ob in (first, second, prepared):
                require(all(ob[k] == basis[k] for k in ("target_key", "scope_id", "source_ref", "target_session_id")), "OBSERVATION_SOURCE_SCOPE_SESSION_BINDING", action_id=aid)
            require(first["store_id"] == second["store_id"] == basis["target_store_id"], "OBSERVATION_STORE_BINDING", action_id=aid)
            require(basis["observer_calls"] == 2 and basis["retries"] == 0 and basis["single_read_seconds"] == 2 and basis["entry_seconds"] == 8 and basis["parent_call_seconds"] == 60, "READ_LIMIT_DECLARATION", action_id=aid)
            require(not any(e["payload"].get("action_id") == aid for e in prefix["events"]), "TAIL_CALLED_IN_PRECOMMIT_PREFIX", action_id=aid)
            prefixes_out.append({"action_id": aid, "prefix_resource": basis["complete_uncalled_prefix"], "through_sequence": prefix["through_sequence"], "fact_sequence": fact["journal_sequence"], "head": prefix["head_hash"]})
        facts_out.append({"resource": rr, "action_id": aid, "origin_phase": fact["origin_phase"], "sequence": fact["journal_sequence"], "predecessor_hash": fact["predecessor_hash"], "outcome": fact["result"]["outcome"]})
    require(len(facts) == len(actions) == len(receipt["payload"]["results"]), "FACT_RESULT_CARDINALITY")
    require([f[1]["action_id"] for f in facts] == [a["action_id"] for a in actions], "FACT_ACTION_ORDER")
    for prefix in prefixes:
        prev = prefix["genesis_hash"]
        require(prefix["from_sequence"] == 1 and prefix["through_sequence"] == len(prefix["events"]), "PREFIX_COUNT")
        for seq, event in enumerate(prefix["events"], 1):
            eh = digest({k: v for k, v in event.items() if k != "event_hash"})
            require(event["sequence"] == seq and event["previous_hash"] == prev and event["event_hash"] == eh, "EVENT_CHAIN_HASH", sequence=seq)
            require(all(event[k] == prefix[k] for k in ("journal_id", "target_key", "plan_ref", "owner_id", "generation")), "EVENT_HEADER_BINDING", sequence=seq)
            if seq in event_by_sequence:
                require(event_by_sequence[seq] == event, "PREFIX_FORK", sequence=seq)
            event_by_sequence[seq] = event
            prev = event["event_hash"]
        require(prev == prefix["head_hash"], "PREFIX_FINAL_HEAD")
    suffix_ref = case.get("runtime_claim", {}).get("post_prefix_events")
    suffix = inp.resource(suffix_ref) if suffix_ref else None
    if suffix:
        for event in suffix["events"]:
            event_by_sequence[event["sequence"]] = event
        require(suffix["from_sequence"] == 10 and suffix["through_sequence"] == 11 and suffix["predecessor_hash"] == event_by_sequence[9]["event_hash"], "POST_PREFIX_9_10_BINDING")
    # The 13-event main branch stores only its precommit prefix. Reconstruct its
    # declared event14 from immutable C fact + actual hand-authored observation
    # time using the documented UNATTEMPTED event serialization; no execution.
    reconstructed = []
    for rr, fact in facts:
        seq = fact["journal_sequence"]
        if seq not in event_by_sequence and fact["origin_phase"] == "UNATTEMPTED_ABSENCE":
            basis = inp.resource(fact["unattempted_basis"])
            e = {k: copy.deepcopy(basis[k]) for k in ("journal_id", "target_key", "plan_ref", "owner_id", "generation")}
            e.update(sequence=seq, event="UNATTEMPTED_ABSENCE_COMMITTED", recorded_at=inp.resource(fact["readback"])["observed_at"],
                     payload={"action_id": fact["action_id"], "action_digest": fact["action_digest"], "fact": rr,
                              "outcome": "NOT_APPLIED", "plan_state": "INTERRUPTED"}, previous_hash=fact["predecessor_hash"])
            e["event_hash"] = digest(e)
            event_by_sequence[seq] = e
            reconstructed.append(e)
    for seq in sorted(event_by_sequence):
        e = event_by_sequence[seq]
        p = e["payload"]
        require(e["event_hash"] == digest({k: v for k, v in e.items() if k != "event_hash"}), "POST_OR_RECONSTRUCTED_HASH", sequence=seq)
        if seq > 1:
            require(e["previous_hash"] == event_by_sequence[seq - 1]["event_hash"], "MERGED_EVENT_PREDECESSOR", sequence=seq)
        if e["event"] == "WRITE_INTENT_COMMITTED":
            ip = known[key(p["intent_ref"])]["payload"]
            require(ip["journal_sequence"] == seq and ip["journal_head_hash"] == e["previous_hash"], "INTENT_EVENT_PREDECESSOR", sequence=seq)
        if e["event"] in ("ACTION_RESULT_COMMITTED", "UNATTEMPTED_ABSENCE_COMMITTED"):
            f = inp.resource(p["fact"])
            require(f["journal_sequence"] == seq and f["predecessor_hash"] == e["previous_hash"] and f["result"]["outcome"] == p["outcome"], "FACT_EVENT_BINDING", sequence=seq)
            require(f["action_id"] == p["action_id"] and f["action_digest"] == p["action_digest"], "FACT_EVENT_ACTION", sequence=seq)
        if e["event"] == "RECONCILIATION_COMMITTED":
            res = known[key(p["resolution_ref"])]["payload"]
            require(all(p[k] == res[k] for k in ("action_id", "action_digest", "intent_ref", "obligation_id", "observation_id", "resolution")), "TERMINAL_RESOLUTION_BINDING")
            original = next(f for rr, f in facts if f["action_id"] == p["action_id"])
            require(original["result"]["outcome"] == "UNKNOWN" and original["intent_ref"] == p["intent_ref"] and original["obligation_id"] == p["obligation_id"], "TERMINAL_ORIGINAL_UNKNOWN_BINDING")
            require(res["original_receipt_ref"] == ref(receipt) and e["recorded_at"] == res["observed_at"] and not res["replay_allowed"], "TERMINAL_RECEIPT_TIME_BINDING")
    last = event_by_sequence[max(event_by_sequence)]
    require((ledger["event_head_sequence"], ledger["event_head_hash"]) == (last["sequence"], last["event_hash"]), "LEDGER_FINAL_HEAD_BINDING")
    require({key(r) for r in ledger["artifact_history"]} == {key(a) for a in arts}, "LEDGER_FULL_ARTIFACT_HISTORY_STATIC")
    for progress in (a for a in arts if a["kind"] == "ExecutionProgress"):
        pp = progress["payload"]
        require((pp["journal_head_sequence"], pp["journal_head_hash"]) == (last["sequence"], last["event_hash"]), "PROGRESS_FINAL_HEAD_BINDING")
        for row, (rr, fact) in zip(pp["actions"], facts):
            require(row["result_fact"] == rr and row["receipt_ref"] == ref(receipt) and row["attempt_fact"] == fact["result"]["attempt_fact"], "PROGRESS_FACT_RECEIPT_BINDING", action_id=row["action_id"])
            if row["resolution_head_ref"] is not None:
                res = known[key(row["resolution_head_ref"])]["payload"]
                require(res["resolution"] == "RESOLVED_APPLIED" and row["effective_outcome"] == "APPLIED" and fact["result"]["outcome"] == "UNKNOWN", "PROGRESS_RECOVERY_PROJECTION")
            else:
                require(row["effective_outcome"] == fact["result"]["outcome"], "PROGRESS_OUTCOME_PROJECTION")
    if suffix:
        require(not ledger["unresolved"] and not ledger["pending_action_ids"] and ledger["pause"] == {"paused": False, "reason_codes": [], "event_ids": []}, "TERMINAL_PAUSE_PROJECTION")
        require(receipt["payload"]["results"][0]["outcome"] == "UNKNOWN", "ORIGINAL_UNKNOWN_MUTATED")
    else:
        unknown = next(f for rr, f in facts if f["result"]["outcome"] == "UNKNOWN")
        require(len(ledger["unresolved"]) == 1 and ledger["unresolved"][0]["intent_ref"] == unknown["intent_ref"] and ledger["unresolved"][0]["obligation_id"] == unknown["obligation_id"], "UNRELATED_UNKNOWN_UNRESOLVED_PROJECTION")
        require(ledger["pending_action_ids"] == [unknown["action_id"]] and ledger["pause"]["paused"] and "SAVE_UNKNOWN" in ledger["pause"]["reason_codes"], "UNRELATED_UNKNOWN_PAUSE_PROJECTION")
        require(receipt["payload"]["write_disposition"] == "PAUSE_RECONCILE", "UNKNOWN_RECEIPT_PAUSE")
        req = case["runtime_claim"]["request"]
        require(req["expected_event_head"] == {"sequence": 13, "hash": event_by_sequence[13]["event_hash"]} and req["action_id"] == actions[-1]["action_id"], "REQUEST_CAS_ACTION_BINDING")
    require(case["runtime_claim"]["plan_status"] == "INTERRUPTED" and case["runtime_claim"]["old_tail_dispatches"] == 0, "NO_OLD_TAIL_RESUME")
    return {"issues": issues, "facts": facts_out, "prefixes": prefixes_out,
            "final_head": {"sequence": last["sequence"], "hash": last["event_hash"]},
            "reconstructed_postcommit_event_serialization": reconstructed,
            "reconstruction_is_static_not_committed_event_evidence": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--git-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inp = Inputs(args.source, args.git_root)
    api = inp.json(PACKAGE + "api-proposal.json")
    base_proc = subprocess.run(["git", "cat-file", "blob", BASE + ":examples/a03/P1-R1/api-proposal.json"], cwd=str(args.git_root), capture_output=True, check=True)
    base = strict_json(base_proc.stdout)
    api_changes = sorted(k for k in set(base) | set(api) if base.get(k) != api.get(k))
    stable = ["groups", "refusal_boundaries", "initial_dispatch_authority", "normal_action_result_protocol",
              "unattempted_absence_protocol", "resource_reference_closure_protocol", "runtime_authority_protocol", "two_stage_gate"]
    api_stable = {k: api[k] == base[k] for k in stable}
    profile = api["candidate_profile"]
    profile_hashes = {}
    for name, entry in profile["schema_files"].items():
        raw = inp.raw(PACKAGE + entry["path"])
        profile_hashes[name] = hashlib.sha256(raw).hexdigest() == entry["sha256"]
    results = {}
    for name in POSITIVE + NEIGHBORS:
        filename = DATA + "cases/" + name + ".json"
        if not (args.source / filename).exists():
            results[name] = {"not_found": True}
            continue
        case = inp.json(filename)
        results[name] = {"closure": Closure(inp, case).run()}
        if name in POSITIVE:
            results[name]["bindings"] = bindings(inp, case)
    failures = {n: {"closure": v["closure"]["issues"], "bindings": v["bindings"]["issues"]}
                for n, v in results.items() if n in POSITIVE and (v["closure"]["issues"] or v["bindings"]["issues"])}
    out = {"review_kind": "INDEPENDENT_STATIC_DESIGN_ONLY", "candidate_final_commit": FINAL, "candidate_design_commit": "a250a76dc0b3f13b9dee3bcd2c3d7414032b9768",
           "baseline_commit": BASE, "source": str(args.source.resolve()), "argv": sys.argv, "cwd": os.getcwd(),
           "python": sys.version, "pid": os.getpid(), "utc_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "author_code_imports_or_expected_fields_used": False, "baseline_api_bytes_sha256": hashlib.sha256(base_proc.stdout).hexdigest(),
           "api_changed_top_level_fields": api_changes, "stable_api_protocols": api_stable, "candidate_profile_seven_schema_hashes": profile_hashes,
           "cases": results, "positive_failures": failures, "exact_git_input_index": inp.index,
           "scope_conclusion": "STATIC_BINDINGS_AND_REFERENCE_CLOSURE_NO_DEFECT_FOUND" if not failures and all(api_stable.values()) and all(profile_hashes.values()) else "REWORK",
           "not_executed": ["runtime_api", "sqlite", "target_effects", "recovery", "fresh_actual_observation", "dispatch", "platform", "browser", "network", "credential_profile", "OCR", "model_api", "P2", "I01"],
           "limitations": ["Not a complete JSON Schema standard validator", "Static hand-authored observations cannot prove freshness or current runtime authority", "Main event14 is independently reconstructed from its documented serialization and immutable fact; it is not a serialized committed-event receipt", "Does not replace root prefix/event transition review or original 69-case semantic mapping"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"scope_conclusion": out["scope_conclusion"], "positive_failures": failures,
                      "stable_api_protocols": api_stable, "schema_hashes": profile_hashes,
                      "inputs": len(inp.index), "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0 if out["scope_conclusion"] != "REWORK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
