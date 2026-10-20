"""Finalize only new independent review documents and their raw manifest."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path('D:/1800-worktrees/a18-independent-fixed')
OUT = Path(__file__).resolve().parent
AUTHOR = ROOT / 'docs/evidence/A18/current-frontend'
INPUT = Path('D:/1800/docs/evidence/coordinator/a18-fixed-delivery/input-raw-manifest.json')
sha = lambda b: hashlib.sha256(b).hexdigest()
load = lambda p: json.loads(p.read_bytes())
now = datetime.now(timezone(timedelta(hours=8))).isoformat()


def write(name, data):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


inputs = load(INPUT)
assert sha(INPUT.read_bytes()) == 'f9c9c1b40f691fceaaf94d5d8f1d0bee9086303dcf4dbb3f3f0f521725c4f2c1'
for member in inputs['members']:
    raw = (ROOT / member['path']).read_bytes()
    assert len(raw) == member['size'] and sha(raw) == member['sha256'], member['path']
assert len(inputs['members']) == 67
delta = load(OUT / 'delta-result.json')
audit = load(OUT / 'fixed-input-source-audit.json')
assert delta['success'] and delta['suite']['tests_run'] == 20 and delta['controls']['tests_run'] == 4
assert audit['result'] == 'PASS_FIXED_INPUT_AND_TARGETED_STATIC_SOURCE'
assert len(audit['markers_verified']) == 24

checks = [
    {'id': 'P0', 'result': 'PASS', 'basis': ['fixed-input-source-audit.json', 'delta-result.json:independent_records:C1'],
     'scope': '67 fixed raw, 22 candidate dependencies, 59 author delivery members and hashes; coordinator whole-history preservation reference, no repeated full old scan'},
    {'id': 'P1', 'result': 'PASS', 'basis': ['delta-result.json:suite_records:unknown_denial', 'tools/a16_current_state_probe.py:235-254,297-386'],
     'scope': 'Unknown non-API same-origin GET XHR/Fetch denied in both layer orders; narrow continuation does not permit sending'},
    {'id': 'P2', 'result': 'PASS', 'basis': ['delta-result.json:suite_records:hard_stop_matrix', 'stderr.txt:test_forged_classification_and_missing_native_identity_stop', 'delta-result.json:independent_records:C4'],
     'scope': 'Hard stops precede exclusions; method/origin/protected/API/sample/known-parameter/redirect/navigation/frame/WS boundaries retained'},
    {'id': 'P3', 'result': 'PASS', 'basis': ['fixed-input-source-audit.json:containing_call_relations_verified', 'stderr.txt:test_version_single_send_both_orders_and_double_repeat_cost', 'stderr.txt:test_version_reservation_before_native_await', 'stderr.txt:test_reload_and_redirect_still_hard_stop'],
     'scope': 'Exact version URL and raw query shape; native send reservation <=1, repeated version denied, reload still second-navigation stopped'},
    {'id': 'P4', 'result': 'PASS', 'basis': ['delta-result.json:suite_records:shared_mixed_budget', 'stderr.txt:test_mixed_reservations_before_await'],
     'scope': 'Single combined event budget16 across CDN/unknown path/version repeat, both layers count separately before await,17th denied and fatal'},
    {'id': 'P5', 'result': 'PASS', 'basis': ['stderr.txt:test_denial_errors_stop_and_do_not_complete', 'stderr.txt:test_pending_callback_and_post_settlement_are_failures', 'delta-result.json:suite_records:late_final_failure', 'delta-result.json:independent_records:C2,C3'],
     'scope': 'Denial exceptions, observed denied responses, late fatal and unsettled callbacks retain final ERROR/UNKNOWN; no excluded body extraction'},
    {'id': 'P6', 'result': 'PASS', 'basis': ['delta-result.json:suite_records:diagnostic_redaction', 'fixed-input-source-audit.json'],
     'scope': 'Opaque path hash/safe known template and query names; no secret values; actual source hash/offset/call relations, no XHR-path/schema inference'},
    {'id': 'P7', 'result': 'PASS', 'basis': ['delta-result.json:independent_records:C1,C3', 'stderr.txt:test_old_a17_and_every_new_binding_mismatch_rejected', 'src/annotation/source/usense/current_readonly/gate.py:fixed_fields,scope_binding,validate_activation', 'tools/a16_current_state_probe.py:734-785'],
     'scope': 'Actual A18 template/gate binding and old A17 rejection; sample0/body/schemaUNKNOWN/write false; no activation or claimed live facts'}
]
write('checks.json', {'task': 'A18', 'result': 'PASS_BOUNDED_READONLY_PREFLIGHT', 'checks': checks,
    'new_suite': delta['suite'], 'finite_independent_controls': delta['controls'],
    'old_suites_run': 0, 'historical_NOT_RUN_changed': False, 'blocking_findings': []})

machine = load(AUTHOR / 'independent-report-template-NONEXECUTABLE.json')
machine.update({
    'result': 'ACCEPTED_OFFLINE_ONLY', 'acceptance_basis': 'BOUNDED_READONLY_PREFLIGHT',
    'schema': 'A18-independent-current-frontend-preflight/v1', 'reviewer_thread_id': '01a15954-997c-7af2-9645-a4e2c2b25e76',
    'review_dispatch_workflow_commit': 'dbb3122383e5138fb1be8d053bf956c32928f970',
    'review_task_sha256': 'f77bee32246b848121b9657fa5a0a4b894e6670ad5c6db23dfc5f25552af11cd',
    'base_commit': inputs['base'], 'product_commit': inputs['product'], 'final_commit': inputs['final'],
    'created_at': now, 'actual_review_output': str(OUT), 'canonical_report_written_by_reviewer': False,
    'input_raw_manifest_sha256': sha(INPUT.read_bytes()), 'input_raw_members_verified': 67,
    'candidate_dependencies_verified': 22, 'author_delivery_members_verified': 59,
    'new_delta': delta['suite'], 'finite_independent_controls': delta['controls'],
    'blocking_findings': [], 'checks': 'checks.json', 'report': 'REPORT.md',
    'raw_manifest': 'sha256-manifest.json', 'release': 'release.json',
    'body_status': 'UNKNOWN', 'schema_status': 'UNKNOWN', 'production_ready': False, 'write_eligible': False,
    'current_authentication': 'UNPROVEN', 'current_book_inventory': 'UNKNOWN', 'current_original_mapping': 'UNKNOWN',
    'original_R02_status': 'REWORK_CAPABILITY_DISABLED_NOT_FIXED', 'A17_blocked_XHR_path': 'UNKNOWN',
    'live_activated': False, 'live_used': 0, 'decision_created': False, 'activation_created': False,
    'new_live_limit': 1, 'context_limit': 1, 'navigation_limit': 1, 'total_seconds': 900,
    'business_get_limit_per_url': 1, 'original_limit_per_viewer': 1,
    'login_submission_limit': 0, 'business_write_limit': 0, 'upload_limit': 0, 'ocr_limit': 0,
    'old_budgets_restored': False, 'old_suites_run': 0, 'historical_NOT_RUN_changed': False,
    'real_browser_network_profile_native_occupancy_login_business_calls': 0,
    'product_child_processes': 0, 'released': True,
    'limitations': [
        'Finite offline fake transport and targeted static bytes only; actual context/native ordering and platform effects unproved',
        'No real authentication, book/directory/frame inventory, original mapping, body/schema, save or refresh/reopen readback proof',
        'Original R02 not repaired; sample0, automatic schema confirmation false, write and production eligibility false',
        'Author run01 asyncio offline guard failure and all old raw/NOT_RUN retained',
        'Complete original cause and correct denial/ERROR remain necessary; minor top-level attribution differences do not independently block this preflight',
        'Historical launcher OS identity, timing decomposition and auxiliary send totals remain UNKNOWN',
        'Whole baseline preservation relies on coordinator fixed raw Git verification; reviewer verified designated67raw and declared dependency/delivery manifests'
    ],
    'next_action': 'Coordinator may bind this exact A18 offline result to its own decision and unique activation under existing standing TLS permission; reviewer does not activate',
    'other_three_cases': 'HOLD', 'Q22_replayed': False, 'B_or_external_messages': 0,
    'book_submission_performed': False
})
assert machine['candidate_manifest_sha256'] == 'c0f7ea30ee5a3484544524b5e8c609125113a474d901bd24fc600529509ae8e8'
write('independent-result.json', machine)
write('command-results.json', {'task': 'A18', 'source': 'Observed completed exec_command results', 'commands': [
    {'command': 'python -B docs/evidence/A18/independent-current-frontend-review/review_runner.py', 'exit_code': 0,
     'working_directory': str(ROOT), 'result': 'delta-result.json', 'stdout_summary': {'suite': delta['suite'], 'controls': delta['controls'], 'success': True}},
    {'command': 'python -B docs/evidence/A18/independent-current-frontend-review/audit_fixed_inputs.py', 'exit_code': 0,
     'working_directory': str(ROOT), 'result': 'fixed-input-source-audit.json', 'summary': audit['result']}
]})
write('release.json', {'task': 'A18', 'reviewer_thread_id': machine['reviewer_thread_id'],
    'state': 'RELEASED_OFFLINE_NO_REAL_RESOURCES_CREATED', 'released': True, 'at': now,
    'release_basis': 'In-process fake objects and static/document helpers only; observed test/audit commands completed exit0; no persistent exec session or owned live resource created',
    'new_suite_runs': 1, 'new_suite_tests': 20, 'finite_independent_controls': 4,
    'old_suites_run': 0, 'fixed_inputs_unchanged_verified': 67,
    'browser_contexts_created': 0, 'network_requests': 0, 'profile_accesses': 0, 'credential_accesses': 0,
    'real_native_loads': 0, 'occupancy_acquisitions': 0, 'login_submissions': 0, 'business_writes': 0,
    'product_children_jobs_handles_created': 0, 'live_activation_created': False,
    'author_active_workspace_accesses': 0, 'root_or_product_edits': 0,
    'source_sidecar_read': False, 'captured_script_executed_or_copied': False,
    'process_kills': 0, 'locks_cleared': 0, 'B_or_external_messages': 0,
    'Q22_replayed': False, 'other_three_cases': 'HOLD',
    'no_background_waiter_or_owned_session_retained': True,
    'actual_platform_resource_release': 'NOT_TESTED_NO_RESOURCES_CREATED',
    'old_launcher_OS_creation_identity': 'UNKNOWN_UNCHANGED'})

members = []
for path in sorted(OUT.rglob('*')):
    if not path.is_file() or path == OUT / 'sha256-manifest.json':
        continue
    raw = path.read_bytes()
    members.append({'path': path.relative_to(OUT).as_posix(), 'size': len(raw), 'sha256': sha(raw)})
write('sha256-manifest.json', {'schema': 'A18-independent-review-raw/v1', 'task': 'A18', 'root': str(OUT),
      'self_exclusion': 'sha256-manifest.json', 'members': members})
for entry in members:
    raw = (OUT / entry['path']).read_bytes()
    assert len(raw) == entry['size'] and sha(raw) == entry['sha256']
print(json.dumps({'result': machine['result'], 'basis': machine['acceptance_basis'],
    'members': len(members), 'manifest_sha256': sha((OUT / 'sha256-manifest.json').read_bytes()),
    'machine_result_sha256': sha((OUT / 'independent-result.json').read_bytes()),
    'report_sha256': sha((OUT / 'REPORT.md').read_bytes()), 'released': True}))
