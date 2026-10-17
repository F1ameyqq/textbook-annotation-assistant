"""R6 file/data helpers; no static checker or product import."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];EX=Path(__file__).resolve().parent
OUT=ROOT/'docs/evidence/A03/execution/P2-R6-mixed-control'
BASE='323013c4f0dbae75368e56db60147a8057368d1f';WORKFLOW='77d3e123ab7247eae6f81f7acd669e3a69c934a0'
OLD_CASE='examples/a03/P2-R5-registration-context/cases/artifact-resource-frame-mixed-cycle/repair-01/case.json'
DATA=ROOT/'examples/a03/P2-R2-proposal/candidate-final'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
def h(v):return sha(canon(v))
def load(p):return json.loads(p.read_bytes())
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(json.dumps(v,ensure_ascii=False,indent=2).encode('utf8')+b'\n')
def raw_write(p,raw):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(raw)
def git(*a):return subprocess.check_output(['git','-c','core.longpaths=true',*a],cwd=ROOT)
def ref(a):return{k:a[k]for k in('artifact_id','revision','kind','content_hash')}
def isref(v):return isinstance(v,dict)and set(v)=={'artifact_id','revision','kind','content_hash'}
def isres(v):return isinstance(v,dict)and{'path','sha256','media_type'}<=set(v)
def old_inventory():
    tree=git('ls-tree','-r','-z',BASE);tree_items=[];checkout=hashlib.sha256();count=0
    for token in tree.split(b'\0'):
        if not token:continue
        header,name=token.split(b'\t',1);mode,kind,blob=header.decode().split();name=name.decode('utf8');p=ROOT/name;raw=p.read_bytes()
        row={'path':name,'mode':mode,'type':kind,'blob':blob,'bytes':len(raw),'sha256':sha(raw),'symlink':p.is_symlink()};encoded=canon(row);checkout.update(len(encoded).to_bytes(8,'big'));checkout.update(encoded);count+=1
        tree_items.append((name,mode,kind,blob))
    current={}
    for token in git('ls-tree','-r','-z','HEAD').split(b'\0'):
        if token:
            header,name=token.split(b'\t',1);current[name.decode('utf8')]=tuple(header.decode().split())
    index={}
    for token in git('ls-files','--stage','-z').split(b'\0'):
        if token:
            header,name=token.split(b'\t',1);mode,blob,stage=header.decode().split();assert stage=='0';index[name.decode('utf8')]=(mode,blob)
    for name,mode,kind,blob in tree_items:assert current[name]==(mode,kind,blob)and index[name]==(mode,blob),name
    return{'base':BASE,'old_paths':count,'git_tree_raw_sha256':sha(tree),'checkout_inventory_sha256':checkout.hexdigest(),'mode_type_blob_preserved':True,'algorithm':'Git ls-tree -r -z base order; SHA256 stream of uint64-big-endian length + canonical JSON(path,mode,type,blob,bytes,sha256,symlink) for each current checkout file; verify HEAD/index old entries against base','old_preservation_lists_copied':0}
