import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from annotation.quality.live_pilot import PilotError
from annotation.runtime.live_pilot.historical_preservation import (
    DOM_LINK_TYPE,
    build_identity_mapping,
    load_historical_original,
)


SOURCE_SHA256 = "02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c"
SOURCE_BYTES = 11625


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class IndependentHistoricalPreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a24-independent-historical-")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def source(self, raw):
        path = self.root / "source.jsonl"
        path.write_bytes(raw)
        return path

    def test_actual_original_preserves_bytes_fields_values_order_and_empty_forms(self):
        path = Path(os.environ["A24_HISTORICAL_EXPORT_PATH"])
        raw = path.read_bytes()
        archive = load_historical_original(path, SOURCE_SHA256, SOURCE_BYTES)
        self.assertEqual(archive.reconstruct_bytes(), raw)
        expected = [json.loads(line, object_pairs_hook=dict)
                    for line in raw.decode("utf-8").splitlines()]
        actual = archive.full_records()
        self.assertEqual(actual, expected)
        self.assertEqual([list(value) for value in actual], [list(value) for value in expected])
        self.assertEqual(len(actual), 19)
        self.assertEqual([value["tixu"] for value in actual], list(range(1, 20)))
        manifest = archive.public_preservation_manifest()
        self.assertIs(manifest["write_allowed"], False)
        serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True)
        for value in actual:
            for field in ("question", "answer", "tishi"):
                if len(value[field]) >= 16:
                    self.assertNotIn(value[field], serialized)

    def test_wrong_hash_tamper_and_nested_duplicate_keys_fail_closed_without_body_leak(self):
        sentinel = "PRIVATE_SENTINEL_BODY"
        raw = ('{"outer":{"secret":"' + sentinel + '","secret":"other"}}').encode()
        path = self.source(raw)
        with self.assertRaises(PilotError) as caught:
            load_historical_original(path, sha(raw), len(raw))
        self.assertEqual(caught.exception.code, "HISTORICAL_JSON_DUPLICATE_KEY")
        self.assertNotIn(sentinel, str(caught.exception))
        with self.assertRaises(PilotError) as caught:
            load_historical_original(path, "0" * 64, len(raw))
        self.assertEqual(caught.exception.code, "HISTORICAL_SOURCE_BYTES")
        self.assertNotIn(sentinel, str(caught.exception))

    def test_identity_candidates_never_become_canonical_and_ambiguity_holds(self):
        raw = b'{"tixu":1,"question":"same"}\n{"tixu":2,"question":"same"}'
        archive = load_historical_original(self.source(raw), sha(raw), len(raw))
        links = [
            {"source_line": 1, "evidence_type": DOM_LINK_TYPE,
             "candidate_value": "dom-shared", "evidence_sha256": "1" * 64},
            {"source_line": 2, "evidence_type": DOM_LINK_TYPE,
             "candidate_value": "dom-shared", "evidence_sha256": "1" * 64},
        ]
        ledger = build_identity_mapping(archive, links)
        self.assertIs(ledger["write_allowed"], False)
        self.assertEqual(ledger["status"], "HOLD_CANONICAL_ID_UNBOUND")
        self.assertTrue(all(item["canonical_question_id"] is None and
                            item["selected_candidate"] is None and
                            item["status"] == "HOLD_AMBIGUOUS_LOCAL_MAPPING"
                            for item in ledger["entries"]))

    def test_identity_authority_disguise_rejects(self):
        raw = b'{"tixu":1}'
        archive = load_historical_original(self.source(raw), sha(raw), len(raw))
        for forbidden in ("canonical_question_id", "selected_candidate", "write_allowed"):
            link = {"source_line": 1, "evidence_type": DOM_LINK_TYPE,
                    "candidate_value": "dom-only", "evidence_sha256": "1" * 64,
                    forbidden: "invented"}
            with self.subTest(forbidden=forbidden), self.assertRaises(PilotError) as caught:
                build_identity_mapping(archive, [link])
            self.assertEqual(caught.exception.code, "IDENTITY_EVIDENCE_SCHEMA")

    def test_decimal_and_overflow_numbers_fail_closed_instead_of_lossy_parse(self):
        for raw in (b'{"value":0.123456789012345678901234567890}', b'{"value":1e309}'):
            with self.subTest(raw=raw):
                with self.assertRaises(PilotError) as caught:
                    load_historical_original(self.source(raw), sha(raw), len(raw))
                self.assertEqual(caught.exception.code, "HISTORICAL_JSON_NUMBER")

    def test_archive_cannot_be_mutated_through_internal_record_value(self):
        raw = b'{"question":"original"}'
        archive = load_historical_original(self.source(raw), sha(raw), len(raw))
        exposed = getattr(archive.records[0], "_value", None)
        if exposed is not None:
            exposed["question"] = "mutated"
        self.assertEqual(archive.full_records(), [{"question": "original"}])
        self.assertEqual(archive.reconstruct_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
