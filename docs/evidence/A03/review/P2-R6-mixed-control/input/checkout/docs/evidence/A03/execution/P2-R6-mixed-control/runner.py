"""One preregistered owned synchronous child; only R6 output paths."""
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent;EX=ROOT/'examples/a03/P2-R6-mixed-control'
label,mode=sys.argv[1:];assert label.replace('-','').isalnum()
scripts={n:OUT/(n+'.py')for n in('freeze','prepare','precheck','archive','driver_syntax')};scripts['entry']=EX/'entry.py';assert mode in scripts
run=OUT/'runs'/label;run.mkdir(parents=True,exist_ok=False)
def sha(raw):return hashlib.sha256(raw).hexdigest()
args=[sys.executable,'-X','utf8','-B',str(scripts[mode])];inputs={}
for p in(OUT/'raw-input-pins.json',EX/'case.json',OUT/'precheck.json'):
    if p.exists():inputs[p.relative_to(ROOT).as_posix()]=sha(p.read_bytes())
record={'argv':args,'cwd':str(ROOT),'registered_at':datetime.now(timezone.utc).isoformat(),'timeout_seconds':60,'script_sha256':sha(scripts[mode].read_bytes()),'input_sha256':inputs,'mode':mode,'scope':'R6_SINGLE_INPUT_CORRECTION_ONE_UNCHANGED_R5_ENTRY'}
(run/'registration.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n');(run/'registered-script.py').write_bytes(scripts[mode].read_bytes())
for p in sorted(EX.glob('*.py')):
    if p!=scripts[mode]:(run/('source-'+p.name)).write_bytes(p.read_bytes())
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1';env['A03_R6_RUN_ID']=label
child=None;code=1;tick=time.monotonic()
with(run/'stdout.txt').open('xb')as stdout,(run/'stderr.txt').open('xb')as stderr:
    try:
        child=subprocess.Popen(args,cwd=ROOT,env=env,stdout=stdout,stderr=stderr);record['owned_pid']=child.pid
        (run/'started.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n');code=child.wait(timeout=60)
    except BaseException as error:
        record['exception']=repr(error);record['timed_out']=isinstance(error,subprocess.TimeoutExpired);stderr.write((repr(error)+'\n').encode());stderr.flush()
        if child is not None and child.poll()is None:child.kill();child.wait(timeout=5)
    finally:
        record.update(exit_code=code,alive=bool(child is not None and child.poll()is None),timed_out=record.get('timed_out',False),elapsed_seconds=time.monotonic()-tick,completed_at=datetime.now(timezone.utc).isoformat(),native_sessions=0,background_tasks=0)
        (run/'exit.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n')
if mode=='archive'and code==0:
    rows=[]
    for p in sorted((OUT/'runs').iterdir()):
        v=json.loads((p/'exit.json').read_bytes());assert not v['alive'];rows.append({'run':p.name,'pid':v['owned_pid'],'exit_code':v['exit_code'],'timed_out':v['timed_out'],'alive':False,'stdout_sha256':sha((p/'stdout.txt').read_bytes()),'stderr_sha256':sha((p/'stderr.txt').read_bytes())})
    with(OUT/'process-release.json').open('xb')as f:f.write(json.dumps({'status':'OWNED_SYNCHRONOUS_CHILDREN_EXITED','runs':rows,'native_sessions':0,'background_tasks':0},indent=2).encode()+b'\n')
    manifest=OUT/'sha256-manifest.json';paths=[ROOT/'docs/tasks/A03-P2-R6-mixed-control-delivery.md']+[p for root in(EX,OUT)for p in root.rglob('*')if p.is_file()and p!=manifest]
    items=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}for p in sorted(paths)]
    with manifest.open('xb')as f:f.write(json.dumps({'status':'REVIEW','base':'323013c4f0dbae75368e56db60147a8057368d1f','workflow':'77d3e123ab7247eae6f81f7acd669e3a69c934a0','excluded_only':[manifest.relative_to(ROOT).as_posix()],'files':items},ensure_ascii=False,indent=2).encode('utf8')+b'\n')
    record.update(manifest_entries=len(items),manifest_sha256=sha(manifest.read_bytes()))
print(json.dumps(record));sys.exit(code)
