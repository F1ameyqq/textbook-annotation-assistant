"""Resolve the remaining 14 rows into source-local answer evidence and a pending review queue.

No question is invented from an answer. All legacy objects and relationships remain immutable.
"""
from pathlib import Path
import argparse, copy, io, json
from fractions import Fraction
from PIL import Image
import build_chapter_workspace_b as base

ROOT=base.ROOT
PINS={
 'identities':('evaluation/book-46007447-unassigned-identities.json','36663180ea7f00c01d33fa40be613d05f257118776d5ea18efb76a6067e17d54'),
 'remaining_review':('tests/fixtures/book46007447/remaining-answer-source-review-20261020.json','d7ac05ada808a4fe61615bff00b8ff8a35bedf78ebc0a85ab72597d5a5e4ce75'),
 'local_search':('evaluation/book-46007447-bounded-local-source-search-20261020.json','4ff6b046716b9083acfa7fe4dc4e8160d8c9457d2872bc65ddd6e489273dc79e'),
}
ROW_NUMBERS=(86,87,111,113,114,115,116,117,119,120,121,122,123,125)
LABELS={'topic1-examples/example-1':('【例1】',1),'topic1-examples/example-2':('【例2】',2),
        'topic2-example/unnumbered-example':('【例】',None),
        **{f'topic2-training/training-{n}':(f'{n}.',n)for n in range(1,6)}}
need=base.need;sha=base.sha;canonical=base.canonical;encode=base.encode

def load_inputs(root=ROOT):
    inputs=base.load_inputs(root)
    for key,(path,pin)in PINS.items():inputs[key]=base.fixed_json((root/path).read_bytes(),pin)
    return inputs

def pointer(value,path):
    for key in path.split('/'):
        value=value[int(key)]if isinstance(value,list)else value[key]
    return value

def acceptance_queue(parent):
    items=[]
    def item(identity,label,paths,criteria,assets):
        items.append(dict(issue_id=identity,label=label,scope_paths=paths,
            subject_sha256=sha(canonical([pointer(parent,p)for p in paths])),
            source_asset_ids=assets,current_evidence='MODEL_SOURCE_REVIEW_RECORDED_NOT_HUMAN_ACCEPTANCE',
            required_action=criteria,status='PENDING_INDEPENDENT_REVIEW',disposition=None,reviewer=None,review_artifact_sha256=None))
    q='payload/q16_relationship'
    item('Q16-MAPPING','题页、三小问及答案关系',[q],
         '独立核对书籍/章节/题号和两页来源，排除其他同号16；逐问确认60/61、第三数公式、三行证明的字符范围。题目三空不回填。',
         ['viewer-14','viewer-15','viewer-173'])
    for index,slot in enumerate(parent['payload']['q16_formula_review']):
        caution=''
        if slot['slot']=='F5':caution='本槽原OCR缺失，不按邻式补写。'
        if slot['slot']=='F9':caution='历史两遍模型曾同错，不以多数票核准。'
        if slot['slot']in('F10','F11'):caution='与相邻槽的历史模糊OCR支持不得复制；按各自像素位置分开确认。'
        item('Q16-'+slot['slot'],slot['slot']+'：分子、横线、分母及幂次',['payload/q16_formula_review/'+str(index)],
             '直接查看该槽原像素，独立逐符号记录分子/分母、括号和幂次后对照当前LaTeX；不清楚则UNKNOWN。'+caution,['viewer-173'])
    item('Q16-PERIPHERAL','三行外围文字与因果符号',[q+'/answer_snapshot'],
         '逐行确认∵/∴、外括号/平方、奇数且a≥3、标点/行序与两数60 61；任何规范化差异需留下源图依据。',['viewer-173'])
    item('Q16-REGIONS','题干及答案呈现区域',[q+'/question_snapshot/blocks',q+'/answer_snapshot/content_fragments'],
         '核对四个题目块及三答行的边界、行序和装饰A/题号口径；源窗口不直接当平台精确框。',['viewer-15','viewer-173'])
    item('READING-IDENTITY','共享材料及三个任务身份',['payload/shared_materials/0'],
         '按题页原图确认材料标题、无主印刷题号、三个任务及图1/图2归属；现有题页OCR有漏符号，不能作为正确性金标准。',['viewer-13'])
    criteria=[
      '核对CFGH边长、三角形面积、CFGH面积三个空的对应顺序；原102仅覆盖第一空，其余值是宽裁片补录，不扩大旧行。',
      '逐步核对S1/S2面积推导和公式/因果符号；104只是分子，108在x=228跨两任务，确认三段拼接没有吞入任务3。',
      '核对恒等式与整图相符，a/b标签、外框/内部线完整；108右段与110括注续接，112只是b标签，不是整图；保留答案不唯一。']
    for i,text in enumerate(criteria):
        item('READING-TASK'+str(i+1),'阅读任务'+str(i+1)+'：正文、答案与来源',
             ['payload/shared_materials/0/tasks/'+str(i),'payload/material_answer_drafts/'+str(i)],text,['viewer-13','viewer-173'])
    return dict(schema_version='b-current-acceptance-queue/0.1',base_workspace_hash=parent['content_hash'],items=items,
                pending_count=len(items),approved_count=0,human_acceptance=False,chapter_acceptance=False)

def source_context(inputs,parent):
    need(base.audit_workspace(parent,inputs)['source_and_structure_accepted'],'BASE_WORKSPACE_AUDIT')
    identity=inputs['identities'];need(identity['content_hash']==sha(canonical(identity['payload'])),'IDENTITY_REVIEW_HASH')
    rows={r['line_id']:r for r in identity['payload']['source_rows']if r['group_id']!='math-world'}
    need(set(rows)=={f'viewer-173/ocr/{n}'for n in ROW_NUMBERS},'FOURTEEN_EXACT_ROWS')
    remaining={r['line_id']for r in parent['payload']['current_unassigned_work_queue']if r['current_status']=='NO_CURRENT_CANDIDATE'}
    need(remaining==set(rows),'BASE_REMAINING_QUEUE')
    review=inputs['remaining_review'];need(review['book_id']=='46007447'and review['decision']=='HOLD'and not review['human_verified']and not review['business_acceptance'],'NO_REVIEW_PROMOTION')
    *_,images=base.prepare(inputs);image=Image.open(io.BytesIO(images['viewer-173'])).convert('RGB')
    need(review['source_sha256']==sha(images['viewer-173'])==identity['payload']['source']['sha256'],'ANSWER_SOURCE_IDENTITY')
    scan=inputs['local_search'];known=sorted(sha(raw)for raw in images.values())
    need(scan['archive_raw_page_shas']==known and scan['direct_raw_page_shas']==known and not scan['new_raw_page_shas']and
         not scan['inventory_frozen']and not scan['whole_computer_absence_proven'],'BOUNDED_SOURCE_SEARCH')
    for row in rows.values():
        need(row['assignment_status']=='UNASSIGNED'and row['source_sha256']==review['source_sha256']and sha(row['text'].encode())==row['text_sha256'],'RAW_ROW_IDENTITY')
        covered=[]
        for membership in row['raw_span_memberships']:
            start,end=membership['span'];need(row['text'][start:end]==membership['text'],'RAW_SPAN_TEXT')
            covered.extend(range(start,end))
        need(sorted(covered)==list(range(len(row['text'])))and len(set(covered))==len(covered),'RAW_SPAN_PARTITION')
    return rows,review,image

def check_region(region,image):
    box=region['bbox']
    need(len(box)==4 and all(type(x)is int for x in box)and 0<=box[0]<box[2]<=image.width and 0<=box[1]<box[3]<=image.height,'REVIEW_REGION_BOUNDS')
    need(region['geometry_status']=='MODEL_REVIEW_WINDOW_NOT_PLATFORM_BOX'and sha(image.crop(box).tobytes())==region['crop_rgb_sha256'],'REVIEW_REGION_PIXELS')

def build_processing(inputs,parent):
    rows,review,image=source_context(inputs,parent)
    originals={r['material_candidate_id']:r for r in inputs['identities']['payload']['material_candidates']}
    candidates=[]
    for item in review['items']:
        name=item['source_local_id'];need(name in LABELS and (item['label'],item['printed_number'])==LABELS[name],'SOURCE_LOCAL_LABEL')
        original=originals[name];need(item['printed_number']==original['printed_number']and item['label']==original['local_printed_label_model_visual'],'PRINTED_LABEL_IDENTITY')
        check_region(item['region'],image)
        for cell in item['cells']:check_region(cell['region'],image)
        for formula in item['formula_occurrences']:check_region(formula['region'],image)
        if name.startswith('topic1'):
            need(item['column_roles']is None and [c['cell_index']for c in item['cells']]==[1,2,3,4],'UNKNOWN_TABLE_COLUMNS')
        supporting=[copy.deepcopy(r)for r in rows.values()if name in r['material_candidate_ids']]
        candidate=dict(evidence_candidate_id='answer-evidence-'+sha(canonical([review['source_sha256'],name]))[:24],
           source_local_id=name,source_namespace=original['candidate_namespace'],source=copy.deepcopy(item),
           raw_rows=supporting,source_asset_id='viewer-173',source_sha256=review['source_sha256'],
           question_id=None,platform_question_id=None,a_contract_id=None,question_source_status='NOT_LOCATED_IN_BOUNDED_LOCAL_SCAN',
           relation_status='NO_QUESTION_RELATION',evidence_grade='MODEL_VISUAL_PIXEL_SUPPLEMENT',
           status='ANSWER_EVIDENCE_READY_QUESTION_SOURCE_PENDING',human_verified=False,business_acceptance=False,decision='HOLD')
        candidates.append(candidate)
    need({c['source_local_id']for c in candidates}==set(LABELS)and len(candidates)==8,'EIGHT_SOURCE_LOCAL_ITEMS')
    queue=copy.deepcopy(parent['payload']['current_unassigned_work_queue'])
    for entry in queue:
        if entry['line_id']not in rows:continue
        row=rows[entry['line_id']]
        entry.update(current_status='ANSWER_EVIDENCE_READY_QUESTION_SOURCE_PENDING',raw_row_snapshot=copy.deepcopy(row),
            evidence_candidate_ids=[c['evidence_candidate_id']for c in candidates if c['source_local_id']in row['material_candidate_ids']])
    x=Fraction(55,16);consistency=dict(table_example1=(10-Fraction(34,5))**2+36==Fraction(34,5)**2,
        table_example2=225-81==169-(14-9)**2,folding_example=(8-x)**2==x*x+9,
        role='AUXILIARY_ALGEBRA_CHECK_NOT_TRANSCRIPTION_IDENTITY_OR_ACCEPTANCE')
    payload=dict(base_workspace=copy.deepcopy(parent),base_workspace_hash=parent['content_hash'],
        answer_evidence_candidates=candidates,current_source_queue=queue,acceptance_queue=acceptance_queue(parent),
        local_source_search=copy.deepcopy(inputs['local_search']),auxiliary_consistency=consistency,
        counts=dict(legacy_unassigned_rows=19,reading_rows_with_assembled_drafts=5,rows_with_answer_evidence_only=14,
                    rows_without_source_processing=0,new_answer_evidence_candidates=8,missing_question_identity_rows=14,
                    acceptance_items=18,human_approved=0),
        input_pins={k:v[1]for k,v in PINS.items()},decision='HOLD',old_ledger_modified=False,platform_actions=[],new_question_entities=0)
    return dict(schema_version='b-chapter-workspace-trial/0.2',book_id='46007447',date='2026-10-20',
                content_hash=sha(canonical(payload)),payload=payload)

def audit_processing(view,inputs):
    errors=[]
    def require(condition,code):
        if not condition:raise ValueError(code)
    try:
        require(view['schema_version']=='b-chapter-workspace-trial/0.2'and view['book_id']=='46007447','WORKSPACE_SCHEMA')
        p=view['payload'];require(view['content_hash']==sha(canonical(p)),'WORKSPACE_HASH')
        parent=p['base_workspace'];rows,review,image=source_context(inputs,parent)
        require(p['base_workspace_hash']==parent['content_hash'],'BASE_WORKSPACE_BINDING')
        require(p['decision']=='HOLD'and not p['old_ledger_modified']and p['platform_actions']==[]and p['new_question_entities']==0,'NO_PROMOTION')
        candidates=p['answer_evidence_candidates'];require(len(candidates)==8 and [c['source_local_id']for c in candidates]==[r['source_local_id']for r in review['items']],'CANDIDATE_COVERAGE')
        originals={r['material_candidate_id']:r for r in inputs['identities']['payload']['material_candidates']}
        for candidate,item in zip(candidates,review['items']):
            name=candidate['source_local_id'];require(candidate['source']==item and (item['label'],item['printed_number'])==LABELS[name],'CURRENT_SOURCE_CONTENT')
            require(candidate['source_namespace']==originals[name]['candidate_namespace']and candidate['evidence_candidate_id']=='answer-evidence-'+sha(canonical([review['source_sha256'],name]))[:24],'SOURCE_LOCAL_IDENTITY')
            require(candidate['raw_rows']==[r for r in rows.values()if name in r['material_candidate_ids']],'RAW_ROWS_PRESERVED')
            require(candidate['question_id']is None and candidate['platform_question_id']is None and candidate['a_contract_id']is None and candidate['relation_status']=='NO_QUESTION_RELATION'and not candidate['human_verified']and not candidate['business_acceptance']and candidate['decision']=='HOLD'and candidate['status']=='ANSWER_EVIDENCE_READY_QUESTION_SOURCE_PENDING','NO_FAKE_QUESTION_OR_APPROVAL')
            require(candidate['question_source_status']=='NOT_LOCATED_IN_BOUNDED_LOCAL_SCAN'and candidate['source_sha256']==review['source_sha256']and candidate['source_asset_id']=='viewer-173'and candidate['evidence_grade']=='MODEL_VISUAL_PIXEL_SUPPLEMENT','CANDIDATE_PROVENANCE')
            check_region(item['region'],image)
            for cell in item['cells']:check_region(cell['region'],image)
            for formula in item['formula_occurrences']:
                check_region(formula['region'],image)
                for rid in formula['raw_support_row_ids']:
                    raw=rows[rid];a,b,c,d=raw['bbox'];x0,y0,x1,y1=formula['region']['bbox']
                    require(x0<=(a+c)/2<x1 and y0<=(b+d)/2<y1,'FORMULA_OCCURRENCE_RAW_SUPPORT')
        queue=p['current_source_queue'];old=parent['payload']['current_unassigned_work_queue']
        require([r['line_id']for r in queue]==[r['line_id']for r in old],'QUEUE_COVERAGE')
        for row,original in zip(queue,old):
            if row['line_id']not in rows:require(row==original,'EXISTING_READING_ROWS_UNCHANGED');continue
            raw=rows[row['line_id']]
            require(all(row[k]==v for k,v in original.items()if k!='current_status')and row['raw_row_snapshot']==raw,'QUEUE_RAW_PRESERVATION')
            require(row['current_status']=='ANSWER_EVIDENCE_READY_QUESTION_SOURCE_PENDING'and row['evidence_candidate_ids']==[c['evidence_candidate_id']for c in candidates if c['source_local_id']in raw['material_candidate_ids']],'QUEUE_EVIDENCE_BINDING')
        require(p['acceptance_queue']==acceptance_queue(parent),'CURRENT_ACCEPTANCE_SCOPES')
        require(p['local_source_search']==inputs['local_search']and p['input_pins']=={k:v[1]for k,v in PINS.items()},'SEARCH_AND_VERSION_BINDING')
        require(p['counts']==dict(legacy_unassigned_rows=19,reading_rows_with_assembled_drafts=5,rows_with_answer_evidence_only=14,rows_without_source_processing=0,new_answer_evidence_candidates=8,missing_question_identity_rows=14,acceptance_items=18,human_approved=0),'COUNT_MEANINGS')
        require(all(p['auxiliary_consistency'][k]is True for k in ('table_example1','table_example2','folding_example'))and p['auxiliary_consistency']['role']=='AUXILIARY_ALGEBRA_CHECK_NOT_TRANSCRIPTION_IDENTITY_OR_ACCEPTANCE','AUXILIARY_NOT_ACCEPTANCE')
    except (ValueError,KeyError,TypeError,IndexError)as exc:errors.append(str(exc))
    return dict(schema_version='b-remaining-source-audit/0.1',workspace_hash=view.get('content_hash'),source_and_structure_accepted=not errors,
                errors=errors,decision='HOLD',human_accepted=False,chapter_accepted=False,audit_calls_producer=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    inputs=load_inputs();parent=base.build_workspace(inputs);view=build_processing(inputs,parent);audit=audit_processing(view,inputs)
    need(audit['source_and_structure_accepted'],'REMAINING_SOURCE_AUDIT_FAILED')
    args.out.mkdir(parents=True,exist_ok=True)
    for name,value in [('workspace.json',view),('audit.json',audit),('acceptance-queue.json',view['payload']['acceptance_queue'])]:
        (args.out/name).write_bytes(encode(value))
    print(json.dumps(dict(counts=view['payload']['counts'],audit=audit),ensure_ascii=False))

if __name__=='__main__':main()
