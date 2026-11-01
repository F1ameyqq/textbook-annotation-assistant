"""Audit a recovered assembly view against retained source and CPU receipts.

This compares exact source objects and approved dispositions independently of
the assembler. It does not certify the mathematical meaning of OCR or formulas.
"""
from .baseline import digest
from .recovery_apply import reference, validate_hypotheses
import hashlib


def audit_recovery(evidence, graph):
    payload = evidence["payload"]
    if "recovery_application" not in payload:
        return [], {}
    issues = []

    def issue(code, refs=(), detail=None, severity="ERROR"):
        issues.append(dict(code=code, scope_id=evidence["scope_id"], evidence_refs=list(refs), detail=detail, severity=severity))

    base, recovery = payload["base_evidence_archive"], payload["recovery_evidence_archive"]
    review, applied = payload["recovery_source_review"], payload["recovery_application"]
    if (applied.get("formula_candidates") != review["formula_candidates"]
            or payload.get("source_review") != review):
        issue("RECOVERY_REVIEW_PROJECTION_MISMATCH")
    for original in (base, recovery):
        if original["content_hash"] != digest(original["payload"]):
            issue("RECOVERY_ARCHIVE_HASH_MISMATCH")
    if (review["base_evidence_ref"] != reference(base) or review["recovery_ref"] != reference(recovery)
            or payload["recovery_ref"] != reference(recovery)
            or payload["recovery_review_ref"]["content_hash"] != digest(review)):
        issue("RECOVERY_REVIEW_BINDING_MISMATCH")
    old = {l["line_id"]: (p,l) for p in base["payload"]["pages"] for l in p["ocr_lines"]}
    active = {l["line_id"]: (p,l) for p in payload["pages"] for l in p["ocr_lines"]}
    removed = set(old)-set(active)
    plans = recovery["payload"]["supersession_plan"]
    expected_removed = {r for plan in plans for r in plan["base_line_ids"]}
    expected_added = {r for plan in plans for r in plan["replacement_line_ids"]} | {r["line_id"] for r in review.get("reviewed_probe_selections", [])}
    if (removed != expected_removed or set(active)-set(old) != expected_added
            or set(applied["replaced_base_line_ids"]) != expected_removed
            or set(applied["replacement_line_ids"]) != expected_added):
        issue("RECOVERY_PROJECTION_COVERAGE_MISMATCH", sorted(removed ^ expected_removed))
    for line_id in set(old) & set(active):
        if old[line_id][1] != active[line_id][1]:
            issue("RECOVERY_ORIGINAL_OCR_CHANGED", [line_id])
    hypotheses, unresolved_order = {}, set()
    for probe in recovery["payload"]["probes"]:
        for variant in probe["variants"]:
            try:
                validate_hypotheses(probe, variant)
            except ValueError as exc:
                issue("RECOVERY_CPU_RECEIPT_MISMATCH", detail=str(exc))
            hypotheses.update({l["line_id"]: l for l in variant["ocr_lines"]})
            if probe["status"] == "ANCHOR_RECOVERED_FORMULAS_UNRESOLVED":
                unresolved_order.update(l["line_id"] for l in variant["ocr_lines"])
    for line_id in expected_added & set(active):
        actual, source = active[line_id][1], hypotheses[line_id]
        if any(actual.get(key) != source.get(key) for key in
               ("text","score","bbox","polygon","asset_id","location","base_line_ids")):
            issue("RECOVERY_CPU_LINE_CHANGED", [line_id])
        if actual.get("verification_status") != "UNVERIFIED" or actual.get("independent_confirmation") is not False:
            issue("RECOVERY_FALSE_VERIFICATION", [line_id])
        if line_id in unresolved_order and actual.get("reading_order_status") != "UNRESOLVED_2D_FORMULA":
            issue("RECOVERY_READING_ORDER_STATUS_LOST", [line_id])
    for answer in graph["payload"]["answers"]:
        refs = set(answer.get("source_line_ids", [])) & unresolved_order
        if refs and (answer.get("assembly_status") != "OPEN" or answer.get("complete") is not False
                     or "ANSWER_2D_READING_ORDER_UNRESOLVED" not in answer.get("assembly_flags", [])):
            issue("RECOVERY_FALSE_COMPLETE_FORMULA", sorted(refs))
    # Frozen source-owned expectations, not the assembler's claimed ledger or
    # its mutable control fields. A poisoned reading-order key must not move a
    # fraction into the preceding answer while making all ledgers agree.
    for case in review.get("recovered_answer_checks", []):
        targets = [a for a in graph["payload"]["answers"] if a["section_path"] == case["section_path"]
                   and a["printed_number"] == case["printed_number"]]
        if len(targets) != 1:
            issue("RECOVERY_ANSWER_TARGET_INVALID", detail=case); continue
        actual = list(dict.fromkeys(f["parent_line_id"] for f in targets[0]["fragments"]))
        if set(actual) != set(case["expected_source_line_ids"]):
            issue("RECOVERY_ANSWER_OWNERSHIP_MISMATCH", sorted(set(actual) | set(case["expected_source_line_ids"])),
                  {"number": case["printed_number"], "expected": case["expected_source_line_ids"], "actual": actual})
        if "ordered_source_line_ids" in case and actual != case["ordered_source_line_ids"]:
            issue("RECOVERY_ANSWER_ORDER_MISMATCH", actual, case["ordered_source_line_ids"])
    triage = review["triage"]
    if len(triage) != 38 or len({t["line_id"] for t in triage}) != 38:
        issue("RECOVERY_TRIAGE_COUNT_INVALID")
    ledger = {r["line_id"]: r for r in graph["payload"]["answer_coverage"]}
    exclusions = {r["line_id"] for r in review["reviewed_exclusions"]}
    remaining = {r for g in review["remaining_source_groups"] for r in g["source_line_ids"]}
    for row in triage:
        line_id = row["line_id"]
        if line_id not in old:
            issue("RECOVERY_TRIAGE_UNKNOWN_SOURCE", [line_id]); continue
        page, line = old[line_id]
        if (row["source_sha256"] != page["source"]["sha256"] or row["bbox"] != line["bbox"]
                or row["source_text_sha256"] != hashlib.sha256(line["text"].encode()).hexdigest()):
            issue("RECOVERY_TRIAGE_SOURCE_MISMATCH", [line_id])
        expected = "REPLACED_IN_ASSEMBLY_VIEW" if line_id in expected_removed else "EXCLUDED_NON_CONTENT" if line_id in exclusions else "RETAINED_UNASSIGNED_SOURCE_REFERENCE"
        if row["disposition"] != expected:
            issue("RECOVERY_TRIAGE_DISPOSITION_MISMATCH", [line_id])
        if expected == "RETAINED_UNASSIGNED_SOURCE_REFERENCE" and (line_id not in remaining or ledger.get(line_id, {}).get("status") != "UNASSIGNED"):
            issue("RECOVERY_MATH_REFERENCE_LOST", [line_id])
    for candidate in review["formula_candidates"]:
        if (candidate.get("method") != "MODEL_VISUAL_DEVELOPMENT_TRANSCRIPTION"
                or candidate.get("verification_status") != "UNVERIFIED"
                or any(candidate.get(k) is not False for k in ("cpu_ocr","human_verified","applied_to_ocr","business_acceptance"))):
            issue("RECOVERY_FORMULA_PROVENANCE_INVALID", detail=candidate["candidate_id"])
        issue("FORMULA_VISUAL_CANDIDATE_REQUIRES_REVIEW", detail=candidate["candidate_id"], severity="REVIEW")
    return issues, {"triaged_original_unassigned_lines": len(triage), "recovered_original_unassigned_lines": sum(t["line_id"] in expected_removed for t in triage),
                    "reviewed_non_content_lines": len(exclusions), "retained_math_source_lines": len(remaining),
                    "recovery_replaced_raw_lines": len(expected_removed), "recovery_candidate_lines": len(expected_added),
                    "visual_formula_candidates": len(review["formula_candidates"]), "formula_candidates_verified": False}
