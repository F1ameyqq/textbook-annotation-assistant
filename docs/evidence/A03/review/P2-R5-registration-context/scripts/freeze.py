# -*- coding: utf-8 -*-
"""Read-only raw Git isolation, never imports the delivery checker or products."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R5-registration-context';STAGE=OUT/'input/checkout'
WF='3f99837789a17770ea7a206667c6d2c79c9a33ce';BASE='e608b54b973b14ff55dd2c4530153f5fe7c931f4';TARGET='323013c4f0dbae75368e56db60147a8057368d1f'
EX='examples/a03/P2-R5-registration-context/';EV='docs/evidence/A03/execution/P2-R5-registration-context/';REPORT='docs/tasks/A03-P2-R5-registration-context-delivery.md'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args,data=None):return subprocess.run(['git',*args],cwd=ROOT,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
def tree(rev):
    result={}
    for row in git('ls-tree','-rz','--full-tree',rev).split(b'\0'):
        if row:
            info,name=row.split(b'\t',1);result[name.decode()]=info.decode()
    return result
def batch(specs):
    specs=sorted(set(specs));raw=git('cat-file','--batch',data=('\n'.join(specs)+'\n').encode());pos=0;result={}
    for spec in specs:
        end=raw.index(b'\n',pos);head=raw[pos:end].decode().split();pos=end+1;assert len(head)==3 and head[1]=='blob',(spec,head)
        n=int(head[2]);body=raw[pos:pos+n];pos+=n;assert raw[pos:pos+1]==b'\n';pos+=1
        assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+body).hexdigest()==head[0];result[spec]=(head[0],body)
    assert pos==len(raw);return result
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
before,after=tree(BASE),tree(TARGET);assert len(before)==28113 and all(after.get(k)==v for k,v in before.items())
added=sorted(set(after)-set(before));assert len(added)==205 and all(p.startswith((EX,EV))or p==REPORT for p in added)
seed=batch([TARGET+':'+EV+n for n in ['sha256-manifest.json','input-index.json','repair-input-index.json']])
manifest_raw=seed[TARGET+':'+EV+'sha256-manifest.json'][1];assert sha(manifest_raw)=='2bb118b00b61f1c22109e3eed37777ee5c77cf88acc9c62911e515fac65dd2f7'
manifest=json.loads(manifest_raw);index=json.loads(seed[TARGET+':'+EV+'input-index.json'][1]);repair=json.loads(seed[TARGET+':'+EV+'repair-input-index.json'][1])
assert len(manifest['files'])==204 and len(index['inputs'])==68 and len(repair['inputs'])==2
pins=index['inputs']+repair['inputs']
wfpaths=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md',
 'docs/tasks/A03-P2-R5-registration-context-review-handoff.md','docs/tasks/A03-P2-R5-registration-context-rework.md',
 'docs/tasks/A03-P2-R4-bridge-registration-coordinator-decision.md',
 'docs/evidence/coordinator/heartbeat-20261017-1044/A03-R5-delivery-preflight.json']
blobs=batch([TARGET+':'+p for p in added]+[x['commit']+':'+x['path']for x in pins]+[WF+':'+p for p in wfpaths])
assert {x['path']for x in manifest['files']}==set(added)-{EV+'sha256-manifest.json'}
for x in manifest['files']:
    oid,raw=blobs[TARGET+':'+x['path']];assert len(raw)==x['bytes']and sha(raw)==x['sha256']and after[x['path']].split()[2]==oid
assert sha(blobs[TARGET+':'+REPORT][1])=='86dd088bc109bf1243cd015d3c2f0dde9c52e2c01397574845766c7bb8208389'
assert sha(blobs[TARGET+':'+EX+'registration.py'][1])=='3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba'
assert sha(blobs[WF+':docs/tasks/A03-P2-R5-registration-context-review-handoff.md'][1])=='712f22734db2a439fa6a76931038eefa0dacbbe0c6c6a0db0366af20fdb4ae88'
for x in pins:
    oid,raw=blobs[x['commit']+':'+x['path']];assert len(raw)==x['bytes']and sha(raw)==x['sha256']and oid==x['git_blob']
    if 'copy'in x:assert raw==blobs[TARGET+':'+x['copy']][1]

exported=[];destinations={}
def export(rev,p,dest,role):
    oid,raw=blobs[rev+':'+p]
    if dest in destinations:
        assert dest.read_bytes()==raw;return
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb')as f:f.write(raw)
    destinations[dest]=True;exported.append({'commit':rev,'path':p,'file':dest.relative_to(OUT).as_posix(),'bytes':len(raw),'sha256':sha(raw),'raw_git_sha1':oid,'role':role})
for p in added:
    if p in [EV+'old-preservation.jsonl',EV+'old-tree.raw']:continue
    if p.startswith(EV+'runs/')and Path(p).name.startswith(('source-','registered-script'))and '/case-07/'not in p and '/case-07-repair-01/'not in p:continue
    export(TARGET,p,STAGE/p,'current_frozen_delivery')
for x in pins:export(x['commit'],x['path'],STAGE/x.get('copy',x['path']),'fixed_raw_input')
for p in wfpaths:export(WF,p,OUT/'input/workflow'/p,'frozen_review_workflow')
guard=[]
for p in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
    if p.is_file()and not p.is_relative_to(OUT):
        raw=p.read_bytes();guard.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
for p in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
    raw=p.read_bytes();guard.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
write(OUT/'protected-old-files.json',{'method':'file bytes only; no database opened','files':guard})
write(OUT/'input-index.json',{'workflow':WF,'base':BASE,'delivery':TARGET,'raw_input_entries_verified':70,'files':exported})
write(OUT/'delivery-byte-index.json',{'workflow':WF,'base':BASE,'delivery':TARGET,'old_git_paths_unchanged':len(before),'added_paths':len(added),'manifest_entries':204,'raw_input_entries_verified':70,
 'files':[{'path':p,'raw_git_sha1':blobs[TARGET+':'+p][0],'bytes':len(blobs[TARGET+':'+p][1]),'sha256':sha(blobs[TARGET+':'+p][1])}for p in added]})
print(json.dumps({'result':'RAW_GIT_FROZEN','old_git_paths_unchanged':len(before),'new_paths':len(added),'raw_input_entries_verified':70,'exports':len(exported),'old_files_guarded':len(guard)}))
