"""Build interface text and exactly four static registration packages."""
import copy,hashlib,json,subprocess,sys
from pathlib import Path
import interfaces
ROOT=interfaces.ROOT;EX=interfaces.EX;OUT=interfaces.OUT
BASE='87606b73e0754fa670491d9fb958a416c26bfe88'
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
def sha(v):return hashlib.sha256(v).hexdigest()
def h(v):return sha(canon(v))
def load(p):return json.loads(p.read_bytes())
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(json.dumps(v,ensure_ascii=False,indent=2).encode('utf8')+b'\n')
def ref(a):return {k:a[k]for k in('artifact_id','revision','kind','content_hash')}
def seal(a):a['content_hash']=h({k:v for k,v in a.items()if k!='content_hash'});return a
def ordinary(v,resources,seen=None):
    seen=set()if seen is None else seen;found={}
    if isinstance(v,dict):
        if set(v)=={'artifact_id','revision','kind','content_hash'}:return {h(v):v}
        if {'path','sha256','media_type'}<=set(v):
            token=(v['path'],v['sha256'])
            if v['media_type']=='application/json'and token not in seen:
                seen.add(token);raw=resources[v['path']];assert sha(raw)==v['sha256'];found.update(ordinary(json.loads(raw),resources,seen))
            return found
        for x in v.values():found.update(ordinary(x,resources,seen))
    elif isinstance(v,list):
        for x in v:found.update(ordinary(x,resources,seen))
    return found

def build_case(name,mode,seed,shared):
    a=[copy.deepcopy(x)for x in seed['artifacts']if x['scope_id']=='original-a']
    assert len(a)==8 # seven immutable initial artifacts plus old receipt; receipt is not needed here.
    a=[x for x in a if x['kind']!='ExecutionReceipt'];assert len(a)==7
    source_a=next(x for x in a if x['kind']=='SourceBundle');snap_a=next(x for x in a if x['kind']=='PlatformSnapshot');plan=next(x for x in a if x['kind']=='ApplyPlan')
    source_b=copy.deepcopy(next(x for x in seed['artifacts']if x['kind']=='SourceBundle'and x['scope_id']=='original-b'))
    old_snap_b=next(x for x in seed['artifacts']if x['kind']=='PlatformSnapshot'and x['scope_id']=='original-b')
    key={'platform_namespace':'a03-synthetic','target_id':'synthetic-r2-target','book_id':plan['book_id']}
    source_ref=ref(source_a)if mode=='source'else ref(source_b)
    snapshot=copy.deepcopy(old_snap_b);snapshot.update(schema_version='1.3.0-a03-static-proposal',artifact_id='r4-static-registration-snapshot',run_id='r4-static-case',created_at='2026-10-17T00:00:05.500Z',input_refs=[ref(source_b)])
    snapshot['producer'].update(module='R4_STATIC_SNAPSHOT_VALUE',implementation_version='UNIMPLEMENTED')
    snapshot['payload'].update(observed_at=snapshot['created_at'],observed_version='r4-static-state-1')
    if mode=='target':snapshot['payload']['target_id']='r4-different-registered-target'
    business={'hash_domain':'R4_STATIC_VALUE_NOT_NATIVE_DIGEST','target_key':key,'source_ref':source_ref,'scope_id':'original-b','target_store_id':'r4-static-store','target_session_id':'r4-static-session',
       'target_view':{k:copy.deepcopy(snapshot['payload'][k])for k in('target_id','platform_version','authorized_scope_id','directories','questions','frames')}}
    snapshot['payload']['observed_hash']=h(business);seal(snapshot)
    snapshot_ref=ref(snap_a)if mode=='snapshot'else ref(snapshot)
    artifacts=a+[source_b,snapshot];resources=dict(shared)
    def resource(value,path):
        raw=canon(value)+b'\n';resources[path]=raw;return {'path':path,'sha256':sha(raw),'media_type':'application/json','origin':'SYNTHETIC'}
    observation=resource({'format_version':'r4-static-observation-value-1','status':'STATIC_NOT_NATIVE','registration_id':'r4-registration-b','source_ref':source_ref,'snapshot_ref':snapshot_ref,'scope_id':'original-b','target_key':key,
       'target_store_id':'r4-static-store','target_session_id':'r4-static-session','read_sequence':2,'observation_id':'r4-observation-b','observed_at':'2026-10-17T00:00:05.500Z',
       'target_state_hash':h(business),'target_state_version':'r4-static-state-1','business_value':business},'r4-static/'+name+'/observation.json')
    baseline=resource({'status':'STATIC_BASELINE_NOT_NATIVE','source_ref':ref(source_b),'target_key':key,'scope_id':'original-b','target_store_id':'r4-static-store','target_session_id':'r4-static-session','read_sequence':1,'observed_at':'2026-10-17T00:00:00Z'},'r4-static/'+name+'/baseline.json')
    frames=[];prev='0'*64
    def append(event,payload,plan_ref=None,scope=None):
        nonlocal prev
        e={'sequence':len(frames)+1,'event':event,'journal_id':'r4-static-independent-journal','target_key':key,'plan_ref':plan_ref,'owner_id':'r4-static-owner','generation':1,
           'recorded_at':'2026-10-17T00:00:%02dZ'%(len(frames)+1),'payload':payload,'previous_hash':prev};e['event_hash']=h(e);prev=e['event_hash']
        frames.append({'frame_version':'a03-journal-consumer-frame-2','consumer_scope_id':scope,'input_refs':list(ordinary(e,resources).values()),'event':e})
    append('OWNER_CLAIM_RESERVED',{});append('OWNER_ACTIVE',{})
    bindings=[{'action_id':x['action_id'],'action_digest':h(x)}for x in plan['payload']['actions']]
    append('PLAN_ACCEPTED',{'plan_ref':ref(plan),'actions':bindings},ref(plan),plan['scope_id']);anchor={'sequence':3,'hash':prev}
    append('PLAN_ACTIONS_RESERVED',{'plan_ref':ref(plan),'reservations':bindings},ref(plan),plan['scope_id'])
    append('PLAN_STARTED',{'plan_ref':ref(plan),'plan_state':'RUNNING'},ref(plan),plan['scope_id'])
    payload={'hold_id':'r4-static-hold-b','registration_id':'r4-registration-b','plan_ref':None,
      'baseline':{'event_sequence':2,'event_hash':frames[1]['event']['event_hash'],'event':'OWNER_ACTIVE','binding':baseline,'plan_ref':None,
                  'target_state_hash':old_snap_b['payload']['observed_hash'],'target_state_version':old_snap_b['payload']['observed_version'],'read_sequence':1,'observed_at':'2026-10-17T00:00:00Z'},
      'observation':observation,'snapshot_ref':snapshot_ref,'observation_id':'r4-observation-b','observed_at':'2026-10-17T00:00:05.500Z','read_sequence':2,
      'target_state_hash':h(business),'target_state_version':'r4-static-state-1','target_store_id':'r4-static-store','target_session_id':'r4-static-session','source_ref':source_ref,'scope_id':'original-b','prior_precheck_refs':[]}
    append('TARGET_DRIFT_HOLD',payload,None,'original-b')
    prefix={'format_version':'a03-runtime-event-prefix-2','profile_id':'a03-p2-r2-static-2-PROPOSAL','journal_id':'r4-static-independent-journal','target_key':key,
      'from_sequence':1,'predecessor':{'sequence':0,'hash':'0'*64},'subject_plan_ref':ref(plan),'accepted_anchor':anchor,'expected_book_head':{'sequence':6,'hash':prev},'frames':frames}
    pr=resource(prefix,'r4-static/'+name+'/prefix.json')
    consumer=copy.deepcopy(source_a);consumer.update(schema_version='1.3.0-a03-static-proposal',artifact_id='r4-registration-prefix-consumer',run_id='r4-static-case',created_at='2026-10-17T00:00:07Z',input_refs=[ref(plan)])
    consumer['producer'].update(module='R4_STATIC_RESOURCE_CONSUMER',implementation_version='UNIMPLEMENTED')
    for mapping in consumer['payload']['external_page_mappings']:mapping['evidence_refs']=['proof-r4-registration']
    seal(consumer);artifacts.append(consumer)
    record=copy.deepcopy(seed['evidence'][0]);record.update(evidence_id='proof-r4-registration',resource=pr,description='R4 static full prefix; not a DB or native registration event')
    bundle={'format_version':'a03-exchange-3-proposal','evidence':[copy.deepcopy(seed['evidence'][0]),record],'policies':copy.deepcopy(seed['policies']),'artifacts':artifacts}
    directory=EX/'cases'/name;write(directory/'bundle.json',bundle);files=[]
    for i,(logical,raw)in enumerate(sorted(resources.items())):
        if logical in shared:continue
        p=directory/'resources'/('%02d.json'%i);p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb')as f:f.write(raw)
        files.append({'logical':logical,'file':p.relative_to(ROOT).as_posix(),'sha256':sha(raw)})
    files += [{'logical':n,'file':(EX/'shared'/Path(n).name).relative_to(ROOT).as_posix(),'sha256':sha(raw)}for n,raw in sorted(shared.items())]
    assert all(h({k:v for k,v in x.items()if k!='content_hash'})==x['content_hash']for x in artifacts)
    previous='0'*64
    for i,f in enumerate(frames,1):
        e=f['event'];assert e['sequence']==i and e['previous_hash']==previous and h({k:v for k,v in e.items()if k!='event_hash'})==e['event_hash'];previous=e['event_hash']
        assert e['target_key']==prefix['target_key']
    assert prefix['expected_book_head']=={'sequence':6,'hash':previous}and frames[-1]['event']['plan_ref']is None
    for logical,raw in resources.items():assert sha(raw)==next((r['sha256']for r in files if r['logical']==logical))
    info={'case':name,'mode':mode,'bundle':(directory/'bundle.json').relative_to(ROOT).as_posix(),'bundle_sha256':sha((directory/'bundle.json').read_bytes()),'resources':files,
      'entry':'fixed R3 closure.Package.validate','base':BASE,'data_root':'examples/a03/P2-R2-proposal/candidate-final','prefix_resource':pr,
      'artifact_count':len(artifacts),'event_count':6,'all_artifact_resource_event_hashes_recomputed':True,'native_registration':False,
      'semantic_change':{'positive':'none; Source/Snapshot exact same book/scope and matching target','source':'payload/source-observation Source ref A instead of B, declared refs updated','snapshot':'payload/observation Snapshot ref A instead of B, declared refs updated','target':'same book/scope but newly sealed Snapshot target_id differs from journal/registration target key'}[mode]}
    write(directory/'case.json',info);return bundle,resources,info

if __name__=='__main__':
    interfaces.build()
    from fixed_entry import c,ROUTING
    write(OUT/'fixed-entry-routing.json',ROUTING)
    seed=load(c.base.DATA/'scope-session.json');shared={};pins=[]
    for n in('original/page-a.pgm','original/page-b.pgm','original/inventory-a.json','original/inventory-b.json','original/proof.txt'):
        p=c.base.DATA/n;raw=p.read_bytes();relative=p.relative_to(ROOT).as_posix()
        archived=subprocess.check_output(['git','-c','core.longpaths=true','show',BASE+':'+relative],cwd=ROOT);assert archived==raw
        dest=EX/'shared'/Path(n).name;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb')as f:f.write(raw)
        shared[n]=raw;pins.append({'commit':BASE,'path':relative,'copy':dest.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha(raw),'raw_git_blob':subprocess.check_output(['git','-c','core.longpaths=true','rev-parse',BASE+':'+relative],cwd=ROOT).decode().strip()})
    write(OUT/'resource-input-pins.json',{'inputs':pins})
    cases=[build_case(name,mode,seed,shared)for name,mode in [('registration-positive','positive'),('source-binding-negative','source'),('snapshot-binding-negative','snapshot'),('target-tuple-negative','target')]]
    results=[];start=c.Package.entry_calls
    for bundle,resources,info in cases:
        expected='STATIC_ACCEPTED'if info['mode']=='positive'else'FRAME_REGISTRATION_BINDING';pkg=c.Package(bundle,resources)
        try:pkg.validate();actual='STATIC_ACCEPTED';error=None
        except c.Rejected as e:actual=e.code;error={'code':e.code,'path':e.path}
        results.append({'case':info['case'],'expected':expected,'actual':actual,'matched':actual==expected,'error':error,'case_path':(EX/'cases'/info['case']/'case.json').relative_to(ROOT).as_posix(),
          'semantic_layer':'registration Source/Snapshot/scope/target tuple','hash_integrity':True,'native_qualification':False})
    assert c.Package.entry_calls-start==4
    gaps=[x for x in results if not x['matched']]
    summary={'status':'REVIEW_WITH_MINIMAL_RESIDUAL'if gaps else'REVIEW_STATIC_PREPARATION_ONLY','checks':results,'fixed_package_calls':4,'old_36_matrix_runs':0,'product_calls':0,'database_queries':0,'native_sessions':0,
      'existing_R3_semantics_unchanged':True,'interface_static_check':load(OUT/'interface-static-check.json'),
      'residuals':gaps,'stop':'freeze after these four; no checker semantic patch or extra controls','field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
    write(OUT/'four-package-results.json',summary)
    print(json.dumps(summary));sys.exit(1 if gaps else 0)
