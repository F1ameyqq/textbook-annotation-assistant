"""Pixel-bound body/wrapper runs around unchanged mathematical fractions.

All connected components, including single pixels, remain in the ledger. Pixel
accounting is not text recognition. No model, expected transcription, semantic
formula repair or graph mutation is performed. OCR crops retain real source
pixels and whole-row fallbacks; they are never whitened to hide fractions.
"""
from __future__ import annotations

import copy
import hashlib
import io
import math
from pathlib import Path
import re
from statistics import median

import cv2
import numpy as np
from PIL import Image, __version__ as pillow_version

from .baseline import code_digest, digest, file_digest, valid_bbox

SCHEMA = "b-region-runs-trial/0.1"
CONFIG = {"thresholds": [180, 190, 210, 220], "connectivity": 8,
          "minimum_component_pixels": 1, "minimum_row_tolerance_pixels": 3,
          "row_tolerance_font_height_ratio": .3, "row_boundary": "FLOOR_MEAN_BASELINE_MIDPOINT",
          "horizontal_halo_minimum_pixels": 2, "horizontal_halo_font_height_ratio": .25,
          "component_closure": "FULL_TOUCHING_COMPONENT_HORIZONTAL_EXTENT_CLAMP_ROW_AND_CROP",
          "pixel_policy": "UNMASKED_ORIGINAL_RGB", "fraction_bbox": "UNION_BAR_NUMERATOR_DENOMINATOR"}
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def reference(value):
    return {k: value[k] for k in ("artifact_id", "revision", "content_hash")}


def _ref(value):
    return (isinstance(value, dict) and set(value) == {"artifact_id", "revision", "content_hash"}
            and isinstance(value["artifact_id"], str) and bool(value["artifact_id"])
            and type(value["revision"]) is int and value["revision"] > 0
            and isinstance(value["content_hash"], str) and bool(_HASH.fullmatch(value["content_hash"])))


def _integer_box(box, size):
    return isinstance(box, list) and len(box) == 4 and all(type(v) is int for v in box) and valid_bbox(box, *size)


def _inside(inner, outer):
    return outer[0] <= inner[0] < inner[2] <= outer[2] and outer[1] <= inner[1] < inner[3] <= outer[3]


def _overlap(left, right):
    return max(left[0], right[0]) < min(left[2], right[2]) and max(left[1], right[1]) < min(left[3], right[3])


def _union(boxes):
    return [min(v[0] for v in boxes), min(v[1] for v in boxes), max(v[2] for v in boxes), max(v[3] for v in boxes)]


def _rgb_sha(image):
    return hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()


def _bound(layout, crop_path):
    if (not isinstance(layout, dict) or layout.get("schema_version") != "b-math-layout-trial/0.1"
            or layout.get("kind") != "MathLayoutTrial" or not _ref({k: layout.get(k) for k in ("artifact_id", "revision", "content_hash")})
            or not isinstance(layout.get("payload"), dict) or layout["content_hash"] != digest(layout["payload"])
            or any(not isinstance(layout.get(k), str) or not layout[k] for k in ("book_id", "scope_id"))
            or layout["artifact_id"] != "math-layout-"+digest([layout.get("input_refs"), layout.get("producer"), layout["payload"]])[:24]):
        raise ValueError("region runs require an unchanged legacy mathematical layout")
    p = layout["payload"]; size, crop_box = p.get("source_size"), p.get("crop_bbox")
    if (p.get("decision") != "HOLD" or p.get("platform_actions") != []
            or any(p.get(k) is not False for k in ("transcription_verified", "formula_text_reconstructed", "visual_formula_references_consumed"))
            or any(container.get(k) is not False for container in (layout, layout.get("producer", {}), p)
                   for k in ("human_verified", "business_acceptance", "complete", "precise_glyph_localization", "spatial_role_verified") if k in container)):
        raise ValueError("mathematical layout cannot claim verified text, precise glyphs or acceptance")
    if (not isinstance(size, list) or len(size) != 2 or any(type(v) is not int or v <= 0 for v in size)
            or not _integer_box(crop_box, size) or any(not isinstance(p.get(k), str) or not _HASH.fullmatch(p[k]) for k in ("source_sha256", "crop_sha256"))
            or not isinstance(p.get("asset_id"), str) or not p["asset_id"]):
        raise ValueError("layout source identity or crop dimensions are invalid")
    refs = layout.get("input_refs")
    if (not isinstance(refs, list) or len(refs) != 3 or not _ref(refs[0])
            or digest(refs[1]) != digest({"asset_id": p["asset_id"], "sha256": p["source_sha256"]})
            or digest(refs[2]) != digest({"crop_sha256": p["crop_sha256"]})):
        raise ValueError("layout source/crop reference binding differs")
    raw = Path(crop_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != p["crop_sha256"]: raise ValueError("region crop bytes changed")
    with Image.open(io.BytesIO(raw)) as opened: image = opened.convert("RGB")
    if image.size != (crop_box[2]-crop_box[0], crop_box[3]-crop_box[1]): raise ValueError("region crop size differs from original coordinates")
    fractions = p.get("fraction_candidates")
    if not isinstance(fractions, list) or not fractions: raise ValueError("fraction-driven region runs require at least one fraction")
    seen = set(); heights = []
    source_ocr = p.get("source_ocr")
    if not isinstance(source_ocr, list): raise ValueError("layout original OCR snapshots are missing")
    line_ids = set()
    for line in source_ocr:
        if (not isinstance(line.get("line_id"), str) or line["line_id"] in line_ids
                or not isinstance(line.get("text"), str) or not isinstance(line.get("bbox"), list)
                or not valid_bbox(line["bbox"], *size) or not _inside(line["bbox"], crop_box)):
            raise ValueError("layout source OCR identity or coordinates differ")
        line_ids.add(line["line_id"]); heights.append(line["bbox"][3]-line["bbox"][1])
    for fraction in fractions:
        fid = fraction.get("fraction_id")
        if not isinstance(fid, str) or not fid or fid in seen: raise ValueError("fraction IDs must be unique")
        seen.add(fid); bar = fraction.get("bar_bbox")
        if not _integer_box(bar, size) or not _inside(bar, crop_box): raise ValueError("fraction bar lies outside the bound crop")
        for role in ("numerator", "denominator"):
            box = fraction[role].get("pixel_bbox"); refs = fraction[role].get("ocr_refs")
            if (not _integer_box(box, size) or not _inside(box, crop_box)
                    or not (box[3] <= bar[1]+1 if role == "numerator" else box[1] >= bar[3]-1)
                    or min(box[2], bar[2]) <= max(box[0], bar[0])
                    or not isinstance(refs, list) or len(refs) != len(set(refs)) or any(r not in line_ids for r in refs)):
                raise ValueError("fraction role geometry or source OCR refs are invalid")
    # This does not rerun the layout generator: source tokens and fractions must
    # still occur exactly once in its declared nested reading/coverage ledger.
    groups = p.get("reading_groups", []); declared_fractions, declared_lines = [], []
    for group in groups:
        for unit in group.get("units", []):
            if unit.get("kind") == "fraction": declared_fractions.append(unit.get("fraction_id"))
            declared_lines.extend(unit.get("ocr_refs", []))
    if (len(declared_fractions) != len(seen) or set(declared_fractions) != seen
            or len(declared_lines) != len(line_ids) or set(declared_lines) != line_ids
            or len(p.get("token_coverage", [])) != len(line_ids)
            or {v.get("line_id") for v in p["token_coverage"]} != line_ids):
        raise ValueError("legacy layout fraction or raw-token coverage differs")
    font = float(median(heights)) if heights else float(median(f["numerator"]["pixel_bbox"][3]-f["numerator"]["pixel_bbox"][1] for f in fractions))
    return image, font


def _slot_id(layout, kind, row_id, box, fraction_id=None):
    return "region-slot-"+digest([reference(layout), kind, row_id, box, fraction_id])[:24]


def _crop(image, source_box, box):
    tile = image.crop([box[i]-source_box[i % 2] for i in range(4)])
    return {"crop_size": list(tile.size), "crop_rgb_sha256": _rgb_sha(tile)}


def plan_region_runs(layout, crop_path):
    """Partition source pixels into fraction slots, body gaps and residuals.

    The returned original-coordinate recognition_bbox crops can be handed to an
    explicitly invoked ordinary OCR collector. Their raw observations cannot be
    called current answer text until separately selected/materialized as drafts.
    """
    original_digest = digest(layout); frozen = copy.deepcopy(layout)
    image, font = _bound(frozen, crop_path)
    p = frozen["payload"]; crop_box = p["crop_bbox"]; origin = crop_box[:2]
    gray = np.asarray(image.convert("L")); tolerance = max(CONFIG["minimum_row_tolerance_pixels"], font*CONFIG["row_tolerance_font_height_ratio"])
    groups = []
    for fraction in sorted(p["fraction_candidates"], key=lambda f: ((f["bar_bbox"][1]+f["bar_bbox"][3])/2, f["bar_bbox"][0], f["fraction_id"])):
        baseline = (fraction["bar_bbox"][1]+fraction["bar_bbox"][3])/2
        group = next((g for g in groups if abs(sum(g["baselines"])/len(g["baselines"])-baseline) <= tolerance), None)
        if group is None:
            group = {"baselines": [], "fractions": []}; groups.append(group)
        group["baselines"].append(baseline); group["fractions"].append(fraction)
    baselines = [sum(g["baselines"])/len(g["baselines"]) for g in groups]
    edges = [crop_box[1]]+[math.floor((a+b)/2) for a, b in zip(baselines, baselines[1:])]+[crop_box[3]]
    if any(a >= b for a, b in zip(edges, edges[1:])): raise ValueError("fraction baselines cannot partition the source crop")
    rows, fractions, bodies, risks = [], [], [], []
    def risk(code, row_id, slot_ids, component_ids=(), threshold=None, detail=None):
        risks.append(dict(code=code, row_id=row_id, slot_ids=list(slot_ids), component_ids=list(component_ids), threshold=threshold,
                          detail=copy.deepcopy(detail), blocks=["AUTOMATIC_CONTENT_ACCEPTANCE"]))
    for index, group in enumerate(groups):
        box = [crop_box[0], edges[index], crop_box[2], edges[index+1]]
        rid = "region-row-"+digest([reference(frozen), baselines[index], box])[:24]
        fallback = dict(slot_id=_slot_id(frozen, "FULL_ROW_FALLBACK", rid, box), kind="FULL_ROW_FALLBACK", row_id=rid,
                        source_bbox=list(box), recognition_bbox=list(box), **_crop(image, crop_box, box))
        row = dict(row_id=rid, baseline_y=baselines[index], source_bbox=box, slot_ids=[], full_row_fallback=fallback)
        current = []
        for f in sorted(group["fractions"], key=lambda f: (f["bar_bbox"][0], f["fraction_id"])):
            fb = _union([f["bar_bbox"], f["numerator"]["pixel_bbox"], f["denominator"]["pixel_bbox"]])
            slot = dict(slot_id=_slot_id(frozen, "FRACTION", rid, fb, f["fraction_id"]), kind="FRACTION", row_id=rid,
                fraction_id=f["fraction_id"], source_bbox=fb, bar_bbox=copy.deepcopy(f["bar_bbox"]), numerator_bbox=copy.deepcopy(f["numerator"]["pixel_bbox"]),
                denominator_bbox=copy.deepcopy(f["denominator"]["pixel_bbox"]), source_ocr_refs={role: copy.deepcopy(f[role]["ocr_refs"]) for role in ("numerator", "denominator")},
                ambiguous_ocr_refs=copy.deepcopy(f.get("ambiguous_ocr_refs", [])))
            fractions.append(slot); current.append(slot)
            if not _inside(fb, box): risk("FRACTION_CROSSES_ROW_BAND", rid, [slot["slot_id"]], detail={"fraction_bbox": fb, "row_bbox": box})
        for i, left in enumerate(current):
            for right in current[i+1:]:
                if _overlap(left["source_bbox"], right["source_bbox"]):
                    risk("FRACTION_SLOT_OVERLAP", rid, [left["slot_id"], right["slot_id"]], detail={"left": left["source_bbox"], "right": right["source_bbox"]})
        cursor, left_ids = box[0], []
        for slot in sorted(current, key=lambda v: (v["source_bbox"][0], v["source_bbox"][2])):
            if slot["source_bbox"][0] > cursor:
                gap = [cursor, box[1], slot["source_bbox"][0], box[3]]
                bodies.append(dict(slot_id=_slot_id(frozen, "BODY_OR_WRAPPER", rid, gap), kind="BODY_OR_WRAPPER", row_id=rid,
                    source_bbox=gap, recognition_bbox=None, adjacent_fraction_ids=left_ids+[slot["fraction_id"]], component_ids=[], risks=[]))
            if slot["source_bbox"][2] >= cursor: cursor, left_ids = slot["source_bbox"][2], [slot["fraction_id"]]
        if cursor < box[2]:
            gap = [cursor, box[1], box[2], box[3]]
            bodies.append(dict(slot_id=_slot_id(frozen, "BODY_OR_WRAPPER", rid, gap), kind="BODY_OR_WRAPPER", row_id=rid,
                source_bbox=gap, recognition_bbox=None, adjacent_fraction_ids=left_ids, component_ids=[], risks=[]))
        row["slot_ids"] = [s["slot_id"] for s in sorted(current+[b for b in bodies if b["row_id"] == rid], key=lambda s: (s["source_bbox"][0], s["kind"]))]
        rows.append(row)
    primary = fractions+bodies; masks = []
    occupancy = np.zeros(gray.shape, dtype=np.int32)
    for slot in primary:
        mask = np.zeros(gray.shape, dtype=np.uint8); b = slot["source_bbox"]
        mask[b[1]-origin[1]:b[3]-origin[1], b[0]-origin[0]:b[2]-origin[0]] = 1
        masks.append(mask); occupancy += mask
    component_sets, coverage = [], []
    all_components = []
    for threshold in CONFIG["thresholds"]:
        ink = (gray < threshold).astype(np.uint8)
        _, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=CONFIG["connectivity"])
        components = []
        for label, (x, y, w, h, area) in enumerate(stats[1:], 1):
            x, y, w, h, area = map(int, (x, y, w, h, area)); bitmap = (labels[y:y+h, x:x+w] == label)
            b = [x+origin[0], y+origin[1], x+w+origin[0], y+h+origin[1]]
            memberships = []
            for slot, mask in zip(primary, masks):
                count = int(np.count_nonzero(mask[y:y+h, x:x+w] & bitmap))
                if count: memberships.append(dict(slot_id=slot["slot_id"], pixel_count=count))
            unowned = int(np.count_nonzero((occupancy[y:y+h, x:x+w] == 0) & bitmap))
            overlaps = int(np.count_nonzero((occupancy[y:y+h, x:x+w] > 1) & bitmap))
            owned = len(memberships) == 1 and memberships[0]["pixel_count"] == area and not unowned and not overlaps
            cid = "region-component-"+digest([reference(frozen), threshold, label, b, area])[:24]
            codes = []
            if len(memberships) > 1: codes.append("INK_CROSSES_SLOT_BOUNDARY")
            if unowned: codes.append("INK_OUTSIDE_PRIMARY_SLOTS")
            if overlaps: codes.append("OVERLAPPING_SLOT_INK")
            if b[0] == crop_box[0] or b[1] == crop_box[1] or b[2] == crop_box[2] or b[3] == crop_box[3]: codes.append("SOURCE_CROP_EDGE_INK")
            if any(b[1] < edge < b[3] for edge in edges[1:-1]): codes.append("ROW_BAND_CUTS_COMPONENT")
            component = dict(component_id=cid, bbox=b, pixel_count=area, pixel_sha256=hashlib.sha256(bitmap.astype(np.uint8).tobytes()).hexdigest(),
                memberships=memberships, uncovered_pixels=unowned, overlap_pixels=overlaps, status="OWNED" if owned else "RESIDUAL", risks=codes)
            components.append(component); all_components.append(component)
            for code in codes:
                related = [r["row_id"] for r in rows if _overlap(r["source_bbox"], b)]
                risk(code, related[0] if len(related) == 1 else None, [m["slot_id"] for m in memberships], [cid], threshold,
                     {"bbox": b, "pixel_count": area, "uncovered_pixels": unowned, "overlap_pixels": overlaps})
        total = int(ink.sum()); owned_pixels = sum(c["pixel_count"] for c in components if c["status"] == "OWNED")
        residual = sum(c["pixel_count"] for c in components if c["status"] == "RESIDUAL"); summed = sum(c["pixel_count"] for c in components)
        coverage.append(dict(threshold=threshold, ink_pixels=total, component_pixels=summed, owned_pixels=owned_pixels,
            residual_pixels=residual, uncovered_pixels=sum(c["uncovered_pixels"] for c in components), overlap_pixels=sum(c["overlap_pixels"] for c in components),
            pixel_accounting_closed=summed == total == owned_pixels+residual))
        component_sets.append(dict(threshold=threshold, ink_pixels=total, components=components))
    halo = max(CONFIG["horizontal_halo_minimum_pixels"], math.ceil(font*CONFIG["horizontal_halo_font_height_ratio"]))
    row_map = {r["row_id"]: r for r in rows}
    for slot in bodies:
        core = slot["source_bbox"]; row = row_map[slot["row_id"]]["source_bbox"]
        rec = [max(crop_box[0], core[0]-halo), row[1], min(crop_box[2], core[2]+halo), row[3]]
        while True:
            touching = [c for c in all_components if _overlap(c["bbox"], rec)]
            closed = [max(crop_box[0], min([rec[0]]+[c["bbox"][0] for c in touching])), rec[1],
                      min(crop_box[2], max([rec[2]]+[c["bbox"][2] for c in touching])), rec[3]]
            if rec == closed: break
            rec = closed
        slot["recognition_bbox"] = rec; slot.update(_crop(image, crop_box, rec))
        relevant = [c for c in all_components if any(m["slot_id"] == slot["slot_id"] for m in c["memberships"])]
        slot["component_ids"] = [c["component_id"] for c in relevant]
        slot["risks"] = sorted({code for c in relevant for code in c["risks"]})
    source = {k: copy.deepcopy(p[k]) for k in ("asset_id", "source_sha256", "source_size", "crop_bbox", "crop_sha256")}
    source["crop_rgb_sha256"] = _rgb_sha(image)
    payload = dict(layout_ref=reference(frozen), layout_archive=frozen, source=source, rows=rows, fraction_slots=fractions, body_slots=bodies,
        components_by_threshold=component_sets, coverage=coverage, risks=risks, decision="HOLD", complete=False, transcription_verified=False,
        business_acceptance=False, expected_text_consumed=False, graph_modified=False, platform_actions=[])
    producer = dict(module=__name__, version="0.1.0", code_sha256=code_digest(Path(__file__)), configuration=copy.deepcopy(CONFIG),
        configuration_sha256=digest(CONFIG), pixel_runtime={"opencv": cv2.__version__, "numpy": np.__version__, "Pillow": pillow_version})
    inputs = [reference(frozen)]
    if original_digest != digest(layout) or file_digest(Path(crop_path)) != p["crop_sha256"]:
        raise ValueError("layout or source crop changed during planning")
    return dict(schema_version=SCHEMA, kind="RegionRunsTrial", artifact_id="region-runs-"+digest([inputs, producer, payload])[:24], revision=1,
                book_id=frozen["book_id"], scope_id=frozen["scope_id"], input_refs=inputs, producer=producer, content_hash=digest(payload), payload=payload)
