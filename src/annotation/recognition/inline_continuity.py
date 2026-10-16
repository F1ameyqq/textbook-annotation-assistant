"""Unselected line-wrap relations from literal OCR spans in the current graph.

Nothing is corrected, simplified or selected. Model variants are diagnostics;
in particular a model-generated final operand is never silently discarded.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path
import re

from .baseline import code_digest, digest

MATH_CHARS = r'A-Za-z0-9\u0370-\u03ff\u2070-\u209f²³¹=+\-−×÷*/^_<>≤≥≠≈±∓√∛∜().（）\[\]{}:：|∥'
SUFFIX = re.compile('['+MATH_CHARS+']+$')
PREFIX = re.compile('['+MATH_CHARS+']+')
HEADING = re.compile(r'^\s*(?:\d+\s*[.、](?!\d)|[A-G]\s*[.、]|[（(]\d+[）)]|[①②③④⑤⑥⑦⑧⑨⑩])')
OPEN_MARKERS = '=+−-×÷*/^_(（<≤≥>:：'
RELATIONS = '<>≤≥'
POLICY = dict(version='LITERAL_CURRENT_GRAPH_LINE_WRAP/0.1', math_char_class=MATH_CHARS,
    open_markers=OPEN_MARKERS, relations=RELATIONS, max_vertical_gap_in_line_heights=2.5,
    minimum_horizontal_overlap_of_shorter_row=0.5,
    ordering='CENTER_Y_THEN_X_THEN_LINE_ID', intermediate_rows='ALL_RAW_ROWS_SAME_LOCATION',
    source_spans='EXACT_OCR_SUBSTRINGS', single_asset_only=True, glyph_localization_verified=False)


def _ref(value):
    return {key:value[key]for key in('artifact_id','revision','content_hash')}


def _box(value):
    return (isinstance(value,list)and len(value)==4
        and all(type(x)in(int,float)and math.isfinite(x)for x in value)
        and value[2]>value[0]and value[3]>value[1])


def _location(row):
    value=row.get('location',{})
    return value.get('column'),value.get('window_index'),value.get('section_path')


def _order(row):
    b=row['bbox']
    return ((b[1]+b[3])/2,b[0],row['line_id'])


def _binding(graph,page,row,start,end):
    """Require one semantic owner and gap/overlap-free current allocations."""
    asset_id=page['asset_id'];line_id=row['line_id'];source=row['text']
    entries=[r for r in graph['payload']['answer_coverage']if r.get('asset_id')==asset_id and r.get('line_id')==line_id]
    if len(entries)!=1 or entries[0].get('status')!='CONSUMED':
        return None,'SOURCE_NOT_UNIQUELY_CONSUMED'
    ledger=entries[0];found=[]
    for answer in graph['payload']['answers']:
        for f in answer.get('fragments',[]):
            if f.get('asset_id')!=asset_id or f.get('parent_line_id')!=line_id:continue
            span=f.get('text_span')
            if(not isinstance(span,list)or len(span)!=2 or any(type(x)is not int for x in span)
                    or not 0<=span[0]<span[1]<=len(source)):
                return None,'FRAGMENT_SOURCE_SPAN_INVALID'
            if span[1]<=start or span[0]>=end:continue
            if(f.get('content_type')!='text'or f.get('represented_by_image_region') is not None
                    or f.get('render_as_separate_region') is False or f.get('structural_marker') is True
                    or f.get('role')not in{'answer','explanation'}or f.get('text')!=source[span[0]:span[1]]
                    or f.get('source_sha256',page['source']['sha256'])!=page['source']['sha256']):
                return None,'FRAGMENT_NOT_LITERAL_TEXT'
            alloc=[a for a in ledger.get('allocations',[])if a.get('answer_id')==answer['answer_id']
                and a.get('fragment_id')==f['fragment_id']and a.get('text_span')==span]
            if len(alloc)!=1:return None,'FRAGMENT_ALLOCATION_MISMATCH'
            regions=sorted(r['region_id']for r in answer.get('render_regions',[])if r.get('content_type')=='text'
                and r.get('asset_id')==asset_id and f['fragment_id']in r.get('source_fragment_ids',[]))
            found.append(dict(answer_id=answer['answer_id'],role=f['role'],fragment_id=f['fragment_id'],
                text_span=copy.deepcopy(span),overlap_span=[max(start,span[0]),min(end,span[1])],render_region_ids=regions))
    if not found:return None,'NO_CURRENT_TEXT_OWNER'
    if len({(f['answer_id'],f['role'])for f in found})!=1:return None,'AMBIGUOUS_OR_MIXED_ROLE_OWNER'
    found.sort(key=lambda f:(f['overlap_span'],f['fragment_id']))
    cursor=start
    for f in found:
        if f['overlap_span'][0]!=cursor:return None,'FRAGMENT_COVERAGE_GAP_OR_OVERLAP'
        cursor=f['overlap_span'][1]
    if cursor!=end:return None,'FRAGMENT_COVERAGE_GAP_OR_OVERLAP'
    return dict(answer_id=found[0]['answer_id'],role=found[0]['role'],fragments=found),None


def build_inline_continuity(evidence,graph,layout,candidates,*,asset_id,line_ids):
    for value in(evidence,graph,layout,candidates):
        if value.get('content_hash')!=digest(value.get('payload')):raise ValueError('line-wrap input payload hash differs')
    if(graph.get('schema_version')not in{'b-graph-trial/0.2','b-graph-trial/0.3','b-graph-trial/0.4'}
            or (graph.get('book_id'),graph.get('scope_id'))!=(evidence.get('book_id'),evidence.get('scope_id'))):
        raise ValueError('line-wrap graph is not the current unextended source scope')
    if(not isinstance(line_ids,list)or not line_ids or any(not isinstance(s,str)for s in line_ids)
            or len(set(line_ids))!=len(line_ids)or layout['payload']['requested_line_ids']!=line_ids):
        raise ValueError('line-wrap requested rows differ from their layout')
    pages=[p for p in evidence['payload']['pages']if p['asset_id']==asset_id]
    if len(pages)!=1:raise ValueError('line-wrap asset is not unique')
    page=pages[0];rows=page['ocr_lines'];by_id={r['line_id']:r for r in rows}
    if(len(by_id)!=len(rows)or any(s not in by_id for s in line_ids)
            or any(not isinstance(r.get('text'),str)or not _box(r.get('bbox'))for r in rows)):
        raise ValueError('line-wrap raw rows/boxes are invalid')
    if(layout['payload']['source']['asset_id']!=asset_id
            or layout['payload']['source']['original_sha256']!=page['source']['sha256']):
        raise ValueError('line-wrap layout belongs to another source')
    units={u['unit_id']:u for u in layout['payload']['units']}
    if len(units)!=len(layout['payload']['units']):raise ValueError('duplicate inline math unit identity')
    selected=[by_id[s]for s in line_ids]
    proposals=[];rejected=[];diagnostics=[]
    for left,right in zip(selected,selected[1:]):
        lid,rid=left['line_id'],right['line_id'];reason=None
        loc=_location(left)
        locations=(_location(left),_location(right))
        if any(type(v[0])is not int or v[0]<0 or type(v[1])is not int or v[1]<0
                or not isinstance(v[2],list)or not v[2]or any(not isinstance(s,str)or not s for s in v[2])for v in locations):
            reason='SOURCE_LOCATION_UNKNOWN'
        elif _location(left)!=_location(right):reason='DIFFERENT_COLUMN_WINDOW_OR_SECTION'
        elif _order(left)>=_order(right):reason='REQUESTED_ROWS_NOT_IN_SOURCE_READING_ORDER'
        elif any(_location(r)==_location(left)and _order(left)<_order(r)<_order(right)for r in rows):reason='INTERVENING_RAW_SOURCE_ROW'
        else:
            gap=right['bbox'][1]-left['bbox'][3]
            height=max(left['bbox'][3]-left['bbox'][1],right['bbox'][3]-right['bbox'][1])
            if gap<0 or gap>2.5*height:reason='VERTICAL_WRAP_GEOMETRY_UNPROVEN'
            elif(max(0,min(left['bbox'][2],right['bbox'][2])-max(left['bbox'][0],right['bbox'][0]))
                    <0.5*min(left['bbox'][2]-left['bbox'][0],right['bbox'][2]-right['bbox'][0])):
                reason='HORIZONTAL_COLUMN_GEOMETRY_UNPROVEN'
        lm,rm=SUFFIX.search(left['text']),PREFIX.match(right['text'])
        if reason is None and HEADING.match(right['text']):reason='NEXT_ROW_LOOKS_LIKE_NEW_QUESTION'
        kind=None
        if reason is None and lm and rm:
            lt,rt=lm.group(),rm.group()
            if lt[-1]in OPEN_MARKERS and any(c.isalnum()for c in lt)and any(c.isalnum()for c in rt):
                kind='OPEN_EQUATION_LINE_WRAP'
            elif rt[0]in RELATIONS and any(c in RELATIONS for c in lt)and any(c.isalnum()for c in rt):
                kind='CHAINED_RELATION_LINE_WRAP'
        if reason is None and kind is None:reason='NO_EXPLICIT_MATH_WRAP_MARKER'
        if reason is not None:
            rejected.append(dict(left_line_id=lid,right_line_id=rid,reason=reason));continue
        spans=[dict(asset_id=asset_id,line_id=lid,text_span=list(lm.span()),text=lm.group()),
               dict(asset_id=asset_id,line_id=rid,text_span=list(rm.span()),text=rm.group())]
        bindings=[]
        for row,span in zip((left,right),spans):
            binding,error=_binding(graph,page,row,*span['text_span'])
            if error:reason=error;break
            bindings.append(binding)
        if reason is None and any(bindings[0][k]!=bindings[1][k]for k in('answer_id','role')):reason='DIFFERENT_CURRENT_ANSWER_OR_ROLE'
        if reason is not None:
            rejected.append(dict(left_line_id=lid,right_line_id=rid,reason=reason));continue
        risks=['UNVERIFIED_RAW_OCR','HEURISTIC_MATH_BOUNDARIES','SINGLE_ASSET_RELATION_ONLY']
        if '.'in lm.group()+rm.group():risks.append('DOT_MAY_BE_PUNCTUATION_OR_DECIMAL')
        proposal=dict(kind=kind,left_line_id=lid,right_line_id=rid,source_spans=spans,bindings=bindings,
            joined_raw_text=lm.group()+rm.group(),evidence_quality='LITERAL_UNVERIFIED_OCR_SPANS',risks=risks,
            selected=False,complete=False,transcription_verified=False,business_acceptance=False)
        proposal['proposal_id']='inline-wrap-'+digest([_ref(evidence),_ref(graph),proposal])[:24]
        proposals.append(proposal)
        if kind=='OPEN_EQUATION_LINE_WRAP'and lm.group().endswith('='):
            for candidate in candidates['payload']['candidates']:
                for binding in candidate['unit_bindings']:
                    unit=units.get(binding['unit_id'])
                    if(unit is None or unit.get('line_id')!=lid or not unit.get('raw_text','').endswith('=')):continue
                    raw=candidate.get('raw_latex')
                    if isinstance(raw,str)and re.search(r'=[^=]*[A-Za-z0-9}]\s*$',raw):
                        diagnostics.append(dict(code='MODEL_CLOSURE_AFTER_RAW_OPEN_EQUATION',proposal_id=proposal['proposal_id'],
                            unit_id=unit['unit_id'],call_id=candidate['call_id'],candidate_id=candidate['candidate_id'],raw_latex=raw))
    payload=dict(asset_id=asset_id,requested_line_ids=copy.deepcopy(line_ids),source_sha256=page['source']['sha256'],
        proposals=proposals,diagnostics=diagnostics,rejected_adjacent_pairs=rejected,selected_proposal_ids=[],
        decision='HOLD',complete=False,transcription_verified=False,business_acceptance=False,graph_modified=False,
        platform_actions=[],new_model_calls=0,expected_text_consumed=False)
    body=dict(schema_version='b-inline-continuity-trial/0.1',kind='InlineContinuityTrial',revision=1,
        book_id=evidence['book_id'],scope_id=evidence['scope_id'],input_refs=[_ref(v)for v in(evidence,graph,layout,candidates)],
        producer=dict(module=__name__,version='0.1.0',code_sha256=code_digest(Path(__file__)),policy=POLICY),payload=payload)
    return {**body,'artifact_id':'inline-continuity-'+digest(body)[:24],'content_hash':digest(payload)}
