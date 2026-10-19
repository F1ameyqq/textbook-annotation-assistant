"""Finite Q4 checks computed from raw inputs and the separate user approval."""
from pathlib import Path

from annotation.contracts import artifact_ref, content_digest, policy_ref, validate_bundle
from annotation.source.b_q4.reader import (
    BOOK, DIRECTORY, QUESTION, SCOPE, TARGET, APPROVAL_SHA, POLICY_SHA,
    artifact, encode, inspect_source, need, sha, write_once,
)


def approved_frames(facts):
    """An approval-derived oracle, independent of plans and target projections."""
    result = []
    for i, r in enumerate(facts["approval"]["approved_regions_in_physical_order"]):
        s = next(s for s in facts["registry"]["sources"] if s["asset_id"] == r["asset_id"])
        result.append({"fragment_id": "a09-fragment-" + str(i), "region_id": r["proposal_region_id"],
            "box": {"image": {k: s[k] for k in ("asset_id", "width", "height", "sha256")}, "bbox": r["bbox"]},
            "platform_role": r["proposed_role"], "platform_type": r["content_type"], "text": r["text"]})
    return result


def compare_approved_frames(actual, facts):
    expected = approved_frames(facts)
    differences = []
    if len(actual) != len(expected):
        differences.append({"field": "frame_count", "expected": len(expected), "actual": len(actual)})
    for i, (a, e) in enumerate(zip(actual, expected)):
        for field in e:
            if a.get(field) != e[field]:
                differences.append({"frame": i, "field": field, "expected": e[field], "actual": a.get(field)})
        if set(a) != set(e):
            differences.append({"frame": i, "field": "field_inventory", "expected": sorted(e), "actual": sorted(a)})
    return differences


def add_report(bundle, graph, policy, stage, checks, root, run_id, created_at, snapshot=None, mode="OBSERVED"):
    data = bundle.model_dump(mode="json")
    proof = "ev-a09-" + stage.lower()
    resource = write_once(root, "assets/calculations/" + stage.lower() + "-" + content_digest(checks) + ".json", encode(checks))
    data["evidence"].append({"evidence_id": proof, "resource": resource, "description": "Computed Q4 comparisons against fixed approval; bounded single-question scope", "mode": mode})
    issues, results = [], []
    for name, value in checks.items():
        ok = all(value.values())
        results.append({"check_id": name, "outcome": "PASS" if ok else "FAIL", "evidence_refs": [proof],
                        "reason": "; ".join(k + "=" + str(v) for k, v in value.items())})
        if not ok:
            issues.append({"issue_id": "a09-failed-" + name, "code": "POLICY_UNRESOLVED", "scope_type": "scope", "scope_id": SCOPE,
                "evidence_refs": [proof], "severity": "blocking", "blocks": ["PLAN", "APPLY"],
                "suggested_strategy": {"strategy_id": "HUMAN_REVIEW", "max_attempts": 0, "max_cost": 0.0}, "reason": "Required Q4 comparison failed: " + name})
    source = next(a for a in bundle.artifacts if a.kind == "SourceBundle")
    evidence = next(a for a in bundle.artifacts if a.kind == "EvidenceBundle")
    coverage = {"scope_id": SCOPE, "pages_expected": list(source.payload.pages_expected), "pages_checked": list(source.payload.pages_acquired),
        "clue_ids": [c.clue_id for c in evidence.payload.coverage_clues],
        "unassigned_region_ids": [r.region_id for r in evidence.payload.regions if r.region_id not in {rid for f in graph.payload.fragments for rid in f.region_ids}]}
    report = artifact("CheckReport", "a09-" + stage.lower() + "-" + run_id, {
        "stage": stage, "subject": artifact_ref(snapshot or graph), "graph": artifact_ref(graph), "policy": policy_ref(policy),
        "snapshot": artifact_ref(snapshot) if snapshot else None, "receipt": None, "coverage": coverage, "checks": results, "issues": issues,
        "decision": "HOLD" if issues else "PASS", "reason": "Computed fixed-Q4 offline comparisons; A user approval separate from unchanged B HOLD"},
        list(bundle.artifacts), policy, run_id, created_at, mode)
    data["artifacts"].append(report)
    return validate_bundle(data, asset_root=root), report


def pre_apply(bundle, inputs, root, run_id, created_at):
    bundle = validate_bundle(bundle, asset_root=root)
    facts = inspect_source(inputs)
    source, evidence, graph = [next(a for a in bundle.artifacts if a.kind == k) for k in ("SourceBundle", "EvidenceBundle", "QuestionGraph")]
    policy = bundle.policies[0]
    selected, expected = facts["selected"], approved_frames(facts)
    regions, fragments = list(evidence.payload.regions), list(graph.payload.fragments)
    q, relations = graph.payload.questions[0], list(graph.payload.answer_relations)
    owned = set(q.fragment_ids) | {fid for rel in relations for fid in rel.selected_fragment_ids}
    covered = {rid for f in fragments if f.fragment_id in owned for rid in f.region_ids}
    ids = [r["proposal_region_id"] for r in selected]
    checks = {
        "source_integrity": {
            "all_resource_bytes": all(sha((Path(root)/e.resource.path).read_bytes()) == e.resource.sha256 for e in bundle.evidence) and
                                  all(sha((Path(root)/a.path).read_bytes()) == a.sha256 for a in source.payload.assets),
            "observed_source": source.producer.evidence_mode == evidence.producer.evidence_mode == graph.producer.evidence_mode == "OBSERVED",
            "original_images_exact": len(source.payload.assets) == 2 and all(a.provenance == "ORIGINAL" and
                {k: getattr(a, k) for k in ("asset_id", "width", "height", "sha256")} == {k: s[k] for k in ("asset_id", "width", "height", "sha256")}
                for a, s in zip(source.payload.assets, facts["registry"]["sources"])),
            "four_original_coordinates": len(regions) == 4 and all(r.box.model_dump(mode="json") == e["box"] for r, e in zip(regions, expected)),
            "raw_authority_bound": facts["provenance"]["input_sha256"]["approval"] == APPROVAL_SHA},
        "structure": {
            "one_fixed_question": len(graph.payload.questions) == 1 and q.question_id == QUESTION and q.directory_id == DIRECTORY,
            "four_semantic_roles": len(fragments) == 4 and [f.role for f in fragments] == ["stem", "stem", "stem", "answer"],
            "types_match_approval": [f.content_type for f in fragments] == [r.content_type for r in regions] == [r["content_type"] for r in selected],
            "content_match_approval": [r.text for r in regions] == [r["text"] for r in selected],
            "group_identity_and_order": [r.region_id for r in regions] == ids and [f.fragment_id for f in fragments] == [e["fragment_id"] for e in expected] and
                [list(f.region_ids) for f in fragments] == [[rid] for rid in ids] and [f.reading_order for f in fragments] == [0, 1, 2, 3],
            "stem_ownership_and_single_page": list(q.fragment_ids) == [e["fragment_id"] for e in expected[:3]] and not q.shared_fragment_ids and
                q.parent_question_id is None and q.cross_page is False and {r.box.image.asset_id for r in regions[:3]} == {"viewer-10"}},
        "answer_matching": {
            "unique_selected_answer": len(relations) == 1 and relations[0].status == "SELECTED" and relations[0].question_id == QUESTION and
                list(relations[0].candidate_fragment_ids) == list(relations[0].selected_fragment_ids) == ["a09-fragment-3"],
            "source_answer_identity": facts["case"]["answer_id"] == facts["approval"]["answer_id"] and facts["case"]["question_snapshot"]["selected_answer_id"] == facts["case"]["answer_id"],
            "original_13_span": facts["case"]["answer_snapshot"]["fragments"][0]["text_span"] == [2, 4] and regions[-1].text == "13",
            "correct_viewer_answer": regions[-1].box.image.asset_id == "viewer-173"},
        "coverage": {
            "independent_scope": list(source.payload.scope_manifest) == [QUESTION] and source.scope_id == SCOPE and APPROVAL_SHA in source.payload.scope_manifest_basis,
            "all_four_groups_owned": covered == set(ids) and len(evidence.payload.coverage_clues) == 4 and
                all(c.disposition == "ASSIGNED" and list(c.region_ids) == [ids[i]] for i, c in enumerate(evidence.payload.coverage_clues)),
            "scoped_pages": set(source.payload.pages_expected) == set(source.payload.pages_acquired) == {"viewer-10", "viewer-173"},
            "old_ocr_mapped_without_rewrite": len(facts["provenance"]["original_ocr_to_A_regions"]) == 4 and facts["provenance"]["A_disposition"]["original_facts_unchanged"] is True,
            "other_cases_HOLD": len(facts["provenance"]["other_cases"]) == 3 and all(x["status"] == "HOLD" and not x["question_relation_created"] for x in facts["provenance"]["other_cases"]),
            "no_whole_page_claim": facts["provenance"]["whole_page_coverage_claim"] is False},
        "policy": {
            "fill_blank_to_free_response": q.question_type == "free_response" and facts["approval"]["approved_content"]["question_type"] == "fill_blank",
            "roles_Q_Q_Q_A": [policy.role_mapping[f.role] for f in fragments] == ["Q", "Q", "Q", "A"],
            "image_text_text_text": [f.content_type for f in fragments] == ["image", "text", "text", "text"],
            "internal_proposal_only": policy.confirmation_status == "A_INTERNAL_PROPOSAL" and policy.applicability == "PROPOSAL_ONLY",
            "exact_authority": APPROVAL_SHA in policy.source_notes[0] and POLICY_SHA in policy.source_notes[1],
            "no_W_or_E": not any(f.role in ("option", "shared_material", "explanation") for f in fragments),
            "B_HOLD_separate": facts["case"]["decision"] == "HOLD" and all(v is False for v in facts["proposal"]["approvals"].values()) and not facts["provenance"]["B_joint_adoption"]}}
    return add_report(bundle, graph, policy, "PRE_APPLY", checks, root, run_id, created_at)


def target_check(bundle, target, snapshot, root, run_id, created_at, execution_mode="SIMULATED"):
    graph = next(a for a in bundle.artifacts if a.kind == "QuestionGraph")
    policy = bundle.policies[0]
    view = target.snapshot_view()
    payload = snapshot["payload"]
    checks = {
        "target_version": {"current_snapshot": payload["observed_hash"] == content_digest(view) and payload["observed_version"] == target.version,
            "fresh_empty": view["epoch"] == 0 and not view["target"]["questions"] and not view["target"]["frames"] and not view["internal_bindings"] and not view["frame_projections"]},
        "authorized_scope": {"book": target.book_id == BOOK, "target": target.target_id == TARGET, "scope": target.scope_id == SCOPE,
            "directory": view["target"]["directories"] == [DIRECTORY] and all(q.directory_id == DIRECTORY for q in graph.payload.questions)},
        "capabilities": {"create_only": target.operations == ("CREATE_FRAMES",), "memory_readback": target.supports_readback is True and callable(target.observe),
            "same_session": target.session_mode == "SAME_SESSION_HANDOFF"},
        "policy": {"simulated_only": execution_mode == "SIMULATED", "internal": policy.confirmation_status == "A_INTERNAL_PROPOSAL" and policy.applicability == "PROPOSAL_ONLY",
            "source_observed": graph.producer.evidence_mode == "OBSERVED"}}
    need(all(all(v.values()) for v in checks.values()), "TARGET", "TARGET_SCOPE_OR_CURRENTNESS", "target identity, mode, capabilities or current state rejected")
    snap = next(a for a in bundle.artifacts if a.kind == "PlatformSnapshot")
    return add_report(bundle, graph, policy, "TARGET", checks, root, run_id, created_at, snap, "SYNTHETIC")
