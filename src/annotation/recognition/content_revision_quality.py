"""Independent source-span, materialized-content and current-rule revision audit.

No content revision producer, plan builder, parser or model is executed here.
Explicit draft edits are not claimed to be literal OCR or verified mathematics.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import re

from .baseline import code_digest,digest,valid_bbox
from .question_quality import audit_questions
from .offline import scope_key,scalar_issues
from .policy import classify

SCHEMA='b-content-revision-check-trial/0.1'
_FLAGS=dict(decision='HOLD',complete=False,transcription_verified=False,business_acceptance=False,platform_actions=[],new_model_calls=0)
_HEADER={'schema_version','kind','artifact_id','revision','book_id','scope_id','input_refs','producer','payload','content_hash'}
_PLAN_HEADER={'schema_version','kind','artifact_id','revision','book_id','scope_id','payload','content_hash'}


def ref(v):return {k:v.get(k)if isinstance(v,dict)else None for k in ('artifact_id','revision','content_hash')}
def docref(v):return dict(artifact_id=v['artifact_id'],content_hash=digest(v))
def _equal(a,b):return digest(a)==digest(b)
def _sha(text):return hashlib.sha256(text.encode('utf8')).hexdigest()


def _artifact(v,schema,kind):
    if (not isinstance(v,dict)or v.get('schema_version')not in schema or v.get('kind')!=kind
            or type(v.get('revision'))is not int or v['revision']<1 or not isinstance(v.get('payload'),dict)
            or any(not isinstance(v.get(k),str)or not v[k]for k in ('artifact_id','book_id','scope_id'))
            or v.get('content_hash')!=digest(v['payload'])):raise ValueError('revision input artifact schema or identity invalid')


def _inputs(e,g,c):
    _artifact(e,{'b-evidence-trial/0.2','b-evidence-trial/0.3'},'EvidenceBundleTrial')
    _artifact(g,{'b-graph-trial/0.5'},'QuestionGraphTrial');_artifact(c,{'b-check-trial/0.5'},'CheckReportTrial')
    if (set(g)!=_HEADER or set(c)!=_HEADER or any(v[k]!=e[k]for v in (g,c)for k in ('book_id','scope_id'))
            or not any(_equal(ref(e),r)for r in g['input_refs'])or not _equal(c['payload'].get('evidence_ref'),ref(e))or not _equal(c['payload'].get('graph_ref'),ref(g))
            or not _equal(c['input_refs'][:2],[ref(e),ref(g)])or 'content_revision'in g['payload']):raise ValueError('revision must bind the current unedited G05 and Check05')
    if any(not _equal({k:v['payload'].get(k)for k in _FLAGS},_FLAGS)for v in (c,)):raise ValueError('revision base check claims acceptance')
    rawbase=g['payload']['inline_content']['base_graph_archive']
    _artifact(rawbase,{'b-graph-trial/0.2','b-graph-trial/0.3','b-graph-trial/0.4'},'QuestionGraphTrial')
    if not _equal({k:v for k,v in g['payload'].items()if k!='inline_content'},rawbase['payload']):raise ValueError('G05 raw core differs from its archived inline source')
    if not _equal({k:g['payload']['inline_content'].get(k)for k in _FLAGS},_FLAGS):raise ValueError('inline evidence claims selection or acceptance')


def _source(e,g):
    units={};raw={};pages={}
    for p in e['payload']['pages']:
        if p['asset_id']in pages:raise ValueError('duplicate source asset')
        pages[p['asset_id']]=p
        for line in p['ocr_lines']+p.get('answer_detail_lines',[]):
            if line['line_id']in units:raise ValueError('duplicate source element identity')
            units[line['line_id']]=(p,line)
        raw.update({r['line_id']:r for r in p['ocr_lines']})
    answers={};fragments={}
    for a in g['payload']['answers']:
        if a['answer_id']in answers:raise ValueError('duplicate answer identity')
        answers[a['answer_id']]=a
        for f in a['fragments']:
            if f['fragment_id']in fragments:raise ValueError('duplicate source fragment identity')
            fragments[f['fragment_id']]=(a,f)
    return pages,units,raw,answers,fragments


def _target_source(e,g,source,answer_id,fragment_id):
    pages,units,raw,answers,fragments=source
    a,f=fragments[fragment_id]
    if (a['answer_id']!=answer_id or f.get('role')not in {'answer','explanation'}or f.get('content_type')!='text'
            or f.get('structural_marker')is True or f.get('represented_by_image_region')is not None or f.get('render_as_separate_region')is False):raise ValueError('revision target has no visible current answer/explanation owner')
    if f['fragment_id']not in {v['fragment_id']for v in _visible(a)[0]}:raise ValueError('revision target is not rendered as visible text')
    refs=f.get('evidence_refs')
    if not isinstance(refs,list)or len(refs)!=1 or refs[0]not in units:raise ValueError('revision target needs one canonical OCR source')
    page,line=units[refs[0]];parent=line.get('parent_line_id',line['line_id']);span=f.get('text_span')
    if (parent not in raw or units[parent][0]['asset_id']!=page['asset_id']or f.get('parent_line_id')!=parent or page['page_role']!='answer'or a['book_id']!=e['book_id']
            or f['asset_id']!=page['asset_id']or line.get('location',{}).get('section_path')!=a['section_path']
            or f.get('section_path')!=a['section_path']or raw[parent].get('location',{}).get('section_path')!=a['section_path']
            or not isinstance(line.get('bbox'),list)or not valid_bbox(line['bbox'],page['source']['width'],page['source']['height'])
            or any(type(raw[parent].get('location',{}).get(k))is not int or raw[parent]['location'][k]<0 or not _equal(f.get(k),raw[parent]['location'][k])for k in ('column','window_index'))
            or not isinstance(span,list)or len(span)!=2 or any(type(n)is not int for n in span)or not 0<=span[0]<span[1]<=len(line['text'])
            or f.get('raw_text')!=line['text']or f['text']!=line['text'][span[0]:span[1]]or not _equal(f['bbox'],line['bbox'])
            or f.get('source_sha256',page['source']['sha256'])!=page['source']['sha256']):raise ValueError('revision target differs from its literal source span/parent/geometry')
    rows=[r for r in g['payload']['answer_coverage']if r['asset_id']==page['asset_id']and r['line_id']==parent]
    allocation=dict(answer_id=answer_id,fragment_id=fragment_id,evidence_refs=refs,text_span=span)
    if (len(rows)!=1 or rows[0]['status']!='CONSUMED'or sum(_equal(v,allocation)for v in rows[0]['allocations'])!=1
            or answer_id not in rows[0]['answer_ids']or fragment_id not in rows[0]['fragment_ids']):raise ValueError('revision target is not exactly allocated to the original owner')
    return a,f,page,line,parent


def _visible(answer):
    fragments={f['fragment_id']:f for f in answer['fragments']};visible=[];blocks=[]
    if 'render_regions'in answer:
        for r in answer['render_regions']:
            if r.get('content_type')=='image':blocks.append(('image',r['region_id']));continue
            if r.get('content_type')!='text'or not r.get('source_fragment_ids'):raise ValueError('unsupported current text rendering ownership')
            fs=[fragments[fid]for fid in r['source_fragment_ids']]
            if len({f['role']for f in fs})!=1 or any(f['role']!=r['role']for f in fs):raise ValueError('mixed-role current text rendering')
            for f in fs:
                if f.get('structural_marker'):continue
                if f.get('represented_by_image_region')is not None or f.get('render_as_separate_region')is False:raise ValueError('diagnostic source fragment appears as body')
                if f['asset_id']!=r['asset_id']:raise ValueError('cross-page current text rendering')
                visible.append(f)
            blocks.append(('text',tuple(f['fragment_id']for f in fs if not f.get('structural_marker'))))
    else:
        for f in answer['fragments']:
            if f.get('structural_marker')or f.get('represented_by_image_region')is not None or f.get('render_as_separate_region')is False:continue
            if f.get('content_type')!='text':blocks.append(('image',f['fragment_id']));continue
            visible.append(f);blocks.append(('text',(f['fragment_id'],)))
    if len({f['fragment_id']for f in visible})!=len(visible):raise ValueError('visible source fragment rendered more than once')
    return visible,blocks


def _select(g,op,f,parent):
    content=g['payload']['inline_content'];candidates=[c for c in content['candidates']if c['candidate_id']==op['candidate_id']]
    calls=[c for c in content['calls']if c['plan']['call_id']==op['call_id']];units=[u for u in content['units']if u['unit_id']==op['unit_id']]
    if len(candidates)!=1 or len(calls)!=1 or len(units)!=1:raise ValueError('selected candidate/call/unit is not unique in current inline scope')
    candidate,call,unit=candidates[0],calls[0],units[0]
    _artifact(call['observation'],{'b-inline-formula-call-trial/0.1'},'InlineFormulaCallTrial')
    raw=candidate['raw_latex']
    if (candidate['call_id']!=op['call_id']or candidate['state']!='DONE'or call['state']!='DONE'or not isinstance(raw,str)or not raw
            or raw!=call['observation']['payload']['raw_latex']or '\r'in raw or '\0'in raw
            or not _equal(candidate.get('observation_ref'),ref(call['observation']))or candidate.get('parse_result',{}).get('raw_latex')!=raw
            or type(candidate['parse_result'].get('supported'))is not bool or not _equal(candidate['unit_bindings'],call['plan']['unit_bindings'])
            or not _equal(call['observation']['payload'].get('plan'),call['plan'])
            or call['observation']['payload'].get('recognition_error')is not None
            or any(b['line_id']!=parent for b in candidate['unit_bindings'])
            or not any(b['unit_id']==op['unit_id']and b['line_id']==parent for b in candidate['unit_bindings'])
            or not any(b['unit_id']==op['unit_id']and b['line_id']==parent for b in call['plan']['unit_bindings'])
            or unit['asset_id']!=f['asset_id']or unit['line_id']!=parent):raise ValueError('selected model string is not the verbatim DONE source-bound candidate')
    rows=[r for r in content['bindings']if r['line_id']==parent]
    if (len(rows)!=1 or rows[0]['unassigned']is not False or not any(b['answer_id']==op['target']['answer_id']and b['fragment_id']==f['fragment_id']
            and b['role']==f['role']and _equal(b['text_span'],f['text_span'])for b in rows[0]['fragments'])
            or any(b['answer_id']!=op['target']['answer_id']or b['role']!=f['role']for b in rows[0]['fragments'])):raise ValueError('selected unit does not bind the current original owner')
    return raw,'latex',candidate


def _join(e,g,source,op):
    proposals=[p for p in g['payload']['inline_content']['continuity']['payload']['proposals']if p['proposal_id']==op['proposal_id']]
    if len(proposals)!=1:raise ValueError('join needs one current proved literal wrap')
    p=proposals[0]
    if len(p['bindings'])!=2 or len(p['source_spans'])!=2 or any(len(b['fragments'])!=1 for b in p['bindings']):raise ValueError('join needs exactly two single-fragment bindings')
    pairs=[]
    for b,span in zip(p['bindings'],p['source_spans']):
        bf=b['fragments'][0];a,f,page,line,parent=_target_source(e,g,source,b['answer_id'],bf['fragment_id']);s=span['text_span']
        if (not isinstance(s,list)or len(s)!=2 or any(type(n)is not int for n in s)or b['role']!=f['role']or not _equal(bf['text_span'],f['text_span'])or not _equal(bf['overlap_span'],s)or span['asset_id']!=f['asset_id']
                or span['line_id']!=parent or line['line_id']!=parent or span['text']!=line['text'][s[0]:s[1]]
                or not f['text_span'][0]<=s[0]<s[1]<=f['text_span'][1]):raise ValueError('join span differs from current canonical literal allocation')
        pairs.append((a,f,page,line,parent))
    (a,left,_,ll,lp),(ra,right,_,rl,rp)=pairs
    if (a['answer_id']!=ra['answer_id']or left['role']!=right['role']or left['asset_id']!=right['asset_id']
            or p['source_spans'][0]['text_span'][1]!=left['text_span'][1]or p['source_spans'][1]['text_span'][0]!=right['text_span'][0]
            or p['left_line_id']!=lp or p['right_line_id']!=rp or p['joined_raw_text']!=''.join(s['text']for s in p['source_spans'])):raise ValueError('join crosses owner/role/source or is not at the literal fragment ends')
    _,blocks=_visible(a);boundary=[('text',(left['fragment_id'],)),('text',(right['fragment_id'],))]
    if not any(blocks[i:i+2]==boundary for i in range(len(blocks)-1)):raise ValueError('join crosses an image/role or nonadjacent visible source')
    # A cached proposal is not a substitute for its actual source ordering.
    def location(row):
        v=row.get('location',{});return v.get('column'),v.get('window_index'),v.get('section_path')
    def order(row):return ((row['bbox'][1]+row['bbox'][3])/2,row['bbox'][0],row['line_id'])
    loc=location(ll);other=location(rl);lbox,rbox=ll['bbox'],rl['bbox']
    if (any(type(v[0])is not int or v[0]<0 or type(v[1])is not int or v[1]<0 or not isinstance(v[2],list)or not v[2]
            or any(not isinstance(s,str)or not s for s in v[2])for v in (loc,other))or loc!=other or order(ll)>=order(rl)
            or any(location(row)==loc and order(ll)<order(row)<order(rl)for row in source[0][left['asset_id']]['ocr_lines'])
            or not 0<=rbox[1]-lbox[3]<=2.5*max(lbox[3]-lbox[1],rbox[3]-rbox[1])
            or max(0,min(lbox[2],rbox[2])-max(lbox[0],rbox[0]))<.5*min(lbox[2]-lbox[0],rbox[2]-rbox[0])):raise ValueError('join lacks current visible same-location source adjacency')
    from .inline_stage_quality import _MATH,_OPEN,_RELATIONS
    lm=re.search('['+_MATH+']+$',ll['text']);rm=re.match('['+_MATH+']+',rl['text'])
    if (not lm or not rm or list(lm.span())!=p['source_spans'][0]['text_span']or list(rm.span())!=p['source_spans'][1]['text_span']
            or re.match(r'^\s*(?:\d+\s*[.、](?!\d)|[A-G]\s*[.、]|[（(]\d+[）)]|[①②③④⑤⑥⑦⑧⑨⑩])',rl['text'])):raise ValueError('join is not the actual non-question mathematical suffix/prefix')
    kind=('OPEN_EQUATION_LINE_WRAP'if lm.group()[-1]in _OPEN and any(c.isalnum()for c in lm.group())and any(c.isalnum()for c in rm.group())
        else'CHAINED_RELATION_LINE_WRAP'if rm.group()[0]in _RELATIONS and any(c in _RELATIONS for c in lm.group())and any(c.isalnum()for c in rm.group())else None)
    if p['kind']!=kind or kind is None:raise ValueError('join has no explicit literal mathematics wrap marker')
    return a,left,right,p


def _plan(plan,e,g,c,source,depth=0,*,current=True):
    if depth>=32:raise ValueError('revision lineage exceeds 32 versions')
    _artifact(plan,{'b-content-revision-plan-trial/0.1'},'ContentRevisionPlanTrial');p=plan['payload']
    keys=set(_FLAGS)|{'evidence_ref','graph_ref','base_check_ref','previous_plan_archive','author','operations'}
    body={k:v for k,v in plan.items()if k not in {'artifact_id','content_hash'}}
    author=p.get('author',{})
    def valid_ref(r):return isinstance(r,dict)and set(r)=={'artifact_id','revision','content_hash'}and isinstance(r['artifact_id'],str)and bool(r['artifact_id'].strip())and type(r['revision'])is int and r['revision']>=1 and isinstance(r['content_hash'],str)and re.fullmatch('[0-9a-f]{64}',r['content_hash'])is not None
    if (set(plan)!=_PLAN_HEADER or set(p)!=keys or any(plan[k]!=e[k]for k in ('book_id','scope_id'))
            or plan['artifact_id']!='content-revision-plan-'+digest(body)[:24]or not _equal({k:p.get(k)for k in _FLAGS},_FLAGS)
            or p['evidence_ref']!=ref(e)or p['graph_ref']!=ref(g)or current and p['base_check_ref']!=ref(c)
            or not all(valid_ref(p[k])for k in ('evidence_ref','graph_ref','base_check_ref'))
            or set(author)!={'kind','id','note'}or author['kind']not in {'MODEL_DRAFT','HUMAN_DRAFT','SYNTHETIC_TEST'}
            or any(not isinstance(author[k],str)or not author[k]for k in ('id','note'))):raise ValueError('revision plan exact fields, external refs, identity or draft author invalid')
    previous=p['previous_plan_archive']
    if plan['revision']==1:
        if previous is not None:raise ValueError('first plan must not claim a prior revision')
    elif not isinstance(previous,dict)or previous.get('revision')!=plan['revision']-1:raise ValueError('revision lineage is not sequential')
    else:_plan(previous,e,g,c,source,depth+1,current=False)
    edits={};joins=[];seen=set();bindings=[]
    if not isinstance(p['operations'],list):raise ValueError('operations must be a complete ordered list')
    for op in p['operations']:
        if (not isinstance(op,dict)or not isinstance(op.get('operation_id'),str)or not op['operation_id']or op['operation_id']in seen
                or not isinstance(op.get('reason'),str)or not op['reason']):raise ValueError('invalid/duplicate revision operation')
        seen.add(op['operation_id']);kind=op.get('kind')
        common={'operation_id','kind','reason'}
        if kind=='JOIN_RAW_WRAP':
            if set(op)!=common|{'proposal_id'}:raise ValueError('unknown join fields')
            a,left,right,proposal=_join(e,g,source,op);boundary=(left['fragment_id'],right['fragment_id'])
            if boundary in [j[1]for j in joins]:raise ValueError('duplicate join boundary')
            joins.append((op,boundary,a,proposal));continue
        required=common|{'target','replacement','format'}if kind=='EDIT_TEXT'else common|{'target','candidate_id','call_id','unit_id'}if kind=='SELECT_INLINE'else None
        if required is None or set(op)!=required:raise ValueError('unknown edit/selection operation or fields')
        t=op['target']
        if set(t)!={'answer_id','fragment_id','role','fragment_span','expected_text'}:raise ValueError('unknown target coordinate space or fields')
        a,f,page,line,parent=_target_source(e,g,source,t['answer_id'],t['fragment_id']);s=t['fragment_span']
        if (t['role']!=f['role']or not isinstance(s,list)or len(s)!=2 or any(type(n)is not int for n in s)
                or not 0<=s[0]<s[1]<=len(f['text'])or t['expected_text']!=f['text'][s[0]:s[1]]):raise ValueError('revision interval is not relative to the original fragment.text')
        if kind=='EDIT_TEXT':
            text,fmt=op['replacement'],op['format'];candidate=None
            if not isinstance(text,str)or not text or '\r'in text or '\0'in text or fmt not in {'plain','latex'}:raise ValueError('invalid verbatim explicit replacement')
        else:text,fmt,candidate=_select(g,op,f,parent)
        entries=edits.setdefault(f['fragment_id'],[])
        if any(max(s[0],x[0]['target']['fragment_span'][0])<min(s[1],x[0]['target']['fragment_span'][1])for x in entries):raise ValueError('overlapping content revision intervals')
        entries.append((op,text,fmt,candidate))
    return edits,joins,bindings


def _source_projection(payload):
    removed={'candidate_answer_ids','selected_answer_id','type_candidate'}
    return dict(questions=[{k:v for k,v in q.items()if k not in removed}for q in payload['questions']],
        answers=[dict(answer_id=a['answer_id'],fragments=a['fragments'],source_line_ids=a['source_line_ids'],evidence_refs=a['evidence_refs'],
            images=[r for r in a.get('render_regions',[])if r.get('content_type')=='image'])for a in payload['answers']],
        answer_coverage=payload['answer_coverage'],inline_content=payload['inline_content'])


def _projection(e,g,c,plan):
    """Build expected bytes directly from external plan and unchanged source."""
    _inputs(e,g,c);source=_source(e,g);edits,joins,_=_plan(plan,e,g,c,source)
    affected=set(source[4][fid][0]['answer_id']for fid in edits)|{j[2]['answer_id']for j in joins}
    affected_ids=[a['answer_id']for a in g['payload']['answers']if a['answer_id']in affected]
    op_bindings={}
    def bound_span(f,span):
        _,_,_,_,parent=_target_source(e,g,source,source[4][f['fragment_id']][0]['answer_id'],f['fragment_id'])
        return dict(fragment_id=f['fragment_id'],fragment_span=span,source_element_ref=f['evidence_refs'][0],
            source_element_span=[f['text_span'][0]+span[0],f['text_span'][0]+span[1]],parent_line_id=parent)
    for fid,values in edits.items():
        a,f=source[4][fid]
        for op,text,fmt,candidate in values:
            op_bindings[op['operation_id']]=dict(operation_id=op['operation_id'],kind=op['kind'],answer_id=a['answer_id'],role=f['role'],fragment_ids=[fid],
                source_spans=[bound_span(f,op['target']['fragment_span'])],replacement=text,format=fmt,candidate_id=op.get('candidate_id'),call_id=op.get('call_id'),unit_id=op.get('unit_id'),proposal_id=None)
    joins_by_boundary={boundary:op for op,boundary,_,_ in joins}
    for op,boundary,a,p in joins:
        fs=[source[4][fid][1]for fid in boundary]
        spans=[bound_span(f,[s['text_span'][0]-f['text_span'][0],s['text_span'][1]-f['text_span'][0]])for f,s in zip(fs,p['source_spans'])]
        op_bindings[op['operation_id']]=dict(operation_id=op['operation_id'],kind=op['kind'],answer_id=a['answer_id'],role=fs[0]['role'],fragment_ids=list(boundary),
            source_spans=spans,replacement=None,format=None,candidate_id=None,call_id=None,unit_id=None,proposal_id=p['proposal_id'])
    payload=copy.deepcopy(g['payload'])
    for answer in payload['answers']:
        if answer['answer_id']not in affected:continue
        visible,_=_visible(answer);current=[]
        for f in visible:
            _target_source(e,g,source,answer['answer_id'],f['fragment_id'])
            pieces=[];cursor=0;out=0
            def piece(kind,start,end,text,operation_id=None,fmt='plain'):
                nonlocal out
                pieces.append(dict(kind=kind,source_fragment_span=[start,end],output_span=[out,out+len(text)],text=text,operation_id=operation_id,format=fmt));out+=len(text)
            for op,text,fmt,_ in sorted(edits.get(f['fragment_id'],[]),key=lambda v:v[0]['target']['fragment_span']):
                lo,hi=op['target']['fragment_span']
                if cursor<lo:piece('SOURCE',cursor,lo,f['text'][cursor:lo])
                piece('REVISION',lo,hi,text,op['operation_id'],fmt);cursor=hi
            if cursor<len(f['text']):piece('SOURCE',cursor,len(f['text']),f['text'][cursor:])
            cf=dict(source_fragment_id=f['fragment_id'],role=f['role'],asset_id=f['asset_id'],source_element_ref=f['evidence_refs'][0],
                source_text_span=f['text_span'],source_fragment_text_sha256=_sha(f['text']),text=''.join(p['text']for p in pieces),pieces=pieces,
                verification_status='UNVERIFIED',complete=False,transcription_verified=False,business_acceptance=False)
            cf['content_fragment_id']='content-fragment-'+digest([ref(e),ref(g),ref(plan),cf])[:24];current.append(cf)
        by_source={cf['source_fragment_id']:cf for cf in current};separators=[];aggregates={}
        for role in ('answer','explanation'):
            fs=[cf for cf in current if cf['role']==role];parts=[]
            for i,cf in enumerate(fs):
                if i:
                    left=fs[i-1];op=joins_by_boundary.get((left['source_fragment_id'],cf['source_fragment_id']));separator=''if op else'\n'
                    separators.append(dict(role=role,left_content_fragment_id=left['content_fragment_id'],right_content_fragment_id=cf['content_fragment_id'],separator=separator,join_operation_id=op['operation_id']if op else None));parts.append(separator)
                parts.append(cf['text'])
            aggregates[role]=''.join(parts)
        answer.update(text=aggregates['answer'],explanation_text=aggregates['explanation'],explanation_present=any(cf['role']=='explanation'for cf in current),
            content_fragments=current,content_projection=dict(schema_version='b-content-projection-trial/0.1',source_graph_ref=ref(g),plan_ref=ref(plan),
                source_fragment_order=[f['fragment_id']for f in visible],separators=separators,verification_status='UNVERIFIED'),
            complete=False,transcription_verified=False,verification_status='UNVERIFIED')
        if 'render_regions'in answer:
            original=copy.deepcopy(answer['render_regions']);regions=copy.deepcopy(original)
            for r in regions:
                if r.get('content_type')=='text'and all(fid in by_source for fid in r['source_fragment_ids']):r['text']='\n'.join(by_source[fid]['text']for fid in r['source_fragment_ids'])
            answer['render_regions']=regions
            if _equal(answer.get('regions'),original):answer['regions']=copy.deepcopy(regions)
    affected_questions=[];derivation=[]
    for q,old in zip(payload['questions'],g['payload']['questions']):
        key=scope_key(q['book_id'],q['section_path'],q['printed_number']);matches=[a for a in payload['answers']if scope_key(a['book_id'],a['section_path'],a['printed_number'])==key]
        q['candidate_answer_ids']=[a['answer_id']for a in matches];q['selected_answer_id']=matches[0]['answer_id']if len(matches)==1 else None
        q['type_candidate']=classify(q['text'],[f['option_label']for f in q['fragments']if f.get('option_start')],matches[0]['text']if len(matches)==1 else None)
        item=dict(question_id=q['question_id'],**{k:q[k]for k in ('candidate_answer_ids','selected_answer_id','type_candidate')});derivation.append(item)
        dependency=set(q['candidate_answer_ids']+old['candidate_answer_ids']+[q['selected_answer_id'],old['selected_answer_id']])&affected
        if dependency or any(not _equal(q[k],old[k])for k in ('candidate_answer_ids','selected_answer_id','type_candidate')):affected_questions.append(q['question_id'])
    payload['unmatched_answer_ids']=[a['answer_id']for a in payload['answers']if not any(a['answer_id']in q['candidate_answer_ids']for q in payload['questions'])]
    before,after=digest(_source_projection(g['payload'])),digest(_source_projection(payload))
    payload.update(_FLAGS)
    metadata=dict(schema_version='b-content-revision-state-trial/0.1',evidence_ref=ref(e),base_graph_ref=ref(g),base_check_ref=ref(c),plan_ref=ref(plan),
        base_graph_archive=g,base_check_archive=c,plan_archive=plan,operation_bindings=[op_bindings[op['operation_id']]for op in plan['payload']['operations']],
        affected_answer_ids=affected_ids,affected_question_ids=affected_questions,matching_derivation=dict(rule='book+section_path+printed_number; unique candidate only',questions=derivation,
            unmatched_answer_ids=payload['unmatched_answer_ids'],policy_code_sha256=code_digest(Path(__file__).with_name('policy.py'))),
        source_layer_proof=dict(base_sha256=before,derived_sha256=after,equal=before==after),**_FLAGS)
    payload['content_revision']=metadata
    return payload


def _producer(operation):
    return dict(module='annotation.recognition.content_revision',version='0.1.0',operation=operation,
        code_sha256=code_digest(Path(__file__).with_name('content_revision.py')),
        dependency_code_sha256={n:code_digest(Path(__file__).with_name(n+'.py'))for n in ('baseline','policy','question_quality','offline')},
        identity_policy='CURRENT_REFS_WITH_EXECUTION_TIME_IN_JOURNAL/0.1')


def _header(value,schema,kind,prefix,e,inputs,operation,revision=1):
    body=dict(schema_version=schema,kind=kind,revision=revision,book_id=e['book_id'],scope_id=e['scope_id'],input_refs=inputs,producer=_producer(operation),payload=value['payload'])
    expected={**body,'artifact_id':prefix+'-'+digest(body)[:24],'content_hash':digest(value['payload'])}
    if not _equal(value,expected):raise ValueError('content revision output header/producer/identity differs')


def _application(e,g,c,plan,application,emit):
    expected=_projection(e,g,c,plan);inputs=[ref(v)for v in (e,g,c,plan)]
    _header(application,'b-content-revision-application-trial/0.1','ContentRevisionApplicationTrial','content-revision-application',e,inputs,'apply')
    derived=application['payload']['graph']
    _header(derived,'b-graph-trial/0.6','QuestionGraphTrial','content-graph',e,inputs,'graph',g['revision']+1)
    if not _equal(derived['payload'],expected):emit('CONTENT_REVISION_GRAPH_PROJECTION_MISMATCH')
    payload=dict(evidence_ref=ref(e),base_graph_ref=ref(g),base_check_ref=ref(c),plan_ref=ref(plan),graph=derived,**_FLAGS)
    if not _equal(application['payload'],payload):emit('CONTENT_REVISION_APPLICATION_BINDING_MISMATCH')
    return expected,derived


def _safe(inputs,operation):
    issues=[];summary={}
    def emit(code,detail=None):
        item=dict(code=code,severity='ERROR',detail=detail)
        if item not in issues:issues.append(item)
    try:summary=operation(emit)
    except (ValueError,TypeError,KeyError,IndexError,AttributeError,OSError,OverflowError,RecursionError,StopIteration)as exc:
        emit('CONTENT_REVISION_DATA_INVALID',type(exc).__name__+': '+str(exc))
    payload=dict(accepted=not issues,issues=issues,summary=summary,**_FLAGS)
    producer=dict(module=__name__,version='0.1.0',code_sha256=code_digest(Path(__file__)))
    return dict(schema_version=SCHEMA,kind='ContentRevisionCheckTrial',artifact_id='content-revision-check-'+digest([[ref(v)for v in inputs],producer,payload])[:24],
        revision=1,book_id=inputs[0].get('book_id')if isinstance(inputs[0],dict)else None,scope_id=inputs[0].get('scope_id')if isinstance(inputs[0],dict)else None,
        input_refs=[ref(v)for v in inputs],producer=producer,content_hash=digest(payload),payload=payload)


def audit_content_application(evidence,base_graph,base_check,plan,application):
    def inspect(emit):
        expected,derived=_application(evidence,base_graph,base_check,plan,application,emit)
        m=expected['content_revision'];return dict(operations=len(plan['payload']['operations']),affected_answers=len(m['affected_answer_ids']),affected_questions=len(m['affected_question_ids']),source_layer_unchanged=m['source_layer_proof']['equal'])
    return _safe([evidence,base_graph,base_check,plan,application],inspect)


def _review(e,g,c,review):
    core=c['payload']['base_check_archive'];rawgraph=g['payload']['inline_content']['base_graph_archive']
    _artifact(core,{'b-check-trial/0.2','b-check-trial/0.3','b-check-trial/0.4'},'CheckReportTrial')
    if review.get('schema_version')!='b-review-trial/0.1'or review.get('book_id')!=e['book_id']:raise ValueError('revision review schema/book differs')
    if core['schema_version']=='b-check-trial/0.4':
        selected=core['payload']['derived_review']
        if (not _equal(core['payload'].get('input_review_ref'),docref(review))or not _equal(core['payload'].get('derived_review_ref'),docref(selected))
                or not _equal(core['payload'].get('evidence_ref'),ref(e))or not _equal(core['payload'].get('graph_ref'),ref(rawgraph))
                or not any(_equal(ref(e),r)for r in core['input_refs'])or not any(_equal(ref(rawgraph),r)for r in core['input_refs'])):raise ValueError('archived continuation review is not current')
        selection='CHECK04_ARCHIVED_DERIVED_REVIEW'
    else:
        selected=review;selection='CHECK02_03_INPUT_REVIEW'
        if not _equal(core['input_refs'],[ref(e),ref(rawgraph),docref(review)]):raise ValueError('archived core review references differ')
    if selected.get('book_id')!=e['book_id']or selected.get('scope_id')!=e['scope_id']:raise ValueError('selected current review scope differs')
    return selected,dict(input_review_ref=docref(review),selected_review_ref=docref(selected),base_core_check_ref=ref(core),selection=selection)


def _finding_key(item):
    return digest([item['code'],item['scope_id'],item['evidence_refs'],item['severity'],item.get('detail')])


def _quality_payload(e,g,c,plan,application,review,derived,expected_graph):
    selected,basis=_review(e,g,c,review)
    prior,_=audit_questions(e,g,selected,scope_key=scope_key,scalar_issues=scalar_issues)
    fresh,coverage=audit_questions(e,derived,selected,scope_key=scope_key,scalar_issues=scalar_issues)
    page_ids={p['asset_id']for p in e['payload']['pages']}
    def issue(code,scope,refs=(),detail=None,severity='REVIEW'):
        body=dict(code=code,scope_type='question'if scope.startswith('q-')else'answer'if scope.startswith('a-')else'asset'if scope in page_ids else'scope',
            scope_id=scope,evidence_refs=list(refs),severity=severity,detail=detail,blocks=['PRE_APPLY'],suggested_strategy='REVIEW_OFFLINE',evidence_ref=ref(e),graph_ref=ref(derived))
        return {**body,'issue_id':'issue-'+digest(body)[:24]}
    current=[issue(f['code'],f['scope_id'],f['evidence_refs'],f.get('detail'),f['severity'])for f in fresh]
    old_keys={_finding_key(f)for f in prior};carried=[];dispositions=[]
    for old in c['payload']['issues']:
        if _finding_key(old)in old_keys:
            dispositions.append(dict(prior_issue=old,origin_check_ref=ref(c),status='FRESH_QUESTION_RULES_RECHECKED',
                current_finding_issue_ids=[i['issue_id']for i in current if i['code']==old['code']and i['scope_id']==old['scope_id']]))
        else:carried.append({**copy.deepcopy(old),'origin_check_ref':ref(c),'carry_basis':dict(source_layer_unchanged=True,remaining_risk_unverified=True)})
    metadata=expected_graph['content_revision'];operations=plan['payload']['operations'];issues=carried+current
    issues.append(issue('CONTENT_REVISION_DRAFT_UNVERIFIED',e['scope_id'],detail=dict(operation_ids=[op['operation_id']for op in operations],affected_answer_ids=metadata['affected_answer_ids'],human_verified=False)))
    candidates={v['candidate_id']:v for v in g['payload']['inline_content']['candidates']}
    diagnostics=g['payload']['inline_content']['continuity']['payload']['diagnostics']
    bindings={v['operation_id']:v for v in metadata['operation_bindings']}
    for op in operations:
        b=bindings[op['operation_id']];refs=list(dict.fromkeys(s['source_element_ref']for s in b['source_spans']))
        if op['kind']=='EDIT_TEXT':
            issues.append(issue('CONTENT_EDIT_DRAFT_UNVERIFIED',b['answer_id'],refs,dict(operation_id=op['operation_id'],author=plan['payload']['author'],format=op['format'],source_span=op['target'],replacement_sha256=_sha(op['replacement']))))
        elif op['kind']=='JOIN_RAW_WRAP':
            issues.append(issue('CONTENT_RAW_WRAP_DRAFT_UNVERIFIED',b['answer_id'],refs,dict(operation_id=op['operation_id'],proposal_id=op['proposal_id'],source_spans=b['source_spans'])))
        else:
            candidate=candidates[op['candidate_id']]
            issues.append(issue('CONTENT_INLINE_SELECTION_DRAFT_UNVERIFIED',b['answer_id'],refs,dict(operation_id=op['operation_id'],candidate_id=op['candidate_id'],unit_id=op['unit_id'],call_id=op['call_id'],
                raw_latex=candidate['raw_latex'],parse_supported=candidate['parse_result']['supported'],transcription_verified=False)))
            if not candidate['parse_result']['supported']:
                issues.append(issue('CONTENT_SELECTED_FORMULA_SYNTAX_UNSUPPORTED',b['answer_id'],refs,dict(operation_id=op['operation_id'],candidate_id=op['candidate_id'],parse_result=candidate['parse_result'])))
            matching=[d for d in diagnostics if d['candidate_id']==op['candidate_id']and d['call_id']==op['call_id']]
            if matching:issues.append(issue('CONTENT_SELECTED_FORMULA_CLOSURE_CONFLICT',b['answer_id'],refs,dict(operation_id=op['operation_id'],diagnostics=matching)))
    summary=dict(questions=len(derived['payload']['questions']),answers=len(derived['payload']['answers']),unique_candidate_links=sum(q['selected_answer_id']is not None for q in derived['payload']['questions']),
        issues=len(issues),affected_answers=len(metadata['affected_answer_ids']),affected_questions=len(metadata['affected_question_ids']),operations=len(operations),source_assets=len(e['payload']['pages']))
    return dict(stage='content_quality',evidence_ref=ref(e),graph_ref=ref(derived),plan_ref=ref(plan),application_ref=ref(application),base_check_ref=ref(c),review_ref=docref(review),review_basis=basis,
        base_check_archive=c,source_layer_proof=metadata['source_layer_proof'],prior_question_findings=prior,fresh_question_findings=fresh,rule_dispositions=dispositions,issues=issues,page_coverage=coverage,summary=summary,**_FLAGS)


def audit_content_quality(evidence,base_graph,base_check,plan,application,review,check):
    def inspect(emit):
        expected,derived=_application(evidence,base_graph,base_check,plan,application,emit)
        _header(check,'b-check-trial/0.6','CheckReportTrial','content-check',evidence,[ref(v)for v in (evidence,derived,base_check,plan,application)]+[docref(review)],'quality')
        payload=_quality_payload(evidence,base_graph,base_check,plan,application,review,derived,expected)
        if not _equal(check['payload'],payload):emit('CONTENT_REVISION_CURRENT_CHECK_MISMATCH')
        return dict(**payload['summary'],prior_question_findings=len(payload['prior_question_findings']),fresh_question_findings=len(payload['fresh_question_findings']),
            individually_rechecked_issues=len(payload['rule_dispositions']))
    return _safe([evidence,base_graph,base_check,plan,application,check],inspect)
