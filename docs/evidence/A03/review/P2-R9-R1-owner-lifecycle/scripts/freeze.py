# -*- coding: utf-8 -*-
"""Exact raw source/evidence and a new source-only workspace; no product calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R9-R1-owner-lifecycle';WORK=OUT/'isolation/workspace'
WF='eff3282de913452c0c63dff6f0bde16696a9e715';EXEC_WF='2aabd591695e73ecd4024c95e06fe0b71a2a9267'
BASE='c83f956c5c29c64ab10735ba11c153201d3f3f4b';TARGET='bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39'
EV='docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle/';REPORT='docs/tasks/A03-P2-R9-R1-owner-lifecycle-report.md';DRIVER='tests/test_a03_p2_r9_r1_owner_lifecycle.py'
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
assert len(before)==31665 and len(changed)==491 and len(added)==487
assert modified==['src/annotation/contracts/a03_native/data/adoption.json','src/annotation/contracts/a03_native/data/profile.json','src/annotation/runtime/recovery/__init__.py','src/annotation/runtime/recovery/native_quality.py']
assert all(p.startswith((EV,'examples/a03/P2-R9-R1-owner-lifecycle/')) or p in (REPORT,DRIVER) for p in added)
first=batch([TARGET+':'+EV+p for p in ('manifest.json','inputs.json')]);manifest_raw=first[TARGET+':'+EV+'manifest.json'][1]
assert sha(manifest_raw)=='fa79fc21f550ea5491d2e122fb39b46976f9850666fe503423195ae90cdfd7be'
manifest=json.loads(manifest_raw);inputs=json.loads(first[TARGET+':'+EV+'inputs.json'][1]);pins=inputs['files'];refs=inputs['unchanged_references_and_copied_fixture_sources']
assert len(manifest['entries'])==490 and len(pins)==4 and len(refs)==12
assert {r['path'] for r in manifest['entries']}==set(changed)-{EV+'manifest.json'}
assert inputs['base_entries']==31665 and inputs['base_tree_sha256']==sha(git('ls-tree','-r',BASE))
source=[p for p in after if p.startswith('src/annotation/')];fixture=[p for p in after if p.startswith('tests/fixtures/a03/P2-R8-R3-post-hold/')]
workspace=set(source+fixture+[DRIVER,'tests/test_a03_p2_r9_minimal_demos.py','tests/test_a03_r8_r3_post_hold.py',EV+'inputs.json']);assert len(workspace)==77 and len(source)==68
workflow=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md','docs/tasks/A03-P2-R9-R1-owner-lifecycle-review-handoff.md',
 'docs/evidence/coordinator/heartbeat-20261018-0544/delivery-preflight.json','docs/evidence/A03/review/P2-R8-R4-remaining/p2-independent-coverage-review.json']
specs=[TARGET+':'+p for p in set(changed)|workspace]+[WF+':'+p for p in workflow]+[r['workflow']+':'+r['path'] for r in pins]+[BASE+':'+r['path'] for r in refs]
blobs=batch(specs)
for r in manifest['entries']:
    oid,b=blobs[TARGET+':'+r['path']];assert len(b)==r['bytes'] and sha(b)==r['sha256'] and after[r['path']].split()[2]==oid
for r in pins:
    b=blobs[r['workflow']+':'+r['path']][1];assert len(b)==r['bytes'] and sha(b)==r['sha256'] and b==blobs[TARGET+':'+EV+'inputs/'+Path(r['path']).name][1]
for r in refs:
    b=blobs[BASE+':'+r['path']][1];assert len(b)==r['bytes'] and sha(b)==r['sha256']
expected={TARGET+':'+REPORT:'d4241688c338d988d122d177305b464ad7aa14e8531b0f6589b492f72cdf956e',
 TARGET+':'+EV+'process-release.json':'91b63555dcea1c1eff0be18138a510e03e1db4e9c8e91a701db25e42e02bb098',
 TARGET+':'+EV+'validation/owner-r1-01/processes/borrow-execute/stderr.txt':'bc895733e5e37d479f5da9c57f73b29f23694a30a5b09e02a833a11cc7436fb5',
 WF+':docs/tasks/A03-P2-R9-R1-owner-lifecycle-review-handoff.md':'254395485491738a0f8921ade760baf5c6740b9ba0a6b615e8eab4b516c00b27'}
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
    if p.name!='A03-P2-R9-R1-owner-lifecycle-review-report.md':history.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p.read_bytes())])
history.sort()
write(OUT/'historical-preservation.json',{'count':len(history),'bytes':sum(r[1] for r in history),'inventory_sha256':sha(json.dumps(history,ensure_ascii=False,separators=(',',':')).encode()),'method':'sorted [path,size,raw SHA256], no historical corpus copied'})
write(OUT/'input-index.json',{'workflow':WF,'execution_workflow':EXEC_WF,'base':BASE,'target':TARGET,'exports':exports})
write(OUT/'delivery-byte-index.json',{'old_entries':31665,'old_entries_preserved':31661,'modified_old_paths':modified,'added_paths':487,'changed_paths':491,
 'manifest_entries':490,'verified_input_pins':pins,'verified_base_references':refs,'files':[{'path':p,'mode_type_blob':after[p],'bytes':len(blobs[TARGET+':'+p][1]),'sha256':sha(blobs[TARGET+':'+p][1])} for p in changed]})
write(OUT/'isolated-source-index.json',{'workspace':str(WORK),'source_package_files':68,'files':[r for r in exports if r['file'].startswith('isolation/workspace/')],
 'author_DB_or_validation_copied':False,'inputs_json_role':'driver preregistration hash only'})
print(json.dumps({'status':'R9_R1_FROZEN_BYTES_VERIFIED','old_preserved':31661,'changed':491,'exports':len(exports),'source_seed_files':77,'historical_files':len(history),'owned_git_children':counter}))
