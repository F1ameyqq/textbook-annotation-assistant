"""Read-only recovery evidence after an exact receipt and failed writer cleanup.

No sender, ledger mutation, profile acquisition or predecessor promotion lives
here. All inputs are original bytes, bound by the separately approved request.
The outer holder must have finished before even configuring a new reader.
"""
from datetime import datetime, timedelta, timezone
import re
from types import SimpleNamespace

from .config import capture_endpoints
from .core import ORIGIN, TARGET, require, sha, utc
from .revision import released, same
from .update import (loads, validate_plan, from_captured_map, json_same,
                     compare_batch_readback)


def positive(value):
    return type(value) is int and value > 0


def run_id(value):
    require(type(value) is str and re.fullmatch(r"usense-readonly-[a-z0-9-]{1,64}", value),
            "RECOVERY_RUN_ID")
    return value


def exact_int(value, expected):
    return type(value) is int and value == expected


def check_events(events, names, *, writer):
    expected = {("GET", sha((ORIGIN + path).encode())) for path in names.values()}
    expected.add(("GET", sha(TARGET.encode())))
    if writer:
        expected.add(("POST", sha((ORIGIN + "/qieti/api/annotate_pic/commit_unified_submit").encode())))
    counts = {}
    require(type(events) is list, "RECOVERY_NETWORK_EVENTS")
    for event in events:
        key = (event.get("layer"), event.get("method"), event.get("url_sha256"))
        require(event.get("allowed") is True and key[0] in ("context", "native") and key[1:] in expected,
                "RECOVERY_NETWORK_SCOPE_OR_DENIAL")
        counts[key] = counts.get(key, 0) + 1
    # The GET-only capture fulfills its inert document in a page route before
    # the context route; its native navigation event is still required. Writer
    # fulfills from the context route and therefore records both layers.
    document = ("GET", sha(TARGET.encode()))
    require(all(counts.get((layer, method, url), 0) ==
                (0 if not writer and layer == "context" and (method, url) == document else 1)
                for layer in ("context", "native") for method, url in expected), "RECOVERY_NETWORK_COUNTS")


def process_result(raw, stdout, stderr, execution):
    process = loads(raw)
    require(type(process) is dict and process.get("timed_out") is False and
            positive(process.get("pid")) and same(process.get("result"), execution) and
            process.get("stdout_sha256") == sha(stdout) and process.get("stderr_sha256") == sha(stderr),
            "RECOVERY_PROCESS_RAW_BINDING")
    require(same(loads(stdout.decode("utf-8").strip().splitlines()[-1]), execution),
            "RECOVERY_STDOUT_EXECUTION_MISMATCH")
    require(utc(process["started_at"]) < utc(execution["finished_at"]) <= utc(process["finished_at"]),
            "RECOVERY_PROCESS_TIME")
    return process


def verify_writer(raw):
    """Recompute intent/receipt/guard/holder chain, never trust a success flag."""
    plan, w, cfg = (loads(raw[key]) for key in ("plan", "execution", "writer_config"))
    validate_plan(plan)
    require(plan["mutation_required"] is True, "RECOVERY_MUTATION_INTENT_REQUIRED")
    wp = process_result(raw["writer_process"], raw["writer_stdout"], raw["writer_stderr"], w)
    require(exact_int(wp.get("exit_code"), 2) and w.get("status") == "RELEASE_UNPROVEN_NO_RETRY" and
            w.get("release", {}).get("context_runtime_release_confirmed") is False and
            not any(key in w for key in ("error_type", "error_code")) and
            w.get("business_status_before_release", "RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK") ==
            "RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK", "RECOVERY_UNKNOWN_BUSINESS_NO_RETRY")
    require(w.get("plan_file_sha256") == sha(raw["plan"]) and w.get("plan_sha256") == plan["plan_sha256"] and
            same(w.get("target"), plan["target"]) and w.get("ledger_key") == plan["ledger_key"] and
            w.get("intent_key") == plan["ledger_key"], "RECOVERY_ORIGINAL_PLAN_BINDING")
    # Revision recovery is intentionally excluded; it needs its own frozen chain.
    require(cfg.get("book_id") == "46007447" and cfg.get("run_id") == run_id(w["run_id"]) and
            w.get("config_sha256") == sha(raw["writer_config"]), "RECOVERY_WRITER_CONFIG_BINDING")
    names = capture_endpoints(SimpleNamespace(data=cfg))
    q = plan["target"]["question_order"]
    require({name.split("_")[0] for name in names if name.startswith("q")} == {f"q{q}"} and
            "source" in names and any(name.startswith("page_") for name in names), "RECOVERY_SINGLE_TARGET_SOURCE")
    require(set(raw["before"]) == set(names), "RECOVERY_BEFORE_ENDPOINT_SET")
    before = {name: loads(value) for name, value in raw["before"].items()}
    require(json_same(from_captured_map(before, f"q{q}_"), plan["before"]), "RECOVERY_WRITER_BEFORE_CHANGED")
    receipt = {"code": 0, "message": "success", "data": {"inserted": False, "question_order": q,
               "inserted_question_node": None, "success": True, "append_at_global_end": False}}
    require(json_same(loads(raw["receipt"]), receipt) and sha(raw["receipt"]) == w.get("receipt_sha256") and
            exact_int(w.get("http_status"), 200) and exact_int(w.get("response_code"), 0) and
            exact_int(w.get("post_attempts"), 1) and json_same(w.get("post_layers"), {"context": 1, "native": 1}),
            "RECOVERY_RECEIPT_NOT_EXACT_SUCCESS")
    intent, send = loads(raw["intent"]), loads(raw["send_intent"])
    require(intent.get("state") == "INTENT_REQUIRES_INDEPENDENT_READBACK" and
            intent.get("automatic_retry_allowed") is False and intent.get("previous_acceptance_sha256") is None and
            intent.get("intent_key") == plan["ledger_key"] and intent.get("intent_at") == w.get("send_intent_at"),
            "RECOVERY_INTENT_MISMATCH")
    for key in ("run_id", "target", "ledger_key", "plan_sha256", "native_body_sha256", "intent_key"):
        require(json_same(intent.get(key), w.get(key)) and json_same(send.get(key), w.get(key)),
                "RECOVERY_SEND_INTENT_BINDING")
    require(send.get("status") == "SEND_INTENT_RECORDED" and exact_int(send.get("post_attempts"), 1) and
            send.get("send_intent_at") == w.get("send_intent_at") and
            utc(wp["started_at"]) < utc(w["send_intent_at"]) < utc(w["finished_at"]), "RECOVERY_SEND_TIME")
    check_events(loads(raw["writer_events"]), names, writer=True)
    holder = loads(raw["holder"])
    require(holder.get("schema") == "A25OwnedWindowsProcess/v1" and holder.get("errors") == [] and
            all(holder.get(key) is True for key in ("resumed", "job_assigned_before_resume", "launcher_exit_signaled",
                "thread_handle_closed", "process_handle_closed", "job_handle_closed", "owned_os_release_confirmed")) and
            exact_int(holder.get("job_active_processes_after"), 0), "RECOVERY_OUTER_RELEASE_UNPROVEN")
    require(utc(holder["started_at"]) <= utc(wp["started_at"]) < utc(wp["finished_at"]) <=
            utc(holder["process_finished_at"]) <= utc(holder["finished_at"]), "RECOVERY_OUTER_TIME")
    rows, seen, writers = holder.get("observed_processes"), set(), []
    require(type(rows) is list and bool(rows), "RECOVERY_HELD_IDENTITIES_REQUIRED")
    for item in rows:
        identity = (item.get("pid"), item.get("creation_filetime"))
        require(all(positive(value) for value in identity) and identity not in seen and
                item.get("exit_signaled") is True and item.get("handle_closed") is True and
                type(item.get("exit_code")) is int and item["exit_code"] != 259,
                "RECOVERY_HELD_IDENTITY_NOT_RELEASED")
        seen.add(identity)
        if identity[0] == wp["pid"]:
            writers.append(item)
    require(len(writers) == 1, "RECOVERY_WRITER_NOT_HELD")
    held = writers[0]
    created = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=held["creation_filetime"] // 10)
    require(utc(wp["started_at"]) <= created <= utc(held["observed_at"]) <= utc(wp["finished_at"]) and
            held["exit_code"] == wp["exit_code"], "RECOVERY_WRITER_OS_IDENTITY_TIME")
    return {"plan": plan, "writer": w, "process": wp, "config": cfg, "names": names,
            "before": before, "holder": holder, "holder_raw": raw["holder"]}


def verify_reader(old, raw):
    r, cfg = loads(raw["summary"]), loads(raw["config"])
    rp = process_result(raw["process"], raw["stdout"], raw["stderr"], r)
    w, wp, holder = old["writer"], old["process"], old["holder"]
    require(exact_int(rp.get("exit_code"), 0) and r.get("status") == "NATIVE_GETS_CAPTURED" and
            exact_int(r.get("save_attempts"), 0) and released(r.get("release", {})), "RECOVERY_READER_FAILED_OR_UNRELEASED")
    require(cfg.get("run_id") == run_id(r["run_id"]) and sha(raw["config"]) == r.get("config_sha256") and
            cfg.get("book_id") == "46007447" and
            same(cfg.get("profile"), old["config"]["profile"]) and
            same(cfg.get("transport"), old["config"]["transport"]) and
            capture_endpoints(SimpleNamespace(data=cfg)) == old["names"], "RECOVERY_READER_CONFIG_SCOPE")
    require(same({k: v for k, v in cfg["tls"].items() if k != "approval_reference"},
                 {k: v for k, v in old["config"]["tls"].items() if k != "approval_reference"}),
            "RECOVERY_READER_TLS_CHANGED")
    require(rp["pid"] not in {row["pid"] for row in holder["observed_processes"]} and r["run_id"] != w["run_id"] and
            utc(rp["started_at"]) > utc(holder["finished_at"]), "RECOVERY_READER_NOT_NEW_AFTER_RELEASE")
    require(set(r["captures"]) == set(old["names"]) == set(raw["captures"]), "RECOVERY_READER_ENDPOINT_SET")
    after = {}
    for name, value in raw["captures"].items():
        cap = r["captures"][name]
        require(cap.get("filename") == name + ".json" and cap.get("sha256") == sha(value) and
                exact_int(cap.get("bytes"), len(value)) and exact_int(cap.get("status"), 200) and
                json_same(cap.get("request_counts"), {"context": 1, "native": 1}) and
                utc(rp["started_at"]) < utc(cap["observed_at"]) < utc(r["finished_at"]), "RECOVERY_CAPTURE_RAW_OR_TIME")
        after[name] = loads(value)
        require(exact_int(after[name].get("code"), 0), "RECOVERY_CAPTURE_BUSINESS_FAILURE")
    check_events(loads(raw["events"]), old["names"], writer=False)
    plan = old["plan"]
    comparison = compare_batch_readback(plan, from_captured_map(after, f"q{plan['target']['question_order']}_"))
    require(comparison["match"] and all(json_same(old["before"][name], after[name]) for name in after
            if name == "source" or name.startswith("page_")), "RECOVERY_FULL_READBACK_MISMATCH")
    return {"schema": "UsensePostsaveReadonlyRecovery/v1", "status": "READBACK_MATCHED_AFTER_OS_RELEASE",
            "target": plan["target"], "plan_sha256": plan["plan_sha256"], "receipt_sha256": w["receipt_sha256"],
            "original_writer_status": w["status"], "original_framework_release": w["release"],
            "writer_run": w["run_id"], "reader_run": r["run_id"], "comparison": comparison,
            "os_release_record_sha256": sha(old["holder_raw"]),
            "posts_performed_by_recovery": 0, "new_standard_accepted_marker": False,
            "revision_predecessor_eligible": False, "old_failure_overwritten": False}
