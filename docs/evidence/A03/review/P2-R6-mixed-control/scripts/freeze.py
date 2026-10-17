# -*- coding: utf-8 -*-
"""Raw Git byte export only, no checker/product import."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R6-mixed-control';STAGE=OUT/'input/checkout'
WF='fbf7792b20f212f1d3b2a329cddba502fcfdc1b4';BASE='323013c4f0dbae75368e56db60147a8057368d1f';TARGET='81d3ec7e42e0a1a76ad744bf59536fc5f68adee4'
EX='examples/a03/P2-R6-mixed-control/';EV='docs/evidence/A03/execution/P2-R6-mixed-control/';REPORT='docs/tasks/A03-P2-R6-mixed-control-delivery.md'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a,data=None):return subprocess.run(['git',*a],cwd=ROOT,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
def tree(rev):
    result={}
    for row in git('ls-tree','-rz','--full-tree',rev).split(b'\0'):
        if row:
            info,name=row.split(b'\t',1);result[name.decode()]=info.decode()
    return result
def batch(specs):
    specs=sorted(set(specs));raw=git('cat-file','--batch',data=('\n'.join(specs)+'\n').encode());pos=0;result={}
    for spec in specs:
        end=raw.index(b'\n',pos);head=raw[pos:end].decode().split();pos=end+1;assert len(head)==3 and head[1]=='blob'
        n=int(head[2]);b=raw[pos:pos+n];pos+=n;assert raw[pos:pos+1]==b'\n';pos+=1
        assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==head[0];result[spec]=(head[0],b)
    assert pos==len(raw);return result
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
before,after=tree(BASE),tree(TARGET);assert len(before)==28318 and all(after.get(k)==v for k,v in before.items())
added=sorted(set(after)-set(before));assert len(added)==93 and all(p.startswith((EX,EV))or p==REPORT for p in added)
seed=batch([TARGET+':'+EV+p for p in ['sha256-manifest.json','raw-input-pins.json']])
manifest_raw=seed[TARGET+':'+EV+'sha256-manifest.json'][1];assert sha(manifest_raw)=='7f8f17697370b0398af58d178bc0af18f6d9cc1e640c73ae7949907ca95ef3e8'
manifest=json.loads(manifest_raw);pins=json.loads(seed[TARGET+':'+EV+'raw-input-pins.json'][1])['inputs'];assert len(manifest['files'])==92 and len(pins)==46
wfpaths=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md',
 'docs/tasks/A03-P2-R6-mixed-control-review-handoff.md','docs/tasks/A03-P2-R6-mixed-control-rework.md',
 'docs/tasks/A03-P2-R5-registration-context-coordinator-decision.md','docs/tasks/A03-P2-R5-registration-context-review-report.md',
 'docs/evidence/coordinator/heartbeat-20261017-1129/A03-R6-delivery-preflight.json']
blobs=batch([TARGET+':'+p for p in added]+[x['commit']+':'+x['path']for x in pins]+[WF+':'+p for p in wfpaths])
assert {x['path']for x in manifest['files']}==set(added)-{EV+'sha256-manifest.json'}
for x in manifest['files']:
    oid,b=blobs[TARGET+':'+x['path']];assert len(b)==x['bytes']and sha(b)==x['sha256']and after[x['path']].split()[2]==oid
assert sha(blobs[TARGET+':'+REPORT][1])=='efe831c7f11e7251e1f0cb9b78f66b72baa0ae7b9f630d1718bfe3aa9518e400'
assert sha(blobs[WF+':docs/tasks/A03-P2-R6-mixed-control-review-handoff.md'][1])=='47b7a464ab95689d9bc7fb91fa0d498c4079ef072c500c968b58e9713304d5d7'
for x in pins:
    oid,b=blobs[x['commit']+':'+x['path']];assert len(b)==x['bytes']and sha(b)==x['sha256']and oid==x['git_blob']
    if 'copy'in x:assert b==blobs[TARGET+':'+x['copy']][1]
exports=[];destinations={}
def export(rev,p,dest,role):
    oid,b=blobs[rev+':'+p]
    if dest in destinations:assert dest.read_bytes()==b;return
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb')as f:f.write(b)
    destinations[dest]=True;exports.append({'commit':rev,'path':p,'file':dest.relative_to(OUT).as_posix(),'bytes':len(b),'sha256':sha(b),'raw_git_sha1':oid,'role':role})
for p in added:
    if p.startswith(EV+'runs/')and Path(p).name.startswith(('source-','registered-script'))and '/entry-01/'not in p and '/entry-02/'not in p:continue
    export(TARGET,p,STAGE/p,'current_frozen_delivery')
for x in pins:export(x['commit'],x['path'],STAGE/x.get('copy',x['path']),'fixed_raw_input')
for p in wfpaths:export(WF,p,OUT/'input/workflow'/p,'frozen_review_workflow')
guard=[]
for p in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
    if p.is_file()and not p.is_relative_to(OUT):
        b=p.read_bytes();guard.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b)})
for p in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
    b=p.read_bytes();guard.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b)})
write(OUT/'protected-old-files.json',{'method':'raw bytes only; no database opened','files':guard})
write(OUT/'input-index.json',{'workflow':WF,'base':BASE,'delivery':TARGET,'raw_input_entries_verified':46,'files':exports})
write(OUT/'delivery-byte-index.json',{'workflow':WF,'base':BASE,'delivery':TARGET,'old_git_paths_unchanged':len(before),'added_paths':93,'manifest_entries':92,'raw_input_entries_verified':46,
 'files':[{'path':p,'raw_git_sha1':blobs[TARGET+':'+p][0],'bytes':len(blobs[TARGET+':'+p][1]),'sha256':sha(blobs[TARGET+':'+p][1])}for p in added]})
print(json.dumps({'result':'RAW_GIT_FROZEN','old_paths_unchanged':len(before),'new_paths':93,'raw_inputs_verified':46,'exports':len(exports),'old_files_guarded':len(guard)}))
