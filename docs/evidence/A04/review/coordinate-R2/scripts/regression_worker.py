"""Run frozen unittest files; optional unchanged Node deadline test excluded."""
import argparse,json,os,sys,unittest
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--pattern');p.add_argument('--tests',nargs='+');p.add_argument('--result',type=Path,required=True);a=p.parse_args()
sys.dont_write_bytecode=True;sys.path[:0]=[str(a.root/'src'),str(a.root/'tests')]
suite=unittest.defaultTestLoader.loadTestsFromNames(a.tests) if a.tests else unittest.defaultTestLoader.discover(str(a.root/'tests'),pattern=a.pattern)
module=sys.modules.get('test_a04_collector_review')
if module:
    cls=module.FetchDeadlineReviewTests
    cls.__unittest_skip__=True
    cls.__unittest_skip_why__='R2 strict local-Python scope: unchanged Node synthetic deadline probe not run; retained under R1'
contracts=sys.modules.get('test_contracts')
if contracts:
    method=contracts.ContractTests.test_relative_symlink_may_not_escape_the_sample_root
    method.__unittest_skip__=True
    method.__unittest_skip_why__='R2 local-Python scope; host lacks symlink privilege and original fallback requires external cmd junction; unchanged C01 boundary'
result=unittest.TextTestRunner(verbosity=2).run(suite)
a.result.write_text(json.dumps({'pattern':a.pattern,'selected_tests':a.tests,'tests_run':result.testsRun,'failures':len(result.failures),
 'errors':len(result.errors),'skipped':[{'test':str(t),'reason':r} for t,r in result.skipped],
 'status':'PASS' if result.wasSuccessful() else 'FAIL'},indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if result.wasSuccessful() else 1)
