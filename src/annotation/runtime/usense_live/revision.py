"""Explicit revision admission from a fully evidenced accepted predecessor.

No network, writes, ledger resets or UNKNOWN recovery. This only verifies stored
evidence and derives a new once-only intent key. Current before must equal the
previous independent readback in full, including its metadata timestamp.
"""
from datetime import datetime
from pathlib import Path
import re
from types import SimpleNamespace

from .core import ORIGIN, canonical, plain_path, require, sha
from .config import capture_endpoints
from .update import (loads, validate_recorded_plan, compare_recorded_readback,
                     from_captured_map, json_same)


def same(a, b): return canonical(a) == canonical(b)
def time(value): return datetime.fromisoformat(value)


def revision_key(stable_key, previous_plan_sha256):
    require(re.fullmatch(r"usense-existing-[0-9a-f]{64}", stable_key) is not None and
            re.fullmatch(r"[0-9a-f]{64}", previous_plan_sha256) is not None, "REVISION_IDENTITY_FORMAT")
    return stable_key + "-revision-" + sha((stable_key + ":" + previous_plan_sha256).encode())


def released(value):
    return (value.get("context_closed") is True and value.get("runtime_stopped") is True and
            type(value.get("pending_callbacks")) is int and value["pending_callbacks"] == 0 and
            value.get("errors") == [] and value.get("context_runtime_release_confirmed") is True)


def verify_previous_acceptance(acceptance_path, current_plan, current_native, ledger_root):
    """Return immutable evidence bindings; all failures stop before browser send.

    Only currently accepted predecessor evidence is eligible. Merely finding a
    receipt, a readback, or a caller-supplied status string is insufficient.
    """
    ledger = plain_path(str(ledger_root))
    acceptance_path = plain_path(str(acceptance_path))
    require(acceptance_path.name == "acceptance.json", "PREVIOUS_ACCEPTANCE_FILE_REQUIRED")
    evidence = {}

    def raw(path):
        path = plain_path(str(path))
        value = path.read_bytes()
        evidence[str(path)] = sha(value)
        return value

    def read(path): return loads(raw(path))

    acceptance_raw = raw(acceptance_path)
    acceptance = loads(acceptance_raw)
    qdir, batch = acceptance_path.parent, acceptance_path.parent.parent
    prior_raw = raw(qdir / "plan.json")
    prior = loads(prior_raw)
    validate_recorded_plan(prior)
    require(acceptance.get("status") == "ACCEPTED" and isinstance(acceptance.get("checks"), dict) and
            bool(acceptance["checks"]) and all(v is True for v in acceptance["checks"].values()), "PREVIOUS_ACCEPTANCE_NOT_SUCCESS")
    require(prior["mutation_required"] is True and same(prior["target"], current_plan["target"]) and
            prior["ledger_key"] == current_plan["ledger_key"] and same(acceptance.get("target"), prior["target"]),
            "PREVIOUS_ACCEPTANCE_TARGET_MISMATCH")
    require(acceptance.get("plan_file_sha256") == sha(prior_raw), "PREVIOUS_PLAN_FILE_HASH_MISMATCH")
    wp, rp = read(qdir / "writer-process-result.json"), read(qdir / "reader-process-result.json")
    w, r = wp["result"], rp["result"]
    require(type(wp.get("exit_code")) is int and wp["exit_code"] == 0 and type(rp.get("exit_code")) is int and rp["exit_code"] == 0,
            "PREVIOUS_PROCESS_NOT_EXIT_ZERO")
    require(w.get("status") == "RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK" and
            r.get("status") == "NATIVE_GETS_CAPTURED", "PREVIOUS_RUN_UNKNOWN_OR_FAILED")
    require(released(w["release"]) and released(r["release"]), "PREVIOUS_RELEASE_UNPROVEN")
    require(type(wp.get("pid")) is int and type(rp.get("pid")) is int and wp["pid"] > 0 and rp["pid"] > 0 and
            wp["pid"] != rp["pid"] and time(rp["started_at"]) > time(wp["finished_at"]), "PREVIOUS_READER_NOT_INDEPENDENT")
    require(time(wp["started_at"]) < time(w["send_intent_at"]) < time(w["finished_at"]) <= time(wp["finished_at"]) and
            time(rp["started_at"]) < time(r["finished_at"]) <= time(rp["finished_at"]), "PREVIOUS_PROCESS_TIME_ORDER")
    require(w["run_id"] != r["run_id"] and acceptance.get("writer_run") == w["run_id"] and
            acceptance.get("reader_run") == r["run_id"], "PREVIOUS_RUN_BINDING_MISMATCH")
    require(w.get("plan_sha256") == prior["plan_sha256"] and w.get("plan_file_sha256") == sha(prior_raw) and
            same(w.get("target"), prior["target"]) and w.get("ledger_key") == prior["ledger_key"], "PREVIOUS_WRITER_PLAN_BINDING")
    configs = []
    for label, result in (("writer", w), ("independent-reader", r)):
        config_raw = raw(qdir / (label + "-config.json"))
        config = loads(config_raw)
        require(sha(config_raw) == result["config_sha256"] and config.get("book_id") == "46007447" and
                Path(config["output_root"]).resolve() == batch.resolve() and
                Path(config["profile"]["directory"]).resolve().parent / "usense-existing-ledger" == ledger,
                "PREVIOUS_CONFIG_OR_LEDGER_BINDING")
        require(config["run_id"] == result["run_id"] and re.fullmatch(r"usense-readonly-[a-z0-9-]{1,64}", result["run_id"]) is not None,
                "PREVIOUS_RUN_PATH_SCOPE")
        configs.append(config)
    require(configs[0]["profile"] == configs[1]["profile"], "PREVIOUS_PROFILE_BINDING")
    wd, rd = batch / w["run_id"], batch / r["run_id"]
    require(same(read(wd / "execution-result.json"), w) and same(read(rd / "capture-summary.json"), r), "PREVIOUS_PROCESS_RESULT_MISMATCH")
    require(raw(wd / "plan.json") == prior_raw, "PREVIOUS_WRITER_PLAN_COPY_CHANGED")
    q = prior["target"]["question_order"]
    expected_receipt = {"code": 0, "message": "success", "data": {"inserted": False, "question_order": q,
                        "inserted_question_node": None, "success": True, "append_at_global_end": False}}
    receipt = raw(wd / "native-receipt.json")
    require(json_same(loads(receipt), expected_receipt) and sha(receipt) == w["receipt_sha256"] and
            type(w.get("http_status")) is int and w["http_status"] == 200 and type(w.get("post_attempts")) is int and w["post_attempts"] == 1 and
            same(w.get("post_layers"), {"context": 1, "native": 1}),
            "PREVIOUS_RECEIPT_NOT_EXACT_SUCCESS")
    require(type(r.get("save_attempts")) is int and r["save_attempts"] == 0, "PREVIOUS_READER_WROTE")
    prior_key = w.get("intent_key", prior["ledger_key"])
    if prior_key != prior["ledger_key"]:
        require(isinstance(w.get("revision"), dict) and
                prior_key == revision_key(prior["ledger_key"], w["revision"]["previous_plan_sha256"]), "PREVIOUS_REVISION_INTENT_KEY")
        require(sha(raw(wd / "revision-validation.json")) == w.get("revision_validation_sha256"), "PREVIOUS_REVISION_EVIDENCE_CHANGED")
    stable = current_plan["ledger_key"]
    intent = read(ledger / (prior_key + ".json"))
    accepted = read(ledger / (prior_key + ".accepted.json"))
    require(intent.get("ledger_key") == stable and intent.get("plan_sha256") == prior["plan_sha256"] and
            intent.get("run_id") == w["run_id"] and intent.get("automatic_retry_allowed") is False and
            intent.get("native_body_sha256") == w["native_body_sha256"] and intent.get("intent_at") == w["send_intent_at"],
            "PREVIOUS_INTENT_MISMATCH")
    require(accepted.get("plan_sha256") == prior["plan_sha256"] and accepted.get("writer_run") == w["run_id"] and
            accepted.get("reader_run") == r["run_id"] and accepted.get("acceptance_sha256") == sha(acceptance_raw),
            "PREVIOUS_ACCEPTED_LEDGER_HASH_MISMATCH")
    send = read(wd / "send-intent.json")
    require(send.get("native_body_sha256") == w["native_body_sha256"] and send.get("plan_sha256") == prior["plan_sha256"] and
            send.get("send_intent_at") == w["send_intent_at"], "PREVIOUS_SEND_INTENT_MISMATCH")
    desired_key = revision_key(stable, prior["plan_sha256"])
    require(not (ledger / (desired_key + ".json")).exists(), "EXISTING_REVISION_INTENT_READBACK_REQUIRED_NO_RETRY")
    # Never bypass an UNKNOWN branch by naming a different accepted ancestor.
    for path in ledger.glob(stable + "*.json"):
        if path.name.endswith(".accepted.json"):
            continue
        require(path.stem == stable or re.fullmatch(re.escape(stable) + r"-revision-[0-9a-f]{64}", path.stem), "UNRECOGNIZED_STABLE_IDENTITY_INTENT")
        item = read(path)
        accepted_path = ledger / (path.stem + ".accepted.json")
        require(accepted_path.is_file(), "UNRESOLVED_IDENTITY_INTENT_NO_REVISION")
        marker = read(accepted_path)
        require(item.get("ledger_key") == stable and marker.get("plan_sha256") == item.get("plan_sha256") and
                marker.get("writer_run") == item.get("run_id") and isinstance(marker.get("acceptance_sha256"), str),
                "UNRESOLVED_IDENTITY_INTENT_NO_REVISION")
    names = capture_endpoints(SimpleNamespace(data=configs[1]))
    require(set(r["captures"]) == set(names) and set(current_native) == set(names), "PREVIOUS_CAPTURE_ENDPOINT_SET_MISMATCH")
    before, after = {}, {}
    for name in names:
        cap = r["captures"][name]
        value = raw(rd / (name + ".json"))
        require(cap.get("filename") == name + ".json" and cap.get("sha256") == sha(value) and cap.get("bytes") == len(value) and
                cap.get("status") == 200 and cap.get("request_counts") == {"context": 1, "native": 1}, "PREVIOUS_CAPTURE_RAW_MISMATCH")
        require(time(wp["finished_at"]) < time(cap["observed_at"]) < time(r["finished_at"]), "PREVIOUS_CAPTURE_TIME_ORDER")
        after[name] = loads(value)
        before[name] = loads(raw(wd / ("before-" + name + ".json")))
        require(type(after[name].get("code")) is int and after[name]["code"] == 0, "PREVIOUS_CAPTURE_BUSINESS_FAILURE")
    require(json_same(from_captured_map(before, f"q{q}_"), prior["before"]), "PREVIOUS_WRITER_BEFORE_MISMATCH")
    comparison = compare_recorded_readback(prior, from_captured_map(after, f"q{q}_"))
    require(comparison["match"] and same(comparison, acceptance.get("comparison")), "PREVIOUS_READBACK_NOT_MATCHED")
    require(all(json_same(before[name], after[name]) for name in names if name == "source" or name.startswith("page_")), "PREVIOUS_SOURCE_CHANGED")
    require(all(json_same(current_native[name], after[name]) for name in names) and
            json_same(current_plan["before"], from_captured_map(after, f"q{q}_")), "CURRENT_BEFORE_NOT_PREVIOUS_READBACK")
    for path, digest in read(qdir / "review-evidence-hashes.json").items():
        require(sha(raw(Path(path))) == digest, "PREVIOUS_REVIEW_EVIDENCE_CHANGED")
    for review in prior["approved_changes"].values():
        require(sha(raw(Path(review["source_ref"]))) == review["source_sha256"], "PREVIOUS_SOURCE_BYTES_CHANGED")
    wevents, revents = read(wd / "network-events.json"), read(rd / "network-events.json")
    post_hash = sha((ORIGIN + "/qieti/api/annotate_pic/commit_unified_submit").encode())
    require(all(event.get("allowed") is True for event in wevents) and
            sum(event.get("method") == "POST" for event in wevents) == 2 and
            all(sum(event.get("method") == "POST" and event.get("layer") == layer and event.get("url_sha256") == post_hash
                    for event in wevents) == 1 for layer in ("context", "native")), "PREVIOUS_POST_GUARD_UNPROVEN")
    require(all(event.get("method") == "GET" and event.get("allowed") is True for event in revents), "PREVIOUS_READER_NETWORK_NOT_READONLY")
    require(all(sum(event.get("method") == "GET" and event.get("layer") == layer and
                    event.get("url_sha256") == sha((ORIGIN + path).encode()) for event in events) == 1
                for events in (wevents, revents) for path in names.values() for layer in ("context", "native")),
            "PREVIOUS_GET_GUARD_UNPROVEN")
    return {"schema": "UsenseVerifiedAcceptedPredecessor/v1", "previous_acceptance": str(acceptance_path),
            "previous_acceptance_sha256": sha(acceptance_raw), "previous_plan_sha256": prior["plan_sha256"],
            "previous_intent_key": prior_key, "previous_writer_run": w["run_id"], "previous_reader_run": r["run_id"],
            "previous_writer_pid": wp["pid"], "previous_reader_pid": rp["pid"], "intent_key": desired_key,
            "evidence_file_sha256": evidence, "current_before_exactly_previous_readback": True,
            "unknown_recovery_performed": False, "old_ledger_modified": False}
