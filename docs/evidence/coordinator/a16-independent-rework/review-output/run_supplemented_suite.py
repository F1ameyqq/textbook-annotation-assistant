"""Verify coordinator's one-file packaging supplement; run the newly authorized suite once."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REPO=Path('D:/1800')
OLD=Path('D:/1800-worktrees/a16-independent-fixed')
NEW=Path('D:/1800-worktrees/a16-independent-complete')
OUT=OLD/'docs/evidence/A16/independent-offline-review'
FINAL='4fe417d5246f20fbbbedc577495c7ca400d4ded8'
env=dict(os.environ,GIT_NO_LAZY_FETCH='1',PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
manifest=json.loads((OUT/'input-raw-manifest.json').read_bytes())
for item in manifest['members']:
    raw=(NEW/item['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==item['sha256']
    assert raw==(OLD/item['path']).read_bytes()
dependency='src/annotation/__init__.py'
raw=(NEW/dependency).read_bytes()
assert len(raw)==73 and hashlib.sha256(raw).hexdigest()=='a11279a7897a17523423f81c888a410edfb53c74d36435f7ab7c7cfacc67ca2d'
blob=subprocess.check_output(['git','-c','core.longpaths=true','show',FINAL+':'+dependency],cwd=str(REPO),env=env)
assert raw==blob
supplement=(REPO/'docs/evidence/coordinator/a16-author-delivery/isolation-package-supplement.json').read_bytes()
with (OUT/'isolation-package-supplement.raw.json').open('xb') as stream:stream.write(supplement)
with (OUT/'supplemented-input-preflight.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump({'task':'A16','original49_equal':True,'new_member':dependency,'new_member_bytes':73,
        'new_member_sha256':hashlib.sha256(raw).hexdigest(),'new_member_blob':'5773de17db987b9f7f94c58bfbcc490faf215979',
        'same_final':FINAL,'member_count':50,'new_product_candidate':False,
        'old_independent01_modified':False},stream,indent=2);stream.write('\n')

command=[sys.executable,'-B','tests/a16_current_readonly/run_offline.py','--output',
    'docs/evidence/A16/current-readonly/test-runs/independent-02']
started=time.monotonic()
child=subprocess.Popen(command,cwd=str(NEW),env=env,stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x08000000)
stdout,stderr=child.communicate(timeout=30)
for name,value in [('supplemented-suite.stdout.raw.txt',stdout),('supplemented-suite.stderr.raw.txt',stderr)]:
    with (OUT/name).open('xb') as stream:stream.write(value)
source=NEW/'docs/evidence/A16/current-readonly/test-runs/independent-02'
copied=[]
dest=OUT/'supplemented-suite-raw';dest.mkdir(exist_ok=False)
for name in ['result.json','unittest.txt','harness-traceback.txt']:
    if (source/name).exists():
        value=(source/name).read_bytes()
        with (dest/name).open('xb') as stream:stream.write(value)
        copied.append({'path':name,'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest(),
            'original':str(source/name)})
record={'task':'A16','command':command,'cwd':str(NEW),'pid':child.pid,'exit_code':child.returncode,
    'wait_completed':True,'duration_ms':round((time.monotonic()-started)*1000),
    'creation_identity':'NOT_OBSERVED_NO_OS_IDENTITY_CLAIM','copied_raw_outputs':copied,
    'initial_import_failure_preserved':True,'real_resource_use':'NO_REAL_RESOURCE_PATH_REQUESTED',
    'product_acceptance':'INDEPENDENT_COUNTEREXAMPLE_REMAINS_REWORK'}
with (OUT/'supplemented-suite-command-result.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps(record))
