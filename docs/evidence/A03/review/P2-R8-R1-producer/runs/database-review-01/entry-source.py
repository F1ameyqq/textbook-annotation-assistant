# -*- coding: utf-8 -*-
"""Two immutable SQLite copies plus frozen material bytes; no native API or failed-progress construction."""
from collections import Counter
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from evidence import OUT,EV,TARGET,INDEX,file,raw,document,sha,canon,ref,stored_path,write

sources=sorted(r['path'] for r in INDEX if r['commit']==TARGET and r['path'].startswith(EV+'validation/') and r['path'].endswith('.sqlite3'))
assert len(sources)==2
temp=Path(tempfile.mkdtemp(prefix='a03-r8-r1-review-immutable-')).resolve();records=[];snapshots={}
try:
    for i,source in enumerate(sources):
        original=raw(source);before=sha(original);copy=temp/('%02d.sqlite3'%i)
        with copy.open('xb') as f:f.write(original)
        db=sqlite3.connect(copy.as_uri()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row;queries=[]
        try:
            db.set_trace_callback(queries.append);db.execute('PRAGMA query_only=ON')
            assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
            app=db.execute('PRAGMA application_id').fetchone()[0];version=db.execute('PRAGMA user_version').fetchone()[0]
            tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            counts={name:db.execute('SELECT count(*) FROM "'+name.replace('"','""')+'"').fetchone()[0] for name in tables}
            selected=['registrations','plans','actions','intents','permits','resolutions','artifacts','native_creation_anchors','events'] if 'native_pre_runs' in tables else ['effects']
            values={name:[dict(r) for r in db.execute('SELECT * FROM '+name)] for name in selected}
            values['meta']={r[0]:r[1] for r in db.execute('SELECT * FROM meta')}
            if 'native_pre_runs' in tables:
                columns='id,registration,status,reads,pre_ref,run_sha,accepted_plan,input_sha,input_manifest'
                values['native_pre_runs']=[dict(r) for r in db.execute('SELECT '+columns+' FROM native_pre_runs')]
        finally:db.close()
        after=sha(copy.read_bytes());assert before==after==sha(raw(source))
        role='runtime' if '/runtime/' in source else 'target';snapshots[role]={'counts':counts,'values':values}
        records.append({'source':source,'source_sha256':before,'copy_path':str(copy),'copy_sha256_before':before,
          'copy_sha256_after':after,'source_sha256_after':sha(raw(source)),
          'mode':'mode=ro&immutable=1; query_only=ON','quick_check':'ok','application_id':app,'user_version':version,
          'counts':counts,'sql':queries,'selected_rows':values})
    runtime=snapshots['runtime'];target=snapshots['target'];v=runtime['values']
    assert all(runtime['counts'][t]==1 for t in ('registrations','plans','actions','intents','permits','resolutions','native_pre_runs','native_creation_anchors'))
    assert runtime['counts']['native_report_reads']==0 and target['counts']['effects']==1
    reg=v['registrations'][0];planrow=v['plans'][0];action=v['actions'][0];intent=v['intents'][0]
    permit=v['permits'][0];resolution=v['resolutions'][0];run=v['native_pre_runs'][0]
    bundle_path=stored_path(reg['bundle_path']);package_root=stored_path(reg['package_root']);bundle=document(bundle_path)
    artifacts=bundle['artifacts'];lookup={canon(ref(a)):a for a in artifacts}
    for artifact in artifacts:
        assert sha(canon({k:x for k,x in artifact.items() if k!='content_hash'}))==artifact['content_hash']
    planref=json.loads(planrow['ref']);intentref=json.loads(intent['ref']);headref=json.loads(resolution['ref'])
    plan=lookup[canon(planref)];intent_artifact=lookup[canon(intentref)];head=lookup[canon(headref)]
    assert len(plan['payload']['actions'])==1 and plan['payload']['actions'][0]['operation']=='CREATE_FRAMES'
    assert plan['payload']['actions'][0]['action_id']==action['id']==intent['action']
    assert sha(canon(planref))==planrow['id']==action['plan']==intent['plan']
    assert action['intent']==intent['id']==permit['intent']==resolution['intent']
    assert action['state']=='APPLIED' and intent['state']=='RESOLVED_APPLIED' and planrow['status']=='INTERRUPTED'
    assert permit['state']=='CONSUMED' and intent['receipt'] is None
    prepared=document(stored_path(intent['prepared']));assert ref(prepared['intent'])==intentref
    assert prepared['intent']==intent_artifact
    factref=json.loads(action['fact']);factpath=package_root+'/'+factref['path'];fact=document(factpath)
    assert sha(raw(factpath))==factref['sha256']
    assert fact['format_version']=='a03-action-fact-3' and fact['origin_phase']=='RECOVERY'
    assert fact['result']['outcome']=='APPLIED' and fact['result']['attempt_fact']=='MAY_HAVE_BEEN_ATTEMPTED'
    assert fact['plan_ref']==planref and fact['action_id']==action['id'] and fact['intent_ref']==intentref
    assert fact['result']['intent_ref']==intentref and fact['resolution_ref']==headref
    assert fact['action_digest']==action['digest']
    assert resolution['outcome']==head['payload']['resolution']=='RESOLVED_APPLIED'
    assert head['payload']['original_receipt_ref'] is None and head['payload']['intent_ref']==intentref
    effect=json.loads(target['values']['effects'][0]['body'])
    assert effect['plan_ref']==planref and effect['action_id']==action['id'] and effect['action_digest']==action['digest']
    assert effect['mutated'] and effect['origin']=='SYNTHETIC' and effect['execution_mode']=='SIMULATED'
    assert run['status']=='ADMITTED' and run['accepted_plan']==planrow['id'] and run['pre_ref'] is not None and run['run_sha'] is not None
    preref=json.loads(run['pre_ref']);pre=lookup[canon(preref)]
    assert pre['payload']['stage']=='PRE_APPLY' and type(pre['payload']['coverage']) is dict and pre['payload']['decision']=='PASS'
    runref=pre['payload']['synthetic_run_ref'];runpath=package_root+'/'+runref['path'];runresource=document(runpath)
    assert sha(raw(runpath))==runref['sha256']==run['run_sha']
    checks={r['check_id']:r['outcome'] for r in pre['payload']['checks']}
    assert checks==runresource['checks'] and set(checks.values())=={'PASS'} and len(checks)==5
    assert runresource['implementation_sha256']==sha(raw('src/annotation/quality/synthetic_precheck.py'))
    marker=document(EV+'validation/native-r1-01/cases/N1/before-dispatch.json')
    assert marker['pre_ref']==preref and marker['plan_ref']==planref and marker['run_id']==run['id'] and marker['registration_id']==reg['id']
    progress=[a for a in artifacts if a['kind']=='ExecutionProgress'];assert len(progress)==2
    assert {a['payload']['actions'][0]['effective_outcome'] for a in progress}=={'UNKNOWN','APPLIED'}
    for a in progress:
        item=a['payload']['actions'][0]
        assert item['attempt_fact']=='MAY_HAVE_BEEN_ATTEMPTED' and item['result_fact'] is None and item['receipt_ref'] is None
        assert item['action_id']==action['id'] and item['intent_ref']==intentref and a['payload']['plan_ref']==planref
    assert not [a for a in artifacts if a['kind'] in ('ExecutionReceipt','BatchReport') or a['kind']=='CheckReport' and a['payload']['stage']=='POST_APPLY']
    durable_refs={canon(json.loads(a['ref'])) for a in v['artifacts']}
    assert {canon(ref(a)) for a in artifacts}==durable_refs
    # Four compared values only: this is a static branch inference, never a new progress Artifact.
    inferred={'plan_ref':planref,'action_id':action['id'],'intent_ref':intentref,'attempt_fact':'ATTEMPTED'}
    actual={'plan_ref':fact['plan_ref'],'action_id':fact['action_id'],'intent_ref':fact['intent_ref'],'attempt_fact':fact['result']['attempt_fact']}
    different={k:inferred[k]!=actual[k] for k in actual}
    assert different=={'plan_ref':False,'action_id':False,'intent_ref':False,'attempt_fact':True}
    all_progress={};candidate_receipts={};candidate_files=[]
    for row in INDEX:
        path=row['path']
        if row['commit']!=TARGET or not path.startswith(EV+'validation/') or not path.endswith('.json'):continue
        if '/runtime/objects/' not in path and not path.startswith(package_root+'/bundle-'):continue
        value=document(path);items=value.get('artifacts',[]) if 'artifacts' in value else [value]
        for artifact in items:
            if artifact.get('kind')=='ExecutionProgress':all_progress[canon(ref(artifact))]=ref(artifact)
            if artifact.get('kind')=='ExecutionReceipt':
                candidate_receipts[canon(ref(artifact))]=ref(artifact)
                candidate_files.append({'path':path,'receipt_ref':ref(artifact),'current_bundle':path==bundle_path})
    assert set(all_progress)=={canon(ref(a)) for a in progress}
    assert len(candidate_receipts)==1 and not set(candidate_receipts)&durable_refs
    assert all(not r['current_bundle'] for r in candidate_files)
    anchor=v['native_creation_anchors'][0];anchor_path=stored_path(anchor['input_path'])
    assert sha(raw(anchor_path))==anchor['input_sha'];anchor_input=document(anchor_path)
    boundary={'status':'ACTUAL_ADMISSION_EFFECT_UNKNOWN_HEAD_AND_MISMATCH_CONFIRMED',
      'current_bundle':{'path':bundle_path,'sha256':sha(raw(bundle_path)),'artifact_kinds':dict(Counter(a['kind'] for a in artifacts))},
      'identity':{'plan_database_id':planrow['id'],'plan_ref':planref,'action_id':action['id'],'action_digest':action['digest'],
        'intent_database_id':intent['id'],'intent_ref':intentref,'resolution_head_ref':headref,'material_fact_ref':factref},
      'actual_PRE':{'ref':preref,'status':run['status'],'accepted_plan':run['accepted_plan'],'coverage_type':'dict',
        'decision':pre['payload']['decision'],'checks':checks,'run_resource':runref,'reads':run['reads']},
      'effect':effect,'effect_count':target['counts']['effects'],'permit_count':1,'permit_state':'CONSUMED',
      'current_intent_receipt':None,'head_original_receipt_ref':None,'terminal_resolution':'RESOLVED_APPLIED',
      'late_material_fact':fact,'persisted_progress':[{'ref':ref(a),'payload':a['payload']} for a in progress],
      'guard_comparison':{'saved_fact_values':actual,'inferred_from_APPLIED_row_and_frozen_branch':inferred,
        'inequality_terms':different,'inferred_progress_created_or_sealed':False,'failed_progress_persisted':False},
      'filesystem_candidate_receipts':candidate_files,'candidate_receipt_not_in_current_bundle_or_SQL_artifacts':True,
      'creation_anchor':{'path':anchor_path,'input_sha256':anchor['input_sha'],'artifacts':len(anchor_input['artifacts']),
        'manifest_entries':len(json.loads(anchor['manifest'])),'post_UNKNOWN_recompute':'NOT_RUN'},
      'POST_Batch':'NOT_REACHED','native_report_reads':0,'candidate_native_API_or_tests_run':0}
finally:
    assert temp.parent==Path(tempfile.gettempdir()).resolve() and temp.name.startswith('a03-r8-r1-review-immutable-') and not temp.is_symlink()
    shutil.rmtree(temp)
write(OUT/'database-review.json',{'status':'TWO_IMMUTABLE_DATABASE_COPIES_VERIFIED','copies':records,
 'temporary_root':str(temp),'removed':not temp.exists(),'runtime_originals_opened':False,'candidate_API_calls':0})
write(OUT/'boundary-and-binding-review.json',boundary)
print(json.dumps({'status':boundary['status'],'effects':boundary['effect_count'],'PRE':boundary['actual_PRE']['status'],
 'guard_terms':different,'persisted_progress':len(progress),'candidate_receipt_files':len(candidate_files),'temporary_root_removed':not temp.exists()}))
