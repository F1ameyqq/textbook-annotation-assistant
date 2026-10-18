"""Independent read-only stage, Resource, effect, process and release audit.

Reads only immutable copies in the reviewer workspace. Never opens author paths.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3

HERE=Path(__file__).resolve().parent
SNAP=HERE/'snapshot'
EV=Path('D:/1800/docs/evidence/A03/T1/review/independent-01')
GROUPS=('L1','U1','U2','U3','U4','U5')
AUTHOR_ROOT='D:/1800-worktrees/a03-t1/'

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def digest(v,field): return sha(canonical({k:x for k,x in v.items() if k!=field}))
def load(p): return json.loads(Path(p).read_bytes())
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f: json.dump(v,f,ensure_ascii=False,indent=2,sort_keys=True);f.write('\n')
def ref(a): return {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}
def map_path(path):
    s=str(path).replace('\\','/')
    if s.lower().startswith(AUTHOR_ROOT.lower()):
        p=SNAP/s[len(AUTHOR_ROOT):]
    else: p=Path(s)
    p=p.resolve()
    assert p.is_relative_to(HERE.resolve()),'attempted read outside reviewer workspace: '+str(p)
    assert p.is_file(),'missing retained file: '+str(p)
    return p
def tables(path):
    path=map_path(path)
    before=sha(path.read_bytes())
    c=sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)
    c.row_factory=sqlite3.Row
    try:
        assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        result={'application_id':c.execute('PRAGMA application_id').fetchone()[0],
                'user_version':c.execute('PRAGMA user_version').fetchone()[0],
                'tables':{r[0]:[dict(x) for x in c.execute('SELECT * FROM "'+r[0].replace('"','""')+'" ORDER BY rowid')]
                    for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()}}
    finally:c.close()
    assert sha(path.read_bytes())==before
    return result

def process_audit(root):
    entries={}
    for completed in sorted(root.rglob('completed.json')):
        v=load(completed)
        assert v['exit_code']==0 and v['alive'] is False and not v.get('timeout',v.get('timed_out',False)),str(completed)
        folder=completed.parent
        started=load(folder/'started.json')
        prereg=load(folder/'preregistered.json')
        assert started['pid']==v['pid']
        for label in ('stdout','stderr'):
            candidates=[folder/(label+'.bin'),folder/(label+'.txt')]
            stream=next((p for p in candidates if p.is_file()),None)
            assert stream is not None
            key=label+'_sha256'
            if key in v: assert sha(stream.read_bytes())==v[key]
        if 'argv' in prereg:
            argv=prereg['argv']
            if Path(argv[0]).stem.lower()=='git': assert argv[1:3]==['-c','core.longpaths=true']
        entries[str(completed.relative_to(root))]={'pid':v['pid'],'exit_code':v['exit_code'],'alive':v['alive'],
            'timeout':v.get('timeout',False),'completion_sha256':sha(completed.read_bytes())}
    return entries

def closure(runtime):
    rt=runtime['tables'];resources={};artifact_refs={};artifacts=[];seen=set()
    for row in rt['artifacts']:
        p=map_path(row['path']);a=load(p)
        assert digest(a,'content_hash')==a['content_hash']
        assert ref(a)==json.loads(row['ref'])
        artifacts.append(a);artifact_refs[canonical(ref(a))]=a
    reg,=rt['registrations']
    package=map_path(reg['bundle_path']).parent
    assert str(package).replace('\\','/').endswith(str(reg['package_root']).replace('\\','/').split('/cases/',1)[1])
    bundle=load(map_path(reg['bundle_path']))
    policies={canonical({k:p[k] for k in ('policy_id','revision','content_hash')}):p for p in bundle['policies']}
    for p in bundle['policies']: assert digest(p,'content_hash')==p['content_hash']
    def walk(v):
        if isinstance(v,dict):
            if set(v)=={'artifact_id','revision','kind','content_hash'}:
                assert canonical(v) in artifact_refs,'unresolved artifact ref: '+str(v)
            if set(v)=={'policy_id','revision','content_hash'}:
                assert canonical(v) in policies
            if {'path','sha256','media_type'}<=set(v):
                target=(package/v['path']).resolve()
                assert target.is_relative_to(package)
                assert target.is_file(),'missing Resource '+str(target)
                raw=target.read_bytes();assert sha(raw)==v['sha256']
                resources[str(target.relative_to(SNAP))]=v['sha256']
                if v['media_type']=='application/json' and target not in seen:
                    seen.add(target);walk(json.loads(raw))
            for x in v.values():walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
    walk(bundle)
    for a in artifacts:walk(a)
    for a in bundle['artifacts']:assert canonical(ref(a)) in artifact_refs
    events=[json.loads(e['body']) for e in rt['events']]
    head='0'*64
    book,=rt['books']
    for n,e in enumerate(events,1):
        assert e['sequence']==n and e['previous_hash']==head
        assert digest(e,'event_hash')==e['event_hash']
        assert e['target_key']==json.loads(book['target_key']) and e['journal_id']==book['journal']
        head=e['event_hash']
    assert book['head_sequence']==len(events) and book['head_hash']==head
    return artifacts,package,resources,events

def scene(root,name):
    case=root/'cases'/name
    expected=['before-build','unknown-established','after-release']+([] if name=='L1' else ['before-reconcile','after-reconcile'])
    phases={};dbs={};all_resources={};history={}
    for stage in expected:
        folder=case/'captures'/stage
        cap=load(folder/'capture.json')
        assert cap['status']=='RAW_COPIES_RETAINED' and cap['cross_database_atomic'] is False
        assert cap['SQL_reads_only_retained_immutable_copies']
        boundary=cap['writer_boundary']
        assert boundary['business_call_in_flight'] is False and boundary['quiescent']['owned_async_writers']==0
        assert len(boundary['threads_quiet'])==1
        assert boundary['requested_at_ns']<=boundary['joined_at_ns']<=boundary['copy_boundary_ended_at_ns']<=boundary['resumed_at_ns']
        if stage in ('before-build','unknown-established'):
            assert boundary['before']['keeper_alive'] and not boundary['quiescent']['keeper_alive'] and boundary['after']['keeper_alive']
            for snap in ('before','quiescent','after'):
                assert not any(k['error'] for k in boundary[snap]['all_keeper_threads'])
            assert boundary['before']['owner_id']==boundary['after']['owner_id']
            assert boundary['before']['generation']==boundary['after']['generation']
        values={};records={}
        assert {r['kind'] for r in cap['records']}=={'runtime','target'}
        for r in cap['records']:
            p=folder/(r['kind']+'.sqlite3');raw=p.read_bytes()
            assert not r['sidecars_after_writer_join']
            assert sha(raw)==r['sha256']==r['source_sha256_after_copy']==r['source_sha256_after_copy_audit']
            assert len(raw)==r['size']
            assert str(map_path(r['retained']))==str(p.resolve())
            values[r['kind']]=tables(p)
            records[r['kind']]={'sha256':sha(raw),'size':len(raw),'path':str(p)}
        assert values==load(folder/'SQL.json'),'stored SQL summary differs from independent immutable query'
        phases[stage]={'databases':records,'table_counts':{k:{t:len(v) for t,v in x['tables'].items()} for k,x in values.items()},
            'quiescent_ns':boundary['joined_at_ns'],'copy_end_ns':boundary['copy_boundary_ended_at_ns']}
        dbs[stage]=values
        artifacts,package,resources,events=closure(values['runtime'])
        all_resources.update(resources)
        history[stage]=(artifacts,package,events)
    bt=dbs['before-build']['runtime']['tables']
    assert not bt['intents'] and not dbs['before-build']['target']['tables']['effects']
    unknown=dbs['unknown-established'];ut=unknown['runtime']['tables']
    artifacts,package,events=history['unknown-established']
    action,=ut['actions'];intent,=ut['intents'];permit,=ut['permits'];plan,=ut['plans']
    assert action['state']=='UNKNOWN' and intent['state']=='PENDING' and permit['state']=='CONSUMED' and plan['status']=='INTERRUPTED'
    receipts=[a for a in artifacts if a['kind']=='ExecutionReceipt'];receipt,=receipts
    progress=[a for a in artifacts if a['kind']=='ExecutionProgress'][-1]
    assert receipt['payload']['write_disposition']=='PAUSE_RECONCILE'
    result,=receipt['payload']['results']
    assert result['outcome']=='UNKNOWN' and result['replay_allowed'] is False
    assert result['attempt_fact']=='MAY_HAVE_BEEN_ATTEMPTED'
    assert len(receipt['payload']['unresolved_issue_ids'])==1
    fact_resource=json.loads(action['fact']);fact=load(package/fact_resource['path'])
    assert sha((package/fact_resource['path']).read_bytes())==fact_resource['sha256']
    assert fact['result']==result and fact['intent_ref']==result['intent_ref']==json.loads(intent['ref'])
    assert fact['action_id']==action['id']==result['action_id'] and fact['action_digest']==action['digest']
    assert fact['plan_ref']==receipt['payload']['plan']==json.loads(plan['ref'])
    assert json.loads(intent['receipt'])==ref(receipt)
    projected,=progress['payload']['actions']
    assert projected['effective_outcome']=='UNKNOWN' and projected['receipt_ref']==ref(receipt) and projected['intent_ref']==result['intent_ref']
    assert projected['result_fact']==fact_resource
    execution=load(case/'execution.json')
    assert execution['comparison']==fact['result'] or execution['comparison'].get('outcome')=='UNKNOWN'
    target=lambda values:json.loads(next(r['value'] for r in values['target']['tables']['meta'] if r['key']=='state'))
    actual_target=target(unknown)
    frames=1 if name in ('L1','U1') else 2
    assert len(actual_target['target']['questions'])==1 and len(actual_target['target']['frames'])==frames
    assert len(unknown['target']['tables']['effects'])==1
    effect_row,=unknown['target']['tables']['effects'];effect=json.loads(effect_row['body'])
    assert effect['action_id']==action['id'] and effect['action_digest']==action['digest']
    if name not in ('L1','U1'): assert execution['observation']['read_status']=='UNAVAILABLE'
    else: assert execution['observation']['read_status']=='OK'
    posts=[a for a in artifacts if a['kind']=='CheckReport' and a['payload']['stage']=='POST_APPLY']
    assert not [a for a in artifacts if a['kind']=='BatchReport']
    if name=='L1':
        post,=posts;assert post['payload']['decision']=='HOLD' and post['payload']['receipt']==ref(receipt)
        assert [i['issue_id'] for i in post['payload']['issues']]==receipt['payload']['unresolved_issue_ids']
        assert 'native_report_reads' not in ut
    else:
        assert not posts and not ut['native_report_reads']
        assert receipt['payload']['unresolved_issue_ids']==['issue-save-unknown-'+sha(canonical(fact))[:32]]
    released=load(case/'owner-release.json')
    assert released['normal_release'] and released['keeper_alive'] is False
    assert not any(k['alive'] or k['error'] for k in released['lifecycle']['all_keeper_threads'])
    for st in expected[2:]:
        book,=dbs[st]['runtime']['tables']['books']
        assert book['owner'] is None and book['pid'] is None and book['lease']==0 and book['phase']=='RELEASED'
        assert dbs[st]['runtime']['tables']['intents'][0]['state']=='PENDING'
    final=dbs[expected[-1]]
    for label in ('runtime','target'):
        assert sha((case/label/(label+'.sqlite3')).read_bytes())==phases[expected[-1]]['databases'][label]['sha256']
    summary={'stage_count':len(expected),'database_count':2*len(expected),'phases':phases,'resource_count':len(all_resources),
        'resources':all_resources,'target_effect_rows':1,'frames':frames,'question_count':1,'original_receipt':ref(receipt),
        'unresolved_issue_ids':receipt['payload']['unresolved_issue_ids'],'native_report_reads':'NOT_APPLICABLE_NO_TABLE' if name=='L1' else 0,
        'final_owner_released':True,'pending':1,'paused':True,'dispatch_count_from_effects_and_permits':1}
    if name!='L1':
        before=dbs['before-reconcile'];after=dbs['after-reconcile'];rt=after['runtime']['tables']
        for table in ('actions','intents','permits'):assert before['runtime']['tables'][table]==rt[table]
        assert before['target']['tables']['effects']==after['target']['tables']['effects']
        for key in ('target','internal_bindings','frame_projections'):assert target(before)[key]==target(after)[key]
        assert len(rt['attempts'])==len(rt['calls'])==len(rt['resolutions'])==1
        assert not rt['native_report_reads']
        resolution,=[a for a in history['after-reconcile'][0] if a['kind']=='ReconciliationResult']
        p=resolution['payload'];expected_class='CONFLICT' if name in ('U1','U2') else 'INDETERMINATE'
        assert p['resolution']=='STILL_UNKNOWN' and p['observation']==expected_class and p['attempt_index']==1
        assert p['action_id']==action['id'] and p['action_digest']==action['digest'] and p['intent_ref']==fact['intent_ref']
        assert p['original_receipt_ref']==ref(receipt)
        final_receipt,=[a for a in history['after-reconcile'][0] if a['kind']=='ExecutionReceipt']
        assert final_receipt==receipt
        package=history['after-reconcile'][1];obs=load(package/p['readback']['path'])
        descriptor=json.loads(next(r['value'] for r in after['target']['tables']['meta'] if r['key']=='descriptor'))
        assert obs['target_key']==descriptor['target_key']
        assert obs['source_ref']==descriptor['fixed_source_ref'] and obs['scope_id']==descriptor['fixed_scope_id']
        assert obs['store_id']==obs['target_store_id']==descriptor['store_id'] and obs['target_session_id']==descriptor['target_session_id']
        persisted,=[json.loads(r['body']) for r in after['target']['tables']['observations'] if r['observation_id']==obs['observation_id']]
        assert persisted==obs
        assert obs['read_status']==dict(U1='OK',U2='OK',U3='CONTRADICTORY',U4='TRUNCATED',U5='UNAVAILABLE')[name]
        assert obs['scope_complete']==obs['relevant_scope_completeness']==(name in ('U1','U2','U3'))
        if name=='U5':
            assert all(obs[k] is None for k in ('view','state','read_sequence','target_state_hash','target_state_version'))
        else:
            old=execution['observation']['read_sequence'] or execution['prepared']['observation']['read_sequence']
            assert obs['read_sequence']>old
        if name=='U2':
            ids=[q['platform_question_id'] for q in obs['view']['target']['questions']]
            assert len(ids)==2 and len(set(ids))==1
        assert (p['observed_snapshot_ref'] is not None)==(name=='U1')
        result=load(case/'reconcile-result.json')
        assert result['attempt_count']==1 and result['pending_count']==1 and result['paused']
        assert len(result['resolutions'])==1 and 'code' not in result['resolutions'][0]
        summary.update(resolution=ref(resolution),classification=expected_class,read_status=obs['read_status'],
            read_sequence=obs['read_sequence'],observation_id=obs['observation_id'],restoration_new_effects=0,reconcile_calls=1,max_attempts=1)
    return summary

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--label',required=True)
    args=parser.parse_args();root=args.run.resolve()
    assert root.is_relative_to(HERE)
    scenes={}
    for name in GROUPS:scenes[name]=scene(root,name)
    processes=process_audit(root)
    # Author outer runs/static Git/fixture processes live above validation.
    if args.label=='author':processes=process_audit(SNAP/'docs/evidence/A03/T1/execution')
    result=dict(status='INDEPENDENT_STATIC_AUDIT_PASS',label=args.label,root=str(root),scenes=scenes,
        logical_stages=sum(x['stage_count'] for x in scenes.values()),database_originals=sum(x['database_count'] for x in scenes.values()),
        processes=processes,process_count=len(processes),business_calls=0,SQL='own immutable copies only',
        known_author_seal='NOT_RUN_KNOWN_LEGACY_TABLE_ASSUMPTION',field_reset='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION')
    save(EV/(args.label+'-semantic-audit.json'),result)
    print(json.dumps(dict(status=result['status'],label=args.label,stages=result['logical_stages'],databases=result['database_originals'],processes=len(processes),matrix={k:v.get('classification','LEGACY_HOLD') for k,v in scenes.items()}),indent=2))

if __name__=='__main__':main()
