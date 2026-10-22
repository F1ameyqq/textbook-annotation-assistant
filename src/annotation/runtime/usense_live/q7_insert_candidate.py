"""Offline materialization of the source-reviewed seven-frame Q7 variant."""
import copy
from pathlib import Path
import uuid
from urllib.parse import urlsplit

from .core import require, sha, parse, plain_path

BOOK = '46007447'
DIRECTORY = 'dir-1792063578574-2a6vq8zom'
OSS = 'https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com'
KEYS = ('variant-stem', 'variant-figures', 'variant-choice-A', 'variant-choice-B',
        'variant-choice-C', 'variant-choice-D', 'variant-answer')


def ref(path):
    file = plain_path(str(path))
    return str(file), sha(file.read_bytes())


def materialize(candidate_path, crop_proof_path, root_review_path, before_full):
    candidate_file, candidate_sha = ref(candidate_path)
    proof_file, proof_sha = ref(crop_proof_path)
    review_file, review_sha = ref(root_review_path)
    candidate = parse(Path(candidate_file).read_bytes())
    proof = parse(Path(proof_file).read_bytes())
    review = parse(Path(review_file).read_bytes())
    require(candidate['schema'] == 'Q7FinalSevenFrameContentCandidate/v1' and
        candidate['logical_owner'] == 'variant' and candidate['book_id'] == BOOK and
        candidate['target_directory_id'] == DIRECTORY, 'EXACT_VARIANT_CANDIDATE_REQUIRED')
    require(review['status'] == 'PASS_SOURCE_CONTENT_AND_BOUNDARIES' and review['variant_answer'] == 'B' and
        review['main_answer'] == 'C' and review['crop_fetch_proof_sha256'] == proof_sha, 'ROOT_VISUAL_REVIEW_REQUIRED')
    require(proof['status'] == 'ALL_14_HTTP200_DIMENSIONS_MATCH' and len(proof['results']) == 14,
            'ALL_FOURTEEN_VERIFIED_CROPS_REQUIRED')
    request_spec = candidate['crop_get_requests']
    require(proof['spec_sha256'] == request_spec['sha256'] == sha(plain_path(request_spec['path']).read_bytes()),
            'CROP_REQUEST_SPEC_CHANGED')
    source_review = candidate['source_review']
    require(sha(plain_path(source_review['path']).read_bytes()) == source_review['sha256'], 'OCR_SOURCE_REVIEW_CHANGED')
    target = candidate['target']
    require(target['node_id'] is None and target['info_id'] is None and target['question_order'] is None and
        target['proposed_insert_after_existing_node_id'] == '1792066417325' and
        target['proposed_insert_after_existing_order'] == 7, 'NO_PRESUMED_SERVER_IDENTITY')
    require(candidate['question_info'] == {'tishi': 'xuanze', 'tilei': None, 'tihao': None}, 'EXPLICIT_NEW_SINGLE_CHOICE_INFO')
    frames = candidate['frames']
    require([f['key'] for f in frames] == list(KEYS), 'EXACT_SEVEN_FRAME_LAYOUT_REQUIRED')
    rows_before = before_full['frames']['data']
    # Actual unified response uses either direct list or data.annotations; preserve it elsewhere.
    if isinstance(rows_before, dict):
        require(set(rows_before) == {'annotations'}, 'ALL_FRAMES_RESPONSE_SHAPE_UNKNOWN')
        rows_before = rows_before['annotations']
    require(isinstance(rows_before, list), 'ALL_FRAMES_LIST_REQUIRED')
    existing_ids = {row['rect_id'] for row in rows_before}
    old_orders = {int(row['order_in_level']) for row in rows_before if row['belong_to_level'] == 'question_level'}
    require(old_orders == set(range(1, 23)), 'EXACT_EXISTING_22_QUESTION_FRAME_ORDERS_REQUIRED')
    crops = {row['key']: row for row in proof['results']}
    require(len(crops) == 14, 'DUPLICATE_CROP_KEYS')
    new_ids, upserts, sources = set(), [], {}
    for frame in frames:
        key, rect = frame['key'], frame['planned_rect_id']
        require(str(uuid.UUID(rect)) == rect and rect not in existing_ids and rect not in new_ids,
                'SEVEN_FRESH_RECT_UUIDS_REQUIRED')
        new_ids.add(rect)
        bbox, dims = frame['bbox'], frame['source_dimensions']
        require(len(bbox) == 4 and all(type(v) is int for v in bbox) and len(dims) == 2 and
            0 <= bbox[0] < bbox[2] <= dims[0] and 0 <= bbox[1] < bbox[3] <= dims[1], 'FULL_SOURCE_BOUNDS_REQUIRED')
        require(frame['rect_bbox'] == ','.join(map(str, bbox)), 'RECT_BBOX_CSV_CHANGED')
        source = frame['source']
        require(sha(plain_path(source['path']).read_bytes()) == source['sha256'] == frame['source_sha256'], 'SOURCE_BYTES_CHANGED')
        sources[source['path']] = source['sha256']
        local = frame['crop']
        require(sha(plain_path(local['path']).read_bytes()) == local['sha256'], 'LOCAL_CROP_BYTES_CHANGED')
        x1, y1, x2, y2 = bbox
        page = frame['viewer_page']
        expected_url = f'{OSS}/upload_images/{BOOK}/{BOOK}_page_{page-1}.jpg?x-oss-process=image/crop,x_{x1},y_{y1},w_{x2-x1},h_{y2-y1}'
        require(frame['image_path'] == frame['hosted_image_url'] == expected_url, 'EXACT_SOURCE_CROP_URL_REQUIRED')
        remote = crops[key]
        require(remote['url'] == expected_url and remote['status'] == 200 and remote['bbox'] == bbox and
            remote['dimensions'] == [x2-x1, y2-y1] and remote['source_sha256'] == source['sha256'] and
            sha(plain_path(remote['file']).read_bytes()) == remote['sha256'], 'REMOTE_CROP_PROOF_CHANGED')
        upserts.append({'rect_id': rect, 'type': frame['zone'], 'belong_to_level': 'question_level',
            'order_in_level': str(max(old_orders) + 1), 'image_order_in_annotation_zone': frame['image_order_in_annotation_zone'],
            'rect_bbox': frame['rect_bbox'], 'page_index': page, 'image_path': expected_url,
            'parent_rect_id': None, 'directory_id': DIRECTORY, 'content_type': frame['content_type'],
            'user_id': None, 'is_pre_annotation': False, 'pre_annotations_id': None})
    zones = candidate['zone_values']
    require(set(zones) == {'question', 'choice', 'answer'}, 'THREE_REVIEWED_ZONES_REQUIRED')
    for zone, text in zones.items():
        require(sha(text.encode('utf-8')) == candidate['zone_text_sha256'][zone], 'REVIEWED_ZONE_TEXT_CHANGED')
    require(zones['answer'] == 'B' and [v[:2] for v in zones['choice'].splitlines()] == ['A.', 'B.', 'C.', 'D.'],
            'VARIANT_B_AND_FOUR_CHOICES_REQUIRED')
    figure_url = frames[1]['image_path']
    require(zones['question'].count('<img ') == 1 and zones['question'].count(figure_url) == 1 and
        zones['question'].startswith(candidate['source_plaintext_zone_values']['question']), 'ONE_EXACT_FIGURE_BODY_REQUIRED')
    rects = {zone: [row['rect_id'] for row in upserts if row['type'] == zone] for zone in zones}
    require(rects == candidate['zone_rect_ids'], 'ZONE_RECT_BINDING_CHANGED')
    payload = {'file_id': BOOK, 'target_directory_id': DIRECTORY, 'question_order': None,
        'is_new_question_insertion': True, 'insert_after_order': 7, 'annotations_upsert': upserts,
        'annotations_delete_rect_ids': [], 'ocr_submissions': [{'zone': zone, 'ocr_result': zones[zone],
            'rect_ids': rects[zone], 'question_order': None} for zone in ('question', 'choice', 'answer')],
        'ocr_delete_zones': [], 'question_info': copy.deepcopy(candidate['question_info']), 'created_by': None}
    approved = {'candidate_ref': candidate_file, 'candidate_sha256': candidate_sha,
        'review_ref': review_file, 'review_sha256': review_sha, 'crop_evidence_ref': proof_file,
        'crop_evidence_sha256': proof_sha, 'source_evidence': [{'path': path, 'sha256': digest} for path, digest in sources.items()],
        'source_review_ref': source_review['path'], 'source_review_sha256': source_review['sha256'],
        'zone_values': copy.deepcopy(zones), 'zone_text_sha256': copy.deepcopy(candidate['zone_text_sha256']),
        'frames': copy.deepcopy(frames), 'candidate': copy.deepcopy(candidate)}
    return {'payload_candidate': payload, 'approved_new_content': approved}
