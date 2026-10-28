"""Visible formula-region suggestions from retained layout and OCR geometry.

No recognition is performed while listing. Chinese mixed rows are explicitly
coarse suggestions; a customer can inspect/adjust them instead of inventing
token geometry. Existing layout regions take precedence over row suggestions.
"""
from __future__ import annotations

import copy
import math
import re

from .source_review_projection import project_candidate
from .store import Hold,digest

MATH = re.compile(r'[=＝+＋−×÷√∛∜^²³⁴⁵⁶⁷⁸⁹∠⊥∥≤≥≠]|[A-Za-z][0-9]|[0-9][A-Za-z]|\d\s*[-/]\s*\d')
CHINESE = re.compile(r'[\u3400-\u9fff]')


def _overlaps(a,b):
    return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])


def _merge_clear_regions(regions,lines):
    """Resolve all same-owner region overlaps before any recognition intent."""
    pending=list(regions);result=[]
    while pending:
        first=pending.pop(0)
        component=[first]
        while True:
            box=[min(r['bbox'][0] for r in component),min(r['bbox'][1] for r in component),
                 max(r['bbox'][2] for r in component),max(r['bbox'][3] for r in component)]
            matching=[row for row in pending
                      if all(row[key]==first[key] for key in ('candidate_key','zone','asset_id','source_sha256'))
                      and _overlaps(row['bbox'],box)]
            if not matching:break
            component.extend(matching);pending=[row for row in pending if row not in matching]
        component.sort(key=lambda row:regions.index(row))
        covered=[(ref,line) for ref,(page,line) in lines.items()
                 if page['asset_id']==first['asset_id'] and _overlaps(box,line['bbox'])]
        mixed=any(row['uncertainty']!='OBSERVED_MATH_ROW' for row in component) or any(CHINESE.search(line['text']) for _,line in covered)
        if len(component)==1 and not mixed:
            result.append(first);continue
        body={key:copy.deepcopy(value) for key,value in first.items() if key not in
              {'proposal_id','status','model_called','content_approved','can_confirm_existing_region','adjustment_available'}}
        refs=set(ref for row in component for ref in row['evidence_refs'])|{ref for ref,_ in covered}
        ordered_refs=[ref for ref in lines if ref in refs]
        ordered_refs.extend(ref for row in component for ref in row['evidence_refs'] if ref not in ordered_refs)
        body.update(bbox=box,origin='RETAINED_CONNECTED_SOURCE_REGIONS' if len(component)>1 else first['origin'],
                    uncertainty='MIXED_TEXT_COARSE_REGION' if mixed else 'OBSERVED_MATH_ROW',
                    evidence_refs=list(dict.fromkeys(ordered_refs)),
                    covered_source_lines=[{'line_id':ref,'line_sha256':digest(line),'line':copy.deepcopy(line)} for ref,line in covered],
                    source_regions=[{key:copy.deepcopy(row[key]) for key in
                                     ('proposal_id','bbox','evidence_refs','origin','uncertainty','layout_ref')} for row in component])
        bounds=[row['adjustment_bounds'] for row in component]
        body['adjustment_bounds']=[min(b[0] for b in bounds),min(b[1] for b in bounds),max(b[2] for b in bounds),max(b[3] for b in bounds)]
        result.append({'proposal_id':digest(body),**body,'status':'REGION_REVIEW_REQUIRED','model_called':False,
                       'content_approved':False,'can_confirm_existing_region':True,'adjustment_available':True})
    return result


def propose(candidate, graph, evidence, *, layouts=()):
    projection=project_candidate(candidate,graph,evidence,layouts=layouts)
    lines={line['line_id']:(page,line) for page in evidence['payload']['pages'] for line in page['ocr_lines']}
    regions,seen=[],set()
    for zone in projection['zones']:
        for segment in zone['segments']:
            size=segment['source_dimensions'];covered=set()
            items=[]
            for hint in segment['formula_hints']:
                observation=hint['observation']
                if hint['kind']=='INLINE_OBSERVATION' and observation.get('kind')!='MATHLIKE_RUN':
                    continue
                items.append((hint['source_bbox'],'RETAINED_LAYOUT',hint['uncertainty'],
                              segment['evidence_refs'],hint.get('layout_ref')))
                if observation.get('line_id'):covered.add(observation['line_id'])
            for ref in segment['evidence_refs']:
                if ref in covered or ref not in lines:
                    continue
                page,line=lines[ref]
                if page['asset_id']!=segment['asset_id'] or not MATH.search(line['text']):
                    continue
                # Keep whole observed line geometry; no character-index to
                # pixel interpolation or guessed missing exponent/radical.
                coarse=bool(CHINESE.search(line['text']))
                items.append((line['bbox'],'RETAINED_OCR_LINE',
                              'MIXED_TEXT_COARSE_REGION' if coarse else 'OBSERVED_MATH_ROW', [ref],None))
            for raw_box,origin,uncertainty,refs,layout_ref in items:
                box=[max(0,math.floor(raw_box[0])-2),max(0,math.floor(raw_box[1])-2),
                     min(size[0],math.ceil(raw_box[2])+2),min(size[1],math.ceil(raw_box[3])+2)]
                identity=(zone['zone'],segment['asset_id'],tuple(box))
                if identity in seen or box==[0,0,*size]:continue
                seen.add(identity)
                body={'candidate_key':candidate['key'],'zone':zone['zone'],'asset_id':segment['asset_id'],
                      'source_sha256':segment['source_sha256'],'source_dimensions':size,'bbox':box,
                      'adjustment_bounds':[max(0,math.floor(min(box[0],segment['source_frame_bbox'][0]))),
                                           max(0,math.floor(min(box[1],segment['source_frame_bbox'][1]))),
                                           min(size[0],math.ceil(max(box[2],segment['source_frame_bbox'][2]))),
                                           min(size[1],math.ceil(max(box[3],segment['source_frame_bbox'][3])))],
                      'origin':origin,'uncertainty':uncertainty,'evidence_refs':list(refs),'layout_ref':layout_ref}
                regions.append({'proposal_id':digest(body),**body,'status':'REGION_REVIEW_REQUIRED',
                                'model_called':False,'content_approved':False,
                                'can_confirm_existing_region':True,'adjustment_available':True})
    regions=_merge_clear_regions(regions,lines)
    return {'schema':'CustomerFormulaRegions/v1','candidate_key':candidate['key'],
            'regions':regions,'rejected_layouts':projection['rejected_layouts'],'model_calls':0,
            'limitations':['Coarse mixed text rows require source-visible confirmation or adjustment.',
                           'No claim that all mathematical glyphs or formulas were detected.']}


def mark_boundary_conflicts(regions):
    """Keep cross-owner uncertainty explicit and outside automatic batches."""
    rows=copy.deepcopy(regions)
    for index,row in enumerate(rows):
        for other in rows[index+1:]:
            if row['source_sha256']!=other['source_sha256'] or not _overlaps(row['bbox'],other['bbox']):continue
            if row['candidate_key']==other['candidate_key'] and row['zone']==other['zone']:
                raise Hold('同题公式区域仍有未解决的重叠，整批尚未开始。')
            reason=('CROSS_QUESTION_BOUNDARY_REVIEW' if row['candidate_key']!=other['candidate_key']
                    else 'CROSS_ROLE_BOUNDARY_REVIEW')
            for selected,peer in ((row,other),(other,row)):
                selected.setdefault('prior_uncertainty',selected['uncertainty'])
                selected.update(uncertainty=reason,boundary_review_required=True,batch_eligible=False,can_confirm_existing_region=False)
                selected.setdefault('boundary_conflicts',[]).append({key:copy.deepcopy(peer[key]) for key in
                    ('proposal_id','candidate_key','zone','source_sha256','bbox')})
    return rows


def propose_job(job,graph,evidence,*,layouts=()):
    proposals={candidate['key']:propose(candidate,graph,evidence,layouts=layouts) for candidate in job['candidates']}
    pending={candidate['key'] for candidate in job['candidates'] if candidate['platform_status']=='NOT_RUN'}
    rows=mark_boundary_conflicts([row for key,value in proposals.items() if key in pending for row in value['regions']])
    for key in pending:proposals[key]['regions']=[row for row in rows if row['candidate_key']==key]
    return proposals


def require_resolved_boundary(selected,box):
    if not selected.get('boundary_review_required'):return
    if box==selected['bbox'] or any(_overlaps(box,peer['bbox']) for peer in selected['boundary_conflicts']):
        raise Hold('此范围与相邻题目或分区重叠；请在原图中调整为不重叠的公式范围后再识别。')


def consumed_records(store,book):
    """Read durable region attempts without changing failure or cache state."""
    import sqlite3
    from contextlib import closing
    from .formula_roi_cache import KIND,_check_request
    result=[]
    with closing(sqlite3.connect((store.root/'state.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        rows=db.execute('SELECT key,state,output FROM operations WHERE kind=?',(KIND,)).fetchall()
    for key,state,reference in rows:
        if reference is None:raise Hold('已有公式调用中断且范围未保留，先保留原任务，不启动其他区域。')
        value=store.get(reference);request=value.get('request')
        if type(request) is not dict:raise Hold('已有公式调用缺少原始范围记录。')
        _check_request(request)
        if request['roi_key']!=key or state not in {'COMPLETE','FAILED_NO_RETRY','INTENT'}:
            raise Hold('已有公式调用身份或状态不一致。')
        if request['roi_identity']['book_id']==book:
            result.append({'key':key,'state':state,'output':reference,'request':request})
    return result


def mark_consumed_regions(store,book,regions):
    records=consumed_records(store,book);rows=copy.deepcopy(regions)
    for row in rows:
        overlaps=[old for old in records if old['request']['roi_identity']['source_sha256']==row['source_sha256']
                  and _overlaps(row['bbox'],old['request']['roi_identity']['source_bbox'])]
        if not overlaps:continue
        failed=any(old['state']!='COMPLETE' for old in overlaps)
        row.setdefault('prior_uncertainty',row['uncertainty'])
        row.update(uncertainty='FORMULA_REGION_FAILED_NO_REPLAY' if failed else 'FORMULA_CANDIDATE_RETAINED',
                   recognition_blocked=True,batch_eligible=False,can_confirm_existing_region=False,
                   prior_model_call_status='UNKNOWN_OR_FAILED' if failed else 'COMPLETE_CANDIDATE',
                   manual_resolution_required=failed,
                   consumed_operations=[{'key':old['key'],'state':old['state'],'output':old['output'],
                     'bbox':old['request']['roi_identity']['source_bbox']} for old in overlaps])
    return rows


def recognize_proposal(store,identity,expected_head,candidate_key,proposal_id,settings,*,source_checked=False,adjusted_bbox=None,layouts=()):
    """Normal review action: recompute the suggestion under current book lock."""
    from .formula_runtime import obtain_region
    from .source import verify_sources
    job,head=store.job(identity)
    with store.book_lock(job['book_id']):
        job,head=store.job(identity)
        if head!=expected_head:raise Hold('任务已更新，请刷新公式区域后再识别。')
        verify_sources(job['pages'])
        candidate=next((q for q in job['candidates'] if q['key']==candidate_key),None)
        if candidate is None or candidate.get('platform_status')!='NOT_RUN':
            raise Hold('这题已发送或状态未知，不能重新识别或改写。')
        suggestions=propose_job(job,store.get(job['graph_ref']),store.get(job['evidence_ref']),layouts=layouts)[candidate_key]
        suggestions['regions']=mark_consumed_regions(store,job['book_id'],suggestions['regions'])
        selected=next((r for r in suggestions['regions'] if r['proposal_id']==proposal_id),None)
        if selected is None or source_checked is not True:raise Hold('请核对当前原图中的公式区域。')
        if selected.get('recognition_blocked'):raise Hold('此范围已有识别记录；失败范围请对照原图人工修正，不换裁剪重跑。')
        page=next(p for p in job['pages'] if p['asset_id']==selected['asset_id'])
        box=selected['bbox'] if adjusted_bbox is None else adjusted_bbox
        if adjusted_bbox is not None:
            original=selected['adjustment_bounds']
            if type(box) is not list or len(box)!=4 or any(type(n) is not int for n in box):
                raise Hold('公式调整区域无效。')
            if not (original[0]<=box[0]<box[2]<=original[2] and original[1]<=box[1]<box[3]<=original[3]):
                raise Hold('公式区域调整须保留在当前可见来源段内。')
        require_resolved_boundary(selected,box)
        result=obtain_region(store,page,job['book_id'],box,settings,allow_first_local_call=True)
        return {**result,'proposal_id':proposal_id,'candidate_key':candidate_key,'head':head,
                'candidate_modified':False,'content_application':'EXPLICIT_REVIEW_REQUIRED'}
