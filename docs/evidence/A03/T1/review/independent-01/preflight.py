"""Verify exact frozen inputs, pins and fixture, without executing business."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import pydantic
from dataclasses import asdict
from annotation.contracts.a03_native import select_native_codec
from bootstrap import ROOT,SNAP,EV,save,sha

HERE=SNAP/'examples/a03/T1-capture'
inputs=json.loads((HERE/'inputs.json').read_bytes())
compiled=[]
for path,entry in inputs['files'].items():
    p=SNAP/path
    assert sha(p.read_bytes())==entry['execution_sha256'],path
    if p.suffix=='.py':compile(p.read_bytes().decode('utf-8',errors='strict'),str(p),'exec');compiled.append(path)
fixture=json.loads((ROOT/'fixture-independent-01/result.json').read_bytes())
assert fixture['business_calls']==0 and fixture['thread_joined'] and fixture['connection_closed'] and not fixture['errors']
cap=json.loads((ROOT/'fixture-independent-01/captured/capture.json').read_bytes())
assert cap['writer_boundary']['quiescent']['owned_async_writers']==0
assert len(cap['writer_boundary']['threads_quiet'])==1
assert sha((ROOT/'fixture-independent-01/fixture.sqlite3').read_bytes())==sha((ROOT/'fixture-independent-01/captured/fixture.sqlite3').read_bytes())
selection=asdict(select_native_codec())
assert Path(sys.modules['annotation'].__file__).resolve().is_relative_to(HERE/'runtime-view/src')
out=dict(status='PREFLIGHT_PASS',python=sys.version,executable=sys.executable,platform=platform.platform(),pydantic=pydantic.__version__,
    compiled=compiled,input_files=len(inputs['files']),selection=selection,fixture_raw_copy_match=True,
    annotation_import=sys.modules['annotation'].__file__,business_calls=0,
    reviewer_auditor_sha256=sha((ROOT/'audit.py').read_bytes()),runner_sha256=sha((ROOT/'runner.py').read_bytes()))
save(EV/'preflight.json',out)
print(json.dumps(dict(status=out['status'],input_files=len(inputs['files']),compiled=len(compiled),fixture='PASS',native_pins='PASS'),indent=2))
