"""Reproduce only I1-GIT-01 in the fixed raw integration copy."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / '.local/stages/A01-review-integration-R1/raw integrated no Git'
COMMIT = '3bda6c2307e93601a574c9979c35fd1b25da3f58'
bindings = {}
for name in ('examples/a02/R1/identity.py', 'tests/test_a02_r1.py'):
    raw = subprocess.check_output(['git','cat-file','blob',COMMIT + ':' + name],cwd=ROOT,timeout=10)
    assert raw == (SOURCE/name).read_bytes(), name
    bindings[name] = hashlib.sha256(raw).hexdigest()
assert not (SOURCE/'.git').exists()
argv = [sys.executable,'-B','-m','unittest','test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head','-v']
rows = []
for label, path in [('without-git', 'C:/Windows/System32;C:/Windows'), ('with-git', os.environ['PATH'])]:
    env = dict(os.environ, PATH=path, PYTHONPATH=str(SOURCE/'src'), PYTHONDONTWRITEBYTECODE='1')
    git_path = shutil.which('git', path=path)
    assert (git_path is None) == (label == 'without-git')
    run = subprocess.run(argv, cwd=SOURCE/'tests', env=env,capture_output=True,timeout=30)
    for stream in ('stdout','stderr'):
        (OUT/(label+'-'+stream+'.txt')).write_bytes(getattr(run,stream))
    rows.append({'label':label,'argv':argv,'cwd':str(SOURCE/'tests'),'git_executable':git_path,
        'exit_code':run.returncode,'stdout':label+'-stdout.txt','stderr':label+'-stderr.txt'})
assert [r['exit_code'] for r in rows] == [1,0]
assert b'FileNotFoundError' in (OUT/'without-git-stderr.txt').read_bytes()
result = {'result':'I1-GIT-01_REPRODUCED','integration_commit':COMMIT,'input_sha256':bindings,'commands':rows,
    'scope':'One existing identity test under two PATHs; no functional or platform acceptance',
    'production_files_changed':False,'platform_model_calls':0}
with (OUT/'coordinator-check.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'result':result['result'],'exit_codes':[r['exit_code'] for r in rows]}))
