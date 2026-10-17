"""Conservative, provenance-preserving answer assembly for B trial artifacts.

This module consumes OCR evidence and reviewed semantic windows, never platform
boxes or historical answer links. ``complete`` describes a bounded assembly of
the *available* OCR, not a verified transcription or a claim that OCR saw every
formula. Every raw answer-page OCR line has one coverage-ledger row.

The public A/B contract is not frozen. These additive fields are B's internal
trial representation. A fragment keeps its original OCR element in ``raw_text``
and its exact character interval in ``text_span``; a line split into explicit
answer/explanation roles may therefore legitimately have disjoint spans sharing
the same source box. No per-character geometry is invented for that case.
"""
from __future__ import annotations

import re
import statistics


PRIMARY = re.compile(r"^\s*(\d{1,2})\s*[.．、]\s*(.+)$")
NUMBER_MARK = re.compile(r"(\d{1,2})\s*[.．、]")
TIER = re.compile(r"^(?:[A-C]?基础题|[A-C]?中档题|[A-C]?综合题|针对训练|巩固训练)\s*$")
TITLE = re.compile(r"^(?:参考答案|第[一二三四五六七八九十\d]+章|第\d+课时|小专题|☆?问题解决策略)")
ROLE_MARKER = re.compile(r"【(答案|解析|分析|详解)】\s*[:：]?|\[(答案|解析|分析|详解)\]\s*[:：]?|(答案|解析|分析|详解)(?:如下)?\s*[:：]")
BARE_ROLE = re.compile(r"^\s*(答案|解析|分析|详解)\s*$")
VARIANT = "【变式】"


def _compact(text):
    return re.sub(r"\s+", "", text).replace("．", ".").replace("、", ".")


def _union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _location(line):
    return line.get("location") or {}


def _role_pieces(raw, start, end, initial):
    """Return exact spans; 解/答/解法一/二 alone never create explanation."""
    pieces, role, cursor = [], initial, start
    bare = BARE_ROLE.fullmatch(raw[start:end])
    if bare:
        return [], "answer" if bare[1] == "答案" else "explanation"
    for marker in ROLE_MARKER.finditer(raw, start, end):
        if marker.start() > cursor and raw[cursor:marker.start()].strip():
            pieces.append((role, cursor, marker.start()))
        label = next(group for group in marker.groups() if group)
        role = "answer" if label == "答案" else "explanation"
        cursor = marker.end()
    if cursor < end and raw[cursor:end].strip():
        pieces.append((role, cursor, end))
    return pieces, role


def _has_embedded_answers(text):
    """A mixed coarse row cannot supply precise boxes for several answers.

    Decimal expressions such as 4.1=16.81 are deliberately not primary-answer
    evidence. Consecutive printed markers and at least one A--G response are a
    reason to leave an unsplit coarse row unresolved, not to synthesize boxes.
    """
    marks = list(NUMBER_MARK.finditer(text))
    if len(marks) < 2:
        return False
    first = PRIMARY.match(text)
    if first and re.search(str(int(first[1]) + 1) + r"\s*[.．、]", first[2]):
        # OCR may fuse scalar answer 3.8 and next marker 4. into '3.84.'.
        # Keep the mixed row unresolved instead of appending it to question 2.
        return True
    for left, right in zip(marks, marks[1:]):
        if int(right[1]) == int(left[1]) + 1:
            value = text[left.end():right.start()].strip()
            if re.match(r"^[A-G](?:$|[【（(\s])", value) or value in set("ABCDEFG"):
                return True
    return False


def _windows(page, evidence):
    context = evidence["payload"].get("context", {}).get("pages", {}).get(page["asset_id"], {})
    known = {i: w for i, w in enumerate(context.get("windows", []))}
    # Tests/adapters can provide located lines without the reviewed-context
    # envelope. Their observed extents are not promoted to explicit boundaries.
    for line in page.get("ocr_lines", []):
        loc = _location(line)
        if not loc or loc["window_index"] in known:
            continue
        selected = [a for a in page["ocr_lines"] if _location(a).get("window_index") == loc["window_index"]]
        known[loc["window_index"]] = {"column": loc["column"], "path": loc["section_path"],
                                     "y_range": [min(a["bbox"][1] for a in selected), max(a["bbox"][3] for a in selected)],
                                     "observed_extents_only": True}
    return sorted(known.items(), key=lambda item: (item[1]["column"], item[1]["y_range"][0], item[0]))


def _can_cross_column(page, current_window, next_window, current, next_lines):
    """Only the adjacent left-bottom -> right-top window of the same asset.

    Equal printed numbers alone never establish continuity. Page transitions
    require additional provenance that this trial does not have and remain OPEN.
    """
    if (current_window.get("observed_extents_only") or next_window.get("observed_extents_only")
            or current_window["column"] != 0 or next_window["column"] != 1
            or current_window["path"] != next_window["path"] or not next_lines):
        return False
    height = page["source"]["height"]
    first = next_lines[0]
    return (current["_bottom"] >= current_window["y_range"][1] - max(35, height * .025)
            and current_window["y_range"][1] >= height * .85
            and first["bbox"][1] <= next_window["y_range"][0] + 25
            and next_window["y_range"][0] <= height * .2
            and not PRIMARY.match(first["text"]) and not TIER.fullmatch(first["text"].strip())
            and not TITLE.match(first["text"].strip()))


def assemble_answers(evidence, make_id):
    """Return ``(answers, issues, raw_line_coverage)`` without mutating evidence.

    ``make_id(role, anchor)`` must be deterministic for this evidence revision.
    Status BOUNDED means observed spans have a next-question/explicit-heading or
    reviewed semantic boundary. OPEN means a missing boundary, suspicious gap,
    missing context, or unsupported continuation. AMBIGUOUS means available OCR
    cannot be assigned without guessing. Transcription always stays UNVERIFIED.
    """
    answers, issues, coverage = [], [], []
    ledger = {}
    exclusions = {item["line_id"]: item for item in evidence["payload"].get("reviewed_exclusions", [])}

    def issue(code, answer=None, refs=(), detail=None):
        item = {"code": code, "evidence_refs": list(refs)}
        if answer is not None:
            item["answer_id"] = answer["answer_id"]
            if code not in answer["assembly_flags"]:
                answer["assembly_flags"].append(code)
        if detail is not None:
            item["detail"] = detail
        issues.append(item)

    def mark_open(answer, code, refs=(), detail=None, ambiguous=False):
        if ambiguous or answer["assembly_status"] != "AMBIGUOUS":
            answer["assembly_status"] = "AMBIGUOUS" if ambiguous else "OPEN"
        issue(code, answer, refs, detail)

    def new_answer(page, line, number, anchor, dense=False):
        loc = line["location"]
        answer = {"answer_id": make_id("a", anchor), "book_id": evidence["book_id"],
                  "section_path": list(loc["section_path"]), "printed_number": str(number),
                  "asset_id": page["asset_id"], "text": "", "bbox": list(line["bbox"]),
                  "evidence_refs": [], "verification_status": "UNVERIFIED",
                  "coarse_detail_agreement": True, "variant_geometry_unresolved": False,
                  "complete": False, "assembly_status": "BOUNDED", "assembly_flags": [],
                  "fragments": [], "regions": [], "source_line_ids": [],
                  "explanation_present": False, "explanation_text": "",
                  "explanation_marker_present": False,
                  "transcription_verified": False, "continuations": [],
                  "boundary": None, "ocr_alternatives": [],
                  "_role": "answer", "_dense": dense, "_bottom": line["bbox"][3],
                  "_heights": [], "_last_line": None}
        answers.append(answer)
        return answer

    def add_element(answer, page, parent, element, start=0, end=None):
        if (parent.get("reading_order_status") == "UNRESOLVED_2D_FORMULA"
                and "ANSWER_2D_READING_ORDER_UNRESOLVED" not in answer["assembly_flags"]):
            mark_open(answer, "ANSWER_2D_READING_ORDER_UNRESOLVED", [parent["line_id"]],
                      "The recovered primary anchor is observed, but fractions and other elevated formula atoms lack a verified 2D reading order.")
        raw = element["text"]
        end = len(raw) if end is None else end
        pieces, final_role = _role_pieces(raw, start, end, answer["_role"])
        answer["_role"] = final_role
        structural_marker = False
        # A label on its own is observed structural evidence. Preserve its
        # exact source region without pretending it contains an explanation.
        if not pieces and start == 0 and end == len(raw) and (
                ROLE_MARKER.fullmatch(raw.strip()) or BARE_ROLE.fullmatch(raw)
                or raw.strip() == VARIANT):
            pieces, structural_marker = [(final_role, start, end)], True
        if len({role for role, _, _ in pieces}) > 1:
            mark_open(answer, "ANSWER_ROLE_REGIONS_UNSPLIT", [element["line_id"]],
                      "Explicit roles were split by text spans sharing one OCR box; separate role geometry is unverified.")
        loc = parent["location"]
        for role, lo, hi in pieces:
            # Trim only the display slice, retaining the complete original OCR
            # element and exact interval in the fragment.
            while lo < hi and raw[lo].isspace():
                lo += 1
            while hi > lo and raw[hi-1].isspace():
                hi -= 1
            if lo == hi:
                continue
            fragment = {"fragment_id": make_id("af", [answer["answer_id"], element["line_id"], lo, hi, role]),
                        "role": role, "content_type": "text", "asset_id": page["asset_id"],
                        "bbox": list(element["bbox"]), "text": raw[lo:hi], "raw_text": raw,
                        "text_span": [lo, hi], "column": loc["column"], "window_index": loc["window_index"],
                        "section_path": list(loc["section_path"]), "evidence_refs": [element["line_id"]],
                        "parent_line_id": parent["line_id"],
                        "structural_marker": structural_marker,
                        "geometry_precision": "OCR_ELEMENT" if lo == 0 and hi == len(raw) else "OCR_LINE_SHARED_TEXT_SPAN",
                        "verification_status": "UNVERIFIED"}
            answer["fragments"].append(fragment)
            answer["regions"].append({key: fragment[key] for key in
                                      ("fragment_id", "asset_id", "bbox", "column", "window_index", "role", "evidence_refs")})
            row = ledger[parent["line_id"]]
            row["status"], row["reason"] = "CONSUMED", "ASSIGNED_TO_ANSWER_FRAGMENTS"
            if answer["answer_id"] not in row["answer_ids"]:
                row["answer_ids"].append(answer["answer_id"])
            row["fragment_ids"].append(fragment["fragment_id"])
            row["allocations"].append({"answer_id": answer["answer_id"], "fragment_id": fragment["fragment_id"],
                                       "evidence_refs": fragment["evidence_refs"], "text_span": fragment["text_span"]})
        if pieces:
            if parent["line_id"] not in answer["source_line_ids"]:
                answer["source_line_ids"].append(parent["line_id"])
            answer["_bottom"] = max(answer["_bottom"], parent["bbox"][3])
            answer["_heights"].append(parent["bbox"][3] - parent["bbox"][1])
            answer["_last_line"] = parent["line_id"]

    def finish(answer, kind, refs=(), uncertain=False):
        if answer is None:
            return
        answer["boundary"] = {"kind": kind, "evidence_refs": list(refs)}
        if uncertain:
            mark_open(answer, "ANSWER_BOUNDARY_UNRESOLVED", refs,
                      "The available OCR does not prove that the answer ends at this edge.")

    def dense_parts(page, line, tokens, margin):
        starts = [(i, PRIMARY.match(token["text"])) for i, token in enumerate(tokens)
                  if PRIMARY.match(token["text"])]
        numbers = [int(match[1]) for _, match in starts]
        if (len(numbers) < 2 or starts[0][0] != 0
                or not all(b == a+1 for a, b in zip(numbers, numbers[1:]))
                or tokens[0]["bbox"][0] > margin + 12):
            return None
        result = []
        for k, (i, match) in enumerate(starts):
            end_index = starts[k+1][0] if k+1 < len(starts) else len(tokens)
            used = tokens[i:end_index]
            base = new_answer(page, line, match[1], [line["line_id"], i, 0], dense=True)
            target = base
            for j, token in enumerate(used):
                text_start = match.start(2) if j == 0 else 0
                pos = token["text"].find(VARIANT, text_start)
                if pos >= 0:
                    add_element(target, page, line, token, text_start, pos)
                    target = new_answer(page, line, match[1] + ":variant", [line["line_id"], i, 1], dense=True)
                    if pos or len(token["text"]) > len(VARIANT):
                        target["variant_geometry_unresolved"] = True
                        mark_open(target, "ANSWER_VARIANT_REGION_UNSPLIT", [token["line_id"]])
                    if token["text"].strip() == VARIANT:
                        add_element(target, page, line, token)
                    else:
                        add_element(target, page, line, token, pos+len(VARIANT))
                else:
                    add_element(target, page, line, token, text_start)
            targets = [base] + ([target] if target is not base else [])
            for item in targets:
                text = " ".join(f["text"] for f in item["fragments"] if f["role"] == "answer" and not f["structural_marker"])
                prefix = VARIANT if item is not base else match[1] + "."
                item["coarse_detail_agreement"] = _compact(prefix + text) in _compact(line["text"])
                finish(item, "DENSE_ROW_PARTITION", [line["line_id"]])
                result.append(item)
        return result

    for page in evidence["payload"]["pages"]:
        if page.get("page_role") != "answer":
            continue
        reviewed_windows = _windows(page, evidence)
        known_headings = {re.sub(r"\s+", "", title)
                          for _, window in reviewed_windows for title in window["path"]}
        for line in page.get("ocr_lines", []):
            text = line["text"].strip()
            explicit_heading = bool(line["line_id"] in exclusions or TIER.fullmatch(text) or TITLE.fullmatch(text)
                                    or re.sub(r"\s+", "", text) in known_headings)
            row = {"asset_id": page["asset_id"], "line_id": line["line_id"],
                   "status": "EXCLUDED" if explicit_heading else "UNASSIGNED",
                   "answer_ids": [], "fragment_ids": [], "allocations": [],
                   "reason": "EXPLICIT_TIER_OR_REVIEWED_TITLE" if explicit_heading else
                             "OUTSIDE_REVIEWED_SEMANTIC_WINDOWS" if not line.get("location") else "MISSING_PRIMARY_ANSWER_ANCHOR"}
            ledger[line["line_id"]] = row
            coverage.append(row)
        details = {}
        for token in page.get("answer_detail_lines", []):
            details.setdefault(token["parent_line_id"], []).append(token)
        for values in details.values():
            values.sort(key=lambda token: (token["bbox"][0], token["bbox"][1], token["line_id"]))
        windows = reviewed_windows
        grouped = {index: sorted((line for line in page.get("ocr_lines", [])
                                  if _location(line).get("window_index") == index),
                                 key=lambda line: tuple(line.get("assembly_order", [line["bbox"][1], line["bbox"][0], 0])) + (line["line_id"],))
                   for index, _ in windows}
        current, carry, expected_number = None, False, None
        for position, (index, window) in enumerate(windows):
            lines = grouped[index]
            if not carry:
                current, expected_number = None, None
            carry = False
            if not lines:
                continue
            margin = min(line["bbox"][0] for line in lines)
            for line in lines:
                text = line["text"].strip()
                row = ledger[line["line_id"]]
                if row["status"] == "EXCLUDED" or TIER.fullmatch(text) or TITLE.match(text):
                    finish(current, "TIER_BOUNDARY" if TIER.fullmatch(text) else "EXPLICIT_TITLE_BOUNDARY", [line["line_id"]])
                    current = None
                    row["status"], row["reason"] = "EXCLUDED", "EXPLICIT_TIER_OR_TITLE"
                    # Difficulty tiers usually retain sequence; a new training
                    # heading may restart it, so no global sequence is imposed.
                    continue
                tokens = details.get(line["line_id"], [])
                partition = dense_parts(page, line, tokens, margin)
                if partition:
                    finish(current, "NEXT_PRIMARY_ANSWER", [line["line_id"]])
                    current = None
                    expected_number = int(partition[-1]["printed_number"].split(":")[0]) + 1
                    continue
                if _has_embedded_answers(text):
                    row["reason"] = "AMBIGUOUS_EMBEDDED_ANSWER_MARKERS"
                    initial = PRIMARY.match(line["text"])
                    is_next_primary = (initial and line["bbox"][0] <= margin + 12
                                       and int(initial[1]) == expected_number)
                    if current and is_next_primary:
                        # The next number bounds the previous answer even when
                        # its own dense row cannot be split into precise boxes.
                        finish(current, "NEXT_PRIMARY_UNPARTITIONED_ROW", [line["line_id"]])
                        current = None
                    issue("AMBIGUOUS_EMBEDDED_ANSWER_MARKERS", current, [line["line_id"]],
                          "Coarse OCR mixes answer identities without a reliable detail-token partition.")
                    if current:
                        current["assembly_status"] = "AMBIGUOUS"
                    continue
                match = PRIMARY.match(line["text"])
                is_primary = False
                reviewed_primary = match and line.get("reviewed_primary_number") == match[1]
                if match and (line["bbox"][0] <= margin + 12 or reviewed_primary):
                    value = match[2]
                    # Prefixes inside decimals/fractions or solution arithmetic
                    # are not a primary number just because they contain a dot.
                    semantic_value = bool(re.match(r"[\u4e00-\u9fffA-G（(【]", value))
                    numeric_value = bool(re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:cm|mm|m|km|°)?", value.strip()))
                    is_primary = reviewed_primary or semantic_value or (numeric_value and (int(match[1]) == expected_number
                                                                                  or current is None and int(match[1]) == 1))
                if is_primary:
                    finish(current, "NEXT_PRIMARY_ANSWER", [line["line_id"]])
                    current = new_answer(page, line, match[1], [line["line_id"], "coarse"])
                    expected_number = int(match[1]) + 1
                    add_element(current, page, line, line, match.start(2))
                    if tokens:
                        detail_text = " ".join(token["text"] for token in tokens)
                        current["ocr_alternatives"].append({"parent_line_id": line["line_id"],
                                                            "coarse_text": line["text"],
                                                            "detail_texts": [token["text"] for token in tokens],
                                                            "detail_evidence_refs": [token["line_id"] for token in tokens]})
                        current["coarse_detail_agreement"] = _compact(detail_text) == _compact(line["text"])
                    continue
                if current is None:
                    issue("UNASSIGNED_ANSWER_OCR_LINE", refs=[line["line_id"]],
                          detail="No trustworthy primary answer anchor in this semantic window.")
                    continue
                height = statistics.median(current["_heights"]) if current["_heights"] else 18
                gap = line["bbox"][1] - current["_bottom"]
                if gap > max(24, height * 1.3):
                    mark_open(current, "ANSWER_SPATIAL_GAP_UNRESOLVED", [current["_last_line"], line["line_id"]],
                              {"gap_pixels": gap, "reason": "Missing OCR/formula/variant content is possible; no text was inferred."})
                if "上题" in text and not any(VARIANT in f["raw_text"] for f in current["fragments"]):
                    mark_open(current, "ANSWER_REFERENTIAL_CONTEXT_UNRESOLVED", [line["line_id"]],
                              "A reference to a prior problem/variant has no observed local boundary.")
                add_element(current, page, line, line)
            if current is None:
                continue
            if position+1 < len(windows):
                next_index, next_window = windows[position+1]
                next_lines = grouped[next_index]
                # It must also be the last left window and first right window:
                # adjacency in this ordered list provides that physical check.
                if _can_cross_column(page, window, next_window, current, next_lines):
                    current["continuations"].append({"kind": "CROSS_COLUMN", "asset_id": page["asset_id"],
                                                      "from_window_index": index, "to_window_index": next_index,
                                                      "evidence_refs": [current["_last_line"], next_lines[0]["line_id"]],
                                                      "basis": "same reviewed semantic scope + adjacent left-bottom/right-top windows"})
                    current["_bottom"] = next_window["y_range"][0]
                    current["_heights"] = []
                    carry = True
                    continue
                # A reviewed semantic section boundary bounds assignment. It
                # does not certify absent formula rows inside that assignment.
                changed_scope = window["path"] != next_window["path"]
                column_edge = window["column"] != next_window["column"]
                finish(current, "COLUMN_EDGE" if column_edge else "SECTION_WINDOW_END" if changed_scope else "WINDOW_EDGE",
                       [current["_last_line"]], uncertain=column_edge or not changed_scope or window.get("observed_extents_only", False))
            else:
                finish(current, "ANSWER_PAGE_EDGE", [current["_last_line"]], uncertain=True)
            current = None

    for answer in answers:
        fragments = answer["fragments"]
        separator = " " if answer["_dense"] else "\n"
        answer["text"] = separator.join(f["text"] for f in fragments if f["role"] == "answer" and not f["structural_marker"])
        answer["explanation_text"] = "\n".join(f["text"] for f in fragments if f["role"] == "explanation" and not f["structural_marker"])
        answer["explanation_present"] = any(f["role"] == "explanation" and not f["structural_marker"] for f in fragments)
        answer["explanation_marker_present"] = any(
            f["role"] == "explanation" and (f["structural_marker"] or ROLE_MARKER.search(f["raw_text"])) for f in fragments)
        if answer["explanation_marker_present"] and not answer["explanation_present"]:
            mark_open(answer, "EXPLANATION_BODY_MISSING", answer["source_line_ids"],
                      "An explicit explanation marker was observed, but no explanation body was available before the boundary.")
        if not answer["text"]:
            mark_open(answer, "ANSWER_BODY_MISSING", answer["source_line_ids"])
        answer["evidence_refs"] = list(dict.fromkeys(ref for fragment in fragments for ref in fragment["evidence_refs"]))
        if fragments:
            first = fragments[0]
            local_boxes = [f["bbox"] for f in fragments if f["asset_id"] == first["asset_id"] and f["column"] == first["column"]]
            answer["bbox"] = _union(local_boxes)
            answer["bbox_scope"] = "ANCHOR_COLUMN_ONLY" if answer["continuations"] else "SINGLE_COLUMN"
        answer["complete"] = answer["assembly_status"] == "BOUNDED" and bool(answer["text"])
        answer["assembly_flags"].sort()
        for key in [key for key in answer if key.startswith("_")]:
            del answer[key]
    return answers, issues, coverage
