"""Independent formula counterexamples; no model runtime, expected OCR, or network.

Expected trees/spans below are handwritten from the displayed LaTeX grammar.
The real source fixture is used only for geometry/order, never as a formula
recognition gold standard. Injected observations are explicitly synthetic.
"""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from annotation.recognition.baseline import digest
from annotation.recognition.formula_syntax import parse_formula_latex, fraction_count
from annotation.recognition.formula_backend import collect_formula_observations, plan_formula_units
from annotation.recognition.formula_candidates import build_formula_candidates
from replay_math_b import replay


def observe(layout, crop, raw):
    def recognizer(rgb):
        return raw, .001
    return collect_formula_observations(layout, crop, recognizer=recognizer)


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values(): yield from walk(child)
    elif isinstance(value, list):
        for child in value: yield from walk(child)


class IndependentLatexSyntax(unittest.TestCase):
    def test_fraction_multidigit_exponent_handwritten_tree_and_exact_source_spans(self):
        raw = r"\frac{a^{12}+1}{2}"
        result = parse_formula_latex(raw)
        self.assertTrue(result["supported"])
        self.assertEqual(result["normalized_ast"], {
            "type": "fraction", "numerator": {"type": "sequence", "items": [
                {"type": "power", "base": {"type": "symbol", "value": "a"},
                 "exponent": {"type": "number", "value": "12"}, "index": None},
                {"type": "operator", "value": "+"}, {"type": "number", "value": "1"}]},
            "denominator": {"type": "number", "value": "2"}})
        nodes = list(walk(result["ast"]))
        self.assertEqual(next(n for n in nodes if n.get("type") == "fraction")["raw_source_span"], [0, 18])
        power = next(n for n in nodes if n.get("type") == "power")
        self.assertEqual(power["raw_source_span"], [6, 12])
        self.assertEqual(power["base"]["raw_source_span"], [6, 7])
        self.assertEqual(power["exponent"]["raw_source_span"], [8, 12])
        self.assertEqual(power["exponent"]["body"]["items"][0]["raw_source_span"], [9, 11])
        self.assertEqual(raw[9:11], "12")

    def test_parenthesized_base_and_braced_multichar_script_keep_their_scopes(self):
        result = parse_formula_latex(r"(a+b)^{10}+x_{ij}")
        self.assertTrue(result["supported"])
        root = result["normalized_ast"]
        first, plus, last = root["items"]
        self.assertEqual(first["type"], "power")
        self.assertEqual(first["base"], {"type": "group", "delimiters": "()", "body": {
            "type": "sequence", "items": [{"type": "symbol", "value": "a"},
                {"type": "operator", "value": "+"}, {"type": "symbol", "value": "b"}]}})
        self.assertEqual(first["exponent"], {"type": "number", "value": "10"})
        self.assertEqual(plus, {"type": "operator", "value": "+"})
        self.assertEqual(last["base"], {"type": "symbol", "value": "x"})
        self.assertEqual(last["index"], {"type": "sequence", "items": [
            {"type": "symbol", "value": "i"}, {"type": "symbol", "value": "j"}]})

    def test_unbraced_single_symbol_script_does_not_swallow_following_symbol(self):
        parsed = parse_formula_latex("x^ab")
        self.assertTrue(parsed["supported"])
        self.assertEqual(parsed["normalized_ast"], {"type": "sequence", "items": [
            {"type": "power", "base": {"type": "symbol", "value": "x"},
             "exponent": {"type": "symbol", "value": "a"}, "index": None},
            {"type": "symbol", "value": "b"}]})
        self.assertFalse(parse_formula_latex("x^12")["supported"])

    def test_unbraced_parenthesis_script_is_not_invented_as_an_entire_group(self):
        for raw in ("a^(b+1)", "a_[i+j]", r"a^\left(b+1\right)"):
            with self.subTest(raw=raw):
                result = parse_formula_latex(raw)
                self.assertFalse(result["supported"])
                self.assertIsNone(result["ast"])
                self.assertTrue(result["unparsed_tail"])

    def test_double_script_without_explicit_group_cannot_be_left_associated(self):
        for raw in ("a^b^c", "a_i_j", "a^2^3", "x^{ab}^{cd}"):
            with self.subTest(raw=raw):
                self.assertFalse(parse_formula_latex(raw)["supported"])
        nested = parse_formula_latex("a^{b^c}")
        self.assertTrue(nested["supported"])
        self.assertEqual(nested["normalized_ast"]["exponent"]["type"], "power")
        self.assertEqual(nested["normalized_ast"]["exponent"]["base"]["value"], "b")
        self.assertEqual(nested["normalized_ast"]["exponent"]["exponent"]["value"], "c")

    def test_plus_inside_exponent_is_neither_simplified_nor_moved_outside(self):
        inside = parse_formula_latex(r"\frac{a^{2+1}}{2}")
        outside = parse_formula_latex(r"\frac{a^2+1}{2}")
        self.assertTrue(inside["supported"] and outside["supported"])
        self.assertNotEqual(inside["normalized_ast"], outside["normalized_ast"])
        self.assertEqual(inside["normalized_ast"]["numerator"]["exponent"], {
            "type": "sequence", "items": [{"type": "number", "value": "2"},
                {"type": "operator", "value": "+"}, {"type": "number", "value": "1"}]})
        self.assertEqual([n["value"] for n in outside["normalized_ast"]["numerator"]["items"]
                          if n["type"] in ("number", "operator")], ["+", "1"])

    def test_nested_fraction_count_and_numerator_denominator_order_are_explicit(self):
        result = parse_formula_latex(r"\frac{1}{\frac{2}{3}}")
        self.assertTrue(result["supported"])
        self.assertEqual(fraction_count(result["ast"]), 2)
        self.assertEqual(result["normalized_ast"], {"type": "fraction", "numerator": {"type": "number", "value": "1"},
                         "denominator": {"type": "fraction", "numerator": {"type": "number", "value": "2"},
                                         "denominator": {"type": "number", "value": "3"}}})

    def test_unknown_math_and_unclosed_scope_remain_raw_and_unsupported(self):
        for raw, position, tail in ((r"a+\unknown{b}", 2, r"\unknown{b}"), ("a+α", 2, "α")):
            with self.subTest(raw=raw):
                parsed = parse_formula_latex(raw)
                self.assertFalse(parsed["supported"])
                self.assertEqual(parsed["raw_latex"], raw)
                self.assertIsNone(parsed["ast"])
                self.assertEqual(parsed["errors"][0]["position"], position)
                self.assertEqual(parsed["unparsed_tail"], tail)
        for raw in (r"\frac{1}{}", r"\frac{1}{2", r"\sqrt{x}", "x^", "x^{a]}"):
            with self.subTest(raw=raw): self.assertFalse(parse_formula_latex(raw)["supported"])

    def test_spacing_commands_preserve_order_and_decimal_digits_remain_one_number(self):
        raw = r"\displaystyle \frac{12.50\,x}{0.25}"
        parsed = parse_formula_latex(raw)
        self.assertTrue(parsed["supported"])
        self.assertEqual(parsed["normalized_ast"]["numerator"], {"type": "sequence", "items": [
            {"type": "number", "value": "12.50"}, {"type": "symbol", "value": "x"}]})
        self.assertEqual(parsed["normalized_ast"]["denominator"], {"type": "number", "value": "0.25"})
        tokens = parsed["tokens"]
        self.assertEqual([t["text"] for t in tokens], [r"\displaystyle", r"\frac", "{", "12.50", r"\,", "x", "}", "{", "0.25", "}"])
        self.assertTrue(all(raw[t["start"]:t["end"]] == t["text"] for t in tokens))


class IndependentFormulaSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout, _, cls.crop = replay(FIXTURE)

    def test_injected_backend_needs_no_formula_runtime_and_stays_synthetic(self):
        real_import = __import__
        def no_runtime(name, *args, **kwargs):
            if name.startswith(("rapid_latex_ocr", "onnxruntime")):
                raise AssertionError("unexpected model runtime import")
            return real_import(name, *args, **kwargs)
        with mock.patch("builtins.__import__", side_effect=no_runtime):
            observations = observe(self.layout, self.crop, r"\frac{a^{12}+1}{2}")
            candidates = build_formula_candidates(self.layout, observations, self.crop)
        self.assertEqual(observations["producer"]["execution_kind"], "SYNTHETIC_TEST")
        self.assertEqual(candidates["producer"]["execution_kind"], "SYNTHETIC_TEST")
        self.assertEqual(len(candidates["payload"]["units"]), 11)
        self.assertEqual(candidates["payload"]["decision"], "HOLD")
        self.assertFalse(candidates["payload"]["entire_answer_reconstructed"])
        self.assertTrue(all(u["selected_candidate_refs"] == [] for u in candidates["payload"]["units"]))

    def test_candidate_shape_does_not_call_nested_or_extra_fraction_a_single_source_fraction(self):
        for raw, number in ((r"\frac{1}{\frac{2}{3}}", 2), (r"\frac{1}{2}+\frac{3}{4}", 2),
                            (r"\frac{1}{2}+3", 1)):
            with self.subTest(raw=raw):
                observations = observe(self.layout, self.crop, raw)
                candidates = build_formula_candidates(self.layout, observations, self.crop)
                variant = candidates["payload"]["units"][0]["variants"][0]
                self.assertEqual(variant["raw_latex"], raw)
                self.assertEqual(variant["fraction_node_count"], number)
                self.assertFalse(variant["source_fraction_shape_matches"])
                self.assertFalse(variant["complete"])
                self.assertIn("FORMULA_SOURCE_FRACTION_SHAPE_MISMATCH", {i["code"] for i in candidates["payload"]["issues"]})

    def test_syntax_unknown_token_is_not_repaired_from_the_source_or_other_variant(self):
        observations = observe(self.layout, self.crop, r"\frac{a+\mystery}{2}")
        candidates = build_formula_candidates(self.layout, observations, self.crop)
        variant = candidates["payload"]["units"][0]["variants"][0]
        self.assertEqual(variant["raw_latex"], r"\frac{a+\mystery}{2}")
        self.assertFalse(variant["parse_result"]["supported"])
        self.assertIsNone(variant["parse_result"]["ast"])
        self.assertFalse(variant["source_fraction_shape_matches"])
        self.assertFalse(candidates["payload"]["units"][0]["exact_ast_agreement"])

    def test_actual_source_body_60_61_and_fraction_positions_survive_without_flattening(self):
        before = copy.deepcopy(self.layout)
        observations = observe(self.layout, self.crop, r"\frac{a+1}{2}")
        candidates = build_formula_candidates(self.layout, observations, self.crop)
        first = candidates["payload"]["reading_groups"][0]["units"]
        self.assertEqual([u.get("raw_text") for u in first[:3]], ["16.解：（1）60", "61", "(2)"])
        self.assertEqual([u["kind"] for u in first[:4]], ["body", "body", "body", "fraction"])
        self.assertEqual([u["x"] for u in first[:3]], [589.6667, 699.0, 736.3333])
        self.assertEqual(first[3]["x"], 766)
        self.assertEqual(self.layout, before)
        first_source = candidates["payload"]["units"][0]
        self.assertEqual(first_source["source_ocr_refs"], {
            "numerator": ["recovery/unit2-q16/scale3/0"], "denominator": ["recovery/unit2-q16/scale3/5"]})

    def test_wrong_side_layout_role_boxes_are_not_accepted_as_source_proof(self):
        changed = copy.deepcopy(self.layout)
        fraction = changed["payload"]["fraction_candidates"][0]
        fraction["numerator"]["pixel_bbox"], fraction["denominator"]["pixel_bbox"] = (
            fraction["denominator"]["pixel_bbox"], fraction["numerator"]["pixel_bbox"])
        changed["content_hash"] = digest(changed["payload"])
        with self.assertRaises(ValueError): plan_formula_units(changed, self.crop)

    def test_synthetic_observation_cannot_be_promoted_by_changing_only_header_kind(self):
        observations = observe(self.layout, self.crop, r"\frac{1}{2}")
        observations["producer"]["execution_kind"] = "CPU_RAPID_LATEX_OCR"
        with self.assertRaises(ValueError): build_formula_candidates(self.layout, observations, self.crop)

    def test_duplicate_or_reordered_source_fraction_cannot_reuse_old_observation(self):
        observations = observe(self.layout, self.crop, r"\frac{1}{2}")
        for mutation in ("duplicate", "order"):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(observations)
                if mutation == "duplicate": changed["payload"]["units"][-1] = copy.deepcopy(changed["payload"]["units"][0])
                else: changed["payload"]["units"].reverse()
                changed["content_hash"] = digest(changed["payload"])
                with self.assertRaises(ValueError): build_formula_candidates(self.layout, changed, self.crop)


if __name__ == "__main__": unittest.main()
