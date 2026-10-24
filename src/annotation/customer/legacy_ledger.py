"""Read historical intent/receipt/readback chains without changing old ledgers.

Closures bind raw claims and business identities. They never create revision
authority, reset spent attempts or convert a failed writer into a successful one.
Unresolved intents in any directory of the selected book stop new sends.
"""
from __future__ import annotations
import copy,json,re
from pathlib import Path
from .store import Hold,byte_hash,digest
from .native_plan import require


def closure_from_raw(raw):
    from annotation.runtime.usense_live.update import json_same,loads,digest as original_digest
    decoded={k:loads(raw[k]) for k in ('claim','plan','writer','receipt','closure','reader')}
    claim,plan,w,receipt,c,r=(decoded[k] for k in ('claim','plan','writer','receipt','closure','reader'))
    require(original_digest({k:v for k,v in plan.items() if k!='plan_sha256'})==plan['plan_sha256'],'旧计划内容摘要不同。')
    require(claim['ledger_key']==plan['ledger_key'] and claim['plan_sha256']==plan['plan_sha256']
            and claim['run_id']==w['run_id'] and w['plan_sha256']==plan['plan_sha256']
            and w['plan_file_sha256']==byte_hash(raw['plan']) and claim['native_body_sha256']==w['native_body_sha256']
            and w['receipt_sha256']==byte_hash(raw['receipt']) and type(w['post_attempts']) is int and w['post_attempts']==1
            and w['post_layers']=={'context':1,'native':1},'旧意图、计划或唯一发送回执未绑定。')
    require(receipt.get('code')==0 and receipt.get('data',{}).get('success') is True,'旧业务回执未成功。')
    comparison=c.get('comparison',{})
    schema=c.get('schema');status=c.get('status')
    if status in {'ACCEPTED','ACCEPTED_LESSON_INSERT'}:
        require(c.get('writer_run')==w['run_id'] and c.get('checks') and all(v is True for v in c['checks'].values()),'旧成功闭环不完整。')
        require(comparison.get('match',comparison.get('ok')) is True and comparison.get('differences')==[], '旧完整读回未匹配。')
    elif schema=='A25LaterQ4IndependentReadback/v1' and status=='MATCHED':
        require(c['writer_run']==w['run_id'] and c['old_intent_preserved'] is True
                and c['checks'] and all(v is True for v in c['checks'].values()) and comparison.get('match') is True,
                '旧失败的后续独立对账未闭合。')
    elif schema=='A25ExistingThirdReadbackReconciliation/v1':
        require(c['plan_sha256']==plan['plan_sha256'] and c['original_failed_status']=='FAILED_STOP'
            and c['provenance_checks'] and all(v is True for v in c['provenance_checks'].values())
            and c['limited_reconciliation']['status']=='CREATED_ZONE_KEY_ORDER_ONLY_MATCH'
            and c['limited_reconciliation']['match'] is True,'旧键顺序差异对账未闭合。')
        comparison=c['limited_reconciliation']['comparison_after_limited_expected_key_order']
        require(comparison['match'] is True and comparison['differences']==[],'旧字段值仍不匹配。')
    else:raise Hold('未知历史闭环类型，保留原记录并核对。')
    require(comparison['plan_sha256']==plan['plan_sha256'],'旧闭环计划身份不同。')
    require(r['run_id']!=w['run_id'] and r['status']=='NATIVE_GETS_CAPTURED' and r['save_attempts']==0
            and r['release']['context_runtime_release_confirmed'] is True,'旧独立读回或释放未证。')
    if c.get('reader_run') is not None:require(c['reader_run']==r['run_id'],'旧读回上下文不同。')
    require(set(raw['captures'])==set(r['captures']),'旧读回原件不完整。')
    after={}
    for name,body in raw['captures'].items():
        descriptor=r['captures'][name]
        require(descriptor['sha256']==byte_hash(body) and descriptor['status']==200
                and descriptor['request_counts']=={'context':1,'native':1},'旧读回字节或次数不同。')
        after[name]=loads(body)
    target=c.get('target') or comparison.get('new_identity')
    require(type(target) is dict and target['book_id']==(plan.get('book_id') or plan['target']['book_id']), '旧闭环题身份缺失。')
    order=target['question_order'];info=after[f'q{order}_info']['data']
    require(info['id']==target['info_id'] and info['file_id']==target['book_id'],'旧读回稳定 info 身份不同。')
    zones={z:after[f'q{order}_{z}'] for z in ('question','choice','answer','analysis','knowledge_point')}
    if 'expected' in plan:
        # Object-key order differences of newly created zones were explicitly
        # reconciled; Python equality still preserves every value/list position.
        require(zones==plan['expected']['zones'],'旧计划正文和最终原始读回不一致。')
    else:
        for item in plan['payload_candidate']['ocr_submissions']:
            require(zones[item['zone']]['data']['ocr_result']==item['ocr_result']
                    and zones[item['zone']]['data']['rect_ids']==item['rect_ids'],'旧插入正文未逐区绑定。')
    return {'schema':'CustomerHistoricalClosure/v1','book_id':target['book_id'],'claim_sha256':byte_hash(raw['claim']),
        'ledger_key':claim['ledger_key'],'target':target,'zones':zones,'annotations':after[f'q{order}_annotations'],
        'claim':claim,'original_writer':w,'closure':c,'plan_sha256':plan['plan_sha256'],
        'provenance':{k:byte_hash(v) for k,v in raw.items() if k!='captures'},
        'capture_provenance':{k:byte_hash(v) for k,v in raw['captures'].items()},
        'new_send_authorized':False,'revision_predecessor_eligible':False,'old_failures_preserved':True}


def import_closure(store,raw):
    closure=closure_from_raw(raw);kind='legacy-closure:'+closure['book_id'];key=closure['claim_sha256']
    old=store.operation(kind,key)
    if old:
        require(old['state']=='COMPLETE' and store.get(old['output'])==closure,'历史闭环已有不同来源。')
        return old['output']
    store.begin(kind,key);return store.finish(kind,key,'COMPLETE',closure)


def import_bundle(store,path,sha256):
    import base64
    raw=Path(path).read_bytes();require(byte_hash(raw)==sha256,'历史迁移包已改变。')
    value=json.loads(raw);require(value.get('schema')=='CustomerHistoricalRawBundle/v1','历史迁移包类型无效。')
    refs=[]
    for item in value['closures']:
        decoded={k:base64.b64decode(v,validate=True) for k,v in item.items() if k!='captures'}
        decoded['captures']={k:base64.b64decode(v,validate=True) for k,v in item['captures'].items()}
        closure=closure_from_raw(decoded);require(closure['book_id']==value['book_id'],'迁移包书籍混杂。')
        refs.append(import_closure(store,decoded))
    return {'book_id':value['book_id'],'closure_refs':refs,'raw_bundle_sha256':sha256,'old_ledger_mutations':0}


def bootstrap(store,book):
    # A current-machine delivery can carry a one-time migration package. A new
    # customer has no prior claims and needs no historical package or artifacts.
    settings_path=store.root/'settings.json'
    if settings_path.is_file():
        registered=json.loads(settings_path.read_bytes()).get('historical_bundle')
        if registered and registered.get('book_id')==book:
            import_bundle(store,registered['path'],registered['sha256']);return
    package=Path(__file__).resolve().parents[3]/'runtime/customer-history'/book
    index=package/'registry.json'
    if not index.is_file():return
    value=json.loads(index.read_bytes())
    require(value['book_id']==book,'历史迁移索引书籍不一致。')
    path=(package/value['filename']).resolve()
    require(path.is_relative_to(package.resolve()),'历史迁移包路径无效。')
    import_bundle(store,path,value['sha256'])


def guard(store,ledger,book):
    """A successful sidecar alone never clears an unresolved original claim."""
    ledger=Path(ledger);require(ledger.is_dir(),'原保存账本目录缺失。')
    closures=[]
    for path in sorted(ledger.glob('*.json')):
        if path.name.endswith('.accepted.json'):continue
        raw=path.read_bytes();claim=json.loads(raw)
        target_book=claim.get('target',{}).get('book_id') or claim.get('book_id')
        if target_book is None:
            match=re.match(r'book([1-9][0-9]*)-',path.name)
            target_book=match[1] if match else None
        if claim.get('operation') in {'CUSTOMER_SOURCE_BOUND_INSERT','CUSTOMER_SOURCE_BOUND_EXISTING_FILL'} and target_book in {None,book}:
            key=claim['ledger_key'].removeprefix('customer-');op=store.operation('save:'+book,key)
            if op and op['state']=='COMPLETE':
                accepted=store.get(op['output'])
                require(accepted['writer']['writer']['run_id']==claim['run_id'],'当前保存与原账本绑定不同。')
                continue
        require(target_book is not None,'原账本有未知书籍意图，先核对原记录。')
        if target_book!=book:continue
        op=store.operation('legacy-closure:'+book,byte_hash(raw))
        require(op is not None and op['state']=='COMPLETE','本书原账本仍有未对账意图：'+path.name)
        closure=store.get(op['output']);require(closure['claim']==claim,'原意图已改变。')
        closures.append(closure)
    return closures


def existing_candidate(current,candidate):
    """Identify existing source/content in current native state, never overwrite.

    This reuse is a read of an existing node, not a new save acceptance. All
    ambiguous overlaps retain HOLD. A separate native-export mapping may reuse
    this exact current record after complete capture.
    """
    from .native_plan import _response,_overlap
    import math
    from .existing_fill import locate
    matched=locate(current,candidate)
    if matched is None:return None
    node,record,order=matched['node_id'],matched['record'],str(matched['order'])
    if any(_response(record['zones'][zone]).get('success') is False for zone in candidate['zones']):return None
    # Compare the entire generated native field, including TeX and images;
    # stripping HTML would silently lose a newly required candidate figure.
    from .existing_fill import bound_frames
    from .rich_content import zone_html
    bound=bound_frames(current,candidate,record)
    for zone,value in candidate['zones'].items():
        data=_response(record['zones'][zone])
        images=[f for f in bound if f['type']==zone and f['content_type']=='image']
        require(data.get('success') is True and data['ocr_result']==zone_html(value,images)
                and data['rect_ids']==[f['rect_id'] for f in _response(record['annotations']) if f['type']==zone],
                '已有题来源重合但完整正文、公式、题图或关联不同，保留原题并核对。')
    for zone,data in record['zones'].items():
        if zone not in candidate['zones']:require(_response(data).get('success') is False,'原生题含候选未核对的正文分区。')
    return {'node_id':node,'record':copy.deepcopy(record),'order':order}
