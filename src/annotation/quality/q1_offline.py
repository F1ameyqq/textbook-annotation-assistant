"""Actual finite PRE_APPLY/TARGET calculations; reports only, no target mutation."""
from pathlib import Path
from annotation.contracts import artifact_ref, content_digest, policy_ref, validate_bundle
from annotation.source.b_q1.reader import (
    BOOK, DIRECTORY, QUESTION, SCOPE, TARGET, APPROVAL_SHA, POLICY_SHA,
    artifact, encode, inspect_source, need, sha, write_once,
)


def add_report(bundle, graph, policy, stage, checks, root, run_id, created_at, snapshot=None, mode="OBSERVED"):
    data = bundle.model_dump(mode="json")
    proof = "ev-a07-" + stage.lower()
    resource = write_once(root, "assets/calculations/" + stage.lower() + ".json", encode(checks))
    data["evidence"].append({"evidence_id": proof, "resource": resource, "description": "Actual A07 comparisons, fixed scope only", "mode": mode})
    issues = []
    results = []
    for name, value in checks.items():
        ok = all(value.values())
        results.append({"check_id": name, "outcome": "PASS" if ok else "FAIL", "evidence_refs": [proof],
                        "reason": "; ".join(k + "=" + str(v) for k, v in value.items())})
        if not ok:
            issues.append({"issue_id": "a07-failed-" + name, "code": "POLICY_UNRESOLVED", "scope_type": "scope", "scope_id": SCOPE,
                "evidence_refs": [proof], "severity": "blocking", "blocks": ["PLAN", "APPLY"],
                "suggested_strategy": {"strategy_id": "HUMAN_REVIEW", "max_attempts": 0, "max_cost": 0.0},
                "reason": "Actual required comparison failed: " + name})
    source = next(a for a in bundle.artifacts if a.kind == "SourceBundle")
    evidence = next(a for a in bundle.artifacts if a.kind == "EvidenceBundle")
    coverage = {"scope_id": SCOPE, "pages_expected": list(source.payload.pages_expected),
        "pages_checked": list(source.payload.pages_acquired), "clue_ids": [x.clue_id for x in evidence.payload.coverage_clues],
        "unassigned_region_ids": [x.region_id for x in evidence.payload.regions if x.region_id not in
                                 {r for f in graph.payload.fragments for r in f.region_ids}]}
    report = artifact("CheckReport", "a07-" + stage.lower() + "-" + run_id, {
        "stage": stage, "subject": artifact_ref(snapshot or graph), "graph": artifact_ref(graph), "policy": policy_ref(policy),
        "snapshot": artifact_ref(snapshot) if snapshot else None, "receipt": None, "coverage": coverage,
        "checks": results, "issues": issues, "decision": "HOLD" if issues else "PASS",
        "reason": "Actual fixed Q1 offline checks; A-only authorization; original B HOLD/ledger retained"},
        list(bundle.artifacts), policy, run_id, created_at, mode)
    data["artifacts"].append(report)
    return validate_bundle(data, asset_root=root), report


def pre_apply(bundle, inputs, root, run_id, created_at):
    bundle = validate_bundle(bundle, asset_root=root)
    facts = inspect_source(inputs)
    source, evidence, graph = [next(a for a in bundle.artifacts if a.kind == k) for k in ("SourceBundle", "EvidenceBundle", "QuestionGraph")]
    policy = bundle.policies[0]
    selected = facts["selected"]
    ids = [r["region_id"] for r in selected]
    regions = list(evidence.payload.regions)
    fragments = list(graph.payload.fragments)
    q = graph.payload.questions[0]
    relations = list(graph.payload.answer_relations)
    content = facts["candidate"]["payload"]["candidate_content"]
    texts = [content["stem_body_normalized_without_number"]] + content["option_texts"] + [content["answer_text"]]
    owners = set(q.fragment_ids)
    owners.update(f for rel in relations for f in rel.selected_fragment_ids)
    covered = {rid for f in fragments if f.fragment_id in owners for rid in f.region_ids}
    checks = {
        "source_integrity": {"all_resources_validated": all(sha((Path(root) / e.resource.path).read_bytes()) == e.resource.sha256 for e in bundle.evidence) and
                all(sha((Path(root) / a.path).read_bytes()) == a.sha256 for a in source.payload.assets),
            "observed_source": source.producer.evidence_mode == evidence.producer.evidence_mode == graph.producer.evidence_mode == "OBSERVED",
            "original_assets": all(a.provenance == "ORIGINAL" for a in source.payload.assets), "input_binding": facts["policy"]["input_sha256"] == facts["provenance"]["input_sha256"],
            "original_coordinates": len(regions) == 6 and all(r.box.bbox == b["bbox"] and r.box.image.asset_id == b["asset_id"] and r.box.image.sha256 == b["source_sha256"] for r, b in zip(regions, selected))},
        "structure": {"one_question": len(graph.payload.questions) == 1 and q.question_id == QUESTION,
            "six_owned_groups": len(fragments) == 6 and [f.role for f in fragments] == ["stem", "option", "option", "option", "option", "answer"],
            "content": [r.text for r in regions] == texts,
            "group_identity": [r.region_id for r in regions] == ids and [list(f.region_ids) for f in fragments] == [[rid] for rid in ids],
            "no_explanation": not any(f.role == "explanation" for f in fragments)},
        "answer_matching": {"unique_selected_relation": len(relations) == 1 and relations[0].status == "SELECTED" and relations[0].question_id == QUESTION and
                list(relations[0].candidate_fragment_ids) == list(relations[0].selected_fragment_ids) == [fragments[-1].fragment_id],
            "original_span": facts["provenance"]["answer_source_span"]["source_text_span"] == [2, 3],
            "source_D": regions[-1].text == facts["provenance"]["native_answer"]["text"] == "D"},
        "coverage": {"independent_single_question_scope": list(source.payload.scope_manifest) == [QUESTION] and source.scope_id == SCOPE and APPROVAL_SHA in source.payload.scope_manifest_basis,
            "all_required_groups_owned": covered == set(ids) and len(evidence.payload.coverage_clues) == 6 and
                all(c.disposition == "ASSIGNED" for c in evidence.payload.coverage_clues),
            "scoped_pages_checked": set(source.payload.pages_acquired) == set(source.payload.pages_expected) == {r["asset_id"] for r in selected},
            "native_fragments_accounted": len([f for r in selected for f in r["source_fragment_ids"]]) == 7,
            "thirty_bound_exclusions": len([d for d in facts["dispositions"] if d["disposition"] == "OUTSIDE_FIXED_SINGLE_QUESTION"]) == 30,
            "no_whole_page_claim": facts["provenance"]["whole_page_coverage_claim"] is False},
        # Original ordinary-choice rule: 项目交接说明.md:72/98, option -> W.
        "policy": {"ordinary_choice": len(graph.payload.questions) == 1 and q.question_type == "ordinary_choice",
            "ordinary_choice_role_mapping": [policy.role_mapping[f.role] for f in sorted(fragments, key=lambda f: (f.reading_order, f.fragment_id))] == ["Q", "W", "W", "W", "W", "A"],
            "separate_options": policy.option_grouping == "SEPARATE", "internal_only": policy.confirmation_status == "A_INTERNAL_PROPOSAL" and policy.applicability == "PROPOSAL_ONLY",
            "exact_authorization": APPROVAL_SHA in policy.source_notes[0] and POLICY_SHA in policy.source_notes[1],
            "all_scoped_issues_disposed": len(facts["dispositions"]) == 31 and all(d["original_issue_unchanged"] for d in facts["dispositions"]),
            "business_review_by_user": len([d for d in facts["dispositions"] if d["disposition"] == "A_USER_APPROVED_FOR_FIXED_OFFLINE_SCOPE"]) == 1}}
    return add_report(bundle, graph, policy, "PRE_APPLY", checks, root, run_id, created_at)


def target_check(bundle, target, snapshot, root, run_id, created_at, execution_mode="SIMULATED"):
    graph = next(a for a in bundle.artifacts if a.kind == "QuestionGraph")
    policy = bundle.policies[0]
    view = target.snapshot_view()
    fixed = view["target"]
    payload = snapshot["payload"]
    checks = {
        "target_version": {"current_snapshot": payload["observed_hash"] == content_digest(view) and payload["observed_version"] == target.version,
            "fresh_empty_target": view["epoch"] == 0 and not fixed["questions"] and not fixed["frames"] and not view["internal_bindings"]},
        "authorized_scope": {"mode": execution_mode == "SIMULATED", "book": target.book_id == BOOK,
            "target": target.target_id == TARGET, "scope": target.scope_id == SCOPE,
            "directory": fixed["directories"] == [DIRECTORY] and all(q.directory_id == DIRECTORY for q in graph.payload.questions)},
        "capabilities": {"create_frames_only": target.operations == ("CREATE_FRAMES",),
            "memory_readback": target.supports_readback is True and callable(target.observe) and target.snapshot_view() == view,
            "same_session": target.session_mode == "SAME_SESSION_HANDOFF"},
        "policy": {"A_offline_only": policy.confirmation_status == "A_INTERNAL_PROPOSAL" and policy.applicability == "PROPOSAL_ONLY",
            "no_platform": execution_mode == "SIMULATED", "source_observed": graph.producer.evidence_mode == "OBSERVED"}}
    # Invalid target facts remain an explicit rejection, never a caller PASS flag.
    need(all(all(v.values()) for v in checks.values()), "TARGET", "TARGET_SCOPE_OR_CURRENTNESS", "target mode, identity, scope, capability or currentness rejected")
    snap = next(a for a in bundle.artifacts if a.kind == "PlatformSnapshot")
    return add_report(bundle, graph, policy, "TARGET", checks, root, run_id, created_at, snap, "SYNTHETIC")
