"""Real cached candidate selection changes drafts; original records stay fixed."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from annotation.recognition.baseline import digest
from content_revision_observed import observed_inputs, observed_plan


class ObservedContentRevisionTests(unittest.TestCase):
    def setUp(self):
        from annotation.recognition import content_revision as producer
        from annotation.recognition import content_revision_quality as consumer
        self.producer, self.consumer = producer, consumer
        self.docs, self.manifest = observed_inputs()
        self.e, self.g, self.c, self.review = [self.docs[n] for n in ("evidence", "graph", "base-check", "review")]

    def apply(self, version):
        plan = observed_plan(version)
        app = self.producer.apply_content_revision(self.e, self.g, self.c, plan)
        checked = self.producer.build_content_quality(self.e, self.g, self.c, plan, app, self.review)
        self.assertTrue(self.consumer.audit_content_application(self.e, self.g, self.c, plan, app)["payload"]["accepted"])
        self.assertTrue(self.consumer.audit_content_quality(self.e, self.g, self.c, plan, app, self.review, checked)["payload"]["accepted"])
        return plan, app, checked

    def test_frozen_actual_inputs_are_bound_to_previous_published_business_outputs(self):
        previous = __import__("json").loads((ROOT / "evaluation/book-46007447-pipeline-inline.json").read_text(encoding="utf-8"))
        for value, name in ((self.e, "evidence_ref"), (self.g, "graph_ref"), (self.c, "quality_ref")):
            self.assertEqual(self.producer.reference(value), previous["final_outputs"][name])
            self.assertEqual(value["content_hash"], digest(value["payload"]))
        self.assertFalse(self.manifest["human_gold"])
        self.assertFalse(self.manifest["original_images"])
        self.assertEqual(self.manifest["new_model_calls"], 0)

    def test_real_wrong_model_final_one_is_not_dropped_when_joining_next_725(self):
        plan, app, check = self.apply(1)
        graph = app["payload"]["graph"]
        selected = next(o for o in plan["payload"]["operations"] if o["kind"] == "SELECT_INLINE")
        candidate = next(c for c in self.g["payload"]["inline_content"]["candidates"] if c["candidate_id"] == selected["candidate_id"])
        self.assertTrue(candidate["raw_latex"].endswith("=1"))
        answer = next(a for a in graph["payload"]["answers"] if a["answer_id"] == selected["target"]["answer_id"])
        self.assertIn(candidate["raw_latex"] + "725", answer["text"])
        self.assertIn("CONTENT_SELECTED_FORMULA_CLOSURE_CONFLICT", {i["code"] for i in check["payload"]["issues"]})
        self.assertEqual(check["payload"]["decision"], "HOLD")

    def test_real_revision_consumes_selected_math_and_keeps_previous_bad_plan(self):
        plan, app, check = self.apply(2)
        graph = app["payload"]["graph"]
        self.assertEqual(plan["payload"]["previous_plan_archive"], observed_plan(1))
        self.assertEqual(plan["payload"]["author"]["kind"], "MODEL_DRAFT")
        answer = next(a for a in graph["payload"]["answers"] if a["answer_id"] in graph["payload"]["content_revision"]["affected_answer_ids"])
        self.assertIn("AB²=10²+25²=725", answer["text"])
        self.assertIn("625=25^{2}", answer["text"])
        self.assertNotIn("\\sqrt{625}", answer["text"])
        self.assertFalse(answer["transcription_verified"])
        self.assertFalse(check["payload"]["business_acceptance"])
        self.assertEqual(len(graph["payload"]["questions"]), 34)
        self.assertEqual(len(graph["payload"]["answers"]), 66)

    def test_raw_fragments_ledger_images_and_all_inline_variants_are_unchanged(self):
        before = copy.deepcopy(self.docs)
        _, app, _ = self.apply(2)
        graph = app["payload"]["graph"]
        self.assertEqual(self.docs, before)
        self.assertEqual(graph["payload"]["answer_coverage"], self.g["payload"]["answer_coverage"])
        self.assertEqual(graph["payload"]["inline_content"], self.g["payload"]["inline_content"])
        images = lambda a: [r for r in a.get("render_regions", []) if r["content_type"] == "image"]
        for original, current in zip(self.g["payload"]["answers"], graph["payload"]["answers"]):
            self.assertEqual(current["fragments"], original["fragments"])
            self.assertEqual(images(current), images(original))
        self.assertEqual(sum(len(images(a)) for a in graph["payload"]["answers"]), 5)
        self.assertEqual(sum(r["status"] == "UNASSIGNED" for r in graph["payload"]["answer_coverage"]), 19)

    def test_new_text_does_not_invent_question_match_for_reflection_q9(self):
        _, app, check = self.apply(2)
        graph = app["payload"]["graph"]
        changed = set(graph["payload"]["content_revision"]["affected_answer_ids"])
        for q in graph["payload"]["questions"]:
            self.assertTrue(changed.isdisjoint(q["candidate_answer_ids"]))
        self.assertEqual(graph["payload"]["content_revision"]["affected_question_ids"], [])
        self.assertEqual(check["payload"]["graph_ref"], self.producer.reference(graph))
        self.assertNotEqual(check["payload"]["graph_ref"], self.producer.reference(self.g))

    def test_observed_replay_never_imports_models_or_uses_network(self):
        with patch.dict(sys.modules, {"onnxruntime": None, "rapidocr_onnxruntime": None,
                "rapid_latex_ocr": None, "torch": None, "paddle": None}), \
                patch("socket.socket.connect", side_effect=AssertionError("network forbidden")), \
                patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
            _, app, check = self.apply(2)
        self.assertEqual(app["payload"]["new_model_calls"], 0)
        self.assertEqual(check["payload"]["platform_actions"], [])

    def test_explicit_external_version_guards_rollback_of_real_materialized_graph(self):
        _, app, _ = self.apply(2)
        graph = app["payload"]["graph"]
        pinned = self.producer.reference(graph)
        self.assertEqual(self.producer.rollback_content_revision(self.e, graph, expected_graph_ref=pinned), self.g)
        changed = copy.deepcopy(graph)
        changed["payload"]["answers"][0]["text"] += "later edit"
        changed["content_hash"] = digest(changed["payload"])
        with self.assertRaises(ValueError):
            self.producer.rollback_content_revision(self.e, changed, expected_graph_ref=pinned)


if __name__ == "__main__":
    unittest.main()
