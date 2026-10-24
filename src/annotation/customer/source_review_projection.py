"""Pure, read-only source-segment projection for customer review.

No filesystem, image processing, model, browser, platform or product imports.
Consumes existing candidate/graph/evidence and optional archived layout outputs.
Never creates candidate text, TeX, answers, production frames or ready states.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math

ROLES = {"question": "stem", "choice": "option", "answer": "answer", "analysis": "explanation"}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _need(value, code):
    if not value:
        raise ValueError(code)


def _ref(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def _artifact(value, kinds):
    _need(isinstance(value, dict) and value.get("kind") in kinds, "ARTIFACT_KIND")
    _need(value.get("content_hash") == _digest(value.get("payload")), "ARTIFACT_HASH")
    _need(type(value.get("revision")) is int and value["revision"] > 0, "ARTIFACT_REVISION")
    return value["payload"]


def _box(value, size):
    return (isinstance(value, (tuple, list)) and len(value) == 4
            and all(type(v) in (int, float) and math.isfinite(v) for v in value)
            and 0 <= value[0] < value[2] <= size[0] and 0 <= value[1] < value[3] <= size[1])


def _contains(outer, inner):
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def _union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def project_candidate(candidate, graph, evidence, *, layouts=()):
    """Return source previews; caller keeps existing editor, save and confirm.

    graph/evidence are hash-checked existing artifacts; layouts may contain
    existing MathLayoutTrial and InlineMathLayoutTrial artifacts. Caller still
    verifies original source bytes with its existing verify_sources boundary.
    Projection bboxes are preview-only, never replacement production frames.
    """
    ep = _artifact(evidence, {"EvidenceBundleTrial"})
    gp = _artifact(graph, {"QuestionGraphTrial"})
    _need((graph.get("book_id"), graph.get("scope_id"), graph.get("input_refs")) ==
          (evidence.get("book_id"), evidence.get("scope_id"), [_ref(evidence)]), "GRAPH_EVIDENCE_BINDING")
    questions = [q for q in gp["questions"] if q["question_id"] == candidate["question_id"]]
    _need(len(questions) == 1, "UNIQUE_QUESTION_REQUIRED")
    question = questions[0]
    _need(question["printed_number"] == candidate["printed_number"] and
          question["section_path"] == candidate["section_path"], "QUESTION_IDENTITY_MISMATCH")
    answers = [a for a in gp["answers"] if a["answer_id"] == question.get("selected_answer_id")]
    _need(len(answers) <= 1, "DUPLICATE_ANSWER")
    fragments = question["fragments"] + (answers[0]["fragments"] if answers else [])
    binding = candidate.get("manual_answer_binding")
    if binding:
        _need(not answers and binding.get("source_checked") is True, "MANUAL_ANSWER_BINDING_CONFLICT")
        source_lines = {line["line_id"]: (page, line) for page in ep["pages"] for line in page["ocr_lines"]}
        ids, texts = binding["line_ids"], binding["raw_texts"]
        _need(len(ids) == len(texts) and len(set(ids)) == len(ids), "MANUAL_ANSWER_LINES_CHANGED")
        for identity, raw_text in zip(ids, texts):
            page, line = source_lines[identity]
            _need(page["page_role"] == "answer" and line["text"] == raw_text and
                  line["location"]["section_path"] == candidate["section_path"], "MANUAL_ANSWER_SOURCE_CHANGED")
            fragments.append({"fragment_id": "customer-assigned:" + identity, "role": "answer",
                              "asset_id": page["asset_id"], "column": line["location"]["column"],
                              "bbox": copy.deepcopy(line["bbox"]), "text": raw_text, "evidence_refs": [identity]})
    _need(len({f["fragment_id"] for f in fragments}) == len(fragments), "DUPLICATE_FRAGMENT")
    pages = {p["asset_id"]: p["source"] for p in ep["pages"]}
    _need(len(pages) == len(ep["pages"]), "DUPLICATE_SOURCE")
    zones, all_segments = [], []
    for zone, current_text in candidate["zones"].items():
        _need(zone in ROLES and isinstance(current_text, str), "SUPPORTED_TEXT_ZONE_REQUIRED")
        frames = [(i, f) for i, f in enumerate(candidate["frames"])
                  if f["zone"] == zone and (f.get("content_type") == "text" or
                      (zone == 'choice' and f.get('graphic_option_label') and f.get('content_type') == 'image'))]
        declared = [fid for _, f in frames for fid in f.get("source_fragment_ids", [])]
        problems = []
        if len(set(declared)) != len(declared):
            problems.append({"code": "DUPLICATE_FRAME_FRAGMENT_REFERENCE"})
        selected = [f for f in fragments if f["role"] == ROLES[zone] and f["fragment_id"] in declared]
        missing = [fid for fid in declared if fid not in {f["fragment_id"] for f in selected}]
        if missing:
            problems.append({"code": "FRAME_REFERENCES_NOT_IN_SELECTED_GRAPH", "fragment_ids": missing})
        omitted = [f["fragment_id"] for f in fragments if f["role"] == ROLES[zone] and f["fragment_id"] not in declared]
        if omitted:
            problems.append({"code": "GRAPH_FRAGMENTS_NOT_BOUND_BY_CANDIDATE", "fragment_ids": omitted})
        segments, previous = [], None
        for fragment in selected:  # Graph order, NEVER a new x/y sort.
            matching = [(i, f) for i, f in frames if fragment["fragment_id"] in f.get("source_fragment_ids", [])]
            if len(matching) != 1:
                previous = None
                continue
            frame_index, frame = matching[0]
            source = pages.get(fragment["asset_id"])
            size = [source["width"], source["height"]] if source else None
            bound = (source and frame["asset_id"] == fragment["asset_id"] and frame["source_sha256"] == source["sha256"]
                     and frame.get("source_dimensions") == size and frame.get("coordinate_space") == "ORIGINAL_PIXELS"
                     and frame.get("column", 0) == fragment.get("column", 0)
                     and _box(frame["bbox"], size) and _box(fragment["bbox"], size) and _contains(frame["bbox"], fragment["bbox"]))
            if not bound:
                problems.append({"code": "FRAGMENT_SOURCE_BINDING_UNPROVEN", "fragment_id": fragment["fragment_id"]})
                previous = None
                continue
            key = (fragment["asset_id"], fragment.get("column", 0), frame_index)
            if key != previous:
                segment = {"segment_id": candidate["key"] + ":" + zone + ":source:" + str(len(segments)),
                    "zone": zone, "order": len(segments), "asset_id": fragment["asset_id"], "column": key[1],
                    "source_sha256": source["sha256"], "source_dimensions": size,
                    "coordinate_space": "ORIGINAL_PIXELS", "frame_index": frame_index,
                    "source_frame_bbox": copy.deepcopy(frame["bbox"]), "fragments": [], "formula_hints": []}
                segments.append(segment)
            segment["fragments"].append(copy.deepcopy(fragment))
            previous = key
        for segment in segments:
            frame = candidate['frames'][segment['frame_index']]
            segment["preview_bbox"] = (copy.deepcopy(frame['bbox']) if frame.get('graphic_option_label')
                                       else _union([f["bbox"] for f in segment["fragments"]]))
            if frame.get('graphic_option_label'):
                segment['option_label'] = frame['graphic_option_label']
                segment['source_checked'] = frame.get('binding', {}).get('source_checked') is True
            segment["source_text"] = "\n".join(f["text"] for f in segment["fragments"])
            segment["evidence_refs"] = list(dict.fromkeys(r for f in segment["fragments"] for r in f.get("evidence_refs", [])))
            segment["status"] = "SOURCE_PREVIEW_NOT_CONTENT_APPROVAL"
        source_text = "\n".join(f["text"] for f in selected)
        exact = not problems and bool(selected) and source_text == current_text
        zones.append({"zone": zone, "current_text": current_text, "source_text": source_text, "segments": segments,
            "edit_mapping": "EXACT_SOURCE_TEXT" if exact else "ZONE_TEXT_ONLY_NO_SEGMENT_EDIT_MAPPING",
            "issues": problems, "formula_candidates": [], "formula_status": "NO_LAYOUT_EVIDENCE"})
        all_segments.extend(segments)
    rejected = _layout_hints(layouts, all_segments, graph, evidence, pages)
    for zone in zones:
        if any(s["formula_hints"] for s in zone["segments"]):
            zone["formula_status"] = "OBSERVED_STRUCTURE_ONLY_NO_TEX_CANDIDATE"
    return {"schema": "CustomerSourceReviewProjection/v1", "candidate_key": candidate["key"],
        "candidate_snapshot_sha256": _digest(candidate), "graph_ref": _ref(graph), "evidence_ref": _ref(evidence),
        "zones": zones, "rejected_layouts": rejected, "original_issues": copy.deepcopy(candidate.get("issues", [])),
        "status": "READ_ONLY_REVIEW_PROJECTION", "source_bytes_verified_here": False,
        "content_approved": False, "candidate_modified": False, "model_calls": 0, "platform_actions": []}


def _layout_hints(layouts, segments, graph, evidence, pages):
    rejected = []
    for artifact in layouts:
        try:
            pending = []
            payload = _artifact(artifact, {"MathLayoutTrial", "InlineMathLayoutTrial"})
            _need((artifact.get("book_id"), artifact.get("scope_id")) ==
                  (graph.get("book_id"), graph.get("scope_id")), "LAYOUT_SCOPE_MISMATCH")
            fraction = artifact["kind"] == "MathLayoutTrial"
            if fraction:
                _need(artifact.get("schema_version") == "b-math-layout-trial/0.1", "LAYOUT_SCHEMA")
                aid, sha, size = payload["asset_id"], payload["source_sha256"], payload["source_size"]
                items = payload["fraction_candidates"]
            else:
                _need(artifact.get("schema_version") == "b-inline-math-layout-trial/0.1", "LAYOUT_SCHEMA")
                _need(payload["evidence_ref"] == _ref(evidence), "INLINE_EVIDENCE_BINDING")
                source = payload["source"]
                aid, sha = source["asset_id"], source["original_sha256"]
                size = [source["asset"]["width"], source["asset"]["height"]]
                items = payload["units"]
            source = pages.get(aid)
            _need(source and sha == source["sha256"] and size == [source["width"], source["height"]], "LAYOUT_SOURCE_BINDING")
            for item in items:
                if fraction:
                    boxes = [item["bar_bbox"], item["numerator"]["pixel_bbox"], item["denominator"]["pixel_bbox"]]
                    _need(all(_box(b, size) for b in boxes), "FRACTION_BOX_INVALID")
                    box, identity = _union(boxes), item["fraction_id"]
                else:
                    box, identity = item["source_bbox"], item["unit_id"]
                    _need(item["asset_id"] == aid and _box(box, size), "INLINE_BOX_INVALID")
                targets = [s for s in segments if s["asset_id"] == aid and _contains(s["source_frame_bbox"], box)
                           and (fraction or item["line_id"] in s["evidence_refs"])]
                if len(targets) != 1:
                    rejected.append({"layout_ref": _ref(artifact), "item_id": identity, "code": "NO_UNIQUE_SOURCE_SEGMENT"})
                    continue
                incomplete = (not fraction or bool(item.get("ambiguous_ocr_refs")) or
                              any(item[role].get("missing_ocr") or not item[role].get("ocr_refs")
                                  for role in ("numerator", "denominator")))
                pending.append((targets[0], {"layout_ref": _ref(artifact), "item_id": identity,
                    "kind": "FRACTION_STRUCTURE" if fraction else "INLINE_OBSERVATION",
                    "source_bbox": copy.deepcopy(box), "observation": copy.deepcopy(item),
                    "uncertainty": "INCOMPLETE_OR_AMBIGUOUS" if incomplete else "STRUCTURE_UNVERIFIED",
                    "tex_candidate": None, "apply_to_content_allowed": False}))
            for target, hint in pending:
                target["formula_hints"].append(hint)
        except (KeyError, TypeError, ValueError) as exc:
            rejected.append({"artifact_id": artifact.get("artifact_id") if isinstance(artifact, dict) else None,
                             "code": "LAYOUT_NOT_PROJECTED", "reason": str(exc)})
    return rejected
