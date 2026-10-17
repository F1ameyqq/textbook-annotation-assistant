"""Independent local-review behavior on generated source pixels and draft text.

All observations come from explicit test recognizers.  MODEL_DRAFT labels an
editor, never a model execution receipt, human gold or approved transcription.
"""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from annotation.recognition import content_revision as revision
from annotation.recognition import content_revision_quality as quality
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.content_review import ReviewWorkspace, ReviewConflict, SourceChanged
from content_revision_fixture import make_content_fixture, edit_target
from test_content_region import region_operation


AUTHOR = {"kind": "MODEL_DRAFT", "id": "portable-review-editor",
          "note": "Generated pixels and synthetic observations; explicit unverified draft"}


def answer(graph, number):
    return next(a for a in graph["payload"]["answers"] if a["printed_number"] == number)


def manifest_for(data, directory):
    """A new portable manifest for every actual generated E page, not fake SHA."""
    root = Path(directory)
    assets = []
    images = [p for p in root.rglob("*.png") if p.is_file()]
    for i, page in enumerate(data["evidence"]["payload"]["pages"]):
        source = page["source"]
        matches = [p for p in images if file_digest(p) == source["sha256"]]
        if not matches:
            raise AssertionError("fixture original PNG is missing: " + page["asset_id"])
        assets.append({**copy.deepcopy(source), "asset_id": page["asset_id"],
                       "path": matches[0].relative_to(root).as_posix(), "reading_order": i})
    manifest = {"schema_version": "b-source-trial/0.1", "artifact_id": "generated-review-source",
                "book_id": data["evidence"]["book_id"], "scope_id": "verified-originals-for-review",
                "assets": assets}
    path = root / "workspace-source.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path


def make_non_bmp_fixture(directory):
    """A fresh synthetic source version with non-BMP original fragment offsets."""
    from annotation.recognition import offline, inline_stage
    from annotation.recognition.inline_ocr import collect_inline_observations
    from annotation.recognition.inline_math import build_inline_math_layout
    from annotation.recognition.inline_formula import collect_inline_formula
    from test_b_inline_formula import FormulaWorker
    from test_b_inline_math import raw_row
    from test_b_inline_stage import refresh_inline_package

    data = make_content_fixture(directory)
    evidence = copy.deepcopy(data["evidence"])
    page = next(p for p in evidence["payload"]["pages"] if p["asset_id"] == "answer")
    next(l for l in page["ocr_lines"] if l["line_id"] == "answer/ocr/2")["text"] = "9.解：𝑥+𝛼="
    evidence["artifact_id"] = "generated-review-nonbmp-evidence"
    evidence["content_hash"] = digest(evidence["payload"])
    ids = ["answer/ocr/2", "answer/ocr/3"]

    def ordinary(bgr, **flags):
        return [raw_row("x+y=", bgr.shape[1], bgr.shape[0])], [.01, 0, .02]

    observed = collect_inline_observations(evidence, data["original"], asset_id="answer", line_ids=ids, recognizer=ordinary)
    layout = build_inline_math_layout(evidence, observed, data["original"], line_ids=ids)
    journal = Path(directory) / "nonbmp-formula"
    formulas, report = collect_inline_formula(evidence, layout, data["original"], journal,
        line_ids=ids, recognizer=FormulaWorker(outputs=(r"\sqrt{4}",)))
    documents = dict(evidence=evidence, rows=ids, ocr_observations=observed,
                     formula_observations=formulas, formula_report=report)
    manifest = copy.deepcopy(data["manifest"])
    manifest["artifact_id"] = "generated-review-nonbmp-inline"
    manifest["journal_dir"] = journal.name
    package = {"documents": documents, "manifest": manifest,
               "package_path": Path(directory) / "nonbmp-package.json", "journal_dir": journal}
    refresh_inline_package(package)
    base = offline.assemble(evidence)
    checked = offline.quality_check(evidence, base, data["review"])
    prepared = inline_stage.prepare_inline_stage(evidence, base, package["package_path"], data["original"])
    application = inline_stage.apply_inline_stage(prepared)
    data.update(evidence=evidence, graph=application["payload"]["graph"],
                check=inline_stage.build_inline_quality(prepared, application, checked))
    return data


class ContentReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = make_content_fixture(self.root / "inputs")
        self.source = manifest_for(self.data, self.root / "inputs")
        self.initial = revision.make_revision_plan(self.data["evidence"], self.data["graph"], self.data["check"], [], AUTHOR)
        self.workdir = self.root / "review-workspace"

    def open(self, *, data=None, initial=None, workdir=None, sources=None, hook=None):
        d = data or self.data
        return ReviewWorkspace(d["evidence"], d["graph"], d["check"], d["review"],
            initial if initial is not None else self.initial, workdir or self.workdir,
            sources if sources is not None else [self.source], before_commit=hook)

    def state_answer(self, state, number="9"):
        return next(a for a in state["answers"] if a["printed_number"] == number)

    def block(self, state, number="9", *, role="answer", kind="FRAGMENT"):
        return next(b for b in self.state_answer(state, number)["blocks"] if b["role"] == role and b["kind"] == kind)

    def request(self, state, change, number="9", *, author=None):
        return {"expected_head": state["head"], "answer_id": self.state_answer(state, number)["answer_id"],
                "changes": [change], "author": author or copy.deepcopy(AUTHOR)}

    def text_request(self, state, text, number="9", *, role="answer"):
        return self.request(state, {"key": self.block(state, number, role=role)["key"], "text": text, "format": "plain"}, number)

    def assert_unverified(self, value):
        self.assertEqual(value["decision"], "HOLD")
        for key in ("complete", "transcription_verified", "business_acceptance"):
            self.assertIs(value[key], False)
        self.assertEqual(value["platform_actions"], [])

    def assert_audited(self, workspace):
        docs = workspace.documents()
        self.assertEqual(set(docs), {"plan", "application", "graph", "check", "application_audit", "quality_audit"})
        d = self.data
        self.assertEqual(docs["application"], revision.apply_content_revision(d["evidence"], d["graph"], d["check"], docs["plan"]))
        self.assertTrue(quality.audit_content_application(d["evidence"], d["graph"], d["check"], docs["plan"], docs["application"])["payload"]["accepted"])
        self.assertTrue(quality.audit_content_quality(d["evidence"], d["graph"], d["check"], docs["plan"], docs["application"], d["review"], docs["check"])["payload"]["accepted"])
        for key in ("application_audit", "quality_audit"):
            self.assertTrue(docs[key]["payload"]["accepted"])
            self.assert_unverified(docs[key]["payload"])
        self.assertEqual(docs["graph"]["payload"]["answer_coverage"], d["graph"]["payload"]["answer_coverage"])
        self.assertEqual(docs["graph"]["payload"]["inline_content"], d["graph"]["payload"]["inline_content"])
        for old, current in zip(d["graph"]["payload"]["answers"], docs["graph"]["payload"]["answers"]):
            for key in ("fragments", "source_line_ids", "evidence_refs"):
                self.assertEqual(old[key], current[key])
            self.assertEqual([r for r in old.get("render_regions", []) if r.get("content_type") == "image"],
                             [r for r in current.get("render_regions", []) if r.get("content_type") == "image"])
        self.assert_unverified(docs["check"]["payload"])
        return docs

    def object_bytes(self):
        return {p.relative_to(self.workdir).as_posix(): p.read_bytes() for p in (self.workdir / "objects").rglob("*") if p.is_file()}

    def test_generated_source_state_has_scoped_blocks_issues_and_no_approval_or_paths(self):
        w = self.open(); state = w.state(); docs = self.assert_audited(w)
        self.assertEqual(state["schema_version"], "b-content-review-state-trial/0.1")
        self.assertEqual(state["author"], AUTHOR); self.assertEqual(state["plan_ref"], revision.reference(docs["plan"]))
        self.assert_unverified(state)
        self.assertEqual({a["asset_id"] for a in state["assets"]}, {"question", "answer"})
        self.assertNotIn(str(self.root), json.dumps(state, ensure_ascii=False))
        self.assertEqual(self.block(state)["source_text"], "解：AB=")
        issues = {i["issue_id"] for i in state["issues"]}
        for a in state["answers"]:
            self.assertTrue(set(a["issue_ids"]) <= issues)
            self.assertTrue(all(b["kind"] in {"FRAGMENT", "REGION"} for b in a["blocks"]))
        q4 = self.state_answer(state, "4")
        self.assertTrue(q4["question_candidates"])
        self.assertTrue(any(i["scope_id"] in {q4["answer_id"], q4["question_candidates"][0]["question_id"]}
                            for i in state["issues"] if i["issue_id"] in q4["issue_ids"]))

    def test_full_original_fragment_edit_preserves_other_operations_and_current_scalar_rules(self):
        q9 = answer(self.data["graph"], "9")
        op = {"operation_id": "keep-q9-analysis", "kind": "EDIT_TEXT", "target": edit_target(self.data["graph"], answer_id=q9["answer_id"], role="explanation"),
              "replacement": "既有解析草稿", "format": "plain", "reason": "Preserve another operation verbatim"}
        self.initial = revision.make_revision_plan(self.data["evidence"], self.data["graph"], self.data["check"], [op], AUTHOR)
        w = self.open(); old = w.state()
        self.assertTrue(any(f["code"] == "ANSWER_VALUE_MISMATCH" for f in w.documents()["check"]["payload"]["fresh_question_findings"]))
        new = w.save(self.text_request(old, "13", "4")); docs = self.assert_audited(w)
        self.assertNotEqual(new["head"], old["head"]); self.assertEqual(new["plan_revision"], old["plan_revision"] + 1)
        self.assertEqual(self.state_answer(new, "4")["text"], "13")
        self.assertIn(op, docs["plan"]["payload"]["operations"])
        edited = next(o for o in docs["plan"]["payload"]["operations"] if o["target"]["answer_id"] == self.state_answer(new, "4")["answer_id"])
        self.assertEqual(edited["target"]["expected_text"], "0"); self.assertEqual(edited["target"]["fragment_span"], [0, 1])
        self.assertEqual(docs["plan"]["payload"]["previous_plan_archive"], self.initial)
        self.assertEqual(docs["graph"]["payload"]["content_revision"]["source_layer_proof"]["equal"], True)
        self.assertFalse(any(f["code"].startswith("ANSWER_SCALAR") or f["code"] == "ANSWER_VALUE_MISMATCH"
                             for f in docs["check"]["payload"]["fresh_question_findings"]))

    def test_unchanged_plain_editor_adds_no_version_and_other_save_preserves_mixed_operations(self):
        target = edit_target(self.data["graph"], answer_id=answer(self.data["graph"], "9")["answer_id"], span=[2, 4])
        op = {"operation_id": "existing-latex", "kind": "EDIT_TEXT", "target": target, "replacement": "𝑥^{2}", "format": "latex", "reason": "Existing mixed piece draft"}
        self.initial = revision.make_revision_plan(self.data["evidence"], self.data["graph"], self.data["check"], [op], AUTHOR)
        w = self.open(); old = w.state(); block = self.block(old, "4")
        saved = w.save(self.request(old, {"key": block["key"], "text": block["text"], "format": "plain"}, "4"))
        self.assertEqual(saved["head"], old["head"]); self.assertEqual(len(saved["history"]), len(old["history"]))
        self.assertEqual(w.documents()["plan"], self.initial)
        edited = w.save(self.text_request(old, "13", "4"))
        self.assertIn(op, w.documents()["plan"]["payload"]["operations"])
        self.assertEqual(self.block(edited)["runs"], self.block(old)["runs"])

    def test_explicit_format_switch_is_a_new_draft_even_with_identical_text(self):
        w = self.open(); old = w.state(); block = self.block(old, "4")
        request = self.request(old, {"key": block["key"], "text": block["text"], "format": "latex"}, "4")
        new = w.save(request); docs = self.assert_audited(w)
        self.assertNotEqual(new["head"], old["head"])
        op = docs["plan"]["payload"]["operations"][0]
        self.assertEqual(op["replacement"], block["text"]); self.assertEqual(op["format"], "latex")
        self.assertEqual(w.save(self.request(new, {"key": block["key"], "text": block["text"], "format": "latex"}, "4"))["head"], new["head"])

    def test_region_run_edit_preserves_geometry_other_blocks_and_plain_latex_order(self):
        op = region_operation(self.data["evidence"], self.data["graph"])
        self.initial = revision.make_revision_plan(self.data["evidence"], self.data["graph"], self.data["check"], [op], AUTHOR)
        w = self.open(); old = w.state(); blocks = self.state_answer(old)["blocks"]; first = self.block(old, kind="REGION")
        runs = [{"format": "plain", "text": "解：新草稿 "}, {"format": "latex", "text": r"\frac{a^{4}+1}{4}"}, {"format": "plain", "text": "，待核对"}]
        new = w.save(self.request(old, {"key": first["key"], "runs": runs})); docs = self.assert_audited(w)
        changed = next(b for b in self.state_answer(new)["blocks"] if b["key"] == first["key"])
        self.assertEqual(changed["runs"], runs); self.assertEqual(changed["text"], "".join(r["text"] for r in runs))
        for key in ("key", "kind", "role", "asset_id", "bbox", "source_fragment_ids", "source_text"):
            self.assertEqual(changed[key], first[key])
        for before in blocks:
            if before["key"] != first["key"]:
                self.assertEqual(before, next(b for b in self.state_answer(new)["blocks"] if b["key"] == before["key"]))
        current_op = docs["plan"]["payload"]["operations"][0]
        self.assertEqual(current_op["target"], op["target"]); self.assertEqual(current_op["source_region"], op["source_region"])
        self.assertEqual(docs["graph"]["schema_version"], "b-graph-trial/0.7")

    def test_candidate_selection_uses_original_unicode_codepoint_span_not_active_text(self):
        self.data = make_non_bmp_fixture(self.root / "nonbmp")
        self.source = manifest_for(self.data, self.root / "nonbmp")
        self.initial = revision.make_revision_plan(self.data["evidence"], self.data["graph"], self.data["check"], [], AUTHOR)
        w = self.open(); old = w.state(); block = self.block(old); candidate = block["candidates"][0]
        self.assertEqual(block["source_text"], "解：𝑥+𝛼=")
        change = {"key": block["key"], **{k: candidate[k] for k in ("candidate_id", "call_id", "unit_id")}, "fragment_span": [4, 5]}
        new = w.save(self.request(old, change)); docs = self.assert_audited(w)
        self.assertEqual(self.state_answer(new)["text"], "解：𝑥+" + candidate["raw_latex"] + "=\n25")
        operation = docs["plan"]["payload"]["operations"][0]
        self.assertEqual(operation["target"]["expected_text"], "𝛼"); self.assertEqual(operation["target"]["fragment_span"], [4, 5])
        self.assertEqual(operation["kind"], "SELECT_INLINE")
        invalid = copy.deepcopy(change); invalid["fragment_span"] = [5, 7]
        with self.assertRaises(ValueError): w.save(self.request(new, invalid))
        self.assertEqual(w.state()["head"], new["head"])
        replacement = "显式替换整个当前编辑框"
        latest = w.save(self.text_request(new, replacement)); docs = self.assert_audited(w)
        self.assertEqual(self.state_answer(latest)["text"], replacement + "\n25")
        self.assertEqual(len(docs["plan"]["payload"]["operations"]), 1)
        original_target = docs["plan"]["payload"]["operations"][0]["target"]
        self.assertEqual(original_target["fragment_span"], [0, 6]); self.assertEqual(original_target["expected_text"], "解：𝑥+𝛼=")

    def test_cross_answer_candidate_or_partial_edit_overlap_rejected_without_losing_head(self):
        w = self.open(); old = w.state(); block = self.block(old); candidate = block["candidates"][0]
        foreign = {"key": self.block(old, "4")["key"], **{k: candidate[k] for k in ("candidate_id", "call_id", "unit_id")}, "fragment_span": [0, 1]}
        with self.assertRaises(ValueError): w.save(self.request(old, foreign, "4"))
        self.assertEqual(w.state()["head"], old["head"])
        op = {"operation_id": "partial-prior-edit", "kind": "EDIT_TEXT", "target": edit_target(self.data["graph"], answer_id=self.state_answer(old)["answer_id"], span=[1, 4]),
              "replacement": "长旧编辑", "format": "plain", "reason": "Prior interval may not be partially discarded"}
        self.initial = revision.make_revision_plan(self.data["evidence"], self.data["graph"], self.data["check"], [op], AUTHOR)
        w = self.open(workdir=self.root / "partial-overlap"); old = w.state(); block = self.block(old)
        bad = {"key": block["key"], **{k: candidate[k] for k in ("candidate_id", "call_id", "unit_id")}, "fragment_span": [2, 5]}
        with self.assertRaises(ValueError): w.save(self.request(old, bad))
        self.assertEqual(w.state()["head"], old["head"])

    def test_stale_tab_cannot_overwrite_committed_head_or_other_answer_edit(self):
        first = self.open(); second = self.open(); old = first.state()
        current = first.save(self.text_request(old, "13", "4"))
        with self.assertRaises(ReviewConflict): second.save(self.text_request(old, "stale replacement"))
        self.assertEqual(self.open().state()["head"], current["head"])
        self.assertEqual(self.state_answer(second.state(), "4")["text"], "13")
        self.assertEqual(len(second.state()["history"]), len(current["history"]))

    def test_restore_appends_new_version_archives_current_and_keeps_all_history_documents(self):
        w = self.open(); initial = w.state(); original = w.documents(initial["head"])
        first = w.save(self.text_request(initial, "13", "4")); first_docs = w.documents()
        second = w.save(self.text_request(first, "另一个草稿")); second_docs = w.documents()
        restored = w.restore({"expected_head": second["head"], "revision_head": first["head"], "author": AUTHOR})
        docs = self.assert_audited(w)
        self.assertNotIn(restored["head"], {initial["head"], first["head"], second["head"]})
        self.assertEqual(restored["plan_revision"], second["plan_revision"] + 1)
        self.assertEqual(docs["plan"]["payload"]["operations"], first_docs["plan"]["payload"]["operations"])
        self.assertEqual(docs["plan"]["payload"]["previous_plan_archive"], second_docs["plan"])
        self.assertEqual(w.documents(initial["head"]), original); self.assertEqual(w.documents(first["head"]), first_docs)
        self.assertEqual(len(restored["history"]), 4)
        with self.assertRaises(ReviewConflict): w.restore({"expected_head": second["head"], "revision_head": initial["head"], "author": AUTHOR})
        with self.assertRaises(ValueError): w.restore({"expected_head": restored["head"], "revision_head": "not-in-this-workspace", "author": AUTHOR})
        self.assertEqual(w.state()["head"], restored["head"])

    def test_restart_uses_exact_immutable_inputs_and_allows_relocated_identical_sources(self):
        w = self.open(); old = w.state(); new = w.save(self.text_request(old, "13", "4")); frozen = w.documents()
        restarted = self.open(); self.assertEqual(restarted.state()["head"], new["head"]); self.assertEqual(restarted.documents(), frozen)
        relocated = self.root / "relocated"; shutil.copytree(self.root / "inputs", relocated)
        moved = self.open(sources=[relocated / self.source.name]); self.assertEqual(moved.state()["head"], new["head"])
        for kind in ("evidence", "graph", "check", "review", "initial_plan"):
            with self.subTest(input=kind):
                data = copy.deepcopy(self.data); plan = self.initial
                if kind == "evidence": data[kind]["created_at"] = "2099-01-01T00:00:00+00:00"
                elif kind == "graph":
                    data["graph"]["artifact_id"] = "different-valid-input-graph"
                    data["check"]["input_refs"][1] = revision.reference(data["graph"])
                    data["check"]["payload"]["graph_ref"] = revision.reference(data["graph"])
                    data["check"]["content_hash"] = digest(data["check"]["payload"])
                    plan = revision.make_revision_plan(data["evidence"], data["graph"], data["check"], [], AUTHOR)
                elif kind == "check":
                    data["check"]["artifact_id"] = "different-valid-input-check"
                    plan = revision.make_revision_plan(data["evidence"], data["graph"], data["check"], [], AUTHOR)
                elif kind == "review": data[kind]["workspace_new_note"] = "different immutable input"
                else: plan = revision.make_revision_plan(data["evidence"], data["graph"], data["check"], [], {**AUTHOR, "note": "Different seed plan"})
                with self.assertRaises(ValueError): self.open(data=data, initial=plan)
        self.assertEqual(w.state()["head"], new["head"])

    def test_caller_mutating_input_objects_cannot_rewrite_a_frozen_workspace(self):
        w = self.open(); before = w.state(); documents = w.documents()
        self.data["evidence"]["payload"]["pages"][0]["ocr_lines"][0]["text"] = "caller mutation"
        self.data["graph"]["payload"]["answers"][0]["text"] = "caller replacement"
        self.initial["payload"]["author"]["note"] = "caller changed author"
        self.assertEqual(w.state(), before); self.assertEqual(w.documents(), documents)

    def test_crop_is_actual_original_png_and_invalid_or_changed_source_is_rejected(self):
        extra = self.source.parent / "extra.png"; Image.new("RGB", (8, 7), "black").save(extra)
        manifest = json.loads(self.source.read_text(encoding="utf-8"))
        manifest["assets"].append({"asset_id": "verified-but-unscoped", "path": extra.name, "sha256": file_digest(extra), "width": 8, "height": 7, "reading_order": 2})
        self.source.write_text(json.dumps(manifest), encoding="utf-8")
        w = self.open(); source = next(a for a in manifest["assets"] if a["asset_id"] == "answer")
        self.assertNotIn("verified-but-unscoped", [a["asset_id"] for a in w.state()["assets"]])
        path = self.source.parent / source["path"]
        from io import BytesIO
        crop = Image.open(BytesIO(w.source_png("answer", [10, 15, 35, 30]))).convert("RGB")
        with Image.open(path) as image:
            self.assertEqual(crop.size, (25, 15)); self.assertEqual(crop.tobytes(), image.convert("RGB").crop((10, 15, 35, 30)).tobytes())
        for aid, box in (("unknown", None), ("verified-but-unscoped", None), ("answer", [0, 0, 999, 300]), ("answer", [True, 0, 3, 3])):
            with self.subTest(asset=aid, box=box), self.assertRaises(ValueError): w.source_png(aid, box)
        old = w.state(); request = self.text_request(old, "13", "4")
        saved = path.read_bytes(); path.write_bytes(saved + b"changed")
        try:
            with self.assertRaises(SourceChanged): w.source_png("answer")
            with self.assertRaises(SourceChanged): w.save(request)
        finally: path.write_bytes(saved)
        self.assertEqual(w.state()["plan_revision"], self.initial["revision"])

    def test_source_change_inside_commit_hook_aborts_without_consuming_published_objects(self):
        armed = False
        image = self.root / "inputs" / "answer.png"; original = image.read_bytes()
        def hook():
            if armed: image.write_bytes(original + b"changed-in-commit-window")
        w = self.open(hook=hook); old = w.state(); before = self.object_bytes(); armed = True
        try:
            with self.assertRaises(SourceChanged): w.save(self.text_request(old, "13", "4"))
        finally: image.write_bytes(original)
        current = self.open(); self.assertEqual(current.state()["head"], old["head"])
        self.assertEqual(len(current.state()["history"]), len(old["history"]))
        self.assertTrue(set(before) <= set(self.object_bytes()))
        for name, raw in before.items(): self.assertEqual(self.object_bytes()[name], raw)

    def test_before_commit_failure_preserves_head_and_orphans_then_retry_is_a_new_valid_revision(self):
        armed = False
        def hook():
            if armed: raise RuntimeError("test crash after immutable publication, before SQL commit")
        w = self.open(hook=hook); old = w.state(); before = self.object_bytes(); armed = True
        request = self.text_request(old, "13", "4")
        with self.assertRaises(RuntimeError): w.save(request)
        after = self.object_bytes(); self.assertGreater(len(after), len(before))
        self.assertEqual(self.open().state()["head"], old["head"])
        for name, raw in before.items(): self.assertEqual(after[name], raw)
        retry = self.open(); saved = retry.save(request)
        self.assertEqual(saved["plan_revision"], old["plan_revision"] + 1); self.assertEqual(len(saved["history"]), 2)
        self.assert_audited(retry)
        for name, raw in after.items(): self.assertEqual(self.object_bytes()[name], raw)

    def test_silent_corruption_of_just_published_object_cannot_advance_committed_head(self):
        armed = False; before = {}; corrupted = []
        def hook():
            if not armed: return
            for path in (self.workdir / "objects").glob("*.json"):
                if path.relative_to(self.workdir).as_posix() in before: continue
                if json.loads(path.read_text(encoding="utf-8")).get("kind") == "QuestionGraphTrial":
                    path.write_bytes(path.read_bytes() + b"silently-corrupted-before-commit")
                    corrupted.append(path)
                    return
            raise AssertionError("fault hook did not see the actual published new graph")
        w = self.open(hook=hook); old = w.state(); before = self.object_bytes(); armed = True
        with self.assertRaises(ValueError): w.save(self.text_request(old, "13", "4"))
        self.assertEqual(len(corrupted), 1)
        self.assertTrue(corrupted[0].read_bytes().endswith(b"silently-corrupted-before-commit"))
        restarted = self.open(); self.assertEqual(restarted.state()["head"], old["head"])
        self.assertEqual(len(restarted.state()["history"]), len(old["history"]))
        for name, raw in before.items(): self.assertEqual(self.object_bytes()[name], raw)

    def test_corrupt_current_immutable_object_refuses_restart_instead_of_repairing_history(self):
        w = self.open(); docs = w.documents(); before = self.object_bytes()
        objects = [p for p in (self.workdir / "objects").rglob("*.json") if json.loads(p.read_text(encoding="utf-8")) == docs["graph"]]
        self.assertTrue(objects, "current graph must be an immutable saved document")
        path = objects[0]; original = path.read_bytes(); path.write_bytes(original + b"corrupt")
        with self.assertRaises(ValueError): self.open()
        self.assertEqual(path.read_bytes(), original + b"corrupt")
        self.assertEqual(set(before), set(self.object_bytes()))

    def test_unknown_changes_keys_duplicate_blocks_and_false_approval_never_create_versions(self):
        w = self.open(); old = w.state(); valid = self.text_request(old, "草稿")
        faults = [lambda r:r.update(complete=True), lambda r:r["author"].update(transcription_verified=True),
                  lambda r:r["author"].update(kind="HUMAN_REVIEWED"), lambda r:r["author"].update(kind="CPU_RAPID_LATEX_OCR"),
                  lambda r:r.update(answer_id="foreign-answer"), lambda r:r["changes"][0].update(key="unknown-block"),
                  lambda r:r["changes"].append(copy.deepcopy(r["changes"][0])), lambda r:r["changes"][0].update(bbox=[0, 0, 3, 3]),
                  lambda r:r["changes"][0].update(format="html"), lambda r:r["changes"][0].update(text="")]
        for i, mutate in enumerate(faults):
            with self.subTest(fault=i):
                request = copy.deepcopy(valid); mutate(request)
                with self.assertRaises(ValueError): w.save(request)
                self.assertEqual(w.state()["head"], old["head"])
        edited = w.save({**valid, "author": {"kind": "HUMAN_DRAFT", "id": "draft-human-label", "note": "Authorship is not approval"}})
        self.assert_unverified(edited); self.assert_unverified(w.documents()["check"]["payload"])

    def test_review_and_edit_default_imports_no_ocr_model_or_network(self):
        with patch.dict(sys.modules, {"rapidocr_onnxruntime": None, "rapid_latex_ocr": None, "onnxruntime": None}), \
             patch("socket.socket", side_effect=AssertionError("No network in offline review")):
            w = self.open(); state = w.state(); w.source_png("answer")
            state = w.save(self.text_request(state, "13", "4")); self.assert_audited(w)
        self.assert_unverified(state)

    def test_generated_typed_images_diagnostics_and_other_regions_survive_text_save(self):
        self.data = make_content_fixture(self.root / "pictures", with_images=True)
        self.source = manifest_for(self.data, self.root / "pictures")
        self.initial = revision.make_revision_plan(self.data["evidence"], self.data["graph"], self.data["check"], [], AUTHOR)
        w = self.open(); old = w.state(); row = self.state_answer(old); self.assertTrue(row["figures"])
        all_ids = {fid for b in row["blocks"] for fid in b["source_fragment_ids"]}
        source_answer = answer(self.data["graph"], "9")
        diagnostic = {f["fragment_id"] for f in source_answer["fragments"] if f.get("represented_by_image_region") is not None or f.get("render_as_separate_region") is False}
        self.assertFalse(all_ids & diagnostic)
        new = w.save(self.text_request(old, "保留图片的显式草稿")); self.assertEqual(self.state_answer(new)["figures"], row["figures"])
        self.assert_audited(w)


if __name__ == "__main__":
    unittest.main()
