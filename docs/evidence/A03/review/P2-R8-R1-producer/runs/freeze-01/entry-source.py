# -*- coding: utf-8 -*-
"""Raw frozen R8-R1 bytes only; no candidate imports or author checker execution."""
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R8-R1-producer'
WF='f09233d9ea7eb02d8f487fbda2e96b14d7902037';BASE='fa6edeb7e9dd0c9502781747e5fce012931d9441';TARGET='a0c40886f3076f84c46377e03fc2206d2fdc5585'
EV='docs/evidence/A03/execution/P2-R8-R1-producer/';REPORT='docs/tasks/A03-P2-R8-R1-producer-report.md'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args,data=None):return subprocess.run(['git','-c','core.longpaths=true',*args],cwd=ROOT,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
def tree(rev):
    result={}
    for row in git('ls-tree','-rz','--full-tree',rev).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);result[path.decode()]=meta.decode()
    return result
def batch(specs):
    specs=sorted(set(specs));body=git('cat-file','--batch',data=('\n'.join(specs)+'\n').encode());pos=0;result={}
    for spec in specs:
        end=body.index(b'\n',pos);head=body[pos:end].decode().split();pos=end+1;assert len(head)==3 and head[1]=='blob'
        n=int(head[2]);raw=body[pos:pos+n];pos+=n;assert body[pos:pos+1]==b'\n';pos+=1
        assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+raw).hexdigest()==head[0];result[spec]=(head[0],raw)
    assert pos==len(body);return result
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
before,after=tree(BASE),tree(TARGET)
modified=sorted(p for p in before if before[p]!=after.get(p));added=sorted(set(after)-set(before));changed=sorted(modified+added)
allowed=['src/annotation/contracts/a03_native/data/adoption.json','src/annotation/contracts/a03_native/data/profile.json','src/annotation/quality/synthetic_precheck.py']
assert modified==allowed and len(before)==29201 and len(changed)==508
assert all(p.startswith((EV,'examples/a03/P2-R8-R1-producer/','tests/fixtures/a03/P2-R8-R1-producer/')) or p in
 [REPORT,'tests/test_a03_r8_r1_minimal.py','tests/test_a03_r8_r1_producer.py'] for p in added)
seed=batch([TARGET+':'+EV+p for p in ('manifest.json','inputs.json')]+[TARGET+':src/annotation/contracts/a03_native/data/profile.json'])
manifest_raw=seed[TARGET+':'+EV+'manifest.json'][1]
assert sha(manifest_raw)=='5d5bf3de95c8e6bd335e8ec1e014a627f9346837df2ff243ae1c63c719bd60ad'
manifest=json.loads(manifest_raw);pins=json.loads(seed[TARGET+':'+EV+'inputs.json'][1])['files']
assert len(manifest['entries'])==507 and len(pins)==5
assert {r['path'] for r in manifest['entries']}==set(changed)-{EV+'manifest.json'}
profile=json.loads(seed[TARGET+':src/annotation/contracts/a03_native/data/profile.json'][1])
def impl_path(p):return 'src/'+p[1:] if p.startswith('@') else 'src/annotation/contracts/a03_native/'+p
needed=[impl_path(p) for p,d in profile['implementation_pins']]
needed += [p for p in after if p.startswith('src/annotation/contracts/a03_native/data/')]
needed += ['src/annotation/contracts/models.py','src/annotation/contracts/integrity.py',
 'src/annotation/contracts/a03_bridge/_schema.py','src/annotation/contracts/a03_bridge/_json.py',
 'tests/test_contracts.py','tests/test_contracts_platform_refs.py']
workflow_paths=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md',
 'docs/tasks/A03-P2-R8-R1-producer-review-handoff.md','docs/tasks/A03-P2-R8-R1-producer-rework.md',
 'docs/evidence/coordinator/heartbeat-20261018-0005/A03-R8-R1-delivery-preflight.json']
specs=[TARGET+':'+p for p in set(changed+needed)] + [WF+':'+p for p in workflow_paths]
specs += [(r.get('workflow') or r['base'])+':'+r['path'] for r in pins]
blobs=batch(specs)
for r in manifest['entries']:
    oid,b=blobs[TARGET+':'+r['path']];assert len(b)==r['bytes'] and sha(b)==r['sha256'] and after[r['path']].split()[2]==oid
for r in pins:
    oid,b=blobs[(r.get('workflow') or r['base'])+':'+r['path']];assert len(b)==r['bytes'] and sha(b)==r['sha256']
checks={REPORT:'e9b99a31b5958f184ef9bea63f5b26a9765fac767af9ef21918929673c6df199',
 EV+'process-release.json':'c051dbc4c821874f45c0e5a213391fd3f7c42a4e04ebcca12c8c6ae207031a77',
 EV+'bounded-outcome.json':'734525b4a1a46b3a69e3ae930168eb904610f2d590f91c8cc4d2634202684381',
 EV+'attempt-field-binding.json':'2c325f6044ae76493da4b6521b6fdf6139eb87d920c8779a32300a95bcf00771'}
for p,d in checks.items():assert sha(blobs[TARGET+':'+p][1])==d
assert sha(blobs[WF+':docs/tasks/A03-P2-R8-R1-producer-review-handoff.md'][1])=='4a2ebdb6f0b557781901c1134c36f76cb73a8efff269fbec53e1082954daa006'
exports=[];seen=set()
def export(rev,p,scope):
    key=rev+':'+p
    if key in seen:return
    oid,b=blobs[key];prefix='input/workflow' if rev==WF else 'input/checkout' if rev==TARGET else 'input/reference'
    relative=Path(prefix)/p
    if len(str(OUT/relative))>235:relative=Path('input/raw')/(sha(key.encode())[:16]+'-'+Path(p).name)
    dest=OUT/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(b)
    seen.add(key);exports.append({'commit':rev,'path':p,'file':relative.as_posix(),'bytes':len(b),'sha256':sha(b),'raw_git_sha1':oid,'scope':scope})
snapshot_suffixes=('/quality/synthetic_precheck.py','/quality/targetcheck/__init__.py','/contracts/recovery.py',
 '/runtime/storage/__init__.py','/runtime/storage/native.py','/contracts/a03_native/data/profile.json','/contracts/a03_native/data/adoption.json')
for p in changed:
    if '/product-snapshot/' in p and not p.endswith(snapshot_suffixes):continue
    export(TARGET,p,'required new delivery bytes; unused duplicate snapshots are indexed only')
for p in needed:export(TARGET,p,'exact final source/schema for static review')
for p in workflow_paths:export(WF,p,'frozen review authority')
for r in pins:
    if r.get('base'):export(r['base'],r['path'],'three product base bytes for diff')
history=[]
for p in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
    if p.is_file() and not p.is_relative_to(OUT):history.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p.read_bytes())])
for p in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
    if p.name!='A03-P2-R8-R1-producer-review-report.md':history.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p.read_bytes())])
history.sort()
write(OUT/'historical-preservation.json',{'method':'canonical sorted [path,size,raw SHA256] inventory; no historical copies',
 'count':len(history),'bytes':sum(r[1] for r in history),'inventory_sha256':sha(json.dumps(history,ensure_ascii=False,separators=(',',':')).encode())})
write(OUT/'input-index.json',{'workflow':WF,'base':BASE,'target':TARGET,'exports':exports})
write(OUT/'delivery-byte-index.json',{'old_entries':len(before),'old_entries_preserved':len(before)-3,
 'modified_old_paths':modified,'added_paths':len(added),'changed_paths':len(changed),'manifest_entries':507,
 'verified_author_input_pins':pins,'files':[{'path':p,'mode_type_blob':after[p],
 'bytes':len(blobs[TARGET+':'+p][1]),'sha256':sha(blobs[TARGET+':'+p][1])} for p in changed]})
print(json.dumps({'status':'R8_R1_RAW_GIT_FROZEN','changed':len(changed),'old_preserved':len(before)-3,
 'modified_old':modified,'raw_input_pins':len(pins),'exported_files':len(exports),'historical_files_guarded':len(history)}))
