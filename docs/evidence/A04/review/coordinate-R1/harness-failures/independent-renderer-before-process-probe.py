"""Local HTTP surrogate, independent OpenCV pixel oracle, real temporary Edge.

Only 127.0.0.1 is reachable from page routes. Policy URLs are synthetic labels
inside a request facade; route.fetch still fetches the real localhost request.
No persistent context, login helper, actual credentials, or live platform access.
"""
import copy,hashlib,json,math,os,sys,threading,traceback
from collections import Counter
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from types import SimpleNamespace
OUT=Path(__file__).resolve().parents[1]/'independent-renderer'
OUT.mkdir(parents=True,exist_ok=False)
STAGE=Path('D:/1800/.local/stages/A04-review/coordinate-R1');ROOT=STAGE/'frozen input with spaces'
sys.path.insert(0,str(ROOT/'src'));os.environ.update(TEMP=str(STAGE),TMP=str(STAGE))
import cv2,numpy as np,psutil
from PIL import Image
from playwright.sync_api import sync_playwright
from annotation.source.usense.viewer_observation import DRAW_OBSERVER,observe_draw
from annotation.delivery.usense_readonly import ViewerMapping,binding_from_file,check_reference_points,CoordinateError
from annotation.runtime.browser.session import HeadlessSession

counts=Counter();route_counts=Counter();cases=[];guard_results=[];error=None
browser_closed=False;context_closed=False;server_closed=False;pw_stopped=False
children_before={p.pid for p in psutil.Process().children(recursive=True)};owned_children=set()
patches={14:[[65,150,280,250],[325,925,525,1085],[650,1335,1000,1425]],
         173:[[160,140,440,220],[215,1125,420,1250],[725,1360,980,1515]]}
source={p:(ROOT/f'docs/evidence/A04/execution/live-run-09/assets/page-{p}.jpg').read_bytes() for p in (14,173)}
def save(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
save(OUT/'reference-selection.json',{'selection':'Original images visually inspected before browser run; reviewer-selected crops, not delivered patch list',
 'pages':{str(p):{'patches':patches[p],'sha256':hashlib.sha256(source[p]).hexdigest()} for p in source}})
html='''<!doctype html><style>body{margin:0;background:#ddd}.pdf-zone{position:absolute;left:41.5px;top:28.25px;width:620px;height:850px;background:white}canvas{position:absolute;left:27.25px;top:18.5px;width:510.25px;height:740.5px}.pdf-zone:nth-child(2){left:710.5px}</style><div class="pdf-zone"><canvas width="620" height="900"></canvas></div><div class="pdf-zone"><canvas width="620" height="900"></canvas></div>'''
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/':body=html.encode();ctype='text/html';counts['document']+=1
        elif path in ['/upload_images/46007447/46007447_page_13.jpg','/upload_images/46007447/46007447_page_172.jpg']:
            p=14 if path.endswith('_13.jpg') else 173;body=source[p];ctype='image/jpeg';counts['original']+=1
        elif path=='/qieti/api/annotate_ocr/directory/get':body=b'{"code":0,"data":{}}';ctype='application/json';counts['allowed_business_get']+=1
        else:body=b'{}';ctype='application/json';counts['unexpected_get']+=1
        self.send_response(200);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def mutation(self):
        # Never retain request body, query or headers.
        counts['login_post' if self.path=='/qieti/api/user_login/login' else 'mutation_received']+=1
        body=b'{"code":0}';self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    do_POST=mutation;do_PUT=mutation;do_PATCH=mutation;do_DELETE=mutation
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base='http://127.0.0.1:'+str(server.server_port)
session=HeadlessSession(STAGE/'synthetic policy label only') # Never entered.
class RouteFacade:
    def __init__(self,route):
        self.route=route;u=urlsplit(route.request.url)
        self.request=SimpleNamespace(method=route.request.method,url='https://www.usense.com'+u.path+('?' + u.query if u.query else ''))
    def fetch(self,**kwargs):route_counts['guard_fetch_localhost']+=1;return self.route.fetch(**kwargs)
    def fulfill(self,**kwargs):return self.route.fulfill(**kwargs)
    def abort(self,*args,**kwargs):route_counts['guard_abort']+=1;return self.route.abort(*args,**kwargs)
def route(route):
    u=urlsplit(route.request.url)
    if u.scheme!='http' or u.hostname!='127.0.0.1' or u.port!=server.server_port:
        route_counts['nonlocal_aborted']+=1;route.abort();return
    if u.path.startswith('/qieti/api/'):
        session._route(RouteFacade(route));return
    route_counts['local_render_continue']+=1;route.continue_()

def independently_locate(original,target,box,scale):
    # Independent algorithm from delivered sparse matcher: full NCC image search.
    x1,y1,x2,y2=box;w=round((x2-x1)*scale[0]);h=round((y2-y1)*scale[1])
    tpl=cv2.resize(original[y1:y2,x1:x2],(w,h),interpolation=cv2.INTER_LINEAR)
    score=cv2.matchTemplate(target,tpl,cv2.TM_CCOEFF_NORMED)
    _,best,_,location=cv2.minMaxLoc(score)
    if best<.6:raise AssertionError(('weak independent NCC match',best))
    return [location[0]+w/2,location[1]+h/2],best

try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='msedge',headless=True,args=['--disable-background-networking','--no-first-run'])
        context=browser.new_context(viewport={'width':1600,'height':1000},device_scale_factor=2.75,service_workers='block')
        try:
            context.route('**/*',route);context.route_web_socket('**/*',lambda ws:ws.close())
            context.add_init_script(DRAW_OBSERVER);page=context.new_page();page.goto(base,wait_until='load')
            owned_children|={p.pid for p in psutil.Process().children(recursive=True)}-children_before
            browser_version=browser.version
            for pg,zone,index in [(14,0,13),(173,1,172)]:
                original_path=OUT/f'original-{pg}.jpg';original_path.write_bytes(source[pg])
                binding=binding_from_file(original_path,f'review-original-{pg}')
                for label,rx,ry,ctm in [('baseline',.36,.4,[1.1,0,0,.9,9.5,13.25]),
                                       ('nontrivial-scale-pan',.41,.44,[1.04,0,0,.96,15.75,8.125])]:
                    page.evaluate('''async ([zone,url,rx,ry,m])=>{const image=new Image();image.src=url;await image.decode();const canvas=document.querySelectorAll('canvas')[zone],c=canvas.getContext('2d');c.setTransform(1,0,0,1,0,0);c.fillStyle='white';c.fillRect(0,0,canvas.width,canvas.height);c.setTransform(...m);c.drawImage(image,22.75,18.5,image.naturalWidth*rx,image.naturalHeight*ry);}''',
                                  [zone,base+f'/upload_images/46007447/46007447_page_{index}.jpg',rx,ry,ctm])
                    observation=observe_draw(page,zone,binding,pg,index)
                    canvas=page.locator('canvas').nth(zone);pane=page.locator('.pdf-zone').nth(zone)
                    import base64
                    cp=OUT/f'{pg}-{label}-canvas.png';cp.write_bytes(base64.b64decode(canvas.evaluate("c=>c.toDataURL('image/png')").split(',')[1]))
                    sp=OUT/f'{pg}-{label}-pane.png';pane.screenshot(path=str(sp),scale='css')
                    origin=cv2.imdecode(np.frombuffer(source[pg],dtype=np.uint8),cv2.IMREAD_GRAYSCALE)
                    painted=cv2.imread(str(cp),cv2.IMREAD_GRAYSCALE);shot=cv2.imread(str(sp),cv2.IMREAD_GRAYSCALE)
                    # Oracle scale comes from independent local renderer constants, not ViewerMapping.
                    draw_scale=[rx*ctm[0],ry*ctm[3]];pane_rect=pane.bounding_box()
                    screen_scale=[draw_scale[0]*510.25/620,draw_scale[1]*740.5/900]
                    refs=[];scores=[]
                    for box in patches[pg]:
                        measured,cs=independently_locate(origin,painted,box,draw_scale)
                        measured_shot,ss=independently_locate(origin,shot,box,screen_scale)
                        refs.append({'original':[(box[0]+box[2])/2,(box[1]+box[3])/2],
                            'measured_canvas':measured,'measured_css':[pane_rect['x']+measured_shot[0],pane_rect['y']+measured_shot[1]]})
                        scores.append({'canvas_ncc':cs,'screenshot_ncc':ss})
                    mapping=ViewerMapping(binding,pg,index,observation);checks=check_reference_points(mapping,refs)
                    negative=[]
                    for field,i,delta in [('canvas_ctm',4,19),('css_rect',0,13),('draw_destination',2,30)]:
                        bad=copy.deepcopy(observation);bad[field][i]+=delta
                        try:check_reference_points(ViewerMapping(binding,pg,index,bad),refs)
                        except CoordinateError as e:negative.append({'field':field,'code':e.code})
                        else:raise AssertionError('wrong mapping not rejected')
                    case={'page':pg,'label':label,'observation':observation,'checks':checks,'scores':scores,
                      'negative_probes':negative,'max_canvas_error':max(r['canvas_error'] for r in checks),
                      'max_css_error':max(r['css_error'] for r in checks),'max_original_error':max(r['original_error'] for r in checks),
                      'status':'PASS','platform_observation':False}
                    cases.append(case);save(OUT/f'{pg}-{label}.json',case)
                    print(json.dumps({k:case[k] for k in ['page','label','max_canvas_error','max_css_error','max_original_error','status']}),flush=True)
            # Real browser requests to localhost, with synthetic platform policy labels.
            for method in ['POST','PUT','PATCH','DELETE']:
                result=page.evaluate("async ([url,method])=>{try{await fetch(url,{method,body:'{}'});return 'sent'}catch(_){return 'blocked'}}",[base+'/qieti/api/annotate_pic/commit_unified_submit',method])
                assert result=='blocked';guard_results.append({'method':method,'result':result})
            assert counts['mutation_received']==0 and route_counts['guard_fetch_localhost']==0
            response=page.evaluate("async url=>(await fetch(url)).status",base+'/qieti/api/annotate_ocr/directory/get?file_id=46007447')
            assert response==200 and counts['allowed_business_get']==1
            session.policy.login_window=True
            for expected in ['sent','blocked']:
                actual=page.evaluate("async url=>{try{await fetch(url,{method:'POST',body:'{}'});return 'sent'}catch(_){return 'blocked'}}",base+'/qieti/api/user_login/login')
                assert actual==expected
            session.policy.login_window=False
            assert counts['login_post']==1 and route_counts['guard_fetch_localhost']==2
        finally:
            context.close();context_closed=True;browser.close();browser_closed=not browser.is_connected()
    pw_stopped=True
except Exception:
    error=traceback.format_exc();(OUT/'failure.txt').write_text(error,encoding='utf-8')
finally:
    server.shutdown();server.server_close();thread.join(timeout=2);server_closed=not thread.is_alive()
    # Observe only PIDs that were descendants of this test, never enumerate user profiles.
    alive=[]
    for pid in owned_children:
        try:
            if psutil.pid_exists(pid) and psutil.Process(pid).status()!=psutil.STATUS_ZOMBIE:alive.append(pid)
        except psutil.NoSuchProcess:pass
    r={'mode':'LOCAL_HTTP_SURROGATE_WITH_HISTORICAL_PIXELS','platform_observation':False,
       'browser_version':locals().get('browser_version'),'dpr':2.75,'image_pages':[14,173],
       'cases':cases,'independent_algorithm':'OpenCV full-image TM_CCOEFF_NORMED; reviewer crops and render constants',
       'network':{'server_counts':dict(counts),'route_counts':dict(route_counts),
                  'guard_cases':guard_results,'actual_platform_requests':0,'policy_label_facade':'Synthetic official URL label; fetch target stays localhost',
                  'audit':session.audit.records},
       'release':{'context_closed':context_closed,'browser_closed':browser_closed,'playwright_stopped':pw_stopped,
                  'local_server_closed':server_closed,'owned_descendant_pids_observed':sorted(owned_children),
                  'owned_descendant_pids_alive_after':alive,'persistent_context_opened':False,'authorized_profile_accessed':False},
       'error':error,'status':'PASS' if not error and not alive and context_closed and browser_closed and server_closed else 'FAIL'}
    save(OUT/'result.json',r);print(json.dumps({k:r[k] for k in ['status','release','error']},ensure_ascii=False),flush=True)
raise SystemExit(0 if r['status']=='PASS' else 1)
