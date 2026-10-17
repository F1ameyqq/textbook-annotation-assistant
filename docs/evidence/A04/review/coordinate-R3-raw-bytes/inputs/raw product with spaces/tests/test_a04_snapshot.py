"""A04 offline platform-view tests; every record/image here is synthetic.

The historical A05 comparison is tested separately and never becomes live
acceptance. These tests use C01's public sealing, writing and validation APIs.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from annotation.contracts import (
    SCHEMA_VERSION, SourceBundle, content_digest, load_bundle, seal_artifact,
    validate_bundle, write_bundle,
)
from annotation.delivery.usense_readonly import (
    SnapshotError, build_snapshot, snapshot_evidence,
)
from annotation.source.usense import ParsedCapture, build_source, parse_capture, source_evidence


ROOT = Path(__file__).resolve().parents[1]
OBSERVED_AT = "2026-10-16T00:00:00+00:00"


def fixture(root, evidence_mode="SYNTHETIC", provenance="SYNTHETIC"):
    """Create a standalone source and normalized collector-shaped input."""
    root = Path(root)
    (root / "assets").mkdir(parents=True)
    (root / "evidence").mkdir()
    pages, assets = [], []
    for viewer_page in (14, 15, 173):
        path = "assets/page-{}.pgm".format(viewer_page)
        image = b"P2\n100 100\n255\n" + b"0 " * 10000
        (root / path).write_bytes(image)
        sha256 = hashlib.sha256(image).hexdigest()
        asset_id = "asset-viewer-{}".format(viewer_page)
        pages.append({"viewer_page": viewer_page, "source_index": viewer_page - 1,
                      "asset_id": asset_id, "path": path, "sha256": sha256,
                      "media_type": "image/x-portable-graymap", "width": 100, "height": 100})
        assets.append({"asset_id": asset_id, "path": path, "sha256": sha256,
                       "media_type": "image/x-portable-graymap", "width": 100, "height": 100,
                       "source_label": "synthetic viewer {}".format(viewer_page),
                       "provenance": "SYNTHETIC" if evidence_mode == "SYNTHETIC" else "ORIGINAL"})
    directories = [
        {"directory_id": "source-dir-one", "platform_directory_id": "platform-dir-one",
         "parent_id": None, "label": "synthetic one"},
        {"directory_id": "source-dir-two", "platform_directory_id": "platform-dir-two",
         "parent_id": None, "label": "synthetic two"},
    ]
    questions = [
        {"platform_question_id": "platform-question-one", "directory_id": "platform-dir-one", "platform_order": 1},
        {"platform_question_id": "platform-question-two", "directory_id": "platform-dir-two", "platform_order": 1},
    ]
    annotations = []
    for index, viewer_page in enumerate((14, 15, 173, 16)):
        annotations.append({
            "platform_frame_id": "frame-{}".format(index),
            "platform_question_id": questions[index % 2]["platform_question_id"],
            "directory_id": questions[index % 2]["directory_id"], "platform_order": 1,
            "viewer_page": viewer_page, "bbox": [1.0, 2.0, 20.0, 30.0],
            "platform_role": ("Q", "W", "A", "E")[index], "parent_frame_id": None,
        })
    fields = dict(
        book_id="46007447", observed_at=OBSERVED_AT, evidence_mode=evidence_mode,
        provenance=provenance, book={"id": "46007447", "page_count": 214,
            "question_count": 2, "status": "标注中", "updated_at": "2026-10-16 08:00:00"},
        metadata_page_count=214, directories=directories, questions=questions,
        pages=pages, annotations=annotations,
    )
    # This is a synthetic normalized capture, not a saved platform response.
    parsed = ParsedCapture(**fields, observed_hash=content_digest(fields))
    proof = {"observed_at": OBSERVED_AT, "provenance": provenance,
             "annotations": annotations, "directories": directories}
    raw = (json.dumps(proof, ensure_ascii=False) + "\n").encode("utf-8")
    (root / "evidence/source-capture.json").write_bytes(raw)
    evidence = {"evidence_id": "proof-a04-source", "resource": {
        "path": "evidence/source-capture.json", "sha256": hashlib.sha256(raw).hexdigest(),
        "media_type": "application/json"}, "description": "Synthetic A04 input.", "mode": evidence_mode}
    source = SourceBundle.model_validate(seal_artifact({
        "schema_version": SCHEMA_VERSION, "artifact_id": "source-a04-synthetic", "revision": 1,
        "kind": "SourceBundle", "run_id": "run-a04-synthetic", "book_id": "46007447",
        "scope_id": "scope-a04-synthetic", "input_refs": [],
        "producer": {"module": "source.usense", "implementation_version": "a04-test",
                     "config_version": "a04-synthetic", "policy_versions": [],
                     "model_version": None, "prompt_version": None, "evidence_mode": evidence_mode},
        "created_at": OBSERVED_AT,
        "payload": {"assets": assets, "directories": [{"directory_id": "source-root", "parent_id": None, "label": "import scope"}],
                    "pages_expected": [a["asset_id"] for a in assets],
                    "pages_acquired": [a["asset_id"] for a in assets],
                    "external_page_mappings": [{"asset_id": p["asset_id"], "directory_id": "source-root",
                        "external_page": "viewer:{};source_index:{}".format(p["viewer_page"], p["source_index"]),
                        "mapping_status": "CONFIRMED", "evidence_refs": ["proof-a04-source"]} for p in pages],
                    "history": [], "scope_manifest": ["question-synthetic"],
                    "scope_manifest_basis": "Synthetic three-page snapshot fixture.", "metadata_page_count": 214},
    }))
    return parsed, source, evidence


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name) / "standalone input"
        self.parsed, self.source, self.evidence = fixture(self.folder)

    def bundle(self, snapshot):
        policy = json.loads((ROOT / "config/policies/usense-v1-proposal.json").read_text(encoding="utf-8"))
        return {"format_version": "c01-exchange-1", "policies": [policy],
                "evidence": [self.evidence, snapshot_evidence(self.parsed, self.source, self.folder)],
                "artifacts": [self.source.model_dump(mode="json"), snapshot.model_dump(mode="json")]}

    def assert_failure(self, mutation, code, path):
        mutation()
        with self.assertRaises(SnapshotError) as caught:
            build_snapshot(self.parsed, self.source, self.folder)
        self.assertEqual((caught.exception.code, caught.exception.path), (code, path))
        self.assertFalse((self.folder / "evidence/platform-summary.json").exists())

    def test_public_contract_roundtrip_and_portable_bundle(self):
        snapshot = build_snapshot(self.parsed, self.source, self.folder)
        bundle = validate_bundle(self.bundle(snapshot), asset_root=self.folder)
        self.assertEqual(snapshot.book_id, "46007447")
        self.assertEqual(snapshot.payload.target_id, "46007447")
        self.assertEqual(snapshot.payload.observed_at, OBSERVED_AT)
        self.assertEqual(len(snapshot.payload.frames), 3)
        self.assertEqual(len(snapshot.payload.questions), 2)
        self.assertEqual(len(snapshot.payload.directories), 2)
        self.assertEqual({frame.box.image.asset_id for frame in snapshot.payload.frames},
                         set(self.source.payload.pages_acquired))
        write_bundle(bundle, self.folder / "exchange.json")
        copied = Path(self.temporary.name) / "copied package with spaces"
        shutil.copytree(self.folder, copied)
        loaded = load_bundle(copied / "exchange.json")
        self.assertEqual(loaded, bundle)

    def test_full_counts_status_and_frame_scope_are_separate_evidence(self):
        snapshot = build_snapshot(self.parsed, self.source, self.folder)
        summary = json.loads((self.folder / "evidence/platform-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["metadata_page_count"], 214)
        self.assertEqual(summary["acquired_original_count"], 3)
        self.assertEqual(summary["full_platform_frame_count"], 4)
        self.assertEqual(summary["snapshot_frame_count"], 3)
        self.assertEqual(summary["omitted_frame_count_without_acquired_original"], 1)
        self.assertEqual(summary["book_status"], "标注中")
        self.assertEqual(summary["full_platform_frame_role_counts"], {"A": 1, "E": 1, "Q": 1, "W": 1})
        self.assertFalse(summary["complete_platform_frames_in_snapshot"])
        self.assertEqual(snapshot.payload.observed_hash, summary["full_platform_observed_hash"])

    def test_unverified_capabilities_remain_c01_unknown(self):
        snapshot = build_snapshot(self.parsed, self.source, self.folder)
        self.assertEqual({cap.status for cap in snapshot.payload.capabilities}, {"UNKNOWN"})
        self.assertTrue(all(not cap.evidence_refs for cap in snapshot.payload.capabilities))

    def test_nested_capture_mutation_cannot_keep_an_old_state_hash(self):
        self.assert_failure(lambda: self.parsed.annotations[3].update(bbox=[2.0, 2.0, 20.0, 30.0]),
                            "HASH_MISMATCH", "capture.observed_hash")

    def test_reference_missing_on_omitted_frame_is_rejected(self):
        self.assert_failure(lambda: self.parsed.annotations[3].update(platform_question_id="missing"),
                            "MISSING_REFERENCE", "annotations[3].platform_question_id")

    def test_wrong_directory_order_pair_on_omitted_frame_is_rejected(self):
        self.assert_failure(lambda: self.parsed.annotations[3].update(directory_id="platform-dir-one"),
                            "QUESTION_REFERENCE_CONFLICT", "annotations[3].platform_question_id")

    def test_missing_parent_frame_on_omitted_frame_is_rejected(self):
        self.assert_failure(lambda: self.parsed.annotations[3].update(parent_frame_id="missing"),
                            "MISSING_REFERENCE", "annotations[3].parent_frame_id")

    def test_missing_directory_on_question_is_rejected(self):
        self.assert_failure(lambda: self.parsed.questions[1].update(directory_id="missing"),
                            "MISSING_REFERENCE", "questions[1].directory_id")

    def test_duplicate_question_order_within_same_directory_is_rejected(self):
        self.assert_failure(lambda: self.parsed.questions[1].update(directory_id="platform-dir-one"),
                            "AMBIGUOUS_QUESTION", "questions[1].platform_order")

    def test_duplicate_frame_in_omitted_scope_is_rejected(self):
        self.assert_failure(lambda: self.parsed.annotations[3].update(platform_frame_id="frame-0"),
                            "DUPLICATE_ID", "annotations[3].platform_frame_id")

    def test_nonfinite_or_invalid_bbox_in_omitted_scope_is_rejected(self):
        self.assert_failure(lambda: self.parsed.annotations[3].update(bbox=[1.0, 2.0, float("nan"), 30.0]),
                            "INVALID_BBOX", "annotations[3].bbox")

    def test_out_of_bounds_acquired_frame_is_preserved_in_capture_and_rejected(self):
        self.assert_failure(lambda: self.parsed.annotations[0].update(bbox=[-1.0, 2.0, 20.0, 30.0]),
                            "BBOX_OUT_OF_BOUNDS", "annotations[0].bbox")
        self.assertEqual(self.parsed.annotations[0]["bbox"][0], -1.0)

    def test_image_identity_conflict_is_rejected(self):
        self.assert_failure(lambda: self.parsed.pages[0].update(sha256="0" * 64),
                            "IMAGE_BINDING_CONFLICT", "pages[0]")

    def test_wrong_book_is_rejected(self):
        def wrong_book():
            self.parsed = replace(self.parsed, book_id="46006966")
        self.assert_failure(wrong_book,
                            "WRONG_BOOK", "source.book_id")

    def test_observed_synthetic_source_conflict_is_rejected(self):
        def wrong_mode():
            self.parsed = replace(self.parsed, evidence_mode="OBSERVED")
        self.assert_failure(wrong_mode,
                            "EVIDENCE_MODE_CONFLICT", "source.producer.evidence_mode")

    def test_summary_is_not_overwritten_and_evidence_detects_tampering(self):
        build_snapshot(self.parsed, self.source, self.folder)
        destination = self.folder / "evidence/platform-summary.json"
        original = destination.read_bytes()
        with self.assertRaises(SnapshotError) as caught:
            build_snapshot(self.parsed, self.source, self.folder)
        self.assertEqual(caught.exception.code, "EVIDENCE_EXISTS")
        self.assertEqual(destination.read_bytes(), original)
        destination.write_bytes(b"{}\n")
        with self.assertRaises(SnapshotError) as tampered:
            snapshot_evidence(self.parsed, self.source, self.folder)
        self.assertEqual(tampered.exception.code, "EVIDENCE_MISMATCH")

    def test_evidence_path_cannot_leave_package(self):
        for path in ("../summary.json", "C:/summary.json", "/summary.json", "evidence\\summary.json"):
            with self.subTest(path=path), self.assertRaises(SnapshotError) as caught:
                build_snapshot(self.parsed, self.source, self.folder, summary_path=path)
            self.assertEqual(caught.exception.code, "INVALID_EVIDENCE_PATH")


class HistoricalA05SnapshotTests(unittest.TestCase):
    """Replay existing A05 files offline; no statement about current platform."""

    def historical_capture(self, root):
        old = ROOT / "docs/evidence/A05/execution"
        def read(name):
            return json.loads((old / name).read_text(encoding="utf-8"))
        book = read("reopen-book.json")
        (root / "assets").mkdir()
        pages = []
        for viewer_page in (14, 173):
            path = "assets/historical-{}.jpg".format(viewer_page)
            shutil.copyfile(old / "source-viewer{}.jpg".format(viewer_page), root / path)
            pages.append({"viewer_page": viewer_page, "asset_path": path, "download_status": 200,
                "source_response": {"code": 0, "data": {"file_id": "46007447", "pages": [
                    {"image": "original:viewer-{}".format(viewer_page), "page_index": viewer_page - 1}]}},
                "mapping_evidence": {"viewer_page": viewer_page, "source_index": viewer_page - 1,
                                     "original_loaded": True}})
        return {"capture_version": "a04.readonly.v1", "complete": True,
                "evidence_mode": "OBSERVED", "provenance": "HISTORICAL",
                "observed_at": book["observed_at"], "book": book,
                "source_metadata": read("source-metadata.json"),
                "directory": read("reopen-directory.json"),
                "annotations": read("reopen-annotations.json"), "pages": pages}

    def test_historical_source_parser_and_snapshot_public_contract_integration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            capture = self.historical_capture(root)
            parsed = parse_capture(capture, root, expected_pages=(14, 173), now=capture["observed_at"])
            source = build_source(parsed, root)
            snapshot = build_snapshot(parsed, source, root)
            policy = json.loads((ROOT / "config/policies/usense-v1-proposal.json").read_text(encoding="utf-8"))
            bundle = validate_bundle({"format_version": "c01-exchange-1", "policies": [policy],
                "evidence": [source_evidence(parsed, root), snapshot_evidence(parsed, source, root)],
                "artifacts": [source.model_dump(mode="json"), snapshot.model_dump(mode="json")]}, asset_root=root)
            self.assertEqual(snapshot.payload.observed_at, capture["observed_at"])
            self.assertEqual(snapshot.producer.evidence_mode, "OBSERVED")
            self.assertEqual(parsed.provenance, "HISTORICAL")
            summary = json.loads((root / "evidence/platform-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["full_platform_frame_count"], 68)
            self.assertEqual(summary["question_node_count"], 22)
            self.assertEqual(summary["provenance"], "HISTORICAL")
            self.assertEqual(summary["acquired_viewer_pages"], [14, 173])
            self.assertLess(summary["snapshot_frame_count"], 68)
            self.assertEqual(summary["snapshot_frame_count"], sum(
                frame["viewer_page"] in (14, 173) for frame in parsed.annotations))
            write_bundle(bundle, root / "exchange.json")
            self.assertEqual(load_bundle(root / "exchange.json"), bundle)

    def test_omitted_historical_frame_change_updates_full_state_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            capture = self.historical_capture(root)
            before = parse_capture(capture, root, expected_pages=(14, 173), now=capture["observed_at"])
            outside = next(row for row in capture["annotations"]["data"] if row["page_index"] not in (14, 173))
            values = [float(value) for value in outside["rect_bbox"].split(",")]
            values[0] += 0.125
            outside["rect_bbox"] = ",".join(str(value) for value in values)
            after = parse_capture(capture, root, expected_pages=(14, 173), now=capture["observed_at"])
            self.assertNotEqual(before.observed_hash, after.observed_hash)
            before_source = build_source(before, root, history_path="evidence/before-source.json")
            after_source = build_source(after, root, history_path="evidence/after-source.json")
            before_snapshot = build_snapshot(before, before_source, root, summary_path="evidence/before-summary.json")
            after_snapshot = build_snapshot(after, after_source, root, summary_path="evidence/after-summary.json")
            self.assertEqual(before_snapshot.payload.frames, after_snapshot.payload.frames)
            self.assertNotEqual(before_snapshot.payload.observed_hash, after_snapshot.payload.observed_hash)


if __name__ == "__main__":
    unittest.main()
