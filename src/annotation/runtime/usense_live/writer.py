"""One existing-question native update. Separate from the GET-only capture entry.

An explicit reviewed plan and current authorization reference are required.
One durable stable-identity intent precedes one send. Never auto-retry unknowns.
The caller must run capture in a separate process and compare complete readback.
"""
import argparse, asyncio, base64, json
from datetime import datetime, timezone
from pathlib import Path

from .core import ORIGIN, TARGET, load_binding, tls_launch_arguments, write_new, require, sha, plain_path
from .config import capture_endpoints
from .capture import FETCH
from .update import loads, validate_plan, from_captured_map, check_prewrite, json_same
from .revision import verify_previous_acceptance, same as revision_same
from .release import close_framework, run_owned_writer

POST=ORIGIN+'/qieti/api/annotate_pic/commit_unified_submit'

class ExactPolicy:
 def __init__(self,binding,urls):
  self.binding=binding; self.urls=set(urls); self.counts={}; self.events=[]; self.blocked=False; self.body_sha=None; self.armed=False
 def allow(self,layer,method,url,body=None,redirected=False):
  try:
   self.binding.check()
   allowed=not self.blocked and not redirected
   if method=='POST': allowed=allowed and self.armed and url==POST and isinstance(body,str) and sha(body.encode('utf-8'))==self.body_sha
   else: allowed=allowed and method=='GET' and url in self.urls
   key=(layer,method,url)
   self.counts[key]=self.counts.get(key,0)+1
   allowed=allowed and self.counts[key]==1
  except Exception: allowed=False
  self.events.append({'layer':layer,'method':method,'url_sha256':sha(url.encode()),'allowed':allowed})
  if not allowed: self.blocked=True
  return allowed

PREPARE="""async payload=>{
 const user=JSON.parse(localStorage.getItem('user')||'null');
 if(!user||!user.access_token||typeof user.username!=='string'||!user.username.trim()) throw Error('AUTH_REQUIRED');
 payload.created_by=user.username;
 const body=JSON.stringify(payload);
 window.__usenseNativeBody=body;
 const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(body));
 return {sha256:Array.from(new Uint8Array(digest)).map(x=>x.toString(16).padStart(2,'0')).join(''),created_by_bound:true};
}"""
SEND="""async url=>{
 const user=JSON.parse(localStorage.getItem('user')||'null');
 if(!user||!user.access_token||!window.__usenseNativeBody) throw Error('AUTH_OR_BODY_MISSING');
 const body=window.__usenseNativeBody; delete window.__usenseNativeBody;
 const c=new AbortController(),timer=setTimeout(()=>c.abort(),25000);
 try{
  const r=await fetch(url,{method:'POST',headers:{Authorization:'Bearer '+user.access_token,'Content-Type':'application/json'},body,credentials:'same-origin',redirect:'error',signal:c.signal});
  const bytes=new Uint8Array(await r.arrayBuffer()); if(bytes.length>1000000) throw Error('RESPONSE_TOO_LARGE');
  let binary=''; for(let i=0;i<bytes.length;i+=32768) binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
  return {status:r.status,body_base64:btoa(binary)};
 }finally{clearTimeout(timer);}
}"""

def validate_inputs(plan, baseline, endpoints, ledger_root, authorization_reference, previous_acceptance=None, revision_context=None):
 validate_plan(plan)
 require(isinstance(authorization_reference,str) and bool(authorization_reference.strip()),'CURRENT_WRITE_AUTHORIZATION_REFERENCE_REQUIRED')
 order=plan['target']['question_order']; prefix=f'q{order}_'
 require({n.split('_')[0] for n in endpoints if n.startswith('q')}=={f'q{order}'},'ONE_TARGET_PER_WRITE')
 native={name:loads((baseline/(name+'.json')).read_bytes()) for name in endpoints}
 require(check_prewrite(plan,from_captured_map(native,prefix))['match'],'BASELINE_PLAN_MISMATCH')
 for review in plan['approved_changes'].values():
  source=Path(review['source_ref']); record=Path(review['review_ref'])
  require(source.is_file() and sha(source.read_bytes())==review['source_sha256'],'SOURCE_BYTES_CHANGED')
  require(record.is_file(),'REVIEW_RECORD_MISSING')
 ledger=plain_path(str(ledger_root))
 require(ledger.is_dir(),'LEDGER_DIRECTORY_REQUIRED')
 if previous_acceptance is not None:
  require(plan['mutation_required'] is True,'REVISION_REQUIRES_EXPLICIT_MUTATION')
  verified=verify_previous_acceptance(previous_acceptance,plan,native,ledger)
  claim=ledger/(verified['intent_key']+'.json')
  if revision_context is not None:revision_context.update(verified)
 else:
  claim=ledger/(plan['ledger_key']+'.json')
  require(not claim.exists(),'EXISTING_INTENT_READBACK_REQUIRED_NO_RETRY')
 return native,claim


async def execute(*,config_path,config_sha256,plan_path,plan_sha256,baseline,ledger_root,authorization_reference,previous_acceptance=None):
 raw=Path(plan_path).read_bytes();require(sha(raw)==plan_sha256,'PLAN_FILE_CHANGED')
 plan=loads(raw); binding=load_binding(config_path,config_sha256)
 require(Path(ledger_root).resolve()==Path(binding.data['profile']['directory']).parent/'usense-existing-ledger','LEDGER_ROOT_MUST_BELONG_TO_BOUND_PROFILE')
 endpoints=capture_endpoints(binding)
 revision={}
 native,claim=validate_inputs(plan,Path(baseline),endpoints,Path(ledger_root),authorization_reference,previous_acceptance,revision)
 binding.check(profile=True)
 run=binding.output;run.mkdir(exist_ok=False)
 result={'schema':'UsenseActualNativeUpdate/v1','operation':'EXISTING_QUESTION_TEXT_UPDATE','book_id':'46007447',
  'status':'PREPARING','plan_sha256':plan['plan_sha256'],'plan_file_sha256':plan_sha256,'config_sha256':config_sha256,
  'target':plan['target'],'run_id':run.name,'post_attempts':0,'save_success':False,'independent_readback':'PENDING',
  'authorization_reference':authorization_reference,'ledger_key':plan['ledger_key'],'intent_key':claim.stem}
 write_new(run/'claim.json',{'operation':'EXISTING_QUESTION_TEXT_UPDATE','config_sha256':config_sha256,'plan_file_sha256':plan_sha256})
 (run/'plan.json').write_bytes(raw)
 if revision:
  write_new(run/'revision-validation.json',revision)
  result['revision']={key:value for key,value in revision.items() if key!='evidence_file_sha256'}
  result['revision_validation_sha256']=sha((run/'revision-validation.json').read_bytes())
 context=runtime=None;pending=set()
 policy=ExactPolicy(binding,[TARGET]+[ORIGIN+p for p in endpoints.values()])
 try:
  from playwright.async_api import async_playwright
  args=await asyncio.to_thread(tls_launch_arguments,binding)
  runtime=await async_playwright().start()
  context=await runtime.chromium.launch_persistent_context(binding.data['profile']['directory'],channel='msedge',headless=True,
   offline=True,service_workers='block',ignore_https_errors=False,accept_downloads=False,timeout=15000,
   args=['--disable-extensions','--disable-background-networking']+args)
  if not context.pages:await context.new_page()
  for extra in list(context.pages[1:]):await extra.close()
  page=context.pages[0];await page.goto('about:blank')
  async def route(r):
   req=r.request
   if policy.allow('context',req.method,req.url,req.post_data,req.redirected_from is not None):
    if req.url==TARGET:await r.fulfill(status=200,content_type='text/html',body='<!doctype html><title>Usense program writer</title><link rel="icon" href="data:,">')
    else:await r.continue_()
   else:await r.abort('blockedbyclient')
  await context.route('**/*',route)
  async def block_ws(ws):policy.blocked=True;await ws.close()
  await context.route_web_socket('**/*',block_ws)
  cdp=await context.new_cdp_session(page)
  async def paused(event):
   req=event['request'];allowed=policy.allow('native',req['method'],req['url'],req.get('postData'),bool(event.get('redirectedRequestId')))
   if allowed:await cdp.send('Fetch.continueRequest',{'requestId':event['requestId']})
   else:await cdp.send('Fetch.failRequest',{'requestId':event['requestId'],'errorReason':'BlockedByClient'})
  def schedule(coro):
   task=asyncio.create_task(coro);pending.add(task)
   def done(t):
    pending.discard(t)
    if not t.cancelled() and t.exception() is not None:policy.blocked=True
   task.add_done_callback(done)
  cdp.on('Fetch.requestPaused',lambda e:schedule(paused(e)))
  await cdp.send('Fetch.enable',{'patterns':[{'urlPattern':'*','requestStage':'Request'}]})
  async def extra_page(p):policy.blocked=True;await p.close()
  context.on('page',lambda p:schedule(extra_page(p)))
  await context.set_offline(False)
  await page.goto(TARGET,wait_until='domcontentloaded',timeout=30000)
  require(not policy.blocked,'GUARD_BLOCKED')
  fresh={}
  for name,path in endpoints.items():
   read=await asyncio.wait_for(page.evaluate(FETCH,path),timeout=30)
   require(read['status']==200,'PREWRITE_READ_FAILED')
   body=base64.b64decode(read['body_base64'],validate=True)
   (run/('before-'+name+'.json')).write_bytes(body)
   fresh[name]=loads(body)
   require(all(policy.counts.get((layer,'GET',ORIGIN+path),0)==1 for layer in ('context','native')),'PREWRITE_DUAL_GUARD_UNPROVEN')
   require(json_same(fresh[name],native[name]),'BEFORE_CHANGED_'+name)
  require(check_prewrite(plan,from_captured_map(fresh,f"q{plan['target']['question_order']}_"))['match'],'PREWRITE_CHANGED')
  require(not policy.blocked,'GUARD_BLOCKED')
  if not plan['mutation_required']:
   result['status']='NO_OP_CURRENT_STATE_CONFIRMED'
  else:
   prepared=await asyncio.wait_for(page.evaluate(PREPARE,plan['payload_candidate']),timeout=10)
   require(prepared['created_by_bound'] is True,'ACTOR_NOT_BOUND')
   policy.body_sha=prepared['sha256']
   result.update(status='PREWRITE_MATCHED',native_body_sha256=policy.body_sha,created_by_source='authenticated username bound inside page; not exported')
   if revision:
    require(revision_same(revision,verify_previous_acceptance(previous_acceptance,plan,fresh,Path(ledger_root))),'PREVIOUS_ACCEPTANCE_EVIDENCE_CHANGED')
   sent_at=datetime.now(timezone.utc).isoformat()
   write_new(claim,{'operation':'EXISTING_QUESTION_TEXT_UPDATE','run_id':run.name,'target':plan['target'],
    'ledger_key':plan['ledger_key'],'plan_sha256':plan['plan_sha256'],'native_body_sha256':policy.body_sha,
    'intent_key':claim.stem,'previous_acceptance_sha256':revision.get('previous_acceptance_sha256'),
    'intent_at':sent_at,'automatic_retry_allowed':False,'state':'INTENT_REQUIRES_INDEPENDENT_READBACK'})
   result.update(status='SEND_INTENT_RECORDED',send_intent_at=sent_at,post_attempts=1)
   write_new(run/'send-intent.json',result)
   policy.armed=True
   response=await asyncio.wait_for(page.evaluate(SEND,POST),timeout=35)
   policy.armed=False
   body=base64.b64decode(response.pop('body_base64'),validate=True)
   (run/'native-receipt.json').write_bytes(body);receipt=loads(body)
   result.update(status='RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK',http_status=response['status'],receipt_sha256=sha(body),
    response_code=receipt.get('code'),post_layers={layer:policy.counts.get((layer,'POST',POST),0) for layer in ('context','native')})
   require(not policy.blocked and all(v==1 for v in result['post_layers'].values()),'POST_BARRIERS_NOT_CONFIRMED')
   expected={'code':0,'message':'success','data':{'inserted':False,'question_order':plan['target']['question_order'],
    'inserted_question_node':None,'success':True,'append_at_global_end':False}}
   require(response['status']==200 and json_same(receipt,expected),'RECEIPT_NOT_EXACT_SUCCESS')
   result['receipt_exact_success']=True
 except BaseException as exc:
  result['status']='UNKNOWN_DO_NOT_RETRY' if result['post_attempts'] else 'BLOCKED_BEFORE_SEND'
  result['error_type']=type(exc).__name__;result['error_code']=getattr(exc,'code',None)
 finally:
  policy.armed=False
  policy.blocked=True
  result['business_status_before_release']=result['status']
  release=await close_framework(context,runtime,pending)
  result['release']=release
  if not release['context_runtime_release_confirmed']:result['status']='RELEASE_UNPROVEN_NO_RETRY'
  write_new(run/'network-events.json',policy.events)
  result['finished_at']=datetime.now(timezone.utc).isoformat()
  write_new(run/'execution-result.json',result)
 return result


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('config','sha256','plan','plan-sha256','baseline','ledger-root','authorization-reference'):
  parser.add_argument('--'+name,required=True)
 parser.add_argument('--previous-acceptance')
 args=parser.parse_args()
 result=run_owned_writer(execute(config_path=args.config,config_sha256=args.sha256,plan_path=args.plan,plan_sha256=args.plan_sha256,
  baseline=args.baseline,ledger_root=args.ledger_root,authorization_reference=args.authorization_reference,previous_acceptance=args.previous_acceptance))
 print(json.dumps(result,ensure_ascii=False),flush=True)
 return 0 if result['status'] in ('NO_OP_CURRENT_STATE_CONFIRMED','RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK') else 2

if __name__=='__main__':raise SystemExit(main())

