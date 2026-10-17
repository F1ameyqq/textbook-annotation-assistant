"""Durable capture of this bounded static repair's own synchronized children."""
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
EX=ROOT/'examples/a03/P2-R3-evidence-closure'
label,mode=sys.argv[1:]
scripts={'freeze':OUT/'freeze.py','controls':EX/'controls.py','replay-original':EX/'replay.py','verify':OUT/'verify.py','seal':OUT/'prepare_seal.py'}
assert mode in scripts and label.replace('-','').isalnum()
directory=OUT/'runs'/label;directory.mkdir(parents=True,exist_ok=False)
argv=[sys.executable,'-X','utf8','-B',str(scripts[mode])]
record={'argv':argv,'cwd':str(ROOT),'registered_at':datetime.now(timezone.utc).isoformat(),'script_sha256':hashlib.sha256(scripts[mode].read_bytes()).hexdigest(),'timeout_seconds':60,'scope':'NEW_STATIC_REPAIR_ONLY'}
(directory/'registration.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n')
(directory/'registered-script.py').write_bytes(scripts[mode].read_bytes())
if mode in('controls','replay-original'):(directory/'closure.py').write_bytes((EX/'closure.py').read_bytes())
child=None;code=1;tick=time.monotonic()
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
env['A03_R3_RUN_ID']=label
with (directory/'stdout.txt').open('xb')as stdout,(directory/'stderr.txt').open('xb')as stderr:
    try:
        child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr);record['owned_pid']=child.pid
        (directory/'started.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n')
        code=child.wait(timeout=60)
    except BaseException as error:
        stderr.write((repr(error)+'\n').encode('utf8'));stderr.flush();record['exception']=repr(error)
        if child is not None and child.poll()is None:child.kill();child.wait(timeout=5)
    finally:
        record.update(exit_code=code,alive=bool(child is not None and child.poll()is None),elapsed_seconds=time.monotonic()-tick,completed_at=datetime.now(timezone.utc).isoformat(),background_tasks=0,native_sessions=0)
        (directory/'exit.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n')
if mode=='seal'and code==0:
    release=[]
    for run in sorted((OUT/'runs').iterdir()):
        v=json.loads((run/'exit.json').read_bytes());assert not v['alive']
        release.append({'run':run.name,'pid':v['owned_pid'],'exit_code':v['exit_code'],'alive':False,'stdout_sha256':hashlib.sha256((run/'stdout.txt').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((run/'stderr.txt').read_bytes()).hexdigest()})
    with (OUT/'process-release.json').open('xb')as f:f.write(json.dumps({'status':'OWNED_STATIC_CHILDREN_EXITED','runs':release,'native_sessions':0,'background_tasks':0,'scope':'own synchronized children only'},indent=2).encode()+b'\n')
    manifest=OUT/'sha256-manifest.json';report=ROOT/'docs/tasks/A03-P2-R3-evidence-closure-delivery.md'
    paths=[report]+[p for root in(OUT,EX)for p in root.rglob('*')if p.is_file()and p!=manifest]
    entries=[]
    for p in sorted(paths):
        raw=p.read_bytes();entries.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    with manifest.open('xb')as f:f.write(json.dumps({'status':'REVIEW_STATIC_ONLY','base':'526d264284f36f856c306db88c1d7e71c04152e1','workflow':'c3b5f38c7e9a3a4a51ae8cbe16a3821ff2f36970','excluded_only':[manifest.relative_to(ROOT).as_posix()],'files':entries},ensure_ascii=False,indent=2).encode('utf8')+b'\n')
    record.update(manifest_entries=len(entries),manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())
print(json.dumps(record));sys.exit(code)
