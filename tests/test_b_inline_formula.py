"""Portable inline formula collection, recovery and loss-preserving candidates.

All source pixels are generated and both OCR callbacks are SYNTHETIC_TEST.
No actual OCR/LaTeX model, network request or platform action is used.
"""
from contextlib import closing
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tests")]
from annotation.recognition import batch
from annotation.recognition.baseline import digest
from annotation.recognition.inline_ocr import collect_inline_observations
from annotation.recognition.inline_math import build_inline_math_layout
from annotation.recognition.inline_formula import collect_inline_formula, plan_inline_formula_calls
from annotation.recognition.inline_candidates import build_inline_candidates
from test_b_continuation_stage import make_continuation_fixture
from test_b_inline_math import raw_row


class FormulaWorker:
    """Inspectable synthetic callback with stable semantic cache identity."""
    def __init__(self, outputs=("1:3",), *, fail_once=False):
        self.outputs = tuple(outputs)
        self.cache_identity = {"fixture": "inline-formula-tensor-only/0.1", "outputs": list(outputs)}
        self.fail_once = fail_once
        self.calls = []

    def __call__(self, tensor):
        if not isinstance(tensor, np.ndarray) or tensor.dtype != np.float32 or tensor.ndim != 4 or tensor.shape[:2] != (1, 1):
            raise AssertionError("the formula callback must receive only one float32 NCHW tensor")
        self.calls.append(hashlib.sha256(tensor.tobytes()).hexdigest())
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("explicit transient synthetic failure")
        return self.outputs[(len(self.calls)-1) % len(self.outputs)], .001


class BadElapsedFormulaWorker(FormulaWorker):
    def __call__(self, tensor):
        raw, _ = super().__call__(tensor)
        return raw, -1


def formula_fixture(directory, *, invalid_word_boxes=False, math_text="4，A，cm，1:3，625=25²，10十5"):
    fixture = make_continuation_fixture(directory)
    evidence = fixture["evidence"]
    original = Path(directory)/"source-page.png"
    page = evidence["payload"]["pages"][0]
    line_ids = [page["ocr_lines"][0]["line_id"]]
    def recognizer(bgr, **flags):
        row = raw_row(math_text, bgr.shape[1], bgr.shape[0])
        if invalid_word_boxes: row[3] = [None]*len(row[3])
        return [row], [.01, 0, .02]
    observed = collect_inline_observations(evidence, original, asset_id=page["asset_id"], line_ids=line_ids, recognizer=recognizer)
    layout = build_inline_math_layout(evidence, observed, original, line_ids=line_ids)
    return dict(evidence=evidence, layout=layout, original=original, line_ids=line_ids)


class InlineFormulaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.f = formula_fixture(self.root)
        self.work = self.root/"formula-work"

    def collect(self, worker, **kwargs):
        return collect_inline_formula(self.f["evidence"], self.f["layout"], self.f["original"], self.work,
            line_ids=self.f["line_ids"], recognizer=worker, **kwargs)

    def plan(self):
        return plan_inline_formula_calls(self.f["evidence"], self.f["layout"], self.f["original"], line_ids=self.f["line_ids"])[1]

    def assert_hold(self, artifact):
        p = artifact["payload"]
        self.assertEqual(p["decision"], "HOLD")
        self.assertFalse(p["complete"])
        self.assertFalse(p["transcription_verified"])
        self.assertFalse(p["business_acceptance"])
        self.assertFalse(p["expected_text_consumed"])
        self.assertFalse(p["graph_modified"])
        self.assertEqual(p["platform_actions"], [])

    def test_plan_keeps_all_eligible_contexts_variants_and_explicit_skipped_units(self):
        plan = self.plan()
        units = self.f["layout"]["payload"]["units"]
        eligible = {u["unit_id"] for u in units if u["raw_text"] in {"1:3", "625=25²", "10十5"}}
        actual = {b["unit_id"] for call in plan["calls"] for b in call["unit_bindings"]}
        self.assertEqual(actual, eligible)
        skipped = {u["unit_id"]: u for u in plan["not_inference_units"]}
        self.assertEqual(set(skipped), {u["unit_id"] for u in units}-eligible)
        for u in units:
            if u["unit_id"] in skipped:
                self.assertFalse(skipped[u["unit_id"]]["inference_performed"])
                self.assertTrue(skipped[u["unit_id"]]["reason"])
        keys = [(tuple(c["source_bbox"]), c["canvas_variant"]["variant_id"]) for c in plan["calls"]]
        self.assertEqual(len(keys), len(set(keys)))
        for uid in eligible:
            variants = {(b["region_variant"], c["canvas_variant"]["variant_id"]) for c in plan["calls"]
                        for b in c["unit_bindings"] if b["unit_id"] == uid}
            self.assertEqual(variants, {(context, variant) for context in ("CORE_CONTEXT_PAD2", "HALO")
                                       for variant in ("gray-native", "gray-scale3")})
        rows = {r["line_id"]: r for r in self.f["layout"]["payload"]["rows"]}
        for call in plan["calls"]:
            row = rows[call["unit_bindings"][0]["line_id"]]
            self.assertEqual([call["source_bbox"][1], call["source_bbox"][3]], [row["crop_bbox"][1], row["crop_bbox"][3]])
            self.assertFalse(call["source_glyph_complete"])

    def test_isolated_digit_ten_digit_is_kept_as_uncertain_without_replacing_the_raw_character(self):
        plan = self.plan()
        units = {u["unit_id"]: u for u in self.f["layout"]["payload"]["units"]}
        bound_ten_units = {b["unit_id"] for c in plan["calls"] for b in c["unit_bindings"]
                           if units[b["unit_id"]]["raw_text"] == "10十5"}
        self.assertEqual(len(bound_ten_units), 2)
        self.assertTrue(all("CHINESE_TEN_OPERATOR_LOOKALIKE_UNRESOLVED" in units[uid]["risks"] for uid in bound_ten_units))

    def test_pure_variable_and_superscript_equations_are_eligible_while_plain_labels_stay_skipped(self):
        f = formula_fixture(self.root/"variable-equations", math_text="A，cm，a²+b²=c²，x+y=z")
        _, plan = plan_inline_formula_calls(f["evidence"], f["layout"], f["original"], line_ids=f["line_ids"])
        units = {u["unit_id"]: u for u in f["layout"]["payload"]["units"]}
        inferred = {units[b["unit_id"]]["raw_text"] for c in plan["calls"] for b in c["unit_bindings"]}
        self.assertEqual(inferred, {"a²+b²=c²", "x+y=z"})
        skipped = {s["raw_text"] for s in plan["not_inference_units"]}
        self.assertTrue({"A", "cm"}.issubset(skipped))

    def test_zero_eligible_units_do_not_initialize_or_read_a_formula_model(self):
        f = formula_fixture(self.root/"no-eligible", math_text="图4，A，cm，只有中文")
        work = self.root/"no-eligible-work"
        with patch("annotation.recognition.inline_formula._local_cpu_backend", side_effect=AssertionError("no model may load")) as backend:
            observed, report = collect_inline_formula(f["evidence"], f["layout"], f["original"], work,
                                                     line_ids=f["line_ids"])
            backend.assert_not_called()
        self.assertEqual(report["payload"]["state"], "READY")
        self.assertEqual(report["payload"]["counts"]["declared_calls"], 0)
        self.assertEqual(report["payload"]["counts"]["new_encoder_decoder_calls"], 0)
        self.assertEqual(report["payload"]["model_initializations"], 0)
        self.assertEqual(observed["payload"]["calls"], [])
        self.assertTrue(observed["payload"]["not_inference_units"])
        built = build_inline_candidates(observed)
        self.assertEqual(built["payload"]["candidates"], [])
        self.assertEqual(built["payload"]["not_inference_units"], observed["payload"]["not_inference_units"])
        for value in (observed, report, built): self.assert_hold(value)

    def test_partial_resume_and_warm_cache_keep_full_scope_and_stable_observation(self):
        worker = FormulaWorker()
        total = len(self.plan()["calls"])
        self.assertGreater(total, 2)
        first, first_report = self.collect(worker, max_items=2)
        self.assertEqual(first_report["payload"]["state"], "PARTIAL")
        self.assertEqual(first_report["payload"]["counts"]["declared_calls"], total)
        self.assertEqual(first_report["payload"]["counts"]["new_encoder_decoder_calls"], 2)
        self.assertEqual(len(first["payload"]["calls"]), total)
        self.assertEqual(sum(c["state"] == "PENDING" for c in first["payload"]["calls"]), total-2)
        partial_candidates = build_inline_candidates(first)
        self.assertEqual(len(partial_candidates["payload"]["candidates"]), total)
        self.assertTrue(any(c["raw_latex"] is None for c in partial_candidates["payload"]["candidates"]))
        final, final_report = self.collect(worker)
        self.assertEqual(final_report["payload"]["state"], "READY")
        self.assertEqual(final_report["payload"]["counts"]["cache_hits"], 2)
        self.assertEqual(final_report["payload"]["counts"]["new_attempts"], total-2)
        self.assertEqual(len(worker.calls), total)
        warm, warm_report = self.collect(worker)
        self.assertEqual(warm, final)
        self.assertEqual(warm_report["payload"]["counts"]["cache_hits"], total)
        self.assertEqual(warm_report["payload"]["counts"]["new_encoder_decoder_calls"], 0)
        self.assertEqual(len(worker.calls), total)
        self.assertNotEqual(warm_report["payload"]["run_id"], final_report["payload"]["run_id"])
        for artifact in (first, first_report, final, final_report, warm, warm_report):
            self.assert_hold(artifact)
            self.assertEqual(artifact["producer"]["execution_kind"], "SYNTHETIC_TEST")
        self.assertEqual(final["payload"]["layout_archive"], self.f["layout"])

    def test_corrupt_single_call_object_retries_only_it_and_keeps_bad_bytes(self):
        worker = FormulaWorker()
        _, report = self.collect(worker)
        total = report["payload"]["counts"]["declared_calls"]
        old = {c["call_id"]: c["output"] for c in report["payload"]["calls"]}
        broken_call = report["payload"]["calls"][0]["call_id"]
        broken = self.work/old[broken_call]["path"]
        broken.write_bytes(b"CORRUPTED IMMUTABLE CALL REMAINS FOR DIAGNOSIS")
        _, restored = self.collect(worker)
        p = restored["payload"]
        self.assertEqual(p["state"], "READY")
        self.assertEqual(p["counts"]["new_attempts"], 1)
        self.assertEqual(p["counts"]["invalidated"], 1)
        self.assertEqual(p["counts"]["cache_hits"], total-1)
        self.assertEqual(len(worker.calls), total+1)
        self.assertEqual(broken.read_bytes(), b"CORRUPTED IMMUTABLE CALL REMAINS FOR DIAGNOSIS")
        for row in p["calls"]:
            if row["call_id"] != broken_call: self.assertEqual(row["output"], old[row["call_id"]])

    def test_failed_call_is_retained_not_cached_and_is_retried_once(self):
        worker = FormulaWorker(fail_once=True)
        observed, report = self.collect(worker)
        total = report["payload"]["counts"]["declared_calls"]
        self.assertEqual(report["payload"]["state"], "FAILED")
        failed = next(c for c in observed["payload"]["calls"] if c["state"] == "FAILED")
        self.assertEqual(failed["observation"]["payload"]["recognition_error"]["type"], "RuntimeError")
        failed_receipt = next(c for c in report["payload"]["calls"] if c["state"] == "FAILED")
        failed_path = self.work/failed_receipt["output"]["path"]
        failed_bytes = failed_path.read_bytes()
        candidates = build_inline_candidates(observed)
        self.assertEqual(len(candidates["payload"]["candidates"]), total)
        self.assertTrue(any(i["code"] == "INLINE_FORMULA_CALL_NOT_DONE" for i in candidates["payload"]["issues"]))
        with closing(sqlite3.connect(self.work/"inline-formula.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM cache WHERE attempt_id=?", (failed_receipt["origin_attempt_id"],)).fetchone()[0], 0)
        recovered, retried = self.collect(worker)
        self.assertEqual(retried["payload"]["state"], "READY")
        self.assertEqual(retried["payload"]["counts"]["cache_hits"], total-1)
        self.assertEqual(retried["payload"]["counts"]["new_attempts"], 1)
        self.assertTrue(all(c["state"] == "DONE" for c in recovered["payload"]["calls"]))
        self.assertEqual(failed_path.read_bytes(), failed_bytes)

    def test_received_raw_string_survives_an_invalid_elapsed_failure_without_becoming_cached_success(self):
        observed, report = self.collect(BadElapsedFormulaWorker())
        self.assertEqual(report["payload"]["state"], "FAILED")
        for call in observed["payload"]["calls"]:
            self.assertEqual(call["state"], "FAILED")
            payload = call["observation"]["payload"]
            self.assertEqual(payload["raw_latex"], "1:3")
            self.assertEqual(payload["decoded_text"], "1:3")
            self.assertEqual(payload["raw_backend_elapsed_seconds"], -1)
            self.assertIsNone(payload["engine_elapsed_seconds"])
            self.assertIsNotNone(payload["recognition_error"])
        with closing(sqlite3.connect(self.work/"inline-formula.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM cache").fetchone()[0], 0)
        built = build_inline_candidates(observed)
        self.assertTrue(all(c["raw_latex"] == "1:3" and c["state"] == "FAILED" and c["selected"] is False
                            for c in built["payload"]["candidates"]))

    def test_missing_start_or_success_origin_event_invalidates_only_its_call(self):
        for event_kind in ("STARTED", "SUCCEEDED"):
            with self.subTest(event=event_kind):
                self.work = self.root/("missing-"+event_kind)
                worker = FormulaWorker()
                _, first = self.collect(worker)
                old = first["payload"]["calls"][0]
                total = first["payload"]["counts"]["declared_calls"]
                old_path = self.work/old["output"]["path"]
                old_bytes = old_path.read_bytes()
                with closing(sqlite3.connect(self.work/"inline-formula.sqlite3")) as db:
                    deleted = db.execute("DELETE FROM events WHERE attempt_id=? AND kind=?",
                        (old["origin_attempt_id"], event_kind)).rowcount
                    db.commit()
                self.assertEqual(deleted, 1)
                _, recovered = self.collect(worker)
                p = recovered["payload"]
                self.assertEqual(p["state"], "READY")
                self.assertEqual(p["counts"]["new_attempts"], 1)
                self.assertEqual(p["counts"]["invalidated"], 1)
                self.assertEqual(p["counts"]["cache_hits"], total-1)
                replaced = next(c for c in p["calls"] if c["call_id"] == old["call_id"])
                self.assertNotEqual(replaced["origin_attempt_id"], old["origin_attempt_id"])
                self.assertFalse(replaced["cached"])
                self.assertEqual(len(worker.calls), total+1)
                self.assertEqual(old_path.read_bytes(), old_bytes)

    def test_candidates_keep_ratio_radical_power_and_unsupported_raw_without_selection(self):
        alternatives = ("1:3", r"\sqrt{625}=25", "625=25^{2}", r"\unknown{2}+\sqrt{625}+中文")
        observed, _ = self.collect(FormulaWorker(alternatives))
        candidates = build_inline_candidates(observed)
        self.assert_hold(candidates)
        p = candidates["payload"]
        self.assertEqual(p["observations_archive"], observed)
        self.assertEqual(p["selected_candidate_refs"], [])
        self.assertFalse(p["entire_answer_reconstructed"])
        by_raw = {c["raw_latex"]: c["parse_result"] for c in p["candidates"]}
        self.assertEqual(set(by_raw), set(alternatives))
        self.assertEqual([item["value"] for item in by_raw["1:3"]["ast"]["items"]], ["1", ":", "3"])
        self.assertNotEqual(by_raw[r"\sqrt{625}=25"]["normalized_ast"], by_raw["625=25^{2}"]["normalized_ast"])
        unsupported = by_raw[alternatives[-1]]
        self.assertFalse(unsupported["supported"])
        self.assertEqual(unsupported["unparsed_tail"], alternatives[-1])
        self.assertTrue(all(c["selected"] is False and c["complete"] is False for c in p["candidates"]))
        self.assertTrue(all(u["selected_candidate_refs"] == [] for u in p["units"]))

    def test_same_roi_dedup_preserves_all_context_bindings_but_not_duplicate_candidate_refs(self):
        f = formula_fixture(self.root/"unlocated", invalid_word_boxes=True)
        _, plan = plan_inline_formula_calls(f["evidence"], f["layout"], f["original"], line_ids=f["line_ids"])
        self.assertEqual(len(plan["calls"]), 2)
        self.assertTrue(all(len(c["unit_bindings"]) > 1 for c in plan["calls"]))
        observed, _ = collect_inline_formula(f["evidence"], f["layout"], f["original"], self.root/"dedup-work",
            line_ids=f["line_ids"], recognizer=FormulaWorker())
        built = build_inline_candidates(observed)
        self.assertEqual(len(built["payload"]["candidates"]), 2)
        for unit in built["payload"]["units"]:
            self.assertEqual(len(unit["candidate_refs"]), len(set(unit["candidate_refs"])))
        self.assertEqual(built["payload"]["not_inference_units"], plan["not_inference_units"])

    def test_changed_roi_or_external_source_scope_rejects_before_any_formula_call(self):
        worker = FormulaWorker()
        for fault in ("roi", "evidence", "scope", "original"):
            f = copy.deepcopy(self.f)
            if fault == "roi":
                f["layout"]["payload"]["units"][0]["source_bbox"][0] += 1
                f["layout"]["content_hash"] = digest(f["layout"]["payload"])
            elif fault == "evidence":
                f["evidence"]["payload"]["pages"][0]["ocr_lines"][0]["text"] += "changed"
                f["evidence"]["content_hash"] = digest(f["evidence"]["payload"])
            elif fault == "scope": f["line_ids"] = []
            else: f["original"].write_bytes(f["original"].read_bytes()+b" ")
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                collect_inline_formula(f["evidence"], f["layout"], f["original"], self.work,
                    line_ids=f["line_ids"], recognizer=worker)
            self.assertEqual(worker.calls, [])
            self.assertFalse(self.work.exists())

    def test_invalid_budget_never_initializes_models_or_workdir(self):
        for value in (0, -1, True, 1.2, "2"):
            with self.subTest(value=value), patch("annotation.recognition.inline_formula._local_cpu_backend") as backend:
                with self.assertRaises(ValueError):
                    collect_inline_formula(self.f["evidence"], self.f["layout"], self.f["original"], self.work,
                        line_ids=self.f["line_ids"], max_items=value)
                backend.assert_not_called()
        self.assertFalse(self.work.exists())

    def test_input_change_during_synthetic_collection_is_explicit_failure_not_ready(self):
        for fault in ("source_bytes", "source_deleted", "layout"):
            with self.subTest(fault=fault):
                f = formula_fixture(self.root/fault)
                before = copy.deepcopy(f["layout"])
                worker = FormulaWorker()
                def mutate(tensor):
                    result = worker(tensor)
                    if len(worker.calls) == 1:
                        if fault == "source_bytes": f["original"].write_bytes(f["original"].read_bytes()+b" ")
                        elif fault == "source_deleted": f["original"].unlink()
                        else: f["layout"]["payload"]["units"][0]["source_bbox"][0] += 1
                    return result
                observed, report = collect_inline_formula(f["evidence"], f["layout"], f["original"], self.root/(fault+"-work"),
                    line_ids=f["line_ids"], recognizer=mutate)
                self.assertEqual(report["payload"]["state"], "FAILED")
                self.assertTrue(observed["payload"]["input_changed_during_execution"])
                self.assertFalse(observed["payload"]["run_complete"])
                self.assertEqual(observed["payload"]["layout_archive"], before)
                self.assertEqual(report["payload"]["layout_ref"], {k: before[k] for k in ("artifact_id", "revision", "content_hash")})
                if fault == "source_deleted": self.assertIsNone(report["payload"]["original_sha256_after"])
                self.assert_hold(observed)

    def test_real_process_death_after_call_publication_keeps_orphan_and_resumes_with_no_models(self):
        for name, value in (("evidence.json", self.f["evidence"]), ("layout.json", self.f["layout"])):
            (self.root/name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        script = self.root/"inline-process.py"
        script.write_text(textwrap.dedent(f'''
            import importlib.abc,json,os,socket,sys
            from pathlib import Path
            class NoModels(importlib.abc.MetaPathFinder):
                def find_spec(self,fullname,path=None,target=None):
                    if fullname.split('.')[0] in {{'rapidocr_onnxruntime','rapid_latex_ocr','onnxruntime','torch','paddle','requests','httpx','aiohttp'}}:
                        raise AssertionError('forbidden formula runtime '+fullname)
            sys.meta_path.insert(0,NoModels())
            class OfflineSocket(socket.socket):
                def connect(self,*a,**k):raise AssertionError('network forbidden')
                def connect_ex(self,*a,**k):raise AssertionError('network forbidden')
            socket.socket=OfflineSocket
            socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network forbidden'))
            sys.path[:0]=[{str(ROOT/'src')!r},{str(ROOT/'tests')!r}]
            from annotation.recognition import inline_formula
            from annotation.recognition.inline_candidates import build_inline_candidates
            from test_b_inline_formula import FormulaWorker
            root,phase=Path(sys.argv[1]),sys.argv[2]
            e=json.loads((root/'evidence.json').read_text(encoding='utf-8'))
            layout=json.loads((root/'layout.json').read_text(encoding='utf-8'))
            publish=inline_formula.batch._put_object
            def crash(work,value):
                descriptor=publish(work,value)
                if phase=='crash' and value.get('schema_version')==inline_formula.CALL_SCHEMA:
                    (root/'orphan.json').write_text(json.dumps(descriptor),encoding='utf-8')
                    os._exit(61)
                return descriptor
            inline_formula.batch._put_object=crash
            observed,report=inline_formula.collect_inline_formula(e,layout,root/'source-page.png',root/'process-work',
                line_ids=layout['payload']['requested_line_ids'],recognizer=FormulaWorker(),max_items=1 if phase=='prime' else None)
            candidates=build_inline_candidates(observed)
            assert candidates['payload']['selected_candidate_refs']==[]
            print(json.dumps(report))
        '''), encoding="utf-8")
        def child(phase, code=0):
            result = subprocess.run([sys.executable, str(script), str(self.root), phase], cwd=ROOT,
                env=dict(os.environ, PYTHONIOENCODING="utf-8"), capture_output=True, text=True, encoding="utf-8", timeout=45)
            self.assertEqual(result.returncode, code, result.stdout+result.stderr)
            return json.loads(result.stdout) if result.stdout else None
        prime = child("prime")
        self.assertEqual(prime["payload"]["state"], "PARTIAL")
        child("crash", 61)
        work = self.root/"process-work"
        orphan = json.loads((self.root/"orphan.json").read_text(encoding="utf-8"))
        orphan_path = work/orphan["path"]
        orphan_bytes = orphan_path.read_bytes()
        before = {p: p.read_bytes() for p in (work/"objects").glob("*.json")}
        with closing(sqlite3.connect(work/"inline-formula.sqlite3")) as db:
            old_attempt, call_id = db.execute("SELECT attempt_id,call_id FROM attempts WHERE state='RUNNING'").fetchone()
            self.assertEqual(db.execute("SELECT output_json FROM attempts WHERE attempt_id=?", (old_attempt,)).fetchone()[0], None)
            self.assertEqual(db.execute("SELECT count(*) FROM cache WHERE attempt_id=?", (old_attempt,)).fetchone()[0], 0)
        resumed = child("resume")
        p = resumed["payload"]
        self.assertEqual(p["state"], "READY")
        self.assertEqual(p["counts"]["cache_hits"], 1)
        self.assertEqual(p["counts"]["new_attempts"], p["counts"]["declared_calls"]-1)
        row = next(c for c in p["calls"] if c["call_id"] == call_id)
        self.assertFalse(row["cached"])
        self.assertNotEqual(row["origin_attempt_id"], old_attempt)
        self.assertNotEqual(row["output"], orphan)
        self.assertEqual(orphan_path.read_bytes(), orphan_bytes)
        self.assertTrue(all(path.read_bytes() == data for path, data in before.items()))
        with closing(sqlite3.connect(work/"inline-formula.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT state FROM attempts WHERE attempt_id=?", (old_attempt,)).fetchone()[0], "INTERRUPTED")
            self.assertEqual(db.execute("SELECT count(*) FROM cache WHERE attempt_id=?", (old_attempt,)).fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM events WHERE attempt_id=? AND kind='SUCCEEDED'", (old_attempt,)).fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM events WHERE attempt_id=? AND kind='INTERRUPTED'", (old_attempt,)).fetchone()[0], 1)
        self.assert_hold(resumed)


if __name__ == "__main__":
    unittest.main()
