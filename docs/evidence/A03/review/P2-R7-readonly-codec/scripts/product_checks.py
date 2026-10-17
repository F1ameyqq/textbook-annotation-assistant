# -*- coding: utf-8 -*-
"""One round of seven public-API cases and the bounded R7 contracts/paths."""
import copy
from dataclasses import FrozenInstanceError,replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from nested import install

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout';FIX=ROOT/'tests/fixtures/a03/P2-R7-readonly-codec'
def load(p):return json.loads(p.read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
assert load(OUT/'source-data-wheel-audit.json')['status']=='STATIC_AUDIT_READY_FOR_BOUNDED_PRODUCT_RUNS'
sys.path.insert(0,str(ROOT/'src'))
import annotation.contracts.a03_bridge as bridge
from annotation.contracts import ContractError
from annotation.contracts.a03_bridge._rules import StaticPackage
assert Path(bridge.__file__).resolve()==ROOT/'src/annotation/contracts/a03_bridge/__init__.py'
rows=load(FIX/'index.json')['cases'];observations=[];checks=[];snapshot=None;original=None
for row in rows:
    bundle=load(FIX/row['bundle']);root=FIX/row['asset_root'];instances=[]
    def trace(frame,event,arg):
        if event=='call'and frame.f_code is StaticPackage.validate.__code__:instances.append(frame.f_locals['self'])
        return trace
    context=bridge.open_static_context(asset_root=root);old_trace=sys.gettrace();sys.settrace(trace)
    try:
        try:
            result=bridge.validate_static_bundle(bundle,context=context);actual='STATIC_ACCEPTED';error=None
            assert result.model_dump()==bundle
        except bridge.StaticCodecError as e:
            assert isinstance(e,ContractError);actual=e.code;error={'code':e.code,'path':e.path}
    finally:sys.settrace(old_trace)
    assert actual==row['expected']and len(instances)==1,(row['id'],actual,error)
    pkg=instances[0];assert all(book is not None for _,_,book,_,_ in pkg.consumers)
    if row['id']=='registration-positive':
        assert pkg.stages==['MIXED_DAG','CONSUMER_DECLARATIONS_BOOK_SCOPE','ARTIFACT_HASH_AND_PRE_STATIC_TAIL','COMPLETE_STATIC_RETURN']
        assert len(pkg.consumers)==16 and [x['mode']for x in pkg.prefix_visits]==['REAL_CONSUMER','GLOBAL_GRAPH']
        snapshot=result;original=copy.deepcopy(bundle);source_input=bundle;positive_root=root
        assert snapshot.canonical_sha256==sha(canon(bundle))
        assert all(sha((root/r.path).read_bytes())==r.raw_sha256 for r in snapshot.resources)
    elif row['id']in ['source-binding-negative','snapshot-binding-negative']:
        assert error['path']=='r4-static/'+row['id']+'/prefix.json'and pkg.registration_checks and not all(pkg.registration_checks[0]['binding_checks'].values())
    elif row['id']=='target-tuple-negative':
        assert error['path'].endswith('/registration/target')and all(pkg.registration_checks[0]['binding_checks'].values())and not pkg.registration_checks[0]['target_checks']['snapshot_target_id']
    elif row['id']=='r3-original-undeclared-evidence':assert error['path']=='origin-a-SourceBundle'and pkg.stages==['MIXED_DAG','CONSUMER_DECLARATIONS_BOOK_SCOPE']
    elif row['id']=='global-resource-hash-corruption':assert error['path']=='r5-static/global-only-proof.txt'and not pkg.contexts and not pkg.stages
    else:assert actual=='MIXED_CYCLE'and pkg.stages==['MIXED_DAG']
    observations.append({'id':row['id'],'actual':actual,'error':error,'stages':pkg.stages,'registration_checks':pkg.registration_checks,
      'real_consumers':len(pkg.consumers),'none_book_consumers':sum(b is None for _,_,b,_,_ in pkg.consumers),'graph_nodes':len(pkg.edges),'complete_API_calls':1})

def rejected(label,expected,fn):
    try:fn();raise AssertionError(label+' unexpectedly accepted')
    except bridge.StaticCodecError as e:assert e.code==expected,(label,e.code,e.path);checks.append({'id':label,'actual':e.code,'path':e.path})
selection=bridge.select_static_codec();assert selection.codec_id=='a03-static-readonly-v1'and selection.adoption_scope=='A_INTERNAL_READONLY'
assert not hasattr(selection,'__dict__')and type(selection.schema_pins)is tuple
for role in ['CURRENT','UNKNOWN_ROLE']:rejected('role-'+role,'ROLE_NOT_ALLOWED',lambda role=role:bridge.open_static_context(asset_root=positive_root,selection=replace(selection,role=role)))
changes={'codec_id':'wrong-codec','exchange_version':'unknown-exchange','artifact_versions':('unknown-artifact',),'profile_id':'wrong-profile',
 'profile_sha256':'0'*64,'schema_pins':((selection.schema_pins[0][0],'0'*64),)+selection.schema_pins[1:],
 'api_sha256':'0'*64,'validation_rules_id':'wrong-rules','adoption_scope':'wrong-scope'}
for field,value in changes.items():rejected('selection-'+field,'SELECTION_PINS',lambda field=field,value=value:bridge.open_static_context(asset_root=positive_root,selection=replace(selection,**{field:value})))
rejected('selection-concrete-type','SELECTION_TYPE',lambda:bridge.open_static_context(asset_root=positive_root,selection={'role':'STATIC_INSPECTION'}))
rejected('asset-root-required-value','ASSET_ROOT',lambda:bridge.open_static_context(asset_root=None))
try:bridge.open_static_context();raise AssertionError('missing asset_root accepted')
except TypeError:checks.append({'id':'asset-root-required-keyword','actual':'TypeError'})
context=bridge.open_static_context(asset_root=positive_root)
rejected('context-concrete-type','CONTEXT_TYPE',lambda:bridge.validate_static_bundle(original,context={'selection':selection}))
bad=copy.deepcopy(original);bad['format_version']='a03-unknown-envelope'
rejected('unknown-envelope','EXCHANGE_VERSION',lambda:bridge.validate_static_bundle(bad,context=context))
for label,value in [('nan',float('nan')),('positive-inf',float('inf')),('negative-inf',-float('inf'))]:
    bad=copy.deepcopy(original);bad['nonfinite']=value
    rejected('finite-json-'+label,'JSON_NONFINITE',lambda bad=bad:bridge.validate_static_bundle(bad,context=context))
from annotation.contracts.a03_bridge._schema import validate as schema_validate
rejected('unknown-schema-assertion','SCHEMA_KEYWORDS',lambda:schema_validate({}, {'allOf':[{}]}))
source_input['artifacts'].clear();dump=snapshot.model_dump();dump['evidence'].clear()
assert snapshot.model_dump()==original and snapshot.canonical_sha256==sha(canon(original))
for label,fn,error_type in [('deep-data-readonly',lambda:snapshot.data['artifacts'][0]['payload'].__setitem__('changed',True),(TypeError,AttributeError)),
 ('frozen-snapshot',lambda:setattr(snapshot,'canonical_sha256','0'*64),FrozenInstanceError),('frozen-resource',lambda:setattr(snapshot.resources[0],'path','changed'),FrozenInstanceError),
 ('frozen-selection',lambda:setattr(selection,'role','CURRENT'),FrozenInstanceError)]:
    try:fn();raise AssertionError(label+' unexpectedly mutable')
    except error_type:checks.append({'id':label,'actual':'IMMUTABLE'})
assert not hasattr(snapshot,'__dict__')and not hasattr(snapshot,'writer')

records,restore=install('product-paths');temp_root=Path(tempfile.mkdtemp(prefix='a03-r7-review-path-')).resolve();junction=None;link=None;path_record={}
def with_orphan(path,raw):
    b=copy.deepcopy(original);record=copy.deepcopy(b['evidence'][0]);record.update(evidence_id='proof-r7-review-path',resource={'path':path,'sha256':sha(raw),'media_type':'text/plain','origin':'SYNTHETIC'})
    b['evidence'].append(record);return b
try:
    root=temp_root/'assets';shutil.copytree(positive_root,root);outside_dir=temp_root/'outside';outside_dir.mkdir();ordinary=outside_dir/'ordinary.txt';ordinary.write_bytes(b'ordinary R7 independent path test\n')
    ctx=bridge.open_static_context(asset_root=root);raw=ordinary.read_bytes()
    for label,path in [('relative','../outside/ordinary.txt'),('absolute',str(ordinary))]:
        rejected('resource-'+label,'RESOURCE_PATH',lambda path=path:bridge.validate_static_bundle(with_orphan(path,raw),context=ctx))
    link=root/'ordinary-link.txt';junction=root/'ordinary-junction'
    try:os.symlink(str(ordinary),str(link));logical=link.name;path_record={'symlink':'CREATED','junction':'NOT_NEEDED'}
    except OSError as e:
        path_record={'symlink':'SKIPPED_PRIVILEGE_OR_HOST_LIMIT','winerror':getattr(e,'winerror',None),'errno':e.errno,'junction':'PENDING'}
        assert os.name=='nt'
        cp=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(junction),str(outside_dir)],capture_output=True,timeout=10)
        assert cp.returncode==0,(cp.returncode,cp.stderr);assert junction.resolve()==outside_dir.resolve()
        logical=junction.name+'/ordinary.txt';path_record['junction']='CREATED_AND_TARGET_VERIFIED'
    rejected('resource-resolved-root-escape','RESOURCE_ESCAPE',lambda:bridge.validate_static_bundle(with_orphan(logical,raw),context=ctx))
    path_record.update(resource_path=logical,resolved_target=str((root/logical).resolve()),asset_root=str(root),expected_outside_file=str(ordinary),result='RESOURCE_ESCAPE')
finally:
    if link is not None and link.is_symlink():assert link.parent.resolve()==(temp_root/'assets').resolve();link.unlink()
    if junction is not None and junction.exists():
        assert junction.parent.resolve()==(temp_root/'assets').resolve()and junction.resolve()==(temp_root/'outside').resolve();os.rmdir(junction)
    restore()
    assert temp_root.parent==Path(tempfile.gettempdir()).resolve()and temp_root.name.startswith('a03-r7-review-path-')and not temp_root.is_symlink()
    shutil.rmtree(temp_root)
assert all(r.logged and r.returncode==0 and not r.record['alive']and not r.record['timed_out']for r in records)
write(OUT/'product-api-results.json',{'status':'BOUNDED_PRODUCT_READONLY_CHECKS_PASSED','product_file':bridge.__file__,'product_file_sha256':sha(Path(bridge.__file__).read_bytes()),
 'seven_fixed_cases':observations,'selection_checks':checks,'snapshot_complete_input_preserved':True,'snapshot_resources_match_actual_bytes':True,
 'path_boundary':path_record,'temporary_path_root_removed':not temp_root.exists(),'nested_children':len(records),
 'role':selection.role,'adoption_scope':selection.adoption_scope,'old_static_or_native_calls':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print(json.dumps({'status':'BOUNDED_PRODUCT_READONLY_CHECKS_PASSED','frozen_cases':len(observations),'API_checks':len(checks),'path_boundary':path_record,'nested_children':len(records)}))
