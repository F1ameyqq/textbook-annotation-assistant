"""Independent C01 R1 mapping probes. Never write the audited tree or old evidence.

Run: python -B agent-r1-probes.py --tree <frozen-export> --output-dir <R1-stage-output>
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
parser = argparse.ArgumentParser(description="Independent C01 R1 mapping audit against an explicit frozen export")
parser.add_argument("--tree", type=Path, required=True,
    help="Frozen checkout or exported project root containing src/annotation/contracts")
parser.add_argument("--output-dir", type=Path, required=True, help="Own R1 evidence directory for inputs/resources/results")
parser.add_argument("--frozen-commit", default="4e42668ab28eda37a37285285d2f6c595d3bba12", help="Exact delivery commit being audited")
parser.add_argument("--manifest", type=Path, help="Read-only delivery-manifest.json to check frozen export hashes")
parser.add_argument("--only", nargs="+", help="Run only named probes; avoids repeating unrelated checks")
ARGS = parser.parse_args()
CHECKOUT = ARGS.tree.resolve()
OUTPUT = ARGS.output_dir.resolve() if ARGS.output_dir else None
OUTPUT.relative_to(Path(r"D:\1800\.local\stages\C01-review-R1").resolve())
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


def mapping(data, graph_id="pq", action_id="pq", order=1):
    get(data, "QuestionGraph")["payload"]["questions"][0]["external_refs"].update(
        platform_question_id=graph_id, platform_order=order)
    get(data, "ApplyPlan")["payload"]["actions"][0]["target"]["platform_question_id"] = action_id


def add_platform_question(data, platform_id="pq-other", directory="pd", order=1):
    snapshot = get(data, "PlatformSnapshot")["payload"]
    if directory not in snapshot["directories"]:
        snapshot["directories"].append(directory)
    snapshot["questions"].append(dict(platform_question_id=platform_id, directory_id=directory, platform_order=order))


def add_internal_question(data, platform_id="pq", platform_order=1, parent=None, internal_dir="dir"):
    source = get(data, "SourceBundle")["payload"]
    evidence = get(data, "EvidenceBundle")["payload"]
    graph = get(data, "QuestionGraph")["payload"]
    plan = get(data, "ApplyPlan")["payload"]
    batch = get(data, "BatchReport")["payload"]
    source["scope_manifest"].append("q-second")
    if internal_dir not in {d["directory_id"] for d in source["directories"]}:
        source["directories"].append(dict(directory_id=internal_dir, parent_id=None, label="second internal directory"))
    for original, new_name in (("r-stem", "r-second-stem"), ("r-answer", "r-second-answer")):
        region = copy.deepcopy(next(r for r in evidence["regions"] if r["region_id"] == original))
        region["region_id"] = new_name
        region["box"]["bbox"] = [4.0, 4.0, 6.0, 6.0]
        evidence["regions"].append(region)
        evidence["coverage_clues"][0]["region_ids"].append(new_name)
    evidence["coverage_clues"][0]["box"]["bbox"] = [0.0, 0.0, 10.0, 10.0]
    graph["fragments"].extend([
        dict(fragment_id="f-second-stem", region_ids=["r-second-stem"], role="stem", content_type="text", reading_order=0),
        dict(fragment_id="f-second-answer", region_ids=["r-second-answer"], role="answer", content_type="text", reading_order=1)])
    graph["questions"].append(dict(question_id="q-second", directory_id=internal_dir, question_type="free_response",
        fragment_ids=["f-second-stem"], parent_question_id=parent, shared_fragment_ids=[], cross_page=False,
        external_refs=dict(printed_number="1", platform_question_id=platform_id, platform_order=platform_order)))
    graph["answer_relations"].append(dict(relation_id="answer-second", question_id="q-second",
        candidate_fragment_ids=["f-second-answer"], selected_fragment_ids=["f-second-answer"], status="SELECTED", evidence_refs=["ev"]))
    action = copy.deepcopy(plan["actions"][0])
    action.update(action_id="action-second", source_entity_ids=["q-second", "f-second-stem", "f-second-answer"],
        expected_before=dict(frame_count=2), expected_after=dict(frame_count=4), depends_on=["action"])
    action["target"].update(question_id="q-second", platform_question_id=platform_id)
    plan["actions"].append(action)
    result = copy.deepcopy(get(data, "ExecutionReceipt")["payload"]["results"][0])
    result.update(action_id="action-second", platform_ids=["pf-second"])
    get(data, "ExecutionReceipt")["payload"]["results"].append(result)
    batch["scope_manifest"].append("q-second")
    batch["questions"].append(dict(question_id="q-second", state="VERIFIED", reason="synthetic second question"))
    batch["total_expected"] = 2


def cross_directory_same_order(data, same_platform_dir=False):
    add_platform_question(data, directory="pd" if same_platform_dir else "platform-other", order=1)
    add_internal_question(data, platform_id="pq-other", platform_order=1, internal_dir="internal-other")


def new_question(data, empty_snapshot=False):
    mapping(data, graph_id=None, action_id=None, order=None)
    if empty_snapshot:
        get(data, "PlatformSnapshot")["payload"].update(questions=[], frames=[])


def action_conflict(data):
    add_platform_question(data)
    mapping(data, action_id="pq-other")


def mapped_other_order(data):
    add_platform_question(data, order=2)
    mapping(data, graph_id="pq-other", action_id="pq-other", order=2)


def dangling_directory(data):
    get(data, "PlatformSnapshot")["payload"]["questions"][0]["directory_id"] = "missing-directory"


def duplicate_directory(data):
    get(data, "PlatformSnapshot")["payload"]["directories"].append("pd")


def run_case(name, mutation, expected="ACCEPT", code=None, suffix=None):
    if ARGS.only and name not in ARGS.only:
        return
    case = OUTPUT / name
    data = base_bundle()
    mutation(data)
    data = reseal(data)
    save_json(case / "input.json", data)
    for resource_path, resource_bytes in RESOURCE_BYTES.items():
        target = case / resource_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(resource_bytes)
    methods = {}
    for method in ("validate_bundle", "assert_plan_ready"):
        try:
            if method == "validate_bundle":
                validate_bundle(data, case)
            else:
                assert_plan_ready(data, artifact_ref(get(data, "ApplyPlan")), artifact_ref(get(data, "PlatformSnapshot")))
            methods[method] = dict(outcome="ACCEPT")
        except ContractError as error:
            methods[method] = dict(outcome="REJECT", issues=error.issues)
        except Exception as error:
            methods[method] = dict(outcome="ERROR", error=repr(error))
    env = dict(os.environ)
    env["PYTHONPATH"] = str(CHECKOUT / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, "-B", "-m", "annotation.contracts", "validate", str(case / "input.json")]
    completed = subprocess.run(command, cwd=str(case), env=env, capture_output=True, text=True, encoding="utf-8")
    (case / "cli-stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (case / "cli-stderr.txt").write_text(completed.stderr, encoding="utf-8")
    passed = completed.returncode == (0 if expected == "ACCEPT" else 1)
    for result in methods.values():
        passed = passed and result["outcome"] == expected
        if expected == "REJECT":
            issues = result.get("issues", [])
            passed = passed and any((code is None or item["code"] == code) and
                (suffix is None or item["path"].endswith(suffix)) for item in issues)
    record = dict(case=name, expected=expected, expected_code=code, expected_path_suffix=suffix, passed=bool(passed),
        methods=methods, cli=dict(command=command, exit_code=completed.returncode, stdout=completed.stdout,
        stderr=completed.stderr), resources_provisioned=True)
    save_json(case / "result.json", record)
    emit(record)


if __name__ == "__main__":
    metadata = dict(commit=ARGS.frozen_commit, code_commit="cb684f90a2cd7bd7064ce1f30b7d024a49389132",
        tree=str(CHECKOUT), python=sys.version.split()[0], source_hashes={name:
        hashlib.sha256((CHECKOUT / "src" / "annotation" / "contracts" / name).read_bytes()).hexdigest()
        for name in ("models.py", "validation.py", "integrity.py")})
    if ARGS.manifest:
        manifest = json.loads(ARGS.manifest.read_text(encoding="utf-8-sig"))
        checks = [dict(path=item["path"], match=hashlib.sha256((CHECKOUT / item["path"]).read_bytes()).hexdigest() == item["sha256"])
            for item in manifest["files"]]
        metadata["manifest"] = dict(commit=manifest["commit"], files_checked=len(checks), all_match=all(item["match"] for item in checks))
        if manifest["commit"] != ARGS.frozen_commit or not metadata["manifest"]["all_match"]:
            raise SystemExit("Frozen delivery manifest mismatch; no probes run")
    print(json.dumps(metadata, ensure_ascii=False))
    run_case("known-mapping-baseline", lambda data: None)
    run_case("snapshot-directory-missing", dangling_directory, "REJECT", "MISSING_REFERENCE", ".questions[0].directory_id")
    run_case("snapshot-directory-duplicate", duplicate_directory, "REJECT", "DUPLICATE_ID", ".directories")
    run_case("action-platform-id-missing", lambda data: mapping(data, action_id="missing-question"), "REJECT", "MISSING_REFERENCE", ".target.platform_question_id")
    run_case("graph-platform-id-missing", lambda data: mapping(data, graph_id="missing-question", action_id="missing-question"), "REJECT", "MISSING_REFERENCE", ".external_refs.platform_question_id")
    run_case("action-other-existing-id-conflict", action_conflict, "REJECT", "PLATFORM_MAPPING_CONFLICT", ".target.platform_question_id")
    run_case("existing-action-requires-explicit-mapping", lambda data: mapping(data, graph_id=None, order=None), "REJECT", "PLATFORM_MAPPING_REQUIRED", ".target.platform_question_id")
    run_case("existing-mapping-action-null-conflict", lambda data: mapping(data, action_id=None), "REJECT", "PLATFORM_MAPPING_CONFLICT", ".target.platform_question_id")
    run_case("new-null-target-nonempty-snapshot", lambda data: new_question(data))
    run_case("new-null-target-empty-snapshot", lambda data: new_question(data, True))
    run_case("empty-string-action-not-null", lambda data: mapping(data, action_id=""), "REJECT", "MISSING_REFERENCE", ".target.platform_question_id")
    run_case("empty-string-graph-not-null", lambda data: mapping(data, graph_id="", action_id=""), "REJECT", "MISSING_REFERENCE", ".external_refs.platform_question_id")
    run_case("known-order-conflict", lambda data: mapping(data, order=2), "REJECT", "PLATFORM_MAPPING_CONFLICT", ".external_refs.platform_order")
    run_case("unknown-order-accepted", lambda data: mapping(data, order=None))
    run_case("explicit-mapping-other-known-order", mapped_other_order)
    run_case("two-internal-questions-share-platform-id", lambda data: add_internal_question(data))
    run_case("parent-child-share-platform-id", lambda data: add_internal_question(data, parent="q"))
    run_case("two-internal-dirs-share-platform-id", lambda data: add_internal_question(data, internal_dir="internal-other"))
    run_case("different-internal-platform-dirs-repeat-order", cross_directory_same_order)
    run_case("repeat-order-same-platform-directory", lambda data: cross_directory_same_order(data, True))
    run_case("shared-platform-id-second-order-unknown", lambda data: add_internal_question(data, platform_order=None))
    run_case("two-new-null-internal-questions", lambda data: (new_question(data), add_internal_question(data, platform_id=None, platform_order=None)))
    summary = dict(metadata=metadata, count=len(RESULTS), passed=sum(item["passed"] for item in RESULTS),
        failed=sum(not item["passed"] for item in RESULTS), cases=RESULTS)
    save_json(OUTPUT / "results.json", summary)
    print(json.dumps(dict(summary={key: summary[key] for key in ("count", "passed", "failed")}), ensure_ascii=False))
    raise SystemExit(1 if summary["failed"] else 0)


