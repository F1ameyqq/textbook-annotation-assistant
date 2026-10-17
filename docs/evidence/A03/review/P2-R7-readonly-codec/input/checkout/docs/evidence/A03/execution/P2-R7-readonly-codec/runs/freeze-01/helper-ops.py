"""Local R7 evidence/file helpers, never imported by the product."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];EX=Path(__file__).resolve().parent
OUT=ROOT/'docs/evidence/A03/execution/P2-R7-readonly-codec';FIX=ROOT/'tests/fixtures/a03/P2-R7-readonly-codec';PRODUCT=ROOT/'src/annotation/contracts/a03_bridge'
BASE='81d3ec7e42e0a1a76ad744bf59536fc5f68adee4';WORKFLOW='5a69df310517f0ca22708262c737db9a5676be32'
DATA=ROOT/'examples/a03/P2-R2-proposal/candidate-final'
PACKAGE_DATA_APPEND=b'\r\n[tool.setuptools.package-data]\r\n"annotation.contracts.a03_bridge" = ["data/*.json", "data/schemas/*.json"]\r\n'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
def load(p):return json.loads(p.read_bytes())
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(json.dumps(v,ensure_ascii=False,indent=2).encode('utf8')+b'\n')
def raw_write(p,raw):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(raw)
def git(*a,**kwargs):return subprocess.check_output(['git','-c','core.longpaths=true',*a],cwd=ROOT,**kwargs)
def raw_git_batch(keys):
    raw=git('cat-file','--batch',input=''.join(commit+':'+name+'\n'for commit,name in keys).encode('utf8'));position=0;result={}
    for key in keys:
        end=raw.index(b'\n',position);header=raw[position:end].decode().split();assert header[1]=='blob',key;size=int(header[2]);position=end+1;body=raw[position:position+size];position+=size+1;result[key]=(header[0],body)
    assert position==len(raw);return result
def preservation():
    tree=git('ls-tree','-r','-z',BASE);stream=hashlib.sha256();rows=[]
    for token in tree.split(b'\0'):
        if not token:continue
        header,name=token.split(b'\t',1);mode,kind,blob=header.decode().split();name=name.decode('utf8')
        if name=='pyproject.toml':continue
        p=ROOT/name;raw=p.read_bytes();value={'path':name,'mode':mode,'type':kind,'blob':blob,'bytes':len(raw),'sha256':sha(raw),'symlink':p.is_symlink()};encoded=canon(value);stream.update(len(encoded).to_bytes(8,'big'));stream.update(encoded);rows.append((name,mode,kind,blob))
    current={}
    for token in git('ls-tree','-r','-z','HEAD').split(b'\0'):
        if token:
            header,name=token.split(b'\t',1);current[name.decode('utf8')]=tuple(header.decode().split())
    for name,mode,kind,blob in rows:assert current[name]==(mode,kind,blob),name
    return{'base':BASE,'preserved_old_paths':len(rows),'excluded_only':'pyproject.toml (exact package-data append audited separately)','git_base_tree_sha256':sha(tree),'checkout_inventory_sha256':stream.hexdigest(),'mode_type_blob_preserved':True,'algorithm':'base ls-tree order; SHA256(uint64be length + canonical JSON path/mode/type/blob/bytes/sha256/symlink) per old path except pyproject; HEAD metadata compared per path'}
def verify_old_exception():
    original=git('show',BASE+':pyproject.toml');actual=(ROOT/'pyproject.toml').read_bytes();assert actual==original+PACKAGE_DATA_APPEND
    return{'path':'pyproject.toml','base_sha256':sha(original),'new_sha256':sha(actual),'only_change':'explicit annotation.contracts.a03_bridge package-data table/key','dependencies_versions_other_config_changed':False}
