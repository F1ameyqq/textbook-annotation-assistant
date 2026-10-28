"""Durable B batch tests, including a genuinely killed worker subprocess."""
import copy
from contextlib import closing
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

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from annotation.recognition.baseline import digest, file_digest, load_source
from annotation.recognition.batch import run_batch
from annotation.recognition import batch


def manifest(directory, count=3):
    directory = Path(directory)
    assets = []
    for index in range(count):
        path = directory / "pages" / f"page-{index}.png"
        path.parent.mkdir(exist_ok=True)
        image = Image.new("RGB", (180, 100), "white")
        ImageDraw.Draw(image).text((15, 20), f"{index+1}. test page", fill="black")
        image.save(path)
        assets.append({"asset_id": f"page-{index}", "path": path.relative_to(directory).as_posix(),
                       "sha256": file_digest(path), "width": 180, "height": 100, "reading_order": index})
    source = {"schema_version": "b-source-trial/0.1", "artifact_id": "test-source", "book_id": "test-book",
              "scope_id": "declared-three-pages", "assets": assets}
    path = directory / "manifest.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    return path, source


def synthetic_result(source_path, *, use_ocr=False):
    """Honest synthetic minimal instance of baseline's provisional format."""
    source, inputs = load_source(Path(source_path))
    asset = inputs[0][0]
    box = [0, 0, asset["width"], asset["height"]]
    page = {"asset_id": asset["asset_id"], "source": asset,
            "regions": [{"region_id": "region-"+digest(asset)[:16], "asset_id": asset["asset_id"],
                         "bbox": [10, 10, 60, 30], "crop_id": "crop", "content_type": "unknown",
                         "role_candidate": None, "confidence": None, "text_hint": "",
                         "text_hint_is_final_transcription": False, "verification_status": "UNVERIFIED"}],
            "crop_transforms": [{"crop_id": "crop", "asset_id": asset["asset_id"], "original_bbox": box,
                                 "crop_to_original": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}],
            "ocr_lines": [], "split_info": {}, "issues": [],
            "coverage_evidence": {"method": "SYNTHETIC_TEST", "independent_of_recognizer": False,
                                  "can_authorize_quality_pass": False, "lines": []}}
    payload = {"pages": [page], "quality_decision": "NOT_EVALUATED", "limitations": ["SYNTHETIC_TEST"]}
    return {"schema_version": "b-evidence-trial/0.1", "kind": "EvidenceBundleTrial",
            "artifact_id": "synthetic-evidence-"+digest([source, payload])[:24], "revision": 1,
            "book_id": source["book_id"], "scope_id": source["scope_id"],
            "input_refs": [{"artifact_id": source["artifact_id"], "content_hash": digest(source)}],
            "producer": {"module": "SYNTHETIC_TEST", "ocr_enabled": use_ocr},
            "payload": payload, "content_hash": digest(payload)}


class CountingWorker:
    def __init__(self, *, revision=1, fail_once=None):
        self.cache_identity = {"revision": revision}
        self.calls = []
        self.fail_once = fail_once

    def __call__(self, path, *, use_ocr=False):
        source, _ = load_source(Path(path))
        aid = source["assets"][0]["asset_id"]
        self.calls.append(aid)
        if self.fail_once == aid:
            self.fail_once = None
            raise RuntimeError("synthetic temporary worker failure")
        return synthetic_result(path, use_ocr=use_ocr), {}


def read_object(workdir, descriptor):
    return json.loads((Path(workdir) / descriptor["path"]).read_text(encoding="utf-8"))


class BatchPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path, self.source = manifest(self.root)
        self.work = self.root / "work"
        self.worker = CountingWorker()

    def tearDown(self):
        self.tmp.cleanup()

    def run_batch(self, **kwargs):
        return run_batch(self.path, self.work, worker=self.worker, **kwargs)

    def test_bounded_run_then_resume_then_full_cache_preserve_declared_scope(self):
        first = self.run_batch(max_items=1)
        self.assertEqual(first["payload"]["counts"], {"declared": 3, "done": 1, "pending": 2,
                         "failed": 0, "invalidated": 0, "cache_hits": 0})
        self.assertIsNone(first["payload"]["bundle"])
        self.assertFalse(first["payload"]["batch_complete"])
        second = self.run_batch(max_items=1)
        self.assertEqual(second["payload"]["counts"]["done"], 2)
        self.assertEqual(second["payload"]["counts"]["cache_hits"], 1)
        third = self.run_batch()
        self.assertTrue(third["payload"]["batch_complete"])
        fourth = self.run_batch(max_items=0)
        self.assertEqual(len(self.worker.calls), 3)
        self.assertEqual(fourth["payload"]["counts"]["cache_hits"], 3)
        self.assertEqual(first["payload"]["job_id"], fourth["payload"]["job_id"])
        self.assertNotEqual(first["run_id"], fourth["run_id"])
        self.assertEqual(third["payload"]["bundle"], fourth["payload"]["bundle"])

    def test_all_source_files_are_validated_before_any_cached_or_budgeted_work(self):
        self.run_batch()
        calls = len(self.worker.calls)
        (self.root / self.source["assets"][-1]["path"]).write_bytes(b"not an image")
        with self.assertRaises(ValueError): self.run_batch(max_items=0)
        self.assertEqual(len(self.worker.calls), calls)

    def test_new_scope_and_book_never_reuse_old_entity_identities(self):
        previous = self.run_batch()
        for key, value in (("scope_id", "other-scope"), ("book_id", "other-book")):
            source = copy.deepcopy(self.source)
            source[key] = value
            self.path.write_text(json.dumps(source), encoding="utf-8")
            report = self.run_batch()
            self.assertEqual(report["payload"]["counts"]["cache_hits"], 0)
            self.assertNotEqual(report["payload"]["job_id"], previous["payload"]["job_id"])
            self.assertFalse(set(i["item_key"] for i in report["payload"]["items"]) &
                             set(i["item_key"] for i in previous["payload"]["items"]))
        self.assertEqual(len(self.worker.calls), 9)

    def test_one_changed_asset_invalidates_only_that_version(self):
        original = self.run_batch()
        old_bytes = {i["asset_id"]: (self.work / i["artifact"]["path"]).read_bytes()
                     for i in original["payload"]["items"]}
        asset = self.source["assets"][1]
        image_path = self.root / asset["path"]
        image = Image.open(image_path).convert("RGB")
        image.putpixel((4, 4), (1, 2, 3))
        image.save(image_path)
        asset["sha256"] = file_digest(image_path)
        self.source["artifact_id"] = "new-source-version"
        self.path.write_text(json.dumps(self.source), encoding="utf-8")
        report = self.run_batch()
        self.assertEqual(report["payload"]["counts"]["cache_hits"], 2)
        self.assertEqual(report["payload"]["counts"]["invalidated"], 1)
        self.assertEqual(self.worker.calls[-1], "page-1")
        self.assertEqual(len(self.worker.calls), 4)
        for item in original["payload"]["items"]:
            self.assertEqual((self.work / item["artifact"]["path"]).read_bytes(), old_bytes[item["asset_id"]])
        with closing(sqlite3.connect(self.work / "batch.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 2)

    def test_added_asset_reuses_only_prior_declared_assets_and_merge_waits(self):
        original = self.run_batch()
        new = copy.deepcopy(self.source["assets"][0])
        new.update(asset_id="new-page", reading_order=3)
        self.source["assets"].append(new)
        self.path.write_text(json.dumps(self.source), encoding="utf-8")
        report = self.run_batch(max_items=0)
        self.assertEqual(report["payload"]["counts"]["declared"], 4)
        self.assertEqual(report["payload"]["counts"]["done"], 3)
        self.assertEqual(report["payload"]["counts"]["pending"], 1)
        self.assertIsNone(report["payload"]["bundle"])
        self.assertEqual(len(self.worker.calls), 3)
        self.assertNotEqual(original["payload"]["job_id"], report["payload"]["job_id"])

    def test_worker_config_and_ocr_mode_changes_create_new_immutable_versions(self):
        original = self.run_batch()
        old_paths = [i["artifact"]["path"] for i in original["payload"]["items"]]
        self.worker.cache_identity = {"revision": 2}
        changed = self.run_batch()
        self.assertEqual(changed["payload"]["counts"]["invalidated"], 3)
        self.assertEqual(changed["payload"]["counts"]["cache_hits"], 0)
        mode = self.run_batch(use_ocr=True)
        self.assertEqual(mode["payload"]["counts"]["invalidated"], 3)
        self.assertEqual(len(self.worker.calls), 9)
        self.assertTrue(all((self.work / p).exists() for p in old_paths))
        self.assertEqual(mode["payload"]["recognizer"]["execution_kind"], "SYNTHETIC_TEST")

    def test_corrupt_object_is_invalidated_then_retried_without_overwrite(self):
        original = self.run_batch()
        bad = original["payload"]["items"][1]["artifact"]
        path = self.work / bad["path"]
        path.write_bytes(b"CORRUPTED ORIGINAL RETAINED")
        bounded = self.run_batch(max_items=0)
        self.assertEqual(bounded["payload"]["counts"]["done"], 2)
        self.assertEqual(bounded["payload"]["counts"]["pending"], 1)
        self.assertEqual(bounded["payload"]["counts"]["invalidated"], 1)
        self.assertIsNone(bounded["payload"]["bundle"])
        recovered = self.run_batch()
        self.assertTrue(recovered["payload"]["batch_complete"])
        self.assertEqual(path.read_bytes(), b"CORRUPTED ORIGINAL RETAINED")
        self.assertNotEqual(recovered["payload"]["items"][1]["artifact"]["path"], bad["path"])
        self.assertEqual(len(self.worker.calls), 4)

    def test_missing_object_and_wrong_source_output_are_not_successful(self):
        report = self.run_batch()
        (self.work / report["payload"]["items"][0]["artifact"]["path"]).unlink()
        pending = self.run_batch(max_items=0)
        self.assertEqual(pending["payload"]["counts"]["pending"], 1)
        def wrong_source(path, *, use_ocr=False):
            result = synthetic_result(path, use_ocr=use_ocr)
            result["payload"]["pages"][0]["source"]["sha256"] = "0"*64
            result["content_hash"] = digest(result["payload"])
            return result
        result = run_batch(self.path, self.root / "wrong-worker", worker=wrong_source)
        self.assertEqual(result["payload"]["counts"]["failed"], 3)
        self.assertEqual(result["payload"]["counts"]["done"], 0)
        self.assertIsNone(result["payload"]["bundle"])

    def test_cached_object_without_real_origin_or_terminal_event_is_not_a_cache_success(self):
        first = self.run_batch()
        origin = read_object(self.work, first["payload"]["items"][0]["artifact"])["payload"]["attempt_id"]
        with closing(sqlite3.connect(self.work / "batch.sqlite3")) as db:
            db.execute("DELETE FROM events WHERE attempt_id=? AND event_type='ATTEMPT_SUCCEEDED'", (origin,))
            db.commit()
        invalid = self.run_batch(max_items=0)
        self.assertEqual(invalid["payload"]["counts"]["done"], 2)
        self.assertEqual(invalid["payload"]["counts"]["pending"], 1)
        self.assertEqual(invalid["payload"]["counts"]["cache_hits"], 2)
        self.assertEqual(invalid["payload"]["counts"]["invalidated"], 1)
        recovered = self.run_batch()
        self.assertTrue(recovered["payload"]["batch_complete"])
        self.assertEqual(len(self.worker.calls), 4)

    def test_transient_failure_is_durable_and_later_retry_only_processes_failure(self):
        self.worker.fail_once = "page-1"
        first = self.run_batch()
        self.assertEqual(first["payload"]["counts"]["failed"], 1)
        self.assertEqual(first["payload"]["counts"]["done"], 2)
        self.assertIsNone(first["payload"]["bundle"])
        second = self.run_batch()
        self.assertTrue(second["payload"]["batch_complete"])
        self.assertEqual(second["payload"]["counts"]["cache_hits"], 2)
        self.assertEqual(len(self.worker.calls), 4)
        self.assertEqual(second["payload"]["items"][1]["attempt_count"], 2)
        with closing(sqlite3.connect(self.work / "batch.sqlite3")) as db:
            states = [r[0] for r in db.execute("SELECT state FROM attempts WHERE asset_id='page-1' ORDER BY attempt_number")]
            self.assertEqual(states, ["FAILED", "SUCCEEDED"])

    def test_worker_observes_committed_running_state_before_execution(self):
        work = self.root / "intent"
        def inspect_running(path, *, use_ocr=False):
            with closing(sqlite3.connect(work / "batch.sqlite3")) as db:
                state = db.execute("SELECT state FROM attempts ORDER BY started_at DESC LIMIT 1").fetchone()[0]
                if state != "RUNNING": raise AssertionError("missing durable intent")
            return synthetic_result(path, use_ocr=use_ocr)
        report = run_batch(self.path, work, worker=inspect_running)
        self.assertTrue(report["payload"]["batch_complete"])

    def test_merge_has_full_source_and_exact_per_page_original_evidence(self):
        report = self.run_batch()
        bundle = read_object(self.work, report["payload"]["bundle"])
        self.assertEqual(bundle["schema_version"], "b-evidence-trial/0.1")
        binding = bundle["payload"]["batch_binding"]
        self.assertEqual(binding["source_manifest"], self.source)
        self.assertEqual(binding["source_ref"], report["payload"]["source_ref"])
        self.assertEqual([p["asset_id"] for p in bundle["payload"]["pages"]], report["payload"]["declared_asset_ids"])
        for item, page, ref in zip(report["payload"]["items"], bundle["payload"]["pages"], binding["per_page_refs"]):
            original = read_object(self.work, item["artifact"])
            self.assertEqual(page, original["payload"]["result"]["payload"]["pages"][0])
            self.assertEqual(ref["artifact_ref"], item["artifact"]["artifact_ref"])
        self.assertEqual(bundle["producer"]["execution_kind"], "SYNTHETIC_TEST")
        self.assertFalse(binding["transcription_verified"])
        self.assertFalse(binding["business_acceptance"])
        self.assertEqual(binding["platform_actions"], [])

    def test_sql_attempt_events_and_report_binding_survive_fresh_connections(self):
        report = self.run_batch()
        with closing(sqlite3.connect(self.work / "batch.sqlite3")) as db:
            rows = db.execute("SELECT event_type,details_json FROM events WHERE job_id=?", (report["payload"]["job_id"],)).fetchall()
            self.assertEqual(sum(kind == "ATTEMPT_STARTED" for kind, _ in rows), 3)
            self.assertEqual(sum(kind == "ATTEMPT_SUCCEEDED" for kind, _ in rows), 3)
            self.assertTrue(all(json.loads(details)["run_id"] == report["run_id"] for _, details in rows))
            finish = json.loads(next(details for kind, details in rows if kind == "RUN_FINISHED"))
            self.assertEqual(finish["report_ref"]["content_hash"], report["content_hash"])
            self.assertEqual(read_object(self.work, finish["report_artifact"]), report)

    def test_default_geometry_worker_does_not_import_ocr_and_is_not_synthetic(self):
        original_import = __import__
        def guarded(name, *args, **kwargs):
            if name.startswith(("rapidocr", "onnxruntime")): raise AssertionError("unexpected OCR import")
            return original_import(name, *args, **kwargs)
        with mock.patch("builtins.__import__", side_effect=guarded):
            report = run_batch(self.path, self.root / "default", max_items=1)
        self.assertEqual(report["payload"]["recognizer"]["execution_kind"], "BASELINE_GEOMETRY")
        self.assertEqual(report["payload"]["counts"]["done"], 1)
        self.assertEqual(report["payload"]["counts"]["pending"], 2)

    def test_stale_raw_ref_and_false_verified_output_are_failed(self):
        for mutation in ("input", "verification", "geometry"):
            with self.subTest(mutation=mutation):
                def invalid(path, *, use_ocr=False):
                    result = synthetic_result(path, use_ocr=use_ocr)
                    if mutation == "input": result["input_refs"][0]["artifact_id"] = "stale"
                    elif mutation == "verification": result["payload"]["pages"][0]["regions"][0]["verification_status"] = "VERIFIED"
                    else: result["payload"]["pages"][0]["regions"][0]["bbox"] = [-1, 0, 30, 20]
                    result["content_hash"] = digest(result["payload"])
                    return result
                report = run_batch(self.path, self.root / mutation, worker=invalid)
                self.assertEqual(report["payload"]["counts"]["failed"], 3)
                self.assertIsNone(report["payload"]["bundle"])

    def test_invalid_budget_types_reject_without_worker_or_database(self):
        for value in (-1, True, 1.5, "2"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): self.run_batch(max_items=value)
        self.assertEqual(self.worker.calls, [])
        self.assertFalse(self.work.exists())

    def test_real_worker_code_change_cannot_reuse_the_previous_worker_cache(self):
        previous = self.run_batch()
        def new_implementation(path, *, use_ocr=False):
            result = synthetic_result(path, use_ocr=use_ocr)
            result["payload"]["pages"][0]["regions"][0]["text_hint"] = "new algorithm observation"
            result["content_hash"] = digest(result["payload"])
            return result
        new_implementation.cache_identity = copy.deepcopy(self.worker.cache_identity)
        changed = run_batch(self.path, self.work, worker=new_implementation)
        self.assertNotEqual(previous["payload"]["recognizer"]["code"]["worker"],
                            changed["payload"]["recognizer"]["code"]["worker"])
        self.assertEqual(changed["payload"]["counts"]["invalidated"], 3)
        self.assertEqual(changed["payload"]["counts"]["cache_hits"], 0)
        self.assertTrue(all((self.work / i["artifact"]["path"]).exists() for i in previous["payload"]["items"]))

    def test_default_configuration_change_and_dependency_version_have_separate_cache_versions(self):
        work = self.root / "default-versions"
        original = run_batch(self.path, work)
        backend_module = batch.baseline.legacy_backend()
        backend_module.CFG = {**backend_module.CFG, "thresh": backend_module.CFG["thresh"]+1}
        with mock.patch.object(batch.baseline, "legacy_backend", return_value=backend_module):
            configured = run_batch(self.path, work)
        self.assertEqual(configured["payload"]["counts"]["invalidated"], 3)
        self.assertEqual(configured["payload"]["counts"]["cache_hits"], 0)
        version = batch.importlib.metadata.version
        def changed_version(name):
            return version(name)+".test_dependency_change" if name == "Pillow" else version(name)
        with mock.patch.object(batch.importlib.metadata, "version", side_effect=changed_version):
            dependency = run_batch(self.path, work)
        self.assertEqual(dependency["payload"]["counts"]["invalidated"], 3)
        self.assertEqual(dependency["payload"]["counts"]["cache_hits"], 0)
        self.assertEqual(len({r["payload"]["job_id"] for r in (original, configured, dependency)}), 3)

    def test_arbitrary_portable_asset_path_can_use_a_directory_named_source_json(self):
        asset = self.source["assets"][0]
        target = self.root / "source.json" / "image.png"
        target.parent.mkdir()
        target.write_bytes((self.root / asset["path"]).read_bytes())
        asset["path"] = "source.json/image.png"
        self.path.write_text(json.dumps(self.source), encoding="utf-8")
        report = self.run_batch()
        self.assertTrue(report["payload"]["batch_complete"])
        self.assertEqual(read_object(self.work, report["payload"]["items"][0]["artifact"])["payload"]["asset"]["path"],
                         "source.json/image.png")

    def test_process_death_after_object_publication_leaves_orphan_then_safe_retry(self):
        script = self.root / "publication_crash.py"
        script.write_text(textwrap.dedent(f'''
            import json,os,sys
            sys.path.insert(0,{str(ROOT/'src')!r})
            sys.path.insert(0,{str(ROOT/'tests')!r})
            import annotation.recognition.batch as module
            from test_b_batch import synthetic_result
            def worker(path,*,use_ocr=False):
                return synthetic_result(path,use_ocr=use_ocr)
            publish=module._put_object
            def crash_after_publish(workdir,value):
                descriptor=publish(workdir,value)
                if value['schema_version']==module.ITEM_SCHEMA and os.environ.get('BATCH_CRASH')=='1':
                    os._exit(29)
                return descriptor
            module._put_object=crash_after_publish
            report=module.run_batch(sys.argv[1],sys.argv[2],worker=worker)
            print(json.dumps(report))
        '''), encoding="utf-8")
        env = dict(os.environ, BATCH_CRASH="1", PYTHONIOENCODING="utf-8")
        first = subprocess.run([sys.executable, str(script), str(self.path), str(self.work)], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(first.returncode, 29, first.stderr)
        orphans = {p.name: p.read_bytes() for p in (self.work / "objects").glob("*.json")}
        self.assertEqual(len(orphans), 1)
        with closing(sqlite3.connect(self.work / "batch.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM cache_entries").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT state FROM items WHERE asset_id='page-0'").fetchone()[0], "RUNNING")
        env.pop("BATCH_CRASH")
        resumed = subprocess.run([sys.executable, str(script), str(self.path), str(self.work)], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        report = json.loads(resumed.stdout)
        self.assertTrue(report["payload"]["batch_complete"])
        self.assertEqual(report["payload"]["counts"]["cache_hits"], 0)
        self.assertTrue(all((self.work / "objects" / name).read_bytes() == value for name, value in orphans.items()))
        self.assertFalse(set(orphans) & {Path(i["artifact"]["path"]).name for i in report["payload"]["items"]})

    def test_real_process_death_is_recorded_interrupted_and_resume_does_not_rerun_success(self):
        script = self.root / "crash_worker.py"
        script.write_text(textwrap.dedent(f'''
            import json,os,sys
            from pathlib import Path
            sys.path.insert(0,{str(ROOT/'src')!r})
            sys.path.insert(0,{str(ROOT/'tests')!r})
            from annotation.recognition.batch import run_batch
            from test_b_batch import synthetic_result
            def worker(path,*,use_ocr=False):
                source=json.loads(Path(path).read_text(encoding='utf-8'))
                if source['assets'][0]['asset_id']=='page-1' and os.environ.get('BATCH_CRASH')=='1':
                    os._exit(23)
                return synthetic_result(path,use_ocr=use_ocr)
            report=run_batch(sys.argv[1],sys.argv[2],worker=worker)
            print(json.dumps(report))
        '''), encoding="utf-8")
        env = dict(os.environ, BATCH_CRASH="1", PYTHONIOENCODING="utf-8")
        first = subprocess.run([sys.executable, str(script), str(self.path), str(self.work)], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(first.returncode, 23, first.stderr)
        with closing(sqlite3.connect(self.work / "batch.sqlite3")) as db:
            self.assertEqual([r[0] for r in db.execute("SELECT state FROM items ORDER BY asset_id")], ["DONE", "RUNNING", "PENDING"])
        env.pop("BATCH_CRASH")
        resumed = subprocess.run([sys.executable, str(script), str(self.path), str(self.work)], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        report = json.loads(resumed.stdout)
        self.assertTrue(report["payload"]["batch_complete"])
        self.assertEqual(report["payload"]["counts"]["cache_hits"], 1)
        with closing(sqlite3.connect(self.work / "batch.sqlite3")) as db:
            self.assertEqual([r[0] for r in db.execute("SELECT state FROM attempts WHERE asset_id='page-1' ORDER BY attempt_number")], ["INTERRUPTED", "SUCCEEDED"])
            self.assertEqual(db.execute("SELECT count(*) FROM attempts WHERE asset_id='page-0'").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM events WHERE event_type='INTERRUPTED'").fetchone()[0], 1)


if __name__ == "__main__": unittest.main()
