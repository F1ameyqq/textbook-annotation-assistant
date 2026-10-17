from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
EX=ROOT/'examples/a03/P2-R4-bridge-registration'
label,mode=sys.argv[1:];assert label.replace('-','').isalnum()
scripts={'freeze':OUT/'freeze.py','prepare':EX/'prepare.py','assess':EX/'assess.py','verify':OUT/'verify.py','seal':OUT/'prepare_seal.py'};assert mode in scripts
run=OUT/'runs'/label;run.mkdir(parents=True,exist_ok=False)
args=[sys.executable,'-X','utf8','-B',str(scripts[mode])]
record={'argv':args,'cwd':str(ROOT),'registered_at':datetime.now(timezone.utc).isoformat(),'timeout_seconds':60,'script_sha256':hashlib.sha256(scripts[mode].read_bytes()).hexdigest(),'scope':'R4_INTERFACE_STATIC_AND_EXACTLY_FOUR_PACKAGE_CONTROLS'}
(run/'registration.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n');(run/'registered-script.py').write_bytes(scripts[mode].read_bytes())
if mode=='prepare':
    for n in('fixed_entry.py','interfaces.py'):(run/n).write_bytes((EX/n).read_bytes())
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1';env['A03_R4_RUN_ID']=label
child=None;code=1;tick=time.monotonic()
with (run/'stdout.txt').open('xb')as stdout,(run/'stderr.txt').open('xb')as stderr:
    try:
        child=subprocess.Popen(args,cwd=ROOT,env=env,stdout=stdout,stderr=stderr);record['owned_pid']=child.pid
        (run/'started.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n');code=child.wait(timeout=60)
    except BaseException as e:
        stderr.write((repr(e)+'\n').encode('utf8'));stderr.flush();record['exception']=repr(e)
        if child is not None and child.poll()is None:child.kill();child.wait(timeout=5)
    finally:
        record.update(exit_code=code,alive=bool(child is not None and child.poll()is None),elapsed_seconds=time.monotonic()-tick,completed_at=datetime.now(timezone.utc).isoformat(),native_sessions=0,background_tasks=0)
        (run/'exit.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n')
if mode=='seal'and code==0:
    rows=[]
    for p in sorted((OUT/'runs').iterdir()):
        v=json.loads((p/'exit.json').read_bytes());assert not v['alive']
        rows.append({'run':p.name,'pid':v['owned_pid'],'exit_code':v['exit_code'],'alive':False,'stdout_sha256':hashlib.sha256((p/'stdout.txt').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((p/'stderr.txt').read_bytes()).hexdigest()})
    with (OUT/'process-release.json').open('xb')as f:f.write(json.dumps({'status':'OWNED_STATIC_CHILDREN_EXITED','runs':rows,'native_sessions':0,'background_tasks':0},indent=2).encode()+b'\n')
    manifest=OUT/'sha256-manifest.json';paths=[ROOT/'docs/tasks/A03-P2-R4-bridge-registration-delivery.md']+[p for root in(OUT,EX)for p in root.rglob('*')if p.is_file()and p!=manifest]
    files=[]
    for p in sorted(paths):
        raw=p.read_bytes();files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    with manifest.open('xb')as f:f.write(json.dumps({'status':'REVIEW_PREPARATION_ONLY','base':'87606b73e0754fa670491d9fb958a416c26bfe88','workflow':'ef1d2f4a20971b416afae500889aa5c090dfe89b','excluded_only':[manifest.relative_to(ROOT).as_posix()],'files':files},ensure_ascii=False,indent=2).encode('utf8')+b'\n')
    record.update(manifest_entries=len(files),manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())
print(json.dumps(record));sys.exit(code)
