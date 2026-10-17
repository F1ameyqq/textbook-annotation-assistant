# -*- coding: utf-8 -*-
import hashlib
import json
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];ROOT=Path('D:/1800')
TARGET='a0c40886f3076f84c46377e03fc2206d2fdc5585';BASE='fa6edeb7e9dd0c9502781747e5fce012931d9441'
EV='docs/evidence/A03/execution/P2-R8-R1-producer/'
def load(p):return json.loads(p.read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def ref(a):return {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}
INDEX=load(OUT/'input-index.json')['exports']
MAP={(r['commit'],r['path']):r for r in INDEX}
def file(path,rev=TARGET):
    row=MAP[(rev,path)];p=OUT/row['file'];b=p.read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256'];return p
def raw(path,rev=TARGET):return file(path,rev).read_bytes()
def text(path,rev=TARGET):return raw(path,rev).decode('utf8')
def document(path,rev=TARGET):return json.loads(raw(path,rev))
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def stored_path(value):
    value=value.replace('\\','/')
    prefix='C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800/'
    assert value.startswith(prefix),value
    return value[len(prefix):]
