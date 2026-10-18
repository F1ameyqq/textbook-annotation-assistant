"""Preregister one bounded reviewer invocation, preserving its actual raw streams."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from bootstrap import ROOT,SNAP,EV,sha,save

HERE=SNAP/'examples/a03/T1-capture'
RUN=SNAP/'docs/evidence/A03/T1/execution/validation/independent-01'
ACTIONS={
 'audit-author':([sys.executable,'-X','utf8','-B',str(ROOT/'audit.py'),'--run',str(SNAP/'docs/evidence/A03/T1/execution/validation/author-01'),'--label','author'],60),
 'fixture':([sys.executable,'-X','utf8','-B',str(HERE/'fixture.py'),str(ROOT/'fixture-independent-01')],20),
 'preflight':([sys.executable,'-X','utf8','-B',str(ROOT/'preflight.py')],30),
 'business':([sys.executable,'-X','utf8','-B',str(HERE/'run.py'),'--output',str(RUN)],540),
 'audit-review':([sys.executable,'-X','utf8','-B',str(ROOT/'audit.py'),'--run',str(RUN),'--label','independent'],60),
}

def main():
    name=sys.argv[1];args,timeout=ACTIONS[name]
    folder=EV/'processes'/name;folder.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PYTHONPATH=os.pathsep.join((str(HERE/'runtime-view/src'),str(HERE))),
        PYTHONDONTWRITEBYTECODE='1',A03_T1_IMPORT_AUDIT=str(folder/'import-processes'))
    scripts={p:sha(Path(p).read_bytes()) for p in args if p.endswith('.py')}
    prereg=dict(argv=args,cwd=str(SNAP),timeout_seconds=timeout,expected_exit=0,retries=0,
        scripts=scripts,runner_sha256=sha(Path(__file__).read_bytes()),
        frozen_inputs_sha256=sha((HERE/'inputs.json').read_bytes()),PYTHONPATH=env['PYTHONPATH'])
    save(folder/'preregistered.json',prereg)
    for p in scripts:save(folder/('source-'+Path(p).name),Path(p).read_bytes())
    with (folder/'stdout.bin').open('xb') as out,(folder/'stderr.bin').open('xb') as err:
        p=subprocess.Popen(args,cwd=SNAP,env=env,stdout=out,stderr=err)
        save(folder/'started.json',dict(pid=p.pid,parent_pid=os.getpid(),started_at_ns=time.time_ns()))
        timed_out=False
        try:p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True;p.kill();p.wait(timeout=5)
    completion=dict(pid=p.pid,exit_code=p.returncode,alive=p.poll() is None,timeout=timed_out,wait_reaped=True,
        ended_at_ns=time.time_ns(),stdout_sha256=sha((folder/'stdout.bin').read_bytes()),stderr_sha256=sha((folder/'stderr.bin').read_bytes()))
    save(folder/'completed.json',completion)
    print(json.dumps(completion,indent=2),flush=True)
    print((folder/'stdout.bin').read_bytes().decode('utf-8'),flush=True)
    if p.returncode or timed_out:
        print((folder/'stderr.bin').read_bytes().decode('utf-8'),flush=True)
        raise SystemExit(p.returncode or 1)

if __name__=='__main__':main()
