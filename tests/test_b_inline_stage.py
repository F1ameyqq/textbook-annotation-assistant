"""Inline stage source, immutable core and honest partial package boundaries."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tests")]
from annotation.recognition import inline_stage, offline
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.inline_formula import collect_inline_formula
from test_b_inline_formula import formula_fixture, FormulaWorker


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def refresh_inline_package(data):
    p, manifest = data["package_path"].parent, data["manifest"]
    for name, value in data["documents"].items():
        descriptor = manifest["documents"][name]
        write(p/descriptor["path"], value)
        descriptor["sha256"] = file_digest(p/descriptor["path"])
        descriptor["artifact_ref"] = inline_stage.reference(value) if name != "rows" else None
    members = {d["path"] for d in manifest["documents"].values()}
    members.update(f.relative_to(p).as_posix() for f in data["journal_dir"].rglob("*") if f.is_file())
    manifest["members"] = {relative: {"sha256": file_digest(p/relative), "bytes": (p/relative).stat().st_size} for relative in sorted(members)}
    write(data["package_path"], manifest)


def make_inline_fixture(directory, *, max_items=None, fail=False, continuation=False):
    """Actual generated source, synthetic OCR/formula, real local SQLite journal."""
    root = Path(directory); root.mkdir(parents=True, exist_ok=True)
    f = formula_fixture(root, math_text="1+2=")
    input_evidence_path = root/"inline-evidence.json"
    if continuation:
        from annotation.recognition.continuation_stage import prepare_continuation_scope, build_continuation_stage_proof, apply_continuation_stage
        from annotation.recognition.continued_quality import build_continued_quality
        from annotation.recognition.inline_ocr import collect_inline_observations
        from annotation.recognition.inline_math import build_inline_math_layout
        from test_b_inline_math import raw_row
        e5 = f["evidence"]; g5 = offline.assemble(e5)
        args = (root/"package.json", root/"source.json", root/"adjacent-original.png")
        scope = prepare_continuation_scope(e5, g5, *args)
        proof = build_continuation_stage_proof(scope, *args)
        application = apply_continuation_stage(scope, proof, *args)
        e6 = scope["payload"]["evidence"]
        original = root/"adjacent-original.png"
        ids = ["target-page/ocr/0"]
        def ordinary(bgr, **flags): return [raw_row("1+2=", bgr.shape[1], bgr.shape[0])], [.01, 0, .02]
        observed = collect_inline_observations(e6, original, asset_id="target-page", line_ids=ids, recognizer=ordinary)
        layout = build_inline_math_layout(e6, observed, original, line_ids=ids)
        review = json.loads((root/"review.json").read_text(encoding="utf-8"))
        f.update(evidence=e6, layout=layout, original=original, line_ids=ids)
        graph = application["payload"]["graph"]
        base_check = build_continued_quality(scope, proof, application, review,
            package_path=args[0], source_path=args[1], adjacent_source_path=args[2])
        input_evidence_path = root/"evidence.json"
    journal = root/"inline-journal"
    worker = FormulaWorker(outputs=("1+2=1",))
    if fail:
        def failed(tensor): raise RuntimeError("SYNTHETIC_TEST explicit failure")
        worker = failed
    observations, report = collect_inline_formula(f["evidence"], f["layout"], f["original"], journal,
        line_ids=f["line_ids"], recognizer=worker, max_items=max_items)
    documents = {"evidence": f["evidence"], "rows": f["line_ids"],
        "ocr_observations": f["layout"]["payload"]["observations_archive"],
        "formula_observations": observations, "formula_report": report}
    manifest = {"schema_version": inline_stage.PACKAGE_SCHEMA, "artifact_id": "synthetic-inline-package",
        "book_id": f["evidence"]["book_id"], "scope_id": f["evidence"]["scope_id"], "asset_id": f["layout"]["payload"]["source"]["asset_id"],
        "line_ids": f["line_ids"], "policy": inline_stage.POLICY, "journal_dir": journal.name, "members": {},
        "documents": {name: {"path": "inline-"+name+".json", "sha256": None, "artifact_ref": None} for name in documents}}
    if not continuation: graph = offline.assemble(f["evidence"])
    review = json.loads((root/"review.json").read_text(encoding="utf-8"))
    data = {**f, "evidence": f["evidence"], "graph": graph, "review": review,
        "base_check": base_check if continuation else offline.quality_check(f["evidence"], graph, review), "manifest": manifest, "documents": documents,
        "package_path": root/"inline-package.json", "journal_dir": journal, "source_path": root/"source.json",
        "context_path": root/"context.json", "review_path": root/"review.json", "evidence_path": input_evidence_path,
        "continuation_path": root/"package.json" if continuation else None,
        "adjacent_source_path": root/"adjacent-original.png" if continuation else None}
    refresh_inline_package(data)
    return data


class InlineStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.d = make_inline_fixture(self.root)

    def prepare(self, evidence=None, graph=None):
        return inline_stage.prepare_inline_stage(evidence or self.d["evidence"], graph or self.d["graph"], self.d["package_path"], self.d["original"])

    def test_ready_application_only_adds_unselected_attachment_and_current_check(self):
        before = copy.deepcopy(self.d["graph"])
        prepared = self.prepare()
        self.assertEqual(prepared["payload"]["execution_state"], "READY", prepared["payload"]["formula_check"]["payload"]["issues"])
        applied = inline_stage.apply_inline_stage(prepared)
        graph = applied["payload"]["graph"]
        attached = graph["payload"]["inline_content"]
        self.assertEqual({k:v for k,v in graph["payload"].items() if k != "inline_content"}, before["payload"])
        self.assertEqual(attached["base_graph_archive"], before)
        self.assertEqual(attached["units"], self.d["layout"]["payload"]["units"])
        self.assertEqual(attached["calls"], self.d["documents"]["formula_observations"]["payload"]["calls"])
        self.assertEqual(attached["selected_candidate_refs"], [])
        self.assertEqual(self.d["graph"], before)
        checked = inline_stage.build_inline_quality(prepared, applied, self.d["base_check"])
        self.assertEqual(checked["schema_version"], "b-check-trial/0.5")
        self.assertEqual(checked["payload"]["issues"][:-1], self.d["base_check"]["payload"]["issues"])
        self.assertEqual(checked["payload"]["graph_ref"], inline_stage.reference(graph))
        self.assertFalse(checked["payload"]["transcription_verified"])
        self.assertEqual(checked["payload"]["decision"], "HOLD")

    def test_package_audits_and_all_stages_do_not_import_models_or_network(self):
        with patch.dict(sys.modules, {"rapidocr_onnxruntime":None,"onnxruntime":None,"rapid_latex_ocr":None}), \
             patch("socket.socket", side_effect=AssertionError("no network")):
            prepared = self.prepare()
            app = inline_stage.apply_inline_stage(prepared)
            check = inline_stage.build_inline_quality(prepared, app, self.d["base_check"])
        self.assertEqual(check["payload"]["new_model_calls"], 0)
        for value in (prepared, app, app["payload"]["graph"], check):
            self.assertNotIn("created_at", value)

    def test_current_evidence_new_identity_can_bind_only_if_full_page_context_equal(self):
        changed = copy.deepcopy(self.d["evidence"]); changed["artifact_id"] = "new-current-E"
        prepared = self.prepare(changed, offline.assemble(changed))
        self.assertEqual(prepared["payload"]["base_evidence_ref"], inline_stage.reference(changed))
        self.assertEqual(prepared["payload"]["original_evidence_archive"], self.d["evidence"])

    def test_selected_page_or_context_change_cannot_rebind_old_ocr(self):
        for fault in ("raw", "score", "context", "bool_numeric"):
            value = copy.deepcopy(self.d["evidence"])
            if fault == "raw": value["payload"]["pages"][0]["ocr_lines"][0]["text"] += "changed"
            elif fault == "score": value["payload"]["pages"][0]["ocr_lines"][0]["score"] += .01
            elif fault == "context": value["payload"]["context"]["changed"] = True
            else: value["payload"]["pages"][0]["source"]["reading_order"] = False
            value["content_hash"] = digest(value["payload"])
            with self.subTest(fault=fault), self.assertRaisesRegex(ValueError, "exact full context"):
                self.prepare(value, offline.assemble(value))

    def test_changed_other_page_is_allowed_with_same_declared_context(self):
        old = copy.deepcopy(self.d["evidence"])
        other = copy.deepcopy(old["payload"]["pages"][0]); other["asset_id"] = "other"
        other["source"]["asset_id"] = "other"; other["ocr_lines"] = []; other["answer_detail_lines"] = []
        old["payload"]["pages"].append(other); old["content_hash"] = digest(old["payload"])
        # The collector archive need not be fabricated/re-signed: a new current
        # page may exist outside the selected observation scope.
        self.prepare(old, offline.assemble(old))

    def test_corrupt_or_missing_unlisted_journal_members_are_rejected(self):
        member = self.d["journal_dir"]/"inline-formula.sqlite3"
        member.write_bytes(member.read_bytes()+b"corrupt")
        with self.assertRaisesRegex(ValueError, "bytes or SHA"):
            inline_stage.load_inline_package(self.d["package_path"], self.d["original"])

    def test_unlisted_added_journal_file_and_path_escape_are_rejected(self):
        extra = self.d["journal_dir"]/"extra.json"; extra.write_text("{}")
        with self.assertRaisesRegex(ValueError, "member set"):
            inline_stage.load_inline_package(self.d["package_path"], self.d["original"])
        extra.unlink()
        self.d["manifest"]["documents"]["rows"]["path"] = "../rows.json"
        write(self.d["package_path"], self.d["manifest"])
        with self.assertRaisesRegex(ValueError, "portable"):
            inline_stage.load_inline_package(self.d["package_path"], self.d["original"])

    def test_forged_parent_cannot_claim_another_selected_source_line(self):
        graph = copy.deepcopy(self.d["graph"])
        a = graph["payload"]["answers"][0]
        first, second = a["fragments"][:2]
        second["parent_line_id"] = first["parent_line_id"]
        graph["content_hash"] = digest(graph["payload"])
        with self.assertRaisesRegex(ValueError, "parent"):
            self.prepare(graph=graph)

    def test_stale_check_or_edited_core_cannot_become_current_check(self):
        prepared = self.prepare(); app = inline_stage.apply_inline_stage(prepared)
        wrong = copy.deepcopy(self.d["base_check"]); wrong["input_refs"][0]["artifact_id"] = "stale"
        with self.assertRaisesRegex(ValueError, "current base-core"):
            inline_stage.build_inline_quality(prepared, app, wrong)
        permuted = copy.deepcopy(self.d["base_check"])
        permuted["input_refs"][:2] = list(reversed(permuted["input_refs"][:2]))
        with self.assertRaisesRegex(ValueError, "exact ordered"):
            inline_stage.build_inline_quality(prepared, app, permuted)
        app["payload"]["graph"]["payload"]["answers"][0]["text"] = "altered core"
        app["content_hash"] = digest(app["payload"])
        with self.assertRaisesRegex(ValueError, "exact attachment"):
            inline_stage.build_inline_quality(prepared, app, self.d["base_check"])

    def test_partial_and_failed_scopes_never_apply(self):
        for kwargs, expected in (({"max_items":1}, "PARTIAL"), ({"fail":True}, "FAILED")):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as directory:
                d = make_inline_fixture(directory, **kwargs)
                prepared = inline_stage.prepare_inline_stage(d["evidence"], d["graph"], d["package_path"], d["original"])
                self.assertEqual(prepared["payload"]["execution_state"], expected)
                with self.assertRaisesRegex(ValueError, "READY"):
                    inline_stage.apply_inline_stage(prepared)

    def test_coordinated_rehash_cannot_promote_numeric_false_or_partial_execution(self):
        prepared = self.prepare()
        p = copy.deepcopy(prepared["payload"]); p["complete"] = 0
        forged = inline_stage._envelope(inline_stage.PREPARE_SCHEMA, "InlinePreparationTrial", "inline-preparation", self.d["evidence"],
            prepared["input_refs"], p, "prepare")
        with self.assertRaisesRegex(ValueError, "flags"):
            inline_stage.apply_inline_stage(forged)
        with tempfile.TemporaryDirectory() as directory:
            d = make_inline_fixture(directory, max_items=1)
            partial = inline_stage.prepare_inline_stage(d["evidence"], d["graph"], d["package_path"], d["original"])
            p = copy.deepcopy(partial["payload"]); p["execution_state"] = "READY"
            forged = inline_stage._envelope(inline_stage.PREPARE_SCHEMA, "InlinePreparationTrial", "inline-preparation", d["evidence"],
                partial["input_refs"], p, "prepare")
            with self.assertRaisesRegex(ValueError, "READY"):
                inline_stage.apply_inline_stage(forged)


if __name__ == "__main__": unittest.main()
