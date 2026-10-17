# -*- coding: utf-8 -*-
"""Read exact raw Git blobs, verify delivery index, export bounded review inputs."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2';STAGE=OUT/'input/checkout'
FINAL='c30526958e313141bf64152627591b0907b04aa8';IMPL='fa645ac8fd70688f3293edc5cfb1077fc7bd9daa'
WORKFLOW='2ef3bfda20476dff3bdd23912d5bf2d1e3eb5ce1';BASE='940a5de33a24b1a3a9ded6e69ade1dd0609ed83a'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def git(*a):
 p=subprocess.run(['git',*a],cwd=ROOT,capture_output=True,timeout=60)
 assert p.returncode==0,(a,p.stderr);return p.stdout
def tree(c):
 result={}
 for row in git('ls-tree','-rz',c).split(b'\0'):
  if not row:continue
  a,p=row.split(b'\t',1);mode,kind,oid=a.split();assert kind==b'blob'
  result[p.decode()]={'mode':mode.decode(),'oid':oid.decode()}
 return result
def blob(c,p):return git('cat-file','blob',c+':'+p)
assert not STAGE.exists()
old={p for p in (ROOT/'docs/evidence/A03/review').rglob('*') if p.is_file() and not p.is_relative_to(OUT)}
old|={p for p in (ROOT/'docs/tasks').glob('A03*review*.md') if p.name!='A03-review-report.md'}
write(OUT/'protected-old-review-files.json',{'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(old)]})
t=tree(FINAL);base=tree(BASE);impl=tree(IMPL)
changes=[{'path':p,'old':base.get(p),'new':t.get(p)} for p in sorted(set(t)|set(base)) if base.get(p)!=t.get(p)]
source_paths=[p for p in t if p.startswith('src/annotation/')]
assert all(t[p]==impl[p] for p in source_paths)
manifest_b=blob(FINAL,'docs/evidence/A03/execution/P2/manifest.json')
assert sha(manifest_b)=='d305dd02378811d99d49e882ede04a72ff27ec0697b9c09a6e94057aa8a8e703'
manifest=json.loads(manifest_b);assert len(manifest['entries'])==17429 and not manifest['omitted']
by_oid={};paths=set()
for e in manifest['entries']:
 assert e['path'] in t and e['path'] not in paths;paths.add(e['path'])
 by_oid.setdefault(t[e['path']]['oid'],[]).append(e)
verified=[];oids=list(by_oid)
for i in range(0,len(oids),256):
 chunk=oids[i:i+256];raw=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,input=('\n'.join(chunk)+'\n').encode(),capture_output=True,timeout=60)
 assert raw.returncode==0;data=raw.stdout;pos=0
 for oid in chunk:
  end=data.index(b'\n',pos);parts=data[pos:end].split();assert parts[:2]==[oid.encode(),b'blob'];n=int(parts[2]);start=end+1;b=data[start:start+n];pos=start+n+1
  assert len(b)==n and data[pos-1:pos]==b'\n'
  assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==oid
  s=sha(b)
  for e in by_oid[oid]:
   assert e['bytes']==n and e['sha256']==s,e['path'];verified.append({'path':e['path'],'git_blob':oid,'bytes':n,'sha256':s})
 assert pos==len(data)
selection=set(source_paths)
selection.update(p for p in t if p.startswith('tests/fixtures/a02/normal/'))
selection.update(p for p in t if p.startswith('examples/a03/P2/') and (p.endswith('.py') or p.endswith('README.md')))
selected=[]
for p in sorted(selection):
 b=blob(FINAL,p);q=STAGE/p;q.parent.mkdir(parents=True,exist_ok=True)
 with q.open('xb') as f:f.write(b)
 selected.append({'source_commit':FINAL,'source_path':p,'git_blob':t[p]['oid'],'bytes':len(b),'sha256':sha(b),'copy':q.relative_to(ROOT).as_posix()})
extra={WORKFLOW:['docs/tasks/A03-P2-review-handoff.md','docs/evidence/coordinator/heartbeat-20261017-0516/A03-delivery-preflight.json',
 'docs/tasks/A03-P2-dispatch.md','docs/tasks/A03-P1-coordinator-acceptance.md','docs/tasks/A03-independent-review.md','docs/tasks/A03-runtime-recovery.md'],
 FINAL:['docs/tasks/A03-execution-report.md','docs/a03-runtime-recovery.md','docs/evidence/A03/execution/P2/authorization-review-block.json',
 'docs/evidence/A03/execution/P2/quality-agent-development/index.json','docs/evidence/A03/execution/P2/hold-agent-development/hold-check-summary.json',
 'docs/evidence/A03/execution/P2/check-summary-final.json','docs/evidence/A03/execution/P2/process-release-final.json'],
 BASE:['examples/a03/P1-R2/api-proposal.json','docs/a03-recovery-contract-v1-proposal.md','docs/a03-recovery-contract-v1-r1-proposal.md','docs/a03-recovery-contract-v1-r2-proposal.md']}
for c,pp in extra.items():
 for p in pp:
  b=blob(c,p);q=OUT/'input/documents'/c/p;q.parent.mkdir(parents=True,exist_ok=True)
  with q.open('xb') as f:f.write(b)
  selected.append({'source_commit':c,'source_path':p,'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'bytes':len(b),'sha256':sha(b),'copy':q.relative_to(ROOT).as_posix()})
api=json.loads(blob(BASE,'examples/a03/P1-R2/api-proposal.json'));schema=[]
assert sha(blob(BASE,'examples/a03/P1-R2/api-proposal.json'))=='e2b0865fc1a25206181f3094155b059a6d34eb851afc750e813f0c2e89960f85'
for name,record in api['candidate_profile']['schema_files'].items():
 p='src/annotation/contracts/schemas/'+name;b=blob(FINAL,p)
 assert sha(b)==record['sha256'];schema.append({'path':p,'sha256':sha(b),'equals_R2_pin':True})
assert sha(blob(FINAL,'docs/tasks/A03-execution-report.md'))=='acde484108252c1437d25b96123d5eb8c22cba6f23aac34c53420700bfab27d7'
write(OUT/'delivery-byte-index.json',{'final_commit':FINAL,'manifest_sha256':sha(manifest_b),'entries':sorted(verified,key=lambda x:x['path']),
 'manifest_copied':False,'purpose':'all 17429 raw blob bytes independently verified; historical trees not duplicated'})
write(OUT/'input-index.json',{'final_commit':FINAL,'implementation_commit':IMPL,'workflow_commit':WORKFLOW,'base':BASE,
 'stage':str(STAGE),'files':selected,'schema_pins':schema,'source_same_as_implementation':True,
 'old_git_files':len(base),'old_git_files_changed':[x for x in changes if x['old']],
 'new_paths':len([x for x in changes if not x['old']]),'source_selection':'frozen annotation source, normal all-synthetic fixture, P2 helpers; not author tests or prohibited field-reset probe',
 'prohibited_probe':'authorization-review-block.json is documentation only; rejected action NOT_EXECUTED'})
print(json.dumps({'result':'FROZEN_INPUTS_VERIFIED','manifest_entries':len(verified),'exported_files':len(selected),'stage':str(STAGE),'schema_pins':len(schema)}))
