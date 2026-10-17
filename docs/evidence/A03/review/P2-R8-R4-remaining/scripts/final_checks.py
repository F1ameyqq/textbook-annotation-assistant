# -*- coding: utf-8 -*-
"""Final byte-only reconciliation; no database reopening or product calls."""
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime
from archive_common import ROOT,OUT,REPORT,PHASES,FIELD_RESET,load,sha,write,links,preservation,own_processes
from evidence import WORK,EV,TARGET,BASE,WF,raw,text
index=load(OUT/'input-index.json')['exports'];assert len(index)==len({r['file'] for r in index})==409
for row in index:
    p=OUT/row['file'];b=p.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['raw_git_sha1']
seed=load(OUT/'isolated-source-index.json')['files'];output=load(OUT/'independent-output-index.json')['files']
assert len(seed)==76 and len(output)==116
for row in seed+output:
    p=OUT/row['file'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
assert {p.relative_to(OUT).as_posix() for p in WORK.rglob('*') if p.is_file()}=={r['file'] for r in seed+output}
assert {p.relative_to(OUT).as_posix() for p in (OUT/'input').rglob('*') if p.is_file()}=={r['file'] for r in index if r['file'].startswith('input/')}
history=preservation();delivery=load(OUT/'delivery-byte-index.json')
assert delivery['old_entries']==delivery['old_entries_preserved']==31167 and not delivery['modified_old_paths']
assert delivery['changed_paths']==315 and delivery['manifest_entries']==314 and len(delivery['verified_author_input_pins'])==6
static=load(OUT/'static-review.json');assert static['product_and_all_base_entries_unchanged'] and static['schema_pins']==6 and static['implementation_pins']==23
identity=load(OUT/'independent-run.json');runroot=Path(identity['run_root']).resolve();assert runroot.is_relative_to(WORK)
times=[]
for phase in PHASES:
    result=load(OUT/('result-'+phase+'.json'))
    assert result['phase']==phase and result['tests_run']==result['rounds']==1 and result['successful']
    assert result['failures']==result['errors']==0 and not result['skips'] and not result['other_groups_or_old_target_replayed']
    imports=load(OUT/('imports-'+phase+'.json'))
    for module in imports['modules']:
        p=Path(module['actual_file']).resolve();assert p.is_relative_to(WORK) and sha(p)==module['sha256']
    d=OUT/'runs'/('independent-'+phase.lower()+'-01');pre=load(d/'registration.json');end=load(d/'completion.json')
    assert pre['timeout_seconds']==60 and pre['source_index_sha256']==sha(OUT/'isolated-source-index.json') and pre['input_index_sha256']==sha(OUT/'input-index.json')
    start=datetime.fromisoformat(pre['registered_at']);finish=datetime.fromisoformat(end['finished_at']);assert start<finish
    times.append((start,finish))
assert times[0][1]<times[1][0] and times[1][1]<times[2][0]
assert {p.name for p in (runroot/'cases').iterdir()}=={'N1','N7-before-completion'}
assert not (WORK/'docs/evidence/A03/execution/P2-R8-R3-post-hold/validation').exists()
boundaries={}
for label in ('author','independent'):
    boundary=load(OUT/(label+'-boundary-review.json'));audit=load(OUT/(label+'-database-review.json'))
    assert boundary['status']=='FORMAL_N1_BOUNDARIES_VERIFIED' and boundary['effect_count']==1 and boundary['POST_HOLD_run_rows']==0
    assert boundary['receipt_three_way_registration'] and boundary['terminal_original_receipt_ref'] is None and boundary['independent_report_read_count']==1
    assert boundary['counts']['runtime']['artifacts']==20 and boundary['counts']['runtime']['native_pre_runs']==1
    assert boundary['counts']['target']['observations']==4
    assert boundary['content_check_status']=='PENDING' and boundary['submission_status']=='NOT_SUBMITTED'
    assert len(boundary['material_progress'])==2 and all(all(r['four_bindings'].values()) and r['attempt_fact']=='MAY_HAVE_BEEN_ATTEMPTED' for r in boundary['material_progress'])
    assert audit['removed'] and len(audit['copies'])==2 and audit['source_DB_SQL_connections']==0 and not Path(audit['temporary_root']).exists()
    for r in audit['copies']:assert r['copy_sha256_before']==r['copy_sha256_after']==r['source_sha256']==r['source_sha256_after'] and r['quick_check']=='ok'
    n6=load(OUT/(label+'-N6-review.json'));assert n6['status']=='COMPLETE_UNKNOWN_HISTORY_RECOMPUTE_AND_NAMED_PRE_DEPENDENCY_VERIFIED'
    assert n6['history_artifacts']==20 and n6['creation_input_artifacts']==7 and len(n6['UNKNOWN_refs'])==1
    assert n6['actual_create_plan_returns']==n6['actual_resource_manifest_returns']==1 and len(n6['resource_closure'])==6
    assert n6['original_and_actual_recomputed_plan_ref']==boundary['plan_ref'] and n6['all_actions_equal']
    assert n6['removed_exactly_one_named_EvidenceRecord'] and n6['original_anchor_and_resources_unchanged'] and n6['permit_effect_increase']==0
    assert n6['API_or_planner_calls_by_auditor']==0
    n7=load(OUT/(label+'-N7-initialization-review.json'));assert n7['status']=='ONE_RUNTIME_BEFORE_COMPLETION_INTERRUPT_FAIL_CLOSED_VERIFIED'
    assert n7['existing_hook_calls']==n7['normal_open_calls']==1 and n7['initialization_recovery_retry']==0
    assert n7['anchor']==n7['formal_completion']=='ABSENT' and not n7['meta'] and n7['copy_removed']
    assert n7['target_database']==n7['target_effects']=='NOT_CREATED' and n7['old_target_entry_or_variant_calls']==0
    assert all(n7['counts'][n]==0 for n in ('plans','intents','permits','native_creation_anchors'))
    boundaries[label]=boundary
assert boundaries['author']['formal_receipt_ref']!=boundaries['independent']['formal_receipt_ref']
author=load(OUT/'author-process-review.json');assert len(author['records'])==8 and len(author['reviewer_audit_failures'])==2
assert author['author_selected_python_JSON_files']==65 and len(author['source_index_reconciliation'])==3
for item in author['source_index_reconciliation']:
    assert item['indexed_files']==65 and sum(r['representation']=='EXPLICIT_FIVE_FILE_LF_TO_CRLF_ONLY' for r in item['specific_representations'])==5
assert author['original_R3_N7_status']=='FAILED_PRESERVED'
assert hashlib.sha256(raw('docs/evidence/A03/execution/P2-R8-R3-post-hold/runs/N7/stderr.txt',BASE)).hexdigest()=='0c5670e4e345ad9c55020d83851ea971c0dbc4a865899b425c15241847706fc5'
old_n7=json.loads(raw('docs/evidence/A03/review/P2-R8-R3-post-hold/N7-readonly-classification.json',WF))
assert old_n7['classification']=='NEW_DRIVER_ASSERTION_MORE_SPECIFIC_THAN_EXISTING_WRITTEN_CONTRACT' and old_n7['N7_original_status']=='FAILED_EXACT_OUTER_CODE_ASSERTION'
coverage=load(OUT/'p2-independent-coverage-review.json');assert len(coverage['entries'])==28 and len(coverage['N1_to_N7'])==7
assert {r['id'] for r in coverage['entries']}=={'V%02d'%i for i in range(1,11)}|{'R%02d'%i for i in range(1,19)}
for row in coverage['entries']:
    source=text(row['source'],'cb9c8f76e9eae40a8fda042c196705d7258b5107').splitlines()
    assert row['original_criterion']==source[row['line']-1] and row['no_criterion_waived']
nested=load(OUT/'independent-nested-release.json');assert nested['count']==len(nested['records'])==4
for row in nested['records']:
    d=OUT/row['record'];pre=load(d/'preregistered.json');start=load(d/'started.json');end=load(d/'completed.json')
    assert start['pid']==end['pid']==row['pid'] and not end['alive'] and not end.get('timed_out',end.get('timeout',True))
    assert end['exit_code']==row['exit_code'] and end['exit_code'] in (0,87)
    expected=hashlib.sha256(raw(row['source'])).hexdigest();assert expected==row['source_sha256']==pre['script_sha256']==sha(d/'script-snapshot.py')
    assert sha(d/'preregistered.json')==row['preregistered_sha256'] and sha(d/'completed.json')==row['completed_sha256']
    for stream in ('stdout','stderr'):assert sha(d/(stream+'.txt'))==row[stream+'_sha256']
    if 'input_sha256' in pre:assert sha(d/'request.json')==pre['input_sha256']
assert sum(r['exit_code']==87 for r in nested['records'])==1
for p in WORK.rglob('*'):
    if p.is_file() and p.name.endswith(('-wal','-journal')):assert p.stat().st_size==0
assert not list(OUT.rglob('__pycache__')) and not (OUT/'immutable-N7-copies').exists()
query_limit=load(OUT/'reviewer-query-preparation-failure.json');assert query_limit['pid'] is None and not query_limit['raw_stdout_stderr_archived']
report=REPORT.read_text(encoding='utf8')
for name in ('plan_ref','formal_receipt_ref','terminal_head_ref','POST_ref','Batch_ref'):
    assert boundaries['independent'][name]['artifact_id'] in report and boundaries['independent'][name]['content_hash'] in report
n6=load(OUT/'independent-N6-review.json');assert n6['anchor_raw_canonical_sha256'] in report and n6['full_plan_canonical_sha256'] in report
assert n6['consumer']['evidence_id'] in report and FIELD_RESET in report and 'A03整体REWORK' in report and 'I01未释放' in report
argv=['git','-c','core.longpaths=true','rev-list','--parents','--ancestry-path',BASE+'..'+TARGET]
proc=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True);lineage=proc.stdout.decode().splitlines()
assert lineage[0].split()[0]==TARGET
parents=own_processes(skip=('final-verification-01',));assert len(parents)==13
pending=tuple(OUT/p for p in ('process-release.json','final-verification.json','sha256-manifest.json'))
report_links=links(pending);assert sum(not r['exists'] for r in report_links)==3
write(OUT/'final-checks.json',{'status':'R4_LIMITED_ACCEPTANCE_FINAL_BYTES_VERIFIED','inputs':409,'source_package_files':68,'isolated_seed_files':76,
 'independent_output_files':116,'historical_preservation':history,'independent_phases_once':list(PHASES),'original_R3_N7':'FAILED_PRESERVED',
 'N7_old_target_or_variant_replays':0,'author_registered_processes':8,'own_checks_before_seal':13,'own_nested_children':4,
 'retained_reviewer_metadata_failures':2,'readonly_path_lookup_PID_raw_stream_limit_preserved':True,'overall_A03':'REWORK',
 'I01_released':False,'report_sha256':sha(REPORT),'report_links':report_links,'commit_lineage':lineage,'lineage_argv':argv,
 'lineage_exit_code':proc.returncode,'lineage_stderr_sha256':hashlib.sha256(proc.stderr).hexdigest(),'field_reset':FIELD_RESET})
print('{"status":"R4_LIMITED_ACCEPTANCE_FINAL_BYTES_VERIFIED","inputs":409,"generated":116,"history":6368,"parents_before_seal":13,"nested":4}')
