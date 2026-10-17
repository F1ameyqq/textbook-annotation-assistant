import ast,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
BASE='87606b73e0754fa670491d9fb958a416c26bfe88';WORKFLOW='ef1d2f4a20971b416afae500889aa5c090dfe89b'
def git(*a):return subprocess.check_output(['git','-c','core.longpaths=true',*a],cwd=ROOT)
def save(n,v):
    p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(json.dumps(v,ensure_ascii=False,indent=2).encode('utf8')+b'\n')
assert git('rev-parse','HEAD').decode().strip()==BASE
docs=['AGENTS.md','docs/coordination.md','docs/tasks/A03-P2-R3-evidence-closure-coordinator-decision.md','docs/tasks/A03-P2-R4-bridge-registration-preparation.md','docs/tasks/A03-P2-R2-proposal-review-report.md','docs/tasks/A03-P2-R1-proposal-coordinator-decision.md']
index=[]
for n in docs:
    raw=git('show',WORKFLOW+':'+n);p=OUT/'inputs/documents'/Path(n).name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(raw)
    index.append({'commit':WORKFLOW,'path':n,'copy':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
assert next(x['sha256']for x in index if x['path'].endswith('R4-bridge-registration-preparation.md'))=='fdef54715b78fcf48bcdb65a4cea3aea0e479ebf3cf1251d2455be91b8399dc5'
source_paths=['src/annotation/contracts/__init__.py','src/annotation/contracts/validation.py','src/annotation/contracts/models.py','src/annotation/contracts/recovery.py','src/annotation/contracts/recovery_schema.py','src/annotation/quality/targetcheck/__init__.py','src/annotation/delivery/planner/__init__.py','src/annotation/delivery/mock/persistent.py','src/annotation/runtime/storage/__init__.py','src/annotation/runtime/storage/holds.py','src/annotation/runtime/recovery/observation.py','src/annotation/runtime/recovery/quality.py']
sources=[]
for n in source_paths:
    raw=git('show',BASE+':'+n);p=OUT/'inputs/product-text'/n;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(raw)
    ast.parse(raw.decode('utf8'))
    sources.append({'commit':BASE,'path':n,'copy':p.relative_to(ROOT).as_posix(),'raw_git_blob':git('rev-parse',BASE+':'+n).decode().strip(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'role':'AST_TEXT_ONLY_NEVER_IMPORTED'})
r2=ROOT/'examples/a03/P2-R2-proposal';needed=[ROOT/'examples/a03/P2-R3-evidence-closure/closure.py',ROOT/'docs/evidence/A03/execution/P2-R3-evidence-closure/r2-input-pins.json']
needed += [r2/n for n in('check.py','schema_check.py','oracle_verifier.py')]
needed += [r2/'candidate-final'/n for n in('profile.json','api.json','scope-session.json','converted-initial.json')]
needed += list((r2/'candidate-final/schemas').glob('*.json'))
pins=[]
for p in sorted(needed):
    n=p.relative_to(ROOT).as_posix();raw=git('show',BASE+':'+n);assert p.read_bytes()==raw
    pins.append({'commit':BASE,'path':n,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'raw_git_blob':git('rev-parse',BASE+':'+n).decode().strip(),'role':'FIXED_STATIC_INPUT_REUSED_NOT_COPIED'})
save('input-index.json',{'base':BASE,'workflow':WORKFLOW,'documents':index,'product_text':sources,'reused_inputs':pins,'thinking':'USER_SETTING_PRESERVED_NOT_CHANGED_OR_INFERRED','delegation':False})
old=[]
for n in git('ls-files','-z').split(b'\0'):
    if n:
        name=n.decode('utf8');raw=(ROOT/name).read_bytes();old.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
save('old-baseline.json',{'base':BASE,'files':old})
print(json.dumps({'documents':len(index),'product_source_files_text_only':len(sources),'static_inputs_reused':len(pins),'protected_old_files':len(old)}))
