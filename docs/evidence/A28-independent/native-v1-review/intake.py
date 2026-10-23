import hashlib,json
from pathlib import Path
R=Path('D:/1800/.local/stages/a28-complete-lesson-production-20261023/root-native-delivery-01')
P=Path('D:/1800/.local/stages/a28-independent-20261023/native-v1-review')
O=Path('D:/1800/docs/evidence/A28-independent/native-v1-review')
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
b=(R/'root-index.json').read_bytes();assert sha(b)=='4d7f11206df99ed81444ab78ad1e491b4945e77f2bfbe947cb6c9526debb1625'
j=json.loads(b);assert len(j['members'])==276;put(P/'root-index.json',b);rows=[]
for row in j['members']:
 source=Path(row['root_frozen']);assert source.parent==R
 raw=source.read_bytes();assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
 target=P/'inputs'/source.name;put(target,raw);rows.append({**row,'copy':str(target)})
put(O/'intake.json',(json.dumps({'schema':'A28IndependentNativeIntake/v1','status':'PASS','root_raw_pairs':276,'root_index_sha256':sha(b),'members':rows,'active_sources_read':0},ensure_ascii=False,indent=2)+'\n').encode('utf8'))
print(json.dumps({'status':'PASS','root_raw_pairs':276}))
