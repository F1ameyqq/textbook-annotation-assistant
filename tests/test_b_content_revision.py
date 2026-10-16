"""Actual draft text reconstruction, immutable source and fresh rule checks."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tests")]
from annotation.recognition.baseline import digest
from annotation.recognition import content_revision as cr
from content_revision_fixture import make_content_fixture, edit_target

AUTHOR = {"kind": "SYNTHETIC_TEST", "id": "test-author", "note": "Generated data and explicit test-only edits"}


def rehash(value):
    value["content_hash"] = digest(value["payload"])
    return value


def resign_plan(plan):
    rehash(plan)
    plan["artifact_id"] = "content-revision-plan-"+digest({k: v for k, v in plan.items() if k not in {"artifact_id", "content_hash"}})[:24]
    return plan


def answer(graph, number):
    return next(a for a in graph["payload"]["answers"] if a["printed_number"] == number)


def edit(graph, number, replacement, *, role="answer", span=None, operation_id="edit"):
    a = answer(graph, number)
    return {"operation_id": operation_id, "kind": "EDIT_TEXT", "target": edit_target(graph, answer_id=a["answer_id"], role=role, span=span),
            "replacement": replacement, "format": "plain", "reason": "SYNTHETIC_TEST explicit development correction"}


def coherent_graph_check(graph, check, change):
    """Rebind a deliberately invalid synthetic upstream state, not CPU gold."""
    g = copy.deepcopy(graph)
    change(g)
    archive = g["payload"]["inline_content"]["base_graph_archive"]
    archive["payload"] = {k: copy.deepcopy(v) for k, v in g["payload"].items() if k != "inline_content"}
    rehash(archive); rehash(g)
    c = copy.deepcopy(check); c["input_refs"][1] = cr.reference(g); c["payload"]["graph_ref"] = cr.reference(g); rehash(c)
    return g, c


class ContentRevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.d = make_content_fixture(self.tmp.name)
        self.e, self.g, self.c = [self.d[k] for k in ("evidence", "graph", "check")]

    def plan(self, operations, *, previous=None, check=None, author=None):
        return cr.make_revision_plan(self.e, self.g, check or self.c, operations, author or AUTHOR, previous_plan=previous)

    def apply(self, plan, *, check=None):
        return cr.apply_content_revision(self.e, self.g, check or self.c, plan)

    def test_variable_length_disjoint_edits_rebuild_answer_and_analysis_without_offset_drift(self):
        first = edit(self.g, "9", "CD^{2}", span=[2, 4], operation_id="formula")
        first["format"] = "latex"
        ops = [first, edit(self.g, "9", ":=", span=[4, 5], operation_id="operator"),
               edit(self.g, "9", "另证", role="explanation", span=[0, 2], operation_id="analysis")]
        p = self.plan(ops); app = self.apply(p); a = answer(app["payload"]["graph"], "9")
        self.assertEqual(a["text"], "解：CD^{2}:=\n25")
        self.assertEqual(a["explanation_text"], "另证定边长\n继续验证")
        self.assertEqual(a["fragments"], answer(self.g, "9")["fragments"])
        self.assertEqual(len(a["content_fragments"]), 4)
        cf = a["content_fragments"][0]
        self.assertEqual([(x["source_fragment_span"], x["output_span"], x["text"]) for x in cf["pieces"]],
                         [([0, 2], [0, 2], "解："), ([2, 4], [2, 8], "CD^{2}"), ([4, 5], [8, 10], ":=")])
        self.assertFalse(a["complete"]); self.assertFalse(a["transcription_verified"])

    def test_explicit_spaces_and_newlines_are_not_normalized(self):
        p = self.plan([edit(self.g, "1", " A\nB ")])
        a = answer(self.apply(p)["payload"]["graph"], "1")
        self.assertEqual(a["text"], " A\nB ")
        self.assertEqual(a["content_fragments"][0]["pieces"][0]["text"], " A\nB ")

    def test_non_bmp_source_and_replacements_use_unicode_code_point_offsets(self):
        with tempfile.TemporaryDirectory() as folder:
            d = make_content_fixture(folder, scalar_text="𝑥+𝛼")
            e, g, c = [d[k] for k in ("evidence", "graph", "check")]
            ops = [edit(g, "4", "𝑦²", span=[0, 1], operation_id="first-symbol"),
                   edit(g, "4", "𝛽+1", span=[2, 3], operation_id="last-symbol")]
            p = cr.make_revision_plan(e, g, c, ops, AUTHOR)
            derived = cr.apply_content_revision(e, g, c, p)["payload"]["graph"]
            a = answer(derived, "4")
            self.assertEqual(a["text"], "𝑦²+𝛽+1")
            pieces = a["content_fragments"][0]["pieces"]
            self.assertEqual([(x["source_fragment_span"], x["output_span"], x["text"]) for x in pieces],
                             [([0, 1], [0, 2], "𝑦²"), ([1, 2], [2, 3], "+"), ([2, 3], [3, 6], "𝛽+1")])
            for piece in pieces:
                self.assertEqual(a["text"][slice(*piece["output_span"])], piece["text"])
            self.assertEqual(a["fragments"], answer(g, "4")["fragments"])

    def test_boolean_revision_cannot_alias_integer_current_or_observation_refs(self):
        c = copy.deepcopy(self.c)
        c["payload"]["graph_ref"]["revision"] = True
        c["input_refs"][1]["revision"] = True
        rehash(c)
        with self.assertRaises(ValueError):
            cr.make_revision_plan(self.e, self.g, c, [], AUTHOR)
        def change(g):
            g["payload"]["inline_content"]["candidates"][0]["observation_ref"]["revision"] = True
        g, c = coherent_graph_check(self.g, self.c, change)
        candidate = g["payload"]["inline_content"]["candidates"][0]
        operation = {"operation_id": "bool-observation", "kind": "SELECT_INLINE",
            "target": edit_target(g, answer_id=answer(g, "9")["answer_id"], span=[2, 5]),
            "candidate_id": candidate["candidate_id"], "call_id": candidate["call_id"],
            "unit_id": candidate["unit_bindings"][0]["unit_id"], "reason": "Reject JSON true as revision 1"}
        with self.assertRaises(ValueError):
            cr.make_revision_plan(self.e, g, c, [operation], AUTHOR)

    def test_question_type_is_recomputed_and_every_answer_dependent_question_is_affected(self):
        p = self.plan([edit(self.g, "1", "AB", operation_id="choice"), edit(self.g, "4", "13", operation_id="scalar")])
        g = self.apply(p)["payload"]["graph"]
        q1 = next(q for q in g["payload"]["questions"] if q["printed_number"] == "1")
        self.assertEqual(q1["type_candidate"]["selection_mode"], "multiple")
        self.assertEqual(len(g["payload"]["content_revision"]["affected_question_ids"]), 2)
        for before, current in zip(self.g["payload"]["questions"], g["payload"]["questions"]):
            self.assertEqual(before["text"], current["text"]); self.assertEqual(before["fragments"], current["fragments"])
        self.assertFalse(any(q["printed_number"] == "9" for q in g["payload"]["questions"]))

    def test_select_wrong_model_one_and_join_preserves_the_wrong_one_and_diagnostic(self):
        inline = self.g["payload"]["inline_content"]
        proposal = inline["continuity"]["payload"]["proposals"][0]
        fid = proposal["bindings"][0]["fragments"][0]["fragment_id"]
        target = edit_target(self.g, answer_id=answer(self.g, "9")["answer_id"], fragment_id=fid, span=[2, 5])
        candidate = next(c for c in inline["candidates"] if c["unit_bindings"][0]["line_id"] == "answer/ocr/2")
        selected = {"operation_id": "select-wrong-one", "kind": "SELECT_INLINE", "target": target,
            "candidate_id": candidate["candidate_id"], "call_id": candidate["call_id"], "unit_id": candidate["unit_bindings"][0]["unit_id"],
            "reason": "SYNTHETIC_TEST intentionally retain known-wrong model closure"}
        join = {"operation_id": "join", "kind": "JOIN_RAW_WRAP", "proposal_id": proposal["proposal_id"], "reason": "SYNTHETIC_TEST explicit raw wrap"}
        p = self.plan([selected, join]); app = self.apply(p)
        a = answer(app["payload"]["graph"], "9")
        self.assertEqual(a["text"], "解：AB=125")
        self.assertEqual(a["content_fragments"][0]["pieces"][-1]["text"], candidate["raw_latex"])
        q = cr.build_content_quality(self.e, self.g, self.c, p, app, self.d["review"])
        self.assertIn("CONTENT_SELECTED_FORMULA_CLOSURE_CONFLICT", [i["code"] for i in q["payload"]["issues"]])
        self.assertEqual(q["payload"]["decision"], "HOLD")
        self.assertEqual(self.g["payload"]["inline_content"], app["payload"]["graph"]["payload"]["inline_content"])

    def test_parser_unsupported_raw_candidate_can_only_be_an_explicit_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            d = make_content_fixture(directory, formula_outputs=(r"\unknown{x}",))
            g, c = d["graph"], d["check"]
            candidate = next(x for x in g["payload"]["inline_content"]["candidates"] if x["unit_bindings"][0]["line_id"] == "answer/ocr/2")
            operation = {"operation_id": "unsupported", "kind": "SELECT_INLINE", "target": edit_target(g, answer_id=answer(g, "9")["answer_id"]),
                "candidate_id": candidate["candidate_id"], "call_id": candidate["call_id"], "unit_id": candidate["unit_bindings"][0]["unit_id"], "reason": "explicit unsupported draft"}
            p = cr.make_revision_plan(d["evidence"], g, c, [operation], AUTHOR)
            with patch("annotation.recognition.formula_syntax.parse_inline_formula_latex", side_effect=AssertionError("do not reparse")):
                app = cr.apply_content_revision(d["evidence"], g, c, p)
                q = cr.build_content_quality(d["evidence"], g, c, p, app, d["review"])
            self.assertTrue(answer(app["payload"]["graph"], "9")["text"].startswith(r"\unknown{x}"))
            self.assertIn("CONTENT_SELECTED_FORMULA_SYNTAX_UNSUPPORTED", [x["code"] for x in q["payload"]["issues"]])

    def test_join_only_removes_separator_and_never_merges_regions_or_changes_glyphs(self):
        proposal = self.g["payload"]["inline_content"]["continuity"]["payload"]["proposals"][0]
        p = self.plan([{"operation_id": "join", "kind": "JOIN_RAW_WRAP", "proposal_id": proposal["proposal_id"], "reason": "raw adjacency"}])
        g = self.apply(p)["payload"]["graph"]
        a = answer(g, "9")
        self.assertEqual(a["text"], "解：AB=25")
        self.assertEqual([f["text"] for f in a["content_fragments"]], ["解：AB=", "25", "先确定边长", "继续验证"])
        self.assertEqual(a["regions"], answer(self.g, "9")["regions"])
        self.assertEqual(a["content_projection"]["separators"][0]["separator"], "")

    def test_q4_ratio_to_thirteen_rechecks_scalar_and_only_exact_prior_issue_is_superseded(self):
        with tempfile.TemporaryDirectory() as directory:
            d = make_content_fixture(directory, scalar_text="1:3")
            e, g, c = d["evidence"], d["graph"], copy.deepcopy(d["check"])
            original = next(i for i in c["payload"]["issues"] if i["code"] == "ANSWER_SCALAR_FORMAT")
            other = {**copy.deepcopy(original), "issue_id": "synthetic-unrelated-same-code", "detail": {"different_remaining_risk": True}}
            c["payload"]["issues"].append(other); rehash(c)
            p = cr.make_revision_plan(e, g, c, [edit(g, "4", "13")], AUTHOR)
            app = cr.apply_content_revision(e, g, c, p)
            q = cr.build_content_quality(e, g, c, p, app, d["review"])["payload"]
            self.assertEqual(answer(app["payload"]["graph"], "4")["text"], "13")
            self.assertFalse(any(f["code"].startswith("ANSWER_SCALAR") or f["code"] == "ANSWER_VALUE_MISMATCH" for f in q["fresh_question_findings"]))
            disposed = next(r for r in q["rule_dispositions"] if r["prior_issue"]["issue_id"] == original["issue_id"])
            self.assertEqual(disposed["current_finding_issue_ids"], [])
            carried = next(i for i in q["issues"] if i["issue_id"] == other["issue_id"])
            self.assertEqual(carried["detail"], other["detail"])
            self.assertEqual(carried["origin_check_ref"], cr.reference(c))
            self.assertEqual(q["base_check_archive"], c)

    def test_lineage_is_a_complete_snapshot_and_empty_revision_reverts_previous_edits(self):
        p1 = self.plan([edit(self.g, "1", "AB")])
        p2 = self.plan([], previous=p1)
        self.assertEqual(p2["revision"], 2); self.assertEqual(p2["payload"]["previous_plan_archive"], p1)
        g = self.apply(p2)["payload"]["graph"]
        self.assertEqual(answer(g, "1")["text"], "A")
        self.assertEqual(g["payload"]["content_revision"]["affected_answer_ids"], [])
        changed_check = copy.deepcopy(self.c); changed_check["payload"]["revision_note"] = "explicit review-only rebase"; rehash(changed_check)
        p3 = self.plan([], previous=p2, check=changed_check)
        self.assertEqual(p3["payload"]["previous_plan_archive"]["payload"]["base_check_ref"], cr.reference(self.c))
        self.assertEqual(p3["payload"]["base_check_ref"], cr.reference(changed_check))

    def test_external_version_and_exact_projection_are_both_required_for_rollback(self):
        p = self.plan([edit(self.g, "1", "AB")]); derived = self.apply(p)["payload"]["graph"]
        self.assertEqual(cr.rollback_content_revision(self.e, derived, expected_graph_ref=cr.reference(derived)), self.g)
        changed = copy.deepcopy(derived); changed["payload"]["later_edit"] = True; rehash(changed)
        changed["artifact_id"] = "content-graph-"+digest({k: v for k, v in changed.items() if k not in {"artifact_id", "content_hash"}})[:24]
        with self.assertRaisesRegex(ValueError, "retained graph"):
            cr.rollback_content_revision(self.e, changed, expected_graph_ref=cr.reference(derived))
        with self.assertRaisesRegex(ValueError, "later graph edits"):
            cr.rollback_content_revision(self.e, changed, expected_graph_ref=cr.reference(changed))

    def test_stale_refs_unknown_approval_fields_boolean_flags_and_bad_lineage_are_rejected(self):
        base = self.plan([edit(self.g, "1", "AB")])
        for fault in ("ref", "approval", "numeric_false", "lineage"):
            value = copy.deepcopy(base)
            if fault == "ref": value["payload"]["graph_ref"]["artifact_id"] = "stale"
            elif fault == "approval": value["payload"]["human_verified"] = True
            elif fault == "numeric_false": value["payload"]["complete"] = 0
            else: value["revision"] = 2; value["payload"]["previous_plan_archive"] = {"invalid": "old"}
            resign_plan(value)
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                cr.validate_revision_plan(value, self.e, self.g, self.c)

    def test_ctc_span_confusion_overlap_role_and_missing_explanation_are_rejected(self):
        a = answer(self.g, "9")
        target = edit_target(self.g, answer_id=a["answer_id"])
        ctc = {**target, "fragment_span": [0, 3], "expected_text": "AB="}
        with self.assertRaisesRegex(ValueError, "original fragment substring"):
            self.plan([{**edit(self.g, "9", "draft"), "target": ctc}])
        one = edit(self.g, "9", "x", span=[0, 3], operation_id="a")
        two = edit(self.g, "9", "y", span=[2, 5], operation_id="b")
        with self.assertRaisesRegex(ValueError, "overlapping"):
            self.plan([one, two])
        wrong_role = edit(self.g, "1", "not an explanation"); wrong_role["target"]["role"] = "explanation"
        with self.assertRaisesRegex(ValueError, "declared role"):
            self.plan([wrong_role])

    def test_coherently_rehashed_graph_cannot_forge_parent_raw_geometry_or_ledger(self):
        for fault in ("parent", "raw", "bbox", "ledger"):
            def change(g):
                a = answer(g, "1"); f = a["fragments"][0]
                if fault == "parent": f["parent_line_id"] = "answer/ocr/1"
                elif fault == "raw": f["raw_text"] += "fake"
                elif fault == "bbox": f["bbox"][0] += 1
                else:
                    row = next(r for r in g["payload"]["answer_coverage"] if r["line_id"] == f["parent_line_id"])
                    row["allocations"][0]["answer_id"] = "wrong-owner"
            g, c = coherent_graph_check(self.g, self.c, change)
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                cr.make_revision_plan(self.e, g, c, [edit(g, "1", "AB")], AUTHOR)

    def test_selected_candidate_must_bind_same_current_row_not_another_unit_or_call(self):
        inline = self.g["payload"]["inline_content"]
        c = next(c for c in inline["candidates"] if c["unit_bindings"][0]["line_id"] == "answer/ocr/2")
        op = {"operation_id": "pick", "kind": "SELECT_INLINE", "target": edit(self.g, "9", "unused")["target"],
              "candidate_id": c["candidate_id"], "call_id": c["call_id"], "unit_id": c["unit_bindings"][0]["unit_id"], "reason": "synthetic"}
        op["unit_id"] = next(u["unit_id"] for u in inline["units"] if u["line_id"] == "answer/ocr/3")
        with self.assertRaisesRegex(ValueError, "source row"):
            self.plan([op])

    def test_typed_body_changes_preserve_all_source_fragments_images_and_diagnostic_text(self):
        with tempfile.TemporaryDirectory() as directory:
            d = make_content_fixture(directory, with_images=True)
            e, g, c = d["evidence"], d["graph"], d["check"]
            target = edit_target(g)
            op = {"operation_id": "body", "kind": "EDIT_TEXT", "target": target, "replacement": "MODEL draft body", "format": "plain", "reason": "synthetic body correction"}
            p = cr.make_revision_plan(e, g, c, [op], AUTHOR); app = cr.apply_content_revision(e, g, c, p)
            old = next(a for a in g["payload"]["answers"] if a["answer_id"] == target["answer_id"])
            new = next(a for a in app["payload"]["graph"]["payload"]["answers"] if a["answer_id"] == target["answer_id"])
            self.assertEqual([r for r in old["render_regions"] if r["content_type"] == "image"], [r for r in new["render_regions"] if r["content_type"] == "image"])
            self.assertEqual(old["fragments"], new["fragments"])
            self.assertEqual(new["regions"], new["render_regions"])
            self.assertIn("MODEL draft body", new["text"])
            self.assertTrue(any(r.get("text") == "MODEL draft body" for r in new["render_regions"]))
            diagnostic = next(f for f in old["fragments"] if f.get("represented_by_image_region") is not None)
            bad = {**op, "target": {"answer_id": old["answer_id"], "fragment_id": diagnostic["fragment_id"], "role": diagnostic["role"],
                    "fragment_span": [0, len(diagnostic["text"])], "expected_text": diagnostic["text"]}}
            with self.assertRaisesRegex(ValueError, "visible nonstructural"):
                cr.make_revision_plan(e, g, c, [bad], AUTHOR)

    def test_false_join_across_image_barrier_and_duplicate_join_are_rejected(self):
        proposal = self.g["payload"]["inline_content"]["continuity"]["payload"]["proposals"][0]
        join = {"operation_id": "join", "kind": "JOIN_RAW_WRAP", "proposal_id": proposal["proposal_id"], "reason": "test"}
        with self.assertRaisesRegex(ValueError, "duplicate join"):
            self.plan([join, {**join, "operation_id": "again"}])
        def image_between(g):
            a = answer(g, "9")
            a["render_regions"] = [{"region_id": "synthetic-text-"+str(i), "content_type": "text", "role": f["role"],
                "asset_id": f["asset_id"], "source_fragment_ids": [f["fragment_id"]], "text": f["text"], "bbox": f["bbox"]} for i, f in enumerate(a["fragments"])]
            a["render_regions"].insert(1, {"region_id": "synthetic-image-barrier", "content_type": "image", "asset_id": "answer", "bbox": [10, 70, 30, 80]})
        g, c = coherent_graph_check(self.g, self.c, image_between)
        with self.assertRaisesRegex(ValueError, "image/role barrier"):
            cr.make_revision_plan(self.e, g, c, [join], AUTHOR)

    def test_deterministic_no_clock_nonmutation_and_model_free_replay(self):
        before = digest([self.e, self.g, self.c])
        author = {"kind": "HUMAN_DRAFT", "id": "synthetic-human-label", "note": "Label is not human verification evidence"}
        with patch.dict(sys.modules, {"rapidocr_onnxruntime": None, "onnxruntime": None, "rapid_latex_ocr": None}), \
             patch("socket.socket", side_effect=AssertionError("no network")):
            p = self.plan([edit(self.g, "1", "AB")], author=author)
            self.assertEqual(p, self.plan([edit(self.g, "1", "AB")], author=author))
            app = self.apply(p)
            checked = cr.build_content_quality(self.e, self.g, self.c, p, app, self.d["review"])
            self.assertEqual(cr.rollback_content_revision(self.e, app["payload"]["graph"], expected_graph_ref=cr.reference(app["payload"]["graph"])), self.g)
        self.assertEqual(before, digest([self.e, self.g, self.c]))
        for value in (p, app, app["payload"]["graph"], checked):
            self.assertNotIn("created_at", value)
            self.assertEqual(value["payload"]["decision"], "HOLD")
            self.assertIs(value["payload"]["complete"], False)
            self.assertIs(value["payload"]["transcription_verified"], False)
            self.assertIs(value["payload"]["business_acceptance"], False)
            self.assertEqual(value["payload"]["platform_actions"], [])


if __name__ == "__main__": unittest.main()
