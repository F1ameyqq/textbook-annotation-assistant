# -*- coding: utf-8 -*-
"""Complete the reviewer's C01 isolation, raw source only; no generator call."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout';name='examples/contracts/build_fixtures.py'
base='81d3ec7e42e0a1a76ad744bf59536fc5f68adee4';target='8ad45dd07214ae406a3fab28d76a4b5abd6eef03'
specs=[base+':'+name,target+':'+name]
raw=subprocess.run(['git','cat-file','--batch'],cwd='D:/1800',input=('\n'.join(specs)+'\n').encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
pos=0;found=[]
for spec in specs:
    end=raw.index(b'\n',pos);header=raw[pos:end].decode().split();pos=end+1;assert header[1]=='blob';n=int(header[2]);body=raw[pos:pos+n];pos+=n+1
    assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+body).hexdigest()==header[0];found.append((header[0],body))
assert pos==len(raw)and found[0]==found[1]
tree=ast.parse(found[1][1].decode());assert any(isinstance(n,ast.FunctionDef)and n.name=='summary'for n in tree.body)
assert any(isinstance(n,ast.If)and ast.unparse(n.test)=="__name__ == '__main__'"for n in tree.body)
p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True)
with p.open('xb')as f:f.write(found[1][1])
value={'commit':target,'base':base,'path':name,'file':p.relative_to(OUT).as_posix(),'bytes':len(found[1][1]),'sha256':hashlib.sha256(found[1][1]).hexdigest(),'raw_git_sha1':found[1][0],
 'role':'unchanged sibling dependency imported by original consume.py for summary only; generator __main__ never run'}
with(OUT/'compatibility-input-supplement.json').open('x',encoding='utf8',newline='\n')as f:json.dump({'files':[value]},f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'result':'REVIEW_C01_DEPENDENCY_COMPLETED','source':name,'product_or_wheel_changed':False,'generator_called':False}))
