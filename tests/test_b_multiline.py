"""Multiline answer regressions: real OCR provenance and synthetic edge cases.

The real expectations below were transcribed from the committed raw OCR fixture,
independently of the assembler. They check spatial preservation, not mathematical
correctness or held-out accuracy. Synthetic cases are labelled separately.
"""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path.insert(0, str(ROOT / "src"))

from annotation.recognition.baseline import digest
from annotation.recognition.answer_assembly import assemble_answers
from annotation.recognition.answer_quality import audit_answers
from annotation.recognition.offline import assemble, quality_check


def read(name):
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def make_id(role, anchor):
    return role + "-" + digest([role, anchor])[:24]


def raw_ref(value):
    return value.split("/detail/", 1)[0]


def source_lines(answer):
    """Use recorded provenance, never rerun the parser to derive expectations."""
    refs = []
    for fragment in answer["fragments"]:
        parent = fragment.get("parent_line_id")
        if parent:
            refs.append(parent)
        else:
            refs.extend(raw_ref(r) for r in fragment["evidence_refs"])
    return refs


def synthetic_evidence(rows, windows=None):
    """Build explicit synthetic OCR input; no image OCR or website is called.

    rows: text, y, optional column, optional window index, optional section path.
    Every supplied row has an independently chosen source line ID.
    """
    scope = ["Synthetic chapter", "Lesson A"]
    windows = windows or [{"column": 0, "y_range": [100, 1500], "path": scope}]
    lines = []
    for index, row in enumerate(rows):
        text, y, *rest = row
        column = rest[0] if rest else 0
        window = rest[1] if len(rest) > 1 else 0
        path = rest[2] if len(rest) > 2 else windows[window]["path"]
        x = 59 if column == 0 else 610
        lines.append({"line_id": "synthetic/ocr/" + str(index),
                      "text": text, "score": .99,
                      "bbox": [x, y, x + 460, y + 18],
                      "location": {"column": column, "window_index": window,
                                   "section_path": path}})
    page = {"asset_id": "synthetic", "source": {"asset_id": "synthetic",
             "width": 1148, "height": 1621, "sha256": "a" * 64},
            "page_role": "answer", "layout": {"mode": "two_columns", "cut_x": 574},
            "ocr_lines": lines, "answer_detail_lines": [], "unscoped_line_ids": []}
    payload = {"pages": [page], "context": {"pages": {
        "synthetic": {"role": "answer", "windows": windows}}}}
    return {"schema_version": "b-evidence-trial/0.2", "artifact_id": "synthetic-evidence",
            "revision": 1, "book_id": "synthetic-book", "scope_id": "synthetic-scope",
            "run_id": "synthetic-run", "content_hash": digest(payload), "payload": payload}


class RealMultilineRegression(unittest.TestCase):
    """Observed sample facts, retaining the original OCR faults as evidence."""

    @classmethod
    def setUpClass(cls):
        cls.evidence = read("ocr-evidence.json")
        cls.answers, cls.issues, cls.coverage = assemble_answers(cls.evidence, make_id)
        cls.windows = cls.evidence["payload"]["context"]["pages"]["viewer-173"]["windows"]

    def answer(self, window, number):
        candidates = [a for a in self.answers if a["section_path"] == self.windows[window]["path"]
                      and a["printed_number"] == str(number)]
        self.assertEqual(len(candidates), 1, (window, number, candidates))
        return candidates[0]

    def assert_preserved(self, answer, numbers):
        actual = source_lines(answer)
        expected = ["viewer-173/ocr/" + str(n) for n in numbers]
        for ref in expected:
            self.assertEqual(actual.count(ref), 1, (ref, actual))
        self.assertFalse(answer["transcription_verified"])
        for fragment in answer["fragments"]:
            self.assertTrue(fragment["evidence_refs"])
            self.assertEqual(fragment["asset_id"], "viewer-173")
            self.assertEqual(fragment["section_path"], answer["section_path"])

    def test_real_lesson1_q6_keeps_wrapped_answer_to_last_word(self):
        a = self.answer(0, 6)
        self.assert_preserved(a, [12, 14, 18])
        self.assertIn("该电视机", a["text"])
        self.assertIn("寸的", a["text"])
        self.assertNotIn("viewer-173/ocr/19", source_lines(a))
        self.assertEqual(a["assembly_status"], "BOUNDED")
        self.assertFalse(a["explanation_present"])
        self.assertEqual(a["explanation_text"], "")

    def test_real_lesson1_q15_preserves_fraction_atoms_and_final_result(self):
        a = self.answer(0, 15)
        self.assert_preserved(a, [27, 28, 29, 32, 33, 34, 35, 36, 37, 38,
                                  40, 41, 42, 43, 45])
        self.assertIn("这块草坪", a["text"])
        self.assertIn("234", a["text"])
        self.assertNotIn("viewer-173/ocr/47", source_lines(a))
        self.assertNotIn("viewer-173/ocr/48", source_lines(a))
        self.assertFalse(a["explanation_present"])

    def test_real_lesson1_q16_keeps_formula_fragments_without_claiming_verification(self):
        a = self.answer(0, 16)
        self.assert_preserved(a, [48, 51, 52, 53, 57, 58, 60, 63, 64, 65, 66, 68])
        self.assertIn("的面积为S", a["text"])
        self.assertNotIn("viewer-173/ocr/75", source_lines(a))
        self.assertIn(a["assembly_status"], {"OPEN", "AMBIGUOUS"})
        self.assertFalse(a["complete"])

    def test_real_lesson2_q5_stops_at_tier_and_keeps_full_conclusion(self):
        a = self.answer(1, 5)
        self.assert_preserved(a, [81, 83, 84])
        self.assertIn("两艘船相距52km", a["text"])
        self.assertNotIn("viewer-173/ocr/85", source_lines(a))
        self.assertNotIn("viewer-173/ocr/88", source_lines(a))
        self.assertEqual(a["assembly_status"], "BOUNDED")

    def test_real_lesson2_q8_decimal_4_point_1_is_continuation(self):
        a = self.answer(1, 8)
        self.assert_preserved(a, [90, 91, 94, 97])
        self.assertIn("4.1=16.81", a["text"])
        self.assertIn("卡车不能通过", a["text"])
        self.assertFalse(any(candidate["printed_number"] == "4"
                             and "上题中的卡车" in candidate["text"] for candidate in self.answers))
        self.assertNotIn("viewer-173/ocr/102", source_lines(a))

    def test_real_unit2_q15_crosses_column_using_separate_regions(self):
        a = self.answer(3, 15)
        self.assert_preserved(a, [154, 2, 3, 5, 7, 9])
        self.assertNotIn("viewer-173/ocr/11", source_lines(a))
        self.assertNotIn("viewer-173/ocr/13", source_lines(a))
        self.assertEqual({f["column"] for f in a["fragments"]}, {0, 1})
        self.assertTrue(a["regions"])
        for region in a["regions"]:
            self.assertFalse(region["bbox"][0] < 574 < region["bbox"][2])
        self.assertIn("角三角形", a["text"])

    def test_real_repeated_one_stays_scoped_to_its_own_lesson(self):
        first, second, unit2 = self.answer(0, 1), self.answer(1, 1), self.answer(3, 1)
        self.assertEqual(first["text"], "D")
        self.assertEqual(unit2["text"], "C")
        self.assertIn("(1)", second["text"].replace("（", "(").replace("）", ")"))
        self.assertEqual(len({a["answer_id"] for a in (first, second, unit2)}), 3)
        self.assertNotEqual(first["section_path"], second["section_path"])

    def test_real_dense_row_allocates_distinct_tokens_instead_of_copying_whole_row(self):
        ledger = [row for row in self.coverage if row["line_id"] == "viewer-173/ocr/10"]
        self.assertEqual(len(ledger), 1)
        row = ledger[0]
        self.assertEqual(row["status"], "CONSUMED")
        expected_ids = {self.answer(0, number)["answer_id"] for number in range(1, 6)}
        self.assertEqual(set(row["answer_ids"]), expected_ids)
        allocations = row["allocations"]
        assigned_refs = [ref for item in allocations for ref in item["evidence_refs"]]
        self.assertEqual(len(assigned_refs), len(set(assigned_refs)))
        self.assertTrue(all("/detail/" in ref for ref in assigned_refs))

    def test_real_input_is_immutable_and_ledger_accounts_for_every_raw_answer_line(self):
        evidence = read("ocr-evidence.json")
        original = copy.deepcopy(evidence)
        _, _, coverage = assemble_answers(evidence, make_id)
        self.assertEqual(evidence, original)
        expected = [line["line_id"] for page in original["payload"]["pages"]
                    if page["page_role"] == "answer" for line in page["ocr_lines"]]
        self.assertCountEqual([row["line_id"] for row in coverage], expected)
        self.assertEqual(len(coverage), len(expected))


class SyntheticMultilineRegression(unittest.TestCase):
    """Constructed layout and role cases; these are not real book observations."""

    def assemble(self, rows, windows=None):
        return assemble_answers(synthetic_evidence(rows, windows), make_id)

    def test_explicit_answer_and_explanation_are_separate_multiline_roles(self):
        answers, _, _ = self.assemble([
            ("1.答案：13", 120), ("解析：由勾股定理可得", 140),
            ("斜边长为13，故得答案。", 160), ("2.答案：D", 180)])
        a = next(a for a in answers if a["printed_number"] == "1")
        self.assertEqual(a["text"], "13")
        self.assertTrue(a["explanation_present"])
        self.assertIn("由勾股定理可得", a["explanation_text"])
        self.assertIn("斜边长为13", a["explanation_text"])
        self.assertEqual([f["role"] for f in a["fragments"]],
                         ["answer", "explanation", "explanation"])
        self.assertEqual(a["assembly_status"], "BOUNDED")

    def test_solution_and_alternative_method_do_not_fabricate_explanation(self):
        answers, _, _ = self.assemble([
            ("1.解：第一种方法。", 120), ("解法二：另一种方法。", 140),
            ("答：结果为13。", 160), ("2.D", 180)])
        a = next(a for a in answers if a["printed_number"] == "1")
        self.assertIn("解法二", a["text"])
        self.assertIn("答：结果为13", a["text"])
        self.assertTrue(all(f["role"] == "answer" for f in a["fragments"]))
        self.assertFalse(a["explanation_present"])
        self.assertEqual(a["explanation_text"], "")

    def test_inline_explicit_roles_keep_disjoint_spans_and_unresolved_geometry(self):
        original = "1.答案：13 解析：由勾股定理可得。"
        evidence = synthetic_evidence([(original, 120), ("2.D", 145)])
        answers, issues, coverage = assemble_answers(evidence, make_id)
        a = next(a for a in answers if a["printed_number"] == "1")
        self.assertEqual(a["text"], "13")
        self.assertEqual(a["explanation_text"], "由勾股定理可得。")
        self.assertEqual(a["assembly_status"], "OPEN")
        self.assertFalse(a["complete"])
        self.assertIn("ANSWER_ROLE_REGIONS_UNSPLIT", {item["code"] for item in issues})
        fragments = a["fragments"]
        self.assertEqual([f["role"] for f in fragments], ["answer", "explanation"])
        self.assertEqual(fragments[0]["bbox"], fragments[1]["bbox"])
        self.assertLessEqual(fragments[0]["text_span"][1], fragments[1]["text_span"][0])
        for fragment in fragments:
            self.assertEqual(fragment["raw_text"], original)
            lo, hi = fragment["text_span"]
            self.assertEqual(fragment["text"], original[lo:hi])
        findings, _ = audit_answers(evidence, {"payload": {"answers": answers,
                                        "answer_coverage": coverage}}, {})
        self.assertNotIn("ANSWER_EVIDENCE_REUSED", {item["code"] for item in findings})

    def test_explicit_detailed_explanation_marker_is_consistent_with_checker(self):
        evidence = synthetic_evidence([
            ("1.答案：13", 120), ("详解：先计算两条直角边。", 140),
            ("再应用勾股定理。", 160), ("2.D", 180)])
        answers, _, coverage = assemble_answers(evidence, make_id)
        a = next(a for a in answers if a["printed_number"] == "1")
        self.assertTrue(a["explanation_present"])
        self.assertIn("先计算两条直角边", a["explanation_text"])
        findings, _ = audit_answers(evidence, {"payload": {"answers": answers,
                                        "answer_coverage": coverage}}, {})
        self.assertNotIn("EXPLANATION_WITHOUT_MARKER", {item["code"] for item in findings})

    def test_forced_explanation_cannot_use_analysis_word_without_explicit_label(self):
        evidence = synthetic_evidence([
            ("1.解：分析如下，结果为13。", 120), ("2.D", 145)])
        answers, _, coverage = assemble_answers(evidence, make_id)
        a = next(a for a in answers if a["printed_number"] == "1")
        self.assertFalse(a["explanation_present"])
        # Inject a role error while keeping aggregate text and ledger coherent.
        # Merely mentioning 分析 inside a worked answer cannot authorize an E.
        a["fragments"][0]["role"] = "explanation"
        a["regions"][0]["role"] = "explanation"
        a["explanation_present"], a["explanation_text"], a["text"] = True, a["text"], ""
        findings, _ = audit_answers(evidence, {"payload": {"answers": answers,
                                        "answer_coverage": coverage}}, {})
        self.assertIn("EXPLANATION_WITHOUT_MARKER", {item["code"] for item in findings})

    def test_standalone_explanation_header_preserves_provenance_and_following_lines(self):
        evidence = synthetic_evidence([
            ("1.答案：13", 120), ("解析：", 140),
            ("由勾股定理先求平方和。", 160), ("开平方得到13。", 180), ("2.D", 200)])
        answers, _, coverage = assemble_answers(evidence, make_id)
        a = next(a for a in answers if a["printed_number"] == "1")
        self.assertEqual(a["text"], "13")
        self.assertTrue(a["explanation_present"])
        self.assertTrue(a["explanation_marker_present"])
        self.assertEqual(a["explanation_text"], "由勾股定理先求平方和。\n开平方得到13。")
        self.assertIn("synthetic/ocr/1", a["source_line_ids"])
        marker = next(f for f in a["fragments"] if f.get("structural_marker"))
        self.assertEqual(marker["raw_text"], "解析：")
        self.assertEqual(marker["role"], "explanation")
        row = next(row for row in coverage if row["line_id"] == "synthetic/ocr/1")
        self.assertEqual(row["status"], "CONSUMED")
        self.assertIn(a["answer_id"], row["answer_ids"])
        findings, _ = audit_answers(evidence, {"payload": {"answers": answers,
                                        "answer_coverage": coverage}}, {})
        codes = {item["code"] for item in findings}
        self.assertNotIn("EXPLANATION_WITHOUT_MARKER", codes)
        self.assertNotIn("EXPLANATION_AGGREGATE_TEXT_MISMATCH", codes)

    def test_standalone_header_without_body_is_explicitly_incomplete(self):
        evidence = synthetic_evidence([
            ("1.答案：13", 120), ("【解析】", 140), ("2.D", 160)])
        answers, issues, coverage = assemble_answers(evidence, make_id)
        a = next(a for a in answers if a["printed_number"] == "1")
        self.assertEqual(a["text"], "13")
        self.assertEqual(a["explanation_text"], "")
        self.assertFalse(a["explanation_present"])
        self.assertTrue(a["explanation_marker_present"])
        self.assertFalse(a["complete"])
        self.assertIn(a["assembly_status"], {"OPEN", "AMBIGUOUS"})
        self.assertIn("EXPLANATION_BODY_MISSING", {item["code"] for item in issues})
        self.assertIn("synthetic/ocr/1", a["source_line_ids"])
        row = next(row for row in coverage if row["line_id"] == "synthetic/ocr/1")
        self.assertEqual(row["status"], "CONSUMED")

    def test_bare_standalone_explanation_label_is_a_header_with_source_evidence(self):
        evidence = synthetic_evidence([
            ("1.答案：13", 120), ("解析", 140),
            ("先求平方和，再开平方。", 160), ("2.D", 180)])
        answers, _, coverage = assemble_answers(evidence, make_id)
        a = next(a for a in answers if a["printed_number"] == "1")
        self.assertTrue(a["explanation_present"])
        self.assertEqual(a["explanation_text"], "先求平方和，再开平方。")
        marker = next(f for f in a["fragments"] if f.get("structural_marker"))
        self.assertEqual(marker["raw_text"], "解析")
        self.assertEqual(marker["text_span"], [0, 2])
        row = next(row for row in coverage if row["line_id"] == "synthetic/ocr/1")
        self.assertEqual(row["status"], "CONSUMED")
        findings, _ = audit_answers(evidence, {"payload": {"answers": answers,
                                        "answer_coverage": coverage}}, {})
        self.assertNotIn("EXPLANATION_WITHOUT_MARKER", {item["code"] for item in findings})

    def test_decimals_subquestions_and_fraction_atoms_are_not_primary_numbers(self):
        answers, _, _ = self.assemble([
            ("5.解：设高为x。", 120), ("4.1=16.81，故可以通过。", 140),
            ("（1）先计算长度。", 160), ("（2）再计算面积。", 180),
            ("1", 200), ("2", 210), ("6.D", 235)])
        self.assertEqual([a["printed_number"] for a in answers], ["5", "6"])
        a = answers[0]
        self.assertEqual(source_lines(a), ["synthetic/ocr/" + str(i) for i in range(6)])
        self.assertIn("4.1=16.81", a["text"])
        self.assertIn("（2）", a["text"])

    def test_tier_boundary_prevents_unlabelled_material_leaking_into_previous_answer(self):
        answers, _, coverage = self.assemble([
            ("1.解：结果为13。", 120), ("中档题", 140),
            ("没有题号的内容，归属未知。", 160), ("2.D", 180)])
        a = next(a for a in answers if a["printed_number"] == "1")
        self.assertNotIn("归属未知", a["text"])
        self.assertNotIn("中档题", a["text"])
        orphan = next(row for row in coverage if row["line_id"] == "synthetic/ocr/2")
        self.assertEqual(orphan["status"], "UNASSIGNED")

    def test_section_boundary_does_not_join_repeated_question_one(self):
        path_a, path_b = ["Chapter", "A"], ["Chapter", "B"]
        windows = [{"column": 0, "y_range": [100, 160], "path": path_a},
                   {"column": 0, "y_range": [160, 300], "path": path_b}]
        answers, _, coverage = self.assemble([
            ("1.解：A课时答案。", 120, 0, 0),
            ("B课时无题号前缀，不能接到A。", 165, 0, 1),
            ("1.答案：C", 190, 0, 1), ("2.D", 215, 0, 1)], windows)
        ones = [a for a in answers if a["printed_number"] == "1"]
        self.assertEqual(len(ones), 2)
        self.assertEqual({tuple(a["section_path"]) for a in ones}, {tuple(path_a), tuple(path_b)})
        self.assertNotIn("B课时无题号", next(a for a in ones if a["section_path"] == path_a)["text"])
        orphan = next(row for row in coverage if row["line_id"] == "synthetic/ocr/1")
        self.assertEqual(orphan["status"], "UNASSIGNED")

    def test_missing_following_page_leaves_tail_open(self):
        answers, issues, _ = self.assemble([
            ("8.解：接下来还要计算", 1440), ("由此得到方程，", 1462)])
        self.assertEqual(len(answers), 1)
        self.assertIn(answers[0]["assembly_status"], {"OPEN", "AMBIGUOUS"})
        self.assertFalse(answers[0]["complete"])
        self.assertTrue(issues)

    def test_unrelated_right_column_cannot_prove_continuation(self):
        path_a, path_b = ["Chapter", "A"], ["Chapter", "B"]
        windows = [{"column": 0, "y_range": [100, 1500], "path": path_a},
                   {"column": 1, "y_range": [100, 1500], "path": path_b}]
        answers, _, coverage = self.assemble([
            ("8.解：A的未完答案，", 1460, 0, 0),
            ("B的无题号文本不能串答。", 120, 1, 1),
            ("1.D", 145, 1, 1)], windows)
        a = next(a for a in answers if a["section_path"] == path_a)
        self.assertNotIn("B的无题号", a["text"])
        self.assertFalse(a["complete"])
        orphan = next(row for row in coverage if row["line_id"] == "synthetic/ocr/1")
        self.assertEqual(orphan["status"], "UNASSIGNED")

    def test_cross_page_adjacency_or_gap_does_not_supply_missing_continuation_proof(self):
        # The current contract supports same-asset cross-column continuation.
        # Asset ordering alone must not silently extend that to cross-page work.
        for resource_index in (174, 176):
            with self.subTest(next_resource_index=resource_index):
                first = synthetic_evidence([("8.解：尚未完成，", 1460)])
                second = synthetic_evidence([
                    ("下一页无编号的文字，身份待确认。", 120), ("9.D", 145)])
                for index, (fixture, asset_id, source_index) in enumerate([
                        (first, "page-173", 173), (second, "page-next", resource_index)]):
                    page = fixture["payload"]["pages"][0]
                    page["asset_id"] = asset_id
                    page["source"].update(asset_id=asset_id, reading_order=index,
                                           external_refs={"resource_index": source_index})
                    for line in page["ocr_lines"]:
                        line["line_id"] = asset_id + "/ocr/" + line["line_id"].rsplit("/", 1)[1]
                    page_context = fixture["payload"]["context"]["pages"].pop("synthetic")
                    fixture["payload"]["context"]["pages"][asset_id] = page_context
                first["payload"]["pages"].extend(second["payload"]["pages"])
                first["payload"]["context"]["pages"].update(second["payload"]["context"]["pages"])
                answers, _, coverage = assemble_answers(first, make_id)
                a = next(a for a in answers if a["printed_number"] == "8")
                self.assertFalse(a["complete"])
                self.assertIn(a["assembly_status"], {"OPEN", "AMBIGUOUS"})
                self.assertNotIn("下一页", a["text"])
                orphan = next(row for row in coverage if row["line_id"] == "page-next/ocr/0")
                self.assertEqual(orphan["status"], "UNASSIGNED")


class MultilineQualityFaultRegression(unittest.TestCase):
    """Injected faults on observed data remain blocking, including old defects."""

    def setUp(self):
        self.evidence = read("ocr-evidence.json")
        self.review = read("review.json")
        self.graph = assemble(self.evidence)

    def question(self, page, number):
        return next(q for q in self.graph["payload"]["questions"]
                    if q["asset_id"] == page and q["printed_number"] == str(number))

    def answer(self, page, number):
        q = self.question(page, number)
        return next(a for a in self.graph["payload"]["answers"]
                    if a["answer_id"] == q["selected_answer_id"])

    def report(self):
        self.graph["revision"] += 1
        self.graph["content_hash"] = digest(self.graph["payload"])
        return quality_check(self.evidence, self.graph, self.review)["payload"]

    def test_q4_ratio_error_remains_blocked_after_multiline_assembly(self):
        self.answer("viewer-10", 4)["text"] = "1:3"
        self.graph["payload"]["historical_task_status"] = "SUCCESS"
        report = self.report()
        self.assertEqual(report["decision"], "HOLD")
        self.assertIn("ANSWER_SCALAR_FORMAT", {i["code"] for i in report["issues"]})

    def test_q7_c_zero_disagreement_is_not_erased_by_multiline_assembly(self):
        q = self.question("viewer-10", 7)
        self.assertEqual(self.answer("viewer-10", 7)["text"], "0")
        codes = {i["code"] for i in self.report()["issues"] if i["scope_id"] == q["question_id"]}
        self.assertTrue({"CHOICE_ANSWER_FORMAT", "OCR_RECOGNITION_DISAGREEMENT"} <= codes)

    def test_dropped_real_q6_continuation_is_found_independently_of_answer_text(self):
        a = self.answer("viewer-10", 6)
        dropped = next(f for f in a["fragments"]
                       if "viewer-173/ocr/14" in [raw_ref(r) for r in f["evidence_refs"]]
                       or f.get("parent_line_id") == "viewer-173/ocr/14")
        a["fragments"].remove(dropped)
        a["regions"] = [r for r in a["regions"] if r.get("fragment_id") != dropped["fragment_id"]]
        # Deliberately leave text and declared coverage looking complete. The
        # checker must compare actual fragments with both source-bound ledgers.
        codes = {i["code"] for i in self.report()["issues"]}
        self.assertIn("ANSWER_LEDGER_MISMATCH", codes)
        self.assertIn("ANSWER_REFERENCE_COVERAGE_MISMATCH", codes)

    def test_duplicated_real_q6_continuation_is_not_hidden_by_new_fragment_id(self):
        a = self.answer("viewer-10", 6)
        original = next(f for f in a["fragments"]
                        if "viewer-173/ocr/14" in [raw_ref(r) for r in f["evidence_refs"]]
                        or f.get("parent_line_id") == "viewer-173/ocr/14")
        duplicate = copy.deepcopy(original)
        duplicate["fragment_id"] += "-injected-duplicate"
        a["fragments"].append(duplicate)
        codes = {i["code"] for i in self.report()["issues"]}
        self.assertIn("ANSWER_EVIDENCE_REUSED", codes)
        self.assertIn("ANSWER_LEDGER_MISMATCH", codes)

    def test_answer_region_cannot_diverge_from_valid_real_q15_fragment(self):
        a = self.answer("viewer-11", 15)
        a["regions"][0]["bbox"] = [1, 1, 2, 2]
        # Both boxes remain in bounds; source fidelity, rather than bounds
        # checking alone, must catch a projected answer box being replaced.
        codes = {i["code"] for i in self.report()["issues"]}
        self.assertIn("ANSWER_REGION_PROJECTION_MISMATCH", codes)

    def shorten_q15_continuation(self):
        a = self.answer("viewer-11", 15)
        fragment = next(f for f in a["fragments"]
                        if f.get("parent_line_id") == "viewer-173/ocr/35")
        self.assertEqual(fragment["raw_text"], "AB·BC+")  # fixed observed source
        fragment["text_span"], fragment["text"] = [0, 2], "AB"
        a["text"] = "\n".join(f["text"] for f in a["fragments"]
                              if f["role"] == "answer" and not f.get("structural_marker"))
        return fragment

    def test_shortened_real_q15_continuation_disagrees_with_allocation_and_reviewed_span(self):
        self.shorten_q15_continuation()
        # The remaining substring is perfectly faithful to the source bytes;
        # completeness needs the separately authored expected interval too.
        codes = {i["code"] for i in self.report()["issues"]}
        self.assertIn("ANSWER_ALLOCATION_MISMATCH", codes)
        self.assertIn("ANSWER_REFERENCE_SPAN_MISMATCH", codes)

    def test_coordinated_shortened_fragment_and_ledger_cannot_change_reviewed_span(self):
        fragment = self.shorten_q15_continuation()
        row = next(row for row in self.graph["payload"]["answer_coverage"]
                   if row["line_id"] == "viewer-173/ocr/35")
        allocation = next(item for item in row["allocations"]
                          if item["fragment_id"] == fragment["fragment_id"])
        allocation["text_span"] = [0, 2]
        codes = {i["code"] for i in self.report()["issues"]}
        self.assertIn("ANSWER_REFERENCE_SPAN_MISMATCH", codes)


if __name__ == "__main__":
    unittest.main()
