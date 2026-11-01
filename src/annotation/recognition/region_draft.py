"""Automatic, unverified region drafts from recorded source observations.

Role combinations are derived candidates, never relabelled complete model calls.
No reference transcription or expected answer is accepted by this module.
"""
from __future__ import annotations

import copy
from pathlib import Path

from .baseline import code_digest, digest
from .content_revision import _visible, make_revision_plan, reference
from .formula_candidates import build_formula_candidates
from .formula_canvas import build_canvas_candidates
from .formula_canvas_quality import audit_canvas_candidates
from .formula_syntax import fraction_count, parse_formula_latex, parse_inline_formula_latex
from .math_reading import _bound_layout, _bound_evidence
from .region_ocr import validate_region_observations
from .region_runs import plan_region_runs

POLICY = "ROLE_AGREEMENT_ELSE_FIRST_SHAPE_CORE_BODY_SYMBOL_CONTEXT/0.1"


def _flags():
    return dict(decision="HOLD", complete=False, transcription_verified=False,
                business_acceptance=False, expected_text_consumed=False, platform_actions=[])


def _id(prefix, value):
    return prefix+"-"+digest(value)[:24]


def _fraction_node(ast):
    if not isinstance(ast, dict):
        return None
    if ast.get("type") == "fraction":
        return ast
    if ast.get("type") == "group" and ast.get("delimiters") == "{}":
        return _fraction_node(ast["body"])
    if ast.get("type") == "sequence" and len(ast["items"]) == 1:
        return _fraction_node(ast["items"][0])
    return None


def _role_tex(raw):
    # Explicit character transcoding, without inferring a missing exponent,
    # correcting punctuation, cancelling terms or changing algebraic value.
    table = {"²": "^{2}", "³": "^{3}", "⁴": "^{4}", "−": "-"}
    pieces, mapping = [], []
    for i, char in enumerate(raw):
        text = table.get(char, char)
        pieces.append(text)
        mapping.append(dict(source_span=[i,i+1], text=text))
    return "".join(pieces), mapping


def _component(fid, role, tex, origin):
    parsed = parse_inline_formula_latex(tex)
    value = dict(fraction_id=fid, role=role, latex=tex, origin=origin,
                 parse_result=parsed, verification_status="UNVERIFIED")
    value["component_id"] = _id("region-role-component", value)
    return value


def _fraction_candidates(layout, legacy, canvas, roles, crop):
    old = build_formula_candidates(layout, legacy, crop)
    new = build_canvas_candidates(layout, canvas, crop, legacy)
    audit = audit_canvas_candidates(layout, canvas, new, crop, legacy)
    if audit["payload"].get("accepted") is not True:
        raise ValueError("formula source/canvas audit rejected observations")
    _bound_evidence(layout, roles, _bound_layout(layout, crop))
    role_index = {(u["fraction_id"], u["role"]): u for u in roles["payload"]["roles"]}
    result = []
    for fraction, old_unit, new_unit in zip(layout["payload"]["fraction_candidates"],
                                           old["payload"]["units"], new["payload"]["units"]):
        fid = fraction["fraction_id"]
        components = {role: [] for role in ("numerator", "denominator")}
        whole = []
        for document, unit, kind in ((legacy,old_unit,"LEGACY_WHOLE"),(canvas,new_unit,"CANVAS_WHOLE")):
            if unit["fraction_id"] != fid:
                raise ValueError("whole formula belongs to a different source fraction")
            for variant in unit["variants"]:
                raw = variant["raw_latex"]
                parsed = parse_formula_latex(raw)
                tree = _fraction_node(parsed["ast"]) if parsed["supported"] else None
                shape = tree is not None and fraction_count(parsed["ast"]) == 1
                origin = dict(kind=kind, observation_ref=reference(document), unit_id=unit["unit_id"],
                              fraction_id=fid, variant_id=variant["variant_id"], raw_latex=raw)
                candidate = dict(kind="WHOLE_MODEL_OBSERVATION", latex=raw, origin=origin,
                                 source_fraction_shape_matches=shape, parse_result=parsed,
                                 verification_status="UNVERIFIED")
                candidate["candidate_id"] = _id("region-whole", candidate)
                whole.append(candidate)
                if not shape:
                    continue
                for role in components:
                    node = tree[role]
                    lo, hi = node["raw_source_span"]
                    # Removing only a syntactic brace pair preserves the operand.
                    if node.get("type") == "group" and node.get("delimiters") == "{}":
                        lo, hi = lo+1, hi-1
                    components[role].append(_component(fid, role, raw[lo:hi],
                        dict(**origin, raw_source_span=[lo,hi], raw_source_text=raw[lo:hi])))
        for role in components:
            unit = role_index[(fid, role)]
            for variant in unit["variants"]:
                for raw_candidate in variant["candidates"]:
                    tex, mapping = _role_tex(raw_candidate["text"])
                    components[role].append(_component(fid, role, tex, dict(kind="ROLE_OCR",
                        observation_ref=reference(roles), role_id=unit["role_id"], fraction_id=fid,
                        role=role, variant_id=variant["variant_id"], candidate_id=raw_candidate["candidate_id"],
                        raw_text=raw_candidate["text"], codepoint_transcoding=mapping)))
        composed = []
        for num in components["numerator"]:
            for den in components["denominator"]:
                if not num["parse_result"]["supported"] or not den["parse_result"]["supported"]:
                    continue
                latex = r"\frac{"+num["latex"]+"}{"+den["latex"]+"}"
                parsed = parse_formula_latex(latex)
                if not parsed["supported"] or parsed["normalized_ast"].get("type") != "fraction" or fraction_count(parsed["ast"]) != 1:
                    continue
                candidate = dict(kind="DERIVED_ROLE_COMPOSITION", fraction_id=fid, latex=latex,
                    component_refs=[num["component_id"],den["component_id"]],
                    parse_result=parsed, verification_status="UNVERIFIED", complete_model_call=False)
                candidate["candidate_id"] = _id("region-composed", candidate)
                composed.append(candidate)
        if len(composed) > 256:
            raise ValueError("composition budget exceeded; no candidates silently truncated")
        stable = {}
        for role, values in components.items():
            only = [c for c in values if c["origin"]["kind"] == "ROLE_OCR"]
            if (len(only) == 2 and len({c["origin"]["variant_id"] for c in only}) == 2
                    and all(c["parse_result"]["supported"] for c in only)
                    and only[0]["parse_result"]["normalized_ast"] == only[1]["parse_result"]["normalized_ast"]):
                stable[role] = only[0]["component_id"]
        selected = next((c for c in composed if c["component_refs"] == [stable.get("numerator"),stable.get("denominator")]), None)
        if selected is None:
            selected = next((c for c in whole if c["source_fraction_shape_matches"]), None)
        if selected is None and composed:
            selected = composed[0]
        result.append(dict(fraction_id=fid, whole_candidates=whole, components=components,
                           composed_candidates=composed, draft_candidate_id=selected["candidate_id"] if selected else None,
                           selection_policy=POLICY, selection_is_content_verification=False,
                           risks=["ALL_CANDIDATES_UNVERIFIED", "AGREEMENT_CAN_BE_WRONG", "FIRST_DRAFT_REQUIRES_SOURCE_REVIEW"]))
    return result


def build_region_draft(plan, observations, legacy, canvas, roles, crop_path):
    """Retain all alternatives and interleave deterministic first-draft runs.

    Body OCR context may contain neighbouring ink. No CTC cut is invented to
    delete it; that ambiguity is retained in the candidate and exported note.
    """
    expected=plan_region_runs(plan["payload"]["layout_archive"],crop_path)
    if (expected["payload"]!=plan["payload"] or any(expected["producer"][k]!=plan["producer"].get(k)
            for k in ("module","version","code_sha256","configuration","configuration_sha256"))):
        raise ValueError("pixel run plan differs from the source-derived geometry/accounting")
    audit = validate_region_observations(plan, observations, crop_path)
    if audit["payload"].get("accepted") is not True:
        raise ValueError("region OCR source/projection audit rejected observations")
    layout = plan["payload"]["layout_archive"]
    fractions = _fraction_candidates(layout, legacy, canvas, roles, crop_path)
    by_fraction = {c["fraction_id"]:c for c in fractions}
    units = {u["slot_id"]:u for u in observations["payload"]["units"]}
    slots = {s["slot_id"]:s for s in plan["payload"]["fraction_slots"]+plan["payload"]["body_slots"]}
    rows, risks = [], copy.deepcopy(plan["payload"]["risks"])
    for row in plan["payload"]["rows"]:
        runs, bindings, missing = [], [], False
        for sid in row["slot_ids"]:
            slot = slots[sid]
            if slot["kind"] == "FRACTION":
                candidates = by_fraction[slot["fraction_id"]]
                all_candidates = candidates["whole_candidates"]+candidates["composed_candidates"]
                chosen = next((c for c in all_candidates if c["candidate_id"] == candidates["draft_candidate_id"]), None)
                if chosen is None:
                    risks.append(dict(code="NO_FORMULA_DRAFT",slot_id=sid));missing=True;continue
                runs.append(dict(format="latex",text=chosen["latex"]))
                bindings.append(dict(run_index=len(runs)-1,slot_id=sid,candidate_id=chosen["candidate_id"],kind=chosen["kind"]))
            else:
                unit = units[sid]
                def usable(variant):
                    return [c for c in variant["candidates"] if c.get("usable") is True and isinstance(c.get("text"),str) and c["text"]]
                first=unit["variants"][0]
                # The first fixed profile reads the core interval; context
                # alternatives cannot silently become exact body text.
                chosen = first if first["recognition_error"] is None and usable(first) else None
                context_symbol=False
                if chosen is None:
                    context=unit["variants"][1]
                    text="".join(c["text"] for c in usable(context))
                    # A bounded punctuation/operator-only observation can be
                    # offered as a draft when the core missed a small glyph.
                    # Never import contextual letters/numbers from a fraction.
                    if (context["recognition_error"] is None and text.strip() and len(text)<=8
                            and all(not char.isalnum() for char in text)):
                        chosen=context;context_symbol=True
                if not slot["component_ids"]:
                    # Context-only hallucinations stay in observations, not in
                    # the first draft of an empty primary source interval.
                    if chosen is not None:
                        risks.append(dict(code="EMPTY_BODY_CONTEXT_ONLY_OCR",slot_id=sid))
                    continue
                if chosen is None:
                    risks.append(dict(code="BODY_OCR_UNREAD",slot_id=sid));missing=True;continue
                accepted=usable(chosen)
                if context_symbol:
                    risks.append(dict(code="CONTEXT_SYMBOL_OWNERSHIP_UNVERIFIED",slot_id=sid))
                if len(accepted)!=len(chosen["candidates"]):
                    risks.append(dict(code="UNUSABLE_BODY_CANDIDATES_NOT_TRANSCRIBED",slot_id=sid))
                text = "".join(c["text"] for c in accepted)
                if text:
                    runs.append(dict(format="plain",text=text))
                    bindings.append(dict(run_index=len(runs)-1,slot_id=sid,variant_id=chosen["variant_id"],
                        candidate_ids=[c["candidate_id"] for c in accepted],kind="BODY_CONTEXT_SYMBOL" if context_symbol else "BODY_OCR",
                        source_bbox=slot["source_bbox"],recognition_source_bbox=chosen["source_bbox"]))
        segmented=copy.deepcopy(dict(runs=runs,bindings=bindings))
        fallback_used=False
        if missing:
            fallback=units[row["full_row_fallback"]["slot_id"]]
            variant=next((v for v in fallback["variants"] if v["recognition_error"] is None
                and all(c.get("usable") is True and isinstance(c.get("text"),str) for c in v["candidates"])
                and any(c.get("text") for c in v["candidates"])),None)
            if variant is not None:
                runs=[dict(format="plain",text="".join(c["text"] for c in variant["candidates"]))]
                bindings=[dict(run_index=0,slot_id=fallback["slot_id"],kind="FULL_ROW_FALLBACK",variant_id=variant["variant_id"],
                    candidate_ids=[c["candidate_id"] for c in variant["candidates"]])]
                fallback_used=True
                risks.append(dict(code="FULL_ROW_FALLBACK_READING_ORDER_UNVERIFIED",row_id=row["row_id"]))
        rows.append(dict(row_id=row["row_id"],source_bbox=row["source_bbox"],runs=runs,bindings=bindings,
                         segmented_draft=segmented,draft_available=not missing or fallback_used,
                         full_row_fallback_used=fallback_used,full_row_fallback_slot=row["full_row_fallback"]["slot_id"]))
    payload = dict(plan_ref=reference(plan),observation_ref=reference(observations),source=copy.deepcopy(plan["payload"]["source"]),
        rows=rows,fractions=fractions,risks=risks,selection_policy=POLICY,
        archives=dict(plan=copy.deepcopy(plan),observations=copy.deepcopy(observations),legacy=copy.deepcopy(legacy),canvas=copy.deepcopy(canvas),roles=copy.deepcopy(roles)),
        source_projection_audit=audit,body_context_is_exact_character_alignment=False,**_flags())
    synthetic=any(x["producer"].get("execution_kind")=="SYNTHETIC_TEST" for x in (observations,legacy,canvas,roles))
    producer=dict(module=__name__,version="0.1.0",code_sha256=code_digest(Path(__file__)),
                  execution_kind="SYNTHETIC_TEST" if synthetic else "DERIVED_CPU_DRAFT")
    inputs=[reference(x) for x in (plan,observations,legacy,canvas,roles)]
    return dict(schema_version="b-region-draft-trial/0.1",kind="RegionDraftTrial",artifact_id=_id("region-draft",[inputs,producer,payload]),
        revision=1,book_id=plan["book_id"],scope_id=plan["scope_id"],input_refs=inputs,producer=producer,payload=payload,content_hash=digest(payload))


def make_region_draft_plan(evidence, graph, check, draft, *, answer_id, previous_plan, author, crop_path):
    """Create a separate unverified plan branch; keep old operations/history.

    All current answer source fragments must fit exactly one planned row.
    Failure leaves the candidate bundle available, without a partial revision.
    """
    if draft.get("content_hash") != digest(draft.get("payload")) or draft.get("schema_version") != "b-region-draft-trial/0.1":
        raise ValueError("region draft changed")
    if any(draft["payload"].get(k)!=v for k,v in _flags().items()):
        raise ValueError("region draft cannot claim approval")
    archive=draft["payload"]["archives"]
    rebuilt=build_region_draft(archive["plan"],archive["observations"],archive["legacy"],archive["canvas"],archive["roles"],crop_path)
    if draft!=rebuilt:
        raise ValueError("region draft differs from deterministic source observation projection")
    expected_author="SYNTHETIC_TEST" if draft["producer"].get("execution_kind")=="SYNTHETIC_TEST" else "MODEL_DRAFT"
    if author.get("kind") != expected_author:
        raise ValueError("automatic draft author must preserve synthetic/CPU draft provenance")
    source=draft["payload"]["source"]
    answers=[a for a in graph["payload"]["answers"] if a["answer_id"]==answer_id]
    if len(answers)!=1 or evidence["book_id"]!=draft["book_id"] or graph["book_id"]!=draft["book_id"]:
        raise ValueError("region draft target scope differs")
    visible,_=_visible(answers[0])
    def inside(a,b):return b[0]<=a[0]<a[2]<=b[2] and b[1]<=a[1]<a[3]<=b[3]
    fragments=[f for f in visible if f["asset_id"]==source["asset_id"] and inside(f["bbox"],source["crop_bbox"])]
    if not fragments or any(f["role"]!="answer" for f in fragments):raise ValueError("expected one source-bound answer role")
    blocks=[];assigned=[]
    for row in draft["payload"]["rows"]:
        ids=[f["fragment_id"] for f in fragments if inside(f["bbox"],row["source_bbox"])]
        if not row["runs"] or row["draft_available"] is not True:raise ValueError("unread automatic row remains candidate-only")
        assigned+=ids
        blocks.append(dict(block_id=_id("automatic-row",row["row_id"]),bbox=copy.deepcopy(row["source_bbox"]),source_fragment_ids=ids,runs=copy.deepcopy(row["runs"]),
            note="Automatic source OCR/formula draft; context overlaps and unresolved ink remain. Bundle "+draft["artifact_id"]+"; not verified."))
    if len(assigned)!=len(fragments) or set(assigned)!={f["fragment_id"] for f in fragments}:
        raise ValueError("automatic row split cuts an existing source fragment; candidate only")
    operation=dict(kind="REBUILD_TEXT_REGION",operation_id=_id("automatic-region",[answer_id,reference(draft)]),
        target=dict(answer_id=answer_id,role="answer",source_fragment_ids=[f["fragment_id"] for f in fragments]),
        source_region=dict(asset_id=source["asset_id"],source_sha256=source["source_sha256"],source_size=copy.deepcopy(source["source_size"]),bbox=copy.deepcopy(source["crop_bbox"])),
        blocks=blocks,reason="Automatic unverified first draft from source-bound observations; no reference transcription consumed.")
    operations=[copy.deepcopy(o) for o in previous_plan["payload"]["operations"] if not(o["kind"]=="REBUILD_TEXT_REGION" and o["target"]["answer_id"]==answer_id)]
    operations.append(operation)
    return make_revision_plan(evidence,graph,check,operations,author,previous_plan=previous_plan)
