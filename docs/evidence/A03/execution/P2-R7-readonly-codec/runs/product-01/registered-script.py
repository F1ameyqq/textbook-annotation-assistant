"""Run only the R7 suite or original C01 contract entry; retain exact outputs."""
import json,os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R7-readonly-codec';sys.path.insert(0,str(EX))
from ops import OUT,sha,write
from child_audit import install
group=sys.argv[1];assert group in('r7','c01')
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
os.environ['PYTHONPATH']=str(ROOT/'src');os.environ['PYTHONDONTWRITEBYTECODE']='1'
children,restore=install(os.environ['A03_R7_RUN_ID'])
if group=='r7':
    import test_a03_r7_readonly_codec as module
    suite=unittest.defaultTestLoader.loadTestsFromModule(module)
else:
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_contracts*.py')
    module=None
try:result=unittest.TextTestRunner(verbosity=2).run(suite)
finally:restore()
assert all(p.poll()is not None for p in children)
summary={'group':group,'tests_run':result.testsRun,'failures':[(str(t),text)for t,text in result.failures],'errors':[(str(t),text)for t,text in result.errors],'skipped':[(str(t),reason)for t,reason in result.skipped],'successful':result.wasSuccessful(),'nested_children':len(children),'product_module_file':None,'observations':getattr(module,'OBSERVATIONS',[]),'old_static_entry_calls':0,'DB_native_network_model_calls':0,'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
if group=='r7':
    import annotation.contracts.a03_bridge as bridge
    summary['product_module_file']=bridge.__file__
    assert not any(getattr(m,'__file__',None)and('/examples/a03/P2-R2' in str(m.__file__).replace('\\','/')or'/examples/a03/P2-R3' in str(m.__file__).replace('\\','/')or'/examples/a03/P2-R5' in str(m.__file__).replace('\\','/'))for m in list(sys.modules.values()))
write(OUT/(os.environ['A03_R7_RUN_ID']+'-result.json'),summary)
print(json.dumps({'group':group,'tests_run':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'nested_children':len(children)}));sys.exit(0 if result.wasSuccessful()else 1)
