# -*- coding: utf-8 -*-
"""Record a final byte-only check, seal after its wait, then rehash the archive."""
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
assert code==0,'inspect preserved final byte check logs before follow-up'
checks=load(OUT/'final-checks.json');own=own_processes();assert len(own)==5
write(OUT/'process-release.json',{'status':'OWNED_READONLY_REVIEW_CHECKS_WAITED_AND_EXITED','runs':own,'count':len(own),
 'basis':'recorded child wait completion; no current OS/profile scan','candidate_processes_started':0,
 'native_API_calls_or_target_effects':0,'background_jobs':0})
write(OUT/'final-verification.json',{'status':'COVERAGE_GAP_CLOSED_R8_R1_OVERALL_REWORK',
 'created_at':datetime.now(timezone.utc).isoformat(),'target':'a0c40886f3076f84c46377e03fc2206d2fdc5585',
 'final_check_exit_code':0,'final_checks_sha256':sha(OUT/'final-checks.json'),'report_sha256':sha(REPORT),
 'process_release_sha256':sha(OUT/'process-release.json'),'inputs':339,'historical_files_preserved':4252,
 'author_processes_reconciled':23,'owned_review_checks':len(own),'candidate_imports_N1_N2_N7_minimal_native_API_or_compatibility_reruns':0,
 'manifest_excludes_only_itself':True,'post_write_body_and_inventory_recheck':'seal_review.py asserts before successful exit',
 'R7_ACCEPTED_preserved':True,'INTEGRATED_state_written':False,'I01_released':False,
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
paths=sorted([p for p in OUT.rglob('*') if p.is_file()]+[REPORT]);assert len(paths)==len(set(paths)) and manifest_path not in paths
write(manifest_path,{'status':'R8_R1_REVIEW_FROZEN','root':str(ROOT),'scope':'coverage gap closed; overall REWORK; frozen bytes/static/immutable DB only',
 'excluded_only':manifest_path.relative_to(ROOT).as_posix(),
 'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]})
manifest=load(manifest_path)
actual={p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and p!=manifest_path};actual.add(REPORT.relative_to(ROOT).as_posix())
assert actual=={r['path'] for r in manifest['files']}
for row in manifest['files']:
    p=ROOT/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
assert all(r['exists'] for r in links())
print(json.dumps({'status':'SEALED_AND_INDEPENDENTLY_REHASHED','manifest_files':len(manifest['files']),
 'report_sha256':sha(REPORT),'manifest_sha256':sha(manifest_path),'owned_review_checks':len(own),'candidate_runs':0,'I01_released':False}))
