"""Seal static actual-result review; no tests, native or product imports."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
ACTUAL = ROOT / 'docs/evidence/A24/minimum-gate-current-body-actual'
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
assert info(OUT / 'input-raw-manifest.json')['sha256'] == '6812bb2a2c5ea2dc3c70d866b2693a1f8eef33bcec379bee16d601daf75e1e73'
assert len(manifest['members']) == 313 and len(manifest['private_references']) == 27
for row in manifest['members']:
    raw = (ROOT / row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['blob']
for row in manifest['private_references']:
    assert info(Path(row['snapshot_path'])) == {'bytes': row['bytes'], 'sha256': row['sha256']}
assessment = json.loads((OUT / 'evidence-assessment.json').read_bytes())
assert assessment['result'] == 'CONSISTENT_FIXED_GOTO_TIMEOUT_CALLBACK_TYPEERROR_AND_PARTIAL_RELEASE_ONLY'
assert len(assessment['held_records']) == 4 and assessment['all_four_stage_streams_verified']
actual = json.loads((ACTUAL / 'actual-result.json').read_bytes())
write('input-preservation.json', {'schema': 'A24MinimumBodyIndependentPreservation/v1', 'at_utc': STAMP,
    'result': 'PASS_RAW_PRESERVATION', 'root_raw_inputs': 313, 'final_delivery_members': 28,
    'candidate_dependencies_verified_at_intake': 136, 'private_snapshots': 27,
    'all_raw_size_sha256_git_blob_checks': True, 'private_snapshot_checks': True,
    'old_actual_manifest_unchanged': True, 'input_product_or_old_evidence_changes': 0,
    'active_author_or_original_private_paths_read': False,
    'root_historical_32950_member_diff': 'FIXED_COORDINATOR_EVIDENCE_NOT_REPEATED'})
write('release.json', {'schema': 'A24MinimumBodyIndependentStaticRelease/v1', 'released': True, 'at_utc': STAMP,
    'scope': 'Own metadata/record-consistency helpers only; actual context release remains unproven',
    'intake_assessment_helper': 'COMPLETED_EXIT_0', 'sealing_helper': 'Exits after manifest verification/hash output',
    'retained_reviewer_helpers': 0, 'real_resources_acquired_by_reviewer': 0,
    'product_suite_native_model_browser_profile_lock_config_credentials_network_calls': 0,
    'upload_save_reopen_or_activation': 0, 'actual_held_resource_release': 'FOUR_EXACT_RECORDS_ONLY',
    'actual_full_context_release': 'UNPROVEN_CONTEXT_CLOSE_FALSE',
    'new_minimum_body_remaining': 0, 'earlier_current_body_remaining': 0, 'older_readonly_remaining': [0, 0],
    'new_retry_or_authority': False, 'actual_save': 'NOT_RUN', 'actual_independent_readback': 'NOT_RUN'})
write('independent-result.json', {
    'schema': 'A24MinimumBodyFixedActualIndependentReview/v1',
    'result': 'ACCEPTED_FIXED_GOTO_TIMEOUT_WITH_OBSERVED_CALLBACK_TYPEERROR_AND_PARTIAL_OWN_RELEASE_EVIDENCE_ONLY',
    'accepted_scope': 'FROZEN_ENTRY_FAILURE_FINITE_STDERR_AND_FOUR_HELD_PROCESS_JOB_HANDLE_RELEASE_RECORDS_ONLY',
    'at_utc': STAMP, 'reviewer_thread_id': '01a15cf8-68e0-7b63-91a3-657a567b344c',
    'coordinator_thread_id': '01a15dfa-9556-7812-9ed5-1b3bce53555e', 'same_A24_stage': True,
    'task_sha256': '6978777c4c588ca9d02a0b0963bfa17206163e35412c58b94032ab5251822989',
    'base_code_final': '1be0a94b71ef9b200e4941ad4488c98280f8cba8',
    'actual_final': '23d6743a1f9540016af5581dcc0d587a052cf309',
    'candidate_sha256': 'e4ca6b3b6f90fffbf9a67866d977a70db08d99a6496c307ce113a839f475b0cf',
    'final_delivery_manifest_sha256': 'f81a1eade0a0487f3b8795d07402d3b526118915c3c91f8842a403bd20836c12',
    'actual_result_sha256': info(ACTUAL / 'actual-result.json')['sha256'],
    'root_input_manifest_sha256': '6812bb2a2c5ea2dc3c70d866b2693a1f8eef33bcec379bee16d601daf75e1e73',
    'inputs_verified': {'raw': 313, 'final_actual_members': 28, 'dependencies': 136, 'private_snapshots': 27},
    'authority': dict(assessment['authority'], run_id=actual['run_id'], attempt_count=1,
        conditional_save_authorized=False, independent_reopen_authorized=False),
    'failure': {'worker_first_error': assessment['worker_first_error'],
        'observed_step': 'ORIGINAL_PAGE_GOTO_DOMCONTENTLOADED',
        'goto_elapsed_ms': 45031.0, 'goto_timeout_ms': 45000,
        'bootstrap_steps': assessment['bootstrap_steps'], 'navigation': assessment['navigation'],
        'callback_error': assessment['stderr_safe_facts'],
        'callback_to_goto_timeout_to_context_close_full_causal_chain': 'NOT_FULLY_PROVEN',
        'root_cause': 'UNKNOWN_NOT_FULLY_PROVEN', 'main_document_HTTP': 'UNKNOWN_NULL_NOT_ZERO',
        'actual_request_count': 'NOT_RECONSTRUCTED_FROM_MISSING_EVENTS'},
    'successors': {k: 'NOT_RUN' for k in ['session_completion', 'viewer_admission', 'book', 'directory',
        'full_frames', 'natural_export', 'signature', 'upload', 'commit', 'refresh', 'independent_reopen']},
    'current_body_source_schema_identity_savepage_completeness': 'UNPROVEN_NO_NEW_FACTS',
    'release_disposition': {'full_context_runtime_release': 'UNPROVEN_CONTEXT_CLOSE_FALSE',
        'worker_release': assessment['worker_release'], 'held_records': assessment['held_records'],
        'accepted_identity_exits_jobs_handles': 4, 'outer_holder_proves_launcher_exit': True,
        'outer_supervisor_own_OS_identity': 'NOT_SELF_CERTIFIED_UNPROVEN',
        'preopen_occupancy_zero_is_post_failure_sweep': False},
    'stream_provenance': {'all_eight_stage_stream_originals_verified': True,
        'outer_launcher_duplicate_stream_refs_verified': 2,
        'worker_stderr_original': {'bytes': 1027, 'sha256': '4705a16315a41a311c7de3faa45dfd96cde2afe17c32d5df2fd9549b5301deb4',
            'raw_content_exported': False},
        'reported_tool_exit1': 'AUTHOR_TRANSCRIPTION_RAW_TOOL_RESULT_NOT_SUPPLIED',
        'held_stage_exits': {'launcher': 2, 'product': 2, 'worker': 2, 'occupancy': 0},
        'historical_missing_1017_byte_stderr_reconstructed': False},
    'metadata_limits': {'profile_or_lock_changed_false': 'NO_DIRECT_MANUAL_RESET_EDIT_LOCK_OR_CLAIM_CLEARING_OUTSIDE_AUTHORIZED_LAUNCH',
        'browser_persistent_profile_unchanged': 'NOT_INSPECTED_NOT_CLAIMED',
        'post_failure_profile_or_lock_or_process_probe': 'NOT_RUN'},
    'budget': {'this_round_spent': 1, 'this_round_remaining': 0, 'earlier_current_body_remaining': 0,
        'older_readonly_remaining': [0, 0], 'retry_extension_claim_clear_profile_mutation': False},
    'prior_and_later_work': {'minimum_gate_offline_acceptance': 'UNCHANGED',
        'model_corrected_content_acceptance': 'UNCHANGED_NOT_REVIEWED_AGAIN',
        'later_callback_candidate': 'OUTSIDE_THIS_ACTUAL_REVIEW_NOT_AWAITED_OR_ACCEPTED',
        'new_stage_or_chat': False},
    'reviewer_activity': {'mode': 'STATIC_ONLY', 'helpers': 'stdlib metadata/data consistency',
        'product_tests_old_suites_model_native_browser_profile_network_actual_runs': 0,
        'initial_control_or_helper_failures': 0},
    'limits': {'write_eligible': False, 'production_ready': False, 'actual_save': 'NOT_RUN',
        'actual_independent_platform_readback': 'NOT_RUN', 'new_authority': False, 'full_release_claimed': False},
    'artifacts': {name: info(OUT / name) for name in ['report.md', 'input-raw-manifest.json', 'actual-input-manifest.json',
        'intake-result.json', 'evidence-assessment.json', 'input-preservation.json', 'release.json']}})
members = [dict(path=p.relative_to(OUT).as_posix(), **info(p)) for p in sorted(OUT.rglob('*'))
    if p.is_file() and p.name != 'output-manifest.json']
write('output-manifest.json', {'schema': 'A24MinimumBodyIndependentOutputManifest/v1',
    'self_excluded': True, 'member_count': len(members), 'members': members})
for row in members:
    assert info(OUT / row['path']) == {'bytes': row['bytes'], 'sha256': row['sha256']}
assert {r['path'] for r in members} == {p.relative_to(OUT).as_posix() for p in OUT.rglob('*')
    if p.is_file() and p.name != 'output-manifest.json'}
print(json.dumps({'result': 'ACCEPTED_FIXED_GOTO_TIMEOUT_WITH_OBSERVED_CALLBACK_TYPEERROR_AND_PARTIAL_OWN_RELEASE_EVIDENCE_ONLY',
    'inputs_preserved': 313, 'private_snapshots_preserved': 27, 'output_members_excluding_manifest': len(members),
    'machine_sha256': info(OUT / 'independent-result.json')['sha256'],
    'output_manifest_sha256': info(OUT / 'output-manifest.json')['sha256'],
    'release_sha256': info(OUT / 'release.json')['sha256'], 'full_release': 'UNPROVEN_CONTEXT_CLOSE_FALSE'}))
