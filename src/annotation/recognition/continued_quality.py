"""Recheck the current extended source and typed continuation graph offline.

Integrity acceptance and transcription/business acceptance are distinct. This
check retains source-bound development disagreements without correcting OCR.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from .baseline import code_digest,digest
from .answer_quality import audit_answers
from .question_quality import audit_questions
from .recovery_quality import audit_recovery
from .offline import scope_key,scalar_issues
from .continuation_stage_quality import (ref,docref,inspect_continuation_package,
    semantic_receipt,audit_continuation_scope,audit_continuation_proof_stage,
    audit_continuation_apply_stage)


def _producer():
    names = ("question_quality","answer_quality","recovery_quality","continuation_stage_quality",
             "continuation_quality","offline")
    return {"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__)),
        "dependency_code_sha256":{n:code_digest(Path(__file__).with_name(n+".py"))for n in names},
        "identity_policy":"CURRENT_REFS_WITH_EXECUTION_TIME_IN_JOURNAL/0.1","new_ocr_calls":0,"website_requests":0}


def _review(review,scope,proof_stage,package):
    evidence = scope["payload"]["evidence"]
    manifest,docs = package["manifest"],package["documents"]
    snapshot = manifest["reviewed_source_answer"]
    fixture = docs["continuation_fixture"]; lines = {l["line_id"]:l for l in fixture["payload"]["ocr_lines"]}
    target = proof_stage["payload"]["proof"]["payload"]["to_line_ids"]
    source_raw = {l["line_id"]:l for l in snapshot["raw_lines"]}
    spans = {}
    for fragment in snapshot["fragments"]:
        for line_id in fragment["evidence_refs"]:
            spans.setdefault(line_id,[]).append(fragment["text_span"])
    expected_spans = [{"line_id":line_id,"source_text_sha256":hashlib.sha256(source_raw[line_id]["text"].encode()).hexdigest(),
        "text_spans":sorted(spans[line_id])}for line_id in spans]
    expected_spans.extend({"line_id":line_id,"source_text_sha256":hashlib.sha256(lines[line_id]["text"].encode()).hexdigest(),
        "text_spans":[[0,len(lines[line_id]["text"])]]}for line_id in target)
    assets = {asset["asset_id"]:asset["sha256"]for asset in package["receipt"]["source_assets"]+[fixture["payload"]["source"]]
              if asset["asset_id"]in {snapshot["asset_id"],fixture["payload"]["source"]["asset_id"]}}
    case = {"case_id":"continued-answer-"+digest([docref(manifest),ref(fixture)])[:24],
        "asset_sha256":assets,"section_path":snapshot["section_path"],"printed_number":snapshot["printed_number"],
        "expected_source_line_ids":snapshot["source_line_ids"]+target,"expected_source_spans":expected_spans,
        "reference_quality":fixture["payload"]["reviewed_scope"]["reference_quality"],
        "human_verified":False,"business_acceptance":False}
    derived = copy.deepcopy(review)
    derived["scope_id"] = evidence["scope_id"]
    derived["multiline_checks"] = derived.get("multiline_checks",[])+[case]
    derived["artifact_id"] = "continued-review-"+digest([docref(review),ref(scope),ref(proof_stage),case])[:24]
    basis = {"input_review_ref":docref(review),"scope_ref":ref(scope),"fixture_ref":ref(fixture),
        "frozen_source_snapshot_sha256":digest(snapshot),"proof_ref":ref(proof_stage["payload"]["proof"]),
        "source_line_ids":snapshot["source_line_ids"],"target_line_ids":target,
        "expected_text_from_current_graph":False,"business_acceptance":False}
    return derived,basis


def build_continued_quality(scope,proof_stage,apply_stage,review,*,package_path,source_path,adjacent_source_path):
    package = inspect_continuation_package(package_path,source_path,adjacent_source_path)
    sp = scope["payload"];e,g = sp["evidence"],apply_stage["payload"]["graph"]
    if (review.get("book_id") != e["book_id"]or review.get("scope_id") != sp["base_evidence_archive"]["scope_id"]
            or review.get("schema_version") != "b-review-trial/0.1"):
        raise ValueError("active review must refer to the original source scope")
    integrity = [audit_continuation_scope(sp["base_evidence_archive"],sp["base_graph_archive"],scope,package_path,source_path,adjacent_source_path),
        audit_continuation_proof_stage(scope,proof_stage,package_path,source_path,adjacent_source_path),
        audit_continuation_apply_stage(scope,proof_stage,apply_stage,package_path,source_path,adjacent_source_path)]
    if not all(c["payload"]["accepted"]for c in integrity):
        raise ValueError("current continuation stages failed independent integrity checks: "+str([c["payload"]["issues"]for c in integrity]))
    derived,basis = _review(review,scope,proof_stage,package)
    question_findings,coverage = audit_questions(e,g,derived,scope_key=scope_key,scalar_issues=scalar_issues)
    answer_findings,metrics = audit_answers(e,g,derived)
    recovery_findings,recovery_metrics = audit_recovery(sp["base_evidence_archive"],g)
    metrics.update(recovery_metrics)
    answer_id = proof_stage["payload"]["proof"]["payload"]["from_answer_id"]
    boundary = proof_stage["payload"]["boundary_check"]["payload"]["boundary"]
    heading = set(boundary["line_ids"])
    dispositions,findings = [],list(question_findings)
    for item in answer_findings:
        replace = (item["scope_id"] == answer_id and item["code"]in {"ANSWER_AGGREGATE_TEXT_MISMATCH","ANSWER_REGIONS_MISMATCH","ANSWER_REGION_PROJECTION_MISMATCH"})
        replace |= (item["code"] == "ANSWER_EXCLUSION_WITHOUT_EVIDENCE"and bool(item["evidence_refs"])and set(item["evidence_refs"]) <= heading)
        if replace:
            dispositions.append({"finding":item,"status":"SUPERSEDED_PRESENTATION_RULE",
                "replacement_check_ref":ref(integrity[2]),"boundary_check_ref":ref(proof_stage["payload"]["boundary_check"])})
        else: findings.append(item)
    findings.extend(recovery_findings)
    def append(code,scope_id,refs=(),detail=None,severity="REVIEW"):
        findings.append(dict(code=code,scope_id=scope_id,evidence_refs=list(refs),severity=severity,detail=detail))
    for item in g["payload"]["issues"]:
        if item["code"] == "UNASSIGNED_ANSWER_OCR_LINE": continue
        if item.get("answer_id") == answer_id and item["code"] == "ANSWER_BOUNDARY_UNRESOLVED"and item.get("status") == "RESOLVED_STRUCTURAL_BOUNDARY":
            dispositions.append({"finding":item,"status":"RESOLVED_STRUCTURAL_BOUNDARY",
                "replacement_check_ref":ref(integrity[2]),"boundary_check_ref":ref(proof_stage["payload"]["boundary_check"])})
            continue
        append(item["code"],item.get("answer_id",e["scope_id"]),item["evidence_refs"],item.get("detail"))
    content = package["documents"]["content_review"]
    for case in content["payload"]["line_checks"]:
        append("CONTINUATION_DEVELOPMENT_TRANSCRIPTION_DISAGREEMENT",answer_id,[case["line_id"]],
            {"case_id":case["case_id"],"content_review_ref":ref(content),"raw_text":case["raw_text"],
             "observed_text":case["observed_text"],"differences":case["differences"],
             "reference_quality":"MODEL_VISUAL_DEVELOPMENT_REVIEW","human_verified":False,"ocr_corrected":False})
    target = proof_stage["payload"]["proof"]["payload"]["to_line_ids"]
    append("CONTINUATION_PARTIAL_ADJACENT_PAGE_OCR",e["scope_id"],target,sp["source_scope"])
    append("CONTINUATION_TYPED_CONTENT_UNVERIFIED",answer_id,target,
        {"body_transcription_verified":False,"image_semantics_verified":False,"source_pixels_verified_only":True})
    append("BUSINESS_REVIEW_REQUIRED",e["scope_id"],detail="Development source reviews and shared OCR are not independent business acceptance.")
    pages = {p["asset_id"]for p in e["payload"]["pages"]}
    issues = [{"issue_id":"issue-"+digest([f["code"],f["scope_id"],f["evidence_refs"],f["detail"]])[:24],**f,
        "scope_type":"question"if f["scope_id"].startswith("q-")else"answer"if f["scope_id"].startswith("a-")else"asset"if f["scope_id"]in pages else"scope",
        "blocks":["PRE_APPLY"],"suggested_strategy":"REVIEW_OFFLINE"}for f in findings]
    payload = {"stage":"PRE_APPLY","scope_ref":ref(scope),"proof_stage_ref":ref(proof_stage),"apply_stage_ref":ref(apply_stage),
        "evidence_ref":ref(e),"graph_ref":ref(g),"package_receipt":semantic_receipt(package["receipt"]),
        "input_review_ref":docref(review),"input_review_archive":copy.deepcopy(review),"derived_review":derived,"derived_review_ref":docref(derived),
        "review_migration_basis":basis,"rule_dispositions":dispositions,"stage_integrity_checks":integrity,
        "basis":{"current_question_census_matching_scalar_rules":True,"current_answer_source_span_owner_ledger_rules":True,
                 "recovery_source_evidence_ref":ref(sp["base_evidence_archive"]),"recovery_graph_ref":ref(g),
                 "typed_application_check_ref":ref(integrity[2]),"adjacent_full_page_ocr":False,"business_acceptance":False},
        "issues":issues,"page_coverage":coverage,
        "summary":{"questions":len(g["payload"]["questions"]),"answers":len(g["payload"]["answers"]),
          "unique_candidate_links":sum(q["selected_answer_id"]is not None for q in g["payload"]["questions"]),
          "issues":len(issues),"source_assets":len(e["payload"]["pages"]),"continuation_target_lines":len(target),
          "development_content_disagreements":len(content["payload"]["line_checks"]),**metrics},
        "decision":"HOLD","transcription_verified":False,"business_acceptance":False,"new_ocr_calls":0,"website_requests":0,"platform_actions":[]}
    inputs = [ref(scope),ref(proof_stage),ref(apply_stage),docref(review),package["receipt"]["package"]["reference"],ref(e),ref(g)]
    body = {"schema_version":"b-check-trial/0.4","kind":"CheckReportTrial","revision":1,"book_id":e["book_id"],"scope_id":e["scope_id"],
        "run_id":e["run_id"],"input_refs":inputs,"producer":_producer(),"payload":payload}
    return {**body,"artifact_id":"checkreporttrial-"+digest(body)[:24],"content_hash":digest(payload)}
