"""Execute a hash-bound stable-target manifest with whole-batch preflight.

Old order-only arguments are deliberately rejected: inserted questions can move
every later native order. This entry reuses the existing one-question writer.
"""
import argparse
from datetime import datetime, timezone
import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from annotation.runtime.usense_live import batch
from annotation.runtime.usense_live.config import endpoints
from annotation.runtime.usense_live.core import require, sha, write_new, profile_identity, LOCKS
from annotation.runtime.usense_live.update import loads, from_captured_map, compare_batch_readback, json_same, validate_plan


def now():
    return datetime.now(timezone.utc).isoformat()


def write_plan(path, plan):
    """Keep native object order: it is part of update plan identity."""
    validate_plan(plan)
    raw = json.dumps(plan, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    validate_plan(loads(path.read_bytes()))


def check_resources(profile, dependency_dir):
    require(os.name == "nt", "WINDOWS_REQUIRED")
    profile, _ = profile_identity(str(profile))
    require(not any((profile / name).exists() for name in LOCKS), "PROFILE_LOCK_PRESENT")
    if dependency_dir:
        require(Path(dependency_dir).is_absolute() and Path(dependency_dir).is_dir(), "BATCH_DEPENDENCY_DIRECTORY_REQUIRED")
        sys.path.insert(0, str(Path(dependency_dir)))
    try:
        require(importlib.util.find_spec("playwright.async_api") is not None, "PYTHON_PLAYWRIGHT_REQUIRED")
        from playwright.async_api import BrowserContext
        require(hasattr(BrowserContext, "route_web_socket"), "PLAYWRIGHT_WEBSOCKET_GUARD_REQUIRED")
    finally:
        if dependency_dir:
            sys.path.pop(0)
    edge = [Path(os.environ.get(key, "C:/missing")) / "Microsoft/Edge/Application/msedge.exe"
            for key in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
    require(any(path.is_file() for path in edge), "MICROSOFT_EDGE_REQUIRED")


def child(args, record, dependency_dir=None):
    boot = "import sys,runpy;sys.path.insert(0,sys.argv[1]);entry=sys.argv[2];sys.argv=[entry]+sys.argv[3:];runpy.run_path(entry,run_name='__main__')"
    entry = str(ROOT / "tools/run_usense_live.py")
    cmd = [sys.executable, "-B", entry, *map(str, args)]
    if dependency_dir:
        cmd = [sys.executable, "-B", "-c", boot, dependency_dir, entry, *map(str, args)]
    started = now()
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=960)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate(timeout=10)
    # Preserve original process bytes even when parsing or the child fails.
    for suffix, value in ((".stdout", stdout), (".stderr", stderr)):
        with record.with_suffix(suffix).open("xb") as stream:
            stream.write(value)
    result = None
    try:
        result = loads(stdout.decode("utf-8").strip().splitlines()[-1])
    except (ValueError, IndexError, UnicodeError):
        pass
    value = {"pid": process.pid, "argv": cmd, "cwd": str(Path.cwd()), "started_at": started,
             "finished_at": now(), "exit_code": process.returncode, "result": result,
             "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr), "timed_out": timed_out}
    write_new(record, value)
    require(not timed_out, "CHILD_TIMEOUT_UNKNOWN_NO_RETRY_OS_RELEASE_UNPROVEN")
    require(type(result) is dict, "CHILD_OUTPUT_NOT_JSON_NO_RETRY")
    require(process.returncode == 0, "CHILD_FAILED_STOP_NO_RETRY")
    return value


def execute(prepared, out, baseline, profile, authorization, tls, run_child, proxy_server=None):
    targets = prepared["targets"]
    summary = {"schema": "UsenseReviewedBatch/v2", "book_id": "46007447", "status": "RUNNING",
               "manifest_sha256": prepared["manifest_sha256"], "started_at": now(),
               "results": [{"target": item["target"], "printed_question": item["printed_question"],
                            "semantic_lesson": item["semantic_lesson"], "status": "NOT_RUN"} for item in targets]}
    current = None
    try:
        require(json_same(prepared["transport"], {"mode": "DIRECT" if proxy_server is None else "HTTP_CONNECT_PROXY",
                                                "proxy_server": proxy_server}), "BATCH_TRANSPORT_MUST_MATCH_CURRENT_CAPTURE")
        # Materialize every plan and evidence binding before any configure/browser.
        for item in targets:
            # Bounded directory name independent of native order and label.
            qout = out / ("target-" + sha(item["target"]["node_id"].encode())[:24])
            qout.mkdir()
            item["qout"] = qout
            write_plan(qout / "plan.json", item["plan"])
            refs = {item["candidate"]["path"]: item["candidate"]["sha256"], **item["review_evidence"]}
            write_new(qout / "review-evidence-hashes.json", refs)
            for path in (qout / "plan.json", qout / "review-evidence-hashes.json"):
                prepared["evidence_file_sha256"][str(path)] = sha(path.read_bytes())
        for index, item in enumerate(targets):
            current = summary["results"][index]
            batch.recheck(prepared, targets[index:])
            current["status"] = "PREPARING"
            qout, plan = item["qout"], item["plan"]
            order, pages = item["target"]["question_order"], item["source_pages"]

            def configure(label):
                batch.recheck(prepared, targets[index:])
                cfg = qout / (label + "-config.json")
                configured = run_child(["configure", "--profile", profile, "--output-root", out, "--config", cfg,
                    "--coordinator", "root-takeover", "--executor", label + "-process", "--reviewer", "existing-update-reviewer",
                    "--authorization-reference", authorization, "--tls-approval-reference", tls,
                    "--orders", order, "--pages", *pages, "--source", *([] if proxy_server is None else ["--proxy-server", proxy_server])],
                    qout / (label + "-configuration-result.json"))
                return cfg, configured["result"]["sha256"]

            cfg, digest = configure("writer")
            batch.recheck(prepared, targets[index:])
            previous = [] if item["previous_acceptance"] is None else ["--previous-acceptance", item["previous_acceptance"]["path"]]
            wp = run_child(["--writer", "--config", cfg, "--sha256", digest, "--plan", qout / "plan.json",
                "--plan-sha256", sha((qout / "plan.json").read_bytes()), "--baseline", baseline,
                "--ledger-root", prepared["ledger_root"], "--authorization-reference", authorization, *previous],
                qout / "writer-process-result.json")
            w = wp["result"]
            require(w["status"] in ("NO_OP_CURRENT_STATE_CONFIRMED", "RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK") and
                    w.get("release", {}).get("context_runtime_release_confirmed") is True, "WRITER_UNKNOWN_OR_RELEASE_UNPROVEN_NO_RETRY")
            # The successful writer spent its own intent. Only pending successors
            # should retain their initial ledger snapshot from this point onward.
            item["ledger_files"] = {str(p): sha(p.read_bytes()) for p in Path(prepared["ledger_root"]).glob(plan["ledger_key"] + "*.json")}
            readcfg, readdigest = configure("independent-reader")
            rp = run_child(["capture", "--config", readcfg, "--sha256", readdigest], qout / "reader-process-result.json")
            r = rp["result"]
            names = endpoints([order], pages, source=True)
            after = {name: loads((out / r["run_id"] / (name + ".json")).read_bytes()) for name in names}
            comparison = compare_batch_readback(plan, from_captured_map(after, f"q{order}_"))
            source_same = all(json_same(loads((baseline / (name + ".json")).read_bytes()), after[name])
                              for name in names if name == "source" or name.startswith("page_"))
            checks = {"writer_exit_zero": wp["exit_code"] == 0, "reader_exit_zero": rp["exit_code"] == 0,
                "writer_expected_status": w["status"] == ("RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK" if plan["mutation_required"] else "NO_OP_CURRENT_STATE_CONFIRMED"),
                "reader_success": r["status"] == "NATIVE_GETS_CAPTURED", "reader_writes_zero": r["save_attempts"] == 0,
                "reader_released": r["release"]["context_runtime_release_confirmed"],
                "different_processes": wp["pid"] != rp["pid"], "different_contexts": w["run_id"] != r["run_id"],
                "reader_started_after_writer_exit": datetime.fromisoformat(rp["started_at"]) > datetime.fromisoformat(wp["finished_at"]),
                "every_read_after_writer": all(datetime.fromisoformat(v["observed_at"]) > datetime.fromisoformat(wp["finished_at"]) for v in r["captures"].values()),
                "native_full_state_matches": comparison["match"], "source_page_responses_unchanged": source_same,
                "one_send_or_noop": w["post_attempts"] == (1 if plan["mutation_required"] else 0)}
            accepted = all(checks.values())
            limited = comparison.get("schema") == "UsenseBatchCreatedZoneReadback/v1"
            current.update(status=("ACCEPTED_CREATED_ZONE_ORDER" if limited else "ACCEPTED") if accepted else "FAILED_STOP", checks=checks, comparison=comparison,
                changed_zones=[c["zone"] for c in plan["changes"]], writer_run=w["run_id"], reader_run=r["run_id"],
                post_attempts=w["post_attempts"], plan_file_sha256=sha((qout / "plan.json").read_bytes()),
                reviewed_candidate_sha256=item["candidate"]["sha256"])
            if limited:
                # No standard accepted marker: revision.py continues to require
                # its unchanged, fully strict predecessor evidence chain.
                current["revision_predecessor_eligible"] = False
            write_new(qout / "acceptance.json", current)
            require(accepted, "READBACK_ACCEPTANCE_FAILED")
            if plan["mutation_required"] and not limited:
                write_new(Path(prepared["ledger_root"]) / (w["intent_key"] + ".accepted.json"),
                    {"plan_sha256": plan["plan_sha256"], "writer_run": w["run_id"], "reader_run": r["run_id"],
                     "acceptance_sha256": sha((qout / "acceptance.json").read_bytes())})
            current = None
        summary["status"] = "ALL_ACCEPTED"
    except BaseException as exc:
        if current is not None and current["status"] != "FAILED_STOP":
            current["status"] = "STOPPED_NO_RETRY"
        summary.update(status="STOPPED_NO_RETRY", error_type=type(exc).__name__, error_code=getattr(exc, "code", str(exc)))
    finally:
        summary["finished_at"] = now()
        write_new(out / "batch-summary.json", summary)
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "manifest-sha256", "profile", "baseline", "out", "authorization-reference", "tls-approval-reference"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--repo", default=str(ROOT))
    p.add_argument("--dependency-dir")
    p.add_argument("--proxy-server")
    p.add_argument("--preflight-only", action="store_true")
    a = p.parse_args(argv)
    require(Path(a.repo).resolve() == ROOT, "BATCH_REPOSITORY_MUST_MATCH_ENTRY")
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    baseline, profile = Path(a.baseline).resolve(), Path(a.profile).resolve()
    supplied_schema = loads(Path(a.manifest).read_bytes()).get('schema')
    lesson_mode = supplied_schema == 'A28ReviewedLessonManifest/v1'
    try:
        if lesson_mode:
            from annotation.runtime.usense_live import lesson_batch
            prepared = lesson_batch.prepare(a.manifest, a.manifest_sha256, baseline, profile, a.authorization_reference)
        else:
            prepared = batch.prepare(a.manifest, a.manifest_sha256, baseline, profile, a.authorization_reference)
        require(json_same(prepared["transport"], {"mode": "DIRECT" if a.proxy_server is None else "HTTP_CONNECT_PROXY",
                                                "proxy_server": a.proxy_server}), "BATCH_TRANSPORT_MUST_MATCH_CURRENT_CAPTURE")
        check_resources(profile, a.dependency_dir)
    except BaseException as exc:
        # These labels describe supplied, unvalidated manifest entries only.
        # They do not promote any identity or partial preflight to acceptance.
        try:
            supplied = loads(Path(a.manifest).read_bytes()).get("targets", [])
            not_run = [{"target": item.get("target"), "printed_question": item.get("printed_question"),
                        "status": "NOT_RUN", "identity_validated": False} for item in supplied if type(item) is dict]
        except (ValueError, OSError, AttributeError, TypeError):
            not_run = []
        write_new(out / "batch-summary.json", {"schema": "UsenseReviewedBatch/v2", "status": "PREFLIGHT_FAILED_ALL_NOT_RUN",
            "all_targets": "NOT_RUN", "results": not_run, "error_type": type(exc).__name__, "error_code": getattr(exc, "code", str(exc)), "finished_at": now()})
        raise
    write_new(out / "batch-preflight.json", prepared)
    if a.preflight_only:
        print(json.dumps({"status": "PREFLIGHT_ONLY_NO_BROWSER", "targets": len(prepared["targets"])}))
        return 0
    if lesson_mode:
        result = lesson_batch.execute(prepared, out, baseline, profile, a.authorization_reference, a.tls_approval_reference,
                     lambda args, record: child(args, record, a.dependency_dir), write_plan)
    else:
        result = execute(prepared, out, baseline, profile, a.authorization_reference, a.tls_approval_reference,
                     lambda args, record: child(args, record, a.dependency_dir), a.proxy_server)
    print(json.dumps({"status": result["status"], "results": result["results"]}, ensure_ascii=True))
    return 0 if result["status"] in ("ALL_ACCEPTED", "ALL_FOUR_ACCEPTED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
