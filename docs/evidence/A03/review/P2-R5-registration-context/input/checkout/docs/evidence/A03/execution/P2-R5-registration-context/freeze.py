"""Freeze exact raw Git inputs and metadata; do not load any checker."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R5-registration-context';sys.path.insert(0,str(EX))
from common import BASE,WORKFLOW,OUT,git,h,isres,load,raw_write,sha,write
assert git('rev-parse','HEAD').decode().strip()==BASE
assert not git('diff','--name-only',BASE).strip()
docs=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md','docs/tasks/A03-P2-R5-registration-context-rework.md','docs/tasks/A03-P2-R4-bridge-registration-coordinator-decision.md','docs/tasks/A03-P2-R4-bridge-registration-review-report.md','docs/evidence/coordinator/heartbeat-20261017-1014/A03-R4-review-check.json','docs/evidence/A03/review/P2-R4-bridge-registration/sha256-manifest.json']
inputs={}
def pin(commit,name,copy=None):
    key=(commit,name)
    if key in inputs:return
    raw=git('show',commit+':'+name)
    if commit==BASE:assert (ROOT/name).read_bytes()==raw,name
    row={'commit':commit,'path':name,'bytes':len(raw),'sha256':sha(raw),'git_blob':git('rev-parse',commit+':'+name).decode().strip(),'role':'FIXED_READ_ONLY_INPUT'}
    if copy:
        raw_write(OUT/copy,raw);row['copy']=(OUT/copy).relative_to(ROOT).as_posix()
    inputs[key]=row;return raw
for n in docs:pin(WORKFLOW,n,'inputs/workflow/'+n)
assert inputs[(WORKFLOW,docs[4])]['sha256']=='64026a73b55c904090544b92c3202208d68189c1c98953affc034b87d716bc69'
assert inputs[(WORKFLOW,docs[6])]['sha256']=='46d2d7aa43eb5a055827ecbacfe9db67ab959575098e52378a1fe9bfa1574049'
assert inputs[(WORKFLOW,docs[8])]['sha256']=='311f1fb987c111b21a92ddb7ea00ec36938f6d45be1b1d56dc64a13f59f555ac'
fixed=['examples/a03/P2-R3-evidence-closure/closure.py','docs/evidence/A03/execution/P2-R3-evidence-closure/r2-input-pins.json']
fixed+=['examples/a03/P2-R2-proposal/'+n for n in('check.py','schema_check.py','oracle_verifier.py','candidate-final/profile.json','candidate-final/api.json')]
fixed+=[p.relative_to(ROOT).as_posix()for p in(ROOT/'examples/a03/P2-R2-proposal/candidate-final/schemas').glob('*.json')]
for n in fixed:pin(BASE,n)
r4=ROOT/'examples/a03/P2-R4-bridge-registration'
for p in sorted((r4/'cases').rglob('*')):
    if p.is_file():pin(BASE,p.relative_to(ROOT).as_posix())
for p in sorted((r4/'shared').iterdir()):pin(BASE,p.relative_to(ROOT).as_posix())
old=ROOT/'docs/evidence/A03/execution/P2-R3-evidence-closure/inputs/counterexample'
for p in sorted(old.iterdir()):
    if p.is_file():pin(BASE,p.relative_to(ROOT).as_posix())
bundle=load(old/'bundle.json');spec=load(old/'result.json');over={r['logical']:(old/Path(r['file']).name).read_bytes()for r in spec['resource_overrides']}
seen=set()
def resources(v):
    if isres(v):
        key=(v['path'],v['sha256'])
        if key in seen:return
        seen.add(key)
        if v['path']in over:raw=over[v['path']]
        else:
            n='examples/a03/P2-R2-proposal/candidate-final/'+v['path'];pin(BASE,n);raw=(ROOT/n).read_bytes()
        assert sha(raw)==v['sha256']
        if v['media_type']=='application/json':resources(json.loads(raw))
    elif isinstance(v,dict):
        for x in v.values():resources(x)
    elif isinstance(v,list):
        for x in v:resources(x)
resources(bundle)
tree=git('ls-tree','-r','-z',BASE);raw_write(OUT/'old-tree.raw',tree);records=[]
for token in tree.split(b'\0'):
    if not token:continue
    header,name=token.split(b'\t',1);mode,kind,oid=header.decode().split();name=name.decode('utf8');p=ROOT/name;raw=p.read_bytes()
    records.append({'path':name,'mode':mode,'type':kind,'blob':oid,'bytes':len(raw),'checkout_sha256':sha(raw),'symlink':p.is_symlink()})
raw_write(OUT/'old-preservation.jsonl',b''.join(json.dumps(r,ensure_ascii=False,separators=(',',':')).encode('utf8')+b'\n'for r in records))
write(OUT/'input-index.json',{'base':BASE,'workflow':WORKFLOW,'inputs':list(inputs.values()),'old_paths':len(records),'old_tree_sha256':sha(tree),'thinking':'CURRENT_USER_SETTING_PRESERVED_NOT_INFERRED','delegation':False,'product_imports':0})
print(json.dumps({'status':'RAW_INPUTS_FROZEN','input_pins':len(inputs),'old_paths':len(records),'checker_calls':0}))
