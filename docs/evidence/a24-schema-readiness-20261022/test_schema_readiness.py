"""Focused offline checks for capture consumption and book identity provenance."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/a24_first_save_wire_r1"))

from fixture import FakeIO, bind_profile, fixture
from annotation.delivery.live_pilot import wire
from annotation.delivery.live_pilot.usense import UsenseTransport
from annotation.quality.live_pilot import PilotError, check_input, global_order
from annotation.runtime.live_pilot.schema_capture import CAPTURES, REPRESENTATION, load_current_schema_capture


class CaptureReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a24-schema-readiness-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def capture(self):
        output = self.root / "owned-output"
        private = output / "private"
        private.mkdir(parents=True)
        reads = []
        for slot, route, query_keys, filename in CAPTURES:
            raw = (slot + "-正文").encode("utf-8")
            path = private / filename
            path.write_bytes(raw)
            reference = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                         "capture_representation": REPRESENTATION}
            reads.append({"slot": slot, "path_template": route, "query_keys": list(query_keys),
                          "http_status": 200, "bytes": len(raw), "sha256": reference["sha256"],
                          "capture_representation": REPRESENTATION, "controlled_raw_ref": reference})
        result = {"status": "CURRENT_SCHEMA_UNBOUND", "write_allowed": False,
                  "successors": "NOT_RUN", "reads": reads}
        return output, result

    def test_exact_four_capture_set_loads_but_remains_unqualified_and_nonwritable(self):
        output, result = self.capture()
        capture = load_current_schema_capture(result, output)
        self.assertEqual(capture.text("book"), "book-正文")
        self.assertEqual([item["slot"] for item in capture.manifest], [v[0] for v in CAPTURES])
        summary = capture.public_summary()
        self.assertEqual(summary["status"], "CAPTURE_BYTES_VERIFIED_SCHEMA_UNBOUND")
        self.assertIs(summary["write_allowed"], False)
        self.assertIsNone(summary["schema_profile"])
        self.assertEqual(summary["qualification"], "NOT_RUN")
        self.assertNotIn(str(output), str(summary))
        self.assertNotIn("正文", str(summary))

    def test_missing_book_member_rejects(self):
        output, result = self.capture()
        result["reads"] = result["reads"][1:]
        with self.assertRaises(PilotError) as caught:
            load_current_schema_capture(result, output)
        self.assertEqual(caught.exception.code, "CURRENT_SCHEMA_CAPTURE_RESULT")

    def test_reference_outside_owned_private_root_rejects(self):
        output, result = self.capture()
        outside = self.root / "outside.bin"
        outside.write_bytes((output / "private/book-snapshot.bin").read_bytes())
        result["reads"][0]["controlled_raw_ref"]["path"] = str(outside)
        with self.assertRaises(PilotError) as caught:
            load_current_schema_capture(result, output)
        self.assertEqual(caught.exception.code, "CURRENT_SCHEMA_CAPTURE_PATH")

    def test_tampered_body_rejects_digest(self):
        output, result = self.capture()
        (output / "private/frames-snapshot.bin").write_bytes(b"tampered")
        with self.assertRaises(PilotError) as caught:
            load_current_schema_capture(result, output)
        self.assertEqual(caught.exception.code, "CURRENT_SCHEMA_CAPTURE_BYTES")

    def profile_case(self, literal_book):
        case = self.root / ("literal" if literal_book else "direct")
        case.mkdir()
        request, initial, fact, profile = fixture(case)
        reads = {}
        for phase in profile["reads"]:
            projection = {name: {"from": {"response": "snapshot", "path": ["snapshot", name]}}
                          for name in wire.SNAPSHOT_FIELDS}
            if literal_book:
                projection["book_id"] = {"literal": "46007447"}
            reads[phase] = {"requests": [
                {"name": "book", "path": "/qieti/api/synthetic/book", "params": {}, "count": 1},
                {"name": "snapshot", "path": "/qieti/api/synthetic/complete-snapshot",
                 "params": {"file_id": "46007447"}, "count": 1}], "projection": projection}
        profile["reads"] = reads
        bind_profile(request, profile, case)
        transport = UsenseTransport(FakeIO(initial, fact))
        return request, case, transport

    def test_literal_book_identity_profile_rejects_before_any_read(self):
        request, case, transport = self.profile_case(True)
        with self.assertRaises(PilotError) as caught:
            check_input(request, case, offline=True, wire=transport)
        self.assertEqual(caught.exception.code, "BOOK_IDENTITY_FROM_RESPONSE_REQUIRED")
        self.assertEqual(transport._session.calls, [])

    def test_direct_response_book_identity_profile_can_bind_without_reading(self):
        request, case, transport = self.profile_case(False)
        admission = check_input(request, case, offline=True, wire=transport)
        self.assertEqual(admission.wire.profile["reads"]["baseline"]["projection"]["book_id"],
                         {"from": {"response": "snapshot", "path": ["snapshot", "book_id"]}})
        self.assertEqual(transport._session.calls, [])

    def observation(self):
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

    def test_empty_denominator_rejects_but_question_without_frame_is_not_invented_as_invalid(self):
        empty = self.observation()
        empty["view"]["target"].update(questions=[], frames=[])
        empty["view"]["question_content"] = {}
        with self.assertRaises(PilotError) as caught:
            global_order(empty)
        self.assertEqual(caught.exception.code, "EMPTY_TARGET_DENOMINATOR")

        missing = self.observation()
        missing["view"]["target"]["questions"].append(
            {"platform_question_id": "q-without-frame", "platform_order": 2, "directory_id": "leaf"})
        missing["view"]["question_content"]["q-without-frame"] = copy.deepcopy(
            missing["view"]["question_content"]["q-old"])
        self.assertEqual(global_order(missing), 2)

    def test_noncanonical_snapshot_question_and_frame_ids_reject(self):
        for field, value in (("platform_question_id", None), ("platform_question_id", " q-old"),
                             ("platform_frame_id", ""), ("platform_frame_id", "r-old ")):
            with self.subTest(field=field, value=value):
                observed = self.observation()
                target = observed["view"]["target"]
                record = target["questions"][0] if field == "platform_question_id" else target["frames"][0]
                record[field] = value
                with self.assertRaises(PilotError) as caught:
                    global_order(observed)
                self.assertEqual(caught.exception.code, "TARGET_IDENTITY_INVALID")

    def complete_codec(self):
        return {"schema": "A24CompleteExportCodec/v1", "kind_path": ["kind"],
                "metadata_value": "metadata", "question_value": "question",
                "metadata_fields": {key: [key] for key in
                    ("book_id", "complete", "question_ids", "zones", "state_version")},
                "question_fields": {key: [key] for key in
                    ("platform_question_id", "question_type", "parts", "wire_zones", "question_info", "rect_ids")}}

    def export_text(self, qid="q-old", parts=None, rect_ids=None):
        metadata = {"kind": "metadata", "book_id": "46007447", "complete": True,
                    "question_ids": [qid], "zones": list(wire.ZONES), "state_version": "observed"}
        row = {"kind": "question", "platform_question_id": qid, "question_type": "ordinary_choice",
               "parts": [{}] if parts is None else parts, "wire_zones": {zone: None for zone in wire.ZONES},
               "question_info": {}, "rect_ids": ["r-old"] if rect_ids is None else rect_ids}
        return "\n".join(json.dumps(value, separators=(",", ":")) for value in (metadata, row))

    def test_export_invalid_question_rect_ids_and_null_parts_reject(self):
        cases = ((None, [{}], ["r-old"]), (" q-old", [{}], ["r-old"]),
                 ("q-old", [None], ["r-old"]), ("q-old", [{}], [None]),
                 ("q-old", [{}], [" r-old"]), ("q-old", [{}], ["r-old", "r-old"]))
        for qid, parts, rect_ids in cases:
            with self.subTest(qid=qid, parts=parts, rect_ids=rect_ids):
                with self.assertRaises(PilotError) as caught:
                    wire.decode_complete_export(self.export_text(qid, parts, rect_ids), self.complete_codec(),
                                                [{"platform_question_id": qid}])
                self.assertEqual(caught.exception.code, "EXPORT_COVERAGE_UNPROVEN" if qid is None or
                                 isinstance(qid, str) and qid != qid.strip() else "EXPORT_QUESTION_COVERAGE")

    def test_valid_complete_export_still_decodes(self):
        contents, proof = wire.decode_complete_export(
            self.export_text(), self.complete_codec(), [{"platform_question_id": "q-old"}])
        self.assertEqual(set(contents), {"q-old"})
        self.assertEqual(contents["q-old"]["rect_ids"], ["r-old"])
        self.assertIs(proof["complete"], True)

    def test_natural_export_applies_same_identity_and_parts_rules(self):
        codec = {"schema": "A24NaturalExportCodec/v1",
                 "question_fields": self.complete_codec()["question_fields"],
                 "qualification": {"schema": "A24FullBodyRouteQualification/v1", "status": "VERIFIED",
                    "route": wire.EXPORT, "book_id": "46007447", "authoritative_catalog_complete": True,
                    "all_business_fields_covered": True, "zones": list(wire.ZONES),
                    "state_binding": "synthetic-bound", "evidence_refs": ["synthetic"]}}
        row = json.loads(self.export_text("q-old", [None], [None]).splitlines()[1])
        with self.assertRaises(PilotError) as caught:
            wire.decode_natural_export(json.dumps(row), codec, [{"platform_question_id": "q-old"}])
        self.assertEqual(caught.exception.code, "EXPORT_QUESTION_COVERAGE")

    def test_identity_lookup_rejects_but_nonidentity_lookup_remains_legal(self):
        lookup = {"lookup": {"key": {"from": {"response": "$", "path": ["raw"]}},
                             "table": {"A": "canonical"}}}
        with self.assertRaises(PilotError) as caught:
            wire.validate_identity_projection({"object": {"platform_question_id": lookup}})
        self.assertEqual(caught.exception.code, "IDENTITY_FROM_RESPONSE_REQUIRED")
        self.assertTrue(wire.validate_identity_projection({"object": {"question_type": lookup}}))

    def test_identity_container_literal_and_array_item_lookup_reject(self):
        with self.assertRaises(PilotError) as caught:
            wire.validate_identity_projection({"object": {"view": {"literal": {
                "target": {"questions": [{"platform_question_id": "made-up"}]}}}}})
        self.assertEqual(caught.exception.code, "IDENTITY_FROM_RESPONSE_REQUIRED")

        directories = {"array": {
            "source": {"from": {"response": "snapshot", "path": ["directories"]}},
            "item": {"lookup": {"key": {"from": {"response": "$", "path": []}},
                                "table": {"raw": "canonical"}}}}}
        with self.assertRaises(PilotError) as caught:
            wire.validate_identity_projection({"object": {"directories": directories}})
        self.assertEqual(caught.exception.code, "IDENTITY_FROM_RESPONSE_REQUIRED")

    def test_identity_container_direct_copy_remains_legal(self):
        direct = {"from": {"response": "snapshot", "path": ["view"]}}
        self.assertTrue(wire.validate_identity_projection({"object": {"view": direct}}))


if __name__ == "__main__":
    unittest.main()
