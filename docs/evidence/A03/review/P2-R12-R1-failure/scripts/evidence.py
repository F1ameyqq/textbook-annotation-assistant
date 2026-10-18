# -*- coding: utf-8 -*-
import hashlib
import json
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];ROOT=Path('D:/1800')
TARGET='6affc61d2ab0b1f0d96bb2497c5ae969ebaf1df2';BASE='394fe51f5ed14c5ed312073a20faac0f5cbb9990'
EV='docs/evidence/A03/execution/P2-R12-R1-unknown-projection/'
EX='examples/a03/P2-R12-R1-unknown-projection/'
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
def ref(a):return {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}
def load(p):return json.loads(p.read_bytes())
INDEX=load(OUT/'input-index.json')['exports'];MAP={(r['commit'],r['path']):r for r in INDEX}
def file(path,rev=TARGET):
    r=MAP[(rev,path)];p=OUT/r['file'];b=p.read_bytes();assert sha(b)==r['sha256'] and len(b)==r['bytes'];return p
def raw(path,rev=TARGET):return file(path,rev).read_bytes()
def doc(path,rev=TARGET):return json.loads(raw(path,rev))
def author_key(path):
    p=str(path).replace('\\','/');prefix='C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800/'
    return p[len(prefix):] if p.startswith(prefix) else p
def read_author(path):return raw(author_key(path))
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(v if isinstance(v,bytes) else (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
