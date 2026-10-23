"""Copy the declared frozen TLS-only matrix. Never execute its script."""
import hashlib,json
from pathlib import Path
PUB=Path(__file__).resolve().parent
FROZEN=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/tls-client-diagnostic-frozen')
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/tls-client-diagnostic-review-20261023')
EXPECTED_MANIFEST='c3bb08190dc000b8ba746a5aaa05860c4d083ea737bcba0d5f744ca907700810'
EXPECTED_CHECKPOINT='add532eb7a0e386bb452fd444f5195c71857df2cec684b33a6983628cd28c537'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def main():
 STAGE.mkdir(exist_ok=False);raw=(FROZEN/'manifest.json').read_bytes();assert sha(raw)==EXPECTED_MANIFEST;manifest=json.loads(raw);put(STAGE/'manifest.json',raw);assert manifest['count']==len(manifest['members'])==18;inputs=[]
 for entry in manifest['members']:
  parts=Path(entry['path']).parts;rel=Path(*parts[parts.index('tls-client-diagnostic')+1:]);assert '..' not in rel.parts
  source=FROZEN/rel;raw=source.read_bytes();assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256'];target=STAGE/'raw'/rel;put(target,raw);inputs.append({'source':str(source),'copy':str(target),'bytes':len(raw),'sha256':sha(raw)})
 checkpoint=(STAGE/'raw/checkpoint.json').read_bytes();assert sha(checkpoint)==EXPECTED_CHECKPOINT==manifest['checkpoint_sha256']
 put(PUB/'intake.json',enc({'schema':'A25IndependentTLSMatrixIntake/v1','checkpoint_sha256':EXPECTED_CHECKPOINT,'manifest_sha256':EXPECTED_MANIFEST,'raw_members':18,'manifest_self':1,'inputs':inputs,'active_author_directory_reads':0,'network_or_product_execution':0}));print(json.dumps({'raw_members':18,'manifest_self':1,'checkpoint_sha256':EXPECTED_CHECKPOINT}))
if __name__=='__main__':main()
