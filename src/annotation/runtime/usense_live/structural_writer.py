"""Explicit single-send structural transport, reusing owned runtime/FETCH/SEND.

Only an apply plan bound to an observed preview or one reviewed insertion draft
is eligible. This writer never accepts readback, resolves UNKNOWN or retries.
"""
import argparse
import asyncio
import base64
import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re

from .core import ORIGIN,TARGET,OwnedReadonlyContext,ReadonlyPolicy,load_binding,sha,write_new,require,utc
from .capture import FETCH
from .writer import SEND
from .config import endpoints
from . import structure as s, new_question as n, directory_apply as da, update as u
from .batch import ref_bytes

PREPARE_APPLY = r"""async payload=>{
 const user=JSON.parse(localStorage.getItem('user')||'null');
 if(!user||!user.access_token)throw Error('AUTH_REQUIRED');
 window.__usenseNativeBody=JSON.stringify(payload);
 const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(window.__usenseNativeBody));
 return {sha256:Array.from(new Uint8Array(digest)).map(x=>x.toString(16).padStart(2,'0')).join('')};
}"""
PREPARE_INSERT = r"""async payload=>{
 const user=JSON.parse(localStorage.getItem('user')||'null');
 if(!user||!user.access_token||typeof user.username!=='string'||!user.username.trim()||typeof user.id!=='string'||!/^\d+$/.test(user.id))throw Error('AUTH_REQUIRED');
 if(payload.created_by!==null||payload.annotations_upsert.some(r=>r.user_id!==null))throw Error('UNBOUND_NEW_ACTORS_REQUIRED');
 payload.created_by=user.username;for(const row of payload.annotations_upsert)row.user_id=user.id;
 window.__usenseNativeBody=JSON.stringify(payload);
 const d=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))).map(x=>x.toString(16).padStart(2,'0')).join('');
 return {sha256:await d(window.__usenseNativeBody),runtime_actor_sha256:await d(user.username),runtime_user_id_sha256:await d(user.id)};
}"""


def endpoint_map(before):
    identities=s.full_snapshot(before)
    pages=sorted(int(name[5:]) for name in before if name.startswith('page_'))
    require(len(pages)<=8 and len(identities)<=100,'STRUCTURAL_EXPLICIT_SCOPE_TOO_LARGE')
    paths=endpoints((),pages,source=True)
    for q in range(1,len(identities)+1):paths.update(endpoints([q]))
    require(set(paths)==set(before),'STRUCTURAL_COMPLETE_ENDPOINT_SCOPE_REQUIRED')
    return paths


def validate_plan(plan,mode):
    if mode=='apply':return da.validate(plan)
    require(mode=='insert' and plan.get('schema')==n.SCHEMA,'STRUCTURAL_EXPLICIT_MODE_REQUIRED')
    rebuilt=n.make_new_draft(plan['before_full'],plan['candidate'],plan['scope_review'],plan['content_review'],plan['protocol'],plan['baseline_observed_at'])
    require(u.json_same(plan,rebuilt),'STRUCTURAL_INSERT_PLAN_CHANGED')
    return plan


def validate_inputs(plan,mode,baseline,ledger,authorization_reference):
    require(type(authorization_reference) is str and bool(authorization_reference.strip()),'CURRENT_STRUCTURAL_AUTHORIZATION_REQUIRED')
    validate_plan(plan,mode);paths=endpoint_map(plan['before_full'])
    native={name:u.loads((Path(baseline)/(name+'.json')).read_bytes()) for name in paths}
    require(all(u.json_same(native[name],plan['before_full'][name]) for name in paths),'STRUCTURAL_BASELINE_PLAN_MISMATCH')
    s.check_ledger(ledger,plan['ledger_key'])
    for target in plan.get('targets',[plan.get('candidate',{}).get('anchor')]):
        s.check_ledger(ledger,'usense-existing-'+u.digest({k:target[k] for k in ('book_id','node_id','info_id')}))
    return native,paths,Path(ledger)/(plan['ledger_key']+'.json')


class OnePostPolicy(ReadonlyPolicy):
    def __init__(self,binding,paths,post,plan_path,plan_sha):
        super().__init__(binding)
        self.rules={TARGET:{'resource_types':['document'],'max_requests':1},
          **{ORIGIN+path:{'resource_types':['fetch','xhr'],'max_requests':1} for path in paths.values()}}
        self.post,self.plan_path,self.plan_sha=post,Path(plan_path),plan_sha
        self.armed=False;self.sealed=False;self.body_sha=None;self.post_counts={}
    def check(self):
        self.binding.check();require(sha(self.plan_path.read_bytes())==self.plan_sha,'STRUCTURAL_PLAN_FILE_CHANGED')
    def decide(self,layer,method,url,kind,*,redirected=False):
        self.check()
        if layer not in ('context','native'):self.blocked=True
        count=len(self.events)
        allowed=super().decide(layer,method,url,kind,redirected=redirected)
        # All-23 capture exceeds the GET-only owner's small log cap. Preserve
        # every event for full independent verification, still without bodies.
        if count>=256:self.events.append({'layer':layer,'method':method,'url_sha256':sha(url.encode()),'allowed':allowed,'redirected':bool(redirected)})
        return allowed
    def allow_post(self,layer,method,url,body,redirected):
        try:
            self.check();self.post_counts[layer]=self.post_counts.get(layer,0)+1
            allowed=(layer in ('context','native') and not self.blocked and not self.sealed and self.armed and
              method=='POST' and url==self.post and not redirected and type(body) is str and sha(body.encode())==self.body_sha and self.post_counts[layer]==1)
        except Exception:allowed=False
        self.events.append({'layer':layer,'method':method,'url_sha256':sha(url.encode()),'allowed':allowed})
        if not allowed:self.blocked=True
        return allowed


class StructuralContext(OwnedReadonlyContext):
    def __init__(self,binding,paths,post,plan_path,plan_sha):
        super().__init__(binding)
        self.policy=OnePostPolicy(binding,paths,post,plan_path,plan_sha)
    async def route(self,route):
        req=route.request
        if req.method!='POST':return await super().route(route)
        if self.policy.allow_post('context',req.method,req.url,req.post_data,req.redirected_from is not None):await route.continue_()
        else:await route.abort('blockedbyclient')
    async def paused(self,event):
        req=event.get('request',{})
        if req.get('method')!='POST':return await super().paused(event)
        allowed=self.policy.allow_post('native',req['method'],req['url'],req.get('postData'),bool(event.get('redirectedRequestId')))
        if allowed:await self.cdp.send('Fetch.continueRequest',{'requestId':event['requestId']})
        else:await self.cdp.send('Fetch.failRequest',{'requestId':event['requestId'],'errorReason':'BlockedByClient'})


def sync_intent(stream):
    """A narrow durability boundary; failures must prevent arming the POST."""
    stream.flush();os.fsync(stream.fileno())


async def record_and_send(page,policy,plan,mode,claim,run,result):
    validate_plan(plan,mode)
    prepared=await asyncio.wait_for(page.evaluate(PREPARE_APPLY if mode=='apply' else PREPARE_INSERT,copy.deepcopy(plan['request']['body'])),10)
    require(type(prepared.get('sha256')) is str and re.fullmatch('[0-9a-f]{64}',prepared['sha256']),'STRUCTURAL_BODY_BINDING_REQUIRED')
    if mode=='insert':
        require(all(type(prepared.get(k)) is str and re.fullmatch('[0-9a-f]{64}',prepared[k]) for k in
          ('runtime_actor_sha256','runtime_user_id_sha256')),'STRUCTURAL_RUNTIME_ACTOR_BINDING_REQUIRED')
        result['runtime_actor_hashes']={k:prepared[k] for k in ('runtime_actor_sha256','runtime_user_id_sha256')}
    policy.check();validate_plan(plan,mode)
    policy.body_sha=prepared['sha256'];sent=datetime.now(timezone.utc).isoformat()
    intent={'schema':'UsenseStructuralIntent/v1','operation':mode,'ledger_key':plan['ledger_key'],
      'plan_sha256':plan['plan_sha256'],'run_id':run.name,'native_body_sha256':policy.body_sha,'intent_at':sent,
      'automatic_retry_allowed':False,'state':'INTENT_REQUIRES_INDEPENDENT_FULL_READBACK'}
    # Exclusive creation and flush+fsync complete before either POST barrier arms.
    with Path(claim).open('x',encoding='utf-8') as stream:
        json.dump(intent,stream,ensure_ascii=False,allow_nan=False);sync_intent(stream)
    result.update(status='SEND_INTENT_RECORDED',post_attempts=1,send_intent_at=sent,native_body_sha256=policy.body_sha)
    write_new(run/'send-intent.json',result)
    policy.armed=True
    try:response=await asyncio.wait_for(page.evaluate(SEND,policy.post),35)
    finally:policy.armed=False;policy.sealed=True
    raw=base64.b64decode(response['body_base64'],validate=True)
    with (run/'native-receipt.json').open('xb') as stream:stream.write(raw)
    result.update(http_status=response['status'],receipt_sha256=sha(raw),post_layers=dict(policy.post_counts))
    require(response['status']==200 and not policy.blocked and policy.post_counts=={'context':1,'native':1},'STRUCTURAL_POST_OR_GUARDS_UNPROVEN')
    receipt=u.loads(raw)
    require(type(receipt) is dict and type(receipt.get('code')) is int and receipt['code']==0,'STRUCTURAL_RESPONSE_NOT_CODE0_UNKNOWN')
    if mode=='insert':
        data=u._response(receipt,code=(0,));node=data.get('inserted_question_node')
        require(set(data)=={'inserted','question_order','inserted_question_node','success','append_at_global_end'} and data['inserted'] is True and
          data['success'] is True and data['append_at_global_end'] is False and type(data['question_order']) is int and
          data['question_order']==plan['new_order'] and type(node) is dict and tuple(node) in (n.NODE_KEYS,n.OBSERVED_INSERTED_NODE_KEYS) and
          node.get('isQuestion') is True and node.get('label')==node.get('order_in_level')==str(plan['new_order']) and
          u._id(node.get('id')) and node['id'] not in {t['node_id'] for t in plan['old_identities']},'STRUCTURAL_INSERT_RECEIPT_UNKNOWN')
    result.update(status='APPLY_RAW_RESPONSE_REQUIRES_INDEPENDENT_FULL_READBACK' if mode=='apply' else
      'INSERT_RAW_RESPONSE_REQUIRES_INDEPENDENT_FULL_READBACK',save_success=None,platform_acceptance=False)


async def execute(*,mode,config_path,config_sha256,plan_path,plan_sha256,baseline,ledger_root,authorization_reference):
    raw=Path(plan_path).read_bytes();require(sha(raw)==plan_sha256,'STRUCTURAL_PLAN_FILE_CHANGED');plan=u.loads(raw)
    binding=load_binding(config_path,config_sha256)
    require(binding.data['operation']=='READONLY_CAPTURE' and binding.data['static_get']=={'mode':'DISABLED','max_requests':0},'STRUCTURAL_INERT_CONFIG_REQUIRED')
    require(Path(ledger_root).resolve()==Path(binding.data['profile']['directory']).parent/'usense-existing-ledger','STRUCTURAL_PROFILE_LEDGER_MISMATCH')
    native,paths,claim=validate_inputs(plan,mode,baseline,ledger_root,authorization_reference)
    binding.check(profile=True);run=binding.output;owner=None
    result={'schema':'UsenseStructuralExecution/v1','operation':mode,'book_id':u.BOOK,'status':'PREPARING','run_id':run.name,
      'plan_sha256':plan['plan_sha256'],'plan_file_sha256':plan_sha256,'config_sha256':config_sha256,'ledger_key':plan['ledger_key'],
      'post_attempts':0,'save_success':None,'platform_acceptance':False,'automatic_retry_allowed':False,'authorization_reference':authorization_reference}
    result['independent_readback_required']=True
    try:
        owner=StructuralContext(binding,paths,ORIGIN+plan['request']['path'],plan_path,plan_sha256)
        async with owner:
            (run/'plan.json').write_bytes(raw)
            await owner.page.route(TARGET,lambda r:r.fulfill(status=200,content_type='text/html',body='<!doctype html><title>Structural writer</title><link rel="icon" href="data:,">'))
            await owner.navigate();fresh={};observations={}
            for name,path in paths.items():
                binding.check();response=await asyncio.wait_for(owner.page.evaluate(FETCH,path),30)
                require(type(response.get('status')) is int and response['status']==200,'STRUCTURAL_FRESH_READ_FAILED')
                body=base64.b64decode(response['body_base64'],validate=True)
                with (run/('before-'+name+'.json')).open('xb') as stream:stream.write(body)
                fresh[name]=u.loads(body);observations[name]=datetime.now(timezone.utc).isoformat()
                require(u.json_same(fresh[name],native[name]),'STRUCTURAL_FRESH_OBJECT_CHANGED_'+name)
                require(all(type(owner.policy.counts.get((layer,ORIGIN+path))) is int and owner.policy.counts[(layer,ORIGIN+path)]==1
                  for layer in ('context','native')),'STRUCTURAL_FRESH_DUAL_GUARDS_UNPROVEN')
            s.full_snapshot(fresh);binding.check();validate_inputs(plan,mode,baseline,ledger_root,authorization_reference)
            require(not owner.policy.blocked and (datetime.now(timezone.utc)-min(map(utc,observations.values()))).total_seconds()<=900,'STRUCTURAL_FRESH_WINDOW_EXPIRED')
            write_new(run/'fresh-capture-observations.json',observations)
            await record_and_send(owner.page,owner.policy,plan,mode,claim,run,result)
    except BaseException as exc:
        result.update(status='UNKNOWN_DO_NOT_RETRY' if result['post_attempts'] else 'BLOCKED_BEFORE_SEND',error_type=type(exc).__name__,error_code=getattr(exc,'code',str(exc)))
    finally:
        if owner is not None:
            result['release']=dict(owner.release or {},schema='UsenseStructuralWriterRelease/v1',save_attempts=result['post_attempts'])
            result['owner_release_file_semantics']='Base owner tracks lifecycle only; writer save attempts are in this result.'
            if not result['release'].get('context_runtime_release_confirmed'):result['status']='RELEASE_UNPROVEN_NO_RETRY'
        result['finished_at']=datetime.now(timezone.utc).isoformat()
        if run.exists():write_new(run/'execution-result.json',result)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('apply','insert'))
    for key in ('config','sha256','plan','plan-sha256','baseline','ledger-root','authorization-reference'):parser.add_argument('--'+key,required=True)
    a=parser.parse_args(argv)
    try:
        result=asyncio.run(execute(mode=a.mode,config_path=a.config,config_sha256=a.sha256,plan_path=a.plan,plan_sha256=a.plan_sha256,
          baseline=a.baseline,ledger_root=a.ledger_root,authorization_reference=a.authorization_reference))
    except (ValueError,OSError,KeyError,TypeError) as e:
        result={'status':'BLOCKED_BEFORE_SEND','error':getattr(e,'code',type(e).__name__),'automatic_retry_allowed':False}
    import json
    print(json.dumps(result,ensure_ascii=True))
    return 0 if result['status'] in ('APPLY_RAW_RESPONSE_REQUIRES_INDEPENDENT_FULL_READBACK','INSERT_RAW_RESPONSE_REQUIRES_INDEPENDENT_FULL_READBACK') else 2
