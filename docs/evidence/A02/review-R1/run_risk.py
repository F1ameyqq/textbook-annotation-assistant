"""Re-run the existing independent reviewer matrix on exact R1 sources, in new outputs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

OUT=Path(__file__).resolve().parent
SOURCE=OUT/'source-38aca9dc'
OLD=OUT.parent/'review/formal/independent_review.py'
script=OLD.read_text(encoding='utf-8')
script=script.replace("Path('D:/1800/.local/stages/A02-review/frozen-5c928572')",'Path('+repr(SOURCE.as_posix())+')')
script=script.replace("'5c9285720c8628c5198bedeadfc9f6bc7826a914'","'38aca9dcc8d027409b95193e9cc142c2336b76d3'")
path=OUT/'risk_review.py'
path.write_text(script,encoding='utf-8')
records=[]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(SOURCE/'src'),TEMP=str(OUT/'tmp'),TMP=str(OUT/'tmp'))
for name,extra in [('risk-original',[]),('risk-supplement',['--supplement'])]:
    argv=[sys.executable,'-B',str(path),*extra]
    result=subprocess.run(argv,cwd=OUT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (OUT/(name+'.stdout.txt')).write_bytes(result.stdout);(OUT/(name+'.stderr.txt')).write_bytes(result.stderr)
    records.append({'name':name,'argv':argv,'cwd':str(OUT),'exit_code':result.returncode})
    print(name,result.returncode,flush=True)
    if result.returncode:print(result.stdout.decode(errors='replace'),result.stderr.decode(errors='replace'))
(OUT/'risk-command-receipts.json').write_text(json.dumps({'commands':records,'derived_from':str(OLD),'original_script_sha256':hashlib.sha256(OLD.read_bytes()).hexdigest(),
    'derived_script_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'changes':'Only source path and target commit binding changed; existing corrected independent cases use new exclusive output root.'},indent=2)+'\n',encoding='utf-8')
sys.exit(any(r['exit_code'] for r in records))
