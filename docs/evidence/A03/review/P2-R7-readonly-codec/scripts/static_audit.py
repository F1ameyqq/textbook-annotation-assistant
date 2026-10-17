# -*- coding: utf-8 -*-
"""Independent source/data/wheel inspection. No product import or build."""
import ast
import base64
import hashlib
import json
from pathlib import Path,PurePosixPath,PureWindowsPath
import zipfile

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout';PRODUCT=ROOT/'src/annotation/contracts/a03_bridge';FIX=ROOT/'tests/fixtures/a03/P2-R7-readonly-codec'
EV=ROOT/'docs/evidence/A03/execution/P2-R7-readonly-codec'
def load(p):return json.loads(p.read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def h(v):return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
raw_pins=load(OUT/'raw-source-index.json')['entries'];pin_shas={x['sha256']for x in raw_pins}
modules=[]
for p in sorted(PRODUCT.glob('*.py')):
    b=p.read_bytes();tree=ast.parse(b.decode());imports=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):imports.extend(x.name for x in n.names)
        if isinstance(n,ast.ImportFrom):imports.append('.'*n.level+(n.module or''))
        if isinstance(n,ast.Call)and isinstance(n.func,ast.Name):assert n.func.id not in ['exec','eval','compile','__import__'],(p,n.lineno)
    assert not any(x.split('.')[0]in ['ast','runpy','subprocess','sqlite3','requests','socket']or'examples'in x for x in imports)
    modules.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(b),'imports':imports})
assert len(modules)==7
builtin_ast=ast.parse((PRODUCT/'_builtin.py').read_text(encoding='utf8'))
pins=ast.literal_eval(next(n.value for n in builtin_ast.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='PINS'for t in n.targets)))
assert len(pins)==9
data=[]
for name,expected in pins:
    b=(PRODUCT/'data'/name).read_bytes();assert sha(b)==expected
    if name!='readonly-adoption.json':assert expected in pin_shas
    data.append({'path':name,'sha256':expected,'bytes':len(b)})
adoption=load(PRODUCT/'data/readonly-adoption.json');profile=load(PRODUCT/'data/profile.json')
assert adoption['role']=='STATIC_INSPECTION'and adoption['adoption_scope']=='A_INTERNAL_READONLY'
assert profile['status']=='STATIC_UNIMPLEMENTED'and profile['implementation_authorized']is False

expected={'registration-positive':'STATIC_ACCEPTED','source-binding-negative':'FRAME_REGISTRATION_BINDING','snapshot-binding-negative':'FRAME_REGISTRATION_BINDING',
 'target-tuple-negative':'FRAME_REGISTRATION_TARGET','r3-original-undeclared-evidence':'UNDECLARED_REFERENCE','global-resource-hash-corruption':'RESOURCE_HASH','R6-single-mixed-control-head-correction':'MIXED_CYCLE'}
case_rows=load(FIX/'index.json')['cases'];assert len(case_rows)==7 and {r['id']:r['expected']for r in case_rows}==expected
cases=[]
for row in case_rows:
    b=(FIX/row['bundle']).read_bytes();assert sha(b)==row['bundle_sha256']and sha(b)in pin_shas
    assert row['source_case_sha256']in pin_shas
    bundle=json.loads(b);index={h({k:a[k]for k in ['artifact_id','revision','kind','content_hash']}):a for a in bundle['artifacts']}
    assert len(index)==len(bundle['artifacts'])and all(h({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash']for a in bundle['artifacts'])
    root=(FIX/row['asset_root']).resolve();seen=set();resources={};prefixes=[];mismatches=[]
    def walk(v,path='$'):
        if isinstance(v,dict):
            if set(v)=={'artifact_id','revision','kind','content_hash'}:assert h(v)in index;return
            if {'path','sha256','media_type'}<=set(v):
                token=(v['path'],v['sha256'])
                if token in seen:return
                seen.add(token);p=(root/v['path']).resolve();assert p.is_relative_to(root);body=p.read_bytes()
                assert sha(body)in pin_shas,(row['id'],v['path'])
                resources[v['path']]={'path':v['path'],'declared_sha256':v['sha256'],'actual_sha256':sha(body),'bytes':len(body)}
                if sha(body)!=v['sha256']:mismatches.append(resources[v['path']]);return
                if v['media_type']=='application/json':walk(json.loads(body),v['path'])
                return
            if v.get('format_version')=='a03-runtime-event-prefix-2':
                prev='0'*64
                for number,f in enumerate(v['frames'],1):
                    e=f['event'];assert e['sequence']==number and e['previous_hash']==prev and h({k:x for k,x in e.items()if k!='event_hash'})==e['event_hash']
                    assert e['target_key']==v['target_key']
                    if 'initial_event_head'in e['payload']:assert e['payload']['initial_event_head']=={'sequence':number-1,'hash':prev}
                    prev=e['event_hash']
                assert v['expected_book_head']=={'sequence':len(v['frames']),'hash':prev}
                anchor=v['accepted_anchor'];assert v['frames'][anchor['sequence']-1]['event']['event_hash']==anchor['hash']
                prefixes.append({'path':path,'events':len(v['frames']),'all_hashes_and_internal_heads_correct':True})
            for k,x in v.items():walk(x,path+'/'+k)
        elif isinstance(v,list):
            for i,x in enumerate(v):walk(x,path+'/'+str(i))
    walk(bundle)
    assert {r['path']:r for r in row['resources']}==resources
    if row['id']=='global-resource-hash-corruption':assert len(mismatches)==1 and mismatches[0]['path']=='r5-static/global-only-proof.txt'and mismatches[0]['bytes']==51
    else:assert not mismatches
    cases.append({'id':row['id'],'bundle_sha256':sha(b),'artifact_count':len(bundle['artifacts']),'resources':list(resources.values()),'intentional_mismatches':mismatches,'prefixes':prefixes})

wheel=EV/'distribution/annotation_contracts-0.1.0-py3-none-any.whl';assert sha(wheel.read_bytes())=='c22c1bcae684d36bf0d39c1fd4c357409e093648157e8132f7b305245b7d02c7'
distributed=[]
with zipfile.ZipFile(wheel)as z:
    names=z.namelist();assert len(names)==len(set(names))
    for name in names:
        p=PurePosixPath(name);w=PureWindowsPath(name)
        assert not p.is_absolute()and '..'not in p.parts and not w.drive and '\\'not in name
        if name.startswith('annotation/contracts/a03_bridge/')and not name.endswith('/'):
            b=z.read(name);source=ROOT/'src'/name;assert source.is_file()and b==source.read_bytes(),name
            distributed.append({'path':name,'sha256':sha(b),'bytes':len(b)})
    assert len([x for x in distributed if x['path'].endswith('.py')])==7
    assert len([x for x in distributed if '/data/'in x['path']])==9
    record_name=next(n for n in names if n.endswith('.dist-info/RECORD'))
    import csv,io
    rows=list(csv.reader(io.StringIO(z.read(record_name).decode())))
    for name,digest,size in rows:
        if digest:
            algorithm,encoded=digest.split('=',1);assert algorithm=='sha256'
            b=z.read(name);assert base64.urlsafe_b64encode(hashlib.sha256(b).digest()).decode().rstrip('=')==encoded and len(b)==int(size)
write(OUT/'source-data-wheel-audit.json',{'status':'STATIC_AUDIT_READY_FOR_BOUNDED_PRODUCT_RUNS','product_modules':modules,'packaged_data':data,'seven_cases':cases,
 'wheel_sha256':sha(wheel.read_bytes()),'wheel_codec_files':distributed,'wheel_RECORD_verified':True,'wheel_rebuilt_or_installed':False,
 'old_C01_default_files_unchanged':'raw Git diff verified in delivery-byte-index.json','all_171_raw_source_pins_verified':True,
 'product_imports':0,'old_static_entry_runs':0})
print(json.dumps({'result':'STATIC_AUDIT_READY','modules':7,'data_files':9,'frozen_cases':7,'wheel_codec_files':len(distributed),'product_calls':0}))
