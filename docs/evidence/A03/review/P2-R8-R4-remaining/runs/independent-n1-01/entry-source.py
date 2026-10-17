# -*- coding: utf-8 -*-
"""Normal frozen imports and output-only test routing; exactly one R4 method."""
import json
from pathlib import Path
import sys
import unittest
from evidence import OUT,WORK,TARGET,MAP,load,sha,write
phase=sys.argv[1];assert phase in ('N1','N6','N7')
identity=load(OUT/'independent-run.json');root=Path(identity['run_root']).resolve();assert root.is_relative_to(WORK)
sys.path.insert(0,str(WORK/'tests'))
import test_a03_r8_r4_remaining as driver
import test_a03_r8_r3_post_hold as accepted
assert driver.ROOT==accepted.ROOT==WORK
initial={'R4.EVIDENCE':str(driver.EVIDENCE),'R3.EVIDENCE':str(accepted.EVIDENCE),'R3.BASE_EVIDENCE':str(accepted.BASE_EVIDENCE)}
driver.EVIDENCE=root
accepted.EVIDENCE=root
accepted.BASE_EVIDENCE=driver.OUT
method={'N1':'test_N1','N6':'test_N6','N7':'test_N7_initialization'}[phase]
write(OUT/('routing-'+phase+'.json'),{'phase':phase,'before':initial,'after':{'R4.EVIDENCE':str(driver.EVIDENCE),
 'R3.EVIDENCE':str(accepted.EVIDENCE),'R3.BASE_EVIDENCE':str(accepted.BASE_EVIDENCE)},
 'method':method,'source_bytes_changed':False,'product_patched':False,'extra_product_calls':0})
case=driver.R4RemainingTests(method)
try:result=unittest.TextTestRunner(verbosity=2,failfast=True).run(unittest.TestSuite([case]))
finally:
    modules=[]
    for name,module in list(sys.modules.items()):
        if not (name.startswith('annotation') or name in ('test_a03_r8_r4_remaining','test_a03_r8_r3_post_hold')):continue
        path=getattr(module,'__file__',None)
        if path:
            p=Path(path).resolve();assert p.is_relative_to(WORK)
            source=p.relative_to(WORK).as_posix();digest=sha(p.read_bytes());assert digest==MAP[(TARGET,source)]['sha256']
            modules.append({'module':name,'actual_file':str(p),'source':source,'sha256':digest})
    write(OUT/('imports-'+phase+'.json'),{'phase':phase,'executable':sys.executable,'modules':modules,'normal_import':True})
    driver.write('imports/'+phase+'.json',driver.modules())
value={'phase':phase,'method':method,'tests_run':result.testsRun,'successful':result.wasSuccessful(),
 'failures':len(result.failures),'errors':len(result.errors),'skips':[str(t) for t,_ in result.skipped],
 'rounds':1,'only_R4_N1_N6_N7_initialization':True,'other_groups_or_old_target_replayed':False}
write(OUT/('result-'+phase+'.json'),value);print(json.dumps(value))
raise SystemExit(0 if result.wasSuccessful() else 1)
