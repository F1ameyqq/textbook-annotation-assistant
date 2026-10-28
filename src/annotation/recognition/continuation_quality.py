"""Independent audit of a local continuation application; never re-run apply.

Original entities are compared with the supplied immutable base. New fragments
are checked directly against source OCR, ownership against the complete graph,
and typed render regions against independently validated input evidence. This
module neither imports the application producer nor creates a replacement graph.
"""
from __future__ import annotations

from collections import Counter
import copy
from pathlib import Path

from .baseline import code_digest, digest
from .continuation import validate_continuation

CHECK_SCHEMA = "b-continuation-application-check-trial/0.1"


def ref(value):
    return {key: value.get(key) for key in ("artifact_id", "revision", "content_hash")}


def audit_continuation_application(evidence, base_graph, derived, proof, *, image_review, capture_root):
    """Audit actual graph contents and return an always-HOLD trial check.

    ``accepted`` certifies this local structural transition only. It does not
    certify OCR/formula/diagram semantics, human acceptance, or site submission.
    """
    issues, summary = [], {}

    def issue(code, refs=(), detail=None):
        issues.append({"code": code, "evidence_refs": list(refs), "detail": detail,
                       "severity": "ERROR", "blocks": ["PRE_APPLY"]})

    def finish():
        payload = {"accepted": not issues, "decision": "HOLD", "issues": issues, "summary": summary,
                   "verification_status": "UNVERIFIED", "business_acceptance": False, "platform_actions": []}
        inputs = [ref(v) for v in (evidence, base_graph, derived, proof)]
        if isinstance(image_review, dict):
            inputs.append(ref(image_review))
        return {"schema_version": CHECK_SCHEMA, "kind": "ContinuationApplicationCheckTrial",
                "artifact_id": "continuationapplicationchecktrial-" + digest([inputs, payload])[:24],
                "revision": 1, "book_id": evidence.get("book_id"), "scope_id": evidence.get("scope_id"),
                "run_id": evidence.get("run_id"), "input_refs": inputs,
                "content_hash": digest(payload), "payload": payload,
                "producer": {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__))}}

    for value, schemas, label in (
            (evidence, {"b-evidence-trial/0.3"}, "evidence"),
            (base_graph, {"b-graph-trial/0.3"}, "base_graph"),
            (derived, {"b-graph-trial/0.4"}, "derived"),
            (proof, {"b-continuation-proof-trial/0.2"}, "proof")):
        if (not isinstance(value, dict) or value.get("schema_version") not in schemas
                or not isinstance(value.get("payload"), dict)
                or value.get("content_hash") != digest(value.get("payload"))):
            issue("APPLY_ARTIFACT_INVALID", detail=label)
    if issues:
        return finish()
    checked = validate_continuation(evidence, base_graph, proof, image_review=image_review, capture_root=capture_root)
    if not checked["payload"]["accepted"]:
        issue("APPLY_INPUT_PROOF_REJECTED", detail=checked["payload"]["issues"])
        return finish()
    plan = checked["payload"]["verified_plan"]
    if not plan.get("source_image_regions") or not plan.get("next_boundary_binding"):
        issue("APPLY_REQUIRED_STRUCTURAL_EVIDENCE_MISSING")
        return finish()
    if ((derived.get("book_id"), derived.get("scope_id"), derived.get("run_id")) !=
            (evidence.get("book_id"), evidence.get("scope_id"), evidence.get("run_id"))
            or derived.get("revision") != base_graph.get("revision", 0) + 1
            or derived.get("artifact_id") == base_graph.get("artifact_id")):
        issue("APPLY_STALE_BINDING", detail="header or revision")
    if derived.get("kind") != "QuestionGraphTrial" or derived.get("producer", {}).get("operation") != "LOCAL_CONTINUATION_ONLY":
        issue("APPLY_GRAPH_KIND_MISMATCH")
    expected_inputs = [ref(evidence), ref(base_graph), ref(proof), ref(image_review), ref(checked)]
    if derived.get("input_refs") != expected_inputs:
        issue("APPLY_STALE_BINDING", detail="input_refs")
    if derived.get("supersedes") != ref(base_graph):
        issue("APPLY_STALE_BINDING", detail="supersedes")
    original, payload = base_graph["payload"], derived["payload"]
    application = payload.get("continuation_application", {})
    required_application = {"schema_version": "b-continuation-application-trial/0.1", "operation": "APPLY_LOCAL_ONLY",
        "base_graph_archive": base_graph, "base_graph_ref": ref(base_graph), "evidence_ref": ref(evidence),
        "proof_archive": proof, "proof_ref": ref(proof), "image_review_ref": ref(image_review),
        "validation_check_archive": checked, "validation_check_ref": ref(checked),
        "affected_answer_id": plan["from_answer_id"], "source_fragment_ids_preserved": plan["source_fragment_ids_preserved"],
        "target_line_ids": plan["target_line_ids"], "boundary_binding": plan["next_boundary_binding"]}
    if not isinstance(application, dict):
        issue("APPLY_ARCHIVE_MISMATCH")
        return finish()
    for key, expected in required_application.items():
        if application.get(key) != expected:
            issue("APPLY_ARCHIVE_MISMATCH", detail=key)
    allowed_top = {"answers", "answer_coverage", "continuation_application", "matching_status", "selection_status", "issues", "decision", "business_acceptance"}
    if {k:v for k,v in payload.items() if k not in allowed_top} != {k:v for k,v in original.items() if k not in allowed_top}:
        issue("APPLY_ORIGINAL_PAYLOAD_CHANGED")
    if payload.get("questions") != original.get("questions"):
        issue("APPLY_ORIGINAL_QUESTION_CHANGED")
    if (payload.get("matching_status") != "LOCAL_STRUCTURE_CONTINUED_UNVERIFIED"
            or payload.get("selection_status") != "DRAFT_UNVERIFIED_CONTINUATION_APPLIED"
            or payload.get("decision") != "HOLD" or payload.get("business_acceptance") is not False):
        issue("APPLY_FALSE_VERIFICATION", detail="graph status")
    old_answers, answers = original["answers"], payload.get("answers", [])
    if [a.get("answer_id") for a in answers] != [a.get("answer_id") for a in old_answers]:
        issue("APPLY_ANSWER_SET_CHANGED")
        return finish()
    old_answer = next(a for a in old_answers if a["answer_id"] == plan["from_answer_id"])
    answer = next(a for a in answers if a["answer_id"] == plan["from_answer_id"])
    all_fids = [f.get("fragment_id") for owner in answers for f in owner.get("fragments", [])]
    if any(not isinstance(fid, str) or not fid for fid in all_fids) or len(all_fids) != len(set(all_fids)):
        issue("APPLY_GLOBAL_FRAGMENT_ID_REUSED")
    expected_issues, resolved = [], []
    for item in original.get("issues", []):
        updated = copy.deepcopy(item)
        if item.get("answer_id") == plan["from_answer_id"] and item.get("code") == "ANSWER_BOUNDARY_UNRESOLVED":
            resolved.append(copy.deepcopy(item))
            updated.update(status="RESOLVED_STRUCTURAL_BOUNDARY", resolution_ref=ref(proof), resolution_check_ref=ref(checked))
        expected_issues.append(updated)
    if payload.get("issues") != expected_issues or application.get("resolved_issues") != resolved:
        issue("APPLY_ORIGINAL_ISSUE_CHANGED")
    for before, after in zip(old_answers, answers):
        if before["answer_id"] != plan["from_answer_id"] and before != after:
            issue("APPLY_ORIGINAL_ANSWER_CHANGED", detail=before["answer_id"])
    mutable_answer = {"fragments", "regions", "text", "source_line_ids", "evidence_refs", "complete",
                      "assembly_status", "boundary", "continuations"}
    allowed_new_answer = {"render_regions", "regions_schema", "regions_migration", "fragment_representation",
                          "structural_complete", "structural_resolution", "active_assembly_flags"}
    if set(answer) != set(old_answer) | allowed_new_answer:
        issue("APPLY_UNKNOWN_ANSWER_FIELD", detail=sorted(set(answer) - set(old_answer) - allowed_new_answer))
    for key, value in old_answer.items():
        if key not in mutable_answer and answer.get(key) != value:
            issue("APPLY_ORIGINAL_ANSWER_METADATA_CHANGED", detail=key)
    expected_boundary = {**copy.deepcopy(plan["next_boundary_binding"]),
                         "evidence_refs": plan["next_boundary_binding"]["line_ids"]}
    if answer.get("boundary") != expected_boundary:
        issue("APPLY_BOUNDARY_BINDING_MISMATCH")
    expected_continuation = {"kind": "CROSS_PAGE", "from_asset_id": old_answer["asset_id"],
        "to_asset_id": plan["to_asset_id"], "source_tail_line_id": plan["source_tail_line_id"],
        "target_line_ids": plan["target_line_ids"], "proof_ref": ref(proof), "check_ref": ref(checked),
        "verification_status": "UNVERIFIED", "business_acceptance": False}
    if answer.get("continuations") != old_answer.get("continuations", []) + [expected_continuation]:
        issue("APPLY_CONTINUATION_RECORD_MISMATCH")
    resolution = answer.get("structural_resolution", {})
    expected_flags = [flag for flag in old_answer.get("assembly_flags", []) if flag == "ANSWER_BOUNDARY_UNRESOLVED"]
    if (resolution.get("proof_ref") != ref(proof) or resolution.get("check_ref") != ref(checked)
            or resolution.get("transcription_verified") is not False
            or resolution.get("resolved_legacy_flags") != expected_flags):
        issue("APPLY_STRUCTURAL_RESOLUTION_MISMATCH")
    if answer.get("active_assembly_flags") != [flag for flag in old_answer.get("assembly_flags", []) if flag != "ANSWER_BOUNDARY_UNRESOLVED"]:
        issue("APPLY_STRUCTURAL_RESOLUTION_MISMATCH", detail="active flags")
    if application.get("resolved_assembly_flags") != expected_flags:
        issue("APPLY_STRUCTURAL_RESOLUTION_MISMATCH", detail="application flags")
    app_meta = {"verification_status": "UNVERIFIED", "decision": "HOLD", "business_acceptance": False, "platform_actions": []}
    if any(application.get(key) != value for key, value in app_meta.items()):
        issue("APPLY_FALSE_VERIFICATION", detail="application state")

    def reject_false_claims(value, path=""):
        if isinstance(value, dict):
            for key, child in value.items():
                if ((key in {"business_acceptance", "human_verified", "transcription_verified", "image_semantics_verified"} and child is True)
                        or key == "reference_quality" and child == "HUMAN_REVIEWED"
                        or key == "platform_actions" and child != []):
                    issue("APPLY_FALSE_VERIFICATION", detail=path + "/" + key)
                reject_false_claims(child, path + "/" + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                reject_false_claims(child, path + "/" + str(index))
    reject_false_claims(answer, "answer")
    reject_false_claims(application, "application")
    old_fragments, fragments = old_answer["fragments"], answer.get("fragments", [])
    if fragments[:len(old_fragments)] != old_fragments:
        issue("APPLY_SOURCE_FRAGMENT_CHANGED")
    pages = {p["asset_id"]: p for p in evidence["payload"]["pages"]}
    units = {line["line_id"]: (page, line) for page in pages.values()
             for line in page["ocr_lines"] + page.get("answer_detail_lines", [])}
    expected_targets = list(plan["target_line_ids"])
    added = fragments[len(old_fragments):]
    if (len(added) != len(expected_targets)
            or [f.get("evidence_refs") for f in added] != [[r] for r in expected_targets]):
        issue("APPLY_TARGET_COVERAGE_MISMATCH", expected_targets)
    fids = [f.get("fragment_id") for f in fragments]
    if any(not isinstance(fid, str) or not fid for fid in fids) or len(fids) != len(set(fids)):
        issue("APPLY_FRAGMENT_ID_REUSED")
    images = plan["source_image_regions"] + [r for r in plan["target_regions"] if r["content_type"] == "image"]
    diagnostic = {r: image["region_id"] for image in images for r in image["diagnostic_ocr_refs"]}
    for fragment in added:
        refs = fragment.get("evidence_refs", [])
        if len(refs) != 1 or refs[0] not in units:
            issue("APPLY_FRAGMENT_SOURCE_MISMATCH", refs)
            continue
        r = refs[0]
        page, line = units[r]
        loc = line["location"]
        expected = {"asset_id": page["asset_id"], "parent_line_id": r, "raw_text": line["text"],
            "text": line["text"], "text_span": [0,len(line["text"])], "bbox": line["bbox"],
            "role": "answer", "content_type": "text", "column": loc["column"], "window_index": loc["window_index"],
            "section_path": loc["section_path"], "verification_status": "UNVERIFIED",
            "render_as_separate_region": r not in diagnostic, "represented_by_image_region": diagnostic.get(r)}
        if any(fragment.get(k) != v for k,v in expected.items()):
            issue("APPLY_FRAGMENT_SOURCE_MISMATCH", refs)
    canonical_parents = []
    for fragment in fragments:
        for r in fragment.get("evidence_refs", []):
            if r in units:
                parent = units[r][1].get("parent_line_id", r)
                if parent not in canonical_parents:
                    canonical_parents.append(parent)
    expected_source_lines = old_answer["source_line_ids"] + expected_targets
    if answer.get("source_line_ids") != expected_source_lines or canonical_parents != expected_source_lines:
        issue("APPLY_SOURCE_LINE_CHAIN_MISMATCH")
    expected_refs = list(dict.fromkeys(old_answer["evidence_refs"] + expected_targets))
    if answer.get("evidence_refs") != expected_refs:
        issue("APPLY_AGGREGATE_EVIDENCE_MISMATCH")
    actual_owners = {}
    for owner in answers:
        for fragment in owner.get("fragments", []):
            for r in fragment.get("evidence_refs", []):
                if r in units:
                    parent = units[r][1].get("parent_line_id", r)
                    actual_owners.setdefault(parent, []).append(owner["answer_id"])
    for r in expected_source_lines:
        if actual_owners.get(r) != [answer["answer_id"]]:
            issue("APPLY_SOURCE_OWNERSHIP_MISMATCH", [r])
    # Original source objects remain exact; the changed representation is typed
    # separately so diagnostic OCR does not become a second drawable text box.
    fragment_by_ref = {r: f for f in fragments for r in f.get("evidence_refs", [])}
    expected_body_refs = [r for r in expected_refs if r not in diagnostic]
    expected_text = "\n".join(fragment_by_ref[r]["text"] for r in expected_body_refs if r in fragment_by_ref)
    if answer.get("text") != expected_text:
        issue("APPLY_TEXT_AGGREGATE_MISMATCH")
    renders = answer.get("render_regions", [])
    if answer.get("regions_schema") != "b-render-region-trial/0.1" or answer.get("regions") != renders:
        issue("APPLY_RENDER_SCHEMA_MISMATCH")
    migration = {"from_graph_schema": base_graph["schema_version"], "to_graph_schema": "b-graph-trial/0.4",
                 "regions_semantics": "TYPED_RENDER_PROJECTION", "legacy_consumers_supported": False,
                 "source_fragments_preserved": True}
    if answer.get("regions_migration") != migration:
        issue("APPLY_RENDER_SCHEMA_MISMATCH", detail="migration")
    render_ids = [r.get("region_id") for r in renders]
    if len(render_ids) != len(set(render_ids)) or any(not r for r in render_ids):
        issue("APPLY_RENDER_REGION_REUSED")
    represented_ids = [fid for region in renders for fid in region.get("source_fragment_ids", [])]
    if Counter(represented_ids) != Counter(fids):
        issue("APPLY_RENDER_COVERAGE_MISMATCH")
    representations = []
    for fragment in fragments:
        refs = fragment.get("evidence_refs", [])
        parents = [units[r][1].get("parent_line_id", r) for r in refs if r in units]
        image_id = next((diagnostic[parent] for parent in parents if parent in diagnostic), None)
        targets = [region.get("region_id") for region in renders
                   if fragment.get("fragment_id") in region.get("source_fragment_ids", [])]
        representations.append({"fragment_id": fragment["fragment_id"],
            "render_as_separate_region": image_id is None, "represented_by_image_region": image_id,
            "render_region_id": targets[0] if len(targets) == 1 else None})
    if answer.get("fragment_representation") != representations:
        issue("APPLY_FRAGMENT_REPRESENTATION_MISMATCH")
    expected_image_ids = {image["region_id"] for image in images}
    actual_image_ids = {r.get("region_id") for r in renders if r.get("content_type") == "image"}
    if actual_image_ids != expected_image_ids or sum(r.get("content_type") == "image" for r in renders) != len(images):
        issue("APPLY_IMAGE_SET_MISMATCH")
    body_seen = []
    for region in renders:
        if region.get("content_type") == "text":
            refs = region.get("evidence_refs", [])
            body_seen.extend(refs)
            if len(refs) != 1 or refs[0] not in fragment_by_ref:
                issue("APPLY_RENDER_PROJECTION_MISMATCH", refs)
                continue
            r, fragment = refs[0], fragment_by_ref[refs[0]]
            if r in diagnostic:
                issue("APPLY_DIAGNOSTIC_RENDERED_AS_TEXT", refs)
            expected = {"content_type": "text", "role": "answer", "asset_id": fragment["asset_id"],
                "bbox": fragment["bbox"], "text": fragment["text"], "source_fragment_ids": [fragment["fragment_id"]],
                "source_sha256": pages[fragment["asset_id"]]["source"]["sha256"], "verification_status": "UNVERIFIED"}
            if any(region.get(k) != v for k,v in expected.items()):
                issue("APPLY_RENDER_PROJECTION_MISMATCH", refs)
        elif region.get("content_type") == "image":
            original_image = next((image for image in images if image["region_id"] == region.get("region_id")), None)
            if original_image is None:
                issue("APPLY_RENDER_PROJECTION_MISMATCH")
                continue
            if any(region.get(k) != v for k,v in original_image.items()):
                issue("APPLY_RENDER_PROJECTION_MISMATCH", original_image["diagnostic_ocr_refs"])
            refs = original_image["diagnostic_ocr_refs"]
            expected_fids = [fragment_by_ref[r]["fragment_id"] for r in refs if r in fragment_by_ref]
            if (region.get("source_fragment_ids") != expected_fids or region.get("evidence_refs") != refs
                    or region.get("image_ref") != {"artifact_ref": plan["image_region_artifact_ref"], "region_id": region["region_id"]}):
                issue("APPLY_RENDER_PROJECTION_MISMATCH", refs)
        else:
            issue("APPLY_RENDER_TYPE_INVALID")
    if body_seen != expected_body_refs:
        issue("APPLY_BODY_RENDER_SET_MISMATCH", body_seen)
    expected_render_order = []
    for fragment in old_fragments:
        refs = fragment["evidence_refs"]
        parents = [units[r][1].get("parent_line_id", r) for r in refs]
        if not any(parent in diagnostic for parent in parents):
            expected_render_order.append(("text", fragment["asset_id"], tuple(refs)))
    expected_render_order.extend(("image", image["asset_id"], image["region_id"]) for image in plan["source_image_regions"])
    for region in plan["target_regions"]:
        expected_render_order.append(("image", region["asset_id"], region["region_id"]) if region["content_type"] == "image"
                                     else ("text", region["asset_id"], (region["line_id"],)))
    actual_render_order = [("image", region.get("asset_id"), region.get("region_id")) if region.get("content_type") == "image"
                           else (region.get("content_type"), region.get("asset_id"), tuple(region.get("evidence_refs", [])))
                           for region in renders]
    if actual_render_order != expected_render_order:
        issue("APPLY_RENDER_ORDER_MISMATCH")
    expected_meta = {"complete": False, "structural_complete": True, "assembly_status": "BOUNDED",
                     "transcription_verified": False, "verification_status": "UNVERIFIED"}
    if any(answer.get(k) != v for k,v in expected_meta.items()):
        issue("APPLY_FALSE_VERIFICATION", detail="answer state")
    if answer.get("bbox") != old_answer["bbox"]:
        issue("APPLY_ANCHOR_BBOX_CHANGED")
    old_ledger, ledger = original["answer_coverage"], payload.get("answer_coverage", [])
    if [r.get("line_id") for r in ledger] != [r.get("line_id") for r in old_ledger]:
        issue("APPLY_LEDGER_SET_CHANGED")
    for before, row in zip(old_ledger, ledger):
        r = before["line_id"]
        if r not in expected_targets:
            if row != before:
                issue("APPLY_ORIGINAL_LEDGER_CHANGED", [r])
            continue
        fragment = fragment_by_ref.get(r)
        if not fragment:
            issue("APPLY_LEDGER_MISMATCH", [r])
            continue
        allocation = {"answer_id": answer["answer_id"], "fragment_id": fragment["fragment_id"],
                      "evidence_refs": [r], "text_span": [0,len(units[r][1]["text"])]}
        expected = {"asset_id": plan["to_asset_id"], "line_id": r, "status": "CONSUMED",
                    "answer_ids": [answer["answer_id"]], "fragment_ids": [fragment["fragment_id"]], "allocations": [allocation]}
        if any(row.get(k) != v for k,v in expected.items()):
            issue("APPLY_LEDGER_MISMATCH", [r])
    archive_expectations = {"added_fragment_ids": [f["fragment_id"] for f in added],
        "old_line_owners": [r for r in old_ledger if r["line_id"] in expected_targets],
        "preserved_source_line_owners": [r for r in old_ledger if r["line_id"] in old_answer["source_line_ids"]],
        "render_region_ids": render_ids, "image_region_ids": [image["region_id"] for image in images]}
    for key, expected in archive_expectations.items():
        if application.get(key) != expected:
            issue("APPLY_ARCHIVE_MISMATCH", detail=key)
    expected_app_keys = set(required_application) | set(archive_expectations) | set(app_meta) | {"resolved_issues", "resolved_assembly_flags"}
    if set(application) != expected_app_keys:
        issue("APPLY_UNKNOWN_APPLICATION_FIELD", detail=sorted(set(application) - expected_app_keys))
    if derived.get("rollback_guard", {}).get("expected_payload_hash") != derived.get("content_hash"):
        issue("APPLY_DERIVED_PAYLOAD_CHANGED")
    if derived.get("rollback_guard") != {"schema_version": "b-continuation-rollback-guard-trial/0.1",
            "expected_payload_hash": derived.get("content_hash"), "requires_external_expected_graph_ref": True}:
        issue("APPLY_ROLLBACK_POLICY_MISMATCH")
    summary.update(source_fragments_preserved=len(old_fragments), target_fragments=len(added),
                   fragments=len(fragments), render_regions=len(renders), text_regions=len(body_seen),
                   image_regions=len(actual_image_ids), diagnostic_fragments=len(diagnostic),
                   unaffected_answers=len(answers)-1)
    return finish()
