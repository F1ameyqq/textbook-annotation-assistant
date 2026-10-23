"""Isolate the 120 root-frozen readiness inputs, preserving exact bytes."""
import hashlib,json
from pathlib import Path,PureWindowsPath
PUB=Path(__file__).resolve().parent
ROOT=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/five-save-readiness-root-frozen')
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-readiness-review-20261023')
REPO=PureWindowsPath('C:/Users/ASUS/.codex/worktrees/b-latest-20261023/1800')
PROJECT=PureWindowsPath('D:/1800/.local/stages/a25-lesson2-expansion-20261023')
MANIFEST='128ee3d8e9eb00b0dc033c03b7654f1613fbad83dfeb05713f7e64eb4776ff67'
INDEX='a449b051023a5d00ca5e8c5d189521e0b2eb594c863cf34fa0072c4dcf840e61'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def main():
 STAGE.mkdir(exist_ok=False);mraw=(ROOT/'manifest.json').read_bytes();iraw=(ROOT/'root-index.json').read_bytes();assert sha(mraw)==MANIFEST and sha(iraw)==INDEX;m=json.loads(mraw);index=json.loads(iraw);put(STAGE/'manifest.json',mraw);put(STAGE/'root-index.json',iraw)
 assert m['product_commit']==index['product_commit']=='8990e1e3c7561bc7403eb29359f0d39ba3a54295' and len(m['members'])==len(index['members'])==120
 inputs=[];registry={};git_count=0
 for a,e in zip(m['members'],index['members']):
  assert all(e[k]==v for k,v in a.items());source=Path(e['root_frozen_path']);assert source.is_relative_to(ROOT/'raw');raw=source.read_bytes();assert sha(raw)==e['sha256'] and len(raw)==e['bytes'];original=PureWindowsPath(e['source_path'])
  try:rel=original.relative_to(REPO);target=STAGE/'snapshot'/Path(*rel.parts);kind='product';assert sha(raw)==e['git_blob_sha256'];git_count+=1
  except ValueError:rel=original.relative_to(PROJECT);target=STAGE/'project'/Path(*rel.parts);kind='private'
  put(target,raw);registry[original.as_posix().lower()]=str(target);inputs.append({'original':str(original),'root_frozen_source':str(source),'copy':str(target),'kind':kind,'bytes':len(raw),'sha256':sha(raw)})
 assert git_count==23
 cp=STAGE/'project/post-manual-login-source/checkpoint-five-save-readiness.json';targets=STAGE/'project/post-manual-login-source/five-candidates-v2/targets.json'
 assert sha(cp.read_bytes())=='7f459e57b8c8d8b9b59a3c2c5b6b3ca162a3b5f2944f8392461acfcc014c4d70' and sha(targets.read_bytes())=='eb3b29c28c80650674f7df24e523dcc7c05e27b6713eda78dec92910b074d792'
 put(STAGE/'registry.json',enc(registry));put(PUB/'intake.json',enc({'schema':'A25IndependentFiveSaveReadinessIntake/v1','product_commit':m['product_commit'],'manifest_sha256':MANIFEST,'root_index_sha256':INDEX,'raw_members':120,'root_provided_git_blob_members_verified':23,'inputs':inputs,'registry':str(STAGE/'registry.json'),'active_author_or_platform_reads':0}));print(json.dumps({'raw_members':120,'git_blob_members':23,'verified':True}))
if __name__=='__main__':main()
