# -*- coding: utf-8 -*-
import hashlib
import json
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];ROOT=Path('D:/1800');WORK=OUT/'isolation/workspace'
TARGET='cc5966dc58c62017a27266c40ca0cedc5c68485c';BASE='1c26b4a8eb378af33e57668472d2071e9ea6afff';WF='0b843a49f394e962e4113ab3b04375e4f4698008'
EV='docs/evidence/A03/execution/P2-R11-crash-cuts/'
def load(p):return json.loads(p.read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def ref(a):return {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}
INDEX=load(OUT/'input-index.json')['exports'];MAP={(r['commit'],r['path']):r for r in INDEX}
def file(path,rev=TARGET):
    r=MAP[(rev,path)];p=OUT/r['file'];b=p.read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'];return p
def raw(path,rev=TARGET):return file(path,rev).read_bytes()
def text(path,rev=TARGET):return raw(path,rev).decode('utf8')
def document(path,rev=TARGET):return json.loads(raw(path,rev))
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def author_key(path):
    path=str(path).replace('\\','/');prefix='C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800/'
    return path[len(prefix):] if path.startswith(prefix) else path
def author_read(path):return raw(author_key(path))
