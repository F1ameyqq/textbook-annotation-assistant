import json,os,subprocess,sys,time
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];STAGE=Path('D:/1800/.local/stages/A04-review/coordinate-R1');ROOT=STAGE/'frozen input with spaces'
env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1',TEMP=str(STAGE),TMP=str(STAGE),PYTHONIOENCODING='utf-8')
args=[sys.executable,str(ROOT/'docs/evidence/A04/execution/coordinate-R1/run-local-renderer.py'),'--output',str(OUT/'author-renderer-replay')]
t=time.time();p=subprocess.run(args,cwd=str(ROOT),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
(OUT/'reproduction/author-renderer.log').write_bytes(p.stdout)
r={'args':args,'cwd':str(ROOT),'returncode':p.returncode,'elapsed_seconds':time.time()-t,
 'summary':p.stdout.decode('utf-8','replace').splitlines()[-10:],
 'scope':'Delivered local renderer only; all page URLs fulfill/abort locally; no persistent context or credentials',
 'platform_validation':False}
(OUT/'reproduction/author-renderer.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r));raise SystemExit(p.returncode)
