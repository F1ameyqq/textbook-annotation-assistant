"""A23 bounded current-session completion; credentials and login are disabled.

Existing page-local session material may serve approved GETs. It is never
returned, copied to Python, logged, or used to perform a new login.
"""
from .gate import TARGET, ORIGIN, Stop, unique_json
from .policy import SESSION

FORM = '.login-wrapper .login-container .login-form'
VIEWER = '.pdf-zones-container:visible'
MAX_AUTH_BYTES = 128 * 1024


def credentials_from_bytes(raw):
    raise Stop('CREDENTIAL_READ_DISABLED_REUSE_ONLY')


def read_credentials(*args, **kwargs):
    # Reject before path validation, filesystem I/O, parsing or form work.
    raise Stop('CREDENTIAL_READ_DISABLED_REUSE_ONLY')


def response_projection(raw, status, login=False, session_route=None):
    """Only a finite projection of a current approved session response escapes."""
    if login:
        raise Stop('LOGIN_DISABLED_REUSE_ONLY')
    if type(status) is not int or status != 200:
        raise Stop('AUTH_HTTP_REJECTED' if status in (401, 403) else 'AUTH_HTTP_FAILED')
    if not isinstance(raw, bytes) or len(raw) > MAX_AUTH_BYTES:
        raise Stop('AUTH_RESPONSE_SIZE_REJECTED')
    try:
        body = unique_json(raw)
    except Stop:
        raise Stop('AUTH_RESPONSE_JSON_REJECTED') from None
    if type(body) is not dict:
        raise Stop('AUTH_RESPONSE_SHAPE_REJECTED')
    code = body.get('code')
    numeric = type(code) in (int, float)
    if numeric and code not in (0, 200):
        raise Stop('AUTH_BUSINESS_REJECTED')
    data = body.get('data') if numeric else body
    if session_route not in {path.rsplit('/', 1)[-1] for path in SESSION} or not numeric or type(data) not in (dict, list):
        raise Stop('SESSION_RESULT_UNKNOWN')
    identity = (session_route == 'profile' and type(data) is dict and
                type(data.get('id')) in (str, int) and bool(data['id']) and
                type(data.get('username')) is str and bool(data['username'].strip()))
    return {'http_status': 200, 'business_decode': 'ACCEPTED_NUMERIC_CODE',
            'credential_return_present': 'NOT_INSPECTED',
            'authenticated_profile_fields_present': identity}


class AuthFlow:
    def __init__(self):
        self.phase = 'VIEWER'
        self.navigation_intents = []
        self.navigation_counts = {'native': 0, 'context': 0}
        self.session_seen = {'native': set(), 'context': set()}
        self.session_responses = set()
        self.session_receipts = []
        self.active_profile_intents = 0
        self.completion_mode = 'NOT_STARTED'
        self.reused = False
        self.authenticated = False

    def arm_navigation(self, url):
        if self.phase != 'VIEWER' or self.navigation_intents or url != TARGET:
            raise Stop('AUTH_NAVIGATION_SEQUENCE_REJECTED')
        self.navigation_intents.append(url)

    def reserve_navigation(self, layer, url):
        if (self.phase != 'VIEWER' or layer not in self.navigation_counts or
                self.navigation_intents != [TARGET] or url != TARGET or self.navigation_counts[layer] != 0):
            raise Stop('EXTRA_NAVIGATION_BLOCKED')
        self.navigation_counts[layer] += 1  # Reserve before either barrier awaits.

    def arm_submit(self, *args, **kwargs):
        raise Stop('LOGIN_DISABLED_REUSE_ONLY')

    def reserve_login(self, *args, **kwargs):
        raise Stop('LOGIN_DISABLED_REUSE_ONLY')

    def reserve_session(self, layer, url):
        if (self.phase != 'VIEWER' or layer not in self.session_seen or
                self.navigation_intents != [TARGET] or self.navigation_counts[layer] != 1 or
                url not in {ORIGIN + path for path in SESSION}):
            raise Stop('SESSION_PATH_REJECTED')
        item = ('VIEWER', url)
        if item in self.session_seen[layer] or len(self.session_seen[layer]) >= 3:
            raise Stop('SESSION_AUTOMATIC_RESEND_BLOCKED')
        self.session_seen[layer].add(item)

    def arm_active_profile(self):
        # Synchronous intent before evaluate/any await. Existing reservations,
        # including a one-layer UNKNOWN, can never be repaired by another GET.
        if (self.phase != 'VIEWER' or self.active_profile_intents or
                self.session_responses or any(self.session_seen.values()) or
                any(n != 1 for n in self.navigation_counts.values())):
            raise Stop('ACTIVE_SESSION_INTENT_REJECTED')
        self.active_profile_intents = 1
        self.completion_mode = 'ACTIVE_PROFILE'

    def record_session(self, url, projection):
        item = ('VIEWER', url)
        if (self.phase != 'VIEWER' or item in self.session_responses or
                any(item not in seen for seen in self.session_seen.values()) or
                type(projection) is not dict or set(projection) != {'http_status', 'business_decode',
                    'credential_return_present', 'authenticated_profile_fields_present'} or
                type(projection['http_status']) is not int or projection['http_status'] != 200 or
                projection['business_decode'] != 'ACCEPTED_NUMERIC_CODE' or
                projection['credential_return_present'] != 'NOT_INSPECTED' or
                type(projection['authenticated_profile_fields_present']) is not bool):
            raise Stop('SESSION_RESPONSE_ASSOCIATION_UNPROVEN')
        self.session_responses.add(item)
        self.session_receipts.append({'phase': 'VIEWER', 'route': url.rsplit('/', 1)[-1], **projection})

    def admit_viewer(self):
        # collect first checks original page/frame, exact TARGET, visible viewer
        # and absence of login/password forms. No historical receipt loader exists.
        if (self.phase != 'VIEWER' or self.navigation_intents != [TARGET] or
                any(value != 1 for value in self.navigation_counts.values()) or
                not self.session_responses or any(phase != 'VIEWER' or
                    any((phase, url) not in seen for seen in self.session_seen.values())
                    for phase, url in self.session_responses)):
            raise Stop('PROTECTED_AUTHENTICATION_UNPROVEN')
        self.reused = self.authenticated = True

    def snapshot(self):
        profiles = [r for r in self.session_receipts if r['route'] == 'profile']
        return {'phase': self.phase, 'session_phase_limit': 1,
            'local_credential_config_read_limit': 0, 'local_credential_config_reads': 0,
            'login_submit_limit': 0, 'native_post_reservations': 0, 'context_post_reservations': 0,
            'actual_login_post_requests': 0, 'reused_without_credentials': self.reused,
            'existing_session_material_usage': 'IN_PAGE_APPROVED_GET_ONLY',
            'viewer_access_confirmed': self.authenticated,
            'protected_viewer_authenticated': self.authenticated,
            'account_identity_fields_available': (profiles[0]['authenticated_profile_fields_present']
                if profiles else 'NOT_OBSERVED'),
            'navigation_intents': len(self.navigation_intents),
            'navigation_reservations': dict(self.navigation_counts),
            'session_receipts': list(self.session_receipts),
            'active_profile_intents': self.active_profile_intents,
            'session_completion_mode': self.completion_mode,
            'session_completion_timeout_seconds': 20}


async def known_form(*args, **kwargs):
    raise Stop('LOGIN_DISABLED_REUSE_ONLY')


def safe_environment(environment):
    return {k: v for k, v in environment.items() if k.upper() not in ('DEBUG', 'PWDEBUG', 'DEBUG_FILE')}
