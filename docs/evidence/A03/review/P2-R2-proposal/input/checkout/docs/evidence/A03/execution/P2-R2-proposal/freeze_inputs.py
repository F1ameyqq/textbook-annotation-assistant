import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
BASE='7fdbde8f16569fd3bc399013115e13269d5d33fa'
WORKFLOW='d834bf531f95abac7ed30b89b3ca55105fa6f491'
def git(*args): return subprocess.check_output(['git','-c','core.longpaths=true',*args],cwd=ROOT)
def save(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2).encode('utf8')+b'\n')
assert git('rev-parse','HEAD').decode().strip()==BASE
sources=[(WORKFLOW,p) for p in ['AGENTS.md','docs/coordination.md','docs/architecture.md','docs/contracts-v1.md',
 'docs/tasks/A03-P2-R2-static-rework.md','docs/tasks/A03-P2-R1-proposal-coordinator-decision.md','docs/tasks/A03-P2-R1-proposal-review-report.md',
 'docs/evidence/A03/review/P2-R1-proposal/diagnostics/readonly-session-does-not-match-gate-binding.json',
 'docs/evidence/A03/review/P2-R1-proposal/diagnostics/initial-head-not-in-canonical-prefix.json',
 'docs/evidence/A03/review/P2-R1-proposal/diagnostics/amended-source-kind-coverage.json',
 'docs/evidence/A03/review/P2-R1-proposal/base-profile-adoption-analysis.json']]
sources += [(BASE,p) for p in ['examples/a03/P1-R2/data/cases/intent-no-receipt-match.json',
 'examples/a03/P2-R1-proposal/candidate-v2/schemas/exchange-v2.schema.json',
 'examples/a03/P2-R1-proposal/candidate-v2/schemas/action-fact-v2.schema.json',
 'src/annotation/delivery/planner/__init__.py']]
index=[]
for commit,name in sources:
    raw=git('show',commit+':'+name); dest=OUT/'inputs'/Path(name).name
    assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    index.append({'commit':commit,'path':name,'copy':dest.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
save('input-index.json',{'base':BASE,'workflow':WORKFLOW,'inputs':index,'encoding_note':'initial Python console used host codec; corrected -X utf8; exact inputs are raw Git bytes',
 'authority':'ONE_BOUNDED_STATIC_REWORK_ONLY','reasoning_requested':'xhigh','field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
old=[]
for name in git('ls-files','-z').split(b'\0'):
    if name:
        p=name.decode('utf8');raw=(ROOT/p).read_bytes();old.append({'path':p,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
save('old-baseline.json',{'base':BASE,'files':old})
print(json.dumps({'frozen_inputs':len(index),'protected_old_files':len(old)}))
