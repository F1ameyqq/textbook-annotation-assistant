# -*- coding: utf-8 -*-
"""Read-only reproduction of ONE static EvidenceRecord closure counterexample.

Exit1 means the invalid static value was accepted. No product/native/DB calls.
"""
from pathlib import Path
import importlib.util,json,sys
OUT=Path('D:/1800/docs/evidence/A03/review/P2-R2-proposal');HOME=OUT/'input/checkout/examples/a03/P2-R2-proposal'
sys.path.insert(0,str(HOME))
spec=importlib.util.spec_from_file_location('frozen_static_R2',HOME/'check.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
case=json.loads((OUT/'counterexample/evidence-id-consumer/result.json').read_bytes())
bundle=json.loads((OUT/case['bundle_file']).read_bytes())
overrides={r['logical']:(OUT/r['file']).read_bytes() for r in case['resource_overrides']}
try:
 m.Package(bundle,overrides).validate()
 print(json.dumps({'id':case['id'],'result':'FAIL_EXPECTED_REJECTION','actual':'STATIC_ACCEPTED','native_qualification':False,'product_runs_DB_queries':0}),flush=True)
 raise SystemExit(1)
except m.Rejected as e:
 print(json.dumps({'id':case['id'],'actual':'STATIC_REJECTED','code':e.code,'path':e.path,'native_qualification':False}),flush=True)
 raise SystemExit(0 if e.code in ('UNDECLARED_REFERENCE','ORDINARY_SCOPE') else 2)
