# -*- coding: utf-8 -*-
"""Exact raw Git identity and fresh source-only R4 workspace; no product imports."""
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R8-R4-remaining';WORK=OUT/'isolation/workspace'
WF='74b4fbc9c2778a516cb9f7cadd7e3b3ca5faa639';EXEC_WF='cb9c8f76e9eae40a8fda042c196705d7258b5107'
BASE='d9ed692db9ab8e9277f8ffd09e040451e8b8f65f';TARGET='435aaee2d140e82d3237ce8902d594a1aee70aad'
EV='docs/evidence/A03/execution/P2-R8-R4-remaining/';REPORT='docs/tasks/A03-P2-R8-R4-remaining-report.md'
DRIVER='tests/test_a03_r8_r4_remaining.py';OLD_DRIVER='tests/test_a03_r8_r3_post_hold.py';FIX='tests/fixtures/a03/P2-R8-R3-post-hold/'
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
before,after=tree(BASE),tree(TARGET);modified=sorted(p for p in before if before[p]!=after.get(p));added=sorted(set(after)-set(before))
assert len(before)==31167 and not modified and len(added)==315
assert all(p.startswith((EV,'examples/a03/P2-R8-R4-remaining/','tests/fixtures/a03/P2-R8-R4-remaining/')) or p in (REPORT,DRIVER) for p in added)
first=batch([TARGET+':'+EV+p for p in ('manifest.json','inputs.json')])
manifest_raw=first[TARGET+':'+EV+'manifest.json'][1]
assert sha(manifest_raw)=='337ba0aa1ce0fd8a70032a6b2580797752f0e4ea5b0216b56913dae2ebd91f4c'
manifest=json.loads(manifest_raw);inputs=json.loads(first[TARGET+':'+EV+'inputs.json'][1]);pins=inputs['files']
assert len(manifest['entries'])==314 and len(pins)==6 and inputs['base']==BASE and inputs['workflow']==EXEC_WF
assert {r['path'] for r in manifest['entries']}==set(added)-{EV+'manifest.json'}
assert inputs['base_entries']==31167 and inputs['base_tree_sha256']==sha(git('ls-tree','-r',BASE))
source=[p for p in after if p.startswith('src/annotation/')];fixture=[p for p in after if p.startswith(FIX)]
workspace=set(source+fixture+[DRIVER,OLD_DRIVER,EV+'inputs.json']);assert len(source)==68 and len(workspace)==76
workflow_paths=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md',
 'docs/tasks/A03-P2-R8-R4-remaining-review-handoff.md','docs/evidence/coordinator/heartbeat-20261018-0429/delivery-preflight.json',
 'docs/evidence/A03/review/P2-R8-R3-post-hold/p2-independent-coverage-review.json',
 'docs/evidence/A03/review/P2-R8-R3-post-hold/N7-readonly-classification.json']
specs=[TARGET+':'+p for p in set(added)|workspace]+[WF+':'+p for p in workflow_paths]
specs += [r['workflow']+':'+r['path'] for r in pins]+[BASE+':'+r['path'] for r in inputs['unchanged_references']]
blobs=batch(specs)
for r in manifest['entries']:
    oid,b=blobs[TARGET+':'+r['path']];assert len(b)==r['bytes'] and sha(b)==r['sha256'] and after[r['path']].split()[2]==oid
for r in pins:
    b=blobs[r['workflow']+':'+r['path']][1];assert len(b)==r['bytes'] and sha(b)==r['sha256']
    assert b==blobs[TARGET+':'+EV+'inputs/'+Path(r['path']).name][1]
for r in inputs['unchanged_references']:
    b=blobs[BASE+':'+r['path']][1];assert len(b)==r['bytes'] and sha(b)==r['sha256']
expected={TARGET+':'+REPORT:'eaba2a007216999ca70e506609a50a049e89b48b86b4c39af0e51dfa50e9e324',
 TARGET+':'+EV+'process-release.json':'31f77b464ff08fbca8c79b4fec0e1e6500a07f9773056f541e96d03318bab6b7',
 TARGET+':'+DRIVER:'27d1969548011b044c21b77a121c53b5bef90d4aa0b19aef95f65b8d692f9a3d',
 WF+':docs/tasks/A03-P2-R8-R4-remaining-review-handoff.md':'b239748cdd5b875b8870f4fa1fdaa679314a46dacf5e2003a17bfe938a7f09bb'}
for key,digest in expected.items():assert sha(blobs[key][1])==digest
exports=[]
for key,(oid,b) in sorted(blobs.items()):
    rev,p=key.split(':',1)
    is_workspace=rev==TARGET and p in workspace
    prefix='isolation/workspace' if is_workspace else 'input/workflow' if rev==WF else 'input/execution-workflow' if rev==EXEC_WF else 'input/author' if rev==TARGET else 'input/base'
    relative=Path(prefix)/p
    if not is_workspace and len(str(OUT/relative))>235:relative=Path('input/raw')/(sha(key.encode())[:16]+'-'+Path(p).name)
    dest=OUT/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(b)
    exports.append({'commit':rev,'path':p,'file':relative.as_posix(),'bytes':len(b),'sha256':sha(b),'raw_git_sha1':oid,
      'role':'fresh source/fixture only' if is_workspace else 'frozen read-only authority or author evidence'})
assert not (WORK/EV/'validation').exists() and not list(WORK.rglob('*.sqlite3'))
history=[]
for p in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
    if p.is_file() and not p.is_relative_to(OUT):history.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p.read_bytes())])
for p in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
    if p.name!='A03-P2-R8-R4-remaining-review-report.md':history.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p.read_bytes())])
history.sort()
write(OUT/'historical-preservation.json',{'method':'canonical sorted [path,size,raw SHA256] digest, no historical copies','count':len(history),
 'bytes':sum(r[1] for r in history),'inventory_sha256':sha(json.dumps(history,ensure_ascii=False,separators=(',',':')).encode())})
write(OUT/'input-index.json',{'workflow':WF,'execution_workflow':EXEC_WF,'base':BASE,'target':TARGET,'exports':exports})
write(OUT/'delivery-byte-index.json',{'old_entries':len(before),'old_entries_preserved':len(before),'modified_old_paths':modified,
 'changed_paths':315,'added_paths':315,'manifest_entries':314,'verified_author_input_pins':pins,
 'files':[{'path':p,'mode_type_blob':after[p],'bytes':len(blobs[TARGET+':'+p][1]),'sha256':sha(blobs[TARGET+':'+p][1])} for p in added]})
write(OUT/'isolated-source-index.json',{'workspace':str(WORK),'source_package_files':68,'files':[r for r in exports if r['file'].startswith('isolation/workspace/')],
 'author_databases_or_validation_outputs_copied':False,'original_inputs_json_role':'unchanged driver preregistration digest only'})
state=ROOT/'docs/coordination-state.json';mermaid=ROOT/'mermaid-diagram.png'
write(OUT/'initial-root-observation.json',{'root_status':git('status','--short').decode(),
 'state_sha256_observed_not_modified':sha(state.read_bytes()),'preexisting_mermaid_sha256':sha(mermaid.read_bytes()),
 'state_may_be_managed_by_coordinator':True})
print(json.dumps({'status':'R4_EXACT_SOURCE_FROZEN','added':315,'old_preserved':31167,'exports':len(exports),'seed_files':76,'history_guarded':len(history)}))
