# -*- coding: utf-8 -*-
"""Raw Git isolation and preservation; no candidate import, build or install."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R7-readonly-codec';STAGE=OUT/'input/checkout'
WF='5cb696378f8c53a7720a5b775b3188012bf5626b';BASE='81d3ec7e42e0a1a76ad744bf59536fc5f68adee4';TARGET='8ad45dd07214ae406a3fab28d76a4b5abd6eef03'
EX='examples/a03/P2-R7-readonly-codec/';EV='docs/evidence/A03/execution/P2-R7-readonly-codec/';PRODUCT='src/annotation/contracts/a03_bridge/';FIX='tests/fixtures/a03/P2-R7-readonly-codec/';REPORT='docs/tasks/A03-P2-R7-readonly-codec-delivery.md'
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
        end=raw.index(b'\n',pos);head=raw[pos:end].decode().split();pos=end+1;assert len(head)==3 and head[1]=='blob',(spec,head)
        n=int(head[2]);b=raw[pos:pos+n];pos+=n;assert raw[pos:pos+1]==b'\n';pos+=1
        assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==head[0];result[spec]=(head[0],b)
    assert pos==len(raw);return result
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
before,after=tree(BASE),tree(TARGET);assert len(before)==28411
assert all(after.get(k)==v for k,v in before.items()if k!='pyproject.toml')
modified=[p for p in before if before[p]!=after.get(p)];assert modified==['pyproject.toml']
added=sorted(set(after)-set(before));changed=sorted(added+modified);assert len(changed)==340
assert all(p.startswith((EX,EV,PRODUCT,FIX))or p in [REPORT,'tests/test_a03_r7_readonly_codec.py','pyproject.toml']for p in changed)
seed=batch([TARGET+':'+EV+p for p in ['sha256-manifest.json','raw-input-pins.json','compatibility-input-pins.json']])
manifest_raw=seed[TARGET+':'+EV+'sha256-manifest.json'][1];assert sha(manifest_raw)=='92361002a2fad609255a7954fabef9f0ffa45082962811ca41b27aaf43a5c8d3'
manifest=json.loads(manifest_raw);pins=json.loads(seed[TARGET+':'+EV+'raw-input-pins.json'][1])['inputs'];compat=json.loads(seed[TARGET+':'+EV+'compatibility-input-pins.json'][1])['inputs']
assert len(manifest['files'])==339 and len(pins)==170 and len(compat)==1;pins=pins+compat
wfpaths=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md',
 'docs/tasks/A03-P2-R7-readonly-codec-review-handoff.md','docs/tasks/A03-P2-R7-readonly-codec-implementation.md',
 'docs/evidence/coordinator/heartbeat-20261017-1144/R7-input-pins.json','docs/evidence/coordinator/heartbeat-20261017-1229/A03-R7-delivery-preflight.json']
core=[p for p in after if p.startswith(('src/annotation/contracts/','tests/fixtures/contracts/'))or p in ['src/annotation/__init__.py','tests/test_contracts.py','tests/test_contracts_platform_refs.py','examples/contracts/consume.py']]
requests=[TARGET+':'+p for p in set(changed+core)]+[x['commit']+':'+x['path']for x in pins]+[WF+':'+p for p in wfpaths]+[BASE+':pyproject.toml']
blobs=batch(requests)
assert {x['path']for x in manifest['files']}==set(changed)-{EV+'sha256-manifest.json'}
for x in manifest['files']:
    oid,b=blobs[TARGET+':'+x['path']];assert len(b)==x['bytes']and sha(b)==x['sha256']and after[x['path']].split()[2]==oid
assert sha(blobs[TARGET+':'+REPORT][1])=='24ae0a28230da26458d6dc6427587e932788d7b8d71e1eceded771001028b2ad'
assert sha(blobs[WF+':docs/tasks/A03-P2-R7-readonly-codec-review-handoff.md'][1])=='4f8f16072268d38b9e2a1f5313f4e0d72b2f85a6214e6e5b3d35970b654eed89'
assert sha(blobs[WF+':docs/evidence/coordinator/heartbeat-20261017-1144/R7-input-pins.json'][1])=='4ba6e0a646f403f552d71c091b62d0a53623f5ea90728ffea7dd2bab8ec172b1'
assert sha(blobs[WF+':docs/evidence/coordinator/heartbeat-20261017-1229/A03-R7-delivery-preflight.json'][1])=='e6ef6a6b8334974e4075047c9ecfa8f96651962dbe3df0bea3df584804f23788'
for x in pins:
    oid,b=blobs[x['commit']+':'+x['path']];assert len(b)==x['bytes']and sha(b)==x['sha256']and oid==x['git_blob']
    if 'copy'in x:assert b==blobs[TARGET+':'+x['copy']][1]
append=b'\n[tool.setuptools.package-data]\n"annotation.contracts.a03_bridge" = ["data/*.json", "data/schemas/*.json"]\n'
assert blobs[TARGET+':pyproject.toml'][1]==blobs[BASE+':pyproject.toml'][1]+append
wheel=EV+'distribution/annotation_contracts-0.1.0-py3-none-any.whl'
assert sha(blobs[TARGET+':'+wheel][1])=='c22c1bcae684d36bf0d39c1fd4c357409e093648157e8132f7b305245b7d02c7'
exports=[];destinations={}
def export(rev,p,dest,role):
    oid,b=blobs[rev+':'+p]
    if dest in destinations:assert dest.read_bytes()==b;return
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb')as f:f.write(b)
    destinations[dest]=True;exports.append({'commit':rev,'path':p,'file':dest.relative_to(OUT).as_posix(),'bytes':len(b),'sha256':sha(b),'raw_git_sha1':oid,'role':role})
for p in changed:
    if p.startswith(EV+'runs/')and Path(p).name.startswith(('source-','registered-script'))and '/freeze-01/'not in p and '/prepare-01/'not in p:continue
    export(TARGET,p,STAGE/p,'current_frozen_delivery')
for p in core:export(TARGET,p,STAGE/p,'C01_and_package_import_dependency')
for x in pins:
    if 'copy'in x or x['path'].endswith('.py'):
        export(x['commit'],x['path'],STAGE/x.get('copy',x['path']),'necessary_fixed_source')
for p in wfpaths:export(WF,p,OUT/'input/workflow'/p,'frozen_review_workflow')
export(BASE,'pyproject.toml',OUT/'input/base/pyproject.toml','authorized_config_diff_base')
guard=[]
for p in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
    if p.is_file()and not p.is_relative_to(OUT):
        b=p.read_bytes();guard.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b)})
for p in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
    b=p.read_bytes();guard.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b)})
write(OUT/'protected-old-files.json',{'method':'raw file bytes only; no database opened','files':guard})
write(OUT/'input-index.json',{'workflow':WF,'base':BASE,'delivery':TARGET,'raw_input_entries_verified':171,'files':exports})
write(OUT/'raw-source-index.json',{'entries':[dict(x,raw_git_verified=True)for x in pins],'method':'all 171 raw Git bodies verified; existing fixture/data duplicates need not be copied twice'})
write(OUT/'delivery-byte-index.json',{'workflow':WF,'base':BASE,'delivery':TARGET,'old_git_paths_unchanged_except_authorized_config':28410,'changed_paths':340,'added_paths':len(added),'modified_old_paths':modified,'manifest_entries':339,
 'pyproject_only_append':append.decode(),'files':[{'path':p,'raw_git_sha1':blobs[TARGET+':'+p][0],'bytes':len(blobs[TARGET+':'+p][1]),'sha256':sha(blobs[TARGET+':'+p][1])}for p in changed]})
print(json.dumps({'result':'RAW_GIT_FROZEN','changed':340,'old_unchanged':28410,'modified_old':['pyproject.toml'],'raw_inputs':171,'exports':len(exports),'old_review_files_guarded':len(guard),'wheel_sha256':sha(blobs[TARGET+':'+wheel][1])}))
