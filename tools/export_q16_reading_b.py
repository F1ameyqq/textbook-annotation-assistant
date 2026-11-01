"""Freeze source-checked Q16/reading candidates into C01 HOLD; never plan or apply."""
from pathlib import Path
import argparse,copy,hashlib,io,json
from datetime import datetime,timezone
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
REVIEW_PATH='tests/fixtures/book46007447/q16-reading-current-review-20261021.json'
REVIEW_SHA='4dd4425140620ef37a289df29206c2f04734c082badd2c73b238851d8031cada'
A_COMMIT='edf125961be9cdc1642652c038d99872b1c8cdc7'
B_BASE='d48b066ad2620d7f1a2e902b2b28e3139390a721'
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
encode=lambda x:(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
ref=lambda a:{k:a[k] for k in ('artifact_id','revision','kind','content_hash')}

def need(value,code):
    if not value:raise ValueError(code)

def read_review(path):
    raw=Path(path).read_bytes().replace(b'\r\n',b'\n')
    need(sha(raw)==REVIEW_SHA,'REVIEW_FIXED_BYTES')
    return json.loads(raw)

def load_basis():
    from build_chapter_workspace_b import load_inputs,prepare,build_workspace,PINS,EXTRA,JSON_PINS
    inputs=load_inputs(); inventory,q16,base,check,reading,rcheck,plan,images=prepare(inputs)
    workspace=build_workspace(inputs)['payload']
    basis=dict(q16=q16,material=workspace['shared_materials'][0],answers=workspace['material_answer_drafts'],
               formulas=workspace['q16_formula_review'],source_rows=workspace['current_unassigned_work_queue'],
               original_unassigned=[r for r in workspace['legacy_answer_coverage'] if r['status']=='UNASSIGNED'],
               source_inventory=inventory,branch_refs=workspace['branch_refs'],
               input_pins={k:dict(path=v[0],sha256=v[1]) for k,v in {**PINS,**EXTRA,**JSON_PINS}.items()})
    return basis,{k:images[k] for k in ('viewer-13','viewer-15','viewer-173')}

def display(runs):
    return ''.join('____' if r['format']=='blank' else '\\('+r['text']+'\\)' if r['format']=='latex' else r['text'] for r in runs)

def seal(value):
    value=copy.deepcopy(value);value['content_hash']=sha(canonical({k:v for k,v in value.items() if k!='content_hash'}));return value

def build_delivery(basis,review,images,generation=None):
    need(not review['independent_human'] and not review['business_acceptance'] and review['decision']=='HOLD','NO_APPROVAL')
    q=review['q16'];m=review['reading'];original=basis['q16']
    need(q['question_id']==original['question_id'] and q['answer_id']==original['answer_id'],'STABLE_Q16')
    need(q['question_blocks']==original['question_snapshot']['blocks'] and q['answer_lines']==original['answer_snapshot']['content_fragments'],'UNCHANGED_Q16')
    need(q['task_map']==original['task_map'] and q['formula_slots']==basis['formulas'],'Q16_SLOT_MAPPING')
    need(m['material_id']==basis['material']['material_id'] and len(m['tasks'])==3,'MATERIAL_IDENTITY')
    for current,task,answer in zip(m['tasks'],basis['material']['tasks'],basis['answers']):
        need(current['task_id']==task['task_id'] and current['answer_id']==answer['answer_id'] and
             current['answer_regions']==answer['source_regions'] and current['blank_responses']==answer['blank_responses'],'READING_CURRENT_BINDING')
    if generation is None:
        generation=dict(created_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
            config_version='q16-reading-20261021.2',b_base_commit=B_BASE,a_consumer_commit=A_COMMIT,
            basis_sha256=sha(encode(basis)),current_review_sha256=sha(encode(review)))
    created=datetime.fromisoformat(generation['created_at'].replace('Z','+00:00'))
    need(created.tzinfo is not None and generation['config_version']=='q16-reading-20261021.2' and
         generation['b_base_commit']==B_BASE and generation['a_consumer_commit']==A_COMMIT and
         generation['basis_sha256']==sha(encode(basis)) and generation['current_review_sha256']==REVIEW_SHA,'GENERATION_CONTEXT')
    seed=sha(canonical(generation))[:24]
    blobs={'basis.json':encode(basis),'current-review.json':encode(review),'generation.json':encode(generation)}
    assets=[]
    for aid,raw in images.items():
        im=Image.open(io.BytesIO(raw));w,h=im.size;path='assets/'+aid+'.jpg';blobs[path]=raw
        assets.append(dict(asset_id=aid,path=path,sha256=sha(raw),media_type='image/jpeg',width=w,height=h,
                           source_label=aid+' / observed book 46007447',provenance='ORIGINAL'))
    by_asset={a['asset_id']:a for a in assets}
    policy=seal(dict(policy_id='b-q16-reading-unresolved',revision=1,confirmation_status='UNRESOLVED',option_grouping='UNRESOLVED',
        role_mapping=dict(stem='Q',option='W',answer='A',explanation='E',shared_material='Q'),
        source_notes=['Unapproved mapping proposal for these four candidates only; no Q1/Q4 authorization transfer.'],
        frame_save_status='UNVERIFIED',ocr_status='UNVERIFIED',applicability='PROPOSAL_ONLY'))
    pref={k:policy[k] for k in ('policy_id','revision','content_hash')}
    def artifact(kind,name,payload,deps):
        return seal(dict(schema_version='1.0.0-a-proposal',artifact_id=name+'-'+seed,revision=1,kind=kind,
            run_id='b-q16-reading-'+seed,book_id='46007447',scope_id='q16-reading-four-candidates',input_refs=[ref(a) for a in deps],
            producer=dict(module='b-source-projection',implementation_version='2',config_version=generation['config_version'],
                policy_versions=[pref],model_version=None,prompt_version=None,evidence_mode='OBSERVED'),
            created_at=generation['created_at'],payload=payload))
    ids=[q['question_id']]+[t['task_id'] for t in m['tasks']]
    source=artifact('SourceBundle','b-q16-reading-source',dict(assets=assets,
        directories=[dict(directory_id='chapter1-local',parent_id=None,label='第一章 勾股定理 / bounded Q16 and reading source windows')],
        pages_expected=list(images),pages_acquired=list(images),external_page_mappings=[dict(asset_id=a['asset_id'],directory_id='chapter1-local',
            external_page={'viewer-13':'viewer 13 / printed 5','viewer-15':'viewer 15 / printed 7','viewer-173':'viewer 173 / printed 25'}[a['asset_id']],
            mapping_status='UNCERTAIN',evidence_refs=['ev-current-review']) for a in assets],history=[],scope_manifest=ids,
        scope_manifest_basis='Exactly Q16 plus three stable local task IDs under one shared material; not a chapter or whole-page denominator. Reading tasks have no printed main question number.',metadata_page_count=None),[])
    regions=[];fragments=[];bindings=[];source_proofs=[]
    def add(block,role,owner,fragment=True):
        aid=block['asset_id'];box=list(map(int,block.get('bbox',block.get('bbox_xyxy',[]))));asset=by_asset[aid]
        im=Image.open(io.BytesIO(images[aid])).convert('RGB');crop=im.crop(box)
        expected=block.get('crop_rgb_sha256');need(expected is None or sha(crop.tobytes())==expected,'REGION_PIXELS')
        need(block.get('source_sha256')==asset['sha256'],'REGION_SOURCE')
        identity=block.get('block_id',block.get('segment_id'));rid='region-'+identity;fid='fragment-'+identity
        image_type=block.get('content_type')=='image' or (not block.get('runs') and identity.startswith('reading-figure'))
        ct='image' if image_type else 'formula' if block.get('content_type')=='formula' else 'text'
        text=None if image_type else display(block['runs'])
        # C01 parses original-image coordinates as floats before hashing.
        regions.append(dict(region_id=rid,box=dict(image={k:asset[k] for k in ('asset_id','width','height','sha256')},bbox=[float(v) for v in box]),
            crop_transform=dict(scale_x=1.0,scale_y=1.0,offset_x=float(-box[0]),offset_y=float(-box[1]),rotation_degrees=0.0,
                padding=[0.0]*4,processed_width=box[2]-box[0],processed_height=box[3]-box[1],invertible=True),
            content_type=ct,text=text,source='HISTORICAL',evidence_refs=['ev-current-review','ev-basis'],printed_number_candidates=[],certainty='UNCERTAIN'))
        path='crops/'+identity+'.png';buf=io.BytesIO();crop.save(buf,format='PNG');blobs[path]=buf.getvalue()
        source_proofs.append(dict(region_id=rid,path=path,sha256=sha(buf.getvalue()),rgb_sha256=sha(crop.tobytes())))
        bindings.append(dict(block_id=identity,owner_id=owner,region_id=rid,fragment_id=fid if fragment else None,
                             runs=copy.deepcopy(block.get('runs',[])),role=role))
        if fragment:fragments.append(dict(fragment_id=fid,region_ids=[rid],role=role,content_type=ct,reading_order=len(fragments)))
        return fid
    qfrags=[add(dict(b,asset_id='viewer-15'),'stem',q['question_id']) for b in q['question_blocks']]
    afrags=[add(dict(b,source_sha256=by_asset['viewer-173']['sha256']),'answer',q['question_id']) for b in q['answer_lines']]
    shared=[add(b,'shared_material',m['material_id']) for b in m['material_blocks']]
    questions=[dict(question_id=q['question_id'],directory_id='chapter1-local',question_type='free_response',fragment_ids=qfrags,
        parent_question_id=None,shared_fragment_ids=[],cross_page=False,external_refs=dict(printed_number='16',platform_question_id=None,platform_order=None))]
    relations=[dict(relation_id='relation-q16',question_id=q['question_id'],candidate_fragment_ids=afrags,selected_fragment_ids=[],
                    status='UNRESOLVED',evidence_refs=['ev-current-review'])]
    for n,t in enumerate(m['tasks'],1):
        taskfrags=[add(b,'stem',t['task_id']) for b in t['question_blocks']]
        answerfrags=[add(dict(b,block_id=b['segment_id']),'answer',t['task_id']) for b in t['answer_regions']]
        questions.append(dict(question_id=t['task_id'],directory_id='chapter1-local',question_type='free_response',fragment_ids=taskfrags,
            parent_question_id=None,shared_fragment_ids=shared,cross_page=False,
            external_refs=dict(printed_number=None,platform_question_id=None,platform_order=None)))
        relations.append(dict(relation_id='relation-reading-'+str(n),question_id=t['task_id'],candidate_fragment_ids=answerfrags,
                              selected_fragment_ids=[],status='UNRESOLVED',evidence_refs=['ev-current-review']))
    for slot in q['formula_slots']:
        add(dict(block_id='q16-'+slot['slot'],asset_id='viewer-173',bbox=slot['source_bbox'],source_sha256=by_asset['viewer-173']['sha256'],
            crop_rgb_sha256=slot['crop_rgb_sha256'],content_type='formula',runs=[dict(format='latex',text=slot['expected_latex'])]),'answer',q['question_id'],fragment=False)
    clues=[dict(clue_id='clue-'+str(i),box=r['box'],source='SHARED_RECOGNITION',disposition='ASSIGNED',region_ids=[r['region_id']],
        reason='Bounded source observation window, not an independent whole-page coverage scan.',evidence_refs=['ev-current-review']) for i,r in enumerate(regions)]
    evidence=artifact('EvidenceBundle','b-q16-reading-evidence',dict(source=ref(source),regions=regions,coverage_clues=clues),[source])
    graph=artifact('QuestionGraph','b-q16-reading-graph',dict(source=ref(source),evidence=ref(evidence),questions=questions,fragments=fragments,
        answer_relations=relations,identity_notes='Stable B Q16 and material task identities only. HISTORICAL regions are projections of frozen model transcriptions, not HUMAN/OCR claims. Formula diagnostic regions are not duplicate answer fragments. No platform frame policy or selection.'),[source,evidence])
    issues=[dict(issue_id='hold-'+code,code=code,scope_type='scope',scope_id=graph['scope_id'],evidence_refs=['ev-current-review'],severity='blocking',
        blocks=['PLAN','APPLY','COMPLETE'],suggested_strategy=dict(strategy_id='HUMAN_REVIEW',max_attempts=0,max_cost=0.0),reason=reason) for code,reason in [
        ('ANSWER_AMBIGUOUS','Source-matched candidates are not independently human accepted or selected.'),
        ('POLICY_UNRESOLVED','Q16 formula and shared-material grouping/frame policy remains an unapproved proposal.'),
        ('SOURCE_MISSING','Chapter inventory and denominator are unknown; only bounded source windows supplied.')]]
    check=artifact('CheckReport','b-q16-reading-precheck',dict(stage='PRE_APPLY',subject=ref(graph),graph=ref(graph),policy=pref,snapshot=None,receipt=None,
        coverage=dict(scope_id=graph['scope_id'],pages_expected=list(images),pages_checked=[],clue_ids=[c['clue_id'] for c in clues],unassigned_region_ids=[]),
        checks=[dict(check_id=name,outcome=outcome,evidence_refs=['ev-current-review','ev-basis'],reason=reason) for name,outcome,reason in [
            ('source_integrity','PASS','Exact original bytes and bound crop pixels checked by B.'),('structure','PASS','Four local question/task identities, explicit source coordinates and three null reading blanks.'),
            ('answer_matching','UNAVAILABLE','Four candidates retained UNRESOLVED; model content recheck is not independent human acceptance.'),
            ('coverage','UNAVAILABLE','No whole-page or chapter coverage assertion.'),('policy','UNAVAILABLE','Unapproved grouping and precise frame policy for these cases.')]],
        issues=issues,decision='HOLD',reason='Read-only consumable C01 projection; no execution, independent human acceptance, or chapter completion.'),[source,evidence,graph])
    ev=[dict(evidence_id='ev-'+key,resource=dict(path=path,sha256=sha(blobs[path]),media_type='application/json'),
             description=description,mode='OBSERVED') for key,path,description in [
        ('current-review','current-review.json','Fresh model source recheck, not independent human gold or business approval.'),
        ('basis','basis.json','Frozen previous B current objects and provenance; historical parent ZIP containers are not replayed here.')]]
    bundle=dict(format_version='c01-exchange-1',evidence=ev,policies=[policy],artifacts=[source,evidence,graph,check])
    sidecar=dict(schema_version='b-q16-reading-delivery/0.1',book_id='46007447',b_base_commit=B_BASE,a_consumer_commit=A_COMMIT,
        current_review_sha256=REVIEW_SHA,basis_sha256=sha(blobs['basis.json']),c01_graph_ref=ref(graph),decision='HOLD',
        generation_sha256=sha(blobs['generation.json']),
        bindings=bindings,source_proofs=source_proofs,q16_task_map=q['task_map'],q16_formula_slots=q['formula_slots'],
        reading_task_answers=[dict(task_id=t['task_id'],answer_id=t['answer_id'],blank_responses=t['blank_responses']) for t in m['tasks']],
        model_checks=review['checks'],independent_human_pending=18,human_verified=False,business_acceptance=False,
        source_windows_are_platform_frames=False,platform_actions=[],native_graphs_or_ledger_modified=False,chapter_denominator=None,
        limitations=review['limitations'])
    subjects=[('Q16-MAPPING',dict(task_map=q['task_map'],question_id=q['question_id'],answer_id=q['answer_id']),
               'Confirm stable section identity and three exact answer spans; retain null question blanks.')]
    subjects.extend(('Q16-'+s['slot'],s,'Read numerator/bar/denominator and raised powers from this exact occurrence; do not copy an equal neighbouring formula.') for s in q['formula_slots'])
    subjects.extend([('Q16-PERIPHERAL',q['answer_lines'],'Read causal signs, external brackets/squares, odd integer condition, 60 and 61, punctuation and order.'),
                     ('Q16-REGIONS',dict(question=q['question_blocks'],answer=q['answer_lines']),'Review source-window bounds and editorial A; separately approve any precise platform frames.'),
                     ('READING-IDENTITY',m['material_blocks'],'Confirm shared title/body/figures 1 and 2, no printed main question number, and three local task identities.')])
    subjects.extend(('READING-TASK'+str(n),t,'Read full task and answer, formula/blank order, logical column flow and whole figure. Row 108 is split at x=228; row 104 and 112 remain partial evidence.') for n,t in enumerate(m['tasks'],1))
    pending=dict(schema_version='b-q16-reading-independent-review/0.1',c01_graph_ref=ref(graph),current_review_sha256=REVIEW_SHA,
        model_source_reviewed_count=18,pending_independent_human_count=18,approved_count=0,
        items=[dict(issue_id=identity,subject=subject,subject_sha256=sha(canonical(subject)),required_action=action,
            model_disposition='SOURCE_CHECKED_CURRENT_CONTENT',human_reviewer=None,human_disposition=None,human_evidence_sha256=None)
            for identity,subject,action in subjects],decision='HOLD')
    blobs['pending-review.json']=encode(pending);sidecar['pending_review_sha256']=sha(blobs['pending-review.json'])
    blobs['bundle.json']=encode(bundle);blobs['delivery.json']=encode(sidecar)
    return blobs

def write_delivery(out,blobs):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for name,raw in blobs.items():
        path=out/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--frozen',type=Path,help='Portable frozen basis/current-review/assets; no historical producer imports')
    args=p.parse_args()
    if args.frozen:
        basis=json.loads((args.frozen/'basis.json').read_bytes());review=read_review(args.frozen/'current-review.json')
        generation=json.loads((args.frozen/'generation.json').read_bytes())
        images={k:(args.frozen/'assets'/(k+'.jpg')).read_bytes() for k in ('viewer-13','viewer-15','viewer-173')}
    else:basis,images=load_basis();review=read_review(ROOT/REVIEW_PATH);generation=None
    blobs=build_delivery(basis,review,images,generation);write_delivery(args.out,blobs)
    print(json.dumps(dict(files=len(blobs),bundle_sha256=sha(blobs['bundle.json']),decision='HOLD')))

if __name__=='__main__':main()
