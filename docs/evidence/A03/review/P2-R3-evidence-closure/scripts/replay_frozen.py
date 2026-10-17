"""Read-only reproduction command; suppress only the static overlay output mkdir."""
import importlib.util
import os
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

out=Path(__file__).resolve().parents[1];root=out/'input/checkout'
example=root/'examples/a03/P2-R3-evidence-closure'
os.environ['A03_R3_RUN_ID']='frozen-replay'
def suppress_output_mkdir(path,*args,**kwargs):
    assert path==root/'docs/evidence/A03/execution/P2-R3-evidence-closure/r2-regression/frozen-replay'
spec=importlib.util.spec_from_file_location('closure',example/'closure.py');closure=importlib.util.module_from_spec(spec)
sys.modules['closure']=closure
with patch.object(Path,'mkdir',suppress_output_mkdir):spec.loader.exec_module(closure)
sys.argv=[str(example/'replay.py'),'--case','original','--expect','UNDECLARED_REFERENCE']
runpy.run_path(str(example/'replay.py'),run_name='__main__')
