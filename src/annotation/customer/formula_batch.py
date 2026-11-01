"""One normal review action prepares clear formula rows; first failure stops."""
from __future__ import annotations
import copy
import time
from .formula_regions import propose,recognize_proposal,mark_boundary_conflicts,mark_consumed_regions,consumed_records
from .store import Hold,digest


def plan(store,identity,expected_head):
    job,head=store.job(identity)
    if head!=expected_head:raise Hold('任务已变化，请刷新公式准备范围。')
    graph,evidence=store.get(job['graph_ref']),store.get(job['evidence_ref'])
    regions=[]
    for candidate in job['candidates']:
        if candidate['platform_status']!='NOT_RUN':continue
        for region in propose(candidate,graph,evidence)['regions']:
            row={'candidate_key':candidate['key'],'printed_number':candidate['printed_number'],**region}
            regions.append(row)
    regions=mark_consumed_regions(store,job['book_id'],mark_boundary_conflicts(regions))
    clear=[row for row in regions if row['uncertainty']=='OBSERVED_MATH_ROW']
    mixed=[row for row in regions if row['uncertainty']!='OBSERVED_MATH_ROW']
    if len(clear)>64:raise Hold('本次明确公式区域超过64处，请缩小普通材料范围。')
    return {'schema':'CustomerFormulaBatchPlan/v1','job_id':identity,'head':head,'book_id':job['book_id'],
            'clear_regions':clear,'manual_region_review':mixed,'content_approved':False,'model_calls':0}


def _signature(row):
    return (row['candidate_key'],row['zone'],row['asset_id'],row['source_sha256'],tuple(row['bbox']))


def _continuation_after_fixed_failure(store,identity,scope,settings):
    """A new explicit GUI batch can use only uncalled suffixes after update."""
    with store.connect() as db:
        previous=db.execute('SELECT key,state,output FROM operations WHERE kind=? AND state!=?',
                            ('formula-batch:'+identity,'COMPLETE')).fetchall()
    if not previous:return []
    from .formula_runtime import local_identity
    from .formula_roi_cache import digest as model_digest
    current_hash=None
    records=consumed_records(store,scope['book_id']);links=[]
    for key,state,reference in previous:
        if state!='FAILED_NO_RETRY' or reference is None:
            raise Hold('本课公式准备有未解决的中断记录，不扩大范围继续运行。')
        report=store.get(reference)
        if report.get('schema')!='CustomerFormulaBatchResult/v1' or report.get('status')!='FAILED_NO_RETRY':
            raise Hold('原失败批次记录不完整。')
        old_plan=report['plan'];items=report['items'];by_id={row['proposal_id']:row for row in old_plan['clear_regions']}
        if old_plan['job_id']!=identity or old_plan['book_id']!=scope['book_id'] or len(items)!=len(by_id) or {r['proposal_id'] for r in items}!=set(by_id):
            raise Hold('原批次范围或后继状态不完整。')
        failed=[row for row in items if row['status']=='FAILED_OR_NOT_COMPLETED']
        if len(failed)!=1 or any(row['status'] not in {'CANDIDATE_RETAINED_PENDING_REVIEW','FAILED_OR_NOT_COMPLETED','NOT_RUN'} for row in items):
            raise Hold('原批次的首次失败与未运行范围不明确。')
        failure_region=by_id[failed[0]['proposal_id']]
        attempts=[row for row in records if row['request']['roi_identity']['source_sha256']==failure_region['source_sha256']
                  and row['request']['roi_identity']['source_bbox']==failure_region['bbox']]
        if len(attempts)!=1 or attempts[0]['state']!='FAILED_NO_RETRY':
            raise Hold('原失败区域没有完整的永久保留记录。')
        if current_hash is None:
            current_model,_,_=local_identity(settings);current_hash=model_digest(current_model)
        old_hash=attempts[0]['request']['cache_identity']['model_identity_sha256']
        if current_hash==old_hash:
            raise Hold('上一批已停止；本地识别程序尚未更新，不继续消耗其他区域。失败范围可对照原图人工修正。')
        unrun={_signature(by_id[row['proposal_id']]) for row in items if row['status']=='NOT_RUN'}
        if any(_signature(row) not in unrun for row in scope['clear_regions']):
            raise Hold('本次范围超出原批次明确未运行的区域。')
        links.append({'batch_key':key,'batch_output':reference,'failed_roi_key':attempts[0]['key'],
                      'old_model_identity_sha256':old_hash,'current_model_identity_sha256':current_hash,
                      'failed_record_preserved':True})
    return links


def run(store,identity,expected_head,settings,retain):
    scope=plan(store,identity,expected_head);items=scope['clear_regions']
    if not items:return {'status':'NO_CLEAR_REGIONS','items':[],'new_worker_invocations':0}
    kind='formula-batch:'+identity;key=digest(items)
    old=store.operation(kind,key)
    if old:
        if old['state']!='COMPLETE':raise Hold('本课公式准备已有中断或失败记录，不重新执行。')
        return {**store.get(old['output']),'batch_reused':True,'new_worker_invocations':0}
    if settings.get('runtime',{}).get('formula_inference_activated') is not True:
        raise Hold('本地公式识别尚未启用，不会开始模型调用。')
    continuation=_continuation_after_fixed_failure(store,identity,scope,settings)
    store.begin(kind,key);started=time.monotonic()
    report={'schema':'CustomerFormulaBatchResult/v1','plan':scope,'items':[],
            'status':'INTENT','new_worker_invocations':0,'automatic_retry':False,'content_approved':False,
            'continuation_of_fixed_failed_batches':continuation}
    try:
        for index,row in enumerate(items):
            if time.monotonic()-started>=900:raise Hold('本次公式准备到达时间上限，后继保留未运行。')
            result=recognize_proposal(store,identity,expected_head,row['candidate_key'],row['proposal_id'],settings,source_checked=True)
            retained=retain(result)
            report['items'].append({'proposal_id':row['proposal_id'],'candidate_key':row['candidate_key'],
                'status':'CANDIDATE_RETAINED_PENDING_REVIEW','record':retained,'new_worker_invocations':result['new_worker_invocations']})
            report['new_worker_invocations']+=result['new_worker_invocations']
        report['status']='CANDIDATES_PENDING_REVIEW';report['elapsed_seconds']=time.monotonic()-started
        store.finish(kind,key,'COMPLETE',report)
        return report
    except BaseException as exc:
        report['status']='FAILED_NO_RETRY';report['error']={'type':type(exc).__name__,'message':str(exc)}
        completed=len(report['items'])
        for index,row in enumerate(items[completed:]):
            report['items'].append({'proposal_id':row['proposal_id'],'candidate_key':row['candidate_key'],
                'status':'FAILED_OR_NOT_COMPLETED' if index==0 else 'NOT_RUN'})
        report['elapsed_seconds']=time.monotonic()-started
        store.finish(kind,key,'FAILED_NO_RETRY',report)
        raise
