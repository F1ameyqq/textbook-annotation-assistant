import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

PUBLIC = Path('D:/1800/docs/evidence/A28-independent/content-v1-review')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(name, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    with (PUBLIC / name).open('xb') as stream:
        stream.write(data)
    return sha(data)


intake = json.loads((PUBLIC / 'intake.json').read_bytes())
remote = json.loads((PUBLIC / 'remote-intake.json').read_bytes())
checks = json.loads((PUBLIC / 'mechanical-checks.json').read_bytes())
assert checks['status'] == 'PASS_FINITE_CONTENT_DATA_CHECKS'
source_images = [m for m in intake['members'] if Path(m['copy']).suffix == '.jpg']
local_crops = [m for m in intake['members'] if '/crops/' in m['source'].replace('\\', '/')]
remote_crops = [m for m in remote['members'] if Path(m['copy']).suffix == '.jpg']
assert len(source_images) == 3 and len(local_crops) == len(remote_crops) == 14
notes = {
    'q6': 'Text/options match source; C; ladder-only figure with labels and dimensions, no Q7 squares.',
    'q7': 'Text/options match source; D; both square arrangements and figure labels complete, no ladder.',
    'q8': 'Radius5.2, two lanes, height4.1,width3; O and squares correct; separate answer can pass.',
    'q8-variant': 'Radius4.3,single lane, inherited Q8 truck; O and squares correct; separate answer cannot pass.',
}
visual = {
    'schema': 'A28IndependentContentVisualReview/v1',
    'reviewer_thread_id': '01a16910-8c4e-7803-9347-87ab6798b358',
    'method': 'Direct local view_image of each final PNG and captured JPEG; no OCR, no remote fetch.',
    'source_basis': 'Three byte-identical originals directly viewed in preparation; hashes reverified in this fixed intake.',
    'source_images': source_images,
    'local_crop_images_viewed': local_crops,
    'remote_jpeg_images_viewed': remote_crops,
    'author_remote_composites_used_for_visual_judgment': 0,
    'questions': [{'logical_key': key, 'decision': 'ACCEPTED_CONTENT_ONLY', 'observation': value}
                  for key, value in notes.items()],
    'remote_visual_result': '14_MATCH_CORRESPONDING_SOURCE_CROPS_NO_WRONG_FIGURE_OR_SEMANTIC_TRUNCATION',
    'final_formula_html_rendering': 'NOT_RUN',
}
visual_hash = write_json('visual-review.json', visual)
result = {
    'schema': 'A28IndependentContentResult/v1',
    'at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
    'status': 'ACCEPTED_FOUR_QUESTION_CONTENT_AND_FIXED_REMOTE_CROPS_ONLY',
    'decision': 'ACCEPTED',
    'reviewer_thread_id': visual['reviewer_thread_id'],
    'root_index_sha256': intake['root_index_sha256'],
    'bundle_manifest_sha256': intake['bundle_manifest_sha256'],
    'remote_root_index_sha256': remote['root_index_sha256'],
    'remote_proof_sha256': remote['proof_sha256'],
    'candidate_product_commit': None,
    'fixed_input_members_verified': 83,
    'fixed_input_indices_verified': 2,
    'nested_current_content_references_verified': checks['nested_current_content_references'],
    'accepted_units': ['q6', 'q7', 'q8', 'q8-variant'],
    'accepted_candidate_sha256': {m['source'].replace('\\', '/').split('/')[-1]: m['sha256']
        for m in intake['members'] if m['source'].endswith('-candidate.json')},
    'content_findings': [],
    'content_rework_required': False,
    'local_crops_pixel_equal_to_original_bbox': 14,
    'remote_crops_exact_request_and_response_bound': 14,
    'remote_crops_decoded_and_directly_viewed': 14,
    'planned_frame_ids_unique_and_noncolliding': 14,
    'preserved_variant_dependency': 'q8; bundle adjacency and review inherited conditions retained',
    'report_sha256': sha((PUBLIC / 'report.md').read_bytes()),
    'visual_review_sha256': visual_hash,
    'mechanical_checks_sha256': sha((PUBLIC / 'mechanical-checks.json').read_bytes()),
    'limits': {
        'product_implementation_review': 'NOT_RUN_NO_FIXED_CODE_THIS_DISPATCH',
        'new_node_and_frame_creation': 'NOT_ACCEPTED_BY_CONTENT_REVIEW',
        'official_insertion_and_order_shift': 'NOT_ACCEPTED_BY_CONTENT_REVIEW',
        'whole_book_preservation': 'NOT_ACCEPTED_BY_CONTENT_REVIEW',
        'actual_new_saves_and_fresh_readbacks': 'NOT_ACCEPTED_BY_CONTENT_REVIEW',
        'native_export_and_formula_html_display': 'NOT_RUN',
        'complete_nine_unit_production': 'NOT_ACCEPTED_BY_CONTENT_REVIEW',
        'remote_JPEG_vs_source_pixels': 'LOSSY_DIFFERENCE_RETAINED_VISUAL_MATCH_NOT_BYTE_EQUALITY',
        'remote_capture_counters': 'VERIFIED_FIXED_RECORDS_NOT_NEW_NETWORK_OBSERVATION',
    },
    'activity': {'active_author_reads': 0, 'author_scripts_executed': 0,
        'product_tests': 0, 'old_suite_or_content_replays': 0, 'OCR': 0,
        'network': 0, 'browser': 0, 'platform': 0, 'saves': 0, 'retries': 0,
        'root_coordination_or_product_edits': 0, 'external_messages': 0,
        'automation_changed': False},
    'helper_observations': ['An auxiliary terminal display decoded Chinese alt as mojibake; raw UTF-8 input and digests unchanged; no U+FFFD in candidate fields.'],
}
result_hash = write_json('result.json', result)
for m in intake['members'] + remote['members']:
    data = Path(m['copy']).read_bytes()
    assert len(data) == m['bytes'] and sha(data) == m['sha256']
members = []
for file in sorted(PUBLIC.iterdir()):
    if file.is_file():
        data = file.read_bytes()
        members.append({'path': file.name, 'bytes': len(data), 'sha256': sha(data)})
manifest_hash = write_json('report-manifest.json', {
    'schema': 'A28IndependentContentReportManifest/v1', 'status': result['status'],
    'members': members, 'private_member_preservation_rechecked': 83})
print(json.dumps({'status': result['status'], 'report_members': len(members),
    'result_sha256': result_hash, 'report_sha256': result['report_sha256'],
    'report_manifest_sha256': manifest_hash}))
