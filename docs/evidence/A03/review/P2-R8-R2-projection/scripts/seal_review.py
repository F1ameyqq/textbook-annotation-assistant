# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys
from datetime import datetime,timezone
from archive_common import ROOT,OUT,REPORT,load,sha,write,links,own_processes
manifest_path=OUT/'sha256-manifest.json';assert not manifest_path.exists()
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
argv=[sys.executable,'-X','utf8','-B',str(OUT/'scripts/run_recorded.py'),'final-verification-01','30',str(OUT/'scripts/final_checks.py')]
with (OUT/'seal-recorder.stdout.log').open('xb') as stdout,(OUT/'seal-recorder.stderr.log').open('xb') as stderr:
    code=subprocess.run(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=40).returncode
assert code==0,'final byte check failed; inspect preserved records before follow-up'
parents=own_processes();assert len(parents)==7;nested=load(OUT/'independent-nested-release.json')
write(OUT/'process-release.json',{'status':'OWNED_REVIEW_CHECKS_AND_N1_CHILDREN_WAITED_AND_EXITED','parents':parents,'parent_count':len(parents),
 'N1_nested_children':nested['records'],'nested_count':nested['count'],'functional_N1_rounds':1,'other_candidate_test_rounds':0,
 'basis':'own Popen wait and recorded nested communicate/wait completion; no system/profile scan','background_jobs':0})
write(OUT/'final-verification.json',{'status':'N1_LIMITED_ACCEPTED_OVERALL_A03_REWORK','created_at':datetime.now(timezone.utc).isoformat(),
 'target':'58d8a64734271d15654bb00b03d760f0f3eccd10','final_check_exit_code':0,'final_checks_sha256':sha(OUT/'final-checks.json'),
 'report_sha256':sha(REPORT),'process_release_sha256':sha(OUT/'process-release.json'),'inputs':407,'historical_files_preserved':4645,
 'independent_N1_rounds':1,'independent_run_id':load(OUT/'independent-run.json')['run_id'],'independent_effect_count':1,
 'N2_N7_minimal_or_compatibility_reruns':0,'author_registered_processes_reconciled':26,'author_bootstrap_PID_raw_stream_limit_preserved':True,
 'owned_review_checks':len(parents),'owned_N1_nested_children':4,'manifest_excludes_only_itself':True,
 'post_write_body_and_inventory_recheck':'seal_review.py asserts before successful exit','R7_ACCEPTED_preserved':True,
 'INTEGRATED_state_written':False,'I01_released':False,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
paths=sorted([p for p in OUT.rglob('*') if p.is_file()]+[REPORT]);assert len(paths)==len(set(paths)) and manifest_path not in paths
write(manifest_path,{'status':'R8_R2_REVIEW_FROZEN','root':str(ROOT),'scope':'projection and fixed synthetic N1 limited acceptance; N2 blocked; overall REWORK',
 'excluded_only':manifest_path.relative_to(ROOT).as_posix(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]})
manifest=load(manifest_path);actual={p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and p!=manifest_path};actual.add(REPORT.relative_to(ROOT).as_posix())
assert actual=={r['path'] for r in manifest['files']}
for row in manifest['files']:
    p=ROOT/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
assert all(r['exists'] for r in links())
print(json.dumps({'status':'SEALED_AND_INDEPENDENTLY_REHASHED','manifest_files':len(manifest['files']),
 'report_sha256':sha(REPORT),'manifest_sha256':sha(manifest_path),'own_parent_checks':len(parents),'own_N1_nested_children':4,
 'N1_independent_rounds':1,'overall':'REWORK','I01_released':False}))
