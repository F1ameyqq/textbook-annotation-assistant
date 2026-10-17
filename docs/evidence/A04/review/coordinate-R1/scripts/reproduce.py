"""Run delivered offline commands from raw-blob export; preserve raw output."""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

OUT=Path(__file__).resolve().parents[1]
STAGE=Path('D:/1800/.local/stages/A04-review/coordinate-R1')
ROOT=STAGE/'frozen input with spaces'
LOG=OUT/'reproduction';LOG.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env.update(PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1',
                               TEMP=str(STAGE),TMP=str(STAGE),PYTHONIOENCODING='utf-8')
jobs=[('a04',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_a04_*.py','-v']),
 ('geometry',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_a01_geometry.py','-v']),
 ('contracts',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_contracts*.py','-v']),
 ('login',[sys.executable,'-m','unittest','discover','-s','tools','-p','test_usense_login.py','-v'])]
def run(job):
    name,args=job;t=time.time()
    p=subprocess.run(args,cwd=str(ROOT),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
    path=LOG/(name+'.log');path.write_bytes(p.stdout)
    result={'name':name,'args':args,'cwd':str(ROOT),'returncode':p.returncode,
      'elapsed_seconds':round(time.time()-t,3),'output':str(path.relative_to(OUT)),
      'output_sha256':hashlib.sha256(p.stdout).hexdigest(),'summary':p.stdout.decode('utf-8','replace').splitlines()[-5:]}
    print(json.dumps(result,ensure_ascii=False),flush=True);return result
with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(run,jobs))
import importlib.metadata
versions={n:importlib.metadata.version(n) for n in ['Pillow','playwright','pydantic']}
(LOG/'results.json').write_text(json.dumps({'python':sys.version,'executable':sys.executable,
 'packages':versions,'installation_tested':False,'results':results},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if all(r['returncode']==0 for r in results) else 1)
