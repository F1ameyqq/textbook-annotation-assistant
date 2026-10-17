# -*- coding: utf-8 -*-
import hashlib
import json
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];ROOT=Path('D:/1800');WORK=OUT/'isolation/workspace'
TARGET='435aaee2d140e82d3237ce8902d594a1aee70aad';BASE='d9ed692db9ab8e9277f8ffd09e040451e8b8f65f'
WF='74b4fbc9c2778a516cb9f7cadd7e3b3ca5faa639';EV='docs/evidence/A03/execution/P2-R8-R4-remaining/'
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
