"""Freeze this completed static review; no product or captured-code execution."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
A=ROOT/'docs/evidence/A24/controlled-capture-current-body-actual'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(path.read_bytes())
def save(name,value):
    with (OUT/name).open('xb') as h:h.write((json.dumps(value,indent=2)+'\n').encode())

raw_manifest=(OUT/'input-raw-manifest.json').read_bytes()
assert sha(raw_manifest)=='aa537bcf9ded57a655a417a23077d4f7729edb7d7b7767ff1b4e49b8159cca27'
m=json.loads(raw_manifest)
for row in m['members']:
    raw=(ROOT/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
for row in m['private_references']:
    raw=Path(row['snapshot_path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
checked=load(OUT/'static-checks.json')
assert checked['result']=='PASS_BOUNDED_ACQUISITION_RECORDS_AND_RELEASE_ONLY' and len(checked['checks'])==26 and all(checked['checks'].values())
w=load(A/'raw/run/worker-result.json');actual=load(A/'actual-result.json')
at=datetime.now(timezone.utc).isoformat()
save('input-preservation.json',dict(schema='A24ControlledBodyActualIndependentPreservation/v1',at=at,
    result='ALL_349_RAW_AND_57_PRIVATE_INPUTS_UNCHANGED',root_manifest_sha256=sha(raw_manifest),
    product_or_input_edits=0,historical_33521_tree_audit_repeated=False,product_tests=0))
machine=dict(schema='A24ControlledBodyActualIndependentReview/v1',at=at,
    reviewer='01a15cf8-68e0-7b63-91a3-657a567b344c',isolation=str(ROOT),
    actual_final='d3c8abcf0c1fa89af123e4b242964f818f1a011c',frozen_product_final='61fb7157eb335d2a0b9348e8496ea0b4b8d17ad0',
    result='ACCEPTED_BOUNDED_FOUR_GET_ACQUISITION_RETAINED_PRIVATE_BYTES_AND_OWN_RELEASE_ONLY',
    frozen_inputs=dict(raw_git=349,actual_delivery_members=26,private_snapshots=57,current_private_refs=16,
        current_ref_categories=dict(body_snapshots=3,stage_streams=8,script_raw=1,script_provenance=1,capture_owner_marker=1,outer_launcher_copies=2),
        root_manifest_sha256='aa537bcf9ded57a655a417a23077d4f7729edb7d7b7767ff1b4e49b8159cca27',
        actual_delivery_sha256='0542873bcfa6d6a9343a1786c059bca8a37d59cfa1297ded20b357acb6d5008b',
        all_verified_and_preserved=True,historical_tree_and_prior_closures='REFERENCED_NOT_REREVIEWED'),
    authority=dict(sha256='411ec3757822ed374ed7f4c13e6a0becc571609d2d2b4117991c8acc20c4e244',
        run_id=actual['run_id'],one_claim_chain=True,within_900_second_window=True,
        spent=1,remaining=0,retry=False,old_budgets_restored=False,new_authority_created=False),
    pre_import_provenance=dict(dependencies=158,installed_source_checks=4,python='3.9.13',playwright='1.58.0',
        evidence='FROZEN_WRAPPER_AND_CLAIM_RECORDS_NO_REVIEW_TIME_REPROBE'),
    actual_observations=dict(terminal_status='PREWRITE_BLOCKED_NO_EFFECT',first_error=None,
        bootstrap_session_viewer_admission='DONE',native_document_http=200,native_document_elapsed_ms=6188,
        goto_http=200,goto_dcl_elapsed_ms=9235,business_get_count=4,
        reads=[{k:r[k] for k in ('slot','bytes','sha256','http_status')} for r in w['prewrite']['reads']],
        book_original='NOT_PERSISTED_BY_FROZEN_COLLECTOR_FINITE_HASH_ONLY',
        book_hash_independently_recomputed_from_retained_body=False,
        retained_original_snapshots=['directory','frames','export'],all_three_snapshot_bytes_match=True,
        schema='CURRENT_SCHEMA_UNBOUND',write_allowed=False,successors='NOT_RUN',
        before_after_safe_event_counts=[14,14],truncated=False,guard_first_failure=None,
        expected_exclusion_observations=1,completed_denial_calls=1,pending_callbacks=0,
        http_send_dns_tcp_tls_script_necessity='UNKNOWN',
        capture_binding_marker_exact_current_run_authority_candidate_scope=True,
        script_bytes=3065996,script_sha256='d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41',
        private_source_url_hash_matches=True,raw_source_urls_or_bodies_exported=False,
        captured_code_executed_by_collector=False),
    not_run=['adapter','signature','upload','commit','refresh','reopen'],actual_save='NOT_RUN',actual_independent_fresh_readback='NOT_RUN',
    not_qualified=['natural body schema','full five-zone completeness','complete old-body preservation','book identity',
        'question newness','legal append','save-page mapping','write eligibility','payload receipt and signature'],
    release=dict(context_closed=True,runtime_stopped=True,callback_pending=0,cleanup_errors=[],
        actual_held_identities=checked['held_identities'],empty_closed_jobs=4,closed_held_handles=4,
        actual_launcher_exit='PROVEN_BY_EXTERNAL_HOLDER_EXIT0',outer_helper_own_os_identity='NOT_SELF_CERTIFIED',
        outer_tool_exit0='AUTHOR_TRANSCRIPTION_ONLY',persistent_profile_effects='NOT_INSPECTED'),
    prior_closure=dict(machine_sha256='b5acbd1bc6358915bf0c09e2b8d9bb2a6d52370de6c9b8e503d23f653a6f6ed5',
        code_model_tests_history_reviews_repeated=False,historical_independent_P3_FAIL='PRESERVED_NOT_RERUN_OR_RELABELED',
        all_old_failures_unknowns_and_spent_budgets='UNCHANGED'),
    takeover=dict(user_instruction='FINISH_CURRENT_ROUND_PUBLISH_PROGRESS_AND_HAND_REMAINDER_TO_B',
        frozen_author_next_work_text='SUPERSEDED_BY_CURRENT_ROOT_TASK_NO_FURTHER_A_DISPATCH',
        new_A_implementation_tests_or_live='NOT_AUTHORIZED_BY_THIS_REVIEW',
        B_remaining_offline=['natural export/schema adaptation','complete old-body/five-zone preservation',
            'current identity/newness/legal append','save-page and payload mapping'],
        later_save_and_fresh_readback='REQUIRE_QUALIFIED_INPUTS_AND_EXACT_AUTHORITY',
        publication_and_B_handoff='ROOT_HANDLES',reviewer_B_messages=0,reviewer_pushes=0,new_diagnostic_stage=False),
    static_record_checks=26,product_tests=0,old_controls=0,model_ocr_content_review=0,
    captured_script_or_private_stream_decoding=0,private_provenance='PARSED_IN_MEMORY_ONLY_NO_URL_EXPORT',
    new_real_resources=0,new_authority_or_activation=0,active_author_reads=False,product_or_input_edits=0,
    reviewer_work_released=True,root_final_disposition='PENDING_COORDINATOR',report_sha256=sha((OUT/'REPORT.md').read_bytes()))
save('machine-result.json',machine)
save('reviewer-release.json',dict(schema='A24ControlledBodyActualIndependentOfflineRelease/v1',at=at,
    reviewer=machine['reviewer'],offline_work_released=True,output_frozen=True,new_real_resources_acquired=0,
    new_real_resources_remaining=0,product_tests=0,captured_code_execution=0,new_authority_or_retry=0,
    further_A_work_dispatched=False,reviewer_B_message_or_push=False,
    machine_result_sha256=sha((OUT/'machine-result.json').read_bytes()),root_final_disposition='PENDING_COORDINATOR'))
members=[]
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw=path.read_bytes();members.append(dict(path=path.relative_to(OUT).as_posix(),bytes=len(raw),sha256=sha(raw)))
save('output-manifest.json',dict(schema='A24ControlledBodyActualIndependentOutputManifest/v1',at=at,self_excluded=True,member_count=len(members),members=members))
for row in members:
    raw=(OUT/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
for name in ('machine-result.json','REPORT.md','reviewer-release.json','output-manifest.json'):
    print(name+' '+sha((OUT/name).read_bytes()))
print('OUTPUT_MEMBERS_VERIFIED '+str(len(members)))
