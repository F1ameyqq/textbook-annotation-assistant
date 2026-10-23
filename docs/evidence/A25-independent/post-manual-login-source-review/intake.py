"""Exact-byte isolation of the frozen current-source packet only."""
import hashlib,json
from pathlib import Path
PUB=Path(__file__).resolve().parent
FROZEN=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/post-manual-login-source-frozen')
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/post-manual-login-source-review-20261023')
MANIFEST='64e9da291eeaa24648b74231d5aba159b3e9c8d9e3bc22c962ada1b857bd3709'
CHECKPOINT='16b48db5a0e5443d49c7a340e08cee34e63a541ca5c48fa145bdb6e39901f3ca'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def main():
 STAGE.mkdir(exist_ok=False);raw=(FROZEN/'manifest.json').read_bytes();assert sha(raw)==MANIFEST;m=json.loads(raw);assert m['count']==len(m['members'])==62 and m['checkpoint_sha256']==CHECKPOINT;put(STAGE/'manifest.json',raw);rows=[]
 for e in m['members']:
  parts=Path(e['path']).parts;rel=Path(*parts[parts.index('post-manual-login-source')+1:]);assert '..' not in rel.parts
  source=FROZEN/'raw'/rel;raw=source.read_bytes();assert len(raw)==e['bytes'] and sha(raw)==e['sha256'];target=STAGE/'raw'/rel;put(target,raw);rows.append({'source':str(source),'copy':str(target),'bytes':len(raw),'sha256':sha(raw)})
 assert sha((STAGE/'raw/checkpoint-current-source.json').read_bytes())==CHECKPOINT
 value={'schema':'A25IndependentCurrentSourceIntake/v1','manifest_sha256':MANIFEST,'checkpoint_sha256':CHECKPOINT,'raw_members':62,'manifest_self':1,'inputs':rows,'author_active_candidate_tree_reads':0,'product_or_platform_OCR_execution':0};put(PUB/'intake.json',enc(value));print(json.dumps({'verified_raw_members':62,'manifest_self':1,'checkpoint_sha256':CHECKPOINT}))
if __name__=='__main__':main()
