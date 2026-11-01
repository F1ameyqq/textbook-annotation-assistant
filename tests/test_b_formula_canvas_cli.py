"""Canvas replay/collection CLI boundaries, using synthetic tensor recognizers.

These tests run no real formula models and use no expected source transcription
as a gold answer. Source pixels/layout are frozen; all newly collected text is
explicit SYNTHETIC_TEST output and remains unverified.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]
from annotation.recognition.formula_backend import collect_formula_observations
from annotation.recognition.baseline import digest
from replay_formula_canvas_b import main, replay


def canvas_observations(layout, crop, *, raw=r"\frac{a^{2}+1}{2}", fail=False, calls=None):
    from annotation.recognition.formula_canvas import collect_canvas_observations
    def recognizer(tensor):
        if calls is not None:
            calls.append((tensor.ndim, tensor.shape[0:2], str(tensor.dtype)))
        if fail: raise RuntimeError("synthetic tensor inference failure")
        return raw, 0.0
    return collect_canvas_observations(layout, crop, recognizer=recognizer)


class FormulaCanvasCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = json.loads((FIXTURE / "formula-layout.json").read_text(encoding="utf-8"))
        cls.source_crop = FIXTURE / "recovery-assets/unit2-q16.png"
        cls.legacy = collect_formula_observations(cls.layout, cls.source_crop,
            recognizer=lambda image: (r"\frac{a^{2}-1}{2}", 0.0))
        cls.observations = canvas_observations(cls.layout, cls.source_crop)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = self.root / "fixture"
        (self.fixture / "recovery-assets").mkdir(parents=True)
        for name in ("source-descriptor.json", "recovery-evidence.json"):
            shutil.copyfile(FIXTURE / name, self.fixture / name)
        self.layout_path = self.fixture / "formula-layout.json"
        self.legacy_path = self.fixture / "formula-observations.json"
        self.obs_path = self.fixture / "formula-canvas-observations.json"
        self.crop = self.fixture / "recovery-assets/unit2-q16.png"
        self.write(self.layout_path, self.layout)
        self.write(self.legacy_path, self.legacy)
        self.write(self.obs_path, self.observations)
        shutil.copyfile(self.source_crop, self.crop)
        self.out = self.root / "new-output"
        self.models = self.root / "local-models"
        self.models.mkdir()

    def write(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def args(self):
        return ["--fixture", str(self.fixture), "--layout", str(self.layout_path), "--crop", str(self.crop),
                "--legacy", str(self.legacy_path), "--observations", str(self.obs_path), "--out", str(self.out)]

    def collect_args(self):
        return ["--fixture", str(self.fixture), "--layout", str(self.layout_path), "--crop", str(self.crop),
                "--legacy", str(self.legacy_path), "--collect", "--models", str(self.models), "--out", str(self.out)]

    def call(self, args=None, expected=0):
        result = subprocess.run([sys.executable, str(ROOT / "tools/replay_formula_canvas_b.py"), *(args or self.args())],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=45)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def summary(self):
        return json.loads((self.out / "summary.json").read_text(encoding="utf-8"))

    def test_cached_custom_paths_write_exact_inputs_and_five_holding_artifacts(self):
        result = self.call()
        summary = json.loads(result.stdout)
        self.assertEqual(set(p.name for p in self.out.iterdir()),
            {"math-layout.json", "canvas-observations.json", "canvas-candidates.json", "canvas-check.json", "summary.json"})
        self.assertEqual(json.loads((self.out / "math-layout.json").read_text(encoding="utf-8")), self.layout)
        self.assertEqual(json.loads((self.out / "canvas-observations.json").read_text(encoding="utf-8")), self.observations)
        self.assertTrue(summary["integrity_accepted"])
        self.assertEqual(summary["replay_mode"], "CACHED_REPLAY")
        self.assertEqual(summary["execution_kind"], "SYNTHETIC_TEST")
        self.assertTrue(summary["upstream"]["legacy_integrity_accepted"])
        self.assertEqual(summary["decision"], "HOLD")
        for key in ("transcription_verified", "business_acceptance", "graph_modified", "entire_answer_reconstructed"):
            self.assertFalse(summary[key])
        self.assertEqual(summary["platform_actions"], [])
        self.assertEqual((summary["paid_model_calls"], summary["website_requests"]), (0, 0))

    def test_default_fixture_uses_frozen_layout_and_new_observation_filename(self):
        self.call(["--fixture", str(self.fixture), "--out", str(self.out)])
        self.assertEqual(json.loads((self.out / "math-layout.json").read_text(encoding="utf-8")), self.layout)
        self.assertEqual(json.loads((self.out / "canvas-observations.json").read_text(encoding="utf-8")), self.observations)

    def test_missing_cache_does_not_fall_back_to_a_model(self):
        self.obs_path.unlink()
        with patch("annotation.recognition.formula_canvas.collect_canvas_observations",
                side_effect=AssertionError("implicit model fallback")) as collector:
            with self.assertRaises(FileNotFoundError): replay(self.fixture)
            collector.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_cached_fresh_process_forbids_models_and_network(self):
        script = r'''
import importlib.abc, runpy, socket, sys
class DenyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'rapid_latex_ocr','rapidocr_onnxruntime','onnxruntime','requests','httpx','aiohttp','torch','paddle'}:
            raise AssertionError('forbidden cached import: '+fullname)
sys.meta_path.insert(0,DenyImports())
class NoNetworkSocket(socket.socket):
    def connect(self,*a,**k):raise AssertionError('network forbidden')
    def connect_ex(self,*a,**k):raise AssertionError('network forbidden')
socket.socket=NoNetworkSocket
socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden'))
tool=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(tool,run_name='__main__')
'''
        result = subprocess.run([sys.executable, "-c", script, str(ROOT / "tools/replay_formula_canvas_b.py"), *self.args()],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["integrity_accepted"])

    def test_explicit_collection_calls_tensor_recognizer_and_stays_synthetic(self):
        calls = []
        def collector(layout, crop, *, model_dir):
            self.assertEqual(Path(model_dir), self.models)
            return canvas_observations(layout, crop, calls=calls)
        def injected(*args, **kwargs): return replay(*args, collector=collector, **kwargs)
        with patch("replay_formula_canvas_b.replay", side_effect=injected), contextlib.redirect_stdout(io.StringIO()):
            result = main(self.collect_args())
        self.assertEqual(result, 0)
        self.assertEqual(len(calls), 22)
        self.assertTrue(all(ndim == 4 and shape == (1, 1) and dtype == "float32" for ndim, shape, dtype in calls))
        self.assertEqual(self.summary()["execution_kind"], "SYNTHETIC_TEST")
        self.assertEqual(self.summary()["replay_mode"], "EXPLICIT_LOCAL_COLLECTION")

    def test_injected_collector_cannot_upgrade_to_cpu(self):
        def collector(*args, **kwargs):
            value = copy.deepcopy(self.observations)
            value["producer"]["execution_kind"] = "CPU_RAPID_LATEX_OCR"
            return value
        with self.assertRaisesRegex(ValueError, "must remain SYNTHETIC_TEST"):
            replay(self.fixture, legacy_path=self.legacy_path, layout_path=self.layout_path,
                crop_path=self.crop, collect=True, model_dir=self.models, collector=collector)

    def test_legacy_integrity_failure_stops_before_new_collection(self):
        bad = copy.deepcopy(self.legacy)
        bad["payload"]["units"][0]["variants"][0]["raw_latex"] = "changed without its receipt"
        self.write(self.legacy_path, bad)
        collector = unittest.mock.Mock(side_effect=AssertionError("collection before legacy audit"))
        with self.assertRaises(ValueError):
            replay(self.fixture, layout_path=self.layout_path, crop_path=self.crop,
                collect=True, model_dir=self.models, collector=collector)
        collector.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_source_crop_damage_stops_before_new_collection(self):
        from PIL import Image
        with Image.open(self.crop) as image: size = image.size
        Image.new("RGB", size, "white").save(self.crop)
        collector = unittest.mock.Mock(side_effect=AssertionError("collection before source audit"))
        with self.assertRaises(ValueError):
            replay(self.fixture, layout_path=self.layout_path, crop_path=self.crop,
                collect=True, model_dir=self.models, collector=collector)
        collector.assert_not_called()

    def test_unknown_latex_is_preserved_without_becoming_verification(self):
        raw = r"\unknown{x}\begin{matrix}1&2\end{matrix}"
        self.write(self.obs_path, canvas_observations(self.layout, self.crop, raw=raw))
        self.call()
        candidate = json.loads((self.out / "canvas-candidates.json").read_text(encoding="utf-8"))
        variants = [v for u in candidate["payload"]["units"] for v in u["variants"]]
        self.assertEqual(len(variants), 22)
        self.assertTrue(all(v["raw_latex"] == raw and not v["parse_result"]["supported"] for v in variants))
        self.assertTrue(self.summary()["integrity_accepted"])
        self.assertFalse(self.summary()["transcription_verified"])

    def test_recorded_model_failure_preserves_artifacts_but_returns_nonzero(self):
        failed = canvas_observations(self.layout, self.crop, fail=True)
        self.write(self.obs_path, failed)
        self.call(expected=1)
        summary = self.summary()
        self.assertEqual(summary["recognition_failures"], 22)
        self.assertEqual(summary["exit_code"], 1)
        saved = json.loads((self.out / "canvas-observations.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, failed)

    def test_independent_rejection_is_saved_and_returns_nonzero(self):
        from annotation.recognition.formula_canvas import build_canvas_candidates
        def falsely_approved(*args):
            candidate = build_canvas_candidates(*args)
            candidate["payload"]["business_acceptance"] = True
            candidate["content_hash"] = digest(candidate["payload"])
            candidate["artifact_id"] = "formula-canvas-candidates-"+digest(
                [candidate["input_refs"], candidate["producer"], candidate["payload"]])[:24]
            return candidate
        with patch("annotation.recognition.formula_canvas.build_canvas_candidates", side_effect=falsely_approved), \
                contextlib.redirect_stdout(io.StringIO()):
            result = main(self.args())
        self.assertEqual(result, 1)
        self.assertFalse(self.summary()["integrity_accepted"])
        self.assertTrue((self.out / "canvas-check.json").is_file())

    def test_existing_output_is_not_overwritten_or_processed(self):
        self.out.mkdir()
        marker = self.out / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        with patch("replay_formula_canvas_b.replay") as runner, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc: main(self.args())
            self.assertEqual(exc.exception.code, 2)
            runner.assert_not_called()
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_incompatible_and_incomplete_modes_are_rejected_before_processing(self):
        cases = [["--collect"], ["--layout", str(self.layout_path)], ["--crop", str(self.crop)],
            ["--models", str(self.models)], ["--collect", "--layout", str(self.layout_path), "--crop", str(self.crop)],
            [*self.args()[:-2], "--collect", "--models", str(self.models)]]
        for args in cases:
            with self.subTest(args=args), patch("replay_formula_canvas_b.replay") as runner, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc: main([*args, "--out", str(self.out)])
                self.assertEqual(exc.exception.code, 2)
                runner.assert_not_called()

    def test_urls_and_network_paths_are_rejected_for_all_local_inputs(self):
        for flag in ("--fixture", "--layout", "--crop", "--observations", "--legacy", "--models", "--out"):
            with self.subTest(flag=flag), patch("replay_formula_canvas_b.replay") as runner, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc: main([flag, "https://example.invalid/input", "--out", str(self.out)])
                self.assertEqual(exc.exception.code, 2)
                runner.assert_not_called()


if __name__ == "__main__": unittest.main()
