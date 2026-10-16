"""Source-bound two-dimensional math layout candidates, without formula repair.

Persistent horizontal pixel strokes must have glyph ink above and below before
they become fraction candidates. OCR elements are attached as complete source
objects; broad/overlapping OCR is never split into invented numerator text.
Reading groups contain fractions as nested units, so a raised numerator cannot
be flattened ahead of the preceding ordinary text. This is a layout candidate,
not a mathematical transcription, verified formula, or platform action.
"""
from __future__ import annotations

from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .baseline import code_digest, digest, file_digest, valid_bbox
from .recovery_apply import reference, validate_hypotheses

SCHEMA = "b-math-layout-trial/0.1"
CONFIG = {"thresholds": [180,190,200], "minimum_threshold_votes": 2,
          "minimum_bar_width_pixels": 12, "bar_width_to_ocr_height": 1.05,
          "maximum_bar_thickness_to_ocr_height": .3,
          "role_search_height_to_ocr_height": 1.5,
          "maximum_role_ocr_width_to_bar_width": 1.6}


def _overlap(a,b):
    return max(0,min(a[1],b[1])-max(a[0],b[0]))


def _union(boxes):
    return [min(b[0] for b in boxes),min(b[1] for b in boxes),
            max(b[2] for b in boxes),max(b[3] for b in boxes)]


def _identifier(role,source,key):
    return role+"-"+digest([source,key])[:24]


def _bound_inputs(source_asset,recovery,probe_id,crop_path,variant_id):
    if (recovery.get("schema_version") != "b-recovery-trial/0.1"
            or recovery.get("content_hash") != digest(recovery.get("payload"))):
        raise ValueError("unsupported or changed recovery evidence")
    probes = [p for p in recovery["payload"]["probes"] if p["probe_id"] == probe_id]
    if len(probes) != 1:
        raise ValueError("missing or duplicate math probe")
    probe = probes[0]
    if (source_asset["asset_id"] != probe["asset_id"]
            or source_asset["sha256"] != probe["source_sha256"]
            or [source_asset["width"],source_asset["height"]] != probe["source_size"]):
        raise ValueError("math probe belongs to another source asset")
    if not valid_bbox(probe["crop_bbox"],source_asset["width"],source_asset["height"]):
        raise ValueError("math source crop outside asset")
    if file_digest(Path(crop_path)) != probe["crop_sha256"]:
        raise ValueError("math crop bytes changed")
    image = Image.open(crop_path).convert("RGB")
    x1,y1,x2,y2 = probe["crop_bbox"]
    if image.size != (x2-x1,y2-y1):
        raise ValueError("math crop size does not match source transform")
    chosen = variant_id or probe.get("selected_variant_id")
    variants = [v for v in probe["variants"] if v["variant_id"] == chosen]
    if len(variants) != 1:
        raise ValueError("an explicit, unique recorded OCR variant is required")
    variant = variants[0]
    validate_hypotheses(probe,variant)
    for line in variant["ocr_lines"]:
        if (line["asset_id"] != source_asset["asset_id"]
                or line.get("location") != probe.get("location")
                or not valid_bbox(line["bbox"],source_asset["width"],source_asset["height"])):
            raise ValueError("math OCR source/geometry mismatch")
    return probe,variant,image


def _pixel_bars(gray,font_height):
    minimum = max(CONFIG["minimum_bar_width_pixels"],round(font_height*CONFIG["bar_width_to_ocr_height"]))
    maximum_thickness = max(2,round(font_height*CONFIG["maximum_bar_thickness_to_ocr_height"]))
    strokes = []
    for threshold in CONFIG["thresholds"]:
        ink = (gray < threshold).astype(np.uint8)
        horizontal = cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((1,minimum),np.uint8))
        _,_,stats,_ = cv2.connectedComponentsWithStats(horizontal,8)
        for x,y,w,h,area in stats[1:]:
            if w >= minimum and h <= maximum_thickness:
                strokes.append({"bbox":[int(x),int(y),int(x+w),int(y+h)],"threshold":threshold})
    # Components can break into several pieces at a lower threshold. A higher
    # threshold's continuous stroke may connect them; there is no gap closing
    # that could silently join an adjacent Chinese character into the bar.
    parents = list(range(len(strokes)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for i,a in enumerate(strokes):
        for j,b in enumerate(strokes[:i]):
            aa,bb = a["bbox"],b["bbox"]
            if (abs((aa[1]+aa[3]-bb[1]-bb[3])/2) <= 2
                    and _overlap([aa[0],aa[2]],[bb[0],bb[2]]) >= .65*min(aa[2]-aa[0],bb[2]-bb[0])):
                parents[find(i)] = find(j)
    groups = {}
    for i,stroke in enumerate(strokes):groups.setdefault(find(i),[]).append(stroke)
    persistent = []
    for values in groups.values():
        votes = sorted({v["threshold"] for v in values})
        if len(votes) < CONFIG["minimum_threshold_votes"]:continue
        persistent.append({"bbox":_union([v["bbox"] for v in values]),"threshold_votes":votes,
                           "component_boxes":[v["bbox"] for v in values]})
    return sorted(persistent,key=lambda b:(b["bbox"][1],b["bbox"][0]))


def _glyph_region(ink,box):
    h,w = ink.shape
    x1,y1,x2,y2 = [int(v) for v in box]
    x1,y1,x2,y2 = max(0,x1),max(0,y1),min(w,x2),min(h,y2)
    if x2 <= x1 or y2 <= y1:return None
    _,_,stats,_ = cv2.connectedComponentsWithStats(ink[y1:y2,x1:x2],8)
    glyphs = [[int(x+x1),int(y+y1),int(x+x1+cw),int(y+y1+ch)]
              for x,y,cw,ch,area in stats[1:] if ch >= 3 and area >= 3]
    return _union(glyphs) if glyphs else None


def _source_box(box,origin):
    return [box[0]+origin[0],box[1]+origin[1],box[2]+origin[0],box[3]+origin[1]]


def build_math_layout(source_asset,recovery,probe_id,crop_path,*,variant_id=None):
    """Build nested 2D reading groups from pixel evidence and unchanged OCR.

    No source-review/formula text is accepted as input. The complete original
    selected OCR elements, including mistakes, remain available in the payload.
    """
    probe,variant,image = _bound_inputs(source_asset,recovery,probe_id,crop_path,variant_id)
    lines = copy.deepcopy(variant["ocr_lines"])
    heights = [l["bbox"][3]-l["bbox"][1] for l in lines]
    font_height = float(np.median(heights)) if heights else 12.
    origin = probe["crop_bbox"][:2]
    gray = np.array(image.convert("L"))
    bars = _pixel_bars(gray,font_height)
    ink = (gray < CONFIG["thresholds"][1]).astype(np.uint8)
    # Remove every persistent horizontal stroke before asking for numerator and
    # denominator glyphs. Equal signs alone cannot act as each other's glyphs.
    for bar in bars:
        x1,y1,x2,y2 = bar["bbox"]
        ink[max(0,y1-1):min(ink.shape[0],y2+1),x1:x2] = 0
    identity = [source_asset["sha256"],probe["crop_sha256"],reference(recovery),probe_id,variant["variant_id"],CONFIG]
    fractions,rejected,issues = [],[],[]
    search = round(font_height*CONFIG["role_search_height_to_ocr_height"])
    for bar in bars:
        x1,y1,x2,y2 = bar["bbox"]
        numerator = _glyph_region(ink,[x1-2,y1-search,x2+2,y1])
        denominator = _glyph_region(ink,[x1-2,y2,x2+2,y2+search])
        if numerator is None or denominator is None:
            rejected.append({"bar_bbox":_source_box(bar["bbox"],origin),
                             "reason":"NO_GLYPH_INK_ABOVE_AND_BELOW","threshold_votes":bar["threshold_votes"]})
            continue
        fraction = {"fraction_id":_identifier("fraction",identity,bar["bbox"]),
                    "bar_bbox":_source_box(bar["bbox"],origin),"threshold_votes":bar["threshold_votes"],
                    "numerator":{"pixel_bbox":_source_box(numerator,origin),"ocr_refs":[],"raw_texts":[]},
                    "denominator":{"pixel_bbox":_source_box(denominator,origin),"ocr_refs":[],"raw_texts":[]},
                    "ambiguous_ocr_refs":[],"verification_status":"UNVERIFIED"}
        fractions.append(fraction)
    by_id = {l["line_id"]:l for l in lines}
    roles,ambiguous = {},{}
    for line in lines:
        x1,y1,x2,y2 = line["bbox"]
        cy = (y1+y2)/2
        candidates,wide = [],[]
        for fraction in fractions:
            bx1,by1,bx2,by2 = fraction["bar_bbox"]
            bar_y = (by1+by2)/2
            overlap = _overlap([x1,x2],[bx1,bx2])
            if overlap < .4*min(x2-x1,bx2-bx1):continue
            numerator = (cy < bar_y-max(1,font_height*.1) and cy >= bar_y-font_height*2
                         and y2 <= by2+font_height*.4)
            denominator = (cy > bar_y+font_height*.25 and cy <= bar_y+font_height*2
                           and y1 >= by1-font_height*.35)
            if not numerator and not denominator:continue
            role = "numerator" if numerator else "denominator"
            pixels = fraction[role]["pixel_bbox"]
            # A preceding row's denominator must not become the next row's
            # numerator merely because the search bands overlap vertically.
            if _overlap([y1,y2],[pixels[1],pixels[3]]) < min(2,.15*(y2-y1)):
                continue
            if (x2-x1 > CONFIG["maximum_role_ocr_width_to_bar_width"]*(bx2-bx1)
                    or overlap < .5*(x2-x1)):
                wide.append((fraction["fraction_id"],role))
            else:candidates.append((fraction["fraction_id"],role))
        if len(candidates) == 1 and not wide:
            fraction_id,role = candidates[0]
            roles[line["line_id"]] = (fraction_id,role)
            fraction = next(f for f in fractions if f["fraction_id"] == fraction_id)
            fraction[role]["ocr_refs"].append(line["line_id"])
            fraction[role]["raw_texts"].append(line["text"])
        elif candidates or wide:
            linked = sorted({fid for fid,role in candidates+wide})
            ambiguous[line["line_id"]] = linked
            for fraction in fractions:
                if fraction["fraction_id"] in linked:fraction["ambiguous_ocr_refs"].append(line["line_id"])
            issues.append({"code":"MATH_OCR_SPANS_MULTIPLE_ROLES","evidence_refs":[line["line_id"]],
                           "fraction_ids":linked})
    for fraction in fractions:
        for role in ("numerator","denominator"):
            fraction[role]["missing_ocr"] = not bool(fraction[role]["ocr_refs"])
            if fraction[role]["missing_ocr"]:
                issues.append({"code":"MATH_"+role.upper()+"_OCR_MISSING","fraction_id":fraction["fraction_id"],
                               "pixel_bbox":fraction[role]["pixel_bbox"],"evidence_refs":[]})
        fraction["status"] = "LAYOUT_TRANSCRIPTION_PARTIAL" if any(
            fraction[role]["missing_ocr"] for role in ("numerator","denominator")) or fraction["ambiguous_ocr_refs"] else "LAYOUT_WITH_OCR_UNVERIFIED"
    # Fraction bars establish ordinary-text baseline rows. A numerator belongs
    # inside a fraction unit, never in the row's top-level text sequence.
    rows = []
    for fraction in fractions:
        y = (fraction["bar_bbox"][1]+fraction["bar_bbox"][3])/2
        row = next((r for r in rows if abs(r["baseline_y"]-y) <= max(3,font_height*.3)),None)
        if row is None:
            row = {"baseline_y":y,"units":[]}
            rows.append(row)
        row["units"].append({"kind":"fraction","fraction_id":fraction["fraction_id"],
                             "x":fraction["bar_bbox"][0],"ocr_refs":fraction["numerator"]["ocr_refs"]+fraction["denominator"]["ocr_refs"]})
    coverage = []
    for line in lines:
        ref = line["line_id"]
        if ref in roles:
            fraction_id,role = roles[ref]
            coverage.append({"line_id":ref,"status":"FRACTION_"+role.upper(),"fraction_id":fraction_id})
            continue
        cy = (line["bbox"][1]+line["bbox"][3])/2
        row = min(rows,key=lambda r:abs(r["baseline_y"]-cy)) if rows else None
        if row is None or abs(row["baseline_y"]-cy) > font_height*1.5:
            row = {"baseline_y":cy,"units":[]}
            rows.append(row)
        kind = "ambiguous_ocr_span" if ref in ambiguous else "body"
        unit = {"kind":kind,"x":line["bbox"][0],"ocr_refs":[ref],"raw_text":line["text"]}
        if ref in ambiguous:unit["linked_fraction_ids"] = ambiguous[ref]
        row["units"].append(unit)
        coverage.append({"line_id":ref,"status":"AMBIGUOUS" if ref in ambiguous else "BODY"})
    rows.sort(key=lambda row:row["baseline_y"])
    for row in rows:
        row["units"].sort(key=lambda unit:(unit["x"],unit["kind"]))
        row["row_id"] = _identifier("math-row",identity,[row["baseline_y"],row["units"]])
        row["status"] = "LAYOUT_CANDIDATE_UNVERIFIED"
    payload = {"asset_id":source_asset["asset_id"],"source_sha256":source_asset["sha256"],
               "source_size":[source_asset["width"],source_asset["height"]],"crop_bbox":probe["crop_bbox"],
               "crop_sha256":probe["crop_sha256"],"probe_id":probe_id,"variant_id":variant["variant_id"],
               "source_ocr":lines,"fraction_candidates":fractions,"rejected_bar_candidates":rejected,
               "reading_groups":rows,"token_coverage":coverage,"issues":issues,
               "decision":"HOLD","layout_status":"PARTIAL" if issues else "LAYOUT_CANDIDATE_UNVERIFIED",
               "transcription_verified":False,"formula_text_reconstructed":False,"visual_formula_references_consumed":False,
               "platform_actions":[],"limitations":["Geometric grouping does not verify OCR characters, formulas or mathematical meaning.",
                 "Missing numerator/denominator text remains missing; no expected answer or visual LaTeX is inserted.",
                 "A nested layout candidate is not a complete linear formula or authority to submit annotations."]}
    inputs = [reference(recovery),{"asset_id":source_asset["asset_id"],"sha256":source_asset["sha256"]},
              {"crop_sha256":probe["crop_sha256"]}]
    producer = {"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__)),
                "configuration":CONFIG,"configuration_sha256":digest(CONFIG),"opencv_version":cv2.__version__,
                "numpy_version":np.__version__,"method":"persistent_horizontal_pixels+glyph_ink_above_below+whole_ocr_object_relations"}
    identity_hash = digest([inputs,producer,payload])
    return {"schema_version":SCHEMA,"kind":"MathLayoutTrial","artifact_id":"math-layout-"+identity_hash[:24],
            "revision":1,"run_id":recovery.get("run_id"),"book_id":recovery["book_id"],"scope_id":recovery["scope_id"],
            "input_refs":inputs,"producer":producer,"content_hash":digest(payload),
            "created_at":datetime.now(timezone.utc).isoformat(),"payload":payload}


def audit_math_layout(layout,source_asset,recovery,crop_path):
    """Check source identity and exact input-token accounting independently.

    This audits the provided structure and source pixels rather than producing a
    replacement layout. Full OCR tokens must occur exactly once in reading units;
    nested role declarations must agree with the coverage ledger and source text.
    """
    payload,issues = layout["payload"],[]
    def issue(code,refs=()):issues.append({"code":code,"evidence_refs":list(refs)})
    probe,variant,image = _bound_inputs(source_asset,recovery,payload["probe_id"],crop_path,payload["variant_id"])
    if layout.get("schema_version") != SCHEMA or layout.get("content_hash") != digest(payload):
        issue("MATH_LAYOUT_HASH_MISMATCH")
    if (payload["source_sha256"] != source_asset["sha256"] or payload["asset_id"] != source_asset["asset_id"]
            or payload["crop_sha256"] != probe["crop_sha256"] or payload["crop_bbox"] != probe["crop_bbox"]
            or layout["input_refs"][0] != reference(recovery)):
        issue("MATH_LAYOUT_SOURCE_MISMATCH")
    expected = {line["line_id"]:line for line in variant["ocr_lines"]}
    font_height = float(np.median([line["bbox"][3]-line["bbox"][1] for line in expected.values()])) if expected else 12.
    if payload["source_ocr"] != variant["ocr_lines"]:issue("MATH_SOURCE_OCR_CHANGED")
    fractions = {f["fraction_id"]:f for f in payload["fraction_candidates"]}
    if len(fractions) != len(payload["fraction_candidates"]):issue("MATH_FRACTION_ID_REUSED")
    pixel_ink = np.array(image.convert("L")) < CONFIG["thresholds"][1]
    origin = probe["crop_bbox"][:2]
    actual,declared = {},{}
    for fraction in fractions.values():
        box = fraction["bar_bbox"]
        if not valid_bbox(box,source_asset["width"],source_asset["height"]):
            issue("MATH_BAR_GEOMETRY_INVALID")
        local = [int(box[0]-origin[0]),int(box[1]-origin[1]),int(box[2]-origin[0]),int(box[3]-origin[1])]
        x1,y1,x2,y2 = local
        if (not 0 <= x1 < x2 <= image.width or not 0 <= y1 < y2 <= image.height
                or max(pixel_ink[y1:y2,x1:x2].mean(axis=1),default=0) < .6):
            issue("MATH_BAR_WITHOUT_PIXEL_SUPPORT")
        for role in ("numerator","denominator"):
            section = fraction[role]
            pixel_box = section["pixel_bbox"]
            px1,py1,px2,py2 = [int(v-origin[i%2]) for i,v in enumerate(pixel_box)]
            role_pixels_valid = (0 <= px1 < px2 <= image.width and 0 <= py1 < py2 <= image.height
                                 and pixel_ink[py1:py2,px1:px2].sum() >= 3
                                 and (pixel_box[3] <= box[1]+1 if role == "numerator" else pixel_box[1] >= box[3]-1))
            if not role_pixels_valid:issue("MATH_ROLE_PIXEL_REGION_INVALID",section["ocr_refs"])
            texts = []
            for ref in section["ocr_refs"]:
                actual.setdefault(ref,[]).append((fraction["fraction_id"],role))
                if ref not in expected:issue("MATH_UNKNOWN_OCR_REFERENCE",[ref])
                else:
                    texts.append(expected[ref]["text"])
                    ocr_box = expected[ref]["bbox"]
                    cy,bar_y = (ocr_box[1]+ocr_box[3])/2,(box[1]+box[3])/2
                    above = (cy < bar_y and ocr_box[3] <= box[3]+font_height*.4)
                    below = (cy > bar_y and ocr_box[1] >= box[1]-font_height*.35)
                    if (not (above if role == "numerator" else below)
                            or _overlap([ocr_box[0],ocr_box[2]],[pixel_box[0],pixel_box[2]]) < 2
                            or _overlap([ocr_box[1],ocr_box[3]],[pixel_box[1],pixel_box[3]]) < min(2,.15*(ocr_box[3]-ocr_box[1]))):
                        issue("MATH_ROLE_GEOMETRY_MISMATCH",[ref])
            if texts != section["raw_texts"]:issue("MATH_ROLE_TEXT_CHANGED",section["ocr_refs"])
    owned,fraction_occurrences = [],Counter()
    if [r["baseline_y"] for r in payload["reading_groups"]] != sorted(r["baseline_y"] for r in payload["reading_groups"]):
        issue("MATH_ROW_ORDER_INVALID")
    for row in payload["reading_groups"]:
        if [unit["x"] for unit in row["units"]] != sorted(unit["x"] for unit in row["units"]):
            issue("MATH_READING_POSITION_INVALID")
        for unit in row["units"]:
            owned.extend(unit["ocr_refs"])
            if unit["kind"] == "fraction":
                fraction = fractions.get(unit.get("fraction_id"))
                fraction_occurrences[unit.get("fraction_id")] += 1
                refs = fraction["numerator"]["ocr_refs"]+fraction["denominator"]["ocr_refs"] if fraction else []
                if unit["ocr_refs"] != refs:issue("MATH_READING_FRACTION_MISMATCH",unit["ocr_refs"])
                if fraction and unit["x"] != fraction["bar_bbox"][0]:issue("MATH_READING_POSITION_INVALID",unit["ocr_refs"])
                if fraction and abs(row["baseline_y"]-(fraction["bar_bbox"][1]+fraction["bar_bbox"][3])/2) > max(3,font_height*.35):
                    issue("MATH_ROW_BASELINE_MISMATCH",unit["ocr_refs"])
            else:
                for ref in unit["ocr_refs"]:
                    actual.setdefault(ref,[]).append((None,"ambiguous" if unit["kind"] == "ambiguous_ocr_span" else "body"))
                    if ref not in expected:issue("MATH_UNKNOWN_OCR_REFERENCE",[ref])
                    else:
                        if unit.get("raw_text") != expected[ref]["text"]:issue("MATH_BODY_TEXT_CHANGED",[ref])
                        if unit["x"] != expected[ref]["bbox"][0]:issue("MATH_READING_POSITION_INVALID",[ref])
                        if abs(row["baseline_y"]-(expected[ref]["bbox"][1]+expected[ref]["bbox"][3])/2) > font_height*1.5:
                            issue("MATH_ROW_BASELINE_MISMATCH",[ref])
    if set(fraction_occurrences) != set(fractions) or any(n != 1 for n in fraction_occurrences.values()):
        issue("MATH_FRACTION_READING_COVERAGE_MISMATCH")
    counts = Counter(owned)
    if set(counts) != set(expected) or any(n != 1 for n in counts.values()):
        issue("MATH_TOKEN_COVERAGE_MISMATCH",sorted(set(expected)^set(counts)))
    for row in payload["token_coverage"]:
        ref,status = row["line_id"],row["status"]
        declared.setdefault(ref,[]).append((row.get("fraction_id"),status.lower().replace("fraction_","")))
    if declared != actual:issue("MATH_ROLE_LEDGER_MISMATCH")
    if (payload.get("transcription_verified") is not False or payload.get("formula_text_reconstructed") is not False
            or payload.get("visual_formula_references_consumed") is not False):
        issue("MATH_FALSE_TRANSCRIPTION_CLAIM")
    return {"decision":"HOLD","geometry_and_token_coverage_valid":not issues,"issues":issues,
            "input_tokens":len(expected),"fraction_candidates":len(fractions),"transcription_verified":False}


def draw_math_layout(layout,crop_path):
    """Render original crop pixels plus bars and role regions for review."""
    image = Image.open(crop_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    origin = layout["payload"]["crop_bbox"][:2]
    for i,fraction in enumerate(layout["payload"]["fraction_candidates"]):
        for key,color in (("bar_bbox","red"),):
            box = fraction[key]
            local = [box[0]-origin[0],box[1]-origin[1],box[2]-origin[0],box[3]-origin[1]]
            draw.rectangle(local,outline=color,width=1)
            draw.text((local[0],max(0,local[1]-10)),str(i+1),fill=color)
        for role,color in (("numerator","blue"),("denominator","green")):
            box = fraction[role]["pixel_bbox"]
            draw.rectangle([box[0]-origin[0],box[1]-origin[1],box[2]-origin[0],box[3]-origin[1]],outline=color,width=1)
    return image
