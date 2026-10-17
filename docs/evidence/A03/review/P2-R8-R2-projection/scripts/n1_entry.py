# -*- coding: utf-8 -*-
"""Normal imports, then exactly the unchanged fixed N1 method once."""
import json
from pathlib import Path
import sys
import unittest
from evidence import OUT,WORK,TARGET,MAP,sha,write

import annotation
import annotation.runtime.storage as storage
import annotation.runtime.storage.native as native
import annotation.contracts.recovery as recovery
import annotation.quality.synthetic_precheck as producer

observed=[]
for module in (annotation,storage,native,recovery,producer):
    path=Path(module.__file__).resolve();assert path.is_relative_to(WORK/'src')
    source=path.relative_to(WORK).as_posix();assert sha(path.read_bytes())==MAP[(TARGET,source)]['sha256']
    observed.append({'module':module.__name__,'actual_file':str(path),'sha256':sha(path.read_bytes())})
sys.path.insert(0,str(WORK/'tests'))
import test_a03_r8_r2_projection as driver
assert Path(driver.__file__).resolve()==WORK/'tests/test_a03_r8_r2_projection.py'
driver_sha=sha(Path(driver.__file__).read_bytes());assert driver_sha==MAP[(TARGET,'tests/test_a03_r8_r2_projection.py')]['sha256']
write(OUT/'independent-imports.json',{'modules':observed,'driver_actual_file':driver.__file__,'driver_sha256':driver_sha,
 'test':'R8R2NativeBridgeTests.test_N1','source':'normal Python imports from exact raw-Git isolated package'})
suite=unittest.TestSuite([driver.R8R2NativeBridgeTests('test_N1')])
result=unittest.TextTestRunner(verbosity=2).run(suite)
write(OUT/'independent-test-result.json',{'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
 'skips':[str(t) for t,_ in result.skipped],'successful':result.wasSuccessful(),
 'only_test':'R8R2NativeBridgeTests.test_N1','candidate_functional_rounds':1,'N2_N7_or_compatibility_run':False})
print(json.dumps({'status':'INDEPENDENT_N1_PASS' if result.wasSuccessful() else 'INDEPENDENT_N1_FAILED','tests_run':result.testsRun,
 'failures':len(result.failures),'errors':len(result.errors)}))
raise SystemExit(0 if result.wasSuccessful() else 1)
