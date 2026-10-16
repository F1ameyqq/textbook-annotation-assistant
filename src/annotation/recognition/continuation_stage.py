"""Current-reference, source-bound continuation stages; no OCR or platform I/O.

The package contains historical observations, never an executable old proof.
Every stage checks the original images and exact capture pixels. Preparation
preserves all current entities; proof construction binds their current IDs;
application produces a separately audited graph and an external rollback ref.
Execution times belong to the orchestration journal, not these new identities.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

from PIL import Image

from . import offline
from .baseline import code_digest, digest, file_digest, load_source, valid_bbox
from .boundary import build_boundary_candidate, validate_boundary
from .continuation import build_adjacency_receipt, build_continuation_proof, validate_continuation
from .continuation_apply import apply_continuation, rollback_continuation
from .continuation_quality import audit_continuation_application
from .image_regions import build_image_regions, validate_image_regions

PACKAGE_SCHEMA = "b-continuation-package-trial/0.1"
SCOPE_SCHEMA = "b-continuation-scope-trial/0.1"
PROOF_STAGE_SCHEMA = "b-continuation-proof-stage-trial/0.1"
APPLY_STAGE_SCHEMA = "b-continuation-apply-stage-trial/0.1"
POLICY = "CURRENT_REFERENCE_REBUILD_ONLY/0.1"
IDENTITY_POLICY = "CURRENT_REFS_WITH_EXECUTION_TIME_IN_JOURNAL/0.1"
CONTENT_POLICY = "NORMALIZED_TEXT_CONTENT/0.1"
PREFIX_COVERAGE = "SOURCE_PREFIX_CROP_ONLY_WITH_BOUNDARY_AND_FIGURES"


def reference(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def _text(path):
    value = Path(path).read_text(encoding="utf-8")
    return value, hashlib.sha256(value.encode("utf-8")).hexdigest()


def _path(root, relative):
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or PurePosixPath(relative).is_absolute() or PureWindowsPath(relative).drive
            or ".." in PurePosixPath(relative).parts):
        raise ValueError("continuation paths must be portable and stay inside the package")
    value = (root / relative).resolve()
    if not value.is_relative_to(root.resolve()) or not value.is_file():
        raise ValueError("missing continuation package file or escaping symlink")
    return value


def _rgb(image):
    return hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()


def _checked(value, schemas, kind=None):
    offline.check_artifact(value, set(schemas))
    if (not isinstance(value.get("artifact_id"), str) or not value["artifact_id"]
            or (kind is not None and value.get("kind") != kind)):
        raise ValueError("invalid continuation artifact identity or kind")


def _producer(operation):
    dependencies = ("baseline", "offline", "answer_assembly", "policy", "continuation", "continuation_apply",
                    "continuation_quality", "image_regions", "boundary")
    return {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
            "dependency_code_sha256": {name: code_digest(Path(__file__).with_name(name+".py")) for name in dependencies},
            "operation": operation, "policy": POLICY, "identity_policy": IDENTITY_POLICY,
            "new_ocr_calls": 0, "website_requests": 0}


def _envelope(schema, kind, payload, inputs, *, book_id, scope_id, run_id, operation, revision=1, **extra):
    body = {"schema_version": schema, "kind": kind, "revision": revision, "book_id": book_id,
            "scope_id": scope_id, "run_id": run_id, "input_refs": copy.deepcopy(inputs),
            "producer": _producer(operation), "payload": payload, **extra}
    return {**body, "artifact_id": kind.lower()+"-"+digest(body)[:24], "content_hash": digest(payload)}


def _common():
    return {"decision": "HOLD", "transcription_verified": False, "business_acceptance": False,
            "new_ocr_calls": 0, "website_requests": 0, "platform_actions": []}


def content_receipt(receipt):
    """Keep normalized JSON identities and every original/capture binary hash."""
    result = copy.deepcopy(receipt)
    for name in ("package", "source"): result[name].pop("file_sha256")
    for value in result["documents"].values(): value.pop("file_sha256")
    result["receipt_policy"] = CONTENT_POLICY
    return result


def source_answer_snapshot(evidence, graph, *, asset_id, section_path, printed_number):
    """Freeze source objects; only evidence-version-dependent fragment IDs vary."""
    candidates = [a for a in graph["payload"]["answers"] if a["asset_id"] == asset_id
                  and a["section_path"] == section_path and a["printed_number"] == printed_number]
    if len(candidates) != 1:
        raise ValueError("reviewed source answer is missing or ambiguous")
    answer = candidates[0]
    page = next(p for p in evidence["payload"]["pages"] if p["asset_id"] == asset_id)
    lines = {line["line_id"]: line for line in page["ocr_lines"]}
    ids = answer["source_line_ids"]
    if not ids or len(ids) != len(set(ids)) or any(key not in lines for key in ids):
        raise ValueError("reviewed source answer has no unique raw parent lines")
    return {"asset_id": asset_id, "section_path": copy.deepcopy(section_path), "printed_number": printed_number,
            "anchor_ref": ids[0], "source_line_ids": list(ids), "source_tail_line_id": ids[-1],
            "raw_lines": [copy.deepcopy(lines[key]) for key in ids],
            "fragments": [{key: copy.deepcopy(value) for key, value in fragment.items() if key != "fragment_id"}
                          for fragment in answer["fragments"]],
            "assembly_status": answer["assembly_status"], "boundary": copy.deepcopy(answer["boundary"])}


def _validate_content_lineage(content, base_inputs, original):
    """Permit explicit development-observation corrections, never raw edits.

    The complete previous review is embedded so the package's document receipt
    covers it. No historical filename is resolved and no observation is treated
    as a human transcription or used to choose continuation source lines.
    """
    revision, payload = content["revision"], content["payload"]
    if revision == 1:
        if content.get("input_refs") != base_inputs or "lineage" in payload:
            raise ValueError("original content review references or lineage changed")
        return
    if revision != 2:
        raise ValueError("unsupported content review correction revision")
    lineage = payload.get("lineage")
    if (not isinstance(lineage, dict)
            or set(lineage) != {"supersedes_ref", "previous_review_archive", "reason", "changes"}
            or not isinstance(lineage.get("reason"), str) or not lineage["reason"].strip()):
        raise ValueError("content review correction requires explicit lineage and reason")
    old = lineage["previous_review_archive"]
    if not isinstance(old, dict) or not isinstance(old.get("payload"), dict):
        raise ValueError("content review correction requires a complete previous archive")
    _checked(old, {"b-continuation-content-review-trial/0.1"}, "ContinuationContentReviewTrial")
    if (old.get("revision") != 1 or any(old.get(k) != content.get(k) for k in ("book_id", "scope_id"))
            or old.get("input_refs") != base_inputs or "lineage" in old["payload"]
            or reference(old) != lineage["supersedes_ref"]
            or content.get("input_refs") != base_inputs+[reference(old)]):
        raise ValueError("content review correction archive or exact prior references changed")
    expected = copy.deepcopy(old["payload"])
    changes = lineage["changes"]
    if not isinstance(changes, list) or not changes:
        raise ValueError("content review correction needs named changes")
    case_lists = [expected.get("line_checks"), payload.get("line_checks")]
    if any(not isinstance(cases, list) or any(not isinstance(case, dict) or not isinstance(case.get("case_id"), str)
            or not case["case_id"] for case in cases) for cases in case_lists):
        raise ValueError("content review correction has invalid case identities")
    old_cases, new_cases = [{case["case_id"]: case for case in cases} for cases in case_lists]
    if any(len(cases) != len(index) for cases, index in zip(case_lists, (old_cases, new_cases))):
        raise ValueError("content review correction has duplicate cases")
    seen = set()
    for change in changes:
        if not isinstance(change, dict):
            raise ValueError("invalid content review change")
        case_id = change.get("case_id")
        if (set(change) != {"case_id", "changed_fields", "reason", "source_geometry_witness"}
                or not isinstance(case_id, str) or case_id in seen or case_id not in old_cases or case_id not in new_cases
                or change.get("changed_fields") != ["observed_text", "differences"]
                or not isinstance(change.get("reason"), str) or not change["reason"].strip()
                or all(old_cases[case_id].get(field) == new_cases[case_id].get(field) for field in change["changed_fields"])):
            raise ValueError("content review correction may change only named observations and differences")
        for field in change["changed_fields"]:
            old_cases[case_id][field] = copy.deepcopy(new_cases[case_id].get(field))
        witness = change["source_geometry_witness"]
        witness_keys = {"source_region_bbox", "source_region_rgb_sha256", "raised_component_bbox", "raised_component_rgb_sha256",
                        "body_digit_bbox", "body_digit_rgb_sha256", "threshold", "interpretation", "human_verified"}
        if (not isinstance(witness, dict) or set(witness) != witness_keys or witness.get("human_verified") is not False
                or type(witness.get("threshold")) is not int or not 0 < witness["threshold"] < 256
                or not isinstance(witness.get("interpretation"), str) or not witness["interpretation"].strip()):
            raise ValueError("content review correction witness cannot verify a symbol")
        region, reviewed = witness["source_region_bbox"], new_cases[case_id].get("review_region_bbox")
        if (not isinstance(region, list) or not valid_bbox(region, *original.size)
                or not isinstance(reviewed, list) or not valid_bbox(reviewed, *original.size)
                or not (reviewed[0] <= region[0] < region[2] <= reviewed[2]
                        and reviewed[1] <= region[1] < region[3] <= reviewed[3])):
            raise ValueError("content review correction witness is outside its reviewed source row")
        for prefix in ("source_region", "raised_component", "body_digit"):
            box = witness[prefix+"_bbox"]
            if (not isinstance(box, list) or not valid_bbox(box, *original.size) or any(type(v) is not int for v in box)
                    or not (region[0] <= box[0] < box[2] <= region[2] and region[1] <= box[1] < box[3] <= region[3])
                    or _rgb(original.crop(box)) != witness[prefix+"_rgb_sha256"]):
                raise ValueError("content review correction witness differs from original pixels")
        raised, body = witness["raised_component_bbox"], witness["body_digit_bbox"]
        if not (raised[0] >= body[0] and raised[1] < body[1] and raised[3] < body[3]):
            raise ValueError("content review correction raised-right geometry is inconsistent")
        seen.add(case_id)
    expected["lineage"] = copy.deepcopy(lineage)
    if payload != expected:
        raise ValueError("content review correction changed unlisted raw, source, pixel or verification fields")


def load_continuation_package(package_path, source_path, adjacent_source_path):
    """Validate all declared originals, captures, normalized documents and OCR.

    Document and capture paths are interpreted at the manifest root, even when
    JSON documents are nested. The adjacent original is mandatory and explicit;
    historical GET URLs are data only and never used to retrieve anything.
    """
    if adjacent_source_path is None:
        raise ValueError("continuation requires an explicit local adjacent original")
    package_path, source_path = Path(package_path), Path(source_path)
    raw, text_sha = _text(package_path)
    manifest = json.loads(raw)
    source, source_paths = load_source(source_path)
    keys = {"schema_version", "artifact_id", "book_id", "scope_id", "extended_scope_id", "policy",
            "printed_number", "documents", "captures", "adjacent_source", "reviewed_source_answer"}
    names = ("continuation_fixture", "image_review", "boundary_review", "content_review")
    if (set(manifest) != keys or manifest.get("schema_version") != PACKAGE_SCHEMA or manifest.get("policy") != POLICY
            or not isinstance(manifest.get("artifact_id"), str) or not manifest["artifact_id"]
            or (manifest.get("book_id"), manifest.get("scope_id")) != (source["book_id"], source["scope_id"])
            or not isinstance(manifest.get("extended_scope_id"), str) or not manifest["extended_scope_id"]
            or manifest["extended_scope_id"] == manifest["scope_id"]
            or not isinstance(manifest.get("printed_number"), str) or not re.fullmatch(r"[1-9]\d?", manifest["printed_number"])
            or not isinstance(manifest.get("documents"), dict) or set(manifest["documents"]) != set(names)):
        raise ValueError("invalid continuation manifest, scope, number or policy")
    schemas = ("b-continuation-fixture-trial/0.1", "b-image-review-trial/0.1", "b-boundary-review-trial/0.1",
               "b-continuation-content-review-trial/0.1")
    documents, receipts = {}, {}
    for name, schema in zip(names, schemas):
        descriptor = manifest["documents"][name]
        if set(descriptor) != {"path", "text_sha256", "artifact_ref"}:
            raise ValueError("invalid continuation document descriptor")
        path = _path(package_path.parent, descriptor["path"])
        raw, sha = _text(path)
        document = json.loads(raw)
        _checked(document, {schema})
        if (sha != descriptor["text_sha256"] or reference(document) != descriptor["artifact_ref"]
                or document.get("book_id") != source["book_id"]):
            raise ValueError("continuation document content, reference or book changed")
        documents[name] = document
        receipts[name] = {**copy.deepcopy(descriptor), "file_sha256": file_digest(path)}
    fixture, image_review, boundary_review, content_review = [documents[name] for name in names]
    data, reviewed = fixture["payload"], fixture["payload"]["reviewed_scope"]
    adjacent = data["source"]
    if (fixture.get("scope_id") != source["scope_id"]
            or image_review.get("scope_id") != manifest["extended_scope_id"]
            or manifest["adjacent_source"] != adjacent or manifest["captures"] != image_review["payload"]["captures"]
            or adjacent["asset_id"] in {a["asset_id"] for a in source["assets"]}
            or adjacent["reading_order"] != max(a["reading_order"] for a in source["assets"])+1
            or "viewer_page" in adjacent.get("external_refs", {})):
        raise ValueError("continuation package scope, capture list or adjacent asset changed")
    if (fixture.get("kind") != "ContinuationEvidenceFixtureTrial" or image_review.get("kind") != "ImageRegionReviewTrial"
            or boundary_review.get("input_refs") != [reference(fixture)]
            or image_review.get("input_refs") != [{"asset_id": c["asset_id"], "sha256": c["source_sha256"]} for c in manifest["captures"]]):
        raise ValueError("continuation review documents do not retain their exact source references")
    previous = [a for a in source["assets"] if a["asset_id"] == reviewed["from_asset_id"]]
    if (len(previous) != 1 or previous[0]["sha256"] != reviewed["from_asset_sha256"]
            or previous[0].get("external_refs", {}).get("resource_index") != reviewed["from_resource_index"]
            or type(reviewed["from_resource_index"]) is not int
            or adjacent.get("external_refs", {}).get("resource_index") != reviewed["from_resource_index"]+1):
        raise ValueError("continuation observed resource adjacency changed")
    acquisition = data["acquisition_receipt"]
    if (acquisition.get("method") != "GET" or acquisition.get("status") != 200
            or any(acquisition.get(key) != adjacent.get(key) for key in ("sha256", "width", "height"))):
        raise ValueError("invalid retained acquisition receipt")
    originals = {}
    for asset, path in source_paths:
        with Image.open(path) as image: originals[asset["asset_id"]] = (asset, image.convert("RGB"))
    adjacent_source_path = Path(adjacent_source_path)
    if file_digest(adjacent_source_path) != adjacent["sha256"]:
        raise ValueError("adjacent original SHA changed")
    with Image.open(adjacent_source_path) as image:
        if image.size != (adjacent["width"], adjacent["height"]):
            raise ValueError("adjacent original dimensions changed")
        originals[adjacent["asset_id"]] = (adjacent, image.convert("RGB"))
    captures, seen_assets, seen_paths = [], set(), set()
    for capture in manifest["captures"]:
        aid, box = capture["asset_id"], capture["source_bbox"]
        if aid in seen_assets or capture["path"] in seen_paths or aid not in originals:
            raise ValueError("duplicate or unknown continuation capture")
        seen_assets.add(aid); seen_paths.add(capture["path"])
        asset, original = originals[aid]
        path = _path(package_path.parent, capture["path"])
        if (capture["source_sha256"] != asset["sha256"] or capture["source_size"] != [asset["width"], asset["height"]]
                or not valid_bbox(box, asset["width"], asset["height"]) or any(type(v) is not int for v in box)
                or file_digest(path) != capture["sha256"]):
            raise ValueError("continuation capture source, geometry or bytes changed")
        with Image.open(path) as image: crop = image.convert("RGB")
        expected = original.crop(box)
        if crop.size != expected.size or crop.tobytes() != expected.tobytes() or _rgb(crop) != capture["rgb_sha256"]:
            raise ValueError("continuation capture does not equal original source pixels")
        captures.append({"asset_id": aid, "path": capture["path"], "file_sha256": file_digest(path),
                         "source_sha256": asset["sha256"], "source_bbox": list(box), "source_size": list(original.size),
                         "rgb_sha256": _rgb(crop), "source_crop_rgb_sha256": _rgb(expected), "crop_size": list(crop.size)})
    if seen_assets != {reviewed["from_asset_id"], adjacent["asset_id"]}:
        raise ValueError("continuation requires both reviewed source and adjacent captures")
    crop = data["crop"]
    crop_path = _path(package_path.parent, crop["path"])
    box, scale = crop["source_bbox"], crop["ocr_scale"]
    if (not valid_bbox(box, adjacent["width"], adjacent["height"]) or any(type(v) is not int for v in box)
            or type(scale) not in (int, float) or not math.isfinite(scale) or scale <= 0
            or crop["crop_to_original"] != [[1/scale, 0, box[0]], [0, 1/scale, box[1]], [0, 0, 1]]
            or [box[2]-box[0], box[3]-box[1]] != [crop["width"], crop["height"]]
            or file_digest(crop_path) != crop["sha256"]
            or not any(c["asset_id"] == adjacent["asset_id"] and c["path"] == crop["path"]
                       and c["source_bbox"] == box and c["file_sha256"] == crop["sha256"] for c in captures)):
        raise ValueError("continuation OCR crop identity or transform changed")
    seen = set()
    for line in data["ocr_lines"]:
        lid = line["line_id"]
        transformed = [round(line["engine_bbox"][k]/scale+box[k % 2], 3) for k in range(4)]
        if (not isinstance(lid, str) or not lid or lid in seen or not isinstance(line.get("text"), str) or not line["text"]
                or not valid_bbox(line["bbox"], adjacent["width"], adjacent["height"]) or line["bbox"] != transformed
                or not (box[0] <= line["bbox"][0] < line["bbox"][2] <= box[2]
                        and box[1] <= line["bbox"][1] < line["bbox"][3] <= box[3])):
            raise ValueError("continuation OCR identity or source geometry changed")
        seen.add(lid)
    # Development text is only a downstream quality reference. It never
    # participates in choosing a source answer, proof lines or replacement OCR.
    cr = content_review["payload"]
    base_review_inputs = [reference(fixture), {"asset_id": adjacent["asset_id"], "sha256": adjacent["sha256"]},
                          {"crop_sha256": crop["sha256"]}]
    _validate_content_lineage(content_review, base_review_inputs, originals[adjacent["asset_id"]][1])
    asset_ref = {key: adjacent[key] for key in ("asset_id", "sha256", "width", "height")}
    capture_ref = {key: crop[key] for key in ("path", "sha256", "source_bbox", "width", "height")}
    if (content_review.get("kind") != "ContinuationContentReviewTrial" or content_review.get("scope_id") != manifest["extended_scope_id"]
            or cr.get("asset") != asset_ref or cr.get("capture") != capture_ref
            or cr.get("reference_quality") != "MODEL_VISUAL_DEVELOPMENT_REVIEW"
            or any(cr.get(key) is not False for key in ("human_verified", "transcription_verified", "business_acceptance"))
            or cr.get("platform_actions") != [] or not isinstance(cr.get("line_checks"), list)):
        raise ValueError("continuation content-review source or unverified status changed")
    raw_lines = {line["line_id"]: line for line in data["ocr_lines"]}
    cases, reviewed_ids = set(), set()
    for case in cr["line_checks"]:
        line = raw_lines.get(case.get("line_id"))
        if line is None:
            raise ValueError("content review names an unknown original OCR line")
        region = [max(box[0], math.floor(line["bbox"][0])-2), max(box[1], math.floor(line["bbox"][1])-2),
                  min(box[2], math.ceil(line["bbox"][2])+2), min(box[3], math.ceil(line["bbox"][3])+2)]
        if (not isinstance(case.get("case_id"), str) or not case["case_id"] or case["case_id"] in cases
                or line["line_id"] in reviewed_ids or line["location"]["window_index"] != 0
                or case.get("asset_id") != adjacent["asset_id"] or case.get("source_sha256") != adjacent["sha256"]
                or case.get("raw_text") != line["text"] or case.get("line_bbox") != line["bbox"]
                or case.get("raw_text_sha256") != hashlib.sha256(line["text"].encode()).hexdigest()
                or case.get("review_region_bbox") != region
                or case.get("review_region_rgb_sha256") != _rgb(originals[adjacent["asset_id"]][1].crop(region))
                or case.get("reference_quality") != "MODEL_VISUAL_DEVELOPMENT_REVIEW"
                or case.get("human_verified") is not False or case.get("business_acceptance") is not False
                or not isinstance(case.get("observed_text"), str) or not case["observed_text"]
                or not isinstance(case.get("differences"), list) or not case["differences"]):
            raise ValueError("content review line, pixel region or unverified provenance changed")
        cases.add(case["case_id"]); reviewed_ids.add(line["line_id"])
        for difference in case["differences"]:
            span = difference.get("raw_text_span")
            if (not isinstance(span, list) or len(span) != 2 or any(type(v) is not int for v in span)
                    or not 0 <= span[0] < span[1] <= len(line["text"])
                    or difference.get("raw_fragment") != line["text"][span[0]:span[1]]
                    or not isinstance(difference.get("observed_source_fragment"), str) or not difference["observed_source_fragment"]
                    or not isinstance(difference.get("kind"), str) or not difference["kind"]):
                raise ValueError("content review difference does not preserve the exact raw OCR span")
    snapshot = manifest["reviewed_source_answer"]
    if (snapshot.get("asset_id") != reviewed["from_asset_id"] or snapshot.get("section_path") != reviewed["section_path"]
            or snapshot.get("printed_number") != manifest["printed_number"] or snapshot.get("assembly_status") != "OPEN"
            or snapshot.get("boundary", {}).get("kind") != "ANSWER_PAGE_EDGE"):
        raise ValueError("reviewed source-answer snapshot is not an explicit open page tail")
    source_text, source_text_sha = _text(source_path)
    receipt = {"book_id": manifest["book_id"], "scope_id": manifest["scope_id"], "extended_scope_id": manifest["extended_scope_id"],
               "package": {"file_sha256": file_digest(package_path), "text_sha256": text_sha,
                            "reference": {"artifact_id": manifest["artifact_id"], "content_hash": digest(manifest)}},
               "documents": receipts,
               "source": {"file_sha256": file_digest(source_path), "text_sha256": source_text_sha,
                          "reference": {"artifact_id": source["artifact_id"], "content_hash": digest(source)}},
               "source_assets": sorted(source["assets"], key=lambda a: a["reading_order"]),
               "adjacent_source": {"file_sha256": file_digest(adjacent_source_path), "asset": copy.deepcopy(adjacent)},
               "captures": captures}
    return {"manifest": manifest, "documents": documents, "receipt": receipt}


def _base(evidence, graph, package, source_path):
    _checked(evidence, {"b-evidence-trial/0.2", "b-evidence-trial/0.3"}, "EvidenceBundleTrial")
    _checked(graph, {"b-graph-trial/0.2", "b-graph-trial/0.3"}, "QuestionGraphTrial")
    source, _ = load_source(Path(source_path))
    offline.validate_context(source, evidence["payload"]["context"])
    if ((evidence["book_id"], evidence["scope_id"]) != (source["book_id"], source["scope_id"])
            or [p["source"] for p in evidence["payload"]["pages"]] != package["receipt"]["source_assets"]
            or "continuation_scope_extension" in evidence["payload"]
            or evidence["payload"].get("history_annotations_consumed") is not False):
        raise ValueError("current evidence does not match the complete original source scope")
    seen = set()
    for page in evidence["payload"]["pages"]:
        asset = page["source"]
        context_page = evidence["payload"]["context"]["pages"][asset["asset_id"]]
        raw_ids = {line.get("line_id") for line in page["ocr_lines"]}
        if page["asset_id"] != asset["asset_id"] or page["page_role"] != context_page["role"]:
            raise ValueError("current evidence page identity or role changed")
        for line in page["ocr_lines"]+page.get("answer_detail_lines", []):
            lid, location = line.get("line_id"), line.get("location")
            if (not isinstance(lid, str) or not lid or lid in seen or not isinstance(line.get("text"), str)
                    or not valid_bbox(line.get("bbox", []), asset["width"], asset["height"])
                    or ("parent_line_id" in line and line["parent_line_id"] not in raw_ids)):
                raise ValueError("current raw/detail OCR provenance or geometry changed")
            seen.add(lid)
            if location is not None:
                index = location.get("window_index")
                windows = context_page["windows"]
                if (type(index) is not int or not 0 <= index < len(windows)
                        or location.get("column") != windows[index]["column"] or location.get("section_path") != windows[index]["path"]):
                    raise ValueError("current OCR location no longer matches its complete context")
    for value in (evidence, graph):
        if (value["payload"].get("platform_actions", []) != [] or value["payload"].get("business_acceptance", False) is not False
                or value["payload"].get("transcription_verified", False) is not False):
            raise ValueError("continuation input falsely claims verification or platform actions")
    expected = offline.assemble(evidence)
    if (graph["payload"] != expected["payload"] or graph.get("input_refs") != [reference(evidence)]
            or graph["schema_version"] != expected["schema_version"]
            or (graph["book_id"], graph["scope_id"]) != (evidence["book_id"], evidence["scope_id"])):
        raise ValueError("current graph must equal the complete current-evidence assembly, not a partial match")
    selector = package["manifest"]["reviewed_source_answer"]
    actual = source_answer_snapshot(evidence, graph, **{key: selector[key] for key in ("asset_id", "section_path", "printed_number")})
    if actual != selector:
        raise ValueError("current source answer differs from the complete reviewed OCR/span snapshot")


def prepare_continuation_scope(evidence, graph, package_path, source_path, adjacent_source_path):
    package = load_continuation_package(package_path, source_path, adjacent_source_path)
    _base(evidence, graph, package, source_path)
    manifest, docs = package["manifest"], package["documents"]
    fixture = docs["continuation_fixture"]
    data, reviewed = fixture["payload"], fixture["payload"]["reviewed_scope"]
    adjacent = data["source"]
    existing = {l["line_id"] for p in evidence["payload"]["pages"] for l in p["ocr_lines"]+p.get("answer_detail_lines", [])}
    if any(l["line_id"] in existing for l in data["ocr_lines"]):
        raise ValueError("continuation OCR IDs collide with original evidence")
    package_ref = package["receipt"]["package"]["reference"]
    run_id = "b-continuation-run-"+digest([reference(evidence), reference(graph), package_ref])[:24]
    scope = manifest["extended_scope_id"]
    ep = copy.deepcopy(evidence["payload"])
    windows = [reviewed["window"], reviewed["hard_boundary_window"]]
    ep["pages"].append({"asset_id": adjacent["asset_id"], "source": copy.deepcopy(adjacent), "page_role": "answer",
        "layout": {"mode": "two_columns", "cut_x": adjacent["width"]/2, "method": "REVIEWED_PREFIX_CROP_ONLY", "verified": False},
        "ocr_lines": copy.deepcopy(data["ocr_lines"]), "answer_detail_lines": [], "unscoped_line_ids": [],
        "coverage_scope": PREFIX_COVERAGE, "crop_provenance": copy.deepcopy(data["crop"])})
    context = ep["context"]
    context["artifact_id"] = "continuation-context-"+digest([
        {"artifact_id": context["artifact_id"], "content_hash": digest(context)}, reference(fixture), scope])[:24]
    context["scope_id"] = scope
    context["pages"][adjacent["asset_id"]] = {"sha256": adjacent["sha256"], "role": "answer", "windows": copy.deepcopy(windows)}
    ep["continuation_scope_extension"] = {"fixture_ref": reference(fixture), "package_ref": package_ref,
        "original_page_count": len(evidence["payload"]["pages"]), "new_asset_id": adjacent["asset_id"],
        "base_evidence_ref": reference(evidence), "base_graph_ref": reference(graph), "coverage_scope": PREFIX_COVERAGE,
        "scope": "Actual adjacent resource prefix only; full-page OCR and viewer mapping are not asserted."}
    e6 = _envelope("b-evidence-trial/0.3", "EvidenceBundleTrial", ep,
        [reference(evidence), reference(graph), reference(fixture), package_ref], book_id=evidence["book_id"], scope_id=scope,
        run_id=run_id, operation="PREPARE_EVIDENCE_SCOPE", revision=evidence["revision"]+1)
    gp = copy.deepcopy(graph["payload"])
    for line in data["ocr_lines"]:
        body = line["location"]["window_index"] == 0
        gp["answer_coverage"].append({"asset_id": adjacent["asset_id"], "line_id": line["line_id"],
            "status": "UNASSIGNED" if body else "EXCLUDED", "answer_ids": [], "fragment_ids": [], "allocations": [],
            "reason": "REVIEWED_CROSS_PAGE_PREFIX_PENDING_PROOF" if body else "OBSERVED_NEXT_SECTION_HEADING"})
    gp["continuation_scope_extension"] = {"fixture_ref": reference(fixture), "package_ref": package_ref,
        "original_entities_preserved": True, "graph_merge_performed": False}
    g6 = _envelope("b-graph-trial/0.3", "QuestionGraphTrial", gp, [reference(e6)], book_id=evidence["book_id"],
        scope_id=scope, run_id=run_id, operation="PREPARE_GRAPH_SCOPE", revision=graph["revision"]+1,
        derivation_refs=[reference(graph), reference(fixture), package_ref])
    source_scope = {"base_scope_id": evidence["scope_id"], "extended_scope_id": scope,
        "base_source_ref": package["receipt"]["source"]["reference"], "base_assets": copy.deepcopy(package["receipt"]["source_assets"]),
        "adjacent_asset": copy.deepcopy(adjacent), "base_page_count": len(evidence["payload"]["pages"]),
        "observed_asset_count": len(ep["pages"]), "adjacent_ocr_coverage": PREFIX_COVERAGE,
        "adjacent_crop_bbox": copy.deepcopy(data["crop"]["source_bbox"]), "full_page_ocr_claimed": False}
    payload = {"evidence": e6, "graph": g6, "base_evidence_ref": reference(evidence), "base_graph_ref": reference(graph),
        "base_evidence_archive": copy.deepcopy(evidence), "base_graph_archive": copy.deepcopy(graph),
        "package_receipt": content_receipt(package["receipt"]), "source_scope": source_scope, **_common()}
    return _envelope(SCOPE_SCHEMA, "ContinuationScopeTrial", payload, [reference(evidence), reference(graph), package_ref],
        book_id=evidence["book_id"], scope_id=scope, run_id=run_id, operation="PREPARE_SCOPE")


def _validated_scope(scope, package_path, source_path, adjacent_source_path):
    _checked(scope, {SCOPE_SCHEMA}, "ContinuationScopeTrial")
    payload = scope["payload"]
    expected = prepare_continuation_scope(payload["base_evidence_archive"], payload["base_graph_archive"],
        package_path, source_path, adjacent_source_path)
    if scope != expected:
        raise ValueError("continuation scope result differs from the exact current-input projection")
    return load_continuation_package(package_path, source_path, adjacent_source_path)


def build_continuation_stage_proof(scope, package_path, source_path, adjacent_source_path):
    package = _validated_scope(scope, package_path, source_path, adjacent_source_path)
    docs = package["documents"]
    evidence, graph = scope["payload"]["evidence"], scope["payload"]["graph"]
    data = docs["continuation_fixture"]["payload"]
    reviewed, snapshot = data["reviewed_scope"], package["manifest"]["reviewed_source_answer"]
    answer = next(a for a in graph["payload"]["answers"] if a["asset_id"] == snapshot["asset_id"]
                  and a["section_path"] == snapshot["section_path"] and a["printed_number"] == snapshot["printed_number"])
    adjacency = build_adjacency_receipt(evidence, snapshot["asset_id"], data["source"]["asset_id"],
        observation_refs=["retained-anonymous-GET-receipt:"+digest(data["acquisition_receipt"]),
                          "reviewed-resource-map:"+digest([reviewed["from_asset_id"], data["source"]])],
        reference_quality=reviewed["reference_quality"])
    images = build_image_regions(evidence, docs["image_review"], Path(package_path).parent)
    image_check = validate_image_regions(evidence, images, docs["image_review"], Path(package_path).parent)
    h = docs["boundary_review"]["payload"]
    page = next(p for p in evidence["payload"]["pages"] if p["asset_id"] == h["asset"]["asset_id"])
    source = page["source"]
    if h["asset"] != {key: source[key] for key in ("asset_id", "sha256", "width", "height")}:
        raise ValueError("boundary source asset changed")
    lines = {line["line_id"]: line for line in page["ocr_lines"]}
    for member in h["members"]:
        line = lines[member["line_id"]]
        if (line["text"] != member["raw_text"] or line["bbox"] != member["bbox"]
                or hashlib.sha256(line["text"].encode()).hexdigest() != member["raw_text_sha256"]):
            raise ValueError("frozen boundary OCR source changed")
    boundary = build_boundary_candidate(evidence, asset_id=h["asset"]["asset_id"], line_spans=h["line_spans"],
        source_bbox=h["source_bbox"], review_basis=h["review_basis"])
    boundary_check = validate_boundary(evidence, boundary)
    prefix = sorted((line for line in data["ocr_lines"] if line["location"]["window_index"] == 0),
                    key=lambda line: (line["bbox"][1], line["bbox"][0], line["line_id"]))
    proof = build_continuation_proof(evidence, graph, from_answer_id=answer["answer_id"], to_asset_id=data["source"]["asset_id"],
        to_line_ids=[line["line_id"] for line in prefix], source_tail_line_id=snapshot["source_tail_line_id"], adjacency_receipt=adjacency,
        review_basis={"kind": "EXPLICIT_SOURCE_REVIEW", "reference_quality": reviewed["reference_quality"],
            "source_tail_open": True, "target_prefix_unanchored": True, "source_tail_line_id": snapshot["source_tail_line_id"],
            "reason": reviewed["basis"]}, image_regions=images, boundary_candidate=boundary)
    check = validate_continuation(evidence, graph, proof, image_review=docs["image_review"], capture_root=Path(package_path).parent)
    if not all(value["payload"].get("accepted") is True for value in (image_check, boundary_check, check)):
        raise ValueError("current continuation proof was rejected by source/image/boundary checks: "+
                         ",".join(item["code"] for item in check["payload"]["issues"]))
    payload = {"scope_ref": reference(scope), "evidence_ref": reference(evidence), "graph_ref": reference(graph),
        "package_receipt": content_receipt(package["receipt"]), "source_scope": copy.deepcopy(scope["payload"]["source_scope"]),
        "adjacency_receipt": adjacency, "image_regions": images, "image_check": image_check,
        "boundary_candidate": boundary, "boundary_check": boundary_check, "proof": proof, "continuation_check": check, **_common()}
    return _envelope(PROOF_STAGE_SCHEMA, "ContinuationProofStageTrial", payload,
        [reference(scope), reference(evidence), reference(graph), package["receipt"]["package"]["reference"]],
        book_id=evidence["book_id"], scope_id=evidence["scope_id"], run_id=evidence["run_id"], operation="REBUILD_PROOF")


def apply_continuation_stage(scope, proof_stage, package_path, source_path, adjacent_source_path):
    package = _validated_scope(scope, package_path, source_path, adjacent_source_path)
    _checked(proof_stage, {PROOF_STAGE_SCHEMA}, "ContinuationProofStageTrial")
    expected = build_continuation_stage_proof(scope, package_path, source_path, adjacent_source_path)
    if proof_stage != expected:
        raise ValueError("continuation proof-stage artifact is stale or changed")
    evidence, base = scope["payload"]["evidence"], scope["payload"]["graph"]
    proof, review = proof_stage["payload"]["proof"], package["documents"]["image_review"]
    graph = apply_continuation(evidence, base, proof, image_review=review, capture_root=Path(package_path).parent)
    graph.pop("created_at", None)
    check = audit_continuation_application(evidence, base, graph, proof, image_review=review, capture_root=Path(package_path).parent)
    if check["payload"].get("accepted") is not True:
        raise ValueError("local continuation application failed independent audit")
    receipt_payload = {"evidence_ref": reference(evidence), "base_graph_ref": reference(base),
        "derived_graph_ref": reference(graph), "proof_ref": reference(proof), "decision": "HOLD", "platform_actions": []}
    receipt = {"schema_version": "b-continuation-application-receipt-trial/0.1", "kind": "LocalContinuationApplicationReceiptTrial",
        "artifact_id": "local-application-receipt-"+digest(receipt_payload)[:24], "revision": 1,
        "book_id": evidence["book_id"], "scope_id": evidence["scope_id"], "content_hash": digest(receipt_payload), "payload": receipt_payload}
    restored = rollback_continuation(evidence, graph, expected_graph_ref=receipt_payload["derived_graph_ref"])
    if restored != base:
        raise ValueError("rollback did not restore the exact current extended base graph")
    payload = {"scope_ref": reference(scope), "proof_stage_ref": reference(proof_stage), "evidence_ref": reference(evidence),
        "base_graph_ref": reference(base), "graph": graph, "application_receipt": receipt, "application_check": check,
        "rollback_verification": {"restored_equals_original": True, "restored_graph_ref": reference(restored),
                                  "restored_complete_object_sha256": digest(restored)},
        "package_receipt": content_receipt(package["receipt"]), "source_scope": copy.deepcopy(scope["payload"]["source_scope"]), **_common()}
    return _envelope(APPLY_STAGE_SCHEMA, "ContinuationApplyStageTrial", payload,
        [reference(scope), reference(proof_stage), package["receipt"]["package"]["reference"]],
        book_id=evidence["book_id"], scope_id=evidence["scope_id"], run_id=evidence["run_id"], operation="APPLY_LOCAL")
