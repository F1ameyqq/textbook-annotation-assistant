"""Metadata seal only; never reruns controls or imports a product/library helper."""
import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
PRIOR = Path('D:/1800-worktrees/a24-minimum-body-actual-review')
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
assert info(OUT / 'input-raw-manifest.json')['sha256'] == '85b3c11b5c6c4877e19ea0c6e83761abeb9a2dcfd4d8510069e53c4587ac329a'
for row in manifest['members']:
    raw = (ROOT / row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['blob']
for row in manifest['private_references']:
    assert info(Path(row['snapshot_path'])) == {'bytes': row['bytes'], 'sha256': row['sha256']}
intake = json.loads((OUT / 'intake-result.json').read_bytes())
for row in intake['actual_local_libraries_verified_before_import']:
    assert info(Path(row['installed_path'])) == {'bytes': row['bytes'], 'sha256': row['sha256']}
suite = json.loads((OUT / 'python-result.json').read_bytes())
control = json.loads((OUT / 'cache-control-result.json').read_bytes())
assert suite['tests'] == 5 and suite['passed'] and suite['failures'] == suite['errors'] == 0
assert control['tests'] == 1 and control['passed'] and control['failures'] == control['errors'] == 0
assert not [p for p in (OUT / 'temporary').rglob('*') if p.is_file()]
relative = 'src/annotation/delivery/live_pilot/usense.py'
before, after = (PRIOR / relative).read_bytes(), (ROOT / relative).read_bytes()
expected = before.decode().replace('from datetime import datetime, timezone\n',
    'from datetime import datetime, timezone\nfrom functools import wraps\n', 1).replace(
    '    def track_callback(function):\n        async def tracked',
    '    def track_callback(function):\n        @wraps(function)\n        async def tracked', 1).encode()
assert after == expected
write('static-delta.json', {'schema': 'A24CallbackIndependentStaticDelta/v1', 'path': relative,
    'prior_raw_sha256': sha(before), 'candidate_raw_sha256': sha(after),
    'exact_two_additions_verified': True,
    'diff': ''.join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
        fromfile='fixed-actual-prior/usense.py', tofile='candidate/usense.py')),
    'policy_count_timeout_source_owner_gate_expansion': False, 'actual_timeout_recovery_proven': False})
write('local-library-contract.json', {'schema': 'A24CallbackIndependentActualLibraryContract/v1',
    'python': '3.9.13', 'playwright': '1.58.0', 'sources_verified_before_helper_import': intake['actual_local_libraries_verified_before_import'],
    'route_handler': {'source': '_helper.py:RouteHandler._handle_internal', 'arguments': ['route', 'route.request'],
        'invocations': 'RouteHandler.handle tracks/removes active invocations in finally'},
    'mapper': {'source': '_impl_to_api_mapping.py:ImplToApiMapping.wrap_handler',
        'arity': 'len(inspect.signature(handler).parameters)', 'argument_selection': 'mapped positional list sliced by arity',
        'bound_cache_key': 'instance attribute prefix plus handler.__name__'},
    'registration': {'source': 'async_api/_generated.py:BrowserContext.route', 'callback': 'self._wrap_handler(handler)'},
    'dispatch': {'source': '_browser_context.py:BrowserContext._on_route', 'callback': 'await route_handler.handle(route)'},
    'new_signature': {'bound_route': ['route'], 'bound_paused': ['event'], 'distinct_handler_names': True},
    'independent_cache_control': control['records'][0],
    'historical_arity_error': 'Consistent with variadic wrapper exposing two parameters; not proof of full timeout causality',
    'whole_environment_or_browser_binary_fully_hashed': False, 'library_installed_or_replaced': False})
write('input-preservation.json', {'schema': 'A24CallbackIndependentPreservation/v1', 'at_utc': STAMP,
    'result': 'PASS_RAW_PRESERVATION', 'raw_inputs': 294, 'dependencies_verified_at_intake': 144,
    'delivery_members_verified_at_intake': 293, 'private_snapshots': 21, 'installed_sources': 4,
    'all_raw_size_sha256_git_blob_checks': True, 'installed_sources_still_match_frozen_hashes': True,
    'input_product_or_old_evidence_changes': 0, 'active_author_or_business_original_paths_read': False,
    'root_historical_diff_repeated': False, 'synthetic_temporary_files_remaining': 0})
write('release.json', {'schema': 'A24CallbackIndependentRelease/v1', 'released': True, 'at_utc': STAMP,
    'scope': 'Own offline actual-library helper and metadata processes only',
    'new_five_controls': {'runs': 1, 'tests': 5, 'exit': 0},
    'independent_cache_control': {'runs': 1, 'tests': 1, 'exit': 0},
    'metadata_helpers': 'Completed; sealing process exits after manifest verification/hash output',
    'retained_helpers': 0, 'synthetic_temporary_files_remaining': 0,
    'real_browser_context_native_profile_model_runtime_job_acquisitions': 0,
    'network_credentials_config_upload_save_reopen_activation': 0, 'old_suite_runs': 0,
    'latest_960f_round_remaining': 0, 'earlier_86f3_round_remaining': 0, 'older_readonly_remaining': [0, 0],
    'actual_timeout_or_context_close_recovery_claimed': False,
    'actual_save': 'NOT_RUN', 'actual_independent_platform_readback': 'NOT_RUN'})
write('independent-result.json', {
    'schema': 'A24RouteCallbackMinimumIndependentReview/v1', 'result': 'ACCEPTED_OFFLINE_ONLY',
    'accepted_scope': 'BOUNDED_ACTUAL_LOCAL_LIBRARY_CALLBACK_SIGNATURE_PREFLIGHT',
    'current_prewrite_accepted_scope': 'BOUNDED_AUTHOR_UNBOUND_FOUR_GET_PREFLIGHT',
    'at_utc': STAMP, 'reviewer': '01a15cf8-68e0-7b63-91a3-657a567b344c', 'same_A24_stage': True,
    'task_sha256': '3c09a0bd44dbe0da124d8f4953f734dcec338bc6abf9fb228eb21466eca12d73',
    'base_actual': '23d6743a1f9540016af5581dcc0d587a052cf309',
    'product': '4aa2aa5aa4eef72995095505086c82ecb4cd57a3',
    'final': 'c71fe78bae5cfd6e3f1d97ba52647159ad68d796',
    'candidate_sha256': '79c4453822efc6e9b856d5859b6711157998291efe62d6f3d6aa15d0244f3574',
    'delivery_manifest_sha256': '16999289344f82b973b80e10f896af9ac3737f23929afdea000c34c8bcc77725',
    'root_input_manifest_sha256': '85b3c11b5c6c4877e19ea0c6e83761abeb9a2dcfd4d8510069e53c4587ac329a',
    'inputs_verified': {'raw': 294, 'dependencies': 144, 'delivery': 293, 'private_snapshots': 21,
        'actual_installed_library_sources': 4},
    'dispositions': {'two_line_signature_correction': 'ACCEPTED_IN_ACTUAL_INSTALLED_HELPER_FAKE_BOUNDARY',
        'remaining_material_code_blockers_in_delta': [], 'callback_tracking_finally': 'PRESERVED',
        'exception_direct_extra_argument_rejection': 'PRESERVED', 'owner_base_and_stopped_rejection': 'PRESERVED',
        'distinct_route_paused_cache_identity': 'PASS_INDEPENDENT_CONTROL',
        'network_policy_scope_counts_timeouts_source_gates_UNKNOWN_no_resend': 'UNCHANGED',
        'actual_timeout_or_context_close_recovery': 'UNPROVEN_NOT_TESTED',
        'qualified_save_or_actual_independent_reopen': 'NOT_ADMITTED'},
    'tests': {'new_actual_library_group': {'runs': 1, 'tests': 5, 'pass': 5, 'fail': 0, 'errors': 0,
            'exit': 0, 'report_duration_ms': 1250, 'embedded_unittest_seconds': 0.028},
        'independent_cache_identity': {'runs': 1, 'tests': 1, 'pass': 1, 'fail': 0, 'errors': 0,
            'exit': 0, 'rounded_report_duration_ms': 0, 'record': control['records'][0]},
        'unexpected_test_failures': 0, 'old_suite_or_historical_entry_runs': 0,
        'model_content_review_or_inference': 0, 'further_testing': 'NOT_NEEDED_NOT_RUN',
        'source_read_no_match': intake['source_inspection_no_match'], 'timing_decomposition': 'UNKNOWN_ORIGINAL_FIELDS_RETAINED'},
    'library_scope': {'python': '3.9.13', 'playwright': '1.58.0',
        'exact_installed_sources_verified_before_import': True, 'whole_environment_fully_hashed': False,
        'browser_binary_runtime_rebuilt': False, 'real_browser_or_transport_constructed': False},
    'current_preflight': {'accepted_offline': True, 'role': 'AUTHOR_SAVE', 'schema_profile': None,
        'body_admission': 'CURRENT_SCHEMA_UNBOUND',
        'scope_sha256': '87324f21901723a4282afc9d06bea243b5bdba72ac25ea7f0c1eea3c018493de',
        'contexts': 1, 'initial_navigation': 1, 'maximum_seconds': 900, 'business_GET': 4,
        'GET_slots': ['same-page official book query once', 'directory once', 'full frames once', 'natural export once'],
        'signature_upload_commit_refresh_reopen_login_credential_config_model_retry': 0,
        'bootstrap_session_static_version_denial_limits': 'UNCHANGED',
        'successful_collection_terminal': 'PREWRITE_BLOCKED_NO_EFFECT', 'self_promotion': False,
        'new_exact_root_authority_required': True, 'new_activation_created': False},
    'preserved_actual_failure': {'machine': '99f48c0d35ebd9921e6c03783e6900d28e520801147dd69b8989827984815023',
        'root': '958b6db82a54851203b3b7c9a4b38ec72a8e06409bf58dd56d1bcb37e83ecd81',
        'goto_elapsed_ms': 45031, 'callback_TypeError': 'OBSERVED_ORIGINAL_RETAINED',
        'full_causal_chain': 'UNPROVEN', 'main_HTTP': 'UNKNOWN', 'context_closed': False,
        'four_GET_save_reopen': 'NOT_RUN', 'earlier_missing_stderr_reconstructed': False},
    'remaining_actual_bindings': ['natural body/schema and authoritative five-zone old-content/full-frame coverage',
        'fresh account/book/target/newness/legal append/save-page/joint policy',
        'signature/receipt/qualified payload/request and new exact authority',
        'known successful author receipt/refresh/full externally certified release chain for readonly reopen'],
    'limits': {'write_eligible': False, 'production_ready': False, 'actual_save': 'NOT_RUN',
        'actual_independent_platform_readback': 'NOT_RUN', 'new_authority': False, 'real_resources': 0,
        'latest_and_earlier_current_body_remaining': [0, 0], 'older_readonly_remaining': [0, 0],
        'model_corrected_content_and_crops': 'UNCHANGED_NOT_REVIEWED_AGAIN', 'new_chat_stage_chapter_formula_gate': False},
    'artifacts': {name: info(OUT / name) for name in ['report.md', 'input-raw-manifest.json', 'intake-result.json',
        'local-library-contract.json', 'static-delta.json', 'python-result.json', 'cache-control-result.json',
        'input-preservation.json', 'release.json']}})
members = [dict(path=p.relative_to(OUT).as_posix(), **info(p)) for p in sorted(OUT.rglob('*'))
    if p.is_file() and p.name != 'output-manifest.json']
write('output-manifest.json', {'schema': 'A24CallbackIndependentOutputManifest/v1',
    'self_excluded': True, 'member_count': len(members), 'members': members})
for row in members:
    assert info(OUT / row['path']) == {'bytes': row['bytes'], 'sha256': row['sha256']}
assert {r['path'] for r in members} == {p.relative_to(OUT).as_posix() for p in OUT.rglob('*')
    if p.is_file() and p.name != 'output-manifest.json'}
print(json.dumps({'result': 'ACCEPTED_OFFLINE_ONLY', 'inputs_preserved': 294,
    'private_snapshots_preserved': 21, 'output_members_excluding_manifest': len(members),
    'machine_sha256': info(OUT / 'independent-result.json')['sha256'],
    'output_manifest_sha256': info(OUT / 'output-manifest.json')['sha256'],
    'release_sha256': info(OUT / 'release.json')['sha256']}))
