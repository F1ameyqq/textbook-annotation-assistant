"""Run only reviewed P1-R1 stdlib static scripts with bounded timeouts."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path('D:/1800')
STAGE=ROOT/'.local/stages/A03-review-P1-R1/ca4fba4f505467228a8164c3999e0cecc54ffc4e'
OUT=ROOT/'docs/evidence/A03/review/P1-R1/author-reproduction'
def main():
 OUT.mkdir(parents=True,exist_ok=False)
 commands=[]
 for name,args in (
  ('check-design',['examples/a03/P1-R1/check_design.py','--root','examples/a03/P1-R1/data']),
  ('check-r1-design',['docs/evidence/A03/execution/P1-R1/check_r1_design.py'])):
  argv=[sys.executable,'-B',str(STAGE/args[0]),*args[1:]]
  env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(STAGE/'src')}
  p=subprocess.run(argv,cwd=STAGE,env=env,capture_output=True,timeout=60)
  for stream,raw in (('stdout',p.stdout),('stderr',p.stderr)):
   with (OUT/(name+'.'+stream+'.log')).open('xb') as f:f.write(raw)
  result=json.loads(p.stdout) if p.returncode==0 else None
  commands.append({'argv':argv,'cwd':str(STAGE),'timeout_seconds':60,'returncode':p.returncode,
    'PYTHONPATH':env['PYTHONPATH'],'script_resolved_path':str((STAGE/args[0]).resolve()),
    'script_sha256':hashlib.sha256((STAGE/args[0]).read_bytes()).hexdigest(),'parsed':result})
 with (OUT/'results.json').open('x',encoding='utf-8',newline='\n') as f:
  json.dump({'python':sys.version,'executable':sys.executable,'commands':commands,
    'business_imports':0,'recovery_or_database_or_effect_execution':False,
    'all_commands_exited':True,'remaining_owned_background_processes':0},f,ensure_ascii=False,indent=2);f.write('\n')
 assert all(c['returncode']==0 for c in commands)
 assert commands[0]['parsed']['case_count']==69
 assert all(c['semantic_actual']=='NOT_EXECUTED' for c in commands[0]['parsed']['cases'])
 print(json.dumps({'exit_codes':[c['returncode'] for c in commands],'cases':69,'semantic_actual':'ALL_NOT_EXECUTED'}))
if __name__=='__main__':main()
