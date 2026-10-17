"""Persist the independent data result before permitting the sole Package call."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R6-mixed-control';sys.path.insert(0,str(EX))
from files import OUT,load,sha,write
assert not(OUT/'entry-result.json').exists()
for pin in load(OUT/'raw-input-pins.json')['inputs']:
    raw=(ROOT/pin.get('copy',pin['path'])).read_bytes();assert sha(raw)==pin['sha256']
from data_check import audit
try:
    result=audit();write(OUT/'precheck.json',result)
except BaseException as error:
    write(OUT/'precheck-failure.json',{'status':'STOP_BEFORE_PACKAGE','error':repr(error),'Package_calls':0});raise
print(__import__('json').dumps({'status':result['status'],'prefix_changes':len(result['prefix_semantic_changes']),'bundle_changes':len(result['bundle_semantic_changes']),'artifacts':result['data']['artifacts'],'resources':len(result['data']['resources']),'consumers':len(result['data']['consumers']),'Package_calls':0}))
