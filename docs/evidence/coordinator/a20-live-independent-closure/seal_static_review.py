"""Seal new review documents only; standard-library JSON/hash work, no product import."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
DELIVERY = 'docs/evidence/A20/authenticated-source/live-delivery/'
RESULT = 'ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY'
REVIEWER = '01a159ab-01ba-7093-89a6-69e7ce572c38'
NOW = datetime.now(timezone.utc).isoformat()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def write(name, data):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

verification = read(OUT / 'static-verification.json')
manifest = read(OUT / 'input-raw-manifest.json')
originals = {}
for item in manifest['members']:
    path = ROOT / item['path']
    raw = path.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    assert len(raw) == item['size'] and sha(raw) == item['sha256'] and blob == item['blob'], 'INPUT_MUTATION'
    originals[item['path']] = {'bytes': len(raw), 'sha256': sha(raw), 'git_blob': blob}
assert len(originals) == 56
actual = read(ROOT / (DELIVERY + 'actual-result.json'))
task_raw = Path('D:/1800/docs/tasks/A20-single-live-fixed-independent-review.md').read_bytes()
assert sha(task_raw) == '92162ae389fdb6c5cfaef84b47feec8f783ef8b2cd4ace2d4345a51f0571aa40'
with (OUT / 'dispatch-task.md').open('xb') as stream:
    stream.write(task_raw)

limitations = [
    'Only the supplied 56 fixed raw inputs were independently compared. The coordinator full-tree preservation of 31853 old members and 28 additions/0 modifications/0 deletions is referenced, not independently replayed against the active repository.',
    'Credential read/fill/click/POST zero is supported by frozen login-navigation failure, later NOT_RUN steps, no submit intent or POST reservations, and static control flow. It is not a new OS file-access audit.',
    'The first fatal Image path is only a SHA256 and finite safe audit metadata. Its exact path, purpose, initiator and root cause remain UNKNOWN; no captcha/logo or other role was inferred.',
    'The audit has 11 guard events, not 11 actual requests. Auxiliary sends are UNKNOWN; version native reservation1/context0 does not establish transmission or HTTP success.',
    'Login main-Document HTTP/DCL were not recorded. NOT_STARTED navigation diagnostics are viewer-only; the static Script HTTP200 is not login or authentication proof.',
    'Three held process receipts, two closed zero-active Jobs and context/runtime closure are accepted within recorded identity scope. Launcher own OS creation/exit identity remains UNKNOWN; no independent OS/native probe was performed.',
    'Outer stdout135bytes is retained as safe JSON projection and hash, without original bytes; it cannot be independently rehashed. The author records capture-wrapper exit0 separately from launcher/product/worker exit2; the original execution-tool transcript is not in the 56-file package.',
    'The first manifest failure and missing-manifest intermediate commit are retained. The error artifact is explicitly an author transcription, not complete original tool stderr. The final raw manifest is consistent and no product rerun was requested.',
    'Recorded durations and UTC endpoint arithmetic are kept as separate time fields; precise discrepancies and inter-layer gaps have UNKNOWN causes.',
    'Authentication, current book/source/inventory/mapping and first save/readback remain unproven. Body/schema UNKNOWN and write eligibility false are preserved; no old NOT_RUN or spent budget is restored.'
]

machine = {
    'schema': 'A20-single-live-independent-result/v1', 'task': 'A20', 'result': RESULT,
    'reviewer_thread_id': REVIEWER, 'review_dispatch_workflow': '90406699ad083a98efc0bd5a1c0eb94fb199c42f',
    'review_task_sha256': sha(task_raw), 'created_at_utc': NOW,
    'product_commit': '28203196b4f2dae27b1de4213b27da9a41ae3139',
    'offline_final_commit': 'b41e88d7756fde9d7f1b348ce5a300d1104e765b',
    'intermediate_actual_commit': '28dc921c84bb4a6f043472337f3df9128c3b4d3f',
    'actual_final_commit': 'f45fa86789b8f154d03e8c4807412a2161d678f6',
    'candidate_manifest_sha256': verification['candidate_sha256'],
    'product_workflow': '52be34a72c43a7331976aba4b286138b9183856b',
    'input_manifest_sha256': verification['input_manifest_sha256'], 'input_raw_count': 56,
    'candidate_dependency_count': 27, 'author_manifest_members_plus_self': 56,
    'bound_execution_scope': verification['bound_execution_scope'], 'scope_binding_fields': 39,
    'acceptance_scope': ['Fixed actual ERROR/API_BLOCKED failure record',
        'Recorded three held-handle process identities and exits',
        'Recorded two zero-active closed Jobs and context/runtime closure',
        'Original first error, terminal stop and zero pending tasks/callbacks'],
    'actual_outcome': 'ERROR', 'first_error': actual['first_error'],
    'first_fatal_audit': verification['first_fatal'],
    'blocked_path_purpose': 'UNKNOWN', 'root_cause': 'UNKNOWN',
    'login_main_document_HTTP_status': 'UNKNOWN_NOT_RECORDED',
    'login_DCL_observation': 'UNKNOWN_NOT_RECORDED',
    'credential_read_zero_basis': verification['credential_zero_basis'],
    'actual_counts': actual['counts'], 'steps': actual['steps'],
    'actual_time_layers': verification['time_layers'],
    'held_process_receipts': verification['identity_receipts'],
    'two_Jobs_active_final': [0, 0], 'two_Jobs_closed': [True, True],
    'context_runtime_release': actual['release']['context_runtime'],
    'pending_tasks': 0, 'pending_callbacks': 0, 'terminal_stopped': True,
    'launcher_self_OS_identity': 'UNKNOWN', 'live_budget': actual['live_budget'],
    'retry_or_extension_authorized': False, 'old_budgets_restored': False,
    'platform_authentication': 'NOT_PROVEN', 'current_book_identity': 'NOT_PROVEN',
    'book_source_inventory': 'NOT_PROVEN', 'mapping': 'NOT_PROVEN',
    'body_status': 'UNKNOWN', 'schema_status': 'UNKNOWN', 'write_eligible': False,
    'first_question_save_readback': 'NOT_RUN', 'other_three_cases': 'HOLD',
    'Q22_navigation_sample_replay': 0, 'B_messages': 0, 'book_submission': 0,
    'review_mode': 'FIXED_JSON_HASH_AST_ONLY', 'static_evidence_comparisons': verification['check_count'],
    'static_comparisons_are_tests_or_suite': False,
    'reviewer_actual_activity': {
        'product_imports': 0, 'product_runs': 0, 'product_or_launcher_child_processes': 0,
        'new_suites': 0, 'old_suites': 0, 'browser_starts': 0, 'network_requests': 0,
        'profile_reads_or_writes': 0, 'credential_reads': 0, 'native_API_calls': 0,
        'occupancy_checks': 0, 'login_submissions': 0, 'business_writes': 0,
        'decisions_created': 0, 'activations_created': 0, 'live_rounds_started': 0,
        'author_active_directory_reads': 0, 'real_local_output_or_Script_reads': 0,
        'old_markers_outputs_or_failure_evidence_changed': 0,
        'new_threads_or_subagents': 0, 'messages_to_other_chats': 0},
    'limitations': limitations,
    'report_path': str(OUT / 'report.md'), 'release_path': str(OUT / 'release.json'),
    'original_inputs_preserved': True, 'reviewer_resources_state': 'RELEASED_STATIC_REVIEW_ONLY',
    'next_dependency': 'Coordinator limited closure only; this report authorizes no retry or successor live phase'
}
write('independent-result.json', machine)
write('release.json', {
    'schema': 'A20-actual-static-independent-release/v1', 'task': 'A20',
    'reviewer_thread_id': REVIEWER, 'released_at_utc': NOW, 'state': 'RELEASED_STATIC_REVIEW_ONLY',
    'result': RESULT, 'actual_final_commit': machine['actual_final_commit'],
    'reviewer_actual_activity': machine['reviewer_actual_activity'],
    'pending_owned_platform_contexts': 0, 'pending_owned_runtimes': 0,
    'pending_owned_product_processes': 0, 'pending_owned_Jobs': 0,
    'pending_real_callbacks': 0, 'background_helpers_started': 0, 'waiting_processes': 0,
    'original_inputs_preserved': True, 'old_runtime_or_Edge_terminated': False,
    'scope': 'Reviewer static evidence work released; actual producer release accepted only from fixed receipts',
    'live_used': 1, 'live_remaining': 0, 'no_retry_or_marker_reset': True,
    'launcher_self_OS_identity': 'UNKNOWN', 'platform_authentication': 'NOT_PROVEN',
    'first_question_save_readback': 'NOT_RUN'})

for item in manifest['members']:
    content = (ROOT / item['path']).read_bytes()
    assert sha(content) == originals[item['path']]['sha256'] and len(content) == item['size'], 'FINAL_INPUT_MUTATION'
write('input-preservation-final.json', {'task': 'A20', 'result': 'PRESERVED_ALL_56_FIXED_RAW',
    'input_manifest_sha256': verification['input_manifest_sha256'], 'checked_at_utc': NOW,
    'candidate_dependencies': 27, 'original_mode_type_blob_declarations_verified': True,
    'changed_original_paths': [], 'members': originals,
    'full_root_old_tree_preservation': 'COORDINATOR_FIXED_REFERENCE_ONLY_NOT_RESCANNED'})

items = []
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        content = path.read_bytes()
        items.append({'path': path.relative_to(OUT).as_posix(), 'bytes': len(content), 'sha256': sha(content)})
write('sha256-manifest.json', {'schema': 'A20-actual-independent-output-manifest/v1',
    'task': 'A20', 'reviewer_thread_id': REVIEWER, 'root': str(OUT), 'result': RESULT,
    'actual_final_commit': machine['actual_final_commit'], 'member_count': len(items), 'members': items,
    'self_excluded': True, 'self_sha256': 'Returned externally in final handoff',
    'no_product_import_run_or_suite': True, 'no_live_authority': True})
print(json.dumps({'result': RESULT, 'raw_inputs_preserved': 56,
    'output_members_plus_manifest': len(items) + 1,
    'report_sha256': sha((OUT / 'report.md').read_bytes()),
    'machine_result_sha256': sha((OUT / 'independent-result.json').read_bytes()),
    'release_sha256': sha((OUT / 'release.json').read_bytes()),
    'manifest_sha256': sha((OUT / 'sha256-manifest.json').read_bytes()),
    'released': True, 'new_suites': 0, 'product_imports': 0, 'live_rounds': 0}))
