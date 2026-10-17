# -*- coding: utf-8 -*-
"""Independent final SQL, resource, timeline, process and import audit; stdlib only."""
import json
from pathlib import Path
from datetime import datetime
import sqlite3
from evidence import OUT,WORK,EV,TARGET,BASE,INDEX,MAP,load,raw,document,text,author_read,author_key,canon,sha,ref,write

def copy_db(label,read,source):
    folder=OUT/'immutable-audit-copies';folder.mkdir(exist_ok=True);path=folder/(label+'.sqlite3');b=read(source)
    with path.open('xb') as f:f.write(b)
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row;queries=[]
    try:
        db.set_trace_callback(queries.append);db.execute('PRAGMA query_only=ON');assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows={n:[dict(r) for r in db.execute('SELECT * FROM "'+n.replace('"','""')+'"')] for n in names}
    finally:db.close()
    assert sha(path.read_bytes())==sha(b)==sha(read(source));path.unlink();folder.rmdir()
    return {'source':source,'source_sha256_before_after':sha(b),'copy_sha256_before_after':sha(b),'copy_removed':True,
      'quick_check':'ok','mode':'mode=ro&immutable=1; query_only=ON','counts':{n:len(v) for n,v in rows.items()},'rows':rows,'queries':queries}

def owned(view,pid,instance,claim):
    b=view['book'];assert b['owner']==claim['owner_id'] and b['generation']==claim['generation'] and b['pid']==pid and b['process_id']==instance and b['phase']=='ACTIVE'
    assert b['lease']>view['recorded_at_ns']/1e9
    assert json.loads(b['target_key'])==claim['target_key']
    assert view['target_fence']=={'fence_owner_id':claim['owner_id'],'fence_generation':claim['generation']}
def zero(view):
    assert all(view['runtime']['counts'][n]==0 for n in ('plans','actions','intents','permits')) and view['target']['counts']['effects']==0
def time_ns(iso):return int(datetime.fromisoformat(iso.replace('Z','+00:00')).timestamp()*1e9)

def audit_case(label,group,read,prefix):
    case=prefix+'cases/'+group+'/';control=prefix+'control/'+group+'/'
    def doc(path):return json.loads(read(path))
    def ctl(name):return doc(control+name)
    runtime=copy_db(label+'-'+group+'-runtime',read,case+'runtime/runtime.sqlite3');target=copy_db(label+'-'+group+'-target',read,case+'target/target.sqlite3')
    r=runtime['rows'];t=target['rows'];rc=runtime['counts'];tc=target['counts'];book=r['books'][0];reg=r['registrations'][0]
    final=doc(prefix+group+'-result.json')['final_state'];assert final['runtime']['tables']==r and final['target']['tables']==t
    assert final['runtime']['raw_sha256_before']==final['runtime']['raw_sha256_after']==runtime['source_sha256_before_after']
    assert final['target']['raw_sha256_before']==final['target']['raw_sha256_after']==target['source_sha256_before_after']
    zero(final);assert book['phase']=='RELEASED' and book['owner'] is None and book['pid'] is None and book['lease']==0 and book['hold'] is None
    assert rc['resolutions']==rc['native_report_reads']==0
    bundle=doc(reg['bundle_path']);lookup={canon(ref(a)):a for a in bundle['artifacts']};formal=[]
    assert {canon(json.loads(a['ref'])) for a in r['artifacts']}==set(lookup)
    for a in bundle['artifacts']:assert sha(canon({k:v for k,v in a.items() if k!='content_hash'}))==a['content_hash']
    for row in r['artifacts']:
        b=read(row['path']);a=json.loads(b);assert ref(a)==json.loads(row['ref']) and a==lookup[canon(ref(a))]
        formal.append({'ref':ref(a),'path':row['path'],'raw_sha256':sha(b)})
    events=[json.loads(e['body']) for e in r['events']];previous=None
    for e in events:
        assert sha(canon({k:v for k,v in e.items() if k!='event_hash'}))==e['event_hash']
        if previous:assert e['previous_hash']==previous['event_hash']
        previous=e
    assert (book['head_sequence'],book['head_hash'])==(events[-1]['sequence'],events[-1]['event_hash'])
    assert events[-1]['event']=='OWNER_RELEASED' and events[-1]['owner_id'] is None
    package=reg['package_root'].replace('\\','/');resource_rows={}
    def resource(item):
        b=read(package+'/'+item['path']);assert sha(b)==item['sha256'];return b
    def walk(value):
        if isinstance(value,dict):
            if {'path','sha256','media_type'}<=set(value):
                key=(value['path'],value['sha256'],value['media_type'])
                if key in resource_rows:return
                b=resource(value);resource_rows[key]={'ref':value,'bytes':len(b),'actual_sha256':sha(b)}
                if value['media_type']=='application/json':walk(json.loads(b))
            else:
                for x in value.values():walk(x)
        elif isinstance(value,list):
            for x in value:walk(x)
    walk(bundle)
    workers={}
    for role in ('A','B'):
        d=prefix+'processes/'+group+'-'+role+'/'
        pre=doc(d+'preregistered.json');start=doc(d+'started.json');end=doc(d+'completed.json')
        assert pre['timeout_seconds']==45 and start['pid']==end['pid'] and end['exit_code']==0 and not end['alive'] and not end['timed_out']
        workers[role]={'pid':end['pid'],'started_at_ns':start['started_at_ns'],'ended_at_ns':end['ended_at_ns']}
    out={'label':label,'group':group,'runtime':runtime,'target':target,'final_book':book,'final_target_fence':final['target_fence'],
      'formal_artifacts':formal,'events':events,'workers':workers,'snapshot_limit':'each live database read transaction is separate; sequential dual DB and raw reads are not atomic cross-database proof',
      'business_rows_plans_actions_intents_permits':[rc[n] for n in ('plans','actions','intents','permits')],'effects':0,'auditor_product_calls':0}
    if group=='C1':
        assert rc['artifacts']==4 and rc['events']==3 and rc['native_pre_runs']==rc['native_creation_anchors']==tc['observations']==0
        ready={role:ctl(role+'-ready.json') for role in ('A','B')};markers={role:ctl(role+'-BEFORE_CLAIM.json') for role in ('A','B')}
        before=ctl('before-common-release.json');go=ctl('claim-go.barrier');live=ctl('simultaneous-competition.json');claims=live['claims']
        assert before['both_alive'] and live['both_processes_still_alive'] and go['participants_ready_before_release']
        assert workers['A']['pid']!=workers['B']['pid'] and ready['A']['instance']!=ready['B']['instance']
        for role in ('A','B'):
            assert ready[role]['pid']==markers[role]['pid']==claims[role]['pid']==workers[role]['pid']==live[role+'_pid']==before[role+'_pid']
            assert markers[role]['point']=='BEFORE_CLAIM' and before['markers'][role+'-BEFORE_CLAIM.json']==markers[role]
            assert workers[role]['started_at_ns']<ready[role]['at_ns']<go['at_ns']
            assert time_ns(markers[role]['at'])<=before['at_ns']<go['at_ns']<claims[role]['at_ns']<live['at_ns']<workers[role]['ended_at_ns']
            finish=ctl(role+'-finish.barrier');assert live['at_ns']<finish['at_ns']<workers[role]['ended_at_ns']
        winners=[role for role,c in claims.items() if c['outcome']=='ACTIVE'];losers=[role for role,c in claims.items() if c['outcome']=='REFUSED']
        assert len(winners)==len(losers)==1 and live['winner']==winners[0]
        winner=winners[0];win=claims[winner];lose=claims[losers[0]]
        assert win['instance']==ready[winner]['instance'] and win['claim']['owner_id']==ready[winner]['owner_id']
        assert lose['type']=='RuntimeFailure' and lose['code']=='OWNER_BUSY' and lose['message']=='lease expired AND previous process exited required' and 'in claim' in lose['traceback']
        owned(live['observed_state'],win['pid'],win['instance'],win['claim']);zero(live['observed_state'])
        assert [e['event'] for e in events]==['OWNER_CLAIM_RESERVED','OWNER_ACTIVE','OWNER_RELEASED']
        assert book['generation']==win['claim']['generation']==1 and book['process_id']==win['instance']
        assert final['target_fence']==live['observed_state']['target_fence']
        released=ctl(winner+'-released.json');assert released['pid']==win['pid'] and released['claim']==win['claim'] and live['at_ns']<released['at_ns']<workers[winner]['ended_at_ns']
        out.update(winner=winner,winner_claim=win,loser_refusal=lose,both_live_observation_ns=live['at_ns'],common_release_ns=go['at_ns'],ready=ready,markers=markers,
          scope='same-book claim mutual exclusion with two live participants; no business plan/effect competition')
    else:
        assert rc['artifacts']==8 and rc['events']==6 and rc['native_pre_runs']==rc['native_creation_anchors']==tc['observations']==1
        q=ctl('A-qualified.json');released=ctl('A-released.json');active=ctl('B-active.json');before=ctl('before-stale-call.json');signal=ctl('A-stale-attempt.barrier');stale=ctl('A-stale-result.json');live=ctl('after-stale-live-observation.json');b_release=ctl('B-released.json')
        assert q['pid']==released['pid']==stale['pid']==workers['A']['pid']==before['A_pid']
        assert active['pid']==b_release['pid']==workers['B']['pid']==before['B_pid']
        assert q['instance']!=active['instance'] and workers['A']['pid']!=workers['B']['pid']
        assert q['claim']==released['old_claim']==stale['old_claim']==before['old_claim'] and before['new_claim']==active['claim']
        assert q['claim']['generation']==1 and active['claim']['generation']==book['generation']==2
        owned(q['state'],q['pid'],q['instance'],q['claim']);zero(q['state'])
        assert released['state']['book']['phase']=='RELEASED' and released['state']['book']['owner'] is None
        owned(active['state'],active['pid'],active['instance'],active['claim'])
        for view in (before['state'],stale['before'],stale['after'],live['state']):owned(view,active['pid'],active['instance'],active['claim']);zero(view)
        assert before['both_alive'] and live['both_alive'] and stale['old_owner_renew_or_release_after_handover']==0
        refusal=stale['refusal'];assert refusal['type']=='RuntimeFailure' and refusal['code']=='OWNER_GENERATION_STALE' and refusal['message']=='current ACTIVE lease required'
        assert refusal['root_lease_guard_reached'] and 'in run_plan' in refusal['traceback'] and 'in _lease' in refusal['traceback']
        for name in ('plans','actions','intents','permits','artifacts','native_pre_runs','native_creation_anchors','events'):
            assert stale['before']['runtime']['counts'][name]==stale['after']['runtime']['counts'][name]
        assert stale['before']['runtime']['tables']['events']==stale['after']['runtime']['tables']['events']
        assert stale['before']['target']['counts']==stale['after']['target']['counts'] and stale['before']['target_fence']==stale['after']['target_fence']
        order=[q['at_ns'],ctl('A-release.barrier')['at_ns'],released['at_ns'],active['at_ns'],before['at_ns'],signal['at_ns'],stale['at_ns'],live['at_ns'],ctl('B-finish.barrier')['at_ns'],b_release['at_ns'],workers['B']['ended_at_ns']]
        assert all(x<y for x,y in zip(order,order[1:])) and workers['A']['started_at_ns']<q['at_ns'] and workers['B']['started_at_ns']<active['at_ns']
        assert live['at_ns']<workers['A']['ended_at_ns'] and live['at_ns']<ctl('A-finish.barrier')['at_ns']<workers['A']['ended_at_ns']
        assert [e['event'] for e in events]==['OWNER_CLAIM_RESERVED','OWNER_ACTIVE','OWNER_RELEASED']*2
        assert final['target_fence']==active['state']['target_fence'] and book['process_id']==active['instance']
        plan=lookup[canon(q['plan_ref'])];pre=lookup[canon(q['pre_ref'])];run=r['native_pre_runs'][0];anchor=r['native_creation_anchors'][0]
        assert plan['kind']=='ApplyPlan' and len(plan['payload']['actions'])==1 and plan['payload']['actions'][0]['operation']=='CREATE_FRAMES'
        assert plan['payload']['precheck']==q['pre_ref'] and plan['payload']['snapshot']==q['snapshot_ref']
        assert pre['kind']=='CheckReport' and pre['payload']['stage']=='PRE_APPLY' and pre['payload']['decision']=='PASS'
        assert run['status']=='ADMITTED' and run['accepted_plan'] is None and run['id']==q['native_pre_run_id'] and json.loads(run['pre_ref'])==q['pre_ref']
        binding=json.loads(run['binding']);assert binding['owner_id']==q['claim']['owner_id'] and binding['generation']==q['claim']['generation'] and binding['context']['kind']=='INITIAL'
        value=json.loads(resource(pre['payload']['synthetic_run_ref']));assert run['run_sha']==pre['payload']['synthetic_run_ref']['sha256'] and value['run_id']==run['id']
        checks={c['check_id']:c['outcome'] for c in pre['payload']['checks']};assert value['checks']==checks and len(checks)==5 and set(checks.values())=={'PASS'}
        assert value['native_binding']=={k:binding[k] for k in ('registry_id','registration_id','owner_id','generation','target_store_id','target_session_id')}
        assert anchor['plan_artifact_id']==plan['artifact_id'];anchor_raw=read(anchor['input_path']);assert sha(anchor_raw)==anchor['input_sha'] and canon(json.loads(anchor_raw))==anchor_raw
        for item in json.loads(anchor['manifest']):resource(item)
        out.update(plan_ref=q['plan_ref'],PRE_ref=q['pre_ref'],native_PRE_run_id=run['id'],creation_anchor=anchor,qualified_plan_actions=plan['payload']['actions'],
          A_qualified=q,B_active=active,stale_refusal=refusal,stale_before_after=stale,live_observation=live,ordered_stage_times_ns=order,
          scope='real normal handover then live old process/store/claim refused at run_plan lease guard before acceptance/dispatch')
    out['recursive_resource_checks']=list(resource_rows.values())
    return out

identity=load(OUT/'independent-run.json');root=Path(identity['run_root']).resolve()
def independent_read(path):
    p=Path(path);p=p if p.is_absolute() else WORK/p;p=p.resolve();assert p.is_relative_to(root);return p.read_bytes()
case_results=[]
for label,read,prefix in [('author',author_read,EV+'validation/r10-01/'),('independent',independent_read,str(root)+'/')]:
    for group in ('C1','C2'):case_results.append(audit_case(label,group,read,prefix))

release=document(EV+'process-release.json');author_processes=[]
for row in release['records']:
    d=EV+row['path'].rsplit('/',1)[0]+'/'
    pre=document(d+'preregistered.json');start=document(d+'started.json');end=document(d+'completed.json')
    assert row['pid']==start['pid']==end['pid'] and row['exit_code']==end['exit_code']==0
    assert not row['alive'] and not row['timed_out'] and not end['alive'] and not end.get('timed_out',end.get('timeout',True))
    assert pre['argv'] and pre['cwd'] and 0<pre['timeout_seconds']<=90
    if 'script_pins' in pre:
        for source,digest in pre['script_pins'].items():
            rev=TARGET if (TARGET,source) in MAP else BASE
            assert sha(raw(source,rev))==digest==sha(raw(d+'script-snapshots/'+Path(source).name))
    else:
        source='tests/test_a03_p2_r10_owner_fencing.py' if '/processes/' in d else 'src/annotation/runtime/recovery/native_observation.py'
        assert pre['script_sha256']==sha(raw(source))==sha(raw(d+'script-snapshot.py'))
        if 'input_sha256' in pre:assert sha(raw(d+'request.json'))==pre['input_sha256']
    for stream in ('stdout','stderr'):
        if stream+'_sha256' in end:assert sha(raw(d+stream+'.txt'))==end[stream+'_sha256']
    author_processes.append({'record':d[len(EV):-1],'pid':end['pid'],'exit_code':0,'argv':pre['argv'],'cwd':pre['cwd'],'timeout_seconds':pre['timeout_seconds'],
      'alive':False,'timed_out':False,'stdout_sha256':sha(raw(d+'stdout.txt')),'stderr_sha256':sha(raw(d+'stderr.txt'))})
assert len(author_processes)==len(release['records'])

CRLF={'src/annotation/__init__.py','src/annotation/contracts/__main__.py','src/annotation/contracts/cli.py','src/annotation/contracts/integrity.py','src/annotation/contracts/models.py'}
def author_source(source,digest):
    b=raw(source)
    if sha(b)==digest:return 'RAW_GIT_BYTES'
    assert source in CRLF and b'\r\n' not in b and sha(b.replace(b'\n',b'\r\n'))==digest
    return 'EXPLICIT_EXISTING_LF_TO_CRLF'
author_imports=[]
for row in INDEX:
    if row['commit']==TARGET and row['path'].startswith(EV+'validation/r10-01/imports/') and row['path'].endswith('.json'):
        for name,m in document(row['path'])['modules'].items():
            source=author_key(m['path']);author_imports.append({'record':row['path'],'module':name,'actual_file':m['path'],'sha256':m['sha256'],'representation':author_source(source,m['sha256'])})
source_indices=[]
for group in ('C1','C2'):
    p=EV+'runs/'+group+'/';body=raw(p+'product-source-index.json');assert sha(body)==document(p+'preregistered.json')['product_source_index_sha256']
    rows=json.loads(body);representations=[{'path':r['path'],'sha256':r['sha256'],'representation':author_source(r['path'],r['sha256'])} for r in rows]
    source_indices.append({'group':group,'index_sha256':sha(body),'files':representations})
assert len({r['index_sha256'] for r in source_indices})==1
write(OUT/'case-and-timeline-review.json',{'status':'ACCEPTED_OWNER_FENCING_TWO_CASES_ONLY','cases':case_results,'unique_immutable_DB_copies':len(case_results)*2,
 'original_DB_connections':0,'auditor_product_calls':0,'both_groups_independent_rounds':1,'whole_A03':'REWORK','I01_released':False,
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
write(OUT/'author-process-review.json',{'status':'ACTUAL_FROZEN_AUTHOR_PROCESS_AND_SOURCE_RECORDS_RECONCILED','records':author_processes,'actual_imports':author_imports,
 'source_indices':source_indices,'process_count':len(author_processes),'current_OS_PID_scan':False,'product_calls_by_auditor':0})
print(json.dumps({'status':'ACCEPTED_OWNER_FENCING_TWO_CASES_ONLY','cases_read':len(case_results),'DB_copies':len(case_results)*2,'author_processes':len(author_processes),'auditor_product_calls':0}))
