# -*- coding: utf-8 -*-
"""One exact frozen readonly entry, gated by the independent data audit."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout';EX=ROOT/'examples/a03/P2-R6-mixed-control'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
audit=load(OUT/'independent-data-audit.json');assert audit['status']=='INDEPENDENT_DATA_READY_FOR_SINGLE_ENTRY'and audit['new_residuals']==[]
assert audit['bundle_sha256']==sha((EX/'bundle.json').read_bytes())and audit['prefix_sha256']==sha((EX/'resources/prefix.json').read_bytes())
pins=load(OUT/'input-index.json')['files'];expected={x['file']:x for x in pins}
paths=['examples/a03/P2-R6-mixed-control/entry.py','examples/a03/P2-R6-mixed-control/files.py',
 'examples/a03/P2-R5-registration-context/registration.py','examples/a03/P2-R5-registration-context/load_static.py','examples/a03/P2-R5-registration-context/common.py',
 'examples/a03/P2-R3-evidence-closure/closure.py','examples/a03/P2-R2-proposal/check.py','examples/a03/P2-R2-proposal/schema_check.py',
 'examples/a03/P2-R2-proposal/oracle_verifier.py','docs/evidence/A03/execution/P2-R3-evidence-closure/r2-input-pins.json']
source_pins=[]
for name in paths:
    p=ROOT/name;b=p.read_bytes();pin=expected[p.relative_to(OUT).as_posix()];assert sha(b)==pin['sha256']and len(b)==pin['bytes']
    source_pins.append({'path':name,'sha256':sha(b),'bytes':len(b)})
write(OUT/'actual-source-pins.json',{'sources':source_pins,'mode':'exact frozen entry.py --readonly, no source/output rewrites',
 'independent_audit_sha256':sha((OUT/'independent-data-audit.json').read_bytes()),'profile':'non-mutating independent sys.setprofile call observer'})
count_files={str(ROOT/'examples/a03/P2-R5-registration-context/registration.py'):'R5',str(ROOT/'examples/a03/P2-R3-evidence-closure/closure.py'):'R3',str(ROOT/'examples/a03/P2-R2-proposal/check.py'):'R2'}
counts={n:0 for n in count_files.values()}
def profile(frame,event,arg):
    if event=='call'and frame.f_code.co_name=='validate'and frame.f_code.co_filename in count_files:counts[count_files[frame.f_code.co_filename]]+=1
previous=sys.getprofile();sys.path.insert(0,str(EX));sys.argv=[str(EX/'entry.py'),'--readonly'];sys.setprofile(profile)
try:
    try:runpy.run_path(str(EX/'entry.py'),run_name='__main__');code=0
    except SystemExit as e:code=e.code
finally:sys.setprofile(previous)
r3=sys.modules['load_static'].r3
write(OUT/'independent-call-counts.json',{'profile_call_counts':counts,'R3_entry_counter_after':r3.Package.entry_calls,
 'frozen_driver_exit_code':code,'method':'independent call profile concurrent with frozen driver line trace','entry_runs':1,
 'product_modules_imported':any(n=='annotation'or n.startswith('annotation.')for n in sys.modules)})
assert code==0 and counts=={'R5':1,'R3':1,'R2':1}and r3.Package.entry_calls==1
assert not any(n=='annotation'or n.startswith('annotation.')for n in sys.modules)
