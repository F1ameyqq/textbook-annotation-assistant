"""Shared independent question, matching and source-census checks.

This rule module does not assemble, select, transcribe or generate graph gold.
Callers supply the existing scoped-identity and scalar predicates explicitly.
"""
from .baseline import valid_bbox
from .policy import option_set_valid,choice_answer_valid


def audit_questions(evidence,graph,review,*,scope_key,scalar_issues):
    pages = {page["asset_id"]:page for page in evidence["payload"]["pages"]}
    findings = []
    def add(code,scope,refs=(),severity="ERROR",detail=None):
        findings.append({"code":code,"scope_id":scope,"evidence_refs":list(refs),"severity":severity,"detail":detail})
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
        if a and not a["coarse_detail_agreement"]:
            add("OCR_RECOGNITION_DISAGREEMENT", qid, a["evidence_refs"])
        if a and a["variant_geometry_unresolved"]:
            add("ANSWER_VARIANT_REGION_UNSPLIT", qid, a["evidence_refs"])
        if a and q["selected_answer_id"] not in q["candidate_answer_ids"]:
            add("INVALID_SELECTED_ANSWER", qid, a["evidence_refs"])
        if a and any(r not in evidence_lines for r in a["evidence_refs"]):
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
    return findings,coverage
