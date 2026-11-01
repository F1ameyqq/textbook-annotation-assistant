"""Offline resolution of the first observed Q7 insert, never write authority.

Keep the original writer UNKNOWN/exit2, strict HOLD, native responses and plan.
This separate proof admits only two explicitly observed backend effects:
the new receipt node's exact two serialization layouts, and 57 reindex timestamps
within this one actual send window. No general timestamp whitelist or retry.
Callers must additionally verify the on-disk raw evidence hashes/ledger bytes.
"""
import copy
from datetime import datetime, timedelta, timezone
import re

from . import update as u
from . import insertion as ins


SCHEMA = "UsenseObservedInsertExecutionEvidence/v1"
RESOLVED = "RESOLVED_UNKNOWN_COPY_FIRST_WITH_INDEPENDENT_FULL_READBACK"


def _utc(value):
    u.require(type(value) is str, "EXECUTION_TIMESTAMP_REQUIRED")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as error:
        raise u.UpdateError("EXECUTION_TIMESTAMP_FORMAT") from error
    u.require(result.tzinfo is not None and result.utcoffset() == timedelta(0), "ACTUAL_UTC_TIMESTAMP_REQUIRED")
    return result


def _release(record):
    return (type(record) is dict and record.get("context_closed") is True and
            record.get("runtime_stopped") is True and record.get("context_runtime_release_confirmed") is True and
            type(record.get("pending_callbacks")) is int and record["pending_callbacks"] == 0 and record.get("errors") == [])


def _seconds(value):
    u.require(type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value), "OBSERVED_NATIVE_SECONDS_FORMAT_REQUIRED")
    return datetime.fromisoformat(value)


def _execution(plan, after, receipt, evidence):
    fields = {"schema", "plan_sha256", "before_sha256", "after_sha256", "native_receipt_raw_sha256",
              "parsed_receipt_sha256", "writer_process", "reader_processes", "ledger_intent"}
    u.require(type(evidence) is dict and set(evidence) == fields and evidence["schema"] == SCHEMA, "OBSERVED_EXECUTION_EVIDENCE_SCHEMA")
    u.require(evidence["plan_sha256"] == plan["plan_sha256"] and evidence["before_sha256"] == plan["before_sha256"] and
              evidence["after_sha256"] == ins.flat_digest(after) and evidence["parsed_receipt_sha256"] == u.digest(receipt),
              "OBSERVED_EXECUTION_STATE_BINDING")
    wp, readers = evidence["writer_process"], evidence["reader_processes"]
    u.require(type(wp) is dict and type(readers) is list and len(readers) == 4, "FOUR_ACTUAL_READER_PROCESSES_REQUIRED")
    w = wp["result"]
    u.require(type(wp.get("exit_code")) is int and wp["exit_code"] == 2 and w["status"] == "UNKNOWN_DO_NOT_RETRY" and
              w.get("error_type") == "UpdateError" and w.get("error_code") == "EXACT_NEW_SERVER_NODE_REQUIRED", "ORIGINAL_UNKNOWN_HISTORY_REQUIRED")
    u.require(type(wp.get("pid")) is int and wp["pid"] > 0 and wp["pid"] == w["process_id"], "ACTUAL_WRITER_PID_REQUIRED")
    u.require(w["plan_sha256"] == plan["plan_sha256"] and w["ledger_key"] == plan["ledger_key"] and
              w.get("http_status") == 200 and w["receipt_sha256"] == evidence["native_receipt_raw_sha256"] and
              ins._hash(evidence["native_receipt_raw_sha256"]), "ACTUAL_RECEIPT_PLAN_BINDING")
    u.require(type(w.get("post_attempts")) is int and w["post_attempts"] == 1 and
              u.json_same(w.get("post_layers"), {"context": 1, "native": 1}) and _release(w["release"]), "ACTUAL_SINGLE_SEND_AND_RELEASE_REQUIRED")
    start, send, finish, process_finish = map(_utc, (wp["started_at"], w["send_intent_at"], w["finished_at"], wp["finished_at"]))
    u.require(start < send < finish <= process_finish, "ACTUAL_WRITER_TIME_ORDER")
    before_caps = w["prewrite_responses"]
    u.require(set(before_caps) == set(plan["before_full"]), "ALL161_ACTUAL_PREWRITE_READS_REQUIRED")
    for cap in before_caps.values():
        u.require(ins._hash(cap.get("sha256")) and type(cap.get("bytes")) is int and cap["bytes"] > 0 and
                  u.json_same(cap.get("request_counts"), {"context": 1, "native": 1}) and
                  start < _utc(cap["observed_at"]) < send, "ACTUAL_PREWRITE_CAPTURE_EVIDENCE")
    intent = evidence["ledger_intent"]
    u.require(intent["operation"] == "Q7_COPY_FIRST_VARIANT_INSERT" and intent["ledger_key"] == plan["ledger_key"] and
              intent["run_id"] == w["run_id"] and intent["plan_sha256"] == plan["plan_sha256"] and
              intent["native_body_sha256"] == w["native_body_sha256"] and intent["intent_at"] == w["send_intent_at"] and
              intent["automatic_retry_allowed"] is False and intent["state"] == "INTENT_REQUIRES_INDEPENDENT_ALL23_READBACK",
              "ORIGINAL_DURABLE_ONCE_INTENT_REQUIRED")
    seen_pids, seen_runs, captured, occurrences, last_end = {wp["pid"]}, {w["run_id"]}, {}, 0, process_finish
    for chunk, process in enumerate(readers):
        r = process["result"]
        orders = range(1 + chunk * 6, min(7 + chunk * 6, 24))
        expected_names = set(ins.GLOBAL_KEYS) | {f"q{i}_{suffix}" for i in orders for suffix in ins.SUFFIXES}
        u.require(set(r["captures"]) == expected_names, "EXACT_FOUR_OBSERVED_READER_SCOPES_REQUIRED")
        u.require(type(process.get("pid")) is int and process["pid"] > 0 and process["pid"] not in seen_pids and
                  r["run_id"] not in seen_runs, "FOUR_DISTINCT_FRESH_READER_PROCESSES_REQUIRED")
        seen_pids.add(process["pid"])
        seen_runs.add(r["run_id"])
        u.require(type(process.get("exit_code")) is int and process["exit_code"] == 0 and r["status"] == "NATIVE_GETS_CAPTURED" and
                  type(r["save_attempts"]) is int and r["save_attempts"] == 0 and _release(r["release"]), "SUCCESSFUL_READONLY_READER_RELEASE_REQUIRED")
        rs, rf, pf = map(_utc, (process["started_at"], r["finished_at"], process["finished_at"]))
        u.require(last_end < rs < rf <= pf, "FRESH_READERS_MUST_FOLLOW_WRITER_AND_EACH_OTHER")
        last_end = pf
        for name, cap in r["captures"].items():
            u.require(name in after and type(cap["status"]) is int and cap["status"] == 200 and
                      cap["filename"] == name + ".json" and ins._hash(cap["sha256"]) and
                      type(cap["bytes"]) is int and cap["bytes"] > 0 and
                      u.json_same(cap["request_counts"], {"context": 1, "native": 1}) and
                      process_finish < rs < _utc(cap["observed_at"]) < rf, "ACTUAL_AFTER_CAPTURE_EVIDENCE")
            if name in captured:
                u.require(captured[name] == cap["sha256"], "COMMON_AFTER_RESPONSE_CHANGED")
            captured[name] = cap["sha256"]
            occurrences += 1
    u.require(set(captured) == set(after) and len(captured) == 168 and occurrences == 189, "ALL168_NATIVE_RESPONSES_AND_REPEATED_GLOBALS_REQUIRED")
    return w, send, finish


def resolve_observed_insert(plan, after, receipt, actual_execution_evidence):
    """Return a new resolution proof or raise; never rewrites historical status.

    The evidence values must come from hash-verified raw files. This pure function
    proves their consistency; the independent outer auditor proves file provenance.
    """
    ins.validate_insert_plan(plan)
    ins.load_full_capture(after, count=23)
    decoded = ins.decode_receipt(plan, receipt)
    w, send, finish = _execution(plan, after, receipt, actual_execution_evidence)
    u.require(tuple(decoded["inserted_question_node"]) == ins.OBSERVED_INSERTED_NODE_KEYS,
              "RESOLUTION_ONLY_FOR_EXACT_OBSERVED_NEW_NODE_LAYOUT")
    original_strict = ins.compare_insert_readback(plan, after, receipt, runtime_actor_hashes=w["runtime_actor_hashes"])
    u.require(original_strict["ok"] is False and original_strict["status"] == "HOLD", "ORIGINAL_STRICT_HOLD_MUST_REMAIN")
    projection = copy.deepcopy(after)
    new_actual_node = ins._questions(projection["directory"])[7][0]
    receipt_node = decoded["inserted_question_node"]
    u.require(tuple(new_actual_node) == ins.NODE_KEYS and all(u.json_same(new_actual_node[key], receipt_node[key]) for key in ins.NODE_KEYS),
              "EXACT_OBSERVED_RECEIPT_TO_DIRECTORY_NODE_PROJECTION")
    before_node_layout = list(new_actual_node)
    new_actual_node.clear()
    new_actual_node.update(copy.deepcopy(receipt_node))
    # Native server timestamps observed in this run are local UTC+8 seconds.
    low = send.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None, microsecond=0)
    high = finish.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None, microsecond=0)
    new_metadata_rows = after["q8_annotations"]["data"] + [after["q8_info"]["data"]]
    u.require(all(low <= _seconds(row["created_at"]) <= high and row["created_at"] == row["updated_at"]
                  for row in new_metadata_rows), "NEW_CREATION_METADATA_OUTSIDE_ACTUAL_SEND_WINDOW")
    records = []

    def timestamp(old, new, kind, identity, old_order, paths):
        old_dt, new_dt = _seconds(old), _seconds(new)
        u.require(new_dt > old_dt and low <= new_dt <= high, "REINDEX_TIMESTAMP_NOT_MONOTONIC_OR_OUTSIDE_ACTUAL_SEND_WINDOW", identity)
        records.append({"entity": kind, "stable_id": identity, "old_order": old_order, "new_order": old_order + 1,
                        "field": "updated_at", "before": old, "after": new, "native_paths": paths})

    old_rows = plan["before_full"]["frames"]["data"]
    actual_rows = {row["rect_id"]: row for row in after["frames"]["data"]}
    projection_rows = {row["rect_id"]: row for row in projection["frames"]["data"]}
    shifted = [row for row in old_rows if u._order(row["order_in_level"]) > 7]
    u.require(len(shifted) == 42, "EXACT_OBSERVED_42_REINDEXED_OLD_FRAMES_REQUIRED")
    for old in shifted:
        rect, order = old["rect_id"], u._order(old["order_in_level"])
        current = actual_rows[rect]
        timestamp(old["updated_at"], current["updated_at"], "frame", rect, order,
                  [f"frames.data[rect_id={rect}].updated_at", f"q{order+1}_annotations.data[rect_id={rect}].updated_at"])
        selected = [row for row in projection[f"q{order+1}_annotations"]["data"] if row["rect_id"] == rect]
        u.require(len(selected) == 1 and selected[0]["updated_at"] == current["updated_at"], "TARGET_AND_GLOBAL_TIMESTAMP_DISAGREE")
        projection_rows[rect]["updated_at"] = old["updated_at"]
        selected[0]["updated_at"] = old["updated_at"]
    for old_order in range(8, 23):
        old_info = plan["before_full"][f"q{old_order}_info"]["data"]
        info = after[f"q{old_order+1}_info"]["data"]
        u.require(info["id"] == old_info["id"], "REINDEX_INFO_IDENTITY_REPLACED")
        timestamp(old_info["updated_at"], info["updated_at"], "info", info["id"], old_order,
                  [f"q{old_order+1}_info.data.updated_at"])
        projection[f"q{old_order+1}_info"]["data"]["updated_at"] = old_info["updated_at"]
    proof = ins.compare_insert_readback(plan, projection, receipt, runtime_actor_hashes=w["runtime_actor_hashes"])
    u.require(proof["ok"] is True, "UNAPPROVED_DELTA_REMAINS_AFTER_EXACT_OBSERVED_EFFECTS", str(proof.get("differences")))
    u.require(proof["old_q7_preserved"] is True, "OLD_Q7_NOT_INTACT")
    return {"schema": "UsenseObservedCopyFirstResolution/v1", "ok": True, "status": RESOLVED,
            "plan_sha256": plan["plan_sha256"], "before_sha256": plan["before_sha256"], "after_sha256": ins.flat_digest(after),
            "native_receipt_raw_sha256": actual_execution_evidence["native_receipt_raw_sha256"],
            "parsed_receipt_sha256": u.digest(receipt), "execution_evidence_sha256": u.digest(actual_execution_evidence),
            "original_writer_status": w["status"], "original_writer_exit_code": actual_execution_evidence["writer_process"]["exit_code"],
            "original_writer_error_code": w["error_code"], "original_strict_status": original_strict["status"],
            "original_strict_comparison_sha256": u.digest(original_strict), "new_identity": proof["new_identity"],
            "observed_effects": {"new_node_only_serialization": {"receipt_key_order": list(receipt_node),
                "directory_key_order": before_node_layout, "id_and_all_values_identical": True},
                "timestamp_timezone": "UTC+08:00", "actual_send_utc": w["send_intent_at"], "actual_finished_utc": w["finished_at"],
                "native_seconds_window": [low.isoformat(), high.isoformat()], "frame_count": 42, "info_count": 15,
                "changes": records}, "all_other_native_values_and_order_exact": True, "old_q7_preserved": True,
            "explicit_effect_projection_comparison": proof, "projection_is_not_actual_after": True,
            "automatic_retry_allowed": False, "phase2_permitted": False,
            "raw_file_provenance_verified_here": False,
            "required_outer_proof": "Hash each original writer, reader, intent, native and approval file; retain original UNKNOWN and strict HOLD. Root controls phase2."}
