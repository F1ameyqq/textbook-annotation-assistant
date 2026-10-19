"""A11 pure admission and readback checks. No session, network, or mutation."""
from dataclasses import dataclass
from datetime import datetime, timezone
import json

from annotation.contracts import artifact_ref, policy_ref, validate_bundle
from annotation.quality.targetcheck import projection_frames, resolve_artifact, resolve_policy
from annotation.delivery.planner import compare_action_effect
from annotation.runtime.storage.common import digest

BOOK = "46007447"
ROLES = ["Q", "W", "W", "W", "W", "A"]
SEMANTIC_ROLES = ["stem", "option", "option", "option", "option", "answer"]


class PilotError(Exception):
    def __init__(self, code, detail=""):
        self.code = code
        super().__init__(detail or code)


def require(condition, code, detail=""):
    if not condition:
        raise PilotError(code, detail)


@dataclass(frozen=True)
class Admission:
    bundle: object
    graph: object
    policy: object
    questions: tuple
    input_hash: str
    approval_hash: str
    offline: bool


def question_facts(bundle, graph, question, policy, bindings):
    evidence = resolve_artifact(bundle, graph.payload.evidence, "EvidenceBundle")
    regions = {r.region_id: r for r in evidence.payload.regions}
    projection = projection_frames(bundle, graph, question, policy)
    fragments = {f.fragment_id: f for f in graph.payload.fragments}
    relations = [r.model_dump(mode="json") for r in graph.payload.answer_relations
                 if r.question_id == question.question_id]
    return {"question_id": question.question_id, "directory_id": question.directory_id,
            "question_type": question.question_type,
            "source": graph.payload.source.model_dump(mode="json"),
            "graph": artifact_ref(graph), "policy": policy_ref(policy),
            "bindings": bindings, "relations": relations, "frames": projection,
            "parts": [{"fragment_id": p["fragment_id"], "role": fragments[p["fragment_id"]].role,
                       "text": regions[p["region_id"]].text} for p in projection]}


def check_input(request, asset_root, *, offline=False, at=None):
    """C01 checks raw resources, closure, dimensions, references; A11 adds semantics."""
    bundle = validate_bundle(request["bundle"], asset_root=asset_root)
    refs = request["refs"]
    graph = resolve_artifact(bundle, refs["graph"], "QuestionGraph")
    policy = resolve_policy(bundle, refs["policy"])
    source = resolve_artifact(bundle, graph.payload.source, "SourceBundle")
    pre = resolve_artifact(bundle, refs["precheck"], "CheckReport")
    require(graph.book_id == BOOK, "BOOK_SCOPE")
    require(pre.payload.stage == "PRE_APPLY" and pre.payload.decision == "PASS" and
            pre.payload.graph.model_dump(mode="json") == artifact_ref(graph) and
            pre.payload.policy.model_dump(mode="json") == policy_ref(policy), "PRECHECK_BINDING")
    require(policy.role_mapping == {"stem": "Q", "option": "W", "answer": "A",
                                  "explanation": "E", "shared_material": "Q"} and
            policy.option_grouping == "SEPARATE", "AUTHORITATIVE_OPTION_ROLE")
    approval = request.get("approval", {})
    require(approval.get("purpose") == ("OFFLINE_A11_TEST_ONLY" if offline else "A11_LIVE_CREATE"),
            "NEW_APPROVAL_REQUIRED")
    require(approval.get("book_id") == BOOK and approval.get("operations") == ["CREATE_FRAMES"] and
            approval.get("per_question_send_limit") == 1, "AUTHORIZATION_SCOPE")
    entries = approval.get("questions", [])
    require(1 <= len(entries) <= 5 and len({e["question_id"] for e in entries}) == len(entries),
            "MANIFEST_SIZE_OR_DUPLICATE")
    require(approval.get("batch_send_limit") == len(entries), "AUTHORIZATION_LIMIT")
    require(approval.get("policy") == policy_ref(policy) and approval.get("evidence_refs"), "POLICY_ADOPTION_REFS")
    try:
        start = datetime.fromisoformat(approval["starts_at"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(approval["ends_at"].replace("Z", "+00:00"))
        clock = at or datetime.now(timezone.utc)
        require(start.tzinfo and end.tzinfo and start <= clock <= end, "AUTHORIZATION_WINDOW")
    except (KeyError, TypeError, ValueError) as exc:
        raise PilotError("AUTHORIZATION_WINDOW") from exc
    questions = graph.payload.questions
    require([e["question_id"] for e in entries] == [q.question_id for q in questions] ==
            source.payload.scope_manifest, "MANIFEST_IDENTITY_ORDER")
    require(set(request["bindings"]) == {a.asset_id for a in source.payload.assets}, "SOURCE_MAPPING")
    maps = {m.asset_id: m for m in source.payload.external_page_mappings}
    for asset in source.payload.assets:
        binding = request["bindings"][asset.asset_id]
        require(set(binding) == {"asset_id", "sha256", "width", "height", "resource_id",
                                "viewer_page", "source_page", "save_page", "evidence_refs"}, "SOURCE_MAPPING")
        require(all(binding.get(k) == getattr(asset, k) for k in ("asset_id", "sha256", "width", "height"))
                and binding["resource_id"] and binding["evidence_refs"] and
                str(binding["viewer_page"]) == maps[asset.asset_id].external_page and
                maps[asset.asset_id].mapping_status == "CONFIRMED" and
                all(type(binding[k]) is int and binding[k] >= 0 for k in ("viewer_page", "source_page", "save_page")),
                "SOURCE_MAPPING")
    facts = []
    for question, entry in zip(questions, entries):
        require(question.question_type == "ordinary_choice" and not question.parent_question_id and
                not question.shared_fragment_ids and not question.cross_page, "UNSUPPORTED_QUESTION")
        external = question.external_refs
        require(external.printed_number not in ("22", "Q22") and external.platform_question_id is None and
                external.platform_order is None, "EXISTING_OR_Q22")
        fact = question_facts(bundle, graph, question, policy, request["bindings"])
        require(len(fact["frames"]) == 6 and [p["role"] for p in fact["parts"]] == SEMANTIC_ROLES and
                [f["platform_role"] for f in fact["frames"]] == ROLES and
                len({f["fragment_id"] for f in fact["frames"]}) == 6 and
                all(f["platform_type"] == "text" for f in fact["frames"]), "SIX_FRAME_SEMANTICS")
        fragments = {f.fragment_id: f for f in graph.payload.fragments}
        require(all(fragments[p["fragment_id"]].content_type == "text" for p in fact["parts"]),
                "TEXT_CODEC_UNSUPPORTED")
        require(all(isinstance(p["text"], str) and p["text"] for p in fact["parts"]), "APPROVED_TEXT_MISSING")
        require(len(fact["relations"]) == 1 and fact["relations"][0]["status"] == "SELECTED" and
                fact["relations"][0]["selected_fragment_ids"] == [fact["parts"][-1]["fragment_id"]],
                "ANSWER_RELATION")
        require(entry.get("input_hash") == digest(fact) and entry.get("approved_parts") == fact["parts"] and
                entry.get("answer_relation") == fact["relations"][0], "APPROVAL_CONTENT_BINDING")
        require(request.get("directory_map", {}).get(question.directory_id), "DIRECTORY_MAPPING")
        facts.append(fact)
    if offline:
        require(request.get("fixture_marker") == "A11_SYNTHETIC_OFFLINE_ONLY" and
                all(a.producer.evidence_mode == "SYNTHETIC" for a in bundle.artifacts) and
                all(e.mode == "SYNTHETIC" for e in bundle.evidence) and
                policy.applicability == "SYNTHETIC_ONLY", "OFFLINE_NAMESPACE")
    else:
        require(all(a.producer.evidence_mode == "OBSERVED" for a in bundle.artifacts) and
                all(e.mode == "OBSERVED" for e in bundle.evidence) and
                all(a.provenance == "ORIGINAL" for a in source.payload.assets), "REAL_SOURCE_REQUIRED")
        require(policy.applicability == policy.confirmation_status == "JOINT_CONFIRMED", "JOINT_POLICY_REQUIRED")
        # No verified adoption/wire registry has been delivered. Labels cannot confer authority.
        raise PilotError("LIVE_FACT_REGISTRY_UNAVAILABLE", "current joint policy and text wire evidence not integrated")
    return Admission(bundle, graph, policy, tuple(facts), digest(request), digest(approval), offline)


def global_order(observation):
    require(observation.get("complete") is True and observation.get("read_status") == "OK" and
            observation.get("book_id") == BOOK and observation.get("submission_status") == "NOT_SUBMITTED",
            "FULL_TARGET_REQUIRED")
    target = observation["view"]["target"]
    questions = target["questions"]
    orders = [q["platform_order"] for q in questions]
    require(all(type(n) is int and n > 0 for n in orders) and len(set(orders)) == len(orders), "GLOBAL_ORDER_AMBIGUOUS")
    for key, records in (("platform_question_id", questions), ("platform_frame_id", target["frames"])):
        require(len({r[key] for r in records}) == len(records), "TARGET_IDENTITY_DUPLICATE")
    require(all(f["platform_question_id"] in {q["platform_question_id"] for q in questions}
                for f in target["frames"]), "FRAME_QUESTION_IDENTITY")
    require(set(target["directories"]) == {d["directory_id"] for d in observation["directory_details"]} and
            len(target["directories"]) == len(observation["directory_details"]), "DIRECTORY_INCOMPLETE")
    require(set(observation["view"]["question_content"]) == {q["platform_question_id"] for q in questions},
            "OLD_CONTENT_INCOMPLETE")
    require(all(c.get("status") == "AVAILABLE" and c.get("question_type") and c.get("parts")
                for c in observation["view"]["question_content"].values()), "OLD_CONTENT_INCOMPLETE")
    require(all(q["directory_id"] in target["directories"] for q in questions), "DIRECTORY_INCOMPLETE")
    return max(orders + [0])


def state_facts(observation):
    return {key: observation[key] for key in ("book_id", "platform_version", "view", "directory_details",
                                             "source_bindings", "submission_status", "complete")}


def check_target(admission, request, observation, *, expected=None):
    maximum = global_order(observation)
    require(observation.get("origin") == "FAKE_BACKEND_READ" and admission.offline, "INDEPENDENT_TARGET_REQUIRED")
    require(observation.get("source_ref") and type(observation.get("read_sequence")) is int and
            observation["read_sequence"] > 0 and observation.get("session_id"), "OBSERVATION_PROVENANCE")
    require(observation["source_bindings"] == request["bindings"], "SOURCE_TARGET_BINDING")
    if expected is not None:
        require(state_facts(expected) == state_facts(observation), "TARGET_CHANGED")
    snapshot = resolve_artifact(admission.bundle, request["refs"]["snapshot"], "PlatformSnapshot")
    caps = {c.name: c for c in snapshot.payload.capabilities}
    for name in ("frame_readback", "content_readback", "same_session_handoff"):
        require(name in caps and caps[name].status == "VERIFIED" and caps[name].evidence_refs,
                "CAPABILITY_UNVERIFIED", name)
        require(caps[name].platform_version == observation["platform_version"] == snapshot.payload.platform_version,
                "CAPABILITY_VERSION")
    for question in admission.questions:
        require(question["question_id"] not in observation["view"]["internal_bindings"], "ALREADY_SAVED")
        require(request["directory_map"][question["directory_id"]] in observation["view"]["target"]["directories"],
                "DIRECTORY_MAPPING")
    return maximum


def check_preservation(before, after, pid=None):
    global_order(after)
    require(before["book_id"] == after["book_id"] and before["platform_version"] == after["platform_version"] and
            before["directory_details"] == after["directory_details"] and
            before["source_bindings"] == after["source_bindings"], "OLD_DIRECTORY_OR_SOURCE_CHANGED")
    old, new = before["view"], after["view"]
    require(old["target"]["directories"] == new["target"]["directories"], "OLD_DIRECTORY_CHANGED")
    for field, key in (("questions", "platform_question_id"), ("frames", "platform_frame_id")):
        index = {item[key]: item for item in new["target"][field]}
        require(all(index.get(item[key]) == item for item in old["target"][field]), "OLD_" + field.upper() + "_CHANGED")
        old_ids = {item[key] for item in old["target"][field]}
        additions = [item for item in new["target"][field] if item[key] not in old_ids]
        require(all(item["platform_question_id"] == pid for item in additions), "UNEXPECTED_ADDITION")
    for field in ("internal_bindings", "frame_projections", "question_content"):
        require(all(new[field].get(k) == v for k, v in old[field].items()), "OLD_" + field.upper() + "_CHANGED")
    added_questions = {q["platform_question_id"] for q in new["target"]["questions"]} - {
        q["platform_question_id"] for q in old["target"]["questions"]}
    added_frames = {f["platform_frame_id"] for f in new["target"]["frames"]} - {
        f["platform_frame_id"] for f in old["target"]["frames"]}
    require(set(new["question_content"]) - set(old["question_content"]) == added_questions and
            set(new["frame_projections"]) - set(old["frame_projections"]) == added_frames, "UNEXPECTED_METADATA")
    new_bindings = {k:v for k,v in new["internal_bindings"].items() if k not in old["internal_bindings"]}
    require((not new_bindings and not added_questions) or
            (len(new_bindings) == 1 and set(new_bindings.values()) == added_questions == {pid}), "UNEXPECTED_BINDING")
    require(after["submission_status"] == "NOT_SUBMITTED", "SUBMISSION_CHANGED")


def check_observed_content(approved_parts, actual):
    require(actual is not None and actual.get("status") == "AVAILABLE", "CONTENT_UNAVAILABLE")
    require(actual.get("question_type") == "ordinary_choice" and actual.get("parts") == approved_parts,
            "CONTENT_MISMATCH")
    return "VERIFIED"


def compare_saved(plan, before, after, *, phase, previous=None):
    previous = previous or before
    require(after.get("origin") == "FAKE_BACKEND_READ" and after.get("phase") == phase and
            after.get("source_ref") and after.get("source_ref") != previous.get("source_ref") and
            type(after.get("read_sequence")) is int and after["read_sequence"] > previous["read_sequence"],
            "READBACK_NOT_INDEPENDENT")
    if phase == "reopen":
        require(after.get("session_id") != previous.get("session_id") and
                after.get("predecessor_session_id") == previous.get("session_id") and
                after.get("released_predecessor") is True, "REOPEN_CHAIN")
    else:
        require(after.get("session_id") == previous.get("session_id"), "SESSION_CHANGED")
    action = plan["action"]
    pid = after["view"]["internal_bindings"].get(action["target"]["question_id"])
    check_preservation(before, after, pid)
    comparison = compare_action_effect(action, before["view"], after["view"])
    require(comparison["effect_match"] == "MATCH", "FRAME_" + comparison["effect_match"])
    oldids = {q["platform_question_id"] for q in before["view"]["target"]["questions"]}
    require(pid not in oldids and len(after["view"]["target"]["questions"]) == len(oldids) + 1 and
            len(after["view"]["target"]["frames"]) == len(before["view"]["target"]["frames"]) + 6,
            "FRAME_COUNT_OR_IDENTITY")
    # Comparator checks projections; also compare actual type and actual raw box/role.
    frames = [f for f in after["view"]["target"]["frames"] if f["platform_question_id"] == pid]
    require([f.get("platform_type") for f in frames] == ["text"] * 6, "FRAME_TYPE")
    check_observed_content(plan["approved_parts"], after["view"]["question_content"].get(pid))
    return {"frames": "PASS", "content": "VERIFIED", "platform_question_id": pid,
            "readback_hash": digest(after), "independent_acceptance": "PENDING", "platform_fact": "OFFLINE_ONLY"}
