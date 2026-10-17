"""Local stage recovery and dependency tests; no model inference or website.

The live full-chain fixture has explicit SYNTHETIC_TEST baseline output and no
answer rows to re-read; existing refine/assemble/quality functions run normally.
Two subprocess tests actually exit during assembly and after object publication.
"""
from contextlib import closing
import copy
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from annotation.recognition import pipeline
from annotation.recognition.baseline import digest
from annotation.recognition.offline import artifact
from test_b_batch import manifest, CountingWorker


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def source_inputs(directory):
    source_path, source = manifest(directory, count=2)
    context = {"schema_version": "b-context-trial/0.1", "artifact_id": "synthetic-context", "book_id": source["book_id"],
               "scope_id": source["scope_id"], "pages": {a["asset_id"]: {"sha256": a["sha256"], "role": "question",
               "windows": [{"column": 0, "y_range": [0, a["height"]], "path": ["Synthetic section"]}]} for a in source["assets"]}}
    review = {"schema_version": "b-review-trial/0.1", "artifact_id": "synthetic-review", "book_id": source["book_id"],
              "scope_id": source["scope_id"], "reference_quality": "SYNTHETIC_TEST", "answer_checks": [],
              "question_census": {a["asset_id"]: {"sha256": a["sha256"], "printed_numbers": []} for a in source["assets"]}}
    pages = [{"asset_id": a["asset_id"], "source": copy.deepcopy(a), "page_role": "question",
              "layout": {"mode": "UNRESOLVED_LAYOUT", "cut_x": 90}, "ocr_lines": [],
              "answer_detail_lines": [], "unscoped_line_ids": []} for a in source["assets"]]
    evidence = artifact("b-evidence-trial/0.2", "EvidenceBundleTrial", source, {"pages": pages,
                        "context": context, "quality_decision": "NOT_EVALUATED", "history_annotations_consumed": False},
                        [{"artifact_id": "synthetic-prior-observation", "content_hash": digest(source)}],
                        {"module": "SYNTHETIC_TEST", "execution_kind": "SYNTHETIC_TEST"})
    paths = [source_path] + [Path(directory) / f"{name}.json" for name in ("context", "review", "evidence")]
    for path, value in zip(paths[1:], (context, review, evidence)): write(path, value)
    return paths, source, context, review, evidence


def result(work, stage):
    value = json.loads((Path(work) / stage["output"]["path"]).read_text(encoding="utf-8"))
    return value["payload"]["result"]


class PipelineRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths, self.source, self.context, self.review, self.evidence = source_inputs(self.root)
        self.source_path, self.context_path, self.review_path, self.evidence_path = self.paths
        self.work = self.root / "pipeline"

    def run_cached(self, **kwargs):
        return pipeline.run_pipeline(*self.paths[:3], self.work, evidence_path=self.evidence_path, **kwargs)

    def run_live(self, **kwargs):
        return pipeline.run_pipeline(*self.paths[:3], self.work, **kwargs)

    def test_cached_full_chain_is_ready_with_hold_quality_then_all_stages_are_cached(self):
        report = self.run_cached()
        self.assertEqual(report["payload"]["pipeline_state"], "READY")
        self.assertEqual([s["stage_id"] for s in report["payload"]["stages"]], ["evidence", "assemble", "quality"])
        check = result(self.work, report["payload"]["stages"][-1])
        self.assertEqual(check["payload"]["decision"], "HOLD")
        self.assertTrue(any(i["severity"] == "ERROR" for i in check["payload"]["issues"]))
        cached = self.run_cached()
        self.assertEqual(cached["payload"]["counts"]["cache_hits"], 3)
        self.assertTrue(all(s["cached"] for s in cached["payload"]["stages"]))
        self.assertFalse(cached["payload"]["business_acceptance"])
        self.assertFalse(cached["payload"]["transcription_verified"])
        self.assertEqual(cached["payload"]["platform_actions"], [])

    def test_stage_stop_does_not_claim_complete_or_lose_declared_assets(self):
        report = self.run_cached(stop_after="recognition")
        self.assertEqual(report["payload"]["pipeline_state"], "PARTIAL")
        self.assertEqual([s["state"] for s in report["payload"]["stages"]], ["DONE", "WAITING", "WAITING"])
        self.assertEqual(report["payload"]["source_assets"], self.source["assets"])
        resumed = self.run_cached()
        self.assertEqual([s["cached"] for s in resumed["payload"]["stages"]], [True, False, False])

    def test_default_live_geometry_waits_before_any_implicit_ocr(self):
        real_import = __import__
        def no_ocr(name, *args, **kwargs):
            if name.startswith(("rapidocr", "onnxruntime")): raise AssertionError("unexpected OCR import")
            return real_import(name, *args, **kwargs)
        with mock.patch("builtins.__import__", side_effect=no_ocr):
            first = self.run_live(max_items=1)
            self.assertEqual(first["payload"]["stages"][0]["state"], "PARTIAL")
            self.assertEqual(result(self.work, first["payload"]["stages"][0])["payload"]["counts"]["declared"], 2)
            resumed = self.run_live()
        self.assertEqual(resumed["payload"]["pipeline_state"], "PARTIAL")
        self.assertEqual(resumed["payload"]["stages"][1]["reason"], "OCR_REQUIRED")
        self.assertEqual(resumed["payload"]["stages"][1]["state"], "WAITING")
        self.assertEqual(resumed["payload"]["counts"]["failed"], 0)

    def test_live_synthetic_worker_runs_normal_refine_assemble_check_without_answer_ocr(self):
        worker = CountingWorker()
        report = self.run_live(use_ocr=True, worker=worker)
        self.assertEqual(report["payload"]["pipeline_state"], "READY")
        self.assertEqual(report["payload"]["execution_kind"], "SYNTHETIC_TEST")
        self.assertEqual(worker.calls, ["page-0", "page-1"])
        again = self.run_live(use_ocr=True, worker=worker)
        self.assertEqual(again["payload"]["counts"]["cache_hits"], 4)
        self.assertEqual(len(worker.calls), 2)

    def test_context_change_reuses_recognition_but_reruns_refine_and_descendants(self):
        worker = CountingWorker()
        first = self.run_live(use_ocr=True, worker=worker)
        for page in self.context["pages"].values(): page["windows"][0]["path"] = ["Changed reviewed section"]
        write(self.context_path, self.context)
        second = self.run_live(use_ocr=True, worker=worker)
        self.assertEqual(second["payload"]["pipeline_state"], "READY")
        self.assertEqual([s["cached"] for s in second["payload"]["stages"]], [True, False, False, False])
        self.assertEqual(first["payload"]["stages"][0]["output"], second["payload"]["stages"][0]["output"])
        self.assertEqual(len(worker.calls), 2)

    def test_review_change_reruns_only_quality(self):
        original = self.run_cached()
        self.review["provenance_note"] = "new independent review revision"
        write(self.review_path, self.review)
        changed = self.run_cached()
        self.assertEqual([s["cached"] for s in changed["payload"]["stages"]], [True, True, False])
        self.assertEqual(original["payload"]["stages"][0]["output"], changed["payload"]["stages"][0]["output"])

    def test_changed_regex_global_invalidates_assembly_and_descendants_only(self):
        self.run_cached()
        with mock.patch.object(pipeline.offline, "QSTART", re.compile(r"^NEW_PATTERN$")):
            changed = self.run_cached()
        self.assertEqual([s["cached"] for s in changed["payload"]["stages"]], [True, False, False])

    def test_bad_middle_object_reruns_only_it_and_descendants_and_keeps_old_bytes(self):
        first = self.run_cached()
        descriptor = first["payload"]["stages"][1]["output"]
        bad = self.work / descriptor["path"]
        bad.write_bytes(b"CORRUPTED VERSION RETAINED")
        restored = self.run_cached()
        self.assertEqual([s["cached"] for s in restored["payload"]["stages"]], [True, False, False])
        self.assertEqual(restored["payload"]["counts"]["invalidated"], 1)
        self.assertEqual(bad.read_bytes(), b"CORRUPTED VERSION RETAINED")
        self.assertNotEqual(restored["payload"]["stages"][1]["output"], descriptor)

    def test_missing_origin_terminal_event_does_not_count_as_cached_success(self):
        first = self.run_cached()
        attempt = first["payload"]["stages"][1]["origin_attempt_id"]
        with closing(sqlite3.connect(self.work / "pipeline.sqlite3")) as db:
            db.execute("DELETE FROM stage_events WHERE attempt_id=? AND event_type='STAGE_SUCCEEDED'", (attempt,))
            db.commit()
        restored = self.run_cached()
        self.assertEqual([s["cached"] for s in restored["payload"]["stages"]], [True, False, False])
        self.assertEqual(restored["payload"]["counts"]["invalidated"], 1)

    def test_stage_exception_is_failed_then_later_valid_stage_recovers_from_prior_cache(self):
        def failure(evidence): raise RuntimeError("deliberate assembly failure")
        with mock.patch.object(pipeline, "assemble", failure):
            failed = self.run_cached()
        self.assertEqual(failed["payload"]["pipeline_state"], "FAILED")
        self.assertEqual([s["state"] for s in failed["payload"]["stages"]], ["DONE", "FAILED", "WAITING"])
        ready = self.run_cached()
        self.assertEqual(ready["payload"]["pipeline_state"], "READY")
        self.assertTrue(ready["payload"]["stages"][0]["cached"])

    def test_stage_fingerprint_setup_failure_has_terminal_report_without_fabricated_key_or_attempt(self):
        with mock.patch.object(pipeline, "_implementation", side_effect=RuntimeError("missing declared runtime dependency")):
            failed = self.run_cached()
        self.assertEqual(failed["payload"]["pipeline_state"], "FAILED")
        first = failed["payload"]["stages"][0]
        self.assertEqual(first["reason"], "STAGE_SETUP_FAILED")
        self.assertIsNone(first["expected_key"])
        self.assertIsNone(first["implementation"])
        self.assertIsNone(first["origin_attempt_id"])
        self.assertIsNone(first["output"])
        with closing(sqlite3.connect(self.work / "pipeline.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM stage_attempts").fetchone()[0], 0)
            types = [r[0] for r in db.execute("SELECT event_type FROM stage_events ORDER BY event_id")]
            self.assertEqual(types, ["RUN_STARTED", "STAGE_SETUP_FAILED", "RUN_FINISHED"])

    def test_input_change_after_stage_execution_still_saves_terminal_failed_report(self):
        original = pipeline.quality_check
        def mutate_review(evidence, graph, review):
            checked = original(evidence, graph, review)
            changed = copy.deepcopy(review)
            changed["changed_during_execution"] = True
            write(self.review_path, changed)
            return checked
        with mock.patch.object(pipeline, "quality_check", mutate_review):
            failed = self.run_cached()
        self.assertEqual(failed["payload"]["pipeline_state"], "FAILED")
        self.assertEqual(failed["payload"]["run_error"]["code"], "INPUT_CHANGED_DURING_RUN")
        with closing(sqlite3.connect(self.work / "pipeline.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM stage_events WHERE event_type='RUN_INPUT_CHANGED'").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM stage_events WHERE event_type='RUN_FINISHED'").fetchone()[0], 1)

    def test_stale_context_missing_page_bad_review_or_changed_image_reject_before_work(self):
        original = copy.deepcopy(self.evidence)
        for mutation in ("context", "page", "review", "image"):
            with self.subTest(mutation=mutation):
                evidence = copy.deepcopy(original)
                if mutation == "context": evidence["payload"]["context"]["artifact_id"] = "stale"
                elif mutation == "page": evidence["payload"]["pages"].pop()
                elif mutation == "review":
                    review = copy.deepcopy(self.review); review["scope_id"] = "wrong"
                    write(self.review_path, review)
                else: (self.root / self.source["assets"][0]["path"]).write_bytes(b"not original pixels")
                evidence["content_hash"] = digest(evidence["payload"])
                write(self.evidence_path, evidence)
                with self.assertRaises(ValueError): self.run_cached()
                self.assertFalse(self.work.exists())
                write(self.review_path, self.review)

    def test_invalid_cached_execution_options_and_budget_are_explicit(self):
        for kwargs in ({"max_items": 1}, {"use_ocr": True}, {"worker": CountingWorker()}, {"stop_after": "refine"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError): self.run_cached(**kwargs)
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): self.run_live(max_items=value)

    def test_raw_cached_input_and_old_stage_objects_remain_unchanged(self):
        raw = self.evidence_path.read_bytes()
        first = self.run_cached()
        before = {s["output"]["path"]: (self.work / s["output"]["path"]).read_bytes() for s in first["payload"]["stages"]}
        self.run_cached()
        self.assertEqual(raw, self.evidence_path.read_bytes())
        self.assertTrue(all((self.work / path).read_bytes() == data for path, data in before.items()))
        with closing(sqlite3.connect(self.work / "pipeline.sqlite3")) as db:
            event = db.execute("SELECT details_json FROM stage_events WHERE run_id=? AND event_type='RUN_FINISHED'", (first["run_id"],)).fetchone()
            descriptor = json.loads(event[0])["report_artifact"]
        self.assertEqual(json.loads((self.work / descriptor["path"]).read_text(encoding="utf-8")), first)

    def test_real_process_death_during_execution_and_after_publication_resume_safely(self):
        script = self.root / "crash_pipeline.py"
        script.write_text(textwrap.dedent(f'''
            import json,os,sys
            sys.path.insert(0,{str(ROOT/'src')!r})
            from annotation.recognition import pipeline
            original=pipeline.assemble
            def assembly(evidence):
                if os.environ.get('PIPE_CRASH')=='inside': os._exit(31)
                return original(evidence)
            pipeline.assemble=assembly
            publish=pipeline.batch._put_object
            def publication(workdir,value):
                descriptor=publish(workdir,value)
                if (os.environ.get('PIPE_CRASH')=='published' and value.get('schema_version')==pipeline.STAGE_SCHEMA
                    and value['payload']['stage_id']=='assemble'): os._exit(32)
                return descriptor
            pipeline.batch._put_object=publication
            report=pipeline.run_pipeline(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],evidence_path=sys.argv[5])
            print(json.dumps(report))
        '''), encoding="utf-8")
        for phase, code in (("inside", 31), ("published", 32)):
            with self.subTest(phase=phase):
                work = self.root / phase
                args = [sys.executable, str(script), *map(str, self.paths[:3]), str(work), str(self.evidence_path)]
                env = dict(os.environ, PIPE_CRASH=phase, PYTHONIOENCODING="utf-8")
                crashed = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
                self.assertEqual(crashed.returncode, code, crashed.stderr)
                old = {p.name: p.read_bytes() for p in (work / "objects").glob("*.json")}
                with closing(sqlite3.connect(work / "pipeline.sqlite3")) as db:
                    self.assertEqual(db.execute("SELECT state FROM stage_attempts WHERE stage_id='assemble'").fetchone()[0], "RUNNING")
                    self.assertEqual(db.execute("SELECT count(*) FROM stage_cache WHERE stage_id='assemble'").fetchone()[0], 0)
                env.pop("PIPE_CRASH")
                resumed = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
                self.assertEqual(resumed.returncode, 0, resumed.stderr)
                report = json.loads(resumed.stdout)
                self.assertEqual(report["payload"]["pipeline_state"], "READY")
                self.assertEqual([s["cached"] for s in report["payload"]["stages"]], [True, False, False])
                self.assertTrue(all((work / "objects" / name).read_bytes() == data for name, data in old.items()))
                with closing(sqlite3.connect(work / "pipeline.sqlite3")) as db:
                    self.assertEqual([r[0] for r in db.execute("SELECT state FROM stage_attempts WHERE stage_id='assemble' ORDER BY started_at")], ["INTERRUPTED", "SUCCEEDED"])


if __name__ == "__main__": unittest.main()
