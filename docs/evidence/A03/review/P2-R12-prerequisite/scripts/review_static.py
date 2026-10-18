# -*- coding: utf-8 -*-
"""Raw Git, class-scoped AST and JSON only. Never imports candidate modules."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import time
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1]
BASE='cc5966dc58c62017a27266c40ca0cedc5c68485c';TARGET='394fe51f5ed14c5ed312073a20faac0f5cbb9990'
WF='7bc96e3aa378fb7b5b0a4b5cdd49fb721777ac84';EXEC_WF='7593f880ebec191ed55e03b2d3893d68b00ab0ca'
EV='docs/evidence/A03/execution/P2-R12-inconclusive-readback/'
TASK='docs/tasks/A03-P2-R12-prerequisite-review-handoff.md'
REPORT='docs/tasks/A03-P2-R12-inconclusive-readback-report.md'
DRIVER='tests/test_a03_p2_r12_inconclusive_readback.py'
RESET='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(v if isinstance(v,bytes) else (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
counter=0
def git(*args,data=b''):
    global counter
    counter+=1;d=OUT/'git-processes'/('%02d'%counter);d.mkdir(parents=True,exist_ok=False)
    argv=['git','-c','core.longpaths=true',*args];write(d/'stdin.bin',data)
    write(d/'preregistered.json',{'argv':argv,'cwd':str(ROOT),'timeout_seconds':10,'registered_at_ns':time.time_ns(),
      'source_sha256':sha(Path(__file__).read_bytes()),'stdin_sha256':sha(data)})
    with (d/'stdout.bin').open('xb') as stdout,(d/'stderr.bin').open('xb') as stderr:
        p=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr)
        write(d/'started.json',{'pid':p.pid,'started_at_ns':time.time_ns()});timed=False
        try:p.communicate(input=data,timeout=10)
        except subprocess.TimeoutExpired:timed=True;p.kill();p.communicate()
    write(d/'completed.json',{'pid':p.pid,'exit_code':p.returncode,'timed_out':timed,'alive':p.poll() is None,
      'ended_at_ns':time.time_ns(),'stdout_sha256':sha((d/'stdout.bin').read_bytes()),'stderr_sha256':sha((d/'stderr.bin').read_bytes())})
    assert p.returncode==0 and not timed
    return (d/'stdout.bin').read_bytes()
def tree(rev):
    result={}
    for r in git('ls-tree','-rz','--full-tree',rev).split(b'\0'):
        if r:
            meta,path=r.split(b'\t',1);result[path.decode('utf8')]=meta.decode()
    return result
def batch(specs):
    specs=sorted(set(specs));body=git('cat-file','--batch',data=('\n'.join(specs)+'\n').encode());pos=0;result={}
    for spec in specs:
        end=body.index(b'\n',pos);head=body[pos:end].decode().split();pos=end+1
        assert len(head)==3 and head[1]=='blob';n=int(head[2]);b=body[pos:pos+n];pos+=n
        assert body[pos:pos+1]==b'\n';pos+=1
        assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==head[0]
        result[spec]=(head[0],b)
    assert pos==len(body);return result

before=tree(BASE);after=tree(TARGET)
assert len(before)==32993 and all(after.get(p)==v for p,v in before.items())
added=sorted(set(after)-set(before));assert len(added)==39
assert all(p.startswith((EV,'examples/a03/P2-R12-inconclusive-readback/')) or p in (REPORT,DRIVER) for p in added)
assert git('rev-parse',TARGET+'^').decode().strip()==BASE
first=batch([TARGET+':'+p for p in added]+[WF+':'+TASK])
assert sha(first[WF+':'+TASK][1])=='b55a77279059871377e59aa1d7eafd6adba7492fba9d3b598f493e1ea5d14db3'
expected={REPORT:'cfb51c43f718349aa2c8d99fbb9bc3e145eb6b891e4d9507065648af9bd4fc04',
 EV+'manifest.json':'b3f0483de0b007341a750963f3d71db92b8b9efec124c26b8394935bd6325f75',
 EV+'process-release.json':'5318caeb0a97f014ee2c038b349316d41be12430e9ff29ca441f0a5679013b1f'}
for p,digest in expected.items():assert sha(first[TARGET+':'+p][1])==digest
def author(name):return json.loads(first[TARGET+':'+EV+name][1])
manifest=author('manifest.json');inputs=author('inputs.json')
assert len(manifest['entries'])==38 and {r['path'] for r in manifest['entries']}==set(added)-{EV+'manifest.json'}
for r in manifest['entries']:
    oid,b=first[TARGET+':'+r['path']];assert len(b)==r['bytes'] and sha(b)==r['sha256'] and after[r['path']].split()[2]==oid
assert len(inputs['files'])==4 and len(inputs['sources'])==10
assert inputs['base_entries']==len(before) and inputs['base_tree_sha256']==sha(git('ls-tree','-r',BASE))
source_index=author('runs/static-prerequisite/product-source-index.json')
source_paths={r['path'] for r in source_index}|{r['path'] for r in inputs['sources']}
source_paths|={'src/annotation/contracts/a03_bridge/_schema.py','src/annotation/delivery/mock/__init__.py'}
specs=[BASE+':'+p for p in source_paths]+[r['workflow']+':'+r['path'] for r in inputs['files']]
second=batch(specs);blobs={**first,**second}
for r in inputs['files']:
    b=blobs[r['workflow']+':'+r['path']][1]
    assert len(b)==r['bytes'] and sha(b)==r['sha256']==sha(first[TARGET+':'+EV+'inputs/'+Path(r['path']).name][1])
for r in inputs['sources']:
    b=blobs[BASE+':'+r['path']][1]
    assert b==first[TARGET+':'+EV+'inputs/base/'+r['path']][1]
    assert len(b)==r['bytes']==r['worktree_bytes'] and sha(b)==r['raw_Git_sha256']==r['worktree_sha256'] and r['raw_bytes_identical']
CRLF={'src/annotation/__init__.py','src/annotation/contracts/__main__.py','src/annotation/contracts/cli.py','src/annotation/contracts/integrity.py','src/annotation/contracts/models.py'}
representations=[]
for r in source_index:
    b=blobs[BASE+':'+r['path']][1];mode='RAW_GIT_BYTES'
    if sha(b)!=r['sha256']:
        assert r['path'] in CRLF and b'\r\n' not in b and sha(b.replace(b'\n',b'\r\n'))==r['sha256'];mode='EXPLICIT_LEGACY_LF_TO_CRLF'
    representations.append({'path':r['path'],'author_sha256':r['sha256'],'raw_sha256':sha(b),'representation':mode})
exports=[]
for spec,(oid,b) in sorted(blobs.items()):
    rev,path=spec.split(':',1);prefix='input/target' if rev==TARGET else 'input/base' if rev==BASE else 'input/workflow' if rev==WF else 'input/execution-workflow'
    relative=Path(prefix)/path
    if len(str(OUT/relative))>235:relative=Path('input/raw')/(sha(spec.encode())[:16]+'-'+Path(path).name)
    write(OUT/relative,b);exports.append({'commit':rev,'path':path,'file':relative.as_posix(),'bytes':len(b),'sha256':sha(b),'raw_git_sha1':oid})
write(OUT/'input-index.json',{'workflow':WF,'execution_workflow':EXEC_WF,'base':BASE,'target':TARGET,'exports':exports})
write(OUT/'delivery-byte-review.json',{'old_tree_entries_preserved':32993,'changed_old_entries':[],'new_files':39,'manifest_entries':38,
 'workflow_inputs_verified':4,'source_inputs_verified':10,'source_index_representations':representations,
 'base_tree_identity_matches_registered_commit':True,'functional_databases_in_added_paths':any(p.endswith(('.sqlite3','.db')) for p in added),
 'expected_hashes':expected,'no_old_local_files_written':True})

def raw(path):return blobs[BASE+':'+path][1]
def text(path):return raw(path).decode('utf8',errors='strict')
def parse(path):return ast.parse(text(path),filename=path)
def entity(path,cls,name):
    root=parse(path);scope=root
    if cls:scope=next(n for n in root.body if isinstance(n,ast.ClassDef) and n.name==cls)
    node=next(n for n in scope.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    return node,{'path':path,'class':cls,'function':name,'line':node.lineno,'end_line':node.end_lineno,
      'source_sha256':sha(raw(path)),'source':ast.get_source_segment(text(path),node)}
ST='src/annotation/runtime/storage/__init__.py';NA='src/annotation/runtime/storage/native.py'
NC='src/annotation/contracts/a03_native/__init__.py';CL='src/annotation/contracts/a03_native/_closure.py'
RE='src/annotation/contracts/recovery.py';NQ='src/annotation/runtime/recovery/native_quality.py'
PL='src/annotation/delivery/planner/__init__.py';PE='src/annotation/delivery/mock/persistent.py'
nodes={};methods={}
for path,cls,names in [(ST,'RuntimeStore',['commit_action_result','project_plan','_project_plan_locked','_new_artifact','_append','_validate','transaction']),
 (NA,'NativeRuntimeStore',['_append','bridge_for']), (NA,'NativeRegistry',['context']),
 (NC,None,['_issue_context','_validate_value','validate_native_bundle','_reports','select_native_codec']),
 (NC,'NativeSchemas',['check']),(CL,'StaticPackage',['validate']),
 (RE,None,['validate_recovery_bundle']),(NQ,None,['publish_native_quality']),
 (PL,None,['compare_action_effect']),(PE,None,['apply_synthetic_action']),(PE,'PersistentMockSession',['dispatch_action','observe_target'])]:
    for name in names:
        node,record=entity(path,cls,name);key=(cls or 'module')+'.'+name;nodes[key]=node;methods[key]=record
native_class=next(n for n in parse(NA).body if isinstance(n,ast.ClassDef) and n.name=='NativeRuntimeStore')
native_methods={n.name for n in native_class.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
inherited=['commit_action_result','project_plan','_project_plan_locked','_new_artifact','_validate','transaction']
assert all(n not in native_methods for n in inherited) and any(isinstance(n,ast.Name) and n.id=='RuntimeStore' for n in native_class.bases)
projection=nodes['RuntimeStore._project_plan_locked'];source=text(ST)
calls=[n for n in ast.walk(projection) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='_new_artifact'
       and len(n.args)>=3 and isinstance(n.args[1],ast.Constant) and n.args[1].value=='CheckReport' and isinstance(n.args[2],ast.Dict)]
assert len(calls)==1;post=calls[0];emitted=sorted(k.value for k in post.args[2].keys if isinstance(k,ast.Constant))
parents={child:parent for parent in ast.walk(projection) for child in ast.iter_child_nodes(parent)}
conditions=[];current=post
while current in parents:
    current=parents[current]
    if isinstance(current,ast.If):conditions.append({'line':current.lineno,'test':ast.get_source_segment(source,current.test)})
schema_path='src/annotation/contracts/a03_native/data/schemas/exchange.json';schema=json.loads(raw(schema_path))
pointer='/$defs/AmendedCheckReport/properties/payload/oneOf/2'
payload=schema['$defs']['AmendedCheckReport']['properties']['payload']['oneOf'][2]
missing=sorted(set(payload['required'])-set(emitted));extra=sorted(set(emitted)-set(payload['properties']))
assert missing==['action_bindings','content_check_status','frame_structure','report_observation','report_snapshot_ref','submission_status']
assert extra==['checks','coverage','reason','snapshot'] and payload['additionalProperties'] is False
stage=payload['properties']['stage'];assert stage.get('const')=='POST_APPLY' or stage.get('enum')==['POST_APPLY']
profile_path='src/annotation/contracts/a03_native/data/profile.json';profile=json.loads(raw(profile_path))
pin_rows=[]
for p,d in profile['schema_pins']:
    path='src/annotation/contracts/a03_native/data/'+p;assert sha(raw(path))==d;pin_rows.append({'kind':'schema','path':path,'sha256':d})
for p,d in profile['implementation_pins']:
    path='src/'+p[1:] if p.startswith('@') else 'src/annotation/contracts/a03_native/'+p
    assert sha(raw(path))==d;pin_rows.append({'kind':'implementation','path':path,'sha256':d})
adoption=json.loads(raw('src/annotation/contracts/a03_native/data/adoption.json'));assert adoption['profile_sha256']==sha(raw(profile_path))
write(OUT/'class-scoped-chain.json',{'analysis':'Class-body AST selection, inheritance resolution and source-only control/data flow; no candidate import/exec.',
 'native_base':'RuntimeStore','native_inherited_methods':inherited,'native_overrides_sorted':sorted(native_methods),
 'methods':methods,'old_POST_constructor_line':post.lineno,'old_POST_ancestor_conditions_nearest_first':conditions,
 'schema_path':schema_path,'schema_raw_sha256':sha(raw(schema_path)),'schema_pointer':pointer,'emitted_literal_keys':emitted,
 'native_required':payload['required'],'native_properties':sorted(payload['properties']),'missing_required':missing,'extra_forbidden':extra,
 'root_artifact_union':schema['properties']['artifacts']['items'],'schema_pins_and_implementation_pins':pin_rows,
 'implementation_repair_pin_hits':[p for p in pin_rows if p['path'] in (ST,NA)],
 'native_report_publication_separate':True,'runtime_exception_or_transaction_effects':'NOT_OBSERVED'})

pre=author('runs/static-prerequisite/preregistered.json');start=author('runs/static-prerequisite/started.json');end=author('runs/static-prerequisite/completed.json')
release=author('process-release.json');snapshot=first[TARGET+':'+EV+'runs/static-prerequisite/script-snapshot.py'][1]
assert sha(snapshot)==sha(first[TARGET+':'+DRIVER][1])==pre['script_sha256']
assert pre['inputs_sha256']==sha(first[TARGET+':'+EV+'inputs.json'][1])
assert pre['source_index_sha256']==sha(first[TARGET+':'+EV+'runs/static-prerequisite/product-source-index.json'][1])
assert start['pid']==end['pid']==release['records'][0]['pid']==54248 and end['exit_code']==0 and not end['alive'] and not end.get('timed_out',end.get('timeout',False))
assert len(release['records'])==1 and pre['timeout_seconds']==45 and pre['scope']=='STATIC_ONLY_NO_PRODUCT_CALLS'
for stream in ('stdout','stderr'):
    if stream+'_sha256' in end:assert sha(first[TARGET+':'+EV+'runs/static-prerequisite/'+stream+'.txt'][1])==end[stream+'_sha256']
script_tree=ast.parse(snapshot.decode('utf8',errors='strict'),filename=DRIVER)
imports=[]
for n in ast.walk(script_tree):
    if isinstance(n,ast.Import):imports.extend(a.name for a in n.names)
    elif isinstance(n,ast.ImportFrom):imports.append(n.module)
assert not any(name and name.startswith(('annotation','sqlite3')) for name in imports)
outcome=author('bounded-outcome.json');assert outcome['effect_count']=='NOT_OBSERVED_NO_TARGET_DATABASE'
assert outcome['runtime_outer_error_code']=='NOT_OBSERVED_NO_RUNTIME_REPRODUCTION' and outcome['runtime_target_databases']=='NOT_CREATED'
assert outcome['functional_processes']==outcome['init_register_PRE_dispatch_UNKNOWN_reconcile_calls']==0
write(OUT/'author-static-record-review.json',{'script_imports':imports,'static_pid':54248,'exit_code':0,'timed_out':False,'alive_at_recorded_completion':False,
 'current_PID_scan':False,'provenance':'Frozen source snapshot, inputs/source-index SHA and historical wait/output records; no author script rerun.',
 'U1_U5':{g:outcome[g] for g in ('U1','U2','U3','U4','U5')},'effect_count':'NOT_OBSERVED','runtime_error_code':'NOT_OBSERVED',
 'transaction_side_effects':'NOT_OBSERVED','no_database_paths_in_added_files':not any(p.endswith(('.sqlite3','.db')) for p in added),
 'author_declared_product_calls':0,'reviewer_product_calls':0,'reviewer_SQL_connections':0})
write(OUT/'static-result.json',{'status':'\u963b\u65ad\u8bc1\u636e\u786e\u8ba4','target':TARGET,'base':BASE,'workflow':WF,
 'frozen_delivery_consistent':True,'class_scoped_UNKNOWN_POST_schema_conflict_confirmed':True,
 'missing_native_fields':missing,'extra_legacy_fields':extra,'functional_calls':0,'SQL_connections':0,
 'U1_U5_functionally_validated':False,'runtime_error_and_transaction_effects':'NOT_OBSERVED','whole_A03':'REWORK','I01_released':False,
 'field_reset':RESET})
print(json.dumps({'status':'STATIC_PREREQUISITE_CONFLICT_CONFIRMED','input_exports':len(exports),'old_entries_preserved':len(before),
 'new_files':len(added),'missing_fields':missing,'extra_fields':extra,'registered_git_children':counter,'product_calls':0,'SQL_connections':0}))
