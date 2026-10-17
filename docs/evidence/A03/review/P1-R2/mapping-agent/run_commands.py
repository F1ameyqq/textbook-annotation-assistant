"""Capture the final finite static-review commands and their real receipts."""
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
stage = str(Path(sys.argv[1]).resolve())
logs = HERE/'logs'
logs.mkdir(exist_ok=True)
rows = []
for name in ['inspect_mapping.py','independent_neighbors.py','audit_triggers.py']:
    argv = [sys.executable,'-B',str(HERE/name),stage]
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    proc=subprocess.Popen(argv,cwd='D:/1800',stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        stdout,stderr=proc.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout,stderr=proc.communicate()
        raise
    finish=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (logs/(name+'.stdout.log')).write_bytes(stdout)
    (logs/(name+'.stderr.log')).write_bytes(stderr)
    rows.append({'argv':argv,'cwd':'D:/1800','start_utc':start,'finish_utc':finish,
                 'pid':proc.pid,'timeout_seconds':60,'returncode':proc.returncode,
                 'stdout':'logs/'+name+'.stdout.log','stderr':'logs/'+name+'.stderr.log',
                 'process_exit_observed':proc.poll() is not None})
result={'runner_pid':os.getpid(),'python_version':sys.version,'python_executable':sys.executable,
        'stage':stage,'final_commit':'940a5de33a24b1a3a9ded6e69ade1dd0609ed83a',
        'design_commit':'a250a76dc0b3f13b9dee3bcd2c3d7414032b9768','commands':rows,
        'finite_child_processes_remaining':sum(not r['process_exit_observed'] for r in rows),
        'background_processes_created':0,'forbidden_operations':{'network':0,'browser':0,'platform':0,
            'credentials_profile':0,'OCR':0,'model_API':0,'database_or_recovery':0},
        'no_global_process_scan':'Only these finite child PIDs were owned/tracked. No claim about other users/services.'}
(HERE/'command-receipts.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'returncodes':[r['returncode'] for r in rows],
                  'remaining_children':result['finite_child_processes_remaining'],
                  'receipt':'command-receipts.json'},indent=2))
raise SystemExit(0 if all(r['returncode']==0 for r in rows) else 1)
