"""Endpoint-local Hn/Mo compatibility from fixed frontend source, not live proof."""
import re
from urllib.parse import urlsplit
from .gate import BOOK, ORIGIN, Stop

OSS = 'https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com'
VIEWERS = (14, 173)
PAGE_SLOTS = {v: 'A24_CURRENT_CONTEXT_R1_PAGE' + str(v) for v in VIEWERS}
META_FIELDS = ('file_id', 'source', 'oss_page_url_pattern', 'oss_image_url_pattern', 'total_pages')


def hn(body):
    if type(body) is dict and 'code' in body:
        code = body['code']
        if type(code) not in (int, float) or code not in (0, 200):
            raise Stop('LOGIN_REQUIRED' if type(code) in (int, float) and code in (401, 403)
                else 'ENDPOINT_BUSINESS_REJECTED')
        return body.get('data'), 'NUMERIC_CODE_' + str(int(code))
    return body, 'EXPLICIT_UNWRAPPED'


def frames_rows(body):
    value, envelope = hn(body)
    if envelope != 'EXPLICIT_UNWRAPPED' and type(value) is list:
        return value, {'envelope': envelope, 'shape': 'DATA_ARRAY'}
    if type(value) is dict and type(value.get('annotations')) is list:
        return value['annotations'], {'envelope': envelope,
            'shape': 'TOP_ANNOTATIONS_ARRAY' if envelope == 'EXPLICIT_UNWRAPPED' else 'DATA_ANNOTATIONS_ARRAY'}
    raise Stop('FRAME_ENVELOPE_REJECTED')


def source_metadata(body):
    value, envelope = hn(body)
    if type(value) is not dict or (envelope == 'EXPLICIT_UNWRAPPED' and value and
            not any(field in value for field in META_FIELDS)):
        raise Stop('SOURCE_METADATA_REJECTED')
    if 'file_id' in value and (type(value['file_id']) not in (str, int) or str(value['file_id']) != BOOK):
        raise Stop('SOURCE_BOOK_MISMATCH')
    return value, {'envelope': envelope,
        'returned_file_id_status': 'MATCHED_TARGET' if 'file_id' in value else 'NOT_RETURNED',
        'request_book_binding': 'EXACT_AUTHENTICATED_SCOPED_TARGET_REQUEST'}


def public_source_url(url):
    """Canonical existing origin/book namespace only, without query or tokens."""
    try:
        if type(url) is not str or len(url) > 4096 or not url.isascii():
            raise ValueError
        p = urlsplit(url)
        if (p.scheme != 'https' or p.netloc not in (urlsplit(ORIGIN).netloc, urlsplit(OSS).netloc)
                or p.username is not None or p.password is not None or p.query or p.fragment
                or '?' in url or '#' in url or '%' in p.path or '\\' in url or '//' in p.path
                or not p.path.startswith('/upload_images/' + BOOK + '/') or p.path.endswith('/')
                or not re.fullmatch('/[A-Za-z0-9_./-]+', p.path)
                or any(part in ('.', '..') for part in p.path.split('/'))):
            raise ValueError
        if p.scheme + '://' + p.netloc + p.path != url:
            raise ValueError
    except (TypeError, ValueError, AttributeError):
        raise Stop('SOURCE_TEMPLATE_URL_REJECTED') from None
    return url


def expand_template(pattern, index):
    if (type(pattern) is not str or not pattern or type(index) is not int or index < 0
            or not ('%d' in pattern or '{pageIndex}' in pattern)):
        raise Stop('SOURCE_TEMPLATE_REJECTED')
    value = pattern.replace('%d', str(index), 1).replace('{pageIndex}', str(index), 1)
    if any(token in value for token in ('%d', '{', '}')):
        raise Stop('SOURCE_TEMPLATE_REJECTED')
    return public_source_url(value)


def page_plan(body, legacy_urls):
    data, facts = source_metadata(body)
    source = data.get('source')
    default = source is None or source is False or type(source) in (int, float) and source == 0 or source == ''
    if default or source == 'legacy_db':
        branch = 'LEGACY_DB'
        pages = {v: {'url': legacy_urls[v], 'resource_index': None,
            'index_provenance': 'REQUIRES_RETURNED_LEGACY_PAGE_INDEX'} for v in VIEWERS}
    elif source == 'oss':
        branch = 'OSS'
        pages = {v: {'url': expand_template(data.get('oss_page_url_pattern'), v - 1),
            'image_url': expand_template(data.get('oss_image_url_pattern'), v - 1),
            'resource_index': v - 1, 'index_provenance': 'FRONTEND_DERIVED_VIEWER_MINUS_ONE'} for v in VIEWERS}
        urls = [value[key] for value in pages.values() for key in ('url', 'image_url')]
        if len(set(urls)) != 4:
            raise Stop('SOURCE_TEMPLATE_AMBIGUOUS')
    else:
        raise Stop('SOURCE_BRANCH_UNSUPPORTED')
    return {'branch': branch, 'source_default_derived': default, 'source_facts': facts, 'pages': pages}


def plan_facts(plan):
    return {'schema': 'A24-current-source-plan/v1', 'branch': plan['branch'],
        'source_provenance': 'FRONTEND_DEFAULT_DERIVED' if plan['source_default_derived'] else 'EXPLICIT_SOURCE_FIELD',
        **plan['source_facts'], 'page_logical_slots': 2, 'fallback_limit': 0,
        'template_values_exported': False,
        'pages': [{'viewer': v, 'logical_slot': 'page' + str(v),
            'resource_index': plan['pages'][v]['resource_index'],
            'index_provenance': plan['pages'][v]['index_provenance'],
            'request_kind': 'SUBSTITUTED_PAGE_JSON' if plan['branch'] == 'OSS' else 'EXACT_LEGACY_PAGE_GET'} for v in VIEWERS]}


def page_blocks(body):
    if type(body) is list:
        return body, 'BARE_BLOCK_ARRAY'
    if type(body) is dict and type(body.get('blocks')) is list:
        return body['blocks'], 'EXPLICIT_BLOCKS_ARRAY'
    raise Stop('OSS_PAGE_JSON_REJECTED')


def legacy_page_data(body):
    data, envelope = hn(body)
    if type(data) is not dict:
        raise Stop('SOURCE_PAGE_BINDING_REJECTED')
    return data, envelope


def endpoint_body(name, result, page_mode=None):
    body = result.get('body')
    status = result.get('http_status')
    if status != 200:
        raise Stop('LOGIN_REQUIRED' if status in (401, 403) else 'BUSINESS_READ_FAILED')
    if name == 'frames':
        frames_rows(body)
    elif name == 'source':
        source_metadata(body)
    elif name in ('page14', 'page173'):
        page_blocks(body) if page_mode == 'OSS' else legacy_page_data(body)
    else:
        raise Stop('UNREGISTERED_BUSINESS_GET')
    return body


def oss_page_binding(body, viewer, plan, response_sha256):
    blocks, shape = page_blocks(body)
    selected = plan['pages'][viewer]
    return {'book_id': BOOK, 'viewer': viewer, 'resource_index': selected['resource_index'],
        'url': selected['image_url'], 'representation': 'FRONTEND_DERIVED',
        'returned_file_id_status': 'NOT_A_SERVER_RETURNED_IDENTITY',
        'index_provenance': 'FRONTEND_DERIVED_VIEWER_MINUS_ONE',
        'page_json_shape': shape, 'block_count': len(blocks),
        'blocks_status': 'EXPLICIT_EMPTY' if not blocks else 'EXPLICIT_PRESENT',
        'raw_page_response_sha256': response_sha256,
        'source_metadata_reference': 'response-facts-source.json',
        'image_template_reference': 'CURRENT_VALIDATED_oss_image_url_pattern'}
