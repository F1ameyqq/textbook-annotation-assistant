"""Spatial drafts use the existing persisted content stages and original bytes."""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools"), str(ROOT / "tests")]
from annotation.recognition.content_revision import make_revision_plan
from annotation.recognition.pipeline_quality import audit_pipeline
from prepare_content_revision_b import execute
from test_b_pipeline_content_revision import make_pipeline_revision_fixture, run_fixture, stage_result, resign_plan
from test_b_inline_stage import write


class RegionPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.d = make_pipeline_revision_fixture(self.root)
        e, g = self.d["current_evidence"], self.d["current_graph"]
        target = self.d["operation"]["target"]
        a = next(a for a in g["payload"]["answers"] if a["answer_id"] == target["answer_id"])
        f = next(f for f in a["fragments"] if f["fragment_id"] == target["fragment_id"])
        page = next(p for p in e["payload"]["pages"] if p["asset_id"] == f["asset_id"])
        bbox = [math.floor(f["bbox"][0]), math.floor(f["bbox"][1]), math.ceil(f["bbox"][2]), math.ceil(f["bbox"][3])]
        self.op = {"operation_id": "synthetic-pixel-rebuild", "kind": "REBUILD_TEXT_REGION",
            "reason": "SYNTHETIC_TEST explicit source-region draft",
            "target": {"answer_id": a["answer_id"], "role": f["role"], "source_fragment_ids": [f["fragment_id"]]},
            "source_region": {"asset_id": f["asset_id"], "source_sha256": page["source"]["sha256"],
                              "source_size": [page["source"]["width"], page["source"]["height"]], "bbox": bbox},
            "blocks": [{"block_id": "synthetic-one-row", "bbox": bbox, "source_fragment_ids": [f["fragment_id"]],
                        "runs": [{"format": "plain", "text": "SYNTHETIC_TEST draft "},
                                 {"format": "latex", "text": r"\frac{x^{2}+1}{2}"}], "note": "No content approval"}]}
        self.plan = make_revision_plan(e, g, self.d["current_check"], [self.op], self.d["author"], previous_plan=self.d["plan"])
        write(self.d["plan_path"], self.plan)

    def run_pipeline(self, **kwargs):
        return run_fixture(self.d, self.d["workdir"], content_revision_path=self.d["plan_path"], **kwargs)

    def audit(self, report):
        checked = audit_pipeline(self.d["source_path"], self.d["context_path"], self.d["review_path"], report,
            self.d["workdir"], evidence_path=self.d["evidence_path"], inline_path=self.d["package_path"],
            inline_source_path=self.d["original"], content_revision_path=self.d["plan_path"])
        self.assertTrue(checked["payload"]["accepted"], checked["payload"]["issues"])

    def test_new_schema_stop_resume_and_warm_cache_keep_current_refs(self):
        stopped = self.run_pipeline(stop_after="content_apply")
        self.audit(stopped)
        self.assertEqual(stopped["payload"]["pipeline_state"], "PARTIAL")
        self.assertIsNone(stopped["payload"]["final_outputs"])
        complete = self.run_pipeline()
        self.audit(complete)
        self.assertEqual(complete["payload"]["pipeline_state"], "READY")
        rows = {s["stage_id"]: s for s in complete["payload"]["stages"]}
        self.assertTrue(rows["content_apply"]["cached"])
        self.assertFalse(rows["content_quality"]["cached"])
        app = stage_result(self.d["workdir"], rows["content_apply"])
        check = stage_result(self.d["workdir"], rows["content_quality"])
        self.assertEqual(app["schema_version"], "b-content-revision-application-trial/0.2")
        self.assertEqual(app["payload"]["graph"]["schema_version"], "b-graph-trial/0.7")
        self.assertEqual(check["schema_version"], "b-check-trial/0.7")
        self.assertEqual(check["payload"]["graph_ref"], complete["payload"]["final_outputs"]["graph_ref"])
        self.assertEqual(check["payload"]["decision"], "HOLD")
        warm = self.run_pipeline()
        self.audit(warm)
        self.assertTrue(all(s["cached"] for s in warm["payload"]["stages"]))
        self.assertEqual(warm["payload"]["final_outputs"], complete["payload"]["final_outputs"])

    def test_empty_snapshot_withdraws_region_without_reusing_its_check(self):
        first = self.run_pipeline()
        self.audit(first)
        empty = make_revision_plan(self.d["current_evidence"], self.d["current_graph"], self.d["current_check"],
            [], self.d["author"], previous_plan=self.plan)
        write(self.d["plan_path"], empty)
        withdrawn = self.run_pipeline()
        self.audit(withdrawn)
        self.assertEqual(empty["schema_version"], "b-content-revision-plan-trial/0.2")
        rows = {s["stage_id"]: s for s in withdrawn["payload"]["stages"]}
        self.assertTrue(all(s["cached"] for s in list(rows.values())[:-2]))
        self.assertFalse(rows["content_apply"]["cached"])
        self.assertFalse(rows["content_quality"]["cached"])
        graph = stage_result(self.d["workdir"], rows["content_apply"])["payload"]["graph"]
        self.assertEqual(graph["payload"]["answers"], self.d["current_graph"]["payload"]["answers"])
        self.assertNotEqual(withdrawn["payload"]["final_outputs"]["quality_ref"], first["payload"]["final_outputs"]["quality_ref"])

    def test_region_in_old_schema_fails_and_does_not_publish_final_outputs(self):
        bad = copy.deepcopy(self.plan)
        bad["schema_version"] = "b-content-revision-plan-trial/0.1"
        write(self.d["plan_path"], resign_plan(bad))
        failed = self.run_pipeline()
        self.audit(failed)
        self.assertEqual(failed["payload"]["pipeline_state"], "FAILED")
        self.assertIsNone(failed["payload"]["final_outputs"])

    def prepare(self, out, **kwargs):
        paths = [self.root / name for name in ("current-e.json", "current-g.json", "current-check.json", "region-ops.json")]
        for path, value in zip(paths, (self.d["current_evidence"], self.d["current_graph"], self.d["current_check"], [self.op])):
            write(path, value)
        return execute(*paths, out, author_kind="SYNTHETIC_TEST", author_id="pixel-fixture",
                       author_note="Synthetic draft, not source transcription", **kwargs)

    def test_prepare_requires_real_source_and_reports_actual_crop(self):
        out = self.root / "pixel-plan.json"
        with self.assertRaisesRegex(ValueError, "requires --source"):
            self.prepare(out)
        self.assertFalse(out.exists())
        result = self.prepare(out, source_paths=[self.d["source_path"]])
        self.assertTrue(result["source_pixel_binding_checked"])
        self.assertEqual(len(result["source_regions"]), 1)
        self.assertEqual(result["source_regions"][0]["source_sha256"], self.op["source_region"]["source_sha256"])
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["schema_version"], "b-content-revision-plan-trial/0.2")

    def test_source_changed_during_plan_builder_is_rejected_before_publication(self):
        source = json.loads(self.d["source_path"].read_text(encoding="utf-8"))
        aid = self.op["source_region"]["asset_id"]
        asset = next(a for a in source["assets"] if a["asset_id"] == aid)
        image = self.d["source_path"].parent / asset["path"]
        def edit(*args, **kwargs):
            result = make_revision_plan(*args, **kwargs)
            image.write_bytes(image.read_bytes() + b"changed during preparation")
            return result
        out = self.root / "rejected-plan.json"
        with self.assertRaisesRegex(ValueError, "original image or manifest changed"):
            self.prepare(out, source_paths=[self.d["source_path"]], builder=edit)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
