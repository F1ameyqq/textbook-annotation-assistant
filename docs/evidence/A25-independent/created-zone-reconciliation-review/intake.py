"""Isolate the declared 87-member incremental frozen packet only."""
import difflib,hashlib,json
from pathlib import Path,PureWindowsPath
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/created-zone-reconciliation-review-20261023')
R=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/created-zone-reconciliation-root-frozen')
REPO=PureWindowsPath('C:/Users/ASUS/.codex/worktrees/b-latest-20261023/1800')
OLD=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-readiness-review-20261023')
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def main():
 S.mkdir(exist_ok=False);mb=(R/'manifest.json').read_bytes();ib=(R/'root-index.json').read_bytes()
 assert sha(mb)=='271c7ca122beeba5511b08619d9dc6cc356d777363eaf1051f372b9205d667b7' and sha(ib)=='cad9723ff924f5e29dabd96297bb2dfcc2b3056507e1bd8b28a37109ae34fff2'
 m=json.loads(mb);ix=json.loads(ib);assert m['product_commit']=='389d2e7a282d21efa25db8d01c02d115ce9e83b7' and len(m['members'])==len(ix['members'])==87
 put(S/'manifest.json',mb);put(S/'root-index.json',ib);registry={};inputs=[];git=0;diffs={}
 for a,e in zip(m['members'],ix['members']):
  assert all(e[k]==v for k,v in a.items());source=Path(e['root_frozen_path']);assert source.parent==R/'raw';b=source.read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes']
  original=PureWindowsPath(e['source_path'])
  if 'git_blob_sha256' in e:
   assert sha(b)==e['git_blob_sha256'];rel=original.relative_to(REPO);target=S/'snapshot'/Path(*rel.parts);git+=1
   prior=OLD/'snapshot'/Path(*rel.parts)
   if prior.exists() and prior.read_bytes()!=b:diffs[rel.as_posix()]=''.join(difflib.unified_diff(prior.read_text(encoding='utf-8').splitlines(True),b.decode('utf-8').splitlines(True),fromfile='accepted8990',tofile='frozen389d'))
  else:target=S/'raw'/source.name
  put(target,b);key=original.as_posix().lower();assert key not in registry;registry[key]=str(target);inputs.append({'original':str(original),'copy':str(target),'root_frozen_source':str(source),'bytes':len(b),'sha256':sha(b)})
 assert git==24
 cp=next(Path(v) for k,v in registry.items() if k.endswith('/checkpoint-created-zone-reconciliation.json'));assert sha(cp.read_bytes())=='d71016829898da16b8c56fd2d9f2b321e0511be5aa499584eef0c306bbceee33'
 put(S/'registry.json',enc(registry));put(P/'intake.json',enc({'schema':'A25ReconciliationIndependentIntake/v1','raw_members':87,'git_blob_members':24,'manifest_sha256':sha(mb),'index_sha256':sha(ib),'checkpoint_sha256':sha(cp.read_bytes()),'inputs':inputs,'existing_product_delta_paths':list(diffs),'active_author_or_real_profile_ledger_platform_reads':0}));put(P/'product-diff.txt','\n'.join(diffs.values()).encode('utf-8'))
 print(json.dumps({'members':87,'git_blob_members':24,'changed_existing_product_paths':list(diffs),'isolated':True}))
if __name__=='__main__':main()
