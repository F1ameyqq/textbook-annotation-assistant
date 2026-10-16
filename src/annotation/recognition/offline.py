"""Offline, conservative assembly experiment. No platform or history-box input.

Section windows are explicit, reviewed development input, not inferred directory
IDs. These formats must be adapted when the shared A/B contract is executable.
"""
from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .baseline import code_digest, digest, legacy_backend, load_source, valid_bbox
from .policy import classify, choice_answer_valid, option_set_valid

CONTEXT_SCHEMA = "b-context-trial/0.1"
EVIDENCE_SCHEMA = "b-evidence-trial/0.2"
GRAPH_SCHEMA = "b-graph-trial/0.1"
CHECK_SCHEMA = "b-check-trial/0.1"
QSTART = re.compile(r"^\s*(\d{1,2})\s*[.．、]\s*(?=[\u4e00-\u9fffA-Za-z（(])")
ASTART = re.compile(r"^\s*(\d{1,2})\s*[.．、]\s*(.+)$")
OPTION = re.compile(r"^\s*([A-G])[.．、]")
CAPTION = re.compile(r"^第\s*(\d{1,2})\s*题图$")
DECORATION = re.compile(r"^(?:[A-C]?基础题|[A-C]?中档题|[A-C]?综合题|知识点|易错点)")


def artifact(schema, kind, source, payload, inputs, producer):
    identity = digest({"schema": schema, "source": source, "payload": payload,
                       "inputs": inputs, "producer": producer})
    return {"schema_version": schema, "kind": kind,
            "artifact_id": kind.lower() + "-" + identity[:24], "revision": 1,
            "run_id": source.get("run_id") or "b-run-" + digest({"source": source, "inputs": inputs})[:24],
            "book_id": source["book_id"], "scope_id": source["scope_id"],
            "input_refs": inputs, "producer": producer,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": digest(payload), "payload": payload}


def ref(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def check_artifact(value, schemas):
    if value.get("schema_version") not in schemas:
        raise ValueError("unsupported provisional artifact schema")
    if value.get("content_hash") != digest(value.get("payload")):
        raise ValueError("artifact payload hash mismatch")
    if type(value.get("revision")) is not int or value["revision"] < 1:
        raise ValueError("invalid artifact revision")


def validate_context(source, context):
    if context.get("schema_version") != CONTEXT_SCHEMA:
        raise ValueError("unsupported context schema")
    if (context.get("book_id"), context.get("scope_id")) != (source["book_id"], source["scope_id"]):
        raise ValueError("context book/scope mismatch")
    assets = {a["asset_id"]: a for a in source["assets"]}
    if set(context.get("pages", {})) != set(assets):
        raise ValueError("context must explicitly cover every input asset")
    for aid, page in context["pages"].items():
        if page.get("sha256") != assets[aid]["sha256"]:
            raise ValueError("context asset hash mismatch")
        windows = page.get("windows", [])
        if page.get("role") not in {"question", "answer"} or not windows:
            raise ValueError("context needs page role and section windows")
        for w in windows:
            lo, hi = w["y_range"]
            if (w["column"] not in (0, 1) or not 0 <= lo < hi <= assets[aid]["height"]
                    or not w.get("path") or any(not isinstance(s, str) or not s for s in w["path"])):
                raise ValueError("invalid context window")
        for i, a in enumerate(windows):
            for b in windows[i + 1:]:
                if a["column"] == b["column"] and max(a["y_range"][0], b["y_range"][0]) < min(a["y_range"][1], b["y_range"][1]):
                    raise ValueError("overlapping context windows")


def detect_columns(mask, lines):
    """Central gutter candidate, confirmed by OCR boxes on both sides.

    Unlike the legacy aspect-ratio shortcut, portrait pages are eligible. This
    supports two columns only. Crossing body text rejects the split explicitly.
    """
    h, w = mask.shape
    band = mask[int(.18 * h):int(.94 * h)]
    ink = band.mean(axis=0)
    candidates = range(int(.46 * w), int(.54 * w))
    cut = min(candidates, key=lambda x: (float(ink[max(0, x-3):x+4].mean()), abs(x-w/2)))
    crossing = [a for a in lines if a["bbox"][0] < cut < a["bbox"][2]
                and a["bbox"][3] > .2 * h]
    left = sum(a["bbox"][2] <= cut for a in lines)
    right = sum(a["bbox"][0] >= cut for a in lines)
    accepted = ink[max(0, cut-3):cut+4].mean() < .015 and left >= 4 and right >= 4 and not crossing
    return {"mode": "two_columns" if accepted else "UNRESOLVED_LAYOUT",
            "cut_x": int(cut), "body_crossing_boxes": len(crossing),
            "left_ocr_boxes": left, "right_ocr_boxes": right,
            "method": "central_gutter+ocr_box_separation", "verified": False}


def locate(line, layout, windows):
    x1, y1, x2, y2 = line["bbox"]
    cut = layout["cut_x"]
    if x1 < cut < x2:
        return None
    column, y = int((x1 + x2) / 2 >= cut), (y1 + y2) / 2
    for i, window in enumerate(windows):
        if window["column"] == column and window["y_range"][0] <= y < window["y_range"][1]:
            return {"column": column, "window_index": i, "section_path": window["path"]}
    return None


def refine(source_path, baseline, context):
    """Validate cached OCR against actual local bytes, then refine dense answers."""
    source, inputs = load_source(source_path)
    validate_context(source, context)
    check_artifact(baseline, {"b-evidence-trial/0.1"})
    if not baseline.get("producer", {}).get("ocr_enabled"):
        raise ValueError("baseline OCR evidence is required")
    if (baseline["book_id"], baseline["scope_id"]) != (source["book_id"], source["scope_id"]):
        raise ValueError("cached evidence book/scope mismatch")
    if baseline["input_refs"] != [{"artifact_id": source["artifact_id"], "content_hash": digest(source)}]:
        raise ValueError("cached evidence source binding mismatch")
    by_id = {p["asset_id"]: p for p in baseline["payload"]["pages"]}
    if len(by_id) != len(inputs) or set(by_id) != {a["asset_id"] for a, _ in inputs}:
        raise ValueError("cached evidence page set mismatch")
    backend, pages = legacy_backend(), []
    for asset, path in inputs:
        original = by_id[asset["asset_id"]]
        if original["source"] != asset:
            raise ValueError("cached evidence asset descriptor mismatch")
        rgb = np.array(Image.open(path).convert("RGB"))
        lines = copy.deepcopy(original["ocr_lines"])
        if any(not valid_bbox(a["bbox"], asset["width"], asset["height"]) for a in lines):
            raise ValueError("invalid OCR box")
        layout = detect_columns(np.array(Image.open(path).convert("L")) < 160, lines)
        page_context = context["pages"][asset["asset_id"]]
        for i, line in enumerate(lines):
            line["line_id"] = f"{asset['asset_id']}/ocr/{i}"
            line["location"] = locate(line, layout, page_context["windows"]) if layout["mode"] == "two_columns" else None
        detail = []
        if page_context["role"] == "answer":
            for line in lines:
                # Re-detect a single row at 3x so printed marker 4.13 is not
                # fused with neighbours into '...244.135.640'. Never rewrite it.
                if not line["location"] or not ASTART.match(line["text"]):
                    continue
                x1, y1, x2, y2 = line["bbox"]
                box = [max(0, int(x1)-4), max(0, int(y1)-2),
                       min(asset["width"], int(x2)+5), min(asset["height"], int(y2)+2)]
                crop = Image.fromarray(rgb).crop(box)
                scale = 3
                crop = crop.resize((crop.width*scale, crop.height*scale), Image.Resampling.LANCZOS)
                atoms = backend.ocr_atoms(np.array(crop)[:, :, ::-1].copy())
                for j, atom in enumerate(sorted(atoms, key=lambda a: a["bbox"][0])):
                    atom["bbox"] = [round(atom["bbox"][k] / scale + box[k % 2], 3) for k in range(4)]
                    atom.update(line_id=f"{line['line_id']}/detail/{j}", parent_line_id=line["line_id"],
                                location=line["location"], crop_to_original=[[1/scale, 0, box[0]], [0, 1/scale, box[1]], [0, 0, 1]])
                    detail.append(atom)
        pages.append({"asset_id": asset["asset_id"], "source": asset, "page_role": page_context["role"],
                      "layout": layout, "ocr_lines": lines, "answer_detail_lines": detail,
                      "unscoped_line_ids": [a["line_id"] for a in lines if not a["location"]]})
    payload = {"pages": pages, "quality_decision": "NOT_EVALUATED",
               "context": context, "history_annotations_consumed": False,
               "limitations": ["Reviewed section windows are development input, not automatic directory recognition.",
                               "OCR and figure candidates are unverified; two-column layouts only."]}
    return artifact(EVIDENCE_SCHEMA, "EvidenceBundleTrial", source, payload,
                    [ref(baseline), {"artifact_id": context["artifact_id"], "content_hash": digest(context)}],
                    {"module": __name__, "version": "0.2.0", "code_sha256": code_digest(Path(__file__)),
                     "baseline_producer": baseline["producer"], "answer_row_scale": 3})


def entity_id(evidence, role, anchor):
    return role + "-" + digest({"evidence": ref(evidence), "role": role, "anchor": anchor})[:24]


def scope_key(book, path, number):
    return (book, tuple(path), str(number))


def assemble(evidence):
    check_artifact(evidence, {EVIDENCE_SCHEMA})
    questions, answers, assembly_issues = [], [], []
    for page in evidence["payload"]["pages"]:
        lines = sorted((a for a in page["ocr_lines"] if a.get("location")),
                       key=lambda a: (a["location"]["column"], a["bbox"][1], a["bbox"][0]))
        if page["page_role"] == "question":
            current, captions = None, []
            for line in lines:
                text, loc = line["text"], line["location"]
                if CAPTION.fullmatch(text):
                    captions.append(line)
                    continue
                if DECORATION.match(text):
                    continue
                match = QSTART.match(text)
                variant = text.startswith("【变式】") and current is not None
                if match or variant:
                    number = match[1] if match else current["printed_number"] + ":variant"
                    parent_id = current["question_id"] if variant else None
                    current = {"question_id": entity_id(evidence, "q", line["line_id"]),
                               "book_id": evidence["book_id"], "section_path": loc["section_path"],
                               "printed_number": number, "parent_question_id": parent_id,
                               "anchor_ref": line["line_id"], "asset_id": page["asset_id"],
                               "fragments": [], "candidate_answer_ids": [], "selected_answer_id": None,
                               "verification_status": "UNVERIFIED", "flags": []}
                    questions.append(current)
                if current is None or current["section_path"] != loc["section_path"]:
                    assembly_issues.append({"code": "ORPHAN_TEXT", "evidence_refs": [line["line_id"]]})
                    continue
                if current["fragments"] and current["fragments"][-1]["column"] != loc["column"]:
                    current["flags"].append("CROSS_COLUMN_CONTINUATION")
                opt = OPTION.match(text)
                previous = current["fragments"][-1] if current["fragments"] else None
                continuation = (not opt and previous and previous["role"] == "option"
                                and previous["column"] == loc["column"]
                                and 0 <= line["bbox"][1] - previous["bbox"][3] <= 1.2 * (previous["bbox"][3]-previous["bbox"][1]))
                current["fragments"].append({"fragment_id": entity_id(evidence, "f", line["line_id"]),
                                             "role": "option" if opt or continuation else "stem", "content_type": "text",
                                             "option_label": opt[1] if opt else previous["option_label"] if continuation else None,
                                             "option_start": bool(opt), "column": loc["column"],
                                             "bbox": line["bbox"], "asset_id": page["asset_id"],
                                             "text": text, "evidence_refs": [line["line_id"]]})
            for caption in captions:
                number = CAPTION.fullmatch(caption["text"])[1]
                targets = [q for q in questions if q["asset_id"] == page["asset_id"] and
                           q["section_path"] == caption["location"]["section_path"] and q["printed_number"] == number]
                if len(targets) == 1:
                    targets[0]["fragments"].append({"fragment_id": entity_id(evidence, "caption", caption["line_id"]),
                                                   "role": "figure_caption", "content_type": "text",
                                                   "asset_id": page["asset_id"], "column": caption["location"]["column"],
                                                   "bbox": caption["bbox"], "text": caption["text"],
                                                   "evidence_refs": [caption["line_id"]]})
                    targets[0]["flags"].append("FIGURE_EXTENT_UNVERIFIED")
        else:
            details = {}
            for token in page["answer_detail_lines"]:
                details.setdefault(token["parent_line_id"], []).append(token)
            for line in lines:
                if not ASTART.match(line["text"]):
                    continue
                tokens = details.get(line["line_id"], [])
                starts = [(i, ASTART.match(a["text"])) for i, a in enumerate(tokens) if ASTART.match(a["text"])]
                sequence = [int(m[1]) for _, m in starts]
                # Decimal values inside solutions must not become answer IDs.
                dense_ok = len(sequence) >= 2 and all(b == a+1 for a, b in zip(sequence, sequence[1:]))
                if not dense_ok:
                    m = ASTART.match(line["text"])
                    if not m[2].startswith(("解", "能", "合格", "不合格")):
                        assembly_issues.append({"code": "AMBIGUOUS_ANSWER_ROW", "evidence_refs": [line["line_id"]]})
                        continue
                    starts, tokens = [(0, m)], [line]
                for k, (i, m) in enumerate(starts):
                    end = starts[k+1][0] if k+1 < len(starts) else len(tokens)
                    used = tokens[i:end]
                    value = " ".join([m[2]] + [a["text"] for a in used[1:]])
                    variant_parts = re.split(r"【变式】", value, maxsplit=1)
                    variant_boundary = next((j for j, a in enumerate(used) if a["text"].startswith("【变式】")), None)
                    for v, val in enumerate(variant_parts):
                        selected_tokens = (used[:variant_boundary] if not v else used[variant_boundary:]) if variant_boundary else used
                        coarse_text = re.sub(r"\s+", "", line["text"])
                        token_text = re.sub(r"\s+", "", ("【变式】" if v else m[1] + ".") + val)
                        agreement = token_text in coarse_text.replace("．", ".").replace("、", ".")
                        answers.append({"answer_id": entity_id(evidence, "a", [line["line_id"], i, v]),
                                        "book_id": evidence["book_id"], "section_path": line["location"]["section_path"],
                                        "printed_number": m[1] + (":variant" if v else ""),
                                        "asset_id": page["asset_id"], "text": val.strip(),
                                        "bbox": [min(a["bbox"][0] for a in selected_tokens), min(a["bbox"][1] for a in selected_tokens),
                                                 max(a["bbox"][2] for a in selected_tokens), max(a["bbox"][3] for a in selected_tokens)],
                                        "evidence_refs": [a["line_id"] for a in selected_tokens],
                                        "variant_geometry_unresolved": len(variant_parts) > 1 and not variant_boundary,
                                        "verification_status": "UNVERIFIED",
                                        "coarse_detail_agreement": agreement,
                                        "complete": dense_ok and bool(re.fullmatch(r"[A-G]+|\d+(?:\.\d+)?", val.strip()))})
    for q in questions:
        qkey = scope_key(q["book_id"], q["section_path"], q["printed_number"])
        candidates = [a for a in answers if scope_key(a["book_id"], a["section_path"], a["printed_number"]) == qkey]
        q["candidate_answer_ids"] = [a["answer_id"] for a in candidates]
        if len(candidates) == 1:
            q["selected_answer_id"] = candidates[0]["answer_id"]
        q["text"] = "\n".join(f["text"] for f in q["fragments"] if f["role"] != "figure_caption")
        q["type_candidate"] = classify(q["text"], [f["option_label"] for f in q["fragments"] if f.get("option_start")],
                                       candidates[0]["text"] if len(candidates) == 1 else None)
        if len(set(re.findall(r"[（(](\d+)[）)]", q["text"]))) > 1:
            q["flags"].append("SHARED_MATERIAL_STRUCTURE_REVIEW")
        q["flags"] = sorted(set(q["flags"]))
    payload = {"questions": questions, "answers": answers, "issues": assembly_issues,
               "matching": "book+reviewed_section_path+printed_number; unique candidate only",
               "unmatched_answer_ids": [a["answer_id"] for a in answers if not any(
                   a["answer_id"] in q["candidate_answer_ids"] for q in questions)],
               "selection_status": "DRAFT_UNVERIFIED", "platform_actions": []}
    return artifact(GRAPH_SCHEMA, "QuestionGraphTrial", evidence, payload, [ref(evidence)],
                    {"module": __name__ + ".assemble", "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
                     "policy_code_sha256": code_digest(Path(__file__).with_name("policy.py"))})


def scalar_issues(value, expected):
    # Whitespace is harmless; a colon changes mathematical meaning. No fuzzy
    # matching, ratio-to-number conversion or automatic repair is performed.
    normalized = re.sub(r"\s+", "", value)
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", normalized):
        return ["ANSWER_SCALAR_FORMAT"]
    return [] if abs(float(normalized) - float(expected)) < 1e-9 else ["ANSWER_VALUE_MISMATCH"]


def quality_check(evidence, graph, review):
    check_artifact(evidence, {EVIDENCE_SCHEMA})
    check_artifact(graph, {GRAPH_SCHEMA})
    if (graph["book_id"], graph["scope_id"], graph["input_refs"]) != (evidence["book_id"], evidence["scope_id"], [ref(evidence)]):
        raise ValueError("graph not bound to this evidence revision")
    if review.get("schema_version") != "b-review-trial/0.1":
        raise ValueError("unsupported review schema")
    if review.get("book_id") != evidence["book_id"] or review.get("scope_id") != evidence["scope_id"]:
        raise ValueError("review book/scope mismatch")
    pages = {p["asset_id"]: p for p in evidence["payload"]["pages"]}
    for aid, census in review["question_census"].items():
        if aid not in pages or census["sha256"] != pages[aid]["source"]["sha256"]:
            raise ValueError("review asset hash mismatch")
    issues = []

    def add(code, scope, refs=(), severity="ERROR", detail=None):
        issues.append({"issue_id": "issue-" + digest([code, scope, refs, detail])[:24],
                       "code": code, "scope_type": "question" if scope.startswith("q-") else "asset" if scope in pages else "scope",
                       "scope_id": scope, "evidence_refs": list(refs), "severity": severity,
                       "blocks": ["PRE_APPLY"], "suggested_strategy": "REVIEW_OFFLINE", "detail": detail})

    questions, answers = graph["payload"]["questions"], graph["payload"]["answers"]
    by_answer = {a["answer_id"]: a for a in answers}
    evidence_lines = {line["line_id"]: (p["asset_id"], line) for p in pages.values()
                      for line in p["ocr_lines"] + p["answer_detail_lines"]}
    keys = {}
    for q in questions:
        key = scope_key(q["book_id"], q["section_path"], q["printed_number"])
        keys.setdefault(key, []).append(q)
    coverage = []
    for aid, page in pages.items():
        if page["layout"]["mode"] != "two_columns":
            add("UNRESOLVED_LAYOUT", aid)
        if page["page_role"] != "question":
            continue
        census = review["question_census"].get(aid)
        actual = [q["printed_number"] for q in questions if q["asset_id"] == aid and not q["parent_question_id"]]
        expected = census["printed_numbers"] if census else []
        if not census:
            add("NO_INDEPENDENT_CENSUS", aid)
        elif actual != expected:
            add("QUESTION_COVERAGE_MISMATCH", aid, detail={"expected": expected, "actual": actual})
        coverage.append({"asset_id": aid, "expected": expected, "actual": actual,
                         "census_matches": bool(census) and actual == expected,
                         "reference_quality": review["reference_quality"], "business_acceptance": False})
    for q in questions:
        qid, a = q["question_id"], by_answer.get(q["selected_answer_id"])
        key = scope_key(q["book_id"], q["section_path"], q["printed_number"])
        if q["book_id"] != evidence["book_id"] or q["asset_id"] not in pages:
            add("QUESTION_SOURCE_MISMATCH", qid, [q["anchor_ref"]])
        if q["anchor_ref"] not in evidence_lines or evidence_lines[q["anchor_ref"]][0] != q["asset_id"]:
            add("UNKNOWN_QUESTION_ANCHOR", qid, [q["anchor_ref"]])
        elif evidence_lines[q["anchor_ref"]][1]["location"]["section_path"] != q["section_path"]:
            add("QUESTION_SECTION_MISMATCH", qid, [q["anchor_ref"]])
        if len(keys[key]) != 1:
            add("DUPLICATE_QUESTION_IDENTITY", qid, [q["anchor_ref"]])
        if len(q["candidate_answer_ids"]) != 1 or not a:
            add("ANSWER_MISSING_OR_AMBIGUOUS", qid, [q["anchor_ref"]])
        elif scope_key(a["book_id"], a["section_path"], a["printed_number"]) != key:
            add("CROSS_SCOPE_ANSWER", qid, a["evidence_refs"])
        elif not a["complete"]:
            add("ANSWER_TRANSCRIPTION_INCOMPLETE", qid, a["evidence_refs"])
        if a and not a["coarse_detail_agreement"]:
            add("OCR_RECOGNITION_DISAGREEMENT", qid, a["evidence_refs"])
        if a and a["variant_geometry_unresolved"]:
            add("ANSWER_VARIANT_REGION_UNSPLIT", qid, a["evidence_refs"])
        if a and q["selected_answer_id"] not in q["candidate_answer_ids"]:
            add("INVALID_SELECTED_ANSWER", qid, a["evidence_refs"])
        if a and any(r not in evidence_lines or evidence_lines[r][0] != a["asset_id"] for r in a["evidence_refs"]):
            add("UNKNOWN_ANSWER_EVIDENCE", qid, a["evidence_refs"])
        labels = [f["option_label"] for f in q["fragments"] if f.get("option_start")]
        if labels and not option_set_valid(labels):
            add("OPTION_SET_INCOMPLETE", qid, [q["anchor_ref"]], detail=labels)
        if labels and a and not choice_answer_valid(a["text"], labels):
            add("CHOICE_ANSWER_FORMAT", qid, a["evidence_refs"], detail=a["text"])
        for flag in q["flags"]:
            add(flag, qid, [q["anchor_ref"]], "REVIEW")
        for fragment in q["fragments"]:
            src = pages.get(fragment["asset_id"], {}).get("source")
            if not src or not valid_bbox(fragment["bbox"], src["width"], src["height"]):
                add("INVALID_FRAGMENT_GEOMETRY", qid, fragment["evidence_refs"])
            if any(r not in evidence_lines or evidence_lines[r][0] != fragment["asset_id"] for r in fragment["evidence_refs"]):
                add("UNKNOWN_FRAGMENT_EVIDENCE", qid, fragment["evidence_refs"])
        # Figure and formula recognition are deliberately not certified by OCR confidence.
        if any(t in q["text"] for t in ("如图", "△", "²", "⊥")):
            add("FIGURE_OR_FORMULA_REVIEW", qid, [q["anchor_ref"]], "REVIEW")
        for case in review.get("answer_checks", []):
            if key != scope_key(evidence["book_id"], case["section_path"], case["printed_number"]):
                continue
            for aid, sha in case["asset_sha256"].items():
                if aid not in pages or pages[aid]["source"]["sha256"] != sha:
                    raise ValueError("answer-check source binding mismatch")
            if a:
                for code in scalar_issues(a["text"], case["expected_scalar"]):
                    add(code, qid, a["evidence_refs"], detail={"expected": case["expected_scalar"], "actual": a["text"], "case_id": case["case_id"]})
    # This independent development census catches a removed whole question, but
    # does not certify diagram extents, formula transcription or business truth.
    add("BUSINESS_REVIEW_REQUIRED", evidence["scope_id"], severity="REVIEW",
        detail="Development visual references and shared OCR are not independent business acceptance.")
    for item in graph["payload"]["issues"]:
        add(item["code"], evidence["scope_id"], item["evidence_refs"], "REVIEW")
    payload = {"stage": "PRE_APPLY", "decision": "HOLD", "issues": issues, "page_coverage": coverage,
               "reason": "Unverified offline draft; blocking issues require review. No platform actions authorized.",
               "summary": {"questions": len(questions), "answers": len(answers),
                           "unique_candidate_links": sum(q["selected_answer_id"] is not None for q in questions),
                           "issues": len(issues)}}
    return artifact(CHECK_SCHEMA, "CheckReportTrial", evidence, payload,
                    [ref(evidence), ref(graph), {"artifact_id": review["artifact_id"], "content_hash": digest(review)}],
                    {"module": __name__ + ".quality_check", "version": "0.1.0", "code_sha256": code_digest(Path(__file__))})


def draw_graph(source_path, graph):
    _, inputs = load_source(source_path)
    overlays = {}
    for asset, path in inputs:
        image = Image.open(path).convert("RGB")
        draw = ImageDraw.Draw(image)
        for q in graph["payload"]["questions"]:
            for f in q["fragments"]:
                if f["asset_id"] == asset["asset_id"]:
                    draw.rectangle(f["bbox"], outline="orange" if f["role"] == "figure_caption" else "red", width=2)
                    draw.text((f["bbox"][0], f["bbox"][1]-12), q["printed_number"], fill="blue")
        overlays[asset["asset_id"]] = image
    return overlays
