# -*- coding: utf-8 -*-
"""Freeze the declared 28-member recovery preparation packet for static review."""
import hashlib,json
from pathlib import Path,PureWindowsPath
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/final-recovery-preparation-review-20261023')
R=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/final-recovery-preparation-root-frozen')
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def main():
 S.mkdir(exist_ok=False);mb=(R/'manifest.json').read_bytes();ib=(R/'root-index.json').read_bytes()
 assert sha(mb)=='2f8b5b76602e353d04c3bcbe8dfaf1d1738fb4c98a883df685dae06445d5aa47' and sha(ib)=='7966b1caf965146635cd5d1fd717a6a3200cc504ef58680e2cea2f3fa12b94e2'
 m=json.loads(mb);ix=json.loads(ib);assert len(m['members'])==len(ix['members'])==28 and m['product_commit']=='389d2e7a282d21efa25db8d01c02d115ce9e83b7'
 put(S/'manifest.json',mb);put(S/'root-index.json',ib);registry={};inputs=[]
 for a,e in zip(m['members'],ix['members']):
  assert all(e[k]==v for k,v in a.items());source=Path(e['root_frozen_path']);assert source.parent==R;b=source.read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'];target=S/'raw'/source.name;put(target,b);key=PureWindowsPath(e['source_path']).as_posix().lower();assert key not in registry;registry[key]=str(target);inputs.append({'original':e['source_path'],'copy':str(target),'root_frozen_source':str(source),'sha256':sha(b),'bytes':len(b)})
 plan=next(Path(v) for k,v in registry.items() if k.endswith('/final-recovery-preparation/recovery-plan.json'));assert sha(plan.read_bytes())=='cd89a2990fbaadf395185a757db9e8848f5821e9dd7cdbc7ccb35b59d83dbc77'
 put(S/'registry.json',enc(registry));put(P/'intake.json',enc({'schema':'A25FinalRecoveryPreparationIndependentIntake/v1','raw_members':28,'manifest_sha256':sha(mb),'root_index_sha256':sha(ib),'recovery_plan_sha256':sha(plan.read_bytes()),'inputs':inputs,'active_author_original_profile_ledger_or_platform_reads':0}));print(json.dumps({'verified_members':28,'recovery_plan_sha256':sha(plan.read_bytes())}))
if __name__=='__main__':main()
