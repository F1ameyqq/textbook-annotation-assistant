"""Preserve only formal portable R2 inputs and relevant historical failure bytes."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P1-R2'
STAGE=ROOT/'.local/stages/A03-review-P1-R2/940a5de33a24b1a3a9ded6e69ade1dd0609ed83a'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 package=STAGE/'examples/a03/P1-R2';dest=OUT/'inputs/package';assert not dest.exists()
 picks=[p for p in (package/'data').rglob('*') if p.is_file()]
 picks += [package/n for n in ('README.md','api-proposal.json','check_design.py','prefix_rules.py','build_r2_fixtures.py','event-prefix.schema.json')]
 rows=[]
 for p in picks:
  name=p.relative_to(package).as_posix();b=p.read_bytes();target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(b)
  rows.append({'path':'inputs/package/'+name,'bytes':len(b),'sha256':sha(b)})
 for name in ('docs/a03-recovery-contract-v1-r2-proposal.md','docs/tasks/A03-P1-R2-execution-report.md'):
  b=(STAGE/name).read_bytes();target=OUT/'inputs'/Path(name).name
  with target.open('xb') as f:f.write(b)
  rows.append({'path':target.relative_to(OUT).as_posix(),'bytes':len(b),'sha256':sha(b)})
 # Keep denial/failure/CRLF logs and affected scripts, not intermediate data snapshots.
 evidence=[]
 for p in STAGE.rglob('*'):
  n=p.relative_to(STAGE).as_posix()
  if not p.is_file() or 'P1-R2/' not in n:continue
  if ('/attempts/' in n and '/data/' not in n) or (n.startswith('docs/evidence/A03/execution/P1-R2/final-static/') and ('diff-check' in n or 'diff-check-results' in n)):
   evidence.append(p)
 for p in evidence:
  n=p.relative_to(STAGE).as_posix();b=p.read_bytes();target=OUT/'inputs/author-history'/n;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(b)
  rows.append({'path':target.relative_to(OUT).as_posix(),'bytes':len(b),'sha256':sha(b)})
 argv=[sys.executable,'-B','check_design.py','--root','data'];env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'};env.pop('PYTHONPATH',None)
 result=subprocess.run(argv,cwd=dest,env=env,capture_output=True,timeout=60)
 for stream,b in (('stdout',result.stdout),('stderr',result.stderr)):
  with (OUT/('portable.'+stream+'.log')).open('xb') as f:f.write(b)
 parsed=json.loads(result.stdout) if result.returncode==0 else None
 with (OUT/'portable-check.json').open('x',encoding='utf-8',newline='\n') as f:
  json.dump({'input_files':rows,'formal_package_files':len(picks),'history_files_selected':len(evidence),
   'selection':'formal data and checker/helpers/profile; only failure/denial/CRLF logs and scripts from author history',
   'argv':argv,'cwd':str(dest),'timeout_seconds':60,'exit_code':result.returncode,'PYTHONPATH':'REMOVED',
   'parsed':parsed,'generator_main_executed':False,'runtime_or_recovery_executed':False},f,ensure_ascii=False,indent=2);f.write('\n')
 assert result.returncode==0 and parsed['case_count']==72
 print(json.dumps({'portable_exit_code':0,'formal_package_files':len(picks),'author_history_files':len(evidence),'cases':72}))
if __name__=='__main__':main()
