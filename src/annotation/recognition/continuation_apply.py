"""Versioned, reversible local continuation projection; no platform operation.

The source validator is called again for every apply. Original source fragments
remain immutable diagnostic objects; typed render regions decide which text is
body and which OCR is represented by a source-pixel-backed image. Structural
completion never certifies transcription. Schema 0.4 requires a new consumer.

Rollback requires an independently retained derived graph reference. Its guard
is a consistency receipt, not a signature, and is not a substitute for that
external version binding.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path

from .baseline import code_digest, digest
from .continuation import validate_continuation

GRAPH_SCHEMA = "b-graph-trial/0.4"
APPLICATION_SCHEMA = "b-continuation-application-trial/0.1"
RENDER_SCHEMA = "b-render-region-trial/0.1"
BOUNDARY_CODE = "ANSWER_BOUNDARY_UNRESOLVED"


def _ref(value):
    return {key:value[key] for key in ("artifact_id","revision","content_hash")}


def _checked(value,schemas):
    if (not isinstance(value,dict) or value.get("schema_version") not in schemas
            or type(value.get("revision")) is not int or value["revision"] < 1
            or not value.get("artifact_id") or not isinstance(value.get("payload"),dict)
            or value.get("content_hash") != digest(value["payload"])):
        raise ValueError("invalid or changed continuation artifact")


def _semantic(value):
    """Ignore artifact creation timestamps for deterministic logical identity."""
    if isinstance(value,list):return [_semantic(item) for item in value]
    if isinstance(value,dict):
        artifact = {"artifact_id","schema_version","payload"} <= set(value)
        return {key:_semantic(item) for key,item in value.items() if not (artifact and key == "created_at")}
    return value


def _graph_id(graph):
    fields = {key:graph[key] for key in
              ("schema_version","kind","revision","book_id","scope_id","run_id","input_refs","producer","payload","supersedes")}
    return "questiongraphtrial-"+digest(_semantic(fields))[:24]


def _fragment_id(evidence,base,proof,answer_id,line_id):
    return "cf-"+digest([_ref(evidence),_ref(base),_ref(proof),answer_id,line_id,"FULL_OCR_LINE"] )[:24]


def _text_region(fragment,source):
    return {"region_id":"render-text-"+digest(fragment["fragment_id"])[:24],
            "content_type":"text","role":fragment["role"],"asset_id":fragment["asset_id"],
            "source_sha256":source["sha256"],"bbox":copy.deepcopy(fragment["bbox"]),"text":fragment["text"],
            "source_fragment_ids":[fragment["fragment_id"]],"evidence_refs":copy.deepcopy(fragment["evidence_refs"]),
            "verification_status":"UNVERIFIED","business_acceptance":False}


def _payload(evidence,base,proof,check,image_review_ref):
    """Pure local projection, also used to reject edited rollback states."""
    plan = check["payload"]["verified_plan"]
    payload = copy.deepcopy(base["payload"])
    answer_id = plan["from_answer_id"]
    selected = [a for a in payload["answers"] if a["answer_id"] == answer_id]
    if len(selected) != 1:raise ValueError("continuation answer is missing or repeated")
    answer = selected[0]
    old_fragments = copy.deepcopy(answer["fragments"])
    original_fragment_ids = [f["fragment_id"] for f in old_fragments]
    if original_fragment_ids != plan["source_fragment_ids_preserved"]:
        raise ValueError("continuation source fragment reference changed")
    pages = {page["asset_id"]:page for page in evidence["payload"]["pages"]}
    units = {line["line_id"]:(page,line) for page in pages.values()
             for line in page["ocr_lines"]+page.get("answer_detail_lines",[])}
    target_lines = plan["target_line_ids"]
    image_refs = plan.get("image_contained_ocr_refs",{})
    fresh = []
    for line_id in target_lines:
        page,line = units[line_id]
        text,loc = line["text"],line["location"]
        if not isinstance(text,str) or not text:raise ValueError("continuation OCR line has no text")
        fresh.append({"fragment_id":_fragment_id(evidence,base,proof,answer_id,line_id),
                      "role":"answer","content_type":"text","asset_id":page["asset_id"],
                      "source_sha256":page["source"]["sha256"],"bbox":copy.deepcopy(line["bbox"]),
                      "text":text,"raw_text":text,"text_span":[0,len(text)],"column":loc["column"],
                      "window_index":loc["window_index"],"section_path":copy.deepcopy(loc["section_path"]),
                      "evidence_refs":[line_id],"parent_line_id":line_id,"structural_marker":False,
                      "geometry_precision":"OCR_ELEMENT","verification_status":"UNVERIFIED",
                      "render_as_separate_region":line_id not in image_refs,
                      "represented_by_image_region":image_refs.get(line_id),"continuation_proof_ref":_ref(proof)})
    all_ids = [f["fragment_id"] for a in base["payload"]["answers"] for f in a["fragments"]]
    added_ids = [f["fragment_id"] for f in fresh]
    if len(set(all_ids+added_ids)) != len(all_ids)+len(added_ids):
        raise ValueError("continuation fragment IDs collide")
    answer["fragments"] = old_fragments+fresh
    parent_by_fragment = {f["fragment_id"]:units[f["evidence_refs"][0]][1].get("parent_line_id",f["evidence_refs"][0])
                          for f in answer["fragments"]}
    image_regions = list(plan.get("source_image_regions",[]))+[
        r for r in plan["target_regions"] if r.get("content_type") == "image"]
    image_by_id = {region["region_id"]:region for region in image_regions}
    projection = []
    # Preserve the proven source-page order first, then the proven target prefix.
    for fragment in old_fragments:
        if parent_by_fragment[fragment["fragment_id"]] not in image_refs:
            projection.append(_text_region(fragment,pages[fragment["asset_id"]]["source"]))

    def add_image(region):
        value = copy.deepcopy(region)
        value["source_fragment_ids"] = [f["fragment_id"] for f in answer["fragments"]
                                         if parent_by_fragment[f["fragment_id"]] in region["diagnostic_ocr_refs"]]
        if not value["source_fragment_ids"]:raise ValueError("image projection has no diagnostic source fragments")
        value["evidence_refs"] = list(region["diagnostic_ocr_refs"])
        value["image_ref"] = {"artifact_ref":copy.deepcopy(plan["image_region_artifact_ref"]),"region_id":region["region_id"]}
        projection.append(value)

    for region in plan.get("source_image_regions",[]):add_image(region)
    fresh_by_parent = {fragment["parent_line_id"]:fragment for fragment in fresh}
    for region in plan["target_regions"]:
        if region.get("content_type") == "image":add_image(region)
        else:
            fragment = fresh_by_parent[region["line_id"]]
            if fragment["parent_line_id"] in image_refs:raise ValueError("image OCR cannot also render as body text")
            projection.append(_text_region(fragment,pages[fragment["asset_id"]]["source"]))
    region_by_fragment = {fid:region["region_id"] for region in projection for fid in region["source_fragment_ids"]}
    if (len(region_by_fragment) != len(answer["fragments"])
            or sum(len(r["source_fragment_ids"]) for r in projection) != len(answer["fragments"])):
        raise ValueError("typed rendering does not represent every source fragment exactly once")
    answer["render_regions"] = projection
    answer["regions"] = copy.deepcopy(projection)
    answer["regions_schema"] = RENDER_SCHEMA
    answer["regions_migration"] = {"from_graph_schema":base["schema_version"],"to_graph_schema":GRAPH_SCHEMA,
                                    "regions_semantics":"TYPED_RENDER_PROJECTION","legacy_consumers_supported":False,
                                    "source_fragments_preserved":True}
    answer["fragment_representation"] = [{"fragment_id":f["fragment_id"],
        "render_as_separate_region":parent_by_fragment[f["fragment_id"]] not in image_refs,
        "represented_by_image_region":image_refs.get(parent_by_fragment[f["fragment_id"]]),
        "render_region_id":region_by_fragment[f["fragment_id"]]} for f in answer["fragments"]]
    answer["text"] = "\n".join(r["text"] for r in projection if r["content_type"] == "text" and r["role"] == "answer")
    answer["source_line_ids"] = list(answer["source_line_ids"])+list(target_lines)
    answer["evidence_refs"] = list(answer["evidence_refs"])+[r for r in target_lines if r not in answer["evidence_refs"]]
    answer["structural_complete"],answer["complete"],answer["assembly_status"] = True,False,"BOUNDED"
    answer["transcription_verified"] = False
    boundary = copy.deepcopy(plan.get("next_boundary_binding"))
    if boundary is None:
        boundary_line = units.get(plan["next_boundary_ref"])
        if boundary_line is None:raise ValueError("continuation boundary is not source bound")
        page,line = boundary_line
        boundary = {"kind":"SOURCE_PRIMARY_OR_SECTION_HEADING","line_ids":[line["line_id"]],
                    "text":line["text"],"asset_id":page["asset_id"],"bbox":copy.deepcopy(line["bbox"]),
                    "verification_status":"UNVERIFIED","business_acceptance":False}
    answer["boundary"] = {**boundary,"evidence_refs":list(boundary["line_ids"])}
    resolved_flags = [code for code in answer.get("assembly_flags",[]) if code == BOUNDARY_CODE]
    answer["active_assembly_flags"] = [code for code in answer.get("assembly_flags",[]) if code not in resolved_flags]
    answer["structural_resolution"] = {"proof_ref":_ref(proof),"check_ref":_ref(check),
                                         "resolved_legacy_flags":resolved_flags,"transcription_verified":False}
    continuation = {"kind":"CROSS_PAGE","from_asset_id":proof["payload"]["from_asset"]["asset_id"],
                    "to_asset_id":plan["to_asset_id"],"source_tail_line_id":plan["source_tail_line_id"],
                    "target_line_ids":list(target_lines),"proof_ref":_ref(proof),"check_ref":_ref(check),
                    "verification_status":"UNVERIFIED","business_acceptance":False}
    answer["continuations"] = copy.deepcopy(answer.get("continuations",[]))+[continuation]
    ledger = payload["answer_coverage"]
    def original_row(line_id):
        rows = [row for row in base["payload"]["answer_coverage"] if row["line_id"] == line_id]
        if len(rows) != 1:raise ValueError("continuation source coverage row is missing or repeated")
        return copy.deepcopy(rows[0])
    old_owners = [original_row(ref) for ref in target_lines]
    preserved_owners = [original_row(ref) for ref in base["payload"]["answers"][payload["answers"].index(answer)]["source_line_ids"]]
    for fragment in fresh:
        rows = [row for row in ledger if row["line_id"] == fragment["parent_line_id"]]
        if len(rows) != 1:raise ValueError("continuation target coverage is not unique")
        row = rows[0]
        row.update(status="CONSUMED",reason="VERSIONED_LOCAL_CONTINUATION_APPLIED",
                   answer_ids=[answer_id],fragment_ids=[fragment["fragment_id"]],
                   allocations=[{"answer_id":answer_id,"fragment_id":fragment["fragment_id"],
                                 "evidence_refs":copy.deepcopy(fragment["evidence_refs"]),"text_span":list(fragment["text_span"])}])
    resolved_issues = []
    for item in payload.get("issues",[]):
        if item.get("answer_id") == answer_id and item.get("code") == BOUNDARY_CODE:
            resolved_issues.append(copy.deepcopy(item))
            item.update(status="RESOLVED_STRUCTURAL_BOUNDARY",resolution_ref=_ref(proof),resolution_check_ref=_ref(check))
    payload["matching_status"] = "LOCAL_STRUCTURE_CONTINUED_UNVERIFIED"
    payload["selection_status"] = "DRAFT_UNVERIFIED_CONTINUATION_APPLIED"
    payload["decision"],payload["business_acceptance"],payload["platform_actions"] = "HOLD",False,[]
    payload["continuation_application"] = {"schema_version":APPLICATION_SCHEMA,"operation":"APPLY_LOCAL_ONLY",
        "base_graph_archive":copy.deepcopy(base),"base_graph_ref":_ref(base),"evidence_ref":_ref(evidence),
        "proof_archive":copy.deepcopy(proof),"proof_ref":_ref(proof),"image_review_ref":copy.deepcopy(image_review_ref),
        "validation_check_archive":copy.deepcopy(check),"validation_check_ref":_ref(check),
        "affected_answer_id":answer_id,"source_fragment_ids_preserved":original_fragment_ids,"added_fragment_ids":added_ids,
        "target_line_ids":list(target_lines),"old_line_owners":old_owners,"preserved_source_line_owners":preserved_owners,
        "render_region_ids":[r["region_id"] for r in projection],"image_region_ids":list(image_by_id),
        "boundary_binding":copy.deepcopy(boundary),"resolved_issues":resolved_issues,
        "resolved_assembly_flags":resolved_flags,"verification_status":"UNVERIFIED",
        "decision":"HOLD","business_acceptance":False,"platform_actions":[]}
    return payload


def apply_continuation(evidence,graph,proof,*,image_review,capture_root):
    """Revalidate and create schema 0.4; never mutate any supplied object."""
    check = validate_continuation(evidence,graph,proof,image_review=image_review,capture_root=capture_root)
    if not check["payload"]["accepted"] or check["payload"]["status"] != "VALIDATED_PROPOSAL":
        codes = ",".join(item["code"] for item in check["payload"]["issues"])
        raise ValueError("continuation rejected by current source validation: "+codes)
    _checked(image_review,{"b-image-review-trial/0.1"})
    if graph["payload"].get("continuation_application") is not None:
        raise ValueError("continuation has already been applied")
    if graph["payload"].get("platform_actions") != []:
        raise ValueError("local continuation cannot consume platform actions")
    payload = _payload(evidence,graph,proof,check,_ref(image_review))
    inputs = [_ref(evidence),_ref(graph),_ref(proof),_ref(image_review),_ref(check)]
    result = {"schema_version":GRAPH_SCHEMA,"kind":"QuestionGraphTrial","revision":graph["revision"]+1,
              "run_id":graph.get("run_id"),"book_id":graph["book_id"],"scope_id":graph["scope_id"],
              "input_refs":inputs,"supersedes":_ref(graph),"producer":{"module":__name__,"version":"0.1.0",
              "code_sha256":code_digest(Path(__file__)),"operation":"LOCAL_CONTINUATION_ONLY"},
              "created_at":datetime.now(timezone.utc).isoformat(),"payload":payload,"content_hash":digest(payload)}
    result["artifact_id"] = _graph_id(result)
    result["rollback_guard"] = {"schema_version":"b-continuation-rollback-guard-trial/0.1",
                                "expected_payload_hash":result["content_hash"],"requires_external_expected_graph_ref":True}
    return result


def rollback_continuation(evidence,derived,*,expected_graph_ref):
    """Restore the exact archived base only for the independently saved version.

    A rehashed edited graph is a later local state, even if its caller also
    updates internal guard fields. Rollback refuses to silently discard it.
    """
    _checked(evidence,{"b-evidence-trial/0.2","b-evidence-trial/0.3"})
    _checked(derived,{GRAPH_SCHEMA})
    if not isinstance(expected_graph_ref,dict) or expected_graph_ref != _ref(derived):
        raise ValueError("rollback graph differs from the independently retained version reference")
    guard = derived.get("rollback_guard",{})
    if (guard.get("expected_payload_hash") != digest(derived["payload"])
            or guard.get("requires_external_expected_graph_ref") is not True
            or derived.get("artifact_id") != _graph_id(derived)):
        raise ValueError("rollback graph changed after continuation apply")
    application = derived["payload"].get("continuation_application",{})
    if application.get("schema_version") != APPLICATION_SCHEMA or application.get("operation") != "APPLY_LOCAL_ONLY":
        raise ValueError("graph has no supported continuation application")
    base = application["base_graph_archive"]
    proof,check = application["proof_archive"],application["validation_check_archive"]
    _checked(base,{"b-graph-trial/0.2","b-graph-trial/0.3"})
    _checked(proof,{"b-continuation-proof-trial/0.1","b-continuation-proof-trial/0.2"})
    _checked(check,{"b-continuation-check-trial/0.1"})
    expected_inputs = [_ref(evidence),_ref(base),_ref(proof),application["image_review_ref"],_ref(check)]
    if (application["evidence_ref"] != _ref(evidence) or application["base_graph_ref"] != _ref(base)
            or application["proof_ref"] != _ref(proof) or application["validation_check_ref"] != _ref(check)
            or derived["input_refs"] != expected_inputs or derived.get("supersedes") != _ref(base)
            or derived["revision"] != base["revision"]+1
            or (derived["book_id"],derived["scope_id"],derived.get("run_id")) != (base["book_id"],base["scope_id"],base.get("run_id"))
            or check["input_refs"] != [_ref(evidence),_ref(base),_ref(proof)]
            or check["payload"].get("accepted") is not True
            or check["payload"].get("status") != "VALIDATED_PROPOSAL"):
        raise ValueError("rollback archives or source references changed")
    expected_payload = _payload(evidence,base,proof,check,application["image_review_ref"])
    if expected_payload != derived["payload"]:
        raise ValueError("rollback would discard subsequent local graph edits")
    return copy.deepcopy(base)
