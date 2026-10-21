"""Freeze completed offline review; no product or control execution."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys

OUT=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(name):return json.loads((OUT/name).read_bytes())
def save(name,value):
    with (OUT/name).open('xb') as handle:handle.write((json.dumps(value,indent=2)+'\n').encode())

seven=load('python-result.json');edge=load('independent-control-result.json');delta=load('static-delta-result.json')
assert seven['tests']==7 and seven['passed'] and seven['failures']==seven['errors']==0
assert edge['tests']==edge['run_count']==1 and edge['passed'] and edge['failures']==edge['errors']==0
assert delta['passed'] and load('input-preservation.json')['result']=='ALL_322_RAW_AND_41_PRIVATE_INPUTS_UNCHANGED'
at=datetime.now(timezone.utc).isoformat()
machine=dict(schema='A24ControlledCaptureIndependentReview/v1',at=at,
    reviewer='01a15cf8-68e0-7b63-91a3-657a567b344c',isolation=str(OUT.parents[3]),
    base='bf92c7b6e1c30a5dd0e4667c3d523ef77af39e01',product='576fe90a98b2f0e933c69062c4e73d9e6210bd86',
    final='61fb7157eb335d2a0b9348e8496ea0b4b8d17ad0',result='ACCEPTED_OFFLINE_ONLY',
    accepted_scope='BOUNDED_CURRENT_OWNER_PRIVATE_CAPTURE_INTEGRATION',
    standalone_four_get='ACCEPTED_OFFLINE_ONLY_BOUNDED_FOUR_GET_PREFLIGHT',
    demonstrated_material_risk_blocking_exact_branch=False,
    frozen_inputs=dict(raw_git=322,candidate_dependencies=158,delivery_members=321,private_snapshots=41,
        root_manifest_sha256='53e6959b6e213bdd89443c1654b75a25ad065d665c121114c2edf0ac80cf02e9',
        candidate_sha256='f1b31fe4e27b9cb47e5476805e00fc56ce49d33666fd8353c67ce43bd4d9326a',
        final_delivery_sha256='8abdacaf11329d62e2ad1e56ae95cf527689d3310cadaecc749298766f8949a9',
        raw_intake_and_closure_preservation=True,historical_tree_audit='ROOT_FIXED_REFERENCE_NOT_REPEATED'),
    capture_binding=dict(validated_authority=True,current_run_hash_scope_candidate=True,
        template='{NEW_AUTHORITY_OUTPUT}/private/source-capture',
        exclusive_directory_marker_and_asset_writes=True,plain_path_and_reparse_checks=True,
        validate_before_inherited_capture=True,fresh_framework_live_out_only=True,
        original_capture_output_equality_and_32MiB_limit_preserved=True,
        old_outputs_claims_native_auth_readonly_and_origin_timeout_guards_unchanged=True,
        safe_evidence_after_settlement=True,raw_urls_and_bytes_private=True,captured_code_executed_by_collector=False),
    execution=dict(python=sys.version,new_seven_group_runs=1,new_seven_passed=7,new_seven_failed=0,new_seven_errors=0,
        seven_report_duration_ms=seven['duration_ms'],independent_controls=1,independent_passed=1,
        independent_failed=0,independent_errors=0,independent_report_duration_ms=edge['duration_ms'],
        independent_edge='POST_BINDING_REPARSE_FLAG_THROUGH_SCHEDULED_RESPONSE',
        independent_observation=edge['observation'],reruns=0,old_suites_or_failures_run=0,
        model_ocr_content_quality_review=0,real_browser_profile_native_network_or_product_launch=0),
    test_limits=['WindowsBackend.open and inherited callbacks use synthetic browser/runtime/CDP/HTTP objects',
        'Constructor/profile/occupancy replaced or bypassed',
        'Four acquisition calls use mocked CurrentPageIO.fetch_async, not actual book query/native response bodies',
        'Reparse flag is simulated through lstat, not a real junction test',
        'No proof of current platform behavior or original failure causal identity'],
    P3=dict(current_decision_allow_block_validation='ACCEPTED_IN_THIS_REVISION',
        new_distinct_negative_control='PASS',historical_independent_decision_FAIL='PRESERVED_NOT_RERUN_OR_RELABELED',
        historical_full_projection_REWORK='PRESERVED_FOR_OLD_CANDIDATE',
        every_other_auxiliary_field_independently_finite_enum_validated='NOT_CLAIMED',
        blocks_exact_four_get=False),
    exact_future_branch=dict(role='AUTHOR_SAVE',schema_profile=None,body_admission='CURRENT_SCHEMA_UNBOUND',
        new_exact_coordinator_authority_required=True,contexts=1,initial_navigations=1,total_seconds_max=900,
        business_reads=['official-context book slot','directory book46007447','full frames book46007447','natural export book46007447'],
        each_read_max=1,terminal_status='PREWRITE_BLOCKED_NO_EFFECT',schema_self_promotion=False,
        signature=0,upload=0,commit=0,refresh=0,reopen=0,login=0,credentials=0,model=0,retry=0),
    prior_actual=dict(final='bf92c7b6e1c30a5dd0e4667c3d523ef77af39e01',
        machine_sha256='4a5b338ae57f1950689e681d44431b847ac397d962632661721387bd54590d9b',
        root_disposition_sha256='79184423a6557dd1b6c64ddc9aee6e294ebfa782f35bd1eadccc61b028f54980',
        acceptance='FIXED_NAVIGATION_CAPTURE_FAILURE_AND_OWN_RELEASE_ONLY',
        exact_script_response_error_association='UNKNOWN_NOT_RECORDED',historical_causes='UNCHANGED',
        all_prior_rounds_remaining=0,reopened_or_retried=False),
    current_body_schema='UNKNOWN_NO_NEW_BODY_FACTS',old_body_preservation='UNPROVEN',
    newness_legal_append_save_page_payload_receipt_signature='UNPROVEN',
    conditional_17_20_plan='UNCHANGED_NOT_ACTUAL_SAVE_QUALIFICATION',actual_save='NOT_RUN',actual_independent_readback='NOT_RUN',
    tools=dict(new_seven=dict(chunk='db7651',exit=0),independent_edge=dict(chunk='7f0032',exit=0),
        static_closure=dict(chunk='3f775f',exit=0)),
    new_authority_or_activation=0,new_real_resources=0,active_author_reads=False,product_or_input_edits=0,
    outbound_messages=0,pushes=0,report_sha256=sha((OUT/'REPORT.md').read_bytes()),
    reviewer_work_released=True,root_final_disposition='PENDING_COORDINATOR')
save('machine-result.json',machine)
save('reviewer-release.json',dict(schema='A24ControlledCaptureIndependentOfflineRelease/v1',at=at,
    reviewer=machine['reviewer'],offline_work_released=True,output_frozen=True,new_real_resources_acquired=0,
    new_real_resources_remaining=0,test_processes='EXITED_AS_RECORDED_BY_TOOLS',synthetic_temporary_objects_only=True,
    product_or_input_edits=0,new_authority_or_activation=0,reruns=0,
    machine_result_sha256=sha((OUT/'machine-result.json').read_bytes()),root_final_disposition='PENDING_COORDINATOR'))
members=[]
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw=path.read_bytes();members.append(dict(path=path.relative_to(OUT).as_posix(),bytes=len(raw),sha256=sha(raw)))
save('output-manifest.json',dict(schema='A24ControlledCaptureIndependentOutputManifest/v1',at=at,self_excluded=True,member_count=len(members),members=members))
for row in members:
    raw=(OUT/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
for name in ('machine-result.json','REPORT.md','reviewer-release.json','output-manifest.json'):
    print(name+' '+sha((OUT/name).read_bytes()))
print('OUTPUT_MEMBERS_VERIFIED '+str(len(members)))
