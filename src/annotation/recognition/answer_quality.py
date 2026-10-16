"""Independent audits of answer-fragment provenance and source-line ownership.

This does not re-run the assembler. It compares actual fragments with the
declared coverage ledger and separately authored development expectations.
Available-OCR coverage is never treated as image/formula correctness.
"""
from collections import Counter, defaultdict
import hashlib
import re

from .baseline import valid_bbox


def audit_answers(evidence, graph, review):
    pages = {p["asset_id"]: p for p in evidence["payload"]["pages"]}
    units = {}
    raw_lines = {}
    for page in pages.values():
        for line in page["ocr_lines"]:
            units[line["line_id"]] = (page, line)
            if page["page_role"] == "answer":
                raw_lines[line["line_id"]] = (page, line)
        for line in page["answer_detail_lines"]:
            units[line["line_id"]] = (page, line)
    answers = graph["payload"]["answers"]
    issues = []

    def issue(code, scope, refs=(), detail=None, severity="ERROR"):
        issues.append(dict(code=code, scope_id=scope, evidence_refs=list(refs), detail=detail, severity=severity))

    actual_owners, actual_fragments = defaultdict(set), defaultdict(set)
    allocations = defaultdict(list)
    actual_allocations = defaultdict(list)
    by_answer = {a["answer_id"]: a for a in answers}
    if len(by_answer) != len(answers):
        issue("ANSWER_ID_REUSED", evidence["scope_id"])
    all_fragment_ids = set()
    parents_by_answer = defaultdict(set)
    multi_fragment, bounded = 0, 0
    for answer in answers:
        aid = answer["answer_id"]
        fragments = answer.get("fragments", [])
        if not fragments:
            issue("ANSWER_NO_FRAGMENTS", aid, answer.get("evidence_refs", []))
        if len(fragments) > 1:
            multi_fragment += 1
        if answer.get("assembly_status") == "BOUNDED":
            bounded += 1
        else:
            issue("ANSWER_ASSEMBLY_UNRESOLVED", aid, answer.get("evidence_refs", []), answer.get("assembly_status"))
        if answer.get("transcription_verified") is not False:
            issue("ANSWER_TRANSCRIPTION_STATUS_INVALID", aid, detail="Assembly cannot certify OCR transcription.")
        declared_refs = set(answer.get("evidence_refs", []))
        actual_refs = {r for f in fragments for r in f.get("evidence_refs", [])}
        if declared_refs != actual_refs:
            issue("ANSWER_AGGREGATE_EVIDENCE_MISMATCH", aid, sorted(declared_refs | actual_refs))
        compact = lambda value: re.sub(r"\s+", "", value)
        answer_text = "\n".join(f["text"] for f in fragments if f.get("role") == "answer" and not f.get("structural_marker"))
        explanation_text = "\n".join(f["text"] for f in fragments if f.get("role") == "explanation" and not f.get("structural_marker"))
        if compact(answer.get("text", "")) != compact(answer_text):
            issue("ANSWER_AGGREGATE_TEXT_MISMATCH", aid, sorted(actual_refs))
        if compact(answer.get("explanation_text", "")) != compact(explanation_text):
            issue("EXPLANATION_AGGREGATE_TEXT_MISMATCH", aid, sorted(actual_refs))
        region_ids = [r.get("fragment_id") for r in answer.get("regions", [])]
        if Counter(region_ids) != Counter(f["fragment_id"] for f in fragments):
            issue("ANSWER_REGIONS_MISMATCH", aid, sorted(actual_refs))
        fragment_by_id = {f["fragment_id"]: f for f in fragments}
        for region in answer.get("regions", []):
            fragment = fragment_by_id.get(region.get("fragment_id"))
            if fragment and any(region.get(key) != fragment.get(key) for key in
                                ("asset_id", "bbox", "column", "window_index", "role", "evidence_refs")):
                issue("ANSWER_REGION_PROJECTION_MISMATCH", aid, fragment["evidence_refs"], region.get("fragment_id"))
        if not answer.get("coarse_detail_agreement", False):
            issue("ANSWER_OCR_DISAGREEMENT", aid, sorted(actual_refs), severity="REVIEW")
        for fragment in fragments:
            fid = fragment["fragment_id"]
            if fid in all_fragment_ids:
                issue("ANSWER_FRAGMENT_ID_REUSED", aid, fragment.get("evidence_refs", []))
            all_fragment_ids.add(fid)
            role = fragment.get("role")
            if role not in {"answer", "explanation"}:
                issue("ANSWER_ROLE_INVALID", aid, fragment.get("evidence_refs", []), role)
            if not fragment.get("evidence_refs"):
                issue("ANSWER_FRAGMENT_WITHOUT_EVIDENCE", aid)
            for ref in fragment.get("evidence_refs", []):
                if ref not in units:
                    issue("UNKNOWN_ANSWER_FRAGMENT_EVIDENCE", aid, [ref])
                    continue
                page, line = units[ref]
                parent = line.get("parent_line_id", ref)
                parents_by_answer[aid].add(parent)
                actual_owners[parent].add(aid)
                actual_fragments[parent].add(fid)
                loc = line.get("location")
                if (page["page_role"] != "answer" or answer["book_id"] != evidence["book_id"]
                        or fragment["asset_id"] != page["asset_id"]
                        or not loc or loc["section_path"] != answer["section_path"]):
                    issue("ANSWER_FRAGMENT_SOURCE_MISMATCH", aid, [ref])
                if not valid_bbox(fragment["bbox"], page["source"]["width"], page["source"]["height"]):
                    issue("ANSWER_FRAGMENT_GEOMETRY_INVALID", aid, [ref])
                else:
                    # A fragment may retain a whole OCR box for a text-span
                    # split; it cannot silently invent a different source box.
                    if any(abs(a-b) > .01 for a,b in zip(fragment["bbox"], line["bbox"])):
                        issue("ANSWER_FRAGMENT_GEOMETRY_MISMATCH", aid, [ref])
                span = fragment.get("text_span", [0, len(line["text"])])
                if (not isinstance(span, list) or len(span) != 2
                        or any(type(v) is not int for v in span)
                        or not 0 <= span[0] < span[1] <= len(line["text"])):
                    issue("ANSWER_TEXT_SPAN_INVALID", aid, [ref], span)
                    continue
                if fragment.get("raw_text") != line["text"]:
                    issue("ANSWER_RAW_TEXT_MISMATCH", aid, [ref])
                if fragment["text"].strip() != line["text"][span[0]:span[1]].strip():
                    issue("ANSWER_TEXT_SOURCE_MISMATCH", aid, [ref])
                allocations[ref].append((span[0], span[1], aid, fid))
                actual_allocations[parent].append((aid, fid, tuple(fragment["evidence_refs"]), tuple(span)))
        explanation = [f for f in fragments if f.get("role") == "explanation"]
        body = [f for f in explanation if not f.get("structural_marker")]
        if bool(body) != bool(answer.get("explanation_present")):
            issue("ANSWER_EXPLANATION_FLAG_MISMATCH", aid)
        if explanation and not body:
            issue("EXPLANATION_BODY_MISSING", aid, [r for f in explanation for r in f["evidence_refs"]])
        # Explicit explanation evidence is mandatory; a worked solution's 解,
        # 解法 or 答 is not by itself an E region under the confirmed policy.
        if explanation and not any(re.search(r"(?:解析|分析|详解)\s*[:：]|[【\[]\s*(?:解析|分析|详解)\s*[】\]]", f.get("raw_text", ""))
                                   or re.fullmatch(r"\s*(?:解析|分析|详解)\s*", f.get("raw_text", "")) for f in explanation):
            issue("EXPLANATION_WITHOUT_MARKER", aid, [r for f in explanation for r in f["evidence_refs"]])

    for ref, spans in allocations.items():
        for i, first in enumerate(spans):
            for second in spans[i+1:]:
                if max(first[0], second[0]) < min(first[1], second[1]):
                    issue("ANSWER_EVIDENCE_REUSED", first[2], [ref], {"fragments": [first[3],second[3]]})
    # Without an independently bound coarse-to-detail character alignment, a
    # coarse text slice and a child detail box cannot prove non-overlap.
    for ref in allocations:
        parent = units[ref][1].get("parent_line_id")
        if parent in allocations:
            issue("ANSWER_COARSE_DETAIL_DOUBLE_USE", evidence["scope_id"], [parent, ref])

    ledger = graph["payload"].get("answer_coverage", [])
    counts = Counter(row["line_id"] for row in ledger)
    if set(counts) != set(raw_lines) or any(n != 1 for n in counts.values()):
        issue("ANSWER_COVERAGE_LEDGER_INVALID", evidence["scope_id"],
              detail={"missing": sorted(set(raw_lines)-set(counts)), "unexpected": sorted(set(counts)-set(raw_lines)),
                      "duplicated": sorted(k for k,v in counts.items() if v != 1)})
    unassigned = 0
    for row in ledger:
        ref = row["line_id"]
        if ref not in raw_lines:
            continue
        actual_a, actual_f = actual_owners[ref], actual_fragments[ref]
        if set(row.get("answer_ids", [])) != actual_a or set(row.get("fragment_ids", [])) != actual_f:
            issue("ANSWER_LEDGER_MISMATCH", evidence["scope_id"], [ref],
                  {"declared_answers": row.get("answer_ids", []), "actual_answers": sorted(actual_a)})
        declared_allocations = Counter((a.get("answer_id"), a.get("fragment_id"), tuple(a.get("evidence_refs", [])),
                                        tuple(a.get("text_span", []))) for a in row.get("allocations", []))
        if declared_allocations != Counter(actual_allocations[ref]):
            issue("ANSWER_ALLOCATION_MISMATCH", evidence["scope_id"], [ref])
        if row.get("status") == "CONSUMED" and not actual_a:
            issue("ANSWER_LEDGER_MISMATCH", evidence["scope_id"], [ref])
        if row.get("status") == "UNASSIGNED":
            unassigned += 1
            issue("ANSWER_UNASSIGNED_CONTENT", evidence["scope_id"], [ref], row.get("reason"), "REVIEW")
        elif row.get("status") not in {"CONSUMED", "EXCLUDED"}:
            issue("ANSWER_COVERAGE_STATUS_INVALID", evidence["scope_id"], [ref])
        if row.get("status") == "EXCLUDED" and actual_a:
            issue("ANSWER_LEDGER_MISMATCH", evidence["scope_id"], [ref])
        if row.get("status") == "EXCLUDED":
            text = re.sub(r"\s+", "", raw_lines[ref][1]["text"])
            known_titles = {re.sub(r"\s+", "", title) for entry in evidence["payload"].get("context", {}).get("pages", {}).values()
                            for window in entry.get("windows", []) for title in window["path"]}
            title = re.fullmatch(r"(?:参考答案|第[一二三四五六七八九十\d]+章|第\d+课时|小专题|☆?问题解决策略)", text)
            tier = re.fullmatch(r"(?:[A-C]?基础题|[A-C]?中档题|[A-C]?综合题|针对训练|巩固训练)", text)
            if not title and not tier and text not in known_titles:
                issue("ANSWER_EXCLUSION_WITHOUT_EVIDENCE", evidence["scope_id"], [ref], row.get("reason"))

    for case in review.get("multiline_checks", []):
        for asset_id, sha in case["asset_sha256"].items():
            if asset_id not in pages or pages[asset_id]["source"]["sha256"] != sha:
                raise ValueError("multiline review source hash mismatch")
        targets = [a for a in answers if a["section_path"] == case["section_path"]
                   and a["printed_number"] == case["printed_number"]]
        if len(targets) != 1:
            issue("ANSWER_REVIEW_TARGET_MISSING_OR_AMBIGUOUS", evidence["scope_id"], detail=case["case_id"])
            continue
        answer = targets[0]
        expected, actual = set(case["expected_source_line_ids"]), parents_by_answer[answer["answer_id"]]
        if expected != actual:
            issue("ANSWER_REFERENCE_COVERAGE_MISMATCH", answer["answer_id"], sorted(expected | actual),
                  {"case_id": case["case_id"], "missing": sorted(expected-actual), "unexpected": sorted(actual-expected)})
        for expected_span in case.get("expected_source_spans", []):
            source_ref = expected_span["line_id"]
            if source_ref not in units:
                raise ValueError("multiline span reference is absent from OCR evidence")
            source_text = units[source_ref][1]["text"]
            if hashlib.sha256(source_text.encode("utf-8")).hexdigest() != expected_span["source_text_sha256"]:
                raise ValueError("multiline span review OCR text hash mismatch; reference review is stale")
            observed = sorted([lo, hi] for lo,hi,owner,_ in allocations[source_ref] if owner == answer["answer_id"])
            if observed != expected_span["text_spans"]:
                issue("ANSWER_REFERENCE_SPAN_MISMATCH", answer["answer_id"], [source_ref],
                      {"expected": expected_span["text_spans"], "actual": observed, "case_id": case["case_id"]})
        for gap in case.get("observed_source_gaps", []):
            issue("ANSWER_SOURCE_OCR_GAP", answer["answer_id"], detail=gap, severity="REVIEW")
    ledger_by_ref = {row["line_id"]: row for row in ledger}
    for group in review.get("unresolved_source_groups", []):
        for asset_id, sha in group["asset_sha256"].items():
            if asset_id not in pages or pages[asset_id]["source"]["sha256"] != sha:
                raise ValueError("unresolved-source review hash mismatch")
        for line_id in group["source_line_ids"]:
            if actual_owners[line_id]:
                issue("UNRESOLVED_SOURCE_ASSIGNED", evidence["scope_id"], [line_id], group["case_id"])
            if ledger_by_ref.get(line_id, {}).get("status") != "UNASSIGNED":
                issue("UNRESOLVED_SOURCE_NOT_RETAINED", evidence["scope_id"], [line_id], group["case_id"])
    return issues, {"multiline_answers": sum(len(refs) > 1 for refs in parents_by_answer.values()),
                    "multi_fragment_answers": multi_fragment, "bounded_answer_candidates": bounded,
                    "answer_raw_lines": len(raw_lines), "unassigned_answer_lines": unassigned,
                    "explanation_candidates": sum(bool(a.get("explanation_present")) for a in answers),
                    "answer_fragment_count": sum(len(a.get("fragments", [])) for a in answers),
                    "ocr_transcription_verified": False}
