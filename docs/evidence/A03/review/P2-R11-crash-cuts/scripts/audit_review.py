"""Stdlib-only cross-check of actual retained bytes, all SQL, refs and timelines."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from evidence import OUT,WORK,EV,TARGET,BASE,INDEX,MAP,load,raw,document,author_read,author_key,canon,sha,ref,write

root=Path(load(OUT/'independent-run.json')['run_root']).resolve()
DB_AUDITS=[]
def own_read(path):
    p=Path(path);p=p if p.is_absolute() else WORK/p;p=p.resolve()
    assert p.is_relative_to(root)
    return p.read_bytes()

def copied_db(label,read,path):
    b=read(path);d=OUT/'immutable-audit-copies';d.mkdir(exist_ok=True);p=d/(label+'.sqlite3')
    with p.open('xb') as f:f.write(b)
    queries=[]
    db=sqlite3.connect(p.resolve().as_uri()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row
    try:
        db.set_trace_callback(queries.append);db.execute('PRAGMA query_only=ON')
        assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows={n:[dict(r) for r in db.execute('SELECT * FROM "'+n.replace('"','""')+'"')] for n in names}
    finally:db.close()
    assert sha(p.read_bytes())==sha(b)==sha(read(path));p.unlink();d.rmdir()
    result={'label':label,'source':path,'bytes':len(b),'sha256_before_after':sha(b),'SQL':rows,'queries':queries,
        'quick_check':'ok','copy_removed':True,'original_connection':False}
    DB_AUDITS.append(result)
    return result

def ns(value):return int(datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()*1e9)

def verify_boundary(view,read):
    r=view['runtime']['tables'];t=view['target']['tables'];book=r['books'][0];reg=r['registrations'][0]
    assert view['runtime']['counts']=={k:len(v) for k,v in r.items()}
    assert view['target']['counts']=={k:len(v) for k,v in t.items()}
    bundle=json.loads(read(reg['bundle_path']));lookup={canon(ref(a)):a for a in bundle['artifacts']}
    assert {canon(json.loads(a['ref'])) for a in r['artifacts']}==set(lookup)
    formal=[]
    for row in r['artifacts']:
        b=read(row['path']);a=json.loads(b)
        assert ref(a)==json.loads(row['ref']) and a==lookup[canon(ref(a))]
        assert sha(canon({k:v for k,v in a.items() if k!='content_hash'}))==a['content_hash']
        formal.append({'ref':ref(a),'path':row['path'],'sha256':sha(b)})
    files=[]
    for row in r['files']:
        b=read(str(Path(reg['package_root']).parents[1]/row['path']));assert sha(b)==row['sha'] and len(b)==row['size']
        files.append({'path':row['path'],'sha256':sha(b),'bytes':len(b)})
    events=[json.loads(e['body']) for e in r['events']]
    for i,e in enumerate(events):
        assert sha(canon({k:v for k,v in e.items() if k!='event_hash'}))==e['event_hash']
        if i:assert e['previous_hash']==events[i-1]['event_hash'] and e['sequence']==events[i-1]['sequence']+1
    assert (book['head_sequence'],book['head_hash'])==(events[-1]['sequence'],events[-1]['event_hash'])
    resources={}
    def resource(item):
        b=read(reg['package_root'].replace('\\','/')+'/'+item['path']);assert sha(b)==item['sha256'];return b
    def walk(value):
        if isinstance(value,dict):
            if {'path','sha256','media_type'}<=set(value):
                key=(value['path'],value['sha256'],value['media_type'])
                if key in resources:return
                b=resource(value);resources[key]={'resource':value,'bytes':len(b),'actual_sha256':sha(b)}
                if value['media_type']=='application/json':walk(json.loads(b))
            else:
                for item in value.values():walk(item)
        elif isinstance(value,list):
            for item in value:walk(item)
    walk(bundle)
    return bundle,lookup,events,resource,{'formal':formal,'files':files,'resources':list(resources.values())}

POINTS={'F1':'BEFORE_INTENT_COMMIT','F2':'AFTER_DISPATCH_STARTED','F3':'AFTER_READBACK_CAPTURE','F4':'AFTER_RECEIPT_COMMIT'}
def audit_case(label,group,read,prefix):
    def doc(path):return json.loads(read(path))
    case=prefix+'cases/'+group+'/'
    final=doc(prefix+group+'-final-SQL.json');cut=doc(prefix+group+'-after-exit90-before-reopen.json')
    before=doc(case+'before-run.json');opened=doc(case+'reopened-before.json');after=doc(case+'reopened-after.json');result=doc(case+'result.json')
    for name in ('runtime','target'):
        a=copied_db(label+'-'+group+'-final-'+name,read,case+name+'/'+name+'.sqlite3')
        assert a['SQL']==final[name]['tables']==after['state'][name]['tables']
        assert a['sha256_before_after']==final[name]['raw_sha256_before']==final[name]['raw_sha256_after']
        copied_db(label+'-'+group+'-pre-'+name,read,case+'before-run-'+name+'.sqlite3')
    bundle,lookup,events,resource,bindings=verify_boundary(final,read)
    cutbundle,cutlookup,cutevents,_,cutbindings=verify_boundary(cut,read)
    assert events[:len(cutevents)]==cutevents
    assert set(cutlookup)<=set(lookup)
    r=final['runtime']['tables'];t=final['target']['tables'];cr=cut['runtime']['tables'];ct=cut['target']['tables']
    book=r['books'][0];reg=r['registrations'][0];plan=lookup[canon(before['plan_ref'])];action=plan['payload']['actions'][0]
    assert len(plan['payload']['actions'])==1 and action['operation']=='CREATE_FRAMES'
    assert plan['payload']['precheck']==before['pre_ref'] and plan['payload']['snapshot']==before['snapshot_ref']
    assert len(r['plans'])==len(r['actions'])==1 and json.loads(r['plans'][0]['ref'])==ref(plan)
    assert sha(canon(ref(plan)))==r['plans'][0]['id']==r['actions'][0]['plan']
    assert r['actions'][0]['id']==action['action_id'] and r['actions'][0]['digest']==sha(canon(action))
    assert before['claim']['generation']==cr['books'][0]['generation']==1
    assert before['claim']['owner_id']==cr['books'][0]['owner'] and before['instance']==cr['books'][0]['process_id']
    assert before['pid']==cr['books'][0]['pid'] and cr['books'][0]['phase']=='ACTIVE'
    run=r['native_pre_runs'][0];binding=json.loads(run['binding']);pre=lookup[canon(before['pre_ref'])]
    assert run['status']=='ADMITTED' and run['id']==before['native_pre_run_id'] and run['accepted_plan']==r['plans'][0]['id']
    assert json.loads(run['pre_ref'])==before['pre_ref'] and binding['owner_id']==before['claim']['owner_id'] and binding['generation']==1
    assert binding['registration_id']==reg['id'] and binding['target_session_id']==reg['session'] and binding['context']['kind']=='INITIAL'
    assert pre['payload']['decision']=='PASS' and pre['payload']['stage']=='PRE_APPLY'
    prebody=json.loads(resource(pre['payload']['synthetic_run_ref']))
    assert prebody['run_id']==run['id'] and pre['payload']['synthetic_run_ref']['sha256']==run['run_sha']
    assert prebody['checks']=={x['check_id']:x['outcome'] for x in pre['payload']['checks']}
    assert set(prebody['checks'].values())=={'PASS'}
    assert prebody['native_binding']=={k:binding[k] for k in ('registry_id','registration_id','owner_id','generation','target_store_id','target_session_id')}
    anchor=r['native_creation_anchors'][0];ab=read(anchor['input_path']);assert sha(ab)==anchor['input_sha'] and anchor['plan_artifact_id']==plan['artifact_id']
    for item in json.loads(anchor['manifest']):resource(item)
    phases={}
    for phase in ('crash','query'):
        d=prefix+'processes/'+group+'-'+phase+'/'
        start=doc(d+'started.json');end=doc(d+'completed.json');preproc=doc(d+'preregistered.json')
        assert start['pid']==end['pid'] and end['exit_code']==(90 if phase=='crash' else 0) and not end['alive'] and not end['timed_out']
        assert preproc['timeout_seconds']==45
        phases[phase]={'pid':end['pid'],'start':start['started_at_ns'],'end':end['ended_at_ns'],'exit_code':end['exit_code']}
    marker=doc(case+'crash.marker.json')
    assert marker['point']==POINTS[group] and marker['pid']==before['pid']==phases['crash']['pid']
    assert phases['crash']['pid']!=phases['query']['pid']==opened['pid']==after['pid']
    assert phases['crash']['start']<before['at_ns']<ns(marker['at'])<phases['crash']['end']<cut['recorded_at_ns']<phases['query']['start']
    assert before['instance']!=opened['instance']
    effect=int(group in ('F3','F4'))
    assert len(ct['effects'])==len(t['effects'])==effect
    assert t['effects']==ct['effects']
    assert len(r['native_report_reads'])==result['POST_count']==result['Batch_count']==0
    assert not any(a['kind']=='BatchReport' or a['kind']=='CheckReport' and a['payload']['stage']=='POST_APPLY' for a in bundle['artifacts'])
    assert result['actual_plan_status']==r['plans'][0]['status']
    names=[e['event'] for e in cutevents]
    terminal={}
    if group=='F1':
        assert not cr['intents'] and not cr['permits'] and not r['intents'] and not r['permits']
        assert not any(a['kind'] in ('WriteIntent','ExecutionReceipt','ExecutionProgress','ReconciliationResult') for a in bundle['artifacts'])
        assert result['attempt_fact'] is None and result['reconcile_calls']==0 and not r['calls'] and not r['attempts'] and not r['resolutions']
    else:
        assert len(cr['intents'])==len(cr['permits'])==1 and cr['permits'][0]['state']=='CONSUMED'
        assert names.count('DISPATCH_STARTED')==names.count('DISPATCH_PERMIT_CONSUMED')==1
        intent=r['intents'][0];ir=json.loads(intent['ref']);ia=lookup[canon(ir)]
        assert ir==json.loads(cr['intents'][0]['ref']) and ia['payload']['plan_ref']==ref(plan)
        assert ia['payload']['action_id']==action['action_id'] and ia['payload']['action_digest']==r['actions'][0]['digest']
        assert ia['payload']['source_ref']==json.loads(reg['source']) and ia['payload']['target_session_id']==reg['session']
        receipt=lookup[canon(json.loads(intent['receipt']))];factref=json.loads(r['actions'][0]['fact']);fact=json.loads(resource(factref))
        assert receipt['payload']['plan']==ref(plan) and receipt['payload']['action_fact_refs']==[factref]
        assert fact['plan_ref']==ref(plan) and fact['intent_ref']==ir and fact['action_id']==action['action_id'] and fact['action_digest']==r['actions'][0]['digest']
        rr=receipt['payload']['results'][0]
        assert rr['intent_ref']==ir and rr['action_id']==action['action_id'] and rr['attempt_fact']==fact['result']['attempt_fact']
        terminal={'receipt_ref':ref(receipt),'fact_resource':factref,'fact':fact}
        if group=='F4':
            assert 'ACTION_RESULT_COMMITTED' in names and not r['calls'] and not r['attempts'] and not r['resolutions']
            assert fact['result']['outcome']=='APPLIED' and fact['result']['attempt_fact']=='ATTEMPTED' and result['reconcile_calls']==0
        else:
            assert 'ACTION_RESULT_COMMITTED' not in names and cr['intents'][0]['state']=='PENDING' and cr['intents'][0]['receipt'] is None and cr['actions'][0]['fact'] is None
            unknown=doc(case+'pre-reconcile-UNKNOWN.json');ub,ul,ue,_,ubind=verify_boundary(unknown['state'],read)
            assert events[:len(ue)]==ue and set(ul)<=set(lookup)
            projection=unknown['projection'];assert projection['receipt_ref'] is None and projection['actions'][0]['effective_outcome']=='UNKNOWN'
            originalprogress=ul[canon(projection['progress_ref'])]
            assert originalprogress==lookup[canon(ref(originalprogress))]
            assert len(r['calls'])==len(r['attempts'])==len(r['resolutions'])==1 and result['reconcile_calls']==result['max_attempts']==1
            resolution=lookup[canon(json.loads(r['resolutions'][0]['ref']))];p=resolution['payload']
            assert p['plan_ref']==ref(plan) and p['intent_ref']==ir and p['action_id']==action['action_id'] and p['action_digest']==r['actions'][0]['digest']
            assert p['original_receipt_ref'] is None and p['replay_allowed'] is False and p['attempt_index']==1
            assert p['resolution']==('RESOLVED_NOT_APPLIED' if group=='F2' else 'RESOLVED_APPLIED') and p['observation']==('ABSENT' if group=='F2' else 'MATCH')
            readback=json.loads(resource(p['readback']));observations=[json.loads(x['body']) for x in ct['observations']]
            assert p['read_sequence']==readback['read_sequence']>max(x['read_sequence'] for x in observations if x['read_sequence'] is not None)
            assert len(t['observations'])==len(ct['observations'])+1
            observed=next(json.loads(x['body']) for x in t['observations'] if x['observation_id']==p['observation_id'])
            assert observed==readback
            assert readback['observation_id']==p['observation_id'] and readback['read_status']=='OK' and readback['scope_complete'] is True
            assert readback['target_key']==json.loads(book['target_key']) and readback['target_store_id']==binding['target_store_id']
            assert readback['target_session_id']==reg['session'] and readback['scope_id']==reg['scope'] and readback['source_ref']==json.loads(reg['source'])
            assert p['target_state_hash']==readback['target_state_hash'] and p['target_state_version']==readback['target_state_version']
            snap=lookup[canon(p['observed_snapshot_ref'])];assert snap['kind']=='PlatformSnapshot' and snap['payload']['observed_hash']==readback['target_state_hash']
            progress=[a for a in bundle['artifacts'] if a['kind']=='ExecutionProgress'][-1]['payload']
            a=progress['actions'][0];assert progress['plan_ref']==ref(plan) and a['action_id']==action['action_id'] and a['intent_ref']==ir
            assert a['result_fact']==factref and a['receipt_ref']==ref(receipt) and a['resolution_head_ref']==ref(resolution)
            assert a['attempt_fact']==projection['actions'][0]['attempt_fact']==fact['result']['attempt_fact']=='MAY_HAVE_BEEN_ATTEMPTED'
            assert [e['event'] for e in events].count('DISPATCH_STARTED')==1 and r['permits']==cr['permits']
            assert book['phase']=='RELEASED' and book['generation']==2 and book['owner'] is None and book['pid'] is None
            terminal.update(resolution_ref=ref(resolution),fresh_readback=readback,observed_snapshot_ref=ref(snap),UNKNOWN_ref=ref(originalprogress),unknown_boundary=ubind)
    stages=[]
    if label=='independent':
        expected=['pre-fault','cut-after-wait']+(['pending-before-projection','UNKNOWN-before-reconcile'] if group in ('F2','F3') else [])+['after-query-or-recovery']
        for stage in expected:
            c=doc(case+'stages/'+stage+'/capture.json');assert c['own_writer_keeper_active']==(stage=='pre-fault')
            for name in ('runtime','target'):
                v=c['databases'][name];a=copied_db(label+'-'+group+'-'+stage+'-'+name,read,v['copy'])
                assert a['SQL']==v['SQL']['tables'] and a['sha256_before_after']==v['sha256']
                assert v['read_started_at_ns']<=v['read_ended_at_ns'] and not v['sidecars']
                if stage!='pre-fault':assert v['source_sha256_after_copy']==v['sha256']
                view=cut if stage in ('cut-after-wait','pending-before-projection') else final if stage=='after-query-or-recovery' else unknown['state'] if stage=='UNKNOWN-before-reconcile' else None
                if view:assert a['SQL']==view[name]['tables'] and v['sha256']==view[name]['raw_sha256_before']
            stages.append(c)
        by={s['stage']:s for s in stages}
        assert before['at_ns']<by['pre-fault']['started_at_ns']<by['pre-fault']['ended_at_ns']<ns(marker['at'])
        assert phases['crash']['end']<by['cut-after-wait']['started_at_ns']<by['cut-after-wait']['ended_at_ns']<phases['query']['start']
        assert phases['query']['end']<by['after-query-or-recovery']['started_at_ns']
        if group in ('F2','F3'):
            assert phases['query']['start']<by['pending-before-projection']['started_at_ns']<by['pending-before-projection']['ended_at_ns']<by['UNKNOWN-before-reconcile']['started_at_ns']<by['UNKNOWN-before-reconcile']['ended_at_ns']
            assert by['UNKNOWN-before-reconcile']['ended_at_ns']/1e9<r['calls'][0]['created']
    if group in ('F1','F4'):
        for name in ('runtime','target'):
            assert cut[name]['raw_sha256_before']==opened['state'][name]['raw_sha256_before']==after['state'][name]['raw_sha256_after']==final[name]['raw_sha256_before']
        assert book['owner']==before['claim']['owner_id'] and book['generation']==1 and book['phase']=='ACTIVE'
    return {'label':label,'group':group,'verdict':'ACCEPTED_INDEPENDENT_CASE_ONLY' if label=='independent' else 'SUPPORTED_WITH_DECLARED_BINARY_LIMIT' if group in ('F2','F3') else 'SUPPORTED_RETAINED_BINARY',
        'marker':marker,'processes':phases,'original_owner':before['claim'],'original_instance':before['instance'],'query_instance':opened['instance'],
        'effects':effect,'plan_status':r['plans'][0]['status'],'final_owner':book,'result':result,'terminal':terminal,'events':events,
        'final_boundary':bindings,'cut_boundary':cutbindings,'stage_captures':stages,'auditor_product_calls':0}

cases=[]
for label,read,prefix in [('author',author_read,EV+'validation/r11-01/'),('independent',own_read,str(root)+'/')]:
    for group in POINTS:cases.append(audit_case(label,group,read,prefix))
write(OUT/'case-and-boundary-review.json',{'status':'ACCEPTED_FOUR_CRASH_CUTS_ONLY','cases':cases,'all_SQL_audits':DB_AUDITS,
 'independent_stage_raw_files':sum(len(x['stage_captures'])*2 for x in cases),'auditor_product_calls':0,'author_active_database_connections':0,
 'author_binary_limit':document(EV+'stage-binary-preservation.json'),'author_missing_intermediate_binaries_reconstructed':False,
 'whole_A03':'REWORK','I01_released':False,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print(json.dumps({'status':'ACCEPTED_FOUR_CRASH_CUTS_ONLY','cases_read':len(cases),'immutable_DB_audits':len(DB_AUDITS),'independent_stage_raw_files':sum(len(x['stage_captures'])*2 for x in cases),'product_calls':0}))
