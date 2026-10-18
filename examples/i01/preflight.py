"""Record the target-free preflight in a real child process."""
import os
import sys
from support import ROOT, EVIDENCE, run_child, write

raw=EVIDENCE/'preparation/raw-view'
env=dict(os.environ,I01_PROJECT=str(ROOT),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(raw/'src'))
result=run_child(EVIDENCE/'preflight/process',[sys.executable,'-X','utf8','-B',
    str(ROOT/'tests/test_i01_preflight.py')],env=env,timeout=60)
write(EVIDENCE/'preflight/result.json',result)
assert result['exit_code']==0 and not result['timeout']
print('STATIC_PREFLIGHT_OK; targets=0 dispatch=0')
