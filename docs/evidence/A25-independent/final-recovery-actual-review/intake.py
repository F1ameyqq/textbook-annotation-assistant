# -*- coding: utf-8 -*-
"""Isolate exactly 110 declared frozen actual members; original paths are not opened."""
import hashlib,json
from pathlib import Path,PureWindowsPath
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/final-recovery-actual-review-20261023')
R=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/final-recovery-actual-root-frozen')
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def main():
 S.mkdir(exist_ok=False);mb=(R/'manifest.json').read_bytes();ib=(R/'root-index.json').read_bytes()
 assert sha(mb)=='f7e3c6121489e769d36be010dfe02669e2866b7545fb0a5e5770c391be97d3fe' and sha(ib)=='b5a3999f8ad9ef4efebf12d187aa830ec0ba0ed3ffdc61390602613bc7ef99b6'
 m=json.loads(mb);ix=json.loads(ib);assert len(m['members'])==len(ix['members'])==110 and m['product_commit']=='389d2e7a282d21efa25db8d01c02d115ce9e83b7'
 put(S/'manifest.json',mb);put(S/'root-index.json',ib);registry={};inputs=[]
 for a,e in zip(m['members'],ix['members']):
  assert all(e[k]==v for k,v in a.items());source=Path(e['root_frozen_path']);assert source.parent==R;b=source.read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'];target=S/'raw'/source.name;put(target,b);key=PureWindowsPath(e['source_path']).as_posix().lower();assert key not in registry;registry[key]=str(target);inputs.append({'original':e['source_path'],'copy':str(target),'root_frozen_source':str(source),'bytes':len(b),'sha256':sha(b)})
 cp=next(Path(v) for k,v in registry.items() if k.endswith('/checkpoint-final-recovery-actual.json'));assert sha(cp.read_bytes())=='dc07a795ad20eda4ed5be56e8a4e52f85d575934e6cc441d5788e86daca89f9d'
 put(S/'registry.json',enc(registry));put(P/'intake.json',enc({'schema':'A25IndependentFinalActualIntake/v1','raw_members':110,'manifest_sha256':sha(mb),'root_index_sha256':sha(ib),'checkpoint_sha256':sha(cp.read_bytes()),'inputs':inputs,'active_author_profile_ledger_platform_reads':0}));print(json.dumps({'verified_members':110,'checkpoint_sha256':sha(cp.read_bytes())}))
if __name__=='__main__':main()
