"""One separately authorized GET-only readback after outer writer Job release.

Input request and authority are frozen/hash-bound by the coordinator. This tool
has no writer dispatch, retry, accepted-ledger repair or revision promotion.
The authority directory's atomic claim fences every reuse of that authority.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]
from annotation.runtime.usense_live.core import (require, sha, plain_path, profile_identity,
                                                LOCKS, write_new, utc, load_binding)
from annotation.runtime.usense_live.config import capture_endpoints
from annotation.runtime.usense_live.update import loads
from annotation.runtime.usense_live.revision import same
from annotation.runtime.usense_live.postsave import verify_writer, verify_reader, run_id
from run_usense_reviewed_batch import child


WRITER_KEYS = {"plan", "execution", "writer_config", "writer_process", "writer_stdout", "writer_stderr",
               "receipt", "intent", "send_intent", "writer_events", "holder", "before"}


def read_ref(ref):
    require(type(ref) is dict and set(ref) == {"path", "sha256"} and
            type(ref["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]), "RECOVERY_FILE_REF")
    raw = plain_path(ref["path"]).read_bytes()
    require(sha(raw) == ref["sha256"], "RECOVERY_FILE_CHANGED")
    return raw


def bound_inputs(request):
    refs = request["writer_evidence"]
    require(type(refs) is dict and set(refs) == WRITER_KEYS and type(refs["before"]) is dict, "RECOVERY_WRITER_INPUT_SET")
    return {key: ({name: read_ref(ref) for name, ref in value.items()} if key == "before" else read_ref(value))
            for key, value in refs.items()}


def ledger_snapshot(root):
    # Read hashes only; never create, remove, rewrite or mark an intent accepted.
    return {p.name: sha(p.read_bytes()) for p in sorted(root.glob("*.json"))}


def prepare_request(writer_qdir, holder_path, holder_sha256, output_root, request_path):
    """Assemble a frozen request from a stopped batch, without dispatch or grant.

The original outer holder's hash must come from its separately accepted release
record. This function validates the whole chain and only creates a new request.
"""
    qdir = plain_path(str(writer_qdir))
    cfg = loads((qdir / "writer-config.json").read_bytes())
    wd = plain_path(str(qdir.parent / run_id(cfg["run_id"])))
    ledger = plain_path(str(Path(cfg["profile"]["directory"]).parent / "usense-existing-ledger"))
    plan = loads((qdir / "plan.json").read_bytes())
    names = capture_endpoints(type("Binding", (), {"data": cfg})())
    def ref(path):
        path = plain_path(str(path))
        return {"path": str(path), "sha256": sha(path.read_bytes())}
    require(read_ref(ref(wd / "plan.json")) == (qdir / "plan.json").read_bytes(), "RECOVERY_WRITER_PLAN_COPY_CHANGED")
    refs = {"plan": ref(qdir / "plan.json"), "execution": ref(wd / "execution-result.json"),
            "writer_config": ref(qdir / "writer-config.json"), "writer_process": ref(qdir / "writer-process-result.json"),
            "writer_stdout": ref(qdir / "writer-process-result.stdout"), "writer_stderr": ref(qdir / "writer-process-result.stderr"),
            "receipt": ref(wd / "native-receipt.json"), "intent": ref(ledger / (plan["ledger_key"] + ".json")),
            "send_intent": ref(wd / "send-intent.json"), "writer_events": ref(wd / "network-events.json"),
            "holder": {"path": str(holder_path), "sha256": holder_sha256},
            "before": {name: ref(wd / ("before-" + name + ".json")) for name in names}}
    request = {"schema": "UsensePostsaveReadbackRequest/v1", "writer_evidence": refs,
               "output_root": str(plain_path(str(output_root), must_exist=False)),
               "ledger_snapshot": ledger_snapshot(ledger)}
    verify_writer(bound_inputs(request))
    destination = plain_path(str(request_path), must_exist=False)
    profile = Path(cfg["profile"]["directory"]).resolve()
    require(all(destination != parent and parent not in destination.parents for parent in (profile, ledger, qdir, wd)),
            "RECOVERY_REQUEST_MUST_NOT_TOUCH_OLD_STATE")
    write_new(destination, request)
    return {"request_path": str(request_path), "request_sha256": sha(Path(request_path).read_bytes()),
            "status": "PREPARED_NO_AUTHORITY_NO_DISPATCH"}


def exclusive_profile(profile, *, run=subprocess.run):
    """Current OS observation, not a caller's success boolean or lock absence.

Fail closed when any Edge process has an unreadable command line. Require an
    no mention of this profile at all; ambiguous command lines stop conservatively.
    The full OS query is ephemeral; retain only identity/hash facts, no command text.
"""
    require(os.name == "nt", "WINDOWS_REQUIRED")
    command = "$OutputEncoding=[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); @(Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" -ErrorAction Stop | Select-Object ProcessId,CreationDate,CommandLine) | ConvertTo-Json -Depth 3 -Compress"
    response = run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                   capture_output=True, timeout=10)
    require(response.returncode == 0, "RECOVERY_PROCESS_OBSERVATION_FAILED")
    rows = loads(response.stdout.decode("utf-8-sig")) if response.stdout.strip() else []
    if type(rows) is dict:
        rows = [rows]
    require(type(rows) is list, "RECOVERY_PROCESS_OBSERVATION_SCHEMA")
    facts = []
    for row in rows:
        commandline = row.get("CommandLine")
        require(type(commandline) is str and bool(commandline.strip()) and
                type(row.get("ProcessId")) is int and row["ProcessId"] > 0 and row.get("CreationDate"),
                "RECOVERY_PROCESS_IDENTITY_UNKNOWN")
        # Conservatively reject any occurrence too: ambiguous quoting must not
        # allow a possibly occupied profile through to capture.
        normalized = commandline.replace("/", "\\").casefold()
        require(str(profile).replace("/", "\\").casefold() not in normalized,
                "RECOVERY_PROFILE_IN_USE")
        facts.append({"pid": row["ProcessId"], "creation": row["CreationDate"],
                      "command_sha256": sha(commandline.encode("utf-8"))})
    return {"observed_at": datetime.now(timezone.utc).isoformat(), "source": "Win32_Process",
            "profile": str(profile), "edge_processes": facts, "matching_profile_processes": 0}


def preflight(request_path, request_sha, authority_path, authority_sha):
    request = loads(read_ref({"path": str(request_path), "sha256": request_sha}))
    authority = loads(read_ref({"path": str(authority_path), "sha256": authority_sha}))
    require(type(request) is dict and set(request) == {"schema", "writer_evidence", "output_root", "ledger_snapshot"} and
            request["schema"] == "UsensePostsaveReadbackRequest/v1", "RECOVERY_REQUEST_SCHEMA")
    old = verify_writer(bound_inputs(request))
    limits = {"readers": 1, "contexts": 1, "posts": 0, "login": 0, "business_gets": len(old["names"]), "retries": 0}
    require(authority.get("schema") == "UsensePostsaveReadbackAuthority/v1" and
            authority.get("operation") == "READONLY_POSTSAVE_RECOVERY" and
            authority.get("request_sha256") == request_sha and same(authority.get("limits"), limits) and
            authority.get("status") == "AUTHORIZED" and
            type(authority.get("authority_id")) is str and re.fullmatch(r"[a-z0-9-]{16,64}", authority["authority_id"]),
            "RECOVERY_EXACT_NEW_AUTHORITY_REQUIRED")
    now = datetime.now(timezone.utc)
    require(utc(authority["not_before"]) <= now < utc(authority["expires_at"]) and
            0 < (utc(authority["expires_at"]) - utc(authority["not_before"])).total_seconds() <= 900 and
            utc(old["holder"]["finished_at"]) < utc(authority["not_before"]), "RECOVERY_AUTHORITY_WINDOW")
    profile, fingerprint = profile_identity(old["config"]["profile"]["directory"])
    require(fingerprint == old["config"]["profile"]["fingerprint"] and
            not any((profile / name).exists() for name in LOCKS), "RECOVERY_PROFILE_IDENTITY_OR_LOCK")
    ledger = plain_path(str(profile.parent / "usense-existing-ledger"))
    require(type(request["ledger_snapshot"]) is dict and
            ledger_snapshot(ledger) == request["ledger_snapshot"] and
            request["ledger_snapshot"].get(old["plan"]["ledger_key"] + ".json") == sha(read_ref(request["writer_evidence"]["intent"])) and
            not any(name.startswith(old["plan"]["ledger_key"]) and name != old["plan"]["ledger_key"] + ".json"
                    for name in request["ledger_snapshot"]), "RECOVERY_ORIGINAL_LEDGER_CHANGED_OR_HAS_SUCCESSOR")
    out = plain_path(request["output_root"], must_exist=False)
    # Never place recovery artifacts in either the actual profile or its ledger.
    require(all(out != parent and parent not in out.parents for parent in (profile, ledger)) and
            not out.exists(), "RECOVERY_FRESH_SEPARATE_OUTPUT_REQUIRED")
    return request, authority, old, profile, ledger, out


def execute(request_path, request_sha, authority_path, authority_sha, *, run_child=child, observe=exclusive_profile):
    request, authority, old, profile, ledger, out = preflight(request_path, request_sha, authority_path, authority_sha)
    observation = observe(profile)
    # An existing marker is a hard stop regardless of earlier result or output.
    marker = Path(authority_path).parent / ("postsave-readback-" + authority["authority_id"] + ".spent.json")
    write_new(marker, {"schema": "UsensePostsaveReadbackSpend/v1", "authority_sha256": authority_sha,
                      "request_sha256": request_sha, "spent_at": datetime.now(timezone.utc).isoformat(),
                      "remaining": 0, "automatic_retry_allowed": False})
    out.mkdir(exist_ok=False)
    result = {"schema": "UsensePostsaveReadbackRun/v1", "status": "STOPPED_NO_RETRY", "reader": "NOT_RUN",
              "request_sha256": request_sha, "authority_sha256": authority_sha, "posts": 0,
              "ledger_modified": False, "revision_predecessor_eligible": False}
    try:
        write_new(out / "profile-observation-before-configure.json", observation)
        q = old["plan"]["target"]["question_order"]
        pages = [int(name[5:]) for name in old["names"] if name.startswith("page_")]
        config = out / "independent-reader-config.json"
        proxy = old["config"]["transport"]["proxy_server"]
        remaining = int((utc(authority["expires_at"]) - datetime.now(timezone.utc)).total_seconds())
        require(remaining >= 30, "RECOVERY_AUTHORITY_TOO_SHORT")
        configured = run_child(["configure", "--profile", profile, "--output-root", out, "--config", config,
            "--coordinator", "root", "--executor", "postsave-independent-reader", "--reviewer", "independent-reviewer",
            "--authorization-reference", str(authority_path), "--tls-approval-reference", str(authority_path),
            "--orders", q, "--pages", *pages, "--source", "--seconds", remaining,
            *([] if proxy is None else ["--proxy-server", proxy])], out / "reader-configuration-result.json")
        digest = configured["result"]["sha256"]
        binding = load_binding(config, digest)
        require(same(binding.data["profile"], old["config"]["profile"]) and
                same(binding.data["transport"], old["config"]["transport"]) and
                capture_endpoints(binding) == old["names"] and binding.data["run_id"] != old["writer"]["run_id"],
                "RECOVERY_NEW_READER_CONFIG_CHANGED")
        # Re-read every fixed input and the whole ledger after configuration.
        require(sha(Path(request_path).read_bytes()) == request_sha and sha(Path(authority_path).read_bytes()) == authority_sha,
                "RECOVERY_APPROVAL_CHANGED")
        verify_writer(bound_inputs(request))
        require(ledger_snapshot(ledger) == request["ledger_snapshot"], "RECOVERY_LEDGER_CHANGED")
        binding.check(profile=True)
        write_new(out / "profile-observation-before-reader.json", observe(profile))
        result["reader"] = "STARTED_ONCE"
        rp = run_child(["capture", "--config", config, "--sha256", digest], out / "reader-process-result.json")
        r = rp["result"]
        require(r.get("run_id") == binding.data["run_id"], "RECOVERY_READER_RUN_CHANGED")
        rd = out / run_id(r["run_id"])
        raw = {"summary": (rd / "capture-summary.json").read_bytes(), "config": config.read_bytes(),
               "process": (out / "reader-process-result.json").read_bytes(),
               "stdout": (out / "reader-process-result.stdout").read_bytes(),
               "stderr": (out / "reader-process-result.stderr").read_bytes(),
               "events": (rd / "network-events.json").read_bytes(),
               "captures": {name: (rd / (name + ".json")).read_bytes() for name in old["names"]}}
        require(same(loads(raw["process"]), rp) and sha(config.read_bytes()) == digest, "RECOVERY_PROCESS_OR_CONFIG_CHANGED")
        compared = verify_reader(old, raw)
        require(sha(Path(request_path).read_bytes()) == request_sha and sha(Path(authority_path).read_bytes()) == authority_sha,
                "RECOVERY_APPROVAL_CHANGED_DURING_READ")
        verify_writer(bound_inputs(request))
        require(ledger_snapshot(ledger) == request["ledger_snapshot"], "RECOVERY_LEDGER_CHANGED_DURING_READ")
        write_new(out / "readonly-recovery.json", compared)
        result.update(status="READBACK_MATCHED_AFTER_OS_RELEASE", reader="COMPLETE")
    except BaseException as exc:
        result.update(error_type=type(exc).__name__, error_code=getattr(exc, "code", str(exc)))
    finally:
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_new(out / "recovery-summary.json", result)
    return result


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "prepare":
        parser = argparse.ArgumentParser(description="Prepare only; requires a separately verified outer release hash.")
        for name in ("writer-target-dir", "holder", "holder-sha256", "output-root", "request"):
            parser.add_argument("--" + name, required=True)
        args = parser.parse_args(argv[1:])
        result = prepare_request(args.writer_target_dir, args.holder, args.holder_sha256, args.output_root, args.request)
        print(json.dumps(result, ensure_ascii=True), flush=True)
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("request", "request-sha256", "authority", "authority-sha256"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    result = execute(args.request, args.request_sha256, args.authority, args.authority_sha256)
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return 0 if result["status"] == "READBACK_MATCHED_AFTER_OS_RELEASE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
