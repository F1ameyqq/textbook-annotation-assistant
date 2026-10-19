"""Independent A09 byte audit and archived-output analysis; never dispatches business."""
import ast
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

os.environ["GIT_NO_LAZY_FETCH"] = "1"
REPORT = Path("D:/1800-worktrees/a09-q4-review")
RUN = Path("D:/1800-worktrees/a09-q4-review-run")
EVIDENCE = REPORT / "docs/evidence/A09/review"
LOCAL = RUN / ".local/a09-review"
PRODUCT = "29c82b0997be3080f53dfde2afbb1d7457b04197"
DELIVERY = "439423ebf4277e3825aba24fed6f56546ef66a2b"
WORKFLOW = "0a9c634d160ac7b39f68a1fb3555f409dd408f49"
DISPATCH = "1cb8768000ed1dc2828a469b91fffa30e401d6ad"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(encode(value))


def git(root, *args):
    return subprocess.check_output(["git", "-c", "core.longpaths=true", *args], cwd=root)


def blob(revision, path):
    return git(REPORT, "cat-file", "blob", revision + ":" + path)


def tree(revision):
    result = {}
    for row in git(REPORT, "ls-tree", "-r", "-z", revision).split(b"\0"):
        if row:
            meta, path = row.split(b"\t", 1)
            result[path.decode("utf-8")] = meta.decode().split()
    return result


def batch_bytes(entries):
    cache = {}
    proc = subprocess.Popen(["git", "-c", "core.longpaths=true", "cat-file", "--batch"],
                            cwd=REPORT, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for path, entry in entries.items():
            oid = entry[2]
            if oid not in cache:
                assert entry[1] == "blob", path
                proc.stdin.write(oid.encode() + b"\n")
                proc.stdin.flush()
                header = proc.stdout.readline().split()
                assert header[:2] == [oid.encode(), b"blob"]
                raw = proc.stdout.read(int(header[2]))
                assert proc.stdout.read(1) == b"\n"
                cache[oid] = raw
    finally:
        proc.stdin.close()
        proc.stdout.close()
        proc.wait(timeout=10)
    assert proc.returncode == 0
    return cache


def facts(path, raw, **extra):
    return dict(path=str(path), bytes=len(raw), sha256=sha(raw), **extra)


def preflight():
    started = now()
    assert git(REPORT, "rev-parse", "HEAD").decode().strip() == DELIVERY
    assert git(RUN, "rev-parse", "HEAD").decode().strip() == PRODUCT
    assert git(REPORT, "symbolic-ref", "--short", "HEAD").decode().strip() == "codex/a09-q4-review"
    assert not (LOCAL / "candidate-1").exists() and not (LOCAL / "budget").exists()
    old, product, delivery = map(tree, (WORKFLOW, PRODUCT, DELIVERY))
    assert all(product.get(p) == v == delivery.get(p) for p, v in old.items())
    assert all(delivery.get(p) == v for p, v in product.items())
    added = set(delivery) - set(old)
    allowed = ("src/annotation/source/b_q4/", "src/annotation/delivery/q4_offline/", "src/annotation/quality/q4_offline.py",
               "config/policies/a09-q4-offline-v1.json", "tests/test_a09_", "tests/fixtures/a09/", "examples/a09/",
               "docs/a09-q4-offline-simulation.md", "docs/tasks/A09-Q4-execution-report.md", "docs/evidence/A09/execution/")
    assert all(p.startswith(allowed) for p in added)
    manifest_path = "docs/evidence/A09/execution/delivery-member-manifest.json"
    manifest_raw = blob(DELIVERY, manifest_path)
    assert sha(manifest_raw) == "5dae17727efd65e98ef9df94ab34abdc95c6faee1caa6b4bd3fc5156bd9eb541"
    manifest = json.loads(manifest_raw)
    assert {m["path"] for m in manifest["members"]} == added - {manifest_path}
    cache = batch_bytes({p: delivery[p] for p in added})
    for member in manifest["members"]:
        raw = cache[delivery[member["path"]][2]]
        assert len(raw) == member["bytes"] and sha(raw) == member["sha256"]
        assert delivery[member["path"]][2] == member["git_blob"]
    checkout_records = []
    for root, revision, entries in ((REPORT, DELIVERY, delivery), (RUN, PRODUCT, product)):
        existing = {p: v for p, v in entries.items() if (root / p).is_file()}
        raw_cache = batch_bytes(existing)
        members = []
        for path, entry in existing.items():
            raw = (root / path).read_bytes()
            assert raw == raw_cache[entry[2]], (root, path)
            members.append(facts(path, raw, git_blob=entry[2], mode=entry[0]))
        assert not git(root, "diff", "--name-only")
        save(EVIDENCE / ("preflight/" + root.name + "-raw-members.json"), members)
        checkout_records.append({"path": str(root), "head": revision, "raw_files": len(members),
                                 "sparse_git_only_files": len(entries) - len(members), "all_actual_bytes_match": True})
    registry_raw = blob(WORKFLOW, "docs/tasks/A09-inputs.json")
    registry = json.loads(registry_raw)
    approval_raw = blob(WORKFLOW, registry["approval_path"])
    proposal_raw = blob(WORKFLOW, registry["proposal_path"])
    assert sha(approval_raw) == registry["approval_sha256"]
    assert sha(proposal_raw) == registry["proposal_sha256"]
    stage_path = Path(registry["local_readonly_input"])
    stage_raw = stage_path.read_bytes()
    assert len(stage_raw) == registry["zip_bytes"] and sha(stage_raw) == registry["zip_sha256"]
    from PIL import Image
    member_facts, image_facts = [], []
    with zipfile.ZipFile(io.BytesIO(stage_raw)) as z:
        assert len(z.namelist()) == len(set(z.namelist()))
        assert set(z.namelist()) == {m["path"] for m in registry["raw_package_members"]}
        for m in registry["raw_package_members"]:
            raw = z.read(m["path"])
            assert len(raw) == m["bytes"] and sha(raw) == m["sha256"]
            member_facts.append(facts(m["path"], raw))
        for s in registry["sources"]:
            raw = z.read("staging/" + s["path"])
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                assert image.size == (s["width"], s["height"]) and sha(raw) == s["sha256"]
                image_facts.append(dict(s, actual_format=image.format, actual_size=list(image.size)))
        case = json.loads(z.read(registry["case_member"]))
    approval, proposal = map(json.loads, (approval_raw, proposal_raw))
    assert case == proposal["source_case_snapshot"]
    assert approval["approved_regions_in_physical_order"] == proposal["proposed_regions_in_physical_order"]
    assert approval["approved_content"] == proposal["content_proposal"]
    assert all(v is False for v in proposal["approvals"].values()) and case["decision"] == "HOLD"
    save(EVIDENCE / "preflight/input-original-members.json", member_facts)
    fixed = []
    for c, p in [(DISPATCH, "docs/tasks/A09-Q4-review-dispatch.md"),
                 (DISPATCH, "docs/evidence/coordinator/a09-preflight-20261019/preflight.json"),
                 (DISPATCH, "docs/evidence/coordinator/a09-preflight-20261019/review-checkouts.json")]:
        raw = blob(c, p)
        dest = EVIDENCE / "dispatch" / Path(p).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("xb") as handle:
            handle.write(raw)
        fixed.append(facts(p, raw, commit=c))
    engine = ast.parse(blob(PRODUCT, "src/annotation/delivery/q4_offline/engine.py"))
    observe = next(n for n in ast.walk(engine) if isinstance(n, ast.FunctionDef) and n.name == "observe")
    assert [n.arg for n in observe.args.args] == ["self"]
    runtime_members = json.loads(blob(DELIVERY, "docs/evidence/A09/execution/candidate-1/runtime-members.json"))
    for m in runtime_members:
        raw = blob(PRODUCT, m["path"])
        assert len(raw) == m["bytes"] and sha(raw) == m["sha256"]
    result = {"status": "INDEPENDENT_PREFLIGHT_PASS_NOT_ACCEPTANCE", "started_at": started, "finished_at": now(),
        "product": PRODUCT, "delivery": DELIVERY, "workflow": WORKFLOW, "dispatch": DISPATCH,
        "old_workflow_entries_preserved": len(old), "all_product_entries_preserved": len(product),
        "delivery_added_paths": len(added), "delivery_manifest_members": len(manifest["members"]),
        "delivery_manifest_bytes": sum(m["bytes"] for m in manifest["members"]),
        "delivery_manifest_sha256": sha(manifest_raw), "checkouts": checkout_records,
        "fixed_dispatch_material": fixed, "stage_original": facts(stage_path, stage_raw),
        "registry_sha256": sha(registry_raw), "approval_sha256": sha(approval_raw), "proposal_sha256": sha(proposal_raw),
        "zip_members_checked_without_execution": len(member_facts), "original_images": image_facts,
        "runtime_members_match_fixed_product": len(runtime_members), "observe_arguments": ["self"],
        "existing_libraries": {n: importlib.metadata.version(n) for n in ("pydantic", "Pillow")},
        "python": sys.version, "executable": sys.executable, "business_runs": 0, "targets_created": 0,
        "stage_package_scripts_executed": 0, "A08_reception_calls": 0}
    save(EVIDENCE / "preflight/result.json", result)
    print(json.dumps({k: result[k] for k in ("status", "old_workflow_entries_preserved", "delivery_added_paths", "checkouts")}))


def staged():
    registry = json.loads(blob(WORKFLOW, "docs/tasks/A09-inputs.json"))
    mappings = [("approval.json", "docs/approvals/A09-Q4-offline-business-approval.json"),
                ("proposal.json", "docs/reviews/q4-first-lesson/proposal.json"),
                ("input-registry.json", "docs/tasks/A09-inputs.json"),
                ("q1-approval.json", "docs/approvals/A07-Q1-offline-business-approval.json")]
    records = []
    for name, path in mappings:
        raw = (LOCAL / "inputs" / name).read_bytes()
        assert raw == blob(WORKFLOW, path)
        records.append(facts(LOCAL / "inputs" / name, raw, source_type="RAW_GIT_BLOB", source_commit=WORKFLOW, source_path=path))
    raw = (LOCAL / "inputs/stage.zip").read_bytes()
    assert sha(raw) == registry["zip_sha256"] and len(raw) == registry["zip_bytes"]
    assert raw == Path(registry["local_readonly_input"]).read_bytes()
    records.append(facts(LOCAL / "inputs/stage.zip", raw, source_type="READ_ONLY_ORIGINAL_ZIP", source_path=registry["local_readonly_input"]))
    raw = (RUN / "config/policies/a09-q4-offline-v1.json").read_bytes()
    assert raw == blob(PRODUCT, "config/policies/a09-q4-offline-v1.json")
    records.append(facts("config/policies/a09-q4-offline-v1.json", raw, source_type="RAW_GIT_BLOB", source_commit=PRODUCT))
    save(EVIDENCE / "preflight/input-raw-manifest.json", {"at": now(), "inputs": records})
    print("Own input copies bound to raw Git/original ZIP; no business run")


def load(path):
    return json.loads(path.read_bytes())


def archive():
    launch = load(LOCAL / "launch-1.json")
    release = load(LOCAL / "candidate-1/release.json")
    query = load(EVIDENCE / "post-release-query.json")
    assert launch["supervisor_released"] and launch["original_process_handle_waited"]
    assert release["child_released"] and release["waited_original_handle"]
    assert launch["supervisor_exit_code"] == release["exit_code"] == 0
    assert all(not q["found"] for q in query["queries"])
    started = now()
    records = []
    for src in sorted(LOCAL.rglob("*")):
        if src.is_file():
            rel = src.relative_to(LOCAL)
            dest = EVIDENCE / "archive" / rel
            raw = src.read_bytes()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as handle:
                handle.write(raw)
            assert dest.read_bytes() == raw == src.read_bytes()
            records.append(dict(source=str(src), archived_path=str(dest.relative_to(REPORT)).replace("\\", "/"),
                                bytes=len(raw), sha256=sha(raw)))
    result = {"started_at": started, "finished_at": now(), "copy_type": "SEQUENTIAL_IMMUTABLE_AFTER_BOTH_PROCESS_EXITS",
              "source": str(LOCAL), "members": records, "files": len(records), "bytes": sum(r["bytes"] for r in records),
              "original_supervisor": launch["supervisor_pid"], "original_worker": release["child_pid"],
              "source_and_copy_bytes_identical": True, "business_reruns": 0}
    save(EVIDENCE / "archive-copies.json", result)
    print(json.dumps({k: result[k] for k in ("copy_type", "files", "bytes", "business_reruns")}))


def analyze():
    """Pure audit of frozen emitted artifacts; does not prepare/execute/observe a target."""
    started = now()
    ar = EVIDENCE / "archive"
    trial = ar / "candidate-1/trial"
    normal = trial / "normal"
    semantic = trial / "semantic"
    registry_raw = blob(WORKFLOW, "docs/tasks/A09-inputs.json")
    registry = json.loads(registry_raw)
    approval_raw = blob(WORKFLOW, registry["approval_path"])
    approval = json.loads(approval_raw)
    proposal_raw = blob(WORKFLOW, registry["proposal_path"])
    proposal = json.loads(proposal_raw)
    summary = load(trial / "summary.json")
    identity = load(trial / "identity.json")
    launch = load(ar / "launch-1.json")
    release = load(ar / "candidate-1/release.json")
    before = load(normal / "assets/before.json")
    after = load(normal / "assets/readback.json")
    prepared = load(normal / "prepared-bundle.json")
    final = load(normal / "final-bundle.json")
    def artifact(bundle, kind, stage=None):
        choices = [a for a in bundle["artifacts"] if a["kind"] == kind and
                   (stage is None or a["payload"].get("stage") == stage)]
        assert len(choices) == 1, (kind, stage)
        return choices[0]
    source = artifact(prepared, "SourceBundle")
    evidence = artifact(prepared, "EvidenceBundle")
    graph = artifact(prepared, "QuestionGraph")
    pre = artifact(prepared, "CheckReport", "PRE_APPLY")
    target_report = artifact(prepared, "CheckReport", "TARGET")
    snapshot = artifact(prepared, "PlatformSnapshot")
    plan = artifact(prepared, "ApplyPlan")
    receipt = artifact(final, "ExecutionReceipt")
    policy = prepared["policies"][0]
    # Import only the frozen public contract validator. No product target/driver imports.
    sys.path.insert(0, str(RUN / "src"))
    from annotation.contracts import validate_bundle, assert_plan_ready, artifact_ref, content_digest
    validated = validate_bundle(prepared, asset_root=normal)
    validate_bundle(final, asset_root=normal)
    assert_plan_ready(validated, artifact_ref(plan), artifact_ref(snapshot))
    sem = load(semantic / "legally-resealed-checked-bundle.json")
    validate_bundle(sem, asset_root=semantic)
    contract_origin = str(Path(sys.modules["annotation.contracts"].__file__).resolve())
    assert contract_origin.startswith(str(RUN / "src"))
    for kind in ("SourceBundle", "EvidenceBundle", "QuestionGraph"):
        assert artifact(prepared, kind)["producer"]["evidence_mode"] == "OBSERVED"
    assert pre["producer"]["evidence_mode"] == "OBSERVED"
    for value in (snapshot, target_report, plan, receipt):
        assert value["producer"]["evidence_mode"] == "SYNTHETIC"
    assert policy["confirmation_status"] == "A_INTERNAL_PROPOSAL" and policy["applicability"] == "PROPOSAL_ONLY"
    assert policy["frame_save_status"] == "SYNTHETIC" and policy["ocr_status"] == "UNVERIFIED"
    assert source["payload"]["scope_manifest"] == [approval["question_id"]]
    regions = evidence["payload"]["regions"]
    fragments = graph["payload"]["fragments"]
    questions = graph["payload"]["questions"]
    relations = graph["payload"]["answer_relations"]
    approved = approval["approved_regions_in_physical_order"]
    expected = []
    for i, r in enumerate(approved):
        image = next(s for s in registry["sources"] if s["asset_id"] == r["asset_id"])
        expected.append({"box": {"image": {k: image[k] for k in ("asset_id", "width", "height", "sha256")}, "bbox": r["bbox"]},
                         "platform_role": r["proposed_role"], "platform_type": r["content_type"], "text": r["text"],
                         "region_id": r["proposal_region_id"], "fragment_id": "a09-fragment-" + str(i)})
    assert [r["bbox"] for r in approved] == [[334,975,581,1077],[100,1118,592,1193],[99,1202,220,1235],[324,239,342,257]]
    assert [r["proposed_role"] for r in approved] == ["Q", "Q", "Q", "A"]
    assert [r["content_type"] for r in approved] == ["image", "text", "text", "text"]
    assert len(regions) == len(fragments) == 4 and len(questions) == len(relations) == 1
    for i, (region, fragment, exp) in enumerate(zip(regions, fragments, expected)):
        assert region["box"] == exp["box"] and region["text"] == exp["text"] and region["content_type"] == exp["platform_type"]
        assert region["region_id"] == exp["region_id"]
        assert fragment["fragment_id"] == exp["fragment_id"] and fragment["region_ids"] == [exp["region_id"]]
        assert fragment["content_type"] == exp["platform_type"] and fragment["reading_order"] == i
        assert policy["role_mapping"][fragment["role"]] == exp["platform_role"]
    q = questions[0]
    assert q["question_id"] == approval["question_id"] and q["question_type"] == "free_response"
    assert q["cross_page"] is False and q["parent_question_id"] is None and q["shared_fragment_ids"] == []
    assert q["fragment_ids"] == [e["fragment_id"] for e in expected[:3]]
    assert relations[0]["question_id"] == q["question_id"] and relations[0]["status"] == "SELECTED"
    assert relations[0]["candidate_fragment_ids"] == relations[0]["selected_fragment_ids"] == [expected[-1]["fragment_id"]]
    assert [f["role"] for f in fragments] == ["stem", "stem", "stem", "answer"]
    provenance = load(normal / "assets/input/provenance.json")
    assert provenance["source_case_snapshot"] == proposal["source_case_snapshot"]
    assert provenance["historical_proposal_approvals"] == proposal["approvals"]
    assert all(v is False for v in proposal["approvals"].values())
    assert provenance["source_case_snapshot"]["decision"] == "HOLD"
    assert provenance["source_case_snapshot"]["question_snapshot"]["flags"] == ["FIGURE_EXTENT_UNVERIFIED"]
    assert provenance["source_case_snapshot"]["question_snapshot"]["verification_status"] == "UNVERIFIED"
    assert provenance["source_case_snapshot"]["answer_snapshot"]["verification_status"] == "UNVERIFIED"
    assert provenance["source_case_snapshot"]["answer_id"] == approval["answer_id"]
    assert provenance["question_type_mapping"]["proposal"] == "fill_blank" and provenance["question_type_mapping"]["C01"] == "free_response"
    assert provenance["cross_page"] is False
    assert len(provenance["original_ocr_to_A_regions"]) == 4
    assert len(provenance["other_cases"]) == 3 and all(x["status"] == "HOLD" and not x["question_relation_created"] for x in provenance["other_cases"])
    assert provenance["full_external_G_Check_plan"] == "DECLARED_ONLY_EXTERNAL_NOT_LOADED"
    assert provenance["whole_page_coverage_claim"] is provenance["B_joint_adoption"] is provenance["platform_eligible"] is False
    assert provenance["A_disposition"]["independent_human_visual_review"] is False
    assert provenance["input_sha256"]["approval"] == sha(approval_raw)
    assert (normal / "assets/input/approval.json").read_bytes() == approval_raw
    assert (normal / "assets/input/proposal.json").read_bytes() == proposal_raw
    assert (normal / "assets/input/input-registry.json").read_bytes() == registry_raw
    raw_stage = (ar / "inputs/stage.zip").read_bytes()
    assert sha(raw_stage) == registry["zip_sha256"]
    with zipfile.ZipFile(io.BytesIO(raw_stage)) as z:
        assert (normal / "assets/input/original-case.json").read_bytes() == z.read(registry["case_member"])
        for image in registry["sources"]:
            assert (normal / "assets/original" / (image["asset_id"] + ".jpg")).read_bytes() == z.read("staging/" + image["path"])
    # Recompute frame oracle solely from fixed authority/registry and actual readback.
    before_view, after_view = before["view"], after["view"]
    assert before_view["target"]["questions"] == before_view["target"]["frames"] == []
    assert before_view["internal_bindings"] == before_view["frame_projections"] == {} and before_view["epoch"] == 0
    assert after_view["epoch"] == 1 and len(after_view["target"]["questions"]) == 1
    base_frames = after_view["target"]["frames"]
    projections = after_view["frame_projections"]
    assert len(base_frames) == len(projections) == 4
    actual = [projections[f["platform_frame_id"]] for f in base_frames]
    assert actual == expected
    pid = after_view["target"]["questions"][0]["platform_question_id"]
    assert after_view["internal_bindings"] == {q["question_id"]: pid}
    for frame, projection in zip(base_frames, actual):
        assert frame["platform_question_id"] == pid and frame["box"] == projection["box"] and frame["platform_role"] == projection["platform_role"]
    assert before["read_sequence"] == 1 and after["read_sequence"] == 2
    assert before["instance_id"] == after["instance_id"]
    assert before["target_state_hash"] == content_digest(before_view) and after["target_state_hash"] == content_digest(after_view)
    assert before["target_state_hash"] != after["target_state_hash"]
    assert plan["payload"]["readiness"] == "READY" and plan["payload"]["execution_mode"] == "SIMULATED"
    actions = plan["payload"]["actions"]
    assert len(actions) == 1 and actions[0]["operation"] == "CREATE_FRAMES"
    assert json.loads(actions[0]["expected_after"]["frames"]) == expected
    assert receipt == load(normal / "receipt.json") and receipt["payload"]["execution_mode"] == "SIMULATED"
    result = receipt["payload"]["results"][0]
    assert result["outcome"] == "APPLIED" and result["effect_match"] == "MATCH" and result["replay_allowed"] is False
    assert result["next_step"] == "POSTCHECK" and receipt["payload"]["write_disposition"] == "POSTCHECK"
    comparison = load(normal / "comparison.json")
    assert comparison["effect_match"] == "MATCH" and comparison["approval_table_match"] is True
    assert comparison["approval_differences"] == [] and comparison["actual_content_and_type_readback"] == expected
    assert comparison["content_check_status"] == "PENDING" and comparison["submission_status"] == "NOT_SUBMITTED"
    assert all(c["outcome"] == "PASS" for c in pre["payload"]["checks"])
    assert {c["check_id"] for c in pre["payload"]["checks"]} == {"source_integrity", "structure", "answer_matching", "coverage", "policy"}
    assert pre["payload"]["decision"] == target_report["payload"]["decision"] == "PASS"
    calc_files = sorted((normal / "assets/calculations").glob("pre_apply-*.json"))
    assert len(calc_files) == 1
    calculations = load(calc_files[0])
    assert all(v is True for group in calculations.values() for v in group.values())
    sem_checks = artifact(sem, "CheckReport", "PRE_APPLY")
    expected_sem = {"source_integrity": "PASS", "structure": "FAIL", "answer_matching": "PASS", "coverage": "PASS", "policy": "FAIL"}
    assert sem_checks["payload"]["decision"] == "HOLD"
    assert {c["check_id"]: c["outcome"] for c in sem_checks["payload"]["checks"]} == expected_sem
    sem_calc_paths = list((semantic / "assets/calculations").glob("pre_apply-*.json"))
    assert len(sem_calc_paths) == 1
    sem_calculations = load(sem_calc_paths[0])
    failed_semantic_fields = [group + "." + name for group, values in sem_calculations.items() for name, value in values.items() if not value]
    assert set(failed_semantic_fields) == {"structure.types_match_approval", "policy.image_text_text_text"}
    sem_regions = artifact(sem, "EvidenceBundle")["payload"]["regions"]
    sem_fragments = artifact(sem, "QuestionGraph")["payload"]["fragments"]
    assert sem_regions[0]["content_type"] == sem_fragments[0]["content_type"] == "text"
    refusal_oracle = {
        "missing_approval": ("AUTHORIZATION", "APPROVAL_MISSING"), "altered_approval": ("AUTHORIZATION", "APPROVAL_BINDING"),
        "q1_approval": ("AUTHORIZATION", "APPROVAL_BINDING"), "replaced_input": ("AUTHORIZATION", "INPUT_BINDING"),
        "replaced_proposal": ("AUTHORIZATION", "INPUT_BINDING"),
        "resealed_image_as_text": ("PRE_APPLY.structure.types_match_approval / policy.image_text_text_text", "COMPUTED_HOLD"),
        "platform_mode": ("TARGET", "PLATFORM_MODE_FORBIDDEN"), "wrong_target": ("TARGET", "TARGET_IDENTITY"),
        "stale_target": ("TARGET", "TARGET_CHANGED"), "same_plan_replay": ("EXECUTION", "PLAN_REPLAY")}
    assert {x["case"] for x in summary["refusals"]} == set(refusal_oracle) and len(summary["refusals"]) == 10
    for r in summary["refusals"]:
        assert r == load(trial / "refusals" / (r["case"] + ".json"))
        assert (r["reached_layer"], r["code"]) == refusal_oracle[r["case"]]
        assert r["rejected"] and r["before_sha256"] == r["after_sha256"]
        assert r["new_questions"] == r["new_frames"] == r["business_dispatches"] == 0
    assert summary["normal_attempts"] == summary["successful_normal_closures"] == summary["business_dispatches"] == 1
    assert summary["actual_questions_added"] == 1 and summary["actual_frames_added"] == 4 and summary["refusal_calls"] == 10
    assert summary["actual_frames"] == expected and all(v == "PASS" for v in summary["stages"].values())
    assert summary["memory_targets_created"] == 3
    assert identity["frozen_head"] == identity["actual_head"] == PRODUCT and Path(identity["cwd"]) == RUN
    assert identity["pid"] == release["child_pid"] and identity["kernel_creation_time"] == release["child_kernel_creation_time"]
    assert launch["supervisor_pid"] == release["supervisor"]["pid"]
    assert launch["supervisor_exit_code"] == release["exit_code"] == 0 and not release["timed_out"]
    assert launch["within_240_seconds"] and release["elapsed_seconds"] <= 180 and release["within_release_bound"]
    assert launch["original_process_handle_waited"] and release["waited_original_handle"] and release["child_released"] and release["success"]
    assert launch["frozen_head"] == release["frozen_head"] == PRODUCT
    assert load(ar / "budget/attempt-1-finish.json") == release
    budget_start = load(ar / "budget/attempt-1-start.json")
    assert budget_start["attempt"] == 1 and budget_start["frozen_head"] == PRODUCT
    assert budget_start["normal_trial_limit"] == 180 and budget_start["release_limit"] == 240
    assert len(list((ar / "budget").glob("attempt-*-start.json"))) == len(list((ar / "budget").glob("attempt-*-finish.json"))) == 1
    runtime = load(ar / "candidate-1/runtime-members.json")
    for m in runtime:
        assert sha(blob(PRODUCT, m["path"])) == m["sha256"] == sha((RUN / m["path"]).read_bytes())
    assert git(RUN, "rev-parse", "HEAD").decode().strip() == PRODUCT and not git(RUN, "diff", "--name-only")
    groups = {
        "raw_input_and_old_byte_preservation": "PASS", "new_C01_source_evidence_graph_closure": "PASS",
        "computed_five_PRE_APPLY_and_explicit_TARGET": "PASS", "approved_four_regions_roles_types_content_order": "PASS",
        "fresh_target_actual_mutation_and_plan_free_readback": "PASS", "new_SIMULATED_receipt_pending_not_submitted": "PASS",
        "original_ten_bounded_refusals_zero_mutation": "PASS", "C01_valid_resealed_type_semantic_HOLD": "PASS",
        "one_attempt_one_success_process_handle_release": "PASS"}
    save(EVIDENCE / "independent-analysis.json", {"recommendation": "PASS", "coordinator_acceptance": "NOT_DECIDED",
        "started_at": started, "finished_at": now(), "product": PRODUCT, "delivery": DELIVERY, "dispatch": DISPATCH,
        "analysis_mode": "READ_ONLY_ARCHIVED_ARTIFACT_VALIDATION_NO_TARGET_CREATION_OR_EXECUTION",
        "groups": groups, "public_contract_import": contract_origin, "contract_input_bundles_validated": ["normal/prepared-bundle", "normal/final-bundle", "semantic/legally-resealed-checked-bundle"],
        "approved_frame_oracle_source": {"approval_commit": WORKFLOW, "approval_sha256": sha(approval_raw), "registry_sha256": sha(registry_raw)},
        "independent_expected_frames": expected, "actual_readback_frames": actual, "approval_differences": [],
        "normal_PRE_APPLY_computed_fields": calculations, "semantic_failed_fields": failed_semantic_fields,
        "refusals": summary["refusals"], "consumption": {"frozen_candidates": 1, "normal_attempts": 1, "successes": 1, "business_dispatches": 1, "refusals": 10, "new_targets_in_analysis": 0, "business_reruns": 0},
        "process_release": {"supervisor_pid": launch["supervisor_pid"], "worker_pid": release["child_pid"], "original_handles_exit_zero": True, "worker_wait_elapsed_seconds": release["elapsed_seconds"], "post_release_query": "post-release-query.json"},
        "boundaries": {"source": "OBSERVED", "target_plan_receipt": "SYNTHETIC", "mode": "SIMULATED", "policy": "A_INTERNAL_PROPOSAL/PROPOSAL_ONLY", "submission": "NOT_SUBMITTED", "content": "PENDING", "other_three_cases": "HOLD_NO_RELATIONS_NO_EXECUTION", "external_G_Check_plan": "DECLARED_ONLY_EXTERNAL_NOT_LOADED", "B_joint_adoption": False, "platform_acceptance": False}})
    print(json.dumps({"recommendation": "PASS", "groups": groups, "normal_attempts": 1, "refusals": 10, "analysis_business_runs": 0}))


def seal():
    assert git(REPORT, "rev-parse", "HEAD").decode().strip() == DELIVERY
    assert git(RUN, "rev-parse", "HEAD").decode().strip() == PRODUCT
    assert not git(REPORT, "diff", "--name-only") and not git(RUN, "diff", "--name-only")
    assert git(RUN, "rev-parse", "HEAD^{tree}").decode().strip() == "240729ac2e07709434df15b5707995ab0cce1f93"
    copies = load(EVIDENCE / "archive-copies.json")
    for m in copies["members"]:
        raw = (REPORT / m["archived_path"]).read_bytes()
        assert raw == Path(m["source"]).read_bytes()
        assert sha(raw) == m["sha256"] and len(raw) == m["bytes"]
    report_path = REPORT / "docs/tasks/A09-Q4-review-report.md"
    links = re.findall(r"\]\(([^)]+)\)", report_path.read_text(encoding="utf-8"))
    manifest_path = EVIDENCE / "review-member-manifest.json"
    closure_path = EVIDENCE / "closure-checks.json"
    future = {manifest_path, closure_path}
    for link in links:
        dest = (report_path.parent / link).resolve()
        assert dest.is_file() or dest in future, link
    analysis = load(EVIDENCE / "independent-analysis.json")
    assert analysis["recommendation"] == "PASS" and analysis["consumption"]["business_reruns"] == 0
    status = git(REPORT, "status", "--porcelain=v1", "-z", "--untracked-files=all").split(b"\0")
    allowed = ("docs/tasks/A09-Q4-review-report.md", "docs/evidence/A09/review/")
    for row in status:
        if row:
            assert row[:2] == b"??" and row[3:].decode("utf-8").startswith(allowed), row
    save(closure_path, {"at": now(), "status": "READY_FOR_COORDINATOR_REVIEW_RECOMMEND_PASS",
         "product_head": PRODUCT, "report_parent": DELIVERY, "dispatch": DISPATCH,
         "running_tree": "240729ac2e07709434df15b5707995ab0cce1f93", "tracked_changes_before_staging": 0,
         "only_allowed_new_paths": True, "report_links_checked": len(links), "all_report_links_resolve_after_sealing": True,
         "archive_sources_still_byte_identical": copies["files"], "consumption": analysis["consumption"],
         "old_evidence_or_product_files_modified": 0, "coordinator_state_writes": 0,
         "services_or_browser_started": 0, "business_reruns": 0, "final_commit_role": "REVIEW_EVIDENCE_ONLY_NOT_RUNNING_HEAD"})
    paths = [report_path] + sorted(p for p in EVIDENCE.rglob("*") if p.is_file() and p != manifest_path)
    members = []
    for path in paths:
        raw = path.read_bytes()
        rel = path.relative_to(REPORT).as_posix()
        assert rel.startswith(allowed)
        git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        members.append(facts(rel, raw, git_blob=git_blob))
    result = {"kind": "INDEPENDENT_REVIEW_RAW_MEMBER_MANIFEST", "product": PRODUCT, "author_delivery": DELIVERY,
              "review_dispatch": DISPATCH, "manifest_excludes_itself": True, "recommendation": "PASS",
              "members": members, "member_count": len(members), "total_bytes": sum(m["bytes"] for m in members)}
    save(manifest_path, result)
    print(json.dumps({"members_excluding_manifest": len(members), "bytes_excluding_manifest": result["total_bytes"],
                      "manifest_sha256": sha(manifest_path.read_bytes()), "report_links": len(links)}))


if __name__ == "__main__":
    {"preflight": preflight, "staged": staged, "archive": archive, "analyze": analyze, "seal": seal}[sys.argv[1]]()
