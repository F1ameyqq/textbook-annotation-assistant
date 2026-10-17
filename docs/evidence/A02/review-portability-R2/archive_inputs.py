"""Archive only necessary exact code and small author failure logs, never historical bulk."""
import hashlib
import json
from pathlib import Path
import subprocess

OUT=Path(__file__).resolve().parent
REPO=Path('C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800')
COMMIT='a1e5be00909172429d792b6c41bdaf384258694e';BASE='38aca9dcc8d027409b95193e9cc142c2336b76d3'
selected=[
 (BASE,'examples/a02/R1/identity.py','inputs/base-identity.py'),
 (COMMIT,'examples/a02/R1/identity.py','inputs/candidate-identity.py'),
 (COMMIT,'tests/test_a02_r1.py','inputs/test_a02_r1.py'),
 (COMMIT,'tests/test_a02_portability_r2.py','inputs/test_a02_portability_r2.py'),
 (COMMIT,'docs/evidence/A02/execution/portability-R2/before-frozen-runner/raw-noGit-identity.stderr.txt','retained-author/base-identity-noGit.stderr.txt'),
 (COMMIT,'docs/evidence/A02/execution/portability-R2/before-frozen-runner/original-identity-test-noGit.stderr.txt','retained-author/base-original-noGit.stderr.txt'),
 (COMMIT,'docs/evidence/A02/execution/portability-R2/delivery-audit-first-attempt.json','retained-author/encoding-error.json'),
 (COMMIT,'docs/evidence/A02/execution/portability-R2/before-frozen-runner/results.json','retained-author/before-results.json')]
entries=[]
for commit,path,target in selected:
    raw=subprocess.check_output(['git','-C',str(REPO),'show',commit+':'+path])
    dest=OUT/target;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as handle:handle.write(raw)
    entries.append({'commit':commit,'source_path':path,'archived_path':target,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
(OUT/'input-provenance.json').write_text(json.dumps({'files':entries,'purpose':'Small fixed code inputs and original author failures; all bytes exactly match specified Git blobs.'},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exact_inputs_archived':len(entries)}))
