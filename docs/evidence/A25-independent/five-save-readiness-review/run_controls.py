"""Retain the bounded independent control process streams verbatim."""
import hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
PUB=Path(__file__).resolve().parent
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-readiness-review-20261023')
def main():
 env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONIOENCODING']='utf-8';argv=[sys.executable,'-B',str(PUB/'controls.py')];start=datetime.now(timezone.utc).isoformat();p=subprocess.run(argv,cwd=str(STAGE),env=env,capture_output=True,timeout=55);streams={}
 for label,raw in [('stdout',p.stdout),('stderr',p.stderr)]:
  path=STAGE/('independent-controls.'+label)
  with path.open('xb') as f:f.write(raw)
  streams[label]={'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 v={'argv':argv,'cwd':str(STAGE),'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'exit_code':p.returncode,**streams}
 with (PUB/'control-process.json').open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
 print(json.dumps({'exit_code':p.returncode,'stdout':p.stdout.decode('utf-8',errors='replace'),'stderr':p.stderr.decode('utf-8',errors='replace')}))
if __name__=='__main__':main()
