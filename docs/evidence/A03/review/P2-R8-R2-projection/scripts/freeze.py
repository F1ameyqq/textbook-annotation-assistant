# -*- coding: utf-8 -*-
"""Exact R2 raw-Git review inputs and a fresh source-only N1 workspace."""
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R8-R2-projection';WORK=OUT/'isolation/workspace'
WF='1f2030b813cbbfc77cc12cab36db453972af26b9';BASE='a0c40886f3076f84c46377e03fc2206d2fdc5585';TARGET='58d8a64734271d15654bb00b03d760f0f3eccd10'
EV='docs/evidence/A03/execution/P2-R8-R2-projection/';REPORT='docs/tasks/A03-P2-R8-R2-projection-report.md'
DRIVER='tests/test_a03_r8_r2_projection.py';FIX='tests/fixtures/a03/P2-R8-R2-projection/'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args,data=None):return subprocess.run(['git','-c','core.longpaths=true',*args],cwd=ROOT,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
def tree(rev):
    result={}
    for row in git('ls-tree','-rz','--full-tree',rev).split(b'\0'):
        if row:
            meta,p=row.split(b'\t',1);result[p.decode()]=meta.decode()
    return result
def batch(specs):
    specs=sorted(set(specs));data=git('cat-file','--batch',data=('\n'.join(specs)+'\n').encode());pos=0;result={}
    for spec in specs:
        end=data.index(b'\n',pos);head=data[pos:end].decode().split();pos=end+1;assert len(head)==3 and head[1]=='blob'
        n=int(head[2]);b=data[pos:pos+n];pos+=n;assert data[pos:pos+1]==b'\n';pos+=1
        assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==head[0];result[spec]=(head[0],b)
    assert pos==len(data);return result
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
before,after=tree(BASE),tree(TARGET);modified=sorted(p for p in before if before[p]!=after.get(p));added=sorted(set(after)-set(before));changed=sorted(modified+added)
assert len(before)==29706 and len(changed)==582
assert modified==['src/annotation/contracts/a03_native/data/adoption.json','src/annotation/contracts/a03_native/data/profile.json','src/annotation/runtime/storage/__init__.py']
assert all(p.startswith((EV,'examples/a03/P2-R8-R2-projection/',FIX)) or p in [REPORT,DRIVER,'tests/test_a03_r8_r2_projection_minimal.py'] for p in added)
seed=batch([TARGET+':'+EV+p for p in ('manifest.json','inputs.json')])
manifest_raw=seed[TARGET+':'+EV+'manifest.json'][1];assert sha(manifest_raw)=='5b5a3cc998c05fbe4ac3d044bac8bfd1b468b24d7b3e71adb7b78a7db397684c'
manifest=json.loads(manifest_raw);pins=json.loads(seed[TARGET+':'+EV+'inputs.json'][1])['files'];assert len(manifest['entries'])==581 and len(pins)==6
assert {r['path'] for r in manifest['entries']}==set(changed)-{EV+'manifest.json'}
source=[p for p in after if p.startswith('src/annotation/')]
needed=source+['tests/test_contracts.py','tests/test_contracts_platform_refs.py']
workflow_paths=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md',
 'docs/tasks/A03-P2-R8-R2-projection-review-handoff.md','docs/tasks/A03-P2-R8-R2-projection-rework.md',
 'docs/evidence/coordinator/heartbeat-20261018-0127/A03-R8-R2-delivery-preflight.json']
specs=[TARGET+':'+p for p in set(changed+needed)]+[WF+':'+p for p in workflow_paths]
specs += [(r.get('workflow') or r['base'])+':'+r['path'] for r in pins]
blobs=batch(specs)
for r in manifest['entries']:
    oid,b=blobs[TARGET+':'+r['path']];assert len(b)==r['bytes'] and sha(b)==r['sha256'] and after[r['path']].split()[2]==oid
for r in pins:
    oid,b=blobs[(r.get('workflow') or r['base'])+':'+r['path']];assert len(b)==r['bytes'] and sha(b)==r['sha256']
for p,d in {REPORT:'8fd88d3f19de8a853f8649412ecbef9cae4c453c689b2540413d206db0178421',
 EV+'process-release.json':'6119e12e0b7b35c09c60b89eb32aa4445c4806c6fd73b365adb1394910425875',
 EV+'bounded-outcome.json':'e20b2567885408ea6edbc37ea51952cfdcccb5ca3ab44036e782ed3b10212bfe',
 EV+'database-readback.json':'b5564cad9c89fcbf2c158989505a61f6a7fbd543984164c93d8f7ca942db34f5'}.items():assert sha(blobs[TARGET+':'+p][1])==d
assert sha(blobs[WF+':docs/tasks/A03-P2-R8-R2-projection-review-handoff.md'][1])=='e66037d79d96b263d5b50b4ab4d3cb101592bfeabe81551ab535f031bcc09507'
assert sha(blobs[WF+':docs/evidence/coordinator/heartbeat-20261018-0127/A03-R8-R2-delivery-preflight.json'][1])=='0abd9fd491ca3d538da16bb9b881c999df5fb21a6dcc3b6378c90ca207de572d'
exports=[];seen=set()
def export(rev,p,scope):
    key=rev+':'+p
    if key in seen:return
    oid,b=blobs[key]
    is_workspace=rev==TARGET and (p in source or p==DRIVER or p.startswith(FIX) or p==EV+'inputs.json')
    prefix='isolation/workspace' if is_workspace else 'input/workflow' if rev==WF else 'input/author' if rev==TARGET else 'input/base'
    relative=Path(prefix)/p
    if not is_workspace and len(str(OUT/relative))>235:relative=Path('input/raw')/(sha(key.encode())[:16]+'-'+Path(p).name)
    dest=OUT/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(b)
    seen.add(key);exports.append({'commit':rev,'path':p,'file':relative.as_posix(),'bytes':len(b),'sha256':sha(b),'raw_git_sha1':oid,'scope':scope})
snapshots=('/runtime/storage/__init__.py','/runtime/storage/native.py','/contracts/recovery.py',
 '/quality/synthetic_precheck.py','/contracts/a03_native/data/profile.json','/contracts/a03_native/data/adoption.json')
for p in changed:
    if '/product-snapshot/' in p and not p.endswith(snapshots):continue
    export(TARGET,p,'necessary frozen source/evidence; unused duplicate snapshots indexed only')
for p in needed:export(TARGET,p,'complete normal annotation package and required original C01 source')
for p in workflow_paths:export(WF,p,'frozen review authority')
for r in pins:
    if r.get('base'):export(r['base'],r['path'],'three exact base product bytes for diff')
assert not (WORK/EV/'validation').exists()
history=[]
for p in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
    if p.is_file() and not p.is_relative_to(OUT):history.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p.read_bytes())])
for p in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
    if p.name!='A03-P2-R8-R2-projection-review-report.md':history.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p.read_bytes())])
history.sort()
write(OUT/'historical-preservation.json',{'method':'canonical sorted [path,size,raw SHA256] digest, no historical copies','count':len(history),
 'bytes':sum(r[1] for r in history),'inventory_sha256':sha(json.dumps(history,ensure_ascii=False,separators=(',',':')).encode())})
write(OUT/'input-index.json',{'workflow':WF,'base':BASE,'target':TARGET,'exports':exports})
write(OUT/'delivery-byte-index.json',{'old_entries':len(before),'old_entries_preserved':len(before)-3,'modified_old_paths':modified,
 'changed_paths':582,'added_paths':len(added),'manifest_entries':581,'verified_author_input_pins':pins,
 'files':[{'path':p,'mode_type_blob':after[p],'bytes':len(blobs[TARGET+':'+p][1]),'sha256':sha(blobs[TARGET+':'+p][1])} for p in changed]})
write(OUT/'isolated-source-index.json',{'workspace':str(WORK),'source_package_files':len(source),
 'files':[r for r in exports if r['file'].startswith('isolation/workspace/')],
 'author_success_databases_or_validation_outputs_copied':False,'original_inputs_json_role':'driver preregistration hash only'})
print(json.dumps({'status':'R2_EXACT_SOURCE_FROZEN','changed':582,'old_preserved':len(before)-3,'raw_input_pins':len(pins),
 'exports':len(exports),'source_package_files':len(source),'workspace_seed_files':len([r for r in exports if r['file'].startswith('isolation/workspace/')]),'history_guarded':len(history)}))
