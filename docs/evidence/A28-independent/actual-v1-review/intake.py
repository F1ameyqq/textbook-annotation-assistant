import hashlib,json
from pathlib import Path
B=Path('D:/1800/.local/stages/a28-complete-lesson-production-20261023')
P=Path('D:/1800/.local/stages/a28-independent-20261023/actual-v1-review')
O=Path('D:/1800/docs/evidence/A28-independent/actual-v1-review')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(p,raw):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
manifest=(B/'fixed-production-actual-01/raw-manifest.json').read_bytes()
actual=(B/'production-actual-fixed.json').read_bytes()
assert sha(manifest)=='d81fc12ee2a2d8bf106835f77a04057648584e951fb8a0dea39b1873113c0d75'
assert sha(actual)=='ef96bef35658cb61c9030981b6db5525de00098178b32719888c64f9543a493e'
write(P/'raw-manifest.json',manifest);write(P/'production-actual-fixed.json',actual)
rows=json.loads(manifest)['members'];assert len(rows)==304
records=[]
for row in rows:
 source=Path(row['frozen_path']);assert source.parent==B/'fixed-production-actual-01'
 raw=source.read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
 target=P/'inputs'/source.name;write(target,raw);records.append({**row,'copy':str(target)})
result={'schema':'A28IndependentActualIntake/v1','status':'PASS_FROZEN_BYTES','members_verified':304,
 'raw_manifest_sha256':sha(manifest),'actual_delivery_sha256':sha(actual),'members':records,'active_source_reads':0}
write(O/'intake.json',(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
print(json.dumps({'status':result['status'],'members':304}))
