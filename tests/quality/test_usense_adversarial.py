"""Independent risk scenarios using public synthetic fixtures, never live data.

Reuse fixture builders only, not TestCase inheritance (which duplicates counts).
Mutations are consumer-visible accidents: compacted order, cross-zone image loss,
coherently changed hashes, missing evidence, and wrong source-page coordinates.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
import test_usense_live_update as ordinary
import test_usense_live_writer_review as writer_fixture
import test_usense_live_revision as history
import test_usense_live_insertion as insertion_fixture
import test_usense_live_finalize as main_fixture
from annotation.runtime.usense_live import update, insertion, finalize_files


def reindex_selected(before, target):
    """Move stable question 2 to native order 3, keeping its source and identity."""
    after, selected = copy.deepcopy((before, target))
    nodes = after["directory"]["data"]["directory_data"][0]["children"][0]["children"]
    nodes[1], nodes[2] = nodes[2], nodes[1]
    for order, row in enumerate(nodes, 1):
        row["order_in_level"] = str(order)
    for row in after["frames"]["data"]:
        row["order_in_level"] = {"2": "3", "3": "2"}.get(row["order_in_level"], row["order_in_level"])
    after["annotations"]["data"] = copy.deepcopy([
        row for row in after["frames"]["data"] if row["order_in_level"] == "3"])
    after["info"]["data"]["order_in_level"] = "3"
    selected["question_order"] = 3
    return after, selected


class IdentityAndImageRisks(unittest.TestCase):
    def test_ledger_identity_survives_valid_reindex_and_changed_text(self):
        before, target = ordinary.fixture()
        original = update.make_plan(before, target, {"question": ordinary.review("first reviewed text")})
        moved, identity = reindex_selected(before, target)
        successor = update.make_plan(moved, identity, {"question": ordinary.review("second reviewed text")})
        self.assertEqual(original["ledger_key"], successor["ledger_key"])
        self.assertNotEqual(original["plan_sha256"], successor["plan_sha256"])
        self.assertEqual(successor["target"]["node_id"], target["node_id"])
        self.assertEqual(successor["payload_candidate"]["question_order"], 3)

    def test_old_order_with_new_occupant_cannot_reuse_original_identity(self):
        before, target = ordinary.fixture()
        moved, _ = reindex_selected(before, target)
        with self.assertRaises(ValueError):
            update.make_plan(moved, target, {"question": ordinary.review("wrong occupant")})

    def test_same_figure_moved_to_other_zone_is_still_loss(self):
        before, target = ordinary.fixture()
        image = '<img src="https://synthetic.invalid/diagram.png?part=1&amp;sig=keep">'
        before["zones"]["question"]["data"]["ocr_result"] += image
        with self.assertRaises(ValueError) as caught:
            update.make_plan(before, target, {"question": ordinary.review("text without figure"),
                                             "choice": ordinary.review("choices " + image)})
        self.assertEqual(caught.exception.code, "EXISTING_IMAGE_REFERENCE_REMOVAL_FORBIDDEN")

    def test_html_to_markdown_preserves_destination_and_multiplicity(self):
        before, target = ordinary.fixture()
        url = "https://synthetic.invalid/a(b).png?part=1&sig=keep"
        before["zones"]["question"]["data"]["ocr_result"] = ('<img src="' + url.replace('&', '&amp;') + '">') * 2
        kept = ("![synthetic](" + url + ")\n") * 2
        plan = update.make_plan(before, target, {"question": ordinary.review(kept)})
        self.assertTrue(update.compare_readback(plan, copy.deepcopy(plan["expected"]))["match"])
        with self.assertRaises(ValueError):
            update.make_plan(before, target, {"question": ordinary.review(kept.splitlines()[0])})

    def test_collapsed_reference_definition_cannot_change_url(self):
        before, target = ordinary.fixture()
        before["zones"]["question"]["data"]["ocr_result"] = "![diagram][]\n[diagram]: <https://synthetic.invalid/original.png>"
        changed = "![diagram][]\n[diagram]: <https://synthetic.invalid/other-page.png>"
        with self.assertRaises(ValueError):
            update.make_plan(before, target, {"question": ordinary.review(changed)})


class StoredEvidenceRisks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.files = writer_fixture.FixtureFiles(Path(self.tmp.name))

    def test_unknown_intent_survives_new_source_text_and_plan(self):
        key = self.files.plan["ledger_key"]
        raw = b'{"state":"UNKNOWN_DO_NOT_RETRY","automatic_retry_allowed":false}'
        self.files.claim.write_bytes(raw)
        changed = copy.deepcopy(self.files.plan["approved_changes"])
        changed["question"]["text"] += " changed reviewed draft"
        changed["question"]["reviewed_text_sha256"] = update.text_digest(changed["question"]["text"])
        plan = update.make_plan(self.files.plan["before"], self.files.plan["target"], changed)
        self.assertEqual(plan["ledger_key"], key)
        with self.assertRaisesRegex(ValueError, "EXISTING_INTENT_READBACK_REQUIRED_NO_RETRY"):
            writer_fixture.writer.validate_inputs(plan, self.files.baseline, self.files.endpoints,
                                                  self.files.ledger, "SYNTHETIC_ONLY")
        self.assertEqual(self.files.claim.read_bytes(), raw)

    def test_unknown_intent_survives_consistent_order_reindex(self):
        before, target = ordinary.fixture()
        moved, identity = reindex_selected(before, target)
        plan = update.make_plan(moved, identity, self.files.plan["approved_changes"])
        self.assertEqual(plan["ledger_key"], self.files.plan["ledger_key"])
        native = {"directory": moved["directory"], "frames": moved["frames"],
                  "q3_annotations": moved["annotations"], "q3_info": moved["info"],
                  **{"q3_" + zone: value for zone, value in moved["zones"].items()}}
        for name, value in native.items():
            history.dump(self.files.baseline / (name + ".json"), value)
        original = b'{"state":"UNKNOWN_DO_NOT_RETRY"}'
        self.files.claim.write_bytes(original)
        endpoints = {name: "/synthetic/" + name for name in native}
        with self.assertRaisesRegex(ValueError, "EXISTING_INTENT_READBACK_REQUIRED_NO_RETRY"):
            writer_fixture.writer.validate_inputs(plan, self.files.baseline, endpoints,
                                                  self.files.ledger, "SYNTHETIC_ONLY")
        self.assertEqual(self.files.claim.read_bytes(), original)

    def test_valid_history_control_and_source_bytes_tamper(self):
        acceptance, _ = history.accepted_predecessor(self.files)
        verify = lambda: history.revision.verify_previous_acceptance(
            acceptance, self.files.plan, self.files.native, self.files.ledger)
        self.assertTrue(verify()["current_before_exactly_previous_readback"])
        self.files.source.write_bytes(b"wrong source page with same filename")
        with self.assertRaisesRegex(ValueError, "PREVIOUS_REVIEW_EVIDENCE_CHANGED"):
            verify()

    def test_rehashed_reader_raw_and_process_summary_do_not_fool_recomparison(self):
        acceptance, prior = history.accepted_predecessor(self.files)
        qdir = acceptance.parent
        reader = qdir.parent / "usense-readonly-synthetic-reader"
        rawpath = reader / "q2_question.json"
        body = json.loads(rawpath.read_bytes())
        body["data"]["ocr_result"] = "coherently rehashed wrong question"
        digest = history.dump(rawpath, body)
        summary = json.loads((reader / "capture-summary.json").read_bytes())
        summary["captures"]["q2_question"]["sha256"] = digest
        summary["captures"]["q2_question"]["bytes"] = rawpath.stat().st_size
        history.dump(reader / "capture-summary.json", summary)
        process = json.loads((qdir / "reader-process-result.json").read_bytes())
        process["result"] = summary
        history.dump(qdir / "reader-process-result.json", process)
        # Acceptance and ledger remain internally consistent, but comparison must
        # be recomputed from native data rather than trusting the PASS summary.
        self.assertTrue(json.loads(acceptance.read_bytes())["comparison"]["match"])
        with self.assertRaisesRegex(ValueError, "PREVIOUS_READBACK_NOT_MATCHED"):
            history.revision.verify_previous_acceptance(acceptance, self.files.plan, self.files.native, self.files.ledger)

    def test_missing_raw_evidence_cannot_be_replaced_by_pass_summary(self):
        acceptance, _ = history.accepted_predecessor(self.files)
        (acceptance.parent.parent / "usense-readonly-synthetic-reader/q2_answer.json").unlink()
        with self.assertRaisesRegex(ValueError, "PATH_MISSING"):
            history.revision.verify_previous_acceptance(acceptance, self.files.plan, self.files.native, self.files.ledger)

    def test_finalizer_rejects_changed_file_even_with_embedded_pass(self):
        path = Path(self.tmp.name) / "receipt.json"
        digest = history.dump(path, {"status": "PASS", "synthetic": True})
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(ValueError) as caught:
            finalize_files._read_ref({"path": str(path.resolve()), "sha256": digest})
        self.assertEqual(caught.exception.code, "EVIDENCE_RAW_FILE_CHANGED")

    def test_audit_manifest_cannot_omit_required_raw_file(self):
        path = Path(self.tmp.name) / "known.json"
        digest = history.dump(path, {"synthetic": True})
        manifest = {"schema": "UsenseIndependentInsertAuditManifest/v1", "status": "VERIFIED",
                    "files": [{"path": str(path.resolve()), "sha256": digest, "role": "known"}]}
        missing = {"receipt": {"path": str(path.parent / "missing.json"), "sha256": "a" * 64}}
        with self.assertRaises(ValueError) as caught:
            finalize_files.verify_audit_manifest(manifest, missing)
        self.assertEqual(caught.exception.code, "AUDIT_MANIFEST_MISSING_REQUIRED_ORIGINAL")


class SourceAndReorderRisks(unittest.TestCase):
    def setUp(self):
        self.before, self.payload, self.approved = insertion_fixture.synthetic_fixture()

    def test_correct_source_page_control(self):
        plan = insertion.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)
        self.assertEqual(plan["before_sha256"], insertion.flat_digest(self.before))

    def test_answer_frame_claiming_question_viewer_page_is_rejected(self):
        row = self.approved["candidate"]["frames"][-1]
        row["viewer_page"] = row["page_index"] = 10
        with self.assertRaisesRegex(ValueError, "FRAME_SOURCE_PAGE"):
            insertion.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)

    def test_wrong_oss_page_even_with_consistent_claimed_url_is_rejected(self):
        row = self.approved["candidate"]["frames"][-1]
        wrong = row["image_path"].replace("_page_172.jpg", "_page_9.jpg")
        row["image_path"] = row["hosted_image_url"] = row["fetch_evidence"]["url"] = wrong
        with self.assertRaisesRegex(ValueError, "EXACT_SOURCE_CROP_URL"):
            insertion.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)

    def test_source_hash_from_other_page_without_evidence_binding_is_rejected(self):
        row = self.approved["candidate"]["frames"][-1]
        row["source"]["sha256"] = row["source_sha256"] = row["fetch_evidence"]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_EVIDENCE_BINDING"):
            insertion.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)

    def test_answer_cannot_reuse_question_source_even_with_rehashed_claims(self):
        frames = self.approved["candidate"]["frames"]
        answer = frames[-1]
        answer["source"] = copy.deepcopy(frames[0]["source"])
        answer["source_sha256"] = answer["fetch_evidence"]["source_sha256"] = answer["source"]["sha256"]
        with self.assertRaises(ValueError) as caught:
            insertion.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)
        self.assertEqual(caught.exception.code, "DISTINCT_SOURCE_PAGE_BINDINGS_REQUIRED")

    def test_one_frame_on_same_page_cannot_silently_use_other_page_source(self):
        frames = self.approved["candidate"]["frames"]
        frames[1]["source"] = copy.deepcopy(frames[-1]["source"])
        frames[1]["source_sha256"] = frames[1]["fetch_evidence"]["source_sha256"] = frames[1]["source"]["sha256"]
        with self.assertRaises(ValueError) as caught:
            insertion.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)
        self.assertEqual(caught.exception.code, "ONE_SOURCE_PER_VIEWER_PAGE_REQUIRED")

    def test_two_paths_to_same_source_bytes_are_not_two_source_pages(self):
        frames = self.approved["candidate"]["frames"]
        answer = frames[-1]
        digest = frames[0]["source"]["sha256"]
        answer["source"]["sha256"] = answer["source_sha256"] = answer["fetch_evidence"]["source_sha256"] = digest
        self.approved["source_evidence"][-1]["sha256"] = digest
        with self.assertRaises(ValueError) as caught:
            insertion.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)
        self.assertEqual(caught.exception.code, "DISTINCT_SOURCE_PAGE_BINDINGS_REQUIRED")

    def test_preserving_visible_text_does_not_allow_swapping_stable_info_ids(self):
        plan = insertion.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)
        after, receipt = insertion_fixture.synthetic_readback(self.before, self.payload)
        after["q9_info"]["data"]["id"], after["q10_info"]["data"]["id"] = (
            after["q10_info"]["data"]["id"], after["q9_info"]["data"]["id"])
        result = insertion.compare_insert_readback(plan, after, receipt, runtime_actor_hashes={
            "runtime_actor_sha256": update.text_digest("SYNTHETIC-username"),
            "runtime_user_id_sha256": update.text_digest("222")})
        self.assertFalse(result["ok"])


class MainSourcePageRisks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before, cls.approved, cls.prior = main_fixture.fixture()

    def test_valid_main_source_control(self):
        plan = main_fixture.f.make_finalize_plan(self.before, self.approved, self.prior)
        self.assertEqual(plan["approved_main_content"]["candidate"]["logical_owner"], "main")

    def reject_source_swap(self, index, source_index, code):
        approved = copy.deepcopy(self.approved)
        candidate = approved["candidate"]
        frames = candidate["frames"]
        row = frames[index]
        row["source"] = copy.deepcopy(frames[source_index]["source"])
        row["source_sha256"] = row["fetch_evidence"]["source_sha256"] = row["source"]["sha256"]
        candidate["planned_frames"] = copy.deepcopy(frames)
        with self.assertRaises(ValueError) as caught:
            main_fixture.f.make_finalize_plan(self.before, approved, self.prior)
        self.assertEqual(caught.exception.code, code)

    def test_main_answer_cannot_reuse_question_source(self):
        self.reject_source_swap(-1, 0, "DISTINCT_SOURCE_PAGE_BINDINGS_REQUIRED")

    def test_main_one_question_frame_cannot_use_answer_source(self):
        self.reject_source_swap(1, -1, "ONE_SOURCE_PER_VIEWER_PAGE_REQUIRED")


if __name__ == "__main__":
    unittest.main()
