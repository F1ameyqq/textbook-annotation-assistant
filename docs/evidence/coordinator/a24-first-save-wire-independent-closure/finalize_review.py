"""Metadata-only closure; never imports product code or reruns a test."""
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
AUTHOR = ROOT / 'docs/evidence/A24/first-save-wire'
STAMP = datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def info(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': sha(raw)}


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))


def verify(rows, count):
    assert len(rows) == len({r['path'] for r in rows}) == count
    for row in rows:
        path = (ROOT / row['path']).resolve()
        assert ROOT.resolve() in path.parents
        raw = path.read_bytes()
        assert len(raw) == row.get('size', row.get('bytes'))
        assert sha(raw) == row['sha256'], row['path']
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
        assert blob == row.get('blob', row.get('git_blob')), row['path']
        assert row['mode'] == '100644' and row['type'] == 'blob'


root_raw = (OUT / 'root-input-manifest.json').read_bytes()
assert sha(root_raw) == '165b840054cc18ecaaa1cc89f17c3678c3450f26c842509351a4a78d2cba0326'
inputs = json.loads(root_raw)['members']
verify(inputs, 225)
candidate_raw = (AUTHOR / 'candidate-manifest.json').read_bytes()
delivery_raw = (AUTHOR / 'delivery-final-manifest.json').read_bytes()
assert sha(candidate_raw) == 'ac9573448692f313076a02489a9727cb9131040e22a6c55e5797c11a3e01cf19'
assert sha(delivery_raw) == '03366e94a4b7d3672322839f5581a118c26190df3d5274b41bcd73fa0cb382d1'
verify(json.loads(candidate_raw)['dependencies'], 92)
verify(json.loads(delivery_raw)['members'], 144)
assert sha((AUTHOR / 'release.json').read_bytes()) == '178934cfb5a530623d77e39b3c276b0dbd70bf2372172f1177c60ec19f2ccd59'
assert sha((OUT / 'fixed-review-task.md').read_bytes()) == '64ffaf55f42fb64e9fc9d0af66945fdddae071ebe09f082b5f83b60a622c8cdb'

targets = {'apply_current_context', 'reopen_current_context', 'build_guard_binding', 'make_first_save_guard'}
definitions, calls, scanned = [], [], []
for folder in ('src', 'tools'):
    for path in sorted((ROOT / folder).rglob('*.py')):
        tree = ast.parse(path.read_bytes(), filename=str(path))
        relative = path.relative_to(ROOT).as_posix()
        scanned.append(relative)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in targets:
                definitions.append({'path': relative, 'line': node.lineno, 'symbol': node.name})
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else (
                    node.func.attr if isinstance(node.func, ast.Attribute) else None)
                if name in targets:
                    calls.append({'path': relative, 'line': node.lineno, 'symbol': name})
assert len(definitions) == 4 and not calls
write('static-integration-scan.json', {
    'schema': 'A24IndependentStaticIntegrationScan/v1', 'method': 'stdlib AST only; no product import',
    'scope': 'Only supplied frozen src/tools Python files', 'files_scanned': len(scanned),
    'definitions': definitions, 'call_sites': calls, 'dynamic_or_outside_scope_claim': False,
    'existing_owned_readonly_guard': {'path': 'tools/a16_current_state_probe.py', 'line': 756,
                                    'expression': 'CurrentGuard(context, page, ReadPolicy())'},
    'fake_test_boundary': {'path': 'tests/a24_first_save_wire/test_platform.py',
                          'lines': [43, 59, 133, 150], 'owner_is_real': False}})

python = json.loads((OUT / 'python-result.json').read_bytes())
js = json.loads((OUT / 'js-result.json').read_bytes())
control = json.loads((OUT / 'privacy-control-result.json').read_bytes())
assert python['tests'] == 45 and python['passed'] and python['failures'] == python['errors'] == 0
assert js['tests'] == 8 and js['passed'] and len(js['results']) == 8
assert all(row['status'] == 'PASS' for row in js['results'])
assert control['tests'] == control['failures'] == 1 and control['errors'] == 0 and not control['passed']
event = (OUT / 'counterexample-event-000004.json').read_bytes()
assert b'INDEPENDENT_SYNTHETIC_PRIVATE_RECEIPT_SENTINEL' in event
assert json.loads(event)['kind'] == 'BUSINESS_RECEIPT'

input_paths = {r['path'] for r in inputs}
outside = []
for path in ROOT.rglob('*'):
    if path.is_file() and OUT not in path.parents:
        relative = path.relative_to(ROOT).as_posix()
        if relative not in input_paths:
            outside.append(relative)
assert not outside, outside
temporary = OUT / 'temporary'
temporary_files = [p.relative_to(OUT).as_posix() for p in temporary.rglob('*') if p.is_file()] if temporary.exists() else []
assert not temporary_files
write('input-preservation.json', {
    'schema': 'A24IndependentRawInputPreservation/v1', 'checked_at_utc': STAMP,
    'result': 'PASS_RAW_PRESERVATION', 'root_input_members': 225, 'candidate_dependencies': 92,
    'authoritative_delivery_members': 144, 'all_sizes_sha256_git_blobs': True,
    'frozen_mode_type_metadata_verified': True, 'full_historical_root_diff_independently_rerun': False,
    'root_historical_diff': 'FIXED_INPUT_EVIDENCE_ONLY', 'new_files_outside_output': outside,
    'frozen_input_changes': 0, 'product_changes': 0, 'old_evidence_changes': 0})

write('release.json', {
    'schema': 'A24IndependentReviewRelease/v1', 'released_at_utc': STAMP, 'released': True,
    'scope': 'Reviewer-owned local offline test and metadata helpers only',
    'python_suite_helper': {'completed': True, 'exit_code': 0, 'run_count': 1},
    'node_vm_helper': {'completed': True, 'exit_code': 0, 'run_count': 1},
    'independent_control_helper': {'completed': True, 'exit_code': 1, 'run_count': 1},
    'metadata_helpers': 'FINISHED; failures retained; closure process exits after printing hashes',
    'test_temporary_files_remaining': temporary_files, 'retained_helpers': 0,
    'real_browser_context_native_runtime_job_acquisitions': 0,
    'actual_profile_home_or_credentials_access': 0, 'real_network_upload_save_calls': 0,
    'release_limit': 'No real owner resources were acquired; this is not an OS/platform release certificate',
    'old_readonly_original_remaining': 0, 'old_readonly_revised_remaining': 0,
    'actual_save': 'NOT_RUN', 'actual_readback': 'NOT_RUN', 'new_activation': False})

metadata_errors = json.loads((OUT / 'intake-result.json').read_bytes())['metadata_errors_preserved']
metadata_errors += [
    {'tool_chunk': None, 'exit_code': 'NOT_EXPOSED',
     'error': 'Read-only rg lookup of tools/a16_current_state_launcher.py absent from supplied isolation; no product invocation'},
    {'tool_chunk': None, 'exit_code': 'NOT_EXPOSED',
     'error': 'First report apply_patch attempt returned truncated output and created no report; corrected only review metadata'}]
write('independent-result.json', {
    'schema': 'A24FirstSaveWireIndependentReview/v1', 'result': 'REWORK',
    'accepted_scope': 'NONE_FIRST_SAVE_WIRE_PREFLIGHT_NOT_ACCEPTED',
    'reviewer': '01a15cf8-68e0-7b63-91a3-657a567b344c',
    'workflow': 'e0bcd85ec419a69d492aebac918917401fef5926', 'checked_at_utc': STAMP,
    'base': 'dceda09db31487d64654e23dd36ccd3705c740fc',
    'product': '851cf6fce217df8f64a6f3bdeaa99b5e5e2c234d',
    'final': '680bd5f624659f1091db974d5ed30b332ff946dc',
    'task_sha256': '64ffaf55f42fb64e9fc9d0af66945fdddae071ebe09f082b5f83b60a622c8cdb',
    'input_manifest_sha256': sha(root_raw), 'input_members': 225,
    'candidate_manifest_sha256': sha(candidate_raw), 'candidate_dependencies': 92,
    'delivery_manifest_sha256': sha(delivery_raw), 'delivery_members': 144,
    'author_release_sha256': '178934cfb5a530623d77e39b3c276b0dbd70bf2372172f1177c60ec19f2ccd59',
    'tests': {
        'new_python': {'run_count': 1, 'tests': 45, 'pass': 45, 'fail': 0, 'error': 0, 'exit_code': 0,
                       'duration_ms': 7688, 'embedded_unittest_seconds': 7.366},
        'new_js': {'run_count': 1, 'tests': 8, 'pass': 8, 'fail': 0, 'exit_code': 0,
                   'independent_duration': 'NOT_MEASURED'},
        'independent_control': {'run_count': 1, 'tests': 1, 'pass': 0, 'fail': 1, 'error': 0,
                                'exit_code': 1, 'duration_ms': 234, 'embedded_unittest_seconds': 0.247},
        'further_controls': 'NOT_RUN_AFTER_FIRST_MATERIAL_CONTROL_FAILURE', 'old_suites_run': 0,
        'timing_discrepancies': 'Both original fields retained; decomposition UNKNOWN'},
    'blockers': [
        {'id': 'R1', 'priority': 1, 'kind': 'MISSING_EXECUTABLE_OWNER_INTEGRATION',
         'source': ['src/annotation/runtime/live_pilot/runner.py:11-37',
                    'src/annotation/delivery/live_pilot/usense.py:52-58',
                    'src/annotation/delivery/live_pilot/usense.py:98-110',
                    'tools/a16_current_state_probe.py:740-756'],
         'evidence': 'static-integration-scan.json',
         'minimum_fix': 'Existing owned framework entry: raw authority/hash/scope/window/count checks before resources, new guard before online/bootstrap, adapter call, full outer release, designated readonly reopen; small fake owner verification'},
        {'id': 'R2', 'priority': 1, 'kind': 'UNAPPROVED_RESPONSE_AND_QUERY_PERSISTENCE',
         'source': ['src/annotation/runtime/live_pilot/runner.py:75-89',
                    'src/annotation/delivery/live_pilot/usense.py:634-636',
                    'src/annotation/delivery/live_pilot/usense.py:790-807',
                    'src/annotation/delivery/live_pilot/wire.py:381-410'],
         'evidence': ['privacy-control-result.json', 'counterexample-event-000004.json'],
         'observed_layer': 'One synthetic response extra member persisted while normal fake flow succeeded',
         'query_value_branch': 'STATIC_DATA_FLOW_ONLY_NO_ACTUAL_ACCOUNT_ACCESS',
         'minimum_fix': 'Finite approved receipt or UNKNOWN plus hashes before journal; no raw response dump; template/key/hash query provenance; preserve claim/no resend; focused sentinel regression'}],
    'unbound_actual_inputs': ['authoritative whole-book/all-zone export and current field maps',
        'protected account identity field map', 'legal new leaf/end insertion and assigned order semantics',
        'joint role/policy/body/six JPEGs/pixel boxes/newness/source-save-page binding',
        'current receipt/readback/signature/OSS success contract', 'current journal/lock admission',
        'final exact owner bootstrap/UI slots and all budgets', 'new direct upload/save authority'],
    'concentrated_plan': {'status': 'PROPOSED_NOT_AUTHORIZED_OR_EXECUTABLE', 'business_get_excluding_bootstrap': 32,
        'signature_get': 1, 'object_post': 6, 'commit_post': 1, 'refresh_document': 1,
        'original_get': 0, 'bootstrap_ui_budget': 'UNBOUND', 'independent_reopen': 'DISTINCT_OWNED_CONTEXT_REQUIRED'},
    'scope_limits': {'write_eligible': False, 'production_ready': False, 'actual_upload': 'NOT_RUN',
        'actual_save': 'NOT_RUN', 'actual_get': 'NOT_RUN', 'actual_refresh': 'NOT_RUN', 'actual_reopen': 'NOT_RUN',
        'real_resources': 0, 'activation': False, 'old_readonly_original_remaining': 0,
        'old_readonly_revised_remaining': 0, 'earlier_actual_source_acceptance': 'UNCHANGED',
        'model_ocr_or_other_question_types_added_to_rework': False, 'new_stage_or_chat': False},
    'metadata_errors_preserved': metadata_errors,
    'artifacts': {name: info(OUT / name) for name in [
        'report.md', 'python-result.json', 'js-result.json', 'privacy-control-result.json',
        'counterexample-event-000004.json', 'static-integration-scan.json',
        'input-preservation.json', 'release.json']}})

# Last closure checks are metadata only. Manifest excludes itself, avoiding a circular digest.
verify(inputs, 225)
write('closure-check.json', {'schema': 'A24IndependentClosureCheck/v1',
    'inputs_reverified_after_report': 225, 'candidate_reverified': 92, 'delivery_reverified': 144,
    'test_results_read_only_no_rerun': True, 'report_exists': (OUT / 'report.md').is_file(),
    'temporary_files_remaining': 0, 'new_files_outside_allowed_output': [],
    'all_required_outputs_present': True, 'manifest_self_excluded': True})
members = []
for path in sorted(OUT.rglob('*')):
    if path.is_file() and path.name != 'raw-manifest.json':
        members.append(dict(path=path.relative_to(OUT).as_posix(), **info(path)))
write('raw-manifest.json', {'schema': 'A24IndependentRawOutputManifest/v1',
    'self_excluded': True, 'member_count': len(members), 'members': members})
manifest = json.loads((OUT / 'raw-manifest.json').read_bytes())
for member in manifest['members']:
    assert info(OUT / member['path']) == {'bytes': member['bytes'], 'sha256': member['sha256']}
actual_names = {p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name != 'raw-manifest.json'}
assert actual_names == {m['path'] for m in members}
print(json.dumps({'result': 'REWORK', 'inputs_preserved': 225,
    'output_members_excluding_manifest': len(members), 'manifest_verified': True,
    'machine_sha256': info(OUT / 'independent-result.json')['sha256'],
    'manifest_sha256': info(OUT / 'raw-manifest.json')['sha256'],
    'release_sha256': info(OUT / 'release.json')['sha256']}))
