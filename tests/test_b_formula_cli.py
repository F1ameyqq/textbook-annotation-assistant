"""Cached formula CLI integrity, with synthetic-only collector observations.

No real formula backend or model is run here. Both successful and failed raw
outputs come from injected SYNTHETIC_TEST recognizers; model truth is not gold.
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
from annotation.recognition.baseline import digest
from annotation.recognition.formula_backend import collect_formula_observations
from replay_math_b import replay as replay_math
from replay_formula_b import main, replay


def synthetic_observations(layout, crop, raw=r"\frac{a^{2}-1}{2}"):
    def recognizer(image):
        return raw, 0.0
    return collect_formula_observations(layout, crop, recognizer=recognizer)


def resign(value):
    value["content_hash"] = digest(value["payload"])
    prefix = "math-layout-" if value["kind"] == "MathLayoutTrial" else "formula-observations-"
    value["artifact_id"] = prefix + digest([value["input_refs"], value["producer"], value["payload"]])[:24]
    return value


class FormulaCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout, check, cls.source_crop = replay_math(FIXTURE)
        assert check["geometry_and_token_coverage_valid"]
        cls.observations = synthetic_observations(cls.layout, cls.source_crop)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.layout_path = self.root / "global-layout.json"
        self.obs_path = self.root / "cached-observations.json"
        self.crop = self.root / "source-crop.png"
        self.out = self.root / "new-output"
        self.models = self.root / "models"
        self.models.mkdir()
        self.write(self.layout_path, self.layout)
        self.write(self.obs_path, self.observations)
        shutil.copyfile(self.source_crop, self.crop)

    def write(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def args(self, *extra):
        return ["--layout", str(self.layout_path), "--crop", str(self.crop),
            "--observations", str(self.obs_path), "--out", str(self.out), *extra]

    def call(self, args=None, expected=0):
        completed = subprocess.run([sys.executable, str(ROOT / "tools/replay_formula_b.py"),
            *(args or self.args())], cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", timeout=30)
        self.assertEqual(completed.returncode, expected, completed.stdout + completed.stderr)
        return completed

    def summary(self):
        return json.loads((self.out / "summary.json").read_text(encoding="utf-8"))

    def test_explicit_saved_layout_cached_replay_writes_five_artifacts(self):
        completed = self.call()
        summary = json.loads(completed.stdout)
        self.assertEqual(set(p.name for p in self.out.iterdir()), {
            "math-layout.json", "formula-observations.json", "formula-candidates.json", "formula-check.json", "summary.json"})
        self.assertEqual(json.loads((self.out / "math-layout.json").read_text(encoding="utf-8")), self.layout)
        self.assertEqual(json.loads((self.out / "formula-observations.json").read_text(encoding="utf-8")), self.observations)
        self.assertEqual(summary["execution_kind"], "SYNTHETIC_TEST")
        self.assertEqual(summary["replay_mode"], "CACHED_REPLAY")
        self.assertTrue(summary["integrity_accepted"])
        self.assertEqual(summary["decision"], "HOLD")
        self.assertFalse(summary["transcription_verified"])
        self.assertFalse(summary["business_acceptance"])
        self.assertFalse(summary["graph_modified"])
        self.assertEqual(summary["paid_model_calls"], 0)
        self.assertEqual(summary["website_requests"], 0)

    def test_default_fixture_rebuild_matches_cached_global_layout(self):
        fixture = self.root / "fixture"
        (fixture / "recovery-assets").mkdir(parents=True)
        for name in ("source-descriptor.json", "recovery-evidence.json"):
            shutil.copyfile(FIXTURE / name, fixture / name)
        recovery = json.loads((FIXTURE / "recovery-evidence.json").read_text(encoding="utf-8"))
        probe = next(p for p in recovery["payload"]["probes"] if p["probe_id"] == "unit2-q16")
        shutil.copyfile(self.source_crop, fixture / probe["crop_path"])
        self.write(fixture / "formula-observations.json", self.observations)
        self.call(["--fixture", str(fixture), "--out", str(self.out)])
        result = json.loads((self.out / "math-layout.json").read_text(encoding="utf-8"))
        self.assertEqual(result["artifact_id"], self.layout["artifact_id"])
        self.assertEqual(result["content_hash"], self.layout["content_hash"])
        self.assertTrue(self.summary()["integrity_accepted"])

    def test_explicit_saved_layout_skips_upstream_rebuild(self):
        with patch("replay_math_b.replay", side_effect=AssertionError("upstream layout must not be rebuilt")):
            _, obs, _, _, summary = replay(self.root / "missing-fixture", observations_path=self.obs_path,
                layout_path=self.layout_path, crop_path=self.crop)
        self.assertEqual(obs, self.observations)
        self.assertTrue(summary["integrity_accepted"])

    def test_default_closed_fixture_reaudits_frozen_layout_without_rebuilding(self):
        fixture = self.root / "closed-fixture"
        (fixture / "recovery-assets").mkdir(parents=True)
        for name in ("source-descriptor.json", "recovery-evidence.json"):
            shutil.copyfile(FIXTURE / name, fixture / name)
        shutil.copyfile(self.source_crop, fixture / "recovery-assets/unit2-q16.png")
        self.write(fixture / "formula-layout.json", self.layout)
        self.write(fixture / "formula-observations.json", self.observations)
        with patch("replay_math_b.replay", side_effect=AssertionError("closed input must not be rebuilt")):
            layout, observations, _, check, summary = replay(fixture)
        self.assertEqual(layout, self.layout)
        self.assertEqual(observations, self.observations)
        self.assertTrue(check["payload"]["accepted"])
        self.assertTrue(summary["integrity_accepted"])

    def test_fresh_cached_process_forbids_model_imports_and_network(self):
        script = r'''
import importlib.abc, runpy, socket, sys
class DenyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'rapid_latex_ocr','rapidocr_onnxruntime','onnxruntime','requests','httpx','aiohttp','torch','paddle'}:
            raise AssertionError('forbidden cached import: '+fullname)
sys.meta_path.insert(0,DenyImports())
class NoNetworkSocket(socket.socket):
    def connect(self,*args,**kwargs): raise AssertionError('network connect forbidden')
    def connect_ex(self,*args,**kwargs): raise AssertionError('network connect_ex forbidden')
socket.socket=NoNetworkSocket
socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden'))
tool=sys.argv[1]
sys.argv=sys.argv[1:]
runpy.run_path(tool,run_name='__main__')
'''
        completed = subprocess.run([sys.executable, "-c", script, str(ROOT / "tools/replay_formula_b.py"),
            *self.args()], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["integrity_accepted"])

    def test_unknown_syntax_preserves_every_raw_variant(self):
        raw = r"\unknown{x}\begin{matrix}1&2\end{matrix}"
        observations = synthetic_observations(self.layout, self.source_crop, raw)
        self.write(self.obs_path, observations)
        self.call()
        candidates = json.loads((self.out / "formula-candidates.json").read_text(encoding="utf-8"))
        variants = [v for u in candidates["payload"]["units"] for v in u["variants"]]
        self.assertTrue(variants)
        self.assertTrue(all(v["raw_latex"] == raw and not v["parse_result"]["supported"] for v in variants))
        self.assertTrue(all(v["parse_result"]["raw_latex"] == raw for v in variants))
        self.assertEqual(self.summary()["unparsed_variant_count"], len(variants))
        self.assertTrue(self.summary()["integrity_accepted"])
        self.assertEqual(self.summary()["decision"], "HOLD")

    def test_recorded_recognition_errors_are_saved_and_return_nonzero(self):
        def failed_recognizer(image):
            raise RuntimeError("synthetic recognition failure")
        observations = collect_formula_observations(self.layout, self.source_crop, recognizer=failed_recognizer)
        self.write(self.obs_path, observations)
        self.call(expected=1)
        summary = self.summary()
        self.assertTrue(summary["integrity_accepted"])
        self.assertGreater(summary["recognition_failures"], 0)
        self.assertEqual(summary["exit_code"], 1)
        saved = json.loads((self.out / "formula-observations.json").read_text(encoding="utf-8"))
        self.assertTrue(all(v["raw_latex"] is None and v["recognition_error"] is not None
            for u in saved["payload"]["units"] for v in u["variants"]))

    def test_self_rehashed_cached_transform_change_is_rejected(self):
        observations = copy.deepcopy(self.observations)
        variant = observations["payload"]["units"][0]["variants"][0]
        variant["transformed_rgb_sha256"] = "0" * 64
        variant["transformed_to_source"][0][2] += 1
        self.write(self.obs_path, resign(observations))
        completed = self.call(expected=1)
        self.assertIn("preprocessing pixels changed", completed.stderr)
        self.assertFalse(self.out.exists())

    def test_self_rehashed_cached_source_hash_change_is_rejected(self):
        observations = copy.deepcopy(self.observations)
        observations["payload"]["source"]["source_sha256"] = "0" * 64
        self.write(self.obs_path, resign(observations))
        self.call(expected=1)
        self.assertFalse(self.out.exists())

    def test_coordinated_layout_observation_source_hash_cannot_bypass_original_asset_ref(self):
        layout = copy.deepcopy(self.layout)
        layout["payload"]["source_sha256"] = "0" * 64
        resign(layout)
        # Recreate every dependent unit/ref consistently, retaining the original
        # layout asset input as the independent source identity witness.
        observations = synthetic_observations(layout, self.crop)
        self.write(self.layout_path, layout)
        self.write(self.obs_path, observations)
        self.call(expected=1)
        check = json.loads((self.out / "formula-check.json").read_text(encoding="utf-8"))
        self.assertFalse(check["payload"]["accepted"])
        self.assertIn("FORMULA_LAYOUT_SOURCE_REFERENCE_MISMATCH", [i["code"] for i in check["payload"]["issues"]])
        self.assertEqual(self.summary()["exit_code"], 1)

    def test_existing_output_is_refused_before_processing_and_not_overwritten(self):
        self.out.mkdir()
        marker = self.out / "existing.txt"
        marker.write_text("preserve me", encoding="utf-8")
        with patch("replay_formula_b.replay") as worker, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main(self.args())
            self.assertEqual(cm.exception.code, 2)
            worker.assert_not_called()
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve me")

    def test_saved_layout_and_crop_must_be_supplied_together(self):
        for flag, path in (("--layout", self.layout_path), ("--crop", self.crop)):
            with self.subTest(flag=flag), patch("replay_formula_b.replay") as worker, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    main([flag, str(path), "--out", str(self.out)])
                self.assertEqual(cm.exception.code, 2)
                worker.assert_not_called()

    def test_collect_requires_all_explicit_local_inputs(self):
        combinations = ([], ["--layout", str(self.layout_path), "--crop", str(self.crop)],
            ["--models", str(self.models)])
        for inputs in combinations:
            with self.subTest(inputs=inputs), patch("replay_formula_b.replay") as worker, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    main(["--collect", *inputs, "--out", str(self.out)])
                self.assertEqual(cm.exception.code, 2)
                worker.assert_not_called()

    def test_collect_and_cached_observations_are_mutually_exclusive(self):
        with patch("replay_formula_b.replay") as worker, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main([*self.args(), "--collect", "--models", str(self.models)])
            self.assertEqual(cm.exception.code, 2)
            worker.assert_not_called()

    def test_models_cannot_silently_enable_collection(self):
        with patch("replay_formula_b.replay") as worker, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main([*self.args(), "--models", str(self.models)])
            self.assertEqual(cm.exception.code, 2)
            worker.assert_not_called()

    def test_injected_collect_uses_same_interpreter_and_stays_synthetic(self):
        calls = []
        def collector(layout, crop, *, model_dir):
            calls.append((sys.executable, Path(model_dir)))
            return synthetic_observations(layout, crop)
        def injected_replay(*args, **kwargs):
            return replay(*args, collector=collector, **kwargs)
        with patch("replay_formula_b.replay", side_effect=injected_replay), contextlib.redirect_stdout(io.StringIO()):
            result = main(["--collect", "--layout", str(self.layout_path), "--crop", str(self.crop),
                "--models", str(self.models), "--out", str(self.out)])
        self.assertEqual(result, 0)
        self.assertEqual(calls, [(sys.executable, self.models)])
        self.assertEqual(self.summary()["replay_mode"], "EXPLICIT_LOCAL_COLLECTION")
        self.assertEqual(self.summary()["execution_kind"], "SYNTHETIC_TEST")

    def test_injected_collector_cannot_masquerade_as_actual_cpu(self):
        def collector(layout, crop, *, model_dir):
            result = synthetic_observations(layout, crop)
            result["producer"]["execution_kind"] = "CPU_RAPID_LATEX_OCR"
            return result
        with self.assertRaisesRegex(ValueError, "must remain SYNTHETIC_TEST"):
            replay(layout_path=self.layout_path, crop_path=self.crop, collect=True,
                model_dir=self.models, collector=collector)

    def test_network_path_is_rejected_before_any_collector_or_runtime(self):
        for value in ("https://example.invalid/cache.json", "file:///tmp/cache.json", "//server/share/cache.json"):
            with self.subTest(value=value), patch("replay_formula_b.replay") as worker, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    main(["--observations", value, "--out", str(self.out)])
                self.assertEqual(cm.exception.code, 2)
                worker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
