# -*- coding: utf-8 -*-
"""Resolve frozen bytes; never import candidate modules."""
import hashlib
import json
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
ROOT=Path('D:/1800')
TARGET='fa6edeb7e9dd0c9502781747e5fce012931d9441'
EV='docs/evidence/A03/execution/P2-R8-native-bridge/'
def load(path):return json.loads(path.read_bytes())
def sha(raw):return hashlib.sha256(raw).hexdigest()
INDEX=load(OUT/'input-index.json')['exports']
BY_PATH={r['path']:r for r in INDEX if r['commit']==TARGET}
def file(path):
    row=BY_PATH[path];p=OUT/row['file'];raw=p.read_bytes()
    assert len(raw)==row['bytes'] and sha(raw)==row['sha256'];return p
def raw(path):return file(path).read_bytes()
def text(path):return raw(path).decode('utf8')
def document(path):return json.loads(raw(path))
def write(path,value):
    with path.open('x',encoding='utf8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
