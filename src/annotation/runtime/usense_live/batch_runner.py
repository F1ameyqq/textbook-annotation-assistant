"""Sequential process orchestration only. Network transport stays in writer/capture.

This module is imported only by explicit `run`. A durable dispatch precedes any
child process; interruption or unknown evidence blocks subsequent dispatches.
"""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

from .batch import (inspect_state, loads, read, ref_bytes, require, sha, validate_batch, write_new)
from .config import endpoints
from .revision import released
from .update import compare_readback, from_captured_map, json_same


def child(args, record, dependency_dir=None):
    entry = Path(__file__).resolve().parents[4] / "tools" / "run_usense_live.py"
    require(entry.is_file(), "BATCH_REPOSITORY_TOOL_REQUIRED")
    boot = "import sys,runpy;sys.path.insert(0,sys.argv[1]);entry=sys.argv[2];sys.argv=[entry]+sys.argv[3:];runpy.run_path(entry,run_name='__main__')"
    command = [sys.executable, "-B"]
    if dependency_dir:
        command += ["-c", boot, str(Path(dependency_dir).resolve()), str(entry)]
    else:
        command += [str(entry)]
    command += list(map(str, args))
    started = datetime.now(timezone.utc).isoformat()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", errors="replace")
    try:
        stdout, _stderr = process.communicate(timeout=150)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=10)
        write_new(record, {"pid": process.pid, "started_at": started, "status": "TIMEOUT_UNKNOWN_NO_RETRY", "os_release_unproven": True})
        raise ValueError("BATCH_CHILD_TIMEOUT_UNKNOWN_NO_RETRY")
    finished = datetime.now(timezone.utc).isoformat()
    try:
        result = loads(stdout.strip().splitlines()[-1])
        require(type(result) is dict, "BATCH_CHILD_RESULT_NOT_OBJECT")
    except (ValueError, IndexError):
        # No stdout/stderr copied: browser errors could contain private payloads.
        write_new(record, {"pid": process.pid, "exit_code": process.returncode, "status": "CHILD_OUTPUT_NOT_JSON_NO_RETRY"})
        raise ValueError("BATCH_CHILD_OUTPUT_UNKNOWN_NO_RETRY")
    write_new(record, {"pid": process.pid, "started_at": started, "finished_at": finished,
                       "exit_code": process.returncode, "result": result})
    return process.returncode, result


def run_item(batch, item, root, args):
    update, ident = item["plan"], item["mapping"]["item_id"]
    qdir = root / ident
    qdir.mkdir(exist_ok=False)
    write_new(qdir / "dispatch.json", {"batch_sha256": batch["batch_sha256"], "intent_key": item["intent_key"]})
    write_new(qdir / "plan.json", update)
    write_new(qdir / "review-evidence-hashes.json", batch["evidence_file_sha256"])
    baseline = qdir / "baseline"
    baseline.mkdir()
    native = {}
    for name, ref in item["baseline_files"].items():
        raw = ref_bytes(ref)
        with (baseline / (name + ".json")).open("xb") as stream:
            stream.write(raw)
        native[name] = loads(raw)
    q, pages = update["target"]["question_order"], item["pages"]

    def configure(label):
        cfg = qdir / (label + "-config.json")
        command = ["configure", "--profile", args.profile, "--output-root", root, "--config", cfg,
                   "--coordinator", "reviewed-batch", "--executor", label + "-process", "--reviewer", "source-review-record",
                   "--authorization-reference", args.authorization_reference, "--orders", q, "--pages", *pages, "--source"]
        if args.tls_approval_reference:
            command += ["--tls-approval-reference", args.tls_approval_reference]
        code, result = child(command, qdir / (label + "-configuration-result.json"), args.dependency_dir)
        require(code == 0, "BATCH_CONFIGURATION_FAILED")
        return cfg, result["sha256"]

    cfg, checksum = configure("writer")
    validate_batch(batch, fresh=True)
    command = ["--writer", "--config", cfg, "--sha256", checksum, "--plan", qdir / "plan.json",
               "--plan-sha256", sha((qdir / "plan.json").read_bytes()), "--baseline", baseline,
               "--ledger-root", batch["ledger_root"], "--authorization-reference", args.authorization_reference]
    if item["previous_acceptance"] is not None:
        command += ["--previous-acceptance", item["previous_acceptance"]["path"]]
    code, writer = child(command, qdir / "writer-process-result.json", args.dependency_dir)
    require(released(writer.get("release", {})), "BATCH_WRITER_RELEASE_UNPROVEN")
    # UNKNOWN is terminal for this executor. Independent recovery belongs to a
    # separate audited workflow and never triggers another writer here.
    require(code == 0 and writer.get("status") == "RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK",
            "BATCH_WRITER_UNKNOWN_OR_FAILED_NO_RETRY")
    cfg, checksum = configure("independent-reader")
    rcode, reader = child(["capture", "--config", cfg, "--sha256", checksum], qdir / "reader-process-result.json", args.dependency_dir)
    require(rcode == 0 and reader.get("status") == "NATIVE_GETS_CAPTURED" and released(reader.get("release", {})),
            "BATCH_READER_FAILED_NO_RETRY")
    import re
    require(re.fullmatch(r"usense-readonly-[a-z0-9-]{1,64}", reader["run_id"]), "BATCH_READER_RUN_PATH")
    names = endpoints([q], pages, source=True)
    after = {name: read(root / reader["run_id"] / (name + ".json")) for name in names}
    comparison = compare_readback(update, from_captured_map(after, f"q{q}_"))
    checks = {"writer_exit_zero": code == 0, "reader_exit_zero": rcode == 0,
              "native_full_state_matches": comparison["match"], "reader_writes_zero": reader.get("save_attempts") == 0,
              "different_contexts": writer["run_id"] != reader["run_id"], "one_send": writer.get("post_attempts") == 1,
              "intent_matches_prepared_identity": writer.get("intent_key") == item["intent_key"],
              "source_page_responses_unchanged": all(json_same(native[name], after[name]) for name in names
                                                    if name == "source" or name.startswith("page_"))}
    require(all(checks.values()), "BATCH_READBACK_FAILED_NO_RETRY")
    acceptance = {"status": "ACCEPTED", "checks": checks, "target": update["target"],
                  "writer_run": writer["run_id"], "reader_run": reader["run_id"], "comparison": comparison,
                  "plan_file_sha256": sha((qdir / "plan.json").read_bytes())}
    write_new(qdir / "acceptance.json", acceptance)
    marker = Path(batch["ledger_root"]) / (item["intent_key"] + ".accepted.json")
    write_new(marker, {"plan_sha256": update["plan_sha256"], "writer_run": writer["run_id"],
                       "reader_run": reader["run_id"], "acceptance_sha256": sha((qdir / "acceptance.json").read_bytes())})
    # Full existing verifier proves process order, raw bytes, receipt and guard
    # events before this runner considers moving on to the next question.
    state = inspect_state(batch, root, running=True)
    require(next(row for row in state["items"] if row["item_id"] == ident)["status"] == "ACCEPTED",
            "BATCH_FULL_ACCEPTANCE_PROOF_FAILED_NO_RETRY")


def run_batch(batch, args):
    validate_batch(batch)
    require(type(args.authorization_reference) is str and bool(args.authorization_reference.strip()), "CURRENT_WRITE_AUTHORIZATION_REFERENCE_REQUIRED")
    require(Path(batch["ledger_root"]) == Path(args.profile).resolve().parent / "usense-existing-ledger", "BATCH_PROFILE_LEDGER_MISMATCH")
    root = Path(args.execution_root).resolve()
    state = inspect_state(batch, root)
    require(state["status"] != "BLOCKED_NO_RETRY", "BATCH_RESUME_BLOCKED_NO_RETRY")
    if state["status"] == "COMPLETE_OFFLINE_AUDIT":
        return state
    root.mkdir(parents=True, exist_ok=True)
    # Exclusive batch lock is separate from the writer's profile and stable-ID
    # protection. Never remove a lock left by an interrupted process automatically.
    lock = root / "batch-running.lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(batch["batch_sha256"])
    try:
        binding = root / "batch-binding.json"
        if binding.exists():
            require(read(binding) == {"batch_sha256": batch["batch_sha256"]}, "BATCH_EXECUTION_ROOT_ALREADY_BOUND")
        else:
            write_new(binding, {"batch_sha256": batch["batch_sha256"]})
        dispatched = 0
        while True:
            state = inspect_state(batch, root, running=True)
            require(state["status"] != "BLOCKED_NO_RETRY", "BATCH_RESUME_BLOCKED_NO_RETRY")
            if state["next_item_id"] is None:
                state["audit_platform_requests"] = state.pop("platform_requests")
                state["live_execution"] = "EXPLICIT_EXISTING_WRITER_AND_CAPTURE_CHILDREN"
                state["dispatched_items_this_invocation"] = dispatched
                return state
            validate_batch(batch, fresh=True)
            item = next(item for item in batch["items"] if item["mapping"]["item_id"] == state["next_item_id"])
            run_item(batch, item, root, args)
            dispatched += 1
    finally:
        lock.unlink()
