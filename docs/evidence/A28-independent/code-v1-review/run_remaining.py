import hashlib, json, os, subprocess
from pathlib import Path
from datetime import datetime, timezone
P=Path('D:/1800/.local/stages/a28-independent-20261023/code-v1-review')
O=Path('D:/1800/docs/evidence/A28-independent/code-v1-review')
PY=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/runtime-py312/venv/Scripts/python.exe')
assert hashlib.sha256(PY.read_bytes()).hexdigest()=='d59c9a894b319828d023f3aa83d9a3488d2339f9e27e60e49b02abb0d53cf538'
code='''import sys,unittest
def audit(event,args):
 if event=='socket.connect':
  f=sys._getframe(1)
  if f.f_code.co_name=='_fallback_socketpair' and f.f_code.co_filename.replace(chr(92),'/').endswith('/Lib/socket.py') and args[1][0]=='127.0.0.1': return
  raise RuntimeError('INDEPENDENT_OFFLINE_DENIAL:'+event)
 if event in ('socket.getaddrinfo','subprocess.Popen','os.system'): raise RuntimeError('INDEPENDENT_OFFLINE_DENIAL:'+event)
 if event=='open' and isinstance(args[0],str) and ('browser-profiles' in args[0].lower() or 'worktrees/b-latest' in args[0].replace(chr(92),'/').lower()): raise RuntimeError('INDEPENDENT_ACTIVE_RESOURCE_READ_DENIED')
sys.addaudithook(audit)
sys.path.insert(0,'src');sys.path.insert(0,'tests')
names=['test_a28_lesson_batch.SendTests','test_a28_lesson_batch.WriterEntrypointTests','test_a28_lesson_batch.WriterReleaseTests']
s=unittest.defaultTestLoader.loadTestsFromNames(names)
r=unittest.TextTestRunner(verbosity=2,failfast=True).run(s)
sys.exit(not r.wasSuccessful())
'''
out=P/'author-new-checks-remaining';out.mkdir()
cmd=[str(PY),'-I','-B','-c',code];start=datetime.now(timezone.utc).isoformat()
r=subprocess.run(cmd,cwd=P/'workspace',capture_output=True,timeout=60,env=dict(os.environ,PYTHONUTF8='1'))
for name,data in [('stdout.txt',r.stdout),('stderr.txt',r.stderr)]:
 with (out/name).open('xb') as f:f.write(data)
record={'schema':'A28IndependentRemainingNewChecks/v1','argv':cmd,'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'exit_code':r.returncode,'stdout':str(out/'stdout.txt'),'stderr':str(out/'stderr.txt'),'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest(),'prior_helper_error_preserved':True,'previous_35_passes_rerun':False,'scope':'Only remaining 5 new checks; stdlib loopback socketpair is permitted for asyncio IPC, business network remains denied.'}
with (O/'remaining-suite-process.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(r.stderr.decode('utf-8')[-1800:]);print(json.dumps({'exit_code':r.returncode}))
