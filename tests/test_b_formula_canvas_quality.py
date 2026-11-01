"""Independent source/tensor/trace faults over explicitly synthetic responses.

Known rectangles are not formula gold. Expected image bounds and trace order
are written independently; actual cached CPU observations are never rerun here.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"),str(ROOT/"tests")]
from annotation.recognition.baseline import digest
from annotation.recognition.formula_backend import collect_formula_observations
from annotation.recognition.formula_canvas import collect_canvas_observations,build_canvas_candidates,preprocess_canvas
from annotation.recognition.formula_canvas_quality import audit_canvas_candidates
from test_b_math_reading_quality import synthetic_layout


def ref(value):
    return {key:value[key]for key in ("artifact_id","revision","content_hash")}


def sign(value):
    value["content_hash"] = digest(value["payload"])
    prefix = "formula-canvas-observations-"if value["kind"] == "FormulaCanvasObservationTrial"else"formula-canvas-candidates-"
    value["artifact_id"] = prefix+digest([value["input_refs"],value["producer"],value["payload"]])[:24]
    return value


def node(value,kind):
    if isinstance(value,dict):
        if value.get("type") == kind: return value
        for child in value.values():
            found = node(child,kind)
            if found is not None: return found
    elif isinstance(value,list):
        for child in value:
            found = node(child,kind)
            if found is not None: return found


class IndependentFormulaCanvasQuality(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.layout,self.path = synthetic_layout(self.temp.name)
        p = self.layout["payload"]
        self.layout["input_refs"] = [{"artifact_id":"synthetic-recovery","revision":1,"content_hash":"0"*64},
            {"asset_id":p["asset_id"],"sha256":p["source_sha256"]},{"crop_sha256":p["crop_sha256"]}]
        self.raw = r"\frac{a^{2}+1}{2}"
        self.legacy = collect_formula_observations(self.layout,self.path,recognizer=lambda image:(self.raw,.001))
        self.obs = collect_canvas_observations(self.layout,self.path,recognizer=lambda tensor:(self.raw,.001))
        self.candidates = build_canvas_candidates(self.layout,self.obs,self.path,self.legacy)

    def check(self,candidates=None,observations=None,legacy=None,layout=None):
        return audit_canvas_candidates(layout or self.layout,observations or self.obs,candidates or self.candidates,
            self.path,legacy or self.legacy)["payload"]

    def reject(self,check,code):
        self.assertFalse(check["accepted"],check)
        self.assertIn(code,{i["code"]for i in check["issues"]},check)
        self.assertEqual(check["decision"],"HOLD")

    def coordinated(self,obs,candidates):
        sign(obs)
        candidates["input_refs"][1] = ref(obs)
        candidates["payload"]["observation_ref"] = ref(obs)
        for unit in candidates["payload"]["units"]:
            for v in unit["variants"]:
                v["candidate_id"] = "formula-canvas-candidate-"+digest([ref(obs),unit["unit_id"],v["variant_id"],v["raw_latex"]])[:24]
        candidates["producer"]["execution_kind"] = obs["producer"]["execution_kind"]
        return sign(candidates)

    def pair(self): return copy.deepcopy(self.obs),copy.deepcopy(self.candidates)

    def variant(self,candidates): return candidates["payload"]["units"][0]["variants"][0]

    def test_full_rectangle_and_two_typed_tensors_are_unselected_hold(self):
        checked = self.check()
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(checked["summary"]["unit_count"],1)
        self.assertEqual(checked["summary"]["variant_count"],2)
        unit = self.obs["payload"]["units"][0]
        self.assertEqual(unit["source_bbox"],[102,200,148,243])
        self.assertEqual(unit["crop_local_bbox"],[2,0,48,43])
        native,large = unit["variants"]
        self.assertEqual(native["transformed_size"],[46,43])
        self.assertEqual(native["canvas_size"],[64,64])
        self.assertEqual(native["tensor_shape"],[1,1,64,64])
        self.assertEqual(native["source_to_canvas"],[[1,0,-102],[0,1,-200],[0,0,1]])
        self.assertEqual(large["canvas_size"],[160,160])
        self.assertFalse(native["preprocessing_trace"]["initial_pad"]["threshold_crop"])
        self.assertEqual(self.candidates["payload"]["units"][0]["selected_candidate_refs"],[])
        self.assertFalse(checked["business_acceptance"])
        self.assertFalse(checked["transcription_verified"])
        self.assertEqual(checked["platform_actions"],[])

    def test_consumer_never_runs_any_model_parser_or_producer(self):
        frozen = copy.deepcopy((self.layout,self.obs,self.candidates,self.legacy))
        with mock.patch("annotation.recognition.formula_canvas.preprocess_canvas",side_effect=AssertionError("preprocessor ran")), \
             mock.patch("annotation.recognition.formula_canvas.collect_canvas_observations",side_effect=AssertionError("collector ran")), \
             mock.patch("annotation.recognition.formula_canvas.build_canvas_candidates",side_effect=AssertionError("builder ran")), \
             mock.patch("annotation.recognition.formula_syntax.parse_formula_latex",side_effect=AssertionError("parser ran")), \
             mock.patch("annotation.recognition.formula_backend.collect_formula_observations",side_effect=AssertionError("legacy collector ran")):
            self.assertTrue(self.check()["accepted"])
        self.assertEqual(frozen,(self.layout,self.obs,self.candidates,self.legacy))
        source = (ROOT/"src/annotation/recognition/formula_canvas_quality.py").read_text(encoding="utf-8")
        for forbidden in ("from .formula_canvas import","from .formula_backend import","from .formula_candidates import","from .formula_syntax import"):
            self.assertNotIn(forbidden,source)

    def test_upper_ink_cannot_be_cut_by_coordinated_unit_geometry_and_hashes(self):
        obs,cp = self.pair()
        for data in (obs,cp):
            unit = data["payload"]["units"][0]
            unit["source_bbox"][1] = 203
            unit["crop_local_bbox"][1] = 3
            unit["crop_size"][1] -= 3
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_UNIT_SOURCE_MISMATCH")

    def test_erased_detached_raised_ink_cannot_be_hidden_by_valid_canvas_metadata(self):
        obs,cp = self.pair()
        with Image.open(self.path)as opened: altered = opened.convert("RGB")
        # Exact synthetic detached component: source [116,202,119,208].
        altered.paste((255,255,255),(16,2,19,8))
        wanted = obs["payload"]["units"][0]
        metadata,_ = preprocess_canvas(altered,wanted,{"variant_id":"gray-native","scale":1})
        for data in (obs,cp): data["payload"]["units"][0]["variants"][0].update(copy.deepcopy(metadata))
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_PIXEL_OR_TENSOR_MISMATCH")

    def test_fake_tensor_digest_on_surface_and_trace_rejected(self):
        obs,cp = self.pair()
        for data in (obs,cp):
            v = data["payload"]["units"][0]["variants"][0]
            v["tensor_sha256"] = "0"*64
            v["preprocessing_trace"]["steps"][-1]["tensor_sha256"] = "0"*64
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_PIXEL_OR_TENSOR_MISMATCH")

    def test_fake_threshold_trim_is_not_a_permitted_full_pad(self):
        obs,cp = self.pair()
        for data in (obs,cp): data["payload"]["units"][0]["variants"][0]["preprocessing_trace"]["initial_pad"]["threshold_crop"] = True
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_PIXEL_OR_TENSOR_MISMATCH")

    def test_fake_gray_normalization_or_tensor_dtype_rejected(self):
        for field,value in (("tensor_dtype","float64"),("paste_offset",[1,0]),("canvas_rgb_sha256","1"*64)):
            with self.subTest(field=field):
                obs,cp = self.pair()
                for data in (obs,cp): data["payload"]["units"][0]["variants"][0][field] = value
                self.coordinated(obs,cp)
                self.reject(self.check(cp,obs),"FORMULA_CANVAS_PIXEL_OR_TENSOR_MISMATCH")

    def test_wrong_source_matrix_with_coordinated_inverse_rejected(self):
        obs,cp = self.pair()
        for data in (obs,cp):
            v = data["payload"]["units"][0]["variants"][0]
            v["source_to_canvas"][0][2] += 1
            v["canvas_to_source"][0][2] -= 1
            v["preprocessing_trace"]["steps"][-1]["source_to_canvas"][0][2] += 1
            v["preprocessing_trace"]["steps"][-1]["canvas_to_source"][0][2] -= 1
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_PIXEL_OR_TENSOR_MISMATCH")

    def multistep(self):
        obs = copy.deepcopy(self.obs)
        calls = []
        def synthetic_resizer(inputs):
            calls.append(inputs[0].shape)
            logits = np.zeros((1,21),dtype="float32");logits[0,2] = 1
            return [logits]
        with Image.open(self.path)as opened: image = opened.convert("RGB")
        metadata,_ = preprocess_canvas(image,obs["payload"]["units"][0],{"variant_id":"gray-native","scale":1},resizer=synthetic_resizer)
        self.assertEqual(calls,[(1,1,64,64),(1,1,96,96)])
        obs["payload"]["units"][0]["variants"][0].update(metadata)
        sign(obs)
        cp = build_canvas_candidates(self.layout,obs,self.path,self.legacy)
        return obs,cp

    def test_two_step_raw_logits_drive_exact_independent_resize_replay(self):
        obs,cp = self.multistep()
        checked = self.check(cp,obs)
        self.assertTrue(checked["accepted"],checked)
        v = self.variant(cp)
        self.assertEqual(v["preprocessing_trace"]["steps"][0]["next_width"],96)
        self.assertEqual(v["source_to_canvas"],[[1.5,0,-153],[0,1.5,-300],[0,0,1]])

    def test_coordinated_raw_logits_cannot_leave_a_stale_next_tensor(self):
        obs,cp = self.multistep()
        for data in (obs,cp):
            step = data["payload"]["units"][0]["variants"][0]["preprocessing_trace"]["steps"][0]
            step["resizer_logits"][0][2] = 0;step["resizer_logits"][0][3] = 1
            step.update(argmax_index=3,next_width=128)
        self.coordinated(obs,cp)
        self.assertFalse(self.check(cp,obs)["accepted"])

    def test_argmax_is_derived_from_original_logits_not_declared_width(self):
        obs,cp = self.pair()
        for data in (obs,cp): data["payload"]["units"][0]["variants"][0]["preprocessing_trace"]["steps"][0]["argmax_index"] += 1
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_PIXEL_OR_TENSOR_MISMATCH")

    def test_dropped_or_extra_resizer_steps_rejected_after_full_rehash(self):
        obs,cp = self.multistep()
        for data in (obs,cp):
            trace = data["payload"]["units"][0]["variants"][0]["preprocessing_trace"]
            trace["steps"].pop();trace["stop_reason"] = "WIDTH_STABLE"
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_TRACE_INVALID")
        obs,cp = self.pair()
        for data in (obs,cp):
            trace = data["payload"]["units"][0]["variants"][0]["preprocessing_trace"]
            trace["steps"].append(copy.deepcopy(trace["steps"][0]))
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_TRACE_INVALID")

    def test_nonfinite_or_wrong_shape_resizer_observation_rejected(self):
        for value in ([[float("nan")]],[[1],[0]]):
            with self.subTest(value=value):
                obs,cp = self.pair()
                for data in (obs,cp): data["payload"]["units"][0]["variants"][0]["preprocessing_trace"]["steps"][0]["resizer_logits"] = value
                if np.isfinite(np.asarray(value)).all():
                    self.coordinated(obs,cp)
                    self.reject(self.check(cp,obs),"FORMULA_CANVAS_TRACE_INVALID")
                else:
                    # NaN cannot receive a canonical JSON digest at all.
                    self.reject(self.check(cp,obs),"FORMULA_CANVAS_PERSISTED_DATA_INVALID")

    def test_missing_or_reordered_variant_cannot_shrink_source_scope(self):
        for remove in (True,False):
            obs,cp = self.pair()
            for data in (obs,cp):
                variants = data["payload"]["units"][0]["variants"]
                if remove: variants.pop()
                else: variants.reverse()
            self.coordinated(obs,cp)
            self.reject(self.check(cp,obs),"FORMULA_CANVAS_VARIANT_COVERAGE_MISMATCH")

    def test_missing_or_duplicated_unit_cannot_claim_complete_scope(self):
        for duplicate in (True,False):
            obs,cp = self.pair()
            for data in (obs,cp):
                if duplicate: data["payload"]["units"].append(copy.deepcopy(data["payload"]["units"][0]))
                else: data["payload"]["units"] = []
            self.coordinated(obs,cp)
            self.reject(self.check(cp,obs),"FORMULA_CANVAS_UNIT_COVERAGE_MISMATCH")

    def test_exponent_and_denominator_cannot_change_under_coordinated_ast_normalization(self):
        for kind in ("power","fraction"):
            cp = copy.deepcopy(self.candidates);parsed = self.variant(cp)["parse_result"]
            if kind == "power":
                node(parsed["ast"],kind)["exponent"]["body"]["items"][0]["value"] = "4"
                node(parsed["normalized_ast"],kind)["exponent"]["value"] = "4"
            else:
                node(parsed["ast"],kind)["denominator"]["items"][0]["value"] = "4"
                node(parsed["normalized_ast"],kind)["denominator"]["value"] = "4"
            self.reject(self.check(sign(cp)),"FORMULA_CANVAS_AST_RAW_MISMATCH")

    def test_raw_edit_cannot_replace_the_fixed_external_observation(self):
        changed = collect_canvas_observations(self.layout,self.path,recognizer=lambda tensor:(r"\frac{a^{4}+1}{2}",.001))
        cp = build_canvas_candidates(self.layout,changed,self.path,self.legacy)
        self.coordinated(self.obs,cp)
        self.reject(self.check(cp),"FORMULA_CANVAS_RAW_OBSERVATION_CHANGED")

    def test_unknown_command_tail_is_preserved_without_becoming_supported(self):
        obs = collect_canvas_observations(self.layout,self.path,recognizer=lambda tensor:(r"\frac{\pi+1}{2}",.001))
        cp = build_canvas_candidates(self.layout,obs,self.path,self.legacy)
        self.assertTrue(self.check(cp,obs)["accepted"])
        parsed = self.variant(cp)["parse_result"]
        self.assertFalse(parsed["supported"])
        parsed["unparsed_tail"] = ""
        self.reject(self.check(sign(cp),obs),"FORMULA_CANVAS_UNPARSED_RAW_DROPPED")

    def test_legacy_raw_archive_or_candidate_projection_cannot_be_rewritten(self):
        cp = copy.deepcopy(self.candidates)
        cp["payload"]["legacy_observations_archive"]["payload"]["units"][0]["variants"][0]["raw_latex"] = "a"
        self.reject(self.check(sign(cp)),"FORMULA_CANVAS_STALE_OR_LEGACY_REFERENCE")
        cp = copy.deepcopy(self.candidates)
        parsed = cp["payload"]["legacy_candidates_payload"]["units"][0]["variants"][0]["parse_result"]
        node(parsed["ast"],"fraction")["denominator"]["items"][0]["value"] = "9"
        self.reject(self.check(sign(cp)),"FORMULA_CANVAS_LEGACY_INTEGRITY_REJECTED")

    def test_exact_agreement_still_cannot_set_complete_or_select_human_gold(self):
        for field,value in (("complete",True),("selected_candidate_refs",["a-selected-candidate"]),("transcription_verified",True)):
            cp = copy.deepcopy(self.candidates);cp["payload"]["units"][0][field] = value
            self.reject(self.check(sign(cp)),"FORMULA_CANVAS_FALSE_VERIFICATION")

    def test_false_cross_path_agreement_cannot_remove_disagreement_risks(self):
        legacy = collect_formula_observations(self.layout,self.path,recognizer=lambda image:(r"\frac{a^{3}+1}{2}",.001))
        cp = build_canvas_candidates(self.layout,self.obs,self.path,legacy)
        self.assertTrue(self.check(cp,legacy=legacy)["accepted"])
        cp["payload"]["units"][0]["cross_path_exact_ast_agreement"] = True
        cp["payload"]["issues"] = []
        self.reject(self.check(sign(cp),legacy=legacy),"FORMULA_CANVAS_FALSE_AGREEMENT")

    def test_legacy_agreement_refs_must_match_actual_normalized_raw_ast(self):
        legacy = collect_formula_observations(self.layout,self.path,recognizer=lambda image:(r"\frac{a^{3}+1}{2}",.001))
        cp = build_canvas_candidates(self.layout,self.obs,self.path,legacy)
        self.variant(cp)["legacy_agreement_candidate_refs"] = [cp["payload"]["legacy_candidates_payload"]["units"][0]["variants"][0]["candidate_id"]]
        self.reject(self.check(sign(cp),legacy=legacy),"FORMULA_CANVAS_LEGACY_AGREEMENT_MISMATCH")

    def test_injected_backend_cannot_impersonate_real_cpu_receipt(self):
        obs,cp = self.pair()
        obs["producer"].update(execution_kind="CPU_RAPID_LATEX_OCR_PRESERVE_CANVAS",backend="rapid-latex-ocr",backend_adapter="PRESERVE_CANVAS_LEARNED_RESIZER")
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_BACKEND_RECEIPT_INVALID")

    def test_stale_configuration_or_source_digest_rejected(self):
        obs,cp = self.pair()
        obs["producer"]["configuration"]["trim"] = True
        obs["producer"]["configuration_sha256"] = digest(obs["producer"]["configuration"])
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_BACKEND_RECEIPT_INVALID")
        obs,cp = self.pair()
        for data in (obs,cp): data["payload"]["source"]["source_sha256"] = "2"*64
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_SOURCE_BINDING_MISMATCH")

    def test_reported_decode_failure_is_traceable_hold_not_fabricated_text(self):
        def fail(tensor): raise RuntimeError("synthetic decoder failed")
        obs = collect_canvas_observations(self.layout,self.path,recognizer=fail)
        cp = build_canvas_candidates(self.layout,obs,self.path,self.legacy)
        checked = self.check(cp,obs)
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(checked["summary"]["unparsed_variant_count"],2)
        self.assertIsNone(self.variant(cp)["raw_latex"])

    def test_failed_resizer_retains_preprocessing_failure_without_decoder_text(self):
        obs = copy.deepcopy(self.obs)
        v = obs["payload"]["units"][0]["variants"][0]
        trace = v["preprocessing_trace"];step = trace["steps"][0]
        step.update(resizer_logits=None,resizer_logits_shape=None,resizer_logits_dtype=None,
            argmax_index=None,next_width=None,terminated=False,resizer_error={"type":"RuntimeError","status":"RESIZER_FAILED"})
        trace["stop_reason"] = "RESIZER_FAILED"
        v.update(raw_latex=None,engine_elapsed_seconds=None,recognition_error={"type":"RuntimeError","status":"PREPROCESSING_FAILED"})
        sign(obs)
        cp = build_canvas_candidates(self.layout,obs,self.path,self.legacy)
        checked = self.check(cp,obs)
        self.assertTrue(checked["accepted"],checked)
        self.assertIsNone(self.variant(cp)["raw_latex"])
        self.variant(cp)["recognition_error"]["status"] = "RECOGNITION_FAILED"
        obs["payload"]["units"][0]["variants"][0]["recognition_error"]["status"] = "RECOGNITION_FAILED"
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_PREPROCESSING_ERROR_MISMATCH")

    def test_actual_twenty_two_cached_cpu_calls_preserve_errors_and_stay_hold(self):
        fixture = ROOT/"tests/fixtures/book46007447"
        path = fixture/"formula-canvas-observations.json"
        if not path.is_file(): self.skipTest("Explicitly collected CPU observations are not installed; never collect from a test")
        layout = json.loads((fixture/"formula-layout.json").read_text(encoding="utf-8"))
        legacy = json.loads((fixture/"formula-observations.json").read_text(encoding="utf-8"))
        obs = json.loads(path.read_text(encoding="utf-8"))
        crop = fixture/"recovery-assets/unit2-q16.png"
        frozen = copy.deepcopy(obs)
        cp = build_canvas_candidates(layout,obs,crop,legacy)
        check = audit_canvas_candidates(layout,obs,cp,crop,legacy)["payload"]
        self.assertTrue(check["accepted"],check)
        self.assertEqual(check["summary"],{"unit_count":11,"variant_count":22,"parsed_candidate_count":17,
            "unparsed_variant_count":5,"disagreement_unit_count":11,"cross_path_disagreement_unit_count":11})
        self.assertEqual(obs["producer"]["execution_kind"],"CPU_RAPID_LATEX_OCR_PRESERVE_CANVAS")
        # Literal retained observations are not asserted to be source truth.
        self.assertEqual(obs["payload"]["units"][2]["variants"][0]["raw_latex"],r"\frac{a^{4}+2a^{2}+1}{4}")
        self.assertEqual(obs["payload"]["units"][4]["variants"][0]["raw_latex"],r"\frac{a^{4}+2a^{2}+1}{a}")
        for unit in cp["payload"]["units"]:
            self.assertEqual(unit["selected_candidate_refs"],[])
            self.assertFalse(unit["complete"])
            self.assertFalse(unit["transcription_verified"])
        self.assertEqual(obs,frozen)

    def test_canonical_but_out_of_range_declared_logit_dtype_fails_closed(self):
        obs,cp = self.pair()
        for data in (obs,cp):
            step = data["payload"]["units"][0]["variants"][0]["preprocessing_trace"]["steps"][0]
            step["resizer_logits_dtype"] = "int64"
            step["resizer_logits"][0][0] = 1e200
        self.coordinated(obs,cp)
        self.reject(self.check(cp,obs),"FORMULA_CANVAS_TRACE_INVALID")

    def test_malformed_persisted_data_fails_closed(self):
        cp = copy.deepcopy(self.candidates);cp["payload"]["units"] = None
        self.assertFalse(self.check(sign(cp))["accepted"])


if __name__ == "__main__": unittest.main()
