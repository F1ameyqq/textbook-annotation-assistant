"""Intake exact-commit complete reports and the immutable supplementary bytes."""
import hashlib,json,os,subprocess
from collections import Counter
from pathlib import Path
PUB=Path(__file__).resolve().parent
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/revised-actual-supplement-review-20261023')
ROOT=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/revised-actual-complete-frozen')
REPO=Path('C:/Users/ASUS/.codex/worktrees/b-latest-20261023/1800')
FINAL='b864f413c8bf971153afcefcb78f9621b70ba95f'
EXPECTED='1634a45f71f7ce9c9feeabc81d3b3f0f641df12715fd337ff80a47e1fb3e3ebc'
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def main():
 STAGE.mkdir(exist_ok=False);rootraw=(ROOT/'root-intake.json').read_bytes();root=json.loads(rootraw);put(STAGE/'root-intake.json',rootraw);commands=[];inputs=[];env=os.environ.copy();env['GIT_NO_LAZY_FETCH']='1'
 def git(args):
  argv=['git','-c','core.longpaths=true',*args];p=subprocess.run(argv,cwd=str(REPO),env=env,capture_output=True);streams={};n=len(commands)+1
  for label,b in [('stdout',p.stdout),('stderr',p.stderr)]:
   path=STAGE/'git-commands'/('%02d.%s'%(n,label));put(path,b);streams[label]={'path':str(path),'bytes':len(b),'sha256':sha(b)}
  commands.append({'argv':argv,'env':{'GIT_NO_LAZY_FETCH':'1'},'exit_code':p.returncode,**streams})
  if p.returncode:put(STAGE/'git-failure.json',enc(commands));raise RuntimeError('Stop on Git read failure')
  return p.stdout
 for entry in root['public_git_members']:
  raw=git(['show',FINAL+':'+entry['path']]);assert sha(raw)==entry['sha256'] and len(raw)==entry['bytes'] and raw==Path(entry['raw_path']).read_bytes();target=STAGE/'public'/entry['path'];put(target,raw);inputs.append({'group':'public_git','path':entry['path'],'copy':str(target),'bytes':len(raw),'sha256':sha(raw)})
 manifest_raw=(STAGE/'public/docs/evidence/A25-revised-current-source-actual/raw-manifest.json').read_bytes();assert sha(manifest_raw)==EXPECTED;manifest=json.loads(manifest_raw)
 assert manifest['product_commit']=='afc9d761294203e7cfb8086a82f1a7fdd8724372' and manifest['launch_commit']=='fef3638d5793347a2b70f21108f6c03ee7856bbc'
 groups={'actual':manifest['actual_raw_members'],'source':manifest['fixed_source_members'],'supplement':manifest['offline_supplement_members'],'supervisor':[manifest['supervisor_dependency']]}
 for group,rows in groups.items():
  declared=Counter((e['sha256'],e['bytes']) for e in rows);received=Counter((e['sha256'],e['bytes']) for e in root['root_copied_raw_members'] if e['group']==group);assert declared==received
 assert len(root['root_copied_raw_members'])==71
 for entry in root['root_copied_raw_members']:
  source=Path(entry['copy']);raw=source.read_bytes();assert sha(raw)==entry['sha256'] and len(raw)==entry['bytes'];target=STAGE/'copied'/source.relative_to(ROOT);put(target,raw);inputs.append({'group':entry['group'],'source':str(source),'copy':str(target),'bytes':len(raw),'sha256':sha(raw)})
 capsule=(ROOT/'failure-capsule-manifest.json').read_bytes();assert sha(capsule)==manifest['failure_capsule']['sha256'];put(STAGE/'failure-capsule-manifest.json',capsule)
 old=json.loads((PUB.parent/'revised-actual-review/intake.json').read_bytes());oldhash={e['sha256'] for e in old['inputs']};actual=[e for e in inputs if e['group']=='actual'];currenthash={e['sha256'] for e in actual};assert oldhash<=currenthash
 additions=[e for e in actual if e['sha256'] not in oldhash];assert len(additions)==12
 previous_sources=json.loads((PUB.parent/'transport-review/intake.json').read_bytes());assert Counter((e['sha256'],e['bytes']) for e in previous_sources['inputs'] if e['kind']=='source')==Counter((e['sha256'],e['bytes']) for e in inputs if e['group']=='source')
 for line in (PUB.parent/'revised-actual-review/review-files.sha256').read_text(encoding='ascii').splitlines():
  h,name=line.split('  ',1);assert sha((PUB.parent/'revised-actual-review'/name).read_bytes())==h
 delta=git(['diff','--name-status',manifest['launch_commit'],FINAL]);put(STAGE/'final-docs-diff.txt',delta)
 assert all(line.split('\t')[-1].startswith(('docs/','evaluation/')) for line in delta.decode('utf-8').splitlines())
 v={'schema':'A25IndependentActualSupplementIntake/v1','final_commit':FINAL,'product_commit':manifest['product_commit'],'launch_commit':manifest['launch_commit'],'manifest_sha256':EXPECTED,'groups_verified':{'actual':34,'source':30,'supplement':6,'supervisor':1},'public_git_members_verified':6,'prior_21_raw_hashes_present':True,'additional_actual_members_by_hash':12,'new_actual_members':additions,'source_equals_previously_accepted_transport_source':True,'previous_review_hashed_members_unchanged':True,'inputs':inputs,'commands':commands,'product_platform_network_OCR_model_tests':0};put(PUB/'intake.json',enc(v));print(json.dumps({'groups':v['groups_verified'],'public_git':6,'new_actual_by_hash':12,'code_changed':False}))
if __name__=='__main__':main()
