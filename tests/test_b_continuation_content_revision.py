"""Source-bound correction of a mistaken model visual development reference.

The small mark is above/right of the last 5. These fixed pixels and geometry
support a development review correction, never independent human OCR gold.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from annotation.recognition.baseline import digest
from annotation.recognition.continuation_stage_quality import _content_lineage,ref

FIXTURE = ROOT/"tests/fixtures/book46007447"


def read(name): return json.loads((FIXTURE/name).read_text(encoding="utf8"))


class ContinuationContentRevisionTests(unittest.TestCase):
    def setUp(self):
        self.old = read("continuation-content-review.json")
        self.new = read("continuation-content-review-v2.json")
        self.raw = read("continuation-evidence.json")
        self.case = next(c for c in self.new["payload"]["line_checks"]if c["line_id"] == "resource-173/ocr/7")
        # Only prefix pixels are used by these lineage unit tests. Actual full
        # original SHA validation is the package inspector's separate contract.
        self.prefix = Image.open(FIXTURE/self.new["payload"]["capture"]["path"]).convert("RGB")
        self.addCleanup(self.prefix.close)
        self.original = Image.new("RGB",(1145,1620),"white")
        self.original.paste(self.prefix,(75,72))
        self.addCleanup(self.original.close)

    def validate(self,value=None): _content_lineage(value or self.new,self.old["input_refs"],self.original)

    def test_old_reference_and_full_archive_are_unchanged_and_transparent(self):
        text = (FIXTURE/"continuation-content-review.json").read_text(encoding="utf8")
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),"317c8a322aab7bf7b350d6402c6241b282f63601c302ea4d62f1685376e6fa12")
        self.assertEqual(self.new["revision"],2)
        lineage = self.new["payload"]["lineage"]
        self.assertEqual(lineage["previous_review_archive"],self.old)
        self.assertEqual(lineage["supersedes_ref"],ref(self.old))
        self.assertEqual(self.new["input_refs"],self.old["input_refs"]+[ref(self.old)])
        self.assertIn("√625=25",self.old["payload"]["line_checks"][-1]["observed_text"])
        self.assertIn("625=25²",self.case["observed_text"])
        self.assertNotIn("√",self.case["observed_text"])
        self.validate()

    def test_only_the_named_model_observation_and_difference_change(self):
        expected = copy.deepcopy(self.old["payload"])
        expected["line_checks"][-1]["observed_text"] = self.case["observed_text"]
        expected["line_checks"][-1]["differences"] = self.case["differences"]
        expected["lineage"] = self.new["payload"]["lineage"]
        self.assertEqual(self.new["payload"],expected)
        self.assertEqual(self.case["differences"],[{"kind":"SUPERSCRIPT_LOST","raw_fragment":"625=25","raw_text_span":[5,11],"observed_source_fragment":"625=25²"}])
        self.assertEqual(len(self.new["payload"]["line_checks"]),5)
        self.assertEqual(sum(len(c["differences"])for c in self.new["payload"]["line_checks"]),6)
        for key in ("human_verified","transcription_verified","business_acceptance"):
            self.assertIs(self.new["payload"][key],False)
        self.assertEqual(self.new["payload"]["reference_quality"],"MODEL_VISUAL_DEVELOPMENT_REVIEW")

    def test_source_pixels_locate_the_small_mark_above_right_of_final_digit(self):
        witness = self.new["payload"]["lineage"]["changes"][0]["source_geometry_witness"]
        self.assertEqual(witness["raised_component_bbox"],[180,214,184,220])
        self.assertEqual(witness["body_digit_bbox"],[173,216,179,226])
        region = witness["source_region_bbox"]
        a = np.asarray(self.original.convert("L").crop(region))
        _,_,stats,_ = cv2.connectedComponentsWithStats((a < witness["threshold"]).astype("uint8"),8)
        components = [[int(x)+region[0],int(y)+region[1],int(x+w)+region[0],int(y+h)+region[1]]for x,y,w,h,n in stats[1:]if n >= 2]
        self.assertIn([180,214,184,220],components)
        self.assertIn([173,216,179,226],components)
        raised,body = witness["raised_component_bbox"],witness["body_digit_bbox"]
        self.assertGreater(raised[0],body[2]);self.assertLess(raised[3],body[3])
        for prefix in ("source_region","raised_component","body_digit"):
            box = witness[prefix+"_bbox"]
            self.assertEqual(hashlib.sha256(self.original.crop(box).tobytes()).hexdigest(),witness[prefix+"_rgb_sha256"])

    def test_current_package_binds_new_revision_while_old_ocr_is_untouched(self):
        package = read("continuation-package.json")
        descriptor = package["documents"]["content_review"]
        self.assertEqual(descriptor["path"],"continuation-content-review-v2.json")
        self.assertEqual(descriptor["artifact_ref"],ref(self.new))
        text = (FIXTURE/descriptor["path"]).read_text(encoding="utf8")
        self.assertEqual(descriptor["text_sha256"],hashlib.sha256(text.encode()).hexdigest())
        line = next(l for l in self.raw["payload"]["ocr_lines"]if l["line_id"] == "resource-173/ocr/7")
        self.assertEqual(self.case["raw_text"],line["text"])
        self.assertIn("625=25，",line["text"])
        self.assertNotIn("25²",line["text"])
        self.assertEqual(self.new["content_hash"],digest(self.new["payload"]))

    def test_lineage_cannot_rewrite_source_raw_or_unlisted_case(self):
        for fault in ("raw","othercase","flags","archive"):
            with self.subTest(fault=fault):
                value = copy.deepcopy(self.new)
                if fault == "raw": value["payload"]["line_checks"][-1]["raw_text"] += "²"
                elif fault == "othercase": value["payload"]["line_checks"][0]["observed_text"] += "changed"
                elif fault == "flags": value["payload"]["human_verified"] = True
                else: value["payload"]["lineage"]["previous_review_archive"]["payload"]["human_verified"] = True
                value["content_hash"] = digest(value["payload"])
                with self.assertRaises(ValueError): self.validate(value)

    def test_lineage_requires_original_reference_and_explicit_changed_fields(self):
        for fault in ("oldref","inputref","field","reason"):
            with self.subTest(fault=fault):
                value = copy.deepcopy(self.new)
                if fault == "oldref": value["payload"]["lineage"]["supersedes_ref"]["artifact_id"] = "new-id"
                elif fault == "inputref": value["input_refs"].pop()
                elif fault == "field": value["payload"]["lineage"]["changes"][0]["changed_fields"].append("raw_text")
                else: value["payload"]["lineage"]["reason"] = ""
                with self.assertRaises(ValueError): self.validate(value)

    def test_wrong_side_or_white_witness_cannot_claim_raised_source_component(self):
        for fault in ("side","pixels"):
            value = copy.deepcopy(self.new);witness = value["payload"]["lineage"]["changes"][0]["source_geometry_witness"]
            if fault == "pixels": witness["raised_component_rgb_sha256"] = "0"*64
            else:
                witness["raised_component_bbox"] = [120,214,124,220]
                witness["raised_component_rgb_sha256"] = hashlib.sha256(self.original.crop(witness["raised_component_bbox"]).tobytes()).hexdigest()
            with self.assertRaises(ValueError): self.validate(value)


@unittest.skipUnless((ROOT.parent/"usense-readonly/source.json").is_file()
    and (ROOT.parent/"adjacent-source/46007447_resource_173.jpg").is_file(),
    "Real original JPGs are external; this test never downloads or recognizes")
class RealCurrentContentRevisionPipeline(unittest.TestCase):
    def test_current_v2_package_and_independent_check_keep_five_risks_without_changing_raw(self):
        sys.path.insert(0,str(ROOT/"tools"))
        from replay_recovery_b import replay
        from annotation.recognition.continuation_stage import (prepare_continuation_scope,build_continuation_stage_proof,
            apply_continuation_stage,load_continuation_package)
        from annotation.recognition.continuation_stage_quality import inspect_continuation_package,audit_continued_quality
        from annotation.recognition.continued_quality import build_continued_quality
        package_path = FIXTURE/"continuation-package.json"
        source = ROOT.parent/"usense-readonly/source.json"
        adjacent = ROOT.parent/"adjacent-source/46007447_resource_173.jpg"
        with patch.dict(sys.modules,{"rapidocr_onnxruntime":None,"onnxruntime":None,"rapid_latex_ocr":None}), \
             patch("socket.socket",side_effect=AssertionError("network forbidden")):
            loaded = load_continuation_package(package_path,source,adjacent)
            independently_loaded = inspect_continuation_package(package_path,source,adjacent)
            self.assertEqual(loaded,independently_loaded)
            self.assertEqual(loaded["documents"]["content_review"]["revision"],2)
            evidence,review,graph,_ = replay(FIXTURE)
            scope = prepare_continuation_scope(evidence,graph,package_path,source,adjacent)
            proof = build_continuation_stage_proof(scope,package_path,source,adjacent)
            applied = apply_continuation_stage(scope,proof,package_path,source,adjacent)
            kwargs = dict(package_path=package_path,source_path=source,adjacent_source_path=adjacent)
            checked = build_continued_quality(scope,proof,applied,review,**kwargs)
            integrity = audit_continued_quality(scope,proof,applied,review,checked,**kwargs)
        self.assertTrue(integrity["payload"]["accepted"],integrity["payload"]["issues"])
        differences = [issue for issue in checked["payload"]["issues"]if issue["code"] == "CONTINUATION_DEVELOPMENT_TRANSCRIPTION_DISAGREEMENT"]
        self.assertEqual(len(differences),5)
        row7 = next(issue for issue in differences if issue["evidence_refs"] == ["resource-173/ocr/7"])
        self.assertIn("625=25²",row7["detail"]["observed_text"])
        self.assertFalse(row7["detail"]["ocr_corrected"])
        fragment = next(fragment for answer in applied["payload"]["graph"]["payload"]["answers"]for fragment in answer["fragments"]
                        if fragment.get("parent_line_id") == "resource-173/ocr/7")
        raw = next(line for line in read("continuation-evidence.json")["payload"]["ocr_lines"]if line["line_id"] == "resource-173/ocr/7")
        self.assertEqual(fragment["text"],raw["text"])
        self.assertEqual(fragment["raw_text"],raw["text"])
        self.assertIn("625=25，",fragment["text"])
        self.assertEqual(checked["payload"]["decision"],"HOLD")
        self.assertFalse(checked["payload"]["business_acceptance"])


if __name__ == "__main__": unittest.main()
