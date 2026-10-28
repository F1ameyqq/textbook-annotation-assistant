"""Pure Q7 phase-2 finalization. No network, files, credentials or sender.

Requires a successful re-evaluation of the actual copy-first receipt/readback and
an explicit outer-process acceptance record. Keeps all native unknown fields.
Only four old Q7 frames, three new choice frames, two retired variant frames,
three Q7 OCR zones and Q7 tishi have planned changes. No automatic retry.
"""
from __future__ import annotations
import copy
from datetime import datetime, timedelta, timezone
import re
import uuid
from . import insertion as i
from . import update as u

BOOK=i.BOOK
DIRECTORY=i.DIRECTORY
SCHEMA='UsenseQ7FinalizePlan/v1'
MAIN_KEYS=('main-stem','main-figure','main-choice-A','main-choice-B','main-choice-C','main-choice-D','main-answer')
REUSED={'main-stem':'6a1e82cf-d5c8-485d-b2da-7a626a899045',
        'main-figure':'ace0132c-46d4-402e-ba53-aa8fc99d7484',
        'main-choice-A':'0eed066a-354d-4d6a-9a6d-c9e54c0c8b5f',
        'main-answer':'e219b027-3b59-4834-8447-dd03c7273a9f'}
RETIRE=('74ec414b-e400-4477-b652-af4c49ed48eb','9ade4dc7-7ea2-42ad-b991-26bf96a7795b')
LAYOUT=(('question',0,'text'),('question',1,'image'),('choice',0,'text'),('choice',1,'text'),
        ('choice',2,'text'),('choice',3,'text'),('answer',0,'text'))
OUTER_FLAGS=('writer_exit_observed','reader_exits_observed','writer_release_confirmed',
             'reader_release_confirmed','all_reads_after_write','ledger_intent_verified',
             'raw_capture_hashes_verified')
EVIDENCE_ROLES=('writer_execution','raw_receipt','comparison','writer_host_release',
                'reader_host_release','ledger_intent','full_capture_index')
require=u.require


def _predecessor(before, predecessor):
    base_keys={'phase1_plan','phase1_receipt','phase1_comparison','runtime_actor_hashes','outer_acceptance','artifact_refs'}
    require(type(predecessor) is dict and set(predecessor) in (base_keys,base_keys|{'observed_resolution'}),
        'EXACT_PHASE1_PREDECESSOR_REQUIRED')
    artifacts=predecessor['artifact_refs']
    require(type(artifacts) is dict and set(artifacts)=={'plan','receipt','comparison','outer_acceptance'},
        'FOUR_PHASE1_ARTIFACT_REFS_REQUIRED')
    for role,ref in artifacts.items():
        require(type(ref) is dict and set(ref)=={'path','sha256'} and u._id(ref['path']) and i._hash(ref['sha256']),
            'PHASE1_ARTIFACT_RAW_HASH_REQUIRED',role)
    pp,receipt=predecessor['phase1_plan'],predecessor['phase1_receipt']
    result=i.compare_insert_readback(pp,before,receipt,
        runtime_actor_hashes=predecessor['runtime_actor_hashes'])
    require(u.json_same(result,predecessor['phase1_comparison']), 'PHASE1_COMPARISON_CHANGED')
    outer=predecessor['outer_acceptance']
    require(type(outer) is dict and outer.get('schema')=='Q7Phase1OuterAcceptance/v1', 'PHASE1_OUTER_ACCEPTANCE_REQUIRED')
    resolved='observed_resolution' in predecessor
    if resolved:
        require(result.get('ok') is False and result.get('status')=='HOLD' and
            result.get('old_q7_preserved') is True and bool(result.get('differences')),
            'ORIGINAL_STRICT_HOLD_MUST_BE_PRESERVED')
        require(outer.get('status')=='RESOLVED_UNKNOWN_COPY_FIRST_WITH_EXTERNAL_RELEASE' and
            outer.get('writer_status')=='UNKNOWN_DO_NOT_RETRY' and outer.get('phase2_only') is True and
            outer.get('phase1_retry_allowed') is False, 'EXPLICIT_RESOLVED_UNKNOWN_OUTER_REQUIRED')
        bundle=predecessor['observed_resolution']
        require(type(bundle) is dict and set(bundle)=={'resolution','execution_evidence','audit_manifest','artifact_refs'},
            'EXACT_OBSERVED_RESOLUTION_BUNDLE_REQUIRED')
        refs=bundle['artifact_refs']
        require(type(refs) is dict and set(refs)=={'resolution','execution_evidence','audit_manifest'},
            'THREE_ORIGINAL_RESOLUTION_REFS_REQUIRED')
        for role,ref in refs.items():
            require(type(ref) is dict and set(ref)=={'path','sha256'} and u._id(ref['path']) and i._hash(ref['sha256']),
                'RESOLUTION_ORIGINAL_RAW_HASH_REQUIRED',role)
        require(u.json_same(outer.get('observed_resolution_refs'),refs),'OUTER_RESOLUTION_REFS_NOT_BOUND')
        evidence=bundle['execution_evidence']
        require(evidence.get('native_receipt_raw_sha256')==artifacts['receipt']['sha256'],
            'RESOLUTION_RAW_RECEIPT_NOT_BOUND')
        require(u.json_same(evidence.get('writer_process',{}).get('result',{}).get('runtime_actor_hashes'),
            predecessor['runtime_actor_hashes']), 'RESOLUTION_RUNTIME_ACTOR_CHANGED')
        # This separate observed-contract resolver does not alter the original
        # UNKNOWN execution or the strict HOLD comparison above.
        from . import insertion_resolution as ir
        checked=ir.resolve_observed_insert(pp,before,receipt,evidence)
        require(checked.get('ok') is True and checked.get('status')==
            'RESOLVED_UNKNOWN_COPY_FIRST_WITH_INDEPENDENT_FULL_READBACK' and
            u.json_same(checked,bundle['resolution']), 'UNKNOWN_RESOLUTION_NOT_REPRODUCIBLE')
        require(checked.get('original_strict_comparison_sha256')==u.digest(result) and
            checked.get('execution_evidence_sha256')==u.digest(evidence) and
            u.json_same(checked.get('new_identity'),result['new_identity']), 'RESOLUTION_STRICT_EVIDENCE_BINDING')
    else:
        require(result.get('ok') is True and result.get('status')=='ACCEPTED_COPY_FIRST_INSERT_PRESERVATION'
            and result.get('old_q7_preserved') is True and result.get('differences')==[],
            'PHASE1_UNKNOWN_OR_NOT_INDEPENDENTLY_PRESERVED')
        require(outer.get('status')=='ACCEPTED_COPY_FIRST_WITH_EXTERNAL_RELEASE' and
            outer.get('writer_status')=='INSERT_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK',
            'UNKNOWN_PREDECESSOR_FORBIDDEN')
    require(all(outer.get(flag) is True for flag in OUTER_FLAGS), 'PHASE1_OUTER_PROOF_INCOMPLETE')
    require(type(outer.get('writer_exit_code')) is int and outer['writer_exit_code']==(2 if resolved else 0) and
        type(outer.get('reader_exit_codes')) is list and bool(outer['reader_exit_codes']) and
        all(type(code) is int and code==0 for code in outer['reader_exit_codes']), 'PHASE1_PROCESS_EXIT_NOT_PROVEN')
    require(type(outer.get('post_attempts')) is int and outer['post_attempts']==1 and
        u.json_same(outer.get('post_layers'),{'context':1,'native':1}) and
        type(outer.get('reader_writes')) is int and outer['reader_writes']==0, 'PHASE1_SINGLE_POST_OR_READ_ONLY_UNPROVEN')
    runs=outer.get('reader_run_ids')
    require(u._id(outer.get('writer_run_id')) and type(runs) is list and bool(runs) and
        all(u._id(r) for r in runs) and len(runs)==len(set(runs)) and
        outer['writer_run_id'] not in runs and len(runs)==len(outer['reader_exit_codes']),
        'PHASE1_INDEPENDENT_CONTEXT_UNPROVEN')
    for key,value in [('phase1_plan_sha256',pp['plan_sha256']),('phase1_receipt_sha256',result['receipt_sha256']),
                      ('after_sha256',result['after_sha256']),('ledger_key',pp['ledger_key'])]:
        require(outer.get(key)==value, 'PHASE1_OUTER_BINDING_MISMATCH',key)
    refs=outer.get('evidence_refs')
    require(type(refs) is dict and set(refs)==set(EVIDENCE_ROLES), 'PHASE1_RAW_EVIDENCE_ROLES_REQUIRED')
    for role,ref in refs.items():
        require(type(ref) is dict and set(ref)=={'path','sha256'} and u._id(ref['path']) and i._hash(ref['sha256']),
            'PHASE1_RAW_EVIDENCE_REFERENCE_REQUIRED',role)
    require(u.json_same(refs['raw_receipt'],artifacts['receipt']) and
        u.json_same(refs['comparison'],artifacts['comparison']), 'PHASE1_RAW_REFERENCE_BINDING')
    return result


def _candidate_payload(before, approved):
    require(type(approved) is dict, 'APPROVED_MAIN_CONTENT_REQUIRED')
    for name in ('candidate','review','crop_evidence'):
        require(u._id(approved.get(name+'_ref')) and i._hash(approved.get(name+'_sha256')),
            'MAIN_EVIDENCE_REFERENCE_REQUIRED',name)
    sources=approved.get('source_evidence')
    require(type(sources) is list and len(sources)==2 and all(type(s) is dict and
        set(s)=={'path','sha256'} and u._id(s['path']) and i._hash(s['sha256']) for s in sources)
        and len({s['path'] for s in sources})==2, 'TWO_CURRENT_SOURCE_REFS_REQUIRED')
    source_map={s['path']:s['sha256'] for s in sources}
    c=approved.get('candidate')
    require(type(c) is dict and c.get('schema')=='Q7FinalSevenFrameContentCandidate/v1' and
        c.get('logical_owner')=='main' and c.get('book_id')==BOOK and
        c.get('target_directory_id')==DIRECTORY, 'MAIN_SOURCE_CANDIDATE_REQUIRED')
    require(u.json_same(c.get('target'),{'node_id':i.OLD_Q7_NODE,'info_id':i.OLD_Q7_INFO,'question_order':7}),
        'MAIN_IDENTITY_MISMATCH')
    require(c.get('root_review_status')=='PASS_SOURCE_CONTENT_AND_BOUNDARIES' and
        c.get('root_review_ref')==approved['review_ref'], 'ROOT_SOURCE_REVIEW_REQUIRED')
    frames=c.get('planned_frames')
    require(type(frames) is list and [f.get('key') for f in frames]==list(MAIN_KEYS) and
        u.json_same(c.get('frames'),frames), 'MAIN_EXACT_SEVEN_FRAME_LAYOUT')
    old={f['rect_id']:f for f in before['frames']['data']}
    main_old={f['rect_id']:f for f in before['q7_annotations']['data']}
    require(set(main_old)==set(REUSED.values())|set(RETIRE), 'ORIGINAL_Q7_SIX_FRAMES_NOT_PRESERVED')
    ids,rows=set(),[]
    for f,layout in zip(frames,LAYOUT):
        key,rect=f['key'],f.get('planned_rect_id')
        require(type(rect) is str, 'FRAME_UUID_REQUIRED')
        try: valid_uuid=str(uuid.UUID(rect))==rect
        except ValueError: valid_uuid=False
        require(valid_uuid and rect not in ids, 'FRAME_UUID_INVALID_OR_DUPLICATE')
        ids.add(rect)
        require((rect==REUSED[key]) if key in REUSED else (rect not in old), 'REUSE_OR_FRESH_FRAME_ID_VIOLATION')
        require(u.json_same([f.get('zone'),f.get('image_order_in_annotation_zone'),f.get('content_type')],list(layout)),
            'FRAME_LAYOUT_MISMATCH')
        bbox,dims=f.get('bbox'),f.get('source_dimensions')
        require(type(bbox) is list and len(bbox)==4 and all(type(v) is int for v in bbox) and
            type(dims) is list and len(dims)==2 and all(type(v) is int for v in dims) and
            0<=bbox[0]<bbox[2]<=dims[0] and 0<=bbox[1]<bbox[3]<=dims[1], 'CURRENT_FULL_SOURCE_BOUNDS')
        require(f.get('rect_bbox')==','.join(map(str,bbox)), 'FRAME_BBOX_SERIALIZATION')
        page=173 if layout[0]=='answer' else 10
        require(type(f.get('viewer_page')) is int and f['viewer_page']==page and
            type(f.get('page_index')) is int and f['page_index']==page, 'FRAME_PAGE_MISMATCH')
        x1,y1,x2,y2=bbox
        url=f'https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com/upload_images/{BOOK}/{BOOK}_page_{page-1}.jpg?x-oss-process=image/crop,x_{x1},y_{y1},w_{x2-x1},h_{y2-y1}'
        require(f.get('image_path')==f.get('hosted_image_url')==url, 'EXACT_VERIFIED_CROP_URL_REQUIRED')
        src,crop,fetch=f.get('source',{}),f.get('crop',{}),f.get('fetch_evidence',{})
        require(source_map.get(src.get('path'))==src.get('sha256')==f.get('source_sha256') and
            i._hash(src.get('sha256')), 'SOURCE_HASH_BINDING')
        require(fetch.get('status')=='FETCHED_CROP' and type(fetch.get('http_status')) is int and
            fetch['http_status']==200 and fetch.get('url')==url and u.json_same(fetch.get('bbox'),bbox) and
            u.json_same(fetch.get('dimensions'),[x2-x1,y2-y1]) and fetch.get('source_sha256')==src['sha256'] and
            fetch.get('sha256')==crop.get('sha256')==f.get('crop_sha256') and i._hash(crop.get('sha256')),
            'MAIN_FETCHED_CROP_EVIDENCE_MISMATCH')
        rows.append({'rect_id':rect,'type':layout[0],'belong_to_level':'question_level','order_in_level':'7',
            'image_order_in_annotation_zone':layout[1],'rect_bbox':f['rect_bbox'],'page_index':page,
            'image_path':url,'parent_rect_id':None,'directory_id':DIRECTORY,'content_type':layout[2],
            'user_id':main_old[rect]['user_id'] if rect in main_old else None,
            'is_pre_annotation':False,'pre_annotations_id':None})
    zones=c.get('zone_values')
    require(type(zones) is dict and set(zones)=={'question','choice','answer'} and all(type(t) is str and t.strip()
        and c.get('zone_text_sha256',{}).get(z)==u.text_digest(t) for z,t in zones.items()), 'MAIN_REVIEWED_TEXT_REQUIRED')
    require(zones['answer']=='C' and [r[:2] for r in zones['choice'].splitlines()]==['A.','B.','C.','D.'] and
        '【变式】' not in zones['question']+zones['choice'], 'MAIN_SINGLE_CHOICE_ONLY')
    require(u.image_references(zones['question'])=={frames[1]['image_path']:1}, 'MAIN_EXACT_ONE_DIAGRAM')
    info=before['q7_info']['data']
    require(info['tishi']=='duoxuan', 'MAIN_TYPE_ALREADY_CHANGED_OR_UNKNOWN')
    return {'file_id':BOOK,'target_directory_id':DIRECTORY,'question_order':7,'is_new_question_insertion':False,
        'insert_after_order':None,'annotations_upsert':rows,'annotations_delete_rect_ids':list(RETIRE),
        'ocr_submissions':[{'zone':z,'ocr_result':zones[z],'rect_ids':[r['rect_id'] for r in rows if r['type']==z],
                            'question_order':7} for z in ('question','choice','answer')],
        'ocr_delete_zones':[],'question_info':{'tishi':'xuanze','tilei':info['tilei'],'tihao':info['tihao']},'created_by':None}


def _expected(before,payload,actor_hashes):
    expected=copy.deepcopy(before)
    old={r['rect_id']:r for r in before['frames']['data']}
    new_ids=[];changed={}
    for patch in payload['annotations_upsert']:
        rect=patch['rect_id']
        if rect in old:
            row=copy.deepcopy(old[rect])
            for key,value in patch.items():
                if key!='user_id':row[key]=copy.deepcopy(value)
        else:
            new_ids.append(rect);row={}
            for key in i.ROW_KEYS:
                if key in patch: row[key]=copy.deepcopy(patch[key])
                elif key=='file_id':row[key]=BOOK
                elif key=='verified':row[key]=0
                else:row[key]={'$runtime_metadata':key}
        changed[rect]=row
    require(len(new_ids)==3, 'THREE_NEW_MAIN_CHOICES_REQUIRED')
    rows=[changed.get(r['rect_id'],copy.deepcopy(r)) for r in before['frames']['data'] if r['rect_id'] not in RETIRE]
    rows += [changed[rect] for rect in new_ids]
    # This is the observed original API ordering; never sort actual readback.
    require([r['rect_id'] for r in before['frames']['data']]==sorted(old), 'OBSERVED_GLOBAL_FRAME_ORDER_CHANGED')
    rows.sort(key=lambda r:r['rect_id'])
    expected['frames']['data']=rows
    expected['q7_annotations']['data']=[copy.deepcopy(r) for r in rows if r['rect_id'] in changed]
    expected['q7_info']['data']['tishi']='xuanze'
    for sub in payload['ocr_submissions']:
        response=expected['q7_'+sub['zone']]
        state,_=u._zone_state(response)
        if state=='present':
            response['data']['rect_ids']=copy.deepcopy(sub['rect_ids'])
            response['data']['ocr_result']=sub['ocr_result']
        else:
            require(u.json_same(response['data'],u.ABSENT), 'UNKNOWN_ABSENT_ZONE_FIELDS_CANNOT_BE_DROPPED')
            response['data']={'rect_ids':copy.deepcopy(sub['rect_ids']),'ocr_result':sub['ocr_result'],'success':True}
    return expected,new_ids


def make_finalize_plan(before_full,approved_main_content,predecessor):
    before=i.load_full_capture(before_full,count=23)
    prior=_predecessor(before,predecessor)
    require(len(before['frames']['data'])==75, 'EXACT_PHASE1_75_FRAME_BASELINE_REQUIRED')
    identities=i._validate_full(before,23)
    require(identities[6]['node_id']==i.OLD_Q7_NODE and identities[6]['info_id']==i.OLD_Q7_INFO and
        u.json_same(identities[7],prior['new_identity']), 'PHASE1_REAL_STABLE_IDENTITIES_CHANGED')
    payload=_candidate_payload(before,approved_main_content)
    expected,new_ids=_expected(before,payload,predecessor['runtime_actor_hashes'])
    plan={'schema':SCHEMA,'operation':'Q7_FINALIZE_ORIGINAL_MAIN_AFTER_ACCEPTED_COPY',
        'book_id':BOOK,'before_count':23,'after_count':23,'target':identities[6],
        'protected_variant_identity':copy.deepcopy(prior['new_identity']),
        'before_full':before,'before_sha256':i.flat_digest(before),
        'approved_main_content':copy.deepcopy(approved_main_content),'predecessor':copy.deepcopy(predecessor),
        'payload_candidate':payload,'expected_template':expected,
        'new_main_rect_ids':new_ids,'reused_main_rect_ids':list(REUSED.values()),'retired_rect_ids':list(RETIRE),
        'expected_frame_count':76,'ledger_key':'book-46007447-node-1792066417325-info-2110705653289365506-finalize-main-after-copy-first',
        'timestamp_policy':{'unchanged_everywhere_except':['q7_info.data.updated_at','four reused Q7 frames.updated_at'],
            'updated_old_rows':'Unchanged or same-format strictly later, and inside proved write clock window.',
            'new_rows':'Exactly three choice rows, observed schema, created_at==updated_at inside proved write window.',
            'new_info_created':False,'other_22_questions_metadata_immutable':True},
        'write_authorized_by_this_module':False,'automatic_retry_allowed':False,'automatic_compensation':False}
    plan['plan_sha256']=u.digest(plan)
    return plan


def validate_finalize_plan(plan):
    require(type(plan) is dict and plan.get('schema')==SCHEMA,'FINALIZE_PLAN_SCHEMA')
    rebuilt=make_finalize_plan(plan.get('before_full'),plan.get('approved_main_content'),plan.get('predecessor'))
    require(u.json_same(rebuilt,plan),'FINALIZE_PLAN_TAMPERED')
    return {'ok':True,'status':'VALID_Q7_FINALIZE_PLAN','plan_sha256':plan['plan_sha256']}


def check_prewrite(plan,fresh):
    validate_finalize_plan(plan)
    i.load_full_capture(fresh,count=23)
    require(set(fresh)==set(plan['before_full']) and all(u.json_same(fresh[k],plan['before_full'][k]) for k in fresh),
        'FINALIZE_PREWRITE_CHANGED')
    return {'ok':True,'status':'EXACT_ALL23_PREWRITE_MATCH','before_sha256':i.flat_digest(fresh)}


def decode_receipt(plan,raw_receipt):
    validate_finalize_plan(plan)
    require(type(raw_receipt) is dict and set(raw_receipt)=={'code','message','data'},'FINALIZE_RECEIPT_ENVELOPE_UNKNOWN')
    data=u._response(raw_receipt,code=(0,))
    require(type(data) is dict and set(data)=={'inserted','question_order','inserted_question_node','success','append_at_global_end'},
        'FINALIZE_RECEIPT_DATA_UNKNOWN')
    require(data['inserted'] is False and data['success'] is True and data['inserted_question_node'] is None and
        data['append_at_global_end'] is False and type(data['question_order']) is int and data['question_order']==7,
        'FINALIZE_RECEIPT_FLAGS_OR_TARGET')
    return {'ok':True,'status':'VALID_FINALIZE_RECEIPT','question_order':7,'receipt_sha256':u.digest(raw_receipt)}


def _clock(write_clock):
    require(type(write_clock) is dict and set(write_clock)=={'send_intent_at','finished_at','database_utc_offset_minutes','tolerance_seconds'},
        'PROVED_WRITE_CLOCK_REQUIRED')
    require(type(write_clock['database_utc_offset_minutes']) is int and write_clock['database_utc_offset_minutes']==480 and
        type(write_clock['tolerance_seconds']) is int and 0<=write_clock['tolerance_seconds']<=5,'OBSERVED_CLOCK_OFFSET_OR_TOLERANCE')
    start,end=(datetime.fromisoformat(write_clock[k]) for k in ('send_intent_at','finished_at'))
    require(start.tzinfo is not None and end.tzinfo is not None and start<=end and (end-start).total_seconds()<=600,
        'INVALID_WRITE_CLOCK_INTERVAL')
    tol=timedelta(seconds=write_clock['tolerance_seconds'])
    return start-tol,end+tol,timezone(timedelta(minutes=480))


def _timestamp(value,window):
    require(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?',value),
        'OBSERVED_DATABASE_TIMESTAMP_FORMAT')
    parsed=datetime.fromisoformat(value).replace(tzinfo=window[2])
    require(window[0]<=parsed<=window[1],'TIMESTAMP_OUTSIDE_ACTUAL_WRITE_WINDOW')
    return parsed


def compare_finalize_readback(plan,after,receipt,*,runtime_actor_hashes=None,write_clock=None):
    """Strict native comparison. Pure PASS is not a claim of outer live acceptance."""
    validate_finalize_plan(plan)
    errors=[];metadata=[]
    try:
        decoded=decode_receipt(plan,receipt)
        i.load_full_capture(after,count=23)
        require(u.json_same(runtime_actor_hashes,plan['predecessor']['runtime_actor_hashes']), 'PHASE2_ACTOR_CHANGED')
        window=_clock(write_clock)
        expected=copy.deepcopy(plan['expected_template'])
        before=plan['before_full']
        actual_by_id={r['rect_id']:r for r in after['frames']['data']}
        expected_by_id={r['rect_id']:r for r in expected['frames']['data']}
        require(len(after['frames']['data'])==76 and set(actual_by_id)==set(expected_by_id), 'FINALIZE_EXACT_FRAME_IDENTITIES')
        def updated(old,new,path):
            if u.json_same(old,new):return new
            require(type(old) is str and type(new) is str and re.sub(r'\d','#',old)==re.sub(r'\d','#',new),
                'CHANGED_OLD_TIMESTAMP_FORMAT',path)
            require(datetime.fromisoformat(new)>datetime.fromisoformat(old),'OLD_TIMESTAMP_NOT_STRICTLY_LATER',path)
            _timestamp(new,window)
            metadata.append({'path':path,'before':old,'after':new})
            return new
        expected['q7_info']['data']['updated_at']=updated(before['q7_info']['data']['updated_at'],
            after['q7_info']['data']['updated_at'],'q7_info.data.updated_at')
        for rect in plan['reused_main_rect_ids']:
            expected_by_id[rect]['updated_at']=updated(expected_by_id[rect]['updated_at'],
                actual_by_id[rect]['updated_at'],'frames.'+rect+'.updated_at')
        for rect in plan['new_main_rect_ids']:
            actual=actual_by_id[rect];row=expected_by_id[rect]
            require(tuple(actual)==i.ROW_KEYS,'UNKNOWN_NEW_CHOICE_FRAME_SCHEMA')
            require(actual.get('created_at')==actual.get('updated_at'),'NEW_CHOICE_TIMESTAMP_PAIR')
            _timestamp(actual['created_at'],window)
            require(type(actual.get('user_id')) is str and u.text_digest(actual['user_id'])==runtime_actor_hashes['runtime_user_id_sha256'],
                'NEW_MAIN_CHOICE_ACTOR_HASH_MISMATCH')
            for key in ('created_at','updated_at','user_id'):row[key]=actual[key]
        expected['q7_annotations']['data']=[copy.deepcopy(r) for r in expected['frames']['data']
            if r['rect_id'] in set(plan['reused_main_rect_ids'])|set(plan['new_main_rect_ids'])]
        # Flat orchestration key insertion order is not native; every response
        # key/array/type/unknown field remains strict. Actual arrays are not sorted.
        for key in sorted(expected):
            if not u.json_same(expected[key],after[key]):
                errors.extend({'path':[key]+d['path'],'reason':d.get('kind','NATIVE_VALUE_CHANGED')}
                    for d in u.differences(expected[key],after[key]))
    except (ValueError,KeyError,TypeError) as exc:
        errors.append({'path':['validation'],'reason':str(exc)})
        decoded=None
    ok=not errors
    return {'schema':'UsenseQ7FinalizeReadback/v1','ok':ok,'status':'ACCEPTED_Q7_FINALIZE_PRESERVATION' if ok else 'HOLD',
        'plan_sha256':plan['plan_sha256'],'before_sha256':plan['before_sha256'],
        'after_sha256':i.flat_digest(after) if type(after) is dict else None,
        'receipt_sha256':decoded['receipt_sha256'] if decoded else None,
        'main_identity':copy.deepcopy(plan['target']),'protected_variant_identity':copy.deepcopy(plan['protected_variant_identity']),
        'expected_question_count':23,'expected_frame_count':76,'differences':errors,'allowed_metadata_changes':metadata,
        'other_22_questions_unchanged':ok,'directory_unchanged':ok,'source_pages_unchanged':ok,
        'receipt_verified':bool(decoded),'independent_context_verified':False,'live_save_verified':False,
        'automatic_retry_allowed':False,'automatic_compensation':False}
