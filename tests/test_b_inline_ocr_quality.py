"""Source-bound inline OCR audit faults with an explicit synthetic backend.

Synthetic recognitions deliberately need not match drawn or archived text.
Traceability acceptance never measures OCR accuracy or precise localization.
"""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image,ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from annotation.recognition.baseline import digest,file_digest
from annotation.recognition.inline_ocr import collect_inline_observations
from annotation.recognition.inline_ocr_quality import audit_inline_ocr


def bind(value):
    value["content_hash"] = digest(value["payload"])
    reference = {k:value["payload"]["evidence_ref"][k]for k in ("artifact_id","revision","content_hash")}
    value["artifact_id"] = "inline-ocr-observation-"+digest({"source":reference,"inputs":[reference],"producer":value["producer"],"payload":value["payload"]})[:24]
    return value


def polygon(x0,y0,x1,y1): return [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]


def fixed_backend(image,**kwargs):
    h,w = image.shape[:2]
    boxes = [polygon(1+i*6,1,6+i*6,h-1)for i in range(4)]
    return [[polygon(1,1,w-1,h-1),"a²+1",.88,boxes,["a","²","+","1"],[.95,.31,.97,.98]]],[.01,0,.02]


class InlineOCRQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/"source.png"
        image = Image.new("RGB",(96,64),"white");draw = ImageDraw.Draw(image)
        draw.rectangle((7,8,13,17),fill=(50,100,190));draw.rectangle((50,31,58,43),fill=(170,40,20))
        image.save(self.path)
        asset = {"asset_id":"synthetic-source","sha256":file_digest(self.path),"width":96,"height":64,"path":"source.png","reading_order":0}
        self.line_ids = ["synthetic-source/ocr/0","synthetic-source/ocr/1"]
        raw = [{"line_id":self.line_ids[0],"text":"Archived source row, not expected transcription","score":.7,"bbox":[4,6,92,20],
                "location":{"column":0,"window_index":0,"section_path":["SYNTHETIC_TEST"]}},
               {"line_id":self.line_ids[1],"text":"Another archived row","score":.8,"bbox":[4,30,92,44],
                "location":{"column":0,"window_index":0,"section_path":["SYNTHETIC_TEST"]}}]
        payload = {"pages":[{"asset_id":asset["asset_id"],"source":asset,"page_role":"answer","ocr_lines":raw,"answer_detail_lines":[]}],"context":{}}
        self.evidence = {"schema_version":"b-evidence-trial/0.3","kind":"EvidenceBundleTrial","artifact_id":"synthetic-current-evidence","revision":3,
            "book_id":"synthetic-book","scope_id":"two-full-source-rows","run_id":"synthetic-run","payload":payload,"content_hash":digest(payload)}
        self.observations = self.collect()

    def collect(self,backend=fixed_backend):
        return collect_inline_observations(self.evidence,self.path,asset_id="synthetic-source",line_ids=self.line_ids,recognizer=backend)

    def audit(self,value=None,**kwargs):
        return audit_inline_ocr(self.evidence,value or self.observations,self.path,line_ids=self.line_ids,**kwargs)["payload"]

    def first(self,value): return value["payload"]["rows"][0]["variants"][0]

    def test_fixed_test_backend_preserves_all_rows_variants_raw_and_low_score_risk(self):
        checked = self.audit()
        self.assertTrue(checked["accepted"],checked["issues"])
        self.assertEqual(checked["summary"]["requested_rows"],2)
        self.assertEqual(checked["summary"]["variants"],4)
        self.assertEqual(checked["summary"]["raw_candidates"],4)
        self.assertEqual(checked["summary"]["word_estimates"],16)
        self.assertEqual(checked["summary"]["pixel_verified_assets"],1)
        self.assertFalse(checked["summary"]["declared_scope_only"])
        self.assertIn("LOW_CONFIDENCE_WORD_ESTIMATE",{r["code"]for r in checked["observation_risks"]})
        self.assertEqual(checked["decision"],"HOLD")
        self.assertFalse(checked["complete"])
        self.assertFalse(checked["precise_glyph_localization"])
        self.assertFalse(checked["spatial_role_verified"])
        self.assertEqual(self.observations["producer"]["execution_kind"],"SYNTHETIC_TEST")

    def test_independent_audit_never_calls_collector_projection_or_models(self):
        with patch("annotation.recognition.inline_ocr.collect_inline_observations",side_effect=AssertionError("collector")), \
             patch("annotation.recognition.inline_ocr._projection",side_effect=AssertionError("projection")), \
             patch("annotation.recognition.inline_ocr._cpu_backend",side_effect=AssertionError("model")):
            self.assertTrue(self.audit()["accepted"])

    def test_external_requested_scope_cannot_shrink_with_coordinated_hash(self):
        value = copy.deepcopy(self.observations)
        value["payload"]["requested_line_ids"].pop();value["payload"]["rows"].pop();bind(value)
        self.assertFalse(self.audit(value)["accepted"])
        self.assertTrue(audit_inline_ocr(self.evidence,value,self.path)["payload"]["summary"]["declared_scope_only"])

    def test_row_and_variant_order_and_missing_variant_are_checked(self):
        for fault in ("rows","variants","drop"):
            with self.subTest(fault=fault):
                value = copy.deepcopy(self.observations)
                if fault == "rows": value["payload"]["rows"].reverse()
                elif fault == "variants": value["payload"]["rows"][0]["variants"].reverse()
                else: value["payload"]["rows"][0]["variants"].pop()
                bind(value);self.assertFalse(self.audit(value)["accepted"])

    def test_crop_must_include_full_original_row_plus_two_pixels(self):
        value = copy.deepcopy(self.observations);row = value["payload"]["rows"][0]
        row["crop_bbox"][1] += 2;row["crop_size"][1] -= 2
        with Image.open(self.path)as image: row["crop_rgb_sha256"] = hashlib.sha256(image.convert("RGB").crop(row["crop_bbox"]).tobytes()).hexdigest()
        bind(value)
        self.assertFalse(self.audit(value)["accepted"])

    def test_entire_current_source_line_snapshot_cannot_lose_score_or_location(self):
        for field in ("score","location","text"):
            value = copy.deepcopy(self.observations)
            value["payload"]["rows"][0]["source_line"].pop(field);bind(value)
            self.assertFalse(self.audit(value)["accepted"])

    def test_original_bytes_are_checked_not_just_row_crop_hashes(self):
        Image.new("RGB",(96,64),"white").save(self.path)
        value = copy.deepcopy(self.observations)
        value["payload"]["source"]["original_sha256"] = file_digest(self.path)
        value["payload"]["source"]["original_rgb_sha256"] = hashlib.sha256(Image.open(self.path).convert("RGB").tobytes()).hexdigest()
        bind(value)
        self.assertFalse(self.audit(value)["accepted"])

    def test_rgb_bgr_and_inverse_transform_cannot_be_relabelled(self):
        for fault in ("bgr","matrix"):
            value = copy.deepcopy(self.observations);variant = self.first(value)
            if fault == "bgr": variant["bgr_sha256"] = variant["rgb_sha256"]
            else: variant["variant_to_original"][1][2] += 1
            bind(value);self.assertFalse(self.audit(value)["accepted"])

    def test_full_raw_call_and_engine_elapsed_are_not_independent_rewrites(self):
        value = copy.deepcopy(self.observations)
        self.first(value)["engine_elapsed_seconds"] = [.7,0,.8];bind(value)
        self.assertFalse(self.audit(value)["accepted"])

    def test_candidate_and_char_projection_cannot_drop_reorder_or_rewrite_raw(self):
        for fault in ("drop","reorder","text"):
            value = copy.deepcopy(self.observations);candidate = self.first(value)["candidates"][0]
            if fault == "drop": candidate["word_estimates"].pop()
            elif fault == "reorder": candidate["word_estimates"].reverse()
            else: candidate["text"] = "a+1"
            bind(value);self.assertFalse(self.audit(value)["accepted"])

    def test_real_engine_sequence_mismatch_is_preserved_as_risk_not_fake_good_text(self):
        def mismatched(image,**kwargs):
            raw,elapsed = fixed_backend(image,**kwargs)
            raw[0][4][1] = "3"  # full text still a²+1; retain this inconsistent raw observation.
            return raw,elapsed
        value = self.collect(mismatched)
        checked = self.audit(value)
        self.assertTrue(checked["accepted"],checked["issues"])
        self.assertIn("WORD_SEQUENCE_MISMATCH",{r["code"]for r in checked["observation_risks"]})
        self.first(value)["issues"] = [];bind(value)
        self.assertFalse(self.audit(value)["accepted"])

    def test_unequal_arrays_keep_maximum_length_and_missing_values(self):
        def unequal(image,**kwargs):
            raw,elapsed = fixed_backend(image,**kwargs);raw[0][5].pop();return raw,elapsed
        value = self.collect(unequal)
        words = self.first(value)["candidates"][0]["word_estimates"]
        self.assertEqual(len(words),4);self.assertIsNone(words[-1]["score"])
        checked = self.audit(value);self.assertTrue(checked["accepted"],checked["issues"])
        self.assertIn("WORD_ARRAY_LENGTH_MISMATCH",{r["code"]for r in checked["observation_risks"]})
        words.pop();bind(value)
        self.assertFalse(self.audit(value)["accepted"])

    def test_degenerate_estimate_is_retained_but_cannot_be_promoted_to_usable(self):
        def degenerate(image,**kwargs):
            raw,elapsed = fixed_backend(image,**kwargs);raw[0][3][1] = [[6,1]]*4;return raw,elapsed
        value = self.collect(degenerate);checked = self.audit(value)
        self.assertTrue(checked["accepted"],checked["issues"])
        self.assertEqual(checked["summary"]["unusable_word_estimates"],4)
        self.first(value)["candidates"][0]["word_estimates"][1]["polygon_status"] = "USABLE";bind(value)
        self.assertFalse(self.audit(value)["accepted"])

    def test_outside_input_estimate_retains_unclamped_projection_and_risk(self):
        def outside(image,**kwargs):
            raw,elapsed = fixed_backend(image,**kwargs);raw[0][3][0] = polygon(-2,1,3,4);return raw,elapsed
        value = self.collect(outside);checked = self.audit(value)
        self.assertTrue(checked["accepted"],checked["issues"])
        word = self.first(value)["candidates"][0]["word_estimates"][0]
        self.assertEqual(word["polygon_status"],"OUTSIDE_INPUT")
        self.assertLess(word["source_polygon"][0][0],value["payload"]["rows"][0]["crop_bbox"][0])

    def test_malformed_raw_rows_are_not_discarded_and_missing_fields_are_explicit(self):
        def malformed(image,**kwargs): return [["too","short"],None], [.01,0,.02]
        value = self.collect(malformed);checked = self.audit(value)
        self.assertTrue(checked["accepted"],checked["issues"])
        self.assertEqual(checked["summary"]["raw_candidates"],8)
        self.assertEqual(len(self.first(value)["candidates"]),2)
        self.first(value)["candidates"].pop();bind(value)
        self.assertFalse(self.audit(value)["accepted"])

    def test_failure_and_empty_results_remain_scope_complete_unverified_observations(self):
        def failure(image,**kwargs): raise RuntimeError("SYNTHETIC_TEST deliberate engine failure")
        for backend in (failure,lambda image,**kwargs:(None,None),lambda image,**kwargs:([],[0,0,0])):
            value = self.collect(backend);checked = self.audit(value)
            self.assertTrue(checked["accepted"],checked["issues"])
            self.assertEqual(checked["summary"]["variants"],4)
            self.assertEqual(checked["summary"]["raw_candidates"],0)
            self.assertTrue(checked["observation_risks"])

    def test_synthetic_cannot_become_cpu_by_changing_execution_label(self):
        value = copy.deepcopy(self.observations)
        value["producer"].update(execution_kind="CPU_RAPIDOCR_INLINE",device="CPU",engine="rapidocr_onnxruntime");bind(value)
        self.assertFalse(self.audit(value)["accepted"])

    def test_human_complete_selected_and_precise_glyph_metadata_are_rejected(self):
        for location,key in (("header","human_verified"),("payload","human_verified"),("payload","complete"),("candidate","precise_glyph_localization"),("word","spatial_role_verified")):
            with self.subTest(location=location,key=key):
                value = copy.deepcopy(self.observations)
                target = value if location == "header"else value["payload"]if location == "payload"else self.first(value)["candidates"][0]
                if location == "word": target = target["word_estimates"][0]
                target[key] = True;bind(value)
                self.assertFalse(self.audit(value)["accepted"])

    def test_ctc_configuration_requires_detection_and_return_word_boxes(self):
        value = copy.deepcopy(self.observations)
        value["producer"]["configuration"]["engine_flags"]["use_det"] = False
        value["producer"]["configuration_sha256"] = digest(value["producer"]["configuration"]);bind(value)
        self.assertFalse(self.audit(value)["accepted"])

    def test_unknown_precision_or_backend_fields_are_not_accepted(self):
        value = copy.deepcopy(self.observations);value["producer"]["human_reviewed"] = True;bind(value)
        self.assertFalse(self.audit(value)["accepted"])

    def test_stale_current_evidence_and_cross_asset_line_ids_are_rejected(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["payload"]["pages"][0]["ocr_lines"][0]["score"] = .2;evidence["content_hash"] = digest(evidence["payload"])
        self.assertFalse(audit_inline_ocr(evidence,self.observations,self.path,line_ids=self.line_ids)["payload"]["accepted"])
        evidence = copy.deepcopy(self.evidence)
        evidence["payload"]["pages"][0]["ocr_lines"][0]["asset_id"] = "other-asset";evidence["content_hash"] = digest(evidence["payload"])
        self.assertFalse(audit_inline_ocr(evidence,self.observations,self.path,line_ids=self.line_ids)["payload"]["accepted"])

    def test_invalid_data_returns_rejected_artifact(self):
        for value in ({},{"payload":{}},None):
            result = audit_inline_ocr(self.evidence,value,self.path,line_ids=self.line_ids)
            self.assertFalse(result["payload"]["accepted"])


if __name__ == "__main__": unittest.main()
