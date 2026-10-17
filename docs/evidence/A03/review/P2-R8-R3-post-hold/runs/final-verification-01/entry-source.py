# -*- coding: utf-8 -*-
"""Final reconciliation of already produced bytes; never executes product APIs."""
import hashlib
import json
from pathlib import Path
import subprocess
from archive_common import ROOT,OUT,REPORT,PHASES,FIELD_RESET,load,sha,write,links,preservation,own_processes
from evidence import WORK,EV,TARGET,BASE,raw,document
index=load(OUT/'input-index.json')['exports'];supplement=load(OUT/'supplemental-input-index.json')['files']
assert len(index)==678 and len(supplement)==1 and len({r['file'] for r in index+supplement})==679
for row in index+supplement:
    p=OUT/row['file'];b=p.read_bytes()
    assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],row['file']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['raw_git_sha1']
seed=load(OUT/'isolated-source-index.json')['files'];output=load(OUT/'independent-output-index.json')['files']
assert len(seed)==121 and len(output)==281
for row in seed+output:
    p=OUT/row['file'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['file']
assert {p.relative_to(OUT).as_posix() for p in WORK.rglob('*') if p.is_file()}=={r['file'] for r in seed+output}
assert {p.relative_to(OUT).as_posix() for p in (OUT/'input').rglob('*') if p.is_file()}=={r['file'] for r in index+supplement if r['file'].startswith('input/')}
history=preservation()
delivery=load(OUT/'delivery-byte-index.json');assert (delivery['old_entries'],delivery['old_entries_preserved'],delivery['manifest_entries'],delivery['changed_paths'])==(30285,30282,884,885)
assert set(delivery['modified_old_paths'])=={'src/annotation/runtime/storage/native.py','src/annotation/contracts/a03_native/data/profile.json','src/annotation/contracts/a03_native/data/adoption.json'}
assert len(delivery['verified_author_input_pins'])==6
static=load(OUT/'static-review.json');assert static['three_call_sites_verified'] and static['schema_pins']==6 and static['implementation_pins']==23
identity=load(OUT/'independent-run.json');runroot=Path(identity['run_root'])
assert runroot.resolve().is_relative_to(WORK)
for phase in PHASES:
    result=load(OUT/('result-'+phase+'.json'))
    assert result['phase']==phase and result['tests_run']==result['rounds']==1 and result['successful']
    assert result['failures']==result['errors']==0 and not result['skips'] and not result['N6_N7_or_compatibility_run']
    imports=load(OUT/('imports-'+phase+'.json'))
    for module in imports['modules']:
        p=Path(module['actual_file']).resolve();assert p.is_relative_to(WORK/'src') and sha(p)==module['sha256']
assert not list((runroot/'cases').glob('N6*')) and not list((runroot/'cases').glob('N7*'))
assert load(OUT/'runs/independent-n2-01/registration.json')['timeout_seconds']==120
assert load(OUT/'runs/independent-n2-01/completion.json')['elapsed_seconds']>=60
boundaries={}
for label,control_count in [('author',7),('independent',6)]:
    boundary=load(OUT/(label+'-boundary-review.json'));post=load(OUT/(label+'-post-hold-review.json'))
    assert boundary['status']=='FORMAL_N1_BOUNDARIES_VERIFIED' and boundary['effect_count']==1 and boundary['POST_HOLD_run_rows']==2
    assert boundary['receipt_three_way_registration'] and boundary['terminal_original_receipt_ref'] is None and boundary['independent_report_read_count']==1
    assert boundary['content_check_status']=='PENDING' and boundary['submission_status']=='NOT_SUBMITTED'
    assert len(boundary['material_progress'])==2 and all(all(r['four_bindings'].values()) and r['attempt_fact']=='MAY_HAVE_BEEN_ATTEMPTED' for r in boundary['material_progress'])
    assert post['status']=='TWO_POST_HOLD_ADMISSIONS_AND_GUARDS_VERIFIED' and len(post['admissions'])==2 and post['effect_count']==1
    assert not post['hold_cleared'] and post['final_hold'] and post['current_same_hold_two_heads_only'] and not post['different_hold_id_or_qualified_clearance_tested']
    assert post['expiry']['recorded_real_wait'] and not post['expiry']['clock_or_SQL_modified']
    assert len(post['exact_refusals'])==6
    audit=load(OUT/(label+'-database-review.json'));assert audit['removed'] and len(audit['copies'])==2 and audit['source_DB_SQL_connections']==0
    assert not Path(audit['temporary_root']).exists()
    for record in audit['copies']:
        assert record['copy_sha256_before']==record['copy_sha256_after']==record['source_sha256']==record['source_sha256_after']
        assert record['quick_check']=='ok'
    controls=load(OUT/(label+'-control-database-review.json'));assert controls['temporary_removed'] and len(controls['records'])==control_count
    assert all(r['sha256_before']==r['sha256_after'] for r in controls['records'])
    boundaries[label]=boundary
assert boundaries['author']['formal_receipt_ref']!=boundaries['independent']['formal_receipt_ref']
negative=load(OUT/'negative-controls-review.json');assert len(negative['results'])==2 and len(negative['actual_N3_inputs'])==5
assert negative['native_product_reexecutions_by_auditor']==0 and not negative['N6_N7_run']
assert all(r['schema_completed_before_comparison'] and r['artifact_hashes_recomputed_and_verified'] and not r['admission_attempted'] for r in negative['actual_N3_inputs'])
n7=load(OUT/'N7-readonly-classification.json')
assert n7['N7_original_status']=='FAILED_EXACT_OUTER_CODE_ASSERTION' and n7['classification']=='NEW_DRIVER_ASSERTION_MORE_SPECIFIC_THAN_EXISTING_WRITTEN_CONTRACT'
assert n7['actual_rejection'] and not n7['product_change_required_by_this_failed_assertion'] and n7['N7_replays_or_variants']==0
assert n7['N6']=='NOT_RUN' and n7['incomplete_initialization']=='NOT_REACHED'
assert hashlib.sha256(raw(EV+'runs/N7/stderr.txt')).hexdigest()=='0c5670e4e345ad9c55020d83851ea971c0dbc4a865899b425c15241847706fc5'
cli=raw('src/annotation/runtime/recovery/cli.py')
assert b'errors = getattr(error, "issues", None)' in cli and b'code = errors[0].get("code", "INVALID_INPUT")' in cli
coverage=load(OUT/'p2-independent-coverage-review.json')
assert coverage['status']=='ALL_28_ORIGINAL_CRITERIA_REVIEWED_NO_WAIVER'
assert {r['id'] for r in coverage['entries']}=={'V%02d'%i for i in range(1,11)}|{'R%02d'%i for i in range(1,19)}
author=load(OUT/'author-process-review.json');assert len(author['records'])==34 and author['N7_parent_exit']==1 and author['candidate_tests_rerun']==0
assert [r['tests'] for r in author['compatibility']]==[70,52,13]
script_proof=[];current=raw('tests/test_a03_r8_r3_post_hold.py')
for phase in ('N1','N2'):
    snapshot=raw(EV+'runs/'+phase+'/script-snapshots/test_a03_r8_r3_post_hold.py')
    assert hashlib.sha256(snapshot).hexdigest()=='501911ae33a741cf2d9cefc60995a12adb6b3ee4197d369629ff521847453659'
    assert hashlib.sha256(current).hexdigest()==static['driver_sha256']=='02acb22f395f380528130166ca8ae4637e3303c73f6496d9da4166b5050a1467'
    before=snapshot.decode('utf8');after=current.decode('utf8')
    assert before.count('    def test_N4')==after.count('    def test_N4')==1
    assert before.split('    def test_N4',1)[0]==after.split('    def test_N4',1)[0]
    marker="if __name__ == '__main__':";assert before.count(marker)==after.count(marker)==1
    assert before.split(marker,1)[1]==after.split(marker,1)[1]
    script_proof.append({'group':phase,'full_snapshot_equals_final':False,'all_helpers_and_N1_N2_prefix_byte_equal':True,'main_entry_suffix_byte_equal':True,
      'snapshot_sha256':hashlib.sha256(snapshot).hexdigest(),'final_sha256':hashlib.sha256(current).hexdigest()})
nested=load(OUT/'independent-nested-release.json');assert nested['count']==len(nested['records'])==10
for row in nested['records']:
    d=OUT/row['record'];pre=load(d/'preregistered.json');start=load(d/'started.json');end=load(d/'completed.json')
    assert start['pid']==end['pid']==row['pid'] and not end['alive'] and not end.get('timed_out',end.get('timeout',True))
    assert end['exit_code']==row['exit_code'] and end['exit_code'] in (0,87)
    expected=hashlib.sha256(raw(row['source'])).hexdigest()
    assert expected==row['source_sha256']==pre['script_sha256']==sha(d/'script-snapshot.py')
    assert sha(d/'preregistered.json')==row['preregistered_sha256'] and sha(d/'completed.json')==row['completed_sha256']
    for stream in ('stdout','stderr'):assert sha(d/(stream+'.txt'))==row[stream+'_sha256']
    if 'input_sha256' in pre:assert sha(d/'request.json')==pre['input_sha256']
assert sum(r['exit_code']==87 for r in nested['records'])==1
for p in WORK.rglob('*'):
    if p.is_file() and p.name.endswith(('-wal','-journal')):assert p.stat().st_size==0
assert not list(OUT.rglob('__pycache__'))
query_limit=load(OUT/'reviewer-query-preparation-failure.json');assert query_limit['pid'] is None and query_limit['exit_code'] is None and not query_limit['raw_stdout_stderr_archived']
report=REPORT.read_text(encoding='utf8')
for name in ('plan_ref','formal_receipt_ref','terminal_head_ref','POST_ref','Batch_ref'):
    assert boundaries['independent'][name]['artifact_id'] in report and boundaries['independent'][name]['content_hash'] in report
for row in load(OUT/'independent-post-hold-review.json')['admissions']:
    assert row['run_id'] in report and row['pre_ref']['content_hash'] in report and row['binding']['context']['hold_head']['hash'] in report
assert FIELD_RESET in report and 'A03 整体 REWORK' in report and 'I01 未释放' in report
argv=['git','-c','core.longpaths=true','rev-list','--parents','--ancestry-path',BASE+'..'+TARGET]
proc=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
lineage=proc.stdout.decode().splitlines();assert lineage[0].split()[0]==TARGET
assert '13c8a766124ac45a91fa3edfa22de7df1e033c3e' in {r.split()[0] for r in lineage}
parents=own_processes(skip=('final-verification-01',));assert len(parents)==18
pending=tuple(OUT/p for p in ('process-release.json','final-verification.json','sha256-manifest.json'))
report_links=links(pending);assert sum(not r['exists'] for r in report_links)==3
value={'status':'POST_HOLD_LOCAL_N1_N5_LIMITED_ACCEPTED_FINAL_BYTES_VERIFIED','inputs':678,'supplemental_authority_inputs':1,
 'source_package_files':68,'isolated_seed_files':121,'independent_output_files':281,'historical_preservation':history,
 'executed_author_N1_N2_driver_region_proof':script_proof,'independent_phases_once':list(PHASES),'N6':'NOT_RUN',
 'N7':'ORIGINAL_FAILED_READONLY_CLASSIFIED','incomplete_initialization':'NOT_REACHED','N7_or_variant_replays':0,
 'author_registered_processes':34,'own_checks_before_seal':18,'own_nested_children':10,'retained_reviewer_metadata_failures':3,
 'CLI_outer_issue_code_is_observable':True,'CLI_source_sha256':hashlib.sha256(cli).hexdigest(),
 'readonly_query_PID_raw_stream_limit_preserved':True,'overall_A03':'REWORK','I01_released':False,'report_sha256':sha(REPORT),
 'report_links':report_links,'commit_lineage':lineage,'lineage_argv':argv,'lineage_exit_code':proc.returncode,
 'lineage_stderr_sha256':hashlib.sha256(proc.stderr).hexdigest(),'field_reset':FIELD_RESET}
write(OUT/'final-checks.json',value)
print(json.dumps({'status':value['status'],'inputs':678,'supplement':1,'generated':281,'history':5229,'own_parents_before_seal':18,'nested':10}))
