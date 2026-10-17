# -*- coding: utf-8 -*-
"""Exact raw-Git export and byte preservation for a read-only R8 failure review."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('D:/1800'); OUT=ROOT/'docs/evidence/A03/review/P2-R8-native-bridge'
WF='267bce2b18b04c75d0737da06052db2b31ba01fa'
BASE='8ad45dd07214ae406a3fab28d76a4b5abd6eef03'; TARGET='fa6edeb7e9dd0c9502781747e5fce012931d9441'
EV='docs/evidence/A03/execution/P2-R8-native-bridge/'
REPORT='docs/tasks/A03-P2-R8-native-bridge-delivery.md'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def git(*args,data=None):
    return subprocess.run(['git','-c','core.longpaths=true',*args],cwd=ROOT,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
def tree(rev):
    result={}
    for row in git('ls-tree','-rz','--full-tree',rev).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);result[path.decode()]=meta.decode()
    return result
def batch(specs):
    specs=sorted(set(specs));raw=git('cat-file','--batch',data=('\n'.join(specs)+'\n').encode());pos=0;result={}
    for spec in specs:
        end=raw.index(b'\n',pos);head=raw[pos:end].decode().split();pos=end+1
        assert len(head)==3 and head[1]=='blob',(spec,head)
        n=int(head[2]);body=raw[pos:pos+n];pos+=n;assert raw[pos:pos+1]==b'\n';pos+=1
        assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+body).hexdigest()==head[0]
        result[spec]=(head[0],body)
    assert pos==len(raw);return result
def write(path,value):
    with path.open('x',encoding='utf8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

before,after=tree(BASE),tree(TARGET)
modified=sorted(p for p in before if after.get(p)!=before[p]);added=sorted(set(after)-set(before))
changed=sorted(modified+added)
assert len(before)==28750 and len(modified)==12 and len(changed)==463
allowed_old={'pyproject.toml','src/annotation/contracts/__init__.py','src/annotation/contracts/validation.py','src/annotation/contracts/recovery.py',
 'src/annotation/quality/targetcheck/__init__.py','src/annotation/delivery/planner/__init__.py',
 'src/annotation/delivery/mock/__init__.py','src/annotation/delivery/mock/persistent.py'}
assert all(p in allowed_old or p.startswith(('src/annotation/runtime/storage/','src/annotation/runtime/recovery/','src/annotation/delivery/reconciler/')) for p in modified)
assert all(p.startswith((EV,'src/annotation/contracts/a03_native/','src/annotation/runtime/storage/','src/annotation/runtime/recovery/',
 'src/annotation/delivery/reconciler/','tests/fixtures/a03/P2-R8-native-bridge/','examples/a03/P2-R8-native-bridge/'))
 or p in [REPORT,'tests/test_a03_r8_native_bridge.py','src/annotation/quality/synthetic_precheck.py'] for p in added)
seed=batch([TARGET+':'+EV+p for p in ('manifest.json','inputs.json')])
manifest_raw=seed[TARGET+':'+EV+'manifest.json'][1]
assert sha(manifest_raw)=='c9d195c5a97ef6293cece1627372ecf8f7404d4537bac9a9bda5e298841f0c7e'
manifest=json.loads(manifest_raw);pins=json.loads(seed[TARGET+':'+EV+'inputs.json'][1])['files']
assert len(manifest['entries'])==462 and len(pins)==89
assert {r['path'] for r in manifest['entries']}==set(changed)-{EV+'manifest.json'}
workflow_paths=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md',
 'docs/tasks/A03-P2-R8-native-bridge-review-handoff.md','docs/tasks/A03-P2-R8-native-bridge-implementation.md',
 'docs/evidence/coordinator/heartbeat-20261017-1510/A03-R8-delivery-preflight.json']
old_needed=[p for p in after if p in ['tests/test_contracts.py','tests/test_contracts_platform_refs.py','examples/contracts/consume.py']
 or p.startswith('src/annotation/contracts/') and p.count('/')==3 and p.endswith('.py')]
specs=[TARGET+':'+p for p in set(changed+old_needed)]+[r['commit']+':'+r['path'] for r in pins]
specs += [WF+':'+p for p in workflow_paths]+[BASE+':pyproject.toml']
blobs=batch(specs)
for row in manifest['entries']:
    oid,body=blobs[TARGET+':'+row['path']]
    assert len(body)==row['bytes'] and sha(body)==row['sha256'] and after[row['path']].split()[2]==oid
for row in pins:
    oid,body=blobs[row['commit']+':'+row['path']]
    assert len(body)==row['bytes'] and sha(body)==row['sha256']
expected={REPORT:'2d482c8c2b20985496cf0b07db65aaa68fccc3acfae6e363af0c3d34d6f0372d',
 EV+'process-release.json':'58f0b7cbfd9d747144f24df05c4852714ad40417575486b92c92cc11eea7a98b',
 EV+'bounded-outcome.json':'6c5c68c5510bcb5cd2d7fb68b4e8bbe2d36fc8a8f093191652245b0233d9e5a7'}
for path,digest in expected.items():assert sha(blobs[TARGET+':'+path][1])==digest
assert sha(blobs[WF+':docs/tasks/A03-P2-R8-native-bridge-review-handoff.md'][1])=='4af279d3be77f3755afda92b7f5efafdbc2b331c039e51ab93c0cb0b97ed5a0d'
assert sha(blobs[WF+':docs/evidence/coordinator/heartbeat-20261017-1510/A03-R8-delivery-preflight.json'][1])=='a416e8ac974ffbc9ca6f78ac22a44d54fe3c9d7d6c2d043bba68b8e59ec311b8'
append=b'\n[tool.setuptools.package-data."annotation.contracts.a03_native"]\n'
oldproject=blobs[BASE+':pyproject.toml'][1];newproject=blobs[TARGET+':pyproject.toml'][1]
# Pin the actual append without assuming a different legal TOML spelling.
assert newproject.startswith(oldproject)
tail=newproject[len(oldproject):]
assert b'annotation.contracts.a03_native' in tail and b'dependencies' not in tail and b'version' not in tail
exports=[];seen=set()
def export(rev,path,scope):
    oid,body=blobs[rev+':'+path]
    relative=Path('input/workflow' if rev==WF else 'input/base' if rev==BASE else 'input/checkout')/path
    dest=OUT/relative
    if len(str(dest))>235:
        relative=Path('input/raw')/(sha(body)+'-'+Path(path).name);dest=OUT/relative
    if relative.as_posix() in seen:return
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(body)
    seen.add(relative.as_posix());exports.append({'commit':rev,'path':path,'file':relative.as_posix(),
      'bytes':len(body),'sha256':sha(body),'raw_git_sha1':oid,'scope':scope})
snapshot_suffixes=('/contracts/a03_native/__init__.py','/quality/synthetic_precheck.py','/quality/targetcheck/__init__.py',
 '/contracts/a03_native/data/profile.json','/contracts/a03_native/data/adoption.json')
for path in changed:
    if '/product-snapshot/' in path and not path.endswith(snapshot_suffixes):continue
    export(TARGET,path,'frozen R8 required source/evidence')
for path in old_needed:export(TARGET,path,'unchanged C01 source for static interpretation only')
for path in workflow_paths:export(WF,path,'frozen review authority')
export(BASE,'pyproject.toml','preserved config base')
protected=[]
for path in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
    if path.is_file() and not path.is_relative_to(OUT):
        raw=path.read_bytes();protected.append([path.relative_to(ROOT).as_posix(),len(raw),sha(raw)])
for path in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
    if path.name!='A03-P2-R8-native-bridge-review-report.md':
        raw=path.read_bytes();protected.append([path.relative_to(ROOT).as_posix(),len(raw),sha(raw)])
protected.sort()
write(OUT/'historical-preservation.json',{'method':'sorted [relative path,byte length,raw SHA256] canonical JSON digest; no historical copies',
 'count':len(protected),'bytes':sum(r[1] for r in protected),'inventory_sha256':sha(json.dumps(protected,ensure_ascii=False,separators=(',',':')).encode())})
write(OUT/'input-index.json',{'workflow':WF,'base':BASE,'target':TARGET,'exports':exports})
write(OUT/'raw-input-pins.json',{'verified_raw_git_pins':89,'files':[dict(r,raw_git_sha1=blobs[r['commit']+':'+r['path']][0]) for r in pins]})
write(OUT/'delivery-byte-index.json',{'old_entries':len(before),'old_entries_preserved':len(before)-len(modified),
 'modified_old_paths':modified,'added_paths':len(added),'changed_paths':len(changed),'manifest_entries':462,
 'pyproject_append':tail.decode(),'files':[{'path':p,'mode_type_blob':after[p],
 'bytes':len(blobs[TARGET+':'+p][1]),'sha256':sha(blobs[TARGET+':'+p][1])} for p in changed]})
print(json.dumps({'status':'R8_RAW_GIT_FROZEN','changed':len(changed),'preserved_old':len(before)-len(modified),
 'modified_old':modified,'raw_pins':89,'exports':len(exports),'historical_files_guarded':len(protected)},ensure_ascii=False))
