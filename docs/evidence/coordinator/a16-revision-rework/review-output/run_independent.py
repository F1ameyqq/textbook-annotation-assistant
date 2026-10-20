"""Freeze independent inputs, syntax-check JS without executing it, then run controls once."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('D:/1800-worktrees/a16-r1-review')
OUT=ROOT/'docs/evidence/A16/independent-r1-review'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',GIT_NO_LAZY_FETCH='1')
members=[]
for name in ['independent_revision_controls.py','native-fetch-valid.js','reserved-getter-invalid.js']:
    raw=(OUT/name).read_bytes();members.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
with (OUT/'independent-input-freeze.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump({'task':'A16','candidate_manifest_sha256':'071340237c76a7159bd90485e17a774c2f870114baef0199172a2fc5f9547efc',
        'script_and_inputs_frozen_before_run':True,'members':members,'controls':13,
        'expected':'Valid bound source may register; invalid JS must remain UNKNOWN and request no sample APIs',
        'old_product_or_suite_replay':False},stream,indent=2);stream.write('\n')

commands=[('valid-js-syntax',[r'C:/Program Files/nodejs/node.exe','--check',str(OUT/'native-fetch-valid.js')],0),
    ('invalid-js-syntax',[r'C:/Program Files/nodejs/node.exe','--check',str(OUT/'reserved-getter-invalid.js')],1),
    ('independent-controls',[sys.executable,'-B',str(OUT/'independent_revision_controls.py')],None)]
records=[]
for name,cmd,expected in commands:
    start=time.monotonic()
    child=subprocess.Popen(cmd,cwd=str(ROOT),env=env,stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x08000000)
    stdout,stderr=child.communicate(timeout=40)
    for kind,data in [('stdout',stdout),('stderr',stderr)]:
        with (OUT/(name+'.'+kind+'.raw.txt')).open('xb') as stream:stream.write(data)
    record={'name':name,'argv':cmd,'pid':child.pid,'wait_completed':True,'exit_code':child.returncode,
        'expected_exit':expected,'duration_ms':round((time.monotonic()-start)*1000),
        'stderr_bytes':len(stderr),'stdout_sha256':hashlib.sha256(stdout).hexdigest(),
        'JS_code_executed':False,'OS_creation_identity':'NOT_OBSERVED_NO_CLAIM'}
    records.append(record);print(json.dumps(record))
    if expected is not None and child.returncode!=expected:break
    if expected is None and child.returncode:break
with (OUT/'independent-command-results.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump({'task':'A16','commands':records,'syntax_checks_only_no_JS_execution':True,
        'new_revision_only':True},stream,indent=2);stream.write('\n')
