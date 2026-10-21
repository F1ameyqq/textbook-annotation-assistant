"""Freeze a static actual review. No product imports or execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
A=ROOT/'docs/evidence/A24/bootstrap-current-body-actual'


def sha(raw): return hashlib.sha256(raw).hexdigest()
def load(path): return json.loads(path.read_bytes())
def save(name,value):
    with (OUT/name).open('xb') as handle: handle.write((json.dumps(value,indent=2)+'\n').encode())


inputs=load(OUT/'input-raw-manifest.json')
assert sha((OUT/'input-raw-manifest.json').read_bytes())=='909574bb4869b10205202dc6ddf74a802d7038e199f62db06d752d8018f11c6f'
for row in inputs['members']:
    raw=(ROOT/row['path']).read_bytes()
    assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
for row in inputs['private_references']:
    raw=Path(row['snapshot_path']).read_bytes()
    assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
checks=load(OUT/'static-checks.json')
assert checks['result']=='PASS_FIXED_ACTUAL_CONSISTENCY_ONLY' and len(checks['checks'])==29 and all(checks['checks'].values())
at=datetime.now(timezone.utc).isoformat()
save('input-preservation.json',dict(schema='A24BootstrapBodyActualIndependentInputPreservation/v1',at=at,
    result='ALL_336_RAW_AND_41_PRIVATE_INPUTS_UNCHANGED',root_manifest_sha256='909574bb4869b10205202dc6ddf74a802d7038e199f62db06d752d8018f11c6f',
    product_or_input_edits=0,historical_tree_audit_repeated=False,tests_run=0))
result=dict(schema='A24BootstrapBodyActualIndependentReview/v1',at=at,
    reviewer='01a15cf8-68e0-7b63-91a3-657a567b344c',isolation=str(ROOT),
    actual_final='bf92c7b6e1c30a5dd0e4667c3d523ef77af39e01',frozen_product_final='e6278af3282cd7617cfb46808db0933aed921c0c',
    result='ACCEPTED_FIXED_NAVIGATION_PROGRESS_SCRIPT_CAPTURE_FAILURE_AND_OWN_RELEASE_ONLY',
    accepted_scope=['Recorded original navigation progress','Fixed first failure and stopped successors','Demonstrated own release'],
    inputs=dict(raw_git=336,delivery_members=27,private_snapshots=41,current_private_stream_refs=10,
        root_manifest_sha256='909574bb4869b10205202dc6ddf74a802d7038e199f62db06d752d8018f11c6f',
        actual_delivery_sha256='0797461bf4fb33f63fb288af962ffdedbfa7e59906decd23579f501b450b207c',
        all_verified=True,all_preserved=True,historical_33324_tree_audit='ROOT_FIXED_REFERENCE_NOT_REPEATED'),
    authority=dict(sha256='2dc9e2b06e0a6f7f62152b0ab0e8fef44d37362bdf7cb5684a3f3462175bc476',
        run_id='A24-first-save-r1-bootstrap-body-20261021t140721z',one_claim_chain=True,
        within_900_second_window=True,spent=1,remaining=0,retry=False,old_budgets_restored=False,
        prior_null_schema_four_get_acceptance='REFERENCED_NOT_PROMOTED_TO_SAVE',new_authority_created=False),
    pre_import_provenance=dict(dependencies=151,installed_source_checks=4,python='3.9.13',playwright='1.58.0',
        basis='Frozen wrapper source and claim records; no review-time reprobe'),
    observed=dict(native_document_http=200,native_document_elapsed_ms=5359,goto_http=200,goto_dcl_elapsed_ms=8984,
        session_completion='STARTED_NOT_RETURNED',worker_first_error=dict(code='OWNER_ERROR',type='OTHER'),
        guard_first_failure=dict(codes=['SCRIPT_CONTROLLED_OUTPUT_REQUIRED'],exception_type='Stop'),
        viewer_admission='NOT_RUN',coarse_context_bootstrap_worker_steps='NOT_RUN_BACKEND_OPEN_DID_NOT_RETURN',
        detailed_bootstrap_progress='RUNTIME_CONTEXT_GUARD_ONLINE_NAVIGATION_RECORDED',
        before_after_safe_event_counts=[13,13],truncated=False,earliest_block_index=4,
        expected_excluded_cdn_script_denials=1,completed_denial_calls=1,shared_limit=16,
        first_failure_category_event_index=None,failure_event_link='NOT_RECORDED',
        exact_script_response_request_to_error_link='UNKNOWN_NOT_RECORDED',
        http_send_dns_tcp_tls_script_necessity='UNKNOWN',
        static_output_binding_discrepancy='CONFIRMED_IN_FROZEN_SOURCE_NOT_FULL_ACTUAL_CAUSAL_PROOF'),
    not_run=['book GET','directory GET','full frames GET','natural export GET','adapter','signature','upload','commit','refresh','reopen'],
    body_schema='UNKNOWN_NO_NEW_BODY_FACTS',old_body_preservation='UNPROVEN',save_page_write_eligibility='UNPROVEN',
    actual_save='NOT_RUN',actual_independent_readback='NOT_RUN',historical_causes='UNCHANGED_UNKNOWN_WHERE_UNPROVEN',
    release=dict(context_closed=True,runtime_stopped=True,callback_pending=0,cleanup_errors=[],
        held_identities_verified=4,empty_closed_jobs=4,held_handles_closed=4,
        held_exit_codes=dict(launcher=2,product=2,worker=2,occupancy=0),
        actual_launcher_exit='PROVEN_BY_EXTERNAL_HOLDER',outer_helper_own_os_identity='NOT_SELF_CERTIFIED',
        outer_tool_exit1='AUTHOR_TRANSCRIPTION_ONLY',persistent_profile_effects='NOT_INSPECTED'),
    prior_P3=dict(original_decision_enum_control='FAIL_PRESERVED_NOT_RERUN',
        full_projection_contract='REWORK_FULL_PROJECTION_ENUM_CONTRACT_ONLY',
        blocks_prior_exact_null_schema_four_get=False,
        prior_machine_sha256='27d5279203e57646aae813e705b4ac4e7560d223b66e11fe184f2630ca00b90f'),
    static_record_checks=29,product_tests=0,old_controls=0,model_ocr_content_quality_review=0,
    private_raw_stream_contents_decoded_or_published=False,active_author_reads=False,
    new_real_resources=0,new_activation=0,product_or_input_edits=0,outbound_messages=0,pushes=0,
    report_sha256=sha((OUT/'REPORT.md').read_bytes()),reviewer_work_released=True,root_final_disposition='PENDING_COORDINATOR')
save('machine-result.json',result)
save('reviewer-release.json',dict(schema='A24BootstrapBodyActualIndependentOfflineRelease/v1',at=at,
    reviewer=result['reviewer'],offline_review_released=True,output_frozen=True,new_real_resources_acquired=0,
    new_real_resources_remaining=0,product_tests=0,product_imports=0,new_authority_or_retry=0,
    machine_result_sha256=sha((OUT/'machine-result.json').read_bytes()),root_final_disposition='PENDING_COORDINATOR'))
members=[]
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw=path.read_bytes(); members.append(dict(path=path.relative_to(OUT).as_posix(),bytes=len(raw),sha256=sha(raw)))
save('output-manifest.json',dict(schema='A24BootstrapBodyActualIndependentOutputManifest/v1',at=at,self_excluded=True,member_count=len(members),members=members))
manifest=load(OUT/'output-manifest.json')
for row in manifest['members']:
    raw=(OUT/row['path']).read_bytes(); assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
for name in ('machine-result.json','REPORT.md','reviewer-release.json','output-manifest.json'):
    print(name+' '+sha((OUT/name).read_bytes()))
print('OUTPUT_MEMBERS_VERIFIED '+str(len(members)))
