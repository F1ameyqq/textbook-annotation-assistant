"""Observation-only independent delta; no old parser/suite execution or real resources."""
import asyncio
import copy
import ctypes
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from unittest.mock import AsyncMock,MagicMock,patch

ROOT=Path('D:/1800-worktrees/a16-observation-review');OUT=ROOT/'docs/evidence/A16/independent-observation-review'
CANDIDATE='e66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f'
ATTEMPTS=[];PARSER_CALLS=[];START=time.monotonic()
def deny(name):
    def f(*a,**kw):ATTEMPTS.append(name);raise AssertionError('FORBIDDEN_REAL_RESOURCE_'+name)
    return f
def audit(event,args):
    if event in ('socket.connect','socket.bind','subprocess.Popen','os.kill'):deny(event)()
    if event=='open' and isinstance(args[0],(str,bytes)):
        text=os.fsdecode(args[0]).replace('\\','/').lower()
        if '/.local/' in text or 'browser-profiles' in text:deny('PRIVATE_LIVE_PROFILE_PATH')()
sys.addaudithook(audit)
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'tests/a16_current_readonly')]
with patch.object(ctypes,'WinDLL',deny('NATIVE_IMPORT')):
    import a16_current_state_probe as probe
    from annotation.source.usense.current_readonly import gate,policy,decode,js_wire
    from test_observation_only import Harness,page_mock,response,SAMPLES,SAMPLE_STEPS

class NoIOLoop(asyncio.SelectorEventLoop):
    def _make_self_pipe(self):pass
    def _close_self_pipe(self):pass
    def _write_to_self(self):pass
    def __init__(self):super().__init__();self._selector.select=lambda timeout=None:[]
class NoIOPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):return NoIOLoop()
asyncio.set_event_loop_policy(NoIOPolicy())

SENTINEL='INDEPENDENT_STATIC_PRIVATE_SENTINEL'
DATA=(b'not executable\r\n'+SENTINEL.encode()+b'\x00\xff; success ocr_result rect_ids')

def no_parser(*a,**kw):
    PARSER_CALLS.append('CALLED');raise AssertionError('PARSER_OR_SCHEMA_QUALIFICATION_CALLED')
def stops(fn):
    try:fn()
    except gate.Stop as e:return str(e)
    raise AssertionError('EXPECTED_REJECTION_MISSING')

async def disabled_register_and_get():
    rejections=[]
    for alleged in [True,{'status':'CURRENT_CODE_CONFIRMED','binding_proof':{'complete':True}},
        {'automatic_schema_confirmation':True,'sample_limit':1,'scope':gate.SCOPE},None]:
        p=policy.ReadPolicy();before=copy.deepcopy(vars(p))
        code=stops(lambda:p.register_sample(3,alleged));assert vars(p)==before
        rejections.append(code)
    tested=0
    for endpoint in SAMPLES:
        for candidate in [endpoint,endpoint.replace('46007447','46007447').replace('/3','/22').replace('order=3','order=22')]:
            g=probe.CurrentGuard(None,page_mock(),policy.ReadPolicy());url=gate.ORIGIN+candidate
            g.policy.business[policy.key(url)]='sample_forged';g.policy.originals[14]=url
            g.cache[url]={'bytes':b'{"code":0,"data":[]}','content_type':'application/json'}
            assert g.policy.decide('GET',url,'Fetch')==(False,'SAMPLE_DISABLED_OBSERVATION_ONLY')
            try:await probe.get_once(g.page,g,candidate)
            except gate.Stop as e:assert str(e)=='UNREGISTERED_BUSINESS_GET'
            else:raise AssertionError('FORGED_SAMPLE_CACHE_BYPASSED_POLICY')
            g.page.evaluate.assert_not_awaited();tested+=1
    return {'register_rejections':rejections,'forged_map_original_cache_paths_blocked':tested,'requests_sent':0}

async def both_guard_paths():
    results=[]
    for path in SAMPLES:
        g=probe.CurrentGuard(None,page_mock(),policy.ReadPolicy());g.session=MagicMock(send=AsyncMock())
        await g.paused({'requestId':'memory','request':{'url':gate.ORIGIN+path,'method':'GET'},'resourceType':'Fetch'})
        assert g.session.send.await_args.args[0]=='Fetch.failRequest' and g.stopped and not g.sent
        g2=probe.CurrentGuard(None,page_mock(),policy.ReadPolicy())
        req=MagicMock(url=gate.ORIGIN+path,method='GET',resource_type='fetch',redirected_from=None,frame=g2.page.main_frame)
        route=MagicMock(request=req,abort=AsyncMock(),continue_=AsyncMock(),fulfill=AsyncMock())
        await g2.route(route)
        route.abort.assert_awaited_once();route.continue_.assert_not_awaited();route.fulfill.assert_not_awaited()
        assert g2.stopped
        results.append({'path_family':path.split('?')[0].rsplit('/',1)[0],'native_block':True,'context_block':True})
    return {'sample_family_guards':results,'server_connections':0}

async def actual_collect_ignores_assets():
    results=[]
    for raw in [DATA,b'async function read(){return null;}',b'/* alleged complete schema */']:
        h=Harness();url=gate.ORIGIN+'/assets/'+SENTINEL+'.js'
        h.guard.scripts=[{'url':url,'ref':'static-assets/synthetic.bin','sha256':gate.sha(raw),'size':len(raw),
            'source_url_sha256':gate.sha(url.encode()),'loaded_origin':{},'http_status':200,'executed_by_collector':False,
            'bytes':raw,'status':'CURRENT_CODE_CONFIRMED','binding_proof':{'complete':True},'sample_limit':1}]
        with patch.object(decode,'current_code',no_parser),patch.object(decode,'sample_order',no_parser), \
            patch.object(js_wire,'analyze_asset',no_parser),patch.object(js_wire,'evidenced_paths',no_parser):
            result=await h.observe()
        assert h.calls==list(policy.FIXED.values()) and len(set(h.calls))==6
        assert [x.args[2]['viewer'] for x in h.original.await_args_list]==[14,173]
        assert h.mapping.await_count==2 and result['target']['q22_in_inventory']
        assert result['target']['inventory_coverage']=='FULL' and result['target']['write_preservation_baseline'] is False
        assert result['sample_limit']==0 and result['sample']['status']=='NOT_RUN'
        assert all(result['steps'][name]=='NOT_RUN' for name in SAMPLE_STEPS)
        assert result['body_status']==result['schema_status']=='UNKNOWN'
        assert all(q['content']['status']=='UNKNOWN' for q in result['target']['questions'])
        assert not result['write_eligible'] and not result['production_ready']
        public=json.dumps(h.files)
        assert SENTINEL not in public and 'CURRENT_CODE_CONFIRMED' not in public and 'AVAILABLE' not in public
        results.append({'script_sha256':gate.sha(raw),'calls':h.calls,'result':result,'saved_names':list(h.files)})
    assert PARSER_CALLS==[]
    return {'collects':results,'parser_qualification_or_selection_calls':0,'fixed_GETs_per_collect':6,'originals_per_collect':2}

async def exact_static_bytes():
    folder=OUT/'synthetic-private-static';folder.mkdir(exist_ok=False)
    g=probe.CurrentGuard(None,page_mock(),policy.ReadPolicy());g.output=folder
    assets=[]
    with patch.object(probe,'LIVE_OUT',folder),patch.object(g.page,'evaluate',deny('ASSET_EXECUTION')):
        for i,raw in enumerate([DATA,DATA+b'\r\nSECOND']):
            url=gate.ORIGIN+'/qieti/assets/'+SENTINEL+'-'+str(i)+'.js'
            r=response(raw,url)
            await g.capture(r);await g.capture(r)
            public=probe.public_assets(g)[-1];saved=(folder/public['ref']).read_bytes()
            source=json.loads((folder/(public['ref']+'.source.json')).read_bytes())
            assert saved==raw and public['sha256']==gate.sha(raw) and public['size']==len(raw)
            assert source['source_url']==url and public['source_url_sha256']==gate.sha(url.encode())
            assert public['executed_by_collector'] is False
            g.audit('GET',url,'Script','STATIC',True,'CURRENT_RESPONSE')
            assets.append(public)
    assert len(g.scripts)==2
    public=json.dumps({'assets':probe.public_assets(g),'audit':g.events})
    assert SENTINEL not in public and 'set-cookie' not in public and 'source_url"' not in public
    assert 'bytes"' not in public and PARSER_CALLS==[]
    return {'assets':assets,'exact_raw_bytes_saved':True,'exact_source_private':True,'public_sanitized':True,
        'collector_eval_or_execute':False,'real_static_data_used':False}

async def capture_rejects_unapproved():
    tested=0
    for url,kind,method in [(gate.ORIGIN+'/qieti/api/user_login/profile','fetch','GET'),
        (gate.ORIGIN+'/assets/not-approved.js?token='+SENTINEL,'script','GET'),
        ('https://unknown.invalid/assets/a.js','script','GET'),(gate.ORIGIN+'/assets/a.js','fetch','GET'),
        (gate.ORIGIN+'/assets/a.js','script','POST'),(gate.ORIGIN+SAMPLES[-1],'fetch','GET')]:
        g=probe.CurrentGuard(None,page_mock(),policy.ReadPolicy());r=response(DATA,url,kind,method)
        await g.capture(r);r.body.assert_not_awaited();assert not g.scripts and not g.cache;tested+=1
    g=probe.CurrentGuard(None,page_mock(),policy.ReadPolicy());r=response(DATA,status=401)
    try:await g.capture(r)
    except gate.Stop as e:assert str(e)=='LOGIN_REQUIRED'
    else:raise AssertionError('FAILED_STATIC_RESPONSE_ACCEPTED')
    r.body.assert_not_awaited()
    return {'excluded_response_bodies_not_read':tested,'login_response_stopped':True}

async def fixed_cache_and_scope():
    p=policy.ReadPolicy();g=probe.CurrentGuard(None,page_mock(),p)
    for name,path in policy.FIXED.items():
        raw=json.dumps({'code':0,'data':{'independent_fixture':name}}).encode()
        r=response(raw,gate.ORIGIN+path,'fetch','GET')
        await g.capture(r)
        body=await probe.get_once(g.page,g,path)
        assert body['data']['independent_fixture']==name
    g.page.evaluate.assert_not_awaited()
    assert len(p.business)==6 and not g.scripts
    for path in ['/qieti/api/unknown',policy.FIXED['page14'].replace('pageNum=14','pageNum=15'),
        policy.FIXED['book'].replace('46007447','46006966')]:
        assert not p.decide('GET',gate.ORIGIN+path,'Fetch')[0]
    assert not p.decide('POST',gate.ORIGIN+policy.FIXED['frames'],'Fetch')[0]
    return {'six_fixed_captured_GETs_consumed_without_resend':True,'additional_fetches':0,
        'unknown_book_page_API_write_blocked':True,'total_HTTP_cap_claimed':False,
        'note':'Original allowed same-origin session/static helper resources remain; six+two does not mean all HTTP limited to8.'}

async def fixed_failure_and_terminal():
    h=Harness();h.fail_source=True;result=await h.observe()
    assert h.code==2 and result['steps']['source']=='FAILED' and h.original.await_count==0
    assert all(result['steps'][k]=='NOT_RUN' for k in ['page14','original14','mapping14','page173','original173','mapping173']+list(SAMPLE_STEPS))
    late=Harness();r=await late.observe(late=True)
    assert late.code==2 and r['outcome']=='ERROR' and r['sample']['status']=='NOT_RUN'
    assert r['sample']['content_acceptable'] is False and not r['write_eligible'] and r['schema_status']=='UNKNOWN'
    return {'failed_fixed_read':result,'late_guard':r,'successors_respected':True}

NOW=datetime(2031,2,3,tzinfo=timezone.utc)
def docs():
    d={**gate.scope_binding(CANDIDATE),'tls_mode':'STRICT','live_authorized':True,'certificate_exception_authorized':False}
    r={**gate.scope_binding(CANDIDATE),'result':'ACCEPTED_OFFLINE_ONLY'}
    a={**gate.fixed_fields(CANDIDATE,'b'*64),'tls_mode':'STRICT','not_before':NOW.isoformat(),
        'expires_at':(NOW+timedelta(minutes=15)).isoformat()}
    return a,d,r
def valid(a,d,r,now=NOW,exception=False):
    d_raw=json.dumps(d,sort_keys=True).encode();r_raw=json.dumps(r,sort_keys=True).encode()
    a={**a,'user_decision_sha256':gate.sha(d_raw),'independent_report_sha256':gate.sha(r_raw)}
    raw=json.dumps(a,sort_keys=True).encode()
    return gate.validate_activation(raw,gate.sha(raw),CANDIDATE,'b'*64,d_raw,r_raw,explicit_live=True,exception=exception,now=now)
def scope_gate():
    a,d,r=docs();approval=valid(a,d,r)
    assert gate.context_options(approval,NOW)=={'ignore_https_errors':False}
    marker=gate.marker(approval);assert marker['sample_limit']==0 and marker['scope']==gate.SCOPE
    changes={'scope':'OLD_SAMPLE_SCOPE','sample_limit':1,'automatic_schema_confirmation':True,
        'fixed_business_get_count':11,'original_get_count':3,'workflow_commit':'f04c1579353de3fd2006b533d5c792c80190f5b8',
        'candidate_manifest_sha256':'f'*64}
    rejected=[]
    for doc_index in range(3):
        for field,value in changes.items():
            values=list(docs());values[doc_index][field]=value
            rejected.append({'document':doc_index,'field':field,'code':stops(lambda:valid(*values))})
    for name in ['scope','sample_limit']:
        values=list(docs());values[2].pop(name);stops(lambda:valid(*values))
    a,d,r=docs();a['sample_limit']=False;stops(lambda:valid(a,d,r))
    a,d,r=docs();d['live_authorized']=False;stops(lambda:valid(a,d,r))
    a,d,r=docs();stops(lambda:valid(a,d,r,now=NOW+timedelta(minutes=15)))
    stops(lambda:valid(a,d,r,exception=True))
    return {'pure_synthetic_scope_approval_only':True,'scope_mutation_rejections':rejected,
        'missing_scope_typed_sample0_unapproved_TLS_expiry_rejected':True,
        'marker_value_only_no_real_marker_created':True,'live_authorized_by_review':False}

def templates_and_candidate():
    e=ROOT/'docs/evidence/A16/current-readonly/revisions/observation-only'
    assert gate.sha((e/'candidate-manifest.json').read_bytes())==CANDIDATE
    templates={}
    for name in ['activation','decision','independent-report']:
        item=json.loads((e/(name+'-template-NONEXECUTABLE.json')).read_bytes())
        assert all(item[k]==v and type(item[k]) is type(v) for k,v in gate.scope_binding(CANDIDATE).items())
        templates[name]=item
    assert templates['activation']['not_before'] is None and templates['activation']['profile_fingerprint'] is None
    assert templates['decision']['live_authorized'] is False and templates['independent-report']['result']=='NOT_REVIEWED'
    assert not hasattr(probe,'current_code') and not hasattr(probe,'sample_order') and not hasattr(probe,'bound_content')
    return {'candidate_digest':CANDIDATE,'scope':gate.SCOPE,'sample_limit':0,
        'automatic_schema_confirmation':False,'templates_not_executable':True,
        'formal_gate_report_compatible_result':'ACCEPTED_OFFLINE_ONLY with exact restricted scope; separate limited review result required',
        'original_R02':'REWORK_NOT_REPAIRED'}

CASES=[('NO_SAMPLE_REGISTRATION_OR_CACHE_BYPASS',disabled_register_and_get),('BOTH_GUARDS_HARD_DENY',both_guard_paths),
    ('COLLECT_NO_PARSER_NO_SAMPLES',actual_collect_ignores_assets),('STATIC_EXACT_PRIVATE_PUBLIC_SANITIZED',exact_static_bytes),
    ('UNAPPROVED_STATIC_NOT_READ',capture_rejects_unapproved),('SIX_FIXED_CACHE_SCOPE',fixed_cache_and_scope),
    ('FIRST_READ_FAILURE_AND_LATE_GUARD',fixed_failure_and_terminal),('SCOPE_GATE_TYPED_BINDINGS',scope_gate),
    ('TEMPLATE_AND_NO_ENABLE_SWITCH',templates_and_candidate)]
records=[];first=None
with patch.object(ctypes,'WinDLL',deny('NATIVE')),patch.object(subprocess,'Popen',deny('POPEN')), \
    patch.object(socket.socket,'connect',deny('SOCKET_CONNECT')),patch.object(socket.socket,'bind',deny('SOCKET_BIND')), \
    patch.object(probe.native,'profile_binding',deny('PROFILE')):
    for name,operation in CASES:
        if first:records.append({'case':name,'status':'NOT_RUN','reason':'FIRST_UNEXPECTED_FAILURE_STOP'});continue
        try:
            value=asyncio.run(operation()) if asyncio.iscoroutinefunction(operation) else operation()
            records.append({'case':name,'status':'PASS','actual':value})
        except BaseException as error:
            first={'case':name,'type':type(error).__name__,'detail':str(error)}
            records.append({'case':name,'status':'FAIL','failure':first})
result={'task':'A16','candidate_manifest_sha256':CANDIDATE,'scope':gate.SCOPE,'cases':records,
    'result':'ALL_NEW_CONTROLS_PASS' if first is None else 'REWORK','first_failure':first,
    'resource_attempts':ATTEMPTS,'parser_qualification_calls':PARSER_CALLS,'duration_ms':round((time.monotonic()-START)*1000),
    'old_suites_or_parser_replayed':False,'real_browser_network_profile_native_or_occupancy':False,
    'harness_boundary':'New18 Harness transport/UI/image/file boundary fakes; actual new collect, policy, guards, get_once, capture, gate executed.'}
with (OUT/'independent-controls-result.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps({'result':result['result'],'statuses':{r['case']:r['status'] for r in records},
    'first_failure':first,'resource_attempts':ATTEMPTS,'parser_calls':PARSER_CALLS,'duration_ms':result['duration_ms']}))
raise SystemExit(1 if first else 0)
