"""One bounded A07 complete experiment; a new output directory is mandatory."""
import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from annotation.contracts import artifact_ref
from annotation.source.b_q1.reader import APPROVAL_SHA, POLICY_SHA, Q1Error, load_inputs, sha
from .engine import MemoryTarget, prepare, execute


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    summary = {"pid": os.getpid(), "run_id": args.run_id, "complete_attempts": 1, "dispatches": 0, "successful_closures": 0,
               "execution_mode": "SIMULATED", "submission_status": "NOT_SUBMITTED", "content_check_status": "PENDING",
               "approval_sha256": APPROVAL_SHA, "policy_sha256": POLICY_SHA, "platform_calls": 0, "model_calls": 0,
               "B_joint_adoption_proven": False, "independent_human_visual_review_proven": False}
    code = 2
    target = MemoryTarget()
    try:
        input_dir = Path(args.input_dir)
        inputs = load_inputs(input_dir / "base.zip", input_dir / "candidate.zip", input_dir / "history.json", input_dir / "approval.json", args.policy)
        created = datetime.now(timezone.utc).isoformat()
        bundle, plan, facts = prepare(inputs, target, root, args.run_id, created)
        (root / "pre-execution.json").write_text(json.dumps(bundle.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary["input_sha256"] = facts["policy"]["input_sha256"]
        summary["plan_ref"] = artifact_ref(plan)
        summary["dispatches"] = 1
        final, receipt, before, after, comparison = execute(inputs, target, bundle, artifact_ref(plan), root, args.run_id, created)
        (root / "exchange.json").write_text(json.dumps(final.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (root / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (root / "comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary.update(receipt_ref=artifact_ref(receipt), question_count=len(after["view"]["target"]["questions"]),
            frame_count=len(after["view"]["target"]["frames"]), before_state_hash=before["target_state_hash"],
            after_state_hash=after["target_state_hash"], actual_read_sequences=[before["read_sequence"], after["read_sequence"]],
            outcome=receipt["payload"]["results"][0]["outcome"], target_held=target.held)
        matched = summary["outcome"] == "APPLIED" and summary["question_count"] == 1 and summary["frame_count"] == 6
        summary["successful_closures"] = int(matched)
        summary["result"] = "READY_FOR_REVIEW" if matched else "FAILED_STOPPED"
        # Negative replay consumes no second business dispatch and must leave the target byte-identical.
        old = target.snapshot_view()
        try:
            execute(inputs, target, bundle, artifact_ref(plan), root, args.run_id, created)
            raise AssertionError("executed plan replay was accepted")
        except Q1Error as exc:
            replay = {"layer": exc.layer, "code": exc.code, "zero_target_change": old == target.snapshot_view(), "business_dispatches": 0}
            assert exc.code == "PLAN_REPLAY" and replay["zero_target_change"]
            (root / "replay-rejection.json").write_text(json.dumps(replay, indent=2) + "\n", encoding="utf-8")
        summary["rejection_calls"] = 1
        current_inputs = load_inputs(input_dir / "base.zip", input_dir / "candidate.zip", input_dir / "history.json", input_dir / "approval.json", args.policy)
        assert current_inputs == inputs
        summary["input_bytes_unchanged"] = True
        code = 0 if matched else 2
    except BaseException as exc:
        summary.update(result="FAILED_STOPPED", error_type=type(exc).__name__, error=str(exc),
                       error_layer=getattr(exc, "layer", None), error_code=getattr(exc, "code", None), target_held=target.held)
        (root / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        summary["final_memory_state_hash"] = sha(json.dumps(target.snapshot_view(), sort_keys=True).encode())
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        summary["services_started"] = 0
        summary["browsers_started"] = 0
        summary["process_exit_code"] = code
        (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
