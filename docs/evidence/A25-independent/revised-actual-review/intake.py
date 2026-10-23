"""Copy only the declared immutable actual checkpoint and its 21 raw members."""
import hashlib,json
from pathlib import Path
PUB=Path(__file__).resolve().parent
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/revised-actual-review-20261023')
CHECKPOINT=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/transport-revision/next-live/checkpoint-fixed-failure.json')
EXPECTED='1b1a98a1a4ac1fa90e74d9dc79aec521531cda461106affe7424d8340e4ab22b'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def main():
 STAGE.mkdir(exist_ok=False);raw=CHECKPOINT.read_bytes();assert sha(raw)==EXPECTED;checkpoint=json.loads(raw);put(STAGE/'checkpoint-fixed-failure.json',raw);inputs=[]
 assert len(checkpoint['raw_members'])==21
 for entry in checkpoint['raw_members']:
  source=Path(entry['path']);rel=source.relative_to(CHECKPOINT.parent);raw=source.read_bytes();assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256'];target=STAGE/'raw'/rel;put(target,raw);inputs.append({'source':str(source),'copy':str(target),'bytes':len(raw),'sha256':sha(raw)})
 previous=PUB.parent/'transport-review';receipt=json.loads((previous/'intake.json').read_bytes());source_count=0
 for entry in receipt['inputs']:
  if entry['kind']=='source':
   raw=Path(entry['copy']).read_bytes();assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256'];source_count+=1
 for line in (previous/'transport-review-files.sha256').read_text(encoding='ascii').splitlines():
  h,name=line.split('  ',1);assert sha((previous/name).read_bytes())==h
 value={'schema':'A25IndependentRevisedActualIntake/v1','checkpoint_source':str(CHECKPOINT),'checkpoint_copy':str(STAGE/'checkpoint-fixed-failure.json'),'checkpoint_sha256':EXPECTED,'raw_members_verified':len(inputs),'previous_frozen_source_reverified':source_count,'previous_review_members_unchanged':True,'inputs':inputs,'product_tests':0,'platform_actions':0,'active_author_worktree_reads':0};put(PUB/'intake.json',enc(value));print(json.dumps({'raw_members_verified':len(inputs),'previous_sources':source_count,'checkpoint_sha256':EXPECTED}))
if __name__=='__main__':main()
