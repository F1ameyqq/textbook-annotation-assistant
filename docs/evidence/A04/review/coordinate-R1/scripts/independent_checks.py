"""Independent negative inputs against raw frozen public API. OFFLINE ONLY."""
import contextlib,copy,hashlib,io,json,math,os,shutil,struct,subprocess,sys,traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock,patch
OUT=Path(__file__).resolve().parents[1];STAGE=Path('D:/1800/.local/stages/A04-review/coordinate-R1')
ROOT=STAGE/'frozen input with spaces';sys.path.insert(0,str(ROOT/'src'))
os.environ.update(PYTHONDONTWRITEBYTECODE='1',TEMP=str(STAGE),TMP=str(STAGE))
from PIL import Image
from annotation.contracts import load_bundle
from annotation.source.usense import parse_capture,build_source
from annotation.source.usense.cli import build_exchange,main as cli_main
from annotation.source.usense import collector
from annotation.runtime.browser.guard import BrowserSafetyError,RequestPolicy,NetworkAudit
from annotation.runtime.browser.lease import ProfileLease,LEASE_NAME
from annotation.runtime.browser.session import HeadlessSession
from annotation.delivery.usense_readonly import ViewerMapping,check_reference_points,CoordinateError
from annotation.geometry import GeometryError

BASE=json.loads((ROOT/'tests/fixtures/a04/source/capture.json').read_text(encoding='utf-8'))
ASOF=BASE['observed_at'];CASES=OUT/'independent/cases';CASES.mkdir(parents=True,exist_ok=True)
results=[]
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def record(case,fn):
    try:
        data=fn();r={'case':case,'status':'PASS','detail':data}
    except Exception as e:
        r={'case':case,'status':'FAIL','error_type':type(e).__name__,'detail':str(e),'traceback':traceback.format_exc()}
    results.append(r);print(json.dumps(r,ensure_ascii=False),flush=True)
def pack(name,mutate=None,asset=None):
    path=CASES/name/'input';shutil.copytree(ROOT/'tests/fixtures/a04/source',path)
    cap=copy.deepcopy(BASE)
    if mutate:mutate(cap)
    if asset is not None:(path/cap['pages'][0]['asset_path']).write_bytes(asset)
    save(path/'capture.json',cap)
    return path,cap
def rejected(name,mutate=None,asset=None,codes=None):
    path,cap=pack(name,mutate,asset)
    try:parse_capture(cap,path,now=ASOF)
    except Exception as e:
        if codes:assert getattr(e,'code',None) in codes,(type(e).__name__,getattr(e,'code',None))
        return {'code':getattr(e,'code',type(e).__name__),'location':getattr(e,'path',None)}
    raise AssertionError('invalid input accepted by parse_capture: '+name)
def normal():
    path,cap=pack('O01-normal');parsed=parse_capture(cap,path,now=ASOF)
    bundle=build_exchange(cap,path,as_of=ASOF)
    assert len(bundle.artifacts)==2
    return {'artifacts':[a.kind for a in bundle.artifacts], 'page_count':len(parsed.pages),
      'metadata_page_count':parsed.metadata_page_count,'observed_at':parsed.observed_at,
      'all_capabilities_unknown':all(c.status=='UNKNOWN' for c in bundle.artifacts[1].payload.capabilities)}
record('O01-normal-bundle',normal)
def portable():
    source=CASES/'O01-normal/input';destination=OUT/'independent/relocated complete package with spaces'
    shutil.copytree(source,destination)
    bundle=load_bundle(destination/'bundle.json')
    assert len(bundle.artifacts)==2
    for asset in bundle.artifacts[0].payload.assets:
        assert not Path(asset.path).is_absolute()
    return {'artifacts':2,'destination':str(destination.relative_to(OUT)),'paths':'relative'}
record('O02-relocated-bundle',portable)
def inventory():
    path=CASES/'O01-normal/input';bundle=load_bundle(path/'bundle.json');rows=[]
    for asset in bundle.artifacts[0].payload.assets:
        with Image.open(path/asset.path) as im:
            im.load();assert im.size==(asset.width,asset.height)
        assert hashlib.sha256((path/asset.path).read_bytes()).hexdigest()==asset.sha256
        rows.append({'path':asset.path,'size':[asset.width,asset.height],'sha256':asset.sha256})
    return rows
record('O03-independent-asset-decode',inventory)

record('F01-wrong-book',lambda:rejected('F01-wrong-book',lambda c:c['book'].update(id='46006966'),codes={'TARGET_MISMATCH'}))
record('F01-missing-book',lambda:rejected('F01-missing-book',lambda c:c['book'].pop('id'),codes={'TARGET_MISMATCH'}))
for pg in (14,173):
    record('F02-missing-'+str(pg),lambda pg=pg:rejected('F02-missing-'+str(pg),lambda c:c.update(pages=[p for p in c['pages'] if p['viewer_page']!=pg]),codes={'SOURCE_MISSING'}))
record('F03-missing-data',lambda:rejected('F03-missing-data',lambda c:c['source_metadata'].pop('data'),codes={'INCOMPLETE_RESPONSE'}))
def badjson():
    p=CASES/'F03-json/input';p.mkdir(parents=True);(p/'capture.json').write_text('{"capture_version":',encoding='utf-8')
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf):rc=cli_main(['offline','--input',str(p),'--output',str(p.parent/'out'),'--as-of',ASOF])
    assert rc==2 and not (p.parent/'out').exists()
    return {'returncode':rc,'stdout':buf.getvalue()}
record('F03-truncated-json-public-cli',badjson)
record('F04-missing-directory',lambda:rejected('F04-missing-directory',lambda c:c['annotations']['data'][0].update(directory_id='absent'),codes={'MISSING_REFERENCE'}))
record('F04-missing-question',lambda:rejected('F04-missing-question',lambda c:c['annotations']['data'][0].update(order_in_level='999'),codes={'MISSING_REFERENCE'}))
record('F04-missing-parent',lambda:rejected('F04-missing-parent',lambda c:c['annotations']['data'][0].update(parent_rect_id='absent'),codes={'MISSING_REFERENCE'}))
record('F05-wrong-sha',lambda:rejected('F05-wrong-sha',lambda c:c['pages'][0].update(sha256='0'*64),codes={'RESOURCE_MISMATCH'}))
record('F05-wrong-size',lambda:rejected('F05-wrong-size',lambda c:c['pages'][0].update(width=999),codes={'RESOURCE_MISMATCH'}))
record('F06-html',lambda:rejected('F06-html',asset=b'<html>not an image</html>',codes={'RESOURCE_INVALID'}))
record('F06-http404',lambda:rejected('F06-http404',lambda c:c['pages'][0].update(download_status=404),codes={'RESOURCE_FAILURE'}))
TRUNCATED=b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',4,3)
record('F06-truncated-png-parser',lambda:rejected('F06-truncated-png-parser',asset=TRUNCATED,codes={'RESOURCE_INVALID'}))
def truncated_cli():
    path,cap=pack('F06-truncated-png-cli',asset=TRUNCATED)
    decode_rejected=False
    try:
        with Image.open(path/cap['pages'][0]['asset_path']) as im:im.load()
    except Exception:decode_rejected=True
    output=path.parent/'output';buf=io.StringIO()
    with contextlib.redirect_stdout(buf):rc=cli_main(['offline','--input',str(path),'--output',str(output),'--as-of',ASOF])
    fact={'input_bytes':len(TRUNCATED),'independent_decoder_rejected':decode_rejected,
      'cli_returncode':rc,'cli_stdout':buf.getvalue(),'bundle_created':(output/'bundle.json').exists()}
    if (output/'bundle.json').exists():
        b=load_bundle(output/'bundle.json');fact['bundle_public_loader_accepted']=True
        fact['pages_acquired']=len(b.artifacts[0].payload.pages_acquired)
    save(path.parent/'observation.json',fact)
    assert decode_rejected and rc==2 and not fact['bundle_created'],fact
    return fact
record('F06-truncated-png-public-cli',truncated_cli)
record('F07-stale',lambda:rejected('F07-stale',lambda c:c.update(observed_at='2026-10-15T00:00:00+00:00'),codes={'STALE_CAPTURE'}))
record('F07-incomplete',lambda:rejected('F07-incomplete',lambda c:c.update(complete=False),codes={'INCOMPLETE_RESPONSE'}))
record('F07-count-conflict',lambda:rejected('F07-count-conflict',lambda c:c['source_metadata']['data'].update(total_pages=213),codes={'INCOMPLETE_RESPONSE'}))
for code in [401,403]:
    record('F08-auth-'+str(code),lambda code=code:rejected('F08-auth-'+str(code),lambda c:c.update(directory={'code':code,'data':{}}),codes={'LOGIN_REQUIRED'}))
def business_fail(response,expected):
    try:collector._business(response)
    except BrowserSafetyError as e:assert e.code==expected;return {'code':e.code,'stage':e.stage}
    raise AssertionError('business response accepted')
record('F08-HTTP200-login-body',lambda:business_fail({'http_status':200,'body':{'code':401}},'LOGIN_REQUIRED'))
record('F09-timeout',lambda:business_fail({'error':'TIMEOUT'},'TIMEOUT'))

def conflict():
    p=STAGE/'synthetic lock owner';owner=ProfileLease(p,process_checker=lambda _:0);owner.acquire()
    before=(p/LEASE_NAME).read_bytes();blocked=None
    try:
        try:ProfileLease(p,process_checker=lambda _:0).acquire()
        except BrowserSafetyError as e:blocked=e.code
        assert blocked=='PROFILE_LEASE_CONFLICT' and (p/LEASE_NAME).read_bytes()==before
    finally:released=owner.release()
    again=ProfileLease(p,process_checker=lambda _:0);again.acquire();r=again.release()
    assert released['released'] and r['released']
    return {'second_error':blocked,'first_owner_preserved':True,'reacquired':True,'released':r['released']}
record('F10-owned-lock-conflict',conflict)

def session_failure(stage):
    root=STAGE/('synthetic session '+stage);root.mkdir(exist_ok=True)
    session=HeadlessSession(root,timeout_ms=3)
    page=MagicMock();context=MagicMock(pages=[page]);runtime=MagicMock()
    runtime.chromium.launch_persistent_context.return_value=context
    manager=MagicMock();manager.start.return_value=runtime
    helper=SimpleNamespace(load_credentials=lambda _:SimpleNamespace(username='review-synthetic',password='REVIEW_SYNTHETIC_MARKER'),
       VIEWER_URL='https://www.usense.com/qieti/annotateUnified',LOGIN_URL='https://www.usense.com/qieti/login',
       VIEWER_MARKER='.synthetic',verify_viewer=MagicMock(side_effect=[False,False] if stage=='auth' else [True]),
       require_login_origin=MagicMock(),trusted_url=lambda _:True)
    if stage=='launch':runtime.chromium.launch_persistent_context.side_effect=RuntimeError('REVIEW_SYNTHETIC_MARKER')
    if stage=='navigate':page.goto.side_effect=TimeoutError('REVIEW_SYNTHETIC_MARKER')
    if stage=='close':context.close.side_effect=RuntimeError('REVIEW_SYNTHETIC_MARKER')
    leases=[]
    def lease_factory(p):
        l=ProfileLease(p,process_checker=lambda _:0);leases.append(l);return l
    error=None
    with patch.object(session,'_load_helper',return_value=helper),patch('playwright.sync_api.sync_playwright',return_value=manager),patch('annotation.runtime.browser.session.ProfileLease',side_effect=lease_factory):
        try:
            with session:pass
        except BrowserSafetyError as e:error={'code':e.code,'stage':e.stage}
    assert error is not None and leases and leases[-1].report()['released']
    assert runtime.stop.call_count==1
    # A fresh owner can obtain the same synthetic profile after each failure.
    next_owner=ProfileLease(leases[-1]._profile,process_checker=lambda _:0);next_owner.acquire();next_owner.release()
    assert 'REVIEW_SYNTHETIC_MARKER' not in json.dumps(session.report())
    return {'failure':error,'report':session.report(),'reacquired_after_failure':True,
      'actual_browser_started':False,'helper':'synthetic replacement; no real file read'}
for stage in ['launch','navigate','auth','close']:record('F11-session-'+stage,lambda stage=stage:session_failure(stage))

def blocked_routes():
    s=HeadlessSession(STAGE/'never opened');details=[]
    for method in ['POST','PUT','PATCH','DELETE','OPTIONS','HEAD','TRACE']:
        route=MagicMock();route.request=SimpleNamespace(method=method,url='https://www.usense.com/qieti/api/annotate_pic/commit_unified_submit')
        s._route(route);assert route.fetch.call_count==0 and route.abort.call_count==1
        details.append({'method':method,'fetch_calls':0,'abort_calls':1})
    return {'routes':details,'audit':s.audit.records,'actual_network_requests':0}
record('F12-F14-mutating-routes-before-fetch',blocked_routes)
def login_boundary():
    p=RequestPolicy();url='https://www.usense.com/qieti/api/user_login/login'
    assert p.decide('POST',url)==(False,'METHOD_BLOCKED');p.login_window=True
    assert p.decide('POST',url)==(True,'LOGIN')
    assert not p.decide('POST',url)[0]
    for url in ['https://www.usense.com/qieti/api/user_login/login/other','https://example.invalid/qieti/api/user_login/login','https://www.usense.com/qieti/api/user_login/login?extra=1']:
        assert not RequestPolicy().decide('POST',url)[0]
    return {'allowed_login_attempts':1,'second_blocked':True,'lookalikes_blocked':3}
record('F13-login-single-slot',login_boundary)
def redacted():
    s=HeadlessSession(STAGE/'never opened redaction');r=MagicMock()
    r.request=SimpleNamespace(method='GET',url='https://www.usense.com/qieti/annotateUnified')
    r.fetch.side_effect=RuntimeError('REVIEW_SYNTHETIC_MARKER body cookie token ?auth=1')
    s._route(r);data={'audit':s.audit.records,'transport':s.transport_failures}
    text=json.dumps(data);assert 'REVIEW_SYNTHETIC_MARKER' not in text and 'https' not in text
    assert all(set(v)=={'method','category','decision','status','time'} for v in s.audit.records)
    return data
record('F15-safe-network-errors',redacted)
record('F16-swapped-mapping',lambda:rejected('F16-swapped-mapping',lambda c:c['pages'][0]['mapping_evidence'].update(source_index=14),codes={'PAGE_MAPPING_UNCERTAIN'}))
record('F16-extra-page',lambda:rejected('F16-extra-page',lambda c:c['pages'].append(copy.deepcopy(c['pages'][0])),codes={'INVALID_SCOPE'}))
def capability_scope():
    b=load_bundle(CASES/'O01-normal/input/bundle.json');s=b.artifacts[0];p=b.artifacts[1]
    assert len(s.payload.assets)==3 and s.payload.metadata_page_count==214
    assert all(c.status=='UNKNOWN' for c in p.payload.capabilities)
    return {'acquired':len(s.payload.assets),'metadata':s.payload.metadata_page_count,
      'capabilities':{c.name:c.status for c in p.payload.capabilities}}
record('F17-scope-and-unknown-capabilities',capability_scope)

# Independent numeric oracle: fixed rational arithmetic, no mapping used to generate expected points.
image={'asset_id':'review-grid','width':600,'height':800,'sha256':'9'*64}
obs={'viewer_page':14,'source_index':13,'image':image,'canvas_size':[960,1200],
 'css_rect':[-31.25,42.5,481.5,601.25], 'draw_source':[0,0,600,800],
 'draw_destination':[37.5,24.25,480,1000],'canvas_ctm':[1.25,0,0,.8,15.625,-9.5],
 'viewport':[1600,1100],'scroll':[17,83],'dpr':2.75}
refs=[]
for x,y in [(120,160),(310,470),(480,640)]:
    canvas=[x+62.5,y+9.9]
    refs.append({'original':[x,y],'measured_canvas':canvas,
                 'measured_css':[-31.25+canvas[0]*.5015625,42.5+canvas[1]*(601.25/1200)]})
save(OUT/'independent/geometry-oracle-input.json',{'image':image,'observation':obs,'references':refs,'basis':'Hand-derived canvas=(x+62.5,y+9.9); separate CSS ratios; no tested API called for oracle'})
def geometry_oracle():
    m=ViewerMapping(image,14,13,obs);checks=check_reference_points(m,refs)
    for r in checks:assert r['canvas_error']<1e-10 and r['css_error']<1e-10 and r['original_error']<1e-10
    return {'checks':checks,'geometry_module':type(m.original_domain).__module__}
record('R05-offline-numeric-oracle',geometry_oracle)
def wrong_mapping(field,index,delta):
    bad=copy.deepcopy(obs);bad[field][index]+=delta;m=ViewerMapping(image,14,13,bad)
    roundtrip=m.css_to_original(m.original_to_css((310,470),image,viewer_page=14,source_index=13),image,viewer_page=14,source_index=13)
    assert math.dist(roundtrip,(310,470))<1e-9
    try:check_reference_points(m,refs)
    except CoordinateError as e:assert e.code=='REFERENCE_MAPPING_MISMATCH';return {'self_consistent':True,'independent_rejection':e.code}
    raise AssertionError('wrong self-consistent mapping accepted')
for f,i,d in [('canvas_ctm',4,17),('css_rect',1,12),('draw_destination',2,30)]:
    record('R05-reject-'+f,lambda f=f,i=i,d=d:wrong_mapping(f,i,d))
def wrong_binding(key,value):
    m=ViewerMapping(image,14,13,obs);bad=dict(image,**{key:value})
    try:m.original_to_css((120,160),bad,viewer_page=14,source_index=13)
    except CoordinateError as e:return {'code':e.code}
    raise AssertionError('wrong image binding accepted')
for key,val in [('asset_id','other'),('width',601),('height',801),('sha256','8'*64)]:
    record('R05-binding-'+key,lambda key=key,val=val:wrong_binding(key,val))
for name,mut in [('page',lambda o:o.update(viewer_page=173)),('index',lambda o:o.update(source_index=172)),
 ('rotation',lambda o:o.update(canvas_ctm=[1,.2,0,1,0,0])),('nan',lambda o:o.update(dpr=float('nan'))),
 ('crop',lambda o:o.update(draw_source=[1,0,599,800]))]:
    def invalid(mut=mut):
        bad=copy.deepcopy(obs);mut(bad)
        try:ViewerMapping(image,14,13,bad)
        except CoordinateError as e:return {'code':e.code}
        raise AssertionError('invalid observation accepted')
    record('R05-invalid-'+name,invalid)

summary={'target_commit':'a86eca6ec87ced20dc3a8bcc8f2c87d329e87c39',
 'level':'OFFLINE_INDEPENDENT_ONLY','results':results,'passed':sum(r['status']=='PASS' for r in results),
 'failed':sum(r['status']=='FAIL' for r in results),'actual_platform_requests':0,
 'actual_persistent_sessions':0,'credential_files_read':0}
save(OUT/'independent/results.json',summary)
print('SUMMARY '+json.dumps({k:summary[k] for k in ['passed','failed']}),flush=True)
raise SystemExit(1 if summary['failed'] else 0)
