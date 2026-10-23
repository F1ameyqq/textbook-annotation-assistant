# -*- coding: utf-8 -*-
"""Isolate the subsequently supplied 76-member readback data package only."""
import hashlib,json
from pathlib import Path,PureWindowsPath
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/final-recovery-actual-review-20261023/export')
R=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/readback-data-export-final-root-frozen')
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def main():
 S.mkdir(exist_ok=False);mb=(R/'manifest.json').read_bytes();ib=(R/'root-index.json').read_bytes()
 assert sha(mb)=='2b44c551610c07983e55c8cf90e5ee7dd1e94e551dddaf1ac83a7d810a9b37e8' and sha(ib)=='b2efbfbd2a4ac61141189eb3e135166ec54ccbeb32f7851ce30410db5858acb2'
 m=json.loads(mb);ix=json.loads(ib);assert len(m['members'])==len(ix['members'])==76;put(S/'manifest.json',mb);put(S/'root-index.json',ib);registry={};inputs=[]
 for a,e in zip(m['members'],ix['members']):
  assert all(e[k]==v for k,v in a.items());source=Path(e['root_frozen_path']);assert source.parent==R;b=source.read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'];target=S/'raw'/source.name;put(target,b);key=PureWindowsPath(e['source_path']).as_posix().lower();assert key not in registry;registry[key]=str(target);inputs.append({'original':e['source_path'],'copy':str(target),'sha256':sha(b),'bytes':len(b)})
 put(S/'registry.json',enc(registry));put(P/'export-intake.json',enc({'schema':'A25IndependentFiveReaderExportIntake/v1','raw_members':76,'manifest_sha256':sha(mb),'index_sha256':sha(ib),'inputs':inputs,'platform_or_OCR_or_original_source_reads':0}));print(json.dumps({'verified_export_members':76}))
if __name__=='__main__':main()
