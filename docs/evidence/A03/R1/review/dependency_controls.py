"""Independent warm/cold dependency deltas; no DB, target or dispatch."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path('D:/1800-worktrees/a03-r1-review-54e86adf')
OUT=ROOT/'docs/evidence/A03/R1/review/dependency-controls'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    from annotation.contracts import ContractError,artifact_ref
    from annotation.contracts.a03_bridge._json import digest
    from annotation.contracts.a03_native import validate_native_bundle
    import annotation.contracts.a03_native as native
    from annotation.runtime.storage.native import NativeRuntimeStore,NativeRegistry
    OUT.mkdir(exist_ok=False)
    fixture=Path(native.__file__).resolve().parents[3]/'examples/a03/T3-closure/inputs/single'
    # The complete source view is pinned; this path deliberately comes from
    # its adjacent raw fixture, never a floating checkout.
    fixture=Path(native.__file__).resolve().parents[4]/'examples/a03/T3-closure/inputs/single'
    root=OUT/'input';shutil.copytree(fixture,root)
    data=json.loads((root/'initial.json').read_bytes())
    graph=next(a for a in data['artifacts'] if a['kind']=='QuestionGraph')
    leaf=json.dumps({'graph':artifact_ref(graph)},sort_keys=True).encode()+b'\n'
    leafref=dict(path='assets/review-leaf.json',sha256=sha(leaf),media_type='application/json',origin='SYNTHETIC')
    outer=json.dumps({'nested':leafref},sort_keys=True).encode()+b'\n'
    outerref=dict(path='assets/review-outer.json',sha256=sha(outer),media_type='application/json',origin='SYNTHETIC')
    (root/leafref['path']).write_bytes(leaf);(root/outerref['path']).write_bytes(outer)
    data['evidence'].append(dict(evidence_id='review-recursive',resource=outerref,description='fixed synthetic independent negative',mode='SYNTHETIC'))
    snapshot=data['artifacts'][-1]
    snapshot['payload']['evidence_refs'].append('review-recursive')
    if artifact_ref(graph) not in snapshot['input_refs']:snapshot['input_refs'].append(artifact_ref(graph))
    snapshot['content_hash']=digest({k:v for k,v in snapshot.items() if k!='content_hash'})
    store=NativeRuntimeStore.__new__(NativeRuntimeStore);store.native_registry=NativeRegistry(store)
    good=store._validate(data,asset_root=root)
    validate_native_bundle(good,bridge_context=good.bridge_context)
    rows=[]
    def rejected(label,call,code):
        try:call()
        except ContractError as e:
            assert any(x['code']==code for x in e.issues),(label,e.issues)
            rows.append(dict(control=label,expected=code,issues=e.issues))
        else:raise AssertionError(label+' unexpectedly accepted')
    altered=b'X'*len(leaf)
    (root/leafref['path']).write_bytes(altered)
    rejected('warm_transitive_resource',lambda:validate_native_bundle(good,bridge_context=good.bridge_context),'RESOURCE_HASH')
    (root/leafref['path']).write_bytes(leaf)
    bad=copy.deepcopy(data)
    second=copy.deepcopy(snapshot);second['artifact_id']='review-second-consumer'
    second['input_refs'].remove(artifact_ref(graph))
    second['content_hash']=digest({k:v for k,v in second.items() if k!='content_hash'})
    bad['artifacts'].append(second)
    rejected('warm_second_consumer_declaration',lambda:store._validate(bad,asset_root=root),'UNDECLARED_REFERENCE')
    bad=copy.deepcopy(data);bad['evidence'][0]['mode']='OBSERVED'
    rejected('warm_observed_evidence',lambda:store._validate(bad,asset_root=root),'SYNTHETIC_ONLY')
    schema=Path(native.__file__).parent/'data/schemas/fact.json';raw=schema.read_bytes()
    try:
        schema.write_bytes(raw+b'\n')
        rejected('warm_schema_bytes',lambda:validate_native_bundle(good,bridge_context=good.bridge_context),'NATIVE_SCHEMA_PIN')
    finally:schema.write_bytes(raw)
    # An actual helper dependency is covered in addition to __init__.py.
    helper=Path(native.__file__).parent.parent/'a03_bridge/_json.py';raw=helper.read_bytes()
    try:
        helper.write_bytes(raw+b'\n# independent disposable dependency negative\n')
        rejected('warm_helper_bytes',lambda:validate_native_bundle(good,bridge_context=good.bridge_context),'NATIVE_IMPLEMENTATION_PIN')
    finally:helper.write_bytes(raw)
    validated=validate_native_bundle(good,bridge_context=good.bridge_context)
    assert validated.model_dump()==data
    result=dict(controls=rows,counts=store.native_registry.validation_counts,no_DB=True,
        targets=0,dispatch=0,product_file=str(Path(native.__file__).resolve()),
        product_sha256=sha(Path(native.__file__).read_bytes()),resource_manifest=good.bridge_context.resource_manifest)
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (OUT/'valid-input.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print('INDEPENDENT_DEPENDENCY_CONTROLS_ENDED',len(rows))

if __name__=='__main__':main()
