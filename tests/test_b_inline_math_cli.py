"""Two-stage CLI and model-free replay using generated, synthetic evidence."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tests"), str(ROOT/"tools")]
from annotation.recognition import batch
from annotation.recognition.baseline import digest
from annotation.recognition.inline_formula import collect_inline_formula
from annotation.recognition.inline_ocr import collect_inline_observations
from run_inline_math_b import execute, main, reference
from test_b_inline_formula import FormulaWorker, formula_fixture
from test_b_inline_math import raw_row


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def container(schema, kind, evidence, payload):
    return dict(schema_version=schema, kind=kind, artifact_id="synthetic-container-"+digest(payload)[:24], revision=1,
        book_id=evidence["book_id"], scope_id=evidence["scope_id"], payload=payload, content_hash=digest(payload),
        producer=dict(module="SYNTHETIC_TEST", execution_kind="SYNTHETIC_TEST"), input_refs=[])


class InlineMathCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.f = formula_fixture(self.root/"inputs")
        self.evidence = self.root/"evidence.json"
        self.rows = self.root/"rows.json"
        self.ordinary = self.root/"ordinary.json"
        self.formulas = self.root/"formulas.json"
        self.report = self.root/"formula-report.json"
        write(self.evidence, self.f["evidence"])
        write(self.rows, self.f["line_ids"])
        write(self.ordinary, self.f["layout"]["payload"]["observations_archive"])
        self.work = self.root/"output"
        self.journal = self.root/"formula-journal"
        self.models = self.root/"models"
        self.models.mkdir()

    def kwargs(self):
        return dict(ocr_observations_path=self.ordinary)

    def run_execute(self, **kwargs):
        return execute(self.evidence, self.f["original"], self.f["evidence"]["payload"]["pages"][0]["asset_id"],
            self.rows, self.work, **{**self.kwargs(), **kwargs})

    def base_args(self):
        return ["--evidence", str(self.evidence), "--source", str(self.f["original"]),
            "--asset-id", self.f["evidence"]["payload"]["pages"][0]["asset_id"], "--rows", str(self.rows),
            "--workdir", str(self.work), "--ocr-observations", str(self.ordinary)]

    def replay_args(self):
        return self.base_args()+["--formula-observations", str(self.formulas), "--formula-report", str(self.report),
            "--formula-workdir", str(self.journal)]

    def cached_formula(self):
        obs, report = collect_inline_formula(self.f["evidence"], self.f["layout"], self.f["original"], self.journal,
            line_ids=self.f["line_ids"], recognizer=FormulaWorker())
        write(self.formulas, obs)
        write(self.report, report)
        return obs, report

    def synthetic_collector(self, worker):
        def collect(evidence, layout, source, workdir, *, line_ids, model_dir, max_items):
            return collect_inline_formula(evidence, layout, source, workdir, line_ids=line_ids,
                                          recognizer=worker, max_items=max_items)
        return collect

    def assert_hold(self, result):
        self.assertEqual(result["decision"], "HOLD")
        for name in ("complete", "business_acceptance", "transcription_verified", "graph_modified", "entire_answer_reconstructed", "expected_text_consumed"):
            self.assertFalse(result[name])
        self.assertEqual(result["platform_actions"], [])
        self.assertTrue(result["audit_performed"])

    def object(self, result, name):
        descriptor = result["artifacts"][name] if name != "result" else result["result"]
        return batch._read_object(self.work, descriptor)

    def test_prepare_cached_rows_audits_and_saves_only_immutable_outputs_without_formula_backend(self):
        originals = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with patch("annotation.recognition.inline_formula._local_cpu_backend", side_effect=AssertionError("no formula model")):
            first = self.run_execute(prepare_only=True)
            second = self.run_execute(prepare_only=True)
        self.assertEqual(first, second)
        self.assertEqual(first["execution_state"], "PREPARED")
        self.assertTrue(first["integrity_accepted"])
        self.assertEqual(first["artifacts"]["formula_check"], None)
        self.assertEqual(self.object(first, "math_layout"), self.f["layout"])
        self.assertEqual(self.object(first, "result")["payload"]["artifacts"], first["artifacts"])
        self.assertFalse((self.work/"formula").exists())
        self.assert_hold(first)
        for path, before in originals.items(): self.assertEqual(path.read_bytes(), before)

    def test_explicit_synthetic_ordinary_collection_is_source_bound_and_prepare_only(self):
        calls = []
        def collector(evidence, source, *, asset_id, line_ids):
            def recognize(bgr, **flags):
                calls.append(True)
                return [raw_row("1:3", bgr.shape[1], bgr.shape[0])], [.01, 0, .02]
            return collect_inline_observations(evidence, source, asset_id=asset_id, line_ids=line_ids, recognizer=recognize)
        result = self.run_execute(ocr_observations_path=None, collect_ocr=True, prepare_only=True, ocr_collector=collector)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["execution_kind"]["ocr"], "SYNTHETIC_TEST")
        self.assertEqual(result["execution_state"], "PREPARED")
        self.assert_hold(result)

    def test_formula_partial_resume_and_warm_cache_are_audited_with_the_real_journal(self):
        worker = FormulaWorker()
        kwargs = dict(collect_formula=True, model_dir=self.models, formula_collector=self.synthetic_collector(worker))
        first = self.run_execute(max_items=2, **kwargs)
        self.assertEqual(first["execution_state"], "PARTIAL")
        self.assertEqual(first["exit_code"], 0)
        self.assertTrue(first["integrity_accepted"])
        self.assertEqual(first["counts"]["formula"]["new_attempts"], 2)
        old = {p: p.read_bytes() for p in (self.work/"objects").glob("*.json")}
        final = self.run_execute(**kwargs)
        warm = self.run_execute(**kwargs)
        self.assertEqual(final["execution_state"], "READY")
        self.assertEqual(warm["execution_state"], "READY")
        self.assertEqual(final["artifacts"]["formula_observations"], warm["artifacts"]["formula_observations"])
        self.assertEqual(warm["counts"]["formula"]["new_attempts"], 0)
        self.assertTrue(warm["integrity_accepted"])
        for path, before in old.items(): self.assertEqual(path.read_bytes(), before)
        self.assertTrue((self.work/"formula"/"inline-formula.sqlite3").is_file())
        self.assert_hold(warm)

    def test_read_only_replay_calls_neither_collector_and_keeps_journal_bytes_unchanged(self):
        self.cached_formula()
        before = {p: p.read_bytes() for p in self.journal.rglob("*") if p.is_file()}
        with patch("annotation.recognition.inline_formula.collect_inline_formula", side_effect=AssertionError("not a collector")), \
                patch("annotation.recognition.inline_ocr.collect_inline_observations", side_effect=AssertionError("not a collector")):
            result = self.run_execute(formula_observations_path=self.formulas, formula_report_path=self.report,
                                      formula_workdir=self.journal)
        self.assertEqual(result["mode"], "CACHED_FORMULA_REPLAY")
        self.assertEqual(result["execution_state"], "READY")
        self.assertTrue(result["integrity_accepted"])
        self.assertEqual(self.object(result, "formula_candidates")["payload"]["selected_candidate_refs"], [])
        self.assertEqual(before, {p: p.read_bytes() for p in self.journal.rglob("*") if p.is_file()})
        self.assert_hold(result)

    def test_fresh_cached_replay_forbids_runtime_imports_and_network(self):
        self.cached_formula()
        script = r'''
import importlib.abc,runpy,socket,sys
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'rapidocr_onnxruntime','rapid_latex_ocr','onnxruntime','torch','paddle','requests','httpx','aiohttp'}:
   raise AssertionError('forbidden cached model import '+fullname)
sys.meta_path.insert(0,NoModels())
class OfflineSocket(socket.socket):
 def connect(self,*a,**k):raise AssertionError('network forbidden')
 def connect_ex(self,*a,**k):raise AssertionError('network forbidden')
socket.socket=OfflineSocket
socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network forbidden'))
tool=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(tool,run_name='__main__')
'''
        child = subprocess.run([sys.executable, "-c", script, str(ROOT/"tools/run_inline_math_b.py"), *self.replay_args()],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=45)
        self.assertEqual(child.returncode, 0, child.stdout+child.stderr)
        result = json.loads(child.stdout)
        self.assertEqual(result["execution_state"], "READY")
        self.assertTrue(result["integrity_accepted"])
        self.assert_hold(result)

    def test_scope_and_pipeline_wrapper_unwrap_all_payload_hashes(self):
        e = self.f["evidence"]
        scope = container("b-continuation-scope-trial/0.1", "ContinuationScopeTrial", e, {"evidence": e})
        wrapper = container("b-pipeline-stage-trial/0.1", "PipelineStageTrial", e,
            {"stage_id": "continuation_prepare", "result": scope})
        for value, count in ((scope, 2), (wrapper, 3)):
            write(self.evidence, value)
            result = self.run_execute(prepare_only=True)
            self.assertEqual(len(result["input_receipts"]["evidence"]["unwrapped_layers"]), count)
            self.assertEqual(self.object(result, "evidence"), e)
            self.assertEqual(self.object(result, "evidence_container"), value)
        for layer in ("outer", "scope", "inner"):
            bad = copy.deepcopy(wrapper)
            if layer == "outer": bad["payload"]["extra"] = True
            elif layer == "scope":
                bad["payload"]["result"]["payload"]["extra"] = True
                bad["content_hash"] = digest(bad["payload"])
            else:
                bad["payload"]["result"]["payload"]["evidence"]["payload"]["extra"] = True
                bad["payload"]["result"]["content_hash"] = digest(bad["payload"]["result"]["payload"])
                bad["content_hash"] = digest(bad["payload"])
            write(self.evidence, bad)
            with self.subTest(layer=layer), self.assertRaisesRegex(ValueError, "hash"):
                self.run_execute(prepare_only=True)

    def test_bad_combinations_are_argparse_errors_before_any_execute_or_model(self):
        bad = [[], ["--models", str(self.models)], ["--collect-formula"], ["--max-items", "1"],
            ["--formula-observations", str(self.formulas)], ["--formula-report", str(self.report)],
            ["--prepare-only", "--models", str(self.models)], ["--prepare-only", "--formula-workdir", str(self.journal)],
            ["--prepare-only", "--collect-formula", "--models", str(self.models)],
            ["--collect-formula", "--models", str(self.models), "--max-items", "0"]]
        for flags in bad:
            with self.subTest(flags=flags), patch("run_inline_math_b.execute") as run, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error: main(self.base_args()+flags)
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()
        self.assertFalse(self.work.exists())

    def test_url_unc_and_parent_traversal_paths_are_rejected_before_execute(self):
        for value in ("https://example.invalid/a", "//server/share/a", "\\\\server\\share\\a", "../escaped-input.json"):
            args = self.base_args()+["--prepare-only"]
            args[args.index("--source")+1] = value
            with self.subTest(path=value), patch("run_inline_math_b.execute") as run, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error: main(args)
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()

    def test_wrong_asset_or_row_scope_fails_before_collector_and_model(self):
        for fault in ("asset", "row"):
            write(self.rows, self.f["line_ids"] if fault == "asset" else ["foreign-row"])
            with self.subTest(fault=fault), patch("annotation.recognition.inline_formula._local_cpu_backend") as backend:
                with self.assertRaises(ValueError):
                    execute(self.evidence, self.f["original"], "foreign-asset" if fault == "asset" else "source-page", self.rows,
                        self.work, collect_ocr=True, prepare_only=True, ocr_collector=lambda *a, **k: self.fail("collector called"))
                backend.assert_not_called()
        self.assertFalse(self.work.exists())

    def test_rejected_ordinary_audit_stops_before_formula_collection_and_preserves_real_check(self):
        ordinary = json.loads(self.ordinary.read_text(encoding="utf-8"))
        ordinary["payload"]["rows"][0]["source_line"]["text"] += "not the frozen line"
        write(self.ordinary, ordinary)
        with patch("annotation.recognition.inline_formula.collect_inline_formula", side_effect=AssertionError("no formula call")):
            result = self.run_execute(collect_formula=True, model_dir=self.models)
        self.assertEqual(result["exit_code"], 1)
        self.assertFalse(result["integrity_accepted"])
        self.assertIsNone(result["artifacts"]["math_layout"])
        self.assertIsNone(result["artifacts"]["formula_check"])
        self.assertFalse(self.object(result, "ocr_check")["payload"]["accepted"])
        self.assert_hold(result)

    def test_changed_journal_is_explicit_integrity_failure_during_read_only_replay(self):
        _, report = self.cached_formula()
        attempt = report["payload"]["calls"][0]["origin_attempt_id"]
        with contextlib.closing(sqlite3.connect(self.journal/"inline-formula.sqlite3")) as db:
            db.execute("DELETE FROM events WHERE attempt_id=? AND kind='SUCCEEDED'", (attempt,))
            db.commit()
        result = self.run_execute(formula_observations_path=self.formulas, formula_report_path=self.report,
                                  formula_workdir=self.journal)
        self.assertEqual(result["exit_code"], 1)
        self.assertFalse(result["integrity_accepted"])
        self.assertFalse(self.object(result, "formula_check")["payload"]["accepted"])
        self.assert_hold(result)

    def test_injected_collector_cannot_promote_synthetic_output_to_cpu_provenance(self):
        ordinary = json.loads(self.ordinary.read_text(encoding="utf-8"))
        ordinary["producer"]["execution_kind"] = "CPU_RAPIDOCR_INLINE"
        with self.assertRaisesRegex(ValueError, "SYNTHETIC_TEST"):
            self.run_execute(ocr_observations_path=None, collect_ocr=True, prepare_only=True,
                ocr_collector=lambda *a, **k: ordinary)

    def test_honest_formula_failure_remains_failed_even_when_integrity_is_accepted(self):
        result = self.run_execute(collect_formula=True, model_dir=self.models,
            formula_collector=self.synthetic_collector(FormulaWorker(fail_once=True)))
        self.assertEqual(result["execution_state"], "FAILED")
        self.assertEqual(result["exit_code"], 1)
        self.assertTrue(result["integrity_accepted"])
        self.assertEqual(result["counts"]["formula"]["failed"], 1)
        self.assertTrue(self.object(result, "formula_check")["payload"]["accepted"])
        self.assert_hold(result)

    def test_honest_ordinary_recognition_failure_stops_before_formula_models(self):
        def collector(evidence, source, *, asset_id, line_ids):
            def failed(bgr, **flags): raise RuntimeError("synthetic ordinary recognition failure")
            return collect_inline_observations(evidence, source, asset_id=asset_id, line_ids=line_ids, recognizer=failed)
        result = self.run_execute(ocr_observations_path=None, collect_ocr=True, ocr_collector=collector,
            collect_formula=True, model_dir=self.models,
            formula_collector=lambda *a, **k: self.fail("formula collection must not start"))
        self.assertEqual(result["execution_state"], "FAILED")
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["counts"]["ordinary_recognition_failures"], 2)
        self.assertIsNone(result["artifacts"]["formula_observations"])
        self.assertTrue(self.object(result, "ocr_check")["payload"]["accepted"])
        self.assert_hold(result)

    def test_replay_cannot_write_outputs_into_its_read_only_journal(self):
        self.cached_formula()
        self.work = self.journal/"replay-output"
        with self.assertRaisesRegex(ValueError, "read-only"):
            self.run_execute(formula_observations_path=self.formulas, formula_report_path=self.report,
                              formula_workdir=self.journal)
        self.assertFalse(self.work.exists())

    def test_changed_input_file_during_prepare_is_not_reported_as_success(self):
        observed = json.loads(self.ordinary.read_text(encoding="utf-8"))
        def mutate(evidence, source, *, asset_id, line_ids):
            write(self.rows, ["changed during preparation"])
            return observed
        result = self.run_execute(ocr_observations_path=None, collect_ocr=True, prepare_only=True, ocr_collector=mutate)
        self.assertEqual(result["exit_code"], 1)
        self.assertFalse(result["integrity_accepted"])
        self.assertTrue(any(i["code"] == "INPUT_CHANGED_DURING_EXECUTION" for i in result["issues"]))
        self.assertEqual(self.object(result, "ocr_observations"), observed)
        self.assertEqual(self.object(result, "result")["payload"]["line_ids"], self.f["line_ids"])
        self.assert_hold(result)

    def test_main_reports_data_errors_as_failed_json_without_starting_a_model(self):
        write(self.rows, ["foreign-row"])
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), patch("annotation.recognition.inline_ocr._cpu_backend") as backend:
            code = main(self.base_args()+["--prepare-only"])
        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(result["execution_state"], "FAILED")
        self.assertFalse(result["audit_performed"])
        self.assertFalse(result["integrity_accepted"])
        backend.assert_not_called()


if __name__ == "__main__":
    unittest.main()
