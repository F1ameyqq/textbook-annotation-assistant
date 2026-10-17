# -*- coding: utf-8 -*-
"""Static source/schema/log reconciliation only; no candidate evaluation or imports."""
import difflib
import hashlib
import json
import subprocess
from evidence import OUT,ROOT,TARGET,EV,BY_PATH,document,raw,text,sha,write

groups=('C01','A02','R7','N1-initial','N1-local-fix')
indexes={g:{r['path']:r for r in document(EV+'runs/'+g+'/product-source-index.json')} for g in groups}
changes=[]
for path in sorted(set(indexes['N1-initial'])|set(indexes['N1-local-fix'])):
    a=indexes['N1-initial'].get(path);b=indexes['N1-local-fix'].get(path)
    if a!=b:changes.append({'path':path,'before':a,'after':b})
assert {r['path'] for r in changes}=={'src/annotation/contracts/recovery.py',
 'src/annotation/contracts/a03_native/data/profile.json','src/annotation/contracts/a03_native/data/adoption.json'}
specs=[TARGET+':'+EV+'runs/'+g+'/product-snapshot/src/annotation/contracts/recovery.py' for g in groups]
profile=document('src/annotation/contracts/a03_native/data/profile.json')
def implementation_path(path):
    return 'src/'+path[1:] if path.startswith('@') else 'src/annotation/contracts/a03_native/'+path
missing=[(implementation_path(p),digest) for p,digest in profile['implementation_pins'] if implementation_path(p) not in BY_PATH]
specs += [TARGET+':'+p for p,_ in missing]
argv=['git','-c','core.longpaths=true','cat-file','--batch']
body=subprocess.run(argv,cwd=ROOT,input=('\n'.join(specs)+'\n').encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
pos=0;supp=[];recovery={}
delivery=json.loads((OUT/'delivery-byte-index.json').read_bytes())
delmap={r['path']:r for r in delivery['files']}
for i,spec in enumerate(specs):
    end=body.index(b'\n',pos);head=body[pos:end].decode().split();pos=end+1
    assert len(head)==3 and head[1]=='blob';n=int(head[2]);value=body[pos:pos+n];pos+=n
    assert body[pos:pos+1]==b'\n';pos+=1
    assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+value).hexdigest()==head[0]
    path=spec.split(':',1)[1]
    if i<len(groups):
        group=groups[i]
        assert sha(value)==delmap[path]['sha256']
        assert sha(value)==indexes[group]['src/annotation/contracts/recovery.py']['sha256']
        relative='input/supplement/'+group+'-recovery.py'
        recovery[group]=value.decode('utf8')
    else:
        source,digest=missing[i-len(groups)]
        assert source==path and sha(value)==digest
        assert indexes['N1-local-fix'][source]['sha256']==digest
        relative='input/supplement/'+path.replace('/','__')
    dest=OUT/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(value)
    supp.append({'commit':TARGET,'path':path,'file':relative,'bytes':n,'sha256':sha(value),'raw_git_sha1':head[0]})
    BY_PATH[path]=supp[-1]
assert pos==len(body)
write(OUT/'supplemental-input-index.json',{'role':'five recovery snapshots for the sole fix and unchanged runtime source pinned by native profile','files':supp,'git_argv':argv})
assert all(recovery[g]==recovery['N1-initial'] for g in ('C01','A02','R7'))
final_recovery=text('src/annotation/contracts/recovery.py')
assert recovery['N1-local-fix']==final_recovery
diff=list(difflib.unified_diff(recovery['N1-initial'].splitlines(),final_recovery.splitlines(),fromfile='N1-initial/recovery.py',tofile='N1-local-fix/recovery.py',lineterm=''))
assert len([v for v in diff if v.startswith('+') and not v.startswith('+++')])==8
assert not [v for v in diff if v.startswith('-') and not v.startswith('---')]
producer=text('src/annotation/quality/synthetic_precheck.py')
targetcheck=text('src/annotation/quality/targetcheck/__init__.py')
native=text('src/annotation/contracts/a03_native/__init__.py')
assert "'coverage': coverage_for(bundle, graph)" in producer
assert 'return coverage, complete' in targetcheck
assert 'json.loads(canonical(' in native and "NativeSchemas().check(value, definition=value.get('kind'))" in native
schema=document('src/annotation/contracts/a03_native/data/schemas/exchange.json')
branches=schema['$defs']['AmendedCheckReport']['properties']['payload']['oneOf']
pre=next(r for r in branches if r['properties']['stage'].get('const')=='PRE_APPLY')
assert pre['properties']['coverage']=={'$ref':'#/$defs/Coverage'}
assert schema['$defs']['Coverage']['type']=='object' and 'coverage' in pre['required']
assert all(r['properties']['stage']['const']!='PRE_APPLY' for r in branches if r is not pre)
for g in groups:
    assert indexes[g]['src/annotation/quality/synthetic_precheck.py']['sha256']==sha(producer.encode())
    assert indexes[g]['src/annotation/quality/targetcheck/__init__.py']['sha256']==sha(targetcheck.encode())
logs={g:{kind:text(EV+'runs/'+g+'/'+kind+'.txt') for kind in ('stdout','stderr')} for g in ('N1-initial','N1-local-fix')}
child_logs={label:text(EV+'validation/'+label+'/processes/n1-child/stderr.txt') for label in ('bounded-01','bounded-02')}
assert 'HASH_MISMATCH' in child_logs['bounded-01'] and 'SHAPE_oneOf' not in child_logs['bounded-01']
assert 'SHAPE_oneOf' in child_logs['bounded-02'] and 'HASH_MISMATCH' not in child_logs['bounded-02']
assert 'produce_a03_pre_run' in child_logs['bounded-02'] and 'seal_native_artifact' in child_logs['bounded-02']
assert '$/payload: [SHAPE_oneOf]' in child_logs['bounded-02']
assert all(child_logs[label].strip() in logs[group]['stderr'] for label,group in (('bounded-01','N1-initial'),('bounded-02','N1-local-fix')))
pins=[]
for path,digest in profile['schema_pins']:
    actual=sha(raw('src/annotation/contracts/a03_native/data/'+path));assert actual==digest;pins.append({'path':path,'sha256':actual})
for path,digest in profile['implementation_pins']:
    source=implementation_path(path)
    assert sha(raw(source))==digest,source
scope=document(EV+'bounded-outcome.json')
assert all(scope['N'+str(n)]=='NOT_RUN_AFTER_INDEPENDENT_BLOCKER' for n in range(2,8))
all_paths={r['path'] for r in delivery['files']}
assert not [p for p in all_paths if p.startswith(EV+'validation/') and '/cases/N' in p and '/cases/N1/' not in p]
assert not [p for p in all_paths if p.endswith(('effect-committed.barrier.json','before-dispatch.json','release.barrier'))]
result={'status':'REWORK_CONFIRMED_BY_STATIC_SOURCE_SCHEMA_AND_ACTUAL_LOGS','target':TARGET,
 'defect':{'id':'R8-N1-COVERAGE-PAIR','producer_line':next(i for i,l in enumerate(producer.splitlines(),1) if "'coverage': coverage_for" in l),
 'return_line':next(i for i,l in enumerate(targetcheck.splitlines(),1) if 'return coverage, complete' in l),
 'schema_pointer':'/$defs/AmendedCheckReport/properties/payload/oneOf/0/properties/coverage',
 'required_type':'object','inferred_actual_after_canonical_json':'two-element array [coverage object,complete bool]',
 'actual_error':'$/payload: SHAPE_oneOf','positive_native_reruns_by_reviewer':0},
 'first_failure':{'code':'HASH_MISMATCH','boundary':'private C01 semantic projection before registration',
 'initial_child_stderr_sha256':sha(child_logs['bounded-01'].encode())},
 'sole_local_fix':{'source_delta':changes,'recovery_unified_diff':diff,
 'classification':'eight native-guarded normalization lines plus regenerated profile/adoption pins; no producer or test fix',
 'first_three_compatibility_recovery_snapshots_equal_initial':True,'final_recovery_equals_second_snapshot':True},
 'second_failure':{'code':'SHAPE_oneOf','boundary':'PRE make_artifact/seal before admission and TARGET',
 'second_child_stderr_sha256':sha(child_logs['bounded-02'].encode())},
 'profile_schema_pins_verified':pins,'profile_implementation_pins_verified':len(profile['implementation_pins']),
 'N2_N7':'NOT_RUN_AFTER_INDEPENDENT_BLOCKER','no_dispatch_or_effect_barrier_files_in_frozen_tree':True,
 'candidate_modules_imported_or_executed':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'static-review.json',result)
print(json.dumps({'status':result['status'],'producer_line':result['defect']['producer_line'],
 'return_line':result['defect']['return_line'],'changed_source_paths':[r['path'] for r in changes],
 'schema_pins':len(pins),'implementation_pins':len(profile['implementation_pins'])}))
