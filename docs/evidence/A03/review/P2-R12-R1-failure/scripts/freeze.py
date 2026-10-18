# -*- coding: utf-8 -*-
"""One exact frozen export. Product code is data only."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1]
BASE='394fe51f5ed14c5ed312073a20faac0f5cbb9990';CODE='7694490ef25539d131b863bdcb2b21531c69dfae'
TARGET='6affc61d2ab0b1f0d96bb2497c5ae969ebaf1df2';WF='4abf5cc98290511fd4cd1112bd527c382ba09d76'
EV='docs/evidence/A03/execution/P2-R12-R1-unknown-projection/'
EX='examples/a03/P2-R12-R1-unknown-projection/';REPORT='docs/tasks/A03-P2-R12-R1-unknown-projection-report.md'
TASK='docs/tasks/A03-P2-R12-R1-failure-review-handoff.md'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(v if isinstance(v,bytes) else (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
counter=0
def git(*args,data=b''):
    global counter
    counter+=1;d=OUT/'git-processes'/('%02d'%counter);d.mkdir(parents=True,exist_ok=False)
    argv=['git','-c','core.longpaths=true',*args];write(d/'stdin.bin',data)
    write(d/'preregistered.json',{'argv':argv,'cwd':str(ROOT),'timeout_seconds':15,'source_sha256':sha(Path(__file__).read_bytes()),
      'stdin_sha256':sha(data),'registered_at_ns':time.time_ns()})
    with (d/'stdout.bin').open('xb') as stdout,(d/'stderr.bin').open('xb') as stderr:
        p=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr)
        write(d/'started.json',{'pid':p.pid,'started_at_ns':time.time_ns()});timed=False
        try:p.communicate(input=data,timeout=15)
        except subprocess.TimeoutExpired:timed=True;p.kill();p.communicate()
    write(d/'completed.json',{'pid':p.pid,'exit_code':p.returncode,'timed_out':timed,'alive':p.poll() is None,'ended_at_ns':time.time_ns(),
      'stdout_sha256':sha((d/'stdout.bin').read_bytes()),'stderr_sha256':sha((d/'stderr.bin').read_bytes())})
    assert p.returncode==0 and not timed
    return (d/'stdout.bin').read_bytes()
def tree(rev):
    result={}
    for row in git('ls-tree','-rz','--full-tree',rev).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);result[path.decode()]=meta.decode()
    return result
def batch(specs):
    specs=sorted(set(specs));data=git('cat-file','--batch',data=('\n'.join(specs)+'\n').encode());pos=0;result={}
    for spec in specs:
        end=data.index(b'\n',pos);head=data[pos:end].decode().split();pos=end+1
        assert len(head)==3 and head[1]=='blob';n=int(head[2]);b=data[pos:pos+n];pos+=n
        assert data[pos:pos+1]==b'\n';pos+=1
        assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==head[0];result[spec]=(head[0],b)
    assert pos==len(data);return result
old=tree(BASE);code=tree(CODE);target=tree(TARGET)
modified=sorted(p for p in old if target.get(p)!=old[p]);added=sorted(set(target)-set(old));changed=modified+added
four=['src/annotation/contracts/a03_native/data/adoption.json','src/annotation/contracts/a03_native/data/profile.json',
 'src/annotation/runtime/storage/__init__.py','src/annotation/runtime/storage/native.py']
assert modified==four and len(added)==320 and len(old)-len(modified)==33028
assert all(target.get(p)==v for p,v in code.items())
assert git('rev-parse',TARGET+'^',CODE+'^').decode().splitlines()==[CODE,BASE]
blobs=batch([TARGET+':'+p for p in changed]+[WF+':'+TASK])
assert sha(blobs[WF+':'+TASK][1])=='037a88207fd595c8b34de2a47a6294775e344e8b10299375bda9f0baa2855484'
expected={REPORT:'457d0f85e491ae9cefa757475918c6766cd527179b99aa3b07de06611db5e133',
 EV+'manifest.json':'b280ef782ee85f2c7f92485debc316a6bfae0902b078894e555df59afe904867',
 EV+'sealing/process-release-proof.json':'6dd2da06a5212db39eaac95437dea5f44bc1e07072bbcb8a2ddc22f6cf1eced4',
 EV+'failure-summary.json':'0c2050da2041d150bbdd871dc4521f322566d0154272f942f2609ff315ab2704',
 EV+'validation/author-01/processes/U1-execute/stderr.txt':'1ccb41363eafc7980a8f602e084a4fb97519506b138ad0006cb495c859eb6d74'}
for p,h in expected.items():assert sha(blobs[TARGET+':'+p][1])==h
manifest=json.loads(blobs[TARGET+':'+EV+'manifest.json'][1]);assert len(manifest['files'])==323
assert set(manifest['files'])==set(changed)-{EV+'manifest.json'}
for p,h in manifest['files'].items():assert sha(blobs[TARGET+':'+p][1])==h
inputs=json.loads(blobs[TARGET+':'+EX+'inputs.json'][1]);assert len(inputs['files'])==109 and inputs['base']==BASE
extra=[TARGET+':'+p for p in inputs['files']]+[BASE+':'+p for p in four]
blobs.update(batch(extra))
CRLF={'src/annotation/__init__.py','src/annotation/contracts/__main__.py','src/annotation/contracts/cli.py','src/annotation/contracts/integrity.py','src/annotation/contracts/models.py'}
representations=[]
for p,h in inputs['files'].items():
    b=blobs[TARGET+':'+p][1];mode='RAW_EQUALS_CHECKOUT'
    if sha(b)!=h:
        assert p in CRLF and b'\r\n' not in b and sha(b.replace(b'\n',b'\r\n'))==h;mode='CHECKOUT_CRLF_RAW_LF'
    assert code[p]==target[p]
    representations.append({'path':p,'raw_sha256':sha(b),'raw_bytes':len(b),'checkout_index_sha256':h,
      'checkout_bytes':len(b.replace(b'\n',b'\r\n')) if mode=='CHECKOUT_CRLF_RAW_LF' else len(b),'representation':mode})
assert sum(r['representation']=='CHECKOUT_CRLF_RAW_LF' for r in representations)==5
exports=[]
for spec,(oid,b) in sorted(blobs.items()):
    rev,p=spec.split(':',1);prefix='input/target' if rev==TARGET else 'input/base' if rev==BASE else 'input/workflow'
    relative=Path(prefix)/p
    if len(str(OUT/relative))>235:relative=Path('input/raw')/(sha(spec.encode())[:20]+'-'+Path(p).name)
    write(OUT/relative,b);exports.append({'commit':rev,'path':p,'file':relative.as_posix(),'bytes':len(b),'sha256':sha(b),'raw_git_sha1':oid})
write(OUT/'input-index.json',{'workflow':WF,'base':BASE,'candidate':CODE,'target':TARGET,'exports':exports})
write(OUT/'delivery-byte-review.json',{'protected_old_entries_preserved':33028,'modified_old':modified,'added':len(added),
 'manifest_entries':323,'changed_paths':len(changed),'candidate_files_preserved_in_final':True,'expected_hashes':expected,
 'checkout_source_index_count':109,'checkout_vs_raw':representations,'checkout_only_EOL_differences':5,
 'raw_SQLite_stage_files':[p for p in added if '/captures/' in p and p.endswith('.sqlite3')],
 'all_other_old_entries_unchanged':True,'candidate_vs_base_modified':sorted(p for p in old if code.get(p)!=old[p])})
print(json.dumps({'status':'FROZEN_DELIVERY_BYTES_VERIFIED','exports':len(exports),'changed':len(changed),'stage_DB_files':sum('/captures/' in p and p.endswith('.sqlite3') for p in added),
 'Git_children':counter,'product_calls':0,'SQL_connections':0}))
