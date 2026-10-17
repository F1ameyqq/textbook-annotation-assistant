"""One whole-package entry: structure, typed consumers, global mixed DAG, sessions.
New static files only. No product/DB/authority import or execution.
"""
import copy
from datetime import datetime,timedelta
import hashlib
import json
from pathlib import Path
from schema_check import Rejected,need,audit,validate
from oracle_verifier import compare

HOME=Path(__file__).resolve().parent
ROOT=HOME.parents[2]
DATA=HOME/'candidate-final'
EVID=ROOT/'docs/evidence/A03/execution/P2-R2-proposal'
PROFILE='a03-p2-r2-static-2-PROPOSAL'
VERSION='1.3.0-a03-static-proposal'
PREFIX='a03-runtime-event-prefix-2'
ZERO='0'*64
RESULTS=[]
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
def sha(v):return hashlib.sha256(v).hexdigest()
def h(v):return sha(canon(v))
def load(p):return json.loads(p.read_bytes())
def ref(a):return {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}
def isref(v):return isinstance(v,dict) and set(v)=={'artifact_id','revision','kind','content_hash'}
def isres(v):return isinstance(v,dict) and {'path','sha256','media_type'}<=set(v)
def shape(v,name):validate(v,load(DATA/'schemas'/name))
def time(v):return datetime.fromisoformat(v.replace('Z','+00:00'))

class Package:
    def __init__(self,bundle,overrides=None):
        self.bundle=bundle;self.overrides=overrides or {};self.nodes={};self.edges={};self.consumers=[];self.prefixes=[]
        self.index={h(ref(a)):a for a in bundle['artifacts']}
        need(len(self.index)==len(bundle['artifacts']),'DUPLICATE_REF','$')
        need(len({(a['artifact_id'],a['revision']) for a in bundle['artifacts']})==len(bundle['artifacts']),'DUPLICATE_ID','$')
    def artifact(self,r,path):
        need(h(r)in self.index and ref(self.index[h(r)])==r,'EXACT_REF',path);return self.index[h(r)]
    def read(self,r):
        p=(DATA/r['path']).resolve();need(p.is_relative_to(DATA.resolve()),'RESOURCE_ESCAPE',r['path'])
        raw=self.overrides.get(r['path'],p.read_bytes() if p.exists() else None)
        need(raw is not None and sha(raw)==r['sha256'],'RESOURCE_HASH',r['path'])
        return json.loads(raw) if r['media_type']=='application/json' else None
    def edge(self,a,b):self.edges.setdefault(a,set()).add(b);self.edges.setdefault(b,set())
    def consumer(self,node,v,book,scope,declared,path):
        found={};self.scan(v,node,book,scope,found,path,set(),False)
        declared={h(r):r for r in declared};self.consumers.append((found,declared,book,scope,path))
        for r in declared.values():
            target=self.artifact(r,path+'/input_refs');self.edge(node,'A:'+h(ref(target)))
    def scan(self,v,parent,book,scope,found,path,active,resource_root):
        if isref(v):
            a=self.artifact(v,path);self.edge(parent,'A:'+h(ref(a)));found[h(v)]=v;return
        if isres(v):
            node='R:'+v['path']+':'+v['sha256'];self.edge(parent,node);body=self.read(v)
            token=(v['path'],v['sha256'])
            if body is not None and token not in active:
                self.scan(body,node,book,scope,found,v['path'],active|{token},True)
            return
        if isinstance(v,dict):
            if v.get('format_version')==PREFIX:
                need(resource_root,'PREFIX_LOCATION',path);shape(v,'prefix-v2.schema.json');self.prefixes.append(v)
                for k,x in v.items():
                    if k!='frames':self.scan(x,parent,book,scope,found,path+'/'+k,active,False)
                for i,frame in enumerate(v['frames']):
                    e=frame['event'];scope_from_plan=None
                    if e['plan_ref'] is not None:
                        a=self.artifact(e['plan_ref'],path+'/frames');need(a['kind']=='ApplyPlan','FRAME_PLAN_KIND',path);scope_from_plan=a['scope_id']
                    elif e['event']=='TARGET_DRIFT_HOLD' and e['payload'].get('registration_id') and e['payload'].get('source_ref'):
                        source=self.artifact(e['payload']['source_ref'],path+'/registration/source');snapshot=self.artifact(e['payload']['snapshot_ref'],path+'/registration/snapshot')
                        need(source['kind']=='SourceBundle' and snapshot['kind']=='PlatformSnapshot' and source['book_id']==snapshot['book_id']==book and source['scope_id']==snapshot['scope_id']==e['payload']['scope_id'],'FRAME_REGISTRATION_BINDING',path)
                        scope_from_plan=source['scope_id']
                    node=parent+'/F:'+str(i);self.edge(parent,node)
                    need(frame['consumer_scope_id']==scope_from_plan,'FRAME_SCOPE',path+'/frames/'+str(i))
                    self.consumer(node,e,book,scope_from_plan,frame['input_refs'],path+'/frames/'+str(i))
                return
            need('frame_version'not in v,'FRAME_OUTSIDE_TYPED_PREFIX',path)
            for k,x in v.items():self.scan(x,parent,book,scope,found,path+'/'+k,active,False)
        elif isinstance(v,list):
            for i,x in enumerate(v):self.scan(x,parent,book,scope,found,path+'/'+str(i),active,False)
    def validate(self):
        shape(self.bundle,'exchange-v3.schema.json')
        registry=set(load(DATA/'api.json')['registry'])
        for a in self.bundle['artifacts']:
            need(a['kind']in registry,'UNREGISTERED_KIND',a['artifact_id'])
            need(a['schema_version']in(VERSION,'1.1.0-a-recovery-proposal'),'VERSION_SELECTOR',a['artifact_id'])
            self.consumer('A:'+h(ref(a)),a['payload'],a['book_id'],a['scope_id'],a['input_refs'],a['artifact_id'])
        for e in self.bundle['evidence']:self.scan(e['resource'],'E:'+e['evidence_id'],None,None,{},'evidence/'+e['evidence_id'],set(),False)
        active=set();done=set()
        def visit(n):
            need(n not in active,'MIXED_CYCLE',n)
            if n in done:return
            active.add(n)
            for x in self.edges.get(n,()):visit(x)
            active.remove(n);done.add(n)
        for n in list(self.edges):visit(n)
        for found,declared,book,scope,path in self.consumers:
            need(set(found)<=set(declared),'UNDECLARED_REFERENCE',path)
            for r in declared.values():
                target=self.artifact(r,path)
                need(target['book_id']==book,'FOREIGN_BOOK',path)
                need(target['scope_id']==scope,'ORDINARY_SCOPE',path)
        for a in self.bundle['artifacts']:
            need(h({k:v for k,v in a.items() if k!='content_hash'})==a['content_hash'],'ARTIFACT_HASH',a['artifact_id'])
            if a['schema_version']==VERSION and a['kind']=='CheckReport' and a['payload']['stage']=='PRE_APPLY':
                run=self.read(a['payload']['synthetic_run_ref']);shape(run,'pre-run-v2.schema.json')
                need(run['context']==a['payload']['verification_context'],'PRE_CONTEXT',a['artifact_id'])
                need(run['graph_ref']==a['payload']['graph'] and run['admission']=='UNIMPLEMENTED_NO_NATIVE_RUN','PRE_BINDING',a['artifact_id'])
        return self

def session(pkg,basis):
    shape(basis,'basis-v3.schema.json');binding=basis['binding']
    need(basis['gate_binding']==binding and basis['readonly_session_id']==binding['readonly_session_id'],'SESSION_BINDING','basis/gate_binding')
    plan=pkg.artifact(binding['plan_ref'],'basis/plan_ref');need(plan['scope_id']==binding['scope_id'] and plan['book_id']==binding['target_key']['book_id'],'SESSION_IDENTITY','basis/binding')
    action=next(a for a in plan['payload']['actions'] if a['action_id']==binding['action_id'])
    need(h(action)==binding['action_digest'],'ACTION_DIGEST','basis/binding')
    prefix=pkg.read(basis['complete_uncalled_prefix']);shape(prefix,'prefix-v2.schema.json')
    previous=ZERO;heads={0:{'sequence':0,'hash':ZERO}};starts=[];anchor=None;reserved=None
    for n,frame in enumerate(prefix['frames'],1):
        e=frame['event'];p=e['payload']
        need(e['sequence']==n and e['previous_hash']==previous and h({k:v for k,v in e.items() if k!='event_hash'})==e['event_hash'],'EVENT_CHAIN','prefix/'+str(n))
        need(e['target_key']==binding['target_key'] and e['journal_id']==prefix['journal_id'],'JOURNAL_IDENTITY','prefix/'+str(n))
        if e['event']=='PLAN_ACCEPTED' and e['plan_ref']==binding['plan_ref']:anchor={'sequence':n,'hash':e['event_hash']}
        if e['event']=='PLAN_ACTIONS_RESERVED' and e['plan_ref']==binding['plan_ref']:reserved=p['reservations']
        if e['event']=='READONLY_ABSENCE_STARTED':starts.append((n,e))
        if e['plan_ref'] is not None and 'plan_ref'in p:
            need(e['plan_ref']==p['plan_ref'],'EVENT_PLAN_BINDING','prefix/'+str(n))
        if e['event']in('PLAN_ACCEPTED','PLAN_ACTIONS_RESERVED'):
            event_plan=pkg.artifact(e['plan_ref'],'prefix/plan');values=p['actions'if e['event']=='PLAN_ACCEPTED'else'reservations']
            need(values==[{'action_id':x['action_id'],'action_digest':h(x)}for x in event_plan['payload']['actions']],'EVENT_ACTION_BINDING','prefix/'+str(n))
        if e['plan_ref']==binding['plan_ref'] and p.get('action_id')==binding['action_id']:
            need(e['event']not in('WRITE_INTENT_COMMITTED','DISPATCH_PERMIT_ISSUED','DISPATCH_PERMIT_CONSUMED','DISPATCH_STARTED','ACTION_RESULT_COMMITTED','UNATTEMPTED_ABSENCE_COMMITTED'),'ACTION_ALREADY_ATTEMPTED','prefix/'+str(n))
        previous=e['event_hash'];heads[n]={'sequence':n,'hash':previous}
    final={'sequence':len(prefix['frames']),'hash':previous}
    need(prefix['expected_book_head']==basis['expected_event_head']==final,'HFINAL','basis/expected_event_head')
    need(prefix['accepted_anchor']==anchor and prefix['subject_plan_ref']==binding['plan_ref'],'ACCEPTED_ANCHOR','prefix')
    need(reserved==[{'action_id':x['action_id'],'action_digest':h(x)} for x in plan['payload']['actions']],'RESERVATIONS','prefix')
    matching=[(n,e) for n,e in starts if e['payload']['binding']['readonly_session_id']==binding['readonly_session_id']]
    need(len(matching)==1,'SESSION_START','prefix')
    n,start=matching[0];h0=heads[n-1]
    need(basis['initial_event_head']==start['payload']['initial_event_head']==h0,'H0_CHAIN','basis/initial_event_head')
    need(time(basis['entry_deadline'])<=min(time(basis['parent_deadline']),time(start['recorded_at'])+timedelta(seconds=8)) and time(basis['parent_deadline'])<=time(start['recorded_at'])+timedelta(seconds=60),'ENTRY_BUDGET','basis/deadlines')
    need(prefix['predecessor']==heads[0] and prefix['from_sequence']==1,'GENESIS','prefix')
    records=prefix['frames'][n-1:];need(len(records)==7,'SESSION_WINDOW_LENGTH','prefix/session')
    expected=['READONLY_ABSENCE_STARTED']+['READONLY_ABSENCE_READ_'+kind for _ in range(3) for kind in ('STARTED','FINISHED')]
    for i,(frame,name) in enumerate(zip(records,expected)):
        e=frame['event'];p=e['payload']
        need(e['event']==name and e.get('event_version')=='a03-runtime-event-3','SESSION_WINDOW_EVENT','prefix/session/'+str(i))
        need(p['binding']==binding and e['owner_id']==binding['owner_id'] and e['generation']==binding['generation'] and e['plan_ref']==binding['plan_ref'],'SESSION_EVENT_BINDING','prefix/session/'+str(i))
        need(time(e['recorded_at'])<=min(time(basis['entry_deadline']),time(basis['parent_deadline'])),'DEADLINE','prefix/session/'+str(i))
    observed=[]
    for i in (1,2,3):
        s=records[i*2-1]['event'];f=records[i*2]['event'];sp,fp=s['payload'],f['payload']
        need(sp['ordinal']==fp['ordinal']==sp['used_count']==i,'READ_COUNTER','prefix/read/'+str(i))
        need(sp['role']==('CURRENTNESS'if i==3 else'EVIDENCE') and sp['in_final_gate']==(i==3),'READ_ROLE','prefix/read/'+str(i))
        need(fp['observation']==basis['observations'][i-1],'READ_RESOURCE_BINDING','basis/observations/'+str(i))
        o=pkg.read(fp['observation']);observed.append(o)
        need(o['binding']==binding and o['ordinal']==o['read_sequence']==i and o['scope_complete'] and o['comparison']=='ABSENT','OBSERVATION_BINDING','read/'+str(i))
        need(time(s['recorded_at'])<=time(o['observed_at'])<=time(f['recorded_at']) and (time(f['recorded_at'])-time(s['recorded_at'])).total_seconds()<=2,'READ_TIME','read/'+str(i))
    need(len({o['observation_id'] for o in observed})==3,'READ_IDENTITY','basis/observations')
    need(len({o['target_state_hash'] for o in observed})==len({o['target_state_version'] for o in observed})==1,'READ_DRIFT','basis/observations')
    prepared=pkg.read(basis['readonly_prepared_ref'])
    need(prepared['binding']==binding and prepared['facts']==action['expected_before'] and prepared['first_observation']==basis['observations'][0] and prepared['capability']=='READONLY_NO_DISPATCH','READONLY_PREPARED','basis/prepare')
    need(basis['fact_key']==h({k:binding[k] for k in ('target_key','plan_ref','action_id','action_digest')}),'FACT_KEY','basis/fact_key')
    facts={}
    for a in pkg.bundle['artifacts']:
        if a['kind']=='ExecutionReceipt':
            receipt=a['payload']
            if receipt['plan']==binding['plan_ref']:
                need([r['action_id']for r in receipt['results']]==[x['action_id']for x in plan['payload']['actions']] and len(receipt['results'])==len(receipt['action_fact_refs']),'RECEIPT_COMPLETE','receipt')
            for pos,r in enumerate(receipt['action_fact_refs']):
                fact=pkg.read(r);shape(fact,'fact-v3.schema.json')
                if fact['plan_ref']==binding['plan_ref'] and fact['action_id']==binding['action_id']:
                    need(receipt['plan']==binding['plan_ref'] and receipt['results'][pos]==fact['result'],'RECEIPT_FACT_BINDING','receipt')
                    facts[h(fact)]=fact
                    need(fact['unattempted_basis']==basis_resource(pkg,basis) and fact['journal_sequence']==final['sequence']+1 and fact['predecessor_hash']==final['hash'],'FACT_CAS','fact')
                    need(fact['intent_ref']is None and fact['obligation_id']is None and fact['result']['attempt_fact']=='NOT_ATTEMPTED','FACT_NO_INTENT','fact')
    need(len(facts)==1,'UNIQUE_FACT','fact')
    return {'H0':h0,'Hfinal':final,'total_reads':3,'subject_scope':plan['scope_id']}

def basis_resource(pkg,basis):
    # Locate the exact Resource by bytes, not by a caller-approved path name.
    matches=[]
    for a in pkg.bundle['artifacts']:
        if a['kind']=='ExecutionReceipt':
            for fr in a['payload']['action_fact_refs']:
                fact=pkg.read(fr);r=fact['unattempted_basis']
                if r is not None and pkg.read(r)==basis:matches.append(r)
    need(bool(matches),'BASIS_RESOURCE_BYTES','basis');return matches[0]

def check_conversion(pkg):
    c=load(DATA/'conversion/case.json');mapping=pkg.read(c['mapping']);source=pkg.read(c['source'])
    need(set(mapping)=={'format_version','source','target_bundle','artifacts','new_derived','resources'} and mapping['source']==c['source'],'MAPPING_SHAPE','mapping')
    legacy=copy.deepcopy(source);legacy['format_version']='a03-exchange-3-proposal';Package(legacy).validate()
    need(all(a['kind']in('SourceBundle','EvidenceBundle','QuestionGraph','PlatformSnapshot','CheckReport','ApplyPlan') for a in source['artifacts']),'INITIAL_ONLY_NO_HISTORY','source')
    target=load(DATA/c['target']);Package(target).validate()
    need(sha((DATA/c['target']).read_bytes())==mapping['target_bundle']['sha256'],'CONVERSION_TARGET_HASH','mapping')
    old={h(ref(a)):a for a in source['artifacts']};new={h(ref(a)):a for a in target['artifacts']}
    need({h(r['old_ref'])for r in mapping['artifacts']}==set(old),'CONVERSION_OLD_COVERAGE','mapping')
    mapped={h(r['new_ref'])for r in mapping['artifacts']if r['new_ref']}
    derived={h(r['ref'])for r in mapping['new_derived']}
    need(not(mapped&derived) and mapped|derived==set(new),'CONVERSION_NEW_COVERAGE','mapping')
    for row in mapping['artifacts']:
        if row['new_ref']:
            need(old[h(row['old_ref'])]['kind']==new[h(row['new_ref'])]['kind'] and old[h(row['old_ref'])]['kind']in('SourceBundle','EvidenceBundle','QuestionGraph','PlatformSnapshot'),'CONVERSION_KIND','mapping')
        else:need(row['disposition']=='ARCHIVE_ONLY' and row.get('reason'),'DERIVED_ARCHIVE','mapping')
    for row in mapping['resources']:
        need(sha((DATA/row['old_path']).read_bytes())==row['old_sha256'] and sha((DATA/row['new_path']).read_bytes())==row['new_sha256'],'RESOURCE_MAP_HASH','mapping')
    refmap={h(r['old_ref']):r['new_ref']for r in mapping['artifacts']if r['new_ref']}
    resmap={(r['old_path'],r['old_sha256']):r for r in mapping['resources']}
    def rewrite(v):
        if isref(v):need(h(v)in refmap,'CONVERSION_REF_MAP','mapping');return refmap[h(v)]
        if isres(v):
            need((v['path'],v['sha256'])in resmap,'CONVERSION_RESOURCE_COVERAGE',v['path']);r=resmap[(v['path'],v['sha256'])]
            return dict(v,path=r['new_path'],sha256=r['new_sha256'])
        if isinstance(v,dict):return {k:('converted-a'if k in('scope_id','authorized_scope_id')and x=='original-a'else rewrite(x))for k,x in v.items()}
        if isinstance(v,list):return [rewrite(x)for x in v]
        return v
    for row in mapping['artifacts']:
        if row['new_ref']:need(rewrite(old[h(row['old_ref'])]['payload'])==new[h(row['new_ref'])]['payload'],'CONVERSION_PAYLOAD_EQUIVALENCE',row['old_ref']['artifact_id'])
    need(rewrite(source['evidence'])==target['evidence'],'CONVERSION_EVIDENCE_MAP','mapping')
    for row in mapping['resources']:
        oldraw=(DATA/row['old_path']).read_bytes();newraw=(DATA/row['new_path']).read_bytes()
        if row['old_path'].endswith('.json'):need(rewrite(json.loads(oldraw))==json.loads(newraw),'CONVERSION_RESOURCE_EQUIVALENCE',row['old_path'])
        else:need(oldraw==newraw,'CONVERSION_RAW_COPY',row['old_path'])
    previous=None
    for r in c['records']:
        v=pkg.read(r);shape(v,'conversion-v3.schema.json');need(v['previous_record']==previous and v['source_raw_sha256']==c['source']['sha256'] and v['conversion_id']=='r2-static-conversion-a','STATE_PREDECESSOR',r['path']);previous=r
    manifest=pkg.read(c['completion_manifest']);need('committed'not in canon(manifest).decode().lower(),'COMPLETION_BACKREF','manifest')
    need(set(manifest)=={'format_version','source','mapping','target_bundle','file_inventory','native_execution_eligible','status'} and manifest['source']==c['source'] and manifest['mapping']==c['mapping'] and manifest['target_bundle']==mapping['target_bundle'],'COMPLETION_BINDING','manifest')
    for r in (c['committed_terminal'],c['incomplete_terminal'],c['failed_terminal']):
        v=pkg.read(r);shape(v,'conversion-v3.schema.json');need(v['previous_record']==previous,'TERMINAL_PREDECESSOR',r['path'])
    for v in manifest['file_inventory']:
        raw=(DATA/v['path']).read_bytes();need(sha(raw)==v['sha256'] and len(raw)==v['bytes'],'COMPLETION_FILE_HASH',v['path'])
    terminal=pkg.read(c['committed_terminal']);need(terminal['state']=='COMMITTED' and terminal['manifest']==c['completion_manifest'] and terminal['source_raw_sha256']==c['source']['sha256'] and not terminal['native_execution_eligible'],'COMMITTED_ONLY','conversion')
    resource_paths=set()
    def collect(v):
        if isres(v):
            if v['path']in resource_paths:return
            resource_paths.add(v['path']);body=pkg.read(v)
            if body is not None:collect(body)
        elif isinstance(v,dict):
            for x in v.values():collect(x)
        elif isinstance(v,list):
            for x in v:collect(x)
    collect(target)
    need(resource_paths=={v['path']for v in manifest['file_inventory']},'COMPLETION_EXACT_RESOURCE_SET','manifest')
    return target

def pre_context(pkg,run):
    shape(run,'pre-run-v2.schema.json');c=run['context'];source=pkg.artifact(run['source_ref'],'pre/source');graph=pkg.artifact(run['graph_ref'],'pre/graph');snapshot=pkg.artifact(run['snapshot_ref'],'pre/snapshot')
    need(source['scope_id']==graph['scope_id']==snapshot['scope_id']==snapshot['payload']['authorized_scope_id'],'PRE_SCOPE','pre')
    observed=pkg.read(run['actual_observation'])
    need(observed['snapshot_ref']==run['snapshot_ref'] and observed['observed_at']==run['observed_at']==snapshot['payload']['observed_at'] and time(run['produced_at'])>=time(run['observed_at']),'PRE_OBSERVATION','pre')
    if c['kind']=='POST_HOLD':
        hold=pkg.read(c['hold_ref']);need(c['hold_id']==hold['hold_id'] and c['hold_head']==hold['head'] and hold['scope_id']==source['scope_id'] and time(run['observed_at'])>time(hold['recorded_at']),'POST_HOLD_BINDING','pre/context')
    need(run['runtime_status']=='NOT_EXECUTED' and run['admission']=='UNIMPLEMENTED_NO_NATIVE_RUN','NO_NATIVE_PRE','pre')
    return c['kind']

def mutate_case(bundle,change,rechain=False,seal=True):
    b=copy.deepcopy(bundle);over={};probe=Package(b,over)
    receipt=b['artifacts'][-1];fr=receipt['payload']['action_fact_refs'][0];fact=probe.read(fr);br=fact['unattempted_basis'];basis=probe.read(br);pr=basis['complete_uncalled_prefix'];prefix=probe.read(pr)
    def virtual(path,value):
        raw=canon(value)+b'\n';over[path]=raw;return {'path':path,'sha256':sha(raw),'media_type':'application/json','origin':'SYNTHETIC'}
    change(b,prefix,basis,fact,virtual)
    if rechain:
        prev=ZERO
        for i,frame in enumerate(prefix['frames'],1):
            e=frame['event'];e.update(sequence=i,previous_hash=prev);e['event_hash']=h({k:v for k,v in e.items()if k!='event_hash'});prev=e['event_hash']
            if e['event']=='PLAN_ACCEPTED' and e['plan_ref']==prefix['subject_plan_ref']:prefix['accepted_anchor']={'sequence':i,'hash':prev}
        prefix['expected_book_head']={'sequence':len(prefix['frames']),'hash':prev};basis['expected_event_head']=prefix['expected_book_head'];fact['predecessor_hash']=prev;fact['journal_sequence']=len(prefix['frames'])+1
    basis['complete_uncalled_prefix']=virtual(pr['path'],prefix);fact['unattempted_basis']=virtual(br['path'],basis);receipt['payload']['action_fact_refs'][0]=virtual(fr['path'],fact)
    if seal:receipt['content_hash']=h({k:v for k,v in receipt.items()if k!='content_hash'})
    pkg=Package(b,over)
    repro={'base_bundle_sha256':sha((DATA/'scope-session.json').read_bytes()),'artifact_replacements':[a for a in b['artifacts']if a not in bundle['artifacts']],
           'resource_overrides':{p:json.loads(raw)for p,raw in over.items()},'seal_receipt':seal}
    return pkg,basis,repro

def positive(name,fn):
    value=fn();RESULTS.append({'id':name,'result':'STATIC_ACCEPTED','native_qualification':False});return value
def reject(name,expected,fn,projection=None):
    try:fn()
    except Rejected as e:
        need(e.code==expected,'WRONG_REJECTION',name+':'+str(e));RESULTS.append({'id':name,'result':'EXPECTED_STATIC_REJECTION','code':e.code,'path':e.path,'projection':projection})
        if projection is not None:
            p=EVID/'negative-values'/(name+'.json');p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(json.dumps({'id':name,'expected_rejection':expected,'reproduction_delta':projection},ensure_ascii=False,indent=2).encode('utf8')+b'\n')
    else:raise Rejected('NEGATIVE_ACCEPTED',name)

def main():
    profile=load(DATA/'profile.json');need(profile['profile_id']==PROFILE and not profile['implementation_authorized'],'PROFILE_SELECTOR','profile')
    need({p.relative_to(DATA).as_posix():sha(p.read_bytes())for p in (DATA/'schemas').glob('*.json')}=={x['path']:x['sha256']for x in profile['schema_pins']},'PINS_SET','profile')
    for n,k in [('api.json','api_sha256')]:need(sha((DATA/n).read_bytes())==profile[k],'PIN_HASH',n)
    need(sha((HOME/'oracle.json').read_bytes())==profile['oracle_sha256'] and sha((HOME/'oracle_verifier.py').read_bytes())==profile['oracle_verifier_sha256'],'ORACLE_PINS','profile')
    for p in (DATA/'schemas').glob('*.json'):audit(load(p))
    for source in profile['source_pins']:need(sha((ROOT/source['path']).read_bytes())==source['sha256'],'SOURCE_PIN',source['path'])
    bundle=load(DATA/'scope-session.json');pkg=positive('whole-package-two-scope-nested-resources',lambda:Package(bundle).validate())
    basis=pkg.read(load(DATA/'case-index.json')['basis']);positive('session-H0-through-three-reads-Hfinal',lambda:session(pkg,basis))
    repeated=copy.deepcopy(bundle);other=copy.deepcopy(repeated['artifacts'][-1]);other['artifact_id']='another-consumer-of-same-fact';other['content_hash']=h({k:v for k,v in other.items()if k!='content_hash'});repeated['artifacts'].append(other)
    positive('same-immutable-fact-may-have-two-consumers',lambda:session(Package(repeated).validate(),basis))
    target=positive('complete-new-initial-types-and-conversion',lambda:check_conversion(pkg))
    tp=Package(target);positive('INITIAL-without-manufactured-hold',lambda:pre_context(tp,load(DATA/'converted/initial-run.json')))
    positive('POST_HOLD-exact-context',lambda:pre_context(tp,load(DATA/'post-hold/run.json')))
    badrun=load(DATA/'post-hold/run.json');badrun['context']['hold_head']['hash']='f'*64
    reject('POST_HOLD-wrong-head','POST_HOLD_BINDING',lambda:pre_context(tp,badrun),badrun)
    badrun=load(DATA/'converted/initial-run.json');badrun['context']['hold_id']='manufactured-hold'
    reject('INITIAL-must-not-carry-hold','SHAPE_oneOf',lambda:pre_context(tp,badrun),badrun)
    comparisons=compare(target,DATA,load(HOME/'oracle.json'));need(all(x['comparison']=='STATIC_MATCH'for x in comparisons.values()),'ORACLE_COMPARISON','oracle')
    RESULTS.append({'id':'five-independent-static-comparisons','result':'STATIC_MATCH','checks':comparisons,'native_qualification':False})
    for name in comparisons:
        bad=copy.deepcopy(target);by={a['kind']:a for a in bad['artifacts']}
        if name=='source_integrity':by['SourceBundle']['payload']['assets'][0]['width']=31
        elif name=='structure':by['EvidenceBundle']['payload']['regions'][0]['box']['bbox'][0]=5
        elif name=='answer_matching':by['QuestionGraph']['payload']['answer_relations'][0]['selected_fragment_ids']=[]
        elif name=='coverage':by['SourceBundle']['payload']['scope_manifest']=[]
        else:bad['policies'][0]['role_mapping']['stem']='E'
        need(compare(bad,DATA,load(HOME/'oracle.json'))[name]['comparison']=='STATIC_MISMATCH','ORACLE_NEGATIVE',name)
        RESULTS.append({'id':'oracle-'+name+'-mismatch','result':'EXPECTED_STATIC_MISMATCH','native_qualification':False})
    # Exact archived diagnostic damage is projected onto the new complete basis.
    for filename,field,code in [('readonly-session-does-not-match-gate-binding.json','readonly_session_id','SESSION_BINDING'),('initial-head-not-in-canonical-prefix.json','initial_event_head','H0_CHAIN')]:
        old=load(EVID/'inputs'/filename);bad=copy.deepcopy(basis);bad[field]=old['value'][field]
        reject('archived-'+old['id'],code,lambda:session(pkg,bad),{'raw_input_sha256':sha((EVID/'inputs'/filename).read_bytes()),'copied_field':field,'copied_value':old['value'][field]})
    # Local protocol mutations do not grant native authority or call product validators.
    bad=copy.deepcopy(basis);bad['binding']['owner_id']='foreign-owner'
    reject('foreign-owner-binding','SESSION_BINDING',lambda:session(pkg,bad))
    bad=copy.deepcopy(basis);bad['fact_key']='f'*64
    reject('wrong-permanent-fact-key','FACT_KEY',lambda:session(pkg,bad))
    bad=copy.deepcopy(basis);bad['entry_deadline']='2026-10-17T00:00:30Z'
    reject('deadline-not-clamped-to-entry','ENTRY_BUDGET',lambda:session(pkg,bad))
    def wrongscope(b,p,bs,f,v):p['frames'][1]['consumer_scope_id']='original-a'
    def missingframe(b,p,bs,f,v):p['frames'][1]['input_refs']=[]
    def foreignbook(b,p,bs,f,v):
        foreign=copy.deepcopy(b['artifacts'][7]);foreign['book_id']='foreign-book';foreign['artifact_id']='foreign-source';foreign['content_hash']=h({k:x for k,x in foreign.items()if k!='content_hash'});b['artifacts'].insert(0,foreign)
        frame=p['frames'][1];frame['event']['payload']['evidence']=v('negative/foreign-book.json',{'nested':v('negative/foreign-nested.json',{'source_ref':ref(foreign)})});frame['input_refs']=[frame['event']['plan_ref'],ref(foreign)]
    def fakeframe(b,p,bs,f,v):p['frames'][1]['event']['payload']['evidence']=v('negative/fake-frame.json',{'frame_version':'a03-journal-consumer-frame-2','consumer_scope_id':'original-b','input_refs':[],'event':{}})
    def cycle(b,p,bs,f,v):
        frame=p['frames'][4];rr=ref(b['artifacts'][-1]);frame['event']['payload']['evidence']=v('negative/back-to-receipt.json',{'receipt_ref':rr});frame['input_refs']=[frame['event']['plan_ref'],rr]
    def readorder(b,p,bs,f,v):p['frames'][8]['event']['payload']['ordinal']=2
    def foreignsession(b,p,bs,f,v):p['frames'][10]['event']['payload']['binding']=dict(bs['binding'],registration_id='foreign-registration')
    def outsideevent(b,p,bs,f,v):
        frame=p['frames'][9];e=frame['event'];e.update(event='OWNER_ACTIVE',plan_ref=None,payload={'fence_token':bs['binding']['fence_token']});frame.update(consumer_scope_id=None,input_refs=[])
    def duplicated(b,p,bs,f,v):
        other=copy.deepcopy(b['artifacts'][-1]);other['artifact_id']='second-receipt-distinct-fact';second=copy.deepcopy(f);second['result']['reason']='SECOND_DISTINCT_FACT_FOR_SAME_PERMANENT_KEY';other['payload']['results'][0]=second['result'];other['payload']['action_fact_refs']=[v('negative/distinct-second-fact.json',second)];other['content_hash']=h({k:x for k,x in other.items()if k!='content_hash'});b['artifacts'].insert(0,other)
    for name,change,code,rechain,seal in [
        ('frame-wrong-scope',wrongscope,'FRAME_SCOPE',False,True),('frame-missing-declaration',missingframe,'UNDECLARED_REFERENCE',False,True),
        ('frame-foreign-book',foreignbook,'FOREIGN_BOOK',False,True),('fake-frame-in-resource',fakeframe,'FRAME_OUTSIDE_TYPED_PREFIX',False,True),
        ('artifact-resource-frame-mixed-cycle',cycle,'MIXED_CYCLE',False,False),('session-read-order',readorder,'READ_COUNTER',True,True),
        ('session-foreign-registration',foreignsession,'SESSION_EVENT_BINDING',True,True),('session-window-control-event',outsideevent,'SESSION_WINDOW_EVENT',True,True),
        ('duplicate-permanent-fact',duplicated,'UNIQUE_FACT',False,True)]:
        mutated,bs,repro=mutate_case(bundle,change,rechain,seal)
        reject(name,code,lambda:session(mutated.validate(),bs),repro)
    conversion=load(DATA/'conversion/case.json')
    for r in conversion['records']+[conversion['incomplete_terminal'],conversion['failed_terminal']]:
        record=pkg.read(r)
        reject('conversion-not-committed-'+record['state'],'CONVERSION_NOT_COMMITTED',lambda:need(record['state']=='COMMITTED','CONVERSION_NOT_COMMITTED',r['path']),record)
    for name,mutate,code in [
        ('ordinary-foreign-scope',lambda b: b['artifacts'][-1]['input_refs'].append(ref(b['artifacts'][7])),'ORDINARY_SCOPE'),
        ('missing-outer-declaration',lambda b: b['artifacts'][-1].update(input_refs=[]),'UNDECLARED_REFERENCE'),
    ]:
        badbundle=copy.deepcopy(bundle);mutate(badbundle)
        reject(name,code,lambda:Package(badbundle).validate())
    RESULTS.append({'id':'archived-amended-source-coverage','result':'STATIC_ACCEPTED','raw_diagnostic_sha256':sha((EVID/'inputs/amended-source-kind-coverage.json').read_bytes()),'covered_new_initial_kinds':[a['kind']for a in target['artifacts']],'native_qualification':False})
    result={'status':'REVIEW_STATIC_ONLY','profile_id':PROFILE,'checker_sha256':sha(Path(__file__).read_bytes()),'schema_interpreter_sha256':sha((HOME/'schema_check.py').read_bytes()),'profile_sha256':sha((DATA/'profile.json').read_bytes()),'records':RESULTS,'product_runs':0,'database_queries':0,'native_sessions':0,'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
    (EVID/'static-results.json').write_bytes(json.dumps(result,ensure_ascii=False,indent=2).encode('utf8')+b'\n')
    print(json.dumps({'status':result['status'],'records':len(RESULTS),'product_runs':0,'native_sessions':0}))

if __name__=='__main__':main()
