"""New path-only controller; all three original check scripts remain unchanged."""
import concurrent.futures,hashlib,io,json,os,shutil,subprocess,sys,time
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];S=OUT/'inputs/replay-scripts';F=OUT/'inputs/raw product with spaces'
TEMP=Path('D:/1800/.local/stages/A04-review/coordinate-R3-raw-bytes');TEMP.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(S));from process_identity import own,child
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(b):return hashlib.sha256(b).hexdigest()
inventory=read(OUT/'runtime-inputs-before.json');assert all(sha((F/e['path']).read_bytes())==e['git_sha256'] for e in inventory['files'])
for script in read(OUT/'replayed-scripts.json')['scripts']:
    assert sha((OUT/script['copy']).read_bytes())==script['sha256'],script
bootstrap=F/'src/sitecustomize.py';assert not bootstrap.exists();bootstrap.write_bytes((S/'offline_guard.py').read_bytes())
save(OUT/'runtime-harness-bootstrap.json',{'path':str(bootstrap),'sha256':sha(bootstrap.read_bytes()),'source':'unchanged prior R3 reviewer guard',
 'not_target_product_file':True,'frozen_212_product_files_modified':False})
ENV=dict(os.environ,PYTHONPATH=str(F/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',
 TEMP=str(TEMP),TMP=str(TEMP),A04_R3_GUARD_LOG_DIR=str(OUT/'guard-records'))
JOBS=OUT/'jobs';JOBS.mkdir(exist_ok=True)
def call(name,args):
    folder=JOBS/name;folder.mkdir(parents=True,exist_ok=False);start=time.perf_counter()
    process=subprocess.Popen(args,cwd=str(TEMP),env=ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE);identity=child(process);timeout=False
    try:stdout,stderr=process.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        timeout=True;process.kill();stdout,stderr=process.communicate(timeout=10)
    (folder/'stdout.txt').write_bytes(stdout);(folder/'stderr.txt').write_bytes(stderr)
    r={'name':name,'args':args,'cwd':str(TEMP),'identity':identity,'returncode':process.returncode,'reaped':process.poll() is not None,
      'timed_out':timeout,'elapsed_seconds':time.perf_counter()-start,'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),
      'stdout':str((folder/'stdout.txt').relative_to(OUT)),'stderr':str((folder/'stderr.txt').relative_to(OUT)),
      'tail':(stdout+stderr).decode('utf-8','replace').splitlines()[-5:]}
    save(folder/'command-result.json',r);print(json.dumps(r),flush=True);return r
commands=[('exact',[sys.executable,'-B',str(S/'exact/repro_incomplete_rows.py'),'--root',str(F),'--output',str(OUT/'exact-replay')]),
 ('regression',[sys.executable,'-B',str(S/'regression_worker.py'),'--root',str(F),'--result',str(OUT/'regression-result.json')]),
 ('independent',[sys.executable,'-B',str(S/'independent_checks.py'),'--root',str(F),'--output',str(OUT/'independent-cases')])]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(lambda job:call(*job),commands))
save(OUT/'main-check-processes.json',{'runner_identity':own(),'jobs':results,'all_reaped':all(r['reaped'] for r in results)})
assert all(r['returncode']==0 and not r['timed_out'] for r in results),'Stop after observed check discrepancy; keep raw outputs'
# One required resource-binding observation using unchanged baseline PGM bytes.
fixture=F/'tests/fixtures/a04/source';capture=read(fixture/'capture.json');package=OUT/'raw-pgm-package'
pgm_cli=call('raw-pgm-cli',[sys.executable,'-B','-m','annotation.source.usense','offline','--input',str(fixture),'--output',str(package),'--as-of',capture['observed_at']])
assert pgm_cli['returncode']==0 and not pgm_cli['timed_out']
relocated=OUT/'raw PGM package relocated with spaces';shutil.copytree(package,relocated)
pgm_consumer=call('raw-pgm-consumer',[sys.executable,'-B',str(S/'independent_checks.py'),'--root',str(F),'--consume',str(relocated)])
assert pgm_consumer['returncode']==0 and not pgm_consumer['timed_out']
save(OUT/'pgm-check-processes.json',{'runner_identity':own(),'jobs':[pgm_cli,pgm_consumer],'all_reaped':True,
 'purpose':'Task-required raw PGM identity and relocated public consumption; no expanded old matrix'})
post=[]
for e in inventory['files']:
    data=(F/e['path']).read_bytes();assert sha(data)==e['git_sha256'] and len(data)==e['git_bytes'],e['path']
    post.append({'path':e['path'],'git_blob_oid':e['git_blob_oid'],'git_sha256':e['git_sha256'],
      'runtime_sha256':sha(data),'runtime_bytes':len(data),'exact_runtime_match':True})
save(OUT/'runtime-inputs-after.json',{'target_commit':inventory['target_commit'],'all_exact':True,'files':post,'products_changed':False})
print(json.dumps({'exact':'PASS','regression':'PASS','independent':'PASS','raw_PGM_public_and_relocated':'PASS','cat_file_inputs_unchanged_after':len(post)}))
