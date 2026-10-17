# -*- coding: utf-8 -*-
"""Normal target imports, then exactly one selected frozen method."""
import json
import copy
from pathlib import Path
import sys
import unittest
from evidence import OUT,WORK,TARGET,MAP,sha,canon,write
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
trace_records={};previous_trace=sys.gettrace()
if phase=='N3':
    from annotation.contracts.a03_native import NativeSchemas
    schema_code=NativeSchemas.check.__code__;compare_code=producer.compare_synthetic_inputs.__code__;test_code=driver.R8R3NativeBridgeTests.test_N3.__code__
    def trace(frame,event,arg):
        if frame.f_code not in (schema_code,compare_code) or frame.f_back is None or frame.f_back.f_code is not test_code:return None
        control=frame.f_back.f_locals['check'];record=trace_records.setdefault(control,{'control':control})
        if frame.f_code is schema_code:
            if event=='call':
                value=copy.deepcopy(frame.f_back.f_locals['data']);folder=OUT/'traces/N3';folder.mkdir(parents=True,exist_ok=True)
                path=folder/(control+'-actual-schema-input.json');write(path,value)
                record.update(input_file=path.relative_to(OUT).as_posix(),input_canonical_sha256=sha(canon(value)),schema_exception=False)
            elif event=='exception':record['schema_exception']=True
            elif event=='return':record['schema_returned']=not record['schema_exception']
        else:
            if event=='call':
                record['compare_input_canonical_sha256']=sha(canon(frame.f_back.f_locals['data']))
                record['asset_root']=str(frame.f_locals['asset_root'])
            elif event=='return':record['comparison_result']=copy.deepcopy(arg)
        return trace
    sys.settrace(trace)
try:result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([case]))
finally:sys.settrace(previous_trace)
if phase=='N3':write(OUT/'N3-readonly-trace.json',{'actual_input_snapshots':list(trace_records.values()),'method':'non-mutating sys.settrace; no candidate changes or additional calls'})
value={'phase':phase,'tests_run':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),
 'skips':[str(t) for t,_ in result.skipped],'method':str(case),'rounds':1,'N6_N7_or_compatibility_run':False}
write(OUT/('result-'+phase+'.json'),value)
print(json.dumps(value))
raise SystemExit(0 if result.wasSuccessful() else 1)
