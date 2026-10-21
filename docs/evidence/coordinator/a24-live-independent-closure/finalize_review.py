"""Final report sealing and original-input readback only; no product imports."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


checks = load(OUT / 'static-checks.json')
assert checks['result'] == 'PASS_BOUNDED_FIXED_EVIDENCE_CHECKS'
inputs = load(OUT / 'root-input-manifest.json')
for row in inputs['members']:
    raw = (ROOT / row['path']).read_bytes()
    assert len(raw) == row['size'] and sha(raw) == row['sha256'], row['path']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest() == row['blob']
assert len(inputs['members']) == 70
input_names = {row['path'] for row in inputs['members']}
output_prefix = OUT.relative_to(ROOT).as_posix() + '/'
extras = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()
    and p.relative_to(ROOT).as_posix() not in input_names
    and not p.relative_to(ROOT).as_posix().startswith(output_prefix)]
assert not extras, extras
write('input-preservation.json', {'result': 'PASS_ALL_70_ORIGINAL_INPUT_BYTES_UNCHANGED',
    'size_sha256_git_blob_verified': 70, 'new_files_outside_allowed_output': extras,
    'product_changes': 0, 'original_failure_or_budget_mutation': 0})
now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat()
result = 'ACCEPTED_FIXED_PARTIAL_VIEWER_BOOK_EMPTY_FAILURE_AND_OWN_RELEASE_ONLY'
machine = {
    'task': 'A24', 'result': result,
    'accepted_scope': 'FIXED_ACTUAL_FINITE_VIEWER_ADMISSION_BOOK_QUERY_FAILURE_AND_PROVEN_OWN_RELEASE_ONLY',
    'reviewer_thread_id': '01a15cf8-68e0-7b63-91a3-657a567b344c',
    'executor_thread_id': '01a15cf8-0c63-70d3-b374-ce85e6f29fd7',
    'review_workflow': '1cbc90e6d002f8cd353fda41a5bf56091292aa73',
    'actual_final': 'a1250758d0fc14e8c7d5c827ece2c207a4d99aac',
    'product_commit': checks['product'], 'candidate_manifest_sha256': checks['candidate_sha256'],
    'input_manifest_sha256': sha((OUT / 'root-input-manifest.json').read_bytes()),
    'input_members_verified_and_preserved': 70, 'candidate_dependencies': 37, 'delivery_members': 31,
    'raw_copy_members_verified': 12, 'window_utc': checks['window'],
    'finite_viewer_admission_accepted': True, 'account_identity': 'NOT_OBSERVED',
    'book_identity_confirmed': False, 'book_http_status': 200, 'book_business_code': 0,
    'book_contract': checks['book_query_facts']['book_contract'], 'book_total_value': 'UNKNOWN_NOT_PROJECTED',
    'first_failure': 'BOOK_TARGET_ABSENT', 'downstream_NOT_RUN': checks['downstream_NOT_RUN'],
    'sources': 0, 'body_schema': 'UNKNOWN', 'source_readiness': 'UNPROVEN',
    'global_book_absence_role_permission_filter_or_old_A23_cause': 'UNKNOWN_NOT_INFERRED',
    'audit_event_count': 16, 'audit_events_equal_HTTP_requests': False,
    'auxiliary_HTTP_send_total': 'UNKNOWN', 'version_HTTP_success': 'UNKNOWN', 'DNS_TCP_TLS_activity': 'UNKNOWN',
    'owned_release_accepted': {'held_processes': checks['held_processes'], 'jobs_final_zero_closed': 2,
        'context_runtime_closed': True, 'errors': [], 'pending_callbacks': 0},
    'exits': checks['exits'],
    'limitations': {'launcher_own_OS_creation_identity': 'UNKNOWN',
        'product_stdout_original': 'UNAVAILABLE_COUNT90_DIGEST_ONLY',
        'outer_stdout_original': '135_BYTES_VERIFIED', 'stderr_original': 'NOT_RETAINED_PUBLICLY_COUNT0_DIGEST_ONLY',
        'timing_differences': checks['timing_records'],
        'prior_preflight_note_corrected_without_rewrite_or_rerun': checks['prior_preflight_vocabulary_note']},
    'live_used': 1, 'live_remaining': 0, 'retry_count': 0,
    'old_activation_output_claims_closed': True, 'new_live_or_write_authorized_by_review': False,
    'production_ready': False, 'write_eligible': False, 'save_or_refresh_or_reopen_proven': False,
    'current_reviewer_suites_product_imports_launchers_real_resources': 0,
    'next_action': 'Root may continue offline same-A24 correction with a separately fixed query scope and own new budget; no automatic retry or activation.',
    'report': 'report.md', 'static_control_records': 'static-checks.json',
    'input_preservation': 'input-preservation.json', 'released_at_china': now
}
write('independent-result.json', machine)
write('release.json', {'task': 'A24', 'state': 'RELEASED_STATIC_ACTUAL_REVIEW_COMPLETE',
    'result': result, 'reviewer_thread_id': machine['reviewer_thread_id'],
    'actual_final': machine['actual_final'], 'report_sha256': sha((OUT / 'report.md').read_bytes()),
    'machine_sha256': sha((OUT / 'independent-result.json').read_bytes()),
    'suite_product_import_launcher_browser_network_profile_credentials_native_occupancy': 0,
    'author_active_directory_reads': 0, 'root_or_product_edits': 0,
    'new_live_or_write_activations': 0, 'external_messages_pushes': 0,
    'retained_processes_sessions_handles_waiting_helpers': [],
    'release_basis': 'Only synchronous standard-library metadata helpers used; no product or real resource created',
    'old_live_used': 1, 'old_live_remaining': 0, 'old_claims_and_failures': 'PRESERVED', 'released_at_china': now})
members = []
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw = path.read_bytes()
        members.append({'path': path.relative_to(OUT).as_posix(), 'size': len(raw), 'sha256': sha(raw)})
write('manifest.json', {'schema': 'A24-independent-live-review/v1', 'task': 'A24',
    'actual_final': machine['actual_final'], 'members': members,
    'self_inclusion': 'EXCLUDED_SELF_HASH_RETURNED_EXTERNALLY', 'state': 'SEALED_RELEASED'})
for row in load(OUT / 'manifest.json')['members']:
    raw = (OUT / row['path']).read_bytes()
    assert len(raw) == row['size'] and sha(raw) == row['sha256']
assert {p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file()} == {
    row['path'] for row in members} | {'manifest.json'}
print(json.dumps({'result': result, 'inputs_unchanged': 70, 'manifest_members': len(members),
    'report_sha256': sha((OUT / 'report.md').read_bytes()),
    'machine_sha256': sha((OUT / 'independent-result.json').read_bytes()),
    'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()),
    'release_sha256': sha((OUT / 'release.json').read_bytes()), 'release': 'COMPLETE'}))
