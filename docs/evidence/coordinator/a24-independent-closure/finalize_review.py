"""Seal independent review metadata; never imports or runs frozen product."""
import ast
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
AUTHOR = ROOT / 'docs/evidence/A24/current-contract'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write_json(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


input_manifest = load(OUT / 'root-input-manifest.json')
checked = []
for row in input_manifest['members']:
    raw = (ROOT / row['path']).read_bytes()
    assert len(raw) == row['size'] and sha(raw) == row['sha256'], row['path']
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    assert blob == row['blob'], row['path']
    checked.append(row['path'])
assert len(checked) == 111
input_paths = set(checked)
output_relative = OUT.relative_to(ROOT).as_posix() + '/'
extra = [file.relative_to(ROOT).as_posix() for file in ROOT.rglob('*') if file.is_file()
    and file.relative_to(ROOT).as_posix() not in input_paths
    and not file.relative_to(ROOT).as_posix().startswith(output_relative)]
assert not extra, extra
write_json('input-preservation.json', {
    'result': 'PASS_111_ORIGINAL_INPUT_BYTES_UNCHANGED', 'checked_count': 111,
    'sha256_size_git_blob_rechecked': True, 'new_files_outside_allowed_output': extra,
    'input_manifest_sha256': sha((OUT / 'root-input-manifest.json').read_bytes()),
    'author_run01_and_raw_run01_distinct_and_preserved': True,
    'product_or_frozen_runner_fixture_edits': 0
})

suite = load(OUT / 'suite-runs/run01/result.json')
controls = load(OUT / 'control-runs/run01/result.json')
assert suite['success'] and suite['tests_run'] == 21 and suite['failures'] == suite['errors'] == 0
assert controls['success'] and controls['tests_run'] == 4 and controls['failures'] == controls['errors'] == 0
binding_record = next(row for row in controls['records'] if row['group'] == 'complete_typed_bindings')
scope = binding_record['real_scope']
assert len(scope) == 66 and binding_record['rejected_mutations'] == 396
for name in ('activation', 'decision', 'independent-report'):
    template = load(AUTHOR / (name + '-template-NONEXECUTABLE.json'))
    for field, expected in scope.items():
        assert type(template.get(field)) is type(expected) and template[field] == expected, (name, field)

tree = ast.parse((ROOT / 'tools/a16_current_state_probe.py').read_text(encoding='utf-8'))
stop_vocabulary = set()
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'SAFE_STOP_CODES'
            for target in node.targets):
        stop_vocabulary = set(ast.literal_eval(node.value.args[0]))
new_branch_codes = ('BOOK_DATA_CONTAINER_REJECTED', 'BOOK_LIST_CONTAINER_REJECTED',
    'BOOK_LIST_ITEM_SCHEMA_REJECTED', 'BOOK_TARGET_ABSENT', 'BOOK_TARGET_CONFLICT',
    'BOOK_TITLE_MISSING', 'BUSINESS_RESPONSE_JSON_REJECTED')
unmapped = [code for code in new_branch_codes if code not in stop_vocabulary]
limitations = [
    'Actual current authentication/book/source/visible/save-page mapping not tested; static/fake evidence is not current platform contract.',
    'Top-level safe_error may map new parser stop codes to UNKNOWN; finite HTTP/shape/canonical branch or INVALID_JSON evidence and correct stop remain. Nonblocking reporting limitation under dispatch.',
    'Inventory PARTIAL; all-old-content preservation, exact current question/wire/upload/receipt and PLATFORM first-save implementation remain unproved or disabled.',
    'Five first-save-readiness hashes are checkout representations, not 37 raw candidate dependency hashes. No first-save module acceptance; later wiring uses raw Git SHA.',
    'Historical author first test/helper/packaging-order failures, intermediate commit and UNKNOWN git-add exit preserved; no rerun to fill old NOT_RUN.',
    'Initial manifest location lookup failed in isolation; exact root manifest path and SHA then verified. No product action on locator failure.',
    'Whole-tree old-member preservation relies on supplied root mechanical verification and frozen reports; not a new full regression or full-tree Git scan.'
]
write_json('static-review.json', {
    'result': 'PASS_LIMITED_CHANGED_BEHAVIOR_REVIEW_WITH_RETAINED_LIMITS',
    'changed_old_paths': load(AUTHOR / 'product-preservation.json')['allowed_modified_old_paths'],
    'preservation_basis': 'Root mechanical 32176/30920 verification plus frozen raw records; no historic suites rerun',
    'candidate_dependencies_independently_verified': 37,
    'all_three_templates_typed_scope_fields': 66,
    'request_plan': scope['book_request_plan'],
    'no_book_picker_or_mapping_UI_actions': True,
    'source_mapping': scope['mapping_semantics'], 'save_page_mapping': scope['save_page_mapping'],
    'parser_stop_codes_absent_from_top_level_vocabulary': unmapped,
    'finite_original_branch_retained_and_stop_correct': True,
    'limits': limitations
})
now = datetime.now(timezone.utc)
machine = dict(scope)
machine.update({
    'result': 'ACCEPTED_OFFLINE_ONLY', 'accepted_scope': 'BOUNDED_READONLY_PREFLIGHT',
    'reviewer_thread_id': '01a15cf8-68e0-7b63-91a3-657a567b344c',
    'base_commit': '454c6ff4a89580e6209b4c45fd6bc74a5e603d83',
    'product_commit': 'eb75fad5ca56daa117929dd1377d2157f2340388',
    'final_commit': '3d53a0b670c04cf84387cd77d69b0a9571741328',
    'review_dispatch_workflow': 'aafc87ac26a67d01d1cf7d814f1fb7262f74a4dc',
    'scope_member_count': 66, 'scope_checked_against_templates': 3,
    'input_manifest_sha256': 'e13ed9bf40a0fb9a9146ca61eb4657f0d0d501ac728465db99ff6fd4446950cd',
    'input_members_verified_and_preserved': 111, 'candidate_dependency_count': 37,
    'delivery_member_count': 98,
    'new_suite': {'tests': 21, 'pass': 21, 'fail': 0, 'error': 0, 'duration_ms': suite['duration_ms'], 'exit_code_observed': 0},
    'independent_controls': {'groups': 4, 'pass': 4, 'fail': 0, 'error': 0,
        'duration_ms': controls['duration_ms'], 'exit_code_observed': 0, 'typed_mutations_rejected': 396},
    'evidence': {'report': 'report.md', 'suite': 'suite-runs/run01/result.json',
        'controls': 'control-runs/run01/result.json', 'intake': 'intake-result.json',
        'input_preservation': 'input-preservation.json', 'static_review': 'static-review.json'},
    'limitations': limitations, 'material_blocking_findings': [],
    'live_activated': False, 'write_activated': False, 'actual_platform_tests': 'NOT_RUN',
    'production_ready': False, 'write_eligible': False,
    'activation_authority': 'ROOT_COORDINATOR_EXACT_BINDING_ONLY',
    'next_dependency': 'Root accepts and binds existing standing readonly TLS permission to this exact candidate and own new bounded activation; same A24 chats later continue first-save candidate and separately budgeted independent reopen.',
    'reviewed_at_utc': now.isoformat(), 'reviewed_at_china': now.astimezone(timezone(timedelta(hours=8))).isoformat()
})
for field, expected in scope.items():
    assert type(machine[field]) is type(expected) and machine[field] == expected
assert machine['business_write_limit'] == machine['sample_limit'] == 0
write_json('independent-result.json', machine)
write_json('release.json', {
    'task': 'A24', 'state': 'RELEASED_OFFLINE_INDEPENDENT_PREFLIGHT_COMPLETE',
    'result': machine['result'], 'accepted_scope': machine['accepted_scope'],
    'reviewer_thread_id': machine['reviewer_thread_id'],
    'candidate_manifest_sha256': machine['candidate_manifest_sha256'],
    'report_sha256': sha((OUT / 'report.md').read_bytes()),
    'machine_report_sha256': sha((OUT / 'independent-result.json').read_bytes()),
    'offline_new_suite_invocations': 1, 'offline_independent_control_invocations': 1,
    'frozen_imports': 'Only inside offline test guards; no product entrypoint/launcher invoked',
    'old_suites_or_author_packaging_helpers_run': 0,
    'real_browser_network_profile_native_occupancy_credentials_login_write_upload_OCR': 0,
    'product_launcher_or_product_children': 0, 'decision_activation_claim_created': 0,
    'author_active_directory_or_output_reads': 0, 'root_or_product_edits': 0,
    'external_messages_or_pushes': 0, 'retained_helpers_processes_sessions_or_handles': [],
    'waiting_processes': 0, 'release_basis': 'No real product resources created; synchronous test commands observed exit0; no detached helper started',
    'old_failures_unknowns_and_spent_budgets': 'PRESERVED_NOT_RESET_NOT_RERUN',
    'environment': {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform()},
    'released_at_china': now.astimezone(timezone(timedelta(hours=8))).isoformat()
})

members = []
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw = path.read_bytes()
        members.append({'path': path.relative_to(OUT).as_posix(), 'size': len(raw), 'sha256': sha(raw)})
write_json('manifest.json', {
    'schema': 'A24-independent-current-contract-review/v1', 'task': 'A24',
    'product_commit': machine['product_commit'], 'final_commit': machine['final_commit'],
    'candidate_manifest_sha256': machine['candidate_manifest_sha256'], 'members': members,
    'self_inclusion': 'EXCLUDED_SELF_SHA256_RETURNED_EXTERNALLY',
    'status': 'SEALED_RELEASED_OFFLINE_ONLY'
})
sealed = load(OUT / 'manifest.json')
for row in sealed['members']:
    raw = (OUT / row['path']).read_bytes()
    assert len(raw) == row['size'] and sha(raw) == row['sha256'], row['path']
actual = {p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file()}
assert actual == {m['path'] for m in sealed['members']} | {'manifest.json'}
print(json.dumps({'result': machine['result'], 'accepted_scope': machine['accepted_scope'],
    'scope_count': 66, 'input_members_unchanged': 111,
    'manifest_member_count': len(members), 'report_sha256': sha((OUT / 'report.md').read_bytes()),
    'machine_sha256': sha((OUT / 'independent-result.json').read_bytes()),
    'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()),
    'release_sha256': sha((OUT / 'release.json').read_bytes()), 'release': 'COMPLETE',
    'all_sealed_members_verified': True}))
