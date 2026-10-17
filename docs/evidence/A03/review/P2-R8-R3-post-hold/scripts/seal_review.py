# -*- coding: utf-8 -*-
"""Finalize already produced evidence after recorded byte-only reconciliation."""
import json
import os
import subprocess
import sys
from datetime import datetime,timezone
from archive_common import ROOT,OUT,REPORT,PHASES,FIELD_RESET,FAILURES,load,sha,write,links,own_processes
manifest_path=OUT/'sha256-manifest.json';assert not manifest_path.exists()
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
argv=[sys.executable,'-X','utf8','-B',str(OUT/'scripts/run_recorded.py'),'final-verification-01','45',str(OUT/'scripts/final_checks.py')]
with (OUT/'seal-recorder.stdout.log').open('xb') as stdout,(OUT/'seal-recorder.stderr.log').open('xb') as stderr:
    code=subprocess.run(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=55).returncode
assert code==0,'final byte check failed; inspect preserved records before any follow-up'
parents=own_processes();assert len(parents)==19;nested=load(OUT/'independent-nested-release.json')
write(OUT/'process-release.json',{'status':'OWNED_REVIEW_CHECKS_AND_BOUNDED_CHILDREN_WAITED_AND_EXITED','parents':parents,'parent_count':19,
 'nested_children':nested['records'],'nested_count':10,'independent_product_groups_once':list(PHASES),
 'retained_reviewer_metadata_failures':sorted(FAILURES),'product_group_failures_or_reruns':0,'N6_N7_variant_compatibility_runs':0,
 'query_preparation_failure_limit':'separate transcribed ParserError has no PID/raw split streams; not represented as registered process proof',
 'basis':'own Popen wait and frozen nested communicate/wait completion; no system/profile scan','background_jobs':0})
write(OUT/'final-verification.json',{'status':'POST_HOLD_LOCAL_N1_N5_LIMITED_ACCEPTED_OVERALL_A03_REWORK','created_at':datetime.now(timezone.utc).isoformat(),
 'target':'d9ed692db9ab8e9277f8ffd09e040451e8b8f65f','final_check_exit_code':0,'final_checks_sha256':sha(OUT/'final-checks.json'),
 'report_sha256':sha(REPORT),'process_release_sha256':sha(OUT/'process-release.json'),'inputs':678,'supplemental_authority_inputs':1,
 'historical_files_preserved':5229,'independent_product_groups_once':list(PHASES),'independent_run_id':load(OUT/'independent-run.json')['run_id'],
 'independent_effect_count':1,'POST_HOLD_admissions':2,'isolated_seed_files_unchanged':121,'independent_generated_files':281,
 'N6':'NOT_RUN','N7':'ORIGINAL_FAILED_READONLY_CLASSIFIED','incomplete_initialization':'NOT_REACHED','N7_or_variant_replays':0,
 'author_registered_processes_reconciled':34,'owned_review_checks':19,'owned_nested_children':10,'retained_reviewer_metadata_failures':3,
 'readonly_query_PID_raw_stream_limit_preserved':True,'manifest_excludes_only_itself':True,
 'post_write_body_and_inventory_recheck':'seal_review.py asserts all entries and report links before successful exit',
 'R7_R8_R2_bounded_acceptance_preserved':True,'INTEGRATED_state_written':False,'I01_released':False,'field_reset':FIELD_RESET})
paths=sorted([p for p in OUT.rglob('*') if p.is_file()]+[REPORT]);assert len(paths)==len(set(paths)) and manifest_path not in paths
write(manifest_path,{'status':'R8_R3_REVIEW_FROZEN','root':str(ROOT),
 'scope':'POST_HOLD and fixed local/N1-N5 limited acceptance; original N7 FAILED; overall A03 REWORK; I01 not released',
 'excluded_only':manifest_path.relative_to(ROOT).as_posix(),
 'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]})
manifest=load(manifest_path)
actual={p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and p!=manifest_path};actual.add(REPORT.relative_to(ROOT).as_posix())
assert actual=={r['path'] for r in manifest['files']}
for row in manifest['files']:
    p=ROOT/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
assert all(r['exists'] for r in links())
print(json.dumps({'status':'SEALED_AND_BODY_INVENTORY_REHASHED','manifest_files':len(manifest['files']),
 'report_sha256':sha(REPORT),'manifest_sha256':sha(manifest_path),'own_registered_checks':19,'own_nested_children':10,
 'independent_product_groups_once':list(PHASES),'overall':'REWORK','I01_released':False}))
