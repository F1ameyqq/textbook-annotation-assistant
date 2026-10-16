"""Read-only draft probes. No fixtures/platform; no writes except this script file.

Run: python -B D:\1800\.local\stages\C01-review\agent-probes.py --tree <frozen-export>
All exchanges are synthetic. With --output-dir the script writes and verifies
real local synthetic resource bytes. It never modifies the audited tree.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description="Read-only C01 contract preparation probes; no final acceptance verdict")
parser.add_argument("--tree", type=Path,
    default=Path(r"C:\Users\ASUS\.codex\worktrees\c01-contracts\1800"),
    help="Frozen checkout or exported project root containing src/annotation/contracts")
parser.add_argument("--output-dir", type=Path, help="Own evidence directory for generated inputs/resources/results")
parser.add_argument("--frozen-commit", help="Exact delivery commit being audited")
parser.add_argument("--manifest", type=Path, help="Read-only delivery-manifest.json to check frozen export hashes")
parser.add_argument("--only", nargs="+", help="Run only named probes; avoids repeating unrelated checks")
ARGS = parser.parse_args()
CHECKOUT = ARGS.tree.resolve()
OUTPUT = ARGS.output_dir.resolve() if ARGS.output_dir else None
sys.path.insert(0, str(CHECKOUT / "src"))
from annotation.contracts import (ContractError, artifact_ref, assert_plan_ready,
    policy_ref, seal_artifact, seal_policy, validate_bundle)

REF_KEYS = {"artifact_id", "revision", "kind", "content_hash"}
HASH = "0" * 64
RESOURCE_BYTES = {
    "assets/page.pgm": b"P2\n10 10\n255\n" + b" ".join([b"255"] * 100) + b"\n",
    "assets/proof.txt": b"Independent synthetic C01 contract probe; no platform observation.\n",
    "assets/readback.json": b'{"synthetic":true,"platform_id":"pf","frame_count":2}\n',
}
RESOURCE_HASHES = {name: hashlib.sha256(value).hexdigest() for name, value in RESOURCE_BYTES.items()}
RESULTS = []


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def emit(record):
    RESULTS.append(record)
    print(json.dumps(record, ensure_ascii=False))


def reseal(data):
    """Refresh every legitimate downstream ref, leaving intended semantic faults."""
    refs = {}
    def relink(value):
        if isinstance(value, dict):
            if set(value) == REF_KEYS:
                return copy.deepcopy(refs.get((value["artifact_id"], value["revision"]), value))
            return {key: relink(item) for key, item in value.items()}
        if isinstance(value, list):
            return [relink(item) for item in value]
        return value
    output = copy.deepcopy(data)
    for index, original in enumerate(output["artifacts"]):
        candidate = seal_artifact(relink(original))
        output["artifacts"][index] = candidate
        refs[(candidate["artifact_id"], candidate["revision"])] = artifact_ref(candidate)
    return output


def get(data, kind):
    return next(item for item in data["artifacts"] if item["kind"] == kind)


def base_bundle():
    policy = seal_policy(dict(policy_id="policy", revision=1, content_hash=HASH,
        confirmation_status="A_INTERNAL_PROPOSAL", option_grouping="UNRESOLVED",
        role_mapping=dict(stem="Q", option="W", answer="A", explanation="E", shared_material="Q"),
        source_notes=["synthetic independent probe"], frame_save_status="SYNTHETIC",
        ocr_status="UNVERIFIED", applicability="PROPOSAL_ONLY"))
    pref = policy_ref(policy)
    def artifact(kind, name, payload, inputs=()):
        return seal_artifact(dict(schema_version="1.0.0-a-proposal", artifact_id=name,
            revision=1, kind=kind, run_id="probe", book_id="probe-book", scope_id="scope",
            input_refs=list(inputs), producer=dict(module="probe", implementation_version="1",
                config_version="1", policy_versions=[pref], model_version=None,
                prompt_version=None, evidence_mode="SYNTHETIC"), content_hash=HASH,
            created_at="2026-10-16T12:00:00+08:00", payload=payload))
    source = artifact("SourceBundle", "source", dict(assets=[dict(path="assets/page.pgm", sha256=RESOURCE_HASHES["assets/page.pgm"],
        media_type="image/x-portable-graymap", asset_id="page", width=10, height=10,
        source_label="probe", provenance="SYNTHETIC")], directories=[dict(directory_id="dir",
        parent_id=None, label="probe")], pages_expected=["page"], pages_acquired=["page"],
        external_page_mappings=[dict(asset_id="page", directory_id="dir", external_page="1",
            mapping_status="CONFIRMED", evidence_refs=["ev"])], history=[], scope_manifest=["q"],
        scope_manifest_basis="synthetic scope", metadata_page_count=1))
    sref = artifact_ref(source)
    box = dict(image=dict(asset_id="page", width=10, height=10, sha256=RESOURCE_HASHES["assets/page.pgm"]), bbox=[0.0, 0.0, 2.0, 2.0])
    transform = dict(scale_x=1.0, scale_y=1.0, offset_x=0.0, offset_y=0.0,
        rotation_degrees=0.0, padding=[0.0]*4, processed_width=10, processed_height=10, invertible=True)
    evidence = artifact("EvidenceBundle", "evidence", dict(source=sref,
        regions=[dict(region_id=name, box=box, crop_transform=transform, content_type="text",
            text=name, source="SYNTHETIC", evidence_refs=["ev"], printed_number_candidates=[],
            certainty="CONFIRMED") for name in ("r-stem", "r-answer")],
        coverage_clues=[dict(clue_id="clue", box=box, source="SYNTHETIC", disposition="ASSIGNED",
            region_ids=["r-stem", "r-answer"], reason="synthetic clue", evidence_refs=["ev"])]), [sref])
    eref = artifact_ref(evidence)
    graph = artifact("QuestionGraph", "graph", dict(source=sref, evidence=eref,
        questions=[dict(question_id="q", directory_id="dir", question_type="free_response",
            fragment_ids=["f-stem"], parent_question_id=None, shared_fragment_ids=[], cross_page=False,
            external_refs=dict(printed_number="1", platform_question_id="pq", platform_order=1))],
        fragments=[dict(fragment_id="f-stem", region_ids=["r-stem"], role="stem", content_type="text", reading_order=0),
            dict(fragment_id="f-answer", region_ids=["r-answer"], role="answer", content_type="text", reading_order=1)],
        answer_relations=[dict(relation_id="answer", question_id="q", candidate_fragment_ids=["f-answer"],
            selected_fragment_ids=["f-answer"], status="SELECTED", evidence_refs=["ev"])],
        identity_notes="independent synthetic identity"), [sref, eref])
    gref = artifact_ref(graph)
    snapshot = artifact("PlatformSnapshot", "snapshot", dict(target_id="probe-book",
        platform_version="probe-v1", observed_at="2026-10-16T12:00:00+08:00", observed_version="v1",
        observed_hash=HASH, authorized_scope_id="scope", directories=["pd"],
        questions=[dict(platform_question_id="pq", directory_id="pd", platform_order=1)], frames=[],
        capabilities=[dict(name=name, status="VERIFIED", platform_version="probe-v1", evidence_refs=["ev"])
            for name in ("frame_readback", "same_session_handoff")], evidence_refs=["ev"]), [sref])
    snapref = artifact_ref(snapshot)
    coverage = dict(scope_id="scope", pages_expected=["page"], pages_checked=["page"], clue_ids=["clue"],
        unassigned_region_ids=[])
    def check(stage, name, subject, names, snapshot_ref=None, receipt_ref=None, issues=None, decision="PASS"):
        inputs = [gref, subject]
        if snapshot_ref is not None:
            inputs.append(snapshot_ref)
        if receipt_ref is not None:
            inputs.append(receipt_ref)
        unique = {json.dumps(ref, sort_keys=True): ref for ref in inputs}
        return artifact("CheckReport", name, dict(stage=stage, subject=subject, graph=gref, policy=pref,
            snapshot=snapshot_ref, receipt=receipt_ref, coverage=coverage,
            checks=[dict(check_id=n, outcome="PASS" if decision == "PASS" else "UNAVAILABLE",
                evidence_refs=["ev"], reason="synthetic check") for n in names],
            issues=issues or [], decision=decision, reason="synthetic result"), unique.values())
    pre = check("PRE_APPLY", "pre", gref, ("source_integrity", "structure", "answer_matching", "coverage", "policy"))
    target = check("TARGET", "target", snapref, ("target_version", "authorized_scope", "capabilities", "policy"), snapref)
    plan = artifact("ApplyPlan", "plan", dict(graph=gref, precheck=artifact_ref(pre), targetcheck=artifact_ref(target),
        snapshot=snapref, policy=pref, readiness="READY", execution_mode="SIMULATED", session_mode="SAME_SESSION_HANDOFF",
        required_capabilities=["frame_readback", "same_session_handoff"],
        actions=[dict(action_id="action", target=dict(target_id="probe-book", question_id="q", platform_question_id="pq"),
            source_entity_ids=["q", "f-stem", "f-answer"], expected_before=dict(frame_count=0), operation="CREATE_FRAMES",
            expected_after=dict(frame_count=2), depends_on=[])], blocked_issue_ids=[], previous_receipt=None,
        final_submission="HUMAN_ONLY"), [gref, artifact_ref(pre), artifact_ref(target), snapref])
    planref = artifact_ref(plan)
    receipt = artifact("ExecutionReceipt", "receipt", dict(plan=planref, execution_mode="SIMULATED",
        results=[dict(action_id="action", outcome="APPLIED", platform_ids=["pf"], before_evidence_refs=["ev"],
            after_evidence_refs=["ev"], readback=dict(path="assets/readback.json", sha256=RESOURCE_HASHES["assets/readback.json"], media_type="application/json"),
            effect_match="MATCH", next_step="POSTCHECK", replay_allowed=False, reason="synthetic effect")],
        unresolved_issue_ids=[], write_disposition="POSTCHECK"), [planref])
    post = check("POST_APPLY", "post", artifact_ref(receipt), ("frame_structure", "final_content"),
        receipt_ref=artifact_ref(receipt))
    batch = artifact("BatchReport", "batch", dict(source=sref, graph=gref, receipt=artifact_ref(receipt),
        postcheck=artifact_ref(post), scope_manifest=["q"], questions=[dict(question_id="q", state="VERIFIED", reason="synthetic")],
        total_expected=1, coverage=coverage, cost=dict(model_calls=0, amount=0.0, currency="CNY", billing_status="KNOWN", human_minutes=0.0),
        unresolved_issue_ids=[], submission_status="NOT_SUBMITTED", submission_evidence_refs=[],
        content_check_status="VERIFIED", frame_check_status="PASS", state="READY_FOR_SUBMISSION"),
        [sref, gref, artifact_ref(receipt), artifact_ref(post)])
    return dict(format_version="c01-exchange-1", evidence=[dict(evidence_id="ev", resource=dict(path="assets/proof.txt",
        sha256=RESOURCE_HASHES["assets/proof.txt"], media_type="text/plain"), description="synthetic probe", mode="SYNTHETIC")], policies=[policy],
        artifacts=[source, evidence, graph, snapshot, pre, target, plan, receipt, post, batch])


def probe(name, mutator, eligible=False, note=None):
    if ARGS.only and name not in ARGS.only:
        return
    try:
        data = base_bundle()
        mutator(data)
        data = reseal(data)
        case_root = OUTPUT / name if OUTPUT else None
        if case_root:
            save_json(case_root / "input.json", data)
            for resource_path, resource_bytes in RESOURCE_BYTES.items():
                target = case_root / resource_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(resource_bytes)
            if name == "snapshot-question-missing-directory":
                minimal = copy.deepcopy(data)
                minimal["artifacts"] = [copy.deepcopy(get(data, "PlatformSnapshot"))]
                minimal["artifacts"][0]["input_refs"] = []
                save_json(case_root / "minimal-input.json", reseal(minimal))
            elif name == "action-missing-platform-question":
                minimal = copy.deepcopy(data)
                minimal["artifacts"] = minimal["artifacts"][:7]
                save_json(case_root / "minimal-input.json", reseal(minimal))
            elif name.startswith("shadow-unknown-"):
                save_json(case_root / "minimal-input.json", data)
        model = validate_bundle(data, case_root)
        if eligible:
            assert_plan_ready(model, artifact_ref(get(data, "ApplyPlan")), artifact_ref(get(data, "PlatformSnapshot")))
        classification = "ACCEPTED_INVALID" if name in ("snapshot-question-missing-directory",
            "action-missing-platform-question") else "NONBLOCKING_CLARIFICATION" if name.startswith("shadow-unknown-") else (
            "INTERPRETATION_REQUIRED" if note else "ACCEPTED_VALID_CONTROL")
        emit(dict(probe=name, outcome="ACCEPTED", classification=classification,
            stage="frozen-contract-audit" if ARGS.frozen_commit else "draft-preparation",
            resources_verified=bool(case_root), eligible_checked=eligible, note=note))
    except ContractError as error:
        emit(dict(probe=name, outcome="REJECTED", classification="REJECTED_INVALID_CONTROL", issues=error.issues))
    except Exception as error:
        emit(dict(probe=name, outcome="ERROR", error=type(error).__name__ + ": " + str(error)))


def mutate_snapshot_directory(data):
    get(data, "PlatformSnapshot")["payload"]["questions"][0]["directory_id"] = "missing-directory"


def mutate_snapshot_frame(data):
    get(data, "PlatformSnapshot")["payload"]["frames"] = [dict(platform_frame_id="pf", platform_question_id="missing-question",
        box=copy.deepcopy(get(data, "EvidenceBundle")["payload"]["regions"][0]["box"]), platform_role="Q")]


def mutate_plan_platform_question(data):
    get(data, "ApplyPlan")["payload"]["actions"][0]["target"]["platform_question_id"] = "missing-question"


def mutate_transform(data):
    get(data, "EvidenceBundle")["payload"]["regions"][0]["crop_transform"]["invertible"] = False


def mutate_graph_version(data):
    graph = copy.deepcopy(get(data, "QuestionGraph"))
    graph["revision"] = 2
    data["artifacts"].insert(3, graph)
    plan = get(data, "ApplyPlan")
    plan["payload"]["graph"]["revision"] = 2
    for ref in plan["input_refs"]:
        if ref["kind"] == "QuestionGraph":
            ref["revision"] = 2


def mutate_patch(data, correct):
    graph = get(data, "QuestionGraph")
    patch = copy.deepcopy(graph)
    patch.update(kind="ReviewPatch", artifact_id="patch", input_refs=[artifact_ref(graph)])
    patch["payload"] = dict(baseline=artifact_ref(graph), result_revision=2,
        changes=[dict(entity_id="q", field="printed_number", before="1", after="2")],
        operator="reviewer", reason="synthetic correction", related_issue_ids=[], requires_recheck=True)
    patch = seal_artifact(patch)
    result = copy.deepcopy(graph)
    result["revision"] = 2
    result["input_refs"].extend([artifact_ref(graph), artifact_ref(patch)])
    if correct:
        result["payload"]["questions"][0]["external_refs"]["printed_number"] = "2"
    data["artifacts"][3:3] = [patch, result]


def mutate_shadow_unknown(data):
    shadow_plan = copy.deepcopy(get(data, "ApplyPlan"))
    shadow_plan["artifact_id"] = "shadow-plan"
    shadow_plan["created_at"] = "2026-10-16T12:00:30+08:00"
    shadow_plan["payload"]["actions"][0]["action_id"] = "shadow-action"
    shadow_plan = seal_artifact(shadow_plan)
    unknown = copy.deepcopy(get(data, "ExecutionReceipt"))
    unknown["artifact_id"] = "shadow-unknown"
    unknown["created_at"] = "2026-10-16T12:01:00+08:00"
    unknown["input_refs"] = [artifact_ref(shadow_plan)]
    unknown["payload"]["plan"] = artifact_ref(shadow_plan)
    unknown["payload"]["results"][0].update(action_id="shadow-action", outcome="UNKNOWN", platform_ids=[], after_evidence_refs=[], readback=None,
        effect_match="INDETERMINATE", next_step="RECONCILE", reason="synthetic timeout")
    unknown["payload"].update(unresolved_issue_ids=["save-unknown"], write_disposition="PAUSE_RECONCILE")
    unknown = seal_artifact(unknown)
    post = copy.deepcopy(next(item for item in data["artifacts"] if item["artifact_id"] == "post"))
    post["artifact_id"] = "shadow-post"
    post["created_at"] = "2026-10-16T12:01:30+08:00"
    ref = artifact_ref(unknown)
    post["payload"].update(subject=ref, receipt=ref, decision="HOLD", issues=[dict(issue_id="save-unknown", code="SAVE_UNKNOWN",
        scope_type="action", scope_id="shadow-action", evidence_refs=["ev"], severity="blocking", blocks=["APPLY", "COMPLETE"],
        suggested_strategy=dict(strategy_id="RECONCILE", max_attempts=0, max_cost=0.0), reason="synthetic unknown")])
    for check in post["payload"]["checks"]:
        check["outcome"] = "UNAVAILABLE"
    post["input_refs"] = [artifact_ref(get(data, "QuestionGraph")), ref]
    data["artifacts"].extend([shadow_plan, unknown, seal_artifact(post)])


def mutate_shadow_unknown_completed(data):
    mutate_shadow_unknown(data)
    get(data, "BatchReport")["payload"].update(state="COMPLETED", submission_status="CONFIRMED",
        submission_evidence_refs=["ev"])


def mutate_current_summary_declares_unknown(data):
    mutate_shadow_unknown(data)
    batch = get(data, "BatchReport")
    batch["revision"] = 2
    batch["created_at"] = "2026-10-16T12:02:00+08:00"
    batch["run_id"] = "current-summary-probe"
    unknown = next(item for item in data["artifacts"] if item["artifact_id"] == "shadow-unknown")
    batch["input_refs"].append(artifact_ref(unknown))
    data["artifacts"].remove(batch)
    data["artifacts"].append(batch)


if __name__ == "__main__":
    metadata = dict(preparation_only=not bool(ARGS.frozen_commit), commit=ARGS.frozen_commit,
        tree=str(CHECKOUT), python=sys.version.split()[0], source_hashes={
        name: hashlib.sha256((CHECKOUT / "src" / "annotation" / "contracts" / name).read_bytes()).hexdigest()
        for name in ("models.py", "validation.py", "integrity.py")})
    if ARGS.manifest:
        manifest = json.loads(ARGS.manifest.read_text(encoding="utf-8-sig"))
        checks = [dict(path=item["path"], match=(hashlib.sha256((CHECKOUT / item["path"]).read_bytes()).hexdigest() == item["sha256"]))
            for item in manifest["files"]]
        metadata["manifest"] = dict(commit=manifest["commit"], files_checked=len(checks),
            all_match=all(item["match"] for item in checks), failures=[item for item in checks if not item["match"]])
    print(json.dumps(metadata, ensure_ascii=False))
    probe("baseline-eligibility", lambda data: None, eligible=True)
    probe("snapshot-question-missing-directory", mutate_snapshot_directory, eligible=True)
    probe("snapshot-frame-missing-question-control", mutate_snapshot_frame)
    probe("action-missing-platform-question", mutate_plan_platform_question, eligible=True)
    probe("noninvertible-transform-original-box-already-bound", mutate_transform, eligible=True,
        note="INTERPRETATION_REQUIRED: original bbox is already supplied and bound; do not infer inaccurate backprojection merely from invertible=False. Geometry computation is outside C01.")
    probe("plan-new-graph-old-check-control", mutate_graph_version)
    probe("patch-result-correct-control", lambda data: mutate_patch(data, True))
    probe("patch-result-lost-control", lambda data: mutate_patch(data, False))
    probe("shadow-unknown-batch-ready", mutate_shadow_unknown)
    probe("shadow-unknown-batch-completed", mutate_shadow_unknown_completed)
    probe("shadow-unknown-declared-current-summary", mutate_current_summary_declares_unknown)
    probe("shadow-unknown-eligibility-control", mutate_shadow_unknown, eligible=True)
    if OUTPUT:
        cli_results = []
        env = dict(os.environ)
        env["PYTHONPATH"] = str(CHECKOUT / "src")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for name in ("snapshot-question-missing-directory", "action-missing-platform-question",
                "shadow-unknown-batch-ready", "shadow-unknown-batch-completed", "shadow-unknown-declared-current-summary"):
            if ARGS.only and name not in ARGS.only:
                continue
            command = [sys.executable, "-B", "-m", "annotation.contracts", "validate", str(OUTPUT / name / "minimal-input.json")]
            completed = subprocess.run(command, env=env, cwd=str(OUTPUT / name), capture_output=True, text=True, encoding="utf-8")
            (OUTPUT / name / "cli-stdout.txt").write_text(completed.stdout, encoding="utf-8")
            (OUTPUT / name / "cli-stderr.txt").write_text(completed.stderr, encoding="utf-8")
            cli_results.append(dict(probe=name, command=command, exit_code=completed.returncode,
                stdout=completed.stdout, stderr=completed.stderr))
        save_json(OUTPUT / "results.json", dict(metadata=metadata, probes=RESULTS, minimal_cli=cli_results))
        for item in cli_results:
            print(json.dumps(dict(minimal_cli=item), ensure_ascii=False))
