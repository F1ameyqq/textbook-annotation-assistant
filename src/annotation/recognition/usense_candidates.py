"""Private, source-bound OCR review candidates; never writer input or approval.

All revisions are explicit MODEL_VISUAL observations. Raw text, all OCR variants,
unknown identity mappings, and omitted semantic-lesson items remain separate.
"""
from copy import deepcopy
import math
from pathlib import Path

from .usense_capture import CaptureReader, checked_ref, file_ref, read_json

SCHEMA = "b-usense-ocr-review-trial/0.1"
REVIEW_SCHEMA = "UsenseOCRSourceReview/v1"
ZONES = ("question", "choice", "answer")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _span(span, pages, frames, zone, target, materialize):
    """Keep exact source geometry, and check actual pixels when reloading."""
    from PIL import Image
    page = pages[str(span["viewer_page"])]
    source_path = checked_ref(page["file"])
    _require(page["sha256"] == page["file"]["sha256"], "Page hash mismatch")
    bbox = span["bbox"]
    _require(isinstance(bbox, list) and len(bbox) == 4
             and all(type(v) in (int, float) and math.isfinite(v) for v in bbox),
             "Finite source bbox required")
    with Image.open(source_path) as original:
        _require(0 <= bbox[0] < bbox[2] <= original.width
                 and 0 <= bbox[1] < bbox[3] <= original.height, "Source bbox outside page")
        _require([original.width, original.height] == page["dimensions"], "Page dimensions changed")
        box = [math.floor(bbox[0]), math.floor(bbox[1]), math.ceil(bbox[2]), math.ceil(bbox[3])]
        crop = original.convert("RGB").crop(box)
    # A source observation must overlap a captured frame of this question and
    # role. This is evidence association, not proof of the proposed text.
    linked = []
    for frame in frames:
        f = [float(v) for v in frame["rect_bbox"].split(",")]
        if (frame["type"] == zone and int(frame["page_index"]) == span["viewer_page"]
                and max(f[0], bbox[0]) < min(f[2], bbox[2])
                and max(f[1], bbox[1]) < min(f[3], bbox[3])):
            linked.append(frame["rect_id"])
    _require(linked, "No matching captured question/zone source frame")
    _require(isinstance(span.get("purpose"), str) and span["purpose"].strip(), "Source purpose required")
    if materialize:
        crop.save(target)
    else:
        with Image.open(target) as saved:
            _require(saved.convert("RGB").size == crop.size
                     and saved.convert("RGB").tobytes() == crop.tobytes(), "Derived source crop changed")
    return {"viewer_page": span["viewer_page"], "bbox": bbox, "rounded_bbox": box,
            "purpose": span["purpose"], "source": page["file"],
            "linked_rect_ids": sorted(linked), "crop": file_ref(target)}


def build_package(ocr_root, review_path, output_root, *, materialize=False):
    """Validate inputs and build a deterministic, explicitly unapproved package."""
    ocr_root, output_root = Path(ocr_root).resolve(), Path(output_root).resolve()
    run_path, sources_path = ocr_root / "run.json", ocr_root / "sources.json"
    run, sources = read_json(run_path), read_json(sources_path)
    _require(run["status"] == "REAL_LOCAL_BATCH_OCR_DONE_REVIEW_REQUIRED", "Incomplete OCR run")
    _require(run["network_disabled"] is True and run["platform_requests"] == 0,
             "Expected offline OCR observations")
    checked_ref(run["script"])
    checked_ref(run["adapter"])
    checked_ref(sources["source_manifest"])
    checked_ref(sources["capture_summary"])
    manifest = sources.get("readback_manifest")
    reader = CaptureReader(sources["capture_directory"], checked_ref(manifest) if manifest else None)
    frames = reader.get("frames")
    directory = reader.get("directory")["directory_data"]
    nodes = {}
    def walk(rows):
        for row in rows:
            _require(row["id"] not in nodes, "Duplicate directory node ID")
            nodes[row["id"]] = row
            walk(row.get("children", []))
    walk(directory)
    review = read_json(review_path) if review_path else {"schema": REVIEW_SCHEMA,
        "review_kind": "MODEL_VISUAL", "scope": {"complete_lesson_denominator": None}, "items": []}
    _require(review["schema"] == REVIEW_SCHEMA and review["review_kind"] == "MODEL_VISUAL",
             "Only non-human source observations are supported")
    _require(review["scope"].get("complete_lesson_denominator") is None,
             "This candidate layer does not establish a complete lesson denominator")
    changes = {}
    for item in review["items"]:
        order = item["native_order"]
        _require(type(order) is int and order not in changes, "Duplicate/invalid review order")
        changes[order] = item
    result = {"schema": SCHEMA, "status": "REVIEW_REQUIRED", "write_allowed": False,
        "human_confirmation": None, "formal_acceptance": "NOT_RUN",
        "ocr_root": str(ocr_root), "ocr_run": file_ref(run_path), "sources": file_ref(sources_path),
        "review": file_ref(review_path) if review_path else None,
        "scope_observation": deepcopy(review["scope"]), "items": []}
    seen = set()
    for record in run["candidates"]:
        cpath = checked_ref(record["candidate"])
        c = read_json(cpath)
        order = c["question_order"]
        _require(type(order) is int and order not in seen and order == record["order"], "OCR order mismatch")
        seen.add(order)
        _require(c["schema"] == "LessonQuestionOCRCandidate/v1" and c["write_allowed"] is False
                 and c["status"] == "REVIEW_REQUIRED", "Unapproved raw OCR required")
        _require(c["node_id"] in nodes and int(nodes[c["node_id"]]["order_in_level"]) == order,
                 "Native directory identity changed")
        _require(reader.get(f"q{order}_info") == c["question_info"]
                 and c["question_info"]["id"] == c["question_info_id"], "Question info changed")
        qframes = reader.get(f"q{order}_annotations")
        _require(qframes == c["platform_frames"], "Captured question frames changed")
        expected = [f for f in frames if f.get("directory_id") == c["lesson_id"]
                    and int(f["order_in_level"]) == order]
        _require(sorted(qframes, key=lambda f: f["rect_id"]) == sorted(expected, key=lambda f: f["rect_id"]),
                 "Captured full-frame inventory mismatch")
        raw = read_json(checked_ref(c["raw_results"]))
        # Reconstruct the exact primary proposal from retained model variants.
        # Do not silently replace it with a cleaned transcript.
        raw_fields = {z: "\n".join(i["variants"][0]["joined_raw_text"] for i in raw.get(z, [])) for z in ZONES}
        _require(raw_fields == c["raw_zone_text"], "Raw primary OCR projection changed")
        for z, items in raw.items():
            for item in items:
                checked_ref(item["crop"])
                checked_ref(item["source"]["file"])
                _require(item["platform_frame"] in qframes and item["zone"] == z,
                         "Raw OCR source identity mismatch")
        change = changes.get(order, {})
        revised = deepcopy(raw_fields)
        revisions, diagrams, formulas = [], [], []
        counter = 0
        def spans(entries, zone):
            nonlocal counter
            _require(isinstance(entries, list) and entries, "Explicit source evidence required")
            found = []
            for entry in entries:
                counter += 1
                found.append(_span(entry, sources["pages"], qframes, zone,
                    output_root / "evidence" / f"q{order}-{counter}.png", materialize))
            return found
        touched = set()
        for revision in change.get("revisions", []):
            zone = revision["field"]
            _require(zone in ZONES and zone not in touched, "Invalid/duplicate revised field")
            touched.add(zone)
            _require(revision["before"] == raw_fields[zone], "Revision predecessor does not match raw OCR")
            _require(isinstance(revision["after"], str) and revision["after"] != revision["before"],
                     "Explicit changed transcription required")
            _require(isinstance(revision.get("reason"), str) and revision["reason"].strip(), "Revision reason required")
            evidence = spans(revision["evidence"], zone)
            revised[zone] = revision["after"]
            revisions.append({"field": zone, "before": revision["before"], "after": revision["after"],
                "reason": revision["reason"], "evidence": evidence, "review_kind": "MODEL_VISUAL",
                "status": "REVIEW_REQUIRED"})
        for diagram in change.get("diagrams", []):
            diagrams.append({"evidence": spans([diagram], "question"), "status": "SOURCE_PIXELS_RETAINED"})
        for formula in change.get("formulas", []):
            _require(formula["field"] in ZONES and isinstance(formula["transcription"], str), "Invalid formula")
            formulas.append({"field": formula["field"], "transcription": formula["transcription"],
                "evidence": spans(formula["evidence"], formula["field"]), "review_kind": "MODEL_VISUAL",
                "status": "REVIEW_REQUIRED"})
        mapping = change.get("mapping")
        if mapping is not None:
            _require(set(mapping) == {"semantic_lesson", "printed_number", "legacy_native_order", "evidence"},
                     "Mapping requires explicit semantic, printed and legacy identities")
            _require(all(type(mapping[k]) is int and mapping[k] > 0 for k in
                         ("semantic_lesson", "printed_number", "legacy_native_order")), "Invalid mapping identity")
            mapping = {**mapping, "evidence": spans(mapping["evidence"], "question"),
                       "status": "MODEL_VISUAL_OBSERVATION_NOT_CANONICAL_MIGRATION"}
        result["items"].append({"native_order": order, "node_id": c["node_id"],
            "question_info_id": c["question_info_id"], "captured_directory_id": c["lesson_id"],
            "mapping": mapping, "mapping_status": "UNKNOWN" if mapping is None else "SOURCE_OBSERVED",
            "raw_candidate": file_ref(cpath), "raw_results": c["raw_results"],
            "raw_fields": raw_fields, "proposal_fields": revised, "source_revisions": revisions,
            "diagrams": diagrams, "formulas": formulas, "ocr_issues": c["issues"],
            "review_issues": change.get("issues", []), "answer_status":
                "SOURCE_OBSERVED_REVIEW_REQUIRED" if any(f["type"] == "answer" for f in qframes)
                else "UNKNOWN_NO_ANSWER_SOURCE", "status": "REVIEW_REQUIRED", "write_allowed": False})
    _require(seen == set(run["orders"]) and set(changes) <= seen, "Review and OCR scopes differ")
    return result


def assemble(ocr_root, review_path, output_root):
    import json
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=False)
    (output_root / "evidence").mkdir()
    package = build_package(ocr_root, review_path, output_root, materialize=True)
    (output_root / "candidates.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return package


def check(path):
    path = Path(path)
    package = read_json(path)
    checked_ref(package["ocr_run"])
    checked_ref(package["sources"])
    review = checked_ref(package["review"]) if package["review"] else None
    rebuilt = build_package(package["ocr_root"], review, path.parent)
    _require(package == rebuilt, "Candidate package changed or elevated beyond source observations")
    return {"status": "SOURCE_BINDINGS_VALID_REVIEW_REQUIRED", "items": len(package["items"]),
            "write_allowed": False, "human_confirmation": None}
