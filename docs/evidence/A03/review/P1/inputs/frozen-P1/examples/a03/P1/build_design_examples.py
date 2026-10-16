"""DESIGN_ONLY: generate static P1 schemas/examples; never execute A03/A02 recovery.

Reads only the public existing schema() and the named archived SYNTHETIC bundle.
Writes new files under an explicitly chosen empty output directory. No runtime,
mock, validator, browser, network, SQLite, credential or model entry is called.
"""
import argparse
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "1.1.0-a-recovery-proposal"
EXCHANGE = "a03-exchange-1"
NOW = "2026-10-17T00:00:00Z"
ZERO = "0" * 64


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode("utf-8")).hexdigest()


def at(seconds):
    return (datetime(2026, 10, 17, tzinfo=timezone.utc) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def business_state(payload, source_reference, bindings=None, projections=None):
    """Static serialization shape shared by the API proposal, not a comparator."""
    return {"target_key": {"platform_namespace": "a02-mock", "target_id": payload["target_id"], "book_id": "synthetic-book"},
            "source_ref": source_reference, "scope_id": payload["authorized_scope_id"],
            **{k: payload[k] for k in ("platform_version", "capabilities", "directories", "questions", "frames")},
            "internal_bindings": bindings or {}, "frame_projections": projections or {}}


def obligation(intent):
    p = intent["payload"]
    return "obl-" + digest({"journal_id": p["journal_id"], "target_key": p["target_key"], "intent_ref": ref(intent),
                             "journal_sequence": p["journal_sequence"], "journal_head_hash": p["journal_head_hash"]})


def seal(value):
    value["content_hash"] = digest({k: v for k, v in value.items() if k != "content_hash"})
    return value


def ref(value):
    return {k: value[k] for k in ("artifact_id", "revision", "kind", "content_hash")}


def walk(value):
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def obj(properties):
    return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}


def arr(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


def nullable(item):
    return {"anyOf": [item, {"type": "null"}]}


def enum(*values):
    return {"type": "string", "enum": list(values)}


def schemas(old_schema):
    schema = copy.deepcopy(old_schema)
    schema.update({"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "recovery-exchange.schema.json",
                   "title": "DESIGN_ONLY A03 candidate production shape; NOT IMPLEMENTED",
                   "$comment": "P1 static proposal. Passing structure is not eligibility or local intent-commit evidence."})
    defs = schema["$defs"]
    identifier = {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.:-]{0,127}$"}
    external = {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"}
    hash_ = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    string = {"type": "string", "minLength": 1}
    timestamp = {"type": "string", "format": "date-time"}
    positive = {"type": "integer", "minimum": 1}
    resource = {"$ref": "#/$defs/Resource"}
    aref = {"$ref": "#/$defs/ArtifactRef"}

    def typed(kind):
        value = copy.deepcopy(defs["ArtifactRef"])
        value["properties"]["kind"] = {"const": kind, "type": "string"}
        return value

    kinds = list(defs["ArtifactRef"]["properties"]["kind"]["enum"])
    kinds += ["WriteIntent", "ExecutionProgress", "ReconciliationResult"]
    defs["ArtifactRef"]["properties"]["kind"]["enum"] = kinds
    for name in kinds:
        if name in defs:
            defs[name]["properties"]["schema_version"] = {"const": VERSION, "type": "string"}
    for name in ("Resource", "Asset"):
        defs[name]["properties"]["origin"] = enum("SYNTHETIC", "ORIGINAL", "OBSERVED")
        defs[name]["required"].append("origin")
    defs["ScopeIntegrity"] = obj({"status": enum("UNKNOWN", "REFERENCE_ONLY", "INDEPENDENT_COMPLETE", "SYNTHETIC_COMPLETE"),
                                  "basis": enum("UNKNOWN", "METADATA", "HISTORICAL_REFERENCE", "PLATFORM_RECORDS", "INDEPENDENT_SCOPE_REVIEW", "INDEPENDENT_SCOPE_SCAN", "FIXTURE"),
                                  "proof": nullable(resource)})
    defs["SourcePayload"]["properties"]["scope_integrity"] = {"$ref": "#/$defs/ScopeIntegrity"}
    defs["SourcePayload"]["required"].append("scope_integrity")
    defs["SourcePayload"]["properties"]["scope_manifest"] = nullable(arr(identifier))
    defs["CheckPayload"]["properties"]["recovery_refs"] = arr(typed("ReconciliationResult"))
    defs["CheckPayload"]["required"].append("recovery_refs")
    for name, kind in (("recovery_refs", "ReconciliationResult"), ("progress_refs", "ExecutionProgress")):
        defs["BatchPayload"]["properties"][name] = arr(typed(kind))
        defs["BatchPayload"]["required"].append(name)
    attempt = enum("NOT_ATTEMPTED", "MAY_HAVE_BEEN_ATTEMPTED", "ATTEMPTED", "LEGACY_UNRECORDED")
    for name, spec in (("attempt_fact", attempt), ("attempt_evidence_refs", arr(resource)), ("intent_ref", nullable(typed("WriteIntent")))):
        defs["ActionResult"]["properties"][name] = spec
        defs["ActionResult"]["required"].append(name)
    defs["ReceiptPayload"]["properties"]["action_fact_refs"] = arr(resource)
    defs["ReceiptPayload"]["required"].append("action_fact_refs")
    defs["TargetKey"] = obj({"platform_namespace": identifier, "target_id": external, "book_id": external})
    defs["WriteIntentPayload"] = obj({"plan_ref": typed("ApplyPlan"), "action_id": identifier, "action_digest": hash_,
        "target_key": {"$ref": "#/$defs/TargetKey"}, "question_id": identifier, "source_entity_ids": arr(identifier, 1),
        "target_session_id": identifier, "source_ref": typed("SourceBundle"), "prepared_before": resource,
        "before_snapshot_ref": typed("PlatformSnapshot"), "execution_mode": {"const": "SIMULATED"},
        "journal_id": identifier, "journal_sequence": positive, "journal_head_hash": hash_, "owner_id": identifier,
        "generation": positive, "intent_committed_at": timestamp, "plan_dependency_digest": hash_})
    defs["WriteIntentPayload"]["$comment"] = "NOT IMPLEMENTED. H=SHA256 of UTF8 canonical JSON(sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False). action_digest=H(complete Action). plan_dependency_digest=H({plan_dependencies_digest:H({graph,precheck,targetcheck,snapshot,policy,execution_mode,session_mode,required_capabilities}),source_ref,target_session_id,comparator_version:'a02-facts-1',prepared_before_sha256}). journal_head_hash is the transaction predecessor hash, not a self-inclusive head. Only a current-library actual durable local transaction gives a WriteIntent qualification."
    defs["ProgressAction"] = obj({"action_id": identifier, "intent_ref": nullable(typed("WriteIntent")),
        "attempt_fact": attempt, "dependency_status": enum("READY", "BLOCKED", "SATISFIED"),
        "attempt_evidence_refs": arr(resource), "receipt_ref": nullable(typed("ExecutionReceipt")),
        "resolution_head_ref": nullable(typed("ReconciliationResult")),
        "result_fact": nullable(resource),
        "effective_outcome": enum("APPLIED", "NOT_APPLIED", "UNKNOWN", "UNDETERMINED")})
    defs["ExecutionProgressPayload"] = obj({"plan_ref": typed("ApplyPlan"), "journal_id": identifier,
        "journal_head_sequence": positive, "journal_head_hash": hash_, "actions": arr({"$ref": "#/$defs/ProgressAction"}, 1)})
    defs["ReconciliationResultPayload"] = obj({"plan_ref": typed("ApplyPlan"), "intent_ref": typed("WriteIntent"),
        "obligation_id": identifier,
        "action_id": identifier, "action_digest": hash_, "original_receipt_ref": nullable(typed("ExecutionReceipt")),
        "previous_resolution_ref": nullable(typed("ReconciliationResult")), "observed_snapshot_ref": nullable(typed("PlatformSnapshot")),
        "observation_id": identifier, "recovery_call_id": identifier, "attempt_index": {"type": "integer", "minimum": 1, "maximum": 3},
        "observed_at": timestamp, "read_sequence": nullable(positive), "target_state_version": nullable(string), "target_state_hash": nullable(hash_),
        "observation": enum("MATCH", "ABSENT", "CONFLICT", "INDETERMINATE"),
        "resolution": enum("RESOLVED_APPLIED", "RESOLVED_NOT_APPLIED", "STILL_UNKNOWN"), "platform_ids": arr(string),
        "evidence_refs": arr(resource), "readback": nullable(resource), "comparator_version": {"const": "a02-facts-1"},
        "reason_code": string, "replay_allowed": {"const": False}})
    for kind in kinds[-3:]:
        envelope = copy.deepcopy(defs["SourceBundle"])
        envelope["title"] = kind
        envelope["properties"]["kind"] = {"const": kind, "type": "string"}
        envelope["properties"]["payload"] = {"$ref": "#/$defs/" + kind + "Payload"}
        defs[kind] = envelope
    artifact_union = schema["properties"]["artifacts"]["items"]
    artifact_union["oneOf"] = [{"$ref": "#/$defs/" + kind} for kind in kinds]
    artifact_union["discriminator"]["mapping"] = {kind: "#/$defs/" + kind for kind in kinds}
    schema["properties"]["format_version"] = {"const": EXCHANGE, "type": "string"}

    # A separate diagnostic export: its refs do not broaden ordinary artifact scope.
    ldefs = copy.deepcopy(defs)
    ledger = obj({"format_version": {"const": "a03-ledger-export-1"},
        "ledger_id": identifier, "db_version": {"const": "a03-runtime-db-1"}, "book_key": {"$ref": "#/$defs/TargetKey"},
        "owner_id": nullable(identifier), "generation": positive, "event_head_sequence": positive, "event_head_hash": hash_,
        "scopes": arr(obj({"scope_id": identifier, "source_ref": typed("SourceBundle"), "target_session_id": nullable(identifier), "archive_refs": arr(resource)}), 1),
        "unresolved": arr(obj({"event_id": identifier, "obligation_id": identifier, "run_id": identifier, "scope_id": identifier,
            "plan_ref": typed("ApplyPlan"), "intent_ref": nullable(typed("WriteIntent")), "receipt_ref": nullable(typed("ExecutionReceipt")),
            "classification": enum("UNKNOWN", "LEGACY_UNRECORDED")})),
        "artifact_history": arr(aref), "pending_action_ids": arr(identifier),
        "external_ids": arr(obj({"question_id": identifier, "platform_question_id": string, "platform_frame_ids": arr(string)})),
        "pause": obj({"paused": {"type": "boolean"}, "reason_codes": arr(string), "event_ids": arr(identifier)}),
        "state_directory_identity": identifier, "target_store_identity": identifier, "diagnostic_only": {"const": True}})
    ledger.update({"$schema": schema["$schema"], "$id": "ledger-export.schema.json", "$defs": ldefs,
                   "title": "DESIGN_ONLY diagnostic book ledger, NOT a permit or ArtifactRef",
                   "$comment": "NOT IMPLEMENTED. P1 instances are marked by their case wrapper. sqlite descriptor a03-runtime-db-1: PRAGMA user_version=1; PRAGMA application_id=0x41303352. This diagnostic JSON is never a live permit."})
    case = obj({"design_only": {"const": True}, "case_id": identifier, "bundle": {"$ref": "recovery-exchange.schema.json"},
                "ledger_export": nullable({"$ref": "ledger-export.schema.json"}), "runtime_claim": {"type": "object"}})
    case.update({"$schema": schema["$schema"], "$id": "case-file.schema.json", "title": "DESIGN_ONLY example wrapper; not consumed by production"})
    return schema, ledger, case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE)
    parser.add_argument("--replace-draft", action="store_true", help="Replace only this generator's unfrozen static drafts; never use on delivered evidence")
    args = parser.parse_args()
    out = args.output.resolve()
    if out != HERE and HERE not in out.parents:
        raise SystemExit("output must remain under examples/a03/P1")
    out.mkdir(parents=True, exist_ok=True)

    def write(path, value):
        path = out / path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w" if args.replace_draft else "x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")

    sys.path.insert(0, str(ROOT / "src"))
    from annotation.contracts import schema as old_schema  # Read-only public export only.
    archived_schema = old_schema()
    archived_schema["$comment"] = "DESIGN_ONLY static public schema export from ec1b4def; archive read shape only, no new recovery eligibility."
    write("archive-v1.schema.json", archived_schema)
    candidate, ledger_schema, case_schema = schemas(old_schema())
    write("recovery-exchange.schema.json", candidate)
    write("ledger-export.schema.json", ledger_schema)
    write("case-file.schema.json", case_schema)
    cdefs = candidate["$defs"]
    action_fact_schema = obj({"format_version": {"const": "a03-action-fact-1"}, "plan_ref": copy.deepcopy(cdefs["WriteIntentPayload"]["properties"]["plan_ref"]),
        "origin_phase": enum("EXECUTION", "RECOVERY"), "resolution_ref": copy.deepcopy(cdefs["ReconciliationResultPayload"]["properties"]["previous_resolution_ref"]),
        "intent_ref": copy.deepcopy(cdefs["ActionResult"]["properties"]["intent_ref"]), "obligation_id": nullable({"type": "string", "minLength": 1}),
        "action_id": copy.deepcopy(cdefs["ActionResult"]["properties"]["action_id"]), "action_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "prepared_before": {"$ref": "#/$defs/Resource"}, "observed_snapshot_ref": copy.deepcopy(cdefs["ReconciliationResultPayload"]["properties"]["observed_snapshot_ref"]),
        "readback": nullable({"$ref": "#/$defs/Resource"}), "comparator_version": {"const": "a02-facts-1"},
        "result": {"$ref": "#/$defs/ActionResult"}, "journal_sequence": {"type": "integer", "minimum": 1},
        "predecessor_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"}})
    action_fact_schema["properties"]["design_only"] = {"type": "boolean"}
    action_fact_schema.update({"$schema": candidate["$schema"], "$id": "action-fact.schema.json", "$defs": {k: copy.deepcopy(cdefs[k]) for k in ("Resource", "ActionResult")},
        "title": "DESIGN_ONLY candidate a03-action-fact-1 event resource; NOT a fourth Artifact kind",
        "$comment": "Only an actual runtime ACTION_RESULT_COMMITTED event after independent read/comparison can discharge a normal conclusive intent. EXECUTION requires null resolution_ref. RECOVERY requires an exact committed resolution_ref and RECONCILIATION_COMMITTED event, preserving original attempt_fact while reporting the new effective outcome; never send it to the original run normal result entry. Original UNKNOWN files remain unchanged. This static file is not commit evidence. Optional design_only metadata annotates hand-authored P1 resources."})
    write("action-fact.schema.json", action_fact_schema)

    old_path = ROOT / "docs/evidence/A02/execution/R1/after/demos/normal/final.json"
    old = json.loads(old_path.read_text(encoding="utf-8"))
    archive = out / "archive/a02-normal-final.json"
    archive.parent.mkdir(exist_ok=True)
    archive.write_bytes(old_path.read_bytes())
    resources = {}
    for node in walk(old):
        if isinstance(node, dict) and {"path", "sha256", "media_type"} <= node.keys():
            resources[node["path"]] = node
    for path in sorted(resources):
        dest = out / "archive" / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((old_path.parent / path).read_bytes())
        # The new copy keeps original bytes, with explicit origin in its new Resource.
        dest = out / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((old_path.parent / path).read_bytes())

    def asset(path, data):
        write("assets/" + path, data)
        data_path = out / "assets" / path
        return {"path": "assets/" + path, "sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
                "media_type": "application/json", "origin": "SYNTHETIC"}

    proof = asset("design-facts.json", {"design_only": True, "origin": "SYNTHETIC", "description": "Hand-constructed P1 facts; no local intent commit, dispatch, read or recovery occurred."})
    old_source = next(a for a in old["artifacts"] if a["kind"] == "SourceBundle")
    old_graph = next(a for a in old["artifacts"] if a["kind"] == "QuestionGraph")
    old_evidence = next(a for a in old["artifacts"] if a["kind"] == "EvidenceBundle")
    fragment_regions = {f["fragment_id"]: f["region_ids"] for f in old_graph["payload"]["fragments"]}
    region_assets = {r["region_id"]: r["box"]["image"]["asset_id"] for r in old_evidence["payload"]["regions"]}
    page_questions = {id_: [] for id_ in old_source["payload"]["pages_expected"]}
    for q in old_graph["payload"]["questions"]:
        fragments = list(dict.fromkeys(q["fragment_ids"] + q["shared_fragment_ids"]))
        pages = {region_assets[r] for f in fragments for r in fragment_regions[f]}
        for page in pages:
            page_questions[page].append(q["question_id"])
    scope_proof = asset("fixture-scope-proof.json", {"design_only": True, "origin": "SYNTHETIC", "basis": "FIXTURE", "complete": True,
        "book_id": old_source["book_id"], "scope_id": old_source["scope_id"], "pages_expected": old_source["payload"]["pages_expected"],
        "pages_acquired": old_source["payload"]["pages_acquired"], "scope_manifest": old_source["payload"]["scope_manifest"],
        "assets": [{k: a[k] for k in ("asset_id", "path", "sha256", "width", "height")} for a in old_source["payload"]["assets"]],
        "per_page_questions": [{"asset_id": page, "question_ids": page_questions[page], "enumeration_complete": True} for page in sorted(page_questions)],
        "limitations": "Explicit manufactured fixture enumeration only. Does not produce S01 real-source completeness."})
    base = copy.deepcopy(old)
    base["format_version"] = EXCHANGE
    # Preserve original receipt and all old outcome evidence only in archive.
    base["artifacts"] = [a for a in base["artifacts"] if a["kind"] not in ("ExecutionReceipt", "BatchReport") and not (a["kind"] == "CheckReport" and a["payload"]["stage"] == "POST_APPLY")]
    mapping = []
    known = {}
    for artifact in base["artifacts"]:
        prior = ref(artifact)
        artifact["schema_version"] = VERSION
        artifact["run_id"] = "a03-design-run"
        artifact["created_at"] = NOW
        artifact["producer"]["implementation_version"] = "a03-P1-NOT-IMPLEMENTED"
        artifact["producer"]["config_version"] = "DESIGN_ONLY"
        for node in walk(artifact):
            if isinstance(node, dict) and {"path", "sha256", "media_type"} <= node.keys():
                node["origin"] = "SYNTHETIC"
            if isinstance(node, dict) and {"artifact_id", "revision", "kind", "content_hash"} == node.keys():
                key = (node["artifact_id"], node["revision"])
                if key in known:
                    node.update(known[key])
        if artifact["kind"] == "SourceBundle":
            artifact["payload"]["scope_integrity"] = {"status": "SYNTHETIC_COMPLETE", "basis": "FIXTURE", "proof": scope_proof}
        if artifact["kind"] == "PlatformSnapshot":
            current_source = next(x for x in base["artifacts"] if x["kind"] == "SourceBundle")
            artifact["input_refs"] = [ref(current_source)]
            artifact["payload"].update(observed_at=NOW, observed_version="design-effects-0")
            artifact["payload"]["observed_hash"] = digest(business_state(artifact["payload"], ref(current_source)))
        if artifact["kind"] == "CheckReport":
            artifact["payload"]["recovery_refs"] = []
        seal(artifact)
        known[(artifact["artifact_id"], artifact["revision"])] = ref(artifact)
        mapping.append({"old": prior, "new": ref(artifact), "design_only": True, "qualification": "NONE"})
    for node in walk(base["evidence"]):
        if isinstance(node, dict) and {"path", "sha256", "media_type"} <= node.keys():
            node["origin"] = "SYNTHETIC"
    plan = next(a for a in base["artifacts"] if a["kind"] == "ApplyPlan")
    source = next(a for a in base["artifacts"] if a["kind"] == "SourceBundle")
    before = next(a for a in base["artifacts"] if a["kind"] == "PlatformSnapshot")
    actions = plan["payload"]["actions"]
    dependency_digest = digest({k: plan["payload"][k] for k in ("graph", "precheck", "targetcheck", "snapshot", "policy", "execution_mode", "session_mode", "required_capabilities")})
    write("migration-map.json", {"design_only": True, "operation": "EXPLICIT_OFFLINE_NEW_SAMPLE_CONVERSION",
        "original_path": old_path.relative_to(ROOT).as_posix(), "original_sha256": hashlib.sha256(old_path.read_bytes()).hexdigest(),
        "original_size": len(old_path.read_bytes()), "archive": "archive/a02-normal-final.json", "mappings": mapping,
        "excluded_old_kinds": ["ExecutionReceipt", "POST_APPLY CheckReport", "BatchReport"],
        "historical_intents_invented": False, "qualification": "NONE: all P1 samples are DESIGN_ONLY; P2 needs fresh current-library local commits"})

    def make(kind, id_, payload, inputs=()):
        a = {k: copy.deepcopy(plan[k]) for k in ("schema_version", "revision", "run_id", "book_id", "scope_id", "producer", "created_at")}
        inputs = {encoded(ref(x)): ref(x) for x in inputs}
        a.update(kind=kind, artifact_id=id_, payload=payload, input_refs=list(inputs.values()), content_hash=ZERO)
        if kind == "WriteIntent":
            a["created_at"] = payload["intent_committed_at"]
        elif kind in ("PlatformSnapshot", "ReconciliationResult"):
            a["created_at"] = payload["observed_at"]
        else:
            a["created_at"] = at(15)
        return seal(a)

    def intent(index):
        action = actions[index]
        prep_snap, prep_read = observed("prepared-" + str(index + 1), list(range(index)), 1 + 2 * index, time_seconds=3 * index + 1)
        prep_observation = json.loads((out / prep_read["path"]).read_text(encoding="utf-8"))
        prepared = asset("prepared-before-" + str(index + 1) + ".json", {"design_only": True, "origin": "SYNTHETIC",
            "action_id": action["action_id"], "target_session_id": "target-session-design", "source_ref": ref(source),
            **{k: prep_observation[k] for k in ("observation_id", "read_sequence", "observed_at", "target_state_version", "target_state_hash", "view")},
            "related_entities_complete": True, "relevant_before": action["expected_before"],
            "legal_predecessors": [{"action_id": a["action_id"], "action_digest": digest(a), "effective_outcome": "APPLIED"} for a in actions[:index]],
            "description": "Hand-constructed prepare facts; not an actual prepare or read transaction."})
        intent_dependencies = {"plan_dependencies_digest": dependency_digest, "source_ref": ref(source),
            "target_session_id": "target-session-design", "comparator_version": "a02-facts-1", "prepared_before_sha256": prepared["sha256"]}
        return make("WriteIntent", "intent-design-" + str(index + 1), {"plan_ref": ref(plan), "action_id": action["action_id"],
            "action_digest": digest(action), "target_key": {"platform_namespace": "a02-mock", "target_id": "synthetic-target", "book_id": "synthetic-book"},
            "question_id": action["target"]["question_id"], "source_entity_ids": action["source_entity_ids"], "before_snapshot_ref": ref(before),
            "target_session_id": "target-session-design", "source_ref": ref(source), "prepared_before": prepared,
            "execution_mode": "SIMULATED", "journal_id": "journal-design", "journal_sequence": 2 + 2 * index,
            "journal_head_hash": digest({"design_only": True, "predecessor_sequence": 1 + 2 * index}), "owner_id": "owner-design", "generation": 1,
            "intent_committed_at": at(3 * index + 2), "plan_dependency_digest": digest(intent_dependencies)}, [plan, before, source])

    def observed(label, applied, seq=10, not_attempted=(), time_seconds=None):
        questions, frames, bindings, projections = [], [], {}, {}
        for i in applied:
            action = actions[i]
            pid = "design-platform-question-" + str(i + 1)
            bindings[action["target"]["question_id"]] = pid
            questions.append({"platform_question_id": pid, "directory_id": action["expected_after"]["directory_id"], "platform_order": action["expected_after"]["platform_order"]})
            for j, projected in enumerate(json.loads(action["expected_after"]["frames"])):
                fid = "design-frame-{}-{}".format(i + 1, j + 1)
                frames.append({"platform_frame_id": fid, "platform_question_id": pid,
                               "box": projected["box"], "platform_role": projected["platform_role"]})
                projections[fid] = projected
        time = at(seq if time_seconds is None else time_seconds)
        state_version = "design-effects-" + str(len(applied))
        payload = copy.deepcopy(before["payload"])
        payload.update(observed_at=time, observed_version=state_version, questions=questions, frames=frames)
        state_hash = digest(business_state(payload, ref(source), bindings, projections))
        payload["observed_hash"] = state_hash
        view = {"target": payload, "internal_bindings": bindings, "frame_projections": projections}
        readback = asset("observation-" + label + ".json", {"design_only": True, "origin": "SYNTHETIC",
            "target_key": {"platform_namespace": "a02-mock", "target_id": "synthetic-target", "book_id": "synthetic-book"},
            "scope_id": "synthetic-scope", "source_ref": ref(source), "observation_id": "observation-" + label,
            "target_session_id": "target-session-design", "store_id": "target-store-design",
            "observed_at": time, "read_sequence": seq, "target_state_version": state_version, "target_state_hash": state_hash,
            "scope_complete": True, "action_ids": [a["action_id"] for a in actions], "questions": questions, "frames": frames,
            "view": view, "read_status": "OK",
            "per_action": [{"action_id": a["action_id"], "action_digest": digest(a), "question_id": a["target"]["question_id"],
                "source_entity_ids": a["source_entity_ids"], "related_scope_complete": True,
                "platform_question_ids": [bindings[a["target"]["question_id"]]] if n in applied else [],
                "platform_frame_ids": [f["platform_frame_id"] for f in frames if f["platform_question_id"] == bindings.get(a["target"]["question_id"])],
                "expected_before_digest": digest(a["expected_before"]), "expected_after_digest": digest(a["expected_after"]),
                "design_observation": "MATCH" if n in applied else "ABSENT"} for n, a in enumerate(actions)],
            "not_attempted_action_ids": [actions[n]["action_id"] for n in not_attempted]})
        snap = make("PlatformSnapshot", "snapshot-" + label, payload, [source])
        return snap, readback

    match_snap, match_read = observed("match", [0])
    absent_snap, absent_read = observed("absent", [])
    all_snap, all_read = observed("normal", [0, 1, 2])
    next_snap, next_read = observed("new-read-unchanged", [], 11)
    partial_snap, partial_read = observed("partial", [0], 12, [2])

    def resolution(i, snap, read, observation="MATCH", id_="resolution-design", previous=None, original=None, seq=1):
        action = actions[0]
        return make("ReconciliationResult", id_, {"plan_ref": ref(plan), "intent_ref": ref(i), "action_id": action["action_id"],
            "obligation_id": obligation(i),
            "action_digest": digest(action), "original_receipt_ref": ref(original) if original else None,
            "previous_resolution_ref": ref(previous) if previous else None, "observed_snapshot_ref": ref(snap) if snap else None,
            "observation_id": Path(read["path"]).stem if read else "observation-" + id_, "recovery_call_id": "recovery-call-design", "attempt_index": seq,
            "observed_at": snap["payload"]["observed_at"] if snap else at(9), "read_sequence": json.loads((out / read["path"]).read_text(encoding="utf-8"))["read_sequence"] if read else None,
            "target_state_version": snap["payload"]["observed_version"] if snap else None,
            "target_state_hash": snap["payload"]["observed_hash"] if snap else None, "observation": observation,
            "resolution": {"MATCH": "RESOLVED_APPLIED", "ABSENT": "RESOLVED_NOT_APPLIED"}.get(observation, "STILL_UNKNOWN"),
            "platform_ids": ["design-platform-question-1"] if observation == "MATCH" else [], "evidence_refs": [read] if read else [proof],
            "readback": read, "comparator_version": "a02-facts-1", "reason_code": "DESIGN_" + observation, "replay_allowed": False},
            [x for x in (plan, i, original, previous, snap) if x is not None])

    def progress(intents, outcomes, facts, receipts=None, resolutions=None, result_facts=None):
        rows = []
        for n, action in enumerate(actions):
            rows.append({"action_id": action["action_id"], "intent_ref": ref(intents[n]) if n in intents else None,
                "attempt_fact": facts[n], "dependency_status": "SATISFIED" if outcomes[n] == "APPLIED" else ("READY" if n == 0 else "BLOCKED"),
                "attempt_evidence_refs": [proof], "receipt_ref": ref(receipts[n]) if receipts and n in receipts else None,
                "resolution_head_ref": ref(resolutions[n]) if resolutions and n in resolutions else None, "effective_outcome": outcomes[n]})
            rows[-1]["result_fact"] = result_facts.get(n) if result_facts else None
        inputs = [plan] + list(intents.values()) + list((receipts or {}).values()) + list((resolutions or {}).values())
        return make("ExecutionProgress", "progress-design", {"plan_ref": ref(plan), "journal_id": "journal-design",
                    "journal_head_sequence": 10, "journal_head_hash": digest({"design_only": True, "sequence": 10}), "actions": rows}, inputs)

    def receipt(intents, outcomes, facts, snap, read):
        results = []
        for n, action in enumerate(actions):
            outcome = outcomes[n]
            results.append({"action_id": action["action_id"], "outcome": outcome, "platform_ids": ["design-platform-question-" + str(n + 1)] if outcome == "APPLIED" else [],
                "before_evidence_refs": ["proof-before"], "after_evidence_refs": [] if outcome == "UNKNOWN" else ["proof-after"],
                "readback": None if outcome == "UNKNOWN" else read, "effect_match": {"APPLIED": "MATCH", "NOT_APPLIED": "ABSENT", "UNKNOWN": "INDETERMINATE"}[outcome],
                "next_step": {"APPLIED": "POSTCHECK", "NOT_APPLIED": "RECHECK_TARGET", "UNKNOWN": "RECONCILE"}[outcome],
                "replay_allowed": False, "reason": "DESIGN_ONLY invented result, not an execution receipt", "attempt_fact": facts[n],
                "attempt_evidence_refs": [proof], "intent_ref": ref(intents[n]) if n in intents else None})
        return make("ExecutionReceipt", "receipt-design", {"plan": ref(plan), "execution_mode": "SIMULATED", "results": results,
            "action_fact_refs": [],
            "unresolved_issue_ids": ["issue-save-unknown"] if "UNKNOWN" in outcomes else [],
            "write_disposition": "PAUSE_RECONCILE" if "UNKNOWN" in outcomes else ("RECHECK_TARGET" if "NOT_APPLIED" in outcomes else "POSTCHECK")}, [plan] + list(intents.values()))

    def result_fact(label, n, result, intent_artifact, snap, read, sequence):
        prepared = intent_artifact["payload"]["prepared_before"] if intent_artifact else read
        return asset("action-fact-" + label + ".json", {"format_version": "a03-action-fact-1", "design_only": True,
            "origin_phase": "EXECUTION", "resolution_ref": None,
            "plan_ref": ref(plan), "intent_ref": ref(intent_artifact) if intent_artifact else None,
            "obligation_id": obligation(intent_artifact) if intent_artifact else None, "action_id": actions[n]["action_id"], "action_digest": digest(actions[n]),
            "prepared_before": prepared, "observed_snapshot_ref": ref(snap) if snap else None, "readback": read,
            "comparator_version": "a02-facts-1", "result": result, "journal_sequence": sequence,
            "predecessor_hash": digest({"design_only": True, "predecessor_sequence": sequence - 1})})

    def ledger(bundle, unresolved=None):
        return {"format_version": "a03-ledger-export-1", "ledger_id": "ledger-design", "db_version": "a03-runtime-db-1",
            "book_key": {"platform_namespace": "a02-mock", "target_id": "synthetic-target", "book_id": "synthetic-book"}, "owner_id": "owner-design", "generation": 1,
            "event_head_sequence": 10, "event_head_hash": digest({"design_only": True, "sequence": 10}),
            "scopes": [{"scope_id": "synthetic-scope", "source_ref": ref(source), "target_session_id": "target-session-design", "archive_refs": []}],
            "unresolved": unresolved or [], "artifact_history": [ref(a) for a in bundle["artifacts"]], "pending_action_ids": [], "external_ids": [],
            "pause": {"paused": bool(unresolved), "reason_codes": ["BOOK_PENDING"] if unresolved else [], "event_ids": [u["event_id"] for u in unresolved or []]},
            "state_directory_identity": "state-directory-design", "target_store_identity": "target-store-design", "diagnostic_only": True}

    cases = []
    def case(id_, extra, code, layer="SEMANTIC", static="PASS", claim=None, note="", led=None):
        bundle = copy.deepcopy(base)
        bundle["artifacts"] += copy.deepcopy(extra)
        item = {"design_only": True, "case_id": id_, "bundle": bundle, "ledger_export": led if led else ledger(bundle), "runtime_claim": claim or {"design_only": True, "local_commit_evidence": "NOT_EXECUTED"}}
        cases.append({"case_id": id_, "path": "cases/" + id_ + ".json", "expected_layer": layer, "expected_code": code,
                      "expected_static": static, "semantic_execution": "EXPECTED_NOT_EXECUTED", "note": note})
        return item

    i0, i1, i2 = intent(0), intent(1), intent(2)
    match = resolution(i0, match_snap, match_read)
    absent = resolution(i0, absent_snap, absent_read, "ABSENT")
    normal_receipt = receipt({0: i0, 1: i1, 2: i2}, ["APPLIED"] * 3, ["ATTEMPTED"] * 3, all_snap, all_read)
    normal_result_snapshots, normal_result_facts = [], {}
    for n, intent_artifact in enumerate((i0, i1, i2)):
        result_snap, result_read = observed("action-result-" + str(n + 1), list(range(n + 1)), 2 + 2 * n, time_seconds=3 * n + 3)
        normal_result_snapshots.append(result_snap)
        normal_receipt["payload"]["results"][n]["readback"] = result_read
        normal_result_facts[n] = result_fact("normal-" + str(n + 1), n, normal_receipt["payload"]["results"][n], intent_artifact, result_snap, result_read, 3 + 2 * n)
    normal_receipt["payload"]["action_fact_refs"] = list(normal_result_facts.values())
    seal(normal_receipt)
    normal_progress = progress({0: i0, 1: i1, 2: i2}, ["APPLIED"] * 3, ["ATTEMPTED"] * 3, {0: normal_receipt, 1: normal_receipt, 2: normal_receipt}, result_facts=normal_result_facts)
    graph = next(a for a in base["artifacts"] if a["kind"] == "QuestionGraph")
    post_payload = copy.deepcopy(next(a for a in old["artifacts"] if a["kind"] == "CheckReport" and a["payload"]["stage"] == "POST_APPLY")["payload"])
    post_payload.update(subject=ref(normal_receipt), graph=ref(graph), snapshot=ref(all_snap), receipt=ref(normal_receipt), recovery_refs=[])
    post = make("CheckReport", "postcheck-design", post_payload, [graph, normal_receipt, all_snap])
    batch_payload = copy.deepcopy(next(a for a in old["artifacts"] if a["kind"] == "BatchReport")["payload"])
    batch_payload.update(source=ref(source), graph=ref(graph), receipt=ref(normal_receipt), postcheck=ref(post), recovery_refs=[], progress_refs=[ref(normal_progress)])
    batch = make("BatchReport", "batch-design", batch_payload, [source, graph, normal_receipt, post, normal_progress])
    normal = case("normal", [i0, i1, i2, *normal_result_snapshots, all_snap, normal_receipt, normal_progress, post, batch], "PENDING_NOT_SUBMITTED", note="New design receipt/postcheck/batch use archived normal payload as a structural template, not a migrated outcome or qualification. Final content remains PENDING. Not a local commit proof.")
    match_case = case("intent-no-receipt-match", [i0, match_snap, match, progress({0: i0}, ["APPLIED", "UNDETERMINED", "UNDETERMINED"], ["MAY_HAVE_BEEN_ATTEMPTED", "NOT_ATTEMPTED", "NOT_ATTEMPTED"], resolutions={0: match})], "RESOLVED_APPLIED_NO_REPLAY")
    absent_case = case("intent-no-receipt-absent", [i0, absent_snap, absent], "RESOLVED_NOT_APPLIED_REPLAN_REQUIRED")
    values = [normal, match_case, absent_case]
    mixed_receipt = receipt({0: i0, 1: i1}, ["APPLIED", "UNKNOWN", "NOT_APPLIED"], ["ATTEMPTED", "MAY_HAVE_BEEN_ATTEMPTED", "NOT_ATTEMPTED"], partial_snap, partial_read)
    mixed_receipt["payload"]["results"][0] = copy.deepcopy(normal_receipt["payload"]["results"][0])
    mixed_result_facts = {0: normal_result_facts[0],
        1: result_fact("partial-unknown", 1, mixed_receipt["payload"]["results"][1], i1, None, None, 5),
        2: result_fact("partial-not-attempted-absent", 2, mixed_receipt["payload"]["results"][2], None, partial_snap, partial_read, 6)}
    mixed_receipt["payload"]["action_fact_refs"] = list(mixed_result_facts.values())
    seal(mixed_receipt)
    mixed = progress({0: i0, 1: i1}, ["APPLIED", "UNKNOWN", "UNDETERMINED"], ["ATTEMPTED", "MAY_HAVE_BEEN_ATTEMPTED", "NOT_ATTEMPTED"], result_facts={0: mixed_result_facts[0], 1: mixed_result_facts[1]})
    values.append(case("partial-without-absent", [i0, i1, normal_result_snapshots[0], mixed], "PROGRESS_ONLY_BOOK_PENDING", note="No receipt fabricated for the unattempted tail; action list remains complete. Prior APPLIED ActionResult event is explicitly retained."))
    mixed_complete = progress({0: i0, 1: i1}, ["APPLIED", "UNKNOWN", "NOT_APPLIED"], ["ATTEMPTED", "MAY_HAVE_BEEN_ATTEMPTED", "NOT_ATTEMPTED"],
                              {0: mixed_receipt, 1: mixed_receipt, 2: mixed_receipt}, result_facts=mixed_result_facts)
    values.append(case("partial-with-complete-absent", [i0, i1, normal_result_snapshots[0], partial_snap, mixed_receipt, mixed_complete], "NOT_ATTEMPTED_NOT_APPLIED_BOOK_PENDING", note="Whole-scope design readback has no tail action identity and explicitly records not_attempted; attempt fact is independently declared. A02 adapter must compare each action and account for legitimate predecessors."))
    bad_partial = case("partial-fabricated-receipt", [i0, i1, normal_result_snapshots[0], partial_snap, mixed_receipt], "ACTION_FACT_RESULT_MISMATCH", "REFERENCE", "DESIGN_FIELD_FAIL", note="Readback removed from NOT_ATTEMPTED receipt result while immutable fact remains unchanged; static exact-fact binding rejects the fabricated aggregation. No recovery semantics are run.")
    bad_partial["bundle"]["artifacts"][-1]["payload"]["results"][-1]["readback"] = None
    values.append(bad_partial)
    for obs in ("CONFLICT", "INDETERMINATE"):
        r = resolution(i0, match_snap if obs == "CONFLICT" else None, match_read if obs == "CONFLICT" else None, obs)
        values.append(case(obs.lower(), [i0] + ([match_snap] if obs == "CONFLICT" else []) + [r], "STILL_UNKNOWN"))
    unknown_receipt = receipt({0: i0}, ["UNKNOWN", "NOT_APPLIED", "NOT_APPLIED"], ["MAY_HAVE_BEEN_ATTEMPTED", "NOT_ATTEMPTED", "NOT_ATTEMPTED"], absent_snap, absent_read)
    unknown_result_facts = {0: result_fact("original-unknown", 0, unknown_receipt["payload"]["results"][0], i0, None, None, 3),
        1: result_fact("original-unattempted-2", 1, unknown_receipt["payload"]["results"][1], None, absent_snap, absent_read, 4),
        2: result_fact("original-unattempted-3", 2, unknown_receipt["payload"]["results"][2], None, absent_snap, absent_read, 5)}
    unknown_receipt["payload"]["action_fact_refs"] = list(unknown_result_facts.values())
    seal(unknown_receipt)
    r_unknown = resolution(i0, match_snap, match_read, original=unknown_receipt)
    values.append(case("original-unknown-preserved", [i0, absent_snap, unknown_receipt, match_snap, r_unknown], "RESOLVED_APPLIED_ORIGINAL_UNKNOWN_RETAINED"))
    recovered_progress = progress({0: i0}, ["APPLIED", "NOT_APPLIED", "NOT_APPLIED"], ["MAY_HAVE_BEEN_ATTEMPTED", "NOT_ATTEMPTED", "NOT_ATTEMPTED"],
                                  {0: unknown_receipt, 1: unknown_receipt, 2: unknown_receipt}, {0: r_unknown}, result_facts=unknown_result_facts)
    recovered_post_payload = copy.deepcopy(post_payload)
    recovered_post_payload.update(subject=ref(unknown_receipt), receipt=ref(unknown_receipt), snapshot=ref(match_snap), recovery_refs=[ref(r_unknown)], decision="HOLD",
        reason="DESIGN_ONLY resolved first effect; unapplied tail and final content remain unverified")
    for check in recovered_post_payload["checks"]:
        check["outcome"] = "FAIL" if check["check_id"] == "frame_structure" else "UNAVAILABLE"
        check["reason"] = "DESIGN_ONLY tail expected frames absent; final content pending"
    recovered_post_payload["issues"] = [{"issue_id": "issue-tail-not-applied", "code": "TARGET_CHANGED", "scope_type": "scope", "scope_id": "synthetic-scope",
        "evidence_refs": ["proof-after"], "severity": "blocking", "blocks": ["COMPLETE"],
        "suggested_strategy": {"strategy_id": "RECHECK_TARGET", "max_attempts": 1, "max_cost": 0}, "reason": "Design tail is known NOT_APPLIED; new target checks and planning are required"}]
    recovered_post = make("CheckReport", "postcheck-recovered-design", recovered_post_payload, [graph, unknown_receipt, match_snap, r_unknown])
    recovered_batch_payload = copy.deepcopy(batch_payload)
    recovered_batch_payload.update(receipt=ref(unknown_receipt), postcheck=ref(recovered_post), recovery_refs=[ref(r_unknown)], progress_refs=[ref(recovered_progress)],
        content_check_status="PENDING", submission_status="NOT_SUBMITTED", frame_check_status="FAIL", state="NEEDS_REVIEW", unresolved_issue_ids=["issue-tail-not-applied"])
    for n, row in enumerate(recovered_batch_payload["questions"]):
        row.update(state="PENDING" if n == 0 else "EXCEPTION", reason="Design first action resolved, content pending" if n == 0 else "Design tail known not applied; replan required")
    recovered_batch = make("BatchReport", "batch-recovered-design", recovered_batch_payload, [source, graph, unknown_receipt, recovered_post, r_unknown, recovered_progress])
    values.append(case("recovered-report-binding", [i0, absent_snap, unknown_receipt, match_snap, r_unknown, recovered_progress, recovered_post, recovered_batch], "RECOVERY_REPORT_PENDING_NOT_SUBMITTED"))
    hold = resolution(i0, None, None, "INDETERMINATE", "resolution-first")
    retry = resolution(i0, next_snap, next_read, "ABSENT", "resolution-second", hold, seq=2)
    values.append(case("new-read-unchanged-state-version", [i0, hold, next_snap, retry], "FRESH_READ_SAME_EFFECT_VERSION", note="Read sequence and observation/time are new; no effect version increment is required."))
    # Cross-scope data is a constructed diagnostic full-book export; never a supported scope switch.
    cross = case("cross-scope-only-one-resolved", [i0, match_snap, match], "BOOK_PENDING_SCOPE_SWITCH_UNSUPPORTED", "RUNTIME_TRANSACTION")
    second = copy.deepcopy(base["artifacts"] + [i0])
    for artifact in second:
        artifact["artifact_id"] = "other-" + artifact["artifact_id"]
        artifact["scope_id"] = "other-design-scope"
        artifact["run_id"] = "other-design-run"
        for node in walk(artifact):
            if isinstance(node, dict) and {"artifact_id", "revision", "kind", "content_hash"} == node.keys():
                node["artifact_id"] = "other-" + node["artifact_id"]
        if artifact["kind"] == "PlatformSnapshot":
            artifact["payload"]["authorized_scope_id"] = "other-design-scope"
        if artifact["kind"] == "CheckReport":
            artifact["payload"]["coverage"]["scope_id"] = "other-design-scope"
        if artifact["kind"] == "WriteIntent":
            artifact["payload"]["target_session_id"] = "historical-other-session-design"
    other_plan = next(a for a in second if a["kind"] == "ApplyPlan")
    other_source = next(a for a in second if a["kind"] == "SourceBundle")
    other_intent = next(a for a in second if a["kind"] == "WriteIntent")
    other_scope_proof = json.loads((out / scope_proof["path"]).read_text(encoding="utf-8"))
    other_scope_proof["scope_id"] = "other-design-scope"
    other_source["payload"]["scope_integrity"]["proof"] = asset("other-fixture-scope-proof.json", other_scope_proof)
    seal(other_source)
    other_prepared = json.loads((out / i0["payload"]["prepared_before"]["path"]).read_text(encoding="utf-8"))
    other_prepared.update(source_ref=ref(other_source), target_session_id="historical-other-session-design", observation_id="observation-other-prepared-1")
    other_prepared["view"]["target"]["authorized_scope_id"] = "other-design-scope"
    other_prepared["target_state_hash"] = digest(business_state(other_prepared["view"]["target"], ref(other_source)))
    other_prepared["view"]["target"]["observed_hash"] = other_prepared["target_state_hash"]
    other_intent["payload"]["prepared_before"] = asset("other-prepared-before-1.json", other_prepared)
    for a in second:
        if a["kind"] == "PlatformSnapshot":
            a["payload"]["observed_hash"] = digest(business_state(a["payload"], ref(other_source)))
    cross["bundle"]["artifacts"] += second
    unresolved = [{"event_id": "event-first-scope", "obligation_id": obligation(i0), "run_id": "a03-design-run", "scope_id": "synthetic-scope", "plan_ref": ref(plan), "intent_ref": ref(i0), "receipt_ref": None, "classification": "UNKNOWN"},
                  {"event_id": "event-other-scope", "obligation_id": obligation(other_intent), "run_id": "other-design-run", "scope_id": "other-design-scope", "plan_ref": ref(other_plan), "intent_ref": ref(other_intent), "receipt_ref": None, "classification": "UNKNOWN"}]
    cross["ledger_export"] = ledger(cross["bundle"], unresolved)
    cross["ledger_export"]["scopes"].append({"scope_id": "other-design-scope", "source_ref": ref(other_source), "target_session_id": None, "archive_refs": []})
    cross["runtime_claim"] = {"design_only": True, "first_scope_has_terminal_resolution": True, "expected_remaining_after_transaction": ["event-other-scope"], "other_scope_read_supported": False, "requested_scope_switch": "other-design-scope", "expected_pause": True, "historical_other_session_is_not_current_authority": True}
    values.append(cross)
    legacy = case("legacy-unrecorded-no-intent", [], "LEGACY_UNRECORDED", "RUNTIME_TRANSACTION")
    legacy["ledger_export"] = ledger(legacy["bundle"], [{"event_id": "event-legacy", "obligation_id": "legacy-event-legacy", "run_id": "old-run", "scope_id": "synthetic-scope", "plan_ref": ref(plan), "intent_ref": None, "receipt_ref": None, "classification": "LEGACY_UNRECORDED"}])
    legacy["runtime_claim"] = {"design_only": True, "archived_legacy_unknown": "archive/legacy/input.json", "migration_may_invent_intent": False}
    values.append(legacy)
    legacy_path = ROOT / "tests/fixtures/contracts/unknown/input.json"
    (out / "archive/legacy").mkdir(parents=True, exist_ok=True)
    (out / "archive/legacy/input.json").write_bytes(legacy_path.read_bytes())
    for node in walk(json.loads(legacy_path.read_text(encoding="utf-8"))):
        if isinstance(node, dict) and {"path", "sha256", "media_type"} <= node.keys():
            destination = out / "archive/legacy" / node["path"]
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((legacy_path.parent / node["path"]).read_bytes())
    legacy_bundle = json.loads(legacy_path.read_text(encoding="utf-8"))
    legacy_plan = next(a for a in legacy_bundle["artifacts"] if a["kind"] == "ApplyPlan")
    legacy_receipt = next(a for a in legacy_bundle["artifacts"] if a["kind"] == "ExecutionReceipt")
    legacy_source = next(a for a in legacy_bundle["artifacts"] if a["kind"] == "SourceBundle")
    legacy["ledger_export"]["unresolved"][0].update(plan_ref=ref(legacy_plan), receipt_ref=ref(legacy_receipt), run_id=legacy_receipt["run_id"])
    legacy["ledger_export"]["scopes"] = [{"scope_id": legacy_source["scope_id"], "source_ref": ref(legacy_source), "target_session_id": None,
        "archive_refs": [{"path": "archive/legacy/input.json", "sha256": hashlib.sha256(legacy_path.read_bytes()).hexdigest(), "media_type": "application/json", "origin": "SYNTHETIC"}]}]
    legacy["ledger_export"]["artifact_history"] += [ref(legacy_plan), ref(legacy_receipt), ref(legacy_source)]

    def modified(id_, modify, code, layer="SEMANTIC", static="PASS", baseline=match_case):
        item = copy.deepcopy(baseline)
        item["case_id"] = id_
        modify(item)
        cases.append({"case_id": id_, "path": "cases/" + id_ + ".json", "expected_layer": layer, "expected_code": code,
                      "expected_static": static, "semantic_execution": "EXPECTED_NOT_EXECUTED", "note": "Single explicit mutation of the complete baseline; not an executed rejection."})
        values.append(item)
        return item

    def find(item, kind):
        return next(a for a in item["bundle"]["artifacts"] if a["kind"] == kind)
    modified("wrong-schema-version", lambda x: find(x, "WriteIntent").update(schema_version="1.0.0-a-proposal"), "RECOVERY_VERSION_UNSUPPORTED", "STRUCTURE", "STRUCTURE_FAIL")
    modified("wrong-exchange-version", lambda x: x["bundle"].update(format_version="c01-exchange-1"), "RECOVERY_VERSION_UNSUPPORTED", "STRUCTURE", "STRUCTURE_FAIL")
    modified("wrong-action-digest", lambda x: find(x, "WriteIntent")["payload"].update(action_digest=ZERO), "ACTION_DIGEST_MISMATCH")
    modified("wrong-target-identity", lambda x: find(x, "WriteIntent")["payload"]["target_key"].update(target_id="wrong-target"), "TARGET_IDENTITY_MISMATCH")
    modified("wrong-book-identity", lambda x: find(x, "WriteIntent").update(book_id="other-book"), "CROSS_BOOK_REFERENCE", "REFERENCE", "REFERENCE_FAIL")
    modified("wrong-scope-reference", lambda x: find(x, "WriteIntent").update(scope_id="other-scope"), "CROSS_SCOPE_REFERENCE", "REFERENCE", "REFERENCE_FAIL")
    modified("missing-plan-reference", lambda x: x["bundle"]["artifacts"].remove(find(x, "ApplyPlan")), "MISSING_REFERENCE", "REFERENCE", "REFERENCE_FAIL")
    modified("wrong-resource-hash", lambda x: find(x, "ReconciliationResult")["payload"]["readback"].update(sha256=ZERO), "RESOURCE_HASH_MISMATCH", "RESOURCE", "RESOURCE_FAIL")
    modified("missing-readback", lambda x: find(x, "ReconciliationResult")["payload"].update(readback=None), "CONCLUSIVE_READBACK_REQUIRED")
    modified("wrong-observed-state-hash", lambda x: find(x, "ReconciliationResult")["payload"].update(target_state_hash=ZERO), "OBSERVATION_BINDING_MISMATCH")
    modified("wrong-obligation-identity", lambda x: find(x, "ReconciliationResult")["payload"].update(obligation_id="obl-" + ZERO), "OBLIGATION_MISMATCH")
    modified("real-original-rejected", lambda x: find(x, "SourceBundle")["payload"]["assets"][0].update(provenance="ORIGINAL", origin="ORIGINAL"), "SYNTHETIC_ONLY", "SYNTHETIC_ADMISSION")
    modified("observed-producer-rejected", lambda x: find(x, "WriteIntent")["producer"].update(evidence_mode="OBSERVED"), "SYNTHETIC_ONLY", "SYNTHETIC_ADMISSION")
    modified("observed-resource-rejected", lambda x: find(x, "ReconciliationResult")["payload"]["readback"].update(origin="OBSERVED"), "SYNTHETIC_ONLY", "SYNTHETIC_ADMISSION")
    modified("observed-evidence-rejected", lambda x: x["bundle"]["evidence"][0].update(mode="OBSERVED"), "SYNTHETIC_ONLY", "SYNTHETIC_ADMISSION")
    modified("real-policy-rejected", lambda x: x["bundle"]["policies"][0].update(applicability="JOINT_CONFIRMED"), "SYNTHETIC_ONLY", "SYNTHETIC_ADMISSION")
    modified("platform-mode-rejected", lambda x: find(x, "ApplyPlan")["payload"].update(execution_mode="PLATFORM"), "SYNTHETIC_ONLY", "SYNTHETIC_ADMISSION")
    modified("unknown-scope-integrity", lambda x: find(x, "SourceBundle")["payload"].update(scope_manifest=None, scope_integrity={"status": "UNKNOWN", "basis": "METADATA", "proof": None}), "SYNTHETIC_COMPLETE_REQUIRED", "SYNTHETIC_ADMISSION")
    modified("stale-owner-generation", lambda x: x["runtime_claim"].update(current_owner_id="new-owner", current_generation=2, supplied_owner_id="owner-design", supplied_generation=1), "OWNER_GENERATION_STALE", "RUNTIME_TRANSACTION")
    modified("wrong-state-directory", lambda x: x["runtime_claim"].update(expected_state_directory_identity="state-directory-design", supplied_state_directory_identity="different-empty-directory", create_if_missing=False), "STATE_DIRECTORY_IDENTITY_MISMATCH", "RUNTIME_TRANSACTION")
    modified("fake-empty-ledger", lambda x: x["runtime_claim"].update(caller_unresolved=[], actual_current_db_unresolved=["event-hidden"], caller_export_is_authority=False), "BOOK_WRITE_PAUSED", "RUNTIME_TRANSACTION")
    modified("intent-not-locally-committed", lambda x: x["runtime_claim"].update(current_library_intent_commit_exists=False, caller_supplied_intent_json=True), "LOCAL_INTENT_COMMIT_REQUIRED", "RUNTIME_TRANSACTION")
    modified("attempt-limit-four", lambda x: find(x, "ReconciliationResult")["payload"].update(attempt_index=4), "RECONCILE_ATTEMPT_LIMIT", "STRUCTURE", "STRUCTURE_FAIL")
    modified("old-observation-reuse", lambda x: x["runtime_claim"].update(previous_observation_id="observation-match", previous_read_sequence=10, actual_new_read=False, caller_only_changes_timestamp=True), "OBSERVATION_NOT_FRESH", "RUNTIME_TRANSACTION")
    modified("resolved-chain-successor", lambda x: x["runtime_claim"].update(append_after_terminal=True, required_action="NEW_UNRESOLVED_EVENT"), "RESOLUTION_TERMINAL")
    terminal_case = values[-1]
    terminal_successor = resolution(i0, next_snap, next_read, "ABSENT", "resolution-terminal-successor", previous=match, seq=2)
    terminal_case["bundle"]["artifacts"] += [copy.deepcopy(next_snap), terminal_successor]
    reuse_case = next(x for x in values if x["case_id"] == "old-observation-reuse")
    old_observation = resolution(i0, match_snap, match_read, "INDETERMINATE", "resolution-old-observation-first")
    reused_observation = resolution(i0, match_snap, match_read, "MATCH", "resolution-old-observation-second", previous=old_observation, seq=2)
    reused_observation["payload"]["observed_at"] = at(11)
    reuse_case["bundle"]["artifacts"] = copy.deepcopy(base["artifacts"] + [i0, match_snap, old_observation, reused_observation])
    fork = copy.deepcopy(match_case)
    fork["case_id"] = "resolution-fork"
    fork_r = copy.deepcopy(match)
    fork_r["artifact_id"] = "resolution-fork-second"
    seal(fork_r)
    fork["bundle"]["artifacts"].append(fork_r)
    values.append(fork)
    cases.append({"case_id": "resolution-fork", "path": "cases/resolution-fork.json", "expected_layer": "SEMANTIC", "expected_code": "RESOLUTION_FORK", "expected_static": "PASS", "semantic_execution": "EXPECTED_NOT_EXECUTED", "note": "Two root resolution heads for the same intent. Both refs remain same-scope."})
    cycle = copy.deepcopy(match_case)
    cycle["case_id"] = "resolution-cycle"
    cr = find(cycle, "ReconciliationResult")
    cr["payload"]["previous_resolution_ref"] = ref(cr)
    cr["input_refs"].append(ref(cr))
    values.append(cycle)
    cases.append({"case_id": "resolution-cycle", "path": "cases/resolution-cycle.json", "expected_layer": "REFERENCE", "expected_code": "DEPENDENCY_CYCLE", "expected_static": "REFERENCE_FAIL", "semantic_execution": "EXPECTED_NOT_EXECUTED", "note": "A content-addressed self-cycle cannot have a consistent fixed-point digest; reject the reference cycle before digest resolution."})
    for id_, manifest, integrity, code in (("source-only-unknown-denominator", None, {"status": "UNKNOWN", "basis": "METADATA", "proof": None}, "SYNTHETIC_COMPLETE_REQUIRED"),
                                          ("source-only-zero-actions", [], {"status": "SYNTHETIC_COMPLETE", "basis": "FIXTURE", "proof": scope_proof}, "NO_ACTIONS")):
        item = case(id_, [], code, "SYNTHETIC_ADMISSION" if manifest is None else "SEMANTIC", note="Source-only diagnostic: no fabricated graph, plan, receipt or BatchReport; existing Batch nonzero/known denominator requirements remain unchanged.")
        item["bundle"]["artifacts"] = [find(item, "SourceBundle")]
        item["bundle"]["artifacts"][0]["payload"].update(scope_manifest=manifest, scope_integrity=integrity)
        if manifest == []:
            zero_proof = json.loads((out / scope_proof["path"]).read_text(encoding="utf-8"))
            zero_proof["scope_manifest"] = []
            zero_proof["scope_id"] = "synthetic-zero-scope"
            for row in zero_proof["per_page_questions"]:
                row["question_ids"] = []
            zero_proof["limitations"] = "Manufactured zero-question scope: page marks are explicitly excluded fixture marks. No plan or BatchReport is fabricated."
            item["bundle"]["artifacts"][0]["scope_id"] = "synthetic-zero-scope"
            item["bundle"]["artifacts"][0]["payload"]["scope_integrity"]["proof"] = asset("zero-fixture-scope-proof.json", zero_proof)
            item["ledger_export"]["scopes"][0]["scope_id"] = "synthetic-zero-scope"
        values.append(item)

    # Reseal modified DAGs and update every ordinary ref by (id, revision), without semantic qualification.
    for item in values:
        artifacts = item["bundle"]["artifacts"]
        policies = {(p["policy_id"], p["revision"]): seal(p) for p in item["bundle"]["policies"]}
        for node in walk(artifacts):
            if isinstance(node, dict) and {"policy_id", "revision", "content_hash"} == node.keys():
                p = policies.get((node["policy_id"], node["revision"]))
                if p is not None:
                    node["content_hash"] = p["content_hash"]
        by_key = {(a["artifact_id"], a["revision"]): a for a in artifacts}
        done, busy = {}, set()
        def refresh(a):
            key = (a["artifact_id"], a["revision"])
            if key in done or key in busy:
                return
            busy.add(key)
            for node in walk(a):
                if isinstance(node, dict) and {"artifact_id", "revision", "kind", "content_hash"} == node.keys():
                    other = by_key.get((node["artifact_id"], node["revision"]))
                    if other is not None and other is not a:
                        refresh(other)
                        node.update(ref(other))
            if a["kind"] == "ReconciliationResult" and item["case_id"] != "wrong-obligation-identity":
                intent_artifact = by_key.get((a["payload"]["intent_ref"]["artifact_id"], a["payload"]["intent_ref"]["revision"]))
                if intent_artifact is not None:
                    a["payload"]["obligation_id"] = obligation(intent_artifact)
            if a["kind"] == "WriteIntent" and a["scope_id"] == "other-design-scope":
                other_p = by_key[(a["payload"]["plan_ref"]["artifact_id"], a["payload"]["plan_ref"]["revision"])]["payload"]
                a["payload"]["plan_dependency_digest"] = digest({"plan_dependencies_digest": digest({k: other_p[k] for k in ("graph", "precheck", "targetcheck", "snapshot", "policy", "execution_mode", "session_mode", "required_capabilities")}),
                    "source_ref": a["payload"]["source_ref"], "target_session_id": a["payload"]["target_session_id"], "comparator_version": "a02-facts-1", "prepared_before_sha256": a["payload"]["prepared_before"]["sha256"]})
            seal(a)
            busy.remove(key)
            done[key] = True
        for a in artifacts:
            refresh(a)
        # Diagnostic refs display the exact same frozen artifacts; they still grant no authority.
        for node in walk(item["ledger_export"]):
            if isinstance(node, dict) and {"artifact_id", "revision", "kind", "content_hash"} == node.keys():
                other = by_key.get((node["artifact_id"], node["revision"]))
                if other is not None:
                    node.update(ref(other))
        for u in item["ledger_export"]["unresolved"]:
            if u["intent_ref"] is not None:
                ia = by_key.get((u["intent_ref"]["artifact_id"], u["intent_ref"]["revision"]))
                if ia is not None:
                    u["obligation_id"] = obligation(ia)
        write("cases/" + item["case_id"] + ".json", item)
    write("case-manifest.json", {"design_only": True, "schema_version": VERSION, "format_version": EXCHANGE,
        "functionality_executed": False, "local_intent_commits": 0, "recovery_calls": 0, "platform_calls": 0,
        "static_check_scope": ["JSON", "JSON_SCHEMA_SUBSET", "RESOURCE_BYTES", "CONTENT_HASH", "ORDINARY_REFERENCES", "REFERENCE_DAG"],
        "cases": cases})
    print(json.dumps({"design_only": True, "output": str(out), "cases": len(cases), "runtime_or_recovery_executed": False}))


if __name__ == "__main__":
    main()
