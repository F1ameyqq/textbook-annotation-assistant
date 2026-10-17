"""Freeze minimal exact inputs; do not import a checker/product."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R6-mixed-control';sys.path.insert(0,str(EX))
from files import BASE,WORKFLOW,DATA,OLD_CASE,OUT,git,isres,load,old_inventory,raw_write,sha,write
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('diff','--name-only',BASE).strip()
pins={}
def pin(commit,name,copy=False):
    if(commit,name)in pins:return
    raw=git('show',commit+':'+name)
    if commit==BASE:assert raw==(ROOT/name).read_bytes(),name
    row={'commit':commit,'path':name,'bytes':len(raw),'sha256':sha(raw),'git_blob':git('rev-parse',commit+':'+name).decode().strip()}
    if copy:
        p=OUT/'inputs/workflow'/name;raw_write(p,raw);row['copy']=p.relative_to(ROOT).as_posix()
    pins[(commit,name)]=row
docs=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md','docs/tasks/A03-P2-R6-mixed-control-rework.md','docs/tasks/A03-P2-R5-registration-context-coordinator-decision.md','docs/tasks/A03-P2-R5-registration-context-review-report.md','docs/evidence/coordinator/heartbeat-20261017-1059/A03-R5-review-check.json','docs/evidence/A03/review/P2-R5-registration-context/sha256-manifest.json']
for n in docs:pin(WORKFLOW,n,True)
assert pins[(WORKFLOW,docs[4])]['sha256']=='97211bd4dd86097ae2ed08c19f38f208c4a790432fe42875bb0d7901fff1f0cd'
assert pins[(WORKFLOW,docs[6])]['sha256']=='f4831a2f8274f3cad718b440b0bd647ccd726ba997dafb5e0089028d2fb5ab5f'
assert pins[(WORKFLOW,docs[8])]['sha256']=='bff7b99b110f8c104317357460a41b05de72ec73f997d3c6c7dd19f65e60f496'
fixed=['examples/a03/P2-R5-registration-context/'+n for n in('registration.py','load_static.py','common.py','repair-case-index.json')]
fixed+=['examples/a03/P2-R3-evidence-closure/closure.py','docs/evidence/A03/execution/P2-R3-evidence-closure/r2-input-pins.json']
fixed+=['examples/a03/P2-R2-proposal/'+n for n in('check.py','schema_check.py','oracle_verifier.py','candidate-final/api.json','candidate-final/profile.json')]
fixed+=[p.relative_to(ROOT).as_posix()for p in(DATA/'schemas').glob('*.json')]
for n in fixed:pin(BASE,n)
assert pins[(BASE,fixed[0])]['sha256']=='3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba'
assert pins[(BASE,fixed[1])]['sha256']=='734b8760b58f7778f4bd32608b77fc87f95a31c027ce457408d5fbdcf8166098'
pin(BASE,OLD_CASE);case=load(ROOT/OLD_CASE);pin(BASE,case['bundle'])
assert case['bundle_sha256']=='f2f5e5a032271d7890165d49e4c336dbcb5f628bbf18e372e0d7148a54535d67'
over={}
for r in case['resources']:pin(BASE,r['file']);over[r['logical']]=(ROOT/r['file']).read_bytes();assert sha(over[r['logical']])==r['raw_sha256']
seen=set()
def resources(v):
    if isres(v):
        token=(v['path'],v['sha256'])
        if token in seen:return
        seen.add(token)
        if v['path']in over:raw=over[v['path']]
        else:
            p=DATA/v['path'];assert p.resolve().is_relative_to(DATA.resolve());pin(BASE,p.relative_to(ROOT).as_posix());raw=p.read_bytes()
        assert sha(raw)==v['sha256']
        if v['media_type']=='application/json':resources(json.loads(raw))
    elif isinstance(v,dict):
        for x in v.values():resources(x)
    elif isinstance(v,list):
        for x in v:resources(x)
resources(load(ROOT/case['bundle']))
write(OUT/'old-preservation-before.json',old_inventory())
write(OUT/'raw-input-pins.json',{'base':BASE,'workflow':WORKFLOW,'inputs':list(pins.values()),'unique_candidate_source':OLD_CASE,'product_imports':0,'Package_calls':0,'thinking':'CURRENT_USER_SETTING_PRESERVED_NOT_INFERRED','delegation':False,'no_old_preservation_list_or_product_source_copied':True})
print(json.dumps({'status':'MINIMAL_RAW_INPUTS_FROZEN','pins':len(pins),'Package_calls':0}))
