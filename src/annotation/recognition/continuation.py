"""Validate explicit cross-page continuation proposals without applying them.

This B trial module does not infer continuity from printed question numbers or
reading-order adjacency. A caller supplies a source-bound mapping receipt and an
explicit review of an open tail and an unanchored prefix. The validator checks
those claims against the current evidence, graph, page resources, and ownership.
Even a structurally accepted proposal remains HOLD / UNVERIFIED; no graph or
website is changed. Synthetic receipts are always labelled synthetic.
"""
from __future__ import annotations

import copy
import hashlib
import re

from .baseline import digest, valid_bbox
from .boundary import validate_boundary
from .image_regions import validate_image_regions

RECEIPT_SCHEMA = "b-page-adjacency-trial/0.1"
PROOF_SCHEMA = "b-continuation-proof-trial/0.1"
PROOF_SCHEMA_WITH_REGIONS = "b-continuation-proof-trial/0.2"
REPORT_SCHEMA = "b-continuation-check-trial/0.1"
EVIDENCE_SCHEMAS = {"b-evidence-trial/0.2", "b-evidence-trial/0.3"}
GRAPH_SCHEMAS = {"b-graph-trial/0.2", "b-graph-trial/0.3"}
QUALITIES = {"SYNTHETIC_TEST", "MODEL_VISUAL_DEVELOPMENT_REVIEW", "HUMAN_REVIEWED"}
PRIMARY = re.compile(r"^\s*\d{1,2}\s*[.．、]\s*\S")
BOUNDARY = re.compile(r"^(?:[A-C]?(?:基础题|中档题|综合题)|参考答案|回顾与思考|第[一二三四五六七八九十\d]+章|第\d+课时|小专题|☆?问题解决策略)")


def _ref(artifact):
    return {key: artifact.get(key) for key in ("artifact_id", "revision", "content_hash")}


def _artifact(schema, kind, evidence, payload, inputs):
    content_hash = digest(payload)
    return {"schema_version": schema, "kind": kind,
            "artifact_id": kind.lower() + "-" + digest([schema, inputs, payload])[:24],
            "revision": 1, "book_id": evidence.get("book_id"),
            "scope_id": evidence.get("scope_id"), "run_id": evidence.get("run_id"),
            "input_refs": copy.deepcopy(inputs), "content_hash": content_hash,
            "payload": copy.deepcopy(payload),
            "producer": {"module": __name__, "version": "0.1.0"}}


def _manifest_hash(evidence):
    return digest([page.get("source") for page in evidence.get("payload", {}).get("pages", [])])


def _asset_snapshot(page, requested_id=None):
    source = page.get("source", {}) if page else {}
    return {"asset_id": page.get("asset_id") if page else requested_id,
            "sha256": source.get("sha256"), "width": source.get("width"),
            "height": source.get("height"),
            "resource_index": source.get("external_refs", {}).get("resource_index")}


def _line_snapshot(line):
    return {"line_id": line.get("line_id"), "raw_text_sha256": hashlib.sha256(line.get("text", "").encode("utf-8")).hexdigest(),
            "bbox": copy.deepcopy(line.get("bbox")), "location": copy.deepcopy(line.get("location"))}


def _report(evidence, graph, proof, issues, plan=None, quality=None):
    accepted = not issues
    payload = {"accepted": accepted, "status": "VALIDATED_PROPOSAL" if accepted else "REJECTED",
               "decision": "HOLD", "issues": issues, "verified_plan": plan,
               "reference_quality": quality, "business_acceptance": False,
               "reason": "Version-bound structural proposal only; no graph merge or platform action was performed."}
    return _artifact(REPORT_SCHEMA, "ContinuationCheckTrial", evidence, payload,
                     [_ref(evidence), _ref(graph), _ref(proof)])


def build_adjacency_receipt(evidence, from_asset_id, to_asset_id, *, observation_refs,
                            reference_quality):
    """Bind observed resource mappings, not a caller's ``confirmed=True`` flag.

    ``observation_refs`` identifies the retained mapping observation (for example
    an API-response digest). The current evidence must independently carry those
    exact asset/hash/resource-index mappings in its source descriptors. This
    builder records missing assets too, so validation can report them gracefully.
    """
    pages = {p.get("asset_id"): p for p in evidence.get("payload", {}).get("pages", [])}
    payload = {"basis": "OBSERVED_RESOURCE_INDEX", "book_id": evidence.get("book_id"),
               "source_manifest_hash": _manifest_hash(evidence),
               "from_asset": _asset_snapshot(pages.get(from_asset_id), from_asset_id),
               "to_asset": _asset_snapshot(pages.get(to_asset_id), to_asset_id),
               "observation_refs": copy.deepcopy(observation_refs),
               "reference_quality": reference_quality}
    return _artifact(RECEIPT_SCHEMA, "PageAdjacencyReceiptTrial", evidence, payload, [_ref(evidence)])


def build_continuation_proof(evidence, graph, *, from_answer_id, to_asset_id,
                             to_line_ids, source_tail_line_id, adjacency_receipt,
                             review_basis, image_regions=None, boundary_candidate=None):
    """Create a reviewable proposal; creation itself does not validate it."""
    pages = {p.get("asset_id"): p for p in evidence.get("payload", {}).get("pages", [])}
    answers = graph.get("payload", {}).get("answers", [])
    source = next((a for a in answers if a.get("answer_id") == from_answer_id), {})
    from_asset_id = source.get("asset_id")
    lines = {line.get("line_id"): line for page in pages.values() for line in page.get("ocr_lines", [])}
    payload = {"book_id": evidence.get("book_id"), "section_path": copy.deepcopy(source.get("section_path")),
               "from_answer_id": from_answer_id, "source_tail_line_id": source_tail_line_id,
               "from_asset": _asset_snapshot(pages.get(from_asset_id), from_asset_id),
               "to_asset": _asset_snapshot(pages.get(to_asset_id), to_asset_id),
               "to_line_ids": copy.deepcopy(to_line_ids),
               "line_snapshots": [_line_snapshot(lines[line_id]) for line_id in
                                  [source_tail_line_id] + list(to_line_ids) if line_id in lines],
               "source_fragment_ids": [f.get("fragment_id") for f in source.get("fragments", [])],
               "adjacency_receipt": copy.deepcopy(adjacency_receipt),
               "review_basis": copy.deepcopy(review_basis), "operation": "PROPOSE_ONLY"}
    inputs = [_ref(evidence), _ref(graph), _ref(adjacency_receipt)]
    for key, value in (("image_regions",image_regions),("boundary_candidate",boundary_candidate)):
        if value is not None:
            payload[key]=copy.deepcopy(value)
            inputs.append(_ref(value))
    schema=PROOF_SCHEMA_WITH_REGIONS if image_regions is not None or boundary_candidate is not None else PROOF_SCHEMA
    return _artifact(schema, "ContinuationProofTrial", evidence, payload, inputs)


def validate_continuation(evidence, graph, proof, *, image_review=None, capture_root=None):
    """Return a verified proposal plan or explicit rejection, never mutate input.

    Acceptance means this version-bound proposal passed structural safeguards.
    It is not transcription verification, public-contract acceptance, or a site
    action. The proposed edge carries stable source fragment IDs and individual
    target line regions; it never creates a bounding box spanning two pages.
    """
    issues = []
    evidence = evidence if isinstance(evidence, dict) else {}
    graph = graph if isinstance(graph, dict) else {}
    proof = proof if isinstance(proof, dict) else {}

    def issue(code, detail=None, refs=()):
        issues.append({"code": code, "detail": detail, "evidence_refs": list(refs),
                       "severity": "ERROR", "blocks": ["PRE_APPLY"]})

    def valid_artifact(value, schemas):
        return (isinstance(value, dict) and value.get("schema_version") in schemas
                and type(value.get("revision")) is int and value["revision"] > 0
                and bool(value.get("artifact_id"))
                and isinstance(value.get("payload"), dict)
                and value.get("content_hash") == digest(value.get("payload")))

    if not valid_artifact(evidence, EVIDENCE_SCHEMAS):
        issue("CONTINUATION_EVIDENCE_INVALID")
    if not valid_artifact(graph, GRAPH_SCHEMAS):
        issue("CONTINUATION_GRAPH_INVALID")
    if not valid_artifact(proof, {PROOF_SCHEMA, PROOF_SCHEMA_WITH_REGIONS}):
        issue("CONTINUATION_PROOF_INVALID")
    if issues:
        return _report(evidence, graph, proof, issues)
    data = proof["payload"]
    if any(data.get(key) is not None and not isinstance(data[key],dict) for key in ("image_regions","boundary_candidate")):
        issue("CONTINUATION_SUPPLEMENT_SHAPE_INVALID")
        return _report(evidence,graph,proof,issues)
    if (any(not isinstance(data.get(field), dict) for field in
            ("from_asset", "to_asset", "review_basis", "adjacency_receipt"))
            or not isinstance(data.get("line_snapshots"), list)
            or not isinstance(data.get("source_fragment_ids"), list)):
        issue("CONTINUATION_PROOF_SHAPE_INVALID")
        return _report(evidence, graph, proof, issues)
    receipt = data.get("adjacency_receipt", {})
    if not valid_artifact(receipt, {RECEIPT_SCHEMA}):
        issue("CONTINUATION_ADJACENCY_RECEIPT_INVALID")
        return _report(evidence, graph, proof, issues)
    receipt_data = receipt.get("payload", {}) if isinstance(receipt, dict) else {}
    if (graph.get("book_id"), graph.get("scope_id")) != (evidence.get("book_id"), evidence.get("scope_id")):
        issue("CONTINUATION_GRAPH_SOURCE_MISMATCH")
    if _ref(evidence) not in graph.get("input_refs", []):
        issue("CONTINUATION_GRAPH_EVIDENCE_REVISION_MISMATCH")
    supplements=[data[key] for key in ("image_regions","boundary_candidate") if data.get(key) is not None]
    if supplements and proof.get("schema_version") != PROOF_SCHEMA_WITH_REGIONS:
        issue("CONTINUATION_SUPPLEMENT_SCHEMA_INVALID")
    if proof.get("input_refs") != [_ref(evidence), _ref(graph), _ref(receipt)]+[_ref(s) for s in supplements]:
        issue("CONTINUATION_STALE_PROOF")
    if receipt.get("input_refs") != [_ref(evidence)] or receipt_data.get("source_manifest_hash") != _manifest_hash(evidence):
        issue("CONTINUATION_STALE_MAPPING_RECEIPT")
    if (data.get("book_id") != evidence.get("book_id") or receipt_data.get("book_id") != evidence.get("book_id")
            or proof.get("book_id") != evidence.get("book_id") or receipt.get("book_id") != evidence.get("book_id")):
        issue("CONTINUATION_BOOK_MISMATCH")
    if proof.get("scope_id") != evidence.get("scope_id") or receipt.get("scope_id") != evidence.get("scope_id"):
        issue("CONTINUATION_SCOPE_MISMATCH")
    if data.get("operation") != "PROPOSE_ONLY":
        issue("CONTINUATION_OPERATION_INVALID")

    pages_list = evidence.get("payload", {}).get("pages", [])
    pages = {p.get("asset_id"): p for p in pages_list}
    if len(pages) != len(pages_list):
        issue("CONTINUATION_DUPLICATE_ASSET_ID")
    from_snapshot, to_snapshot = data.get("from_asset", {}), data.get("to_asset", {})
    from_id, to_id = from_snapshot.get("asset_id"), to_snapshot.get("asset_id")
    source_page, target_page = pages.get(from_id), pages.get(to_id)
    if source_page is None:
        issue("CONTINUATION_SOURCE_ASSET_MISSING", from_id)
    if target_page is None:
        issue("CONTINUATION_TARGET_ASSET_MISSING", to_id)
    if from_id == to_id:
        issue("CONTINUATION_REQUIRES_DIFFERENT_PAGES")
    if from_snapshot.get("sha256") and from_snapshot.get("sha256") == to_snapshot.get("sha256"):
        issue("CONTINUATION_DUPLICATE_SOURCE_IMAGE")
    for snapshot, page, label in ((from_snapshot, source_page, "source"), (to_snapshot, target_page, "target")):
        if page:
            if snapshot != _asset_snapshot(page):
                issue("CONTINUATION_ASSET_IDENTITY_MISMATCH", label)
            source = page.get("source", {})
            if (source.get("asset_id") != page.get("asset_id")
                    or not re.fullmatch(r"[0-9a-f]{64}", str(source.get("sha256", "")))
                    or source.get("book_id", evidence.get("book_id")) != evidence.get("book_id")):
                issue("CONTINUATION_ASSET_DESCRIPTOR_INVALID", label)
    if (receipt_data.get("basis") != "OBSERVED_RESOURCE_INDEX"
            or receipt_data.get("from_asset") != from_snapshot or receipt_data.get("to_asset") != to_snapshot
            or not isinstance(receipt_data.get("observation_refs"), list)
            or not receipt_data.get("observation_refs")
            or not all(isinstance(r, str) and r.strip() for r in receipt_data.get("observation_refs", []))):
        issue("CONTINUATION_MAPPING_OBSERVATION_MISMATCH")
    fi, ti = from_snapshot.get("resource_index"), to_snapshot.get("resource_index")
    if type(fi) is not int or type(ti) is not int:
        issue("CONTINUATION_RESOURCE_MAPPING_MISSING")
    elif ti != fi + 1:
        issue("CONTINUATION_SOURCE_PAGE_GAP", {"from_resource_index": fi, "to_resource_index": ti})

    answer_list = graph.get("payload", {}).get("answers", [])
    matching = [a for a in answer_list if a.get("answer_id") == data.get("from_answer_id")]
    answer = matching[0] if len(matching) == 1 else None
    if answer is None:
        issue("CONTINUATION_ANSWER_MISSING_OR_DUPLICATE")
    validated_images, composed_boundary = [], None
    if data.get("image_regions") is not None:
        if image_review is None or capture_root is None:
            issue("CONTINUATION_IMAGE_PIXELS_NOT_RECHECKED")
        else:
            image_check=validate_image_regions(evidence,data["image_regions"],image_review,capture_root)
            if not image_check["payload"]["accepted"]:
                issue("CONTINUATION_IMAGE_EVIDENCE_INVALID",image_check["payload"]["issues"])
            else:
                validated_images=image_check["payload"]["validated_regions"]
                for region in validated_images:
                    if (not answer or region["section_path"] != answer["section_path"]
                            or region["printed_number"] != answer["printed_number"]
                            or region["asset_id"] not in {from_id,to_id}):
                        issue("CONTINUATION_IMAGE_OWNERSHIP_MISMATCH",refs=[region["region_id"]])
    if data.get("boundary_candidate") is not None:
        boundary_check=validate_boundary(evidence,data["boundary_candidate"])
        if not boundary_check["payload"]["accepted"]:
            issue("CONTINUATION_BOUNDARY_EVIDENCE_INVALID",boundary_check["payload"]["issues"])
        else:
            composed_boundary=boundary_check["payload"]["boundary"]
            if composed_boundary["asset"]["asset_id"] != to_id:
                issue("CONTINUATION_BOUNDARY_ASSET_MISMATCH")
    lines = {}
    units = {}
    for page in pages_list:
        for line in page.get("ocr_lines", []):
            if line.get("line_id") in lines:
                issue("CONTINUATION_DUPLICATE_LINE_ID", refs=[line.get("line_id")])
            lines[line.get("line_id")] = (page, line)
        for line in page.get("ocr_lines", []) + page.get("answer_detail_lines", []):
            units[line.get("line_id")] = (page, line)
    requested = data.get("to_line_ids", [])
    if not isinstance(requested, list) or not requested or any(not isinstance(r, str) for r in requested):
        issue("CONTINUATION_TARGET_PREFIX_EMPTY_OR_INVALID")
        requested = []
    if len(requested) != len(set(requested)):
        issue("CONTINUATION_TARGET_LINE_REUSED")
    snapshots = data.get("line_snapshots", [])
    expected_refs = [data.get("source_tail_line_id")] + requested
    expected_snapshots = [_line_snapshot(lines[r][1]) for r in expected_refs if r in lines]
    if snapshots != expected_snapshots or len(expected_snapshots) != len(expected_refs):
        issue("CONTINUATION_LINE_SNAPSHOT_MISMATCH", refs=expected_refs)
    tail_pair = lines.get(data.get("source_tail_line_id"))
    tail = tail_pair[1] if tail_pair else None
    if tail_pair and tail_pair[0].get("asset_id") != from_id:
        issue("CONTINUATION_TAIL_SOURCE_MISMATCH")

    review = data.get("review_basis", {})
    qualities = {review.get("reference_quality"), receipt_data.get("reference_quality")}
    if "HUMAN_REVIEWED" in qualities:
        issue("CONTINUATION_HUMAN_REVIEW_RECEIPT_MISSING",
              "This trial has no independent human-acceptance receipt contract.")
    known_qualities={evidence["payload"].get("context",{}).get("reference_quality")}
    known_qualities.update(p["source"].get("reference_quality") for p in pages_list)
    if "SYNTHETIC_TEST" in known_qualities and qualities != {"SYNTHETIC_TEST"}:
        issue("CONTINUATION_REFERENCE_QUALITY_ESCALATION")
    if (review.get("kind") != "EXPLICIT_SOURCE_REVIEW" or not isinstance(review.get("reason"), str)
            or not review.get("reason", "").strip() or review.get("source_tail_open") is not True
            or review.get("target_prefix_unanchored") is not True
            or review.get("source_tail_line_id") != data.get("source_tail_line_id")
            or not qualities <= QUALITIES):
        issue("CONTINUATION_EXPLICIT_REVIEW_MISSING")

    def ordered(page):
        return sorted((line for line in page.get("ocr_lines", []) if line.get("location")),
                      key=lambda line: (line["location"]["column"], line["bbox"][1], line["bbox"][0], line["line_id"]))

    def window_for(page, line):
        windows = evidence.get("payload", {}).get("context", {}).get("pages", {}).get(page["asset_id"], {}).get("windows", [])
        loc = line.get("location") or {}
        index = loc.get("window_index")
        return windows[index] if type(index) is int and 0 <= index < len(windows) else None

    def window_consistent(page, line):
        window = window_for(page, line)
        loc, box = line.get("location") or {}, line.get("bbox")
        if (not window or not isinstance(box, list)
                or not valid_bbox(box, page["source"]["width"], page["source"]["height"])
                or window.get("path") != loc.get("section_path")
                or window.get("path") != data.get("section_path")
                or window.get("column") != loc.get("column")):
            return False
        lo, hi = window["y_range"]
        cut = page.get("layout", {}).get("cut_x")
        return (lo <= (box[1] + box[3]) / 2 < hi
                and isinstance(cut, (int, float))
                and ((loc.get("column") == 0 and box[2] <= cut)
                     or (loc.get("column") == 1 and box[0] >= cut)))

    canonical_fragment_parent={}
    if answer:
        if (answer.get("book_id") != evidence.get("book_id") or answer.get("asset_id") != from_id
                or answer.get("section_path") != data.get("section_path")):
            issue("CONTINUATION_ANSWER_SOURCE_MISMATCH")
        if (answer.get("assembly_status") != "OPEN"
                or (answer.get("boundary") or {}).get("kind") != "ANSWER_PAGE_EDGE"):
            issue("CONTINUATION_ANSWER_NOT_OPEN_PAGE_TAIL")
        original_ids = [f.get("fragment_id") for f in answer.get("fragments", [])]
        if not original_ids or len(original_ids) != len(set(original_ids)) or data.get("source_fragment_ids") != original_ids:
            issue("CONTINUATION_FRAGMENT_IDENTITY_MISMATCH")
        canonical_parents = []
        for fragment in answer.get("fragments", []):
            refs = fragment.get("evidence_refs", [])
            if not refs:
                issue("CONTINUATION_SOURCE_FRAGMENT_UNBOUND")
            for r in refs:
                pair = units.get(r)
                if not pair:
                    issue("CONTINUATION_SOURCE_FRAGMENT_UNBOUND", refs=[r])
                    continue
                page, line = pair
                parent = line.get("parent_line_id", r)
                canonical_fragment_parent[fragment["fragment_id"]]=parent
                if fragment.get("parent_line_id") != parent:
                    issue("CONTINUATION_SOURCE_PARENT_MISMATCH",refs=[r])
                if parent not in canonical_parents:
                    canonical_parents.append(parent)
                span = fragment.get("text_span", [])
                if (page.get("asset_id") != fragment.get("asset_id") or page.get("page_role") != "answer"
                        or not line.get("location") or line["location"]["section_path"] != answer.get("section_path")
                        or fragment.get("bbox") != line.get("bbox")
                        or not valid_bbox(fragment.get("bbox"), page["source"]["width"], page["source"]["height"])
                        or fragment.get("raw_text") != line.get("text")
                        or not isinstance(span, list) or len(span) != 2
                        or any(type(v) is not int for v in span)
                        or not 0 <= span[0] < span[1] <= len(line["text"])
                        or fragment.get("text") != line["text"][span[0]:span[1]]):
                    issue("CONTINUATION_SOURCE_FRAGMENT_MISMATCH", refs=[r])
        if answer.get("source_line_ids") != canonical_parents:
            issue("CONTINUATION_SOURCE_LEDGER_MISMATCH")
        if not canonical_parents or canonical_parents[-1] != data.get("source_tail_line_id"):
            issue("CONTINUATION_TAIL_NOT_OWNED")
        if not answer.get("source_line_ids") or answer["source_line_ids"][-1] != data.get("source_tail_line_id"):
            issue("CONTINUATION_NON_TAIL_LINE")
        if tail:
            if source_page and not window_consistent(source_page, tail):
                issue("CONTINUATION_SOURCE_WINDOW_INCONSISTENT", refs=[tail["line_id"]])
            if (tail.get("location") or {}).get("section_path") != answer.get("section_path"):
                issue("CONTINUATION_TAIL_SECTION_MISMATCH")
            tail_window = window_for(source_page, tail) if source_page else None
            scoped = ordered(source_page) if source_page else []
            if not scoped or scoped[-1]["line_id"] != tail["line_id"]:
                issue("CONTINUATION_NOT_LAST_VISIBLE_LINE")
            if (not tail_window or tail["location"]["column"] != 1
                    or tail_window["y_range"][1] < source_page["source"]["height"] * .85
                    or tail["bbox"][3] < tail_window["y_range"][1] - max(35, source_page["source"]["height"] * .025)):
                issue("CONTINUATION_SOURCE_EDGE_NOT_PROVEN")
            if re.search(r"[。！？!?]\s*$", tail.get("text", "")):
                issue("CONTINUATION_VISIBLE_TAIL_ALREADY_CLOSED")

    prefix = []
    boundary_ref = None
    if target_page:
        if source_page and (source_page.get("page_role") != "answer" or target_page.get("page_role") != "answer"):
            issue("CONTINUATION_PAGE_ROLE_MISMATCH")
        ordered_target = ordered(target_page)
        prefix = [lines[r][1] for r in requested if r in lines and lines[r][0].get("asset_id") == to_id]
        if len(prefix) != len(requested):
            issue("CONTINUATION_TARGET_LINE_SOURCE_MISMATCH")
        if [line["line_id"] for line in ordered_target[:len(requested)]] != requested:
            issue("CONTINUATION_TARGET_NOT_LEADING_PREFIX")
        if prefix:
            first, w = prefix[0], window_for(target_page, prefix[0])
            if (not w or first["location"]["column"] != 0 or w["y_range"][0] > target_page["source"]["height"] * .2
                    or first["bbox"][1] > w["y_range"][0] + 25):
                issue("CONTINUATION_TARGET_TOP_NOT_PROVEN")
            for line in prefix:
                if not window_consistent(target_page, line):
                    issue("CONTINUATION_TARGET_WINDOW_INCONSISTENT", refs=[line["line_id"]])
                if PRIMARY.match(line["text"]) or BOUNDARY.match(line["text"].strip()):
                    issue("CONTINUATION_TARGET_HAS_PRIMARY_OR_HEADING", refs=[line["line_id"]])
                numbers=set(re.findall(r"图\s*(\d+)",line["text"]))
                proven_numbers={r["figure_number"] for r in validated_images}
                if (re.search(r"如图\s*[\d一二三四五六七八九十]*|图\s*\d+", line["text"])
                        and (not numbers or not numbers <= proven_numbers)):
                    issue("CONTINUATION_FIGURE_EXTENT_UNVERIFIED",
                          "OCR labels do not prove complete diagram extents; this trial has no executable image-region proof.",
                          [line["line_id"]])
                if (line.get("location") or {}).get("section_path") != data.get("section_path"):
                    issue("CONTINUATION_SECTION_CHANGED", refs=[line["line_id"]])
                if line["location"]["window_index"] != first["location"]["window_index"]:
                    issue("CONTINUATION_PREFIX_CROSSES_WINDOW")
                if not valid_bbox(line["bbox"], target_page["source"]["width"], target_page["source"]["height"]):
                    issue("CONTINUATION_TARGET_GEOMETRY_INVALID", refs=[line["line_id"]])
            for previous, line in zip(prefix, prefix[1:]):
                if line["bbox"][1] - previous["bbox"][3] > max(24, (previous["bbox"][3] - previous["bbox"][1]) * 1.3):
                    issue("CONTINUATION_PREFIX_SPATIAL_GAP", refs=[previous["line_id"], line["line_id"]])
            if len(ordered_target) > len(requested):
                boundary = ordered_target[len(requested)]
                boundary_members=set(composed_boundary["line_ids"]) if composed_boundary else set()
                following={l["line_id"] for l in ordered_target[len(requested):len(requested)+len(boundary_members)]}
                if composed_boundary and boundary["line_id"] in boundary_members and following == boundary_members:
                    boundary_ref=composed_boundary["candidate_ref"]["artifact_id"]
                elif PRIMARY.match(boundary["text"]) or BOUNDARY.match(boundary["text"].strip()):
                    boundary_ref = boundary["line_id"]
                else:
                    issue("CONTINUATION_PREFIX_INCOMPLETE", refs=[boundary["line_id"]])
            else:
                issue("CONTINUATION_TARGET_END_UNRESOLVED")
    ownership = {}
    for candidate in answer_list:
        for fragment in candidate.get("fragments", []):
            for r in fragment.get("evidence_refs", []):
                unit = units.get(r)
                parent = unit[1].get("parent_line_id", r) if unit else r
                ownership.setdefault(parent, set()).add(candidate.get("answer_id"))
    if ownership.get(data.get("source_tail_line_id"), set()) != {data.get("from_answer_id")}:
        issue("CONTINUATION_TAIL_OWNERSHIP_CONFLICT", refs=[data.get("source_tail_line_id")])
    for region in validated_images:
        for r in region["diagnostic_ocr_refs"]:
            pair=units.get(r)
            parent=pair[1].get("parent_line_id",r) if pair else r
            if region["asset_id"]==from_id and ownership.get(parent,set()) != {data.get("from_answer_id")}:
                issue("CONTINUATION_SOURCE_IMAGE_OWNERSHIP_CONFLICT",refs=[r])
            if region["asset_id"]==to_id and (r not in requested or ownership.get(parent)):
                issue("CONTINUATION_TARGET_IMAGE_OWNERSHIP_CONFLICT",refs=[r])
    ledger = graph.get("payload", {}).get("answer_coverage", [])
    for r in requested:
        records = [row for row in ledger if row.get("line_id") == r]
        if (ownership.get(r) or len(records) != 1 or records[0].get("status") != "UNASSIGNED"
                or records[0].get("answer_ids") or records[0].get("fragment_ids") or records[0].get("allocations")):
            issue("CONTINUATION_TARGET_ALREADY_OWNED_OR_UNACCOUNTED", refs=[r])

    accepted = not issues
    quality = "SYNTHETIC_TEST" if "SYNTHETIC_TEST" in qualities else review.get("reference_quality")
    plan = None
    if accepted:
        image_refs={ref:region["region_id"] for region in validated_images for ref in region["diagnostic_ocr_refs"]}
        if len(image_refs) != sum(len(r["diagnostic_ocr_refs"]) for r in validated_images):
            issue("CONTINUATION_IMAGE_LABEL_REUSED")
            return _report(evidence,graph,proof,issues,quality=quality)
        if validated_images:
            mentioned=set(re.findall(r"图\s*(\d+)"," ".join(f["raw_text"] for f in answer["fragments"])+" "+" ".join(l["text"] for l in prefix)))
            if mentioned != {r["figure_number"] for r in validated_images}:
                issue("CONTINUATION_IMAGE_REFERENCE_SET_MISMATCH",{"mentioned":sorted(mentioned)})
                return _report(evidence,graph,proof,issues,quality=quality)
        plan = {"operation": "PROPOSE_ONLY", "from_answer_id": data["from_answer_id"],
                "source_fragment_ids_preserved": list(data["source_fragment_ids"]),
                "source_tail_line_id": data["source_tail_line_id"],
                "to_asset_id": to_id, "target_line_ids": list(requested),
                "target_regions": [{"asset_id": to_id, "line_id": line["line_id"],
                                    "bbox": copy.deepcopy(line["bbox"]), "raw_text": line["text"],
                                    "evidence_refs": [line["line_id"]]} for line in prefix],
                "next_boundary_ref": boundary_ref, "section_path": copy.deepcopy(data["section_path"]),
                "input_refs": [_ref(evidence), _ref(graph), _ref(proof), _ref(receipt)],
                "verification_status": "UNVERIFIED", "reference_quality": quality,
                "business_acceptance": False, "platform_actions": []}
        if validated_images:
            plan["target_regions"]=[{**region,"content_type":"text"} for region in plan["target_regions"] if region["line_id"] not in image_refs]
            plan["target_regions"].extend(copy.deepcopy(r) for r in validated_images if r["asset_id"]==to_id)
            plan["source_image_regions"]=[copy.deepcopy(r) for r in validated_images if r["asset_id"]==from_id]
            plan["source_fragment_representation"]=[{"fragment_id":f["fragment_id"],"represented_by_image_region":image_refs[canonical_fragment_parent[f["fragment_id"]]],
                                                      "render_as_separate_region":False} for f in answer["fragments"] if canonical_fragment_parent.get(f["fragment_id"]) in image_refs]
            plan["image_contained_ocr_refs"]=image_refs
            plan["image_semantics_verified"]=False
            plan["image_region_artifact_ref"]=_ref(data["image_regions"])
        if composed_boundary:
            plan["next_boundary_binding"]=copy.deepcopy(composed_boundary)
    return _report(evidence, graph, proof, issues, plan, quality)
