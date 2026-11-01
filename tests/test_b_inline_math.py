"""Generated inline math geometry and loss-preserving proposal regressions."""
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from annotation.recognition.baseline import digest
from annotation.recognition.inline_ocr import collect_inline_observations
from annotation.recognition.inline_math import build_inline_math_layout, mathlike_spans
from test_b_continuation_stage import make_continuation_fixture


def raw_row(text, width, height, *, words=None):
    words = list(text) if words is None else words
    step = (width-4)/max(1, len(words))
    boxes = [[[2+i*step, 2], [2+(i+1)*step, 2], [2+(i+1)*step, height-2], [2+i*step, height-2]]
             for i in range(len(words))]
    return [[[0, 0], [width, 0], [width, height], [0, height]], text, .9, boxes, words, [.9]*len(words)]


class InlineMathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.f = make_continuation_fixture(self.root)
        self.evidence = self.f["evidence"]
        self.original = self.root / "source-page.png"
        self.line_ids = [line["line_id"] for line in self.evidence["payload"]["pages"][0]["ocr_lines"]]
        self.asset_id = self.evidence["payload"]["pages"][0]["asset_id"]

    def observations(self, texts=None, mutate=None, line_ids=None):
        line_ids = self.line_ids if line_ids is None else line_ids
        texts = texts or ["中文AB=82+（8+12）²=464，10十5=15，625=252", "没有数学内容"]
        calls = []
        def recognizer(bgr, **flags):
            self.assertTrue(flags["return_word_box"])
            self.assertTrue(flags["use_det"])
            self.assertFalse(flags["use_cls"])
            text = texts[min(len(calls)//2, len(texts)-1)]
            row = raw_row(text, bgr.shape[1], bgr.shape[0])
            calls.append(True)
            rows = mutate(row) if mutate else [row]
            return rows, [.01, 0, .02]
        return collect_inline_observations(self.evidence, self.original, asset_id=self.asset_id,
                                           line_ids=line_ids, recognizer=recognizer)

    def layout(self, obs=None, line_ids=None):
        return build_inline_math_layout(self.evidence, obs or self.observations(), self.original,
                                        line_ids=self.line_ids if line_ids is None else line_ids)

    def rehash(self, value):
        value["content_hash"] = digest(value["payload"])
        return value

    def test_raw_runs_keep_fullwidth_context_and_do_not_repair_operators_or_missing_powers(self):
        text = "由定理得AB=82+（8+12）²=464，10十5=15，625=252"
        runs = [text[a:b] for a, b in mathlike_spans(text)]
        self.assertEqual(runs, ["AB=82+（8+12）²=464", "10十5=15", "625=252"])
        self.assertNotIn("10+5", "".join(runs))
        self.assertNotIn("√625", "".join(runs))
        text = "十，A十B，1十2，1十A"
        self.assertEqual([text[a:b] for a, b in mathlike_spans(text)], ["A", "B", "1十2", "1", "A"])

    def test_complete_declared_scope_all_variants_and_full_archive_survive_without_selection(self):
        obs = self.observations()
        before = copy.deepcopy((self.evidence, obs))
        result = self.layout(obs)
        p = result["payload"]
        self.assertEqual(p["counts"], dict(declared_rows=2, variants=4, raw_rows=4, mathlike_runs=6,
                                          full_line_fallbacks=4, units=10))
        self.assertEqual(p["observations_archive"], obs)
        self.assertEqual(p["requested_line_ids"], self.line_ids)
        self.assertEqual(p["selected_unit_ids"], [])
        self.assertEqual(p["model_calls"], 0)
        self.assertFalse(p["expected_text_consumed"])
        self.assertFalse(p["graph_modified"])
        self.assertFalse(p["complete"])
        self.assertFalse(p["transcription_verified"])
        self.assertFalse(p["business_acceptance"])
        self.assertEqual(p["platform_actions"], [])
        self.assertEqual(p["decision"], "HOLD")
        self.assertEqual(before, (self.evidence, obs))
        self.assertNotIn("created_at", result)
        self.assertEqual(result, self.layout(obs))

    def test_rois_use_full_saved_row_height_fixed_source_halo_and_actual_pixel_crops(self):
        obs = self.observations()
        layout = self.layout(obs)
        by_line = {row["line_id"]: row for row in obs["payload"]["rows"]}
        with Image.open(self.original) as opened:
            image = opened.convert("RGB")
        for unit in layout["payload"]["units"]:
            row = by_line[unit["line_id"]]
            roi, crop = unit["source_bbox"], row["crop_bbox"]
            self.assertEqual([roi[1], roi[3]], [crop[1], crop[3]])
            self.assertEqual(unit["horizontal_halo_source_pixels"], max(4, crop[3]-crop[1]))
            self.assertEqual(unit["crop_rgb_sha256"], hashlib.sha256(image.crop(roi).tobytes()).hexdigest())
            self.assertEqual(unit["crop_size"], [roi[2]-roi[0], roi[3]-roi[1]])
            self.assertFalse(unit["precise_glyph_localization"])
            self.assertFalse(unit["spatial_role_verified"])
            self.assertFalse(unit["complete"])
            self.assertFalse(unit["selected"])
            if unit["kind"] == "MATHLIKE_RUN":
                core, halo = unit["core_source_bbox"], unit["horizontal_halo_source_pixels"]
                self.assertEqual(roi[0], max(0, math.floor(core[0])-halo))
                self.assertEqual(roi[2], min(image.width, math.ceil(core[2])+halo))
            else:
                self.assertEqual(roi, crop)
            self.assertIn("MISSING_GLYPH_NOT_LOCALIZED", unit["risks"])

    def test_all_weak_tokens_and_overlapping_duplicate_raw_rows_remain_distinct(self):
        obs = self.observations(["4，A，cm"], lambda row: [row, copy.deepcopy(row)], line_ids=self.line_ids[:1])
        layout = self.layout(obs, self.line_ids[:1])
        units = layout["payload"]["units"]
        self.assertEqual(layout["payload"]["counts"]["mathlike_runs"], 12)
        self.assertEqual(layout["payload"]["counts"]["full_line_fallbacks"], 2)
        self.assertEqual(len(set(u["unit_id"] for u in units)), 14)
        self.assertEqual({u["raw_text"] for u in units if u["kind"] == "MATHLIKE_RUN"}, {"4", "A", "cm"})
        self.assertEqual({u["raw_result_index"] for u in units if u["kind"] == "MATHLIKE_RUN"}, {0, 1})

    def test_chinese_ten_is_a_risk_bearing_verbatim_candidate_only(self):
        units = self.layout()["payload"]["units"]
        ten = [u for u in units if u["raw_text"] == "10十5=15"]
        self.assertEqual(len(ten), 2)
        self.assertTrue(all("CHINESE_TEN_OPERATOR_LOOKALIKE_UNRESOLVED" in u["risks"] for u in ten))

    def test_empty_raw_output_still_retains_each_whole_line_fallback(self):
        obs = self.observations(mutate=lambda row: [])
        p = self.layout(obs)["payload"]
        self.assertEqual(p["counts"]["raw_rows"], 0)
        self.assertEqual(p["counts"]["mathlike_runs"], 0)
        self.assertEqual(p["counts"]["full_line_fallbacks"], 4)
        self.assertEqual(p["observations_archive"], obs)

    def test_length_mismatch_preserves_raw_arrays_and_does_not_zip_away_missing_symbols(self):
        def broken(row):
            row[3].pop()
            return [row]
        obs = self.observations(mutate=broken)
        p = self.layout(obs)["payload"]
        self.assertEqual(p["counts"]["mathlike_runs"], 0)
        self.assertEqual(p["counts"]["full_line_fallbacks"], 4)
        self.assertEqual(p["observations_archive"], obs)
        self.assertTrue(all(v["issues"][0]["code"] == "RAW_CHARACTER_ALIGNMENT_UNRESOLVED_FULL_LINE_RETAINED"
                            for row in p["rows"] for v in row["variants"]))

    def test_unusable_word_geometry_keeps_math_run_with_explicit_full_line_fallback(self):
        def broken(row):
            row[3] = [None]*len(row[3])
            return [row]
        p = self.layout(self.observations(mutate=broken))["payload"]
        runs = [u for u in p["units"] if u["kind"] == "MATHLIKE_RUN"]
        self.assertEqual(len(runs), 6)
        for u in runs:
            self.assertIsNone(u["core_source_bbox"])
            self.assertIn("UNLOCATED_MATH_RUN_FULL_LINE_FALLBACK", u["risks"])
            row = next(r for r in p["rows"] if r["line_id"] == u["line_id"])
            self.assertEqual(u["source_bbox"], row["crop_bbox"])

    def test_degenerate_estimates_and_low_scores_are_retained_as_uncertain(self):
        def weak(row):
            row[3] = [[[8, 8]]*4 for _ in row[3]]
            row[5] = [.1]*len(row[5])
            return [row]
        runs = [u for u in self.layout(self.observations(mutate=weak))["payload"]["units"] if u["kind"] == "MATHLIKE_RUN"]
        self.assertEqual(len(runs), 6)
        self.assertTrue(all("CTC_DEGENERATE_WORD_ESTIMATE" in u["risks"] and "LOW_CHARACTER_SCORE" in u["risks"] for u in runs))

    def test_multicharacter_word_tokens_keep_codepoint_span_and_original_word_indices(self):
        def tokens(row):
            width, height = row[0][2]
            return [raw_row("AB=2", width, height, words=["AB", "=", "2"])]
        obs = self.observations(["AB=2"], tokens, line_ids=self.line_ids[:1])
        runs = [u for u in self.layout(obs, self.line_ids[:1])["payload"]["units"] if u["kind"] == "MATHLIKE_RUN"]
        self.assertEqual(len(runs), 2)
        self.assertTrue(all(u["char_span"] == [0, 4] and u["raw_word_indices"] == [0, 1, 2] for u in runs))

    def test_external_declared_scope_cannot_be_shrunk_reordered_or_duplicated(self):
        obs = self.observations()
        for ids in (self.line_ids[:1], list(reversed(self.line_ids)), self.line_ids+self.line_ids[:1], []):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.layout(obs, ids)

    def test_same_page_sha_does_not_allow_a_different_raw_source_line(self):
        obs = self.observations()
        changed = copy.deepcopy(self.evidence)
        changed["payload"]["pages"][0]["ocr_lines"][0]["text"] = "another unverified original observation"
        self.rehash(changed)
        obs["payload"]["evidence_ref"] = {key: changed[key] for key in ("artifact_id", "revision", "content_hash")}
        obs["input_refs"] = [obs["payload"]["evidence_ref"]]
        self.rehash(obs)
        with self.assertRaisesRegex(ValueError, "row binding"):
            build_inline_math_layout(changed, obs, self.original, line_ids=self.line_ids)

    def test_crop_or_transform_single_field_changes_are_rejected_even_after_payload_rehash(self):
        for field in ("crop_rgb_sha256", "variant_to_original", "bgr_sha256"):
            obs = self.observations()
            if field == "crop_rgb_sha256": obs["payload"]["rows"][0][field] = "0"*64
            elif field == "variant_to_original": obs["payload"]["rows"][0]["variants"][0][field][0][2] += 1
            else: obs["payload"]["rows"][0]["variants"][0][field] = "0"*64
            self.rehash(obs)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.layout(obs)

    def test_original_byte_change_is_rejected_even_when_decoder_pixels_are_unchanged(self):
        obs = self.observations()
        self.original.write_bytes(self.original.read_bytes()+b" ")
        with self.assertRaisesRegex(ValueError, "SHA"):
            self.layout(obs)

    def test_cached_layout_fresh_process_forbids_models_network_and_review_reads(self):
        obs = self.observations()
        for name, value in (("evidence-cache.json", self.evidence), ("inline-cache.json", obs)):
            (self.root/name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        script = r'''
import importlib.abc,json,socket,sys
from pathlib import Path
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'rapidocr_onnxruntime','rapid_latex_ocr','onnxruntime','torch','paddle','requests','httpx','aiohttp'}:
   raise AssertionError('forbidden model import '+fullname)
sys.meta_path.insert(0,NoModels())
class OfflineSocket(socket.socket):
 def connect(self,*a,**k):raise AssertionError('network forbidden')
 def connect_ex(self,*a,**k):raise AssertionError('network forbidden')
socket.socket=OfflineSocket
socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network forbidden'))
sys.path.insert(0,sys.argv[1])
from annotation.recognition.inline_math import build_inline_math_layout
root=Path(sys.argv[2])
e=json.loads((root/'evidence-cache.json').read_text(encoding='utf-8'))
o=json.loads((root/'inline-cache.json').read_text(encoding='utf-8'))
read=Path.read_text
def no_review(self,*a,**k):
 if 'review' in self.name:raise AssertionError('transcription review read')
 return read(self,*a,**k)
Path.read_text=no_review
result=build_inline_math_layout(e,o,root/'source-page.png',line_ids=o['payload']['requested_line_ids'])
print(json.dumps(result['payload']['counts']))
'''
        child = subprocess.run([sys.executable, "-c", script, str(ROOT/"src"), str(self.root)], cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(child.returncode, 0, child.stdout+child.stderr)
        self.assertEqual(json.loads(child.stdout)["units"], 10)


if __name__ == "__main__":
    unittest.main()
