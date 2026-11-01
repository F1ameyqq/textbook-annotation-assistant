"""Persistent inline attachment stages, using source-bound synthetic journals."""
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tests")]
from annotation.recognition import pipeline
from annotation.recognition.baseline import digest
from test_b_inline_stage import make_inline_fixture, write


def result(workdir, entry):
    return json.loads((Path(workdir)/entry["output"]["path"]).read_text(encoding="utf-8"))["payload"]["result"]


class PipelineInlineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.d = make_inline_fixture(self.root)
        self.work = self.root/"pipeline"

    def run_pipeline(self, **kwargs):
        return pipeline.run_pipeline(self.d["source_path"], self.d["context_path"], self.d["review_path"], self.work,
            evidence_path=self.d["evidence_path"], inline_path=self.d["package_path"], inline_source_path=self.d["original"], **kwargs)

    def test_complete_chain_current_final_outputs_and_full_cache(self):
        first = self.run_pipeline()
        self.assertEqual(first["payload"]["pipeline_state"], "READY", first["payload"]["stages"])
        stages = first["payload"]["stages"]
        self.assertEqual([s["stage_id"] for s in stages], ["evidence", "assemble", "quality", "inline_prepare", "inline_apply", "inline_quality"])
        app, checked = result(self.work, stages[-2]), result(self.work, stages[-1])
        self.assertEqual(first["payload"]["final_outputs"]["graph_ref"], pipeline._ref(app["payload"]["graph"]))
        self.assertEqual(first["payload"]["final_outputs"]["quality_ref"], pipeline._ref(checked))
        self.assertFalse(first["payload"]["business_acceptance"])
        self.assertNotIn("created_at", result(self.work, stages[1]))
        again = self.run_pipeline()
        self.assertEqual(again["payload"]["counts"]["cache_hits"], 6)
        self.assertEqual(again["payload"]["final_outputs"], first["payload"]["final_outputs"])

    def test_stop_prepare_then_apply_then_resume(self):
        first = self.run_pipeline(stop_after="inline_prepare")
        self.assertEqual(first["payload"]["pipeline_state"], "PARTIAL")
        self.assertIsNone(first["payload"]["final_outputs"])
        self.assertEqual([s["state"] for s in first["payload"]["stages"]][-3:], ["DONE", "WAITING", "WAITING"])
        second = self.run_pipeline(stop_after="inline_apply")
        self.assertEqual(second["payload"]["counts"]["cache_hits"], 4)
        self.assertIsNone(second["payload"]["final_outputs"])
        third = self.run_pipeline()
        self.assertEqual(third["payload"]["counts"]["cache_hits"], 5)
        self.assertEqual(third["payload"]["pipeline_state"], "READY")

    def test_review_change_only_repeats_base_and_inline_quality(self):
        self.run_pipeline()
        review = json.loads(self.d["review_path"].read_text(encoding="utf-8")); review["note"] = "review-only-change"
        write(self.d["review_path"], review)
        changed = self.run_pipeline()
        self.assertEqual([s["cached"] for s in changed["payload"]["stages"]], [True, True, False, True, True, False])

    def test_partial_and_failed_package_never_apply_or_emit_final_outputs(self):
        for args, state in (({"max_items":1}, "PARTIAL"), ({"fail":True}, "FAILED")):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as directory:
                d = make_inline_fixture(directory, **args)
                out = pipeline.run_pipeline(d["source_path"], d["context_path"], d["review_path"], Path(directory)/"pipeline",
                    evidence_path=d["evidence_path"], inline_path=d["package_path"], inline_source_path=d["original"])
                self.assertEqual(out["payload"]["pipeline_state"], state)
                self.assertEqual([s["state"] for s in out["payload"]["stages"]][-3:], [state, "WAITING", "WAITING"])
                self.assertIsNone(out["payload"]["final_outputs"])

    def test_inline_arguments_are_paired(self):
        for kwargs in ({"inline_path":self.d["package_path"]}, {"inline_source_path":self.d["original"]}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "required together"):
                pipeline.run_pipeline(self.d["source_path"], self.d["context_path"], self.d["review_path"], self.work,
                    evidence_path=self.d["evidence_path"], **kwargs)

    def test_package_byte_change_repeats_only_last_three_but_content_refs_stable(self):
        first = self.run_pipeline()
        self.d["package_path"].write_bytes(self.d["package_path"].read_bytes()+b"\n ")
        second = self.run_pipeline()
        self.assertEqual([s["cached"] for s in second["payload"]["stages"]], [True, True, True, False, False, False])
        self.assertEqual(first["payload"]["final_outputs"], second["payload"]["final_outputs"])

    def test_corrupt_apply_is_preserved_and_only_apply_quality_rebuilt(self):
        first = self.run_pipeline()
        path = self.work/first["payload"]["stages"][-2]["output"]["path"]
        path.write_bytes(b"DAMAGED immutable wrapper")
        second = self.run_pipeline()
        self.assertEqual(path.read_bytes(), b"DAMAGED immutable wrapper")
        self.assertEqual([s["cached"] for s in second["payload"]["stages"]], [True, True, True, True, False, False])
        self.assertEqual(second["payload"]["counts"]["invalidated"], 1)

    def test_inflight_package_change_is_terminal_failure(self):
        put = pipeline.batch._put_object
        def change(workdir, value):
            descriptor = put(workdir, value)
            if value.get("payload", {}).get("stage_id") == "inline_apply":
                self.d["package_path"].write_bytes(self.d["package_path"].read_bytes()+b"\n ")
            return descriptor
        with patch.object(pipeline.batch, "_put_object", side_effect=change):
            out = self.run_pipeline()
        self.assertEqual(out["payload"]["pipeline_state"], "FAILED")
        self.assertEqual(out["payload"]["run_error"]["code"], "INPUT_CHANGED_DURING_RUN")
        self.assertIsNone(out["payload"]["final_outputs"])

    def test_continuation_then_inline_use_actual_current_e6_g4_check04(self):
        with tempfile.TemporaryDirectory() as directory:
            d = make_inline_fixture(directory, continuation=True)
            work = Path(directory)/"pipeline"
            out = pipeline.run_pipeline(d["source_path"], d["context_path"], d["review_path"], work,
                evidence_path=d["evidence_path"], continuation_path=d["continuation_path"], adjacent_source_path=d["adjacent_source_path"],
                inline_path=d["package_path"], inline_source_path=d["original"])
            self.assertEqual(out["payload"]["pipeline_state"], "READY", out["payload"]["stages"])
            entries = {s["stage_id"]:s for s in out["payload"]["stages"]}
            e6 = result(work, entries["continuation_prepare"])["payload"]["evidence"]
            g4 = result(work, entries["continuation_apply"])["payload"]["graph"]
            checked4 = result(work, entries["continuation_quality"])
            prepared = result(work, entries["inline_prepare"])
            checked5 = result(work, entries["inline_quality"])
            self.assertEqual(prepared["payload"]["base_evidence_ref"], pipeline._ref(e6))
            self.assertEqual(prepared["payload"]["base_graph_archive"], g4)
            self.assertEqual(checked5["payload"]["base_check_archive"], checked4)
            self.assertEqual(out["payload"]["final_outputs"]["evidence_ref"], pipeline._ref(e6))

    def test_formula_backend_and_batch_fingerprint_changes_only_repeat_three_inline_stages(self):
        """Simulate dependency versions, not changed OCR bytes or CPU receipts.

        All saved observations are SYNTHETIC_TEST, with a real local journal.
        Only the runner's implementation fingerprint is varied. The original
        source, helper files and historical observation producers stay intact;
        this test demonstrates invalidation, not acceptance of stale models.
        """
        from annotation.recognition import offline, recovery_stage
        from annotation.recognition.baseline import file_digest
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            d = make_inline_fixture(root, continuation=True)
            base = json.loads(d["evidence_path"].read_text(encoding="utf-8"))
            ref = pipeline._ref
            recovery = offline.artifact("b-recovery-trial/0.1", "RecoveryEvidenceTrial", base,
                {"base_evidence_ref": ref(base), "probes": [], "supersession_plan": []}, [ref(base)],
                {"module": "SYNTHETIC_TEST", "execution_kind": "SYNTHETIC_TEST", "engine": "injected_test_backend",
                 "device": "SYNTHETIC_TEST", "dependencies": {}, "dependency_sha256": digest({}), "model_files": []})
            review = offline.artifact("b-source-review-trial/0.1", "SourceRecoveryReviewTrial", base,
                {"base_evidence_ref": ref(base), "recovery_ref": ref(recovery), "reviewed_exclusions": [],
                 "reviewed_probe_selections": [], "formula_candidates": [], "triage": [], "remaining_source_groups": [],
                 "regression_additions": [], "recovered_answer_checks": []}, [ref(base), ref(recovery)],
                {"module": "SYNTHETIC_TEST", "reference_quality": "SYNTHETIC_TEST"})
            package = {"schema_version": recovery_stage.PACKAGE_SCHEMA, "artifact_id": "synthetic-empty-recovery",
                "book_id": base["book_id"], "scope_id": base["scope_id"], "policy": recovery_stage.POLICY, "documents": {}}
            import hashlib
            for name, value in (("base_evidence", base), ("recovery", recovery), ("source_review", review)):
                path = root/("empty-recovery-"+name+".json"); write(path, value)
                package["documents"][name] = {"path": path.name,
                    "text_sha256": hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest(), "artifact_ref": ref(value)}
            recovery_path = root/"empty-recovery-package.json"; write(recovery_path, package)
            work = root/"pipeline"
            def run():
                return pipeline.run_pipeline(d["source_path"], d["context_path"], d["review_path"], work,
                    evidence_path=d["evidence_path"], recovery_path=recovery_path,
                    continuation_path=d["continuation_path"], adjacent_source_path=d["adjacent_source_path"],
                    inline_path=d["package_path"], inline_source_path=d["original"])
            helpers = [ROOT/"src/annotation/recognition"/(name+".py") for name in ("formula_backend", "batch")]
            before = {path: file_digest(path) for path in helpers}
            fingerprint = pipeline.code_digest
            with patch.dict(sys.modules, {"rapidocr_onnxruntime": None, "onnxruntime": None, "rapid_latex_ocr": None}), \
                 patch("socket.socket", side_effect=AssertionError("no network")):
                first = run()
                self.assertEqual(first["payload"]["pipeline_state"], "READY", first["payload"]["stages"])
                self.assertEqual(len(first["payload"]["stages"]), 12)
                for name in ("formula_backend", "batch"):
                    def simulated(path):
                        real = fingerprint(path)
                        return digest({"SYNTHETIC_TEST_FINGERPRINT_ONLY": name, "actual_code_sha256": real}) if Path(path).name == name+".py" else real
                    with self.subTest(helper=name), patch.object(pipeline, "code_digest", side_effect=simulated):
                        changed = run()
                        stages = changed["payload"]["stages"]
                        self.assertEqual(changed["payload"]["pipeline_state"], "READY", stages)
                        self.assertEqual([s["cached"] for s in stages], [True]*9+[False]*3)
                        self.assertEqual([s["stage_id"] for s in stages[-3:]], list(pipeline.INLINE_STAGES))
                        self.assertTrue(all(s["implementation"]["code"]["modules"][name] != fingerprint(ROOT/"src/annotation/recognition"/(name+".py")) for s in stages[-3:]))
                        prepared = result(work, stages[-3])
                        self.assertEqual(prepared["payload"]["formula_observations_archive"]["producer"]["execution_kind"], "SYNTHETIC_TEST")
            self.assertEqual({path: file_digest(path) for path in helpers}, before)

    def test_true_process_exit_after_inline_object_before_sql_commit_recovers(self):
        script = r'''
import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/"src"))
from annotation.recognition import pipeline
root=Path(sys.argv[1]); put=pipeline.batch._put_object
def abrupt(workdir,value):
    output=put(workdir,value)
    if value.get("payload",{}).get("stage_id")=="inline_apply":os._exit(71)
    return output
pipeline.batch._put_object=abrupt
pipeline.run_pipeline(root/"source.json",root/"context.json",root/"review.json",root/"pipeline",
    evidence_path=root/"inline-evidence.json",inline_path=root/"inline-package.json",inline_source_path=root/"source-page.png")
'''
        exited = subprocess.run([sys.executable, "-c", script, str(self.root)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(exited.returncode, 71, exited.stderr)
        before = set((self.work/"objects").glob("*.json"))
        recovered = self.run_pipeline()
        self.assertEqual(recovered["payload"]["pipeline_state"], "READY")
        self.assertTrue(before.issubset(set((self.work/"objects").glob("*.json"))))
        with closing(sqlite3.connect(self.work/"pipeline.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT state FROM stage_attempts WHERE stage_id='inline_apply' ORDER BY started_at LIMIT 1").fetchone()[0], "INTERRUPTED")


if __name__ == "__main__": unittest.main()
