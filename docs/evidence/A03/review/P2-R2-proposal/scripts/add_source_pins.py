# -*- coding: utf-8 -*-
"""Read only exact profile-pinned historical schema dependency, not old trees."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R2-proposal';P=OUT/'input-index.json'
idx=json.loads(P.read_bytes());stage=Path(idx['stage']);data=stage/idx['candidate'];profile=json.loads((data/'profile.json').read_bytes())
added=[]
for x in profile['source_pins']:
 q=stage/x['path'];assert not q.exists()
 r=subprocess.run(['git','cat-file','blob',idx['commit']+':'+x['path']],cwd=ROOT,capture_output=True,timeout=30);assert r.returncode==0
 b=r.stdout;assert hashlib.sha256(b).hexdigest()==x['sha256'];q.parent.mkdir(parents=True,exist_ok=True)
 with q.open('xb') as f:f.write(b)
 record={'commit':idx['commit'],'path':x['path'],'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'bytes':len(b),'sha256':x['sha256'],'copy':q.relative_to(ROOT).as_posix()}
 idx['files'].append(record);added.append(record)
idx['additional_explicit_profile_source_pins']=added
with P.open('w',encoding='utf-8',newline='\n') as f:json.dump(idx,f,ensure_ascii=False,indent=2);f.write('\n')
with (OUT/'source-pin-export.json').open('x',encoding='utf-8',newline='\n') as f:json.dump({'initial_export_files':121,'additional':added,'final_export_files':len(idx['files']),'scope':'only explicit frozen schema source pin; no product Python'},f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'source_pins_added':len(added),'exports':len(idx['files'])}))
