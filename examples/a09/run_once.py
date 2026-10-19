"""One frozen normal trial followed by exactly the task's ten refusal calls."""
import argparse
import dataclasses
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from audit import git, utc, process_creation
from semantics import image_as_text
from annotation.contracts import artifact_ref, assert_plan_ready
from annotation.delivery.q4_offline.engine import MemoryTarget, prepare, execute
from annotation.quality.q4_offline import pre_apply, approved_frames, compare_approved_frames
from annotation.source.b_q4.reader import build_source, load_inputs, Q4Error, encode, parse, sha


def save(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(encode(value) + b"\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    stages = {k: "NOT_RUN" for k in ("normal", "missing_approval", "altered_approval", "q1_approval", "replaced_input", "replaced_proposal",
                                     "resealed_image_as_text", "platform_mode", "wrong_target", "stale_target", "same_plan_replay")}
    identity = {"pid": os.getpid(), "kernel_creation_time": process_creation(os.getpid()), "started_at": utc(),
        "frozen_head": args.expected_head, "actual_head": git(ROOT, "rev-parse", "HEAD").decode().strip(),
        "cwd": str(ROOT), "executable": sys.executable, "python": sys.version, "execution_mode": "SIMULATED"}
    save(out, "identity.json", identity)
    run_id, now = "a09-q4-" + str(os.getpid()), utc()
    refusals, normal_attempts, successes = [], 0, 0
    try:
        if identity["actual_head"] != args.expected_head:
            raise ValueError("running HEAD differs from frozen candidate")
        # Every imported project source and bound input has already been frozen.
        members = parse((out.parent / "runtime-members.json").read_bytes())
        for member in members:
            if sha((ROOT / member["path"]).read_bytes()) != member["sha256"]:
                raise ValueError("runtime member raw bytes differ: " + member["path"])
        inputs = load_inputs(args.inputs / "stage.zip", args.inputs / "proposal.json", args.inputs / "approval.json",
                             args.inputs / "input-registry.json", ROOT / "config/policies/a09-q4-offline-v1.json")
        save(out, "input-bytes.json", [{"name": f.name, "bytes": len(getattr(inputs, f.name)), "sha256": sha(getattr(inputs, f.name))} for f in dataclasses.fields(inputs)])
        target = MemoryTarget()
        normal_attempts += 1
        stages["normal"] = "STARTED"
        bundle, plan, facts = prepare(inputs, target, out / "normal", run_id, now)
        snap = next(a for a in bundle.artifacts if a.kind == "PlatformSnapshot")
        assert_plan_ready(bundle, artifact_ref(plan), artifact_ref(snap))
        save(out, "normal/prepared-bundle.json", bundle.model_dump(mode="json"))
        save(out, "normal/approved-frame-oracle.json", approved_frames(facts))
        final, receipt, before, after, comparison = execute(inputs, target, bundle, artifact_ref(plan), out / "normal", run_id, now)
        save(out, "normal/final-bundle.json", final.model_dump(mode="json"))
        save(out, "normal/receipt.json", receipt)
        save(out, "normal/comparison.json", comparison)
        actual = [after["view"]["frame_projections"][f["platform_frame_id"]] for f in after["view"]["target"]["frames"]]
        assert not compare_approved_frames(actual, facts)
        assert comparison["effect_match"] == "MATCH" and comparison["approval_table_match"]
        assert receipt["payload"]["execution_mode"] == "SIMULATED" and receipt["payload"]["results"][0]["outcome"] == "APPLIED"
        assert len(before["view"]["target"]["questions"]) == len(before["view"]["target"]["frames"]) == 0
        assert len(after["view"]["target"]["questions"]) == 1 and len(after["view"]["target"]["frames"]) == 4
        assert after["view"]["epoch"] == 1 and not target.held
        successes += 1
        stages["normal"] = "PASS"

        def reject(name, call, expected_layer, expected_code, subject=target):
            stages[name] = "STARTED"
            old = subject.snapshot_view()
            try:
                call()
            except Q4Error as error:
                assert (error.layer, error.code) == (expected_layer, expected_code), (error.layer, error.code)
                new = subject.snapshot_view()
                assert old == new
                record = {"case": name, "reached_layer": error.layer, "code": error.code, "rejected": True,
                    "target_instance": subject.instance_id, "before_sha256": sha(encode(old)), "after_sha256": sha(encode(new)),
                    "new_questions": 0, "new_frames": 0, "business_dispatches": 0}
                refusals.append(record)
                save(out, "refusals/" + name + ".json", record)
                stages[name] = "PASS"
            else:
                raise AssertionError("required rejection did not occur: " + name)

        def attempt(changed):
            return execute(changed, target, bundle, artifact_ref(plan), out / "normal", run_id, now)

        reject("missing_approval", lambda: attempt(dataclasses.replace(inputs, approval_raw=b"")), "AUTHORIZATION", "APPROVAL_MISSING")
        reject("altered_approval", lambda: attempt(dataclasses.replace(inputs, approval_raw=inputs.approval_raw + b"\n")), "AUTHORIZATION", "APPROVAL_BINDING")
        reject("q1_approval", lambda: attempt(dataclasses.replace(inputs, approval_raw=(args.inputs / "q1-approval.json").read_bytes())), "AUTHORIZATION", "APPROVAL_BINDING")
        reject("replaced_input", lambda: attempt(dataclasses.replace(inputs, stage_raw=inputs.stage_raw + b"\n")), "AUTHORIZATION", "INPUT_BINDING")
        proposal = parse(inputs.proposal_raw)
        proposal["approvals"]["simulation_run_authorized"] = True
        reject("replaced_proposal", lambda: attempt(dataclasses.replace(inputs, proposal_raw=encode(proposal))), "AUTHORIZATION", "INPUT_BINDING")

        stages["resealed_image_as_text"] = "STARTED"
        old = target.snapshot_view()
        source, _ = build_source(inputs, out / "semantic", run_id + "-type", now)
        resealed = image_as_text(source, out / "semantic")
        checked, report = pre_apply(resealed, inputs, out / "semantic", run_id + "-type", now)
        assert report["payload"]["decision"] == "HOLD"
        results = {c["check_id"]: c["outcome"] for c in report["payload"]["checks"]}
        assert results == {"source_integrity": "PASS", "structure": "FAIL", "answer_matching": "PASS", "coverage": "PASS", "policy": "FAIL"}
        assert old == target.snapshot_view()
        record = {"case": "resealed_image_as_text", "reached_layer": "PRE_APPLY.structure.types_match_approval / policy.image_text_text_text",
            "code": "COMPUTED_HOLD", "C01_resealed_valid": True, "checks": results, "rejected": True,
            "before_sha256": sha(encode(old)), "after_sha256": sha(encode(target.snapshot_view())), "new_questions": 0, "new_frames": 0, "business_dispatches": 0}
        refusals.append(record)
        save(out, "semantic/legally-resealed-checked-bundle.json", checked.model_dump(mode="json"))
        save(out, "refusals/resealed_image_as_text.json", record)
        stages["resealed_image_as_text"] = "PASS"
        reject("platform_mode", lambda: prepare(inputs, target, out / "platform", run_id, now, execution_mode="PLATFORM"), "TARGET", "PLATFORM_MODE_FORBIDDEN")
        wrong = MemoryTarget(book_id="wrong-book")
        reject("wrong_target", lambda: execute(inputs, wrong, bundle, artifact_ref(plan), out / "wrong", run_id, now), "TARGET", "TARGET_IDENTITY", wrong)
        stale = MemoryTarget()
        stale_bundle, stale_plan, _ = prepare(inputs, stale, out / "stale", run_id + "-stale", now)
        stale.inject_external_change_for_refusal()
        reject("stale_target", lambda: execute(inputs, stale, stale_bundle, artifact_ref(stale_plan), out / "stale", run_id + "-stale", now), "TARGET", "TARGET_CHANGED", stale)
        reject("same_plan_replay", lambda: attempt(inputs), "EXECUTION", "PLAN_REPLAY")
        assert len(refusals) == 10 and all(v == "PASS" for v in stages.values())
        save(out, "summary.json", {"status": "AUTHOR_TRIAL_PASS_NOT_INDEPENDENT_ACCEPTANCE", "identity": identity, "stages": stages,
            "normal_attempts": normal_attempts, "successful_normal_closures": successes, "business_dispatches": 1,
            "actual_questions_added": 1, "actual_frames_added": 4, "memory_targets_created": 3, "refusal_calls": len(refusals), "refusals": refusals,
            "actual_frames": actual, "approval_comparison_differences": [], "assert_plan_ready": "RETURNED_SUCCESSFULLY",
            "source_evidence_graph_precheck": "OBSERVED", "target_plan_receipt": "SYNTHETIC", "execution_mode": "SIMULATED",
            "policy": "A_INTERNAL_PROPOSAL/PROPOSAL_ONLY", "content_check_status": "PENDING", "submission_status": "NOT_SUBMITTED",
            "other_three_cases": "HOLD_NO_RELATIONS_NO_EXECUTION", "full_external_G_Check_plan": "DECLARED_ONLY_EXTERNAL_NOT_LOADED",
            "platform_calls": 0, "B_producers_executed": 0, "A08_CLI_calls": 0, "B_messages": 0, "pushes": 0,
            "child_ended_at": utc(), "background_services_started": 0})
        print("A09: one normal closure, four actual frames, ten bounded refusals; author trial only", flush=True)
        return 0
    except BaseException as error:
        for name, state in stages.items():
            if state == "STARTED":
                stages[name] = "FAIL"
        save(out, "failure.json", {"identity": identity, "stages": stages, "normal_attempts": normal_attempts, "successful_normal_closures": successes,
            "exception": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(), "ended_at": utc(),
            "rule": "First failure retained; successors NOT_RUN; no automatic retry"})
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
