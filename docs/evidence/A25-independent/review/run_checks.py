"""Run the bounded frozen A25 tests, retaining each original process stream."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone

PUB=Path(__file__).resolve().parent
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/review-initial-20261023')
SNAP=STAGE/'snapshot';RUNS=STAGE/'runs';GUARD=STAGE/'guard'
GUARD_CODE='''import os,sys
def guard(event,args):
 if event in ('socket.connect','socket.getaddrinfo','socket.bind'):raise RuntimeError('INDEPENDENT_OFFLINE_NETWORK_DENIED')
 if event=='subprocess.Popen':
  exe,args2=args[0],args[1]
  if os.path.basename(str(exe)).lower() not in ('python.exe','python','python3'):raise RuntimeError('INDEPENDENT_BROWSER_OR_NONPYTHON_PROCESS_DENIED')
  if any(str(x) in ('capture','login','--writer','writer','--insert-writer','--finalize-writer') for x in args2):raise RuntimeError('INDEPENDENT_LIVE_COMMAND_DENIED')
sys.addaudithook(guard)
'''
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):
 with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def main():
 RUNS.mkdir(exist_ok=False);GUARD.mkdir(exist_ok=False);(GUARD/'sitecustomize.py').write_text(GUARD_CODE,encoding='utf-8')
 env=os.environ.copy();env['PYTHONPATH']=str(GUARD);env['PYTHONDONTWRITEBYTECODE']='1';env['A25_REVIEW_SNAPSHOT']=str(SNAP);env['A25_REVIEW_RUNS']=str(RUNS)
 cmds=[('author-new-file-final',[sys.executable,'-B',str(SNAP/'tests/test_a25_batch.py'),'-f']),('independent-controls',[sys.executable,'-B',str(PUB/'controls.py')])];records=[]
 for name,argv in cmds:
  start=datetime.now(timezone.utc).isoformat();p=subprocess.run(argv,cwd=str(RUNS),env=env,capture_output=True,timeout=45)
  streams={}
  for label,b in [('stdout',p.stdout),('stderr',p.stderr)]:
   path=RUNS/(name+'.'+label);path.write_bytes(b);streams[label]={'path':str(path),'bytes':len(b),'sha256':sha(b)}
  rec={'label':name,'argv':argv,'cwd':str(RUNS),'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'exit_code':p.returncode,**streams};records.append(rec);save(RUNS/(name+'.process.json'),rec)
  print(json.dumps({'label':name,'exit_code':p.returncode,'output_tail':p.stderr.decode('utf-8',errors='replace')[-1400:]}),flush=True)
  if p.returncode:break
 save(PUB/'test-commands.json',{'commands':records,'successors_not_run':[name for name,_ in cmds[len(records):]],'network_and_live_command_guard':str(GUARD/'sitecustomize.py'),'guard_sha256':sha((GUARD/'sitecustomize.py').read_bytes()),'product_scope':'final new A25 file only; no old194, first-lesson, OCR, historical suites'})
if __name__=='__main__':main()
