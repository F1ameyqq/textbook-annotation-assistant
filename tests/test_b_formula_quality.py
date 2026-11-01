"""Independent formula faults over fixed synthetic observations and raw spans.

Synthetic text is a labelled backend response, not image-transcription gold.
The quality consumer may not call a collector or production syntax parser.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from annotation.recognition.baseline import digest
from annotation.recognition.formula_backend import collect_formula_observations
from annotation.recognition.formula_candidates import build_formula_candidates
from annotation.recognition.formula_quality import audit_formula_candidates
from tests.test_b_math_reading_quality import synthetic_layout


def rehash(value):
    value["content_hash"] = digest(value["payload"])
    return value


def observations(layout,path,raws=None):
    values = iter(raws or [r"\frac{a^{2}+1}{2}"]*2)
    def labelled_test_backend(pixels):
        value = next(values)
        if isinstance(value,Exception): raise value
        return value,.001
    return collect_formula_observations(layout,path,recognizer=labelled_test_backend)


def find_node(node,kind):
    if isinstance(node,dict):
        if node.get("type") == kind: return node
        for child in node.values():
            found = find_node(child,kind)
            if found is not None: return found
    if isinstance(node,list):
        for child in node:
            found = find_node(child,kind)
            if found is not None: return found


class IndependentFormulaQuality(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.layout,self.path = synthetic_layout(self.temp.name)
        p = self.layout["payload"]
        self.layout["input_refs"] = [{"artifact_id":"synthetic-recovery","revision":1,"content_hash":"0"*64},
            {"asset_id":p["asset_id"],"sha256":p["source_sha256"]},{"crop_sha256":p["crop_sha256"]}]
        self.obs = observations(self.layout,self.path)
        self.candidates = build_formula_candidates(self.layout,self.obs,self.path)

    def check(self,candidates=None,obs=None,layout=None):
        return audit_formula_candidates(layout or self.layout,obs or self.obs,
                                        candidates or self.candidates,self.path)["payload"]

    def assertCode(self,candidates,code,*,obs=None,layout=None):
        checked = self.check(candidates,obs,layout)
        self.assertFalse(checked["accepted"],checked)
        self.assertIn(code,{i["code"]for i in checked["issues"]},checked)
        self.assertEqual(checked["decision"],"HOLD")

    def variant(self,candidates):
        return candidates["payload"]["units"][0]["variants"][0]

    def test_traceable_nested_fraction_and_superscript_are_unselected_hold(self):
        checked = self.check()
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(checked["summary"],{"unit_count":1,"variant_count":2,"parsed_candidate_count":2,
                                             "unparsed_variant_count":0,"disagreement_unit_count":0})
        self.assertEqual(self.obs["producer"]["execution_kind"],"SYNTHETIC_TEST")
        unit = self.candidates["payload"]["units"][0]
        self.assertEqual(unit["selected_candidate_refs"],[])
        self.assertFalse(unit["complete"])
        self.assertFalse(checked["transcription_verified"])
        self.assertFalse(checked["business_acceptance"])
        self.assertEqual(checked["platform_actions"],[])

    def test_consumer_never_calls_collector_candidate_or_syntax_producer(self):
        frozen = copy.deepcopy((self.layout,self.obs,self.candidates))
        with mock.patch("annotation.recognition.formula_backend.collect_formula_observations",side_effect=AssertionError("collector ran")), \
             mock.patch("annotation.recognition.formula_candidates.build_formula_candidates",side_effect=AssertionError("candidate ran")), \
             mock.patch("annotation.recognition.formula_syntax.parse_formula_latex",side_effect=AssertionError("parser ran")):
            self.assertTrue(self.check()["accepted"])
        self.assertEqual(frozen,(self.layout,self.obs,self.candidates))
        source = Path(sys.modules["annotation.recognition.formula_quality"].__file__).read_text(encoding="utf-8")
        for name in ("from .formula_backend import","from .formula_candidates import","from .formula_syntax import"):
            self.assertNotIn(name,source)

    def test_changed_exponent_with_coordinated_normalized_ast_is_rejected(self):
        candidates = copy.deepcopy(self.candidates)
        parsed = self.variant(candidates)["parse_result"]
        find_node(parsed["ast"],"power")["exponent"]["body"]["items"][0]["value"] = "3"
        find_node(parsed["normalized_ast"],"power")["exponent"]["value"] = "3"
        self.assertCode(rehash(candidates),"FORMULA_AST_RAW_MISMATCH")

    def test_changed_denominator_with_consistent_normalization_is_rejected(self):
        candidates = copy.deepcopy(self.candidates)
        parsed = self.variant(candidates)["parse_result"]
        find_node(parsed["ast"],"fraction")["denominator"]["items"][0]["value"] = "3"
        find_node(parsed["normalized_ast"],"fraction")["denominator"]["value"] = "3"
        self.assertCode(rehash(candidates),"FORMULA_AST_RAW_MISMATCH")

    def test_raw_and_token_and_ast_edits_cannot_replace_fixed_external_observation(self):
        different = observations(self.layout,self.path,[r"\frac{a^{3}+1}{2}"]*2)
        forged = build_formula_candidates(self.layout,different,self.path)
        # Repair references to fixed external obs while retaining changed raw,
        # tokens and AST: no stale content hash alone should be the barrier.
        forged["payload"]["observation_ref"] = {k:self.obs[k]for k in ("artifact_id","revision","content_hash")}
        forged["input_refs"][1] = forged["payload"]["observation_ref"]
        for variant in forged["payload"]["units"][0]["variants"]:
            variant["candidate_id"] = "formula-candidate-"+digest([forged["payload"]["observation_ref"],
                forged["payload"]["units"][0]["unit_id"],variant["variant_id"],variant["raw_latex"]])[:24]
        self.assertCode(rehash(forged),"FORMULA_RAW_OBSERVATION_CHANGED")

    def test_missing_or_duplicated_unit_cannot_shrink_declared_formula_scope(self):
        for duplicate in (False,True):
            candidates = copy.deepcopy(self.candidates)
            if duplicate: candidates["payload"]["units"].append(copy.deepcopy(candidates["payload"]["units"][0]))
            else: candidates["payload"]["units"] = []
            self.assertCode(rehash(candidates),"FORMULA_CANDIDATE_UNIT_COVERAGE_MISMATCH")

    def test_dropped_fraction_from_two_fraction_raw_cannot_claim_single_source_shape(self):
        obs = observations(self.layout,self.path,[r"\frac{a}{2}\frac{b}{3}"]*2)
        candidates = build_formula_candidates(self.layout,obs,self.path)
        self.assertTrue(self.check(candidates,obs)["accepted"])
        self.assertIn("FORMULA_SOURCE_FRACTION_SHAPE_MISMATCH",{i["code"]for i in candidates["payload"]["issues"]})
        for variant in candidates["payload"]["units"][0]["variants"]:
            parsed = variant["parse_result"]
            parsed["ast"]["items"].pop()
            parsed["ast"]["raw_source_span"] = parsed["ast"]["items"][0]["raw_source_span"][:]
            parsed["normalized_ast"] = parsed["normalized_ast"]["items"][0]
            variant.update(fraction_node_count=1,source_fraction_shape_matches=True)
        candidates["payload"]["issues"] = []
        self.assertCode(rehash(candidates),"FORMULA_AST_RAW_MISMATCH",obs=obs)

    def test_model_omission_of_fraction_stays_explicit_shape_risk(self):
        obs = observations(self.layout,self.path,["a^2+1"]*2)
        candidates = build_formula_candidates(self.layout,obs,self.path)
        self.assertTrue(self.check(candidates,obs)["accepted"])
        self.assertEqual([v["fraction_node_count"]for v in candidates["payload"]["units"][0]["variants"]],[0,0])
        candidates["payload"]["issues"] = []
        self.assertCode(rehash(candidates),"FORMULA_RISK_LEDGER_MISMATCH",obs=obs)

    def test_unknown_command_is_preserved_as_unsupported_not_a_successful_prefix(self):
        obs = observations(self.layout,self.path,[r"\frac{\unknown{a}}{2}"]*2)
        candidates = build_formula_candidates(self.layout,obs,self.path)
        self.assertTrue(self.check(candidates,obs)["accepted"])
        parsed = self.variant(candidates)["parse_result"]
        self.assertFalse(parsed["supported"])
        self.assertIn(r"\unknown",[t["text"]for t in parsed["tokens"]])
        self.assertIn(r"\unknown",parsed["unparsed_tail"])
        parsed["unparsed_tail"] = "a"
        self.assertCode(rehash(candidates),"FORMULA_UNPARSED_RAW_DROPPED",obs=obs)

    def test_unknown_character_cannot_disappear_from_token_prefix_and_tail(self):
        obs = observations(self.layout,self.path,[r"\frac{α}{2}"]*2)
        candidates = build_formula_candidates(self.layout,obs,self.path)
        self.assertTrue(self.check(candidates,obs)["accepted"])
        parsed = self.variant(candidates)["parse_result"]
        parsed.update(supported=True,ast=copy.deepcopy(self.variant(self.candidates)["parse_result"]["ast"]),
                      normalized_ast=copy.deepcopy(self.variant(self.candidates)["parse_result"]["normalized_ast"]),errors=[],unparsed_tail=None)
        self.assertCode(rehash(candidates),"FORMULA_AST_RAW_MISMATCH",obs=obs)

    def test_unknown_command_cannot_be_skipped_with_coordinated_error_position_and_empty_tail(self):
        obs = observations(self.layout,self.path,[r"\frac{\unknown{a}}{2}"]*2)
        candidates = build_formula_candidates(self.layout,obs,self.path)
        parsed = self.variant(candidates)["parse_result"]
        parsed["errors"][0]["position"] = len(parsed["raw_latex"])
        parsed["unparsed_tail"] = ""
        self.assertCode(rehash(candidates),"FORMULA_UNPARSED_RAW_DROPPED",obs=obs)

    def test_two_variants_are_retained_with_disagreement_not_selected(self):
        obs = observations(self.layout,self.path,[r"\frac{a^2+1}{2}",r"\frac{a+1}{2}"])
        candidates = build_formula_candidates(self.layout,obs,self.path)
        checked = self.check(candidates,obs)
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(checked["summary"]["disagreement_unit_count"],1)
        candidates["payload"]["units"][0]["exact_ast_agreement"] = True
        self.assertCode(rehash(candidates),"FORMULA_FALSE_AGREEMENT",obs=obs)

    def test_failed_backend_is_explicit_unparsed_hold_without_invented_text(self):
        obs = observations(self.layout,self.path,[RuntimeError("synthetic failure"),r"\frac{a}{2}"])
        candidates = build_formula_candidates(self.layout,obs,self.path)
        checked = self.check(candidates,obs)
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(checked["summary"]["unparsed_variant_count"],1)
        self.variant(candidates)["raw_latex"] = r"\frac{a}{2}"
        self.assertCode(rehash(candidates),"FORMULA_RAW_OBSERVATION_CHANGED",obs=obs)

    def test_crop_metadata_and_transformed_pixels_are_checked_independently(self):
        obs = copy.deepcopy(self.obs)
        obs["payload"]["units"][0]["variants"][0]["transformed_rgb_sha256"] = "0"*64
        candidates = copy.deepcopy(self.candidates)
        candidates["payload"]["units"][0]["variants"][0]["transformed_rgb_sha256"] = "0"*64
        rehash(obs)
        candidates["payload"]["observation_ref"] = {k:obs[k]for k in ("artifact_id","revision","content_hash")}
        candidates["input_refs"][1] = candidates["payload"]["observation_ref"]
        self.assertCode(rehash(candidates),"FORMULA_TRANSFORM_MISMATCH",obs=obs)

    def test_read_order_cannot_be_replaced_with_formula_order(self):
        candidates = copy.deepcopy(self.candidates)
        candidates["payload"]["reading_groups"][0]["units"] = []
        self.assertCode(rehash(candidates),"FORMULA_LAYOUT_ORDER_CHANGED")

    def test_ast_source_spans_cannot_move_a_correct_symbol_to_another_position(self):
        candidates = copy.deepcopy(self.candidates)
        parsed = self.variant(candidates)["parse_result"]
        find_node(parsed["ast"],"power")["exponent"]["raw_source_span"][0] += 1
        self.assertCode(rehash(candidates),"FORMULA_AST_RAW_MISMATCH")

    def test_presentation_tokens_and_group_scopes_are_retained_losslessly(self):
        obs = observations(self.layout,self.path,[r"\displaystyle\dfrac{(a_1+1)^{2}}{2}"]*2)
        candidates = build_formula_candidates(self.layout,obs,self.path)
        checked = self.check(candidates,obs)
        self.assertTrue(checked["accepted"],checked)
        parsed = self.variant(candidates)["parse_result"]
        self.assertEqual(parsed["tokens"][0]["text"],r"\displaystyle")
        # Redundant {} may normalize; actual parentheses must keep their scope.
        self.assertIsNotNone(find_node(parsed["normalized_ast"],"group"))

    def test_false_complete_or_selected_or_graph_modified_is_never_approved(self):
        for target,key,value in (("top","complete",True),("top","graph_modified",True),
                                 ("unit","selected_candidate_refs",["invented"]),("variant","transcription_verified",True)):
            with self.subTest(target=target,key=key):
                candidates = copy.deepcopy(self.candidates)
                destination = candidates["payload"] if target == "top" else candidates["payload"]["units"][0] if target == "unit" else self.variant(candidates)
                destination[key] = value
                self.assertCode(rehash(candidates),"FORMULA_FALSE_VERIFICATION")

    def test_synthetic_receipt_cannot_claim_cpu_without_models_and_provider_proof(self):
        obs = copy.deepcopy(self.obs)
        obs["producer"]["execution_kind"] = "CPU_RAPID_LATEX_OCR"
        candidates = copy.deepcopy(self.candidates)
        candidates["producer"]["execution_kind"] = "CPU_RAPID_LATEX_OCR"
        self.assertCode(candidates,"FORMULA_BACKEND_RECEIPT_INVALID",obs=obs)

    def test_stale_observation_and_unknown_schema_reject(self):
        candidates = copy.deepcopy(self.candidates)
        candidates["payload"]["observation_ref"]["revision"] += 1
        self.assertCode(rehash(candidates),"FORMULA_STALE_REFERENCE")
        candidates = copy.deepcopy(self.candidates)
        candidates["schema_version"] = "accepted-formula/1"
        self.assertCode(candidates,"FORMULA_ARTIFACT_INVALID")

    def test_coordinated_source_labels_cannot_override_fixed_layout_asset_reference(self):
        layout = copy.deepcopy(self.layout)
        layout["payload"]["source_sha256"] = "2"*64
        rehash(layout)
        obs = observations(layout,self.path)
        candidates = build_formula_candidates(layout,obs,self.path)
        self.assertCode(candidates,"FORMULA_LAYOUT_SOURCE_REFERENCE_MISMATCH",obs=obs,layout=layout)

    def test_unknown_verified_formula_fields_cannot_bypass_false_complete_guards(self):
        candidates = copy.deepcopy(self.candidates)
        candidates["payload"]["units"][0]["verified_latex"] = r"\frac{a^2+1}{2}"
        self.assertCode(rehash(candidates),"FORMULA_UNKNOWN_FIELD")

    def test_unsupported_unbraced_script_group_cannot_be_promoted_with_a_forged_ast(self):
        obs = observations(self.layout,self.path,["a^(b+1)"]*2)
        candidates = build_formula_candidates(self.layout,obs,self.path)
        self.assertTrue(self.check(candidates,obs)["accepted"])
        def leaf(kind,value,start,end):
            return {"type":kind,"value":value,"raw_source_span":[start,end]}
        group = {"type":"group","delimiters":"()","raw_source_span":[2,7],
            "body":{"type":"sequence","raw_source_span":[3,6],"items":[leaf("symbol","b",3,4),leaf("operator","+",4,5),leaf("number","1",5,6)]}}
        power = {"type":"power","raw_source_span":[0,7],"base":leaf("symbol","a",0,1),"exponent":group,"index":None}
        parsed = self.variant(candidates)["parse_result"]
        parsed.update(supported=True,ast={"type":"sequence","raw_source_span":[0,7],"items":[power]},
                      normalized_ast={},errors=[],unparsed_tail=None)
        self.assertCode(rehash(candidates),"FORMULA_AST_RAW_MISMATCH",obs=obs)

    def test_double_superscript_requires_explicit_source_braces(self):
        obs = observations(self.layout,self.path,["a^2^3"]*2)
        candidates = build_formula_candidates(self.layout,obs,self.path)
        self.assertTrue(self.check(candidates,obs)["accepted"])
        def leaf(value,start,end): return {"type":"number" if value.isdigit()else"symbol","value":value,"raw_source_span":[start,end]}
        inner = {"type":"power","raw_source_span":[0,3],"base":leaf("a",0,1),"exponent":leaf("2",2,3),"index":None}
        outer = {"type":"power","raw_source_span":[0,5],"base":inner,"exponent":leaf("3",4,5),"index":None}
        self.variant(candidates)["parse_result"].update(supported=True,ast={"type":"sequence","raw_source_span":[0,5],"items":[outer]},
                                                       normalized_ast={},errors=[],unparsed_tail=None)
        self.assertCode(rehash(candidates),"FORMULA_AST_RAW_MISMATCH",obs=obs)

    def test_style_commands_only_change_presentation_and_remain_in_raw_tokens(self):
        for style in (r"\textstyle",r"\scriptstyle",r"\scriptscriptstyle"):
            with self.subTest(style=style):
                obs = observations(self.layout,self.path,[style+r"{\frac{a^2+1}{2}}"]*2)
                candidates = build_formula_candidates(self.layout,obs,self.path)
                checked = self.check(candidates,obs)
                self.assertTrue(checked["accepted"],checked)
                first = self.variant(candidates)["parse_result"]["tokens"][0]
                self.assertEqual((first["kind"],first["text"]),("presentation",style))


class RealFormulaObservationsQuality(unittest.TestCase):
    """Actual CPU observations; replay does not rerun or verify the model."""
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(ROOT/"tools"))
        from replay_math_b import replay
        fixture = ROOT/"tests/fixtures/book46007447"
        cls.layout,_,cls.crop = replay(fixture)
        receipt = fixture/"formula-observations.json"
        cls.obs = json.loads(receipt.read_text(encoding="utf-8"))
        cls.candidates = build_formula_candidates(cls.layout,cls.obs,cls.crop)

    def test_actual_11_source_units_22_cpu_observations_are_traceable_but_hold(self):
        checked = audit_formula_candidates(self.layout,self.obs,self.candidates,self.crop)["payload"]
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(checked["summary"]["unit_count"],11)
        self.assertEqual(checked["summary"]["variant_count"],22)
        self.assertEqual(self.obs["producer"]["execution_kind"],"CPU_RAPID_LATEX_OCR")
        self.assertEqual(self.obs["producer"]["providers"],[["CPUExecutionProvider"]]*3)
        self.assertFalse(any(v["recognition_error"]for u in self.obs["payload"]["units"]for v in u["variants"]))
        self.assertFalse(checked["transcription_verified"])
        self.assertFalse(checked["business_acceptance"])
        self.assertEqual(checked["decision"],"HOLD")

    def test_actual_last_scale3_raised_symbol_and_scale4_hallucination_are_not_blended(self):
        last = self.candidates["payload"]["units"][-1]
        raw = [v["raw_latex"]for v in last["variants"]]
        self.assertEqual(raw,[r"\textstyle{\frac{a^{2}+1}{2}}",r"\scriptstyle{\frac{\pi+1}{2}}"])
        self.assertEqual([v["parse_result"]["supported"]for v in last["variants"]],[True,False])
        self.assertIn(r"\pi",last["variants"][1]["parse_result"]["unparsed_tail"])
        self.assertFalse(last["exact_ast_agreement"])
        self.assertEqual(last["selected_candidate_refs"],[])
        self.assertFalse(last["complete"])
        original_math = json.loads((ROOT/"tests/fixtures/book46007447/math-role-evidence.json").read_text(encoding="utf-8"))
        self.assertEqual([v["raw_ocr_result"][0][0]for v in original_math["payload"]["roles"][-2]["variants"]],["a+1","a+1"])
        # The dedicated formula candidate does not mutate the old observations
        # or resolve their source-pixel warning on its own authority.
        self.assertFalse(self.candidates["payload"]["graph_modified"])
        self.assertFalse(self.candidates["payload"]["expected_text_consumed"])

    def test_actual_supported_denominator_cannot_change_under_a_rehashed_candidate(self):
        candidates = copy.deepcopy(self.candidates)
        parsed = candidates["payload"]["units"][0]["variants"][0]["parse_result"]
        self.assertTrue(parsed["supported"])
        find_node(parsed["ast"],"fraction")["denominator"]["items"][0]["value"] = "3"
        find_node(parsed["normalized_ast"],"fraction")["denominator"]["value"] = "3"
        checked = audit_formula_candidates(self.layout,self.obs,rehash(candidates),self.crop)["payload"]
        self.assertFalse(checked["accepted"])
        self.assertIn("FORMULA_AST_RAW_MISMATCH",{i["code"]for i in checked["issues"]})


if __name__ == "__main__":
    unittest.main()
