"""Post-run byte preservation, exact-source and diff-format checks."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parent
REPO=Path('C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800')
COMMIT='38aca9dcc8d027409b95193e9cc142c2336b76d3';BASE='5c9285720c8628c5198bedeadfc9f6bc7826a914'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
export=load(OUT/'frozen-export.json');source=Path(export['source_root'])
source_mismatches=[f['path'] for f in export['files'] if sha(source/f['path'])!=f['sha256']]
old=load(OUT/'old-review-preservation.json')['files_sha256']
old_mismatches=[p for p,h in old.items() if sha(ROOT/p)!=h]
assert not source_mismatches and not old_mismatches
format_results=[]
for name,paths in [('all-delivery',[]),('source-tests-examples',['src','tests','examples']),('all-except-raw-failure',['.',':(exclude)docs/evidence/A02/execution/R1/before/r1-regression.stderr.txt'])]:
    argv=['git','-C',str(REPO),'diff','--check',BASE,COMMIT]+(['--']+paths if paths else [])
    result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (OUT/(name+'-diff-check.stdout.txt')).write_bytes(result.stdout);(OUT/(name+'-diff-check.stderr.txt')).write_bytes(result.stderr)
    format_results.append({'name':name,'argv':argv,'exit_code':result.returncode,'stdout':name+'-diff-check.stdout.txt','stderr':name+'-diff-check.stderr.txt'})
assert format_results[1]['exit_code']==0 and format_results[2]['exit_code']==0
result={'target_commit':COMMIT,'source_files_reverified':len(export['files']),'source_mismatches':source_mismatches,
    'old_review_files_preserved':len(old),'old_review_mismatches':old_mismatches,'old_delivery_files_preserved':len(export['old_delivery_artifacts']),
    'format_checks':format_results,'format_note':'Complete diff check preserves one raw failed-unittest stderr trailing-space finding; source/tests/examples and all other paths pass.',
    'source_worktree_head':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD']).decode().strip(),
    'source_worktree_status':subprocess.check_output(['git','-C',str(REPO),'status','--short']).decode().splitlines()}
assert result['source_worktree_head']==COMMIT and not result['source_worktree_status']
save(OUT/'post-run-integrity.json',result)
print(json.dumps({'sources':len(export['files']),'old_review_files':len(old),'diff_exit_codes':[r['exit_code'] for r in format_results],'source_worktree_clean':True}))
