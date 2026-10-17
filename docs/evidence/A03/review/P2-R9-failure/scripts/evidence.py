# -*- coding: utf-8 -*-
import hashlib
import json
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];ROOT=Path('D:/1800')
TARGET='c83f956c5c29c64ab10735ba11c153201d3f3f4b';BASE='435aaee2d140e82d3237ce8902d594a1aee70aad';WF='d9c0be133ac86919bea1f9caec29120e0ea650b3'
EV='docs/evidence/A03/execution/P2-R9-minimal-demos/'
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
