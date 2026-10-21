"""Freeze this completed review; never execute product or tests."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    with (OUT / name).open('xb') as handle:
        handle.write((json.dumps(value, indent=2)+'\n').encode('utf-8'))


seven = json.loads((OUT / 'python-result.json').read_bytes())
edge = json.loads((OUT / 'independent-control-result.json').read_bytes())
delta = json.loads((OUT / 'static-delta-result.json').read_bytes())
preservation = json.loads((OUT / 'input-preservation.json').read_bytes())
assert seven['tests'] == 7 and seven['passed'] and seven['failures'] == seven['errors'] == 0
assert edge['tests'] == edge['failures'] == edge['run_count'] == 1 and edge['errors'] == 0 and not edge['passed']
assert edge['subsequent_controls'] == 'NOT_RUN_FIRST_FAILURE'
assert delta['passed'] and preservation['result'] == 'ALL_FROZEN_INPUTS_UNCHANGED'
at = datetime.now(timezone.utc).isoformat()
machine = dict(schema='A24BootstrapExclusionIndependentReview/v1', at=at,
    reviewer='01a15cf8-68e0-7b63-91a3-657a567b344c',
    isolation=str(OUT.parents[3]), base='3bf353e7e486c2648bdfb5a602d96f3fd80781fc',
    product='0a0cd3491df0bc0cf7d38364599fe3c39b830388', final='e6278af3282cd7617cfb46808db0933aed921c0c',
    full_projection_contract='REWORK_FULL_PROJECTION_ENUM_CONTRACT_ONLY',
    denial_compatibility='ACCEPTED_OFFLINE_ONLY_DENIAL_SHARED16',
    reachable_safe_audit_path='ACCEPTED_FOR_BOUNDED_FOUR_GET_WITH_AUXILIARY_LIMITATION',
    standalone_four_get='ACCEPTED_OFFLINE_ONLY_BOUNDED_FOUR_GET_PREFLIGHT',
    auxiliary_gap_blocks_standalone_four_get=False,
    finding=dict(id='A24-BOOTSTRAP-I01', priority='P3',
        location='src/annotation/runtime/live_pilot/owner.py:178',
        fact='Shape-valid non-enum decision is projected with complete=true after direct internal mutation',
        expected='Explicit finite-enum validation, PROJECTION_ERROR and complete=false',
        independent_control='FAIL_PRESERVED_NO_RERUN',
        producer_reachability='NOT_REACHABLE_FROM_FROZEN_AUDIT_AND_POLICY_PRODUCERS',
        direct_internal_mutation_required=True, synthetic_value_sensitive=False,
        demonstrated_credential_body_leak=False, demonstrated_authority_change=False,
        demonstrated_wrong_business_request=False, demonstrated_loss_of_real_first_failure=False,
        permitted_disposition='Nonblocking auxiliary robustness gap for the exact null-schema four-GET branch only'),
    independent_execution=dict(python=sys.version, seven_control_groups=1, seven_controls=7, seven_passed=7,
        seven_failed=0, seven_errors=0, seven_report_duration_ms=seven['duration_ms'],
        independent_controls=1, independent_passed=0, independent_failed=1, independent_errors=0,
        first_failure_preserved=True, successors='NOT_RUN_FIRST_FAILURE', reruns=0,
        old_suites=0, model_content_crop_reviews=0, real_product_launches=0),
    frozen_inputs=dict(raw_git=308, candidate_dependencies=151, delivery_members=307, private_snapshots=31,
        root_manifest_sha256='b8b76362839d1d0ab688830044b165ef19c6979138d0a96a56dc4e102016c490',
        candidate_sha256='a949fb89eba82b4b1e225764b1e07c1022e3052fa242e9c81635f4031af1dc62',
        final_delivery_sha256='f384634367966762aba93a051aa2e4a2f3aa2b8d4cf965a2f14e755a164f00d9',
        raw_verified_before_execution=True, all_308_and_31_reverified_unchanged=True,
        historical_full_tree_comparison='ROOT_FIXED_EVIDENCE_REFERENCED_NOT_RERUN', active_author_reads=False),
    exact_future_branch=dict(role='AUTHOR_SAVE', schema_profile=None, body_admission='CURRENT_SCHEMA_UNBOUND',
        new_exact_coordinator_authority_required=True, activated_by_this_review=False,
        contexts=1, initial_viewer_navigations=1, total_seconds_max=900,
        business_reads=['same-page official-context book slot', 'directory file_id=46007447',
                        'full frames book46007447', 'natural export book46007447'], each_business_read_max=1,
        terminal_status='PREWRITE_BLOCKED_NO_EFFECT', schema_self_promotion=False,
        signature=0, upload=0, commit=0, refresh=0, reopen=0, credentials=0, login=0, model=0, retry=0),
    actual_facts=dict(new_live_runs=0, all_prior_actual_remaining=0,
        previous_blocked_origin_path_kind_purpose='UNKNOWN_NOT_RETAINED',
        actual_cause_repaired='UNPROVEN', source_body_schema='UNKNOWN_NO_NEW_BODY_FACTS',
        old_body_preservation='UNPROVEN', save_page_and_write_eligibility='UNPROVEN',
        conditional_17_20_plan='UNCHANGED_NOT_ACTUAL_SAVE_QUALIFICATION',
        actual_save='NOT_RUN', actual_independent_reopen='NOT_RUN'),
    helper_failures=[dict(chunk='735f54', exit=1, kind='Source definition no-match in imported wrapper'),
        dict(chunk='4075be', exit=1, kind='Guessed package path absent; corrected using rg --files'),
        dict(chunk='b1abda', exit=1, kind='Guessed package paths absent; corrected using rg --files')],
    tool_exit_evidence=dict(seven=dict(chunk='b28fed', exit=0),
        independent_control=dict(chunk='3df9b0', exit=1), static_closure=dict(chunk='e973af', exit=0)),
    product_or_input_edits=0, new_activations=0, outbound_thread_or_service_messages=0, pushes=0,
    root_final_disposition='PENDING_COORDINATOR', reviewer_work_released=True,
    report_sha256=sha((OUT / 'REPORT.md').read_bytes()))
save('machine-result.json', machine)
save('reviewer-release.json', dict(schema='A24BootstrapIndependentOfflineRelease/v1', at=at,
    reviewer=machine['reviewer'], offline_work_released=True, output_frozen=True,
    new_real_resources_acquired=0, new_real_resources_remaining=0,
    python_test_processes='EXITED_AS_RECORDED_BY_TOOLS', synthetic_objects_only=True,
    product_or_input_edits=0, activation_or_live=0, live_authority_created=False,
    root_final_disposition='PENDING_COORDINATOR',
    machine_result_sha256=sha((OUT / 'machine-result.json').read_bytes()),
    failure_preserved=True, reruns=0, successors='NOT_RUN_FIRST_FAILURE'))
members = []
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw = path.read_bytes()
        members.append(dict(path=path.relative_to(OUT).as_posix(), bytes=len(raw), sha256=sha(raw)))
save('output-manifest.json', dict(schema='A24BootstrapIndependentOutputManifest/v1', at=at,
    self_excluded=True, member_count=len(members), members=members))
for name in ('machine-result.json', 'REPORT.md', 'reviewer-release.json', 'output-manifest.json'):
    print(name+' '+sha((OUT / name).read_bytes()))
print('OUTPUT_MEMBERS '+str(len(members)))
