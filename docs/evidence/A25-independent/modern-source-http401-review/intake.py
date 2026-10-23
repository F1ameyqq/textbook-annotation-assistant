"""Copy only the two declared frozen packets. No runtime/product imports."""
import hashlib,json
from pathlib import Path
PUB=Path(__file__).resolve().parent
BASE=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023')
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/modern-source-http401-review-20261023')
PACKETS=[('actual','modern-source-http401-frozen','source-live','checkpoint-http401.json','0cc09b14db9f7cdd03e141e7b619a4dfc69c71615ff8cbce1610125fc6a20a22','8c6ee5e6de171ab537071c55406014667ac4e8f5c189176e51e7bd9644d319de',26),('runtime','runtime-py312-frozen','runtime-py312','checkpoint.json','bf68beff4671bed8890981829ced17a47769cd2ce049214fd8636b8752bef358','0041f98318fad2200f4eb6cd817bd14621bd420e7d4ea87c033d4ef83a70ec2e',18)]
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def main():
 STAGE.mkdir(exist_ok=False);inputs=[];packets=[]
 for label,name,anchor,checkpoint,checkhash,manhash,count in PACKETS:
  frozen=BASE/name;manraw=(frozen/'manifest.json').read_bytes();assert sha(manraw)==manhash;manifest=json.loads(manraw);assert len(manifest['members'])==manifest['count']==count and manifest['checkpoint_sha256']==checkhash;put(STAGE/label/'manifest.json',manraw)
  checkraw=(frozen/checkpoint).read_bytes();assert sha(checkraw)==checkhash
  for entry in manifest['members']:
   parts=Path(entry['path']).parts;rel=Path(*parts[parts.index(anchor)+1:]);assert '..' not in rel.parts
   source=(frozen/'raw'/rel) if label=='actual' else (frozen/rel);raw=source.read_bytes();assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256'];target=STAGE/label/'raw'/rel;put(target,raw);inputs.append({'packet':label,'source':str(source),'copy':str(target),'bytes':len(raw),'sha256':sha(raw)})
  assert (STAGE/label/'raw'/checkpoint).read_bytes()==checkraw
  packets.append({'packet':label,'frozen_root':str(frozen),'checkpoint_sha256':checkhash,'manifest_sha256':manhash,'members':count,'manifest_self':1})
 value={'schema':'A25IndependentModernHTTP401Intake/v1','packets':packets,'inputs':inputs,'active_author_or_authentication_directory_reads':0,'product_or_network_execution':0};put(PUB/'intake.json',enc(value));print(json.dumps({'actual_members':26,'runtime_members':18,'manifest_self':2,'verified':True}))
if __name__=='__main__':main()
