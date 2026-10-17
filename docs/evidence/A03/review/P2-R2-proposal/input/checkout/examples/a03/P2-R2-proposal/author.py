"""Author new static values only. No product import, DB, session or network."""
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HOME=Path(__file__).resolve().parent
OUT=HOME/'candidate-final'
INPUT=ROOT/'docs/evidence/A03/execution/P2-R2-proposal/inputs'
PROFILE='a03-p2-r2-static-2-PROPOSAL'
VERSION='1.3.0-a03-static-proposal'
PREFIX='a03-runtime-event-prefix-2'
ZERO='0'*64

def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
def sha(v):return hashlib.sha256(v).hexdigest()
def h(v):return sha(canon(v))
def load(p):return json.loads(p.read_bytes())
def write(path,value):
    p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2).encode('utf8')+b'\n')
def ref(a):return {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}
def walk(v):
    yield v
    if isinstance(v,dict):
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)
def ordinary(v,seen=None):
    result={};seen=set() if seen is None else seen
    if isinstance(v,dict):
        if set(v)=={'artifact_id','revision','kind','content_hash'}:return {h(v):v}
        if {'path','sha256','media_type'}<=set(v):
            if v['media_type']=='application/json' and v['path'] not in seen:
                seen.add(v['path']);return ordinary(load(OUT/v['path']),seen)
            return {}
        for k,x in v.items():
            if v.get('format_version')==PREFIX and k=='frames':continue
            result.update(ordinary(x,seen))
    elif isinstance(v,list):
        for x in v:result.update(ordinary(x,seen))
    return result
def raw_resource(raw,name,media='application/json'):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():p.write_bytes(raw)
    assert p.read_bytes()==raw
    return {'path':name,'sha256':sha(raw),'media_type':media,'origin':'SYNTHETIC'}
def resource(v,name=None):
    raw=canon(v)+b'\n';return raw_resource(raw,name or 'assets/'+sha(raw)+'.json')
def artifact(kind,identity,payload,scope,version=VERSION,producer='STATIC_PROPOSAL'):
    a={'schema_version':version,'artifact_id':identity,'revision':1,'kind':kind,'run_id':'r2-static-values',
       'book_id':'synthetic-r2-book','scope_id':scope,'created_at':'2026-10-17T00:00:00Z',
       'producer':copy.deepcopy(SEED['artifacts'][0]['producer']),'payload':payload,'input_refs':list(ordinary(payload).values())}
    a['producer'].update(module=producer,implementation_version='UNIMPLEMENTED');a['content_hash']=h(a);return a
def obj(p):return {'type':'object','properties':p,'required':list(p),'additionalProperties':False}
S={'type':'string','minLength':1};H={'type':'string','pattern':'^[0-9a-f]{64}$'};N={'type':'integer','minimum':1}
REF=obj({'artifact_id':S,'revision':N,'kind':S,'content_hash':H})
RES=obj({'path':S,'sha256':H,'media_type':S,'origin':{'const':'SYNTHETIC'}})
HEAD=obj({'sequence':{'type':'integer','minimum':0},'hash':H})
KEY=obj({k:S for k in ('book_id','platform_namespace','target_id')})
ARR=lambda x:{'type':'array','items':x}
NULL=lambda x:{'oneOf':[{'type':'null'},x]}
CTX={'oneOf':[obj({'kind':{'const':'INITIAL'},'hold_id':{'type':'null'},'hold_head':{'type':'null'},'hold_ref':{'type':'null'}}),
              obj({'kind':{'const':'POST_HOLD'},'hold_id':S,'hold_head':HEAD,'hold_ref':RES})]}
BIND=obj({'ledger_id':S,'readonly_session_id':S,'entry_id':S,'parent_call_id':S,'owner_id':S,'generation':N,
          'registration_id':S,'target_store_id':S,'target_session_id':S,'target_key':KEY,'plan_ref':REF,
          'scope_id':S,'action_id':S,'action_digest':H,'fence_token':S})

def schemas():
    exchange=load(INPUT/'exchange-v2.schema.json')
    exchange['$id']='urn:a03:p2-r2:exchange-3';exchange['properties']['format_version']={'const':'a03-exchange-3-proposal'}
    kinds=[r['$ref'].rsplit('/',1)[1] for r in exchange['properties']['artifacts']['items']['oneOf'] if 'Amended' in r['$ref']]
    for name in kinds:exchange['$defs'][name]['properties']['schema_version']={'const':VERSION}
    # Explicit legacy nodes are immutable read-only inputs, never eligible writer outputs.
    exchange['properties']['artifacts']['items']['oneOf']=[{'$ref':'#/$defs/'+n} for n in kinds]+[{'$ref':'#/$defs/'+n.removeprefix('Amended')} for n in kinds]
    pre=exchange['$defs']['AmendedCheckReport']['properties']['payload']['oneOf'][0]
    pre['properties']['verification_context']=CTX;pre['required'].append('verification_context')
    exchange['title']='R2 STATIC PROPOSAL: shape + exact registry, not native eligibility'
    write('schemas/exchange-v3.schema.json',exchange)
    event_payloads={
      'OWNER_ACTIVE':obj({'fence_token':S}),
      'RUNTIME_PROFILE_ADOPTED':obj({'previous_profile':S,'new_profile':{'const':PROFILE},'previous_head':HEAD,'meta_raw_sha256':H,'retired_writers':RES}),
      'PLAN_ACCEPTED':obj({'plan_ref':REF,'actions':ARR(obj({'action_id':S,'action_digest':H})),'evidence':RES}),
      'PLAN_ACTIONS_RESERVED':obj({'plan_ref':REF,'reservations':ARR(obj({'action_id':S,'action_digest':H}))}),
      'PLAN_INTERRUPTED':obj({'plan_ref':REF,'reason':{'const':'EXPLICIT_STATIC_INTERRUPTION'}}),
      'READONLY_ABSENCE_STARTED':obj({'binding':BIND,'initial_event_head':HEAD,'counter_before':{'const':0}}),
      'READONLY_ABSENCE_READ_STARTED':obj({'binding':BIND,'ordinal':N,'used_count':N,'role':{'enum':['EVIDENCE','CURRENTNESS']},'in_final_gate':{'type':'boolean'}}),
      'READONLY_ABSENCE_READ_FINISHED':obj({'binding':BIND,'ordinal':N,'observation':RES}),
      'READONLY_ABSENCE_READ_FAILED':obj({'binding':BIND,'ordinal':N,'failure':RES}),
      'READONLY_ABSENCE_ABORTED':obj({'binding':BIND,'used_count':N,'reason':S}),
    }
    variants=[]
    for name,payload in event_payloads.items():
        variants.append(obj({'event_version':{'const':'a03-runtime-event-3'},'sequence':N,'event':{'const':name},
            'journal_id':S,'target_key':KEY,'plan_ref':NULL(REF),'owner_id':S,'generation':N,
            'recorded_at':S,'payload':payload,'previous_hash':H,'event_hash':H}))
    legacy_prefix=load(ROOT/'examples/a03/P2-R1-proposal/candidate-v2/schemas/runtime-event-prefix-v1.schema.json')
    variants+=legacy_prefix['properties']['frames']['items']['properties']['event']['oneOf']
    frame=obj({'frame_version':{'const':'a03-journal-consumer-frame-2'},'consumer_scope_id':NULL(S),'input_refs':ARR(REF),'event':{'oneOf':variants}})
    prefix=obj({'format_version':{'const':PREFIX},'profile_id':{'const':PROFILE},'journal_id':S,'target_key':KEY,
       'from_sequence':{'const':1},'predecessor':HEAD,'subject_plan_ref':REF,'accepted_anchor':HEAD,'expected_book_head':HEAD,'frames':ARR(frame)})
    write('schemas/prefix-v2.schema.json',prefix)
    basis=obj({'format_version':{'const':'a03-unattempted-basis-3'},'binding':BIND,'readonly_session_id':S,
       'gate_binding':BIND,'initial_event_head':HEAD,'expected_event_head':HEAD,'complete_uncalled_prefix':RES,
       'readonly_prepared_ref':RES,'observations':ARR(RES),'observer_calls':{'const':2},'total_read_calls':{'const':3},
       'used_count':{'const':3},'retries':{'const':0},'single_read_seconds':{'const':2},'entry_seconds':{'const':8},
       'parent_seconds':{'const':60},'busy_seconds':{'const':1},'gate_seconds':{'const':5},'lease_seconds':{'const':10},
       'renew_seconds':{'const':2},'parent_deadline':S,'entry_deadline':S,'fact_key':H,'plan_status':{'const':'INTERRUPTED'},'comparison':{'const':'ABSENT'}})
    write('schemas/basis-v3.schema.json',basis)
    fact=load(INPUT/'action-fact-v2.schema.json')
    for x in walk(fact):
        if isinstance(x,dict) and x.get('const')=='a03-action-fact-2':x['const']='a03-action-fact-3'
    fact['$id']='urn:a03:p2-r2:fact-3';write('schemas/fact-v3.schema.json',fact)
    run=obj({'format_version':{'const':'a03-synthetic-pre-run-2'},'context':CTX,'source_ref':REF,'graph_ref':REF,'snapshot_ref':REF,
             'oracle':RES,'input_raw_sha256':H,'implementation_sha256':H,'actual_observation':RES,'observed_at':S,'produced_at':S,'checks':obj({k:{'const':'UNAVAILABLE'} for k in ('source_integrity','structure','answer_matching','coverage','policy')}),
             'runtime_status':{'const':'NOT_EXECUTED'},'admission':{'const':'UNIMPLEMENTED_NO_NATIVE_RUN'}})
    write('schemas/pre-run-v2.schema.json',run)
    conversion=obj({'format_version':{'const':'a03-conversion-record-3'},'conversion_id':S,
        'state':{'enum':['CREATED','COPYING','VALIDATING','INCOMPLETE','FAILED','COMMITTED']},'previous_record':NULL(RES),
        'source_raw_sha256':H,'manifest':NULL(RES),'failure':NULL(S),'native_execution_eligible':{'const':False}})
    write('schemas/conversion-v3.schema.json',conversion)
    write('api.json',{'profile_id':PROFILE,'status':'STATIC_UNIMPLEMENTED','registry':[n.removeprefix('Amended') for n in kinds],
      'legacy_version':'1.1.0-a-recovery-proposal','legacy_role':'IMMUTABLE_READ_ONLY_INPUT; never writer output or old-tail resume',
      'new_version':VERSION,'prefix_boundary':'Only exact profile/format + valid schema + bytes-bound prefix.frames, reached through Resource; each frame owns recursive declarations; all other ordinary refs same book/scope; one global mixed DAG',
      'session_binding_fields':list(BIND['properties']),'entry':'begin_readonly_absence(binding, H0); persistent counter before each read; two evidence + final-gated currentness read; H0 immediately precedes STARTED; only same-binding session bookkeeping until Hfinal; immutable unique fact at Hfinal+1',
      'write_guards':['claim','takeover','plan_accept/start','commit_intent','issue/consume_permit','target_effect','hold_clear','profile_adoption','conversion_registration'],
      'pre_entry':'produce/admit_synthetic_precheck(context=INITIAL|POST_HOLD, exact approved oracle, actual snapshot, five checks, private native run); INITIAL has no hold; POST_HOLD exact hold head and fresh observation',
      'conversion_admission':'only terminal COMMITTED record referencing durable manifest; manifest never references COMMITTED; incomplete/failed/reopen diagnostic only; no automatic completion',
      'r17_roles':{'single_head':'future unmodified A02 planner one-question input; version bridge unresolved, no native pass','multi_head':'R1 immutable value fixtures only; no claim of reachable multihead history'},
      'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
    return kinds

def fresh_legacy(suffix):
    scope='original-'+suffix;version='1.1.0-a-recovery-proposal';art=[]
    def a(kind,p):
        v=artifact(kind,'origin-'+suffix+'-'+kind,p,scope,version);art.append(v);return v
    image=raw_resource(b'P2\n32 32\n255\n'+(' '.join('0' if (4<=x<28 and (4<=y<10 or 18<=y<24)) else '255' for y in range(32) for x in range(32))+'\n').encode(), 'original/page-'+suffix+'.pgm','image/x-portable-graymap')
    inventory=resource({'origin':'SYNTHETIC','scope_id':scope,'pages':['page-'+suffix],'question_ids':['question-'+suffix]},'original/inventory-'+suffix+'.json')
    asset=dict(image,asset_id='page-'+suffix,width=32,height=32,source_label='R2 new authored synthetic fixture',provenance='SYNTHETIC')
    source=copy.deepcopy(T['SourceBundle']['payload']);source.update(assets=[asset],directories=[{'directory_id':'directory-'+suffix,'parent_id':None,'label':'Fixture '+suffix}],pages_expected=['page-'+suffix],pages_acquired=['page-'+suffix],external_page_mappings=[{'asset_id':'page-'+suffix,'directory_id':'directory-'+suffix,'external_page':'1','mapping_status':'CONFIRMED','evidence_refs':['proof']}],history=[],scope_manifest=['question-'+suffix],scope_manifest_basis='new fixed explicit one-question fixture',metadata_page_count=1,scope_integrity={'status':'SYNTHETIC_COMPLETE','basis':'FIXTURE','proof':inventory})
    source=a('SourceBundle',source)
    regions=[];clues=[]
    for role,box in [('stem',[4,4,28,10]),('answer',[4,18,28,24])]:
        r=copy.deepcopy(T['EvidenceBundle']['payload']['regions'][0]);r.update(region_id='region-'+role+'-'+suffix,box={'image':{'asset_id':asset['asset_id'],'width':32,'height':32,'sha256':asset['sha256']},'bbox':box},text='New synthetic '+role,printed_number_candidates=[],evidence_refs=['proof']);r['crop_transform'].update(processed_width=32,processed_height=32);regions.append(r)
        c=copy.deepcopy(T['EvidenceBundle']['payload']['coverage_clues'][0]);c.update(clue_id='clue-'+role+'-'+suffix,box=r['box'],region_ids=[r['region_id']],evidence_refs=['proof']);clues.append(c)
    evidence=a('EvidenceBundle',{'source':ref(source),'regions':regions,'coverage_clues':clues})
    graph=copy.deepcopy(T['QuestionGraph']['payload']);question=copy.deepcopy(graph['questions'][0]);question.update(question_id='question-'+suffix,directory_id='directory-'+suffix,fragment_ids=['fragment-stem-'+suffix,'fragment-answer-'+suffix],shared_fragment_ids=[],cross_page=False);question['external_refs'].update(printed_number='1',platform_question_id=None,platform_order=None)
    fragments=[{'fragment_id':'fragment-'+role+'-'+suffix,'region_ids':['region-'+role+'-'+suffix],'role':role,'content_type':'text','reading_order':i} for i,role in enumerate(('stem','answer'))]
    graph.update(source=ref(source),evidence=ref(evidence),questions=[question],fragments=fragments,answer_relations=[{'relation_id':'relation-'+suffix,'question_id':question['question_id'],'candidate_fragment_ids':['fragment-answer-'+suffix],'selected_fragment_ids':['fragment-answer-'+suffix],'status':'SELECTED','evidence_refs':['proof']}],identity_notes='New static one-question input; no existing plan cropped')
    graph=a('QuestionGraph',graph)
    snap=copy.deepcopy(T['PlatformSnapshot']['payload']);snap.update(target_id='synthetic-r2-target',authorized_scope_id=scope,directories=['platform-'+suffix],evidence_refs=['proof']);
    for cap in snap['capabilities']:
        if cap['evidence_refs']:cap['evidence_refs']=['proof']
    snapshot=a('PlatformSnapshot',snap)
    pre=copy.deepcopy(T['CheckReport']['payload']);pre.update(subject=ref(graph),graph=ref(graph),policy=POLICY_REF,coverage={'scope_id':scope,'pages_expected':['page-'+suffix],'pages_checked':['page-'+suffix],'clue_ids':[x['clue_id'] for x in clues],'unassigned_region_ids':[]},reason='STATIC legacy fixture stub; not new PRE authority')
    for c in pre['checks']:c['evidence_refs']=['proof']
    pre=a('CheckReport',pre)
    targetp=copy.deepcopy(T['CheckReport']['payload']);targetp.update(stage='TARGET',subject=ref(snapshot),graph=ref(graph),policy=POLICY_REF,snapshot=ref(snapshot),coverage=pre['payload']['coverage'],reason='STATIC legacy TARGET stub')
    for c in targetp['checks']:c['evidence_refs']=['proof']
    target=artifact('CheckReport','origin-'+suffix+'-TARGET',targetp,scope,version);art.append(target)
    projected=[{'box':r['box'],'fragment_id':'fragment-'+role+'-'+suffix,'platform_role':{'stem':'Q','answer':'A'}[role],'platform_type':'text','region_id':r['region_id']} for role,r in zip(('stem','answer'),regions)]
    action={'action_id':'action-a02-'+h({'plan_id':'origin-'+suffix+'-ApplyPlan','question_id':'question-'+suffix,'graph':ref(graph),'snapshot':ref(snapshot)})[:32],
            'target':{'target_id':snap['target_id'],'question_id':'question-'+suffix,'platform_question_id':None},'source_entity_ids':['question-'+suffix]+[f['fragment_id'] for f in fragments],
            'expected_before':{'question_exists':False,'platform_question_id':None,'directory_id':'platform-'+suffix,'frame_count':0,'frames_hash':h([]),'next_order':1},
            'operation':'CREATE_FRAMES','expected_after':{'question_exists':True,'directory_id':'platform-'+suffix,'platform_order':1,'frames':canon(projected).decode()},'depends_on':[]}
    pp=copy.deepcopy(T['ApplyPlan']['payload']);pp.update(graph=ref(graph),precheck=ref(pre),targetcheck=ref(target),snapshot=ref(snapshot),policy=POLICY_REF,actions=[action]);plan=a('ApplyPlan',pp)
    return art

def conversion(original):
    raw=resource({'format_version':'a03-exchange-1','evidence':EVIDENCES,'policies':[POLICY],'artifacts':original},'original/new-authored-initial-a.json')
    mapped={};rows=[];resources={}
    def transform(v):
        if isinstance(v,dict):
            if set(v)=={'artifact_id','revision','kind','content_hash'}:return mapped[h(v)]
            if {'path','sha256','media_type'}<=set(v):
                key=(v['path'],v['sha256'])
                if key not in resources:
                    data=(OUT/v['path']).read_bytes()
                    if v['media_type']=='application/json':data=canon(transform(json.loads(data)))+b'\n'
                    target='converted/'+v['path'];new=raw_resource(data,target,v['media_type']);resources[key]=new
                return dict(v,**resources[key])
            return {k:('converted-a' if k=='scope_id' and x=='original-a' else transform(x)) for k,x in v.items()}
        if isinstance(v,list):return [transform(x) for x in v]
        return v
    target=[]
    for a in original:
        if a['kind'] in ('SourceBundle','EvidenceBundle','QuestionGraph','PlatformSnapshot'):
            p=transform(a['payload'])
            if a['kind']=='PlatformSnapshot':p['authorized_scope_id']='converted-a'
            new=artifact(a['kind'],'converted-a-'+a['kind'],p,'converted-a');target.append(new);mapped[h(ref(a))]=ref(new)
            rows.append({'old_ref':ref(a),'new_ref':ref(new),'disposition':'CONVERTED_INITIAL_INPUT'})
        else:rows.append({'old_ref':ref(a),'new_ref':None,'disposition':'ARCHIVE_ONLY','reason':'derived PRE/TARGET/plan depends on old stub; not equivalent to new producer/admission'})
    source,graph,snapshot=[next(x for x in target if x['kind']==k) for k in ('SourceBundle','QuestionGraph','PlatformSnapshot')]
    oracle=raw_resource((HOME/'oracle.json').read_bytes(),'oracle.json')
    observation=resource({'status':'NOT_EXECUTED_STATIC_OBSERVATION_VALUE','snapshot_ref':ref(snapshot),'scope_id':snapshot['scope_id'],'observed_at':snapshot['payload']['observed_at'],'native_admission':False},'converted/pre-observation.json')
    run_body={'format_version':'a03-synthetic-pre-run-2','context':{'kind':'INITIAL','hold_id':None,'hold_head':None,'hold_ref':None},'source_ref':ref(source),'graph_ref':ref(graph),'snapshot_ref':ref(snapshot),
         'oracle':oracle,'input_raw_sha256':source['payload']['assets'][0]['sha256'],'implementation_sha256':sha((HOME/'oracle_verifier.py').read_bytes()),
         'actual_observation':observation,'observed_at':snapshot['payload']['observed_at'],'produced_at':'2026-10-17T00:00:01Z',
         'checks':{k:'UNAVAILABLE' for k in ('source_integrity','structure','answer_matching','coverage','policy')},'runtime_status':'NOT_EXECUTED','admission':'UNIMPLEMENTED_NO_NATIVE_RUN'}
    run=resource(run_body,'converted/initial-run.json')
    hold=resource({'hold_id':'static-hold-r2','head':{'sequence':3,'hash':h('static-hold')},'scope_id':source['scope_id'],'recorded_at':'2026-10-16T23:59:59Z','status':'STATIC_NOT_NATIVE'},'post-hold/hold.json')
    post=copy.deepcopy(run_body);post['context']={'kind':'POST_HOLD','hold_id':'static-hold-r2','hold_head':{'sequence':3,'hash':h('static-hold')},'hold_ref':hold}
    resource(post,'post-hold/run.json')
    p=copy.deepcopy(next(x for x in original if x['kind']=='CheckReport')['payload']);p.update(subject=ref(graph),graph=ref(graph),decision='HOLD',reason='NOT_EXECUTED INITIAL producer; no approved oracle/registry/run',synthetic_run_ref=run,verification_context=run_body['context']);p['coverage']['scope_id']='converted-a'
    for c in p['checks']:c.update(outcome='UNAVAILABLE',reason='NOT_EXECUTED native check')
    pre=artifact('CheckReport','converted-a-new-INITIAL-PRE',p,'converted-a');target.append(pre)
    converted_evidences=transform(EVIDENCES)
    bundle={'format_version':'a03-exchange-3-proposal','evidence':converted_evidences,'policies':[POLICY],'artifacts':target};write('converted-initial.json',bundle)
    table={'format_version':'a03-static-conversion-map-3','source':raw,'target_bundle':{'path':'converted-initial.json','sha256':sha((OUT/'converted-initial.json').read_bytes())},
       'artifacts':rows,'new_derived':[{'ref':ref(pre),'origin':'fresh INITIAL context/source/graph/snapshot/run, not equivalent mapping of old PRE','native_status':'NOT_EXECUTED'}],
       'resources':[{'old_path':p,'old_sha256':s,'new_path':r['path'],'new_sha256':r['sha256']} for (p,s),r in resources.items()]}
    mapping=resource(table,'conversion/mapping.json')
    previous=None;records=[]
    for state in ('CREATED','COPYING','VALIDATING'):
        v={'format_version':'a03-conversion-record-3','conversion_id':'r2-static-conversion-a','state':state,'previous_record':previous,'source_raw_sha256':raw['sha256'],'manifest':None,'failure':None,'native_execution_eligible':False}
        previous=resource(v,'conversion/'+state+'.json');records.append(previous)
    manifest=resource({'format_version':'a03-static-completion-manifest-3','source':raw,'mapping':mapping,'target_bundle':table['target_bundle'],
       'file_inventory':[{'path':p.relative_to(OUT).as_posix(),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted([p for p in (OUT/'converted').rglob('*') if p.is_file()]+[OUT/'oracle.json'])],
       'native_execution_eligible':False,'status':'STATIC_BYTES_ONLY'},'conversion/completion-manifest.json')
    incomplete=resource({'format_version':'a03-conversion-record-3','conversion_id':'r2-static-conversion-a','state':'INCOMPLETE','previous_record':previous,'source_raw_sha256':raw['sha256'],'manifest':manifest,'failure':'STATIC rename completed but COMMITTED absent','native_execution_eligible':False},'conversion/INCOMPLETE-after-rename.json')
    committed=resource({'format_version':'a03-conversion-record-3','conversion_id':'r2-static-conversion-a','state':'COMMITTED','previous_record':previous,'source_raw_sha256':raw['sha256'],'manifest':manifest,'failure':None,'native_execution_eligible':False},'conversion/COMMITTED.json')
    failed=resource({'format_version':'a03-conversion-record-3','conversion_id':'r2-static-conversion-a','state':'FAILED','previous_record':previous,'source_raw_sha256':raw['sha256'],'manifest':None,'failure':'STATIC failure during validation','native_execution_eligible':False},'conversion/FAILED.json')
    write('conversion/case.json',{'status':'STATIC_UNIMPLEMENTED','records':records,'completion_manifest':manifest,'committed_terminal':committed,'incomplete_terminal':incomplete,'failed_terminal':failed,'mapping':mapping,'target':'converted-initial.json','source':raw,'native_qualification':False})

def session_case(a,b):
    allart=a+b;plan=a[-1];source=a[0];snapshot=next(x for x in a if x['kind']=='PlatformSnapshot');action=plan['payload']['actions'][0]
    key={'platform_namespace':'a03-synthetic','target_id':'synthetic-r2-target','book_id':plan['book_id']}
    binding={'ledger_id':'static-ledger-r2','readonly_session_id':'static-session-r2','entry_id':'entry-r2','parent_call_id':'call-r2','owner_id':'owner-r2','generation':1,'registration_id':'registration-a','target_store_id':'static-store-r2','target_session_id':'target-session-r2','target_key':key,'plan_ref':ref(plan),'scope_id':plan['scope_id'],'action_id':action['action_id'],'action_digest':h(action),'fence_token':'STATIC_NOT_NATIVE_FENCE'}
    frames=[]
    def head():return {'sequence':len(frames),'hash':frames[-1]['event']['event_hash'] if frames else ZERO}
    def append(name,p,plan_a=None):
        e={'event_version':'a03-runtime-event-3','sequence':len(frames)+1,'event':name,'journal_id':'static-journal-r2','target_key':key,'plan_ref':ref(plan_a) if plan_a else None,'owner_id':'owner-r2','generation':1,'recorded_at':'2026-10-17T00:00:00.%03dZ'%(len(frames)*50),'payload':p,'previous_hash':head()['hash']};e['event_hash']=h(e)
        frames.append({'frame_version':'a03-journal-consumer-frame-2','consumer_scope_id':plan_a['scope_id'] if plan_a else None,'input_refs':list(ordinary(e).values()),'event':e})
    append('OWNER_ACTIVE',{'fence_token':binding['fence_token']})
    anchor=None
    for items in (b,a):
        pl=items[-1];bindings=[{'action_id':x['action_id'],'action_digest':h(x)} for x in pl['payload']['actions']]
        nested=resource({'nested':resource({'source_ref':ref(items[0])})})
        append('PLAN_ACCEPTED',{'plan_ref':ref(pl),'actions':bindings,'evidence':nested},pl)
        if pl is plan:anchor=head()
        append('PLAN_ACTIONS_RESERVED',{'plan_ref':ref(pl),'reservations':bindings},pl)
        append('PLAN_INTERRUPTED',{'plan_ref':ref(pl),'reason':'EXPLICIT_STATIC_INTERRUPTION'},pl)
    h0=head();append('READONLY_ABSENCE_STARTED',{'binding':binding,'initial_event_head':h0,'counter_before':0},plan)
    observations=[]
    for n in (1,2,3):
        append('READONLY_ABSENCE_READ_STARTED',{'binding':binding,'ordinal':n,'used_count':n,'role':'CURRENTNESS' if n==3 else 'EVIDENCE','in_final_gate':n==3},plan)
        observed=resource({'format_version':'a03-static-observation-2','binding':binding,'ordinal':n,'read_sequence':n,'observation_id':'obs-r2-'+str(n),'observed_at':'2026-10-17T00:00:00.%03dZ'%(len(frames)*50-25),'target_state_hash':snapshot['payload']['observed_hash'],'target_state_version':'static-unchanged','scope_complete':True,'comparison':'ABSENT','authority':'STATIC_NOT_NATIVE'})
        observations.append(observed);append('READONLY_ABSENCE_READ_FINISHED',{'binding':binding,'ordinal':n,'observation':observed},plan)
    prefix=resource({'format_version':PREFIX,'profile_id':PROFILE,'journal_id':'static-journal-r2','target_key':key,'from_sequence':1,'predecessor':{'sequence':0,'hash':ZERO},'subject_plan_ref':ref(plan),'accepted_anchor':anchor,'expected_book_head':head(),'frames':frames},'session/prefix.json')
    prepared=resource({'format_version':'a03-readonly-prepared-2','binding':binding,'first_observation':observations[0],'facts':action['expected_before'],'capability':'READONLY_NO_DISPATCH'})
    basis={'format_version':'a03-unattempted-basis-3','binding':binding,'readonly_session_id':binding['readonly_session_id'],'gate_binding':binding,'initial_event_head':h0,'expected_event_head':head(),'complete_uncalled_prefix':prefix,'readonly_prepared_ref':prepared,'observations':observations,'observer_calls':2,'total_read_calls':3,'used_count':3,'retries':0,'single_read_seconds':2,'entry_seconds':8,'parent_seconds':60,'busy_seconds':1,'gate_seconds':5,'lease_seconds':10,'renew_seconds':2,'parent_deadline':'2026-10-17T00:01:00Z','entry_deadline':'2026-10-17T00:00:08Z','fact_key':h({'target_key':key,'plan_ref':ref(plan),'action_id':action['action_id'],'action_digest':h(action)}),'plan_status':'INTERRUPTED','comparison':'ABSENT'}
    br=resource(basis,'session/basis.json')
    result={'action_id':action['action_id'],'outcome':'NOT_APPLIED','attempt_fact':'NOT_ATTEMPTED','intent_ref':None,'platform_ids':[],'before_evidence_refs':['proof'],'after_evidence_refs':['proof'],'readback':observations[1],'effect_match':'ABSENT','next_step':'RECHECK_TARGET','replay_allowed':False,'attempt_evidence_refs':observations,'reason':'STATIC_VALUE_ONLY_UNATTEMPTED_ABSENCE'}
    fact=resource({'format_version':'a03-action-fact-3','design_only':True,'plan_ref':ref(plan),'origin_phase':'UNATTEMPTED_ABSENCE','resolution_ref':None,'intent_ref':None,'obligation_id':None,'action_id':action['action_id'],'action_digest':h(action),'prepared_before':prepared,'observed_snapshot_ref':ref(snapshot),'readback':observations[1],'comparator_version':'a02-facts-1','result':result,'journal_sequence':head()['sequence']+1,'predecessor_hash':head()['hash'],'unattempted_basis':br},'session/fact.json')
    receipt=artifact('ExecutionReceipt','r2-static-complete-receipt',{'plan':ref(plan),'execution_mode':'SIMULATED','results':[result],'action_fact_refs':[fact],'unresolved_issue_ids':[],'write_disposition':'RECHECK_TARGET'},plan['scope_id']);allart.append(receipt)
    write('scope-session.json',{'format_version':'a03-exchange-3-proposal','evidence':EVIDENCES,'policies':[POLICY],'artifacts':allart})
    write('case-index.json',{'status':'STATIC_UNIMPLEMENTED_NO_NATIVE_AUTHORITY','profile_id':PROFILE,'scope_session_bundle':'scope-session.json','subject_receipt':ref(receipt),'basis':br,'prefix':prefix,'fact':fact,'native_reads':0,'native_sessions':0,'native_admission':False})

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=False)
    SEED=load(INPUT/'intent-no-receipt-match.json')['bundle'];T={}
    for a in SEED['artifacts']:T.setdefault(a['kind'],a)
    POLICY=copy.deepcopy(SEED['policies'][0]);POLICY_REF={k:POLICY[k] for k in ('policy_id','revision','content_hash')}
    proof=raw_resource(b'R2 new hand-authored synthetic fixture; not historical or native evidence.\n','original/proof.txt','text/plain')
    EVIDENCES=[{'evidence_id':'proof','resource':proof,'description':'STATIC fixture declaration only','mode':'SYNTHETIC'}]
    kinds=schemas();a=fresh_legacy('a');b=fresh_legacy('b');conversion(a);session_case(a,b)
    write('profile.json',{'profile_id':PROFILE,'status':'STATIC_UNIMPLEMENTED','implementation_authorized':False,'new_artifact_version':VERSION,'exchange_version':'a03-exchange-3-proposal','schema_pins':[{'path':p.relative_to(OUT).as_posix(),'sha256':sha(p.read_bytes())} for p in sorted((OUT/'schemas').glob('*.json'))],
        'api_sha256':sha((OUT/'api.json').read_bytes()),'oracle_sha256':sha((HOME/'oracle.json').read_bytes()),'oracle_verifier_sha256':sha((HOME/'oracle_verifier.py').read_bytes()),'registry':[n.removeprefix('Amended') for n in kinds],
        'selection':'only candidate-final and this exact profile plus complete pins/API/oracle/verifier hashes; early candidate and old R1 are not aliases','legacy':'1.1 immutable input only; 1.2 R1 separate read-only candidate, never implicit writer upgrade',
        'source_pins':[{'path':'examples/a03/P2-R1-proposal/candidate-v2/schemas/runtime-event-prefix-v1.schema.json','sha256':sha((ROOT/'examples/a03/P2-R1-proposal/candidate-v2/schemas/runtime-event-prefix-v1.schema.json').read_bytes())}]})
    print(json.dumps({'status':'NEW_STATIC_CANDIDATE_AUTHORED','schema_pins':6,'scope_session_artifacts':len(a)+len(b)+1,'native_qualification':False}))
