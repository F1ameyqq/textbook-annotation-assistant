"""Independent entry-point tests for the fixed A24 schema-readiness patch."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE = WORKSPACE / "work" / "a24-schema-readiness-v2-independent-20261022" / "source-lf"
sys.path.insert(0, str(SOURCE / "src"))
sys.path.insert(0, str(SOURCE / "tests" / "a24_first_save_wire_r1"))

from fixture import FakeIO, bind_profile, fixture  # noqa: E402
from annotation.delivery.live_pilot import wire  # noqa: E402
from annotation.delivery.live_pilot.usense import UsenseTransport  # noqa: E402
from annotation.quality.live_pilot import PilotError, check_input, global_order  # noqa: E402


class IndependentSchemaReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a24-schema-independent-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def bind_case(self, mutate=None):
        case = self.root / f"case-{len(list(self.root.glob('case-*')))}"
        case.mkdir()
        request, initial, fact, profile = fixture(case)
        reads = {}
        for phase in profile["reads"]:
            projection = {name: {"from": {"response": "snapshot", "path": ["snapshot", name]}}
                          for name in wire.SNAPSHOT_FIELDS}
            if mutate is not None:
                mutate(projection)
            reads[phase] = {"requests": [
                {"name": "book", "path": "/qieti/api/synthetic/book", "params": {}, "count": 1},
                {"name": "snapshot", "path": "/qieti/api/synthetic/complete-snapshot",
                 "params": {"file_id": "46007447"}, "count": 1},
            ], "projection": projection}
        profile["reads"] = reads
        bind_profile(request, profile, case)
        transport = UsenseTransport(FakeIO(initial, fact))
        return request, case, transport

    def assert_entry_rejects(self, mutate):
        request, case, transport = self.bind_case(mutate)
        with self.assertRaises(PilotError) as caught:
            check_input(request, case, offline=True, wire=transport)
        self.assertEqual(caught.exception.code, "IDENTITY_FROM_RESPONSE_REQUIRED")
        self.assertEqual(transport._session.calls, [])

    def test_actual_entry_rejects_view_literal_and_lookup(self):
        self.assert_entry_rejects(lambda p: p.__setitem__("view", {"literal": {"target": {}}}))
        lookup = {"lookup": {"key": {"from": {"response": "snapshot", "path": ["raw_view"]}},
                             "table": {"raw": {"target": {}}}}}
        self.assert_entry_rejects(lambda p: p.__setitem__("view", lookup))

    def test_actual_entry_rejects_questions_container_literal(self):
        value = {"object": {"target": {"object": {"questions": {"literal": []}}}}}
        self.assert_entry_rejects(lambda p: p.__setitem__("view", value))

    def test_actual_entry_rejects_directories_array_item_alias(self):
        directories = {"array": {
            "source": {"from": {"response": "snapshot", "path": ["directories"]}},
            "item": {"lookup": {"key": {"from": {"response": "$", "path": []}},
                                "table": {"raw": "canonical"}}},
        }}
        value = {"object": {"target": {"object": {"directories": directories}}}}
        self.assert_entry_rejects(lambda p: p.__setitem__("view", value))

    def test_actual_entry_allows_nonidentity_lookup(self):
        lookup = {"lookup": {"key": {"from": {"response": "snapshot", "path": ["raw_version"]}},
                             "table": {"raw": "canonical-version"}}}
        request, case, transport = self.bind_case(lambda p: p.__setitem__("platform_version", lookup))
        admission = check_input(request, case, offline=True, wire=transport)
        self.assertEqual(admission.wire.profile["reads"]["baseline"]["projection"]["platform_version"], lookup)
        self.assertEqual(transport._session.calls, [])

    def test_actual_entry_allows_direct_identity_containers(self):
        request, case, transport = self.bind_case()
        admission = check_input(request, case, offline=True, wire=transport)
        self.assertEqual(admission.wire.profile["reads"]["baseline"]["projection"]["view"],
                         {"from": {"response": "snapshot", "path": ["snapshot", "view"]}})
        self.assertEqual(transport._session.calls, [])

    @staticmethod
    def observation():
        return {"book_id": "46007447", "platform_version": "observed", "complete": True,
                "read_status": "OK", "submission_status": "NOT_SUBMITTED", "source_bindings": {},
                "directory_details": [{"directory_id": "leaf", "parent_id": None}],
                "view": {"target": {"directories": ["leaf"],
                    "questions": [{"platform_question_id": "q-old", "platform_order": 1,
                                   "directory_id": "leaf"}],
                    "frames": [{"platform_frame_id": "r-old", "platform_question_id": "q-old"}]},
                    "internal_bindings": {}, "frame_projections": {"r-old": {}},
                    "question_content": {"q-old": {"status": "AVAILABLE", "question_type": "ordinary_choice",
                        "parts": [{}], "wire_zones": {zone: None for zone in wire.ZONES},
                        "question_info": {}, "rect_ids": ["r-old"]}}}}

    def test_empty_denominator_rejects_without_inventing_per_question_frame_rule(self):
        empty = self.observation()
        empty["view"]["target"].update(questions=[], frames=[])
        empty["view"]["question_content"] = {}
        with self.assertRaises(PilotError) as caught:
            global_order(empty)
        self.assertEqual(caught.exception.code, "EMPTY_TARGET_DENOMINATOR")

        missing = self.observation()
        missing["view"]["target"]["questions"].append(
            {"platform_question_id": "q-no-frame", "platform_order": 2, "directory_id": "leaf"})
        missing["view"]["question_content"]["q-no-frame"] = copy.deepcopy(
            missing["view"]["question_content"]["q-old"])
        self.assertEqual(global_order(missing), 2)

    @staticmethod
    def complete_codec():
        return {"schema": "A24CompleteExportCodec/v1", "kind_path": ["kind"],
                "metadata_value": "metadata", "question_value": "question",
                "metadata_fields": {key: [key] for key in
                    ("book_id", "complete", "question_ids", "zones", "state_version")},
                "question_fields": {key: [key] for key in
                    ("platform_question_id", "question_type", "parts", "wire_zones", "question_info", "rect_ids")}}

    @staticmethod
    def row(qid="q-old", rect_ids=None, parts=None):
        return {"kind": "question", "platform_question_id": qid,
                "question_type": "ordinary_choice", "parts": [{}] if parts is None else parts,
                "wire_zones": {zone: None for zone in wire.ZONES}, "question_info": {},
                "rect_ids": ["r-old"] if rect_ids is None else rect_ids}

    def complete_text(self, qid="q-old", rect_ids=None, parts=None):
        metadata = {"kind": "metadata", "book_id": "46007447", "complete": True,
                    "question_ids": [qid], "zones": list(wire.ZONES), "state_version": "observed"}
        return "\n".join(json.dumps(value, separators=(",", ":"))
                          for value in (metadata, self.row(qid, rect_ids, parts)))

    def natural_codec(self):
        return {"schema": "A24NaturalExportCodec/v1", "question_fields": self.complete_codec()["question_fields"],
                "qualification": {"schema": "A24FullBodyRouteQualification/v1", "status": "VERIFIED",
                    "route": wire.EXPORT, "book_id": "46007447", "authoritative_catalog_complete": True,
                    "all_business_fields_covered": True, "zones": list(wire.ZONES),
                    "state_binding": "synthetic-bound", "evidence_refs": ["synthetic"]}}

    def test_complete_codec_rejects_invalid_question_and_rect_ids(self):
        for qid, rect_ids in ((None, ["r-old"]), (7, ["r-old"]), (" q-old", ["r-old"]),
                              ("q-old", [None]), ("q-old", [7]), ("q-old", [" r-old"])):
            with self.subTest(qid=qid, rect_ids=rect_ids), self.assertRaises(PilotError):
                wire.decode_complete_export(self.complete_text(qid, rect_ids), self.complete_codec(),
                                            [{"platform_question_id": qid}])

    def test_natural_codec_rejects_invalid_question_and_rect_ids(self):
        for qid, rect_ids in ((None, ["r-old"]), (7, ["r-old"]), (" q-old", ["r-old"]),
                              ("q-old", [None]), ("q-old", [7]), ("q-old", [" r-old"])):
            with self.subTest(qid=qid, rect_ids=rect_ids), self.assertRaises(PilotError):
                row = self.row(qid, rect_ids)
                wire.decode_natural_export(json.dumps(row), self.natural_codec(),
                                           [{"platform_question_id": qid}])

    def test_empty_part_object_is_still_accepted_and_remains_open(self):
        contents, _ = wire.decode_complete_export(
            self.complete_text(parts=[{}]), self.complete_codec(), [{"platform_question_id": "q-old"}])
        self.assertEqual(contents["q-old"]["parts"], [{}])
        contents, _ = wire.decode_natural_export(
            json.dumps(self.row(parts=[{}])), self.natural_codec(), [{"platform_question_id": "q-old"}])
        self.assertEqual(contents["q-old"]["parts"], [{}])


if __name__ == "__main__":
    unittest.main()
