"""Source-bound question content projection, deliberately outside graph/matching APIs.

This retains model transcriptions as drafts. Pixel/line provenance is checked;
neither a matching crop nor a complete ledger certifies semantic completeness.
"""
from __future__ import annotations
import copy
import hashlib
import io
import json
from pathlib import Path
import re
from PIL import Image
from .baseline import digest, file_digest, load_source, code_digest

PLAN_SCHEMA = 'b-question-source-draft-trial/0.1'
APPLICATION_SCHEMA = 'b-question-content-application-trial/0.1'
RISK_CODES = ['MODEL_TRANSCRIPTION_UNVERIFIED', 'SOURCE_REGION_EXTENT_UNVERIFIED', 'FIGURE_EXTENT_UNVERIFIED',
              'FORMULA_TRANSCRIPTION_UNVERIFIED', 'SECTION_IDENTITY_UNVERIFIED',
              'ANSWER_MATCHING_NOT_PERFORMED', 'BUSINESS_REVIEW_REQUIRED']


def ref(value):
    return {key: value[key] for key in ('artifact_id', 'revision', 'content_hash')}


def read_json(path):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value: raise ValueError('duplicate JSON key')
            value[key] = item
        return value
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def _box(box, size):
    return (isinstance(box, list) and len(box) == 4 and all(type(v) is int for v in box)
            and 0 <= box[0] < box[2] <= size[0] and 0 <= box[1] < box[3] <= size[1])


def _contains(outer, inner):
    return outer[0] <= inner[0] < inner[2] <= outer[2] and outer[1] <= inner[1] < inner[3] <= outer[3]


def _intersects(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def _flags(value):
    if (value.get('decision') != 'HOLD' or value.get('human_verification') is not False
            or value.get('transcription_verified') is not False or value.get('business_acceptance') is not False
            or value.get('platform_actions') != []): raise ValueError('question drafts cannot assert approval')


def _fraction_order(components):
    rows=[]
    for part in sorted(components,key=lambda c:min(p['bbox'][1]for p in c['parts'])):
        x=min(p['bbox'][0]for p in part['parts']);lo=min(p['bbox'][1]for p in part['parts']);hi=max(p['bbox'][3]for p in part['parts'])
        if rows and max(lo,rows[-1]['lo'])<min(hi,rows[-1]['hi']):
            rows[-1]['items'].append((x,part['component_id']));rows[-1]['lo']=max(lo,rows[-1]['lo']);rows[-1]['hi']=min(hi,rows[-1]['hi'])
        else:rows.append(dict(lo=lo,hi=hi,items=[(x,part['component_id'])]))
    return [id for row in rows for _,id in sorted(row['items'])]


def apply_question_content(source_path, evidence, graph, plan_path, *, expected_plan_sha256, output_dir):
    """Materialize one exact reviewed draft; no OCR, model, graph mutation or matching."""
    plan_path, output_dir = Path(plan_path), Path(output_dir)
    if file_digest(plan_path) != expected_plan_sha256: raise ValueError('externally fixed plan bytes changed')
    plan = read_json(plan_path)
    if set(plan) != {'schema_version', 'content_hash', 'payload'} or plan['schema_version'] != PLAN_SCHEMA:
        raise ValueError('unsupported question plan schema')
    p = plan['payload']
    if set(p) != {'book_id','asset_id','source_sha256','source_size','evidence_ref','graph_ref','baseline_ref','context_ref','evidence_artifact_sha256','graph_artifact_sha256','page_ocr_snapshot','source_ledger','author','questions','decision','human_verification','transcription_verified','business_acceptance','platform_actions'}:
        raise ValueError('unknown plan fields')
    if plan['content_hash'] != digest(p): raise ValueError('question plan payload hash mismatch')
    _flags(p)
    if set(p.get('author',{}))!={'kind','id','note'} or p['author']['kind'] != 'MODEL_DRAFT': raise ValueError('draft author required')
    if (evidence.get('schema_version') != 'b-evidence-trial/0.2' or graph.get('schema_version') != 'b-graph-trial/0.2'
            or evidence.get('kind')!='EvidenceBundleTrial' or graph.get('kind')!='QuestionGraphTrial'):
        raise ValueError('question projection accepts only exact evidence0.2/graph0.2 base pair')
    for item in (evidence, graph):
        if set(item)!={'artifact_id','book_id','content_hash','created_at','input_refs','kind','payload','producer','revision','run_id','schema_version','scope_id'}:
            raise ValueError('base envelope fields differ')
        if type(item.get('revision')) is not int or item['revision'] < 1 or item.get('content_hash') != digest(item['payload']):
            raise ValueError('base artifact is corrupt')
    context=evidence['payload']['context']
    if (digest(evidence)!=p['evidence_artifact_sha256'] or digest(graph)!=p['graph_artifact_sha256']
            or evidence['run_id']!=graph['run_id'] or graph['input_refs']!=[ref(evidence)]
            or p['context_ref']!={'artifact_id':context['artifact_id'],'content_hash':digest(context)}
            or evidence['input_refs']!=[p['baseline_ref'],p['context_ref']]):
        raise ValueError('complete base envelope or exact input references changed')
    source, assets = load_source(Path(source_path))
    if (len(assets) != 1 or source['book_id'] != p['book_id'] or evidence['book_id'] != p['book_id']
            or graph['book_id'] != p['book_id'] or source['scope_id'] != evidence['scope_id']
            or graph['scope_id'] != evidence['scope_id'] or p['evidence_ref'] != ref(evidence)
            or p['graph_ref'] != ref(graph) or p['baseline_ref'] != evidence['input_refs'][0]):
        raise ValueError('single-page source/base identity mismatch')
    asset, image_path = assets[0]
    pages = evidence['payload']['pages']
    if len(pages) != 1 or pages[0]['source'] != asset or graph['input_refs'][0] != ref(evidence):
        raise ValueError('source evidence or graph binding mismatch')
    page = pages[0]
    if (p['asset_id'] != asset['asset_id'] or p['source_sha256'] != asset['sha256']
            or p['source_size'] != [asset['width'], asset['height']] or p['page_ocr_snapshot'] != page['ocr_lines']):
        raise ValueError('source pixels or complete OCR snapshot mismatch')
    base_questions = graph['payload']['questions']
    if (graph['payload']['answers'] or any(q['candidate_answer_ids'] or q['selected_answer_id'] is not None for q in base_questions)
            or [q['question_id'] for q in p['questions']] != [q['question_id'] for q in base_questions]):
        raise ValueError('all page questions must remain isolated and unmatched')
    image = Image.open(image_path).convert('RGB')
    products, receipts, seen_blocks, seen_blanks, claimed_lines = [], [], set(), set(), set()
    regions = [q['question_bbox'] for q in p['questions']]
    for i, box in enumerate(regions):
        if not _box(box, p['source_size']) or any(_intersects(box, other) for other in regions[i+1:]):
            raise ValueError('question regions overlap or leave source bounds')
    for q, old in zip(p['questions'], base_questions):
        if set(q)!={'question_id','printed_number','asset_id','source_question_sha256','question_bbox','blocks','counting_status','section_status','answer_link_status','source_ocr_snapshot','source_question_archive'}:
            raise ValueError('unknown question projection fields')
        if (q['source_question_archive'] != old or q['source_question_sha256'] != digest(old)
                or q['printed_number'] != old['printed_number'] or q['asset_id'] != asset['asset_id']
                or q['counting_status'] != 'UNKNOWN' or q['section_status'] != 'INFERRED_UNVERIFIED'
                or q['answer_link_status'] != 'UNMATCHED'):
            raise ValueError('question identity/archive or unverified state changed')
        if any(not _contains(q['question_bbox'], f['bbox']) for f in old['fragments']):
            raise ValueError('question region clips an original fragment')
        actual_lines = [line for line in page['ocr_lines'] if _contains(q['question_bbox'], line['bbox'])]
        if q['source_ocr_snapshot'] != actual_lines: raise ValueError('question OCR snapshot is incomplete')
        for line in actual_lines:
            if line['line_id'] in claimed_lines: raise ValueError('OCR assigned to two questions')
            claimed_lines.add(line['line_id'])
        blocks = q['blocks']
        if not blocks or blocks[0]['role'] != 'stem': raise ValueError('question requires a source stem')
        old_options = [f['option_label'] for f in old['fragments'] if f.get('option_start')]
        options = [b.get('label') for b in blocks if b['role'] == 'option']
        if options != old_options or options and options != ['A', 'B', 'C', 'D']:
            raise ValueError('independent A-D option sequence changed')
        anchors = [m.group(1) for line in actual_lines if (m := re.match(r'^[（(](\d+)[）)]', line['text']))]
        if [b.get('label') for b in blocks if b['role'] == 'task'] != anchors:
            raise ValueError('source task anchors differ')
        if '如图' in old['text'] and not any(b['role'] == 'figure' for b in blocks):
            raise ValueError('source figure prompt cannot be represented only by text')
        for i, b in enumerate(blocks):
            allowed={'block_id','role','bbox','source_sha256','crop_rgb_sha256','verification_status','crop_png_sha256','crop_size','source_ocr_refs','content_origin'}
            if b['role']!='figure':allowed.add('runs')
            if b['role']in{'option','task'}:allowed.add('label')
            if b['role']=='task':allowed.add('parent_question_id')
            if 'fraction_components'in b:allowed.add('fraction_components')
            if 'editorial_badges'in b:allowed.add('editorial_badges')
            if set(b)!=allowed:raise ValueError('unknown content block fields')
            bid, box = b['block_id'], b['bbox']
            if (not isinstance(bid, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', bid) or bid in seen_blocks
                    or b['role'] not in {'stem', 'option', 'figure', 'task'} or not _box(box, p['source_size'])
                    or not _contains(q['question_bbox'], box) or b['verification_status'] != 'UNVERIFIED'
                    or b['source_sha256'] != asset['sha256'] or any(_intersects(box, other['bbox']) for other in blocks[i+1:])):
                raise ValueError('invalid, overlapping or duplicate source block')
            seen_blocks.add(bid)
            actual_refs = [line['line_id'] for line in actual_lines if _contains(box, line['bbox'])]
            if b['source_ocr_refs'] != actual_refs: raise ValueError('block OCR refs changed')
            contained=[line for line in actual_lines if line['line_id']in actual_refs]
            if b['role']=='stem'and old['anchor_ref']not in actual_refs:raise ValueError('stem omits original question anchor')
            if b['role']=='option'and [m.group(1)for line in contained if(m:=re.match(r'^([A-D])[.．、]',line['text']))]!=[b['label']]:
                raise ValueError('option label differs from source marker')
            if b['role']=='task'and [m.group(1)for line in contained if(m:=re.match(r'^[（(](\d+)[）)]',line['text']))]!=[b['label']]:
                raise ValueError('task label differs from source marker')
            if b['role'] == 'task' and b.get('parent_question_id') != q['question_id']: raise ValueError('task parent changed')
            for badge in b.get('editorial_badges',[]):
                if (set(badge)!={'text','bbox','crop_rgb_sha256','disposition','verification_status'} or b['role']!='stem'
                        or not isinstance(badge['text'],str) or not badge['text'] or not _box(badge['bbox'],p['source_size'])
                        or not _contains(box,badge['bbox']) or badge['disposition']!='SOURCE_DECORATION_RETAINED'
                        or badge['verification_status']!='UNVERIFIED' or hashlib.sha256(image.crop(badge['bbox']).tobytes()).hexdigest()!=badge['crop_rgb_sha256']):
                    raise ValueError('editorial badge source or disposition differs')
            if b['content_origin'] != ('SOURCE_PIXELS' if b['role'] == 'figure' else 'MODEL_VISUAL_TRANSCRIPTION'):
                raise ValueError('question content origin is not explicit')
            crop = image.crop(box); rgb_sha = hashlib.sha256(crop.tobytes()).hexdigest()
            stream = io.BytesIO(); crop.save(stream, format='PNG'); png = stream.getvalue()
            if (rgb_sha != b['crop_rgb_sha256'] or list(crop.size) != b['crop_size']
                    or hashlib.sha256(png).hexdigest() != b['crop_png_sha256']): raise ValueError('source crop differs')
            if b['role'] == 'figure':
                if b.get('runs'): raise ValueError('figure must retain original source pixels')
            elif not b.get('runs'): raise ValueError('text block lacks explicit draft runs')
            for run in b.get('runs', []):
                if run['format'] == 'blank':
                    if (set(run) != {'format','blank_id','bbox','response_kind','value'} or run['value'] is not None
                            or run['blank_id'] in seen_blanks or not _box(run['bbox'], p['source_size'])
                            or not _contains(box, run['bbox']) or run['response_kind'] not in {'expression','single_choice'}):
                        raise ValueError('response blank is filled, duplicated or outside source block')
                    seen_blanks.add(run['blank_id'])
                elif (run['format'] not in {'plain','latex'} or set(run) != {'format','text'}
                      or not isinstance(run['text'],str) or not run['text'].strip()): raise ValueError('unsupported draft text run')
            fractions = b.get('fraction_components', [])
            if sum(run.get('text','').count(r'\frac{') for run in b.get('runs', [])) != len(fractions):
                raise ValueError('fraction text lacks explicit source component structure')
            component_ids=set();numerator_boxes=set()
            positions=[i for i,run in enumerate(b.get('runs',[]))if run.get('format')=='latex'and r'\frac{'in run.get('text','')]
            if [c.get('run_index')for c in fractions]!=positions or any(type(c.get('run_index'))is not int for c in fractions):
                raise ValueError('source fractions are not bound to exact LaTeX runs')
            for fraction in fractions:
                parts = fraction['parts']
                if set(fraction)!={'component_id','parts','verification_status','run_index'}:raise ValueError('unknown fraction fields')
                if (not isinstance(fraction['component_id'],str) or not fraction['component_id'] or fraction['component_id']in component_ids
                        or not isinstance(parts,list) or len(parts)!=3):raise ValueError('duplicate or malformed fraction component')
                component_ids.add(fraction['component_id'])
                if fraction['verification_status'] != 'UNVERIFIED' or [c['role'] for c in parts] != ['numerator','bar','denominator']:
                    raise ValueError('fraction structure is not explicit')
                if not (parts[0]['bbox'][3] <= parts[1]['bbox'][1] and parts[1]['bbox'][3] <= parts[2]['bbox'][1]):
                    raise ValueError('fraction parts are not in numerator/bar/denominator order')
                for part in parts:
                    if (set(part)!={'role','bbox','crop_rgb_sha256','verification_status'} or not _box(part['bbox'],p['source_size']) or not _contains(box,part['bbox'])
                            or part['verification_status'] != 'UNVERIFIED'
                            or hashlib.sha256(image.crop(part['bbox']).tobytes()).hexdigest() != part['crop_rgb_sha256']):
                        raise ValueError('fraction component pixels or geometry differ')
                if tuple(parts[0]['bbox'])in numerator_boxes:raise ValueError('same source fraction counted twice')
                numerator_boxes.add(tuple(parts[0]['bbox']))
            if [c['component_id']for c in fractions]!=_fraction_order(fractions):raise ValueError('source fraction reading order changed')
            receipts.append(dict(block_id=bid,relative_path=bid+'.png',source_bbox=box,
                                 rgb_sha256=rgb_sha,file_sha256=hashlib.sha256(png).hexdigest(),size=list(crop.size),
                                 transform_to_source=[[1,0,box[0]],[0,1,box[1]],[0,0,1]]))
            products.append((bid+'.png',png))
    expected_ledger = [dict(line_id=line['line_id'],owner_question_id=next((q['question_id'] for q in p['questions']
                       if _contains(q['question_bbox'],line['bbox'])),None),status='QUESTION_SOURCE'
                       if line['line_id'] in claimed_lines else 'COLUMN_HEADER_DECORATION' if line['bbox'][3]<=min(r[1]for r in regions)
                       else 'PAGE_FOOTER' if line['bbox'][1]>=max(r[3]for r in regions) else 'UNASSIGNED') for line in page['ocr_lines']]
    if any(r['status']=='UNASSIGNED'for r in expected_ledger):raise ValueError('body OCR remains unassigned')
    if p['source_ledger'] != expected_ledger: raise ValueError('full page OCR ledger differs')
    if file_digest(image_path) != asset['sha256'] or file_digest(plan_path) != expected_plan_sha256:
        raise ValueError('input bytes changed during projection')
    payload = dict(plan_file_sha256=expected_plan_sha256,plan_archive=copy.deepcopy(plan),evidence_ref=ref(evidence),
                   source_graph_archive=copy.deepcopy(graph),questions=copy.deepcopy(p['questions']),source_ledger=expected_ledger,
                   crop_receipts=receipts,risks=RISK_CODES,decision='HOLD',complete=False,human_verification=False,
                   transcription_verified=False,business_acceptance=False,platform_actions=[],new_model_calls=0,
                   answer_matching_performed=False,graph_projection_performed=False)
    app = dict(schema_version=APPLICATION_SCHEMA,kind='QuestionContentApplicationTrial',book_id=p['book_id'],
               scope_id=evidence['scope_id'],revision=1,content_hash=digest(payload),payload=payload)
    app['producer']={'module':__name__,'code_sha256':code_digest(Path(__file__)),'baseline_code_sha256':code_digest(Path(__file__).with_name('baseline.py'))}
    app['artifact_id']='question-content-application-'+digest(app)[:24]
    output_dir.mkdir(parents=True,exist_ok=True)
    for name, raw in products:
        path=output_dir/name
        if path.exists() and path.read_bytes()!=raw: raise ValueError('refusing to overwrite a different source crop')
        path.write_bytes(raw)
    return app
