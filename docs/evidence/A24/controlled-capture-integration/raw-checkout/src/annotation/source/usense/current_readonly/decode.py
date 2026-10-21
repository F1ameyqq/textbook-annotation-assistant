"""Read-only field adapters. Completeness and missing content stay explicit."""
import io
import math
import re
from decimal import Decimal, InvalidOperation
from .gate import BOOK, Stop, sha


FRAME_BINDING_VERSION = 'A16-sample-frame-binding/v1'
FRAME_BINDING_FIELDS = ('rect_id', 'file_id', 'type', 'belong_to_level',
    'order_in_level', 'image_order_in_annotation_zone', 'rect_bbox', 'page_index',
    'parent_rect_id', 'directory_id', 'content_type', 'is_pre_annotation', 'pre_annotations_id')


def _frame_text(value):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise Stop('SAMPLE_FRAME_SCHEMA_REJECTED')
    return value


def _frame_index(value):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch('0|[1-9][0-9]*', value):
        return int(value)
    raise Stop('SAMPLE_FRAME_SCHEMA_REJECTED')


def _frame_reference(value):
    if value is None:
        return None
    if type(value) is int and value > 0:
        return str(value)
    return _frame_text(value)


def _frame_bbox(value):
    values = value.split(',') if isinstance(value, str) else value
    if not isinstance(values, list) or len(values) != 4:
        raise Stop('SAMPLE_FRAME_SCHEMA_REJECTED')
    coords = []
    for v in values:
        if type(v) not in (str, int, float):
            raise Stop('SAMPLE_FRAME_SCHEMA_REJECTED')
        token = str(v).strip()
        if len(token) > 80 or not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', token):
            raise Stop('SAMPLE_FRAME_SCHEMA_REJECTED')
        try:
            coordinate = Decimal(token)
        except InvalidOperation:
            raise Stop('SAMPLE_FRAME_SCHEMA_REJECTED') from None
        if not coordinate.is_finite():
            raise Stop('SAMPLE_FRAME_SCHEMA_REJECTED')
        coords.append(coordinate)
    if not (0 <= coords[0] < coords[2] and 0 <= coords[1] < coords[3]):
        raise Stop('SAMPLE_FRAME_SCHEMA_REJECTED')
    # Decimal equality is exact; no tolerance or coordinate rounding is used.
    return tuple(coords)


def _frame_projection(row, order, directory_id, *, require_source_url):
    if not isinstance(row, dict) or any(k not in row for k in FRAME_BINDING_FIELDS):
        raise Stop('SAMPLE_FRAME_SCHEMA_REJECTED')
    projected = {k: row[k] for k in FRAME_BINDING_FIELDS}
    for name in ('rect_id', 'type', 'belong_to_level', 'directory_id', 'content_type'):
        projected[name] = _frame_text(row[name])
    projected['file_id'] = str(_frame_index(row['file_id']))
    projected['order_in_level'] = number(row['order_in_level'])
    if (projected['file_id'] != BOOK or projected['order_in_level'] != order or
            projected['directory_id'] != directory_id or projected['belong_to_level'] != 'question_level'):
        raise Stop('SAMPLE_FRAME_BINDING_MISMATCH')
    for name in ('image_order_in_annotation_zone', 'page_index'):
        projected[name] = _frame_index(row[name])
    for name in ('parent_rect_id', 'pre_annotations_id'):
        projected[name] = _frame_reference(row[name])
    if type(row['is_pre_annotation']) is not bool:
        raise Stop('SAMPLE_FRAME_SCHEMA_REJECTED')
    projected['rect_bbox'] = _frame_bbox(row['rect_bbox'])
    # Source/crop references are compared exactly by digest, never exported as
    # sensitive URL values. Inventory carries this derived field in memory/evidence.
    source_digest = row.get('image_path_sha256')
    if require_source_url and 'image_path' not in row:
        raise Stop('SAMPLE_FRAME_SOURCE_REFERENCE_MISSING')
    if 'image_path' in row:
        digest = sha(_frame_text(row['image_path']).encode('utf-8'))
        if source_digest is not None and source_digest != digest:
            raise Stop('SAMPLE_FRAME_BINDING_MISMATCH')
        source_digest = digest
    if not isinstance(source_digest, str) or not re.fullmatch('[0-9a-f]{64}', source_digest):
        raise Stop('SAMPLE_FRAME_SOURCE_REFERENCE_MISSING')
    projected['image_path_sha256'] = source_digest
    if 'zone' in row:
        projected['zone'] = _frame_text(row['zone'])
    return projected


def bind_sample_frames(current, expected, order, directory_id):
    """Compare complete semantic projections; transport list order is irrelevant.

    Missing is distinct from null. Unsupported metadata is excluded. Optional
    explicit zone presence must agree; no zone or parent is inferred from type.
    """
    if (type(order) is not int or order <= 0 or order == 22 or
            not isinstance(directory_id, str) or not directory_id or
            not isinstance(current, list) or not isinstance(expected, list) or
            not expected or len(current) != len(expected)):
        raise Stop('SAMPLE_FRAME_COUNT_OR_IDENTITY_MISMATCH')
    def project(rows, require_source_url):
        result = {}
        for row in rows:
            value = _frame_projection(row, order, directory_id, require_source_url=require_source_url)
            if value['rect_id'] in result:
                raise Stop('SAMPLE_FRAME_DUPLICATE_ID')
            result[value['rect_id']] = value
        if any(v['parent_rect_id'] is not None and v['parent_rect_id'] not in result for v in result.values()):
            raise Stop('SAMPLE_FRAME_PARENT_REFERENCE_MISMATCH')
        return result
    before, after = project(expected, False), project(current, True)
    if before != after:
        raise Stop('SAMPLE_FRAME_BINDING_MISMATCH')
    frames = []
    for rect_id in sorted(after):
        row = dict(after[rect_id])
        row['rect_bbox'] = [str(v) for v in row['rect_bbox']]
        frames.append(row)
    return {'schema': FRAME_BINDING_VERSION, 'status': 'MATCHED_CURRENT_SAMPLE_TO_INVENTORY',
        'order': order, 'directory_id': directory_id, 'count': len(frames), 'frames': frames}


def business(result):
    body = result.get('body')
    if result.get('http_status') in (401, 403) or isinstance(body, dict) and body.get('code') in (401, 403, '401', '403'):
        raise Stop('LOGIN_REQUIRED')
    if result.get('http_status') != 200 or not isinstance(body, dict) or type(body.get('code')) is not int or body['code'] != 0:
        raise Stop('BUSINESS_READ_FAILED')
    return body


def number(value):
    if type(value) is int and value > 0:
        return value
    if isinstance(value, str) and re.fullmatch('[1-9][0-9]*', value):
        return int(value)
    raise Stop('QUESTION_ORDER_REJECTED')


def book_identity(body):
    facts, row = book_contract(body)
    if facts['branch'] != 'MATCHED_TARGET':
        raise Stop(facts['branch'])
    result = {'id': row['id'], 'title': row['title']}
    # Only numeric count metadata is useful to the existing inventory adapter.
    # Missing/invalid counts cannot promote partial inventory to FULL.
    for field in ('question_count', 'page_count'):
        value = row.get(field)
        if type(value) is int and value >= 0:
            result[field] = value
        elif type(value) is str and re.fullmatch('0|[1-9][0-9]{0,9}', value):
            result[field] = int(value)
    return result


def value_type(value):
    return {dict: 'object', list: 'array', str: 'string', int: 'integer',
        float: 'number', bool: 'boolean', type(None): 'null'}.get(type(value), 'unsupported')


def _js_truthy(value):
    # In the captured viewer, [] and {} are truthy, unlike Python containers.
    return not (value is None or value is False or
        type(value) in (int, float) and value == 0 or type(value) is str and value == '')


def _safe_title(value):
    return (type(value) is str and 0 < len(value) <= 500 and bool(value.strip())
        and not any(ord(c) < 32 or ord(c) == 127 for c in value))


def book_contract(body):
    """Exact vyt -> qze -> n0 list precedence, never recursive alias merging.

    This is a static frontend contract, not proof of the actual server schema.
    The facts contain only finite names/counts/types and target id/title.
    """
    facts = {'data_type': 'missing', 'containers': {}, 'selected_container': None,
        'item_count': None, 'non_object_item_count': None, 'target_match_count': 0,
        'target_fields': [], 'branch': 'BOOK_DATA_CONTAINER_REJECTED'}
    data = body.get('data') if type(body) is dict else None
    facts['data_type'] = value_type(data)
    if type(data) is not dict:
        return facts, None
    rows = []
    for field in ('records', 'books', 'list'):
        if field in data:
            value = data[field]
            facts['containers'][field] = {'type': value_type(value),
                'length': len(value) if type(value) is list else None}
            if facts['selected_container'] is None and _js_truthy(value):
                facts['selected_container'], rows = field, value
    if type(rows) is not list:
        facts['branch'] = 'BOOK_LIST_CONTAINER_REJECTED'
        return facts, None
    facts['item_count'] = len(rows)
    facts['non_object_item_count'] = sum(type(row) is not dict for row in rows)
    found = [row for row in rows if type(row) is dict and
        type(row.get('id')) in (int, str) and str(row['id']) == BOOK]
    facts['target_match_count'] = len(found)
    # Cap the exported target projections independently of response size.
    for row in found[:2]:
        facts['target_fields'].append({'id': row['id'], 'title_type': value_type(row.get('title')),
            'title': row['title'] if _safe_title(row.get('title')) else None})
    if facts['non_object_item_count']:
        facts['branch'] = 'BOOK_LIST_ITEM_SCHEMA_REJECTED'
    elif not found:
        facts['branch'] = 'BOOK_TARGET_ABSENT'
    elif len(found) != 1:
        facts['branch'] = 'BOOK_TARGET_CONFLICT'
    elif not _safe_title(found[0].get('title')):
        facts['branch'] = 'BOOK_TITLE_MISSING'
    else:
        facts['branch'] = 'MATCHED_TARGET'
        return facts, found[0]
    return facts, None


# Exact schema names only. Unknown keys (including apparently harmless ones)
# never escape. This is bounded structure, not response or account export.
STRUCTURE_FIELDS = ('data', 'records', 'books', 'list', 'total', 'directory_data',
    'children', 'id', 'title', 'label', 'isQuestion', 'order_in_level', 'rect_id',
    'file_id', 'type', 'belong_to_level', 'image_order_in_annotation_zone',
    'rect_bbox', 'page_index', 'parent_rect_id', 'directory_id', 'content_type',
    'is_pre_annotation', 'pre_annotations_id', 'image_path', 'pages', 'image',
    'total_pages', 'annotation_type', 'manifest_exists', 'question_count', 'page_count',
    'annotations', 'source', 'oss_page_url_pattern', 'oss_image_url_pattern', 'blocks')


def finite_structure(value, depth=0, _remaining=None):
    if _remaining is None:
        _remaining = [128]
    result = {'type': value_type(value)}
    _remaining[0] -= 1
    if type(value) is list:
        result['length'] = len(value)
        if depth < 4:
            result['items'] = []
            for item in value[:3]:
                if _remaining[0] <= 0:
                    result['truncated'] = True
                    break
                result['items'].append(finite_structure(item, depth + 1, _remaining))
    elif type(value) is dict and depth < 4:
        result['fields'] = {}
        for field in STRUCTURE_FIELDS:
            if field in value:
                if _remaining[0] <= 0:
                    result['truncated'] = True
                    break
                result['fields'][field] = finite_structure(value[field], depth + 1, _remaining)
    return result


def response_facts(name, status, body):
    """Pre-adapter evidence. Does not validate or upgrade envelope semantics."""
    if name not in ('book', 'directory', 'frames', 'source', 'page14', 'page173'):
        raise Stop('UNREGISTERED_BUSINESS_GET')
    code = body.get('code') if type(body) is dict else None
    safe_code = (code if type(code) is int and -(2**31) <= code < 2**31 else
        code if type(code) is str and re.fullmatch('-?[0-9]{1,10}', code) else None)
    facts = {'schema': 'A24-finite-response-facts/v1', 'endpoint': name,
        'http_status': status if type(status) is int and 100 <= status <= 599 else None,
        'business_code': safe_code, 'business_code_type': value_type(code),
        'envelope_type': value_type(body), 'structure': finite_structure(body),
        'server_schema_confirmed': False, 'raw_body_exported': False}
    if name == 'book':
        facts['book_contract'] = book_contract(body)[0]
    return facts


def content_state(body=None, *, fetched=False, schema_confirmed=False):
    result = {'status': 'UNKNOWN', 'reason': 'NOT_FETCHED', 'text': None}
    if not fetched:
        return result
    if not isinstance(body, dict) or body.get('code') != 0:
        return {**result, 'reason': 'READ_FAILED'}
    data = body.get('data')
    # A success:false/missing result is missing evidence, never known empty.
    if not schema_confirmed or not isinstance(data, dict) or data.get('success') is not True:
        return {**result, 'reason': 'SCHEMA_OR_RESULT_UNCONFIRMED'}
    if 'ocr_result' not in data or not isinstance(data['ocr_result'], str):
        return {**result, 'reason': 'TEXT_FIELD_UNKNOWN'}
    text = data['ocr_result']
    return {'status': 'KNOWN_EMPTY' if text == '' else 'AVAILABLE',
            'reason': 'EXPLICIT_CURRENT_SUCCESS_RESULT', 'text': text,
            'rect_ids': data.get('rect_ids') if isinstance(data.get('rect_ids'), list) else None}


def bound_content(body, zone, order, expected_frames, schema_confirmed):
    data = body.get('data')
    state = content_state(body, fetched=True, schema_confirmed=schema_confirmed)
    if not isinstance(data, dict):
        return state
    for field, expected in (('file_id', BOOK), ('question_order', str(order)), ('zone', zone)):
        if field in data and str(data[field]) != expected:
            raise Stop('CONTENT_IDENTITY_MISMATCH')
    expected = sorted((r for r in expected_frames if r['type'] == zone),
                      key=lambda r: r.get('image_order_in_annotation_zone', 0))
    ids = [r['rect_id'] for r in expected]
    if 'rect_ids' in data and data['rect_ids'] != ids:
        raise Stop('CONTENT_RECT_ORDER_MISMATCH')
    if state['status'] != 'UNKNOWN' and ('rect_ids' not in data or not ids):
        return {'status': 'UNKNOWN', 'reason': 'CONTENT_RECT_BINDING_UNPROVEN', 'text': None}
    return state


def inventory(book, directory, frames, *, all_responses_complete=False):
    """Read-only raw tree plus explicitly separate official frontend DFS order.

    Raw missing/invalid/duplicate orders are retained as gaps, never replaced by
    derived orders or silently accepted as a save-order/preservation baseline.
    """
    from .source_contract import frames_rows
    try:
        nodes = directory['data']['directory_data']
    except (KeyError, TypeError):
        raise Stop('DIRECTORY_SCHEMA_REJECTED') from None
    questions, directories, ids, disagreements = [], [], set(), []
    scalar_types = (str, int, float, bool, type(None))
    def scalar(value):
        if type(value) not in scalar_types:
            return {'unprojected_type': value_type(value)}
        if type(value) is float and not math.isfinite(value):
            return {'unprojected_type': 'nonfinite_number'}
        return value
    def raw_tree(values):
        if type(values) is not list:
            raise Stop('DIRECTORY_SCHEMA_REJECTED')
        projected = []
        for n in values:
            if type(n) is not dict:
                raise Stop('DIRECTORY_SCHEMA_REJECTED')
            row = {k: scalar(n[k]) for k in ('id', 'type', 'label', 'order_in_level', 'isQuestion') if k in n}
            if 'children' in n:
                row['children'] = None if n['children'] is None else raw_tree(n['children'])
            projected.append(row)
        return projected
    original_tree = raw_tree(nodes)
    def walk(values, parent=None):
        if type(values) is not list:
            raise Stop('DIRECTORY_SCHEMA_REJECTED')
        for n in values:
            raw_id = n.get('id')
            if (type(raw_id) not in (str, int) or not str(raw_id) or
                    type(raw_id) is int and raw_id <= 0):
                raise Stop('DIRECTORY_SCHEMA_REJECTED')
            identity = str(raw_id)
            if identity in ids:
                raise Stop('DUPLICATE_DIRECTORY_ID')
            ids.add(identity)
            flag = n.get('isQuestion')
            if type(flag) not in scalar_types or type(flag) is float and not math.isfinite(flag):
                raise Stop('DIRECTORY_SCHEMA_REJECTED')
            raw = {k: scalar(n[k]) for k in ('id', 'type', 'label', 'order_in_level', 'isQuestion') if k in n}
            if _js_truthy(flag):
                derived = len(questions) + 1
                try:
                    order = number(n.get('order_in_level'))
                    order_state = 'VALID_POSITIVE_RAW_ORDER'
                except Stop:
                    order, order_state = None, 'MISSING_OR_INVALID_RAW_ORDER'
                q = {'id': identity, 'raw_node_fields': raw, 'order': order,
                    'raw_order_in_level': scalar(n.get('order_in_level')),
                    'raw_order_field_present': 'order_in_level' in n,
                    'raw_order_status': order_state, 'directory_id': parent,
                    'raw_label': scalar(n.get('label')),
                    'frontend_derived_global_order': derived, 'frontend_derived_label': str(derived),
                    'frontend_derivation': 'OFFICIAL_DFS_PRIMITIVE_TRUTHINESS_SKIP_QUESTION_DESCENDANTS',
                    'frames': [], 'frontend_derived_frame_candidates': [], 'content': content_state()}
                questions.append(q)
                if order != derived:
                    disagreements.append({'id': identity, 'raw_order': order,
                        'raw_order_status': order_state, 'frontend_derived_global_order': derived})
                continue  # Matches C0; raw_tree still preserves these children.
            directories.append({'id': identity, 'raw_node_fields': raw,
                'label': scalar(n.get('label')), 'parent': parent})
            children = n.get('children')
            if children is not None:
                walk(children, identity)
    walk(nodes)
    rows, frame_envelope = frames_rows(frames)
    by_order = {}
    for q in questions:
        if q['order'] is not None:
            by_order.setdefault(q['order'], []).append(q)
    frame_ids, orphans = set(), []
    keys = ('rect_id', 'type', 'file_id', 'belong_to_level', 'order_in_level',
        'image_order_in_annotation_zone', 'rect_bbox', 'page_index', 'parent_rect_id',
        'directory_id', 'content_type', 'is_pre_annotation', 'pre_annotations_id')
    for r in rows:
        if type(r) is not dict or type(r.get('file_id')) not in (str, int) or str(r.get('file_id')) != BOOK:
            raise Stop('FRAME_BOOK_MISMATCH')
        if type(r.get('rect_id')) is not str or not r['rect_id'] or r['rect_id'] in frame_ids:
            raise Stop('FRAME_ID_REJECTED')
        frame_ids.add(r['rect_id'])
        order = number(r.get('order_in_level'))
        copy = {k: r[k] for k in keys if k in r}
        for field, value in copy.items():
            values = value if field == 'rect_bbox' and type(value) is list else [value]
            if (field == 'rect_bbox' and type(value) is list and len(value) != 4 or
                    any(type(v) not in scalar_types or type(v) is float and not math.isfinite(v) for v in values)):
                raise Stop('FRAME_FIELD_SHAPE_REJECTED')
        if 'image_path' in r:
            copy['image_path_sha256'] = sha(_frame_text(r['image_path']).encode('utf-8'))
        if 'zone' in r:
            copy['zone'] = _frame_text(r['zone'])
        candidates = by_order.get(order, [])
        if len(candidates) == 1 and str(r.get('directory_id')) == candidates[0]['directory_id']:
            candidates[0]['frames'].append(copy)
        else:
            orphans.append(copy)
        for q in questions:
            if q['frontend_derived_global_order'] == order and str(r.get('directory_id')) == q['directory_id']:
                q['frontend_derived_frame_candidates'].append(copy)
    raw_orders = [q['order'] for q in questions if q['order'] is not None]
    duplicate_orders = sorted(k for k, values in by_order.items() if len(values) != 1)
    return {'book_id': BOOK, 'inventory_coverage': 'PARTIAL', 'content_coverage': 'UNKNOWN',
        'write_preservation_baseline': False, 'question_count_reported': book.get('question_count'),
        'question_count_observed': len(questions), 'frame_count': len(rows),
        'global_max_observed': max(raw_orders, default=None), 'append_after_order': None,
        'questions': questions, 'directories': directories, 'orphan_frames': orphans,
        'raw_directory_tree_projection': original_tree, 'raw_directory_tree_is_full_response_body': False,
        'frontend_derived_global_max': len(questions), 'raw_vs_frontend_order_disagreements': disagreements,
        'duplicate_raw_orders': duplicate_orders, 'frame_envelope': frame_envelope,
        'raw_order_or_derived_order_is_save_order': False,
        'q22_in_inventory': 22 in raw_orders, 'q22_sample_or_navigation': False}


def sample_order(state):
    for q in sorted(state['questions'], key=lambda q: q['order']):
        if q['order'] == 22:
            continue
        choices = [r for r in q['frames'] if r.get('type') == 'choice']
        if len(choices) == 4:
            indexes = [r.get('image_order_in_annotation_zone') for r in choices]
            if all(type(i) is int for i in indexes) and sorted(indexes) == [0, 1, 2, 3]:
                return q['order']
    return None


def source_page(body, viewer):
    data = body.get('data')
    if (viewer not in (14, 173) or not isinstance(data, dict) or str(data.get('file_id')) != BOOK or
            not isinstance(data.get('pages'), list) or len(data['pages']) != 1):
        raise Stop('SOURCE_PAGE_BINDING_REJECTED')
    p = data['pages'][0]
    # Viewer identity is request+UI evidence; resource index is read verbatim.
    if not isinstance(p, dict) or type(p.get('page_index')) is not int or p['page_index'] < 0 or not isinstance(p.get('image'), str):
        raise Stop('SOURCE_RESOURCE_REJECTED')
    return {'book_id': BOOK, 'viewer': viewer, 'resource_index': p['page_index'], 'url': p['image']}


def original_info(data):
    from PIL import Image, ImageFile
    if type(data) is not bytes or ImageFile.LOAD_TRUNCATED_IMAGES is not False:
        raise Stop('ORIGINAL_DECODE_CONFIGURATION_REJECTED')
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()  # Full pixel decode from these exact immutable bytes.
            width, height = img.size
            image_format = img.format
            if getattr(img, 'n_frames', 1) != 1:
                raise Stop('ORIGINAL_MULTIFRAME_UNSUPPORTED')
    except Exception:
        raise Stop('ORIGINAL_IMAGE_REJECTED') from None
    return {'width': width, 'height': height, 'format': image_format, 'size': len(data),
        'sha256': sha(data), 'full_pixel_decode': True}


def current_code(scripts):
    """Record lexical observations separately from a concrete static fetch proof."""
    from .js_wire import analyze_asset, Unsupported
    evidence, complete = [], []
    wanted = ('commit_unified_submit', 'ocr_submissions', 'ocr_result', 'rect_ids',
        'question_order', 'zone', 'get_question_info',
        'get_manual_annotations_unified_by_order_in_level', 'get-ocr-annotation')
    for asset in scripts:
        raw = asset['bytes']
        text = raw.decode('utf-8', errors='replace')
        hits = {token: [m.start() for m in re.finditer(re.escape(token), text)][:8] for token in wanted}
        try:
            proof = analyze_asset(raw, asset['ref'])
        except (Unsupported, UnicodeError) as error:
            proof = {'complete': False, 'reason': str(error) if isinstance(error, Unsupported) else 'NON_UTF8_SCRIPT'}
        evidence.append({'asset_ref': asset['ref'], 'sha256': sha(raw), 'size': len(raw),
            'token_observations_non_authorizing': hits, 'binding_analysis': proof})
        if proof.get('complete') is True:
            complete.append(proof)
    # Each complete proof is self-contained in one declaration-only module.
    # Unsupported bundling, aliases, axios/interceptors, comments and unrelated
    # matching words remain observations, never applicability confirmation.
    proof = complete[0] if complete else None
    return {'status': 'CURRENT_CODE_CONFIRMED' if proof else 'UNKNOWN',
        'read_parameters_confirmed': proof is not None,
        'content_schema_confirmed': proof is not None,
        'binding_proof': proof, 'scripts': evidence, 'save_capability': 'NOT_RUN',
        'schema_evidence': 'CURRENT_CODE_STATIC_BINDING_ONLY',
        'unsupported_boundary': 'Only explicit native-fetch GET/JSON getters plus one consistent straight call chain are supported'}


def validate_draft(draft):
    frames = draft.get('frames', [])
    if draft.get('book_id') != BOOK or len(frames) != 6 or [f.get('role') for f in frames] != ['Q', 'W', 'W', 'W', 'W', 'A']:
        raise Stop('DRAFT_ROLE_BINDING_REJECTED')
    if [f.get('choice') for f in frames[1:5]] != ['A', 'B', 'C', 'D']:
        raise Stop('DRAFT_CHOICE_ORDER_REJECTED')
    if frames[0].get('text') != '（2025·青岛城阳区期中）下列四组数能作为直角三角形的三边长的是（　）。':
        raise Stop('DRAFT_QUESTION_TEXT_MISMATCH')
    if [f.get('text') for f in frames[1:5]] != ['1，2，3', '2，3，4', '3，4，5', '4，5，6'] or frames[5].get('text') != 'C':
        raise Stop('DRAFT_CONTENT_MISMATCH')
    for f in frames:
        if f.get('viewer') != (173 if f['role'] == 'A' else 14):
            raise Stop('DRAFT_SOURCE_MISMATCH')
        box = f.get('historical_bbox_xyxy')
        if (not isinstance(box, list) or len(box) != 4 or
                any(type(v) not in (int, float) or not math.isfinite(v) for v in box) or
                not 0 <= box[0] < box[2] or not 0 <= box[1] < box[3]):
            raise Stop('DRAFT_GEOMETRY_REJECTED')
        size = next((s['dimensions'] for s in draft.get('sources', []) if s['viewer'] == f['viewer']), None)
        if size is None or box[2] > size[0] or box[3] > size[1]:
            raise Stop('DRAFT_GEOMETRY_BOUNDS_REJECTED')
    return {'status': 'HOLD_CURRENT_SOURCE_AND_NEWNESS_UNKNOWN', 'production_ready': False}
