# -*- coding: utf-8 -*-
"""Isolate only the declared 55 root-frozen final-two actual inputs."""
import hashlib,json
from pathlib import Path,PureWindowsPath
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/remaining-two-actual-review-20261023')
R=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/remaining-two-actual-root-frozen')
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def main():
 S.mkdir(exist_ok=False);mb=(R/'manifest.json').read_bytes();ib=(R/'root-index.json').read_bytes()
 assert sha(mb)=='1daeb71c2c88b9ff4d36b525b558572dd2de5a8244044cf7657649ccb5ac6c56' and sha(ib)=='803ab34adcc37f5e51952be81f11182955976abdfc1f8658011dc654700666ac'
 m=json.loads(mb);ix=json.loads(ib);assert len(m['members'])==len(ix['members'])==55 and m['product_commit']=='389d2e7a282d21efa25db8d01c02d115ce9e83b7'
 put(S/'manifest.json',mb);put(S/'root-index.json',ib);registry={};inputs=[]
 for a,e in zip(m['members'],ix['members']):
  assert all(e[k]==v for k,v in a.items());source=Path(e['root_frozen_path']);assert source.parent==R;b=source.read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'];target=S/'raw'/source.name;put(target,b);key=PureWindowsPath(e['source_path']).as_posix().lower();assert key not in registry;registry[key]=str(target);inputs.append({'original':e['source_path'],'copy':str(target),'root_frozen_source':str(source),'sha256':sha(b),'bytes':len(b)})
 cp=next(Path(v) for k,v in registry.items() if k.endswith('/checkpoint-remaining-two-actual.json'));assert sha(cp.read_bytes())=='ad819727e059a83662f7e5d934f6f26db73614fd33268813ca9d159c71de78d0'
 put(S/'registry.json',enc(registry));put(P/'intake.json',enc({'schema':'A25FinalTwoActualIndependentIntake/v1','manifest_sha256':sha(mb),'root_index_sha256':sha(ib),'checkpoint_sha256':sha(cp.read_bytes()),'raw_members':55,'inputs':inputs,'source_policy':'Only declared root-frozen bytes; source_path strings are not opened','real_profile_ledger_active_author_or_platform_reads':0}));print(json.dumps({'verified_raw_members':55,'checkpoint_sha256':sha(cp.read_bytes())}))
if __name__=='__main__':main()
