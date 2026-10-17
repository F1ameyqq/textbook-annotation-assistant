import hashlib,json,os,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
root=Path('D:/1800');out=Path(__file__).resolve().parent
def git(*args):return subprocess.check_output(['git',*args],cwd=root,timeout=30)
head=git('rev-parse','HEAD').decode().strip();index=json.loads((out/'merge-index-check.json').read_bytes())
parents=git('show','-s','--format=%P',head).decode().strip().split()
assert parents==[index['parent'],index['final_commit']]
assert git('rev-parse',head+'^{tree}').decode().strip()==index['merged_index_tree']
for row in index['files']:assert hashlib.sha256((root/row['path']).read_bytes()).hexdigest()==row['disk_sha256']
probe=root/'docs/evidence/A02/coordinator/portability-R2-acceptance/probe.py'
argv=[sys.executable,'-B',str(probe),str(root),'suite',str(root),head]
env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
for key in list(env):
 if key.startswith('GIT_'):env.pop(key)
r=subprocess.run(argv,cwd=root,env=env,capture_output=True,timeout=120)
(out/'a02-stdout.txt').write_bytes(r.stdout);(out/'a02-stderr.txt').write_bytes(r.stderr)
events=[json.loads(line) for line in r.stdout.decode('utf-8').splitlines() if line.startswith('{')]
tests=next((x for x in events if x.get('event')=='test-result'),None)
result={'at':datetime.now(timezone.utc).isoformat(),'merge_commit':head,'parents':parents,'tree':index['merged_index_tree'],'argv':argv,'cwd':str(root),'exit_code':r.returncode,'tests':tests,'probe_sha256':hashlib.sha256(probe.read_bytes()).hexdigest(),'stdout':'a02-stdout.txt','stderr':'a02-stderr.txt','own_synchronous_children_returned':True,'platform_model_calls':0,'remote_push':False,'scope':'62 affected A02 tests on actual integrated checkout; no A01 combined entry or recovery acceptance.'}
with (out/'checks.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
assert r.returncode==0 and tests and tests['run']==62 and tests['failures']==tests['errors']==tests['skipped']==0,result
for row in index['files']:assert hashlib.sha256((root/row['path']).read_bytes()).hexdigest()==row['disk_sha256']
assert not git('diff','--name-only').strip()
print(json.dumps({'merge_commit':head,'exit_code':r.returncode,'tests':tests['run'],'skip':tests['skipped']}))
