"""Reproduce bounded frozen author static checks without writing their inputs."""
import json,os,subprocess,sys,hashlib
from pathlib import Path
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P1-R2'
STAGE=ROOT/'.local/stages/A03-review-P1-R2/940a5de33a24b1a3a9ded6e69ade1dd0609ed83a'
def main():
 dest=OUT/'author-reproduction';dest.mkdir()
 pre='docs/evidence/A03/execution/P1-R2/'
 cmds=[('design',['examples/a03/P1-R2/check_design.py','--root','examples/a03/P1-R2/data']),
  ('bindings',[pre+'audit_prefix_bindings.py']),('before-regression',[pre+'check_before_prefix.py']),
  ('mapping',[pre+'audit_mapping_bytes.py']),('profile',[pre+'audit_profile.py']),
  ('resources',[pre+'audit_resource_closure.py','--root','examples/a03/P1-R2/data',
   '--case','cases/unattempted-absence-commit.json','--case','cases/partial-with-complete-absent.json',
   '--case','cases/original-unknown-preserved.json','--case','cases/recovered-report-binding.json'])]
 rows=[]
 for name,args in cmds:
  argv=[sys.executable,'-B',str(STAGE/args[0]),*args[1:]]
  env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(STAGE/'src')}
  p=subprocess.run(argv,cwd=STAGE,env=env,capture_output=True,timeout=60)
  for stream,raw in (('stdout',p.stdout),('stderr',p.stderr)):
   with (dest/(name+'.'+stream+'.log')).open('xb') as f:f.write(raw)
  result=json.loads(p.stdout) if p.returncode==0 else None
  rows.append({'name':name,'argv':argv,'cwd':str(STAGE),'timeout_seconds':60,'exit_code':p.returncode,
   'script_path':str((STAGE/args[0]).resolve()),'script_sha256':hashlib.sha256((STAGE/args[0]).read_bytes()).hexdigest(),
   'PYTHONPATH':env['PYTHONPATH'],'parsed':result})
 with (dest/'results.json').open('x',encoding='utf-8',newline='\n') as f:
  json.dump({'python':sys.version,'executable':sys.executable,'commands':rows,'business_execution':False,
   'fixture_generator_main_executed':False,'checker_imports_guarded_static_helpers':True,
   'all_sync_commands_exited':True,'remaining_owned_background_processes':0},f,ensure_ascii=False,indent=2);f.write('\n')
 assert all(x['exit_code']==0 for x in rows)
 print(json.dumps({'checks':len(rows),'exit_codes':[x['exit_code'] for x in rows],'runtime_actual':'NOT_EXECUTED'}))
if __name__=='__main__':main()
