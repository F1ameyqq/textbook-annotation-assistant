"""Export bounded P1-R2 static inputs as exact Git blobs; index all other bytes."""
import hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path('D:/1800'); COMMIT='940a5de33a24b1a3a9ded6e69ade1dd0609ed83a'
DESIGN='a250a76dc0b3f13b9dee3bcd2c3d7414032b9768'; BASE='ca4fba4f505467228a8164c3999e0cecc54ffc4e'
OUT=ROOT/'docs/evidence/A03/review/P1-R2'; STAGE=ROOT/'.local/stages/A03-review-P1-R2'/COMMIT
EXPECTED={'docs/tasks/A03-P1-R2-execution-report.md':'387212c84155bdde735ce6b758c14d94fef60ae01e7316ce00a1a7164ca4899b',
 'docs/evidence/A03/execution/P1-R2/sha256-manifest.json':'8226c4542720fe1004eb12fbce084d72d72033f588293b5cefcb878460f7309e',
 'docs/a03-recovery-contract-v1-r2-proposal.md':'acd67720e905a45b85c0943648b239b2dfd1fdb36eaf3095e56803c1de564f9d'}
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):
 p=subprocess.run(['git',*a],cwd=ROOT,capture_output=True,timeout=60,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
 assert p.returncode==0,(a,p.returncode,p.stderr.decode('utf-8','replace'));return p.stdout
def tree(commit):
 out={}
 for row in git('ls-tree','-rz',commit).split(b'\0'):
  if row:
   h,n=row.split(b'\t',1);mode,kind,oid=h.decode().split();assert kind=='blob' and mode in ('100644','100755');out[n.decode()]=oid
 return out
def selected(n):
 if n.startswith('examples/a03/P1-R2/'):
  tail=n[len('examples/a03/P1-R2/'):]
  return not tail.startswith('attempts/') or '/data/' not in tail
 if n.startswith('docs/evidence/A03/execution/P1-R2/'):
  return not n.endswith('/baseline-preservation.json')
 if n.startswith('examples/a03/P1-R1/'):
  tail=n[len('examples/a03/P1-R1/'):];return tail.startswith('data/') or '/' not in tail
 return n in ('AGENTS.md','docs/architecture.md','docs/contracts-v1.md',
  'docs/a03-recovery-contract-v1-proposal.md','docs/a03-recovery-contract-v1-r1-proposal.md',
  'docs/a03-recovery-contract-v1-r2-proposal.md','docs/tasks/A03-P1-R2-execution-report.md',
  'docs/tasks/A03-independent-review.md','docs/tasks/A03-runtime-recovery.md')
def write(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
 assert not STAGE.exists(),'preserve existing stage and reconcile before rerun'
 for a in (BASE,DESIGN):git('merge-base','--is-ancestor',a,COMMIT)
 old=tree(BASE);new=tree(COMMIT);assert len(old)==8923
 assert all(new.get(n)==oid for n,oid in old.items()),'old raw blobs changed'
 added=set(new)-set(old);assert len(added)==787
 assert all(n.startswith(('examples/a03/P1-R2/','docs/evidence/A03/execution/P1-R2/')) or n in (
  'docs/a03-recovery-contract-v1-r2-proposal.md','docs/tasks/A03-P1-R2-execution-report.md') for n in added)
 assert not git('diff','--name-only',DESIGN,COMMIT,'--','examples/a03/P1-R2','docs/a03-recovery-contract-v1-r2-proposal.md')
 chosen={n for n in new if selected(n)};wanted=sorted(chosen|added)
 p=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,input=('\n'.join(new[n] for n in wanted)+'\n').encode(),capture_output=True,timeout=60)
 assert p.returncode==0;pos=0;rows=[];raws={};STAGE.mkdir(parents=True)
 for n in wanted:
  e=p.stdout.index(b'\n',pos);oid,kind,size=p.stdout[pos:e].decode().split();assert oid==new[n] and kind=='blob'
  pos=e+1;raw=p.stdout[pos:pos+int(size)];pos+=int(size)+1
  assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid
  if n in added:raws[n]=raw
  if n in chosen:
   dest=(STAGE/n).resolve();assert dest.is_relative_to(STAGE);dest.parent.mkdir(parents=True,exist_ok=True)
   with dest.open('xb') as f:f.write(raw)
  rows.append({'path':n,'git_blob':oid,'bytes':len(raw),'sha256':sha(raw),'exported':n in chosen,'added_in_R2':n in added})
 assert pos==len(p.stdout)
 for n,d in EXPECTED.items():assert sha(raws[n])==d,n
 m=json.loads(raws['docs/evidence/A03/execution/P1-R2/sha256-manifest.json']);assert len(m['files'])==786
 for x in m['files']:
  b=raws[x['path']];assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
 protected=[]
 for dirname in ('P1','P1-R1','preparation'):
  protected.extend(p for p in (ROOT/'docs/evidence/A03/review'/dirname).rglob('*') if p.is_file())
 protected.extend(ROOT/'docs/tasks'/n for n in ('A03-P1-review-report.md','A03-P1-R1-review-report.md','A03-review-preparation.md'))
 inputs=OUT/'inputs';inputs.mkdir();standards=[]
 for n in ('A03-P1-R2-review-handoff.md','A03-P1-rework-R2.md','A03-independent-review.md','A03-runtime-recovery.md','A03-P1-R1-review-report.md'):
  raw=(ROOT/'docs/tasks'/n).read_bytes()
  with (inputs/n).open('xb') as f:f.write(raw)
  standards.append({'path':'docs/tasks/'+n,'bytes':len(raw),'sha256':sha(raw)})
 write(OUT/'input-index.json',{'commit':COMMIT,'design_commit':DESIGN,'base_commit':BASE,'stage':str(STAGE),
  'selection':'formal R2, relevant failures/logs, required R1 mapping data only; no duplicate historical attempt data trees',
  'files':rows,'old_git_blobs_preserved':8923,'new_allowed_files':787,'manifest_entries_verified':786,
  'specified_sha256_verified':EXPECTED,'standards':standards,
  'protected_old_review_files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in protected]})
 print(json.dumps({'result':'BOUNDED_RAW_GIT_EXPORT_VERIFIED','exported':len(chosen),'indexed_added':787,'old_preserved':8923,
  'execution_manifest_entries':786,'protected_old_review_files':len(protected)}))
if __name__=='__main__':main()
