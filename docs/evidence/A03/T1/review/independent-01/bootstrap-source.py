import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
SNAP = ROOT / 'snapshot'
EV = Path('D:/1800/docs/evidence/A03/T1/review/independent-01')
TARGET = 'ed90664ab15afd1938725441e2bc86db7884f784'
CODE = '73f21654adb8ee86e33381a3ff3bf1a179303928'
BASE = '1330047dd29890dea0e433ff01b991f615bf78f4'
WORKFLOW = '69ef1b3456c7c44c463c4f4fb43b6064b8cf4e09'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    b = data if isinstance(data, bytes) else (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')
    with path.open('xb') as f:
        f.write(b)

def command(name, args, stdin=None, timeout=30):
    folder = EV / 'bootstrap-processes' / name
    folder.mkdir(parents=True, exist_ok=False)
    assert args[:3] == ['git', '-c', 'core.longpaths=true']
    save(folder/'preregistered.json', dict(argv=args,cwd='D:/1800',timeout_seconds=timeout,
        stdin_sha256=sha(stdin) if stdin is not None else None,script_sha256=sha(Path(__file__).read_bytes())))
    if stdin is not None:
        save(folder/'stdin.bin', stdin)
    with (folder/'stdout.bin').open('xb') as out, (folder/'stderr.bin').open('xb') as err:
        p = subprocess.Popen(args,cwd='D:/1800',stdin=subprocess.PIPE if stdin is not None else None,stdout=out,stderr=err)
        save(folder/'started.json',dict(pid=p.pid,parent_pid=os.getpid(),started_at_ns=time.time_ns()))
        timed_out=False
        try:
            p.communicate(stdin, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True
            p.kill()
            p.communicate(timeout=5)
    save(folder/'completed.json',dict(pid=p.pid,exit_code=p.returncode,alive=p.poll() is None,
        timeout=timed_out,wait_reaped=True,ended_at_ns=time.time_ns(),stdout_sha256=sha((folder/'stdout.bin').read_bytes()),
        stderr_sha256=sha((folder/'stderr.bin').read_bytes())))
    assert p.returncode==0 and not timed_out
    return (folder/'stdout.bin').read_bytes()

def git(name,*args,**kwargs):
    return command(name,['git','-c','core.longpaths=true',*args],**kwargs)

def tree(name, commit):
    raw=git(name,'ls-tree','-r','-z',commit)
    result={}
    for item in raw.split(b'\0'):
        if not item: continue
        meta,path=item.split(b'\t',1)
        mode,kind,oid=meta.decode('ascii').split()
        result[path.decode('utf-8')]=(mode,kind,oid)
    return result

def blobs(name, refs):
    refs=list(refs)
    raw=git(name,'cat-file','--batch',stdin=('\n'.join(refs)+'\n').encode('utf-8'))
    cursor=0
    result=[]
    for ref in refs:
        end=raw.index(b'\n',cursor)
        oid,kind,size=raw[cursor:end].decode('ascii').split()
        assert kind=='blob'
        start=end+1
        data=raw[start:start+int(size)]
        assert raw[start+int(size):start+int(size)+1]==b'\n'
        cursor=start+int(size)+1
        result.append(data)
    assert cursor==len(raw)
    return result

def main():
    SNAP.mkdir(exist_ok=False)
    target_tree=tree('target-tree',TARGET)
    base_tree=tree('base-tree',BASE)
    code_tree=tree('code-tree',CODE)
    prefixes=('examples/a03/T1-capture/','docs/evidence/A03/T1/execution/')
    input_path='examples/a03/T1-capture/inputs.json'
    input_raw,manifest_raw=blobs('input-manifest',[TARGET+':'+input_path,TARGET+':docs/evidence/A03/T1/execution/manifest.json'])
    inputs=json.loads(input_raw)
    manifest=json.loads(manifest_raw)
    assert sha(manifest_raw)=='3fe14986f26b058c200cc75c2922be811dc1d31a98e60fefd9ab986d34036063'
    selected=set(inputs['files'])|{p for p in target_tree if p.startswith(prefixes)}|{'docs/tasks/A03-T1-execution-report.md'}
    paths=sorted(selected)
    data=blobs('selected-blobs',[target_tree[p][2] for p in paths])
    raw_map=dict(zip(paths,data))
    members=manifest['files']
    mismatches=[]
    for p,entry in members.items():
        expected=entry['sha256'] if isinstance(entry,dict) else entry
        if sha(raw_map[p])!=expected: mismatches.append(p)
    assert not mismatches
    changed={p for p in set(target_tree)|set(base_tree) if target_tree.get(p)!=base_tree.get(p)}
    allowed=lambda p:p.startswith(('examples/a03/T1-capture/','docs/evidence/A03/T1/execution/')) or p in ('tests/test_a03_t1_capture.py','docs/tasks/A03-T1-execution-report.md')
    assert all(allowed(p) for p in changed)
    assert all(target_tree.get(p)==code_tree.get(p) for p in target_tree if p.startswith('examples/a03/T1-capture/') or p=='tests/test_a03_t1_capture.py')
    materialized={}
    for p,raw in raw_map.items():
        actual=raw
        entry=inputs['files'].get(p)
        if entry and sha(actual)!=entry['execution_sha256']:
            variants=[raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'),raw.replace(b'\r\n',b'\n')]
            matches=[v for v in variants if sha(v)==entry['execution_sha256']]
            assert matches, 'cannot reproduce exact frozen execution bytes: '+p
            actual=matches[0]
        save(SNAP/p,actual)
        materialized[p]={'raw_git_sha256':sha(raw),'materialized_sha256':sha(actual),'size':len(actual),
            'blob_oid':target_tree[p][2],'representation':'RAW_GIT' if actual==raw else 'EXACT_HASH_MATCHED_CHECKOUT_REPRESENTATION'}
    source_view=json.loads(raw_map['examples/a03/T1-capture/source-view.json'])
    for p,entry in source_view['files'].items():
        original=p.replace('examples/a03/T1-capture/runtime-view/','',1)
        assert target_tree[p][2]==base_tree[original][2]
        assert sha((SNAP/p).read_bytes())==entry['raw_sha256']
    save(EV/'source-materialization.json',dict(target=TARGET,code=CODE,base=BASE,workflow=WORKFLOW,
        author_manifest_sha256=sha(manifest_raw),manifest_members=len(members),manifest_mismatches=mismatches,
        changed_paths=sorted(changed),product_changes=[],runtime_view_raw_files=len(source_view['files']),
        files=materialized,source_checkout_representations=sum(e['representation']!='RAW_GIT' for e in materialized.values())))
    save(EV/'frozen-inputs.json',inputs)
    save(EV/'bootstrap-source.py',Path(__file__).read_bytes())
    print(json.dumps(dict(snapshot=str(SNAP),materialized_files=len(paths),manifest_members=len(members),raw_view_files=len(source_view['files']),input_files=len(inputs['files'])),indent=2))

if __name__=='__main__':
    main()
