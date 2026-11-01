"""Replay the real resource-172 -> resource-173 continuation proposal offline.

No network, OCR model, graph merge, or platform action is performed. The saved
RapidOCR crop includes all visible diagram labels and the following heading.
The original adjacent full image can optionally be checked against its GET
receipt; without it, replay verifies the committed crop and evidence only.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image
from annotation.recognition.baseline import code_digest, digest, file_digest, valid_bbox
from annotation.recognition.continuation import (
    build_adjacency_receipt, build_continuation_proof, validate_continuation)
from annotation.recognition.offline import assemble, check_artifact, ref

FIXTURE_SCHEMA = "b-continuation-fixture-trial/0.1"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_continuation_fixture(path, adjacent_source=None):
    path = Path(path)
    fixture = load_json(path)
    check_artifact(fixture, {FIXTURE_SCHEMA})
    data = fixture["payload"]
    source, acquisition, crop = data["source"], data["acquisition_receipt"], data["crop"]
    if (acquisition.get("method") != "GET" or acquisition.get("status") != 200
            or any(acquisition.get(key) != source.get(key) for key in ("sha256", "width", "height"))
            or "viewer_page" in source.get("external_refs", {})):
        raise ValueError("invalid source acquisition binding or unverified viewer mapping asserted")
    relative = crop["path"]
    if (not isinstance(relative, str) or "\\" in relative or PurePosixPath(relative).is_absolute()
            or PureWindowsPath(relative).drive or ".." in PurePosixPath(relative).parts):
        raise ValueError("crop path must stay within the fixture package")
    crop_path = (path.parent / relative).resolve()
    if not crop_path.is_relative_to(path.parent.resolve()) or not crop_path.is_file():
        raise ValueError("crop asset is missing or outside fixture")
    if file_digest(crop_path) != crop["sha256"]:
        raise ValueError("crop asset hash mismatch")
    with Image.open(crop_path) as image:
        if image.size != (crop["width"], crop["height"]):
            raise ValueError("crop asset dimensions mismatch")
    box = crop["source_bbox"]
    scale = crop["ocr_scale"]
    if (not valid_bbox(box, source["width"], source["height"])
            or [box[2]-box[0], box[3]-box[1]] != [crop["width"], crop["height"]]
            or type(scale) not in (int, float) or scale <= 0
            or crop["crop_to_original"] != [[1/scale,0,box[0]],[0,1/scale,box[1]],[0,0,1]]):
        raise ValueError("crop transform is inconsistent")
    ids = []
    for line in data["ocr_lines"]:
        ids.append(line["line_id"])
        transformed = [round(line["engine_bbox"][k] / scale + box[k % 2], 3) for k in range(4)]
        if line["bbox"] != transformed or not valid_bbox(line["bbox"], source["width"], source["height"]):
            raise ValueError("OCR line transform mismatch")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate continuation OCR line IDs")
    body_labels = {line["text"].strip() for line in data["ocr_lines"] if line["location"]["window_index"] == 0}
    if not all(label in body_labels for label in data["reviewed_scope"]["figure_labels"]):
        raise ValueError("reviewed diagram labels missing from OCR evidence")
    if not any("回顾与思考" in line["text"] for line in data["ocr_lines"]
               if line["location"]["window_index"] == 1):
        raise ValueError("observed heading boundary missing")
    original_validation = "NOT_RECHECKED_CACHED_CROP_REPLAY"
    if adjacent_source is not None:
        original = Path(adjacent_source)
        if file_digest(original) != source["sha256"]:
            raise ValueError("adjacent original source hash mismatch")
        with Image.open(original) as image:
            if image.size != (source["width"], source["height"]):
                raise ValueError("adjacent original source dimensions mismatch")
            expected = image.convert("RGB").crop(box)
            with Image.open(crop_path) as saved:
                if expected.tobytes() != saved.convert("RGB").tobytes():
                    raise ValueError("saved crop does not match the bound original image")
        original_validation = "ORIGINAL_BYTES_AND_CROP_PIXELS_RECHECKED"
    return fixture, original_validation


def prepare_continuation(evidence, graph, fixture):
    """Extend only the observed source scope, preserving every original entity.

    The new page contains a reviewed prefix crop, not full-page OCR. Existing
    question/answer/fragment IDs and texts stay unchanged. Target prefix lines
    remain UNASSIGNED until a later reviewed graph change; this function only
    builds the separate continuation proposal and its check result.
    """
    check_artifact(evidence, {"b-evidence-trial/0.2", "b-evidence-trial/0.3"})
    check_artifact(graph, {"b-graph-trial/0.2", "b-graph-trial/0.3"})
    check_artifact(fixture, {FIXTURE_SCHEMA})
    if (graph["book_id"], graph["scope_id"], graph["input_refs"]) != (
            evidence["book_id"], evidence["scope_id"], [ref(evidence)]):
        raise ValueError("base graph does not match evidence revision")
    data, reviewed = fixture["payload"], fixture["payload"]["reviewed_scope"]
    if fixture["book_id"] != evidence["book_id"]:
        raise ValueError("continuation fixture book mismatch")
    pages = {page["asset_id"]: page for page in evidence["payload"]["pages"]}
    previous = pages.get(reviewed["from_asset_id"])
    if (not previous or previous["source"]["sha256"] != reviewed["from_asset_sha256"]
            or previous["source"].get("external_refs", {}).get("resource_index") != reviewed["from_resource_index"]):
        raise ValueError("base source asset identity differs from reviewed continuation")
    new_source = data["source"]
    if new_source["asset_id"] in pages:
        raise ValueError("adjacent resource already exists; do not append it twice")
    candidates = [a for a in graph["payload"]["answers"]
                  if a["asset_id"] == reviewed["from_asset_id"]
                  and a["section_path"] == reviewed["section_path"] and a["printed_number"] == "9"]
    if len(candidates) != 1:
        raise ValueError("reviewed reflection Q9 source answer missing or ambiguous")
    source_answer = candidates[0]
    producer = {"module": "tools.verify_continuation_b", "version": "0.1.0",
                "code_sha256": code_digest(Path(__file__)), "ocr_replayed_not_rerun": True,
                "history_annotations_consumed": False}
    extended = copy.deepcopy(evidence)
    extended["schema_version"] = "b-evidence-trial/0.3"
    extended["revision"] += 1
    extended["scope_id"] += "+adjacent-resource-173-prefix"
    extended["run_id"] = "b-continuation-run-" + digest([ref(evidence), ref(graph), ref(fixture)])[:24]
    extended["input_refs"] = [ref(evidence), ref(fixture)]
    extended["producer"] = producer
    extended["created_at"] = datetime.now(timezone.utc).isoformat()
    windows = [reviewed["window"], reviewed["hard_boundary_window"]]
    extended["payload"]["pages"].append({
        "asset_id": new_source["asset_id"], "source": copy.deepcopy(new_source), "page_role": "answer",
        "layout": {"mode": "two_columns", "cut_x": new_source["width"] / 2,
                   "method": "REVIEWED_PREFIX_CROP_ONLY", "verified": False},
        "ocr_lines": copy.deepcopy(data["ocr_lines"]), "answer_detail_lines": [], "unscoped_line_ids": [],
        "coverage_scope": "SOURCE_PREFIX_CROP_ONLY_WITH_BOUNDARY_AND_FIGURES",
        "crop_provenance": copy.deepcopy(data["crop"])})
    extended["payload"]["context"]["pages"][new_source["asset_id"]] = {
        "sha256": new_source["sha256"], "role": "answer", "windows": copy.deepcopy(windows)}
    extended["payload"]["continuation_scope_extension"] = {
        "fixture_ref": ref(fixture), "original_page_count": len(pages), "new_asset_id": new_source["asset_id"],
        "scope": "Actual adjacent resource prefix only; full-page OCR and viewer mapping are not asserted."}
    extended["content_hash"] = digest(extended["payload"])
    derived_graph = copy.deepcopy(graph)
    derived_graph["schema_version"] = "b-graph-trial/0.3"
    derived_graph["revision"] += 1
    derived_graph["scope_id"], derived_graph["run_id"] = extended["scope_id"], extended["run_id"]
    derived_graph["input_refs"] = [ref(extended)]
    derived_graph["derivation_refs"] = [ref(graph), ref(fixture)]
    derived_graph["producer"] = producer
    derived_graph["created_at"] = extended["created_at"]
    for line in data["ocr_lines"]:
        body = line["location"]["window_index"] == 0
        derived_graph["payload"]["answer_coverage"].append({
            "asset_id": new_source["asset_id"], "line_id": line["line_id"],
            "status": "UNASSIGNED" if body else "EXCLUDED", "answer_ids": [], "fragment_ids": [], "allocations": [],
            "reason": "REVIEWED_CROSS_PAGE_PREFIX_PENDING_PROOF" if body else "OBSERVED_NEXT_SECTION_HEADING"})
    derived_graph["payload"]["continuation_scope_extension"] = {
        "fixture_ref": ref(fixture), "original_entities_preserved": True, "graph_merge_performed": False}
    derived_graph["content_hash"] = digest(derived_graph["payload"])
    receipt = build_adjacency_receipt(extended, reviewed["from_asset_id"], new_source["asset_id"],
        observation_refs=["retained-anonymous-GET-receipt:" + digest(data["acquisition_receipt"]),
                          "reviewed-resource-map:" + digest([previous["source"], new_source])],
        reference_quality=reviewed["reference_quality"])
    prefix = sorted((line for line in data["ocr_lines"] if line["location"]["window_index"] == 0),
                    key=lambda line: (line["bbox"][1], line["bbox"][0], line["line_id"]))
    tail = source_answer["source_line_ids"][-1]
    proof = build_continuation_proof(extended, derived_graph,
        from_answer_id=source_answer["answer_id"], to_asset_id=new_source["asset_id"],
        to_line_ids=[line["line_id"] for line in prefix], source_tail_line_id=tail, adjacency_receipt=receipt,
        review_basis={"kind": "EXPLICIT_SOURCE_REVIEW", "reference_quality": reviewed["reference_quality"],
            "source_tail_open": True, "target_prefix_unanchored": True, "source_tail_line_id": tail,
            "reason": reviewed["basis"]})
    report = validate_continuation(extended, derived_graph, proof)
    return {"evidence": extended, "graph": derived_graph, "adjacency_receipt": receipt,
            "proof": proof, "report": report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=ROOT / "tests/fixtures/book46007447/continuation-evidence.json")
    parser.add_argument("--evidence", type=Path, default=ROOT / "tests/fixtures/book46007447/ocr-evidence.json")
    parser.add_argument("--graph", type=Path, help="optional matching base graph; otherwise assemble cached base OCR")
    parser.add_argument("--adjacent-source", type=Path, help="optional original resource-173 image to recheck bytes and crop pixels")
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new directory")
    try:
        fixture, original_check = load_continuation_fixture(args.fixture, args.adjacent_source)
        evidence = load_json(args.evidence)
        graph = load_json(args.graph) if args.graph else assemble(evidence)
        results = prepare_continuation(evidence, graph, fixture)
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    args.out.mkdir(parents=True)
    names = {"evidence": "continuation-evidence-six-assets.json", "graph": "question-graph-source-extension.json",
             "adjacency_receipt": "source-adjacency-receipt.json", "proof": "continuation-proof.json",
             "report": "continuation-check.json"}
    for key, value in results.items():
        (args.out / names[key]).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    report = results["report"]["payload"]
    summary = {"book_id": evidence["book_id"], "source_assets": len(results["evidence"]["payload"]["pages"]),
               "new_ocr_lines": len(fixture["payload"]["ocr_lines"]),
               "prefix_lines": len(results["proof"]["payload"]["to_line_ids"]),
               "status": report["status"], "decision": report["decision"], "accepted": report["accepted"],
               "issue_codes": sorted({issue["code"] for issue in report["issues"]}),
               "original_source_validation": original_check, "ocr_rerun": False,
               "graph_merge_performed": False, "platform_actions": 0,
               "viewer_page_mapping": "UNKNOWN_FOR_RESOURCE_173"}
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
