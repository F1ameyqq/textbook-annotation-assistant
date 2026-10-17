# -*- coding: utf-8 -*-
"""Own immutable SQL/Resource readback of completed cases, stdlib only."""
import json
from pathlib import Path
import sqlite3
from evidence import OUT,WORK,EV,load,author_read,canon,sha,ref,write

def copy_db(label,read,source):
    folder=OUT/'immutable-case-copies';folder.mkdir(exist_ok=True);path=folder/(label+'.sqlite3');body=read(source);before=sha(body)
    with path.open('xb') as f:f.write(body)
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row;queries=[]
    try:
        db.set_trace_callback(queries.append);db.execute('PRAGMA query_only=ON');assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows={n:[dict(r) for r in db.execute('SELECT * FROM "'+n.replace('"','""')+'"')] for n in names}
    finally:db.close()
    assert sha(path.read_bytes())==before==sha(read(source));path.unlink();folder.rmdir()
    return {'source':source,'source_sha256_before_after':before,'copy_sha256_before_after':before,'copy_removed':True,
      'mode':'mode=ro&immutable=1; query_only=ON','quick_check':'ok','counts':{k:len(v) for k,v in rows.items()},'rows':rows,'queries':queries}

def case_audit(label,group,read,prefix):
    case=prefix+'cases/'+group+'/'
    runtime=copy_db(label+'-'+group+'-runtime',read,case+'runtime/runtime.sqlite3');target=copy_db(label+'-'+group+'-target',read,case+'target/target.sqlite3')
    r=runtime['rows'];t=target['rows'];rc=runtime['counts'];tc=target['counts'];d2=group=='D2'
    assert all(rc[n]==1 for n in ('plans','actions','intents','native_pre_runs','native_creation_anchors'))
    assert rc['permits']==(0 if d2 else 1) and tc['effects']==(0 if d2 else 1)
    reg=r['registrations'][0];book=r['books'][0];action=r['actions'][0];intent=r['intents'][0];planrow=r['plans'][0]
    assert book['phase']=='RELEASED' and book['owner'] is None and book['pid'] is None and book['lease']==0 and book['hold'] is None
    bundle=json.loads(read(reg['bundle_path']));lookup={canon(ref(a)):a for a in bundle['artifacts']};formal=[]
    assert {canon(json.loads(a['ref'])) for a in r['artifacts']}==set(lookup)
    for a in bundle['artifacts']:assert sha(canon({k:v for k,v in a.items() if k!='content_hash'}))==a['content_hash']
    for row in r['artifacts']:
        b=read(row['path']);a=json.loads(b);assert json.loads(row['ref'])==ref(a) and lookup[canon(ref(a))]==a
        formal.append({'ref':ref(a),'path':row['path'],'raw_sha256':sha(b)})
    planref=json.loads(planrow['ref']);plan=lookup[canon(planref)];intentref=json.loads(intent['ref']);receiptref=json.loads(intent['receipt']);receipt=lookup[canon(receiptref)]
    assert planrow['id']==sha(canon(planref))==action['plan']==intent['plan']
    assert len(plan['payload']['actions'])==1 and plan['payload']['actions'][0]['operation']=='CREATE_FRAMES'
    planned=plan['payload']['actions'][0];assert planned['action_id']==action['id']==intent['action'] and sha(canon(planned))==action['digest']
    assert action['intent']==intent['id'] and planrow['status']==('INTERRUPTED' if d2 else 'FINISHED')
    assert action['state']==('NOT_APPLIED' if d2 else 'APPLIED') and intent['state']==('RESOLVED_NOT_APPLIED' if d2 else 'APPLIED')
    package=reg['package_root'].replace('\\','/');resources=[]
    def resource(item):
        b=read(package+'/'+item['path']);assert sha(b)==item['sha256'];resources.append({'ref':item,'bytes':len(b),'actual_sha256':sha(b)});return json.loads(b)
    run=r['native_pre_runs'][0];pre=lookup[canon(json.loads(run['pre_ref']))]
    assert run['status']=='ADMITTED' and run['accepted_plan']==planrow['id'] and pre['payload']['stage']=='PRE_APPLY'
    pre_run=resource(pre['payload']['synthetic_run_ref']);assert run['run_sha']==pre['payload']['synthetic_run_ref']['sha256']
    assert pre_run['checks']=={c['check_id']:c['outcome'] for c in pre['payload']['checks']} and len(pre_run['checks'])==5 and set(pre_run['checks'].values())=={'PASS'}
    factref=json.loads(action['fact']);fact=resource(factref)
    assert fact['plan_ref']==planref and fact['intent_ref']==intentref and fact['action_id']==action['id'] and fact['action_digest']==action['digest']
    assert receipt['payload']['plan']==planref and receipt['payload']['action_fact_refs']==[factref] and receipt['payload']['results']==[fact['result']]
    assert fact['result']['intent_ref']==intentref and fact['result']['action_id']==action['id'] and not fact['result']['replay_allowed']
    resource(fact['prepared_before']);readback=resource(fact['readback'])
    observations={row['observation_id']:json.loads(row['body']) for row in t['observations']}
    assert readback['observation_id'] in observations and observations[readback['observation_id']]['read_sequence']==readback['read_sequence']
    assert readback['read_status']=='OK' and readback['scope_complete'] and readback['relevant_scope_completeness']
    material=[]
    for a in bundle['artifacts']:
        if a['kind']!='ExecutionProgress':continue
        for item in a['payload']['actions']:
            if item.get('result_fact') is None:continue
            assert a['payload']['plan_ref']==planref and item['action_id']==action['id'] and item['intent_ref']==intentref
            assert item['result_fact']==factref and item['attempt_fact']==fact['result']['attempt_fact'] and item['attempt_evidence_refs']==fact['result']['attempt_evidence_refs']
            assert canon(item['receipt_ref']) in lookup;material.append(ref(a))
    assert material
    events=[json.loads(row['body']) for row in r['events']];previous=None
    for e in events:
        assert sha(canon({k:v for k,v in e.items() if k!='event_hash'}))==e['event_hash']
        if previous:assert e['previous_hash']==previous['event_hash']
        previous=e
    assert (book['head_sequence'],book['head_hash'])==(events[-1]['sequence'],events[-1]['event_hash'])
    postlist=[a for a in bundle['artifacts'] if a['kind']=='CheckReport' and a['payload']['stage']=='POST_APPLY'];batchlist=[a for a in bundle['artifacts'] if a['kind']=='BatchReport']
    result={'group':group,'runtime':runtime,'target':target,'current_bundle_path':reg['bundle_path'],'current_bundle_raw_sha256':sha(read(reg['bundle_path'])),
      'formal_artifacts':formal,'plan_ref':planref,'plan_status':planrow['status'],'plan_cursor':planrow['cursor'],'intent_ref':intentref,'current_intent_receipt_ref':receiptref,'action_id':action['id'],'action_digest':action['digest'],
      'fact_ref':factref,'fact':fact,'material_progress_refs':material,'book':book,'events':events,'resource_checks':resources,
      'effect_count':tc['effects'],'report_read_count':rc['native_report_reads'],'native_API_calls_by_auditor':0}
    if not d2:
        assert r['permits'][0]['state']=='CONSUMED' and r['permits'][0]['intent']==intent['id']
        effect=json.loads(t['effects'][0]['body']);assert effect['plan_ref']==planref and effect['action_id']==action['id'] and effect['action_digest']==action['digest'] and effect['mutated']
        assert effect['owner_id']==intent['owner'] and effect['generation']==intent['generation']
        assert fact['origin_phase']=='EXECUTION' and fact['resolution_ref'] is None and fact['result']['outcome']=='APPLIED' and fact['result']['attempt_fact']=='ATTEMPTED'
        assert len(postlist)==len(batchlist)==rc['native_report_reads']==1
        post,batch=postlist[0],batchlist[0];pp,bp=post['payload'],batch['payload'];report_receipt=lookup[canon(pp['receipt'])]
        assert report_receipt['payload']['plan']==planref and report_receipt['payload']['action_fact_refs']==[factref] and report_receipt['payload']['results']==[fact['result']]
        assert bp['receipt']==pp['receipt'] and bp['postcheck']==ref(post) and bp['report_snapshot_ref']==pp['report_snapshot_ref']
        assert pp['content_check_status']==bp['content_check_status']=='PENDING' and pp['submission_status']==bp['submission_status']=='NOT_SUBMITTED' and bp['state']=='CONTENT_PENDING' and pp['frame_structure']=='PASS'
        assert pp['report_snapshot_ref']!=fact['observed_snapshot_ref'] and pp['report_observation']['sha256']!=fact['readback']['sha256']
        assert canon(pp['report_snapshot_ref']) in lookup
        reportobs=resource(pp['report_observation']);assert reportobs['observation_id'] in observations
        assert reportobs['read_sequence']==observations[reportobs['observation_id']]['read_sequence'] and reportobs['target_state_hash']==observations[reportobs['observation_id']]['target_state_hash']
        meta={row['key']:row['value'] for row in r['meta']}
        assert reportobs['target_store_id']==meta['target_store_id'] and reportobs['target_session_id']==reg['session']
        assert reportobs['source_ref']==json.loads(reg['source']) and reportobs['scope_id']==reg['scope']
        binding=pp['action_bindings'][0];assert len(pp['action_bindings'])==1
        assert binding['action_id']==action['id'] and binding['action_digest']==action['digest'] and binding['intent_ref']==intentref and binding['fact_ref']==factref
        assert binding['resolution_head_ref'] is None and binding['head_original_receipt_ref'] is None
        assert r['native_report_reads'][0]['plan_id']==planrow['id'] and r['native_report_reads'][0]['reads']==1
        result.update(POST_ref=ref(post),Batch_ref=ref(batch),report_bound_receipt_ref=pp['receipt'],report_observation_ref=pp['report_observation'],report_observation_id=reportobs['observation_id'],effect=effect)
    else:
        assert not postlist and not batchlist and rc['native_report_reads']==0 and rc['resolutions']==rc['calls']==rc['attempts']==1
        assert fact['origin_phase']=='RECOVERY' and fact['result']['outcome']=='NOT_APPLIED' and fact['result']['effect_match']=='ABSENT'
        headref=json.loads(r['resolutions'][0]['ref']);head=lookup[canon(headref)];hp=head['payload']
        assert fact['resolution_ref']==headref and hp['resolution']=='RESOLVED_NOT_APPLIED' and hp['observation']==hp['reason_code']=='ABSENT'
        assert hp['plan_ref']==planref and hp['intent_ref']==intentref and hp['action_id']==action['id'] and hp['action_digest']==action['digest']
        assert hp['original_receipt_ref'] is None and hp['observed_snapshot_ref']==fact['observed_snapshot_ref'] and hp['readback']==fact['readback']
        assert hp['observation_id']==readback['observation_id'] and hp['read_sequence']==readback['read_sequence']
        assert not readback['effect_log'] and not readback['view']['target']['frames'] and not readback['view']['target']['questions']
        before=json.loads(read(case+'restarted-projection-before.json'));after=json.loads(read(case+'restarted-projection-after.json'))
        assert before['receipt_ref'] is None and before['actions'][0]['effective_outcome']=='UNKNOWN'
        assert before['actions'][0]['attempt_fact']==after['actions'][0]['attempt_fact']==fact['result']['attempt_fact']=='MAY_HAVE_BEEN_ATTEMPTED'
        assert before['actions'][0]['intent_ref']==intentref and after['actions'][0]['result_fact']==factref
        assert canon(before['progress_ref']) in lookup and lookup[canon(before['progress_ref'])]['payload']['actions'][0]['receipt_ref'] is None
        recovered=json.loads(read(case+'reconcile-once.json'));assert recovered['attempt_count']==1 and recovered['pending_count']==0 and recovered['target_effects_during_reconcile']==0
        assert recovered['resolutions'][0]['result_ref']==headref and recovered['resolutions'][0]['classification']=='ABSENT' and not recovered['deadline_exceeded']
        execute=json.loads(read(prefix+'D2-after-execute-SQL.json'));initial=execute['runtime']['tables'];assert initial['actions'][0]['state']=='INTENT' and initial['actions'][0]['fact'] is None and initial['intents'][0]['state']=='PENDING'
        assert execute['runtime']['counts']['permits']==execute['target']['counts']['effects']==0
        marker=json.loads(read(case+'after-intent-commit.marker.json'));end=json.loads(read(prefix+'processes/D2-execute/completed.json'))
        assert marker['point']=='AFTER_INTENT_COMMIT' and marker['pid']==end['pid'] and end['exit_code']==90 and not end['alive'] and not end['timed_out']
        result.update(resolution_ref=headref,original_UNKNOWN_progress_ref=before['progress_ref'],attempt_fact_preserved=fact['result']['attempt_fact'],actual_complete_ABSENT_observation=readback['observation_id'],reconcile=recovered,real_exit_marker=marker)
    if label=='independent' and group in ('D1','D2'):
        duplicate=json.loads(read(case+'duplicate-result.json'));assert duplicate['business_outcome']=='REFUSED' and duplicate['code']=='REPLAY_FORBIDDEN' and duplicate['message']=='accepted plan is permanently reserved'
        before_dup=json.loads(read(case+'before-duplicate-query.json'));after_dup=json.loads(read(case+'after-duplicate-query.json'))
        assert before_dup['target']['counts']['effects']==after_dup['target']['counts']['effects']==tc['effects']
        for name in ('intents','permits'):assert before_dup['runtime']['counts'][name]==after_dup['runtime']['counts'][name]==rc[name]
        result['duplicate_result']=duplicate
    if label=='independent' and group=='D1':
        normal=json.loads(read(case+'normal-run-result.json'));assert normal['status']=='FINISHED' and normal['quality']['content_check_status']=='PENDING' and normal['quality']['submission_status']=='NOT_SUBMITTED'
        executed=json.loads(read(prefix+'D1-after-execute-SQL.json'))
        assert executed['runtime']['tables']['books'][0]['generation']==1 and book['generation']==2
        result['normal_return']='FINISHED';result['report_generation']=1;result['later_duplicate_claim_generation']=2
    result['resource_checks']=resources
    return result

root=Path(load(OUT/'independent-run.json')['run_root']).resolve()
def independent_read(path):
    p=Path(path);p=p if p.is_absolute() else WORK/p;p=p.resolve();assert p.is_relative_to(root);return p.read_bytes()
author_cases=[case_audit('author',g,author_read,EV+'validation/owner-r1-01/') for g in ('D1','standalone','borrow')]
independent_cases=[case_audit('independent',g,independent_read,str(root)+'/') for g in ('D1','standalone','borrow','D2')]
before_copies=[]
for group in ('D1','D2'):
    for role in ('runtime','target'):
        source=str(root/'cases'/group/('before-run-'+role+'.sqlite3'));record=copy_db('independent-'+group+'-before-'+role,independent_read,source)
        if role=='runtime':assert all(record['counts'][n]==0 for n in ('plans','actions','intents','permits'))
        else:assert record['counts']['effects']==0
        before_copies.append(record)

case=root/'cases/standalone';proof=load(case/'standalone-owner-proof.json');a,b=proof['before'],proof['after']
assert a['book']['phase']=='RELEASED' and b['book']['phase']=='RELEASED' and a['book']['owner'] is b['book']['owner'] is None
assert a['book']['generation']==1 and b['book']['generation']==2 and a['counts']['native_report_reads']==0 and b['counts']['native_report_reads']==1
for event in ('OWNER_CLAIM_RESERVED','OWNER_ACTIVE','OWNER_RELEASED'):assert b['events'].count(event)==a['events'].count(event)+1
assert b['target']['counts']['observations']==a['target']['counts']['observations']+1 and b['target']['counts']['effects']==a['target']['counts']['effects']==1
case=root/'cases/borrow';borrow=load(case/'borrowed-owner-proof.json');limit=load(case/'single-read-refusal-proof.json');a,b,c=borrow['before'],borrow['after'],limit['after_read_limit_refusal']
assert borrow['saved_before_read_limit_control'] and borrow['outer_keeper_alive'] and limit['outer_keeper_alive']
assert a['events']==b['events']==c['events'] and a['book']['generation']==b['book']['generation']==c['book']['generation']==1
for state in (a,b,c):assert state['book']['phase']=='ACTIVE' and state['book']['owner']==a['book']['owner']
assert b['counts']==c['counts'] and b['target']==c['target'] and b['bundle']==c['bundle']
assert b['report_artifact_counts']==c['report_artifact_counts']=={'POST':1,'Batch':1} and b['counts']['native_report_reads']==1
assert len(borrow['controls'])==4 and {r['control'] for r in borrow['controls']}=={'owner_only','generation_only','stale_generation','foreign_owner'}
for name in ('owner_only','generation_only','stale_generation','foreign_owner'):
    control=load(case/('control-'+name+'.json'));x,y=control['before'],control['after']
    assert control['record']['code']=='OWNER_GENERATION_STALE' and control['record']['type']=='RuntimeFailure'
    assert x['counts']==y['counts'] and x['events']==y['events'] and x['target']==y['target'] and x['bundle']==y['bundle']
    assert y['book']['phase']=='ACTIVE' and y['counts']['native_report_reads']==0
error=limit['read_limit_refusal'];assert error['type']=='RuntimeFailure' and error['code']=='STORAGE_TRANSACTION_FAILED' and error['message']=='UNIQUE constraint failed: native_report_reads.plan_id'
assert error['context_type']=='IntegrityError' and error['context_message']==error['message'] and 'sqlite3.IntegrityError' in error['traceback']
write(OUT/'case-boundaries-review.json',{'status':'FOUR_INDEPENDENT_GROUPS_FORMAL_BINDINGS_VERIFIED','author_cases':author_cases,'independent_cases':independent_cases,
 'independent_before_DB_copies':before_copies,'unique_final_or_before_DB_copies':18,'all_copy_sources_and_bodies_unchanged':True,'original_DB_connections':0,
 'author_borrow':'FAILED_PRESERVED','author_D2':'NOT_RUN','independent_D2':'REAL_EXIT90_COMPLETE_ABSENT_NO_REPLAY_VERIFIED','product_calls_by_auditor':0})
write(OUT/'ownership-boundaries-review.json',{'status':'STANDALONE_AND_BORROWED_LIFECYCLES_AND_SINGLE_READ_VERIFIED','standalone':proof,
 'borrow_legal_proof_before_limit':borrow,'single_read_refusal':limit,'exact_error':error,'extra_observations_reports_effects_after_refusal':0,
 'borrowed_generation_and_owner_retained_until_caller_cleanup':True,'formal_read_budget':1,'source_scope':'four authorized cases only; legacy static only',
 'product_calls_by_auditor':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print('{"status":"FOUR_INDEPENDENT_GROUPS_FORMAL_BINDINGS_VERIFIED","unique_DB_copies":18,"effects":[1,1,1,0],"auditor_product_calls":0}')
