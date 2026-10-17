"""Copy exact newly delivered P1-R1 files and run the standalone static checker."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
ROOT=Path('D:/1800')
COMMIT='ca4fba4f505467228a8164c3999e0cecc54ffc4e'
BASE='2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9'
STAGE=ROOT/'.local/stages/A03-review-P1-R1'/COMMIT
OUT=ROOT/'docs/evidence/A03/review/P1-R1'
def main():
 dest=OUT/'inputs/frozen-R1';assert not dest.exists()
 p=subprocess.run(['git','diff','--diff-filter=A','--name-only',BASE,COMMIT],cwd=ROOT,capture_output=True,timeout=30)
 assert p.returncode==0;paths=p.stdout.decode().splitlines();assert len(paths)==781
 copied=[]
 for name in paths:
  raw=(STAGE/name).read_bytes();target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(raw)
  assert target.read_bytes()==raw
  copied.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
 cwd=dest/'examples/a03/P1-R1'
 argv=[sys.executable,'-B','check_design.py','--root','data']
 env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'};env.pop('PYTHONPATH',None)
 p=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=60)
 for name,raw in (('stdout',p.stdout),('stderr',p.stderr)):
  with (OUT/('portable-static.'+name+'.log')).open('xb') as f:f.write(raw)
 data=json.loads(p.stdout) if p.returncode==0 else None
 with (OUT/'portable-check.json').open('x',encoding='utf-8',newline='\n') as f:
  json.dump({'copied_files':copied,'argv':argv,'cwd':str(cwd),'timeout_seconds':60,
   'returncode':p.returncode,'PYTHONPATH':'REMOVED','static_result':data,
   'business_imports_or_recovery_execution':False},f,ensure_ascii=False,indent=2);f.write('\n')
 assert p.returncode==0 and data['case_count']==69
 print(json.dumps({'frozen_R1_files_copied':781,'portable_static_exit_code':p.returncode,'static_cases':69}))
if __name__=='__main__':main()
