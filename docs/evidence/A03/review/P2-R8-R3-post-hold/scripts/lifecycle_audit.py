# -*- coding: utf-8 -*-
"""Immutable formal N1 and two actual POST_HOLD admissions, no native API calls."""
import json
from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
import tempfile
from evidence import OUT,WORK,EV,TARGET,INDEX,load,sha,canon,ref,write,author_read,raw
from verify_case import verify_case

def inspect_post_hold(label,read,result_path):
    audit=load(OUT/(label+'-database-review.json'))
    runtime=next(r for r in audit['copies'] if r['role']=='runtime')['selected_rows']
    target=next(r for r in audit['copies'] if r['role']=='target')['selected_rows']
    reg=runtime['registrations'][0];book=runtime['books'][0];bundle=json.loads(read(reg['bundle_path']))
    lookup={canon(ref(a)):a for a in bundle['artifacts']};events=[json.loads(r['body']) for r in runtime['events']]
    byseq={e['sequence']:e for e in events};observations={r['observation_id']:json.loads(r['body']) for r in target['observations']}
    previous=None
    for e in sorted(events,key=lambda e:e['sequence']):
        assert sha(canon({k:v for k,v in e.items() if k!='event_hash'}))==e['event_hash']
        if previous:assert e['previous_hash']==previous['event_hash']
        previous=e
    assert (book['head_sequence'],book['head_hash'])==(previous['sequence'],previous['event_hash'])
    result=json.loads(read(result_path));runs=[r for r in runtime['native_pre_runs'] if json.loads(r['binding'])['context']['kind']=='POST_HOLD'];assert len(runs)==2
    def resource(r):
        body=read(reg['package_root'].replace('\\','/')+'/'+r['path']);assert sha(body)==r['sha256'];return json.loads(body)
    details=[]
    for row in sorted(runs,key=lambda r:r['created']):
        binding=json.loads(row['binding']);ctx=binding['context'];cap=json.loads(row['observation']);preref=json.loads(row['pre_ref']);pre=lookup[canon(preref)]
        assert row['status']=='ADMITTED' and row['reads']==1 and row['accepted_plan'] is None
        assert ctx['hold_id']==book['hold']==result['same_current_hold_preserved']
        assert ctx['hold_head']=={'sequence':row['head_sequence'],'hash':row['head_hash']}
        assert byseq[row['head_sequence']]['event_hash']==row['head_hash']
        event=resource(ctx['hold_ref']);assert event in events and event['payload']['hold_id']==book['hold']
        assert event['target_key']==json.loads(book['target_key']) and event['payload']['registration_id']==reg['id']
        assert event['payload']['source_ref']==json.loads(reg['source']) and event['payload']['scope_id']==reg['scope']
        assert event['payload']['target_session_id']==reg['session'] and event['payload']['target_store_id']==runtime['meta']['target_store_id']
        assert pre['payload']['verification_context']==ctx and pre['payload']['snapshot']==json.loads(row['snapshot']) and pre['payload']['decision']=='PASS'
        runref=pre['payload']['synthetic_run_ref'];run=resource(runref);assert runref['sha256']==row['run_sha']
        assert run['run_id']==row['id'] and run['context']==ctx and run['snapshot_ref']==json.loads(row['snapshot'])
        assert run['native_binding']=={k:binding[k] for k in ('registry_id','registration_id','owner_id','generation','target_store_id','target_session_id')}
        assert run['actual_observation']==cap['resource'] and run['observed_at']==cap['observed_at']
        assert cap['observation_id'] in observations and observations[cap['observation_id']]['read_sequence']==cap['read_sequence']
        assert run['input_raw_sha256']==row['input_sha'] and run['input_manifest']==json.loads(row['input_manifest'])
        for r in run['input_manifest']:
            assert sha(read(reg['package_root'].replace('\\','/')+'/'+r['path']))==r['sha256']
        assert run['checks']=={r['check_id']:r['outcome'] for r in pre['payload']['checks']} and set(run['checks'].values())=={'PASS'}
        original=next(r for r in result['POST_HOLD_runs'] if r['run_id']==row['id'])
        assert original['pre_ref']==preref and original['hold_context']==ctx and original['snapshot_ref']==json.loads(row['snapshot'])
        assert original['generation']==binding['generation'] and original['owner_id']==binding['owner_id'] and original['observation_id']==cap['observation_id'] and original['read_sequence']==cap['read_sequence']
        details.append({'run_id':row['id'],'pre_ref':preref,'status':row['status'],'reads':row['reads'],'created':row['created'],
          'binding':binding,'observation_id':cap['observation_id'],'read_sequence':cap['read_sequence'],'observation_resource':cap['resource'],
          'snapshot_ref':json.loads(row['snapshot']),'run_resource':runref,'manifest_entries':len(run['input_manifest'])})
    a,b=details;assert a['binding']['context']['hold_ref']==b['binding']['context']['hold_ref']
    assert a['binding']['generation']<b['binding']['generation'] and a['binding']['context']['hold_head']['sequence']<b['binding']['context']['hold_head']['sequence']
    assert a['observation_id']!=b['observation_id'] and a['read_sequence']<b['read_sequence']
    codes={r['control']:r['actual_code'] for r in result['refusals']}
    assert codes=={'old_INITIAL_after_registry_reopen':'NATIVE_ADMITTED_RUN_REQUIRED','INITIAL_while_held':'TARGET_DRIFT_HOLD',
      'ordinary_plan_accept_while_held':'TARGET_DRIFT_HOLD','old_hold_run_after_normal_owner_head_progress':'OWNER_GENERATION_STALE',
      'ordinary_write_still_blocked_after_POST_HOLD_admission':'TARGET_DRIFT_HOLD','expired_current_hold_proof':'NATIVE_PRE_DEADLINE_EXCEEDED'}
    assert result['hold_clear_calls']==0 and result['permit_count']==result['target_effect_count']==1 and result['real_expiry_wait'] and not result['clock_or_SQL_fabrication']
    value={'status':'TWO_POST_HOLD_ADMISSIONS_AND_GUARDS_VERIFIED','label':label,'admissions':details,'exact_refusals':codes,
      'final_hold':book['hold'],'final_owner':book['owner'],'generation':book['generation'],'hold_cleared':False,
      'current_same_hold_two_heads_only':True,'different_hold_id_or_qualified_clearance_tested':False,'effect_count':1,
      'expiry':{'product_window_seconds':60,'recorded_real_wait':True,'clock_or_SQL_modified':False},'native_API_calls_by_auditor':0}
    if label=='independent':
        complete=load(OUT/'runs/independent-n2-01/completion.json');assert complete['elapsed_seconds']>=60
        assert datetime.fromisoformat(complete['finished_at']).timestamp()>=details[1]['created']+60
        value['expiry']['parent_elapsed_seconds']=complete['elapsed_seconds'];value['expiry']['parent_watchdog_seconds']=120
    write(OUT/(label+'-post-hold-review.json'),value)
    return value

def controls(label,read,sources):
    temp=Path(tempfile.mkdtemp(prefix='a03-r3-control-immutable-')).resolve();results=[]
    try:
        for n,source in enumerate(sources):
            body=read(source);before=sha(body);copy=temp/(str(n)+'.sqlite3');copy.write_bytes(body)
            db=sqlite3.connect(copy.as_uri()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row;queries=[]
            try:
                db.set_trace_callback(queries.append);db.execute('PRAGMA query_only=ON');assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
                tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
                counts={t:db.execute('SELECT count(*) FROM "'+t+'"').fetchone()[0] for t in tables}
                meta={r[0]:r[1] for r in db.execute('SELECT * FROM meta')}
                pending=db.execute("SELECT count(*) FROM intents WHERE state='PENDING'").fetchone()[0] if 'intents' in tables else None
                runs=[dict(r) for r in db.execute('SELECT id,binding,status,reads,pre_ref FROM native_pre_runs')] if 'native_pre_runs' in tables else []
                app=db.execute('PRAGMA application_id').fetchone()[0];version=db.execute('PRAGMA user_version').fetchone()[0]
            finally:db.close()
            assert sha(copy.read_bytes())==sha(read(source))==before
            if 'effects' in counts:assert counts['effects']==0
            else:
                assert counts['permits']==0
                if '/local-pending/' in str(source):assert pending==1
                if '/N4-' in str(source):assert counts['plans']==counts['intents']==0 and counts['native_pre_runs']==1 and runs[0]['status']=='ADMITTED'
                if '/N7/' in str(source):assert counts['plans']==counts['native_pre_runs']==0 and meta['initialization']=='COMPLETE'
            results.append({'source':str(source),'sha256_before':before,'sha256_after':sha(read(source)),'counts':counts,'pending':pending,
              'runs':runs,'meta':meta,'application_id':app,'user_version':version,'sql':queries})
    finally:
        assert temp.parent==Path(tempfile.gettempdir()).resolve() and temp.name.startswith('a03-r3-control-immutable-') and not temp.is_symlink();shutil.rmtree(temp)
    write(OUT/(label+'-control-database-review.json'),{'status':'CONTROL_DB_COPIES_IMMUTABLY_VERIFIED','label':label,'records':results,'temporary_removed':not temp.exists()})
    return results

def main(label):
    if label=='author':
        read=author_read;prefix=EV+'validation/native-r3-01/';case=prefix+'cases/N1/'
        sources=[r['path'] for r in INDEX if r['commit']==TARGET and r['path'].startswith(prefix) and r['path'].endswith('.sqlite3') and '/cases/N1/' not in r['path']]
    else:
        root=Path(load(OUT/'independent-run.json')['run_root']).resolve();prefix=str(root)+'/' ;case=str(root/'cases/N1')+'/'
        def read(path):
            p=Path(path);p=p if p.is_absolute() else WORK/p;p=p.resolve();assert p.is_relative_to(root);return p.read_bytes()
        sources=[str(p) for p in root.rglob('*.sqlite3') if p.parent.parent.name!='N1']
    positive=verify_case(label,read,case+'runtime/runtime.sqlite3',case+'target/target.sqlite3',True)
    post=inspect_post_hold(label,read,prefix+'N2-result.json');negative=controls(label,read,sources)
    print(json.dumps({'label':label,'N1':positive['status'],'POST_HOLD':len(post['admissions']),'effect_count':1,'control_databases':len(negative),'native_API_calls_by_auditor':0}))

if __name__=='__main__':
    import sys
    main(sys.argv[1])
