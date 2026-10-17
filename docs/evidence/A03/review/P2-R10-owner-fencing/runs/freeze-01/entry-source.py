# -*- coding: utf-8 -*-
"""Exact raw source/evidence and a new source-only workspace; no product calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R10-owner-fencing';WORK=OUT/'isolation/workspace'
WF='2b6771285507fb18d4c6fcd5d6f4933003e94bd0';EXEC_WF='2d8357e040ee5c54494882bc175baf2579d07aed'
BASE='bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39';TARGET='1c26b4a8eb378af33e57668472d2071e9ea6afff'
EV='docs/evidence/A03/execution/P2-R10-owner-fencing/';REPORT='docs/tasks/A03-P2-R10-owner-fencing-report.md';DRIVER='tests/test_a03_p2_r10_owner_fencing.py'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
counter=0
def git(*args,data=None):
    global counter
    counter+=1;d=OUT/'git-processes'/('%02d'%counter);d.mkdir(parents=True,exist_ok=False)
    argv=['git','-c','core.longpaths=true',*args];body=data or b'';(d/'stdin.bin').write_bytes(body)
    write(d/'preregistered.json',{'argv':argv,'cwd':str(ROOT),'timeout_seconds':30,'stdin_sha256':sha(body),'entry_source_sha256':sha(Path(__file__).read_bytes()),'registered_at_ns':time.time_ns()})
    with (d/'stdout.bin').open('xb') as stdout,(d/'stderr.bin').open('xb') as stderr:
        p=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr)
        write(d/'started.json',{'pid':p.pid,'started_at_ns':time.time_ns()});timed=False
        try:p.communicate(input=body,timeout=30)
        except subprocess.TimeoutExpired:timed=True;p.kill();p.communicate()
    write(d/'completed.json',{'pid':p.pid,'exit_code':p.returncode,'timed_out':timed,'alive':p.poll() is None,'ended_at_ns':time.time_ns(),
      'stdout_sha256':sha((d/'stdout.bin').read_bytes()),'stderr_sha256':sha((d/'stderr.bin').read_bytes())})
    assert p.returncode==0 and not timed;return (d/'stdout.bin').read_bytes()
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
before,after=tree(BASE),tree(TARGET);modified=sorted(p for p in before if before[p]!=after.get(p));added=sorted(set(after)-set(before));changed=sorted(modified+added)
assert len(before)==32152 and len(changed)==261 and len(added)==261
assert modified==[]
assert git('rev-parse',TARGET+'^').decode().strip()==BASE
assert all(p.startswith((EV,'examples/a03/P2-R10-owner-fencing/')) or p in (REPORT,DRIVER) for p in added)
first=batch([TARGET+':'+EV+p for p in ('manifest.json','inputs.json')]);manifest_raw=first[TARGET+':'+EV+'manifest.json'][1]
assert sha(manifest_raw)=='7372f10d785322d949a29ea4b28c730ea90411f05ddc2448a39f4e6d2b9bc9a7'
manifest=json.loads(manifest_raw);inputs=json.loads(first[TARGET+':'+EV+'inputs.json'][1]);pins=inputs['files'];refs=inputs['unchanged_references_and_copied_fixture_sources']
assert len(manifest['entries'])==260 and len(pins)==4 and len(refs)==11
assert {r['path'] for r in manifest['entries']}==set(changed)-{EV+'manifest.json'}
assert inputs['base_entries']==32152 and inputs['base_tree_sha256']==sha(git('ls-tree','-r',BASE))
source=[p for p in after if p.startswith('src/annotation/')];fixture=[p for p in after if p.startswith('tests/fixtures/a03/P2-R8-R3-post-hold/')]
workspace=set(source+fixture+[DRIVER,'tests/test_a03_r8_r3_post_hold.py',EV+'inputs.json']);assert len(workspace)==76 and len(source)==68
workflow=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md','docs/tasks/A03-P2-R10-owner-fencing-review-handoff.md',
 'docs/evidence/coordinator/heartbeat-20261018-0629/delivery-preflight.json']
specs=[TARGET+':'+p for p in set(changed)|workspace]+[WF+':'+p for p in workflow]+[r['workflow']+':'+r['path'] for r in pins]+[BASE+':'+r['path'] for r in refs]
blobs=batch(specs)
for r in manifest['entries']:
    oid,b=blobs[TARGET+':'+r['path']];assert len(b)==r['bytes'] and sha(b)==r['sha256'] and after[r['path']].split()[2]==oid
for r in pins:
    b=blobs[r['workflow']+':'+r['path']][1];assert len(b)==r['bytes'] and sha(b)==r['sha256'] and b==blobs[TARGET+':'+EV+'inputs/'+Path(r['path']).name][1]
for r in refs:
    b=blobs[BASE+':'+r['path']][1];assert len(b)==r['bytes'] and sha(b)==r['sha256']
expected={TARGET+':'+REPORT:'a718ddf8b3969dd8b44d81fb22f4ee86b30400c9d85f7226194a6136613e86d4',
 TARGET+':'+EV+'process-release.json':'b7d20a8254ba93b815b40066724a23c75a1206c0f826df90aa9838da4dc1fbd2',
 WF+':docs/tasks/A03-P2-R10-owner-fencing-review-handoff.md':'e3008275528e4b90493339ca82326bbfd691f2313a640acf84b6ccfb3a87eff0'}
for key,digest in expected.items():assert sha(blobs[key][1])==digest
exports=[]
for key,(oid,b) in sorted(blobs.items()):
    rev,p=key.split(':',1);is_workspace=rev==TARGET and p in workspace
    prefix='isolation/workspace' if is_workspace else 'input/workflow' if rev==WF else 'input/execution-workflow' if rev==EXEC_WF else 'input/target' if rev==TARGET else 'input/base'
    relative=Path(prefix)/p
    if not is_workspace and len(str(OUT/relative))>235:relative=Path('input/raw')/(sha(key.encode())[:16]+'-'+Path(p).name)
    dest=OUT/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(b)
    exports.append({'commit':rev,'path':p,'file':relative.as_posix(),'bytes':len(b),'sha256':sha(b),'raw_git_sha1':oid})
assert not list(WORK.rglob('*.sqlite3')) and not (WORK/EV/'validation').exists()
history=[]
for p in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
    if p.is_file() and not p.is_relative_to(OUT):history.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p.read_bytes())])
for p in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
    if p.name!='A03-P2-R10-owner-fencing-review-report.md':history.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p.read_bytes())])
history.sort()
write(OUT/'historical-preservation.json',{'count':len(history),'bytes':sum(r[1] for r in history),'inventory_sha256':sha(json.dumps(history,ensure_ascii=False,separators=(',',':')).encode()),'method':'sorted [path,size,raw SHA256], no historical corpus copied'})
write(OUT/'input-index.json',{'workflow':WF,'execution_workflow':EXEC_WF,'base':BASE,'target':TARGET,'exports':exports})
write(OUT/'delivery-byte-index.json',{'old_entries':32152,'old_entries_preserved':32152,'modified_old_paths':modified,'added_paths':261,'changed_paths':261,
 'manifest_entries':260,'verified_input_pins':pins,'verified_base_references':refs,'files':[{'path':p,'mode_type_blob':after[p],'bytes':len(blobs[TARGET+':'+p][1]),'sha256':sha(blobs[TARGET+':'+p][1])} for p in changed]})
write(OUT/'isolated-source-index.json',{'workspace':str(WORK),'source_package_files':68,'files':[r for r in exports if r['file'].startswith('isolation/workspace/')],
 'author_DB_or_validation_copied':False,'inputs_json_role':'driver preregistration hash only'})
print(json.dumps({'status':'R10_FROZEN_BYTES_VERIFIED','old_preserved':32152,'changed':261,'exports':len(exports),'source_seed_files':76,'historical_files':len(history),'owned_git_children':counter}))
