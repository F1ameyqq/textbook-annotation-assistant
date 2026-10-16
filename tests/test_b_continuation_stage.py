"""Portable generated continuation sources and stage failure boundaries.

All OCR observations in the generated fixture are SYNTHETIC_TEST. Historical
development-review classifications required by the old image contract are not
CPU or human execution receipts. Every original/capture is an actual local PNG;
no engine, network, website, expected transcription or hidden source is used.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition import offline
from annotation.recognition.continuation_stage import (POLICY, reference, source_answer_snapshot,
    load_continuation_package, prepare_continuation_scope, build_continuation_stage_proof, apply_continuation_stage)
from annotation.recognition.image_regions import ink_witness
from annotation.recognition.continuation_apply import rollback_continuation, _graph_id


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def refresh_package(data):
    """Rebind explicit temporary test edits, never mutate an existing source."""
    for name, value in data["documents"].items():
        value["content_hash"] = digest(value["payload"])
        descriptor = data["package"]["documents"][name]
        path = data["package_path"].parent / descriptor["path"]
        write(path, value)
        descriptor.update(text_sha256=hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest(), artifact_ref=reference(value))
    write(data["package_path"], data["package"])


def _document(schema, kind, payload, *, book, scope, inputs=None):
    return offline.artifact(schema, kind, {"book_id": book, "scope_id": scope}, payload, inputs or [],
                            {"module": "SYNTHETIC_TEST", "execution_kind": "SYNTHETIC_TEST"})


def make_continuation_fixture(directory):
    """One generated answer page plus an observed adjacent prefix with images."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    book, scope, expanded = "synthetic-continuation-book", "one-observed-answer-page", "one-answer-plus-adjacent-prefix"
    path = ["Synthetic chapter", "Synthetic reflection"]
    source_image = Image.new("RGB", (200, 300), "white")
    draw = ImageDraw.Draw(source_image)
    draw.text((110, 260), "9.tail figure1", fill="black")
    draw.rectangle((130, 276, 155, 284), outline="black")
    draw.text((130, 288), "F1", fill="black")
    source_file = root / "source-page.png"
    source_image.save(source_file)
    target_image = Image.new("RGB", (200, 300), "white")
    draw = ImageDraw.Draw(target_image)
    draw.text((10, 10), "figure2 continues", fill="black")
    draw.rectangle((25, 28, 65, 44), outline="black")
    draw.text((35, 48), "F2", fill="black")
    draw.text((10, 75), "next", fill="black")
    adjacent_file = root / "adjacent-original.png"
    target_image.save(adjacent_file)
    asset = {"asset_id": "source-page", "path": source_file.name, "sha256": file_digest(source_file),
             "width": 200, "height": 300, "reading_order": 0, "external_refs": {"resource_index": 4},
             "reference_quality": "MODEL_VISUAL_DEVELOPMENT_REVIEW"}
    adjacent = {"asset_id": "target-page", "path": "unbundled/adjacent-original.png", "sha256": file_digest(adjacent_file),
                "width": 200, "height": 300, "reading_order": 1, "external_refs": {"resource_index": 5},
                "reference_quality": "MODEL_VISUAL_DEVELOPMENT_REVIEW"}
    source = {"schema_version": "b-source-trial/0.1", "artifact_id": "synthetic-source-manifest", "book_id": book,
              "scope_id": scope, "assets": [asset]}
    context = {"schema_version": "b-context-trial/0.1", "artifact_id": "synthetic-context", "book_id": book, "scope_id": scope,
               "pages": {asset["asset_id"]: {"sha256": asset["sha256"], "role": "answer",
                   "windows": [{"column": 1, "y_range": [250, 300], "path": path}]}}}
    location = {"column": 1, "window_index": 0, "section_path": path}
    raw = [{"line_id": "source-page/ocr/0", "text": "9.解：如图1，继续", "score": .9, "bbox": [110, 260, 190, 272],
            "location": copy.deepcopy(location)},
           {"line_id": "source-page/ocr/1", "text": "图1", "score": .9, "bbox": [130, 288, 150, 298],
            "location": copy.deepcopy(location)}]
    evidence = _document("b-evidence-trial/0.2", "EvidenceBundleTrial",
        {"pages": [{"asset_id": asset["asset_id"], "source": asset, "page_role": "answer",
                    "layout": {"mode": "two_columns", "cut_x": 100}, "ocr_lines": raw,
                    "answer_detail_lines": [], "unscoped_line_ids": []}], "context": context,
         "history_annotations_consumed": False, "quality_decision": "NOT_EVALUATED"}, book=book, scope=scope)
    graph = offline.assemble(evidence)
    window = {"column": 0, "y_range": [0, 70], "path": path}
    next_path = ["Synthetic chapter", "下一节"]
    hard_window = {"column": 0, "y_range": [70, 100], "path": next_path}
    target_lines = []
    for i, (text, box, window_index) in enumerate([
            ("如图2，接着计算", [10, 10, 90, 22], 0), ("B", [25, 28, 35, 38], 0),
            ("图2", [35, 48, 55, 58], 0), ("下一节", [10, 75, 70, 87], 1)]):
        target_lines.append({"line_id": "target-page/ocr/"+str(i), "text": text, "score": .9, "bbox": box,
            "engine_bbox": list(box), "location": {"column": 0, "window_index": window_index,
                                                    "section_path": path if window_index == 0 else next_path}})
    captures = []
    for aid, original, source_asset, box, filename in (
            ("source-page", source_image, asset, [100, 250, 200, 300], "source-capture.png"),
            ("target-page", target_image, adjacent, [0, 0, 100, 100], "target-capture.png")):
        capture = original.crop(box)
        capture.save(root / filename)
        captures.append({"asset_id": aid, "source_sha256": source_asset["sha256"], "source_size": [200, 300],
            "path": filename, "source_bbox": box, "sha256": file_digest(root / filename),
            "rgb_sha256": hashlib.sha256(capture.tobytes()).hexdigest(), "source_mapping": "SYNTHETIC_TEST exact PNG crop"})
    crop = {"path": captures[1]["path"], "source_bbox": [0, 0, 100, 100], "sha256": captures[1]["sha256"],
            "width": 100, "height": 100, "ocr_scale": 1, "crop_to_original": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
    fixture = _document("b-continuation-fixture-trial/0.1", "ContinuationEvidenceFixtureTrial",
        {"source": adjacent, "acquisition_receipt": {"method": "GET", "status": 200, "sha256": adjacent["sha256"],
            "width": 200, "height": 300, "requested_url": "synthetic://not-a-network-request", "execution_kind": "SYNTHETIC_TEST"},
         "crop": crop, "ocr_lines": target_lines, "reviewed_scope": {"from_asset_id": asset["asset_id"],
            "from_asset_sha256": asset["sha256"], "from_resource_index": 4, "section_path": path,
            "window": window, "hard_boundary_window": hard_window, "figure_labels": ["B", "图2"],
            "reference_quality": "MODEL_VISUAL_DEVELOPMENT_REVIEW", "basis": "SYNTHETIC_TEST explicit open-tail/prefix fixture"}},
        book=book, scope=scope, inputs=[reference(evidence)])
    regions = []
    for index, (cap, search, required, caption) in enumerate([
            (captures[0], [120, 274, 170, 300], ["source-page/ocr/1"], "source-page/ocr/1"),
            (captures[1], [15, 25, 80, 63], ["target-page/ocr/1", "target-page/ocr/2"], "target-page/ocr/2")], 1):
        with Image.open(root / cap["path"]) as image: witness = ink_witness(image.convert("RGB"), cap, search)
        regions.append({"region_id": "synthetic-figure-"+str(index), "asset_id": cap["asset_id"],
            "figure_number": str(index), "search_bbox": search, "section_path": path, "printed_number": "9",
            "required_line_ids": required, "caption_ref": caption, "ink_witness": witness})
    image_review = _document("b-image-review-trial/0.1", "ImageRegionReviewTrial",
        {"captures": captures, "regions": regions, "reference_quality": "MODEL_VISUAL_DEVELOPMENT_REVIEW", "business_acceptance": False},
        book=book, scope=expanded, inputs=[{"asset_id": c["asset_id"], "sha256": c["source_sha256"]} for c in captures])
    line = target_lines[-1]
    basis = {"kind": "EXPLICIT_SOURCE_REVIEW", "reference_quality": "MODEL_VISUAL_DEVELOPMENT_REVIEW",
             "reason": "SYNTHETIC_TEST single observed next-section heading"}
    boundary = _document("b-boundary-review-trial/0.1", "SyntheticBoundaryReviewTrial",
        {"asset": {key: adjacent[key] for key in ("asset_id", "sha256", "width", "height")},
         "window_index": 1, "window_snapshot": hard_window, "source_bbox": [5, 70, 80, 95],
         "line_spans": [{"line_id": line["line_id"], "text_span": [0, len(line["text"])]}],
         "members": [{"line_id": line["line_id"], "text_span": [0, len(line["text"])], "raw_text": line["text"],
             "raw_text_sha256": hashlib.sha256(line["text"].encode()).hexdigest(), "bbox": line["bbox"]}],
         "expected_title": "下一节", "review_basis": basis}, book=book, scope=expanded, inputs=[reference(fixture)])
    content_review = _document("b-continuation-content-review-trial/0.1", "ContinuationContentReviewTrial",
        {"asset": {key: adjacent[key] for key in ("asset_id", "sha256", "width", "height")},
         "capture": {key: crop[key] for key in ("path", "sha256", "source_bbox", "width", "height")},
         "line_checks": [], "reference_quality": "MODEL_VISUAL_DEVELOPMENT_REVIEW", "human_verified": False,
         "transcription_verified": False, "business_acceptance": False, "platform_actions": [],
         "review_method": "SYNTHETIC_TEST empty development comparison; never source transcription gold", "limitations": []},
        book=book, scope=expanded, inputs=[reference(fixture), {"asset_id": adjacent["asset_id"], "sha256": adjacent["sha256"]},
                                        {"crop_sha256": crop["sha256"]}])
    review = {"schema_version": "b-review-trial/0.1", "artifact_id": "synthetic-review", "book_id": book,
              "scope_id": scope, "reference_quality": "SYNTHETIC_TEST", "question_census": {}, "answer_checks": []}
    package = {"schema_version": "b-continuation-package-trial/0.1", "artifact_id": "synthetic-continuation-package",
        "book_id": book, "scope_id": scope, "extended_scope_id": expanded, "policy": POLICY, "printed_number": "9",
        "documents": {}, "captures": captures, "adjacent_source": adjacent,
        "reviewed_source_answer": source_answer_snapshot(evidence, graph, asset_id=asset["asset_id"], section_path=path, printed_number="9")}
    documents = {"continuation_fixture": fixture, "image_review": image_review, "boundary_review": boundary, "content_review": content_review}
    for name, document in documents.items():
        filename = name+".json"
        write(root / filename, document)
        package["documents"][name] = {"path": filename, "text_sha256": hashlib.sha256((root / filename).read_text(encoding="utf-8").encode()).hexdigest(),
                                       "artifact_ref": reference(document)}
    values = {"source": source, "context": context, "review": review, "evidence": evidence, "graph": graph, "package": package}
    for name, value in values.items(): write(root / (name+".json"), value)
    return {**values, "documents": documents, **{name+"_path": root / (name+".json") for name in values},
            "adjacent_source_path": adjacent_file}


class ContinuationStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = make_continuation_fixture(self.root)

    def args(self):
        return self.data["package_path"], self.data["source_path"], self.data["adjacent_source_path"]

    def prepare(self, evidence=None, graph=None):
        return prepare_continuation_scope(evidence or self.data["evidence"], graph or self.data["graph"], *self.args())

    def test_generated_sources_prepare_proof_apply_and_exact_rollback(self):
        snapshot = copy.deepcopy(self.data)
        scope = self.prepare()
        proof = build_continuation_stage_proof(scope, *self.args())
        applied = apply_continuation_stage(scope, proof, *self.args())
        self.assertTrue(applied["payload"]["application_check"]["payload"]["accepted"])
        evidence, base = scope["payload"]["evidence"], scope["payload"]["graph"]
        graph = applied["payload"]["graph"]
        self.assertEqual(rollback_continuation(evidence, graph,
            expected_graph_ref=applied["payload"]["application_receipt"]["payload"]["derived_graph_ref"]), base)
        self.assertEqual(graph["payload"]["answers"][0]["text"].count("图"), 2)
        self.assertEqual(self.data, snapshot)

    def test_scope_preserves_every_original_entity_and_archive_without_new_time(self):
        scope = self.prepare()
        p = scope["payload"]
        self.assertEqual(p["base_evidence_archive"], self.data["evidence"])
        self.assertEqual(p["base_graph_archive"], self.data["graph"])
        self.assertEqual(p["evidence"]["payload"]["pages"][:-1], self.data["evidence"]["payload"]["pages"])
        for key in ("questions", "answers", "issues", "unmatched_answer_ids"):
            self.assertEqual(p["graph"]["payload"][key], self.data["graph"]["payload"][key])
        self.assertEqual(p["graph"]["payload"]["answer_coverage"][:-4], self.data["graph"]["payload"]["answer_coverage"])
        for value in (scope, p["evidence"], p["graph"]): self.assertNotIn("created_at", value)
        self.assertFalse(p["source_scope"]["full_page_ocr_claimed"])
        self.assertEqual(p["source_scope"]["observed_asset_count"], 2)
        self.assertEqual(p["evidence"]["payload"]["context"]["scope_id"], scope["scope_id"])
        self.assertNotEqual(p["evidence"]["payload"]["context"]["artifact_id"], self.data["context"]["artifact_id"])

    def test_any_reviewed_raw_object_change_is_rejected_after_consistent_reassembly(self):
        for field, value in (("score", .91), ("text", "9.解：changed")):
            with self.subTest(field=field):
                evidence = copy.deepcopy(self.data["evidence"])
                evidence["payload"]["pages"][0]["ocr_lines"][0][field] = value
                evidence["content_hash"] = digest(evidence["payload"])
                with self.assertRaisesRegex(ValueError, "reviewed OCR/span snapshot"):
                    self.prepare(evidence, offline.assemble(evidence))

    def test_unrelated_evidence_can_change_but_requires_the_complete_matching_graph(self):
        evidence = copy.deepcopy(self.data["evidence"])
        line = copy.deepcopy(evidence["payload"]["pages"][0]["ocr_lines"][0])
        line.update(line_id="source-page/ocr/earlier", text="8.答：3", bbox=[110, 250, 150, 258])
        evidence["payload"]["pages"][0]["ocr_lines"].insert(0, line)
        evidence["content_hash"] = digest(evidence["payload"])
        scope = self.prepare(evidence, offline.assemble(evidence))
        self.assertEqual(len(scope["payload"]["graph"]["payload"]["answers"]), 2)
        with self.assertRaisesRegex(ValueError, "complete current-evidence assembly"):
            self.prepare(evidence, self.data["graph"])

    def test_graph_edits_and_stale_evidence_refs_are_not_partial_match_exceptions(self):
        for field in ("payload", "input_refs"):
            with self.subTest(field=field):
                graph = copy.deepcopy(self.data["graph"])
                if field == "payload": graph["payload"]["answers"][0]["text"] = "edited"
                else: graph["input_refs"][0]["artifact_id"] = "stale"
                graph["content_hash"] = digest(graph["payload"])
                with self.assertRaisesRegex(ValueError, "complete current-evidence assembly"): self.prepare(graph=graph)

    def test_unknown_adjacent_original_and_changed_bytes_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "explicit local adjacent"):
            load_continuation_package(self.data["package_path"], self.data["source_path"], None)
        self.data["adjacent_source_path"].write_bytes(b"changed original")
        with self.assertRaisesRegex(ValueError, "adjacent original SHA"): self.prepare()

    def test_rehashed_capture_substitution_cannot_replace_original_pixels(self):
        capture = self.data["documents"]["image_review"]["payload"]["captures"][0]
        filename = self.root / capture["path"]
        with Image.open(filename) as image: size = image.size
        white = Image.new("RGB", size, "white")
        white.save(filename)
        capture["sha256"] = file_digest(filename)
        capture["rgb_sha256"] = hashlib.sha256(white.tobytes()).hexdigest()
        refresh_package(self.data)
        with self.assertRaisesRegex(ValueError, "original source pixels"): self.prepare()

    def test_document_paths_are_package_relative_even_when_documents_are_nested(self):
        (self.root / "documents").mkdir()
        for name, descriptor in self.data["package"]["documents"].items():
            descriptor["path"] = "documents/"+name+".json"
        # An unrelated false crop under the document directory must never be read.
        Image.new("RGB", (100, 100), "black").save(self.root / "documents/target-capture.png")
        refresh_package(self.data)
        scope = self.prepare()
        proof = build_continuation_stage_proof(scope, *self.args())
        self.assertTrue(apply_continuation_stage(scope, proof, *self.args())["payload"]["application_check"]["payload"]["accepted"])

    def test_escape_unknown_policy_and_unknown_documents_are_refused(self):
        baseline = copy.deepcopy(self.data["package"])
        for kind in ("escape", "policy", "extra"):
            with self.subTest(kind=kind):
                value = copy.deepcopy(baseline)
                if kind == "escape": value["documents"]["image_review"]["path"] = "../outside.json"
                elif kind == "policy": value["policy"] = "MATCH_PAGE_SHA_ONLY"
                else: value["documents"]["old_proof"] = value["documents"]["image_review"]
                write(self.data["package_path"], value)
                with self.assertRaises(ValueError): self.prepare()

    def test_lf_crlf_changes_runtime_bytes_but_not_new_business_artifacts(self):
        paths = [self.data["package_path"], self.data["source_path"]]+[
            self.root / d["path"] for d in self.data["package"]["documents"].values()]
        for path in paths: path.write_bytes(path.read_text(encoding="utf-8").encode())
        before = load_continuation_package(*self.args())["receipt"]
        first = self.prepare()
        first_proof = build_continuation_stage_proof(first, *self.args())
        first_apply = apply_continuation_stage(first, first_proof, *self.args())
        for path in paths: path.write_bytes(path.read_text(encoding="utf-8").replace("\n", "\r\n").encode())
        after = load_continuation_package(*self.args())["receipt"]
        second = self.prepare()
        second_proof = build_continuation_stage_proof(second, *self.args())
        second_apply = apply_continuation_stage(second, second_proof, *self.args())
        self.assertNotEqual(before["package"]["file_sha256"], after["package"]["file_sha256"])
        self.assertNotEqual(before["source"]["file_sha256"], after["source"]["file_sha256"])
        self.assertEqual(first, second)
        self.assertEqual(first_proof, second_proof)
        self.assertEqual(first_apply, second_apply)
        self.assertEqual(before["captures"], after["captures"])

    def test_scope_and_proof_edits_do_not_survive_rehashing(self):
        scope = self.prepare()
        proof = build_continuation_stage_proof(scope, *self.args())
        damaged = copy.deepcopy(scope)
        damaged["payload"]["graph"]["payload"]["answers"][0]["text"] = "changed"
        damaged["content_hash"] = digest(damaged["payload"])
        with self.assertRaisesRegex(ValueError, "exact current-input projection"):
            build_continuation_stage_proof(damaged, *self.args())
        damaged = copy.deepcopy(proof)
        damaged["payload"]["proof"]["payload"]["source_tail_line_id"] = "different"
        damaged["content_hash"] = digest(damaged["payload"])
        with self.assertRaisesRegex(ValueError, "proof-stage artifact is stale or changed"):
            apply_continuation_stage(scope, damaged, *self.args())

    def test_already_extended_input_is_not_extended_again(self):
        scope = self.prepare()
        with self.assertRaises(ValueError): self.prepare(scope["payload"]["evidence"], scope["payload"]["graph"])

    def test_external_receipt_rejects_coordinated_later_edit(self):
        scope = self.prepare()
        proof = build_continuation_stage_proof(scope, *self.args())
        applied = apply_continuation_stage(scope, proof, *self.args())["payload"]
        changed = copy.deepcopy(applied["graph"])
        changed["payload"]["subsequent_edit"] = "must not discard"
        changed["content_hash"] = digest(changed["payload"])
        changed["rollback_guard"]["expected_payload_hash"] = changed["content_hash"]
        changed["artifact_id"] = _graph_id(changed)
        with self.assertRaisesRegex(ValueError, "independently retained version"):
            rollback_continuation(scope["payload"]["evidence"], changed,
                expected_graph_ref=applied["application_receipt"]["payload"]["derived_graph_ref"])

    def test_content_reference_is_pixel_bound_and_never_rewrites_recognition(self):
        review = self.data["documents"]["content_review"]
        line = self.data["documents"]["continuation_fixture"]["payload"]["ocr_lines"][0]
        region = [8, 8, 92, 24]
        with Image.open(self.data["adjacent_source_path"]) as image:
            rgb_sha = hashlib.sha256(image.convert("RGB").crop(region).tobytes()).hexdigest()
        case = {"case_id": "synthetic-raw-difference", "asset_id": "target-page",
            "source_sha256": self.data["package"]["adjacent_source"]["sha256"], "line_id": line["line_id"],
            "raw_text": line["text"], "raw_text_sha256": hashlib.sha256(line["text"].encode()).hexdigest(),
            "line_bbox": line["bbox"], "review_region_bbox": region, "review_region_rgb_sha256": rgb_sha,
            "observed_text": "SYNTHETIC_TEST comparison only, never recognize this string",
            "differences": [{"kind": "SYNTHETIC_TEST", "raw_fragment": line["text"][0:1], "raw_text_span": [0, 1],
                             "observed_source_fragment": "comparison"}],
            "reference_quality": "MODEL_VISUAL_DEVELOPMENT_REVIEW", "human_verified": False, "business_acceptance": False}
        review["payload"]["line_checks"] = [case]
        refresh_package(self.data)
        scope = self.prepare()
        proof = build_continuation_stage_proof(scope, *self.args())
        graph = apply_continuation_stage(scope, proof, *self.args())["payload"]["graph"]
        self.assertNotIn("comparison only", graph["payload"]["answers"][0]["text"])
        case["review_region_rgb_sha256"] = "0"*64
        refresh_package(self.data)
        with self.assertRaisesRegex(ValueError, "content review line, pixel region"): self.prepare()


if __name__ == "__main__": unittest.main()
