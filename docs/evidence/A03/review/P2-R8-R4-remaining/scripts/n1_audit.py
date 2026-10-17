# -*- coding: utf-8 -*-
"""N1 formal boundaries from immutable own copies, never author store APIs."""
import json
from pathlib import Path
from evidence import OUT,WORK,EV,load,author_read
from verify_case import verify_case
identity=load(OUT/'independent-run.json');root=Path(identity['run_root']).resolve()
assert root.is_relative_to(WORK) and load(OUT/'result-N1.json')['successful']
def independent_read(path):
    p=Path(path);p=p if p.is_absolute() else WORK/p;p=p.resolve();assert p.is_relative_to(root);return p.read_bytes()
results=[]
for label,read,case in [('author',author_read,EV+'validation/r4-native-01/cases/N1/'),
 ('independent',independent_read,str(root/'cases/N1')+'/')]:
    boundary=verify_case(label,read,case+'runtime/runtime.sqlite3',case+'target/target.sqlite3',False)
    assert boundary['counts']['runtime']['artifacts']==20 and boundary['counts']['runtime']['native_pre_runs']==1
    assert boundary['counts']['target']['observations']==4 and boundary['POST_HOLD_run_rows']==0
    results.append({'label':label,'status':boundary['status'],'effect_count':boundary['effect_count'],'artifacts':20})
print(json.dumps({'status':'BOTH_R4_N1_FORMAL_BOUNDARIES_VERIFIED','results':results,'native_API_calls':0}))
