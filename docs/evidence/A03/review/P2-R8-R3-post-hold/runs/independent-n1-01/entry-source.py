# -*- coding: utf-8 -*-
"""Normal target imports, then exactly one selected frozen method."""
import json
from pathlib import Path
import sys
import unittest
from evidence import OUT,WORK,TARGET,MAP,sha,write
phase=sys.argv[1];assert phase in ('local','N1','N2','N3','N4','N5')
import annotation
import annotation.runtime.storage as storage
import annotation.runtime.storage.native as native
import annotation.contracts.recovery as recovery
import annotation.quality.synthetic_precheck as producer
observed=[]
for module in (annotation,storage,native,recovery,producer):
    p=Path(module.__file__).resolve();assert p.is_relative_to(WORK/'src')
    source=p.relative_to(WORK).as_posix();assert sha(p.read_bytes())==MAP[(TARGET,source)]['sha256']
    observed.append({'module':module.__name__,'actual_file':str(p),'sha256':sha(p.read_bytes())})
sys.path.insert(0,str(WORK/'tests'))
import test_a03_r8_r3_post_hold as driver
import test_a03_r8_r3_local as local
for module in (driver,local):
    p=Path(module.__file__).resolve();assert p.is_relative_to(WORK/'tests')
    assert sha(p.read_bytes())==MAP[(TARGET,p.relative_to(WORK).as_posix())]['sha256']
case=local.R8R3LocalControls('test_no_hold_owner_and_pending') if phase=='local' else driver.R8R3NativeBridgeTests('test_'+phase)
write(OUT/('imports-'+phase+'.json'),{'phase':phase,'modules':observed,'main_driver':driver.__file__,'local_driver':local.__file__,'test':str(case)})
result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([case]))
value={'phase':phase,'tests_run':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),
 'skips':[str(t) for t,_ in result.skipped],'method':str(case),'rounds':1,'N6_N7_or_compatibility_run':False}
write(OUT/('result-'+phase+'.json'),value)
print(json.dumps(value))
raise SystemExit(0 if result.wasSuccessful() else 1)
