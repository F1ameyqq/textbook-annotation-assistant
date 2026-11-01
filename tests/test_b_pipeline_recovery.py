"""Optional recovery-stage orchestration; actual replacements, no model calls."""
from contextlib import closing
import copy
import json
import os
from pathlib import Path
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
from annotation.recognition.recovery_apply import reference
from annotation.recognition.recovery_stage import recover_evidence
from test_b_recovery_stage import make_recovery_fixture, write
from test_b_batch import CountingWorker


def stage_result(workdir, entry):
    return json.loads((Path(workdir) / entry["output"]["path"]).read_text(encoding="utf-8"))["payload"]["result"]


class PipelineRecoveryIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = make_recovery_fixture(self.root)
        self.work = self.root / "pipeline"

    def run_pipeline(self, **kwargs):
        return pipeline.run_pipeline(self.root / "source.json", self.root / "context.json", self.root / "review.json", self.work,
                                     evidence_path=self.root / "current.json", recovery_path=self.root / "package.json", **kwargs)

    def test_cached_base_is_automatically_recovered_then_reviewed_and_checked(self):
        report = self.run_pipeline()
        self.assertEqual(report["payload"]["pipeline_state"], "READY")
        entries = report["payload"]["stages"]
        self.assertEqual([e["stage_id"] for e in entries], ["evidence", "recover", "assemble", "recovery_review", "quality"])
        recovered, graph, review, checked = [stage_result(self.work, e) for e in entries[1:]]
        self.assertEqual(recovered["payload"]["recovery_migration"]["current_base_ref"], reference(self.data["current"]))
        self.assertEqual(graph["input_refs"], [reference(recovered)])
        self.assertEqual(graph["payload"]["answers"][0]["text"], "4")
        self.assertEqual(review["payload"]["review"]["recovery_migration_ref"], reference(recovered))
        self.assertEqual(checked["input_refs"][-1], {"artifact_id": review["payload"]["review"]["artifact_id"],
                         "content_hash": digest(review["payload"]["review"])})
        self.assertEqual(checked["payload"]["decision"], "HOLD")
        again = self.run_pipeline()
        self.assertEqual(again["payload"]["counts"]["cache_hits"], 5)

    def test_stop_after_recover_and_review_stage_resume_from_prior_outputs(self):
        first = self.run_pipeline(stop_after="recover")
        self.assertEqual([e["state"] for e in first["payload"]["stages"]], ["DONE", "DONE", "WAITING", "WAITING", "WAITING"])
        second = self.run_pipeline(stop_after="recovery_review")
        self.assertEqual([e["cached"] for e in second["payload"]["stages"]], [True, True, False, False, False])
        self.assertEqual(second["payload"]["pipeline_state"], "PARTIAL")
        third = self.run_pipeline()
        self.assertEqual([e["cached"] for e in third["payload"]["stages"]], [True, True, True, True, False])

    def test_review_only_change_does_not_repeat_recovery_or_assembly(self):
        self.run_pipeline()
        self.data["review"]["revision_note"] = "changed review input only"
        write(self.root / "review.json", self.data["review"])
        changed = self.run_pipeline()
        self.assertEqual([e["cached"] for e in changed["payload"]["stages"]], [True, True, True, False, False])

    def test_package_file_byte_change_reuses_only_prior_evidence(self):
        self.run_pipeline()
        path = self.root / "package.json"
        path.write_bytes(path.read_bytes()+b"\n ")
        changed = self.run_pipeline()
        self.assertEqual([e["cached"] for e in changed["payload"]["stages"]], [True, False, False, False, False])

    def test_corrupt_recover_object_is_not_overwritten_and_only_descendants_repeat(self):
        original = self.run_pipeline()
        old = self.work / original["payload"]["stages"][1]["output"]["path"]
        old.write_bytes(b"DAMAGED HISTORICAL STAGE")
        restored = self.run_pipeline()
        self.assertEqual([e["cached"] for e in restored["payload"]["stages"]], [True, False, False, False, False])
        self.assertEqual(old.read_bytes(), b"DAMAGED HISTORICAL STAGE")
        self.assertEqual(restored["payload"]["counts"]["invalidated"], 1)

    def test_non_equivalent_base_fails_recover_with_a_terminal_report(self):
        current = copy.deepcopy(self.data["current"])
        current["payload"]["pages"][1]["answer_detail_lines"][0]["score"] = .8
        current["content_hash"] = digest(current["payload"])
        write(self.root / "current.json", current)
        failed = self.run_pipeline()
        self.assertEqual(failed["payload"]["pipeline_state"], "FAILED")
        self.assertEqual([e["state"] for e in failed["payload"]["stages"]], ["DONE", "FAILED", "WAITING", "WAITING", "WAITING"])
        self.assertIn("canonical base payload equivalence", failed["payload"]["stages"][1]["last_error"])
        with closing(sqlite3.connect(self.work / "pipeline.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM stage_events WHERE event_type='RUN_FINISHED'").fetchone()[0], 1)

    def test_already_recovered_input_or_review_is_not_recovered_again(self):
        migrated = recover_evidence(self.data["current"], self.root / "package.json", self.root / "source.json", self.data["context"])
        write(self.root / "current.json", migrated)
        with self.assertRaises(ValueError): self.run_pipeline()
        write(self.root / "current.json", self.data["current"])
        review = {**self.data["review"], "recovery_migration_ref": reference(migrated)}
        write(self.root / "review.json", review)
        with self.assertRaises(ValueError): self.run_pipeline()
        self.assertFalse(self.work.exists())

    def test_package_change_after_recover_publication_is_terminal_failure_then_resumable(self):
        publish = pipeline.batch._put_object
        changed = [False]
        def mutate_after_recover(workdir, value):
            descriptor = publish(workdir, value)
            if value.get("schema_version") == pipeline.STAGE_SCHEMA and value["payload"]["stage_id"] == "recover" and not changed[0]:
                path = self.root / "package.json"
                path.write_bytes(path.read_bytes()+b"\n ")
                changed[0] = True
            return descriptor
        with mock.patch.object(pipeline.batch, "_put_object", mutate_after_recover):
            failed = self.run_pipeline()
        self.assertEqual(failed["payload"]["pipeline_state"], "FAILED")
        self.assertEqual(failed["payload"]["run_error"]["code"], "INPUT_CHANGED_DURING_RUN")
        self.assertEqual(self.run_pipeline()["payload"]["pipeline_state"], "READY")

    def test_live_chain_has_six_stages_and_never_relabels_synthetic_observations_cpu(self):
        def synthetic_refine(source_path, baseline, context):
            return artifact("b-evidence-trial/0.2", "EvidenceBundleTrial", self.data["source"], copy.deepcopy(self.data["base_evidence"]["payload"]),
                            [reference(baseline), {"artifact_id": context["artifact_id"], "content_hash": digest(context)}],
                            {"module": "SYNTHETIC_TEST_REFINER", "execution_kind": "SYNTHETIC_TEST"})
        worker = CountingWorker()
        with mock.patch.object(pipeline, "refine", synthetic_refine):
            report = pipeline.run_pipeline(self.root / "source.json", self.root / "context.json", self.root / "review.json", self.work,
                                           recovery_path=self.root / "package.json", use_ocr=True, worker=worker)
        self.assertEqual(report["payload"]["pipeline_state"], "READY")
        self.assertEqual([e["stage_id"] for e in report["payload"]["stages"]], ["recognition", "refine", "recover", "assemble", "recovery_review", "quality"])
        self.assertEqual(report["payload"]["execution_kind"], "SYNTHETIC_TEST")
        recovered = stage_result(self.work, report["payload"]["stages"][2])
        self.assertEqual(recovered["payload"]["recovery_evidence_archive"]["producer"]["execution_kind"], "SYNTHETIC_TEST")

    def test_actual_process_exit_after_recovery_object_published_resumes_without_using_orphan(self):
        script = self.root / "crash_recovery.py"
        script.write_text(textwrap.dedent(f'''
            import os,sys,json
            sys.path.insert(0,{str(ROOT/'src')!r})
            from annotation.recognition import pipeline
            publish=pipeline.batch._put_object
            def publication(workdir,value):
                descriptor=publish(workdir,value)
                if (os.environ.get('KILL_RECOVERY')=='1' and value.get('schema_version')==pipeline.STAGE_SCHEMA
                    and value['payload']['stage_id']=='recover'): os._exit(47)
                return descriptor
            pipeline.batch._put_object=publication
            from pathlib import Path
            root=Path(sys.argv[1])
            report=pipeline.run_pipeline(root/'source.json',root/'context.json',root/'review.json',root/'pipeline',
                evidence_path=root/'current.json',recovery_path=root/'package.json')
            print(json.dumps(report))
        '''), encoding="utf-8")
        env = dict(os.environ, KILL_RECOVERY="1", PYTHONIOENCODING="utf-8")
        crashed = subprocess.run([sys.executable, str(script), str(self.root)], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(crashed.returncode, 47, crashed.stderr)
        old = {p.name: p.read_bytes() for p in (self.work / "objects").glob("*.json")}
        env.pop("KILL_RECOVERY")
        resumed = subprocess.run([sys.executable, str(script), str(self.root)], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        report = json.loads(resumed.stdout)
        self.assertEqual(report["payload"]["pipeline_state"], "READY")
        self.assertEqual([e["cached"] for e in report["payload"]["stages"]], [True, False, False, False, False])
        self.assertTrue(all((self.work / "objects" / name).read_bytes() == value for name, value in old.items()))
        with closing(sqlite3.connect(self.work / "pipeline.sqlite3")) as db:
            self.assertEqual([r[0] for r in db.execute("SELECT state FROM stage_attempts WHERE stage_id='recover' ORDER BY started_at")], ["INTERRUPTED", "SUCCEEDED"])


if __name__ == "__main__": unittest.main()
