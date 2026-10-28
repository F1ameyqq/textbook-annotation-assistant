"""Pixel-bound math layout regressions; no model call or website access.

Real-case expectations describe the retained source crop and recorded OCR, not
mathematical truth. Synthetic images exercise non-fraction and missing-OCR cases.
"""
from collections import Counter
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/"tests/fixtures/book46007447"
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tools"))
from annotation.recognition.baseline import digest,file_digest
from annotation.recognition.math_layout import build_math_layout,audit_math_layout
from replay_math_b import replay


def rehash(value):
    value["content_hash"] = digest(value["payload"])
    return value


def synthetic(directory,*,fraction=True,equal_sign=False):
    """Construct explicit test pixels and a labelled synthetic OCR receipt."""
    path = Path(directory)/"source.png"
    image = Image.new("RGB",(200,80),"white")
    draw = ImageDraw.Draw(image)
    if fraction:
        draw.text((10,25),"1.(1)60",fill="black")
        draw.text((50,25),"61",fill="black")
        draw.text((75,25),"(2)",fill="black")
        draw.text((99,14),"a+1",fill="black")
        draw.text((112,37),"2",fill="black")
        draw.rectangle([96,30,135,31],fill="black")
        elements = [("1.(1)60",[10,25,46,37]),("61",[50,25,65,37]),("(2)",[75,25,91,37]),
                    ("a+1",[98,14,134,27]),("2",[111,36,121,49])]
    else:
        draw.text((40,28),"a",fill="black")
        draw.text((142,28),"b",fill="black")
        draw.rectangle([90,35,130,36],fill="black")
        if equal_sign:draw.rectangle([90,29,130,30],fill="black")
        elements = [("a=b" if equal_sign else "a-b",[40,26,152,45])]
    image.save(path)
    asset = {"asset_id":"synthetic","sha256":file_digest(path),"width":200,"height":80}
    lines,raw = [],[]
    for i,(text,box) in enumerate(elements):
        x1,y1,x2,y2 = box
        polygon = [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
        raw.append([polygon,text,.99])
        lines.append({"line_id":f"recovery/synthetic/scale1/{i}","text":text,"score":.99,
                      "bbox":box,"polygon":polygon,"asset_id":"synthetic","location":None})
    variant = {"variant_id":"scale1","scale":1,"contrast":1,"use_det":True,
               "crop_to_original":[[1,0,0],[0,1,0],[0,0,1]],"raw_ocr_result":raw,"ocr_lines":lines}
    probe = {"probe_id":"synthetic","asset_id":"synthetic","source_sha256":asset["sha256"],
             "source_size":[200,80],"crop_bbox":[0,0,200,80],"crop_sha256":file_digest(path),
             "location":None,"selected_variant_id":"scale1","variants":[variant]}
    payload = {"probes":[probe]}
    recovery = {"schema_version":"b-recovery-trial/0.1","artifact_id":"synthetic-recovery","revision":1,
                "book_id":"synthetic-book","scope_id":"synthetic-math","run_id":"synthetic-run",
                "payload":payload,"content_hash":digest(payload)}
    return asset,recovery,path


class RealMathLayoutRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout,cls.check,cls.crop = replay(FIXTURE)
        cls.recovery = json.loads((FIXTURE/"recovery-evidence.json").read_text(encoding="utf-8"))
        source = json.loads((FIXTURE/"source-descriptor.json").read_text(encoding="utf-8"))
        cls.asset = next(a for a in source["assets"] if a["asset_id"] == "viewer-173")

    def test_real_11_pixel_fraction_bars_and_17_tokens_are_accounted_once(self):
        payload = self.layout["payload"]
        self.assertEqual(len(payload["fraction_candidates"]),11)
        self.assertEqual(len(payload["reading_groups"]),3)
        self.assertEqual(Counter(r["status"] for r in payload["token_coverage"]),{
            "FRACTION_NUMERATOR":2,"FRACTION_DENOMINATOR":9,"BODY":5,"AMBIGUOUS":1})
        owned = [ref for row in payload["reading_groups"] for unit in row["units"] for ref in unit["ocr_refs"]]
        self.assertEqual(len(owned),17)
        self.assertEqual(len(set(owned)),17)
        self.assertTrue(self.check["geometry_and_token_coverage_valid"])
        self.assertEqual(self.check["decision"],"HOLD")

    def test_real_60_and_61_precede_nested_fraction_not_raised_numerator(self):
        row = self.layout["payload"]["reading_groups"][0]
        self.assertEqual([unit.get("raw_text") for unit in row["units"][:3]],
                         ["16.解：（1）60","61","(2)"])
        self.assertEqual(row["units"][3]["kind"],"fraction")
        fraction = next(f for f in self.layout["payload"]["fraction_candidates"] if f["fraction_id"] == row["units"][3]["fraction_id"])
        self.assertEqual(fraction["numerator"]["ocr_refs"],["recovery/unit2-q16/scale3/0"])
        self.assertEqual(fraction["numerator"]["raw_texts"],["a²+1"])
        self.assertEqual(fraction["denominator"]["raw_texts"],["2"])
        body_refs = [ref for unit in row["units"] if unit["kind"] == "body" for ref in unit["ocr_refs"]]
        self.assertNotIn("recovery/unit2-q16/scale3/0",body_refs)
        self.assertNotIn("recovery/unit2-q16/scale3/1",body_refs)

    def test_missing_formula_text_and_spanning_ocr_remain_explicit(self):
        payload = self.layout["payload"]
        self.assertEqual(sum(f["numerator"]["missing_ocr"] for f in payload["fraction_candidates"]),9)
        self.assertEqual(sum(f["denominator"]["missing_ocr"] for f in payload["fraction_candidates"]),2)
        spanning = [unit for row in payload["reading_groups"] for unit in row["units"] if unit["kind"] == "ambiguous_ocr_span"]
        self.assertEqual(len(spanning),1)
        self.assertEqual(spanning[0]["raw_text"],"a-la²+1")
        self.assertEqual(len(spanning[0]["linked_fraction_ids"]),2)
        self.assertEqual(payload["layout_status"],"PARTIAL")
        self.assertFalse(payload["formula_text_reconstructed"])
        self.assertFalse(payload["transcription_verified"])
        self.assertFalse(payload["visual_formula_references_consumed"])
        self.assertEqual(payload["platform_actions"],[])

    def test_input_is_immutable_and_exact_replay_ids_are_stable(self):
        before = copy.deepcopy(self.recovery)
        other = build_math_layout(self.asset,self.recovery,"unit2-q16",self.crop)
        self.assertEqual(self.recovery,before)
        self.assertEqual(other["content_hash"],self.layout["content_hash"])
        self.assertEqual(other["artifact_id"],self.layout["artifact_id"])
        selected = next(p for p in self.recovery["payload"]["probes"] if p["probe_id"] == "unit2-q16")
        variant = next(v for v in selected["variants"] if v["variant_id"] == "scale3")
        self.assertEqual(other["payload"]["source_ocr"],variant["ocr_lines"])

    def test_coordinated_missing_token_and_ledger_cannot_claim_coverage(self):
        layout = copy.deepcopy(self.layout)
        ref = "recovery/unit2-q16/scale3/5"
        for fraction in layout["payload"]["fraction_candidates"]:
            if ref in fraction["denominator"]["ocr_refs"]:
                fraction["denominator"]["ocr_refs"] = []
                fraction["denominator"]["raw_texts"] = []
        for row in layout["payload"]["reading_groups"]:
            for unit in row["units"]:unit["ocr_refs"] = [r for r in unit["ocr_refs"] if r != ref]
        layout["payload"]["token_coverage"] = [r for r in layout["payload"]["token_coverage"] if r["line_id"] != ref]
        rehash(layout)
        check = audit_math_layout(layout,self.asset,self.recovery,self.crop)
        self.assertFalse(check["geometry_and_token_coverage_valid"])
        self.assertIn("MATH_TOKEN_COVERAGE_MISMATCH",{i["code"] for i in check["issues"]})

    def test_bar_without_pixels_and_raised_fraction_order_tampering_are_rejected(self):
        for kind in ("pixels","order"):
            with self.subTest(kind=kind):
                layout = copy.deepcopy(self.layout)
                if kind == "pixels":
                    x,y = layout["payload"]["crop_bbox"][:2]
                    layout["payload"]["fraction_candidates"][0]["bar_bbox"] = [x+2,y+2,x+35,y+3]
                else:
                    row = layout["payload"]["reading_groups"][0]
                    row["units"].insert(0,row["units"].pop(3))
                rehash(layout)
                check = audit_math_layout(layout,self.asset,self.recovery,self.crop)
                self.assertFalse(check["geometry_and_token_coverage_valid"])

    def test_coordinated_role_swap_and_shifted_row_baselines_are_rejected(self):
        for kind in ("roles","rows"):
            with self.subTest(kind=kind):
                layout = copy.deepcopy(self.layout)
                if kind == "roles":
                    fraction = layout["payload"]["fraction_candidates"][0]
                    for key in ("ocr_refs","raw_texts"):
                        fraction["numerator"][key],fraction["denominator"][key] = fraction["denominator"][key],fraction["numerator"][key]
                    for row in layout["payload"]["token_coverage"]:
                        if row.get("fraction_id") == fraction["fraction_id"]:
                            row["status"] = "FRACTION_DENOMINATOR" if row["status"] == "FRACTION_NUMERATOR" else "FRACTION_NUMERATOR"
                    for row in layout["payload"]["reading_groups"]:
                        for unit in row["units"]:
                            if unit.get("fraction_id") == fraction["fraction_id"]:
                                unit["ocr_refs"] = fraction["numerator"]["ocr_refs"]+fraction["denominator"]["ocr_refs"]
                    expected = "MATH_ROLE_GEOMETRY_MISMATCH"
                else:
                    # Moving every row together preserves sorted order but
                    # breaks alignment to actual bars and source OCR centers.
                    for row in layout["payload"]["reading_groups"]:row["baseline_y"] += 100
                    expected = "MATH_ROW_BASELINE_MISMATCH"
                rehash(layout)
                check = audit_math_layout(layout,self.asset,self.recovery,self.crop)
                self.assertFalse(check["geometry_and_token_coverage_valid"])
                self.assertIn(expected,{issue["code"] for issue in check["issues"]})


class SyntheticMathLayoutRegression(unittest.TestCase):
    def test_known_fraction_forms_nested_unit_without_transcription_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            asset,recovery,path = synthetic(temporary)
            layout = build_math_layout(asset,recovery,"synthetic",path)
            self.assertEqual(len(layout["payload"]["fraction_candidates"]),1)
            fraction = layout["payload"]["fraction_candidates"][0]
            self.assertEqual(fraction["numerator"]["raw_texts"],["a+1"])
            self.assertEqual(fraction["denominator"]["raw_texts"],["2"])
            check = audit_math_layout(layout,asset,recovery,path)
            self.assertTrue(check["geometry_and_token_coverage_valid"])
            self.assertFalse(check["transcription_verified"])

    def test_minus_and_equal_signs_without_above_below_glyphs_are_not_fractions(self):
        for equal_sign in (False,True):
            with self.subTest(equal_sign=equal_sign),tempfile.TemporaryDirectory() as temporary:
                asset,recovery,path = synthetic(temporary,fraction=False,equal_sign=equal_sign)
                layout = build_math_layout(asset,recovery,"synthetic",path)
                self.assertEqual(layout["payload"]["fraction_candidates"],[])
                self.assertTrue(layout["payload"]["rejected_bar_candidates"])
                self.assertTrue(audit_math_layout(layout,asset,recovery,path)["geometry_and_token_coverage_valid"])

    def test_wrong_source_or_changed_crop_bytes_reject_before_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            asset,recovery,path = synthetic(temporary)
            for key,value in (("sha256","0"*64),("asset_id","foreign"),("width",201)):
                wrong = {**asset,key:value}
                with self.subTest(field=key),self.assertRaises(ValueError):
                    build_math_layout(wrong,recovery,"synthetic",path)
            path.write_bytes(path.read_bytes()+b"changed")
            with self.assertRaisesRegex(ValueError,"crop bytes changed"):
                build_math_layout(asset,recovery,"synthetic",path)

    def test_missing_engine_detection_is_not_filled_with_a_guessed_denominator(self):
        with tempfile.TemporaryDirectory() as temporary:
            asset,recovery,path = synthetic(temporary)
            variant = recovery["payload"]["probes"][0]["variants"][0]
            variant["raw_ocr_result"].pop()
            variant["ocr_lines"].pop()
            rehash(recovery)
            layout = build_math_layout(asset,recovery,"synthetic",path)
            self.assertEqual(len(layout["payload"]["fraction_candidates"]),1)
            fraction = layout["payload"]["fraction_candidates"][0]
            self.assertTrue(fraction["denominator"]["missing_ocr"])
            self.assertEqual(fraction["denominator"]["raw_texts"],[])
            self.assertIn("MATH_DENOMINATOR_OCR_MISSING",{i["code"] for i in layout["payload"]["issues"]})
            self.assertEqual(layout["payload"]["decision"],"HOLD")

    def test_changed_ocr_text_cannot_be_a_visual_formula_disguised_as_cpu(self):
        with tempfile.TemporaryDirectory() as temporary:
            asset,recovery,path = synthetic(temporary)
            recovery["payload"]["probes"][0]["variants"][0]["ocr_lines"][3]["text"] = "VISUAL-FORMULA-REFERENCE"
            rehash(recovery)
            with self.assertRaisesRegex(ValueError,"raw CPU output"):
                build_math_layout(asset,recovery,"synthetic",path)


class MathReplayInterface(unittest.TestCase):
    def test_replay_does_not_import_an_ocr_engine_or_read_visual_reference(self):
        original_import = __import__
        def no_ocr(name,*args,**kwargs):
            if name.split(".",1)[0] in {"rapidocr_onnxruntime","onnxruntime"}:raise AssertionError("new OCR request")
            return original_import(name,*args,**kwargs)
        with mock.patch("builtins.__import__",side_effect=no_ocr):
            layout,check,path = replay(FIXTURE)
        self.assertFalse(layout["payload"]["visual_formula_references_consumed"])
        self.assertEqual(check["fraction_candidates"],11)

    def test_cli_writes_layout_check_and_overlay_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)/"math"
            command = [sys.executable,str(ROOT/"tools/replay_math_b.py"),"--fixture",str(FIXTURE),"--out",str(out)]
            first = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding="utf-8",check=False)
            self.assertEqual(first.returncode,0,first.stderr)
            self.assertEqual(json.loads(first.stdout)["fraction_candidates"],11)
            self.assertEqual({p.name for p in out.iterdir()},{"math-layout.json","math-layout-check.json","math-layout.png"})
            before = {p.name:p.read_bytes() for p in out.iterdir()}
            second = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding="utf-8",check=False)
            self.assertNotEqual(second.returncode,0)
            self.assertEqual(before,{p.name:p.read_bytes() for p in out.iterdir()})


if __name__ == "__main__":unittest.main()
