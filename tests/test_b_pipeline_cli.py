"""Independent CLI contracts using small synthetic sources, never real OCR.

The cached evidence is explicitly SYNTHETIC_TEST. Live full-stage tests use a
declared injected batch worker and a patched synthetic refiner, never a model.
Existing five-page real source images are neither required nor impersonated.
"""
import contextlib
import copy
import hashlib
import importlib.metadata
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]
from annotation.recognition.baseline import digest
from annotation.recognition.offline import artifact
from run_pipeline_b import execute, main


def reference(value):
    return {k: value[k] for k in ("artifact_id", "revision", "content_hash")}


def synthetic_refined(source, context, baseline=None, schema="b-evidence-trial/0.2"):
    pages = []
    for asset in source["assets"]:
        aid = asset["asset_id"]
        window = context["pages"][aid]["windows"][0]
        role = context["pages"][aid]["role"]
        line = dict(line_id=f"{aid}/ocr/0", bbox=[30, 40, 300, 60],
            text="1. 求2+2的值。" if role == "question" else "1.4", score=1.0,
            location=dict(column=window["column"], window_index=0, section_path=window["path"]))
        pages.append(dict(asset_id=aid, source=copy.deepcopy(asset), page_role=role,
            layout=dict(mode="two_columns", cut_x=350, verified=False, method="SYNTHETIC_TEST"),
            ocr_lines=[line], answer_detail_lines=[], unscoped_line_ids=[]))
    payload = dict(pages=pages, quality_decision="NOT_EVALUATED", context=copy.deepcopy(context),
        history_annotations_consumed=False, limitations=["SYNTHETIC_TEST: unverified generated CLI fixture"])
    context_ref = dict(artifact_id=context["artifact_id"], content_hash=digest(context))
    inputs = ([reference(baseline)] if baseline else
        [dict(artifact_id="synthetic-baseline-reference", revision=1, content_hash=digest(source))]) + [context_ref]
    producer = dict(module="test_b_pipeline_cli.synthetic_refined", version="0.1",
        execution_kind="SYNTHETIC_TEST")
    if baseline:
        producer["baseline_producer"] = copy.deepcopy(baseline["producer"])
    return artifact(schema, "EvidenceBundleTrial", source, payload, inputs, producer)


class SyntheticOCRWorker:
    """Fixture-only baseline producer; it makes no OCR-engine call."""
    cache_identity = {"kind": "pipeline-cli-fixture-baseline/0.1"}

    def __init__(self):
        self.calls = []

    def __call__(self, source_path, *, use_ocr=False):
        source = json.loads(Path(source_path).read_text(encoding="utf-8"))
        asset = source["assets"][0]
        self.calls.append(asset["asset_id"])
        crop_id = asset["asset_id"] + "-synthetic-crop"
        page = dict(asset_id=asset["asset_id"], source=copy.deepcopy(asset),
            regions=[], crop_transforms=[dict(crop_id=crop_id, asset_id=asset["asset_id"],
                original_bbox=[0, 0, asset["width"], asset["height"]],
                crop_to_original=[[1, 0, 0], [0, 1, 0], [0, 0, 1]])],
            ocr_lines=[dict(bbox=[30, 40, 300, 60], text="synthetic raw line", score=1.0, crop_id=crop_id)],
            issues=[], coverage_evidence={"method": "SYNTHETIC_TEST"})
        payload = dict(pages=[page], quality_decision="NOT_EVALUATED", limitations=["SYNTHETIC_TEST"])
        return dict(schema_version="b-evidence-trial/0.1", kind="EvidenceBundleTrial", revision=1,
            artifact_id="synthetic-ocr-fixture-" + digest(source)[:24],
            book_id=source["book_id"], scope_id=source["scope_id"],
            producer=dict(module="test_b_pipeline_cli.SyntheticOCRWorker", execution_kind="SYNTHETIC_TEST", ocr_enabled=use_ocr),
            input_refs=[dict(artifact_id=source["artifact_id"], content_hash=digest(source))],
            content_hash=digest(payload), payload=payload), {}


class PipelineCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workdir = self.root / "pipeline"
        self.source_path = self.root / "source.json"
        self.context_path = self.root / "context.json"
        self.review_path = self.root / "review.json"
        self.evidence_path = self.root / "synthetic-evidence.json"
        assets = []
        for i, aid in enumerate(("synthetic-question", "synthetic-answer")):
            image = Image.new("RGB", (700, 400), "white")
            draw = ImageDraw.Draw(image)
            for left in (30 + i, 390 + i):
                for y in (40, 80, 120, 160):
                    draw.rectangle((left, y, left + 250, y + 9), fill="black")
            path = self.root / (aid + ".png")
            image.save(path)
            assets.append(dict(asset_id=aid, path=path.name, width=700, height=400, reading_order=i,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(), reference_quality="SYNTHETIC_TEST"))
        self.source = dict(schema_version="b-source-trial/0.1", artifact_id="synthetic-pipeline-cli-source",
            book_id="synthetic-book", scope_id="synthetic-two-assets", assets=assets)
        self.context = dict(schema_version="b-context-trial/0.1", artifact_id="synthetic-context",
            book_id=self.source["book_id"], scope_id=self.source["scope_id"], reference_quality="SYNTHETIC_TEST",
            pages={a["asset_id"]: dict(sha256=a["sha256"], role="question" if i == 0 else "answer",
                windows=[dict(column=0, y_range=[20, 380], path=["Synthetic section"])]) for i, a in enumerate(assets)})
        self.review = dict(schema_version="b-review-trial/0.1", artifact_id="synthetic-review",
            book_id=self.source["book_id"], scope_id=self.source["scope_id"], reference_quality="SYNTHETIC_TEST",
            provenance="Generated CLI fixture; not human gold or real-image OCR",
            question_census={assets[0]["asset_id"]: dict(sha256=assets[0]["sha256"], printed_numbers=["1"])},
            answer_checks=[])
        self.evidence = synthetic_refined(self.source, self.context)
        for path, value in ((self.source_path, self.source), (self.context_path, self.context),
                (self.review_path, self.review), (self.evidence_path, self.evidence)):
            self.write(path, value)

    def write(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def args(self, *extra, cached=True):
        result = ["--source", str(self.source_path), "--context", str(self.context_path),
            "--review", str(self.review_path), "--workdir", str(self.workdir)]
        if cached:
            result += ["--evidence", str(self.evidence_path)]
        return result + list(extra)

    def cli(self, *extra, cached=True, expected=0):
        completed = subprocess.run([sys.executable, str(ROOT / "tools/run_pipeline_b.py"),
            *self.args(*extra, cached=cached)], cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", timeout=30)
        self.assertEqual(completed.returncode, expected, completed.stdout + completed.stderr)
        return json.loads(completed.stdout)

    def report(self, result):
        for path in self.workdir.rglob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if isinstance(value, dict) and all(value.get(k) == v for k, v in result["report_ref"].items()):
                return value
        self.fail("actual persisted report reference is missing")

    def stages(self, result):
        return {stage["stage_id"]: stage for stage in self.report(result)["payload"]["stages"]}

    def stage_result(self, stage):
        path = (self.workdir / stage["output"]["path"]).resolve()
        self.assertTrue(path.is_relative_to(self.workdir.resolve()))
        return json.loads(path.read_text(encoding="utf-8"))["payload"]["result"]

    def assert_input_rejected(self, result):
        self.assertFalse(result["integrity_accepted"])
        self.assertEqual(result["pipeline_state"], "FAILED")
        self.assertEqual(result["decision"], "HOLD")
        # A missing implementation is not evidence that a data fault was caught.
        self.assertNotEqual(result.get("error", {}).get("stage"), "SETUP_FAILED")

    def test_cached_stops_resume_and_quality_hold_is_ready_without_new_refinement(self):
        original = self.evidence_path.read_bytes()
        first = self.cli("--stop-after", "recognition")
        self.assertEqual(first["pipeline_state"], "PARTIAL")
        self.assertEqual(first["mode"], "CACHED_INPUT")
        stages = self.stages(first)
        self.assertEqual(set(stages), {"evidence", "assemble", "quality"})
        self.assertEqual(stages["evidence"]["state"], "DONE")
        self.assertEqual(stages["assemble"]["state"], "WAITING")
        self.assertEqual(self.stage_result(stages["evidence"]), self.evidence)
        check_path = self.workdir / first["check"]["path"]
        first_check = check_path.read_bytes()
        second = self.cli("--stop-after", "assemble")
        second_stages = self.stages(second)
        self.assertTrue(second_stages["evidence"]["cached"])
        self.assertEqual(second_stages["assemble"]["state"], "DONE")
        self.assertEqual(second_stages["quality"]["state"], "WAITING")
        third = self.cli()
        final_stages = self.stages(third)
        self.assertEqual(third["pipeline_state"], "READY")
        self.assertTrue(third["integrity_accepted"])
        self.assertTrue(all(final_stages[name]["cached"] for name in ("evidence", "assemble")))
        self.assertEqual(self.stage_result(final_stages["quality"])["payload"]["decision"], "HOLD")
        self.assertEqual(third["decision"], "HOLD")
        self.assertFalse(third["business_acceptance"])
        self.assertFalse(third["transcription_verified"])
        self.assertEqual(self.evidence_path.read_bytes(), original)
        self.assertEqual(check_path.read_bytes(), first_check)

    def test_review_metadata_change_only_recomputes_quality_with_same_review_id(self):
        first = self.cli()
        stages = self.stages(first)
        self.review["provenance"] = "Changed synthetic development note; artifact_id unchanged"
        self.write(self.review_path, self.review)
        second = self.cli()
        changed = self.stages(second)
        self.assertEqual(second["pipeline_state"], "READY")
        for name in ("evidence", "assemble"):
            self.assertTrue(changed[name]["cached"])
            self.assertEqual(changed[name]["result_ref"], stages[name]["result_ref"])
        self.assertFalse(changed["quality"]["cached"])
        self.assertNotEqual(changed["quality"]["result_ref"], stages["quality"]["result_ref"])

    def test_cached_context_change_is_rejected_without_rewriting_evidence(self):
        self.cli()
        original = self.evidence_path.read_bytes()
        self.context["pages"]["synthetic-question"]["windows"][0]["path"] = ["Changed section"]
        self.write(self.context_path, self.context)
        result = self.cli(expected=1)
        self.assert_input_rejected(result)
        self.assertEqual(self.evidence_path.read_bytes(), original)

    def test_live_default_geometry_stops_with_ocr_required_without_implicit_model(self):
        result = self.cli(cached=False)
        stages = self.stages(result)
        self.assertEqual(result["pipeline_state"], "PARTIAL")
        self.assertEqual(result["mode"], "LIVE_BATCH")
        self.assertEqual(stages["recognition"]["state"], "DONE")
        self.assertEqual(stages["refine"]["state"], "WAITING")
        self.assertEqual(stages["refine"]["reason"], "OCR_REQUIRED")
        self.assertTrue(result["integrity_accepted"])
        child = self.stage_result(stages["recognition"])
        self.assertEqual(child["payload"]["recognizer"]["execution_kind"], "BASELINE_GEOMETRY")
        self.assertFalse(child["payload"]["recognizer"]["use_ocr"])

    def test_live_recognition_budget_never_shrinks_declared_source_pages(self):
        first = self.cli("--max-items", "1", cached=False)
        recognition = self.stage_result(self.stages(first)["recognition"])
        self.assertEqual(recognition["payload"]["counts"]["declared"], 2)
        self.assertEqual(recognition["payload"]["counts"]["done"], 1)
        self.assertEqual(recognition["payload"]["counts"]["pending"], 1)
        self.assertEqual(first["pipeline_state"], "PARTIAL")
        second = self.cli(cached=False)
        recognition = self.stage_result(self.stages(second)["recognition"])
        self.assertEqual(recognition["payload"]["counts"]["declared"], 2)
        self.assertEqual(recognition["payload"]["counts"]["done"], 2)
        self.assertEqual(second["pipeline_state"], "PARTIAL")

    def test_cached_and_geometry_fresh_processes_forbid_ocr_imports_and_network(self):
        script = r'''
import importlib.abc,runpy,socket,sys
class DenyImports(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'rapidocr_onnxruntime','rapid_latex_ocr','onnxruntime','torch','paddle','requests','httpx','aiohttp'}:
            raise AssertionError('forbidden cached import: '+fullname)
sys.meta_path.insert(0,DenyImports())
class NoNetworkSocket(socket.socket):
    def connect(self,*a,**k): raise AssertionError('network forbidden')
    def connect_ex(self,*a,**k): raise AssertionError('network forbidden')
socket.socket=NoNetworkSocket
socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden'))
tool=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(tool,run_name='__main__')
'''
        for cached in (True, False):
            args = self.args(cached=cached)
            args[args.index("--workdir") + 1] = str(self.root / ("cached-no-models" if cached else "live-no-models"))
            with self.subTest(cached=cached):
                completed = subprocess.run([sys.executable, "-c", script, str(ROOT / "tools/run_pipeline_b.py"),
                    *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                result = json.loads(completed.stdout)
                self.assertEqual(result["mode"], "CACHED_INPUT" if cached else "LIVE_BATCH")
                self.assertEqual(result["pipeline_state"], "READY" if cached else "PARTIAL")

    def test_cached_missing_page_is_rejected_instead_of_reducing_scope(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["payload"]["pages"].pop()
        evidence["content_hash"] = digest(evidence["payload"])
        self.write(self.evidence_path, evidence)
        result = self.cli(expected=1)
        self.assert_input_rejected(result)
        self.assertEqual(len(self.source["assets"]), 2)

    def test_cached_payload_edit_without_hash_update_is_rejected(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["payload"]["pages"][0]["ocr_lines"][0]["text"] = "edited unbound OCR"
        self.write(self.evidence_path, evidence)
        result = self.cli(expected=1)
        self.assert_input_rejected(result)

    def test_baseline_01_cannot_be_imported_as_already_refined_or_fake_cpu(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["schema_version"] = "b-evidence-trial/0.1"
        evidence["producer"]["ocr_enabled"] = True
        self.write(self.evidence_path, evidence)
        result = self.cli(expected=1)
        self.assertEqual(result["mode"], "CACHED_INPUT")
        self.assert_input_rejected(result)

    def test_cached_synthetic_03_preserves_import_and_matching_graph_schema(self):
        evidence = synthetic_refined(self.source, self.context, schema="b-evidence-trial/0.3")
        self.write(self.evidence_path, evidence)
        result = self.cli()
        stages = self.stages(result)
        self.assertEqual(self.stage_result(stages["evidence"]), evidence)
        self.assertEqual(self.stage_result(stages["assemble"])["schema_version"], "b-graph-trial/0.3")
        self.assertEqual(self.stage_result(stages["quality"])["schema_version"], "b-check-trial/0.3")
        self.assertEqual(result["mode"], "CACHED_INPUT")
        self.assertEqual(result["pipeline_state"], "READY")
        self.assertFalse(result["business_acceptance"])

    def test_cached_incompatible_flags_and_unknown_stage_are_argparse_errors(self):
        cases = (("--ocr",), ("--max-items", "1"), ("--stop-after", "refine"), ("--stop-after", "unknown"))
        for flags in cases:
            with self.subTest(flags=flags), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    main(self.args(*flags))
                self.assertEqual(cm.exception.code, 2)
        self.assertFalse(self.workdir.exists())

    def test_live_nonpositive_budget_is_argparse_error(self):
        for value in ("0", "-1", "1.5"):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    main(self.args("--max-items", value, cached=False))
                self.assertEqual(cm.exception.code, 2)
        self.assertFalse(self.workdir.exists())

    def test_network_source_is_refused_before_pipeline_initialization(self):
        for value in ("https://example.invalid/source.json", "//server/share/source.json"):
            args = self.args()
            args[1] = value
            with self.subTest(value=value), patch("run_pipeline_b.execute") as runner, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    main(args)
                self.assertEqual(cm.exception.code, 2)
                runner.assert_not_called()

    def test_live_synthetic_context_change_reuses_recognition_only(self):
        from annotation.recognition.pipeline import run_pipeline
        worker = SyntheticOCRWorker()
        refine_calls = []
        def refiner(source_path, baseline, context):
            refine_calls.append(digest(context))
            source = json.loads(Path(source_path).read_text(encoding="utf-8"))
            return synthetic_refined(source, context, baseline=baseline)
        def runner(source, context, review, workdir, **kwargs):
            return run_pipeline(source, context, review, workdir, worker=worker, **kwargs)
        def run(**kwargs):
            return execute(self.source_path, self.context_path, self.review_path, self.workdir,
                use_ocr=True, runner=runner, **kwargs)
        version, find_spec = importlib.metadata.version, importlib.util.find_spec
        def no_model_version(distribution):
            if distribution in {"rapidocr-onnxruntime", "rapid-latex-ocr", "onnxruntime"}:
                raise AssertionError("synthetic full-stage tests must not need optional model dependencies")
            return version(distribution)
        def no_model_spec(module, *args, **kwargs):
            if module.split(".")[0] in {"rapidocr_onnxruntime", "rapid_latex_ocr", "onnxruntime"}:
                raise AssertionError("synthetic full-stage tests must not locate model runtimes")
            return find_spec(module, *args, **kwargs)
        with patch("annotation.recognition.pipeline.refine", new=refiner), \
                patch("importlib.metadata.version", new=no_model_version), \
                patch("importlib.util.find_spec", new=no_model_spec):
            first = run(stop_after="refine")
            initial = self.stages(first)
            self.assertEqual(first["pipeline_state"], "PARTIAL")
            self.assertEqual(initial["refine"]["state"], "DONE")
            second = run()
            complete = self.stages(second)
            self.assertEqual(second["pipeline_state"], "READY")
            self.assertTrue(complete["recognition"]["cached"])
            self.assertTrue(complete["refine"]["cached"])
            self.context["pages"]["synthetic-question"]["windows"][0]["path"] = ["Changed section"]
            self.context["pages"]["synthetic-answer"]["windows"][0]["path"] = ["Changed section"]
            self.write(self.context_path, self.context)
            third = run()
            changed = self.stages(third)
        self.assertEqual(third["pipeline_state"], "READY")
        self.assertTrue(changed["recognition"]["cached"])
        self.assertEqual(changed["recognition"]["result_ref"], complete["recognition"]["result_ref"])
        for name in ("refine", "assemble", "quality"):
            self.assertFalse(changed[name]["cached"])
            self.assertNotEqual(changed[name]["result_ref"], complete[name]["result_ref"])
        self.assertEqual(len(refine_calls), 2)
        self.assertEqual(len(worker.calls), 2)
        self.assertEqual(self.report(third)["payload"]["execution_kind"], "SYNTHETIC_TEST")
        self.assertEqual(third["decision"], "HOLD")

    def test_setup_failure_is_terminal_and_has_an_independent_cli_receipt(self):
        with patch("annotation.recognition.pipeline._implementation",
                side_effect=RuntimeError("controlled synthetic fingerprint setup failure")):
            result = execute(self.source_path, self.context_path, self.review_path, self.workdir,
                evidence_path=self.evidence_path)
        self.assertEqual(result["pipeline_state"], "FAILED")
        self.assertEqual(result["exit_code"], 1)
        self.assertTrue(result["audit_performed"])
        self.assertTrue(result["integrity_accepted"])  # an honestly recorded failure
        self.assertTrue((self.workdir / result["check"]["path"]).is_file())
        evidence_stage = self.stages(result)["evidence"]
        self.assertEqual(evidence_stage["reason"], "STAGE_SETUP_FAILED")
        self.assertIsNone(evidence_stage["origin_attempt_id"])
        with contextlib.closing(sqlite3.connect(self.workdir / "pipeline.sqlite3")) as connection:
            events = [row[0] for row in connection.execute("SELECT event_type FROM stage_events ORDER BY event_id")]
            attempts = connection.execute("SELECT COUNT(*) FROM stage_attempts").fetchone()[0]
        self.assertIn("STAGE_SETUP_FAILED", events)
        self.assertEqual(events[-1], "RUN_FINISHED")
        self.assertEqual(attempts, 0)

    def test_input_change_at_final_boundary_returns_failure_receipt_and_can_resume(self):
        from annotation.recognition import pipeline
        publish = pipeline.batch._put_object
        def publish_then_change_review(workdir, value):
            descriptor = publish(workdir, value)
            if value.get("kind") == "PipelineStageTrial" and value["payload"]["stage_id"] == "quality":
                updated = copy.deepcopy(self.review)
                updated["provenance"] = "Controlled input edit after quality output publication"
                self.write(self.review_path, updated)
            return descriptor
        with patch("annotation.recognition.pipeline.batch._put_object", new=publish_then_change_review):
            result = execute(self.source_path, self.context_path, self.review_path, self.workdir,
                evidence_path=self.evidence_path)
        self.assertEqual(result["pipeline_state"], "FAILED")
        self.assertEqual(result["exit_code"], 1)
        self.assertTrue(result["audit_performed"])
        self.assertFalse(result["integrity_accepted"])
        self.assertTrue(self.report(result)["payload"].get("run_error"))
        self.assertTrue((self.workdir / result["check"]["path"]).is_file())
        self.assertEqual(result["decision"], "HOLD")
        resumed = self.cli()
        self.assertEqual(resumed["pipeline_state"], "READY")
        stages = self.stages(resumed)
        self.assertTrue(stages["evidence"]["cached"])
        self.assertTrue(stages["assemble"]["cached"])
        self.assertFalse(stages["quality"]["cached"])


if __name__ == "__main__":
    unittest.main()
