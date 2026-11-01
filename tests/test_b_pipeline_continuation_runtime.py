"""Real continuation process death and native dependency invalidation.

The portable source pixels and OCR observations are generated SYNTHETIC_TEST
fixtures. Child processes forbid model imports and network connections. A fake
native-file receipt changes metadata only; the installed binary is untouched.
"""
from contextlib import closing
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

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from test_b_continuation_stage import make_continuation_fixture


STAGES = ("evidence", "assemble", "quality", "continuation_prepare", "continuation_proof",
          "continuation_apply", "continuation_quality")


def reference(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


class ContinuationRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = make_continuation_fixture(self.root)
        self.original_inputs = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.workdir = self.root / "pipeline"
        self.fake_native = self.root / "synthetic-cv2-native.pyd"
        self.publication = self.root / "apply-publication.json"
        inputs = {name: str(self.fixture[name]) for name in (
            "source_path", "context_path", "review_path", "evidence_path", "package_path", "adjacent_source_path")}
        inputs.update(fake_native=str(self.fake_native), publication=str(self.publication))
        self.inputs = self.root / "runtime-inputs.json"
        self.inputs.write_text(json.dumps(inputs), encoding="utf-8")
        self.script = self.root / "continuation_runtime.py"
        self.script.write_text(textwrap.dedent(f'''
            import contextlib,importlib.abc,json,os,socket,sys
            from pathlib import Path
            from unittest.mock import patch
            class NoModels(importlib.abc.MetaPathFinder):
                def find_spec(self,fullname,path=None,target=None):
                    if fullname.split('.')[0] in {{'rapidocr_onnxruntime','rapid_latex_ocr','onnxruntime','torch','paddle','requests','httpx','aiohttp'}}:
                        raise AssertionError('forbidden continuation runtime import: '+fullname)
            sys.meta_path.insert(0,NoModels())
            class OfflineSocket(socket.socket):
                def connect(self,*a,**k): raise AssertionError('network forbidden')
                def connect_ex(self,*a,**k): raise AssertionError('network forbidden')
            socket.socket=OfflineSocket
            socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network forbidden'))
            sys.path[:0]=[{str(ROOT / 'src')!r},{str(ROOT / 'tools')!r}]
            from annotation.recognition import pipeline
            from run_pipeline_b import execute
            inputs=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
            phase=sys.argv[3]
            publish=pipeline.batch._put_object
            def publication(workdir,value):
                descriptor=publish(workdir,value)
                if (phase=='crash' and value.get('schema_version')==pipeline.STAGE_SCHEMA
                        and value['payload']['stage_id']=='continuation_apply'):
                    Path(inputs['publication']).write_text(json.dumps({{'descriptor':descriptor,
                        'attempt_id':value['payload']['attempt_id']}}),encoding='utf-8')
                    os._exit(74)
                return descriptor
            pipeline.batch._put_object=publication
            dependency_patch=contextlib.nullcontext()
            if phase=='native':
                import cv2
                dependency_patch=patch.object(cv2._native,'__file__',inputs['fake_native'])
            with dependency_patch:
                result=execute(inputs['source_path'],inputs['context_path'],inputs['review_path'],sys.argv[2],
                    evidence_path=inputs['evidence_path'],continuation_path=inputs['package_path'],
                    adjacent_source_path=inputs['adjacent_source_path'])
            print(json.dumps(result))
            raise SystemExit(result['exit_code'])
        '''), encoding="utf-8")

    def child(self, phase, expected=0):
        completed = subprocess.run([sys.executable, str(self.script), str(self.inputs), str(self.workdir), phase],
            cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING="utf-8"), capture_output=True, text=True,
            encoding="utf-8", timeout=45)
        self.assertEqual(completed.returncode, expected, completed.stdout + completed.stderr)
        return json.loads(completed.stdout) if completed.stdout.strip() else None

    def read_report(self, result):
        for path in (self.workdir / "objects").glob("*.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            if all(value.get(key) == item for key, item in result["report_ref"].items()):
                return value
        self.fail("CLI report has no actual immutable object")

    def assert_accepted(self, result):
        self.assertEqual(result["pipeline_state"], "READY")
        self.assertTrue(result["integrity_accepted"])
        self.assertTrue(result["audit_performed"])
        self.assertEqual(result["decision"], "HOLD")
        self.assertFalse(result["business_acceptance"])
        self.assertFalse(result["transcription_verified"])
        check_path = self.workdir / result["check"]["path"]
        self.assertEqual(hashlib.sha256(check_path.read_bytes()).hexdigest(), result["check"]["sha256"])
        check = json.loads(check_path.read_text(encoding="utf-8"))
        self.assertEqual(reference(check), result["check"]["artifact_ref"])
        self.assertTrue(check["payload"]["accepted"])
        self.assertEqual(check["payload"]["platform_actions"], [])
        report = self.read_report(result)
        self.assertEqual(report["payload"]["platform_actions"], [])
        self.assertEqual([row["stage_id"] for row in report["payload"]["stages"]], list(STAGES))
        for path, original in self.original_inputs.items():
            self.assertEqual(path.read_bytes(), original, str(path))
        return report

    def test_published_apply_orphan_is_preserved_but_never_consumed_after_real_process_death(self):
        self.assertIsNone(self.child("crash", expected=74))
        publication = json.loads(self.publication.read_text(encoding="utf-8"))
        orphan_path = self.workdir / publication["descriptor"]["path"]
        orphan_bytes = orphan_path.read_bytes()
        orphan = json.loads(orphan_bytes)
        old_attempt = publication["attempt_id"]
        self.assertEqual(orphan["payload"]["attempt_id"], old_attempt)
        self.assertEqual(orphan["payload"]["stage_id"], "continuation_apply")
        self.assertEqual(hashlib.sha256(orphan_bytes).hexdigest(), publication["descriptor"]["sha256"])
        published_before_resume = {path: path.read_bytes() for path in (self.workdir / "objects").glob("*.json")}
        with closing(sqlite3.connect(self.workdir / "pipeline.sqlite3")) as db:
            old_run, state, output, result_ref = db.execute(
                "SELECT run_id,state,output_json,result_ref_json FROM stage_attempts WHERE attempt_id=?", (old_attempt,)).fetchone()
            self.assertEqual(state, "RUNNING")
            self.assertIsNone(output)
            self.assertIsNone(result_ref)
            self.assertEqual(db.execute("SELECT count(*) FROM stage_attempts WHERE state='SUCCEEDED'").fetchone()[0], 5)
            self.assertEqual(db.execute("SELECT count(*) FROM stage_cache WHERE attempt_id=?", (old_attempt,)).fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM stage_events WHERE attempt_id=? AND event_type='STAGE_SUCCEEDED'",
                (old_attempt,)).fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM stage_events WHERE run_id=? AND event_type='RUN_FINISHED'",
                (old_run,)).fetchone()[0], 0)
        resumed = self.child("resume")
        report = self.assert_accepted(resumed)
        rows = report["payload"]["stages"]
        self.assertEqual([row["cached"] for row in rows], [True]*5+[False, False])
        applied = rows[5]
        self.assertNotEqual(applied["origin_attempt_id"], old_attempt)
        self.assertNotEqual(applied["output"], publication["descriptor"])
        self.assertEqual(applied["result_ref"], reference(orphan["payload"]["result"]))
        for path, content in published_before_resume.items():
            self.assertEqual(path.read_bytes(), content, str(path))
        with closing(sqlite3.connect(self.workdir / "pipeline.sqlite3")) as db:
            attempts = db.execute("SELECT attempt_id,state FROM stage_attempts WHERE stage_id='continuation_apply' ORDER BY started_at").fetchall()
            # Existing journal terminology is INTERRUPTED: the abandoned old
            # attempt is never promoted to success or reused as a cache origin.
            self.assertEqual(attempts, [(old_attempt, "INTERRUPTED"), (applied["origin_attempt_id"], "SUCCEEDED")])
            interrupted = db.execute("SELECT details_json FROM stage_events WHERE attempt_id=? AND event_type='STAGE_INTERRUPTED'",
                (old_attempt,)).fetchall()
            self.assertEqual(len(interrupted), 1)
            self.assertEqual(json.loads(interrupted[0][0])["origin_run_id"], old_run)
            self.assertEqual(db.execute("SELECT count(*) FROM stage_cache WHERE attempt_id=?", (old_attempt,)).fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT attempt_id FROM stage_cache WHERE stage_id='continuation_apply'").fetchone()[0],
                applied["origin_attempt_id"])
            hits = [(row[0], json.loads(row[1])) for row in db.execute(
                "SELECT attempt_id,details_json FROM stage_events WHERE run_id=? AND event_type='CACHE_HIT'", (report["run_id"],))]
            self.assertEqual(len(hits), 5)
            self.assertTrue(all(attempt != old_attempt and hit["output"] != publication["descriptor"] for attempt, hit in hits))

    def test_native_binary_digest_change_invalidates_only_four_continuation_stages(self):
        first_bytes = b"SYNTHETIC native dependency receipt version one; not an executable module"
        second_bytes = b"SYNTHETIC native dependency receipt version two; not an executable module"
        self.fake_native.write_bytes(first_bytes)
        first_result = self.child("native")
        first = self.assert_accepted(first_result)
        old_rows = first["payload"]["stages"]
        old_objects = {path: path.read_bytes() for path in (self.workdir / "objects").glob("*.json")}
        old_check_path = self.workdir / first_result["check"]["path"]
        old_check_bytes = old_check_path.read_bytes()
        self.fake_native.write_bytes(second_bytes)
        second_result = self.child("native")
        second = self.assert_accepted(second_result)
        new_rows = second["payload"]["stages"]
        self.assertEqual([row["cached"] for row in new_rows], [True]*3+[False]*4)
        for old, new in zip(old_rows[:3], new_rows[:3]):
            self.assertEqual(old["output"], new["output"])
            self.assertEqual(old["origin_attempt_id"], new["origin_attempt_id"])
            self.assertEqual(old["implementation"], new["implementation"])
            self.assertNotIn("opencv", new["implementation"]["dependencies"])
        for old, new in zip(old_rows[3:], new_rows[3:]):
            old_opencv = old["implementation"]["dependencies"]["opencv"]
            new_opencv = new["implementation"]["dependencies"]["opencv"]
            self.assertEqual(old_opencv["native_module"], dict(name=self.fake_native.name,
                sha256=hashlib.sha256(first_bytes).hexdigest()))
            self.assertEqual(new_opencv["native_module"], dict(name=self.fake_native.name,
                sha256=hashlib.sha256(second_bytes).hexdigest()))
            self.assertEqual(old_opencv["version"], new_opencv["version"])
            self.assertEqual(old_opencv["package_entry_sha256"], new_opencv["package_entry_sha256"])
            self.assertNotEqual(old["expected_key"], new["expected_key"])
            self.assertNotEqual(old["origin_attempt_id"], new["origin_attempt_id"])
        self.assertEqual(second["payload"]["counts"]["cache_hits"], 3)
        self.assertEqual(old_check_path.read_bytes(), old_check_bytes)
        for path, content in old_objects.items():
            self.assertEqual(path.read_bytes(), content, str(path))


if __name__ == "__main__":
    unittest.main()
