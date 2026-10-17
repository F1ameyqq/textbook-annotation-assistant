# -*- coding: utf-8 -*-
"""Freeze static proposal input bytes; never import product code or open DBs."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R1-proposal';STAGE=OUT/'input/checkout'
C='7fdbde8f16569fd3bc399013115e13269d5d33fa';B='c30526958e313141bf64152627591b0907b04aa8';W='c135542791cb9172dd3163bf593273814a556968'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def git(*args):
 r=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,timeout=60);assert r.returncode==0,(args,r.stderr);return r.stdout
def blob(c,p):return git('cat-file','blob',c+':'+p)
def tree(c):
 d={}
 for row in git('ls-tree','-rz',c).split(b'\0'):
  if row:
   h,p=row.split(b'\t',1);mode,kind,oid=h.split();assert kind==b'blob';d[p.decode()]=(mode.decode(),oid.decode())
 return d
assert not STAGE.exists()
old={p for p in (ROOT/'docs/evidence/A03/review').rglob('*') if p.is_file() and not p.is_relative_to(OUT)}
old|={p for p in (ROOT/'docs/tasks').glob('A03*review*.md') if p.name!='A03-P2-R1-proposal-review-report.md'}
write(OUT/'protected-old-review-files.json',{'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(old)],'database_files':'hash bytes only; no SQLite connections'})
t=tree(C);base=tree(B);assert len(base)==27168 and all(t.get(p)==o for p,o in base.items())
added=sorted(set(t)-set(base));assert len(added)==502
assert all(p=='docs/tasks/A03-P2-R1-amendment-delivery.md' or p.startswith(('examples/a03/P2-R1-proposal/','docs/evidence/A03/execution/P2-R1-proposal/')) for p in added)
manifest_path='docs/evidence/A03/execution/P2-R1-proposal/sha256-manifest.json';mb=blob(C,manifest_path)
assert sha(mb)=='2eea068aba8b1e678cc8e8984165cd0025ac8a21f6cfdfebc439aeb08d2010ab'
m=json.loads(mb);entries=m.get('entries',m.get('files'));assert len(entries)==501
index=[];cache={}
for e in entries:
 p=e['path'];b=cache.get(t[p][1])
 if b is None:b=blob(C,p);cache[t[p][1]]=b
 assert len(b)==e['bytes'] and sha(b)==e['sha256'],p
 index.append({'path':p,'git_blob':t[p][1],'bytes':len(b),'sha256':sha(b)})
assert {e['path'] for e in entries}==set(added)-{manifest_path}
selected=set(p for p in t if p.startswith('examples/a03/P2-R1-proposal/candidate-v2/'))
selected.update(['examples/a03/P2-R1-proposal/check_static.py','examples/a03/P2-R1-proposal/build_static.py','examples/a03/P2-R1-proposal/README.md'])
selected.update(p for p in t if p.startswith('docs/evidence/A03/execution/P2-R1-proposal/negative-values/'))
selected.update(['docs/tasks/A03-P2-R1-amendment-delivery.md','docs/evidence/A03/execution/P2-R1-proposal/future-test-matrix.json',
 'docs/evidence/A03/execution/P2-R1-proposal/static-check-result.json','docs/evidence/A03/execution/P2-R1-proposal/command-notes.json',
 'docs/evidence/A03/execution/P2-R1-proposal/initial-command-note.json','docs/evidence/A03/execution/P2-R1-proposal/delivery-verification.json',
 'docs/evidence/A03/execution/P2-R1-proposal/draft-retention.json'])
selected.update(p for p in t if p.startswith('docs/evidence/A03/execution/P2-R1-proposal/runs/') and (p.endswith('exit.json') or '/check-05/' in p))
selected.update(p for p in t if p.startswith('src/annotation/contracts/schemas/'))
selected.add('examples/a03/P1-R2/api-proposal.json')
files=[]
for p in sorted(selected):
 b=blob(C,p);q=STAGE/p;q.parent.mkdir(parents=True,exist_ok=True)
 with q.open('xb') as f:f.write(b)
 files.append({'commit':C,'path':p,'git_blob':t[p][1],'bytes':len(b),'sha256':sha(b),'copy':q.relative_to(ROOT).as_posix()})
for p in ['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md','docs/tasks/A03-P2-R1-proposal-review-handoff.md',
 'docs/tasks/A03-P2-R1-amendment-proposal.md','docs/evidence/coordinator/heartbeat-20261017-0619/A03-proposal-delivery-preflight.json']:
 b=blob(W,p);q=OUT/'input/workflow'/p;q.parent.mkdir(parents=True,exist_ok=True)
 with q.open('xb') as f:f.write(b)
 files.append({'commit':W,'path':p,'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'bytes':len(b),'sha256':sha(b),'copy':q.relative_to(ROOT).as_posix()})
assert sha(blob(C,'docs/tasks/A03-P2-R1-amendment-delivery.md'))=='0f70c125dbbfa2f4897a43cef9762e9aef6bfcc65d8708ca50d9b11813fc4cf4'
write(OUT/'delivery-byte-index.json',{'commit':C,'manifest_sha256':sha(mb),'entries':index,'old_git_files_unchanged':27168,'old_trees_copied':False})
write(OUT/'input-index.json',{'commit':C,'base':B,'workflow':W,'stage':str(STAGE),'candidate':'examples/a03/P2-R1-proposal/candidate-v2',
 'files':files,'added_files':502,'manifest_entries':501,'old_git_files_unchanged':27168,
 'selection':'current candidate-v2 only; necessary static checker and generator source (generator not run), explicit negatives, relevant diagnostics/exit records and frozen schema/API byte comparators; no product Python implementation exported'})
print(json.dumps({'result':'STATIC_INPUTS_FROZEN','exports':len(files),'candidate_files':sum('/candidate-v2/' in x['path'] for x in files),'manifest_entries':501,'old_git_unchanged':27168}))
