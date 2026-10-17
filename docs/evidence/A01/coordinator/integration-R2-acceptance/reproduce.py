"""Bounded coordinator reproduction of the accepted fixed combination."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path('D:/1800')
out = Path(__file__).resolve().parent
tree = '0645ac862f79fb4e232e4cfbd5f6bb5055a68d62'
main = '2d1dc8b97713ee06ec5bf35febe0b894ece584b2'
delivery = '5f872150a237b195f73c78e02e13a91d2f4f46a7'
assert subprocess.check_output(['git','merge-tree','--write-tree',main,delivery],cwd=root,text=True).strip() == tree
stage = root / '.local/stages/A01-coordinator-integration-R2'
stage.mkdir(exist_ok=False)
raw = stage / 'raw source'
raw.mkdir()
selection = ['src/annotation','examples/a01','examples/a02/R1','tests/fixtures/a01/integration-R1','tests/fixtures/contracts/unknown','tests/test_a01_integration_r1.py','tests/test_a02_r1.py']
rows = subprocess.check_output(['git','ls-tree','-r','-z',tree,*selection],cwd=root).split(b'\0')
items = []
specs = []
for row in rows:
    if not row: continue
    meta,name = row.split(b'\t',1)
    mode,kind,oid = meta.split()
    assert mode in (b'100644',b'100755') and kind == b'blob'
    specs.append((name.decode('utf-8'),oid.decode('ascii')))
batch = subprocess.run(['git','cat-file','--batch'],cwd=root,input=('\n'.join(oid for _,oid in specs)+'\n').encode('ascii'),capture_output=True,check=True).stdout
pos = 0
for path,oid in specs:
    eol = batch.index(b'\n',pos)
    header = batch[pos:eol].split()
    assert header[0].decode() == oid and header[1] == b'blob'
    size = int(header[2]); data = batch[eol+1:eol+1+size]; pos=eol+size+2
    assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest() == oid
    dest = raw/path; dest.resolve().relative_to(raw.resolve())
    dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
    items.append({'path':path,'oid':oid,'bytes':size,'sha256':hashlib.sha256(data).hexdigest()})
assert pos == len(batch)
env = os.environ.copy()
for key in list(env):
    if key.startswith('GIT_'): env.pop(key)
env.update(PATH=r'C:\Windows\System32;C:\Windows',PYTHONPATH=str(raw/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
commands=[]
def run(name,args,cwd):
    argv=[sys.executable,'-B',*map(str,args)]
    proc=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=120)
    (out/(name+'-stdout.txt')).write_bytes(proc.stdout)
    (out/(name+'-stderr.txt')).write_bytes(proc.stderr)
    commands.append({'name':name,'argv':argv,'cwd':str(cwd),'PATH':env['PATH'],'PYTHONPATH':env['PYTHONPATH'],'exit_code':proc.returncode,'stdout':name+'-stdout.txt','stderr':name+'-stderr.txt'})
    assert proc.returncode==0,(name,proc.returncode)
    return proc
probe="import json,shutil,subprocess,annotation.source.static.importer as i,annotation.geometry as g; r={'which_git':shutil.which('git'),'importer':i.__file__,'geometry':g.__file__};\ntry: subprocess.run(['git','--version'],check=True,capture_output=True)\nexcept OSError as e: r.update(git_spawn=type(e).__name__,winerror=e.winerror)\nelse: raise AssertionError('Git unexpectedly available')\nassert r['which_git'] is None; print(json.dumps(r))"
run('environment', ['-c',probe],stage)
case=run('original-noGit',['-m','unittest','test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head','-v'],raw/'tests')
assert b'Ran 1 test' in case.stderr and b'OK' in case.stderr and b'skipped' not in case.stderr
guard=run('frozen-input-guards',['-m','unittest','test_a01_integration_r1','-v'],raw/'tests')
assert b'Ran 3 tests' in guard.stderr and b'OK' in guard.stderr
run('URL-cases',[raw/'examples/a01/R3/probe.py',stage/'URL-replay'],stage)
for book in ['46006966','46007447']:
    copied=stage/('moved book '+book)
    shutil.copytree(raw/'examples/a01/R3/bundles'/book,copied)
    run('consume-'+book,[raw/'examples/a01/consume.py',copied/'exchange.json','--book-id',book],stage)
for item in items: assert hashlib.sha256((raw/item['path']).read_bytes()).hexdigest()==item['sha256']
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'BOUNDED_REPRODUCTION_PASS','main_parent':main,'A01_delivery':delivery,'combination_tree':tree,'raw_files':items,'commands':commands,'raw_source_unchanged':True,'original_single_test':{'run':1,'skipped':0,'exit_code':0},'guard_tests':3,'scope':'Fixed combination raw noGit: original regression, preservation negative controls, five URL cases and two relocated complete image consumers. No full-suite rerun or platform action.','sessions_to_release':0,'synchronous_children_returned':True,'remote_push':False}
with (out/'checks.json').open('x',encoding='utf-8',newline='\n') as f: json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'result':result['result'],'files':len(items),'commands':len(commands)}))
