"""Bind exact workflow, sources, seven cases, fallback bytes and C01 inputs."""
import importlib.metadata,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R7-readonly-codec';sys.path.insert(0,str(EX))
from ops import BASE,WORKFLOW,DATA,OUT,git,load,preservation,raw_git_batch,raw_write,sha,write
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('diff','--name-only',BASE).strip()
task='docs/tasks/A03-P2-R7-readonly-codec-implementation.md';meta='docs/evidence/coordinator/heartbeat-20261017-1144/R7-input-pins.json'
task_raw=git('show',WORKFLOW+':'+task);meta_raw=git('show',WORKFLOW+':'+meta)
assert sha(task_raw)=='fc32fe579d2131cb38a9682b6497060cc3469b604507a9dde9bb145919d7766c'and sha(meta_raw)=='4ba6e0a646f403f552d71c091b62d0a53623f5ea90728ffea7dd2bab8ec172b1'
spec=json.loads(meta_raw);assert spec['base_commit']==BASE
docs=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md',task,meta,'docs/tasks/A03-P2-R6-mixed-control-coordinator-decision.md']
keys={(WORKFLOW,n)for n in docs};keys|={(BASE,row['path'])for row in spec['inputs']}
cases=[]
for source in spec['cases']:
    p=ROOT/source['case'];raw=p.read_bytes();assert sha(raw)==source['case_sha256'];case=json.loads(raw);bundle_raw=(ROOT/case['bundle']).read_bytes();assert sha(bundle_raw)==case['bundle_sha256']
    keys.add((BASE,case['bundle']));over={}
    for r in case['resources']:
        keys.add((BASE,r['file']));body=(ROOT/r['file']).read_bytes();assert sha(body)==r['raw_sha256'];over[r['logical']]=body
    seen=set();mismatches=[]
    def collect(v):
        if isinstance(v,dict)and{'path','sha256','media_type'}<=set(v):
            token=(v['path'],v['sha256'])
            if token in seen:return
            seen.add(token)
            if v['path']in over:body=over[v['path']]
            else:
                p=DATA/v['path'];assert p.resolve().is_relative_to(DATA.resolve());keys.add((BASE,p.relative_to(ROOT).as_posix()));body=p.read_bytes()
            if sha(body)!=v['sha256']:mismatches.append({'path':v['path'],'declared':v['sha256'],'actual':sha(body)})
            if v['media_type']=='application/json':collect(json.loads(body))
        elif isinstance(v,dict):
            for x in v.values():collect(x)
        elif isinstance(v,list):
            for x in v:collect(x)
    collect(json.loads(bundle_raw));assert len(mismatches)==(1 if source['id']=='global-resource-hash-corruption'else 0)
    cases.append(dict(source,resource_count=len(seen),intentional_digest_mismatches=mismatches))
for name in git('ls-files','src/annotation','tests/test_contracts.py','tests/test_contracts_platform_refs.py','tests/fixtures/contracts').decode().splitlines():keys.add((BASE,name))
keys=sorted(keys);raw_inputs=raw_git_batch(keys);pins=[]
for commit,name in keys:
    blob,raw=raw_inputs[(commit,name)];row={'commit':commit,'path':name,'git_blob':blob,'bytes':len(raw),'sha256':sha(raw)}
    if commit==BASE:
        checkout=(ROOT/name).read_bytes();row['checkout_sha256']=sha(checkout);row['checkout_bytes']=len(checkout)
        if checkout!=raw:
            assert raw.replace(b'\r\n',b'\n')==checkout.replace(b'\r\n',b'\n'),name
            row['checkout_transform']='NEWLINE_ONLY_GIT_TEXT_CONVERSION'
    else:
        p=OUT/'inputs/workflow'/name
        if p.exists():assert p.read_bytes()==raw
        else:raw_write(p,raw)
        row['copy']=p.relative_to(ROOT).as_posix()
    pins.append(row)
for row in spec['inputs']:
    raw=raw_inputs[(BASE,row['path'])][1];assert len(raw)==row['bytes']and sha(raw)==row['sha256']
write(OUT/'raw-input-pins.json',{'base':BASE,'workflow':WORKFLOW,'inputs':pins,'cases':cases,'default_contracts_sha256':sha((ROOT/'src/annotation/contracts/__init__.py').read_bytes()),'thinking':'CURRENT_USER_MODEL_AND_SETTING_PRESERVED','delegation':False})
write(OUT/'old-preservation-before.json',preservation())
versions={}
for name in('setuptools','wheel','pydantic'):
    try:versions[name]=importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:versions[name]=None
write(OUT/'local-build-tools.json',{'python':sys.executable,'version':sys.version,'versions':versions,'build_module':importlib.util.find_spec('build')is not None,'offline_backend':'setuptools.build_meta','installed_or_downloaded':False})
print(json.dumps({'status':'RAW_INPUTS_FROZEN','pins':len(pins),'fixed_cases':len(cases),'intentional_bad_resource_cases':sum(bool(r['intentional_digest_mismatches'])for r in cases)}))
