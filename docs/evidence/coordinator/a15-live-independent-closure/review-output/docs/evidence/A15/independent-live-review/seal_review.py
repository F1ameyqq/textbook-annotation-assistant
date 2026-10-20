"""Seal only this independent static review. No suite, product, profile or process calls."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path('D:/1800-worktrees/a15-independent-fixed')
OUT = ROOT / 'docs/evidence/A15/independent-live-review'
LIVE = ROOT / 'docs/evidence/A15/certificate-exception/live-observation-delivery'
OLD = ROOT / 'docs/evidence/A15/independent-preflight'
DECISION = 'ACCEPTED_FAILURE_ARCHIVE_AND_EVIDENCED_OWNED_RELEASE_ONLY'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')

def save(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write(encode(value))

audit = json.loads((OUT / 'fixed-record-audit.json').read_bytes())
inputs = list(audit['raw_members'])
inputs.append({'path': (LIVE / 'delivery-raw-manifest.json').relative_to(ROOT).as_posix(),
               'sha256': audit['author_manifest_sha256']})
assert len(inputs) == 74
for item in inputs:
    assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
old_raw = (OLD / 'manifest.json').read_bytes()
assert sha(old_raw) == audit['original_independent_manifest_sha256']
for item in json.loads(old_raw)['members']:
    assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
assert DECISION in (OUT / 'report.md').read_text(encoding='utf-8')
at = datetime.now(timezone.utc).isoformat()
save('input-preservation.json', {'task': 'A15', 'phase': 'INDEPENDENT_LIVE_STATIC_REVIEW', 'at': at,
 'fixed_author_final': audit['author_final'], 'fixed_raw_members_including_manifest': 74,
 'fixed_inputs_after_review': inputs, 'all_74_fixed_inputs_unchanged': True,
 'original_independent_27_members_and_manifest_unchanged': True,
 'original_independent_manifest_sha256': sha(old_raw),
 'candidate_or_raw_lifecycle_records_or_timestamps_modified': False,
 'author_active_directory_or_actual_local_source_accessed': False})
report = {'task': 'A15', 'phase': 'SINGLE_LIVE_FIXED_RESULT_STATIC_REVIEW', 'at': at,
 'decision': DECISION, 'state': 'STOP_REVIEW_RELEASED',
 'review_thread_id': '01a157fe-5cc9-7d91-8bbe-73b376cbe2a5',
 'coordinator_thread_id': '01a15768-1e2d-7781-b29f-1f7376270216',
 'product_commit': 'bef0204541eedd86e1fab849e8002a83f432cd7b',
 'author_final': audit['author_final'], 'prior_author_final': audit['prior_author_final'],
 'author_manifest_sha256': audit['author_manifest_sha256'],
 'raw_members_verified': 74, 'prior_final_members_preserved_mode_type_blob': 31259,
 'new_members_only_in_live_delivery_subtree': 27, 'frozen_candidate_members_unchanged': 22,
 'old_independent_output_seals_unchanged': True,
 'candidate_manifest_sha256': '78382e0b484ad46ab497217683fa3022440a1f570589f538c3d355670d552652',
 'activation_sha256': audit['activation_sha256'],
 'user_decision_sha256': '36ffcbb42c030192313773b510c69598651b2c2ffe5fb54162c46b8041e40763',
 'proposal_sha256': 'eb6aea7ad9b01ccbcaf7710c9c45d7c5c3a80d6efcef4db857838d204d725656',
 'bound_independent_offline_report_sha256': audit['independent_report_binding_sha256'],
 'activation_and_profile_binding_in_fixed_records_accepted': True,
 'time_checks': audit['time_checks'], 'observed_live_scope': audit['observed_live_scope'],
 'fixed_live_outcome': 'ERROR', 'fixed_live_error': ['NETWORK_GUARD_STOPPED'],
 'first_policy_denial': audit['first_policy_denial'],
 'terminal_guard_stopped_pre_shutdown_and_serialization': True,
 'guard_pending_tasks_at_serialization': 0, 'successors': 'NOT_RUN',
 'audit_event_count': 8, 'audit_categories': audit['audit_categories'],
 'audit_events_are_unique_request_count': False,
 'two_navigation_audit_events_are_not_two_navigation_intents': True,
 'blocked_domain': 'UNKNOWN_NOT_RECORDED', 'blocked_URL': 'UNKNOWN_NOT_RECORDED',
 'blocked_resource_type': 'UNKNOWN_NOT_RECORDED', 'root_cause': 'UNKNOWN',
 'authenticated_viewer': 'NOT_PROVEN', 'login_required': 'NOT_PROVEN',
 'server_identity_by_certificate': 'NOT_PROVEN', 'prior_certificate_defect_cured': 'NOT_PROVEN',
 'evidenced_owned_processes': audit['three_retained_child_identities'],
 'three_process_handles_recorded_closed': True, 'both_owned_jobs_assigned_and_closed': True,
 'owned_job_active_counts_before_final_cleanup': [1, 1], 'owned_job_final_active_counts': [0, 0],
 'individual_identities_of_residual_job_members': 'NOT_RECORDED_NO_INFERENCE',
 'context_closed_and_runtime_stopped': True,
 'launcher_own_OS_exit_identity': 'UNKNOWN_PRESERVED',
 'command_native_exit_code': 2, 'command_exit_code_does_not_replace_launcher_OS_identity': True,
 'all_machine_browser_or_system_processes_released': 'NOT_CLAIMED',
 'A13_wrapper_OS_exit_identity': 'UNKNOWN_PRESERVED', 'A14_TIMING_01_general_guard_accepted': False,
 'report_packaging_error_preserved': audit['report_packaging_event'],
 'report_only_correction_is_an_additional_live_attempt': False,
 'source_capture_archive_hashes_verified': 10,
 'actual_local_source_independently_refreshed': False,
 'accepted_scope': ['This fixed one-attempt failure archive and authority/scope/window binding',
   'Three retained owned child identities and observed exits, three closed process handles',
   'Two assigned owned Jobs with final active0 and closed handles',
   'Recorded context/runtime closure and terminal guard with no pending tasks'],
 'not_accepted_as_proven': ['Authentication or LOGIN_REQUIRED', 'Blocked URL/domain/resource type or root cause',
   'Server identity or certificate remediation', 'Book data/content/save/refreshed readback',
   'Launcher own retained OS exit identity', 'General timeout correctness or system-wide process release'],
 'new_live_used': 1, 'new_live_remaining': 0, 'prior_budgets_restored': False,
 'reviewer_new_suite_runs': 0, 'reviewer_new_live_runs': 0,
 'reviewer_product_imports': 0, 'reviewer_profile_process_native_or_actual_occupancy_access': False,
 'first_question_save_and_refreshed_readback': 'NOT_RUN', 'other_three_cases': 'HOLD',
 'Q22_replayed': False, 'B_messages': 0, 'book_review_or_delivery_submission': 0,
 'A16_processed_by_this_review': False, 'next_dependency': 'Coordinator closure of A15 fixed failure; no A15 rerun.'}
save('report.json', report)
save('reviewer-release.json', {'task': 'A15', 'phase': 'INDEPENDENT_LIVE_STATIC_REVIEW', 'at': at,
 'state': 'RELEASED_NO_LIVE_RESOURCES_CREATED', 'reviewer_suite_runs': 0, 'reviewer_live_runs': 0,
 'product_subprocesses': 0, 'candidate_imports': 0, 'browser_contexts': 0, 'network_attempts': 0,
 'profile_reads': 0, 'native_API_calls': 0, 'process_scans': 0, 'actual_occupancy_checks': 0,
 'other_chat_messages': 0, 'input_or_old_review_output_mutations': 0,
 'preparation_process_scope': 'Own synchronous static audit/report interpreters and three completed Git raw reads; not a zero-process claim.',
 'static_audit_exit_code': 0, 'static_Git_reads': 3, 'all_static_Git_exit_codes': [0, 0, 0],
 'file_handle_scope': 'Own synchronous reads/writes use context managers; no retained product/browser handle created.',
 'reviewer_shell_or_reporter_retained_OS_identity': 'NOT_MEASURED_NOT_CLAIMED',
 'read_tooling_note': 'One early read batch used D:/1800 and returned four missing archive paths; retried only those reads in the approved fixed isolation. This was not a candidate/suite/live run or an input mismatch.',
 'release_claim_for_author': 'Only the fixed recorded scopes listed in report.json; no refreshed process or local-source observation.',
 'next_state': 'STOP_REVIEW_NO_A15_RERUN'})
members = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name != 'manifest.json':
        raw = path.read_bytes()
        members.append({'path': path.relative_to(ROOT).as_posix(), 'size': len(raw), 'sha256': sha(raw)})
save('manifest.json', {'task': 'A15', 'phase': 'INDEPENDENT_LIVE_STATIC_REVIEW', 'decision': DECISION,
 'self_excluded': True, 'fixed_author_final': audit['author_final'],
 'fixed_author_manifest_sha256': audit['author_manifest_sha256'],
 'report_sha256': sha((OUT / 'report.json').read_bytes()),
 'reviewer_suite_runs': 0, 'reviewer_live_runs': 0, 'members': members})
for item in members:
    assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
for item in inputs:
    assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
print(json.dumps({'decision': DECISION, 'report_sha256': sha((OUT / 'report.json').read_bytes()),
 'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()), 'manifest_members': len(members),
 'reviewer_release_sha256': sha((OUT / 'reviewer-release.json').read_bytes()),
 'all_74_inputs_unchanged': True, 'suite_runs': 0, 'live_runs': 0,
 'A15_live_remaining': 0}))
