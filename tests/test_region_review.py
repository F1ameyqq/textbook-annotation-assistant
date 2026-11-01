"""Source-bound candidate choices are explicit drafts, never content approval."""
import base64
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from annotation.recognition import offline
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.formula_backend import collect_formula_observations
from annotation.recognition.formula_canvas import collect_canvas_observations
from annotation.recognition.math_reading import collect_math_roles
from annotation.recognition.region_draft import build_region_draft
from annotation.recognition.region_ocr import collect_region_observations
from annotation.recognition.region_runs import plan_region_runs
from test_region_runs import pixel_layout, reference, resign_layout


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def make_region_review_fixture(directory):
    """Generated pixels and injected observations; this is not CPU or math gold.

    The minimal G05 capsule is for the adapter's raw source/ledger contract.
    Full inline-stage/workspace behavior is tested by the integration owner.
    """
    root = Path(directory); root.mkdir(parents=True, exist_ok=True)
    layout, crop = pixel_layout(root)
    section = ["Generated region section"]
    lines = [{"line_id": "generated/ocr/" + str(i), "text": text, "score": .8,
              "bbox": [102, y, 119, y + 12],
              "location": {"column": 0, "window_index": 0, "section_path": section}}
             for i, (y, text) in enumerate(((217, "16.解：generated"), (252, "continued")))]
    lp = layout["payload"]
    lp["source_ocr"] = copy.deepcopy(lines)
    for group, line in zip(lp["reading_groups"], lines):
        group["units"] = [u for u in group["units"] if u["kind"] != "body"]
        group["units"].insert(0, {"kind": "body", "ocr_refs": [line["line_id"]]})
    lp["token_coverage"] = [{"line_id": line["line_id"], "status": "BODY"} for line in lines]
    resign_layout(layout)
    plan = plan_region_runs(layout, crop)
    ordinary = collect_region_observations(plan, crop,
        recognizer=lambda *a, **kw: ([["generated body", .8]], [.01]))
    duplicate = r"\frac{x^{2}+1}{2}"
    legacy = collect_formula_observations(layout, crop,
        recognizer=lambda *a: (duplicate, .01))
    canvas_raw = iter([r"\unknown{x}", duplicate] * 2)
    canvas = collect_canvas_observations(layout, crop,
        recognizer=lambda *a: (next(canvas_raw), .01))
    roles = collect_math_roles(layout, crop,
        recognizer=lambda *a, **kw: ([["2", .8]], [.01]))
    draft = build_region_draft(plan, ordinary, legacy, canvas, roles, crop)
    asset = {"asset_id": lp["asset_id"], "path": "generated-original.png",
             "sha256": lp["source_sha256"], "width": 300, "height": 400,
             "reading_order": 0, "reference_quality": "SYNTHETIC_TEST"}
    source = {"schema_version": "b-source-trial/0.1", "artifact_id": "generated-region-source",
              "book_id": layout["book_id"], "scope_id": layout["scope_id"], "assets": [asset]}
    context = {"schema_version": "b-context-trial/0.1", "artifact_id": "generated-region-context",
               "book_id": layout["book_id"], "scope_id": layout["scope_id"], "pages": {
                   asset["asset_id"]: {"sha256": asset["sha256"], "role": "answer", "windows": [
                       {"column": 0, "y_range": [0, 400], "path": section}]}}}
    page = {"asset_id": asset["asset_id"], "source": asset, "page_role": "answer",
            "layout": {"mode": "two_columns", "cut_x": 250}, "ocr_lines": lines,
            "answer_detail_lines": [], "unscoped_line_ids": []}
    producer = {"module": "SYNTHETIC_TEST", "execution_kind": "SYNTHETIC_TEST"}
    evidence = offline.artifact("b-evidence-trial/0.3", "EvidenceBundleTrial", source,
        {"pages": [page], "context": context, "history_annotations_consumed": False,
         "quality_decision": "NOT_EVALUATED"}, [], producer)
    graph03 = offline.assemble(evidence)
    graph = offline.artifact("b-graph-trial/0.5", "QuestionGraphTrial", evidence,
                             copy.deepcopy(graph03["payload"]), [reference(evidence)], producer)
    answer_id = graph["payload"]["answers"][0]["answer_id"]
    draft_path = root / "draft.json"; _write(draft_path, draft)
    manifest = {"schema_version": "b-region-review-inputs-trial/0.1", "entries": [
        {"answer_id": answer_id, "draft": draft_path.name, "crop": crop.name}]}
    catalog_path = root / "region-catalog.json"; _write(catalog_path, manifest)
    return {"root": root, "layout": layout, "plan": plan, "draft": draft, "crop": crop,
            "original": root / asset["path"], "source_paths": {asset["asset_id"]: root / asset["path"]},
            "source": source, "evidence": evidence, "graph": graph, "answer_id": answer_id,
            "manifest": manifest, "catalog_path": catalog_path, "draft_path": draft_path}


class RegionReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.temp.cleanup)
        cls.data = make_region_review_fixture(cls.temp.name)
        cls.api = importlib.import_module("annotation.recognition.region_review")
        d = cls.data
        cls.loaded = cls.api.load_region_catalog(d["catalog_path"])
        cls.catalog = cls.api.validate_region_catalog(cls.loaded, d["evidence"], d["graph"], d["source_paths"])

    def block(self, *, row_index=0):
        d = self.data; row = d["draft"]["payload"]["rows"][row_index]
        source = self.catalog[0]["source_rows"][row["row_id"]]
        return {"key": "generated-region-block-" + str(row_index), "kind": "REGION",
                "asset_id": source["asset_id"], "bbox": copy.deepcopy(source["bbox"]),
                "source_fragment_ids": copy.deepcopy(source["source_fragment_ids"]), "role": source["role"],
                "runs": copy.deepcopy(row["runs"])}

    def options(self, block=None, answer_id=None):
        return self.api.region_options(self.catalog, answer_id or self.data["answer_id"],
                                       block if block is not None else self.block())

    def proposed(self, *, kind="WHOLE_MODEL_OBSERVATION", supported=True):
        block = self.block(); group = self.options(block)[0]
        choice = next(c for c in group["choices"] if c["kind"] == kind and c["parse_supported"] is supported)
        runs = copy.deepcopy(block["runs"]); runs[group["run_index"]] = {"format": "latex", "text": choice["latex"]}
        selection = {k: copy.deepcopy(group[k]) for k in ("bundle_ref", "row_id", "run_index", "fraction_id")}
        selection["candidate_id"] = choice["candidate_id"]
        author = {"kind": "SYNTHETIC_TEST", "id": "generated-choice", "note": "Not content approval"}
        return block, group, choice, runs, [selection], author

    def validate_selection(self, values, **changes):
        block, _, _, runs, selections, author = values
        args = {"attachments": self.catalog, "answer_id": self.data["answer_id"], "block": block,
                "runs": runs, "selections": selections, "author": author}
        args.update(changes)
        return self.api.validate_region_selections(**args)

    def test_loader_and_validation_bind_original_crop_and_return_fresh_source_rows(self):
        d = self.data; before = copy.deepcopy((self.loaded, d["evidence"], d["graph"]))
        self.assertEqual(set(self.loaded[0]), {"answer_id", "draft", "crop_png_base64"})
        self.assertEqual(base64.b64decode(self.loaded[0]["crop_png_base64"], validate=True), d["crop"].read_bytes())
        self.assertEqual(file_digest(d["original"]), d["layout"]["payload"]["source_sha256"])
        repeated = self.api.validate_region_catalog(self.catalog, d["evidence"], d["graph"], d["source_paths"])
        self.assertEqual(repeated, self.catalog)
        self.assertIsNot(repeated[0]["draft"], self.catalog[0]["draft"])
        self.assertEqual((self.loaded, d["evidence"], d["graph"]), before)
        ids = [f["fragment_id"] for f in d["graph"]["payload"]["answers"][0]["fragments"]]
        self.assertEqual([fid for row in repeated[0]["source_rows"].values() for fid in row["source_fragment_ids"]], ids)
        self.assertEqual(self.api.validate_region_catalog([], d["evidence"], d["graph"], d["source_paths"]), [])

    def test_every_whole_and_derived_candidate_keeps_unknown_syntax_and_duplicate_identity(self):
        before = copy.deepcopy(self.catalog)
        for i, fraction in enumerate(self.data["draft"]["payload"]["fractions"]):
            group, = self.options(self.block(row_index=i))
            slot = next(s for s in self.data["plan"]["payload"]["fraction_slots"]
                        if s["fraction_id"] == fraction["fraction_id"])
            self.assertEqual(group["fraction_id"], fraction["fraction_id"])
            self.assertEqual(group["source_bbox"], slot["source_bbox"])
            self.assertEqual(group["bundle_ref"], reference(self.data["draft"]))
            self.assertEqual(group["default_candidate_id"], fraction["draft_candidate_id"])
            raw = fraction["whole_candidates"] + fraction["composed_candidates"]
            self.assertEqual([c["candidate_id"] for c in group["choices"]], [c["candidate_id"] for c in raw])
            self.assertEqual([c["latex"] for c in group["choices"]], [c["latex"] for c in raw])
            unknown = next(c for c in group["choices"] if c["latex"] == r"\unknown{x}")
            self.assertFalse(unknown["parse_supported"])
            copies = [c for c in group["choices"] if c["latex"] == r"\frac{x^{2}+1}{2}"
                      and c["kind"] == "WHOLE_MODEL_OBSERVATION"]
            self.assertEqual(len(copies), 3)
            self.assertEqual(len({c["candidate_id"] for c in copies}), 3)
            self.assertEqual(group["decision"], "HOLD"); self.assertIs(group["transcription_verified"], False)
            block = self.block(row_index=i); block["runs"][group["run_index"]]["text"] = copies[0]["latex"]
            matches, = self.options(block)
            all_same_text = {c["candidate_id"] for c in group["choices"] if c["latex"] == copies[0]["latex"]}
            self.assertEqual(set(matches["matching_candidate_ids"]), all_same_text)
        self.assertEqual(self.catalog, before)

    def test_whole_and_composed_selection_provenance_is_distinct_and_inputs_immutable(self):
        for kind, supported in (("WHOLE_MODEL_OBSERVATION", True), ("DERIVED_ROLE_COMPOSITION", True),
                                ("WHOLE_MODEL_OBSERVATION", False)):
            with self.subTest(kind=kind, supported=supported):
                values = self.proposed(kind=kind, supported=supported); before = copy.deepcopy((self.catalog, values))
                record, = self.validate_selection(values)
                self.assertEqual(record["kind"], kind); self.assertEqual(record["latex"], values[2]["latex"])
                self.assertEqual(record["candidate_id"], values[2]["candidate_id"])
                self.assertEqual(record["source_bbox"], values[1]["source_bbox"])
                self.assertEqual(record["editor_kind"], "SYNTHETIC_TEST")
                self.assertEqual(record["complete_model_call"], kind == "WHOLE_MODEL_OBSERVATION")
                self.assertEqual(record["decision"], "HOLD"); self.assertIs(record["transcription_verified"], False)
                if kind == "WHOLE_MODEL_OBSERVATION":
                    self.assertEqual(record["origin"], values[2]["origin"])
                    self.assertIn(record["origin"]["kind"], {"LEGACY_WHOLE", "CANVAS_WHOLE"})
                else:
                    self.assertEqual([c["role"] for c in record["origin"]["components"]], ["numerator", "denominator"])
                    self.assertTrue(all(c["fraction_id"] == record["fraction_id"] for c in record["origin"]["components"]))
                    self.assertTrue(all(set(c) == {"component_id", "fraction_id", "role", "latex", "origin"}
                                        for c in record["origin"]["components"]))
                    self.assertNotIn("archives", record["origin"])
                self.assertEqual((self.catalog, values), before)

    def test_plain_edit_can_accompany_explicit_choice_but_changed_topology_cannot(self):
        values = self.proposed(); values[3][0]["text"] = "explicit plain edit 𝛼"
        self.assertEqual(len(self.validate_selection(values)), 1)
        base = self.block()
        for mutate in (lambda b: b["runs"].append({"format": "plain", "text": "extra"}),
                       lambda b: b.update(runs=b["runs"][1:] + b["runs"][:1]),
                       lambda b: b["runs"][1].update(format="plain"),
                       lambda b: b.update(source_fragment_ids=["same-pixels-wrong-fragment"]),
                       lambda b: b.update(role="explanation"),
                       lambda b: b.update(asset_id="other-asset"),
                       lambda b: b["bbox"].__setitem__(0, b["bbox"][0] + 1)):
            block = copy.deepcopy(base); mutate(block)
            self.assertEqual(self.options(block), [])
        self.assertEqual(self.options(answer_id="other-answer"), [])
        self.assertEqual(self.api.region_options(self.loaded, self.data["answer_id"], base), [])

    def test_selection_rejects_unknown_identity_bool_index_duplicates_and_forged_fields(self):
        foreign_candidate = self.options(self.block(row_index=1))[0]["choices"][0]["candidate_id"]
        for mutate in (
            lambda s: s[0].update(candidate_id="unknown"),
            lambda s: s[0].update(candidate_id=foreign_candidate),
            lambda s: s[0]["bundle_ref"].update(content_hash="0" * 64),
            lambda s: s[0]["bundle_ref"].update(revision=True),
            lambda s: s[0].update(row_id="other-row"),
            lambda s: s[0].update(fraction_id="other-fraction"),
            lambda s: s[0].update(run_index=True),
            lambda s: s.append(copy.deepcopy(s[0])),
            lambda s: s[0].update(transcription_verified=True),
        ):
            values = self.proposed(); mutate(values[4])
            with self.subTest(selection=values[4]), self.assertRaises(ValueError):
                self.validate_selection(values)
        values = self.proposed()
        with self.assertRaises(ValueError): self.validate_selection(values, answer_id="other-answer")
        with self.assertRaises(ValueError): self.validate_selection(values, selections=[])

    def test_selected_raw_latex_and_run_format_cannot_be_cleaned_or_replaced(self):
        for mutate in (lambda r, i: r[i].update(text=r[i]["text"] + " "),
                       lambda r, i: r[i].update(format="plain"),
                       lambda r, i: r[i].update(human_verified=True),
                       lambda r, i: r.append({"format": "plain", "text": "new topology"})):
            values = self.proposed(); mutate(values[3], values[1]["run_index"])
            with self.subTest(runs=values[3]), self.assertRaises(ValueError): self.validate_selection(values)

    def test_synthetic_bundle_cannot_be_promoted_by_editor_author(self):
        for kind in ("MODEL_DRAFT", "HUMAN_DRAFT", "HUMAN_REVIEWED"):
            values = self.proposed(); values[5]["kind"] = kind
            with self.subTest(kind=kind), self.assertRaises(ValueError): self.validate_selection(values)
        values = self.proposed(); values[5]["transcription_verified"] = True
        with self.assertRaises(ValueError): self.validate_selection(values)

    def test_forged_source_row_index_and_duplicate_region_do_not_become_validated_inputs(self):
        d = self.data; forged = copy.deepcopy(self.catalog)
        row = next(iter(forged[0]["source_rows"].values())); row["source_fragment_ids"] = ["foreign-fragment"]
        for capsules in (forged, [self.loaded[0], copy.deepcopy(self.loaded[0])]):
            with self.subTest(duplicate=len(capsules)), self.assertRaises(ValueError):
                self.api.validate_region_catalog(capsules, d["evidence"], d["graph"], d["source_paths"])

    def test_wrong_answer_role_and_same_crop_different_asset_are_rejected(self):
        d = self.data
        bad = copy.deepcopy(self.loaded); bad[0]["answer_id"] = "not-current-answer"
        with self.assertRaises(ValueError): self.api.validate_region_catalog(bad, d["evidence"], d["graph"], d["source_paths"])
        graph = copy.deepcopy(d["graph"])
        graph["payload"]["answers"][0]["fragments"][0]["role"] = "explanation"
        graph["content_hash"] = digest(graph["payload"])
        with self.assertRaises(ValueError): self.api.validate_region_catalog(self.loaded, d["evidence"], graph, d["source_paths"])
        evidence = copy.deepcopy(d["evidence"])
        evidence["payload"]["pages"][0]["source"]["asset_id"] = "other-asset"
        evidence["payload"]["pages"][0]["asset_id"] = "other-asset"
        evidence["content_hash"] = digest(evidence["payload"])
        with self.assertRaises(ValueError):
            self.api.validate_region_catalog(self.loaded, evidence, d["graph"], {"other-asset": d["original"]})

    def test_original_bytes_crop_pixels_and_capsule_shape_are_required(self):
        d = self.data
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); changed = root / "changed.png"
            changed.write_bytes(d["original"].read_bytes() + b"outside-crop-tail")
            with self.assertRaises(ValueError):
                self.api.validate_region_catalog(self.loaded, d["evidence"], d["graph"], {d["layout"]["payload"]["asset_id"]: changed})
            changed_crop = root / "wrong-crop.png"; Image.new("RGB", (80, 80), "white").save(changed_crop)
            bad_crop = copy.deepcopy(self.loaded)
            bad_crop[0]["crop_png_base64"] = base64.b64encode(changed_crop.read_bytes()).decode("ascii")
            whitespace = copy.deepcopy(self.loaded); whitespace[0]["crop_png_base64"] += "\n"
            approved = copy.deepcopy(self.loaded); approved[0]["human_verified"] = True
            for capsules in (bad_crop, whitespace, approved):
                with self.subTest(keys=list(capsules[0])), self.assertRaises(ValueError):
                    self.api.validate_region_catalog(capsules, d["evidence"], d["graph"], d["source_paths"])

    def test_rehashed_changed_candidate_text_cannot_replace_archived_raw_observation(self):
        d = self.data; changed = copy.deepcopy(self.loaded)
        draft = changed[0]["draft"]
        draft["payload"]["fractions"][0]["whole_candidates"][0]["latex"] = r"\frac{999}{2}"
        draft["content_hash"] = digest(draft["payload"])
        draft["artifact_id"] = "region-draft-" + digest([draft["input_refs"], draft["producer"], draft["payload"]])[:24]
        with self.assertRaises(ValueError):
            self.api.validate_region_catalog(changed, d["evidence"], d["graph"], d["source_paths"])

    def test_frozen_catalog_roundtrip_revalidates_derived_source_index(self):
        d = self.data
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frozen-catalog.json"
            frozen = {"schema_version": "b-region-review-catalog-trial/0.1", "entries": self.catalog}
            _write(path, frozen)
            loaded = self.api.load_region_catalog(path)
            self.assertEqual(self.api.validate_region_catalog(loaded, d["evidence"], d["graph"], d["source_paths"]), self.catalog)
            changed = copy.deepcopy(frozen)
            source_row = next(iter(changed["entries"][0]["source_rows"].values()))
            source_row["source_fragment_ids"] = ["not-the-current-source"]
            _write(path, changed)
            with self.assertRaises(ValueError):
                loaded = self.api.load_region_catalog(path)
                self.api.validate_region_catalog(loaded, d["evidence"], d["graph"], d["source_paths"])

    def test_manifest_rejects_ambiguous_json_and_nonlocal_paths_before_reading_inputs(self):
        d = self.data
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "inputs.json"
            for raw in ('{"schema_version":"b-region-review-inputs-trial/0.1","entries":[],"entries":[]}',
                        '{"schema_version":"b-region-review-inputs-trial/0.1","entries":NaN}'):
                manifest.write_text(raw, encoding="utf-8")
                with self.subTest(raw=raw), self.assertRaises(ValueError): self.api.load_region_catalog(manifest)
            for path in ("../draft.json", "https://invalid.example/draft.json", "//server/share/draft.json",
                         "C:/outside/draft.json", "folder\\draft.json"):
                value = copy.deepcopy(d["manifest"]); value["entries"][0]["draft"] = path
                _write(manifest, value)
                with self.subTest(path=path), self.assertRaises(ValueError): self.api.load_region_catalog(manifest)

    def test_repeated_member_cannot_replace_its_initial_byte_receipt_during_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); draft = root / "shared-draft.json"; crop = root / "crop.png"
            _write(draft, self.data["draft"]); crop.write_bytes(self.data["crop"].read_bytes())
            manifest = root / "inputs.json"
            _write(manifest, {"schema_version": "b-region-review-inputs-trial/0.1", "entries": [
                {"answer_id": aid, "draft": draft.name, "crop": crop.name} for aid in ("first", "second")]})
            original_read = Path.read_bytes; reads = 0
            def read_bytes(path):
                nonlocal reads
                raw = original_read(path)
                if path.resolve() == draft.resolve():
                    reads += 1
                    if reads == 1: draft.write_bytes(raw + b"\n")
                return raw
            with patch.object(Path, "read_bytes", read_bytes), self.assertRaisesRegex(ValueError, "changed"):
                self.api.load_region_catalog(manifest)


if __name__ == "__main__":
    unittest.main()
