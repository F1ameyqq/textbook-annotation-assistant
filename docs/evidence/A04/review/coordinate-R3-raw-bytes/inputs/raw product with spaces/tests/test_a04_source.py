"""A04 offline source tests. All fixture captures and pixels are SYNTHETIC."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import zlib

from annotation.contracts import content_digest, validate_bundle
from annotation.source.usense import (
    SourceParseError, build_source, parse_capture, parse_directory, source_evidence,
)


REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "a04" / "source"


class SourceParserTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        shutil.copytree(FIXTURE / "assets", self.root / "assets")
        self.capture = json.loads((FIXTURE / "capture.json").read_text(encoding="utf-8"))

    def parse(self, data=None, **kwargs):
        return parse_capture(data or self.capture, self.root,
                             now=kwargs.pop("now", self.capture["observed_at"]), **kwargs)

    def fails(self, code, data=None, **kwargs):
        with self.assertRaises(SourceParseError) as raised:
            self.parse(data, **kwargs)
        self.assertEqual(raised.exception.code, code)
        self.assertTrue(raised.exception.path.startswith("$"))
        return str(raised.exception)

    def test_source_bundle_public_api_and_real_asset_bytes(self):
        parsed = self.parse()
        source = build_source(parsed, self.root)
        self.assertEqual(source.content_hash, content_digest(source))
        self.assertEqual(source.payload.metadata_page_count, 214)
        self.assertEqual(len(source.payload.pages_acquired), 3)
        self.assertEqual(len(source.payload.scope_manifest), 2)
        self.assertEqual(source.payload.history[0].quality, "UNVERIFIED")
        for asset in source.payload.assets:
            self.assertEqual((asset.width, asset.height), (4, 3))
            self.assertEqual(asset.sha256, hashlib.sha256((self.root / asset.path).read_bytes()).hexdigest())
            self.assertEqual(asset.provenance, "SYNTHETIC")
        policy = json.loads((REPO / "config/policies/synthetic-choice-separate.json").read_text(encoding="utf-8"))
        exchange = {"format_version": "c01-exchange-1", "evidence": [source_evidence(parsed, self.root)],
                    "policies": [policy], "artifacts": [source.model_dump(mode="json")]}
        checked = validate_bundle(exchange, asset_root=self.root)
        self.assertEqual(checked.artifacts[0].kind, "SourceBundle")

    def test_page_mapping_is_not_geometry_or_coverage(self):
        parsed = self.parse()
        self.assertEqual([(p["viewer_page"], p["source_index"]) for p in parsed.pages], [(14, 13), (15, 14), (173, 172)])
        self.assertEqual(len(parsed.annotations), 4)
        source = build_source(parsed, self.root)
        history = json.loads((self.root / source.payload.history[0].resource.path).read_text(encoding="utf-8"))
        self.assertEqual(history["geometry_status"], "NOT_PERFORMED_BY_SOURCE")
        self.assertIn("not content coverage", source.payload.scope_manifest_basis)
        self.assertEqual(len(source.payload.external_page_mappings), 3)
        self.assertEqual(len({m.directory_id for m in source.payload.external_page_mappings}), 1)

    def test_question_identity_independent_of_printed_number_and_order(self):
        directories, questions = parse_directory(self.capture["directory"])
        self.assertEqual(len(directories), 2)
        self.assertEqual([q["printed_label"] for q in questions], ["1", "1"])
        self.assertEqual([q["platform_order"] for q in questions], [1, 1])
        self.assertNotEqual(questions[0]["question_id"], questions[1]["question_id"])
        changed = copy.deepcopy(self.capture["directory"])
        changed["data"]["directory_data"][0]["children"][0]["label"] = "99"
        changed["data"]["directory_data"][0]["children"][0]["order_in_level"] = "99"
        self.assertEqual(parse_directory(changed)[1][0]["question_id"], questions[0]["question_id"])

    def test_same_order_in_one_directory_is_ambiguous(self):
        node = copy.deepcopy(self.capture["directory"]["data"]["directory_data"][0]["children"][0])
        node["id"] = "different-node"
        self.capture["directory"]["data"]["directory_data"][0]["children"].append(node)
        self.fails("AMBIGUOUS_QUESTION")

    def test_directory_duplicate_node_id_fails(self):
        self.capture["directory"]["data"]["directory_data"][1]["id"] = "chapter-one"
        self.fails("DUPLICATE_REFERENCE")

    def test_question_without_directory_fails(self):
        self.capture["directory"]["data"]["directory_data"] = [self.capture["directory"]["data"]["directory_data"][0]["children"][0]]
        self.fails("MISSING_REFERENCE")

    def test_empty_question_scope_not_fabricated(self):
        for directory in self.capture["directory"]["data"]["directory_data"]:
            directory["children"] = []
        self.fails("SOURCE_EMPTY_SCOPE")

    def test_wrong_book_at_each_response_boundary(self):
        for mutate in (
            lambda d: d["book"].update(id="46006966"),
            lambda d: d["source_metadata"]["data"].update(file_id="46006966"),
            lambda d: d["pages"][0]["source_response"]["data"].update(file_id="46006966"),
            lambda d: d["annotations"]["data"][0].update(file_id="46006966"),
        ):
            with self.subTest(mutate=mutate):
                data = copy.deepcopy(self.capture)
                mutate(data)
                self.fails("TARGET_MISMATCH", data)

    def test_login_expired_response_is_classified_without_echo(self):
        secret = "DO-NOT-EMIT-SECRET-OR-RAW-URL"
        self.capture["directory"] = {"code": 401, "message": secret, "token": secret}
        message = self.fails("LOGIN_REQUIRED")
        self.assertNotIn(secret, message)

    def test_failed_and_incomplete_response(self):
        data = copy.deepcopy(self.capture)
        data["source_metadata"]["code"] = 500
        self.fails("RESPONSE_FAILURE", data)
        data = copy.deepcopy(self.capture)
        del data["directory"]["data"]
        self.fails("INCOMPLETE_RESPONSE", data)
        data = copy.deepcopy(self.capture)
        data["complete"] = False
        self.fails("INCOMPLETE_RESPONSE", data)

    def test_explicit_clock_replay_preserves_historical_tag(self):
        data = copy.deepcopy(self.capture)
        data.update(evidence_mode="OBSERVED", provenance="HISTORICAL")
        parsed = self.parse(data)
        self.assertEqual(parsed.provenance, "HISTORICAL")
        build_source(parsed, self.root)
        self.assertIn("HISTORICAL", source_evidence(parsed, self.root)["description"])
        self.fails("STALE_CAPTURE", data, now="2026-10-16T14:00:00+00:00")

    def test_stale_future_and_naive_timestamps_fail(self):
        self.fails("STALE_CAPTURE", now="2026-10-16T13:06:00+00:00")
        self.fails("STALE_CAPTURE", now="2026-10-16T12:59:00+00:00")
        self.capture["observed_at"] = "2026-10-16T13:00:00"
        self.fails("INVALID_TIME")

    def test_synthetic_cannot_be_relabelled_live(self):
        self.capture["provenance"] = "LIVE"
        self.fails("PROVENANCE")

    def test_missing_download_and_download_failure(self):
        data = copy.deepcopy(self.capture)
        data["pages"].pop()
        self.fails("SOURCE_MISSING", data)
        data = copy.deepcopy(self.capture)
        data["pages"][0]["download_status"] = 503
        self.fails("RESOURCE_FAILURE", data)
        (self.root / "assets/page-14.pgm").unlink()
        self.fails("RESOURCE_MISSING")

    def test_outside_scope_or_duplicate_page_fails(self):
        self.capture["pages"].append(copy.deepcopy(self.capture["pages"][0]))
        self.fails("INVALID_SCOPE")
        self.capture["pages"].pop()
        self.fails("INVALID_SCOPE", expected_pages=(14, 173))

    def test_uncertain_source_viewer_mapping_fails(self):
        for mutate in (
            lambda d: d["pages"][0]["mapping_evidence"].update(original_loaded=False),
            lambda d: d["pages"][0]["mapping_evidence"].update(source_index=12),
            lambda d: d["pages"][0]["source_response"]["data"]["pages"][0].update(image="raw-sensitive-url"),
            lambda d: d["pages"][0]["source_response"]["data"]["pages"].clear(),
        ):
            with self.subTest(mutate=mutate):
                data = copy.deepcopy(self.capture)
                mutate(data)
                self.fails("PAGE_MAPPING_UNCERTAIN", data)

    def test_does_not_assume_global_minus_one_page_mapping(self):
        self.capture["pages"][0]["source_response"]["data"]["pages"][0]["page_index"] = 11
        self.capture["pages"][0]["mapping_evidence"]["source_index"] = 11
        self.assertEqual(self.parse().pages[0]["source_index"], 11)

    def test_metadata_does_not_replace_acquired_count(self):
        self.capture["book"]["page_count"] = 215
        self.fails("INCOMPLETE_RESPONSE")

    def test_relative_path_and_declared_identity_rejected(self):
        for path in ("../outside.pgm", "C:/secret.pgm", "assets\\page-14.pgm", "assets/CON.pgm"):
            data = copy.deepcopy(self.capture)
            data["pages"][0]["asset_path"] = path
            self.fails("PATH_ESCAPE", data)
        self.capture["pages"][0]["sha256"] = "0" * 64
        self.fails("RESOURCE_MISMATCH")

    def test_invalid_image_header_fails(self):
        (self.root / "assets/page-14.pgm").write_bytes(b"not an image")
        self.fails("RESOURCE_INVALID")

    def test_png_and_jpeg_dimensions_from_bytes(self):
        def png_chunk(kind, payload):
            return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
        png = (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 3, 8, 0, 0, 0, 0))
               + png_chunk(b"IDAT", zlib.compress((b"\0" + b"\xff" * 4) * 3)) + png_chunk(b"IEND", b""))
        (self.root / "assets/page-14.pgm").write_bytes(png)
        self.assertEqual(self.parse().pages[0]["media_type"], "image/png")
        # A header alone cannot establish a complete original. Use fully encoded
        # SYNTHETIC pixels for this positive JPEG case.
        import io
        from PIL import Image
        jpeg = io.BytesIO()
        Image.new("RGB", (4, 3), "white").save(jpeg, format="JPEG")
        (self.root / "assets/page-14.pgm").write_bytes(jpeg.getvalue())
        page = self.parse().pages[0]
        self.assertEqual((page["media_type"], page["width"], page["height"]), ("image/jpeg", 4, 3))

    def test_frame_references_checked_including_unacquired_page(self):
        self.capture["annotations"]["data"][-1]["directory_id"] = "missing-directory"
        self.fails("MISSING_REFERENCE")

    def test_frame_id_duplicate_and_missing_parent(self):
        data = copy.deepcopy(self.capture)
        data["annotations"]["data"][1]["rect_id"] = data["annotations"]["data"][0]["rect_id"]
        self.fails("DUPLICATE_REFERENCE", data)
        self.capture["annotations"]["data"][0]["parent_rect_id"] = "missing-frame"
        self.fails("MISSING_REFERENCE")

    def test_frame_parent_cycle_fails(self):
        self.capture["annotations"]["data"][0]["parent_rect_id"] = "synthetic-frame-q"
        self.fails("REFERENCE_CYCLE")

    def test_nonfinite_boxes_rejected_out_of_bounds_preserved(self):
        data = copy.deepcopy(self.capture)
        data["annotations"]["data"][0]["rect_bbox"] = "0,0,NaN,3"
        self.fails("INVALID_BBOX", data)
        self.capture["annotations"]["data"][0]["rect_bbox"] = "-1,0,5,4"
        self.assertEqual(self.parse().annotations[0]["bbox"], [-1.0, 0.0, 5.0, 4.0])

    def test_unknown_sensitive_fields_never_survive(self):
        secret = "do-not-retain-any-secret-value"
        self.capture["cookie"] = secret
        self.capture["book"]["token"] = secret
        self.capture["directory"]["request_body"] = secret
        self.capture["annotations"]["data"][0]["image_path"] = "https://secret.invalid/?token=" + secret
        parsed = self.parse()
        source = build_source(parsed, self.root)
        self.assertNotIn(secret, json.dumps(parsed.safe_data()))
        self.assertNotIn(secret, (self.root / source.payload.history[0].resource.path).read_text(encoding="utf-8"))

    def test_nested_mutation_fails_before_build(self):
        parsed = self.parse()
        parsed.annotations[0]["bbox"][0] = 2.0
        with self.assertRaises(SourceParseError) as raised:
            build_source(parsed, self.root)
        self.assertEqual(raised.exception.code, "CAPTURE_MUTATED")
        self.assertFalse((self.root / "evidence").exists())

    def test_history_immutable_and_byte_bound(self):
        parsed = self.parse()
        source = build_source(parsed, self.root)
        self.assertEqual(build_source(parsed, self.root), source)
        history = self.root / source.payload.history[0].resource.path
        history.write_text("tampered", encoding="utf-8")
        with self.assertRaises(SourceParseError) as raised:
            build_source(parsed, self.root)
        self.assertEqual(raised.exception.code, "IMMUTABLE_RESOURCE")
        with self.assertRaises(SourceParseError):
            source_evidence(parsed, self.root)

    def test_original_change_between_parse_and_build_fails(self):
        parsed = self.parse()
        page = self.root / parsed.pages[0]["path"]
        page.write_bytes(page.read_bytes().replace(b"0 10 20 30", b"1 10 20 30"))
        with self.assertRaises(SourceParseError) as raised:
            build_source(parsed, self.root)
        self.assertEqual(raised.exception.code, "RESOURCE_MISMATCH")
        self.assertFalse((self.root / "evidence").exists())

    def test_full_observation_hash_includes_unacquired_frame(self):
        before = self.parse().observed_hash
        self.capture["annotations"]["data"][-1]["rect_bbox"] = "0,0,2,2"
        self.assertNotEqual(self.parse().observed_hash, before)


if __name__ == "__main__":
    unittest.main()
