"""Synthetic proof consistency tests; no network or filesystem acceptance claims."""
import copy
import importlib.util
import sys
import unittest

from test_usense_live_insertion import u, ins, synthetic_fixture, synthetic_readback
from annotation.runtime.usense_live import insertion_resolution as resolution


def synthetic_execution(plan, after, receipt):
    release = {"context_closed": True, "runtime_stopped": True, "context_runtime_release_confirmed": True,
               "pending_callbacks": 0, "errors": []}
    w = {"status": "UNKNOWN_DO_NOT_RETRY", "error_type": "UpdateError", "error_code": "EXACT_NEW_SERVER_NODE_REQUIRED",
        "process_id": 100, "plan_sha256": plan["plan_sha256"], "ledger_key": plan["ledger_key"], "run_id": "synthetic-writer",
        "http_status": 200, "receipt_sha256": u.digest(receipt), "post_attempts": 1, "post_layers": {"context": 1, "native": 1},
        "release": release, "send_intent_at": "2026-10-22T18:51:24.365170+00:00", "finished_at": "2026-10-22T18:51:25.413981+00:00",
        "prewrite_responses": {name: {"sha256": u.digest(raw), "bytes": 10, "request_counts": {"context": 1, "native": 1},
            "observed_at": "2026-10-22T18:51:23.000000+00:00"} for name, raw in plan["before_full"].items()},
        "native_body_sha256": "f" * 64, "runtime_actor_hashes": {"runtime_actor_sha256": u.text_digest("SYNTHETIC-username"),
            "runtime_user_id_sha256": u.text_digest("222")}}
    wp = {"pid": 100, "exit_code": 2, "started_at": "2026-10-22T18:51:12+00:00", "finished_at": "2026-10-22T18:51:25.500000+00:00", "result": w}
    readers = []
    for i in range(4):
        minute = 52 + i
        names = set(ins.GLOBAL_KEYS) | {f"q{order}_{suffix}" for order in range(1 + 6*i, min(7 + 6*i, 24)) for suffix in ins.SUFFIXES}
        r = {"run_id": f"synthetic-reader-{i}", "status": "NATIVE_GETS_CAPTURED", "save_attempts": 0, "release": copy.deepcopy(release),
            "finished_at": f"2026-10-22T18:{minute}:50+00:00", "captures": {name: {"status": 200, "filename": name + ".json",
                "sha256": u.digest(after[name]), "bytes": 10, "request_counts": {"context": 1, "native": 1},
                "observed_at": f"2026-10-22T18:{minute}:30+00:00"} for name in sorted(names)}}
        readers.append({"pid": 200+i, "exit_code": 0, "started_at": f"2026-10-22T18:{minute}:00+00:00",
            "finished_at": f"2026-10-22T18:{minute}:51+00:00", "result": r})
    ledger = {"operation": "Q7_COPY_FIRST_VARIANT_INSERT", "ledger_key": plan["ledger_key"], "run_id": w["run_id"],
        "plan_sha256": plan["plan_sha256"], "native_body_sha256": w["native_body_sha256"], "intent_at": w["send_intent_at"],
        "automatic_retry_allowed": False, "state": "INTENT_REQUIRES_INDEPENDENT_ALL23_READBACK"}
    return {"schema": resolution.SCHEMA, "plan_sha256": plan["plan_sha256"], "before_sha256": plan["before_sha256"],
        "after_sha256": ins.flat_digest(after), "native_receipt_raw_sha256": u.digest(receipt), "parsed_receipt_sha256": u.digest(receipt),
        "writer_process": wp, "reader_processes": readers, "ledger_intent": ledger}


class ObservedResolutionTests(unittest.TestCase):
    def setUp(self):
        before, payload, approved = synthetic_fixture()
        self.plan = ins.make_insert_plan(before, payload_candidate=payload, approved_new_content=approved)
        self.after, self.receipt = synthetic_readback(before, payload)
        node = self.receipt["data"]["inserted_question_node"]
        self.receipt["data"]["inserted_question_node"] = {key: node[key] for key in ins.OBSERVED_INSERTED_NODE_KEYS}
        for row in self.after["frames"]["data"]:
            if int(row["order_in_level"]) >= 8:
                row["updated_at"] = "2026-10-23T02:51:25"
                if row["order_in_level"] == "8":
                    row["created_at"] = row["updated_at"]
        for i in range(8, 24):
            self.after[f"q{i}_info"]["data"]["updated_at"] = "2026-10-23T02:51:25"
        self.after["q8_info"]["data"]["created_at"] = "2026-10-23T02:51:25"

    def resolve(self):
        e = synthetic_execution(self.plan, self.after, self.receipt)
        return resolution.resolve_observed_insert(self.plan, self.after, self.receipt, e)

    def reject(self):
        with self.assertRaises(ValueError):
            self.resolve()

    def test_exact_observed_effects_resolve_without_rewriting_unknown(self):
        original = copy.deepcopy(self.after)
        report = self.resolve()
        self.assertEqual(report["status"], resolution.RESOLVED)
        self.assertEqual(report["original_writer_exit_code"], 2)
        self.assertEqual(report["original_strict_status"], "HOLD")
        self.assertEqual(len(report["observed_effects"]["changes"]), 57)
        self.assertFalse(report["automatic_retry_allowed"])
        self.assertFalse(report["phase2_permitted"])
        self.assertTrue(u.json_same(original, self.after))

    def test_changed_old_question_text_rejected(self):
        self.after["q9_question"]["data"]["ocr_result"] += "CORRUPT"
        self.reject()

    def test_changed_old_q7_metadata_rejected(self):
        self.after["q7_info"]["data"]["updated_at"] = "2026-10-23T02:51:25"
        self.reject()

    def test_changed_old_q1_frame_metadata_rejected(self):
        self.after["q1_annotations"]["data"][0]["updated_at"] = "2026-10-23T02:51:25"
        self.reject()

    def test_shifted_frame_timestamp_outside_send_window_rejected(self):
        self.after["q23_annotations"]["data"][0]["updated_at"] = "2026-10-23T02:51:26"
        self.reject()

    def test_info_timestamp_outside_send_window_rejected(self):
        self.after["q23_info"]["data"]["updated_at"] = "2026-10-23T02:51:23"
        self.reject()

    def test_info_timestamp_old_value_not_accepted_as_observed_effect(self):
        self.after["q23_info"]["data"]["updated_at"] = self.plan["before_full"]["q22_info"]["data"]["updated_at"]
        self.reject()

    def test_wrong_info_entity_rejected(self):
        self.after["q23_info"]["data"]["id"] = "123456"
        self.reject()

    def test_wrong_frame_geometry_rejected(self):
        self.after["q23_annotations"]["data"][0]["rect_bbox"] = "0,0,1,1"
        self.reject()

    def test_wrong_new_node_value_rejected(self):
        self.after["directory"]["data"]["directory_data"][0]["children"][0]["children"][7]["id"] = "123456"
        self.reject()

    def test_unknown_new_node_key_order_rejected(self):
        nodes = self.after["directory"]["data"]["directory_data"][0]["children"][0]["children"]
        nodes[7] = dict(reversed(list(nodes[7].items())))
        self.reject()

    def test_wrong_new_creation_time_rejected(self):
        self.after["q8_info"]["data"]["created_at"] = self.after["q8_info"]["data"]["updated_at"] = "2026-10-23T03:00:00"
        self.reject()

    def test_unknown_history_cannot_be_forged_as_exit_zero(self):
        e = synthetic_execution(self.plan, self.after, self.receipt)
        e["writer_process"]["exit_code"] = 0
        with self.assertRaisesRegex(ValueError, "UNKNOWN"):
            resolution.resolve_observed_insert(self.plan, self.after, self.receipt, e)

    def test_second_post_rejected(self):
        e = synthetic_execution(self.plan, self.after, self.receipt)
        e["writer_process"]["result"]["post_attempts"] = 2
        with self.assertRaises(ValueError):
            resolution.resolve_observed_insert(self.plan, self.after, self.receipt, e)

    def test_same_pid_reader_rejected(self):
        e = synthetic_execution(self.plan, self.after, self.receipt)
        e["reader_processes"][0]["pid"] = 100
        with self.assertRaises(ValueError):
            resolution.resolve_observed_insert(self.plan, self.after, self.receipt, e)

    def test_reader_precedes_send_rejected(self):
        e = synthetic_execution(self.plan, self.after, self.receipt)
        e["reader_processes"][0]["started_at"] = "2026-10-22T18:50:00+00:00"
        with self.assertRaises(ValueError):
            resolution.resolve_observed_insert(self.plan, self.after, self.receipt, e)

    def test_retry_ledger_rejected(self):
        e = synthetic_execution(self.plan, self.after, self.receipt)
        e["ledger_intent"]["automatic_retry_allowed"] = True
        with self.assertRaises(ValueError):
            resolution.resolve_observed_insert(self.plan, self.after, self.receipt, e)

    def test_after_hash_evidence_mismatch_rejected(self):
        e = synthetic_execution(self.plan, self.after, self.receipt)
        e["after_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            resolution.resolve_observed_insert(self.plan, self.after, self.receipt, e)


if __name__ == "__main__":
    unittest.main()
