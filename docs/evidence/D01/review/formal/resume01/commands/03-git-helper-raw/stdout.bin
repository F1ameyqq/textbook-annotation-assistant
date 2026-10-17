"""Deterministic, entirely synthetic C01 exchange examples (Python 3.9)."""
import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

from annotation.contracts import (
    ContractError, artifact_ref, assert_plan_ready, load_bundle, policy_ref,
    seal_artifact, seal_policy, validate_bundle, write_bundle,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "contracts"
TIMESTAMP = "2026-10-16T00:00:00Z"
SCHEMA_VERSION = "1.0.0-a-proposal"
PAGES = ["asset-page-a1", "asset-page-a2", "asset-page-b1"]
QUESTIONS = ["question-alpha", "question-child", "question-beta"]


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def resource(folder, relative, data, media_type):
    target = folder / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "media_type": media_type}


def policy(synthetic_choice=False):
    return seal_policy({
        "policy_id": "synthetic-choice-separate" if synthetic_choice else "usense-v1-proposal",
        "revision": 1,
        "confirmation_status": "SYNTHETIC_ASSUMPTION" if synthetic_choice else "A_INTERNAL_PROPOSAL",
        "option_grouping": "SEPARATE" if synthetic_choice else "UNRESOLVED",
        "role_mapping": {"stem": "Q", "option": "W", "answer": "A", "explanation": "E", "shared_material": "Q"},
        "source_notes": [
            "A-side v1 implementation proposal; no joint A/B confirmation is asserted.",
            "DOCX separate option boxes and sampled video combined option box remain unresolved.",
            "A05 observed only bounded frame-save/readback behavior; OCR was not accepted.",
        ] + (["SEPARATE is an explicit fabricated assumption for SIMULATED examples only."] if synthetic_choice else []),
        "frame_save_status": "SYNTHETIC" if synthetic_choice else "BOUNDED_A05_OBSERVED",
        "ocr_status": "SYNTHETIC" if synthetic_choice else "UNVERIFIED",
        "applicability": "SYNTHETIC_ONLY" if synthetic_choice else "PROPOSAL_ONLY",
    })


def summary(bundle):
    """Consumer-facing exact comparison; it uses only public model/API surfaces."""
    data = bundle.model_dump(mode="json")
    artifacts = data["artifacts"]
    by_kind = lambda kind: [a for a in artifacts if a["kind"] == kind]
    graph = max(by_kind("QuestionGraph"), key=lambda a: a["revision"])
    plan = by_kind("ApplyPlan")[0]
    snapshot = by_kind("PlatformSnapshot")[0]
    receipt = by_kind("ExecutionReceipt")[0]
    batch = by_kind("BatchReport")[0]
    ready = "PASS"
    readiness_issue_codes = []
    try:
        assert_plan_ready(bundle, artifact_ref(plan), artifact_ref(snapshot))
    except ContractError as error:
        ready = "BLOCKED"
        readiness_issue_codes = [item["code"] for item in error.issues]
    return {
        "format_version": data["format_version"],
        "schema_version": graph["schema_version"],
        "provenance": "SYNTHETIC; no browser, recognition, OCR, executor or paid model was used",
        "kind_counts": dict(sorted(Counter(a["kind"] for a in artifacts).items())),
        "artifact_hashes": {a["artifact_id"] + "@" + str(a["revision"]): a["content_hash"] for a in artifacts},
        "graph_revision": graph["revision"],
        "questions": [{"question_id": q["question_id"], "directory_id": q["directory_id"],
                       "printed_number": q["external_refs"]["printed_number"],
                       "cross_page": q["cross_page"], "shared_fragment_ids": q["shared_fragment_ids"]}
                      for q in graph["payload"]["questions"]],
        "check_decisions": {a["payload"]["stage"]: a["payload"]["decision"] for a in by_kind("CheckReport")},
        "plan": {"readiness": plan["payload"]["readiness"], "readiness_check": ready,
                 "readiness_issue_codes": readiness_issue_codes,
                 "execution_mode": plan["payload"]["execution_mode"],
                 "action_count": len(plan["payload"]["actions"]), "final_submission": plan["payload"]["final_submission"]},
        "receipt": {"execution_mode": receipt["payload"]["execution_mode"],
                    "outcomes": [r["outcome"] for r in receipt["payload"]["results"]],
                    "next_steps": [r["next_step"] for r in receipt["payload"]["results"]],
                    "replay_allowed": [r["replay_allowed"] for r in receipt["payload"]["results"]],
                    "write_disposition": receipt["payload"]["write_disposition"]},
        "batch": {key: batch["payload"][key] for key in ("state", "total_expected", "scope_manifest",
                   "questions", "submission_status", "content_check_status", "frame_check_status", "cost")},
        "policy": {key: data["policies"][0][key] for key in ("confirmation_status", "option_grouping",
                   "frame_save_status", "ocr_status", "applicability")},
    }


def build_case(name):
    folder = FIXTURES / name
    folder.mkdir(parents=True, exist_ok=True)
    exceptional, unknown, choice = name == "exception", name == "unknown", name == "choice-assumption"
    active_policy = policy(choice)
    pref = policy_ref(active_policy)
    artifacts = []
    manifest = QUESTIONS + (["question-missing"] if exceptional else [])
    records = []
    for evidence_id, description in [
        ("proof-source", "Synthetic original assets and external page mapping."),
        ("proof-geometry", "Hand-authored original boxes, coverage and invertible transform; not detector output."),
        ("proof-checks", "Constructed quality assertions, never platform acceptance."),
        ("proof-target", "Invented same-session target state and capabilities."),
        ("proof-before", "Invented per-action state before simulated write."),
        ("proof-after", "Invented readback including final synthetic content."),
        ("proof-timeout", "Simulated response timeout with no conclusive readback; no duplicate dispatch permitted."),
        ("proof-patch", "Synthetic review changed printed label; baseline and result revisions remain separate."),
    ]:
        records.append({"evidence_id": evidence_id,
                        "resource": resource(folder, "assets/" + evidence_id + ".txt", (description + "\n").encode("utf-8"), "text/plain"),
                        "description": description, "mode": "SYNTHETIC"})

    assets = []
    for index, page in enumerate(PAGES):
        pixels = bytearray([255] * 8000)
        # Each file is a valid 80x100 P5 original image, visibly fabricated.
        for y in range(5 + index, 90, 15):
            for x in range(5, 65):
                pixels[y * 80 + x] = 32 + index * 24
        res = resource(folder, "assets/" + page + ".pgm", b"P5\n80 100\n255\n" + bytes(pixels), "image/x-portable-graymap")
        assets.append(dict(res, asset_id=page, width=80, height=100,
                           source_label="Synthetic original page " + str(index + 1), provenance="SYNTHETIC"))
    history = resource(folder, "assets/history.json", json_bytes({"provenance": "SYNTHETIC", "usable_as_gold": False}), "application/json")

    def add(kind, identity, payload, dependencies=(), revision=1):
        unique_dependencies = {(a["artifact_id"], a["revision"]): a for a in dependencies}
        result = seal_artifact({
            "schema_version": SCHEMA_VERSION, "artifact_id": identity, "revision": revision, "kind": kind,
            "run_id": "synthetic-run-" + name, "book_id": "synthetic-book", "scope_id": "synthetic-scope",
            "input_refs": [artifact_ref(a) for a in unique_dependencies.values()],
            "producer": {"module": "synthetic-fixtures", "implementation_version": "c01-fixtures-1",
                         "config_version": "fixed-1", "policy_versions": [pref], "model_version": None,
                         "prompt_version": None, "evidence_mode": "SYNTHETIC"},
            "created_at": TIMESTAMP, "payload": payload,
        })
        artifacts.append(result)
        return result

    source = add("SourceBundle", "source-" + name, {
        "assets": assets, "directories": [{"directory_id": "directory-a", "parent_id": None, "label": "Unit A"},
                                             {"directory_id": "directory-b", "parent_id": None, "label": "Unit B"}],
        "pages_expected": PAGES, "pages_acquired": PAGES,
        "external_page_mappings": [{"asset_id": page, "directory_id": "directory-a" if i < 2 else "directory-b",
                                    "external_page": str(i + 1), "mapping_status": "CONFIRMED", "evidence_refs": ["proof-source"]}
                                   for i, page in enumerate(PAGES)],
        "history": [{"resource": history, "quality": "UNVERIFIED", "reason": "Fabricated history is not gold data."}],
        "scope_manifest": manifest, "scope_manifest_basis": "Explicit synthetic independent question inventory; omitted candidates remain in denominator.",
        "metadata_page_count": 250,
    })

    def box(page_index, coordinates):
        asset = assets[page_index]
        return {"image": {key: asset[key] for key in ("asset_id", "width", "height", "sha256")},
                "bbox": [float(v) for v in coordinates]}

    region_specs = [
        ("region-alpha-start", 0, [5, 5, 65, 20], "text", "1. Parent problem begins; continues on next page."),
        ("region-shared", 0, [5, 25, 65, 35], "text", "Shared material for alpha and its child."),
        ("region-alpha-end", 1, [5, 5, 65, 20], "formula", "Parent continuation: x + 1 = 3."),
        ("region-alpha-answer", 1, [5, 25, 65, 35], "formula", "x = 2"),
        ("region-child-stem", 1, [5, 40, 65, 50], "text", "(a) Explain the shared material."),
        ("region-child-answer", 1, [5, 55, 65, 65], "text", "Synthetic explanation."),
        ("region-beta-stem", 2, [5, 5, 65, 20], "text", "1. Independent Unit B problem."),
        ("region-beta-answer", 2, [5, 60, 65, 70], "text", "Unit B answer; cannot match Unit A by printed label."),
    ]
    if choice or exceptional:
        region_specs += [("region-option-a", 2, [5, 25, 35, 35], "text", "A. First option"),
                         ("region-option-b", 2, [40, 25, 70, 35], "text", "B. Second option")]
    regions, clues = [], []
    for identity, page, coordinates, content_type, text in region_specs:
        transform = {"scale_x": 1.0, "scale_y": 1.0, "offset_x": 0.0, "offset_y": 0.0,
                     "rotation_degrees": 0.0, "padding": [0.0, 0.0, 0.0, 0.0],
                     "processed_width": 80, "processed_height": 100, "invertible": True}
        if identity == "region-alpha-answer":
            transform.update(scale_x=2.0, scale_y=2.0, offset_x=10.0, offset_y=200.0,
                             processed_width=170, processed_height=400)
        regions.append({"region_id": identity, "box": box(page, coordinates), "crop_transform": transform,
                        "content_type": content_type, "text": text, "source": "SYNTHETIC",
                        "evidence_refs": ["proof-geometry"], "printed_number_candidates": ["1"] if "stem" in identity or "start" in identity else [],
                        "certainty": "CONFIRMED"})
        clues.append({"clue_id": "clue-" + identity.removeprefix("region-"), "box": box(page, coordinates),
                      "source": "SYNTHETIC", "disposition": "ASSIGNED", "region_ids": [identity],
                      "reason": "Independent synthetic full-page inventory assigns this content region.", "evidence_refs": ["proof-geometry"]})
    if exceptional:
        clues.append({"clue_id": "clue-missing-whole-question", "box": box(2, [5, 80, 65, 95]),
                      "source": "WHOLE_PAGE_SCAN", "disposition": "UNASSIGNED", "region_ids": [],
                      "reason": "Entire scoped question-missing was absent from the candidate list; independent page coverage found its box.",
                      "evidence_refs": ["proof-geometry"]})
    evidence = add("EvidenceBundle", "evidence-" + name, {"source": artifact_ref(source), "regions": regions,
                                                          "coverage_clues": clues}, [source])
    fragments = []
    roles = {"alpha-start": "stem", "shared": "shared_material", "alpha-end": "stem", "alpha-answer": "answer",
             "child-stem": "stem", "child-answer": "answer", "beta-stem": "stem", "beta-answer": "answer",
             "option-a": "option", "option-b": "option"}
    for i, r in enumerate(regions):
        suffix = r["region_id"][len("region-"):]
        fragments.append({"fragment_id": "fragment-" + suffix, "region_ids": [r["region_id"]], "role": roles[suffix],
                          "content_type": r["content_type"], "reading_order": i})
    questions = []
    for identity, directory, kind, fragment_ids, shared, parent, cross in [
        ("question-alpha", "directory-a", "combination", ["fragment-alpha-start", "fragment-alpha-end", "fragment-alpha-answer"], ["fragment-shared"], None, True),
        ("question-child", "directory-a", "free_response", ["fragment-child-stem", "fragment-child-answer"], ["fragment-shared"], "question-alpha", True),
        ("question-beta", "directory-b", "ordinary_choice" if choice or exceptional else "free_response",
         ["fragment-beta-stem", "fragment-beta-answer"] + (["fragment-option-a", "fragment-option-b"] if choice or exceptional else []), [], None, False),
    ]:
        questions.append({"question_id": identity, "directory_id": directory, "question_type": kind,
                          "fragment_ids": fragment_ids, "parent_question_id": parent, "shared_fragment_ids": shared,
                          "cross_page": cross, "external_refs": {"printed_number": "1?" if identity == "question-alpha" else "(a)" if parent else "1",
                                                                   "platform_question_id": None, "platform_order": None}})
    graph_payload = {"source": artifact_ref(source), "evidence": artifact_ref(evidence), "questions": questions,
                     "fragments": fragments,
                     "answer_relations": [{"relation_id": "relation-" + suffix, "question_id": "question-" + suffix,
                                           "candidate_fragment_ids": ["fragment-" + suffix + "-answer"],
                                           "selected_fragment_ids": ["fragment-" + suffix + "-answer"], "status": "SELECTED",
                                           "evidence_refs": ["proof-checks"]} for suffix in ("alpha", "child", "beta")],
                     "identity_notes": "Stable IDs do not derive from bbox, printed label or platform order; repeated printed 1 remains in distinct directories."}
    baseline = add("QuestionGraph", "graph-" + name, graph_payload, [source, evidence])
    patch = add("ReviewPatch", "patch-" + name, {
        "baseline": artifact_ref(baseline), "result_revision": 2,
        "changes": [{"entity_id": "question-alpha", "field": "printed_number", "before": "1?", "after": "1"}],
        "operator": "synthetic-reviewer", "reason": "Demonstrate immutable baseline and explicitly rechecked new revision.",
        "related_issue_ids": [], "requires_recheck": True,
    }, [baseline])
    revised_payload = copy.deepcopy(graph_payload)
    revised_payload["questions"][0]["external_refs"]["printed_number"] = "1"
    graph = add("QuestionGraph", "graph-" + name, revised_payload, [source, evidence, baseline, patch], revision=2)
    snapshot_payload = {"target_id": "synthetic-target", "observed_at": TIMESTAMP, "platform_version": "synthetic-platform-1",
                        "observed_version": "synthetic-empty-v1", "observed_hash": hashlib.sha256(b"synthetic-empty-target-v1").hexdigest(),
                        "authorized_scope_id": "synthetic-scope", "directories": ["directory-a", "directory-b"],
                        "questions": [], "frames": [], "evidence_refs": ["proof-target"],
                        "capabilities": [{"name": cap, "status": "VERIFIED" if cap in ("frame_readback", "same_session_handoff") else "UNKNOWN",
                                          "platform_version": "synthetic-platform-1", "evidence_refs": ["proof-target"] if cap in ("frame_readback", "same_session_handoff") else []}
                                         for cap in ("persistent_draft", "frame_readback", "content_readback", "ocr_before_submit", "resume_after_restart", "multi_session", "same_session_handoff")]}
    snapshot = add("PlatformSnapshot", "snapshot-" + name, snapshot_payload)
    coverage = {"scope_id": "synthetic-scope", "pages_expected": PAGES, "pages_checked": PAGES,
                "clue_ids": [c["clue_id"] for c in clues], "unassigned_region_ids": []}

    def issue(identity, code, scope_type, scope_id, blocks, strategy, reason):
        return {"issue_id": identity, "code": code, "scope_type": scope_type, "scope_id": scope_id,
                "evidence_refs": ["proof-timeout" if code == "SAVE_UNKNOWN" else "proof-checks"],
                "severity": "blocking", "blocks": blocks,
                "suggested_strategy": {"strategy_id": strategy, "max_attempts": 0, "max_cost": 0.0}, "reason": reason}

    pre_issues = []
    if exceptional:
        pre_issues = [issue("issue-policy", "POLICY_UNRESOLVED", "question", "question-beta", ["PLAN", "APPLY"], "HUMAN_REVIEW", "Separate versus combined W is not jointly decided."),
                      issue("issue-missing", "UNASSIGNED_CONTENT", "question", "question-missing", ["PLAN", "COMPLETE"], "HUMAN_REVIEW", "Full-page clue found an entire omitted scoped question.")]
    def check(stage, identity, subject, receipt=None):
        names = {"PRE_APPLY": ["source_integrity", "structure", "answer_matching", "coverage", "policy"],
                 "TARGET": ["target_version", "authorized_scope", "capabilities", "policy"],
                 "POST_APPLY": ["frame_structure", "final_content"]}[stage]
        issues = pre_issues if stage != "POST_APPLY" else post_issues
        failed = set()
        if exceptional:
            failed = {"coverage", "policy"} if stage == "PRE_APPLY" else {"policy"} if stage == "TARGET" else set(names)
        if stage == "POST_APPLY" and unknown:
            failed = set(names)
        return add("CheckReport", identity, {
            "stage": stage, "subject": artifact_ref(subject), "graph": artifact_ref(graph), "policy": pref,
            "snapshot": artifact_ref(snapshot) if stage != "PRE_APPLY" else None,
            "receipt": artifact_ref(receipt) if receipt else None, "coverage": copy.deepcopy(coverage),
            "checks": [{"check_id": n, "outcome": "UNAVAILABLE" if stage == "POST_APPLY" and n in failed else "FAIL" if n in failed else "PASS",
                        "evidence_refs": ["proof-checks"], "reason": "Explicit synthetic check: " + n + (" cannot pass in this constructed case." if n in failed else " passed for the declared synthetic scope.")}
                       for n in names],
            "issues": issues, "decision": "EXCEPTION" if exceptional else "HOLD" if stage == "POST_APPLY" and unknown else "PASS",
            "reason": "Diagnostic contract fixture; not measured algorithm quality or platform acceptance.",
        }, [graph, subject] + ([snapshot] if subject is not snapshot else []) + ([receipt] if receipt and subject is not receipt else []))
    precheck = check("PRE_APPLY", "precheck-" + name, graph)
    targetcheck = check("TARGET", "targetcheck-" + name, snapshot)
    actions = []
    if not exceptional:
        for q in revised_payload["questions"]:
            actions.append({"action_id": "action-" + q["question_id"][len("question-"):],
                            "target": {"target_id": "synthetic-target", "question_id": q["question_id"], "platform_question_id": None},
                            "source_entity_ids": q["fragment_ids"] + q["shared_fragment_ids"],
                            "expected_before": {"question_exists": False}, "operation": "CREATE_FRAMES",
                            "expected_after": {"question_exists": True, "fragment_count": len(q["fragment_ids"]) + len(q["shared_fragment_ids"])},
                            "depends_on": []})
    plan = add("ApplyPlan", "plan-" + name, {
        "graph": artifact_ref(graph), "precheck": artifact_ref(precheck), "targetcheck": artifact_ref(targetcheck),
        "snapshot": artifact_ref(snapshot), "policy": pref, "readiness": "BLOCKED" if exceptional else "READY",
        "execution_mode": "SIMULATED", "session_mode": "SAME_SESSION_HANDOFF", "required_capabilities": ["frame_readback", "same_session_handoff"],
        "actions": actions, "blocked_issue_ids": [i["issue_id"] for i in pre_issues], "previous_receipt": None, "final_submission": "HUMAN_ONLY",
    }, [graph, precheck, targetcheck, snapshot])
    readback = resource(folder, "assets/readback.json", json_bytes({"mode": "SYNTHETIC", "observed": not unknown,
        "questions": [{"question_id": q, "platform_question_id": "synthetic-platform-" + q, "frame_structure_matches": True,
                       "final_content": "Fabricated complete content; no OCR was run."} for q in QUESTIONS] if not unknown else [],
        "timeout_note": "The invented remote effect may already exist; absence of a response proves neither success nor failure." if unknown else None}), "application/json")
    results = []
    for action in actions:
        results.append({"action_id": action["action_id"], "outcome": "UNKNOWN" if unknown else "APPLIED",
                        "platform_ids": [] if unknown else ["synthetic-platform-" + action["target"]["question_id"]],
                        "before_evidence_refs": ["proof-before"], "after_evidence_refs": ["proof-timeout"] if unknown else ["proof-after"],
                        "readback": None if unknown else readback, "effect_match": "INDETERMINATE" if unknown else "MATCH",
                        "next_step": "RECONCILE" if unknown else "POSTCHECK", "replay_allowed": False,
                        "reason": "Simulated timeout; reconcile before any further writing." if unknown else "Fabricated matching frame/content readback."})
    save_issue = issue("issue-save-unknown", "SAVE_UNKNOWN", "action", "action-alpha", ["APPLY", "COMPLETE"], "RECONCILE", "Simulated save may have succeeded; do not automatically resend.")
    post_issues = pre_issues if exceptional else [save_issue] if unknown else []
    receipt = add("ExecutionReceipt", "receipt-" + name, {
        "plan": artifact_ref(plan), "execution_mode": "NOT_EXECUTED" if exceptional else "SIMULATED", "results": results,
        "unresolved_issue_ids": [i["issue_id"] for i in post_issues],
        "write_disposition": "NOT_EXECUTED" if exceptional else "PAUSE_RECONCILE" if unknown else "POSTCHECK",
    }, [plan])
    postcheck = check("POST_APPLY", "postcheck-" + name, receipt, receipt)
    statuses = [{"question_id": q, "state": "SKIPPED" if q == "question-missing" else "EXCEPTION" if exceptional else "UNKNOWN" if unknown else "VERIFIED",
                 "reason": "Entire scoped question omitted from candidates; denominator retained." if q == "question-missing" else "Constructed " + name + " contract state."}
                for q in manifest]
    add("BatchReport", "batch-" + name, {
        "source": artifact_ref(source), "graph": artifact_ref(graph), "receipt": artifact_ref(receipt), "postcheck": artifact_ref(postcheck),
        "scope_manifest": manifest, "questions": statuses, "total_expected": len(manifest), "coverage": copy.deepcopy(coverage),
        "cost": {"model_calls": 0, "amount": 0.0, "currency": "CNY", "billing_status": "KNOWN", "human_minutes": 0.0},
        "unresolved_issue_ids": [i["issue_id"] for i in post_issues], "submission_status": "NOT_SUBMITTED", "submission_evidence_refs": [],
        "content_check_status": "UNAVAILABLE" if exceptional else "PENDING" if unknown else "VERIFIED",
        "frame_check_status": "UNAVAILABLE" if exceptional or unknown else "PASS",
        "state": "NEEDS_REVIEW" if exceptional else "NEEDS_RECONCILIATION" if unknown else "READY_FOR_SUBMISSION",
    }, [source, graph, receipt, postcheck])
    raw = {"format_version": "c01-exchange-1", "evidence": records, "policies": [active_policy], "artifacts": artifacts}
    # The public writer is immutable; this explicit builder alone regenerates fixtures.
    bundle = validate_bundle(raw, asset_root=folder)
    if (folder / "input.json").exists():
        (folder / "input.json").unlink()
    write_bundle(bundle, folder / "input.json")
    bundle = load_bundle(folder / "input.json")
    (folder / "expected.json").write_bytes(json_bytes(summary(bundle)))
    purpose = {
        "normal": "No option fragments: content and target checks PASS under the unresolved W proposal. Simulated matching readback produces READY_FOR_SUBMISSION, NOT_SUBMITTED; no real completion is asserted.",
        "exception": "Ordinary-choice W policy remains UNRESOLVED and whole-page coverage finds an omitted scoped question. Diagnostic plan is BLOCKED, receipt is NOT_EXECUTED, and all four denominator entries remain in the batch.",
        "unknown": "The fake save response times out. Results remain UNKNOWN/INDETERMINATE/RECONCILE and replay_allowed=false. Batch pauses in NEEDS_RECONCILIATION with content PENDING, never COMPLETED.",
        "choice-assumption": "Ordinary-choice W is SEPARATE only under an explicit SYNTHETIC_ASSUMPTION/SYNTHETIC_ONLY policy and SIMULATED plan. This is not a business decision or a jointly confirmed interface.",
    }[name]
    readme = """# C01 {name} fixed exchange fixture

Version: c01-fixtures-1; contract {version}; A-side implementation proposal, pending joint confirmation.

{purpose}

Every image, question, capability, quality assertion, platform identity and receipt is **SYNTHETIC**. No original textbook, login, browser, paid model, OCR, algorithm or platform executor was used. The proposal policy's bounded A05 note describes its policy provenance; it does not turn this fixture into A05 evidence.

The closed exchange includes all nine artifact kinds, three CheckReports (PRE_APPLY/TARGET/POST_APPLY), and both QuestionGraph revisions around a ReviewPatch. Three tiny original P5 grayscale pages are 80 x 100 pixels. Metadata says 250 pages while exactly three are acquired and scoped; metadata never asserts all pages were fetched.

question-alpha spans pages a1/a2, and alpha/child share fragment-shared. question-alpha and question-beta print the same label 1 in different directories. Stable IDs and answer relations prevent matching by the printed label alone. The alpha-answer crop uses processed x=2*x+10, y=2*y+200; inverse (processed-[10,200])/2 returns its original [5,25,65,35] box. These are fixed facts, not an extraction algorithm. The patch changes only alpha's printed label from 1? in revision 1 to 1 in revision 2; all checks/plans use revision 2 and the old revision remains available.

From an installed checkout (any current directory):

```powershell
python <checkout>/examples/contracts/consume.py <copied-fixture-directory>
python <checkout>/examples/contracts/consume.py <copied-fixture-directory> --roundtrip <output-directory>/input.json
```

`consume.py` loads and validates resources with the public contracts API, compares the complete deterministic summary against expected.json, and optionally writes a self-contained copy. All expected values, hashes, ordered lists, decisions and status combinations use exact equality; no numeric tolerances are needed for these fabricated integer/half-open boxes. Rebuild all fixtures with `python examples/contracts/build_fixtures.py`; time, resource bytes and input order are fixed. A failure exits nonzero with the public validation error location.
""".format(name=name, version=SCHEMA_VERSION, purpose=purpose)
    (folder / "README.md").write_bytes(readme.encode("utf-8"))
    return {"fixture": name, "artifact_count": len(artifacts), "expected": summary(bundle)["batch"]["state"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["normal", "exception", "unknown", "choice-assumption"])
    args = parser.parse_args()
    policy_dir = ROOT / "config" / "policies"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "usense-v1-proposal.json").write_bytes(json_bytes(policy()))
    (policy_dir / "synthetic-choice-separate.json").write_bytes(json_bytes(policy(True)))
    for name in [args.case] if args.case else ["normal", "exception", "unknown", "choice-assumption"]:
        print(json.dumps(build_case(name), sort_keys=True))


if __name__ == "__main__":
    main()
