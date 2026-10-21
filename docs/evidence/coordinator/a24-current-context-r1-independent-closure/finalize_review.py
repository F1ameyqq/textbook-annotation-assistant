"""Seal current-context-r1 review from fixed test records; no product import/run."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
AUTHOR = ROOT / 'docs/evidence/A24/revisions/current-context-r1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


inputs = load(OUT / 'root-input-manifest.json')
assert len(inputs['members']) == 120
for row in inputs['members']:
    raw = (ROOT / row['path']).read_bytes()
    assert len(raw) == row['size'] and sha(raw) == row['sha256'], row['path']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest() == row['blob']
input_names = {row['path'] for row in inputs['members']}
output_prefix = OUT.relative_to(ROOT).as_posix() + '/'
extras = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()
    and p.relative_to(ROOT).as_posix() not in input_names
    and not p.relative_to(ROOT).as_posix().startswith(output_prefix)]
assert not extras, extras
write('input-preservation.json', {'result': 'PASS_ALL_120_ORIGINAL_INPUT_BYTES_UNCHANGED',
    'size_sha256_git_blob_rechecked': 120, 'new_files_outside_allowed_output': extras,
    'frozen_source_runner_fixture_evidence_modified': 0})

python = load(OUT / 'python-runs/run01/result.json')
javascript = load(OUT / 'js-runs/run01.json')
binding = load(OUT / 'binding-runs/run01/result.json')
public = load(OUT / 'public-vm-result.json')
assert python['success'] and python['tests_run'] == 28 and python['failures'] == python['errors'] == 0
assert javascript['success'] and javascript['case_count'] == 15 and javascript['node_returncode'] == 0
assert binding['success'] and binding['tests_run'] == 1 and binding['failures'] == binding['errors'] == 0
assert public['result'] == 'PASS' and len(public['cases']) == 3 and public['node_returncode'] == 0
scope_record = binding['records'][0]
scope = scope_record['real_scope']
assert len(scope) == 103 and scope_record['rejected_mutations'] == 618
for name in ('activation', 'decision', 'independent-report'):
    template = load(AUTHOR / (name + '-template-NONEXECUTABLE.json'))
    for field, expected in scope.items():
        assert type(template.get(field)) is type(expected) and template[field] == expected, (name, field)
decision = load(AUTHOR / 'decision-template-NONEXECUTABLE.json')
activation = load(AUTHOR / 'activation-template-NONEXECUTABLE.json')
assert decision['live_authorized'] is False and decision['certificate_exception_authorized'] is False
assert activation['not_before'] is None and activation['expires_at'] is None
assert scope['business_write_limit'] == scope['sample_limit'] == 0

# Inspect output records/logs only, never source fixtures containing synthetic inputs.
logs = [p for folder in ('python-runs', 'js-runs', 'binding-runs') for p in (OUT / folder).rglob('*') if p.is_file()]
logs += [OUT / 'public-vm-stdout.txt', OUT / 'public-vm-stderr.txt', OUT / 'public-vm-result.json']
sentinels = ('SYNTHETIC_CONTEXT_SECRET', 'FAKE_TOKEN_STAYS_IN_PAGE', 'SYNTHETIC_USERNAME_SECRET',
    'SYNTHETIC_PRIVATE_VALUE_MUST_NOT_ESCAPE', 'INDEPENDENT_PRIVATE_THROW_SENTINEL')
for path in logs:
    raw = path.read_bytes()
    assert not any(value.encode('utf-8') in raw for value in sentinels), path.name
write('privacy-and-scope-checks.json', {
    'result': 'PASS_COMPLETE_103_TYPED_SCOPE_AND_FINITE_OUTPUT_PRIVACY',
    'templates_compared': 3, 'typed_deletion_or_change_rejections': 618,
    'result_log_files_checked': len(logs), 'synthetic_runtime_sentinels_checked': len(sentinels),
    'runtime_sentinel_leak_hits': 0, 'template_activation_created': False,
    'public_program_sha256': public['exact_PUBLIC_JSON_sha256'],
    'public_fake_cases': public['cases'], 'real_platform_contract_proven': False
})
limits = [
    'Static frontend compatibility and synthetic passes do not prove current authentication, account/role/permission, book contents, source schema or old empty-query cause.',
    'Unsupported controls/surrogates/overlength/URL-normalization changes stop; no approximation, guessed replacement context or alternate query.',
    'Absent source identity is request binding only; default legacy and resource13/172 are explicitly frontend-derived, not returned server identity or save-page.',
    'Inventory PARTIAL/content UNKNOWN, no legal append/save order or full old-content preservation. Existing first-save sender/receipt and future active author work not accepted here.',
    'Root mechanical whole-tree preservation and fixed unchanged-region comparisons reused without rerunning historical suites or counterexamples.',
    'Old actual round stays used1/remaining0. New revision checkpoint requires root exact binding and activation; no activation or write authority from this review.'
]
now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat()
machine = load(AUTHOR / 'independent-report-template-NONEXECUTABLE.json')
assert machine['result'] == 'NOT_REVIEWED'
machine.update({
    'result': 'ACCEPTED_OFFLINE_ONLY', 'accepted_scope': 'BOUNDED_READONLY_PREFLIGHT',
    'revision': 'current-context-r1', 'reviewer_thread_id': '01a15cf8-68e0-7b63-91a3-657a567b344c',
    'review_dispatch_workflow': 'b93bdf8abc478567694bc17a6e8d37399a19b2bd',
    'base_commit': 'a1250758d0fc14e8c7d5c827ece2c207a4d99aac',
    'product_commit': 'dde5746600df9854c33c5814a8f41ad85b7b4e16',
    'final_commit': '6740d7533ea7b5bf5f322d768e8688826afe5d43',
    'input_manifest_sha256': sha((OUT / 'root-input-manifest.json').read_bytes()),
    'input_members_verified_and_preserved': 120, 'candidate_dependency_count': 42, 'delivery_member_count': 108,
    'scope_member_count': 103, 'scope_templates_compared': 3,
    'python_new_suite': {'tests': 28, 'pass': 28, 'fail': 0, 'errors': 0,
        'duration_ms': python['duration_ms'], 'exit_code_observed': 0},
    'Node_new_VM_suite': {'cases': 15, 'pass': 15, 'duration_ms': javascript['duration_ms'],
        'node_returncode': 0, 'local_fake_interpreter_only': True},
    'independent_binding_control': {'groups': 1, 'pass': 1, 'rejected_mutations': 618,
        'duration_ms': binding['duration_ms'], 'exit_code_observed': 0},
    'independent_public_VM_control': {'cases': 3, 'pass': 3, 'duration_ms': public['duration_ms'],
        'node_returncode': 0, 'no_Authorization_or_credentials_or_storage_access': True},
    'evidence': {'report': 'report.md', 'intake': 'intake-result.json',
        'Python': 'python-runs/run01/result.json', 'Node': 'js-runs/run01.json',
        'bindings': 'binding-runs/run01/result.json', 'public': 'public-vm-result.json',
        'privacy': 'privacy-and-scope-checks.json', 'preservation': 'input-preservation.json'},
    'material_blocking_findings': [], 'limitations': limits,
    'real_browser_network_profile_credentials_user_context_native_occupancy_product_launcher_login_write': 0,
    'local_fake_Node_processes_completed_by_reviewer': 2,
    'live_activated': False, 'write_activated': False, 'production_ready': False, 'write_eligible': False,
    'activation_authority': 'ROOT_COORDINATOR_ONLY_EXACT_CURRENT_REVISION_BINDING',
    'next_action': 'Root verifies and directly binds standing same-kind readonly TLS permission to this distinct revision checkpoint. Same A24 first-save work remains separately frozen/reviewed/authorized before saving.',
    'reviewed_at_china': now
})
for field, expected in scope.items():
    assert type(machine[field]) is type(expected) and machine[field] == expected
write('independent-result.json', machine)
write('release.json', {'task': 'A24', 'revision': 'current-context-r1',
    'state': 'RELEASED_OFFLINE_INDEPENDENT_PREFLIGHT_COMPLETE', 'result': 'ACCEPTED_OFFLINE_ONLY',
    'accepted_scope': 'BOUNDED_READONLY_PREFLIGHT', 'reviewer_thread_id': machine['reviewer_thread_id'],
    'product_commit': machine['product_commit'], 'final_commit': machine['final_commit'],
    'candidate_manifest_sha256': machine['candidate_manifest_sha256'],
    'report_sha256': sha((OUT / 'report.md').read_bytes()),
    'machine_sha256': sha((OUT / 'independent-result.json').read_bytes()),
    'new_Python_suite_invocations': 1, 'new_Node_VM_suite_invocations': 1,
    'independent_binding_groups': 1, 'independent_public_VM_cases': 3,
    'local_fake_Node_processes_completed': 2,
    'old_suites_or_author_packaging_helpers_run': 0,
    'real_browser_network_profile_config_user_context_native_occupancy_product_launcher_login_write_upload_OCR': 0,
    'root_product_or_frozen_input_edits': 0, 'active_author_directory_or_output_reads': 0,
    'new_activation_live_write_claims': 0, 'external_messages_or_pushes': 0,
    'retained_processes_sessions_handles_waiting_helpers': [],
    'release_basis': 'All synchronous test/fake VM commands observed exit0; no real product resource created',
    'old_actual_live_remaining': 0, 'old_failures_and_allocations': 'PRESERVED_NOT_RESET', 'released_at_china': now})
members = []
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw = path.read_bytes()
        members.append({'path': path.relative_to(OUT).as_posix(), 'size': len(raw), 'sha256': sha(raw)})
write('manifest.json', {'schema': 'A24-independent-current-context-r1-review/v1', 'task': 'A24',
    'product_commit': machine['product_commit'], 'final_commit': machine['final_commit'],
    'candidate_manifest_sha256': machine['candidate_manifest_sha256'], 'members': members,
    'self_inclusion': 'EXCLUDED_SELF_SHA256_RETURNED_EXTERNALLY', 'state': 'SEALED_RELEASED'})
for row in load(OUT / 'manifest.json')['members']:
    raw = (OUT / row['path']).read_bytes()
    assert len(raw) == row['size'] and sha(raw) == row['sha256'], row['path']
assert {p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file()} == {
    row['path'] for row in members} | {'manifest.json'}
print(json.dumps({'result': machine['result'], 'accepted_scope': machine['accepted_scope'],
    'scope_fields': 103, 'original_inputs_unchanged': 120, 'manifest_members': len(members),
    'report_sha256': sha((OUT / 'report.md').read_bytes()),
    'machine_sha256': sha((OUT / 'independent-result.json').read_bytes()),
    'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()),
    'release_sha256': sha((OUT / 'release.json').read_bytes()), 'release': 'COMPLETE'}))
