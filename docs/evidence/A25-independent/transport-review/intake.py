"""Exact raw intake of the frozen A25 transport delta; no product execution."""
import hashlib,json,os,subprocess
from pathlib import Path
PUB=Path(__file__).resolve().parent
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/transport-review-20261023')
REPO=Path('C:/Users/ASUS/.codex/worktrees/b-latest-20261023/1800')
PRODUCT='afc9d761294203e7cfb8086a82f1a7fdd8724372'
FINAL='fef3638d5793347a2b70f21108f6c03ee7856bbc'
PARENT='b74e9865d0e77bab304f0e91fb0c5e839ae56079'
EXPECTED='e6459fad81e5b222fe73a74161c0fbf710162bf8a4910528d5062c62f140d752'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def main():
 STAGE.mkdir(exist_ok=False);env=os.environ.copy();env['GIT_NO_LAZY_FETCH']='1';cmds=[];inputs=[]
 def git(args):
  argv=['git','-c','core.longpaths=true',*args];p=subprocess.run(argv,cwd=str(REPO),env=env,capture_output=True);n=len(cmds)+1;streams={}
  for label,b in [('stdout',p.stdout),('stderr',p.stderr)]:
   path=STAGE/'git'/('%03d.%s'%(n,label));put(path,b);streams[label]={'path':str(path),'bytes':len(b),'sha256':sha(b)}
  cmds.append({'argv':argv,'env':{'GIT_NO_LAZY_FETCH':'1'},'exit_code':p.returncode,**streams})
  if p.returncode:put(STAGE/'failed-git.json',enc(cmds));raise RuntimeError('Git failed; no retry')
  return p.stdout
 raw=git(['show',FINAL+':docs/evidence/A25-transport-revision/raw-manifest.json']);assert sha(raw)==EXPECTED;manifest=json.loads(raw);put(STAGE/'raw-manifest.json',raw)
 assert manifest['product_commit']==PRODUCT and manifest['parent_fixed_commit']==PARENT
 for entry in manifest['source_members']:
  name=entry['path'];assert not Path(name).is_absolute() and '..' not in Path(name).parts
  raw=git(['show',PRODUCT+':'+name]);assert sha(raw)==entry['sha256'] and len(raw)==entry['bytes'];assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==entry['git_blob']
  assert raw==Path(entry['raw_path']).read_bytes()==git(['show',FINAL+':'+name])
  target=STAGE/'snapshot'/name;put(target,raw);inputs.append({'kind':'source','git':PRODUCT+':'+name,'copy':str(target),'bytes':len(raw),'sha256':sha(raw)})
 for entry in manifest['private_inputs_and_evidence']:
  source=Path(entry['raw_path']);raw=source.read_bytes();assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256'];parts=source.parts;rel=Path(*parts[parts.index('private')+1:]);target=STAGE/'private'/rel;put(target,raw);inputs.append({'kind':'frozen_private','source':str(source),'copy':str(target),'bytes':len(raw),'sha256':sha(raw)})
 for name in ['docs/evidence/A25-transport-revision/README.md','evaluation/a25-transport-revision-20261023.json']:
  raw=git(['show',FINAL+':'+name]);target=STAGE/'snapshot'/name;put(target,raw);inputs.append({'kind':'final_report','git':FINAL+':'+name,'copy':str(target),'bytes':len(raw),'sha256':sha(raw)})
 put(STAGE/'product-delta.patch',git(['diff',PARENT,PRODUCT,'--','src','tools','tests']))
 put(STAGE/'diff-name-status.txt',git(['diff','--name-status',PARENT,FINAL]))
 put(STAGE/'product-to-final.txt',git(['diff','--name-status',PRODUCT,FINAL]))
 oldmanifest=json.loads(Path('D:/1800/.local/stages/a25-independent-20261023/review-initial-20261023/raw-manifest.json').read_bytes());old=0
 for group,key in [('source_members','raw_path'),('private_evidence','frozen_path')]:
  for entry in oldmanifest[group]:
   raw=Path(entry[key]).read_bytes();assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256'];old+=1
 previous=PUB.parent/'review'
 for line in (previous/'review-files.sha256').read_text(encoding='ascii').splitlines():
  h,name=line.split('  ',1);assert sha((previous/name).read_bytes())==h
 plan=(STAGE/'private/next-capture-plan.json').read_bytes();assert sha(plan)==manifest['next_plan_sha256']=='51ed313709d56bf7064a0a65e2bd41fe138ab8d185e3b1fb852ff7d988121313'
 v={'schema':'A25IndependentTransportIntake/v1','parent':PARENT,'product':PRODUCT,'final':FINAL,'manifest_sha256':EXPECTED,'next_plan_sha256':sha(plan),'source_verified':30,'private_verified':23,'additional_reports':2,'old_source_and_private_verified_unchanged':old,'previous_review_hashed_members_unchanged':True,'inputs':inputs,'commands':cmds,'active_author_worktree_reads':0,'product_execution':0};put(PUB/'intake.json',enc(v));print(json.dumps({k:v[k] for k in ['source_verified','private_verified','old_source_and_private_verified_unchanged','next_plan_sha256']}))
if __name__=='__main__':main()
