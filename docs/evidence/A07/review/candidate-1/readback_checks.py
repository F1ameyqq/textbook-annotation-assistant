"""Read existing independent-run evidence; no prepare/execute or business retry."""
import inspect
import json
import os
import subprocess
from pathlib import Path

from review_checks import REPO, OUT, INPUT, CANDIDATE, DELIVERY, APPROVAL, digest, encoded, save, tree, git
from annotation.contracts import artifact_ref, assert_plan_ready, validate_bundle
from annotation.delivery.q1_offline import MemoryTarget

RUN = OUT / "normal/run"

def load(path):
    return json.loads(Path(path).read_bytes())

def canonical_hash(value):
    data = dict(value)
    data.pop("content_hash", None)
    return digest(encoded(data))

def main():
    summary = load(RUN / "summary.json")
    supervisor = load(OUT / "normal/supervisor.json")
    exchange = load(RUN / "exchange.json")
    validated = validate_bundle(exchange, asset_root=RUN)
    artifacts = exchange["artifacts"]
    by_kind = {a["kind"]:a for a in artifacts if a["kind"] != "CheckReport"}
    source,evidence,graph,plan,snapshot,receipt = [by_kind[k] for k in
        ("SourceBundle","EvidenceBundle","QuestionGraph","ApplyPlan","PlatformSnapshot","ExecutionReceipt")]
    reports = {a["payload"]["stage"]:a for a in artifacts if a["kind"] == "CheckReport"}
    policy = exchange["policies"][0]
    for obj in artifacts + exchange["policies"]:
        assert canonical_hash(obj) == obj["content_hash"]
    assert_plan_ready(validated, artifact_ref(plan), artifact_ref(snapshot))
    for kind in ("SourceBundle","EvidenceBundle","QuestionGraph"):
        assert by_kind[kind]["producer"]["evidence_mode"] == "OBSERVED"
    assert reports["PRE_APPLY"]["producer"]["evidence_mode"] == "OBSERVED"
    for kind in ("PlatformSnapshot","ApplyPlan","ExecutionReceipt"):
        assert by_kind[kind]["producer"]["evidence_mode"] == "SYNTHETIC"
    assert reports["TARGET"]["producer"]["evidence_mode"] == "SYNTHETIC"
    assert policy["confirmation_status"] == "A_INTERNAL_PROPOSAL" and policy["applicability"] == "PROPOSAL_ONLY"
    assert all(a["provenance"] == "ORIGINAL" for a in source["payload"]["assets"])
    for stage, expected in (("PRE_APPLY", {"source_integrity","structure","answer_matching","coverage","policy"}),
                            ("TARGET", {"target_version","authorized_scope","capabilities","policy"})):
        report = reports[stage]["payload"]
        calc = load(RUN / ("assets/calculations/"+stage.lower()+".json"))
        assert set(calc) == {c["check_id"] for c in report["checks"]} == expected
        assert all(values and all(v is True for v in values.values()) for values in calc.values())
        assert report["decision"] == "PASS" and not report["issues"] and all(c["outcome"] == "PASS" for c in report["checks"])
        assert report["graph"] == artifact_ref(graph)
        assert report["policy"] == {k:policy[k] for k in ("policy_id","revision","content_hash")}
    before, after = [load(RUN / ("assets/"+name+".json")) for name in ("before","readback")]
    assert before["read_sequence"] == 1 and after["read_sequence"] == 2
    assert before["instance_id"] == after["instance_id"] and before["instance_id"].startswith("memory-")
    assert all(ob["execution_mode"] == "SIMULATED" and ob["book_id"] == "46007447" and
        ob["scope_id"] == "a07-fixed-q1-offline" and ob["target_id"] == "a07-q1-memory-target" for ob in (before,after))
    assert canonical_hash(before["view"]) == before["target_state_hash"]
    assert canonical_hash(after["view"]) == after["target_state_hash"]
    assert before["target_state_hash"] != after["target_state_hash"]
    oldview,view = before["view"],after["view"]
    assert oldview["epoch"] == 0 and not oldview["target"]["questions"] and not oldview["target"]["frames"] and not oldview["internal_bindings"] and not oldview["frame_projections"]
    assert view["epoch"] == 1 and len(view["target"]["questions"]) == 1 and len(view["target"]["frames"]) == 6
    question = view["target"]["questions"][0]
    qid = "q-e92a499995ca1bbd570a2a09"
    assert question["directory_id"] == "a07-lesson1" and question["platform_order"] == 1
    assert view["internal_bindings"] == {qid:question["platform_question_id"]}
    candidate = load(RUN / "assets/input/side-candidate.json")
    cp = candidate["payload"]
    selected = [next(r for r in cp["regions"] if r["region_id"] == rid) for rid in cp["proposed_semantic_region_ids"]]
    frames = view["target"]["frames"]
    assert len({f["platform_frame_id"] for f in frames}) == 6
    assert [f["platform_role"] for f in frames] == ["Q","Q","Q","Q","Q","A"]
    assert {f["platform_frame_id"] for f in frames} == set(view["frame_projections"])
    rows = []
    for number,(frame,region) in enumerate(zip(frames,selected)):
        assert frame["platform_question_id"] == question["platform_question_id"]
        assert frame["box"]["bbox"] == region["bbox"]
        assert frame["box"]["image"]["asset_id"] == region["asset_id"]
        assert frame["box"]["image"]["sha256"] == region["source_sha256"]
        assert [frame["box"]["image"]["width"],frame["box"]["image"]["height"]] == region["source_size"]
        projection = view["frame_projections"][frame["platform_frame_id"]]
        assert projection["region_id"] == region["region_id"] and projection["fragment_id"] == "a07-fragment-"+str(number)
        assert projection["box"] == frame["box"] and projection["platform_role"] == frame["platform_role"]
        rows.append({"native_region_id":region["region_id"],"semantic_role":region["role"],"platform_role":frame["platform_role"],
            "platform_frame_id":frame["platform_frame_id"],"asset_id":region["asset_id"],"bbox":region["bbox"]})
    assert len(graph["payload"]["questions"]) == 1 and graph["payload"]["questions"][0]["question_id"] == qid
    relation = graph["payload"]["answer_relations"]
    assert len(relation) == 1 and relation[0]["question_id"] == qid and relation[0]["status"] == "SELECTED"
    assert relation[0]["candidate_fragment_ids"] == relation[0]["selected_fragment_ids"] == ["a07-fragment-5"]
    assert [r["region_id"] for r in evidence["payload"]["regions"]] == cp["proposed_semantic_region_ids"]
    assert [r["text"] for r in evidence["payload"]["regions"]] == [cp["candidate_content"]["stem_body_normalized_without_number"],"A.2","B.3","C.4","D.5","D"]
    assert len(graph["payload"]["fragments"]) == 6 and not any(f["role"] == "explanation" for f in graph["payload"]["fragments"])
    descriptor = load(RUN / next(e["resource"]["path"] for e in exchange["evidence"] if e["evidence_id"] == "ev-target-descriptor"))
    assert descriptor["instance_id"] == after["instance_id"] and descriptor["view"] == before["view"]
    assert descriptor["operations"] == ["CREATE_FRAMES"] and descriptor["approval_sha256"] == APPROVAL
    assert descriptor["execution_mode"] == "SIMULATED" and descriptor["submission_status"] == "NOT_SUBMITTED"
    assert snapshot["payload"]["observed_hash"] == before["target_state_hash"] and snapshot["payload"]["observed_version"] == descriptor["version"]
    result = receipt["payload"]["results"]
    assert len(result) == 1 and result[0]["outcome"] == "APPLIED" and result[0]["effect_match"] == "MATCH"
    assert result[0]["next_step"] == "POSTCHECK" and result[0]["replay_allowed"] is False
    assert result[0]["readback"]["path"] == "assets/readback.json" and result[0]["readback"]["sha256"] == digest((RUN/"assets/readback.json").read_bytes())
    assert receipt["payload"]["plan"] == artifact_ref(plan) and receipt["payload"]["execution_mode"] == "SIMULATED"
    assert receipt["payload"]["write_disposition"] == "POSTCHECK" and not receipt["payload"]["unresolved_issue_ids"]
    for obj in ("approval","base-check","base-evidence","base-graph","base-manifest","history","side-base-package-binding","side-candidate","side-manifest","side-native-scope-issues","side-native-selection","side-scope-applicability-proposal"):
        path = RUN/("assets/input/"+obj+".json")
        assert any(e["resource"]["sha256"] == digest(path.read_bytes()) for e in exchange["evidence"])
    assert load(RUN/"receipt.json") == receipt
    replay = load(RUN / "replay-rejection.json")
    assert replay == {"layer":"EXECUTION","code":"PLAN_REPLAY","zero_target_change":True,"business_dispatches":0}
    assert summary["complete_attempts"] == summary["dispatches"] == summary["successful_closures"] == 1
    assert summary["question_count"] == 1 and summary["frame_count"] == 6 and summary["actual_read_sequences"] == [1,2]
    assert summary["submission_status"] == "NOT_SUBMITTED" and summary["content_check_status"] == "PENDING"
    assert summary["B_joint_adoption_proven"] is False and summary["independent_human_visual_review_proven"] is False
    assert summary["platform_calls"] == summary["model_calls"] == summary["services_started"] == summary["browsers_started"] == 0
    assert not summary["target_held"] and summary["process_exit_code"] == 0
    assert supervisor["candidate_commit"] == CANDIDATE and supervisor["child_pid"] == summary["pid"]
    assert supervisor["child_exit_code"] == 0 and supervisor["child_reaped"] is True and supervisor["timed_out"] is False
    assert supervisor["outer_experiment_seconds"] == 180 and supervisor["outer_reclaim_seconds"] == 240
    author_read = json.loads(git("show",DELIVERY+":docs/evidence/A07/execution/candidate-1/run/assets/readback.json"))
    assert after["instance_id"] != author_read["instance_id"] and summary["run_id"] == "a07-review-1"
    assert list(inspect.signature(MemoryTarget.observe).parameters) == ["self"]
    assert "snapshot_view()" in inspect.getsource(MemoryTarget.observe)
    copies = load(INPUT/"copy-manifest.json")
    originals = {
      "base.zip":Path("D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip"),
      "candidate.zip":Path("D:/1800/.local/stages/coordinator/b-q1-ef6ba4dd/handoffs/b/46007447/B-46007447-Q1-source-candidate-v1-HOLD-2026-10-18.zip"),
      "history.json":Path("D:/1800/.local/stages/coordinator/b-q1-ef6ba4dd/handoffs/b/46007447/single-question-q1/historical-evidence-revision1.json")}
    preserved = {}
    for name, record in copies.items():
        raw = (INPUT/name).read_bytes()
        assert digest(raw) == record["sha256"] and len(raw) == record["bytes"]
        if name in originals:
            assert originals[name].read_bytes() == raw
        preserved[name] = record
    save("readback-review.json",{"result":"PASS","candidate":CANDIDATE,"delivery":DELIVERY,"run_id":summary["run_id"],
        "C01_validation":True,"C01_assert_plan_ready":True,"full_envelope_hashes_independently_recomputed":True,
        "PRE_APPLY_checks":[c["check_id"] for c in reports["PRE_APPLY"]["payload"]["checks"]],
        "TARGET_checks":[c["check_id"] for c in reports["TARGET"]["payload"]["checks"]],
        "observed_source_and_synthetic_target_separate":True,"single_question_six_frame_diff":rows,"readback_differences":[],
        "before_state_hash":before["target_state_hash"],"after_state_hash":after["target_state_hash"],
        "read_sequences":[1,2],"instance_id":after["instance_id"],"different_from_author_target":True,
        "plan_ref":artifact_ref(plan),"receipt_ref":artifact_ref(receipt),"replay_rejection":replay,
        "post_run_originals_preserved":preserved,"business_attempts":1,"business_dispatches":1,"successful_closures":1,
        "negative_calls":10,"platform_calls":0,"model_calls":0,"services_started":0,"browsers_started":0,
        "submission_status":"NOT_SUBMITTED","content_check_status":"PENDING"})
    print("independent readback/C01/raw-input preservation review PASS; zero differences")

if __name__ == "__main__":
    main()
