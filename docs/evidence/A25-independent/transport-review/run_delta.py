"""Bounded offline delta run. Asyncio's local control sockets remain possible."""
import hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
PUB=Path(__file__).resolve().parent;STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/transport-review-20261023')
CODE='''import socket,sys
def denied(*args,**kwargs):raise RuntimeError('INDEPENDENT_REAL_CONNECTION_DENIED')
socket.create_connection=denied
def guard(event,args):
 if event=='subprocess.Popen':raise RuntimeError('INDEPENDENT_CHILD_PROCESS_DENIED')
 if event=='socket.connect':
  address=args[1]
  if not(isinstance(address,tuple) and address[0]=='127.0.0.1' and address[1]>=49152):raise RuntimeError('INDEPENDENT_EXTERNAL_OR_PROXY_CONNECT_DENIED')
 if event=='socket.bind':
  address=args[1]
  if not(isinstance(address,tuple) and address[0]=='127.0.0.1' and address[1]==0):raise RuntimeError('INDEPENDENT_NONCONTROL_BIND_DENIED')
 if event=='socket.getaddrinfo' and args[0] not in ('127.0.0.1','localhost'):raise RuntimeError('INDEPENDENT_EXTERNAL_DNS_DENIED')
sys.addaudithook(guard)
'''
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):
 with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def main():
 runs=STAGE/'runs';runs.mkdir(exist_ok=False);guard=STAGE/'guard';guard.mkdir(exist_ok=False);(guard/'sitecustomize.py').write_text(CODE,encoding='utf-8');env=os.environ.copy();env['PYTHONPATH']=str(guard);env['PYTHONDONTWRITEBYTECODE']='1';env['A25_TRANSPORT_SNAPSHOT']=str(STAGE/'snapshot');records=[]
 for name in ['suite','controls']:
  argv=[sys.executable,'-B',str(PUB/(name+'.py'))];start=datetime.now(timezone.utc).isoformat();p=subprocess.run(argv,cwd=str(runs),env=env,capture_output=True,timeout=55);streams={}
  for label,raw in [('stdout',p.stdout),('stderr',p.stderr)]:
   path=runs/(name+'.'+label);path.write_bytes(raw);streams[label]={'path':str(path),'bytes':len(raw),'sha256':sha(raw)}
  record={'label':name,'argv':argv,'cwd':str(runs),'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'exit_code':p.returncode,**streams};records.append(record);save(runs/(name+'.process.json'),record);print(json.dumps({'label':name,'exit_code':p.returncode,'output':p.stderr.decode('utf-8',errors='replace')}),flush=True)
  if p.returncode:break
 save(PUB/'test-commands.json',{'records':records,'successors_not_run':['controls'] if len(records)==1 else [],'guard_sha256':sha((guard/'sitecustomize.py').read_bytes()),'guard_scope':'deny actual create_connection, external DNS, external/proxy sockets and subprocess; allow only Windows asyncio loopback control sockets','old16plus8':'NOT_RERUN','old194_first_lesson_OCR':'NOT_RERUN'})
if __name__=='__main__':main()
