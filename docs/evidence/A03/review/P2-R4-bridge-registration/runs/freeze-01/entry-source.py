"""Raw Git export and byte guards only; never imports delivery/product code."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R4-bridge-registration';STAGE=OUT/'input/checkout'
WF='cb6b8336555e52deaf129c0c1eccf27ea830d098';BASE='87606b73e0754fa670491d9fb958a416c26bfe88';TARGET='e608b54b973b14ff55dd2c4530153f5fe7c931f4'
EX='examples/a03/P2-R4-bridge-registration/';EV='docs/evidence/A03/execution/P2-R4-bridge-registration/';REPORT='docs/tasks/A03-P2-R4-bridge-registration-delivery.md'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args,data=None):return subprocess.run(['git',*args],cwd=ROOT,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
def tree(rev):
    result={}
    for row in git('ls-tree','-rz','--full-tree',rev).split(b'\0'):
        if not row:continue
        info,name=row.split(b'\t',1);result[name.decode()]=info.decode()
    return result
def batch(specs):
    specs=sorted(set(specs));raw=git('cat-file','--batch',data=('\n'.join(specs)+'\n').encode());pos=0;result={}
    for spec in specs:
        end=raw.index(b'\n',pos);head=raw[pos:end].decode().split();pos=end+1;assert len(head)==3 and head[1]=='blob',(spec,head)
        n=int(head[2]);body=raw[pos:pos+n];pos+=n;assert raw[pos:pos+1]==b'\n';pos+=1
        assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+body).hexdigest()==head[0]
        result[spec]=(head[0],body)
    assert pos==len(raw);return result
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
before,after=tree(BASE),tree(TARGET)
assert all(after.get(k)==v for k,v in before.items())and len(before)==28002
added=sorted(set(after)-set(before));assert len(added)==111 and all(p.startswith((EX,EV))or p==REPORT for p in added)
seed=batch([TARGET+':'+EV+n for n in ['sha256-manifest.json','input-index.json','resource-input-pins.json']])
manifest_raw=seed[TARGET+':'+EV+'sha256-manifest.json'][1]
assert sha(manifest_raw)=='5c5823f1b146574202fbfd00e066aafc1697d017e40c12cab66b9330cb75d28e'
manifest=json.loads(manifest_raw);assert len(manifest['files'])==110
index=json.loads(seed[TARGET+':'+EV+'input-index.json'][1]);resources=json.loads(seed[TARGET+':'+EV+'resource-input-pins.json'][1])['inputs']
sources=index['documents']+index['product_text']+index['reused_inputs']+resources;assert len(sources)==38
wfpaths=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md',
 'docs/tasks/A03-P2-R4-bridge-registration-review-handoff.md','docs/tasks/A03-P2-R4-bridge-registration-preparation.md',
 'docs/tasks/A03-P2-R3-evidence-closure-coordinator-decision.md',
 'docs/evidence/coordinator/heartbeat-20261017-0944/A03-R4-delivery-preflight.json']
requests=[TARGET+':'+p for p in added]+[x['commit']+':'+x['path']for x in sources]+[WF+':'+p for p in wfpaths]
blobs=batch(requests)
assert {x['path']for x in manifest['files']}==set(added)-{EV+'sha256-manifest.json'}
for x in manifest['files']:
    oid,raw=blobs[TARGET+':'+x['path']];assert len(raw)==x['bytes']and sha(raw)==x['sha256']
    assert after[x['path']].split()[2]==oid
assert sha(blobs[TARGET+':'+REPORT][1])=='95cf2746bb9ceb5a1857f3e8babca04892d8481c74c11d3ee256d5eeb26055f9'
assert sha(blobs[TARGET+':'+EX+'bridge-interface-proposal.json'][1])=='b57d0af5d72a03c4b16e6eeedc267bda50f1dfcf022728b1f107f5b158a22207'
assert sha(blobs[WF+':docs/tasks/A03-P2-R4-bridge-registration-review-handoff.md'][1])=='454388a8db52bc8eb65c62ef3eb637f0a68a03deab4e508b4c005854ebf5a7db'
for x in sources:
    oid,raw=blobs[x['commit']+':'+x['path']];assert len(raw)==x['bytes']and sha(raw)==x['sha256']
    if 'raw_git_blob'in x:assert oid==x['raw_git_blob']
    if 'copy'in x:assert raw==blobs[TARGET+':'+x['copy']][1]

exported=[]
def export(rev,path,dest,role):
    oid,raw=blobs[rev+':'+path];dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb')as f:f.write(raw)
    exported.append({'commit':rev,'path':path,'file':dest.relative_to(OUT).as_posix(),'bytes':len(raw),'sha256':sha(raw),'raw_git_sha1':oid,'role':role})
for p in added:
    if p==EV+'old-baseline.json':continue
    export(TARGET,p,STAGE/p,'current_frozen_delivery')
for x in index['reused_inputs']:export(x['commit'],x['path'],STAGE/x['path'],'fixed_static_input')
for p in wfpaths:export(WF,p,OUT/'input/workflow'/p,'frozen_review_workflow')
guard=[]
for p in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
    if p.is_file()and not p.is_relative_to(OUT):
        raw=p.read_bytes();guard.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
for p in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
    raw=p.read_bytes();guard.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
write(OUT/'protected-old-files.json',{'method':'raw file bytes only, no database opened','files':guard})
write(OUT/'input-index.json',{'workflow':WF,'base':BASE,'delivery':TARGET,'files':exported})
write(OUT/'delivery-byte-index.json',{'workflow':WF,'base':BASE,'delivery':TARGET,'old_git_paths_unchanged':len(before),
 'added_paths':len(added),'manifest_entries':110,'raw_inputs_verified':len(sources),
 'files':[{'path':p,'raw_git_sha1':blobs[TARGET+':'+p][0],'bytes':len(blobs[TARGET+':'+p][1]),'sha256':sha(blobs[TARGET+':'+p][1])}for p in added]})
print(json.dumps({'result':'RAW_GIT_FROZEN','old_git_paths_unchanged':len(before),'new_paths':len(added),'raw_source_inputs_verified':len(sources),'exports':len(exported),'old_files_guarded':len(guard)}))
