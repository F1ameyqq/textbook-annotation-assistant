# -*- coding: utf-8 -*-
"""Independent actual-result/immutable-SQL audit; no candidate imports or calls."""
import copy
import json
from pathlib import Path
import sqlite3
import sys
from evidence import OUT,WORK,EV,load,raw,author_read,canon,ref,sha,write

def audit(label):
    if label=='author':
        read=author_read;prefix=EV+'validation/r4-native-01/'
    else:
        root=Path(load(OUT/'independent-run.json')['run_root']).resolve();prefix=str(root)+'/'
        def read(path):
            p=Path(path);p=p if p.is_absolute() else WORK/p;p=p.resolve();assert p.is_relative_to(root);return p.read_bytes()
    def doc(path):return json.loads(read(path))
    boundary=load(OUT/(label+'-boundary-review.json'));dbreview=load(OUT/(label+'-database-review.json'))
    runtime=next(r for r in dbreview['copies'] if r['role']=='runtime');target=next(r for r in dbreview['copies'] if r['role']=='target')
    rows=runtime['selected_rows'];reg=rows['registrations'][0];anchor=rows['native_creation_anchors'][0]
    current=doc(reg['bundle_path']);saved_history=read(prefix+'N6/full-current-history.json')
    assert saved_history==canon(current) and len(current['artifacts'])==20
    lookup={canon(ref(a)):a for a in current['artifacts']};plan=lookup[canon(boundary['plan_ref'])]
    assert all(canon(ref(a)) in {canon(json.loads(r['ref'])) for r in rows['artifacts']} for a in current['artifacts'])
    unknown=[a for a in current['artifacts'] if a['kind']=='ExecutionProgress' and any(r['effective_outcome']=='UNKNOWN' for r in a['payload']['actions'])]
    assert len(unknown)==1 and all(r['receipt_ref'] is None for r in unknown[0]['payload']['actions'])
    for name in ('formal_receipt_ref','terminal_head_ref','POST_ref','Batch_ref'):assert canon(boundary[name]) in lookup
    recorded=doc(prefix+'N6/creation-anchor-SQL.json')
    assert recorded['anchor']==anchor and recorded['artifacts']==rows['artifacts'] and recorded['intents']==rows['intents']
    anchor_raw=read(anchor['input_path']);creation=json.loads(anchor_raw)
    assert sha(anchor_raw)==anchor['input_sha'] and anchor_raw==canon(creation)==read(prefix+'N6/creation-input-canonical.json')
    assert not any(a['kind'] in ('ApplyPlan','ExecutionReceipt','ExecutionProgress','ReconciliationResult','BatchReport') for a in creation['artifacts'])
    captured=doc(prefix+'N6/actual-recompute-returns.json');assert captured['generated_plans']==[plan]
    original=read(prefix+'N6/original-plan-canonical.json');recomputed=read(prefix+'N6/recomputed-plan-canonical.json')
    assert original==recomputed==canon(plan) and ref(json.loads(original))==boundary['plan_ref']
    assert json.loads(original)['payload']['actions']==plan['payload']['actions']
    manifest=json.loads(anchor['manifest']);assert captured['resource_manifests']==[manifest] and len(manifest)==6
    package=reg['package_root'].replace('\\','/');found={};resource_checks=[]
    def entity(item):
        b=read(package+'/'+item['path']);assert sha(b)==item['sha256'];return b
    def walk(value):
        if isinstance(value,dict):
            if {'path','sha256','media_type'}<=set(value):
                token=tuple(value[k] for k in ('path','sha256','media_type'))
                if token in found:return
                item={k:value[k] for k in ('path','sha256','media_type','origin')};found[token]=item;b=entity(item)
                if item['media_type']=='application/json':walk(json.loads(b))
            else:
                for v in value.values():walk(v)
        elif isinstance(value,list):
            for v in value:walk(v)
    walk(creation)
    assert {canon(r) for r in found.values()}=={canon(r) for r in manifest}
    recorded_resources=doc(prefix+'N6/consumed-resource-readback.json');assert len(recorded_resources)==6
    for item in manifest:
        b=entity(item);r=next(r for r in recorded_resources if r['resource']==item)
        assert r['actual_sha256']==sha(b) and r['bytes']==len(b)
        resource_checks.append({'resource':item,'actual_sha256':sha(b),'bytes':len(b),'recursive_closure_member':True})
    missing=doc(prefix+'N6/missing-dependency-input.json');consumer=doc(prefix+'N6/missing-dependency-consumer.json')
    pre=next(a for a in creation['artifacts'] if ref(a)==plan['payload']['precheck']);check=pre['payload']['checks'][0]
    eid=check['evidence_refs'][0];evidence=next(r for r in creation['evidence'] if r['evidence_id']==eid)
    assert consumer['artifact_ref']==ref(pre) and consumer['check_id']==check['check_id']=='source_integrity'
    assert consumer['evidence_id']==eid and consumer['record']==evidence
    expected=copy.deepcopy(creation);expected['evidence']=[r for r in expected['evidence'] if r['evidence_id']!=eid]
    assert missing==expected and len(creation['evidence'])==len(missing['evidence'])+1
    refusal=doc(prefix+'N6/missing-dependency-refusal.json')
    codes=[i.get('code') for i in (refusal['issues'] or [])]+[refusal['code']]
    assert refusal['type']=='StaticCodecError' and 'EVIDENCE_ID_MISSING' in codes
    assert eid in refusal['message'] and 'checks/0/evidence_refs['+eid+']' in refusal['message']
    assert 'context' in refusal['traceback'] and 'closure' in refusal['traceback']
    result=doc(prefix+'N6-result.json');assert result['same_plan_four_tuple']==ref(plan) and result['full_history_artifact_count']==20
    assert result['full_UNKNOWN_count']==1 and result['all_formal_history_retained']
    assert result['original_and_recomputed_plan_canonical_sha256']==sha(original) and result['creation_anchor_canonical_sha256']==sha(anchor_raw)
    assert result['missing_dependency']==consumer and result['actual_refusal']==refusal and result['database_before']==result['database_after']
    assert result['permit_and_effect_added']==0 and not result['clock_SQL_filter_reseal_downgrade']
    for role,record in [('runtime',runtime),('target',target)]:
        state=result['database_before'][role];b=read(record['source'])
        assert sha(b)==state['sha256']==record['source_sha256']
    assert result['database_before']['runtime']['counts']['permits']==result['database_before']['target']['counts']['effects']==1
    assert read(anchor['input_path'])==anchor_raw
    n6_value={'status':'COMPLETE_UNKNOWN_HISTORY_RECOMPUTE_AND_NAMED_PRE_DEPENDENCY_VERIFIED','label':label,
      'history_artifacts':20,'UNKNOWN_refs':[ref(a) for a in unknown],'formal_later_refs':{k:boundary[k] for k in ('formal_receipt_ref','terminal_head_ref','POST_ref','Batch_ref')},
      'anchor_SQL_row':anchor,'anchor_raw_canonical_sha256':sha(anchor_raw),'creation_input_artifacts':len(creation['artifacts']),
      'original_and_actual_recomputed_plan_ref':ref(plan),'full_plan_canonical_sha256':sha(original),'all_actions_equal':True,
      'actual_create_plan_returns':1,'actual_resource_manifest_returns':1,'resource_closure':resource_checks,
      'consumer':consumer,'actual_refusal':refusal,'removed_exactly_one_named_EvidenceRecord':True,'original_anchor_and_resources_unchanged':True,
      'database_before_after':result['database_before'],'permit_effect_increase':0,'API_or_planner_calls_by_auditor':0,
      'scope':'one positive historical recompute and one closure rejection; not all resource damage controls'}
    n7=doc(prefix+'N7-result.json');controlled=doc(prefix+'N7/original-controlled-interruption.json');refusal=doc(prefix+'N7/normal-open-refusal.json')
    assert n7['hook_calls']==['before_completion'] and n7['same_process_controlled_exception'] and not n7['real_process_crash_claim']
    assert not n7['anchor_exists'] and n7['formal_completion']=='ABSENT' and n7['database_before_open']==n7['database_after_open']
    assert n7['target_database']==n7['target_effects']=='NOT_CREATED' and not n7['all_target_interruption_points_claim']
    assert n7['old_failed_target_entry_or_variant_calls']==0 and n7['migration']=='NOT_IMPLEMENTED_BLOCKED'
    assert controlled['type']=='ControlledStop' and 'controlled same-process interruption' in controlled['message'] and 'before_completion()' in controlled['traceback']
    assert n7['normal_open_refusal']==refusal and refusal['code']=='STATE_DIRECTORY_IDENTITY_MISMATCH' and 'FileNotFoundError' in refusal['traceback']
    assert 'anchor.json' in refusal['message']
    source=prefix+'cases/N7-before-completion/runtime/runtime.sqlite3';b=read(source);digest=sha(b)
    assert digest==n7['database_before_open']['sha256']
    clones=OUT/'immutable-N7-copies';clones.mkdir(exist_ok=True);clone=clones/(label+'.sqlite3')
    with clone.open('xb') as f:f.write(b)
    db=sqlite3.connect(clone.resolve().as_uri()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row;queries=[]
    try:
        db.set_trace_callback(queries.append);db.execute('PRAGMA query_only=ON');assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        counts={name:db.execute('SELECT count(*) FROM "'+name+'"').fetchone()[0] for name in names}
        meta=[dict(r) for r in db.execute('SELECT * FROM meta')]
        assert not meta and all(counts[n]==0 for n in ('plans','intents','permits','native_creation_anchors'))
        app=db.execute('PRAGMA application_id').fetchone()[0];version=db.execute('PRAGMA user_version').fetchone()[0]
    finally:db.close()
    assert sha(clone.read_bytes())==digest==sha(read(source));clone.unlink();clones.rmdir()
    if label=='independent':
        case=Path(prefix)/'cases/N7-before-completion';assert not (case/'anchor.json').exists() and not (case/'target').exists()
        actual_files={p.relative_to(WORK).as_posix() for p in case.rglob('*') if p.is_file()}
        assert actual_files=={r['path'] for r in n7['retained_files']}
    for r in n7['retained_files']:
        entity_raw=read(r['path']);assert len(entity_raw)==r['bytes'] and sha(entity_raw)==r['sha256']
    n7_value={'status':'ONE_RUNTIME_BEFORE_COMPLETION_INTERRUPT_FAIL_CLOSED_VERIFIED','label':label,
      'existing_hook_calls':1,'controlled_original_exception':controlled,'normal_open_refusal':refusal,'anchor':'ABSENT','formal_completion':'ABSENT',
      'runtime_source':source,'source_sha256_before_after':digest,'immutable_copy_sha256_before_after':digest,'copy_removed':True,
      'application_id':app,'user_version':version,'counts':counts,'meta':meta,'queries':queries,
      'target_database':'NOT_CREATED','target_effects':'NOT_CREATED','normal_open_calls':1,'initialization_recovery_retry':0,
      'scope':'same-process controlled exception at runtime hook only; not real crash or target initialization matrix',
      'original_R3_N7_FAILED_preserved':True,'old_target_entry_or_variant_calls':0,'API_calls_by_auditor':0}
    write(OUT/(label+'-N6-review.json'),n6_value)
    write(OUT/(label+'-N7-initialization-review.json'),n7_value)
    print(json.dumps({'label':label,'N6':'VERIFIED','N7_runtime_initialization':'VERIFIED','native_API_calls_by_auditor':0}))
if __name__=='__main__':audit(sys.argv[1])
