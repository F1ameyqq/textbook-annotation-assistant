"""Task-derived A16 controls against exact raw modules, with no real resource access."""
import asyncio
import copy
import ctypes
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import types
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path('D:/1800-worktrees/a16-independent-fixed')
OUT = ROOT / 'docs/evidence/A16/independent-offline-review'
REAL_CLOCK = time.monotonic
RESOURCE_ATTEMPTS = []


def denied_resource(name):
    def denied(*args, **kwargs):
        RESOURCE_ATTEMPTS.append(name)
        raise AssertionError('REVIEW_REAL_RESOURCE_DENIED_' + name)
    return denied


def audit(event, args):
    if event in ('socket.connect', 'socket.bind', 'subprocess.Popen', 'os.kill'):
        denied_resource(event)()
    if event == 'open' and args and isinstance(args[0], (str, bytes)):
        text = os.fsdecode(args[0]).replace('\\', '/').lower()
        if '/.local/' in text or 'browser-profiles' in text:
            denied_resource('PROFILE_OR_PRIVATE_PATH')()


sys.addaudithook(audit)

# The 49-file raw input omits parent __init__ files. A controlled in-memory
# package bridge prevents resolution to an unrelated installed `annotation`.
# It changes neither frozen files nor production import/package behavior.
for name, relative in [('annotation', 'src/annotation'), ('annotation.source', 'src/annotation/source'),
    ('annotation.source.usense', 'src/annotation/source/usense'),
    ('annotation.source.usense.current_readonly', 'src/annotation/source/usense/current_readonly')]:
    module = types.ModuleType(name)
    module.__path__ = [str(ROOT / relative)]
    sys.modules[name] = module
sys.path.insert(0, str(ROOT / 'tools'))
with patch.object(subprocess, 'Popen', denied_resource('POPEN_IMPORT')), \
        patch.object(ctypes, 'WinDLL', denied_resource('WINDLL_IMPORT')):
    import a16_current_state_probe as probe
    from annotation.source.usense.current_readonly import gate, policy, decode


class NoIOLoop(asyncio.SelectorEventLoop):
    def _make_self_pipe(self):
        pass
    def _close_self_pipe(self):
        pass
    def _write_to_self(self):
        pass
    def __init__(self):
        super().__init__()
        self._selector.select = lambda timeout=None: []


class NoIOPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):
        return NoIOLoop()


asyncio.set_event_loop_policy(NoIOPolicy())


def encoded(value):
    return json.dumps(value, sort_keys=True).encode('utf-8')


def rejects(operation, code=None):
    try:
        operation()
    except gate.Stop as error:
        if code is not None:
            assert str(error) == code, (str(error), code)
        return str(error)
    raise AssertionError('EXPECTED_REJECTION_MISSING')


def fixture(orders=(3, 11, 22)):
    b = {'id': gate.BOOK, 'title': 'INDEPENDENT_SYNTHETIC', 'question_count': len(orders)}
    nodes = [{'id': 'qid-' + str(n), 'isQuestion': True, 'order_in_level': str(n), 'label': 'fixture'} for n in orders]
    directory = {'code': 0, 'data': {'directory_data': [{'id':'dir-independent', 'label':'fixture', 'children':nodes}]}}
    rows = []
    for order in orders:
        for i, role in enumerate(['question','choice','choice','choice','choice','answer']):
            rows.append({'file_id':gate.BOOK, 'rect_id':'r-%d-%d' % (order,i),
                'order_in_level':str(order), 'directory_id':'dir-independent', 'type':role,
                'image_order_in_annotation_zone':i-1 if role == 'choice' else 0,
                'page_index':173 if role == 'answer' else 14, 'rect_bbox':[1,2,3,4],
                'content_type':'text', 'parent_rect_id':None})
    return b, directory, {'code':0,'data':rows}


def controls_default():
    with patch.object(probe, 'load_native', denied_resource('NATIVE')), \
            patch.object(probe.native, 'profile_binding', denied_resource('PROFILE')), \
            patch.object(subprocess, 'Popen', denied_resource('POPEN')):
        result = probe.main([])
    assert result == 0
    assert gate.context_options() == {'ignore_https_errors':False}
    return {'default_exit':result, 'strict_tls':True, 'candidate_actual_bytes_checked':True}


NOW = datetime(2026,10,20,12,tzinfo=timezone.utc)


def synthetic_grant(exception=False):
    mode = 'CONTEXT_EXCEPTION' if exception else 'STRICT'
    decision = encoded({'task':'A16','run_id':gate.RUN_ID,'tls_mode':mode,
        'live_authorized':True,'certificate_exception_authorized':exception})
    report = encoded({'task':'A16','candidate_manifest_sha256':'1'*64,'result':'ACCEPTED_OFFLINE_ONLY'})
    activation = {**gate.fixed_fields('1'*64,'2'*64), 'not_before':NOW.isoformat(),
        'expires_at':(NOW+timedelta(minutes=15)).isoformat(), 'tls_mode':mode,
        'user_decision_sha256':gate.sha(decision), 'independent_report_sha256':gate.sha(report)}
    return activation, decision, report


def validate(data, decision, report, exception=False, now=NOW):
    raw = encoded(data)
    return gate.validate_activation(raw, gate.sha(raw), '1'*64, '2'*64, decision, report,
        explicit_live=True, exception=exception, now=now)


def controls_gate():
    for exception in (False,True):
        a,d,r = synthetic_grant(exception)
        result = validate(a,d,r,exception)
        assert gate.context_options(result,NOW)['ignore_https_errors'] is exception
    checks = []
    for field, value in [('task','A15'), ('workflow_commit','old'), ('run_id','A15-old'),
        ('executor_thread_id','other'), ('candidate_manifest_sha256','9'*64), ('book_id','46006966'),
        ('viewers',[14,15,173]), ('target','https://other.invalid/'), ('profile_fingerprint','9'*64),
        ('output_directory','D:/not-authorized'), ('new_live_limit',2), ('context_limit',True),
        ('business_write_limit',1), ('old_budgets_restored',True)]:
        a,d,r = synthetic_grant()
        a[field] = value
        checks.append({'field':field,'rejection':rejects(lambda:validate(a,d,r))})
    a,d,r = synthetic_grant()
    for instant in [NOW-timedelta(seconds=1), NOW+timedelta(minutes=15)]:
        checks.append({'time_boundary':instant.isoformat(),'rejection':rejects(lambda:validate(a,d,r,now=instant))})
    rejects(lambda:validate(a,d,r,True), 'A16_TLS_DECISION_REQUIRED')
    rejects(lambda:gate.unique_json(b'{"task":"A16","task":"A15"}'), 'DUPLICATE_JSON_KEY')
    return {'synthetic_strict_and_exception_only':True,'rejections':checks,'activation_written':False}


def controls_policy():
    p = policy.ReadPolicy()
    assert all(p.decide('GET',gate.ORIGIN+v,'Fetch')[0] for v in policy.FIXED.values())
    for kind in ['Image','Font','Media']:
        assert p.decide('GET','https://optional.invalid/item',kind) == (False,'EXPECTED_PASSIVE_DENIAL')
        assert p.decide('POST','https://optional.invalid/item',kind) == (False,'METHOD_BLOCKED')
        assert p.decide('GET','https://optional.invalid/item',kind,True)[1] != 'EXPECTED_PASSIVE_DENIAL'
    for kind in ['Document','Script','Stylesheet','XHR','Fetch','WebSocket']:
        assert p.decide('GET','https://other.invalid/item',kind)[1] != 'EXPECTED_PASSIVE_DENIAL'
    for url in [gate.ORIGIN+policy.FIXED['page14'].replace('pageNum=14','pageNum=15'),
        gate.ORIGIN+policy.FIXED['book']+'&id=46006966',
        gate.ORIGIN+'/unknown?path='+policy.FIXED['frames'],
        gate.ORIGIN+'/qieti/api/unknown', 'https://u:p@www.usense.com/qieti/annotateUnified']:
        assert not p.decide('GET',url,'Fetch')[0]
    url = policy.OSS+'/upload_images/'+gate.BOOK+'/registered.jpg'
    p.register_original(url,gate.BOOK,14,57,'CURRENT_SYNTHETIC_PAGE_RESPONSE')
    assert p.decide('GET',url,'Image') == (True,'REGISTERED_ORIGINAL')
    rejects(lambda:p.register_original('https://unknown.invalid/a',gate.BOOK,173,72,'ref'))
    return {'fixed_gets':6,'optional_categories':['Image','Font','Media'],'source_registration':True,
        'writes_unknown_APIs_cross_origin_active_and_redirects_rejected':True}


def controls_redaction():
    secret = 'SYNTHETIC_SECRET_SENTINEL'
    entry = policy.diagnostic('https://user:'+secret+'@cdn.invalid:443/private/'+secret+'?token='+secret,
        'Font','EXPECTED_PASSIVE_DENIAL',False,'FIXED_SYNTHETIC')
    error = probe.safe_error(ValueError('Bearer '+secret))
    assert secret not in json.dumps([entry,error])
    assert entry['hostname'] == 'cdn.invalid' and entry['port'] == 443
    assert 'path' not in entry
    return {'safe_event':entry,'safe_error':error,'sentinel_absent':True}


def controls_inventory():
    b,d,f = fixture((11,22,3))
    target = decode.inventory(b,d,f,all_responses_complete=True)
    assert target['append_after_order'] == 22 and target['q22_in_inventory'] is True
    assert target['inventory_coverage'] == 'FULL' and target['content_coverage'] == 'UNKNOWN'
    assert not target['write_preservation_baseline'] and decode.sample_order(target) == 3
    unknown = copy.deepcopy(b); unknown.pop('question_count')
    assert decode.inventory(unknown,d,f,all_responses_complete=True)['inventory_coverage'] == 'PARTIAL'
    b2,d2,f2 = fixture((22,))
    assert decode.sample_order(decode.inventory(b2,d2,f2,all_responses_complete=True)) is None
    bad = copy.deepcopy(f); bad['data'][0]['file_id'] = '46006966'
    rejects(lambda:decode.inventory(b,d,bad))
    return {'full_inventory':True,'append':22,'selected_sample':3,'Q22_retained_not_sampled':True,
        'content_status':'UNKNOWN','write_ready':False,'partial_rejected_for_append':True}


def controls_content():
    b,d,f = fixture((3,))
    ids = [r['rect_id'] for r in f['data'] if r['type'] == 'choice']
    for text, expected in [('text','AVAILABLE'),('','KNOWN_EMPTY')]:
        body = {'code':0,'data':{'success':True,'ocr_result':text,'rect_ids':ids}}
        assert decode.bound_content(body,'choice',3,f['data'],True)['status'] == expected
        assert decode.bound_content(body,'choice',3,f['data'],False)['status'] == 'UNKNOWN'
    missing = {'code':0,'data':{'success':False,'message':'missing'}}
    assert decode.bound_content(missing,'choice',3,f['data'],True)['status'] == 'UNKNOWN'
    wrong = {'code':0,'data':{'success':True,'ocr_result':'text','rect_ids':ids[::-1]}}
    rejects(lambda:decode.bound_content(wrong,'choice',3,f['data'],True),'CONTENT_RECT_ORDER_MISMATCH')
    for response in [{'http_status':401},{'http_status':200,'body':{'code':False}},
        {'http_status':200,'body':{'code':403}}]:
        rejects(lambda:decode.business(response))
    return {'three_states_distinct':True,'rect_order_rejection':True,'login_and_bad_business_rejected':True}


def controls_source_and_draft():
    value = {'data':{'file_id':gate.BOOK,'pages':[{'page_index':57,'image':policy.OSS+'/upload_images/46007447/57.jpg'}]}}
    assert decode.source_page(value,14)['resource_index'] == 57
    rejects(lambda:decode.source_page(value,15))
    draft = json.loads((ROOT/'docs/evidence/A16/current-readonly/first-question-draft.json').read_bytes())
    assert decode.validate_draft(draft)['production_ready'] is False
    for mutation in ['roles','choice_order','numbers','answer_page']:
        wrong = copy.deepcopy(draft)
        if mutation == 'roles':
            for frame in wrong['frames'][1:5]: frame['role'] = 'Q'
        elif mutation == 'choice_order':
            wrong['frames'][1],wrong['frames'][2] = wrong['frames'][2],wrong['frames'][1]
        elif mutation == 'numbers': wrong['frames'][2]['text'] = '3，4，5'
        else: wrong['frames'][-1]['viewer'] = 14
        rejects(lambda:decode.validate_draft(wrong))
    return {'source57_retained_for_viewer14':True,'stale_role_and_order_controls_rejected':4,
        'candidate_remains_HOLD':True,'exact_punctuation_not_approved':True}


async def controls_cache():
    page = MagicMock(evaluate=AsyncMock())
    guard = probe.CurrentGuard(None,page,policy.ReadPolicy()); guard.session = MagicMock(send=AsyncMock())
    url = gate.ORIGIN+policy.FIXED['frames']
    raw = b'{"code":0,"data":[]}'
    event = {'request':{'method':'GET','url':url},'resourceType':'Fetch','requestId':'one'}
    await guard.paused(event)
    response = MagicMock(url=url,status=200,headers={'content-type':'application/json'},body=AsyncMock(return_value=raw))
    response.request.resource_type='fetch'; response.request.method='GET'
    await guard.capture(response)
    actual = await probe.get_once(page,guard,policy.FIXED['frames'])
    assert actual == {'code':0,'data':[]} and guard.cache[url]['bytes'] == raw
    page.evaluate.assert_not_called()
    event['requestId']='two'
    await guard.paused(event)
    assert guard.session.send.call_args.args[0] == 'Fetch.fulfillRequest'
    assert len(guard.sent) == 1 and not guard.stopped
    return {'capture_to_get_once_to_local_replay':True,'original_bytes_sha256':gate.sha(raw),
        'second_network_send':False,'page_evaluate_calls':0}


async def controls_fatal():
    guard = probe.CurrentGuard(None,MagicMock(),policy.ReadPolicy()); guard.session=MagicMock(send=AsyncMock())
    optional={'request':{'method':'GET','url':'https://optional.invalid/a'},'resourceType':'Font','requestId':'one'}
    await guard.paused(optional)
    assert not guard.stopped
    write={'request':{'method':'POST','url':gate.ORIGIN+policy.FIXED['frames']},'resourceType':'Image','requestId':'two'}
    await guard.paused(write)
    assert guard.stopped and guard.failure['codes']==['METHOD_BLOCKED']
    first=copy.deepcopy(guard.failure); guard.record_failure(gate.Stop('SECOND_FAILURE'))
    assert guard.failure==first
    page=MagicMock(evaluate=AsyncMock())
    try: await probe.get_once(page,guard,policy.FIXED['directory'])
    except gate.Stop: pass
    else: raise AssertionError('SUCCESSOR_NOT_STOPPED')
    page.evaluate.assert_not_called()
    ws=MagicMock(url='wss://other.invalid/?token=SYNTHETIC',close=AsyncMock())
    await guard.websocket(ws); ws.connect_to_server.assert_not_called()
    return {'expected_passive_then_fatal_method':True,'first_failure':first,'no_successor_get':True,'WS_no_connect':True}


async def controls_terminal():
    guard=probe.CurrentGuard(None,MagicMock(),policy.ReadPolicy()); captured={}
    async def opened(profile,approval,state):
        state['guard']=guard; return MagicMock(),guard
    async def collected(page,guard,result): result['outcome']='READONLY_REVIEW'
    async def closed(state):
        guard.record_failure(gate.Stop('SYNTHETIC_LATE_FATAL')); state['release']['state']='RELEASED'
    with patch.object(probe,'open_owned',opened),patch.object(probe,'collect',collected), \
        patch.object(probe.native,'close_owned',closed),patch.object(probe,'save_new',lambda p,v:captured.update(copy.deepcopy(v))):
        code=await probe.observe_live('IN_MEMORY_SYNTHETIC_ONLY',None)
    assert code==2 and captured['outcome']=='ERROR' and captured['error']['codes']==['SYNTHETIC_LATE_FATAL']
    return {'real_observer_finalization_with_memory_open_close':True,'outcome':captured['outcome'],
        'error':captured['error'],'real_live_entry_constructed':False}


async def controls_local_clock():
    guard=probe.CurrentGuard(None,MagicMock(),policy.ReadPolicy())
    url=gate.ORIGIN+policy.FIXED['book']; guard.sent.add(url)
    ticks=iter([7,28])
    try: await probe.await_existing_response(guard,url,clock=lambda:next(ticks))
    except gate.Stop as error: assert str(error)=='EXISTING_GET_RESPONSE_UNPROVEN'
    else: raise AssertionError('TIMEOUT_MISSING')
    return {'local_clock_origin':7,'timeout_at':28,'resend':False,
        'OS_Job_and_held_identity': 'STATIC_ONLY_NOT_EXECUTED'}


async def collector_sample_rebinding(mutate=False):
    b,d,f=fixture((3,22)); p=policy.ReadPolicy(); guard=probe.CurrentGuard(None,MagicMock(),p)
    code=b'''client.get("/qieti/api/verify_annotation/get-ocr-annotation",{params:{file_id:a,question_order:b,zone:c}});
        get_question_info get_manual_annotations_unified_by_order_in_level "question" "choice" "answer"
        commit_unified_submit ocr_submissions ocr_result rect_ids success'''
    guard.scripts=[{'bytes':code,'ref':'INDEPENDENT_SYNTHETIC_SCRIPT','loaded_origin':{}}]
    calls=[]; sample_changed=[]
    async def get(page,g,path):
        calls.append(path)
        if path==policy.FIXED['book']:return {'code':0,'data':[b]}
        if path==policy.FIXED['directory']:return d
        if path==policy.FIXED['frames']:return f
        if path==policy.FIXED['source']:return {'code':0,'data':{'file_id':gate.BOOK}}
        for viewer in [14,173]:
            if path==policy.FIXED['page'+str(viewer)]:
                body={'code':0,'data':{'file_id':gate.BOOK,'pages':[{'page_index':viewer+43,
                    'image':policy.OSS+'/upload_images/46007447/page%d.jpg'%viewer}]}}
                g.cache[gate.ORIGIN+path]={'bytes':encoded(body)}; return body
        if 'by_order_in_level' in path:
            rows=copy.deepcopy([r for r in f['data'] if r['order_in_level']=='3'])
            if mutate:
                rows[1]['type']='answer'
                rows[2]['image_order_in_annotation_zone']=3
                sample_changed.extend([rows[1],rows[2]])
            return {'code':0,'data':rows}
        if 'get_question_info' in path:return {'code':0,'data':{'file_id':gate.BOOK,'order_in_level':'3','tishi':'xuanze'}}
        zone=path.split('&zone=')[1]
        ids=[r['rect_id'] for r in f['data'] if r['order_in_level']=='3' and r['type']==zone]
        return {'code':0,'data':{'success':True,'ocr_result':'SYNTHETIC_'+zone,'rect_ids':ids}}
    page=MagicMock(goto=AsyncMock()); page.url=gate.TARGET
    page.get_by_placeholder.return_value.is_visible=AsyncMock(return_value=False)
    page.get_by_role.return_value.click=AsyncMock()
    page.locator.return_value.first.wait_for=AsyncMock()
    page.locator.return_value.inner_text=AsyncMock(return_value=gate.BOOK)
    row=page.locator.return_value.filter.return_value
    row.wait_for=AsyncMock(); row.count=AsyncMock(return_value=1); row.get_by_role.return_value.click=AsyncMock()
    result={'steps':{},'sources':[],'gaps':[]}; saves={}; thrown=None
    with patch.object(probe,'get_once',get),patch.object(probe,'original_once',AsyncMock(return_value={'synthetic':True})), \
        patch.object(probe,'visible_mapping',AsyncMock(return_value={'synthetic':True})), \
        patch.object(probe,'save_new',lambda path,value:saves.update({path.name:copy.deepcopy(value)})):
        try: await probe.collect(page,guard,result)
        except gate.Stop as error: thrown=str(error)
    return {'mutate_sample_only':mutate,'sample_changed_fields':sample_changed,
        'thrown':thrown,'result':result,'business_GET_count':len(calls),'saved_names':sorted(saves),
        'stubs': ['business transport responses','image fetch/visible UI proof','file writes'],
        'actual_product_path':['collect','inventory','sample_order','current_code','register_sample','bound_content','sample_frame_identity_check']}


async def controls_collector_baseline():
    value=await collector_sample_rebinding(False)
    assert value['thrown'] is None and value['result']['outcome']=='READONLY_REVIEW'
    assert value['result']['target']['inventory_coverage']=='FULL'
    assert value['result']['target']['content_coverage']=='PARTIAL'
    assert value['result']['sample']['content']['choice']['status']=='AVAILABLE'
    assert value['business_GET_count']==11 and value['result']['sample']['order']==3
    return value


async def counterexample_changed_sample():
    value=await collector_sample_rebinding(True)
    with (OUT/'counterexample-changed-sample.actual.json').open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
    assert value['thrown'] is not None, 'SAME_RECT_IDS_WRONG_ROLE_AND_ORDER_ACCEPTED_AS_READONLY_REVIEW'
    return value


PROBES=[
    ('C01_DEFAULT_STATIC',['A01','A05','L03'],controls_default),
    ('C02_GATE',['A02','A03','A04','A05'],controls_gate),
    ('C03_POLICY',['N01','N02','N03','N04','N06','N10','S01'],controls_policy),
    ('C04_REDACTION',['R01','R02'],controls_redaction),
    ('C05_INVENTORY',['I01','I02','I04','Q01'],controls_inventory),
    ('C06_CONTENT',['C01','C02','C03','D02','D03'],controls_content),
    ('C07_SOURCE_DRAFT',['S02','F01','F02','F03'],controls_source_and_draft),
    ('C08_REAL_CAPTURE_CACHE',['N09'],controls_cache),
    ('C09_PASSIVE_THEN_FATAL',['N04','N05','N07'],controls_fatal),
    ('C10_TERMINAL',['N08'],controls_terminal),
    ('C11_LOCAL_WAIT_CLOCK',['L01'],controls_local_clock),
    ('C12_COLLECTOR_BASELINE',['I01','C02','Q01','Q03'],controls_collector_baseline),
    ('C13_CHANGED_SAMPLE_COUNTEREXAMPLE',['D02','F03'],counterexample_changed_sample),
    ('C14_TRUNCATED_JPEG',['S03'],None),
    ('C15_LEXICAL_SCHEMA_FALSE_POSITIVE',['D01','D02','D04'],None),
    ('C16_JOB_IDENTITY_MISMATCH',['L02'],None)]

started=REAL_CLOCK(); results=[]; first_failure=None
with patch.object(socket.socket,'connect',denied_resource('SOCKET_CONNECT')), \
    patch.object(socket.socket,'bind',denied_resource('SOCKET_BIND')), \
    patch.object(subprocess,'Popen',denied_resource('POPEN')), \
    patch.object(ctypes,'WinDLL',denied_resource('WINDLL')), \
    patch.object(probe,'load_native',denied_resource('NATIVE_API')), \
    patch.object(probe.native,'profile_binding',denied_resource('PROFILE')):
    for ident,cases,operation in PROBES:
        if first_failure is not None:
            results.append({'id':ident,'cases':cases,'status':'NOT_RUN','reason':'FIRST_SEMANTIC_COUNTEREXAMPLE_STOP'})
            continue
        if operation is None:
            results.append({'id':ident,'cases':cases,'status':'NOT_RUN','reason':'STATIC_REVIEW_ONLY'})
            continue
        try:
            value=asyncio.run(operation()) if asyncio.iscoroutinefunction(operation) else operation()
            results.append({'id':ident,'cases':cases,'status':'PASS','actual':value})
        except BaseException as error:
            first_failure={'id':ident,'exception_type':type(error).__name__,'detail':str(error)}
            results.append({'id':ident,'cases':cases,'status':'FAIL','failure':first_failure})

record={'task':'A16','candidate_manifest_sha256':'2579b043d65e665263796d0922f080ad101f4d20c1e9ea500fd7894ba41d966c',
    'result':'REWORK' if first_failure else 'CONTROLS_COMPLETE', 'probes':results,'first_failure':first_failure,
    'resource_attempts':RESOURCE_ATTEMPTS,'duration_ms':round((REAL_CLOCK()-started)*1000),
    'package_bridge':'Only frozen 49-file input modules; no missing parent initializer fetched or product file changed',
    'real_browser_network_profile_native_or_occupancy':False,'live_activation':False}
with (OUT/'independent-controls-result.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(record,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps({'result':record['result'],'probe_statuses':{r['id']:r['status'] for r in results},
    'first_failure':first_failure,'resource_attempts':RESOURCE_ATTEMPTS,'duration_ms':record['duration_ms']}))
raise SystemExit(1 if first_failure else 0)
