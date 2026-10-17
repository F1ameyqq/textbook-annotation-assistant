"""Explicit draft plan creation, immutable output and live input preservation."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools"), str(ROOT / "tests")]
from prepare_content_revision_b import execute, main
from annotation.recognition import inline_stage
from annotation.recognition.baseline import digest, file_digest
from test_b_inline_stage import make_inline_fixture, write


class ContentPlanPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        data = make_inline_fixture(self.root)
        prepared = inline_stage.prepare_inline_stage(data["evidence"], data["graph"], data["package_path"], data["original"])
        application = inline_stage.apply_inline_stage(prepared)
        self.evidence = data["evidence"]
        self.graph = application["payload"]["graph"]
        self.check = inline_stage.build_inline_quality(prepared, application, data["base_check"])
        answer = next(a for a in self.graph["payload"]["answers"] if any(f.get("role") == "answer" for f in a["fragments"]))
        fragment = next(f for f in answer["fragments"] if f.get("role") == "answer" and not f.get("structural_marker"))
        self.operation = {"operation_id": "synthetic-edit", "kind": "EDIT_TEXT",
            "target": {"answer_id": answer["answer_id"], "fragment_id": fragment["fragment_id"],
                "role": "answer", "fragment_span": [0, 1], "expected_text": fragment["text"][:1]},
            "replacement": "x", "format": "plain", "reason": "SYNTHETIC_TEST explicit character draft"}
        self.paths = [self.root / name for name in ("current-e.json", "current-g.json", "current-c.json", "ops.json")]
        for path, value in zip(self.paths, (self.evidence, self.graph, self.check, [self.operation])):
            write(path, value)
        self.out = self.root / "plans" / "revision1.json"

    def prepare(self, **kwargs):
        return execute(*self.paths, kwargs.pop("out", self.out), author_kind="SYNTHETIC_TEST",
            author_id="fixture-editor", author_note="SYNTHETIC_TEST; no human or model evidence", **kwargs)

    def test_creation_binds_exact_inputs_and_preserves_all_source_bytes(self):
        before = {str(p): file_digest(p) for p in self.paths}
        result = self.prepare()
        plan = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(plan["payload"]["graph_ref"], {k: self.graph[k] for k in ("artifact_id", "revision", "content_hash")})
        self.assertEqual(plan["payload"]["operations"], [self.operation])
        self.assertEqual(result["input_sha256"], dict(zip(("evidence", "graph", "base_check", "operations"), before.values())))
        self.assertEqual(result["sha256"], file_digest(self.out))
        self.assertEqual(plan["content_hash"], digest(plan["payload"]))
        self.assertEqual(before, {str(p): file_digest(p) for p in self.paths})
        self.assertFalse(result["business_acceptance"])

    def test_existing_output_is_refused_without_replacing_old_bytes(self):
        self.prepare()
        original = self.out.read_bytes()
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(self.out.read_bytes(), original)

    def test_input_changed_during_builder_is_refused_before_publication(self):
        from annotation.recognition.content_revision import make_revision_plan
        def changed(*args, **kwargs):
            result = make_revision_plan(*args, **kwargs)
            self.paths[-1].write_bytes(self.paths[-1].read_bytes() + b"\n ")
            return result
        with self.assertRaisesRegex(ValueError, "input changed"):
            self.prepare(builder=changed)
        self.assertFalse(self.out.exists())

    def test_duplicate_json_keys_and_nonfinite_values_are_rejected(self):
        for raw in (b'{"operation_id":"a","operation_id":"b"}', b'[NaN]'):
            with self.subTest(raw=raw):
                self.paths[-1].write_bytes(raw)
                with self.assertRaises(ValueError):
                    self.prepare()
                self.assertFalse(self.out.exists())

    def test_operation_input_is_a_complete_list(self):
        write(self.paths[-1], {"operations": [self.operation]})
        with self.assertRaisesRegex(ValueError, "complete JSON operation list"):
            self.prepare()
        self.assertFalse(self.out.exists())

    def test_empty_second_snapshot_withdraws_edits_and_archives_previous_plan(self):
        self.prepare()
        original = self.out.read_bytes()
        write(self.paths[-1], [])
        second = self.root / "plans" / "revision2.json"
        self.prepare(out=second, previous_path=self.out)
        p = json.loads(second.read_text(encoding="utf-8"))
        self.assertEqual(p["revision"], 2)
        self.assertEqual(p["payload"]["operations"], [])
        self.assertEqual(p["payload"]["previous_plan_archive"], json.loads(original))
        self.assertEqual(self.out.read_bytes(), original)

    def test_cli_reports_refusal_and_keeps_existing_output(self):
        self.prepare()
        original = self.out.read_bytes()
        args = []
        for flag, path in zip(("--evidence", "--graph", "--base-check", "--operations"), self.paths):
            args += [flag, str(path)]
        args += ["--out", str(self.out), "--author-kind", "SYNTHETIC_TEST",
            "--author-id", "fixture-editor", "--author-note", "test"]
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            status = main(args)
        result = json.loads(captured.getvalue())
        self.assertEqual(status, 1)
        self.assertFalse(result["plan_created"])
        self.assertEqual(result["error"]["type"], "FileExistsError")
        self.assertEqual(self.out.read_bytes(), original)

    def test_fresh_cli_has_no_model_or_network_permission(self):
        args = []
        for flag, path in zip(("--evidence", "--graph", "--base-check", "--operations"), self.paths):
            args += [flag, str(path)]
        args += ["--out", str(self.out), "--author-kind", "SYNTHETIC_TEST",
            "--author-id", "fixture-editor", "--author-note", "fresh process SYNTHETIC_TEST"]
        script = """import importlib.abc,runpy,socket,sys
class Guard(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'onnxruntime','rapidocr_onnxruntime','rapid_latex_ocr','torch','paddle'}: raise AssertionError('model imported')
sys.meta_path.insert(0,Guard())
def deny(*a,**kw): raise AssertionError('network used')
socket.socket.connect=socket.socket.connect_ex=socket.create_connection=deny
sys.argv=[sys.argv[1]]+sys.argv[2:]
runpy.run_path(sys.argv[0],run_name='__main__')
"""
        completed = subprocess.run([sys.executable, "-X", "utf8", "-c", script,
            str(ROOT / "tools" / "prepare_content_revision_b.py"), *args],
            capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(result["new_model_calls"], 0)
        self.assertEqual(result["platform_actions"], [])


if __name__ == "__main__":
    unittest.main()
