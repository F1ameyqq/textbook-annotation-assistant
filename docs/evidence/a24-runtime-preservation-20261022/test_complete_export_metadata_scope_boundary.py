"""Independent scope-boundary evidence for the frozen V3 candidate.

This is deliberately not an acceptance expectation.  It documents that the
conditional A24CompleteExportCodec/v1 preserves every question row but does not
bind the full metadata row into raw_business_projection/raw_business_residuals.
The actual OBSERVED owner path separately requires A24NaturalExportCodec/v1.
"""
from __future__ import annotations

import copy
import json
import unittest

from annotation.delivery.live_pilot import wire
from annotation.quality.live_pilot import check_preservation


def content(pid: str, rect_ids: list[str]) -> dict:
    return {
        "status": "AVAILABLE",
        "question_type": "ordinary_choice",
        "parts": [{"text": pid}],
        "wire_zones": {zone: None for zone in wire.ZONES},
        "question_info": {},
        "rect_ids": rect_ids,
    }


def observation() -> dict:
    value = {
        "book_id": "46007447",
        "platform_version": "observed-v1",
        "complete": True,
        "read_status": "OK",
        "submission_status": "NOT_SUBMITTED",
        "source_bindings": {},
        "directory_details": [{"directory_id": "leaf", "parent_id": None}],
        "view": {
            "target": {
                "directories": ["leaf"],
                "questions": [{"platform_question_id": "q-old", "platform_order": 1,
                               "directory_id": "leaf"}],
                "frames": [{"platform_frame_id": "r-old",
                            "platform_question_id": "q-old"}],
            },
            "internal_bindings": {},
            "frame_projections": {"r-old": {}},
            "question_content": {"q-old": content("q-old", ["r-old"])},
        },
    }
    value["raw_business_projection"] = wire.build_business_preservation(
        value, direct_view=True)
    value["raw_business_residuals"] = {
        "schema": "A24RawBusinessResponseResiduals/v1",
        "slots": {"snapshot": {"node_type": "DECLARED_SUBTREE_MASK"}},
    }
    return value


def complete_codec() -> dict:
    return {
        "schema": "A24CompleteExportCodec/v1",
        "kind_path": ["kind"],
        "metadata_value": "metadata",
        "question_value": "question",
        "metadata_fields": {key: [key] for key in
                            ("book_id", "complete", "question_ids", "zones",
                             "state_version")},
        "question_fields": {key: [key] for key in
                            ("platform_question_id", "question_type", "parts",
                             "wire_zones", "question_info", "rect_ids")},
    }


class CompleteExportMetadataScopeBoundary(unittest.TestCase):
    def test_decoder_preserves_full_question_row_but_not_full_metadata_row(self):
        metadata = {
            "kind": "metadata", "book_id": "46007447", "complete": True,
            "question_ids": ["q-old"], "zones": list(wire.ZONES),
            "state_version": "v1", "unknown_metadata": {"zero": 0},
        }
        question = {
            "kind": "question", "platform_question_id": "q-old",
            "question_type": "ordinary_choice", "parts": [{"text": "old"}],
            "wire_zones": {zone: None for zone in wire.ZONES},
            "question_info": {}, "rect_ids": ["r-old"],
            "unknown_question": {"kept": True},
        }
        text = "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                         for row in (metadata, question))
        contents, coverage = wire.decode_complete_export(
            text, complete_codec(), [{"platform_question_id": "q-old"}])

        self.assertEqual(contents["q-old"]["raw_record"]["unknown_question"],
                         {"kept": True})
        self.assertNotIn("raw_metadata_record", coverage)
        self.assertNotIn("unknown_metadata", coverage)

    def test_post_append_gate_does_not_bind_complete_export_metadata_unknowns(self):
        before = observation()
        after = copy.deepcopy(before)
        pid = "q-new"
        after["view"]["target"]["questions"].append(
            {"platform_question_id": pid, "platform_order": 2,
             "directory_id": "leaf"})
        rect_ids = []
        for index in range(6):
            rid = f"r-new-{index}"
            rect_ids.append(rid)
            after["view"]["target"]["frames"].append(
                {"platform_frame_id": rid, "platform_question_id": pid})
            after["view"]["frame_projections"][rid] = {"index": index}
        after["view"]["internal_bindings"]["local-new"] = pid
        after["view"]["question_content"][pid] = content(pid, rect_ids)
        after["raw_business_projection"] = wire.build_business_preservation(
            after, direct_view=True)

        before["raw_business_responses"] = {
            "export": {"body": '{"kind":"metadata","unknown_metadata":0}'}
        }
        after["raw_business_responses"] = {
            "export": {"body": '{"kind":"metadata","unknown_metadata":false}'}
        }

        # This pass is the observed scope boundary: raw_business_responses and
        # export_coverage are runtime-only in the post-append preservation gate.
        check_preservation(before, after, pid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
