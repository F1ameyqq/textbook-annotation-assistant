"""P1-R1 exact Git blob export and immutable readset audit; no business imports."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path('D:/1800')
COMMIT = 'ca4fba4f505467228a8164c3999e0cecc54ffc4e'
DESIGN = '095ed4aa18a56100ce3aabc4a0d6885ad37ab520'
BASE = '2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9'
STAGE = ROOT / '.local/stages/A03-review-P1-R1' / COMMIT
OUT = ROOT / 'docs/evidence/A03/review/P1-R1'
EXPECTED = {
 'docs/tasks/A03-P1-R1-execution-report.md': '5121b6bfecf767ff496ce4a973d81df71ccd308cbebd9057f816d571b54cb301',
 'docs/evidence/A03/execution/P1-R1/sha256-manifest.json': 'c882542e9aefe1f413533b1350f6b81d20202f0bc37dd44b829d1eeb39f946b5',
 'docs/a03-recovery-contract-v1-r1-proposal.md': 'bec9ad4f89bc5f026d6a71c2214edd8d8d8eacec8a61ec8e3287e9e4b702e23e'}

def sha(b): return hashlib.sha256(b).hexdigest()
def git(*args):
 p=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,timeout=60,
                  env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
 assert p.returncode==0,(args,p.returncode,p.stderr.decode('utf-8','replace'))
 return p.stdout
def write(p,x):
 with p.open('x',encoding='utf-8',newline='\n') as f:
  json.dump(x,f,ensure_ascii=False,indent=2); f.write('\n')
def main():
 assert not STAGE.exists(),'preserve/reconcile existing stage before export'
 for ancestor in (BASE,DESIGN): git('merge-base','--is-ancestor',ancestor,COMMIT)
 tree={}
 for row in git('ls-tree','-rz',COMMIT).split(b'\0'):
  if not row: continue
  head,name=row.split(b'\t',1); mode,kind,oid=head.decode().split()
  assert mode in ('100644','100755') and kind=='blob'
  tree[name.decode()]=oid
 batch=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,
  input=('\n'.join(tree.values())+'\n').encode(),capture_output=True,timeout=60)
 assert batch.returncode==0
 STAGE.mkdir(parents=True); position=0; rows=[]
 for name,expected in tree.items():
  end=batch.stdout.index(b'\n',position); oid,kind,size=batch.stdout[position:end].decode().split()
  assert oid==expected and kind=='blob'
  position=end+1; raw=batch.stdout[position:position+int(size)]; position+=int(size)+1
  assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid
  p=(STAGE/name).resolve(); assert p.is_relative_to(STAGE.resolve()); p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f: f.write(raw)
  rows.append({'path':name,'bytes':len(raw),'sha256':sha(raw),'git_blob':oid})
 assert position==len(batch.stdout)
 changes=git('diff','--name-status',BASE,COMMIT).decode().splitlines()
 assert len(changes)==781 and all(x.startswith('A\t') for x in changes)
 for x in changes:
  p=x[2:]
  assert p.startswith(('examples/a03/P1-R1/','docs/evidence/A03/execution/P1-R1/')) or p in (
   'docs/a03-recovery-contract-v1-r1-proposal.md','docs/tasks/A03-P1-R1-execution-report.md')
 assert not git('diff','--name-only',DESIGN,COMMIT,'--','examples/a03/P1-R1','docs/a03-recovery-contract-v1-r1-proposal.md')
 for p,d in EXPECTED.items(): assert sha((STAGE/p).read_bytes())==d,p
 manifest=json.loads((STAGE/'docs/evidence/A03/execution/P1-R1/sha256-manifest.json').read_bytes())
 assert len(manifest['files'])==780
 for x in manifest['files']:
  p=(STAGE/x['path']).resolve(); assert p.is_relative_to(STAGE)
  b=p.read_bytes(); assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
 protected=[]
 for folder in ('docs/evidence/A03/review/P1','docs/evidence/A03/review/preparation'):
  protected.extend(p for p in (ROOT/folder).rglob('*') if p.is_file())
 protected.extend(ROOT/p for p in ('docs/tasks/A03-P1-review-report.md','docs/tasks/A03-review-preparation.md'))
 protected_rows=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in protected]
 inputs=OUT/'inputs'; inputs.mkdir()
 source_rows=[]
 for p in ('docs/tasks/A03-P1-R1-review-handoff.md','docs/tasks/A03-P1-rework-R1.md',
           'docs/tasks/A03-independent-review.md','docs/tasks/A03-runtime-recovery.md','AGENTS.md'):
  b=(ROOT/p).read_bytes(); dest=inputs/Path(p).name
  with dest.open('xb') as f:f.write(b)
  source_rows.append({'path':p,'bytes':len(b),'sha256':sha(b)})
 write(OUT/'export-manifest.json',{'commit':COMMIT,'design_commit':DESIGN,'base_commit':BASE,'stage':str(STAGE),'files':rows})
 write(OUT/'freeze-checks.json',{'commit':COMMIT,'new_allowed_files':781,'old_git_files_preserved':len(rows)-781,
  'all_raw_git_blobs_verified':True,'manifest_entries_verified':780,'specified_sha256_verified':EXPECTED,
  'design_files_unchanged_after_design_commit':True,'standards':source_rows,'protected_old_review_files':protected_rows,
  'stage_file_count':len(rows),'business_code_executed':False})
 print(json.dumps({'result':'FROZEN_GIT_EXPORT_VERIFIED','files':len(rows),'old_files_preserved':len(rows)-781,
  'new_files':781,'manifest_entries':780,'protected_old_review_files':len(protected_rows)}))
if __name__=='__main__':main()
