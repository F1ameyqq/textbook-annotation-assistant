"""Compose three fixed B content lanes and source-bound review candidates, offline only.

This internal workspace is neither a public graph contract nor an approval.
Native records, selected relationships and original source ledger remain intact.
"""
from pathlib import Path
import argparse, copy, hashlib, io, json, sys
from PIL import Image

from reconcile_chapter_sources_b import (ROOT, PINS, QID, AID, unpack_fixed, build as reconcile,
                                         sha, canonical, encode, need)

EXTRA = {
 'base':('handoffs/b/46007447/B-46007447-Q15-revision9-current-baseline-HOLD-2026-10-18.zip','8c812330b93cc60b920f6ccd1cd7784f0afe8d293336166a586e1aeaab8231ad'),
 'reading':('handoffs/b/46007447/B-46007447-viewer13-v3-portable-HOLD-2026-10-18.zip','81d5773a5aca8bd3dd67cef75dc610c4af9fc78903d57fc7f8373287b8041936'),
 'geometry':('handoffs/b/46007447/B-46007447-math-world-geometry-v1-HOLD-2026-10-17.zip','761ef0f98a4ea0b96a73ba0eb798d9192052eda6ce35f69d2d9ceeeb0dc47525'),
}
JSON_PINS = {
 'review':('tests/fixtures/book46007447/current-content-model-review-20261020.json','a5f96d493e291ab47a7ea7945874a64e2d02c86547443d62d750bb190858c798'),
 'binding':('evaluation/46007447-math-world-g09-readonly-binding-sidecar-v2-20261018.json','7f57ae75d19272086151970c9207e501630468fe03c36959445cb786426e69b5'),
}
ROW_IDS=['viewer-173/ocr/'+str(n) for n in (102,104,108,110,112)]
ref=lambda item:{k:item[k] for k in ('artifact_id','revision','content_hash')}

def unique_object(raw):
    def pairs(values):
        out={}
        for k,v in values:
            need(k not in out,'DUPLICATE_JSON_KEY');out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs)

def fixed_json(raw,pin):
    # Git text eol=lf: normalize only CRLF, never images, ZIPs or arbitrary whitespace.
    normalized=raw.replace(b'\r\n',b'\n')
    need(sha(normalized)==pin,'FIXED_JSON_LF_SHA')
    return unique_object(normalized)

def load_inputs(root=ROOT):
    packages={key:unpack_fixed(root/path,pin) for key,(path,pin) in {**PINS,**EXTRA}.items()}
    objects={}
    for key,(path,pin) in JSON_PINS.items():
        objects[key]=fixed_json((root/path).read_bytes(),pin)
    objects.update(packages=packages)
    return objects

def prepare(inputs):
    pkg=inputs['packages']
    inventory,q16=reconcile(pkg['observed'],pkg['question'],pkg['answers'])
    base=unique_object(pkg['base']['reference/final/graph.json'])
    check=unique_object(pkg['base']['reference/final/check.json'])
    reading=unique_object(pkg['reading']['reference/artifacts/graph.json'])
    reading_check=unique_object(pkg['reading']['reference/artifacts/check.json'])
    plan=unique_object(pkg['question']['plan.json'])
    for obj,schema in ((base,'b-graph-trial/0.8'),(reading,'b-graph-trial/0.9')):
        need(obj['schema_version']==schema and obj['book_id']=='46007447' and obj['content_hash']==sha(canonical(obj['payload'])),'NATIVE_GRAPH_IDENTITY')
    need(check['payload']['graph_ref']==ref(base) and check['content_hash']==sha(canonical(check['payload'])),'BASE_CHECK_BINDING')
    need(reading_check['schema_version']=='b-check-trial/0.9' and reading_check['input_refs'][1]==ref(reading) and
         reading_check['content_hash']==sha(canonical(reading_check['payload'])),'READING_CHECK_BINDING')
    b=inputs['binding'];review=inputs['review']
    need(ref(reading)==b['fixed_target']['artifact_ref'] and b['bound_material']['material_id']==review['material']['material_id'],'READING_BINDING_TARGET')
    need(sha(pkg['reading']['reference/artifacts/graph.json'])==b['fixed_target']['cold_assemble_sha256'],'READING_FIXED_FILE')
    need(not review['independent_human'] and not review['business_acceptance'] and review['decision']=='HOLD','NO_REVIEW_PROMOTION')
    images={row['asset_id']:pkg['observed'][row['source_package_member']] for row in inventory['verified_local_assets']}
    need(images['viewer-13']==pkg['reading']['inputs/source/46007447_page_12.jpg'],'READING_SOURCE_PIXELS')
    need(images['viewer-173']==pkg['geometry']['source/46007447_viewer_173.jpg'],'MATERIAL_SOURCE_PIXELS')
    need(review['source_sha256']==sha(images['viewer-173']),'MODEL_REVIEW_SOURCE')
    actual_answer=next(a for a in base['payload']['answers'] if a['answer_id']==AID)
    need(actual_answer==q16['answer_snapshot'],'Q16_CURRENT_ANSWER')
    return inventory,q16,base,check,reading,reading_check,plan,images

def build_workspace(inputs):
    inventory,q16,base,check,reading,rcheck,plan,images=prepare(inputs)
    b=inputs['binding'];review=inputs['review'];image=Image.open(io.BytesIO(images['viewer-173'])).convert('RGB')
    questions=[]
    for lane,items,origin,interface in [('base',base['payload']['questions'],ref(base),'native-fragments/0.8'),
              ('reading',reading['payload']['questions'],ref(reading),'native-fragments/0.9'),
              ('question',plan['payload']['questions'],{'file_sha256':q16['provenance']['question_plan_file_sha256']},'source-blocks/v4')]:
        questions.extend(dict(question_id=q['question_id'],lane=lane,source_ref=origin,content_interface=interface,native=copy.deepcopy(q))for q in items)
    need(len({q['question_id'] for q in questions})==len(questions),'DUPLICATE_QUESTION_ID')
    answers=[dict(answer_id=a['answer_id'],lane='base',source_ref=ref(base),native=copy.deepcopy(a))for a in base['payload']['answers']]
    material=copy.deepcopy(reading['payload']['shared_materials'][0])
    need(material['material_id']==b['bound_material']['material_id'],'MATERIAL_IDENTITY')
    regions=[]
    for region in b['geometry_bindings']:
        raw=inputs['packages']['geometry'][region['segment_id']+'.png']
        need(sha(raw)==region['png_sha256'],'MATERIAL_CROP_FILE')
        crop=Image.open(io.BytesIO(raw)).convert('RGB')
        need(crop.size==(region['bbox_xyxy'][2]-region['bbox_xyxy'][0],region['bbox_xyxy'][3]-region['bbox_xyxy'][1]) and
             crop.tobytes()==image.crop(region['bbox_xyxy']).tobytes(),'MATERIAL_CROP_PIXELS')
        runs=copy.deepcopy(review['material']['segments'].get(region['segment_id'],[]))
        regions.append(dict(**copy.deepcopy(region),content_origin='MODEL_VISUAL_PIXEL_SUPPLEMENT_NOT_OCR',
                            asset_id='viewer-173',source_sha256=sha(images['viewer-173']),runs=runs,
                            content_type='image' if region['segment_id']=='task3-diagram' else 'text',
                            text=''.join(r['text'] for r in runs),human_verified=False))
    current_task_answers=[]
    for task in material['tasks']:
        parts=[r for r in regions if r['target_task_id']==task['task_id']]
        answer_id='material-answer-'+sha(canonical([task['task_id'],[(r['segment_id'],r['png_sha256']) for r in parts]]))[:24]
        current_task_answers.append(dict(answer_id=answer_id,task_id=task['task_id'],material_id=material['material_id'],
            source_regions=parts,text='\n'.join(r['text'] for r in parts if r['content_type']=='text'),
            blank_responses=copy.deepcopy(review['material']['task1_blank_responses']) if task['label']=='(1)' else [],
            status='MODEL_DRAFT_REVIEW_PENDING',relationship_status='CANDIDATE_NOT_SELECTED',
            verification_status='UNVERIFIED',human_verified=False,business_acceptance=False))
    legacy=copy.deepcopy(base['payload']['answer_coverage'])
    working=[]
    for row in legacy:
        if row['status']!='UNASSIGNED':continue
        bindings=[x for x in b['source_line_bindings'] if x['line_id']==row['line_id']]
        working.append(dict(line_id=row['line_id'],legacy_status=row['status'],
            current_status='CANDIDATE_ASSEMBLED_REVIEW_PENDING' if bindings else 'NO_CURRENT_CANDIDATE',
            source_binding=copy.deepcopy(bindings[0]) if bindings else None,
            material_answer_ids=[a['answer_id'] for a in current_task_answers if bindings and a['task_id'] in bindings[0]['target_task_ids']],
            production_assignment_written=False))
    formula_runs=[(line,index,run) for line in q16['answer_snapshot']['content_fragments'] for index,run in enumerate(line['runs']) if run['format']=='latex']
    fractions=[]
    need(len(formula_runs)==len(review['q16']['fractions'])==11,'Q16_FORMULA_COUNT')
    for (line,index,run),slot in zip(formula_runs,review['q16']['fractions']):
        need(run['text']==slot['expected_latex'],'Q16_FORMULA_SLOT_'+slot['slot'])
        need(sha(image.crop(slot['source_bbox']).tobytes())==slot['crop_rgb_sha256'],'Q16_FORMULA_PIXELS')
        fractions.append(dict(**copy.deepcopy(slot),content_fragment_id=line['content_fragment_id'],run_index=index,
                              answer_file_basis=q16['provenance']['answer_source_graph_ref']))
    payload=dict(questions=questions,legacy_answers=answers,shared_materials=[material],
        material_answer_drafts=current_task_answers,source_regions=regions,legacy_answer_coverage=legacy,
        current_unassigned_work_queue=working,q16_relationship=q16,q16_formula_review=fractions,
        source_inventory=inventory,branch_checks={'base':copy.deepcopy(check),'reading':copy.deepcopy(rcheck)},
        branch_refs={'base':ref(base),'reading':ref(reading),'question_plan':q16['provenance']['question_plan_file_sha256']},
        counts=dict(question_candidates=len(questions),legacy_answers=len(answers),materials=1,material_tasks=len(material['tasks']),
            new_material_answer_drafts=len(current_task_answers),legacy_unassigned=len(working),
            candidate_assembled_rows=sum(r['current_status']=='CANDIDATE_ASSEMBLED_REVIEW_PENDING' for r in working),
            rows_without_current_candidate=sum(r['current_status']=='NO_CURRENT_CANDIDATE' for r in working)),
        decision='HOLD',chapter_denominator=None,human_verified=False,business_acceptance=False,
        public_contract_frozen=False,platform_actions=[],old_graphs_modified=False,old_ledger_modified=False,
        input_pins={k:v[1] for k,v in {**PINS,**EXTRA,**JSON_PINS}.items()})
    return dict(schema_version='b-chapter-workspace-trial/0.1',book_id='46007447',date='2026-10-20',
                content_hash=sha(canonical(payload)),payload=payload)

def audit_workspace(workspace,inputs):
    """Check native preservation and review bindings without calling the producer."""
    errors=[]
    def require(test,code):
        if not test:raise ValueError(code)
    try:
        inventory,q16,base,check,reading,rcheck,plan,images=prepare(inputs)
        p=workspace['payload'];b=inputs['binding'];review=inputs['review']
        require(workspace['schema_version']=='b-chapter-workspace-trial/0.1' and workspace['book_id']=='46007447','WORKSPACE_SCHEMA')
        require(workspace['content_hash']==sha(canonical(p)),'WORKSPACE_HASH')
        require(p['decision']=='HOLD' and p['chapter_denominator'] is None and not p['human_verified'] and not p['business_acceptance'] and
                not p['public_contract_frozen'] and p['platform_actions']==[] and not p['old_graphs_modified'] and not p['old_ledger_modified'],'NO_PROMOTION')
        source_sets={'base':base['payload']['questions'],'reading':reading['payload']['questions'],'question':plan['payload']['questions']}
        require(set(source_sets)=={q['lane'] for q in p['questions']},'LANES_COMPLETE')
        all_ids=[]
        for lane,records in source_sets.items():
            got=[q for q in p['questions'] if q['lane']==lane]
            require([q['native'] for q in got]==records,'NATIVE_QUESTION_PRESERVATION_'+lane)
            expected_ref=ref(base) if lane=='base' else ref(reading) if lane=='reading' else {'file_sha256':q16['provenance']['question_plan_file_sha256']}
            interface={'base':'native-fragments/0.8','reading':'native-fragments/0.9','question':'source-blocks/v4'}[lane]
            require(all(q['source_ref']==expected_ref and q['question_id']==q['native']['question_id'] and q['content_interface']==interface for q in got),'QUESTION_REFERENCE_'+lane)
            all_ids.extend(q['question_id'] for q in got)
        require(len(set(all_ids))==len(all_ids),'DUPLICATE_QUESTION_ID')
        require([a['native'] for a in p['legacy_answers']]==base['payload']['answers'] and all(a['answer_id']==a['native']['answer_id'] and a['source_ref']==ref(base) and a['lane']=='base' for a in p['legacy_answers']),'LEGACY_ANSWER_PRESERVATION')
        require(p['shared_materials']==reading['payload']['shared_materials'],'SHARED_MATERIAL_PRESERVATION')
        require(p['legacy_answer_coverage']==base['payload']['answer_coverage'],'LEGACY_LEDGER_PRESERVATION')
        require(p['branch_checks']=={'base':check,'reading':rcheck} and p['source_inventory']==inventory and
                p['branch_refs']=={'base':ref(base),'reading':ref(reading),'question_plan':q16['provenance']['question_plan_file_sha256']},'BRANCH_CHECK_AND_INVENTORY')
        require(p['q16_relationship']==q16,'Q16_CURRENT_RELATION_BINDING')
        runs=[(line,index,run) for line in q16['answer_snapshot']['content_fragments'] for index,run in enumerate(line['runs']) if run['format']=='latex']
        require(len(p['q16_formula_review'])==len(runs)==11,'Q16_SLOT_COVERAGE')
        image=Image.open(io.BytesIO(images['viewer-173'])).convert('RGB')
        for got,want,(line,index,run) in zip(p['q16_formula_review'],review['q16']['fractions'],runs):
            require(all(got[k]==v for k,v in want.items()) and got['expected_latex']==run['text'] and got['content_fragment_id']==line['content_fragment_id'] and got['run_index']==index and got['answer_file_basis']==ref(base),'Q16_SLOT_IDENTITY_AND_CONTENT')
            require(sha(image.crop(got['source_bbox']).tobytes())==got['crop_rgb_sha256'],'Q16_SLOT_PIXEL_BINDING')
        require(len(p['source_regions'])==7,'MATERIAL_REGION_COUNT')
        tasks={t['task_id']:t for t in reading['payload']['shared_materials'][0]['tasks']}
        for got,want in zip(p['source_regions'],b['geometry_bindings']):
            require(all(got[k]==v for k,v in want.items()) and got['target_task_id'] in tasks,'MATERIAL_GEOMETRY_TARGET')
            raw=inputs['packages']['geometry'][got['segment_id']+'.png']
            require(sha(raw)==got['png_sha256'] and Image.open(io.BytesIO(raw)).convert('RGB').tobytes()==image.crop(got['bbox_xyxy']).tobytes(),'MATERIAL_PIXELS')
            require(got['runs']==review['material']['segments'].get(got['segment_id'],[]) and got['text']==''.join(r['text'] for r in got['runs']),'MATERIAL_CURRENT_TEXT')
            require(not got['human_verified'] and not got['production_assignment_allowed'] and got['content_origin']=='MODEL_VISUAL_PIXEL_SUPPLEMENT_NOT_OCR','NO_SUPPLEMENT_PROMOTION')
        drafts=p['material_answer_drafts'];require(len(drafts)==3 and len({a['answer_id'] for a in drafts})==3,'MATERIAL_ANSWER_IDENTITIES')
        for a,task in zip(drafts,tasks.values()):
            require(a['task_id']==task['task_id'] and a['material_id']==b['bound_material']['material_id'],'MATERIAL_TASK_IDENTITY')
            regions=[r for r in p['source_regions'] if r['target_task_id']==task['task_id']]
            require(a['source_regions']==regions and a['text']=='\n'.join(r['text'] for r in regions if r['content_type']=='text'),'MATERIAL_ANSWER_ASSEMBLY')
            expected_id='material-answer-'+sha(canonical([task['task_id'],[(r['segment_id'],r['png_sha256'])for r in regions]]))[:24]
            require(a['answer_id']==expected_id and not a['human_verified'] and not a['business_acceptance'] and a['relationship_status']=='CANDIDATE_NOT_SELECTED' and a['status']=='MODEL_DRAFT_REVIEW_PENDING' and a['verification_status']=='UNVERIFIED','MATERIAL_ANSWER_UNSELECTED')
            require(a['blank_responses']==(review['material']['task1_blank_responses'] if task['label']=='(1)' else []),'MATERIAL_BLANK_RESPONSE_ORDER')
        queue=p['current_unassigned_work_queue'];legacy=[r for r in base['payload']['answer_coverage'] if r['status']=='UNASSIGNED']
        require([r['line_id'] for r in queue]==[r['line_id'] for r in legacy],'WORK_QUEUE_COVERAGE')
        require([r['line_id'] for r in queue if r['current_status']=='CANDIDATE_ASSEMBLED_REVIEW_PENDING']==ROW_IDS,'FIVE_ROW_DISPOSITION')
        for row in queue:
            binding=next((x for x in b['source_line_bindings'] if x['line_id']==row['line_id']),None)
            expected_status='CANDIDATE_ASSEMBLED_REVIEW_PENDING' if binding else 'NO_CURRENT_CANDIDATE'
            require(row['legacy_status']=='UNASSIGNED' and row['source_binding']==binding and not row['production_assignment_written'] and row['current_status']==expected_status,'ROW_GRANULARITY')
            require(row['material_answer_ids']==[a['answer_id'] for a in drafts if binding and a['task_id'] in binding['target_task_ids']],'ROW_TASK_ASSIGNMENTS')
        expected_counts=dict(question_candidates=len(all_ids),legacy_answers=len(base['payload']['answers']),materials=1,material_tasks=3,new_material_answer_drafts=3,legacy_unassigned=len(legacy),candidate_assembled_rows=5,rows_without_current_candidate=len(legacy)-5)
        require(p['counts']==expected_counts,'COUNT_ACCOUNTING')
        require(p['input_pins']=={k:v[1]for k,v in {**PINS,**EXTRA,**JSON_PINS}.items()},'INPUT_PINS')
    except (ValueError,KeyError,TypeError,IndexError) as exc: errors.append(str(exc))
    return dict(schema_version='b-chapter-workspace-audit/0.1',workspace_content_hash=workspace.get('content_hash'),
                source_and_structure_accepted=not errors,errors=errors,decision='HOLD',human_accepted=False,chapter_accepted=False,
                audit_calls_producer=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();inputs=load_inputs();view=build_workspace(inputs);audit=audit_workspace(view,inputs)
    need(audit['source_and_structure_accepted'],'WORKSPACE_AUDIT_FAILED')
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'workspace.json').write_bytes(encode(view));(args.out/'audit.json').write_bytes(encode(audit))
    print(json.dumps(dict(counts=view['payload']['counts'],audit=audit),ensure_ascii=False))

if __name__=='__main__':main()
