# -*- coding: utf-8 -*-
"""Raw frozen R9 evidence only. Never imports or calls candidate modules."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R9-failure'
WF='d9c0be133ac86919bea1f9caec29120e0ea650b3';EXEC_WF='11300250bef18d4bdf7220111cf82232c7d5e0f3'
BASE='435aaee2d140e82d3237ce8902d594a1aee70aad';TARGET='c83f956c5c29c64ab10735ba11c153201d3f3f4b'
EV='docs/evidence/A03/execution/P2-R9-minimal-demos/';REPORT='docs/tasks/A03-P2-R9-minimal-demos-report.md'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
counter=0
def git(*args,data=None):
    global counter
    counter+=1;d=OUT/'git-processes'/('%02d'%counter);d.mkdir(parents=True,exist_ok=False)
    argv=['git','-c','core.longpaths=true',*args];body=data or b'';(d/'stdin.bin').write_bytes(body)
    write(d/'preregistered.json',{'argv':argv,'cwd':str(ROOT),'timeout_seconds':30,'stdin_sha256':sha(body),
      'entry_source_sha256':sha(Path(__file__).read_bytes()),'registered_at_ns':time.time_ns()})
    with (d/'stdout.bin').open('xb') as stdout,(d/'stderr.bin').open('xb') as stderr:
        p=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr)
        write(d/'started.json',{'pid':p.pid,'started_at_ns':time.time_ns()});timed=False
        try:p.communicate(input=body,timeout=30)
        except subprocess.TimeoutExpired:timed=True;p.kill();p.communicate()
    write(d/'completed.json',{'pid':p.pid,'exit_code':p.returncode,'timed_out':timed,'alive':p.poll() is None,
      'ended_at_ns':time.time_ns(),'stdout_sha256':sha((d/'stdout.bin').read_bytes()),'stderr_sha256':sha((d/'stderr.bin').read_bytes())})
    assert p.returncode==0 and not timed
    return (d/'stdout.bin').read_bytes()
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
before,after=tree(BASE),tree(TARGET);modified=sorted(p for p in before if before[p]!=after.get(p));added=sorted(set(after)-set(before))
assert len(before)==31482 and not modified and len(added)==183
assert all(p.startswith((EV,'examples/a03/P2-R9-minimal-demos/')) or p in (REPORT,'tests/test_a03_p2_r9_minimal_demos.py') for p in added)
first=batch([TARGET+':'+EV+p for p in ('manifest.json','inputs.json')]);manifest_raw=first[TARGET+':'+EV+'manifest.json'][1]
assert sha(manifest_raw)=='7712cad90e09e0883dc4dc95d36608a066d76ca62aa10a2664df0b7a48917c86'
manifest=json.loads(manifest_raw);inputs=json.loads(first[TARGET+':'+EV+'inputs.json'][1]);pins=inputs['files'];refs=inputs['unchanged_references_and_copied_fixture_sources']
assert len(manifest['entries'])==182 and len(pins)==5 and len(refs)==11
assert {r['path'] for r in manifest['entries']}==set(added)-{EV+'manifest.json'}
assert inputs['base_entries']==31482 and inputs['base_tree_sha256']==sha(git('ls-tree','-r',BASE))
source=[p for p in after if p.startswith('src/annotation/')]
workflow=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md',
 'docs/tasks/A03-P2-R9-failure-review-handoff.md','docs/evidence/coordinator/heartbeat-20261018-0514/delivery-preflight.json']
specs=[TARGET+':'+p for p in added+source]+[WF+':'+p for p in workflow]+[r['workflow']+':'+r['path'] for r in pins]+[BASE+':'+r['path'] for r in refs]
blobs=batch(specs)
for r in manifest['entries']:
    oid,b=blobs[TARGET+':'+r['path']];assert len(b)==r['bytes'] and sha(b)==r['sha256'] and after[r['path']].split()[2]==oid
for r in pins:
    b=blobs[r['workflow']+':'+r['path']][1];assert len(b)==r['bytes'] and sha(b)==r['sha256']
    assert b==blobs[TARGET+':'+EV+'inputs/'+Path(r['path']).name][1]
for r in refs:
    b=blobs[BASE+':'+r['path']][1];assert len(b)==r['bytes'] and sha(b)==r['sha256']
expected={TARGET+':'+REPORT:'6f68b69ed13cbdc3194346181054eef70b9abc45c1a714ab35b60ab847b3c72d',
 TARGET+':'+EV+'process-release.json':'f64486a952a14bf62589f4ae12d63681811bfafdbc6fcaf69d1b81d4f7271273',
 TARGET+':'+EV+'validation/r9-01/processes/D1-execute/stderr.txt':'0db6947c2321a6a6fe42b68486f7dc0f0cd7e5340a50a6f412f013fe9fc4852d',
 WF+':docs/tasks/A03-P2-R9-failure-review-handoff.md':'685cdf4ba3433e28680a092cdd60b97056db9d04265e503a39f5aa5a063efd41'}
for key,digest in expected.items():assert sha(blobs[key][1])==digest
exports=[]
for key,(oid,b) in sorted(blobs.items()):
    rev,p=key.split(':',1);prefix='input/workflow' if rev==WF else 'input/execution-workflow' if rev==EXEC_WF else 'input/target' if rev==TARGET else 'input/base'
    relative=Path(prefix)/p
    if len(str(OUT/relative))>235:relative=Path('input/raw')/(sha(key.encode())[:16]+'-'+Path(p).name)
    dest=OUT/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(b)
    exports.append({'commit':rev,'path':p,'file':relative.as_posix(),'bytes':len(b),'sha256':sha(b),'raw_git_sha1':oid})
history=[]
for p in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
    if p.is_file() and not p.is_relative_to(OUT):history.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p.read_bytes())])
for p in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
    if p.name!='A03-P2-R9-failure-review-report.md':history.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p.read_bytes())])
history.sort()
write(OUT/'historical-preservation.json',{'count':len(history),'bytes':sum(r[1] for r in history),
 'inventory_sha256':sha(json.dumps(history,ensure_ascii=False,separators=(',',':')).encode()),'method':'sorted [path,size,raw SHA256], no historical corpus copied'})
write(OUT/'input-index.json',{'workflow':WF,'execution_workflow':EXEC_WF,'base':BASE,'target':TARGET,'exports':exports})
write(OUT/'delivery-byte-index.json',{'old_entries':31482,'old_entries_preserved':31482,'modified_old_paths':modified,
 'added_paths':183,'manifest_entries':182,'verified_input_pins':pins,'verified_base_references':refs,
 'files':[{'path':p,'mode_type_blob':after[p],'bytes':len(blobs[TARGET+':'+p][1]),'sha256':sha(blobs[TARGET+':'+p][1])} for p in added]})
write(OUT/'review-scope.json',{'product_imports_calls_or_runs':0,'D1_D2_replays':0,'subagents':0,'write_scope':'new R9 failure report/evidence only',
 'original_failure_preserved':True,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print(json.dumps({'status':'R9_FROZEN_BYTES_VERIFIED','old_preserved':31482,'new_files':183,'exports':len(exports),'historical_files':len(history),'owned_git_children':counter}))
