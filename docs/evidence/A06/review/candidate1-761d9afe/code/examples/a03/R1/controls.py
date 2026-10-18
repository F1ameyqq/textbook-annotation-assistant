"""Finite independent rejection/value deltas, no dispatch/recovery/target starts."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/evidence/A03/R1/execution/controls'
MROOT=ROOT/'docs/evidence/A03/R1/execution/candidate-1/business'
sys.path.insert(0,str(MROOT/'runtime-view/src'))
spec=importlib.util.spec_from_file_location('r1_delta',ROOT/'examples/a03/R1/deltas.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)


def seal_all(data):
    from annotation.contracts.a03_bridge._json import digest
    from annotation.contracts import artifact_ref
    changed={}
    def rewrite(v):
        if isinstance(v,dict):
            if set(v)=={'artifact_id','revision','kind','content_hash'}:
                return copy.deepcopy(changed.get((v['artifact_id'],v['revision']),v))
            return {k:rewrite(x)for k,x in v.items()}
        if isinstance(v,list):return [rewrite(x)for x in v]
        return v
    for i,original in enumerate(data['artifacts']):
        a=rewrite(original)
        a['content_hash']=digest({k:v for k,v in a.items()if k!='content_hash'})
        changed[(a['artifact_id'],a['revision'])]=artifact_ref(a)
        data['artifacts'][i]=a


def main():
    from annotation.runtime.storage.native import NativeRuntimeStore,NativeRegistry,open_native_state
    from annotation.runtime.recovery import reconcile
    from annotation.contracts import load_archive_bundle,validate_bundle
    from annotation.contracts.a03_native import select_native_codec
    from annotation.contracts.a03_bridge import open_static_context,validate_static_bundle
    from annotation.contracts.recovery import _node
    from annotation.runtime.recovery.quality import _diagnostic
    OUT.mkdir(exist_ok=False)
    rows=[]
    root=OUT/'input'
    shutil.copytree(MROOT/'runtime-view/examples/a03/T3-closure/inputs/single',root)
    initial=json.loads((root/'initial.json').read_bytes())
    store=NativeRuntimeStore.__new__(NativeRuntimeStore);store.native_registry=NativeRegistry(store)
    good=store._validate(initial,asset_root=root)
    slots=('producer','asset','record','region','coverage','recursive')
    for slot in slots:
        data=copy.deepcopy(initial)
        source,evidence,graph,snapshot=data['artifacts']
        if slot=='producer':source['producer']['evidence_mode']='OBSERVED'
        elif slot=='asset':source['payload']['assets'][0]['origin']='ORIGINAL'
        elif slot=='record':data['evidence'][0]['mode']='OBSERVED'
        elif slot=='region':evidence['payload']['regions'][0]['source']='HUMAN'
        elif slot=='coverage':evidence['payload']['coverage_clues'][0]['source']='INDEPENDENT_REVIEW'
        else:
            raw=b'{"origin":"ORIGINAL"}\n';(root/'assets/control-nested.json').write_bytes(raw)
            data['evidence'].append(dict(evidence_id='R1-nested-origin',description='synthetic negative only',mode='SYNTHETIC',
                resource=dict(path='assets/control-nested.json',sha256=hashlib.sha256(raw).hexdigest(),media_type='application/json',origin='SYNTHETIC')))
        seal_all(data)
        rows.append(dict(key='G4-'+slot,refusal=d.reject(lambda:store._validate(data,asset_root=root))))
    sql=json.loads((MROOT/'cases/M1/captures/after-release-finish/SQL.json').read_bytes())
    reg=sql['runtime']['tables']['registrations'][0]
    real=json.loads(Path(reg['bundle_path']).read_bytes())
    realroot=Path(reg['package_root'])
    store._validate(real,asset_root=realroot)
    data=copy.deepcopy(real)
    receipt=next(a for a in data['artifacts']if a['kind']=='ExecutionReceipt')
    receipt['producer']['evidence_mode']='PLATFORM_OBSERVED'
    seal_all(data)
    rows.append(dict(key='G4-receipt',refusal=d.reject(lambda:store._validate(data,asset_root=realroot))))
    for field,value in [('content_check_status','VERIFIED'),('total_expected',0)]:
        data=copy.deepcopy(real);batch=next(a for a in data['artifacts']if a['kind']=='BatchReport')
        batch['payload'][field]=value;seal_all(data)
        rows.append(dict(key='G5-'+field,refusal=d.reject(lambda:store._validate(data,asset_root=realroot))))
    source=next(a for a in real['artifacts']if a['kind']=='SourceBundle')
    graph=next(a for a in real['artifacts']if a['kind']=='QuestionGraph')
    diagnostic_rows=[]
    for label,manifest in [('known',['not-in-graph','exception','skipped']),('unknown',None),('zero',[])]:
        s=copy.deepcopy(source);s['payload']['scope_manifest']=manifest
        result=_diagnostic(_node(s),_node(graph),{'exception':'EXCEPTION','skipped':'SKIPPED'}if manifest else {},{}, {},state='HOLD')
        assert result['total_expected']==(None if manifest is None else len(manifest))
        assert result['completion_ratio']is None and result['content_check_status']=='PENDING'
        diagnostic_rows.append(dict(label=label,value=result,layer='PURE_DIAGNOSTIC_NOT_NATIVE_REPORT'))
    for limit in (0,4):
        refusal=d.reject(lambda:reconcile(None,max_attempts=limit))
        assert refusal.get('code')=='RECONCILE_ATTEMPT_LIMIT'
        rows.append(dict(key='G6-invalid-'+str(limit),refusal=refusal))
    # Disposable implementation/schema bytes only; restore exact original bytes.
    import annotation.contracts.a03_native as native
    schema=Path(native.__file__).parent/'data/schemas/fact.json';raw=schema.read_bytes()
    try:
        schema.write_bytes(raw+b'\n')
        rows.append(dict(key='G1-schema-bytes-after-success',refusal=d.reject(select_native_codec)))
    finally:schema.write_bytes(raw)
    anchor=json.loads((MROOT/'cases/M1/anchor.json').read_bytes())
    for label,overrides in [('wrong-ledger',dict(expected_ledger_id='wrong',expected_target_store_id=anchor['target_store_id'])),
        ('wrong-target-store',dict(expected_ledger_id=anchor['ledger_id'],expected_target_store_id='wrong'))]:
        rows.append(dict(key='G2-'+label,refusal=d.reject(lambda:open_native_state(MROOT/'cases/M1/anchor.json',**overrides))))
    for label,raw in [('corrupt',b'not a sqlite database'),('missing',None)]:
        folder=OUT/label;folder.mkdir();state=folder/'runtime';state.mkdir();a=folder/'anchor.json'
        desc=dict(anchor,anchor_path=str(a.resolve()),state_dir=str(state.resolve()))
        d.write(a,desc)
        if raw is not None:(state/'runtime.sqlite3').write_bytes(raw)
        rows.append(dict(key='G2-'+label,refusal=d.reject(lambda:open_native_state(a,expected_ledger_id=anchor['ledger_id'],expected_target_store_id=anchor['target_store_id']))))
    # Current 1.4 never aliases the 1.3 readonly selector.
    context=open_static_context(asset_root=root)
    rows.append(dict(key='G3-native-as-readonly',refusal=d.reject(lambda:validate_static_bundle(initial,context=context))))
    # Explicit role reads; archive loading does not acquire a native context.
    legacy_path=ROOT/'docs/evidence/A03/R1/execution/deltas-correction/legacy/history-1/history.json'
    archive=load_archive_bundle(legacy_path)
    role=dict(legacy_archive_read='OK',native_authority=hasattr(archive,'bridge_context'))
    assert not role['native_authority']
    d.write(OUT/'results.json',dict(negative_controls=rows,diagnostics=diagnostic_rows,roles=role,
        imports=d.imports(),native_validation_counts=store.native_registry.validation_counts,
        native_targets=0,dispatch=0,reconcile_reads=0,claims=0))
    print('FINITE_CONTROLS_ENDED',len(rows))


if __name__=='__main__':main()
