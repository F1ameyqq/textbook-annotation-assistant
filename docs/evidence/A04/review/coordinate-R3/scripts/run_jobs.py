"""Run only bounded local Python jobs and retain creation-time/reap records."""
import argparse,concurrent.futures,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from process_identity import own,child
OUT=Path(__file__).resolve().parents[1];S=OUT/'scripts';STAGE=Path('D:/1800/.local/stages/A04-review/coordinate-R3');F=STAGE/'frozen source with spaces'
p=argparse.ArgumentParser();p.add_argument('--group',choices=['initial','independent'],required=True);a=p.parse_args()
bootstrap=F/'src/sitecustomize.py';data=(S/'offline_guard.py').read_bytes()
if bootstrap.exists():assert bootstrap.read_bytes()==data
else:bootstrap.write_bytes(data)
env=dict(os.environ,PYTHONPATH=str(F/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',
 TEMP=str(STAGE),TMP=str(STAGE),A04_R3_GUARD_LOG_DIR=str(OUT/'guard-records'))
group=OUT/a.group;group.mkdir(parents=True,exist_ok=True)
if a.group=='initial':jobs=[('exact-unchanged',[sys.executable,'-B',str(OUT/'inputs/unchanged-R2-repro/repro_incomplete_rows.py'),'--root',str(F),'--output',str(OUT/'exact-replay')]),
 ('regression',[sys.executable,'-B',str(S/'regression_worker.py'),'--root',str(F),'--result',str(group/'regression-result.json')])]
else:jobs=[('independent',[sys.executable,'-B',str(S/'independent_checks.py'),'--root',str(F),'--output',str(OUT/'independent-cases')])]
def run(job):
    name,args=job;start=time.time();process=subprocess.Popen(args,cwd=str(STAGE),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    ident=child(process);timed_out=False
    try:out,err=process.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        timed_out=True;process.kill();out,err=process.communicate(timeout=10)
    (group/(name+'-stdout.txt')).write_bytes(out);(group/(name+'-stderr.txt')).write_bytes(err)
    r={'name':name,'args':args,'cwd':str(STAGE),'identity':ident,'returncode':process.returncode,
      'reaped':process.poll() is not None,'timed_out':timed_out,'elapsed_seconds':time.time()-start,
      'stdout':str((group/(name+'-stdout.txt')).relative_to(OUT)),'stderr':str((group/(name+'-stderr.txt')).relative_to(OUT)),
      'stdout_sha256':hashlib.sha256(out).hexdigest(),'stderr_sha256':hashlib.sha256(err).hexdigest(),
      'tail':(out+err).decode('utf-8','replace').splitlines()[-5:]}
    print(json.dumps(r),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(run,jobs))
(group/'process-results.json').write_text(json.dumps({'runner_identity':own(),'jobs':rows,
 'bootstrap_sha256':hashlib.sha256(data).hexdigest(),'all_reaped':all(r['reaped'] for r in rows)},indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if all(r['returncode']==0 and not r['timed_out'] for r in rows) else 1)
