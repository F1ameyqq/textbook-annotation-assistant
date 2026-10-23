"""Copy only the 202 declared root-frozen actual members into reviewer isolation."""
import hashlib,json
from pathlib import Path,PureWindowsPath
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-actual-review-20261023')
R=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/five-save-actual-root-frozen')
PREVIOUS=Path('D:/1800/docs/evidence/A25-independent/five-save-readiness-review')
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def main():
 S.mkdir(exist_ok=False);mraw=(R/'manifest.json').read_bytes();iraw=(R/'root-index.json').read_bytes()
 assert sha(mraw)=='a72cc4a6d4f63c6eb2d3e5393ad031d38a9fb12d2d97cbf81771871dcd131eae'
 assert sha(iraw)=='e6e5f33af06b98fab55e494acf6b879bf3b09cb57d48d943323d7e45f0fade9a'
 m=json.loads(mraw);index=json.loads(iraw);assert len(m['members'])==len(index['members'])==202
 assert m['product_commit']=='8990e1e3c7561bc7403eb29359f0d39ba3a54295' and m['authority_id']=='ab2ca4a8-08bb-44ad-b8a9-4154d08d0a74'
 put(S/'manifest.json',mraw);put(S/'root-index.json',iraw);inputs=[];registry={}
 for item,entry in zip(m['members'],index['members']):
  assert all(entry[k]==v for k,v in item.items());source=Path(entry['root_frozen_path']);assert source.parent==R/'raw'
  raw=source.read_bytes();assert sha(raw)==entry['sha256'] and len(raw)==entry['bytes'];target=S/'raw'/source.name;put(target,raw)
  key=PureWindowsPath(entry['source_path']).as_posix().lower();assert key not in registry;registry[key]=str(target)
  inputs.append({'original':entry['source_path'],'root_frozen_source':str(source),'copy':str(target),'bytes':len(raw),'sha256':sha(raw)})
 # Read prior accepted reviewer copies only, with their fixed integrity inventory.
 prior=(PREVIOUS/'raw-manifest.json').read_bytes();assert sha(prior)=='78469881ee0826b0ebc7bc949dc7222e0795c34c51ac6159439dbe3d770d05db'
 prior_manifest=json.loads(prior);reused=[]
 for item in prior_manifest['members']:
  p=Path(item['path'])
  if 'five-save-readiness-review-20261023' in str(p) and any(x in str(p) for x in ('snapshot','project')):
   raw=p.read_bytes();assert sha(raw)==item['sha256'] and len(raw)==item['bytes'];reused.append(item)
 assert len(reused)==120
 put(S/'registry.json',enc(registry));put(P/'intake.json',enc({'schema':'A25IndependentFiveSaveActualIntake/v1','primary_manifest_sha256':sha(mraw),'root_index_sha256':sha(iraw),'raw_members':202,'inputs':inputs,'reused_prior_frozen_readiness_files':120,'prior_raw_manifest_sha256':sha(prior),'reused_inputs':reused,'no_active_author_profile_ledger_or_platform_reads':True}))
 cp=next(Path(v) for k,v in registry.items() if k.endswith('/checkpoint-five-save-actual.json'));assert sha(cp.read_bytes())=='1af6ad4a4e15081586c4057f51c286d34bc621d5db53937fdfe5189b7dce4504'
 print(json.dumps({'actual_raw_verified':202,'reused_fixed_files_verified':120,'checkpoint_sha256':sha(cp.read_bytes())}))
if __name__=='__main__':main()
