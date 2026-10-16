"""Capture R1 author reproduction on independently exported exact final source."""
import json
import os
import subprocess
import sys
from pathlib import Path

OUT=Path(__file__).resolve().parent
SOURCE=OUT/'source-38aca9dc'
temp=OUT/'tmp'
temp.mkdir(exist_ok=False)
env=dict(os.environ,PYTHONPATH=str(SOURCE/'src'),PYTHONDONTWRITEBYTECODE='1',TEMP=str(temp),TMP=str(temp))
argv=[sys.executable,'-B',str(SOURCE/'examples/a02/R1/verify.py'),'--source-root',str(SOURCE),
      '--source-commit','38aca9dcc8d027409b95193e9cc142c2336b76d3','--identity-repo',
      'C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800','--output',str(OUT/'reproduction')]
result=subprocess.run(argv,cwd=SOURCE,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(OUT/'author.stdout.txt').write_bytes(result.stdout)
(OUT/'author.stderr.txt').write_bytes(result.stderr)
(OUT/'author-command.json').write_text(json.dumps({'argv':argv,'cwd':str(SOURCE),'exit_code':result.returncode,
    'environment':{k:env[k] for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE','TEMP','TMP')},
    'target_commit':'38aca9dcc8d027409b95193e9cc142c2336b76d3','stdout':'author.stdout.txt','stderr':'author.stderr.txt'},indent=2)+'\n',encoding='utf-8')
print(result.stdout.decode('utf-8',errors='replace'))
if result.returncode:print(result.stderr.decode('utf-8',errors='replace'))
sys.exit(result.returncode)
