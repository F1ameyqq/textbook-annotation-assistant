"""Static result seal only; no product/control/library/native execution."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
ACTUAL = ROOT / 'docs/evidence/A24/callback-current-body-actual'
STAMP = datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def info(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': sha(raw)}


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, indent=2) + '\n').encode())


manifest = json.loads((OUT / 'input-raw-manifest.json').read_bytes())
assert info(OUT / 'input-raw-manifest.json')['sha256'] == 'ea5d849d326feb360649f4146933c39e4d6d378f28531b7faaa4d1192f523e4e'
assert len(manifest['members']) == 321 and len(manifest['private_references']) == 31
for row in manifest['members']:
    raw = (ROOT / row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['blob']
for row in manifest['private_references']:
    assert info(Path(row['snapshot_path'])) == {'bytes': row['bytes'], 'sha256': row['sha256']}
assessment = json.loads((OUT / 'evidence-assessment.json').read_bytes())
assert assessment['result'] == 'CONSISTENT_FIXED_HTTP200_DCL_ORIGIN_BLOCKED_FAILURE_AND_OWN_RELEASE_RECORDS'
actual = json.loads((ACTUAL / 'actual-result.json').read_bytes())
write('input-preservation.json', {'schema': 'A24CallbackBodyIndependentPreservation/v1', 'at_utc': STAMP,
    'result': 'PASS_RAW_PRESERVATION', 'raw_inputs': 321, 'candidate_dependencies_verified_at_intake': 144,
    'final_actual_members': 26, 'private_snapshots': 31, 'current_output_refs': 10,
    'all_raw_size_sha256_git_blob_checks': True, 'private_size_sha256_checks': True,
    'input_product_or_old_evidence_changes': 0, 'active_author_or_original_private_paths_read': False,
    'root_historical_33135_member_diff': 'FIXED_COORDINATOR_EVIDENCE_NOT_REPEATED',
    'earlier_actual_manifest': 'PRESERVED_NOT_FINAL_INTAKE_AUTHORITY'})
write('release.json', {'schema': 'A24CallbackBodyIndependentStaticRelease/v1', 'released': True, 'at_utc': STAMP,
    'scope': 'Own static metadata/record-consistency helpers only', 'intake_assessment_helper': 'COMPLETED_EXIT_0',
    'sealing_helper': 'Exits after output-manifest verification/hash output', 'retained_reviewer_helpers': 0,
    'real_resources_acquired_by_reviewer': 0, 'product_control_suite_model_native_browser_profile_lock_network_runs': 0,
    'credentials_login_upload_save_reopen_activation': 0,
    'actual_accepted_release_scope': 'Recorded context/runtime/callback plus four exact held-process/Job/handle releases',
    'actual_outer_supervisor_own_OS_exit': 'NOT_SELF_CERTIFIED',
    'this_round_remaining': 0, 'earlier_current_body_remaining': [0, 0], 'older_readonly_remaining': [0, 0],
    'actual_save': 'NOT_RUN', 'actual_independent_platform_readback': 'NOT_RUN', 'new_authority_or_retry': False})
write('independent-result.json', {
    'schema': 'A24CallbackBodyFixedActualIndependentReview/v1',
    'result': 'ACCEPTED_FIXED_PARTIAL_NAVIGATION_HTTP200_DCL_ORIGIN_BLOCKED_FAILURE_AND_OWN_RELEASE_ONLY',
    'accepted_scope': 'RECORDED_ORIGINAL_NAVIGATION_FAILURE_AND_DEMONSTRATED_OWN_CONTEXT_RUNTIME_CALLBACK_HELD_RELEASE_ONLY',
    'at_utc': STAMP, 'reviewer': '01a15cf8-68e0-7b63-91a3-657a567b344c',
    'coordinator': '01a15dfa-9556-7812-9ed5-1b3bce53555e', 'same_A24_stage': True,
    'task_sha256': '198ecdcd8042b438eba4dfeeb1cc6dc98a4826c4392748c902d609d563e05601',
    'base_code_final': 'c71fe78bae5cfd6e3f1d97ba52647159ad68d796',
    'actual_final': '3bf353e7e486c2648bdfb5a602d96f3fd80781fc',
    'candidate_sha256': '79c4453822efc6e9b856d5859b6711157998291efe62d6f3d6aa15d0244f3574',
    'final_actual_manifest_sha256': 'b9246689ceee971f4b55a37f55a1851513f50922613b668c5391abf699836e97',
    'actual_result_sha256': info(ACTUAL / 'actual-result.json')['sha256'],
    'root_input_manifest_sha256': 'ea5d849d326feb360649f4146933c39e4d6d378f28531b7faaa4d1192f523e4e',
    'inputs_verified': {'raw': 321, 'candidate_dependencies': 144, 'final_actual_members': 26,
        'private_snapshots': 31, 'current_raw_output_refs': 10},
    'authority': dict(assessment['authority'], attempt_count=1, conditional_save_authorized=False,
        independent_reopen_authorized=False),
    'recorded_library_preflight': {'source': 'Frozen wrapper plus outer claim; no reviewer import/reprobe',
        'dependency_hash_count': 144, 'library_source_hash_count': 4, 'python': '3.9.13', 'playwright': '1.58.0',
        'whole_runtime_or_browser_binary_fully_hashed': False},
    'navigation_progress': {'original_main_document_association': 'ORIGINAL_MAIN_DOCUMENT_NETWORK_ID',
        'native_HTTP': 200, 'native_HTTP_elapsed_ms': 6922.0, 'goto_HTTP': 200,
        'goto_and_DCL_elapsed_ms': 7094.0, 'goto_state': 'DONE', 'DCL_observed': True,
        'authentication_or_viewer_admission_proven': False},
    'failure': {'bootstrap_steps': assessment['bootstrap_steps'], 'worker_first_error': assessment['worker_first_error'],
        'guard_first_failure': assessment['guard_first_failure'], 'phase': 'SESSION_COMPLETION_STARTED_NOT_RETURNED',
        'blocked_origin': 'UNKNOWN_NOT_RETAINED', 'blocked_path': 'UNKNOWN_NOT_RETAINED',
        'blocked_resource_kind': 'UNKNOWN_NOT_RETAINED', 'blocked_request_purpose': 'UNKNOWN',
        'full_causal_chain': 'UNKNOWN_NOT_FULLY_PROVEN', 'historical_timeout_causal_fix_claimed': False,
        'navigation': assessment['navigation']},
    'successors': {k: 'NOT_RUN' for k in ['viewer_admission', 'book', 'directory', 'full_frames', 'natural_export',
        'adapter', 'signature', 'upload', 'commit', 'refresh', 'independent_reopen']},
    'body_schema_complete_old_content_newness_legal_append_account_savepage': 'UNPROVEN_NO_BUSINESS_SOURCE_FACTS',
    'recorded_login_credential_config_model_calls': 0,
    'release_disposition': {'worker_context_runtime_callback': 'ACCEPTED_RECORDED_OWN_RELEASE',
        'worker_release': assessment['worker_release'], 'held_records': assessment['held_records'],
        'accepted_held_identity_exits_empty_closed_jobs_handles': 4,
        'outer_holder_proves_actual_launcher_exit': True,
        'outer_supervisor_own_OS_identity': 'NOT_SELF_CERTIFIED_UNPROVEN',
        'guard_failure_after_release': 'RETAINED_FAILURE_NOT_PROMOTED_TO_SUCCESS'},
    'raw_streams': {'all_eight_stage_stdout_stderr_originals_verified': True,
        'all_four_stage_stderr': 'EMPTY_ORIGINAL_BYTES_VERIFIED', 'outer_duplicate_stream_refs_verified': 2,
        'raw_contents_published': False,
        'held_stage_exits': {'launcher': 2, 'product': 2, 'worker': 2, 'occupancy': 0},
        'reported_outer_tool_exit1': 'AUTHOR_TRANSCRIPTION_NO_RAW_TOOL_RESULT_SUPPLIED',
        'held_launcher_exit2': 'FROZEN_HELD_IDENTITY_RECORD'},
    'profile_scope': {'manual_reset_edit_lock_removal_claim_clear': 'RECORDED_FALSE',
        'persistent_browser_effects': 'NOT_INSPECTED_NOT_CLAIMED_ABSENT', 'post_failure_probe': 'NOT_RUN'},
    'budget': {'this_round_spent': 1, 'this_round_remaining': 0,
        'earlier_current_body_remaining': [0, 0], 'older_readonly_remaining': [0, 0],
        'retry_extension_restart_or_source_replay': False},
    'reviewer_activity': {'mode': 'STATIC_ONLY', 'product_tests_old_suites_callback_controls_model_actual_resources': 0,
        'read_helper_error': json.loads((OUT / 'intake-result.json').read_bytes())['reviewer_metadata_error']},
    'other_work': {'prior_model_content_and_code_acceptance': 'UNCHANGED_NOT_REVIEWED_AGAIN',
        'later_author_compatibility_candidate': 'OUTSIDE_THIS_REVIEW_NOT_AWAITED', 'new_chat_or_stage': False},
    'limits': {'write_eligible': False, 'production_ready': False, 'actual_save': 'NOT_RUN',
        'actual_independent_platform_readback': 'NOT_RUN', 'new_authority': False,
        'global_or_outer_supervisor_full_OS_release_claimed': False},
    'artifacts': {name: info(OUT / name) for name in ['report.md', 'input-raw-manifest.json', 'actual-input-manifest.json',
        'intake-result.json', 'evidence-assessment.json', 'input-preservation.json', 'release.json']}})
members = [dict(path=p.relative_to(OUT).as_posix(), **info(p)) for p in sorted(OUT.rglob('*'))
    if p.is_file() and p.name != 'output-manifest.json']
write('output-manifest.json', {'schema': 'A24CallbackBodyIndependentOutputManifest/v1',
    'self_excluded': True, 'member_count': len(members), 'members': members})
for row in members:
    assert info(OUT / row['path']) == {'bytes': row['bytes'], 'sha256': row['sha256']}
assert {r['path'] for r in members} == {p.relative_to(OUT).as_posix() for p in OUT.rglob('*')
    if p.is_file() and p.name != 'output-manifest.json'}
print(json.dumps({'result': 'ACCEPTED_FIXED_PARTIAL_NAVIGATION_HTTP200_DCL_ORIGIN_BLOCKED_FAILURE_AND_OWN_RELEASE_ONLY',
    'inputs_preserved': 321, 'private_snapshots_preserved': 31, 'output_members_excluding_manifest': len(members),
    'machine_sha256': info(OUT / 'independent-result.json')['sha256'],
    'output_manifest_sha256': info(OUT / 'output-manifest.json')['sha256'],
    'release_sha256': info(OUT / 'release.json')['sha256']}))
