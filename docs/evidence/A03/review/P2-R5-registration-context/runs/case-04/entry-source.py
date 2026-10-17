# -*- coding: utf-8 -*-
"""Execute the frozen read-only driver once, with independently pinned sources."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout';EX=ROOT/'examples/a03/P2-R5-registration-context'
tag,case_id,*options=sys.argv[1:];assert all(x=='--repair'for x in options)
allowed=['registration-positive','source-binding-negative','snapshot-binding-negative','target-tuple-negative','r3-original-undeclared-evidence','global-resource-hash-corruption','artifact-resource-frame-mixed-cycle']
assert case_id in allowed and ('--repair'in options)==(case_id==allowed[-1])and sys.flags.optimize==0
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
index=json.loads((OUT/'input-index.json').read_bytes());pinned={x['file']:x for x in index['files']}
paths=['examples/a03/P2-R5-registration-context/'+n for n in ['common.py','load_static.py','registration.py','run_case.py']]
paths+=['examples/a03/P2-R3-evidence-closure/closure.py','examples/a03/P2-R2-proposal/check.py',
        'examples/a03/P2-R2-proposal/schema_check.py','examples/a03/P2-R2-proposal/oracle_verifier.py',
        'docs/evidence/A03/execution/P2-R3-evidence-closure/r2-input-pins.json']
sources=[]
for path in paths:
    p=ROOT/path;raw=p.read_bytes();expected=pinned[p.relative_to(OUT).as_posix()]
    assert sha(raw)==expected['sha256']and len(raw)==expected['bytes']
    sources.append({'path':path,'sha256':sha(raw),'bytes':len(raw)})
write(OUT/'source-pins'/(tag+'.json'),{'source_files':sources,'mode':'exact frozen run_case.py --readonly; no redirection or semantic edits',
 'case':case_id,'repair_index':'--repair'in options,'generator_runs':0})
sys.path.insert(0,str(EX));sys.argv=[str(EX/'run_case.py'),case_id,'--readonly',*options]
try:
    runpy.run_path(str(EX/'run_case.py'),run_name='__main__')
    code=0
except SystemExit as e:code=e.code
assert code==0,('frozen case unexpected outcome',code)
loader=sys.modules['load_static'];assert loader.r3.Package.entry_calls==1
assert not any(name=='annotation'or name.startswith('annotation.')for name in sys.modules)
write(OUT/'call-counts'/(tag+'.json'),{'case':case_id,'exact_driver_exit':code,'observed_R3_entry_call_counter':loader.r3.Package.entry_calls,
 'loader':loader.LOADER,'product_module_imports':0,'models_or_oracle_comparisons':0})
