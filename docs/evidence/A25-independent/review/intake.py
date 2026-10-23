"""Independent exact-commit intake. Does not import or execute product code."""
import hashlib, json, os, subprocess
from pathlib import Path

REPO=Path('C:/Users/ASUS/.codex/worktrees/b-latest-20261023/1800')
OUT=Path('D:/1800/.local/stages/a25-independent-20261023/review-initial-20261023')
PUB=Path('D:/1800/docs/evidence/A25-independent/review')
BASE='ee463c800bef1ec5010ee5950662b9726d474e42'
PRODUCT='b551dceadb052efad2e7e47216ec62896213ee40'
FINAL='b74e9865d0e77bab304f0e91fb0c5e839ae56079'
MANIFEST='558dddbdf859374095cd9b1d56c889bc0e88e5d9c3cef3544513f401a2b9438c'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def put(p,raw):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def main():
 if OUT.exists():raise RuntimeError('No overwrite of prior intake')
 OUT.mkdir(parents=True);env=os.environ.copy();env['GIT_NO_LAZY_FETCH']='1';commands=[];inputs=[]
 def git(args):
  argv=['git','-c','core.longpaths=true',*args]
  p=subprocess.run(argv,cwd=str(REPO),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  n=len(commands)+1;streams={}
  for label,raw in [('stdout',p.stdout),('stderr',p.stderr)]:
   path=OUT/'git'/('%03d.%s'%(n,label));put(path,raw)
   streams[label]={'path':str(path),'bytes':len(raw),'sha256':sha(raw)}
  commands.append({'argv':argv,'env':{'GIT_NO_LAZY_FETCH':'1'},'exit_code':p.returncode,**streams})
  if p.returncode:put(OUT/'failed-commands.json',enc(commands));raise RuntimeError('Git intake failure, no retry')
  return p.stdout
 for commit in [BASE,PRODUCT,FINAL]:
  assert git(['rev-parse','--verify',commit+'^{commit}']).decode().strip()==commit
 raw=git(['show',FINAL+':docs/evidence/A25-execution/raw-manifest.json']);assert sha(raw)==MANIFEST
 put(OUT/'raw-manifest.json',raw);manifest=json.loads(raw)
 assert manifest['product_commit']==PRODUCT and manifest['base_commit']==BASE
 for entry in manifest['source_members']:
  name=entry['path'];assert not Path(name).is_absolute() and '..' not in Path(name).parts
  raw=git(['show',PRODUCT+':'+name]);assert sha(raw)==entry['sha256'] and len(raw)==entry['bytes']
  assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==entry['git_blob']
  assert raw==Path(entry['raw_path']).read_bytes()
  assert raw==git(['show',FINAL+':'+name])
  p=OUT/'snapshot'/name;put(p,raw);inputs.append({'kind':'source','git':PRODUCT+':'+name,'copy':str(p),'bytes':len(raw),'sha256':sha(raw)})
 for group,key,prefix in [('external_inputs','raw_path','external'),('private_evidence','frozen_path','private')]:
  for i,entry in enumerate(manifest[group]):
   source=Path(entry[key]);raw=source.read_bytes();assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256']
   anchor='external-inputs' if prefix=='external' else 'private-evidence'
   parts=source.parts;rel=Path(*parts[parts.index(anchor)+1:]);p=OUT/prefix/rel;put(p,raw)
   inputs.append({'kind':prefix,'source':str(source),'copy':str(p),'bytes':len(raw),'sha256':sha(raw)})
 for name in ['docs/evidence/A25-execution/README.md','docs/evidence/A25-execution/publication-check-initial-observation.json','evaluation/a25-lesson2-execution-20261023.json']:
  raw=git(['show',FINAL+':'+name]);p=OUT/'snapshot'/name;put(p,raw);inputs.append({'kind':'final_report','git':FINAL+':'+name,'copy':str(p),'bytes':len(raw),'sha256':sha(raw)})
 diff=git(['diff','--name-status',BASE,FINAL]);put(OUT/'diff-name-status.txt',diff)
 patch=git(['diff',BASE,PRODUCT,'--','src/annotation/__init__.py','src/annotation/runtime/usense_live/batch.py','tools/run_usense_reviewed_batch.py','tests/test_a25_batch.py']);put(OUT/'product-delta.patch',patch)
 raw=git(['diff','--name-status',PRODUCT,FINAL]);put(OUT/'product-to-final.txt',raw)
 records={'schema':'A25IndependentRawIntake/v1','base':BASE,'product':PRODUCT,'final':FINAL,'manifest_sha256':MANIFEST,'inputs':inputs,'commands':commands,'source_verified':27,'external_verified':3,'private_verified':47,'source_matches_git_and_frozen':True,'source_unchanged_in_final':True,'product_execution':0,'active_worktree_reads':0}
 put(PUB/'intake.json',enc(records));print(json.dumps({'source':27,'external':3,'private':47,'commands':len(commands),'status':'VERIFIED_FROZEN_INPUTS'}))
if __name__=='__main__':main()
