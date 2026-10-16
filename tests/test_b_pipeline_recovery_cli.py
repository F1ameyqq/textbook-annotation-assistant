"""Recovery CLI contracts on generated pixels and explicit synthetic hypotheses.

No test performs OCR or uses real-book pixels as if they were generated data.
The frozen package is portable and independently bound to a full old payload.
"""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools"), str(ROOT / "tests")]
import test_b_pipeline_cli as common
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.offline import artifact
from run_pipeline_b import execute, main


def ref(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def make_package(directory, source, base):
    """A real pixel crop, but all recognized text is labelled SYNTHETIC_TEST."""
    package_root = directory / "recovery-package"
    package_root.mkdir()
    answer = base["payload"]["pages"][1]
    asset = answer["source"]
    box = [30, 40, 300, 60]
    location = copy.deepcopy(answer["ocr_lines"][0]["location"])
    old_id = answer["ocr_lines"][0]["line_id"]
    crop_path = package_root / "synthetic-answer-crop.png"
    with Image.open(directory / asset["path"]) as source_image:
        source_image.convert("RGB").crop(box).save(crop_path)
    with Image.open(crop_path) as crop:
        pixels = np.array(crop.convert("RGB"))[:, :, ::-1].copy()
    line = dict(line_id="recovery/synthetic-answer/scale1/0", asset_id=asset["asset_id"],
        text="1.解：2+2=4", score=.99, bbox=box[:], polygon=None,
        location=location, base_line_ids=[old_id], verification_status="UNVERIFIED",
        geometry_precision="REVIEWED_CROP_REGION")
    variant = dict(variant_id="scale1", scale=1, contrast=1.0, use_det=False,
        resampling="PIL_LANCZOS", use_cls=False, use_rec=True,
        crop_to_original=[[1, 0, 30], [0, 1, 40], [0, 0, 1]],
        transformed_pixels_sha256=hashlib.sha256(pixels.tobytes()).hexdigest(),
        raw_ocr_result=[[line["text"], .99]], ocr_lines=[line])
    probe = dict(probe_id="synthetic-answer", asset_id=asset["asset_id"],
        source_sha256=asset["sha256"], source_size=[asset["width"], asset["height"]],
        crop_bbox=box[:], crop_path=crop_path.name, crop_sha256=file_digest(crop_path),
        base_line_ids=[old_id], location=location, variants=[variant],
        selected_variant_id="scale1", status="SYNTHETIC_TEST_UNVERIFIED", verification_status="UNVERIFIED",
        selection_rationale="Generated observation for offline recovery tests; no model ran.")
    plan = dict(plan_id="synthetic-answer", action="REPLACE_FOR_ASSEMBLY",
        asset_id=asset["asset_id"], source_sha256=asset["sha256"], location=location,
        base_line_ids=[old_id], replacement_line_ids=[line["line_id"]], selected_probe_ids=[probe["probe_id"]])
    recovery = artifact("b-recovery-trial/0.1", "RecoveryEvidenceTrial", base,
        dict(base_evidence_ref=ref(base), source_ref=dict(artifact_id=source["artifact_id"], content_hash=digest(source)),
            base_raw_line_count=2, base_detail_line_count=1, base_evidence_unchanged=True,
            probes=[probe], supersession_plan=[plan], run_status="COMPLETE"),
        [ref(base)], dict(module=__name__, execution_kind="SYNTHETIC_TEST", reference_quality="SYNTHETIC_TEST",
            device="SYNTHETIC_TEST", engine="injected_test_backend", model_files=[]))
    review_payload = dict(base_evidence_ref=ref(base), recovery_ref=ref(recovery),
        reviewed_exclusions=[], reviewed_primary_anchors=[], reviewed_probe_selections=[],
        regression_additions=[], recovered_answer_checks=[], remaining_source_groups=[], formula_candidates=[],
        triage=[], reference_quality="SYNTHETIC_TEST", platform_actions=[], business_acceptance=False,
        provenance="Generated test evidence; no CPU execution or human acceptance claimed.")
    source_review = artifact("b-source-review-trial/0.1", "SourceRecoveryReviewTrial", base,
        review_payload, [ref(base), ref(recovery)], dict(module=__name__, reference_quality="SYNTHETIC_TEST"))
    documents = {}
    for name, value in (("base_evidence", base), ("recovery", recovery), ("source_review", source_review)):
        path = package_root / (name + ".json")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        documents[name] = dict(path=path.name,
            text_sha256=hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest(),
            artifact_ref=ref(value))
    manifest = dict(schema_version="b-recovery-package-trial/0.1", artifact_id="synthetic-cli-recovery-package",
        book_id=source["book_id"], scope_id=source["scope_id"],
        policy="EXACT_PAYLOAD_EQUIVALENCE_ONLY/0.1", documents=documents)
    path = package_root / "package.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, manifest


class PipelineRecoveryCLI(unittest.TestCase):
    write = common.PipelineCLI.write
    args = common.PipelineCLI.args
    report = common.PipelineCLI.report
    stages = common.PipelineCLI.stages
    stage_result = common.PipelineCLI.stage_result

    def setUp(self):
        common.PipelineCLI.setUp(self)
        answer = self.evidence["payload"]["pages"][1]
        parent = answer["ocr_lines"][0]
        answer["answer_detail_lines"].append(dict(line_id=parent["line_id"] + "/detail/0",
            parent_line_id=parent["line_id"], text=parent["text"], score=.99,
            bbox=parent["bbox"][:], location=copy.deepcopy(parent["location"]),
            crop_to_original=[[1, 0, 0], [0, 1, 0], [0, 0, 1]]))
        self.evidence["content_hash"] = digest(self.evidence["payload"])
        self.write(self.evidence_path, self.evidence)
        self.package_path, self.package = make_package(self.root, self.source, self.evidence)

    def cli(self, *extra, cached=True, recovery=True, expected=0, script=None):
        args = self.args(*extra, cached=cached)
        if recovery:
            args += ["--recovery", str(self.package_path)]
        prefix = [sys.executable, "-c", script] if script else [sys.executable]
        completed = subprocess.run([*prefix, str(ROOT / "tools/run_pipeline_b.py"), *args],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=35)
        self.assertEqual(completed.returncode, expected, completed.stdout + completed.stderr)
        return json.loads(completed.stdout)

    def run_cached(self, **kwargs):
        return execute(self.source_path, self.context_path, self.review_path, self.workdir,
            evidence_path=self.evidence_path, recovery_path=self.package_path, **kwargs)

    def assert_rejected(self, result):
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["pipeline_state"], "FAILED")
        self.assertEqual(result["decision"], "HOLD")
        self.assertFalse(result["business_acceptance"])
        self.assertFalse(result["transcription_verified"])
        self.assertNotEqual(result.get("error", {}).get("stage"), "SETUP_FAILED")

    def test_cached_stop_recover_resume_review_then_ready_preserves_frozen_inputs(self):
        frozen = {path: path.read_bytes() for path in self.package_path.parent.iterdir() if path.is_file()}
        frozen[self.evidence_path] = self.evidence_path.read_bytes()
        frozen[self.review_path] = self.review_path.read_bytes()
        first = self.cli("--stop-after", "recover")
        stages = self.stages(first)
        self.assertEqual(list(stages), ["evidence", "recover", "assemble", "recovery_review", "quality"])
        self.assertEqual(first["pipeline_state"], "PARTIAL")
        self.assertEqual(stages["recover"]["state"], "DONE")
        self.assertEqual(stages["assemble"]["state"], "WAITING")
        evidence = self.stage_result(stages["recover"])
        self.assertEqual(evidence["schema_version"], "b-evidence-trial/0.3")
        self.assertEqual(evidence["payload"]["base_evidence_archive"], self.evidence)
        self.assertEqual(evidence["payload"]["pages"][1]["ocr_lines"][0]["text"], "1.解：2+2=4")
        first_check = (self.workdir / first["check"]["path"]).read_bytes()
        second = self.cli("--stop-after", "recovery_review")
        resumed = self.stages(second)
        self.assertTrue(all(resumed[stage]["cached"] for stage in ("evidence", "recover")))
        self.assertEqual(resumed["recovery_review"]["state"], "DONE")
        self.assertEqual(resumed["quality"]["state"], "WAITING")
        third = self.cli()
        final = self.stages(third)
        self.assertEqual(third["pipeline_state"], "READY")
        self.assertTrue(third["integrity_accepted"])
        self.assertTrue(all(final[name]["cached"] for name in ("evidence", "recover", "assemble", "recovery_review")))
        self.assertEqual(self.stage_result(final["quality"])["payload"]["decision"], "HOLD")
        self.assertFalse(third["business_acceptance"])
        self.assertFalse(third["transcription_verified"])
        self.assertEqual((self.workdir / first["check"]["path"]).read_bytes(), first_check)
        for path, data in frozen.items():
            self.assertEqual(path.read_bytes(), data, path.name)

    def test_review_only_change_invalidates_only_derived_review_and_quality(self):
        first = self.cli()
        before = self.stages(first)
        self.review["provenance"] = "New synthetic review metadata with unchanged review ID"
        self.write(self.review_path, self.review)
        second = self.cli()
        after = self.stages(second)
        self.assertEqual(second["pipeline_state"], "READY")
        for name in ("evidence", "recover", "assemble"):
            self.assertTrue(after[name]["cached"], name)
            self.assertEqual(after[name]["result_ref"], before[name]["result_ref"])
        for name in ("recovery_review", "quality"):
            self.assertFalse(after[name]["cached"], name)
            self.assertNotEqual(after[name]["result_ref"], before[name]["result_ref"])
        self.assertEqual(second["counts"]["cache_hits"], 3)

    def test_exact_full_payload_migrates_new_base_identity_without_changing_package(self):
        frozen = {path: path.read_bytes() for path in self.package_path.parent.iterdir() if path.is_file()}
        current = copy.deepcopy(self.evidence)
        current.update(artifact_id="new-synthetic-runtime-base", revision=2, run_id="new-synthetic-runtime-run")
        current["producer"] = dict(module="test-only-new-runtime", execution_kind="SYNTHETIC_TEST")
        self.write(self.evidence_path, current)
        result = self.cli()
        self.assertEqual(result["pipeline_state"], "READY")
        derived = self.stage_result(self.stages(result)["recover"])
        self.assertEqual(derived["payload"]["base_evidence_archive"], self.evidence)
        self.assertEqual(derived["input_refs"][0], ref(current))
        self.assertEqual(derived["payload"]["base_evidence_archive"]["payload"], self.evidence["payload"])
        self.assertEqual(derived["payload"]["recovery_migration"]["current_base_ref"], ref(current))
        for path, data in frozen.items():
            self.assertEqual(path.read_bytes(), data)

    def test_same_page_hash_with_one_raw_or_detail_field_changed_is_not_equivalent(self):
        for kind in ("raw_text", "raw_score", "detail_score", "payload_note"):
            evidence = copy.deepcopy(self.evidence)
            if kind == "raw_text":
                evidence["payload"]["pages"][0]["ocr_lines"][0]["text"] += "改"
            elif kind == "raw_score":
                evidence["payload"]["pages"][0]["ocr_lines"][0]["score"] = .98
            elif kind == "detail_score":
                evidence["payload"]["pages"][1]["answer_detail_lines"][0]["score"] = .98
            else:
                evidence["payload"]["limitations"].append("changed payload metadata")
            evidence["content_hash"] = digest(evidence["payload"])
            evidence["artifact_id"] = "changed-synthetic-base-" + kind
            self.write(self.evidence_path, evidence)
            self.workdir = self.root / ("reject-" + kind)
            with self.subTest(kind=kind):
                result = self.cli(expected=1)
                self.assert_rejected(result)
                if "report_ref" in result:
                    stages = self.stages(result)
                    self.assertEqual(stages["recover"]["state"], "FAILED")
                    self.assertTrue(result["audit_performed"])
                    self.assertTrue((self.workdir / result["check"]["path"]).is_file())
            self.assertEqual(evidence["payload"]["pages"][0]["source"]["sha256"], self.source["assets"][0]["sha256"])

    def test_already_recovered_evidence_cannot_be_recovered_twice(self):
        first = self.cli("--stop-after", "recover")
        derived = self.stage_result(self.stages(first)["recover"])
        self.write(self.evidence_path, derived)
        result = self.cli(expected=1)
        self.assert_rejected(result)
        self.assertEqual(self.evidence_path.read_text(encoding="utf-8"), json.dumps(derived, ensure_ascii=False, indent=2))

    def test_live_geometry_with_package_waits_before_refinement_and_recovery(self):
        result = self.cli(cached=False)
        stages = self.stages(result)
        self.assertEqual(list(stages), ["recognition", "refine", "recover", "assemble", "recovery_review", "quality"])
        self.assertEqual(result["pipeline_state"], "PARTIAL")
        self.assertTrue(result["integrity_accepted"])
        self.assertEqual(stages["refine"]["reason"], "OCR_REQUIRED")
        self.assertTrue(all(stages[name]["state"] == "WAITING" for name in ("recover", "assemble", "recovery_review", "quality")))

    def test_explicit_synthetic_live_chain_migrates_refined_payload_without_a_model(self):
        from annotation.recognition.pipeline import run_pipeline
        worker = common.SyntheticOCRWorker()
        calls = []
        def refiner(source_path, baseline, context):
            calls.append(ref(baseline))
            result = copy.deepcopy(self.evidence)
            result["artifact_id"] = "new-synthetic-live-refined-base"
            result["input_refs"] = [ref(baseline), dict(artifact_id=context["artifact_id"], content_hash=digest(context))]
            result["producer"] = dict(module=__name__, execution_kind="SYNTHETIC_TEST",
                baseline_producer=copy.deepcopy(baseline["producer"]))
            return result
        def runner(*args, **kwargs):
            return run_pipeline(*args, **kwargs, worker=worker)
        with patch("annotation.recognition.pipeline.refine", new=refiner):
            first = execute(self.source_path, self.context_path, self.review_path, self.workdir,
                use_ocr=True, recovery_path=self.package_path, runner=runner, stop_after="recover")
            self.assertEqual(first["pipeline_state"], "PARTIAL")
            second = execute(self.source_path, self.context_path, self.review_path, self.workdir,
                use_ocr=True, recovery_path=self.package_path, runner=runner)
        stages = self.stages(second)
        self.assertEqual(second["pipeline_state"], "READY")
        self.assertTrue(second["integrity_accepted"])
        self.assertEqual(self.report(second)["payload"]["execution_kind"], "SYNTHETIC_TEST")
        self.assertTrue(all(stages[name]["cached"] for name in ("recognition", "refine", "recover")))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(worker.calls), 2)
        self.assertTrue(self.stage_result(stages["recover"])["payload"]["recovery_migration"]["current_identity_differs"])

    def test_cached_recovery_fresh_process_forbids_model_imports_and_network(self):
        script = r'''
import importlib.abc,runpy,socket,sys
class DenyImports(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'rapidocr_onnxruntime','rapid_latex_ocr','onnxruntime','torch','paddle','requests','httpx','aiohttp'}:
            raise AssertionError('forbidden recovery import: '+fullname)
sys.meta_path.insert(0,DenyImports())
class NoNetworkSocket(socket.socket):
    def connect(self,*a,**k): raise AssertionError('network forbidden')
    def connect_ex(self,*a,**k): raise AssertionError('network forbidden')
socket.socket=NoNetworkSocket
socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden'))
tool=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(tool,run_name='__main__')
'''
        # Change only the runtime identity, so the fresh process actually migrates.
        current = copy.deepcopy(self.evidence)
        current["artifact_id"] = "new-synthetic-cached-runtime"
        self.write(self.evidence_path, current)
        result = self.cli(script=script)
        self.assertEqual(result["pipeline_state"], "READY")
        self.assertTrue(result["integrity_accepted"])
        self.assertEqual(result["decision"], "HOLD")

    def test_package_document_corruption_is_rejected_without_new_ocr(self):
        path = self.package_path.parent / self.package["documents"]["recovery"]["path"]
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        result = self.cli(expected=1)
        self.assert_rejected(result)
        self.assertEqual(path.read_bytes(), original + b" ")

    def test_package_json_document_newlines_are_portable_but_runtime_bytes_remain_bound(self):
        # Git newline conversion changes fileSHA, but not normalized textSHA.
        for document in self.package["documents"].values():
            path = self.package_path.parent / document["path"]
            text = path.read_text(encoding="utf-8")
            path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
            self.assertEqual(hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest(),
                document["text_sha256"])
        result = self.cli()
        self.assertEqual(result["pipeline_state"], "READY")
        self.assertTrue(result["integrity_accepted"])

    def test_same_content_keeps_evidence_graph_check_refs_across_runtime_time_and_git_newlines(self):
        document_paths = {name: self.package_path.parent / descriptor["path"]
            for name, descriptor in self.package["documents"].items()}
        text_paths = [self.package_path, *document_paths.values()]
        # Start with explicit LF bytes on every OS, as in a Git export.
        for path in text_paths:
            path.write_bytes(path.read_text(encoding="utf-8").encode("utf-8"))
        historical = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in document_paths.items()}
        historical_bytes = {name: path.read_bytes() for name, path in document_paths.items()}
        first = self.cli()
        initial_report, initial_stages = self.report(first), self.stages(first)
        first_check = (self.workdir / first["check"]["path"]).read_bytes()
        expected_refs = {name: initial_stages[name]["result_ref"]
            for name in ("recover", "assemble", "quality")}

        # Change only current-base execution time. Its source/content reference
        # and entire payload stay exactly equal to the frozen historical base.
        current = copy.deepcopy(self.evidence)
        current["created_at"] = "2099-01-01T00:00:00+00:00"
        self.assertNotEqual(current["created_at"], self.evidence["created_at"])
        self.assertEqual(ref(current), ref(self.evidence))
        self.assertEqual(current["payload"], self.evidence["payload"])
        self.write(self.evidence_path, current)
        second = self.cli()
        timed_report, timed_stages = self.report(second), self.stages(second)
        self.assertNotEqual(initial_report["payload"]["input_receipts"]["evidence"]["file_sha256"],
            timed_report["payload"]["input_receipts"]["evidence"]["file_sha256"])
        self.assertFalse(timed_stages["evidence"]["cached"])
        self.assertFalse(timed_stages["recover"]["cached"])
        self.assertEqual({name: timed_stages[name]["result_ref"] for name in expected_refs}, expected_refs)
        for name, path in document_paths.items():
            self.assertEqual(path.read_bytes(), historical_bytes[name])

        # The same package's normalized text is unchanged by LF -> CRLF, but
        # the runtime must detect all changed raw bytes and rerun recovery.
        previous_file_shas = {path: file_digest(path) for path in text_paths}
        for path in text_paths:
            path.write_bytes(path.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
            self.assertNotEqual(file_digest(path), previous_file_shas[path])
        from annotation.recognition.pipeline_quality import audit_pipeline
        stale = audit_pipeline(self.source_path, self.context_path, self.review_path, timed_report, self.workdir,
            evidence_path=self.evidence_path, recovery_path=self.package_path)
        self.assertFalse(stale["payload"]["accepted"])
        third = self.cli()
        final_report, final_stages = self.report(third), self.stages(third)
        self.assertTrue(final_stages["evidence"]["cached"])
        self.assertFalse(final_stages["recover"]["cached"])
        self.assertEqual({name: final_stages[name]["result_ref"] for name in expected_refs}, expected_refs)
        before = timed_report["payload"]["input_receipts"]["recovery"]
        after = final_report["payload"]["input_receipts"]["recovery"]
        self.assertNotEqual(before["package"]["file_sha256"], after["package"]["file_sha256"])
        self.assertEqual(before["package"]["text_sha256"], after["package"]["text_sha256"])
        for name in document_paths:
            self.assertNotEqual(before["documents"][name]["file_sha256"], after["documents"][name]["file_sha256"])
            self.assertEqual(before["documents"][name]["text_sha256"], after["documents"][name]["text_sha256"])
            self.assertEqual(json.loads(document_paths[name].read_text(encoding="utf-8")), historical[name])
        self.assertEqual(before["crops"], after["crops"])
        self.assertEqual(before["source_assets"], after["source_assets"])
        recovered = self.stage_result(final_stages["recover"])
        migrated_review = self.stage_result(final_stages["recovery_review"])
        self.assertNotIn("created_at", recovered)
        self.assertNotIn("created_at", migrated_review)
        self.assertEqual(recovered["payload"]["base_evidence_archive"], historical["base_evidence"])
        self.assertEqual(recovered["payload"]["recovery_evidence_archive"], historical["recovery"])
        self.assertEqual(recovered["payload"]["recovery_migration"]["original_source_review_archive"], historical["source_review"])
        content_receipt = recovered["payload"]["recovery_migration"]["package_receipt"]
        self.assertEqual(content_receipt["receipt_policy"], "NORMALIZED_TEXT_CONTENT/0.1")
        self.assertNotIn("file_sha256", content_receipt["package"])
        self.assertTrue(all("file_sha256" not in row for row in content_receipt["documents"].values()))
        self.assertEqual(content_receipt["crops"], after["crops"])
        self.assertEqual(content_receipt["source_assets"], after["source_assets"])
        self.assertEqual((self.workdir / first["check"]["path"]).read_bytes(), first_check)
        self.assertTrue(third["integrity_accepted"])
        self.assertEqual(third["pipeline_state"], "READY")
        self.assertEqual(third["decision"], "HOLD")

    def test_package_changed_after_recover_is_terminal_rejected_and_resume_is_explicit(self):
        from annotation.recognition import pipeline
        publish = pipeline.batch._put_object
        changed = []
        def publish_then_change_package(workdir, value):
            descriptor = publish(workdir, value)
            if value.get("kind") == "PipelineStageTrial" and value["payload"]["stage_id"] == "recover" and not changed:
                # Semantics unchanged: even a byte-only edit must not evade the
                # runtime receipt after it was captured at run start.
                self.package_path.write_bytes(self.package_path.read_bytes() + b" ")
                changed.append(True)
            return descriptor
        with patch("annotation.recognition.pipeline.batch._put_object", new=publish_then_change_package):
            result = self.run_cached()
        self.assertEqual(changed, [True])
        self.assert_rejected(result)
        self.assertTrue(result["audit_performed"])
        self.assertFalse(result["integrity_accepted"])
        self.assertTrue(self.report(result)["payload"]["run_error"])
        self.assertTrue((self.workdir / result["check"]["path"]).is_file())
        with contextlib.closing(sqlite3.connect(self.workdir / "pipeline.sqlite3")) as db:
            last = db.execute("SELECT event_type FROM stage_events ORDER BY event_id DESC LIMIT 1").fetchone()[0]
        self.assertEqual(last, "RUN_FINISHED")
        resumed = self.cli()
        self.assertEqual(resumed["pipeline_state"], "READY")
        self.assertTrue(self.stages(resumed)["evidence"]["cached"])
        self.assertFalse(self.stages(resumed)["recover"]["cached"])

    def test_exported_relative_package_uses_its_own_root_and_no_original_paths(self):
        exported = self.root / "exported"
        exported.mkdir()
        shutil.copytree(self.package_path.parent, exported / self.package_path.parent.name)
        for asset in self.source["assets"]:
            shutil.copy2(self.root / asset["path"], exported / asset["path"])
        for path in (self.source_path, self.context_path, self.review_path, self.evidence_path):
            shutil.copy2(path, exported / path.name)
        self.source_path, self.context_path, self.review_path, self.evidence_path = (
            exported / path.name for path in (self.source_path, self.context_path, self.review_path, self.evidence_path))
        previous_package = self.package_path.parent
        self.package_path = exported / previous_package.name / self.package_path.name
        self.workdir = exported / "new-workdir"
        shutil.rmtree(previous_package)
        result = self.cli()
        self.assertEqual(result["pipeline_state"], "READY")
        self.assertTrue(result["integrity_accepted"])

    def test_recovery_stop_requires_package_and_other_cached_restrictions_still_apply(self):
        cases = [("recover", False, ()), ("recovery_review", False, ()),
            ("refine", True, ()), ("recover", True, ("--ocr",)),
            ("recover", True, ("--max-items", "1"))]
        for stage, package, flags in cases:
            args = self.args("--stop-after", stage, *flags)
            if package:
                args += ["--recovery", str(self.package_path)]
            with self.subTest(stage=stage, package=package, flags=flags), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:
                    main(args)
                self.assertEqual(exc.exception.code, 2)
        self.assertFalse(self.workdir.exists())

    def test_network_recovery_path_is_argparse_error_before_execute(self):
        for path in ("https://example.invalid/package.json", "//server/share/package.json"):
            with self.subTest(path=path), patch("run_pipeline_b.execute") as runner, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:
                    main(self.args("--recovery", path))
                self.assertEqual(exc.exception.code, 2)
                runner.assert_not_called()

    def test_execute_passes_recovery_path_to_both_interfaces_and_keeps_receipt_schema(self):
        seen = []
        report = dict(artifact_id="synthetic-interface-report", revision=1, content_hash="1" * 64,
            run_id="synthetic-interface-run", payload=dict(pipeline_state="PARTIAL", mode="CACHED_INPUT", counts={},
                decision="HOLD", business_acceptance=False, transcription_verified=False, platform_actions=[]))
        check = dict(schema_version="b-pipeline-check-trial/0.1", artifact_id="synthetic-interface-check",
            revision=1, content_hash="2" * 64, payload=dict(accepted=True, issues=[], decision="HOLD",
                business_acceptance=False, transcription_verified=False, platform_actions=[]))
        def runner(*args, **kwargs):
            seen.append(("runner", kwargs))
            return report
        def auditor(*args, **kwargs):
            seen.append(("auditor", kwargs))
            return check
        result = self.run_cached(runner=runner, auditor=auditor, stop_after="recover")
        self.assertEqual([name for name, _ in seen], ["runner", "auditor"])
        self.assertTrue(all(kwargs["recovery_path"] == self.package_path for _, kwargs in seen))
        self.assertEqual(seen[0][1]["stop_after"], "recover")
        self.assertEqual(result["schema_version"], "b-pipeline-cli-result-trial/0.1")
        self.assertTrue((self.workdir / result["check"]["path"]).is_file())


if __name__ == "__main__":
    unittest.main()
