"""Preregister one owned bounded product/test/file command and retain failures."""
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent;EX=ROOT/'examples/a03/P2-R7-readonly-codec';PRODUCT=ROOT/'src/annotation/contracts/a03_bridge'
label,mode,*extra=sys.argv[1:];assert label.replace('-','').isalnum()
scripts={n:OUT/(n+'.py')for n in('freeze','prepare','static_audit','phase_audit','test_run','build_wheel','isolate','archive','seal_check')};assert mode in scripts
run=OUT/'runs'/label;run.mkdir(parents=True,exist_ok=False)
def sha(raw):return hashlib.sha256(raw).hexdigest()
inputs={}
for p in(OUT/'raw-input-pins.json',ROOT/'tests/fixtures/a03/P2-R7-readonly-codec/index.json',ROOT/'pyproject.toml'):
    if p.exists():inputs[p.relative_to(ROOT).as_posix()]=sha(p.read_bytes())
product=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}for p in sorted(PRODUCT.rglob('*'))if p.is_file()]
(run/'product-source-index.json').write_bytes(json.dumps(product,indent=2).encode()+b'\n')
args=[sys.executable,'-X','utf8','-B',str(scripts[mode]),*extra]
if mode=='test_run'and extra==['c01']:args=[sys.executable,'-B',str(scripts[mode]),*extra]
record={'argv':args,'cwd':str(ROOT),'registered_at':datetime.now(timezone.utc).isoformat(),'timeout_seconds':60,'script_sha256':sha(scripts[mode].read_bytes()),'inputs':inputs,'product_source_index_sha256':sha((run/'product-source-index.json').read_bytes()),'mode':mode,'scope':'R7_READONLY_PRODUCT_ONLY_NO_NATIVE'}
(run/'registration.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n');(run/'registered-script.py').write_bytes(scripts[mode].read_bytes())
for p in sorted(EX.glob('*.py')):(run/('helper-'+p.name)).write_bytes(p.read_bytes())
test=ROOT/'tests/test_a03_r7_readonly_codec.py'
if test.exists():(run/'test-source.py').write_bytes(test.read_bytes())
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1';env['A03_R7_RUN_ID']=label;env['R7_TEMP_ROOT']=str(OUT/'temporary');(OUT/'temporary').mkdir(exist_ok=True)
child=None;code=1;tick=time.monotonic()
with(run/'stdout.txt').open('xb')as stdout,(run/'stderr.txt').open('xb')as stderr:
    try:
        child=subprocess.Popen(args,cwd=ROOT,env=env,stdout=stdout,stderr=stderr);record['owned_pid']=child.pid
        (run/'started.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n');code=child.wait(timeout=60)
    except BaseException as error:
        record['exception']=repr(error);record['timed_out']=isinstance(error,subprocess.TimeoutExpired);stderr.write((repr(error)+'\n').encode());stderr.flush()
        if child is not None and child.poll()is None:child.kill();child.wait(timeout=5)
    finally:
        record.update(exit_code=code,alive=bool(child is not None and child.poll()is None),timed_out=record.get('timed_out',False),elapsed_seconds=time.monotonic()-tick,completed_at=datetime.now(timezone.utc).isoformat(),background_tasks=0,native_sessions=0)
        (run/'exit.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n')
if mode in('archive','seal_check')and code==0:
    rows=[]
    for p in sorted((OUT/'runs').iterdir()):
        v=json.loads((p/'exit.json').read_bytes());assert not v['alive'];rows.append({'run':p.name,'pid':v['owned_pid'],'exit_code':v['exit_code'],'timed_out':v['timed_out'],'alive':False,'stdout_sha256':sha((p/'stdout.txt').read_bytes()),'stderr_sha256':sha((p/'stderr.txt').read_bytes())})
    with(OUT/'process-release.json').open('xb')as f:f.write(json.dumps({'status':'OWNED_RECORDED_COMMANDS_EXITED','runs':rows,'nested_children':'separate child-process records where applicable','native_sessions':0,'background_tasks':0},indent=2).encode()+b'\n')
    manifest=OUT/'sha256-manifest.json';roots=[PRODUCT,ROOT/'tests/fixtures/a03/P2-R7-readonly-codec',EX,OUT]
    files=[ROOT/'tests/test_a03_r7_readonly_codec.py',ROOT/'docs/tasks/A03-P2-R7-readonly-codec-delivery.md',ROOT/'pyproject.toml']+[p for root in roots for p in root.rglob('*')if p.is_file()and p!=manifest]
    items=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}for p in sorted(files)]
    with manifest.open('xb')as f:f.write(json.dumps({'status':'REVIEW','base':'81d3ec7e42e0a1a76ad744bf59536fc5f68adee4','workflow':'5a69df310517f0ca22708262c737db9a5676be32','excluded_only':[manifest.relative_to(ROOT).as_posix()],'files':items},ensure_ascii=False,indent=2).encode('utf8')+b'\n')
    record.update(manifest_entries=len(items),manifest_sha256=sha(manifest.read_bytes()))
print(json.dumps(record));sys.exit(code)
