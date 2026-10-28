"""Finite automatic readiness for clear ordinary text images.

This is a machine quality gate, not a human transcription claim. Unexplained
ink, low confidence, mathematical layout and figures remain explicit exceptions.
"""
import re
from pathlib import Path
from .store import digest

MATH_LAYOUT=re.compile(r'[²³⁰¹⁴⁵⁶⁷⁸⁹√±×÷=<>≤≥∠⊥∥∽\\$]|[a-zA-Z]\s*[+−-]|\d\s*[+−-]\s*\d')

def assess(candidate,graph,evidence,pages):
    if candidate['source_kind']!='IMAGE_OCR':return
    question=next(q for q in graph['payload']['questions'] if q['question_id']==candidate['question_id'])
    answer=next((a for a in graph['payload']['answers'] if a['answer_id']==question['selected_answer_id']),None)
    fragments=question['fragments']+(answer['fragments'] if answer else [])
    line_map={line['line_id']:line for page in evidence['payload']['pages']
              for field in ('ocr_lines','answer_detail_lines') for line in page.get(field,[])}
    refs={r for fragment in fragments for r in fragment.get('evidence_refs',[])}
    found=[line_map[r] for r in refs if r in line_map]
    scores=[];corroborated=[]
    compact=lambda text:re.sub(r'\s+','',text)
    for line in found:
        score=line.get('score',line.get('confidence',0));parent=line_map.get(line.get('parent_line_id'))
        # A detail token can be corroborated by the already captured coarse
        # row. Both are retained observations; no extra OCR or truth claim.
        if parent is not None and score>=.90:
            parent_score=parent.get('score',parent.get('confidence',0))
            if parent_score>=.97 and compact(line['text']) in compact(parent['text']):
                corroborated.append({'detail':line['line_id'],'parent':parent['line_id'],'detail_score':score,'parent_score':parent_score})
                score=max(score,parent_score)
        scores.append(score)
    issues=set(candidate['issues'])-{'IMAGE_TRANSCRIPTION_AND_FIGURES_REVIEW'}
    if not refs or len(found)!=len(refs) or not scores or min(scores)<.97:issues.add('LOW_OR_MISSING_OCR_CONFIDENCE')
    if MATH_LAYOUT.search('\n'.join(candidate['zones'].values())):issues.add('FORMULA_LAYOUT_REVIEW')
    if any(f['role']=='figure_caption' for f in question['fragments']):issues.add('FIGURE_EXTENT_UNVERIFIED')
    from .review_features import figure_requirements
    issues.update(row['code'] for row in figure_requirements(candidate,pages,graph,evidence))
    # Pixel coverage is measured inside each observed source span. Existing
    # figure/cross-column/section issues remain independent gates outside it.
    from PIL import Image
    import numpy as np
    source_pages={p['asset_id']:p for p in pages};coverage=[]
    for frame in candidate['frames']:
        page=source_pages[frame['asset_id']]
        if page['kind']!='image':continue
        with Image.open(page['raw_path']) as image:ink=np.asarray(image.convert('L'))<160
        x1,y1,x2,y2=frame['bbox'];region=ink[y1:y2,x1:x2];mask=np.zeros(region.shape,dtype=bool)
        related=[f for f in fragments if f['fragment_id'] in frame['source_fragment_ids']]
        for f in related:
            b=f['bbox'];left=max(x1,int(b[0])-2);top=max(y1,int(b[1])-2)
            right=min(x2,int(b[2]+.999)+2);bottom=min(y2,int(b[3]+.999)+2)
            mask[top-y1:bottom-y1,left-x1:right-x1]=True
        total=int(region.sum());unexplained=int((region & ~mask).sum())
        ratio=unexplained/max(1,total)
        coverage.append({'asset_id':page['asset_id'],'bbox':frame['bbox'],'ink_pixels':total,'unexplained_ink':unexplained,'ratio':ratio})
        if not total or ratio>.01:issues.add('UNEXPLAINED_SOURCE_INK')
    candidate['quality']={'schema':'CustomerOrdinaryImageQuality/v1','minimum_score':min(scores) if scores else None,
        'minimum_required_score':.97,'maximum_unexplained_ink_ratio':.01,'coverage':coverage,
        'evidence_hash':evidence['content_hash'],'machine_checked':True,'human_transcription_verified':False,
        'existing_coarse_detail_corroboration':corroborated,
        'exceptions':sorted(issues)}
    candidate['issues']=sorted(issues)
    candidate['content_status']='NEEDS_REVIEW' if issues else 'READY_SOURCE_CHECKED'
    candidate['quality']['content_hash']=candidate['content_hash']
