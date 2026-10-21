"""One bounded fail-fast inherited-capture integration set; real I/O forbidden."""
import argparse
import asyncio
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
import unittest
import urllib.request
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"tests/a24_first_save_wire_r1"))
from noio_loop import MemoryPolicy
def forbidden(*args,**kwargs):raise AssertionError("A24_REAL_IO_FORBIDDEN")
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True);args=parser.parse_args()
    path=Path(args.report);assert not path.exists();path.parent.mkdir(parents=True,exist_ok=True)
    asyncio.set_event_loop_policy(MemoryPolicy());output=io.StringIO();started=time.monotonic()
    with patch.object(socket,"create_connection",forbidden),patch.object(socket.socket,"connect",forbidden),patch.object(subprocess,"Popen",forbidden),patch.object(urllib.request,"urlopen",forbidden):
        try:
            suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent),pattern="test_integration.py")
            result=unittest.TextTestRunner(stream=output,verbosity=2,failfast=True).run(suite)
            value={"schema":"A24OwnedCaptureIntegrationControls/v1","tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"passed":result.wasSuccessful(),"successors_after_first_failure":"NOT_RUN_IF_ANY"}
        except BaseException:
            value={"schema":"A24CaptureIntegrationHelperFailure/v1","passed":False,"successors":"NOT_RUN"};output.write(traceback.format_exc())
    value.update(duration_ms=round((time.monotonic()-started)*1000),raw_output=output.getvalue(),actual_resources=0,old_suites_run=0,model_or_content_review=0)
    with path.open("xb") as handle:handle.write((json.dumps(value,indent=2)+"\n").encode())
    print(json.dumps({k:v for k,v in value.items() if k!="raw_output"}))
    if not value["passed"]:print(output.getvalue()[-6000:]);raise SystemExit(1)
