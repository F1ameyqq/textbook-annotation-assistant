"""Minimum-delta static mapping and seal. No product/test execution."""
import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
PRIOR = Path('D:/1800-worktrees/a24-current-body-actual-review')
DELIVERY = ROOT / 'docs/evidence/A24/first-save-minimum-gate'
STAMP = datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def info(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': sha(raw)}


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, indent=2) + '\n').encode('utf-8'))


manifest = json.loads((OUT / 'input-raw-manifest.json').read_bytes())
assert info(OUT / 'input-raw-manifest.json')['sha256'] == '4fe96dd755f734fca61fe04f8ab93fd50879b62f038b10a00bedc89985a3d6bd'
for row in manifest['members']:
    raw = (ROOT / row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['blob']
for row in manifest['private_references']:
    assert info(Path(row['snapshot_path'])) == {'bytes': row['bytes'], 'sha256': row['sha256']}
suite = json.loads((OUT / 'python-result.json').read_bytes())
control = json.loads((OUT / 'independent-control-result.json').read_bytes())
assert suite['tests'] == 9 and suite['passed'] and suite['failures'] == suite['errors'] == 0
assert control['tests'] == 2 and control['passed'] and control['failures'] == control['errors'] == 0
assert not [p for p in (OUT / 'temporary').rglob('*') if p.is_file()]
delta_files = []
for filename in ('authority.py', 'owner.py'):
    relative = 'src/annotation/runtime/live_pilot/' + filename
    before, after = (PRIOR / relative).read_bytes(), (ROOT / relative).read_bytes()
    delta_files.append({'path': relative, 'prior_raw_sha256': sha(before), 'candidate_raw_sha256': sha(after),
        'unified_diff': ''.join(difflib.unified_diff(before.decode('utf-8').splitlines(True),
            after.decode('utf-8').splitlines(True), fromfile='fixed-prior/' + filename, tofile='candidate/' + filename))})
write('static-delta.json', {'schema': 'A24MinimumGateIndependentStaticDelta/v1',
    'method': 'Exact prior actual raw isolation versus candidate bytes, no Git normalization',
    'files': delta_files, 'plan_scope_unchanged': '87324f21901723a4282afc9d06bea243b5bdba72ac25ea7f0c1eea3c018493de',
    'only_authority_and_owner_product_changes': 'Root fixed 32799-member comparison; directly inspected these two diffs',
    'request_listener_allowlist_retry_timeout_expansion_found': False,
    'historical_timeout_root_cause_repair_proven': False})
write('gate-scope-map.json', {'schema': 'A24MinimumGateIndependentScopeMap/v1',
    'pre_resource_gate': ['verify_authority returns Authority.check', 'Authority.check seal/input/window checks',
        'Authority.check validate_predecessor before stage/backend/framework/native/profile/context',
        'acquire_current_schema independently requires AUTHOR_SAVE before CurrentPageIO'],
    'reopen_predecessor': {
        'role': 'INDEPENDENT_REOPEN only; AUTHOR_SAVE bypasses predecessor as intended',
        'profile': 'dict, mode matches OBSERVED/SYNTHETIC; qualified body_admission',
        'author_result': 'known mode-specific success plus frames PASS/content VERIFIED/question identity',
        'frozen_inputs': 'exact plan/baseline/receipt/author_observation/release dict membership',
        'plan': 'input_hash(request), baseline equality, profile hash and payload dict',
        'receipt': 'exact ten fields, integer code/order, inserted true, stable id, six unique payload rect ids, response/payload hash and mode',
        'refresh_release_chain': 'refresh phase/mode, author session, profile/plan/receipt/last observation hashes',
        'external_certificate': 'path under evidence root, actual bytes/SHA, A24OwnedRelease/v1 coordinator issuer/mode/status',
        'subject': 'exact subject release hash and author result hash',
        'release_flags': 'context/runtime/held identities/jobs/launcher all identity True',
        'pending': 'type is int and exactly zero', 'raw_refs': 'nonempty list; each path/bytes/SHA verified under root',
        'unknown': 'cannot return capability or enter author acquisition; reconciliation remains separate'},
    'entry_evidence': ['same goto target/wait/45000ms, begin/end on success and exception',
        'finite bootstrap STARTED/DONE states', 'existing safe passive navigation snapshot on worker exit',
        'cleanup errors finite named steps', 'normal communicate return raw stdout/stderr exclusive private files before decoding/rejection'],
    'scope_limits': ['No new request/listener/retry/timeout/source expansion',
        'communicate exception/timeout full bytes not guaranteed', 'existing context-close false remains unproved',
        'historical missing navigation/stderr cannot be reconstructed', 'outer launcher own exit still separately certified'],
    'current_author_preflight': {'role': 'AUTHOR_SAVE', 'schema_profile': None,
        'body_admission': 'CURRENT_SCHEMA_UNBOUND', 'contexts': 1, 'initial_navigation': 1,
        'business_GET': ['book official same-page query once', 'directory once', 'full frames once', 'natural export once'],
        'maximum_seconds': 900, 'signature_upload_commit_refresh_reopen': 0,
        'terminal_after_successful_acquisition': 'PREWRITE_BLOCKED_NO_EFFECT', 'self_promotion': False,
        'new_root_authority_required_before_actual_use': True}})
write('input-preservation.json', {'schema': 'A24MinimumGateIndependentPreservation/v1', 'at_utc': STAMP,
    'result': 'PASS_RAW_PRESERVATION', 'root_members': 284, 'dependencies_verified_at_intake': 136,
    'delivery_members_verified_at_intake': 283, 'private_snapshots': 17,
    'raw_size_sha256_git_blob_checks': True, 'input_changes': 0, 'product_changes': 0,
    'active_author_or_original_private_paths_read': False, 'old_evidence_changed': False,
    'root_historical_diff_repeated': False, 'test_temporary_files_remaining': 0})
write('release.json', {'schema': 'A24MinimumGateIndependentRelease/v1', 'released': True, 'at_utc': STAMP,
    'scope': 'Own local offline review helpers only', 'new_suite': {'runs': 1, 'tests': 9, 'exit': 0},
    'independent_controls': {'runs': 1, 'tests': 2, 'exit': 0}, 'old_suite_or_historical_failed_entry_runs': 0,
    'metadata_helpers': 'Completed; final sealing process exits after printing hashes',
    'retained_helpers': 0, 'synthetic_temporary_files_remaining': 0,
    'real_native_browser_context_profile_model_runtime_jobs_acquired': 0,
    'network_credentials_config_model_upload_save_reopen_activation': 0,
    'current_body_round_remaining': 0, 'older_readonly_remaining': [0, 0],
    'actual_save': 'NOT_RUN', 'actual_independent_platform_readback': 'NOT_RUN',
    'historical_context_closed_false_and_missing_stderr': 'PRESERVED_NOT_REPAIRED_BY_REVIEW'})
write('independent-result.json', {
    'schema': 'A24MinimumGateIndependentReview/v1', 'result': 'ACCEPTED_OFFLINE_ONLY',
    'accepted_scope': 'BOUNDED_MINIMUM_PREDECESSOR_GATE_AND_ENTRY_EVIDENCE_DELTA',
    'current_prewrite_accepted_scope': 'BOUNDED_AUTHOR_UNBOUND_FOUR_GET_PREFLIGHT',
    'at_utc': STAMP, 'reviewer': '01a15cf8-68e0-7b63-91a3-657a567b344c', 'same_A24_stage': True,
    'task_sha256': '9052fe9c1915e1f49c9401b043870d4f18fad0ec98869e3dc232bc6697783346',
    'base': '93649b44f85d218117bc7f27e495dd1d48e8487e',
    'product': 'f529cd890814045689cb0907247d765d7218e215',
    'final': '1be0a94b71ef9b200e4941ad4488c98280f8cba8',
    'candidate_sha256': 'e4ca6b3b6f90fffbf9a67866d977a70db08d99a6496c307ce113a839f475b0cf',
    'delivery_manifest_sha256': 'a56c41e3c59c20d66d348ff9fd7959b556dd2b6089e15f2a7f46f34a6043ea14',
    'root_input_manifest_sha256': '4fe96dd755f734fca61fe04f8ab93fd50879b62f038b10a00bedc89985a3d6bd',
    'inputs_verified': {'raw': 284, 'candidate_dependencies': 136, 'delivery': 283, 'private_snapshots': 17},
    'dispositions': {'R1_R': 'CLOSED_IN_REVIEWED_STATIC_AND_FAKE_LAYER',
        'receipt_query_previous_offline_closure': 'UNCHANGED', 'material_code_blockers_in_delta': [],
        'entry_evidence': 'FINITE_WIRING_ACCEPTED_OFFLINE_ONLY',
        'historical_TimeoutError_root_cause_or_repair': 'UNPROVEN_UNKNOWN_UNCHANGED',
        'conditional_actual_save': 'NOT_QUALIFIED_NOT_ADMITTED',
        'conditional_actual_independent_reopen': 'NO_CURRENT_PREDECESSOR_OR_AUTHORITY_NOT_ADMITTED'},
    'tests': {'new_nine_control_suite': {'runs': 1, 'tests': 9, 'pass': 9, 'fail': 0, 'errors': 0,
            'exit': 0, 'report_duration_ms': 1032, 'embedded_unittest_seconds': 0.355},
        'independent_minimum_controls': {'runs': 1, 'tests': 2, 'pass': 2, 'fail': 0, 'errors': 0,
            'exit': 0, 'duration_ms': 47, 'records': control['records']},
        'initial_unexpected_control_or_helper_failures': 0, 'further_testing': 'NOT_NEEDED_NOT_RUN',
        'historical_suite_and_failed_entry_runs': 0, 'model_content_revalidation_or_inference': 0,
        'timing_difference_decomposition': 'UNKNOWN_ORIGINAL_FIELDS_RETAINED'},
    'current_preflight': {'accepted_offline': True, 'role': 'AUTHOR_SAVE', 'schema_profile': None,
        'body_admission': 'CURRENT_SCHEMA_UNBOUND',
        'scope_sha256': '87324f21901723a4282afc9d06bea243b5bdba72ac25ea7f0c1eea3c018493de',
        'context': 1, 'initial_navigation': 1, 'business_GET': 4, 'maximum_seconds': 900,
        'signature_GET': 0, 'object_POST': 0, 'commit_POST': 0, 'refresh': 0, 'reopen': 0,
        'bootstrap_slots_and_denials': 'UNCHANGED_FROM_FIXED_PLAN',
        'success_terminates': 'PREWRITE_BLOCKED_NO_EFFECT', 'self_promotion': False,
        'actual_success_predicted': False, 'new_exact_root_authority_required': True},
    'remaining_actual_bindings': ['natural export codec/authoritative completeness/all-five-zone old bodies and full frames',
        'fresh inventory/legal append/newness', 'current account/save-page/joint policy/receipt/signature contracts',
        'exact qualified payload/request and new authority',
        'known successful author/refresh/strict receipt/full external release chain and readonly authority before independent reopen'],
    'historical_preservation': {'actual_failure_machine': 'd6d4c11596284fbe82cfa81b3d10fae2ed8b83f2a10f10c71d2ab50767478395',
        'root_partial_failure_acceptance': 'fa6bc186203ef4ebdef51a8ee09e8d6b69e8acb04a1a5a452c9edc6aa77e91a2',
        'substep_HTTP_navigation_root_cause': 'UNKNOWN', 'context_closed': False,
        'worker_stderr_raw': 'MISSING', 'four_GETs_and_effects': 'NOT_RUN',
        'original_independent_control_FAIL': 'UNCHANGED_NOT_RECLASSIFIED',
        'model_FAILED_HOLD_empty_answer_and_corrected_content_acceptance': 'UNCHANGED_NOT_REVIEWED_AGAIN'},
    'limits': {'write_eligible': False, 'production_ready': False, 'actual_save': 'NOT_RUN',
        'actual_independent_platform_readback': 'NOT_RUN', 'real_resources': 0, 'new_activation': False,
        'old_authority_86f3ad15_restart_allowed': False, 'current_body_remaining': 0,
        'older_readonly_remaining': [0, 0], 'new_stage_chat_or_chapter_formula_gate': False},
    'artifacts': {name: info(OUT / name) for name in ['report.md', 'input-raw-manifest.json', 'static-delta.json',
        'gate-scope-map.json', 'python-result.json', 'independent-control-result.json', 'input-preservation.json', 'release.json']}})
members = [dict(path=p.relative_to(OUT).as_posix(), **info(p)) for p in sorted(OUT.rglob('*'))
    if p.is_file() and p.name != 'output-manifest.json']
write('output-manifest.json', {'schema': 'A24MinimumGateIndependentOutputManifest/v1',
    'self_excluded': True, 'member_count': len(members), 'members': members})
for row in members:
    assert info(OUT / row['path']) == {'bytes': row['bytes'], 'sha256': row['sha256']}
assert {r['path'] for r in members} == {p.relative_to(OUT).as_posix() for p in OUT.rglob('*')
    if p.is_file() and p.name != 'output-manifest.json'}
print(json.dumps({'result': 'ACCEPTED_OFFLINE_ONLY', 'R1_R': 'CLOSED_OFFLINE', 'inputs_preserved': 284,
    'private_snapshots_preserved': 17, 'output_members_excluding_manifest': len(members),
    'machine_sha256': info(OUT / 'independent-result.json')['sha256'],
    'output_manifest_sha256': info(OUT / 'output-manifest.json')['sha256'],
    'release_sha256': info(OUT / 'release.json')['sha256']}))
