"""Freeze finite actual review inventory; no product or live execution."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-actual-review-20261023')
def sha(b):return hashlib.sha256(b).hexdigest()
def entry(p,kind):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b),'kind':kind}
def put(p,b):
 with p.open('xb') as f:f.write(b)
def main():
 intake=json.loads((P/'intake.json').read_bytes());rows=[]
 for p in sorted(S.rglob('*')):
  if p.is_file():rows.append(entry(p,'actual_frozen_copy_or_manifest_mapping'))
 for old in intake['reused_inputs']:
  p=Path(old['path']);item=entry(p,'reused_prior_accepted_readiness_frozen_input');assert item['sha256']==old['sha256'] and item['bytes']==old['bytes'];rows.append(item)
 for p in sorted(P.iterdir()):
  if p.is_file() and p.name not in ('raw-manifest.json','review-files.sha256'):rows.append(entry(p,'independent_report_or_static_helper'))
 assert len({x['path'] for x in rows})==len(rows)
 value={'schema':'A25IndependentFiveSaveActualRawManifest/v1','self_and_public_checksum_excluded':True,'actual_input_members':202,'reused_prior_input_members':120,'total_files':len(rows),'members':rows}
 put(P/'raw-manifest.json',(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
 public=[p for p in sorted(P.iterdir()) if p.is_file() and p.name!='review-files.sha256']
 put(P/'review-files.sha256',(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in public)).encode())
 for x in rows:
  b=Path(x['path']).read_bytes();assert sha(b)==x['sha256'] and len(b)==x['bytes']
 print(json.dumps({'status':'FIXED_AND_RELEASED','raw_files':len(rows),'public_files_plus_self':len(public)+1,'result':entry(P/'result.json','result'),'report':entry(P/'report.md','report'),'raw_manifest':entry(P/'raw-manifest.json','manifest'),'checksum':entry(P/'review-files.sha256','checksum')}))
if __name__=='__main__':main()
