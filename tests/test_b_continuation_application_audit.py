"""Independent real-source transition faults and external rollback version binding.

Fixed Q9 membership/reading order comes from source review, never from the
application producer's counters or its embedded before/after receipt.
"""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]

from annotation.recognition.baseline import digest
from annotation.recognition.continuation_apply import (
    apply_continuation, rollback_continuation, _graph_id,
)
from annotation.recognition.continuation_quality import audit_continuation_application
from annotation.recognition.image_regions import load_capture, subimage, rgb_hash
from replay_structure_b import run


SOURCE_IDS = ["viewer-173/ocr/" + str(i) for i in (141, 143, 145, 148, 150, 153, 155, 156)]
TARGET_IDS = {"resource-173/ocr/" + str(i) for i in range(25)}
BODY_IDS = ["viewer-173/ocr/141"] + ["resource-173/ocr/" + str(i) for i in range(9)]
TITLE_IDS = {"resource-173/ocr/25", "resource-173/ocr/26"}


def reference(value):
    return {k: value[k] for k in ("artifact_id", "revision", "content_hash")}


def replace_string(value, old, new):
    """Coordinate all current derived references, including ledger/projection."""
    if isinstance(value, str):
        return new if value == old else value
    if isinstance(value, list):
        return [replace_string(item, old, new) for item in value]
    if isinstance(value, dict):
        return {key: replace_string(item, old, new) for key, item in value.items()}
    return value


def resign(value):
    # This deliberately repairs caller-editable consistency fields. A checksum
    # is not a signature, and the independent consumer must inspect actual data.
    value["content_hash"] = digest(value["payload"])
    value["rollback_guard"]["expected_payload_hash"] = value["content_hash"]
    value["artifact_id"] = _graph_id(value)
    return value


class RealContinuationApplicationAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bundle = run(FIXTURE)
        cls.fixed_evidence = bundle["evidence.json"]
        cls.fixed_base = bundle["question-graph-source-extension.json"]
        cls.fixed_proof = bundle["continuation-proof.json"]
        cls.fixed_review = json.loads((FIXTURE / "image-region-review.json").read_text(encoding="utf-8"))
        cls.fixed_derived = apply_continuation(cls.fixed_evidence, cls.fixed_base, cls.fixed_proof,
            image_review=cls.fixed_review, capture_root=FIXTURE)

    def setUp(self):
        self.evidence = copy.deepcopy(self.fixed_evidence)
        self.base = copy.deepcopy(self.fixed_base)
        self.proof = copy.deepcopy(self.fixed_proof)
        self.review = copy.deepcopy(self.fixed_review)
        self.derived = copy.deepcopy(self.fixed_derived)
        self.issued_ref = reference(self.derived)
        self.answer_id = self.proof["payload"]["from_answer_id"]

    def answer(self, graph=None):
        return next(a for a in (graph or self.derived)["payload"]["answers"] if a["answer_id"] == self.answer_id)

    def audit(self):
        return audit_continuation_application(self.evidence, self.base, self.derived, self.proof,
            image_review=self.review, capture_root=FIXTURE)["payload"]

    def rejected(self):
        result = self.audit()
        self.assertFalse(result["accepted"], "Independent consumer accepted coordinated transition corruption")
        self.assertEqual(result["decision"], "HOLD")
        self.assertFalse(result["business_acceptance"])
        return {item["code"] for item in result["issues"]}

    def synchronize_render_receipt(self):
        answer = self.answer()
        answer["regions"] = copy.deepcopy(answer["render_regions"])
        application = self.derived["payload"]["continuation_application"]
        application["render_region_ids"] = [r["region_id"] for r in answer["render_regions"]]
        application["image_region_ids"] = [r["region_id"] for r in answer["render_regions"] if r["content_type"] == "image"]
        resign(self.derived)

    def test_real_fixed_membership_render_order_and_body_are_independent(self):
        result = self.audit()
        self.assertTrue(result["accepted"], result["issues"])
        answer, before = self.answer(), self.answer(self.base)
        self.assertEqual(before["source_line_ids"], SOURCE_IDS)
        self.assertEqual(answer["fragments"][:8], before["fragments"])
        self.assertEqual(len(answer["fragments"]), 33)
        self.assertEqual(set(answer["source_line_ids"]), set(SOURCE_IDS) | TARGET_IDS)
        self.assertEqual(answer["bbox"], before["bbox"])
        signatures = [(r["asset_id"], r["content_type"],
                       r.get("figure_number") if r["content_type"] == "image" else r["evidence_refs"][0])
                      for r in answer["render_regions"]]
        expected = [("viewer-173", "text", "viewer-173/ocr/141"),
                    ("viewer-173", "image", "3"), ("viewer-173", "image", "4")]
        expected += [("resource-173", "text", "resource-173/ocr/" + str(i)) for i in range(9)]
        expected += [("resource-173", "image", str(i)) for i in (5, 6, 7)]
        self.assertEqual(signatures, expected)
        self.assertEqual(sum(not r["render_as_separate_region"] for r in answer["fragment_representation"]), 23)
        units = {l["line_id"]: l for p in self.evidence["payload"]["pages"] for l in p["ocr_lines"]}
        expected_text = "\n".join([before["fragments"][0]["text"]] + [units[r]["text"] for r in BODY_IDS[1:]])
        self.assertEqual(answer["text"], expected_text)
        self.assertEqual(len(answer["render_regions"]), 15)
        self.assertFalse(answer["complete"])
        self.assertTrue(answer["structural_complete"])
        old_ledger = {r["line_id"]: r for r in self.base["payload"]["answer_coverage"]}
        new_ledger = {r["line_id"]: r for r in self.derived["payload"]["answer_coverage"]}
        for line_id in TITLE_IDS:
            self.assertEqual(new_ledger[line_id], old_ledger[line_id])
            self.assertEqual(new_ledger[line_id]["status"], "EXCLUDED")

    def test_coordinated_fragment_id_alias_to_an_unaffected_answer_is_rejected(self):
        old_id = self.answer()["fragments"][8]["fragment_id"]
        other = next(a for a in self.base["payload"]["answers"] if a["answer_id"] != self.answer_id)
        collision = other["fragments"][0]["fragment_id"]
        self.derived["payload"] = replace_string(self.derived["payload"], old_id, collision)
        resign(self.derived)
        self.assertIn("APPLY_GLOBAL_FRAGMENT_ID_REUSED", self.rejected())

    def test_coordinated_image_order_cannot_jump_back_to_the_source_page(self):
        renders = self.answer()["render_regions"]
        source_image = next(r for r in renders if r.get("figure_number") == "3")
        renders.remove(source_image)
        renders.append(source_image)
        self.synchronize_render_receipt()
        self.rejected()

    def test_coordinated_image_crop_cannot_replace_the_figure_with_its_caption(self):
        region = next(r for r in self.answer()["render_regions"] if r.get("figure_number") == "5")
        descriptor = next(c for c in self.review["payload"]["captures"] if c["asset_id"] == "resource-173")
        image = load_capture(FIXTURE, descriptor)
        region["bbox"] = [167, 418, 202, 441]
        region["crop_rgb_sha256"] = rgb_hash(subimage(image, descriptor, region["bbox"]))
        self.synchronize_render_receipt()
        self.rejected()

    def test_coordinated_embedded_archive_is_not_the_original_entity_authority(self):
        # A matching corruption in current graph and its mutable archive must
        # not replace the independently supplied base_graph.
        self.derived["payload"]["questions"][0]["audit_corruption"] = "changed"
        archive = self.derived["payload"]["continuation_application"]["base_graph_archive"]
        archive["payload"]["questions"][0]["audit_corruption"] = "changed"
        archive["content_hash"] = digest(archive["payload"])
        resign(self.derived)
        self.rejected()

    def test_unaffected_answer_order_is_part_of_the_preserved_graph(self):
        answers = self.derived["payload"]["answers"]
        positions = [i for i, a in enumerate(answers) if a["answer_id"] != self.answer_id][:2]
        a, b = positions
        answers[a], answers[b] = answers[b], answers[a]
        resign(self.derived)
        self.rejected()

    def test_coordinated_title_consumption_is_rejected(self):
        # Updating both allocation and cached old-owner metadata cannot make
        # the next chapter heading part of this answer.
        line_id = "resource-173/ocr/26"
        row = next(r for r in self.derived["payload"]["answer_coverage"] if r["line_id"] == line_id)
        row.update(status="CONSUMED", answer_ids=[self.answer_id])
        application = self.derived["payload"]["continuation_application"]
        application["old_line_owners"].append(copy.deepcopy(row))
        resign(self.derived)
        self.rejected()

    def test_exact_rollback_restores_every_original_entity_and_ledger(self):
        before = copy.deepcopy(self.derived)
        restored = rollback_continuation(self.evidence, self.derived, expected_graph_ref=self.issued_ref)
        self.assertEqual(restored, self.base)
        self.assertEqual(self.derived, before)
        self.assertIsNot(restored, self.base)
        with self.assertRaises(ValueError):
            rollback_continuation(self.evidence, restored, expected_graph_ref=reference(restored))

    def test_rollback_requires_an_external_reference(self):
        with self.assertRaises(TypeError):
            rollback_continuation(self.evidence, self.derived)

    def test_rollback_rejects_rehashed_and_resigned_later_local_edit(self):
        self.answer()["text"] += "\nLater local user edit"
        resign(self.derived)
        with self.assertRaises(ValueError):
            rollback_continuation(self.evidence, self.derived, expected_graph_ref=self.issued_ref)
        # Even a caller that supplies its new on-the-spot ref cannot bypass
        # comparison with the archived source/proof projection.
        with self.assertRaises(ValueError):
            rollback_continuation(self.evidence, self.derived, expected_graph_ref=reference(self.derived))

    def test_rollback_rejects_new_evidence_revision_and_new_graph_revision(self):
        changed_evidence = copy.deepcopy(self.evidence)
        changed_evidence["revision"] += 1
        with self.assertRaises(ValueError):
            rollback_continuation(changed_evidence, self.derived, expected_graph_ref=self.issued_ref)
        self.derived["revision"] += 1
        self.derived["artifact_id"] = _graph_id(self.derived)
        with self.assertRaises(ValueError):
            rollback_continuation(self.evidence, self.derived, expected_graph_ref=self.issued_ref)

    def test_double_apply_cannot_consume_the_target_prefix_again(self):
        with self.assertRaises(ValueError):
            apply_continuation(self.evidence, self.derived, self.proof,
                               image_review=self.review, capture_root=FIXTURE)


if __name__ == "__main__":
    unittest.main()
