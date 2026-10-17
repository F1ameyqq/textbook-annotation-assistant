"""DESIGN_ONLY P1-R1 static data revision. No business module/API is imported.

Read frozen P1 bytes and write a new, empty directory below this R1 directory.
Only JSON shape, exact references and data hashes are transformed. Nothing here
qualifies an intent, performs a target read, commits a fact or recovers a run.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "P1"
ZERO = "0" * 64


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode("utf-8")).hexdigest()


def raw(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def is_ref(value):
    return isinstance(value, dict) and set(value) == {"artifact_id", "revision", "kind", "content_hash"}


def is_resource(value):
    return isinstance(value, dict) and {"path", "sha256", "media_type"} <= set(value)


def ref(value):
    return {k: value[k] for k in ("artifact_id", "revision", "kind", "content_hash")}


def seal(value):
    value["content_hash"] = digest({k: v for k, v in value.items() if k != "content_hash"})
    return value


def obligation(intent):
    p = intent["payload"]
    return "obl-" + digest({"journal_id": p["journal_id"], "target_key": p["target_key"], "intent_ref": ref(intent),
                            "journal_sequence": p["journal_sequence"], "journal_head_hash": p["journal_head_hash"]})


def business(payload, source, bindings=None, projections=None):
    return {"target_key": {"platform_namespace": "a02-mock", "target_id": payload["target_id"], "book_id": "synthetic-book"},
            "source_ref": source, "scope_id": payload["authorized_scope_id"],
            **{k: payload[k] for k in ("platform_version", "capabilities", "directories", "questions", "frames")},
            "internal_bindings": bindings or {}, "frame_projections": projections or {}}


class Revision:
    def __init__(self, output):
        self.output = output
        self.virtual = {}
        self.resource_count = 0

    def write(self, path, value):
        target = self.output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw(value))

    def resource(self, name, value):
        path = "virtual/" + name
        self.virtual[path] = value
        return {"path": path, "sha256": hashlib.sha256(raw(value)).hexdigest(), "media_type": "application/json", "origin": "SYNTHETIC"}

    def read_resource(self, resource):
        path = resource["path"]
        if path in self.virtual:
            return copy.deepcopy(self.virtual[path]), raw(self.virtual[path])
        generated = self.output / path
        data = generated.read_bytes() if generated.is_file() else (OLD / path).read_bytes()
        return (json.loads(data) if resource["media_type"] == "application/json" else None), data

    def repair(self, case):
        artifacts = case["bundle"]["artifacts"]
        known = {(a["artifact_id"], a["revision"]): a for a in artifacts}
        done, busy, resource_busy = set(), set(), set()
        resource_cache = {}
        case_id = case["case_id"]
        evidence = {row["evidence_id"]: row["resource"] for row in case["bundle"]["evidence"]}
        evidence_fields = {"evidence_refs", "before_evidence_refs", "after_evidence_refs", "submission_evidence_refs"}

        def rewrite_resource(node):
            cache_key = (node["path"], node["sha256"], node["media_type"], node.get("origin"))
            if cache_key in resource_cache:
                replacement, refs = resource_cache[cache_key]
                node.update(copy.deepcopy(replacement))
                return copy.deepcopy(refs)
            if cache_key in resource_busy:
                raise ValueError("resource cycle in static input: " + str(cache_key))
            resource_busy.add(cache_key)
            value, before_bytes = self.read_resource(node)
            wrong_hash = hashlib.sha256(before_bytes).hexdigest() != node["sha256"]
            all_refs = []
            if value is not None:
                all_refs = transform(value)
                if isinstance(value, dict) and {"view", "source_ref", "target_state_hash"} <= set(value):
                    view = value["view"]
                    state_hash = digest(business(view["target"], value["source_ref"], view["internal_bindings"], view["frame_projections"]))
                    value["target_state_hash"] = state_hash
                    view["target"]["observed_hash"] = state_hash
                if isinstance(value, dict) and value.get("format_version") == "a03-action-fact-1" and value["intent_ref"] is not None:
                    intent = known.get((value["intent_ref"]["artifact_id"], value["intent_ref"]["revision"]))
                    if intent is not None:
                        value["obligation_id"] = obligation(intent)
                if isinstance(value, dict) and value.get("format_version") == "a03-action-fact-1":
                    value.setdefault("unattempted_basis", None)
                data = raw(value)
                byte_hash = hashlib.sha256(data).hexdigest()
                path = "assets/r1/" + byte_hash + ".json"
                target = self.output / path
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and target.read_bytes() != data:
                    raise ValueError("resource hash collision")
                if not target.exists():
                    target.write_bytes(data)
                    self.resource_count += 1
                node["path"] = path
                if not wrong_hash:
                    node["sha256"] = byte_hash
            resource_busy.remove(cache_key)
            resource_cache[cache_key] = (copy.deepcopy(node), copy.deepcopy(all_refs))
            return all_refs

        def transform(value):
            result = []
            if is_ref(value):
                other = known.get((value["artifact_id"], value["revision"]))
                if other is not None:
                    refresh(other)
                    value.update(ref(other))
                return [copy.deepcopy(value)]
            if is_resource(value):
                return rewrite_resource(value)
            if isinstance(value, dict):
                for name, child in value.items():
                    result += transform(child)
                    if name in evidence_fields and isinstance(child, list):
                        for evidence_id in child:
                            if isinstance(evidence_id, str) and evidence_id in evidence:
                                result += transform(evidence[evidence_id])
            elif isinstance(value, list):
                for child in value:
                    result += transform(child)
            return result

        def refresh(artifact):
            key = (artifact["artifact_id"], artifact["revision"])
            if key in done:
                return
            if key in busy:
                raise ValueError("artifact/resource dependency cycle: " + str(key))
            busy.add(key)
            # Envelope itself is never an ordinary ref: only its fields are visited.
            all_refs = []
            for name, child in artifact.items():
                if name != "content_hash":
                    all_refs += transform(child)
            declared = {encoded(r): r for r in artifact["input_refs"]}
            for r in all_refs:
                declared.setdefault(encoded(r), r)
            artifact["input_refs"] = list(declared.values())
            payload = artifact["payload"]
            if artifact["kind"] == "PlatformSnapshot":
                source_ref = next((r for r in artifact["input_refs"] if r["kind"] == "SourceBundle"), None)
                if source_ref is not None:
                    # Derive binding/projection maps from the matching static observation, where present.
                    obs = observation_by_snapshot.get(artifact["artifact_id"])
                    bindings = obs["view"]["internal_bindings"] if obs else {}
                    projections = obs["view"]["frame_projections"] if obs else {}
                    payload["observed_hash"] = digest(business(payload, source_ref, bindings, projections))
            if artifact["kind"] == "WriteIntent":
                plan = known.get((payload["plan_ref"]["artifact_id"], payload["plan_ref"]["revision"]))
                if plan is not None:
                    pp = plan["payload"]
                    payload["plan_dependency_digest"] = digest({"plan_dependencies_digest": digest({k: pp[k] for k in
                        ("graph", "precheck", "targetcheck", "snapshot", "policy", "execution_mode", "session_mode", "required_capabilities")}),
                        "source_ref": payload["source_ref"], "target_session_id": payload["target_session_id"],
                        "comparator_version": "a02-facts-1", "prepared_before_sha256": payload["prepared_before"]["sha256"]})
            if artifact["kind"] == "ReconciliationResult":
                intent = known.get((payload["intent_ref"]["artifact_id"], payload["intent_ref"]["revision"]))
                if intent is not None and case_id != "wrong-obligation-identity":
                    payload["obligation_id"] = obligation(intent)
                if payload["observed_snapshot_ref"] is not None and case_id != "wrong-observed-state-hash":
                    snap = known.get((payload["observed_snapshot_ref"]["artifact_id"], payload["observed_snapshot_ref"]["revision"]))
                    if snap is not None:
                        payload["target_state_hash"] = snap["payload"]["observed_hash"]
            seal(artifact)
            busy.remove(key)
            done.add(key)

        # Static target views are consulted only to serialize the declared business hash.
        observation_by_snapshot = {}
        for resource in (n for n in walk(case["bundle"]) if is_resource(n) and n["media_type"] == "application/json"):
            value, _ = self.read_resource(resource)
            if isinstance(value, dict) and {"observation_id", "view"} <= set(value):
                snapshot_id = value["observation_id"].replace("observation-", "snapshot-", 1)
                observation_by_snapshot[snapshot_id] = value
        for artifact in artifacts:
            refresh(artifact)
        # Diagnostic export and runtime claims bind the revised graph but grant no authority.
        transform(case["bundle"]["evidence"])
        transform(case["ledger_export"])
        transform(case["runtime_claim"])
        if case["ledger_export"] is not None:
            for row in case["ledger_export"]["unresolved"]:
                if row["intent_ref"] is not None:
                    intent = known.get((row["intent_ref"]["artifact_id"], row["intent_ref"]["revision"]))
                    if intent is not None:
                        row["obligation_id"] = obligation(intent)
        return case


def find(case, kind):
    return next(a for a in case["bundle"]["artifacts"] if a["kind"] == kind)


def partial_revision(revision, case):
    plan = find(case, "ApplyPlan")
    progress = next((a for a in case["bundle"]["artifacts"] if a["kind"] == "ExecutionProgress"), None)
    actions = plan["payload"]["actions"]
    intents = [a for a in case["bundle"]["artifacts"] if a["kind"] == "WriteIntent"]
    unknown_intent = intents[1]
    case["ledger_export"]["unresolved"] = [{"event_id": "event-partial-B-unknown", "obligation_id": obligation(unknown_intent),
        "run_id": unknown_intent["run_id"], "scope_id": unknown_intent["scope_id"], "plan_ref": ref(plan),
        "intent_ref": ref(unknown_intent), "receipt_ref": None, "classification": "UNKNOWN"}]
    case["ledger_export"]["pause"] = {"paused": True, "reason_codes": ["SAVE_UNKNOWN"], "event_ids": ["event-partial-B-unknown"]}
    case["ledger_export"]["pending_action_ids"] = [actions[1]["action_id"]]
    case["runtime_claim"].update(plan_status="INTERRUPTED", old_tail_dispatches=0, original_B_unknown_preserved=True,
        intent_for_tail=False, obligation_for_tail=False, resolution_for_tail=False, actual="NOT_EXECUTED")
    if case["case_id"] == "partial-without-absent":
        return
    resource = progress["payload"]["actions"][2]["result_fact"] if progress is not None else find(case, "ExecutionReceipt")["payload"]["action_fact_refs"][2]
    fact, _ = revision.read_resource(resource)
    request = {"registration_id": "registration-design", "plan_ref": ref(plan), "action_id": actions[2]["action_id"],
        "action_digest": digest(actions[2]), "expected_event_head": {"sequence": 5, "hash": fact["predecessor_hash"]}}
    case["runtime_claim"].update(entry="runtime.storage.commit_unattempted_absence", request=request,
        supplied_owner_id="owner-design", supplied_generation=1, current_owner_id="owner-design", current_generation=1,
        complete_uncalled_prefix=True, independent_absent=True, actual_new_read=True,
        expected_event="UNATTEMPTED_ABSENCE_COMMITTED", expected_fact_origin="UNATTEMPTED_ABSENCE",
        expected_pending_before=["event-partial-B-unknown"], expected_pending_after=["event-partial-B-unknown"],
        expected_target_effects=0, expected_dispatches=0, expected_plan_status="INTERRUPTED")


def upgrade_unattempted_facts(revision, case):
    """Give every new no-intent ABSENT fact its dedicated static two-read origin.

    Old UNKNOWN fact bytes in OLD and in copied archives are never rewritten.
    These new candidate resources are still not committed facts or real reads.
    """
    plan = next((a for a in case["bundle"]["artifacts"] if a["kind"] == "ApplyPlan"), None)
    if plan is None:
        return
    actions = plan["payload"]["actions"]
    fact_resources = {}
    for node in walk(case["bundle"]):
        if is_resource(node) and node["media_type"] == "application/json":
            value, _ = revision.read_resource(node)
            if isinstance(value, dict) and value.get("format_version") == "a03-action-fact-1":
                fact_resources.setdefault(node["path"], (copy.deepcopy(node), value))
    by_action = {value["action_id"]: (resource, value) for resource, value in fact_resources.values()}
    for original, fact in fact_resources.values():
        if fact["intent_ref"] is not None or fact["result"]["attempt_fact"] != "NOT_ATTEMPTED":
            continue
        index = next(i for i, action in enumerate(actions) if action["action_id"] == fact["action_id"])
        action = actions[index]
        old_observation, _ = revision.read_resource(fact["readback"])
        pair_first = 11 if case["case_id"].startswith("partial-") else 2 + 2 * index
        label = "unattempted-" + str(index + 1)
        before_observation = copy.deepcopy(old_observation)
        after_observation = copy.deepcopy(old_observation)
        for observation, phase, seq in ((before_observation, "before", pair_first), (after_observation, "after", pair_first + 1)):
            observation.update(observation_id="observation-" + label + "-" + phase, read_sequence=seq,
                observed_at="2026-10-17T00:00:{:02d}Z".format(seq))
            observation["view"]["target"]["observed_at"] = observation["observed_at"]
        first_read = revision.resource(label + "-first.json", before_observation)
        second_read = revision.resource(label + "-second.json", after_observation)
        prefix = [(r, f) for r, f in by_action.values() if f["result"]["outcome"] == "APPLIED" and
                  next(i for i, a in enumerate(actions) if a["action_id"] == f["action_id"]) < index]
        relevant_before = copy.deepcopy(action["expected_before"])
        # Keep A02 next_order: serialize the fresh actual directory order, never remove it.
        if "next_order" in relevant_before:
            directory = action["expected_after"]["directory_id"]
            orders = [q["platform_order"] for q in before_observation["view"]["target"]["questions"] if q["directory_id"] == directory]
            relevant_before["next_order"] = max(orders, default=0) + 1
        prepared = {"design_only": True, "origin": "SYNTHETIC", "plan_ref": ref(plan),
            "action_id": action["action_id"], "action_digest": digest(action), "target_key": before_observation["target_key"],
            "source_ref": before_observation["source_ref"], "scope_id": plan["scope_id"], "target_session_id": before_observation["target_session_id"],
            "first_observation_ref": first_read, "observation_id": before_observation["observation_id"], "read_sequence": before_observation["read_sequence"],
            "observed_at": before_observation["observed_at"], "target_state_version": before_observation["target_state_version"],
            "target_state_hash": before_observation["target_state_hash"], "view": before_observation["view"], "related_entities_complete": True,
            "relevant_before": relevant_before, "applied_prefix_fact_refs": [r for r, _ in prefix],
            "prior_effect_delta": [{"action_id": f["action_id"], "action_digest": f["action_digest"], "effective_outcome": "APPLIED"} for _, f in prefix],
            "description": "Static dedicated readonly-before from first new observation; independent second readback. Not an actual observer call or commit."}
        prepared_resource = revision.resource(label + "-prepared.json", prepared)
        head_sequence = fact["journal_sequence"] - 1
        events = [{"sequence": 1, "event": "PLAN_REGISTERED", "plan_ref": ref(plan)}]
        for intent in (a for a in case["bundle"]["artifacts"] if a["kind"] == "WriteIntent"):
            if intent["payload"]["journal_sequence"] <= head_sequence:
                events.append({"sequence": intent["payload"]["journal_sequence"], "event": "WRITE_INTENT_COMMITTED",
                    "action_id": intent["payload"]["action_id"], "intent_ref": ref(intent)})
        for _, earlier in by_action.values():
            if earlier["journal_sequence"] <= head_sequence:
                unattempted = earlier["intent_ref"] is None and earlier["result"]["attempt_fact"] == "NOT_ATTEMPTED"
                event = {"sequence": earlier["journal_sequence"], "event": "UNATTEMPTED_ABSENCE_COMMITTED" if unattempted else "ACTION_RESULT_COMMITTED",
                    "action_id": earlier["action_id"], "outcome": earlier["result"]["outcome"]}
                if earlier["result"]["outcome"] == "UNKNOWN":
                    event["plan_status"] = "INTERRUPTED"
                events.append(event)
        events.sort(key=lambda item: item["sequence"])
        if [item["sequence"] for item in events] != list(range(1, head_sequence + 1)):
            raise ValueError("static event prefix has missing/duplicate sequence for " + case["case_id"])
        events[-1]["head_hash"] = fact["predecessor_hash"]
        prefix_resource = revision.resource(label + "-uncalled-prefix.json", {
            "design_only": True, "origin": "SYNTHETIC", "actual": "NOT_EXECUTED",
            "registration_id": "registration-design", "plan_ref": ref(plan), "action_id": action["action_id"],
            "from_sequence": 1, "through_sequence": head_sequence, "complete": True,
            "description": "Candidate complete current-library event prefix: no intent, obligation, resolution, permit or dispatch for this tail action. Hand-authored design data gives no authority.",
            "events": events,
            "intent_ref_for_action": None, "obligation_id_for_action": None, "resolution_ref_for_action": None,
            "dispatch_count_for_action": 0, "permit_count_for_action": 0})
        basis = revision.resource(label + "-basis.json", {
            "format_version": "a03-unattempted-basis-1", "journal_id": "journal-design",
            "design_only": True, "origin": "SYNTHETIC", "actual": "NOT_EXECUTED",
            "target_key": before_observation["target_key"], "target_store_id": "target-store-design",
            "target_session_id": before_observation["target_session_id"],
            "source_ref": before_observation["source_ref"], "scope_id": plan["scope_id"],
            "registration_id": "registration-design", "plan_ref": ref(plan), "action_id": action["action_id"],
            "action_digest": digest(action), "plan_status": "INTERRUPTED", "owner_id": "owner-design", "generation": 1,
            "expected_event_head": {"sequence": head_sequence, "hash": fact["predecessor_hash"]},
            "complete_uncalled_prefix": prefix_resource, "first_observation_ref": first_read,
            "readonly_prepared_ref": prepared_resource, "second_observation_ref": second_read,
            "gate_held": True, "comparison": "ABSENT", "observer_calls": 2, "retries": 0,
            "single_read_seconds": 2, "entry_seconds": 8, "parent_call_seconds": 60})
        template = next(a for a in case["bundle"]["artifacts"] if a["artifact_id"] == fact["observed_snapshot_ref"]["artifact_id"])
        snapshot = copy.deepcopy(template)
        snapshot.update(artifact_id="snapshot-" + label + "-after", created_at=after_observation["observed_at"])
        snapshot["payload"] = copy.deepcopy(after_observation["view"]["target"])
        seal(snapshot)
        case["bundle"]["artifacts"].append(snapshot)
        fact.update(origin_phase="UNATTEMPTED_ABSENCE", intent_ref=None, obligation_id=None, resolution_ref=None,
            prepared_before=prepared_resource, readback=second_read, observed_snapshot_ref=ref(snapshot), unattempted_basis=basis)
        fact["result"].update(intent_ref=None, readback=copy.deepcopy(second_read))
        replacement = revision.resource(label + "-fact.json", fact)
        for node in walk(case["bundle"]):
            if is_resource(node) and node == original:
                node.update(copy.deepcopy(replacement))
        for artifact in case["bundle"]["artifacts"]:
            if artifact["kind"] == "ExecutionReceipt":
                for row in artifact["payload"]["results"]:
                    if row["action_id"] == fact["action_id"]:
                        fabricated = case["case_id"] == "partial-fabricated-receipt" and row["readback"] is None
                        row.update(copy.deepcopy(fact["result"]))
                        if fabricated:
                            row["readback"] = None
        case["runtime_claim"].update(plan_status="INTERRUPTED", old_tail_dispatches=0, original_unknown_preserved=True,
            two_read_design_only=True, actual="NOT_EXECUTED")


def basis_schema():
    fact = load(OLD / "action-fact.schema.json")
    resource = copy.deepcopy(fact["$defs"]["Resource"])
    resource["properties"]["media_type"] = {"const": "application/json"}
    plan_ref = copy.deepcopy(fact["properties"]["plan_ref"])
    source_ref = copy.deepcopy(plan_ref)
    source_ref["properties"]["kind"] = {"const": "SourceBundle"}
    props = {
        "format_version": {"const": "a03-unattempted-basis-1"},
        "design_only": {"type": "boolean"}, "origin": {"const": "SYNTHETIC"}, "actual": {"type": "string"},
        "plan_ref": plan_ref, "source_ref": source_ref, "target_key": {"$ref": "recovery-exchange.schema.json#/$defs/TargetKey"},
        "plan_status": {"const": "INTERRUPTED"}, "generation": {"type": "integer", "minimum": 1},
        "action_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "expected_event_head": {"type": "object", "additionalProperties": False,
            "properties": {"sequence": {"type": "integer", "minimum": 1}, "hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"}},
            "required": ["sequence", "hash"]},
        "gate_held": {"const": True}, "comparison": {"const": "ABSENT"}, "observer_calls": {"const": 2}, "retries": {"const": 0},
        "single_read_seconds": {"const": 2}, "entry_seconds": {"const": 8}, "parent_call_seconds": {"const": 60}}
    for name in ("journal_id", "registration_id", "action_id", "owner_id", "target_store_id", "target_session_id", "scope_id"):
        props[name] = {"type": "string", "minLength": 1}
    for name in ("complete_uncalled_prefix", "first_observation_ref", "readonly_prepared_ref", "second_observation_ref"):
        props[name] = {"$ref": "#/$defs/JsonResource"}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "a03-unattempted-basis-P1-R1-design",
        "title": "P1-R1 DESIGN_ONLY non-Artifact basis Resource", "$comment": "Field/byte equality only. This JSON never establishes current gate/owner/ledger authority, actual new reads or committed facts.",
        "type": "object", "additionalProperties": False, "properties": props,
        "required": [name for name in props if name not in {"design_only", "actual"}], "$defs": {"JsonResource": resource}}


def write_resource(revision, value):
    data = raw(value)
    byte_hash = hashlib.sha256(data).hexdigest()
    path = "assets/r1/" + byte_hash + ".json"
    revision.write(path, value)
    return {"path": path, "sha256": byte_hash, "media_type": "application/json", "origin": "SYNTHETIC"}


def reseal_reports(case):
    """Rebind report envelopes only after a local static probe mutation.

    No intent/plan is altered here; resource-internal malicious refs remain as
    deliberately authored. Receipt, postcheck and batch report hashes form a DAG.
    """
    known = {(a["artifact_id"], a["revision"]): a for a in case["bundle"]["artifacts"]}
    done, busy = set(), set()
    def refresh(a):
        key = (a["artifact_id"], a["revision"])
        if key in done:
            return
        if key in busy:
            return  # Deliberate cycle probes are not solved as hash fixed points.
        busy.add(key)
        for child in walk({k: v for k, v in a.items() if k != "content_hash"}):
            if is_ref(child):
                other = known.get((child["artifact_id"], child["revision"]))
                if other is not None:
                    refresh(other)
                    child.update(ref(other))
        seal(a)
        busy.remove(key)
        done.add(key)
    for artifact in known.values():
        refresh(artifact)


def add_closure_probes(revision, repaired, manifest):
    """Neighbor fixtures for the two R1 design gaps; no runtime is invoked."""
    def append(case, case_id, static, code, note):
        case["case_id"] = case_id
        revision.write("cases/" + case_id + ".json", case)
        manifest["cases"].append({"case_id": case_id, "path": "cases/" + case_id + ".json", "expected_layer": "STRUCTURE" if static == "STRUCTURE_FAIL" else ("REFERENCE" if static != "PASS" else "STATIC_REFERENCE_CLOSURE"),
            "expected_code": code, "expected_static": static, "semantic_execution": "EXPECTED_NOT_EXECUTED", "note": note})

    def fact_and_prepared(case):
        receipt = find(case, "ExecutionReceipt")
        fact_ref = receipt["payload"]["action_fact_refs"][0]
        fact = load(revision.output / fact_ref["path"])
        prepared = load(revision.output / fact["prepared_before"]["path"])
        return receipt, fact, prepared

    def replace_prepared(case, receipt, fact, prepared):
        fact["prepared_before"] = write_resource(revision, prepared)
        receipt["payload"]["action_fact_refs"][0] = write_resource(revision, fact)
        reseal_reports(case)

    case = copy.deepcopy(repaired["normal"])
    receipt = find(case, "ExecutionReceipt")
    receipt["input_refs"] = [r for r in receipt["input_refs"] if r["artifact_id"] != "snapshot-action-result-1"]
    reseal_reports(case)
    append(case, "resource-fact-missing-declaration", "REFERENCE_FAIL", "UNDECLARED_RESOURCE_REFERENCE", "Immutable fact remains present; remove only receipt declaration for its observed snapshot.")

    case = copy.deepcopy(repaired["normal"])
    progress = find(case, "ExecutionProgress")
    progress["input_refs"] = [r for r in progress["input_refs"] if r["artifact_id"] != "snapshot-action-result-1"]
    reseal_reports(case)
    append(case, "shared-resource-second-consumer-missing", "REFERENCE_FAIL", "UNDECLARED_RESOURCE_REFERENCE", "Receipt consumes and declares the same fact first; progress still must independently declare its nested snapshot. A shared parsed-resource cache cannot grant declaration.")

    case = copy.deepcopy(repaired["normal"])
    receipt = find(case, "ExecutionReceipt")
    receipt["input_refs"] = [r for r in receipt["input_refs"] if r["kind"] != "SourceBundle"]
    reseal_reports(case)
    append(case, "nested-prepared-missing-declaration", "REFERENCE_FAIL", "UNDECLARED_RESOURCE_REFERENCE", "Fact -> prepared JSON -> SourceBundle exact ref remains; remove only this consumer's SourceBundle declaration.")

    for flavor in ("positive", "wrong-ref-hash", "cross-book", "cross-scope", "wrong-resource-hash"):
        case = copy.deepcopy(repaired["normal"])
        receipt, fact, prepared = fact_and_prepared(case)
        if flavor == "wrong-ref-hash":
            prepared["source_ref"]["content_hash"] = ZERO
        elif flavor in {"cross-book", "cross-scope"}:
            foreign = copy.deepcopy(find(case, "SourceBundle"))
            foreign["artifact_id"] = "foreign-source-probe"
            foreign["book_id" if flavor == "cross-book" else "scope_id"] = "different-" + flavor
            seal(foreign)
            case["bundle"]["artifacts"].append(foreign)
            prepared["source_ref"] = ref(foreign)
            receipt["input_refs"].append(ref(foreign))
        elif flavor == "positive":
            prepared["nested_reference_probe"] = {"ordinary_ref": copy.deepcopy(prepared["source_ref"])}
        if flavor == "wrong-resource-hash":
            fact["prepared_before"]["sha256"] = ZERO
            receipt["payload"]["action_fact_refs"][0] = write_resource(revision, fact)
            reseal_reports(case)
        else:
            replace_prepared(case, receipt, fact, prepared)
        expected = "PASS" if flavor == "positive" else ("RESOURCE_FAIL" if flavor == "wrong-resource-hash" else "REFERENCE_FAIL")
        code = {"positive": "RECURSIVE_DECLARATION_CLOSED", "wrong-ref-hash": "REFERENCE_HASH_MISMATCH", "cross-book": "REFERENCE_SCOPE_MISMATCH",
            "cross-scope": "REFERENCE_SCOPE_MISMATCH", "wrong-resource-hash": "RESOURCE_HASH_MISMATCH"}[flavor]
        append(case, "nested-prepared-" + flavor, expected, code, "Nested resource neighbor: all surrounding normal facts stay present; only the stated prepared resource field changes. Ref lookup alone is insufficient.")

    case = copy.deepcopy(repaired["normal"])
    receipt, fact, prepared = fact_and_prepared(case)
    prepared["mixed_cycle_probe"] = ref(receipt)
    replace_prepared(case, receipt, fact, prepared)
    append(case, "mixed-artifact-resource-cycle", "REFERENCE_FAIL", "REFERENCE_CYCLE", "Receipt -> fact Resource -> prepared Resource -> receipt identity cycle. Reject graph before impossible hash fixed-point checks.")

    case = copy.deepcopy(repaired["normal"])
    receipt, fact, prepared = fact_and_prepared(case)
    a = {"path": "assets/resource-cycle-a.json", "sha256": ZERO, "media_type": "application/json", "origin": "SYNTHETIC"}
    b = {"path": "assets/resource-cycle-b.json", "sha256": ZERO, "media_type": "application/json", "origin": "SYNTHETIC"}
    revision.write(a["path"], {"design_only": True, "nested": b})
    revision.write(b["path"], {"design_only": True, "nested": a})
    prepared["resource_cycle_probe"] = a
    replace_prepared(case, receipt, fact, prepared)
    append(case, "nested-resource-cycle", "RESOURCE_FAIL", "RESOURCE_HASH_MISMATCH", "JSON Resource A -> B -> A has no valid finite content-hash fixed point. Verify bytes before parsing, so this invalid-byte fixture is rejected at the earlier hash gate; the checker also rejects resource cycles after valid byte verification.")

    case = copy.deepcopy(repaired["normal"])
    receipt, fact, prepared = fact_and_prepared(case)
    fact["prepared_before"]["path"] = "../P1/assets/prepared-before-1.json"
    receipt["payload"]["action_fact_refs"][0] = write_resource(revision, fact)
    reseal_reports(case)
    append(case, "nested-resource-nonportable-path", "RESOURCE_FAIL", "NONPORTABLE_RESOURCE_PATH", "Reject escaping nested resource path before accessing it. The fixture is fully portable and never follows this path.")

    for missing in (False, True):
        case = copy.deepcopy(repaired["normal"])
        receipt, fact, _ = fact_and_prepared(case)
        snapshot = copy.deepcopy(next(a for a in case["bundle"]["artifacts"] if a["artifact_id"] == "snapshot-action-result-1"))
        snapshot["artifact_id"] = "evidence-only-snapshot"
        seal(snapshot)
        case["bundle"]["artifacts"].append(snapshot)
        evidence_resource = write_resource(revision, {"design_only": True, "ordinary_ref": ref(snapshot)})
        case["bundle"]["evidence"].append({"evidence_id": "proof-r1-extra", "resource": evidence_resource,
            "description": "Formal EvidenceRecord ID resolves to a JSON Resource with an ordinary dependency.", "mode": "SYNTHETIC"})
        fact["result"]["before_evidence_refs"].append("proof-r1-extra")
        receipt["payload"]["results"][0]["before_evidence_refs"].append("proof-r1-extra")
        receipt["payload"]["action_fact_refs"][0] = write_resource(revision, fact)
        if not missing:
            receipt["input_refs"].append(ref(snapshot))
        reseal_reports(case)
        append(case, "evidence-id-resource-" + ("missing-declaration" if missing else "closed"), "REFERENCE_FAIL" if missing else "PASS",
            "UNDECLARED_RESOURCE_REFERENCE" if missing else "RECURSIVE_DECLARATION_CLOSED",
            "Resolve only the formal before_evidence_refs ID via this bundle's unique EvidenceRecord table; then expand its resource as the receipt consumer.")

    for mutation in ("tail-missing-basis", "execution-with-basis"):
        case = copy.deepcopy(repaired["partial-with-complete-absent"])
        receipt = find(case, "ExecutionReceipt")
        fact = load(revision.output / receipt["payload"]["action_fact_refs"][2]["path"])
        if mutation == "tail-missing-basis":
            fact["unattempted_basis"] = None
        else:
            fact["origin_phase"] = "EXECUTION"
        new_fact = write_resource(revision, fact)
        receipt["payload"]["action_fact_refs"][2] = copy.deepcopy(new_fact)
        find(case, "ExecutionProgress")["payload"]["actions"][2]["result_fact"] = copy.deepcopy(new_fact)
        reseal_reports(case)
        append(case, "unattempted-schema-" + mutation, "STRUCTURE_FAIL", "UNATTEMPTED_BASIS_ORIGIN_MISMATCH", "Schema branches require a nonnull basis only for UNATTEMPTED_ABSENCE; all other origins require null. No runtime origin validation is executed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if HERE not in output.parents or output.exists():
        raise SystemExit("output must be a new nonexistent child of examples/a03/P1-R1")
    output.mkdir(parents=True)
    revision = Revision(output)
    for path in OLD.iterdir():
        if path.name in {"archive", "assets"}:
            if path.name == "archive":
                shutil.copytree(path, output / path.name)
            else:
                for asset in path.iterdir():
                    if asset.suffix != ".json":
                        target = output / "assets" / asset.name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(asset, target)
        elif path.name.endswith(".schema.json"):
            value = load(path)
            value["$comment"] = value.get("$comment", "") + " P1-R1 DESIGN_ONLY revision; NOT IMPLEMENTED."
            if path.name == "action-fact.schema.json":
                value["properties"]["origin_phase"]["enum"].append("UNATTEMPTED_ABSENCE")
                value["properties"]["unattempted_basis"] = {"anyOf": [{"$ref": "#/$defs/Resource"}, {"type": "null"}]}
                value["required"].append("unattempted_basis")
                value["$comment"] += " UNATTEMPTED_ABSENCE uses only commit_unattempted_absence / UNATTEMPTED_ABSENCE_COMMITTED: INTERRUPTED plan, no intent/obligation/resolution, independently fresh sufficient ABSENT and complete uncalled event prefix; never dispatch or clear other pending."
                variants = []
                for phase in ("EXECUTION", "RECOVERY", "UNATTEMPTED_ABSENCE"):
                    branch = {k: copy.deepcopy(value[k]) for k in ("type", "additionalProperties", "properties", "required")}
                    branch["properties"]["origin_phase"] = {"const": phase}
                    branch["properties"]["unattempted_basis"] = {"$ref": "#/$defs/Resource"} if phase == "UNATTEMPTED_ABSENCE" else {"type": "null"}
                    if phase == "UNATTEMPTED_ABSENCE":
                        for nullable in ("intent_ref", "obligation_id", "resolution_ref"):
                            branch["properties"][nullable] = {"type": "null"}
                        branch["properties"]["result"] = copy.deepcopy(value["$defs"]["ActionResult"])
                        result = branch["properties"]["result"]["properties"]
                        result.update(attempt_fact={"const": "NOT_ATTEMPTED"}, outcome={"const": "NOT_APPLIED"},
                            effect_match={"const": "ABSENT"}, intent_ref={"type": "null"}, replay_allowed={"const": False})
                    variants.append(branch)
                value["oneOf"] = variants
            revision.write(path.name, value)
    revision.write("unattempted-basis.schema.json", basis_schema())
    old_manifest = load(OLD / "case-manifest.json")
    manifest = copy.deepcopy(old_manifest)
    manifest.update(candidate_revision="P1-R1", baseline_commit="2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9", ordinary_resource_closure_required=True)
    manifest["static_check_scope"] += ["RECURSIVE_RESOURCE_REFERENCE_DECLARATIONS", "RESOURCE_REFERENCE_DAG"]
    repaired = {}
    mapping = []
    for row in manifest["cases"]:
        case = load(OLD / row["path"])
        # The deliberate old self-cycle is injected after repairing the acyclic graph.
        cycle = case["case_id"] == "resolution-cycle"
        if cycle:
            target = find(case, "ReconciliationResult")
            target["payload"]["previous_resolution_ref"] = None
            target["input_refs"] = [r for r in target["input_refs"] if r["artifact_id"] != target["artifact_id"]]
        if case["case_id"] in {"partial-without-absent", "partial-with-complete-absent", "partial-fabricated-receipt"}:
            partial_revision(revision, case)
        upgrade_unattempted_facts(revision, case)
        revision.repair(case)
        if cycle:
            target["payload"]["previous_resolution_ref"] = ref(target)
            target["input_refs"].append(ref(target))
            seal(target)
        repaired[case["case_id"]] = case
        revision.write(row["path"], case)
        row["source_P1_case_id"] = row["case_id"]
        mapping.append({"old_case_id": row["case_id"], "old_path": row["path"],
            "old_sha256": hashlib.sha256((OLD / row["path"]).read_bytes()).hexdigest(), "r1_case_id": row["case_id"],
            "r1_path": row["path"], "r1_sha256": hashlib.sha256((output / row["path"]).read_bytes()).hexdigest(),
            "coverage_retained": True, "expected_layer": row["expected_layer"], "expected_code": row["expected_code"]})
    revision.write("case-mapping.json", {"design_only": True, "candidate_revision": "P1-R1", "original_case_count": 42, "mappings": mapping})
    migration = load(OLD / "migration-map.json")
    normal = repaired["normal"]
    for row in migration["mappings"]:
        artifact = next(a for a in normal["bundle"]["artifacts"] if a["artifact_id"] == row["new"]["artifact_id"])
        row["new"] = ref(artifact)
        row["old_namespace"] = "schema:1.0.0-a-proposal/exchange:c01-exchange-1"
        row["new_namespace"] = "schema:1.1.0-a-recovery-proposal/exchange:a03-exchange-1"
    migration.update(candidate_revision="P1-R1", identity_meaning="Identity is namespace plus book_id/scope_id/artifact_id/revision; kind and content_hash are a unique immutable binding. Same local ID across old/new namespaces is not the same persisted identity. Never overwrite the same identity with another kind or digest.",
        namespace_fields=["schema_version", "exchange_version"],
        future_index_key=["namespace", "book_id", "scope_id", "artifact_id", "revision"],
        namespace_conflict="reject different kind or digest for the same namespace/book_id/scope_id/artifact_id/revision")
    revision.write("migration-map.json", migration)
    # New semantic API cases retain valid repaired data. Claims are expectations only.
    api_cases = [
        ("unattempted-absence-commit", "UNATTEMPTED_ABSENCE_COMMITTED", {}),
        ("unattempted-missing-absent", "CONCLUSIVE_READBACK_REQUIRED", {"independent_absent": False}),
        ("unattempted-stale-observation", "OBSERVATION_NOT_FRESH", {"actual_new_read": False}),
        ("unattempted-incomplete-prefix", "EVENT_PREFIX_INCOMPLETE", {"complete_uncalled_prefix": False}),
        ("unattempted-wrong-plan-action", "PLAN_ACTION_MISMATCH", {"requested_action_belongs_to_plan": False}),
        ("unattempted-stale-generation", "OWNER_GENERATION_STALE", {"supplied_generation": 0}),
        ("unattempted-duplicate-fact", "UNATTEMPTED_FACT_DUPLICATE", {"same_committed_fact": True, "expected_new_events": 0}),
        ("unattempted-conflicting-fact", "UNATTEMPTED_FACT_CONFLICT", {"different_existing_fact": True})]
    api_cases += [
        ("unattempted-wrong-plan-state", "PLAN_STATE_INVALID", {"current_plan_status": "RUNNING"}),
        ("unattempted-already-called", "ACTION_ALREADY_ATTEMPTED", {"current_action_dispatch_count": 1}),
        ("unattempted-event-head-stale", "EVENT_HEAD_CAS_MISMATCH", {"current_event_head": {"sequence": 6, "hash": ZERO}}),
        ("unattempted-prepared-mismatch", "PREPARED_BEFORE_MISMATCH", {"readonly_prepared_action_id": "different-action"})]
    for case_id, code, claims in api_cases:
        case = copy.deepcopy(repaired["partial-with-complete-absent"])
        case["case_id"] = case_id
        case["runtime_claim"].update(claims)
        receipt = find(case, "ExecutionReceipt")
        fact = load(output / receipt["payload"]["action_fact_refs"][2]["path"])
        basis = load(output / fact["unattempted_basis"]["path"])
        if case_id == "unattempted-wrong-plan-action":
            case["runtime_claim"]["request"]["action_id"] = "action-not-in-registered-plan"
        elif case_id == "unattempted-missing-absent":
            observation = load(output / basis["second_observation_ref"]["path"])
            observation["scope_complete"] = False
            for item in observation.get("action_facts", []):
                if item["action_id"] == fact["action_id"]:
                    item["related_scope_complete"] = False
                    item["design_observation"] = "INDETERMINATE"
            case["runtime_claim"]["candidate_second_observation"] = write_resource(revision, observation)
        elif case_id == "unattempted-stale-observation":
            case["runtime_claim"]["candidate_second_observation"] = copy.deepcopy(basis["first_observation_ref"])
        elif case_id == "unattempted-incomplete-prefix":
            prefix = load(output / basis["complete_uncalled_prefix"]["path"])
            prefix["events"] = prefix["events"][1:]
            prefix["from_sequence"] = 2
            prefix["complete"] = False
            case["runtime_claim"]["candidate_uncalled_prefix"] = write_resource(revision, prefix)
        elif case_id == "unattempted-prepared-mismatch":
            prepared = load(output / basis["readonly_prepared_ref"]["path"])
            prepared["action_id"] = "different-action"
            case["runtime_claim"]["candidate_readonly_prepared"] = write_resource(revision, prepared)
        elif case_id in {"unattempted-duplicate-fact", "unattempted-conflicting-fact"}:
            case["runtime_claim"]["current_library_existing_fact_binding"] = {"journal_id": basis["journal_id"],
                "target_key": basis["target_key"], "action_id": fact["action_id"], "plan_ref": copy.deepcopy(fact["plan_ref"]),
                "action_digest": fact["action_digest"], "committed_fact": copy.deepcopy(receipt["payload"]["action_fact_refs"][2])}
            if case_id == "unattempted-conflicting-fact":
                case["runtime_claim"]["current_library_existing_fact_binding"]["action_digest"] = ZERO
        revision.write("cases/" + case_id + ".json", case)
        manifest["cases"].append({"case_id": case_id, "path": "cases/" + case_id + ".json", "expected_layer": "RUNTIME_TRANSACTION",
            "expected_code": code, "expected_static": "PASS", "semantic_execution": "EXPECTED_NOT_EXECUTED", "note": "P1-R1 API design input only; no call, target read, transaction or refusal occurred."})
    add_closure_probes(revision, repaired, manifest)
    revision.write("case-manifest.json", manifest)
    print(json.dumps({"design_only": True, "candidate_revision": "P1-R1", "cases": len(manifest["cases"]), "new_json_resources": revision.resource_count,
        "original_cases_mapped": 42, "runtime_or_recovery_executed": False, "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
