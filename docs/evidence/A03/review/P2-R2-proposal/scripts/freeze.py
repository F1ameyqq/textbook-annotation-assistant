# -*- coding: utf-8 -*-
"""Exact Git blob export for bounded STATIC review; no product imports/DB."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R2-proposal';STAGE=OUT/'input/checkout'
C='526d264284f36f856c306db88c1d7e71c04152e1';B='7fdbde8f16569fd3bc399013115e13269d5d33fa';W='0a668650f3dfdc00898032fb9c89e96694260d23'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def git(*a,input=None):
 r=subprocess.run(['git',*a],cwd=ROOT,input=input,capture_output=True,timeout=60);assert r.returncode==0,(a,r.stderr);return r.stdout
def tree(c):
 result={}
 for row in git('ls-tree','-rz',c).split(b'\0'):
  if row:
   a,p=row.split(b'\t',1);mode,typ,oid=a.split();assert typ==b'blob';result[p.decode()]=(mode.decode(),oid.decode())
 return result
def blob(c,p):return git('cat-file','blob',c+':'+p)
assert not STAGE.exists()
old={p for p in (ROOT/'docs/evidence/A03/review').rglob('*') if p.is_file() and not p.is_relative_to(OUT)}
old|={p for p in (ROOT/'docs/tasks').glob('A03*review*.md') if p.name!='A03-P2-R2-proposal-review-report.md'}
write(OUT/'protected-old-review-files.json',{'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(old)],'old_DB_files':'byte hashes only, not SQLite queries'})
t=tree(C);base=tree(B);assert all(t.get(p)==oid for p,oid in base.items());added=sorted(set(t)-set(base));assert len(added)==206
assert all(p=='docs/tasks/A03-P2-R2-proposal-delivery.md' or p.startswith(('docs/evidence/A03/execution/P2-R2-proposal/','examples/a03/P2-R2-proposal/')) for p in added)
cache={};oids=sorted({t[p][1] for p in added});raw=git('cat-file','--batch',input=('\n'.join(oids)+'\n').encode());pos=0
for oid in oids:
 end=raw.index(b'\n',pos);header=raw[pos:end].split();assert header[:2]==[oid.encode(),b'blob'];n=int(header[2]);start=end+1;b=raw[start:start+n];pos=start+n+1
 assert raw[pos-1:pos]==b'\n' and hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==oid;cache[oid]=b
assert pos==len(raw)
mp='docs/evidence/A03/execution/P2-R2-proposal/sha256-manifest.json';mb=cache[t[mp][1]]
assert sha(mb)=='75f158577e48f029e542674ad5216df0b41ea02df69e76cf646cd35f4a83ed64'
m=json.loads(mb);entries=m.get('entries',m.get('files'));assert len(entries)==205
assert {x['path'] for x in entries}==set(added)-{mp}
for x in entries:
 b=cache[t[x['path']][1]];assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
selected={p for p in added if p.startswith('examples/a03/P2-R2-proposal/candidate-final/')}
selected.update('examples/a03/P2-R2-proposal/'+p for p in ['check.py','schema_check.py','oracle_verifier.py','author.py','SPEC.md','oracle.json'])
selected.update(p for p in added if p.startswith('docs/evidence/A03/execution/P2-R2-proposal/inputs/'))
selected.update(p for p in added if p.startswith('docs/evidence/A03/execution/P2-R2-proposal/negative-values/'))
selected.update(p for p in added if p.startswith('docs/evidence/A03/execution/P2-R2-proposal/runs/') and (p.endswith('/exit.json') or '/check-01/' in p or '/check-05/' in p))
selected.update(p for p in added if p.startswith('docs/evidence/A03/execution/P2-R2-proposal/') and p.count('/')==5 and p!=mp)
selected.add('docs/tasks/A03-P2-R2-proposal-delivery.md')
files=[]
for p in sorted(selected):
 b=cache[t[p][1]];q=STAGE/p;q.parent.mkdir(parents=True,exist_ok=True)
 with q.open('xb') as f:f.write(b)
 files.append({'commit':C,'path':p,'git_blob':t[p][1],'bytes':len(b),'sha256':sha(b),'copy':q.relative_to(ROOT).as_posix()})
for p in ['AGENTS.md','docs/coordination.md','docs/tasks/A03-P2-R2-proposal-review-handoff.md','docs/tasks/A03-P2-R2-static-rework.md',
 'docs/tasks/A03-P2-R1-proposal-coordinator-decision.md','docs/evidence/coordinator/heartbeat-20261017-0734/A03-R2-delivery-preflight.json']:
 b=blob(W,p);q=OUT/'input/workflow'/p;q.parent.mkdir(parents=True,exist_ok=True)
 with q.open('xb') as f:f.write(b)
 files.append({'commit':W,'path':p,'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'bytes':len(b),'sha256':sha(b),'copy':q.relative_to(ROOT).as_posix()})
assert sha(cache[t['docs/tasks/A03-P2-R2-proposal-delivery.md'][1]])=='e6df1732e7a3623047a4ed02457a1d5b453cb2aae3253a3913426a00fcf5b218'
assert sha(cache[t['examples/a03/P2-R2-proposal/candidate-final/profile.json'][1]])=='f7385ba20090b5df8aa062c417e3d5c66a889a30f464facff994d9929b94f9ea'
write(OUT/'delivery-byte-index.json',{'commit':C,'base':B,'old_git_unchanged':len(base),'new_paths':206,'manifest_sha256':sha(mb),'entries':entries,
 'method':'raw cat-file blob framing and SHA1/SHA256; no archive transform','historical_candidate_trees_duplicated':False})
write(OUT/'input-index.json',{'commit':C,'base':B,'workflow':W,'stage':str(STAGE),'candidate':'examples/a03/P2-R2-proposal/candidate-final','files':files,
 'manifest_entries':205,'new_paths':206,'old_git_unchanged':len(base),'generator_execution':False,
 'selection':'candidate-final, reviewed checker/deps, specific prior diagnostics/text/planner SOURCE only, failure/current raw logs, exits and workflow; not full historical trees'})
print(json.dumps({'result':'R2_RAW_INPUTS_FROZEN','exports':len(files),'candidate_files':sum('/candidate-final/' in x['path'] for x in files),'manifest_entries':205,'old_git_unchanged':len(base)}))
