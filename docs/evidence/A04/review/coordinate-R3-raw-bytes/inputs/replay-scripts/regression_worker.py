import argparse,json,sys,unittest
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--result',type=Path,required=True);a=p.parse_args()
sys.dont_write_bytecode=True;sys.path[:0]=[str(a.root/'src'),str(a.root/'tests')]
modules=['test_a04_png_r3','test_a04_decode_r2','test_a04_source','test_a04_cli']
suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
r=unittest.TextTestRunner(verbosity=2).run(suite)
a.result.write_text(json.dumps({'modules':modules,'tests_run':r.testsRun,'errors':len(r.errors),
 'failures':len(r.failures),'skipped':[{'test':str(t),'reason':x} for t,x in r.skipped],
 'status':'PASS' if r.wasSuccessful() else 'FAIL',
 'not_run_unchanged':['Node deadline','Windows junction','full contracts/browser/coordinate matrix']},indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if r.wasSuccessful() else 1)
