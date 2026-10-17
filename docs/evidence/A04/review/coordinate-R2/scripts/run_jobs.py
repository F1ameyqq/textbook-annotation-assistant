"""Bounded local Python children, stdout/stderr and reap evidence per job."""
import argparse,concurrent.futures,hashlib,json,os,subprocess,sys,time
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];STAGE=Path('D:/1800/.local/stages/A04-review/coordinate-R2')
FROZEN=STAGE/'frozen source with spaces';SCRIPTS=OUT/'scripts'
p=argparse.ArgumentParser();p.add_argument('--group',choices=['regression','guard-correction','guard-correction-remaining','independent','pixel-diagnostics'],required=True);a=p.parse_args()
bootstrap=FROZEN/'src/sitecustomize.py';guard=(SCRIPTS/'offline_guard.py').read_bytes()
if bootstrap.exists() and bootstrap.read_bytes()!=guard:
    assert bootstrap.read_bytes()==(OUT/'harness-notes/offline-guard-before-windows-fix.py').read_bytes(),'Unrecognized harness bootstrap'
bootstrap.write_bytes(guard)
env=dict(os.environ,PYTHONPATH=str(FROZEN/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',
 TEMP=str(STAGE),TMP=str(STAGE),A04_R2_GUARD_LOG_DIR=str(OUT/'guard-records'))
record_dir=OUT/a.group;record_dir.mkdir(parents=True,exist_ok=True)
if a.group=='regression':
    jobs=[(name,[sys.executable,'-B',str(SCRIPTS/'regression_worker.py'),'--root',str(FROZEN),
       '--pattern',pattern,'--result',str(record_dir/(name+'-unittest.json'))])
       for name,pattern in [('a04','test_a04_*.py'),('contracts','test_contracts*.py')]]
elif a.group=='guard-correction':
    names=['test_a04_cli.OfflineEntryTests.test_public_module_offline_command_and_relocation_with_spaces',
     'test_a04_decode_r2.FullOriginalDecodeTests.test_original_24_byte_png_public_module_rejects_before_output',
     'test_contracts.ContractTests.test_copied_sample_cli_and_public_consumer_work_from_another_cwd',
     'test_contracts_platform_refs.PlatformReferenceTests.test_f1_and_f2_default_loader_and_cli_reject_resealed_complete_inputs']
    jobs=[('affected-four',[sys.executable,'-B',str(SCRIPTS/'regression_worker.py'),'--root',str(FROZEN),
       '--result',str(record_dir/'affected-four-unittest.json'),'--tests',*names])]
elif a.group=='guard-correction-remaining':
    names=['test_contracts.ContractTests.test_cli_rejects_invalid_exchange_with_nonzero_exit_and_location',
      'test_contracts.ContractTests.test_cli_schema_uses_the_public_schema_authority',
      'test_contracts.ContractTests.test_relative_symlink_may_not_escape_the_sample_root']
    jobs=[('remaining-three',[sys.executable,'-B',str(SCRIPTS/'regression_worker.py'),'--root',str(FROZEN),
      '--result',str(record_dir/'remaining-three-unittest.json'),'--tests',*names])]
elif a.group=='pixel-diagnostics':jobs=[('pixel-diagnostics',[sys.executable,'-B',str(SCRIPTS/'strict_pixel_diagnostics.py'),'--root',str(FROZEN),'--output',str(OUT/'pixel-diagnostics-cases')])]
else:jobs=[('independent',[sys.executable,'-B',str(SCRIPTS/'independent_checks.py'),'--root',str(FROZEN),'--output',str(OUT/'independent-cases')])]
def run(job):
    name,args=job;start=time.time();process=subprocess.Popen(args,cwd=str(STAGE),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    timed_out=False
    try:stdout,stderr=process.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        timed_out=True;process.kill();stdout,stderr=process.communicate(timeout=10)
    (record_dir/(name+'-stdout.txt')).write_bytes(stdout);(record_dir/(name+'-stderr.txt')).write_bytes(stderr)
    result={'name':name,'args':args,'cwd':str(STAGE),'pid':process.pid,'returncode':process.returncode,
      'wait_complete':process.poll() is not None,'timed_out':timed_out,'elapsed_seconds':time.time()-start,
      'stdout':str((record_dir/(name+'-stdout.txt')).relative_to(OUT)),
      'stderr':str((record_dir/(name+'-stderr.txt')).relative_to(OUT)),
      'stdout_sha256':hashlib.sha256(stdout).hexdigest(),'stderr_sha256':hashlib.sha256(stderr).hexdigest(),
      'output_tail':(stdout+stderr).decode('utf-8','replace').splitlines()[-6:]}
    print(json.dumps(result,ensure_ascii=False),flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,jobs))
summary={'group':a.group,'runner_pid':os.getpid(),'children':results,'all_reaped':all(r['wait_complete'] for r in results),
 'harness_only_bootstrap':str(bootstrap),'bootstrap_sha256':hashlib.sha256(guard).hexdigest(),
 'frozen_product_files_modified':False,'network_or_browser_authorized':False}
(record_dir/'process-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if all(r['returncode']==0 and not r['timed_out'] for r in results) else 1)
