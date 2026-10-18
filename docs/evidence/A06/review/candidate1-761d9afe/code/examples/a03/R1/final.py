"""The one final bounded R1 package. No post-freeze retry or product edits."""
import argparse
import copy
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback

HERE=Path(__file__).resolve().parent
PROJECT=Path(os.environ.get('A03_R1_PROJECT',str(HERE.parents[2]))).resolve()
EVIDENCE=PROJECT/'docs/evidence/A03/R1/final-correction'
OLD=PROJECT/'docs/evidence/A03/R1/execution'
PRODUCT='6097a06de937fee8876feccedf46920510850b83'


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


d=module(HERE/'deltas.py','final_delta')
m=module(HERE.parent/'T3-closure/run.py','final_m_driver')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(store,rid,out,stage):return d.snapshot(store,rid,out,stage)


def claim(store,rid,observer):
    from annotation.runtime.recovery.lease import LeaseKeeper
    key=store.target_key(rid);owner=store.claim(key,observer=observer)
    return owner,LeaseKeeper(store,key,owner.owner_id,owner.generation).start()


def release(store,rid,owner,keeper):
    if keeper is not None:keeper.stop()
    if owner is not None and store.status(rid)['owner_id']==owner.owner_id:
        store.release(store.target_key(rid),owner_id=owner.owner_id,generation=owner.generation)


def g1(store,rid,observer,owner,p,config,out):
    from annotation.contracts import artifact_ref,policy_ref
    from annotation.contracts.a03_native import seal_native_artifact
    from annotation.quality.targetcheck import append_artifacts,check_target
    c=module(HERE/'controls.py','final_value_controls')
    root=Path(store.registration(rid)['package_root'])
    b=store._validate(store.bundle(rid),asset_root=root)
    data=b.model_dump();rows=[]
    def keep(key,call):
        result=d.reject(call);rows.append(dict(key=key,result=result))
        d.write(out/'G1.json',rows)
    kwargs=dict(current_snapshot_ref=p['payload']['snapshot'],asset_root=root,bridge_context=b.bridge_context)
    bad=dict(artifact_ref(p),content_hash='0'*64)
    keep('plan-reference',lambda:observer.prepare_action(b,bad,p['payload']['actions'][0]['action_id'],config,**kwargs))
    keep('action-identity',lambda:observer.prepare_action(b,artifact_ref(p),'missing-final-action',config,**kwargs))
    keep('missing-registration',lambda:store.registration('missing-final-registration'))
    mutations=[('question',lambda a:a['payload']['actions'][0]['target'].update(question_id='missing-question')),
        ('run',lambda a:a.update(run_id='unbound-final-run'))]
    for field in ('graph','snapshot','policy'):
        mutations.append((field+'-revision',lambda a,f=field:a['payload'][f].update(revision=a['payload'][f]['revision']+1)))
    for field in ('precheck','targetcheck','snapshot','policy'):
        mutations.append(('missing-'+field,lambda a,f=field:a['payload'].update({f:None})))
    mutations.append(('missing-capability',lambda a:a['payload'].update(required_capabilities=[])))
    for key,change in mutations:
        candidate=copy.deepcopy(data);a=next(a for a in candidate['artifacts']if a['kind']=='ApplyPlan')
        change(a);c.seal_all(candidate)
        changed=next(a for a in candidate['artifacts']if a['kind']=='ApplyPlan')
        keep(key,lambda v=candidate,a=changed:store.record_native_plan(rid,v,artifact_ref(a),config,
            owner_id=owner.owner_id,generation=owner.generation))
    keep('authorization',lambda:observer.prepare_action(b,artifact_ref(p),p['payload']['actions'][0]['action_id'],
        replace(config,allowed_operations=()),**kwargs))
    snapshot=copy.deepcopy(next(a for a in data['artifacts']if artifact_ref(a)==p['payload']['snapshot']))
    snapshot['artifact_id']='final-negative-capability-snapshot'
    for cap in snapshot['payload']['capabilities']:
        if cap['name']=='frame_readback':cap['status']='UNKNOWN'
    snapshot=seal_native_artifact(snapshot,bridge_context=b.bridge_context)
    values=append_artifacts(b,snapshot,bridge_context=b.bridge_context)
    report=check_target(values,p['payload']['graph'],p['payload']['snapshot'],artifact_ref(snapshot),p['payload']['policy'],
        config,artifact_id='final-negative-capability-target',created_at=__import__('annotation.runtime.storage.common',fromlist=['now']).now(),
        bridge_context=values.bridge_context).artifacts[-1]
    assert report.payload.decision!='PASS'
    rows.append(dict(key='capability-version',layer='QUALITY_VALUE',report=report.model_dump()))
    assert len(rows)==15
    d.write(out/'G1.json',rows)


def l2(out):
    from annotation.contracts import load_bundle,artifact_ref
    from annotation.runtime.recovery import run_plan
    fixtures=Path(os.environ['A03_R1_RAW_VIEW'])/'tests/fixtures/a03/R1/final/B-representations'
    single=load_bundle(fixtures/'single.json');mixed=load_bundle(fixtures/'mixed.json')
    left=[a.model_dump()for a in single.artifacts if a.book_id=='book-M-single']
    right=[a.model_dump()for a in mixed.artifacts if a.book_id=='book-M-single']
    assert left==right and any(a.kind=='ExecutionReceipt'and a.book_id!='book-M-single'for a in mixed.artifacts)
    d.write(out/'representations.json',dict(B_consumers_identical=True,single_B_refs=[artifact_ref(a)for a in single.artifacts],
        mixed_B_refs=[artifact_ref(a)for a in mixed.artifacts if a.book_id=='book-M-single'],
        public_C01_read='PASS',mixed_native_execution='NOT_CLAIMED',legacy_generation=0))
    case=OLD/'candidate-1/business/cases/M2-sufficient'
    for r in json.loads((EVIDENCE/'preparation/checks.json').read_bytes())['continuation']:
        assert sha(r['path'])==r['sha256'],'continuation changed since preflight'
    store=d.open_state(case);before=store.status('registration-M');assert before['pending_count']==2
    target_A=case/'target/target.sqlite3';target_before=sha(target_A)
    observer,config=d.setup(store,out,'registration-B')
    owner=keeper=None
    try:
        owner,keeper=claim(store,'registration-B',observer)
        p,config=d.plan(store,'registration-B',observer,owner,'R1-final-B')
        d.write(out/'plan.json',p)
        g1(store,'registration-B',observer,owner,p,config,out)
        keeper.stop();keeper=None
        result=run_plan(store,'registration-B',owner_id=owner.owner_id,generation=owner.generation,config=vars(config))
        assert result['status']=='FINISHED'and result['pending_count']==0
    finally:release(store,'registration-B',owner,keeper)
    after=store.status('registration-M');assert after['pending']==before['pending']and sha(target_A)==target_before
    capture(store,'registration-B',out,'after-release')
    d.write(out/'result.json',dict(B=result,A_before=before,A_after=after,A_target_sha256=target_before,
        B_status=store.status('registration-B'),native_targets=1,dispatch=1,legacy_generation=0))


def l3(out,phase):
    from annotation.runtime.storage.native import init_native_state
    from annotation.runtime.recovery import open_observer,reconcile
    first=EVIDENCE/'run/cases/L3-execute';rid='registration-L3'
    if phase=='L3-execute':
        store=init_native_state(out/'anchor.json',out/'runtime',expected_ledger_id='ledger-final-L3',expected_target_store_id='store-final-L3')
        observer,_=d.setup(store,out,rid)
    else:store=d.open_state(first);observer=open_observer(store,rid)
    if phase=='L3-reconcile':
        result=reconcile(store,rid,call_id='final-L3-ABSENT',max_attempts=1)
        assert store.status(rid)['pending_count']==0 and result['resolutions'][0]['classification']=='ABSENT'
        capture(store,rid,out,'after-release')
        d.write(out/'result.json',dict(reconcile=result,status=store.status(rid),bundle=store.bundle(rid)))
        return
    owner=keeper=None
    try:
        owner,keeper=claim(store,rid,observer)
        p,config=d.plan(store,rid,observer,owner,phase)
        projection=d.unknown(store,rid,observer,owner,p,config,absent=phase=='L3-execute')
        if phase=='L3-second':
            original=json.loads((first.parent/'L3-reconcile/result.json').read_bytes())['bundle']
            resolution=next(a for a in original['artifacts']if a['kind']=='ReconciliationResult')
            old=d.reject(lambda:store.commit_reconciliation(resolution,owner_id=owner.owner_id,generation=owner.generation))
            assert old.get('code')=='OBSERVATION_NOT_FRESH'
            stopped=d.reject(lambda:store.begin_native_pre(rid,owner_id=owner.owner_id,generation=owner.generation,observer=observer))
            assert stopped.get('code')=='BOOK_WRITE_PAUSED'
            d.write(out/'old-proof-refusals.json',dict(old_resolution=old,new_INITIAL=stopped))
    finally:release(store,rid,owner,keeper)
    assert store.status(rid)['pending_count']==1
    capture(store,rid,out,'after-release')
    d.write(out/'result.json',dict(plan=p,projection=projection,status=store.status(rid),bundle=store.bundle(rid),
        native_targets=int(phase=='L3-execute'),dispatch=1))


def g6(out,phase):
    from annotation.runtime.recovery import reconcile
    store=d.open_state(EVIDENCE/'run/cases/L3-execute');rid='registration-L3'
    result=reconcile(store,rid,call_id='final-G6-fixed-call',read_fault='timeout',max_attempts=3)
    if phase=='G6-first':assert 0<result['attempt_count']<=3
    else:assert result['attempt_count']==0
    assert store.status(rid)['pending_count']==1
    capture(store,rid,out,'after-release')
    d.write(out/'result.json',dict(reconcile=result,export=store.export(rid),dispatch=0))


def l4(out):
    from annotation.contracts import artifact_ref
    from annotation.runtime.storage.native import NativeRegistry,NativeRuntimeStore
    from annotation.contracts.a03_native import NativeSchemas,VERSION
    from annotation.contracts import recovery
    result=json.loads((EVIDENCE/'run/cases/L3-second/result.json').read_bytes())
    value=result['bundle'];root=Path(json.loads((EVIDENCE/'run/cases/L3-execute/anchor.json').read_bytes())['state_dir'])
    reg=json.loads((EVIDENCE/'run/cases/L3-second/captures/after-release/SQL.json').read_bytes())['runtime']['tables']['registrations'][0]
    assets=Path(reg['package_root']);rows=[]
    store=NativeRuntimeStore.__new__(NativeRuntimeStore);store.native_registry=NativeRegistry(store)
    c=module(HERE/'controls.py','final_l4_seal')
    original=next(a for a in value['artifacts']if a['kind']=='ReconciliationResult')
    branch=copy.deepcopy(value);sibling=copy.deepcopy(original)
    sibling['artifact_id']='final-negative-fork';sibling['payload']['observation_id']='final-negative-distinct-read'
    sibling['payload']['recovery_call_id']='final-negative-other-call';branch['artifacts'].append(sibling);c.seal_all(branch)
    rows.append(dict(key='fork',layer='FULL_NATIVE',result=d.reject(lambda:store._validate(branch,asset_root=assets))))
    cycle=copy.deepcopy(value);a=next(a for a in cycle['artifacts']if a['kind']=='ReconciliationResult')
    a['payload']['previous_resolution_ref']=artifact_ref(a);c.seal_all(cycle)
    rows.append(dict(key='cycle',layer='FULL_NATIVE_EXACT_REFERENCE',result=d.reject(lambda:store._validate(cycle,asset_root=assets))))
    wrong=copy.deepcopy(value);a=next(a for a in wrong['artifacts']if a['kind']=='ReconciliationResult')
    newer=[a for a in wrong['artifacts']if a['kind']=='ExecutionReceipt'][-1]
    a['payload']['original_receipt_ref']=artifact_ref(newer);c.seal_all(wrong)
    rows.append(dict(key='wrong-original-receipt-full',layer='FULL_NATIVE',result=d.reject(lambda:store._validate(wrong,asset_root=assets))))
    ctx=recovery._Closure(wrong,assets,schema_version=VERSION,schemas=NativeSchemas());ctx.native=True
    rows.append(dict(key='wrong-original-receipt-semantic',layer='VALUE_RESOLUTION_GUARD',result=d.reject(lambda:recovery._resolutions(ctx))))
    assert len(rows)<=6;d.write(out/'result.json',dict(controls=rows,dispatch=0,new_targets=0))


def f_read(out):
    from types import SimpleNamespace
    state=OLD/'candidate-1/business/cases/M2-sufficient'
    original=[sha(state/'runtime/runtime.sqlite3'),sha(state/'target/target.sqlite3')]
    for operation in ('query','export'):
        m.query_export(SimpleNamespace(state=state,output=out/operation,operation=operation))
    after=[sha(state/'runtime/runtime.sqlite3'),sha(state/'target/target.sqlite3')]
    assert original==after
    d.write(out/'result.json',dict(before=original,after=after,dispatch=0,claim=0,reconcile=0,publisher=0,
        inherited_F=dict(normal='accepted M1',new_plan='accepted M3-new-plan',unknown='accepted L1')))


def worker(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    d.write(out/'worker-started.json',dict(pid=os.getpid(),argv=sys.argv,phase=args.phase,product=PRODUCT))
    start=(time.monotonic(),time.process_time())
    try:
        if args.phase=='noop':d.write(out/'result.json',dict(stdlib_only=True,DB=0,target=0,dispatch=0));return
        if args.phase=='L2':l2(out)
        elif args.phase.startswith('L3-'):l3(out,args.phase)
        elif args.phase.startswith('G6-'):g6(out,args.phase)
        elif args.phase=='L4':l4(out)
        elif args.phase=='F':f_read(out)
        else:module(HERE/'final_controls.py','final_controls').run(args.phase,out)
    except BaseException as error:
        d.write(out/'failure.json',dict(error=repr(error),traceback=traceback.format_exc(),no_retry=True));raise
    finally:
        d.write(out/'worker-ended.json',dict(pid=os.getpid(),wall_seconds=time.monotonic()-start[0],
            cpu_seconds=time.process_time()-start[1],imports=d.imports(),threads=[t.name for t in threading.enumerate()]))


def batch(args):
    prep=module(HERE/'final_prepare.py','final_prep')
    run=EVIDENCE/'run';run.mkdir(exist_ok=False)
    frozen=EVIDENCE/'frozen';frozen.mkdir(exist_ok=False)
    view=m.raw_view(args.candidate,frozen)
    extra=prep.export(args.candidate,view,['tests/fixtures/a03/R1/final','examples/a03/P2-R12-R1-unknown-projection/legacy-recovery'])
    d.write(frozen/'extra-identities.json',extra)
    checks=json.loads((EVIDENCE/'preparation/checks.json').read_bytes())
    for row in checks['inputs']:assert sha(view/row['path'])==row['sha256']
    env=dict(os.environ,PYTHONPATH=str(view/'src')+os.pathsep+str(view/'examples/a03/T1-capture'),
        A03_R1_PROJECT=str(PROJECT),A03_R1_RAW_VIEW=str(view),PYTHONDONTWRITEBYTECODE='1')
    phases=['L2','L3-execute','L3-reconcile','L3-second','G6-first','G6-reopen','L4','G2-G3','G5','F']
    dependencies={'L3-reconcile':'L3-execute','L3-second':'L3-reconcile','G6-first':'L3-second','G6-reopen':'G6-first','L4':'L3-second'}
    matrix=[];failed_business=False
    d.write(run/'frozen-invocation.json',dict(candidate=args.candidate,product=PRODUCT,phases=phases,dependencies=dependencies,
        child_seconds=180,parent_seconds=240,new_targets_upper=2,dispatch_upper=3,legacy_generation=0,
        G1_delta_upper=15,G2_delta_upper=7,G3_delta_upper=4,G5_delta_upper=2,L4_gates_upper=4,no_retry=True))
    try:
        for phase in phases:
            prior={r['phase']:r for r in matrix}
            business=phase.startswith(('L2','L3','G6'))
            dependency=dependencies.get(phase)
            if (business and failed_business)or(dependency and prior[dependency]['status']!='ENDED'):
                matrix.append(dict(phase=phase,status='NOT_RUN_DEPENDENCY_OR_FROZEN_FAILURE'));continue
            result=m.run_child(run/'processes'/phase,[sys.executable,'-X','utf8','-B',str(view/'examples/a03/R1/final.py'),
                '--watch','--phase',phase,'--output',str(run/'cases'/phase)],cwd=PROJECT,env=env,timeout=240)
            status='ENDED'if result['exit_code']==0 and not result['timeout']else'FAILED_NO_RETRY'
            matrix.append(dict(phase=phase,status=status,process=result))
            if status!='ENDED'and business:failed_business=True
    finally:d.write(run/'matrix.json',matrix)


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',action='store_true');p.add_argument('--watch',action='store_true')
    p.add_argument('--candidate');p.add_argument('--phase');p.add_argument('--output',type=Path)
    args=p.parse_args()
    if args.batch:batch(args)
    elif args.watch:
        args.output.mkdir(parents=True,exist_ok=False)
        result=m.run_child(args.output/'process',[sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),
            '--phase',args.phase,'--output',str(args.output)],cwd=PROJECT,env=dict(os.environ),timeout=180)
        if result['exit_code']!=0 or result['timeout']:raise RuntimeError('frozen worker failed; no retry')
    else:worker(args)


if __name__=='__main__':main()
