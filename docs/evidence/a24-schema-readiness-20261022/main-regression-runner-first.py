"""Fixed synthetic regression for the newly applied readiness patch only."""
from pathlib import Path
import asyncio, datetime, hashlib, importlib.util, io, json, os, socket, subprocess, sys, unittest, urllib.request
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE/'source'
OUT=HERE/'schema-readiness-main'
TEMP=OUT/'long-temp'
TEMP.mkdir(exist_ok=False)
os.environ['TEMP']=os.environ['TMP']=str(TEMP)
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests/a24_first_save_wire_r1')]
from noio_loop import MemoryPolicy
asyncio.set_event_loop_policy(MemoryPolicy())
def forbidden(*a,**k):raise AssertionError('READINESS_REGRESSION_REAL_IO_FORBIDDEN')
specs=[('readiness','tests/a24_schema_readiness/test_schema_readiness.py',14),
       ('controlled_capture','tests/a24_controlled_capture/test_integration.py',7),
       ('current_body','tests/a24_first_save_current_body/test_minimum_gate.py',10),
       ('book_snapshot','tests/a24_book_snapshot_fix/test_book_snapshot.py',4),
       ('wire_r1','tests/a24_first_save_wire_r1/test_r1.py',None)]
rows=[]
with patch.object(socket,'create_connection',forbidden),patch.object(socket.socket,'connect',forbidden),patch.object(subprocess,'Popen',forbidden),patch.object(urllib.request,'urlopen',forbidden):
    for index,(name,rel,expected) in enumerate(specs):
        path=ROOT/rel
        spec=importlib.util.spec_from_file_location('readiness_main_'+str(index),path)
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
        suite=unittest.TestLoader().loadTestsFromModule(module)
        discovered=suite.countTestCases();stream=io.StringIO()
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        row={'suite':name,'path':rel,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'discovered':discovered,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful() and result.testsRun==discovered and discovered>0 and (expected is None or discovered==expected),'raw_output':stream.getvalue()}
        rows.append(row)
        if not row['passed']:break
r={'schema':'A24ReadinessMainSyntheticRegression/v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'suites':rows,'tests':sum(row['tests'] for row in rows),'passed':len(rows)==len(specs) and all(row['passed'] for row in rows),'guard_limit':'MemoryPolicy plus four patched Python entrypoints, not an OS I/O sandbox','platform_business_reads':0,'platform_writes':0,'write_allowed':False,'decision':'SYNTHETIC_ONLY_HOLD'}
with (OUT/'regression.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'tests':r['tests'],'passed':r['passed'],'suites':[{k:row[k] for k in ('suite','tests','failures','errors','passed')} for row in rows]}))
if not r['passed']:raise SystemExit(1)
