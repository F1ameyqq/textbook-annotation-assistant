# -*- coding: utf-8 -*-
"""One original C01 test-contracts discovery run, with raw child receipts."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from nested_rest import install

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout'
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
records,restore=install('c01-compatibility')
try:
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_contracts*.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
finally:restore()
import annotation.contracts as contracts
assert Path(contracts.__file__).resolve()==ROOT/'src/annotation/contracts/__init__.py'
assert all(r.logged and not r.record['alive']and not r.record['timed_out']for r in records)
value={'status':'C01_COMPATIBILITY_PASSED'if result.wasSuccessful()else'REWORK','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
 'skips':[{'test':str(t),'reason':reason}for t,reason in result.skipped],'child_processes':len(records),
 'child_exits':[r.returncode for r in records],'contract_module_file':contracts.__file__,
 'contract_module_sha256':hashlib.sha256(Path(contracts.__file__).read_bytes()).hexdigest(),'pattern':'test_contracts*.py','rounds':1,
 'A03_static_main_session_conversion_or_native_tests':0}
with(OUT/'c01-compatibility-results.json').open('x',encoding='utf8',newline='\n')as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(value,ensure_ascii=False))
assert result.testsRun==70 and result.wasSuccessful()
