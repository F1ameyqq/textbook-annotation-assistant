"""Exact GET policy plus sanitized, causally useful diagnostics."""
import re
import hashlib
from urllib.parse import urlsplit, parse_qsl
from .gate import BOOK, ORIGIN, TARGET, LOGIN, LOGIN_POST, STATIC_IMAGE_PATH_PATTERN, Stop
from .context_query import BOOK_PATH, BOOK_SLOT, validate_endpoint
from .source_contract import PAGE_SLOTS, public_source_url

PREFIX = '/qieti/api/'
FIXED = {
    'book': BOOK_PATH,  # Diagnostic route only; no book GET before page binding.
    'directory': PREFIX + 'annotate_ocr/directory/get?file_id=' + BOOK,
    'frames': PREFIX + 'annotate_pic/get_manual_annotations_unified/' + BOOK,
    'source': PREFIX + 'annotate_pic/pre_annotation_source/' + BOOK + '?annotationType=mr_pre',
    **{'page' + str(v): PREFIX + 'annotate_pic/pre_annotation/' + BOOK +
       '?pageNum=' + str(v) + '&annotationType=mr_pre' for v in (14, 173)}}
SESSION = frozenset(PREFIX + p for p in ('user_login/profile',
    'user_login/config/permissions', 'user_login/config/teams'))
STATIC = re.compile(r'/(?:qieti/)?(?:assets|static)/[^%\\]*\.(?:js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|webp)$', re.I)
PASSIVE = frozenset(('Image', 'Font', 'Media'))
OSS = 'https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com'
SAMPLE_PATHS = (
    PREFIX + 'annotate_pic/get_manual_annotations_unified_by_order_in_level',
    PREFIX + 'annotate_pic/get_question_info',
    PREFIX + 'verify_annotation/get-ocr-annotation')
EXCLUDED_STATIC = 'EXPECTED_EXCLUDED_STATIC_DENIAL'
EXCLUDED_PATH = 'EXPECTED_EXCLUDED_SAME_ORIGIN_DENIAL'
EXCLUDED_VERSION = 'EXPECTED_EXCLUDED_VERSION_REPEAT'
EXCLUSIONS = frozenset((EXCLUDED_STATIC, EXCLUDED_PATH, EXCLUDED_VERSION))
VERSION_PATH = '/qieti/version.json'


def scoped_json(category):
    return category.startswith(('BUSINESS_', 'SOURCE_PAGE_JSON_'))
PROTECTED = re.compile(r'(^|/)(?:api|login|logout|signin|signout|sign[-_]in|sign[-_]out|user[-_]login|auth|oauth)(?:/|[._-]|$)', re.I)
STATIC_IMAGE = re.compile(STATIC_IMAGE_PATH_PATTERN)


def static_image(method, url, resource_type, redirected=False):
    """Canonical single-basename assets image; frame proof belongs to barriers."""
    try:
        p = parts(url)
        return (method == 'GET' and resource_type == 'Image' and redirected is False
            and p.scheme + '://' + p.netloc == ORIGIN and '?' not in url
            and STATIC_IMAGE.fullmatch(p.path) is not None)
    except (ValueError, TypeError, AttributeError, Stop):
        return False


def version_check(method, url, resource_type, redirected=False):
    """The observed Date.now() static GET shape, never a generic JSON rule."""
    try:
        p = parts(url)
        origin, path, query = key(url)
        return (method == 'GET' and resource_type in ('XHR', 'Fetch') and redirected is False
            and origin == ORIGIN and path == VERSION_PATH and len(query) == 1
            and query[0][0] == 't' and re.fullmatch(r'[1-9][0-9]{12}', query[0][1]) is not None
            and re.fullmatch(r't=[1-9][0-9]{12}', p.query) is not None)
    except (ValueError, TypeError, AttributeError, Stop):
        return False


def excluded_same_origin(method, url, resource_type, redirected=False):
    """Only a strict unknown path can be denied without stopping; no sending."""
    try:
        origin, path, _ = key(url)
        return (method == 'GET' and resource_type in ('XHR', 'Fetch') and redirected is False
            and origin == ORIGIN and not PROTECTED.search(path)
            and path != VERSION_PATH and not path.startswith(VERSION_PATH + '/')
            and path not in {parts(ORIGIN + v).path for v in FIXED.values()}
            and not any(path == v or path.startswith(v + '/') for v in SAMPLE_PATHS))
    except (ValueError, TypeError, AttributeError, Stop):
        return False


def excluded_static(method, url, resource_type, redirected=False):
    """Classification only, never permission to send or an event counter.

    The observed path is unknown. No path is invented or fetched; API/login
    shapes cannot borrow this disposition even on the exact observed host.
    """
    try:
        p = parts(url)
        key(url)  # Retain strict query structure validation too.
        protected = re.search(r'(^|/)(?:api|login|logout|signin|sign-in|sign_in|user_login)(?:/|[._-]|$)', p.path, re.I)
        return (method == 'GET' and resource_type == 'Script' and redirected is False
            and p.hostname == 'cdn.bootcdn.net' and p.port in (None, 443)
            and p.netloc in ('cdn.bootcdn.net', 'cdn.bootcdn.net:443') and not protected)
    except (ValueError, TypeError, AttributeError, Stop):
        return False


def parts(url):
    p = urlsplit(url)
    if (p.username is not None or p.password is not None or p.fragment or
            '#' in url or not p.hostname or
            any(ord(c) <= 32 or ord(c) == 127 for c in url) or
            '%' in p.path or '\\' in p.path or '//' in p.path or
            any(x in ('.', '..') for x in p.path.split('/'))):
        raise Stop('URL_BLOCKED')
    if p.scheme != 'https' or p.port not in (None, 443):
        raise Stop('ORIGIN_BLOCKED')
    return p


def key(url):
    p = parts(url)
    pairs = parse_qsl(p.query, keep_blank_values=True, strict_parsing=True) if p.query else []
    if len(pairs) != len(set(k for k, _ in pairs)):
        raise Stop('QUERY_BLOCKED')
    return p.scheme + '://' + p.netloc, p.path, tuple(sorted(pairs))


def diagnostic(url, resource_type, category, allowed, source, redirected=False):
    """Hash unknown paths; only fixed route templates and safe query names escape."""
    endpoint = {'path_sha256': None, 'path_template': None, 'known_route': 'UNKNOWN',
        'query_parameter_names': [], 'query_names_redacted': 0}
    try:
        p = urlsplit(url)
        endpoint['path_sha256'] = hashlib.sha256(p.path.encode('utf-8')).hexdigest()
        routes = {parts(ORIGIN + path).path: name for name, path in FIXED.items()}
        routes.update({v: 'SESSION_' + v.rsplit('/', 1)[-1].upper() for v in SESSION})
        routes[VERSION_PATH] = 'VERSION_CHECK'
        routes[LOGIN_POST[len(ORIGIN):]] = 'LOGIN_POST'
        if p.path in routes:
            endpoint.update(path_template=p.path.replace(BOOK, '{book_id}'), known_route=routes[p.path])
        names = [k for k, _ in parse_qsl(p.query, keep_blank_values=True)]
        safe_names = {'t', 'page', 'pageSize', 'status_list', 'id', 'title', 'team_name',
            'username', 'role', 'is_admin', 'file_id', 'pageNum', 'annotationType', 'type', 'order_in_level'}
        endpoint['query_parameter_names'] = sorted(set(k for k in names if k in safe_names))
        endpoint['query_names_redacted'] = sum(k not in safe_names for k in names)
        host = p.hostname or ''
        host = host if re.fullmatch('[A-Za-z0-9.-]{1,253}', host) else 'REDACTED'
        scheme = p.scheme if p.scheme in ('https', 'http', 'wss', 'ws', 'data', 'blob') else 'OTHER'
        port = p.port or (443 if scheme in ('https', 'wss') else 80 if scheme in ('http', 'ws') else None)
    except (ValueError, TypeError):
        scheme, host, port = 'OTHER', 'INVALID', None
    safe_type = resource_type if resource_type in ('Document', 'XHR', 'Fetch', 'Script',
        'Stylesheet', 'Image', 'Font', 'Media', 'WebSocket', 'Other') else 'Other'
    return {**endpoint, 'scheme': scheme, 'hostname': host, 'port': port, 'resource_type': safe_type,
        'category': category, 'decision': 'ALLOW' if allowed else 'BLOCK', 'source': source,
        'redirect_hop': bool(redirected), 'main_navigation': safe_type == 'Document',
        'business_read': category.startswith('BUSINESS_'), 'scoped_source_read': scoped_json(category),
        'expected_passive_denial': category == 'EXPECTED_PASSIVE_DENIAL',
        'expected_excluded_static_denial': category == EXCLUDED_STATIC,
        'expected_excluded_path_denial': category == EXCLUDED_PATH,
        'expected_excluded_version_repeat': category == EXCLUDED_VERSION}


class ReadPolicy:
    def __init__(self):
        self.business = {key(ORIGIN + path): name for name, path in FIXED.items()
            if name not in ('book', 'page14', 'page173')}
        self.request_urls = {key(ORIGIN + path): ORIGIN + path for name, path in FIXED.items()
            if name not in ('book', 'page14', 'page173')}
        self.originals = {}
        self.sample_order = None
        self._book_endpoint = None  # Sensitive, transient process memory only.
        self.book_binding_attempted = False
        self.book_read_started = False
        self.page_binding_attempted = False
        self._page_urls = {}
        self.page_modes = {}

    def bind_book_query(self, endpoint):
        if self.book_binding_attempted or self.book_read_started:
            raise Stop('BOOK_CONTEXT_REBIND_BLOCKED')
        self.book_binding_attempted = True  # Reserve before validation/any await.
        validate_endpoint(endpoint)
        self._book_endpoint = endpoint
        bound_key = key(ORIGIN + endpoint)
        self.business[bound_key] = 'book'
        self.request_urls[bound_key] = BOOK_SLOT

    def begin_book_read(self, endpoint):
        if (self._book_endpoint is None or endpoint != self._book_endpoint or self.book_read_started):
            raise Stop('BOOK_CONTEXT_READ_INTENT_REJECTED')
        self.book_read_started = True

    def bind_pages(self, plan):
        if self.page_binding_attempted:
            raise Stop('SOURCE_PAGE_REBIND_BLOCKED')
        self.page_binding_attempted = True
        if (type(plan) is not dict or plan.get('branch') not in ('OSS', 'LEGACY_DB') or
                set(plan.get('pages', {})) != {14, 173}):
            raise Stop('SOURCE_PAGE_PLAN_REJECTED')
        selected = {}
        for viewer in (14, 173):
            url = plan['pages'][viewer].get('url')
            if plan['branch'] == 'OSS':
                public_source_url(url)
            elif url != ORIGIN + FIXED['page' + str(viewer)]:
                raise Stop('SOURCE_PAGE_PLAN_REJECTED')
            if url in selected or key(url) in self.business:
                raise Stop('SOURCE_PAGE_PLAN_REJECTED')
            selected[url] = 'page' + str(viewer)
        for url, name in selected.items():
            self.business[key(url)] = name
            self.request_urls[key(url)] = PAGE_SLOTS[int(name[4:])]
            self.page_modes[name] = plan['branch']
        self._page_urls = selected

    def public_page(self, url):
        return (url in self._page_urls and self.page_modes[self._page_urls[url]] == 'OSS'
            and parts(url).scheme + '://' + parts(url).netloc == OSS)

    def register_sample(self, order, current_code):
        # Unconditional for this candidate: no schema/proof/flag can enable it.
        raise Stop('SAMPLE_DISABLED_OBSERVATION_ONLY')

    def register_original(self, url, book, viewer, resource, response_ref):
        p = parts(url)
        if (book != BOOK or type(viewer) is not int or viewer not in (14, 173) or
                type(resource) is not int or resource < 0 or not response_ref or
                p.scheme + '://' + p.netloc not in (ORIGIN, OSS) or
                not p.path.startswith('/upload_images/' + BOOK + '/') or p.query or
                viewer in self.originals or url in self.originals.values()):
            raise Stop('ORIGINAL_SOURCE_BINDING_REJECTED')
        self.originals[viewer] = url

    def decide(self, method, url, resource_type, redirected=False):
        # A22 has no login capability, even with old approval or injected intent.
        if method not in ('GET', 'HEAD'):
            return False, 'METHOD_BLOCKED'
        try:
            p = parts(url)
            origin = p.scheme + '://' + p.netloc
            if any(p.path == prefix or p.path.startswith(prefix + '/') for prefix in SAMPLE_PATHS):
                return False, 'SAMPLE_DISABLED_OBSERVATION_ONLY'
            if resource_type == 'Document':
                return (True, 'NAVIGATION') if method == 'GET' and url == TARGET else (False, 'NAVIGATION_BLOCKED')
            if excluded_static(method, url, resource_type, redirected):
                return False, EXCLUDED_STATIC
            if url in self.originals.values() and method == 'GET':
                return True, 'REGISTERED_ORIGINAL'
            if url in self._page_urls:
                name = self._page_urls[url]
                category = ('SOURCE_PAGE_JSON_' if self.page_modes[name] == 'OSS' else 'BUSINESS_') + name.upper()
                return (True, category) if method == 'GET' and not redirected else (False, 'SOURCE_PAGE_REQUEST_BLOCKED')
            if origin != ORIGIN:
                # Only unredirected passive subresources may be denied without
                # stopping the task. The precise A17 script exclusion above is
                # also denied; all other external script/CSS/XHR/WS stop.
                return (False, 'EXPECTED_PASSIVE_DENIAL') if resource_type in PASSIVE and not redirected else (False, 'ORIGIN_BLOCKED')
            key(url)  # Strict query structure also applies to unknown same-origin paths.
            if p.path == VERSION_PATH or p.path.startswith(VERSION_PATH + '/'):
                return (True, 'VERSION_CHECK') if version_check(method, url, resource_type, redirected) else (False, 'VERSION_CHECK_BLOCKED')
            if p.path == BOOK_PATH:
                return ((True, 'BUSINESS_BOOK') if method == 'GET' and not redirected
                    and self._book_endpoint is not None and self.book_read_started
                    and url == ORIGIN + self._book_endpoint else (False, 'BOOK_CONTEXT_QUERY_BLOCKED'))
            if key(url) in self.business and method == 'GET':
                return True, 'BUSINESS_' + self.business[key(url)].upper()
            if p.path in SESSION and not p.query:
                return (True, 'SESSION_GET') if method == 'GET' else (False, 'METHOD_BLOCKED')
            if static_image(method, url, resource_type, redirected):
                return True, 'STATIC'
            if PROTECTED.search(p.path):
                return False, 'API_BLOCKED'
            if not p.query and (STATIC.fullmatch(p.path) or p.path in ('/favicon.ico', '/qieti/favicon.ico')):
                return True, 'STATIC'
            return False, 'PATH_BLOCKED'
        except (ValueError, TypeError, Stop):
            return False, 'URL_BLOCKED'
