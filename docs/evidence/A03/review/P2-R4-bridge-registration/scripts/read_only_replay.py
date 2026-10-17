"""Future read-only reproduction. Not run again during this bounded review."""
import io
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

out=Path(__file__).resolve().parents[1];name=sys.argv[1]if len(sys.argv)>1 else'registration-positive'
assert name in ['registration-positive','source-binding-negative','snapshot-binding-negative','target-tuple-negative']
entry=out/'scripts/review_case.py';original_open=Path.open
def read_only_open(path,mode='r',*args,**kwargs):
    if any(x in mode for x in 'wax+'):
        assert path==out/'cases'/name/'result.json'and mode=='x'
        return io.StringIO()
    return original_open(path,mode,*args,**kwargs)
def suppress_mkdir(path,*args,**kwargs):
    assert path.resolve().is_relative_to(out)
sys.argv=[str(entry),name]
with patch.object(Path,'open',read_only_open),patch.object(Path,'mkdir',suppress_mkdir):
    runpy.run_path(str(entry),run_name='__main__')
