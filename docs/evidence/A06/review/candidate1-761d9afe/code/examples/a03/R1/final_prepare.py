"""Final bounded package preparation: raw bytes and pure contracts only."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/evidence/A03/R1/final-correction'
PRODUCT='6097a06de937fee8876feccedf46920510850b83'
BASE='54e86adfaf144093a688b62fe0dad5190ceb2fa6'


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,default=str)+'\n').encode('utf-8'))


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj


def export(candidate,view,prefixes):
    args=['git','-c','core.longpaths=true','-C',str(ROOT)]
    paths=subprocess.check_output(args+['ls-tree','-r','--name-only',candidate,*prefixes]).decode().splitlines()
    raw=subprocess.check_output(args+['cat-file','--batch'],input=''.join(candidate+':'+p+'\n'for p in paths).encode())
    pos=0;rows=[]
    for path in paths:
        end=raw.index(b'\n',pos);header=raw[pos:end].split();pos=end+1;size=int(header[2])
        value=raw[pos:pos+size];pos+=size+1;dest=view/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(value)
        rows.append(dict(path=path,git_blob=header[0].decode(),bytes=size,sha256=hashlib.sha256(value).hexdigest()))
    return rows


def prepare():
    assert subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip()==BASE
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'.gitignore').write_text('**/runtime-view/\n',encoding='utf-8')
    (OUT/'.gitattributes').write_text('* -text\n',encoding='utf-8')
    pre=OUT/'preparation';pre.mkdir(exist_ok=True);view=pre/'runtime-view'
    identities=export(BASE,view,['src/annotation','examples/a03/T3-closure','examples/a03/T1-capture/capture.py',
        'examples/a02/R1/scenarios.py','tests/fixtures/a02/normal',
        'examples/a03/P2-R12-R1-unknown-projection/legacy-recovery'])
    write(pre/'raw-identities.json',dict(product=PRODUCT,source=BASE,files=identities))
    sys.path.insert(0,str(view/'src'))
    from annotation.runtime.storage.native import NativeRegistry,NativeRuntimeStore
    from annotation.contracts import load_bundle,validate_bundle,seal_artifact,write_bundle
    from annotation.contracts.a03_bridge._resources import ResourceReader
    fixture=view/'examples/a03/T3-closure/inputs/single'
    data=json.loads((fixture/'initial.json').read_bytes())
    store=NativeRuntimeStore.__new__(NativeRuntimeStore);store.native_registry=NativeRegistry(store)
    store._validate(data,asset_root=fixture)
    pgm=(fixture/'assets/page-1.pgm').read_bytes()
    assert len(pgm)==3579 and hashlib.sha256(pgm).hexdigest()=='1f82898615c67c676c532b17a8bd8e801c73eb6e7e2ba5a7f685bf1c3582cc7a'
    case=ROOT/'docs/evidence/A03/R1/execution/candidate-1/business/cases/M2-sufficient'
    old=ROOT/'docs/evidence/A03/R1/execution/deltas-correction/L1/captures/after-release'
    continuation=[]
    for label,path in [('runtime',case/'runtime/runtime.sqlite3'),('target',case/'target/target.sqlite3')]:
        raw=path.read_bytes();assert raw==(old/(label+'.sqlite3')).read_bytes(),label
        continuation.append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    helper=module(view/'examples/a02/R1/scenarios.py','raw_a02_helper')
    dest=ROOT/'tests/fixtures/a03/R1/final';dest.mkdir(parents=True,exist_ok=True)
    (dest/'.gitattributes').write_text('* -text\n',encoding='utf-8')
    bdir=dest/'B-representations';bdir.mkdir(exist_ok=True)
    b,config=helper.own_input(view,bdir,'book-M-single','R1-final-B',scope='scope-M-single')
    value=b.model_dump()
    for a in value['artifacts']:
        if a['kind']=='PlatformSnapshot':a['payload']['target_id']='target-M-single';a.update(seal_artifact(a))
    def retain_bundle(bundle,path):
        if path.exists():assert json.loads(path.read_bytes())==bundle.model_dump()
        else:write_bundle(bundle,path)
    b=validate_bundle(value,asset_root=bdir);retain_bundle(b,bdir/'single.json')
    histories=[]
    for ordinal in (1,2):
        path=ROOT/f'docs/evidence/A03/R1/execution/deltas-correction/legacy/history-{ordinal}/history.json'
        histories.append(load_bundle(path))
        def copy_resources(v):
            if isinstance(v,dict):
                if {'path','sha256','media_type'}<=set(v):
                    p=(path.parent/v['path']).resolve();raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==v['sha256']
                    target=bdir/v['path'];target.parent.mkdir(parents=True,exist_ok=True)
                    if target.exists():assert target.read_bytes()==raw
                    else:target.write_bytes(raw)
                    if v['media_type']=='application/json':copy_resources(json.loads(raw))
                else:
                    for x in v.values():copy_resources(x)
            elif isinstance(v,list):
                for x in v:copy_resources(x)
        copy_resources(json.loads(path.read_bytes()))
    # The two immutable A histories reuse several C01 evidence IDs for
    # different bytes. Do not rewrite either old history to merge them. One
    # foreign UNKNOWN is sufficient for the legal multi-book B representation;
    # both histories continue to exist independently in the actual A ledger.
    mixed=helper.merge(bdir,b,histories[0]);retain_bundle(mixed,bdir/'mixed.json')
    # Deterministic post-marker I/O failure: a legal source resource directory
    # has the same name as the converter's destination INCOMPLETE marker.
    cdir=dest/'conversion-failure';cdir.mkdir(exist_ok=True)
    import shutil
    shutil.copytree(bdir/'assets',cdir/'assets',dirs_exist_ok=True)
    c=json.loads((bdir/'single.json').read_bytes())
    resource=c['evidence'][0]['resource'];raw=(bdir/resource['path']).read_bytes()
    resource['path']='conversion-incomplete.json/proof.txt'
    cp=cdir/resource['path'];cp.parent.mkdir(exist_ok=True);cp.write_bytes(raw)
    validate_bundle(c,asset_root=cdir);write(cdir/'input.json',c)
    inputs=[]
    for path in sorted(dest.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();inputs.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    write(pre/'checks.json',dict(native_raw_input='COMPLETE_VALIDATION_OK',native_pgm_bytes=len(pgm),
        native_pgm_sha256=hashlib.sha256(pgm).hexdigest(),continuation=continuation,inputs=inputs,
        B_single_and_mixed='PUBLIC_C01_VALIDATION_OK; identical B consumers; mixed native admission not claimed',
        converter_failure_input='PUBLIC_C01_VALIDATION_OK',sqlite_connections=0,targets=0,dispatch=0,legacy_generation=0))
    print('FINAL_STATIC_PREPARATION_OK')


if __name__=='__main__':prepare()
