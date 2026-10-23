"""Freeze only already accepted references and the three delegated source images.

No product import, active-author reads, browser, network, profile or platform action.
"""
import hashlib
import json
import struct
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path('D:/1800')
PUBLIC = ROOT / 'docs/evidence/A28-independent/preparation'
PRIVATE = ROOT / '.local/stages/a28-independent-20261023/preparation'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def jpeg_size(data):
    assert data[:2] == b'\xff\xd8'
    pos = 2
    while pos < len(data):
        assert data[pos] == 255
        while data[pos] == 255:
            pos += 1
        marker = data[pos]
        pos += 1
        if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
            continue
        length = struct.unpack('>H', data[pos:pos + 2])[0]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            height, width = struct.unpack('>HH', data[pos + 3:pos + 7])
            return [width, height]
        pos += length
    raise ValueError('JPEG dimensions unavailable')


paths = [
    'AGENTS.md',
    'docs/coordination-state.json',
    'docs/A26-five-native-delivery-20261023.md',
    'docs/A27-stability-closure-20261023.md',
    'docs/evidence/coordinator/a25-final-five-save-readback-closure/receipt.json',
    'docs/evidence/coordinator/a26-final-native-delivery-closure/receipt.json',
    'docs/evidence/coordinator/a27-final-stability-closure/receipt.json',
    'docs/evidence/coordinator/a27-product-adoption/receipt.json',
    'docs/evidence/A25-independent/final-recovery-actual-review/result.json',
    'docs/evidence/A25-independent/final-recovery-actual-review/report.md',
    'docs/evidence/A26-independent/final-native-delivery-actual-review/result.json',
    'docs/evidence/A26-independent/final-native-delivery-actual-review/report.md',
    'docs/evidence/A27-independent/r1-review/result.json',
    'docs/evidence/A27-independent/r1-review/report.md',
    '.local/stages/A05/source-viewer12.jpg',
    '.local/stages/A05/source-viewer13.jpg',
    '.local/stages/A05/source-viewer173.jpg',
    'docs/tasks/A28-complete-lesson-production-20261023.md',
]
raw = {}
members = []
for index, relative in enumerate(paths, 1):
    source = ROOT / relative
    data = source.read_bytes()
    target = PRIVATE / 'inputs' / ('%02d-%s' % (index, source.name))
    write_new(target, data)
    assert target.read_bytes() == data
    raw[relative] = data
    entry = {'source': relative, 'copy': str(target), 'bytes': len(data),
             'sha256': digest(data)}
    if source.suffix == '.jpg':
        entry['dimensions'] = jpeg_size(data)
    members.append(entry)


def obj(relative):
    return json.loads(raw[relative])


a25 = obj(paths[4])
a26 = obj(paths[5])
a27 = obj(paths[6])
adopt = obj(paths[7])
links = [
    (paths[8], a25['machine_result']['sha256']),
    (paths[9], a25['report']['sha256']),
    (paths[10], a26['formal_result_sha256']),
    (paths[11], a26['report_sha256']),
    (paths[12], a27['formal_result_sha256']),
    (paths[13], a27['formal_report_sha256']),
    (paths[6], adopt['root_closure_sha256']),
]
checks = []
for relative, expected in links:
    actual = digest(raw[relative])
    assert actual == expected, relative
    checks.append({'source': relative, 'expected': expected, 'actual': actual,
                   'status': 'PASS_ACCEPTED_REFERENCE_ONLY'})

state = obj(paths[1])
assert state['coordinator_thread_id'] == '01a166c5-f93f-76e3-baf4-a3545ccddebd'
assert state['automation']['status'] == 'PAUSED'
assert state['tasks']['A28']['reviewer_thread_id'] == '01a16910-8c4e-7803-9347-87ab6798b358'
assert state['tasks']['A28']['platform_owner'] == '01a1690f-c20a-73a2-9446-c357f60b3d75'
assert a25['cumulative_counts']['posts'] == 5
assert a25['cumulative_counts']['fresh_postsave_readers'] == 5
assert a26['accepted_printed_questions'] == [1, 2, 3, 4, 5]
assert adopt['after_commit'] == a27['product_commit'] == 'ebca4c71a70bdfb5fbccc023d00e0207ae532470'
assert obj(paths[12])['status'] == 'ACCEPTED_OFFLINE_ONLY'
assert obj(paths[12])['product_commit'] == adopt['after_commit']

manifest = {'schema': 'A28IndependentPreparationInputs/v1',
            'created_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
            'source_copy_pairs': len(members), 'members': members}
write_new(PRIVATE / 'raw-manifest.json', json_bytes(manifest))
write_new(PUBLIC / 'input-manifest.json', json_bytes(manifest))
result = {
    'schema': 'A28IndependentPreparation/v1',
    'status': 'READY_WAITING_FROZEN_CANDIDATE',
    'candidate_review': 'WAITING_EXECUTION',
    'candidate_commit': None,
    'candidate_raw_manifest': None,
    'reviewer_thread_id': '01a16910-8c4e-7803-9347-87ab6798b358',
    'coordinator_thread_id': state['coordinator_thread_id'],
    'executor_thread_id': '01a1690f-c20a-73a2-9446-c357f60b3d75',
    'accepted_product_baseline': adopt['after_commit'],
    'coordination_state_sha256': digest(raw[paths[1]]),
    'A28_registration_in_snapshot': 'A28' in state['tasks'],
    'input_manifest_sha256': digest(json_bytes(manifest)),
    'input_pairs_verified': len(members),
    'accepted_reference_links_verified': len(checks),
    'accepted_reference_checks': checks,
    'source_visual_review': {
        'method': 'DIRECT_LOCAL_IMAGE_VIEW_NO_OCR',
        'images_viewed': ['source-viewer12.jpg', 'source-viewer13.jpg', 'source-viewer173.jpg'],
        'printed_pages': [4, 5, 25],
        'lesson': '第2课时 勾股定理的验证及简单应用',
        'source_units': ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q8-variant'],
        'source_denominator': 9,
        'new_units': ['Q6', 'Q7', 'Q8', 'Q8-variant'],
        'excluded_branch': '漫话勾股世界——教材P6“阅读·思考”变式',
        'new_platform_stable_identities': 'UNKNOWN_AWAIT_FIXED_CURRENT_SOURCE',
        'new_units_require_new_nodes_and_frames': True,
        'native23': 'EXCLUDED_NEXT_SECTION_VIEWER14_PER_ROOT_DISPATCH',
    },
    'reused_accepted_layers': {
        'A25': 'FIVE_REAL_SAVES_AND_FIVE_FRESH_INDEPENDENT_READBACKS_REFERENCE_ONLY',
        'A26': 'FIVE_NATIVE_EXPORT_IMAGES_FORMULAS_AND_PORTABLE_ZIP_REFERENCE_ONLY',
        'A27': 'OFFLINE_ONLY_ADOPTED_BASELINE_NO_NEW_LIVE_CLAIM',
    },
    'new_scope_status': {
        'content_candidate_comparison': 'NOT_RUN_NO_FROZEN_CANDIDATE',
        'implementation_controls': 'NOT_RUN_NO_FROZEN_CANDIDATE',
        'actual_receipt_review': 'NOT_RUN_NO_FIXED_ACTUAL',
        'fresh_reader_review': 'NOT_RUN_NO_FIXED_ACTUAL',
        'native_export_and_display_review': 'NOT_RUN_NO_FIXED_DELIVERY',
        'nine_unit_completion': 'NOT_ACCEPTED',
    },
    'activity': {
        'active_author_workspace_reads': 0, 'product_tests': 0,
        'old_content_revalidation': 0, 'old_suite_runs': 0, 'OCR': 0,
        'network': 0, 'browser': 0, 'profile': 0, 'platform': 0,
        'save': 0, 'retry': 0, 'product_edits': 0,
        'coordination_edits': 0, 'external_messages': 0,
        'automation': 'PAUSED_UNCHANGED_REPOSITORY_SNAPSHOT',
    },
    'limits': [
        'Readiness is preparation only, not candidate or actual acceptance.',
        'Source page/printed units do not establish current stable platform identities.',
        'The five accepted old units are referenced, not rewritten or content-revalidated.',
        'A27 real recovery and real Edge enumeration remain unobserved.',
        'No frozen A28 candidate or actual delivery was supplied to this preparation.',
    ],
}
write_new(PUBLIC / 'result.json', json_bytes(result))
print(json.dumps({'status': result['status'], 'input_pairs': len(members),
                  'accepted_reference_checks': len(checks),
                  'source_images': [x for x in members if 'dimensions' in x],
                  'result_sha256': digest(json_bytes(result))}, ensure_ascii=True))
