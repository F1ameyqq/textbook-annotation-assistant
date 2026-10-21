"""A15: one explicitly activated context certificate exception. Import is inert.

Default CLI only verifies the frozen candidate. No credentials, login fallback,
APIRequestContext or browser/profile inspection on import. Default TLS is strict.
"""
from __future__ import annotations

import argparse
import asyncio
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/A15/certificate-exception'
MANIFEST = EVIDENCE / 'candidate-manifest.json'
LIVE_OUT = Path('D:/1800/.local/stages/a15-cert-reuse-live')
ACTIVATION_FILE = Path('D:/1800/.local/stages/a15-cert-reuse-activation.json')
PROFILE_ROOT = Path('D:/1800/.local/browser-profiles')
TARGET = 'https://www.usense.com/qieti/annotateUnified'
ORIGIN = 'https://www.usense.com'
VIEWER_MARKER = '.pdf-zones-container:visible'
PASSWORD = 'input[placeholder="请输入密码"]:visible'
NAV_SECONDS = 45
WORKER_SECONDS = 75
HARD_SECONDS = 85
TASK = 'A15'
WORKFLOW = 'ec69a4bfd72b64e3bd6c6435ef0ec780fd109249'
USER_DECISION_SHA = '36ffcbb42c030192313773b510c69598651b2c2ffe5fb54162c46b8041e40763'
PROPOSAL_SHA = 'eb6aea7ad9b01ccbcaf7710c9c45d7c5c3a80d6efcef4db857838d204d725656'
COORDINATOR = '01a15768-1e2d-7781-b29f-1f7376270216'
RUN_ID = 'A15-cert-reuse-01a157fd-c8e7-71e1-881a-7f766b4af082'
STATIC = re.compile(r'/(?:qieti/)?(?:assets|static)/[^%\\]*\.(?:js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|webp)$', re.I)
SESSION = frozenset('/qieti/api/' + p for p in (
    'user_login/profile', 'user_login/config/permissions', 'user_login/config/teams'))


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save_new(path, value):
    data = (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8')
    with Path(path).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


class StopProbe(Exception):
    pass


def safe_error(error):
    kind = type(error).__name__
    known = {'TimeoutError', 'Error', 'OSError', 'ValueError', 'ImportError',
             'ModuleNotFoundError', 'StopProbe', 'CheckFailure', 'CancelledError'}
    text = str(error)
    codes = [code for code in ('ERR_CERT_COMMON_NAME_INVALID', 'ERR_CERT_AUTHORITY_INVALID',
             'ERR_CERT_DATE_INVALID', 'ERR_CONNECTION_RESET', 'ERR_CONNECTION_TIMED_OUT',
             'ERR_NAME_NOT_RESOLVED', 'ERR_BLOCKED_BY_CLIENT', 'ERR_FAILED') if code in text]
    # Only our enumerated stop values can leave the exception boundary.
    if isinstance(error, StopProbe) and re.fullmatch('[A-Z_]{1,80}', text):
        codes.append(text)
    return {'exception_type': kind if kind in known else 'OTHER', 'codes': codes or ['UNKNOWN']}


def candidate(expected=None):
    raw = MANIFEST.read_bytes()
    actual = digest(raw)
    if expected is not None and expected != actual:
        raise StopProbe('CANDIDATE_DIGEST_MISMATCH')
    manifest = json.loads(raw)
    if manifest['workflow_commit'] != WORKFLOW or manifest['task'] != TASK:
        raise StopProbe('WORKFLOW_MISMATCH')
    for item in manifest['members']:
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise StopProbe('CANDIDATE_PATH_REJECTED')
        member = ROOT / relative
        if member.is_symlink() or digest(member.read_bytes()) != item['sha256']:
            raise StopProbe('CANDIDATE_MEMBER_MISMATCH')
    return actual


@dataclass(frozen=True)
class GateApproval:
    candidate_sha256: str
    profile_fingerprint: str
    activation_sha256: str
    not_before: datetime
    expires_at: datetime
    ignore_https_errors: bool = False


def parse_utc(value):
    if not isinstance(value, str) or not re.fullmatch(
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)', value):
        raise StopProbe('ACTIVATION_TIME_REJECTED')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise StopProbe('ACTIVATION_TIME_REJECTED') from None


def validate_activation(raw, expected_sha, candidate_sha, profile_fingerprint,
                        explicit_exception=False, explicit_live=False, now=None):
    """Pure gate. No filesystem, subprocess, native API, browser or profile access."""
    if explicit_live is not True or explicit_exception is not True:
        raise StopProbe('EXPLICIT_ACTIVATION_REQUIRED')
    if not isinstance(raw, bytes) or not isinstance(expected_sha, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha):
        raise StopProbe('ACTIVATION_DIGEST_REQUIRED')
    if digest(raw) != expected_sha:
        raise StopProbe('ACTIVATION_DIGEST_MISMATCH')
    if (not isinstance(candidate_sha, str) or not re.fullmatch('[0-9a-f]{64}', candidate_sha) or
            not isinstance(profile_fingerprint, str) or not re.fullmatch('[0-9a-f]{64}', profile_fingerprint)):
        raise StopProbe('EXPLICIT_LIVE_BINDING_REQUIRED')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise StopProbe('ACTIVATION_JSON_REJECTED')
            result[key] = value
        return result
    try:
        activation = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise StopProbe('ACTIVATION_JSON_REJECTED') from None
    fixed = {'schema': 'A15-live-activation/v1', 'task': TASK, 'workflow_commit': WORKFLOW,
        'user_decision_sha256': USER_DECISION_SHA, 'proposal_sha256': PROPOSAL_SHA,
        'candidate_manifest_sha256': candidate_sha, 'coordinator_thread_id': COORDINATOR,
        'run_id': RUN_ID, 'target': TARGET, 'certificate_exception': True,
        'profile_fingerprint': profile_fingerprint, 'output_directory': LIVE_OUT.as_posix(),
        'new_live_limit': 1, 'context_limit': 1, 'navigation_limit': 1,
        'login_submission_limit': 0, 'business_write_limit': 0, 'old_budgets_restored': False,
        'independent_preflight': 'ACCEPTED_OFFLINE_ONLY'}
    if type(activation) is not dict or set(activation) != set(fixed) | {
            'not_before', 'expires_at', 'independent_report_sha256'}:
        raise StopProbe('ACTIVATION_FIELDS_REJECTED')
    for key, value in fixed.items():
        if type(activation[key]) is not type(value) or activation[key] != value:
            raise StopProbe('ACTIVATION_BINDING_MISMATCH')
    if (not isinstance(activation['independent_report_sha256'], str) or
            not re.fullmatch('[0-9a-f]{64}', activation['independent_report_sha256'])):
        raise StopProbe('INDEPENDENT_PREFLIGHT_BINDING_REQUIRED')
    start, end = parse_utc(activation['not_before']), parse_utc(activation['expires_at'])
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or not 0 < (end - start).total_seconds() <= 900 or not start <= now < end:
        raise StopProbe('ACTIVATION_WINDOW_REJECTED')
    return GateApproval(candidate_sha, profile_fingerprint, expected_sha, start, end, True)


def context_options(approval=None, now=None):
    """Only a still-current validated result can opt this one context into the exception."""
    if approval is None:
        return {'ignore_https_errors': False}
    now = datetime.now(timezone.utc) if now is None else now
    if (type(approval) is not GateApproval or approval.ignore_https_errors is not True or
            not approval.not_before <= now < approval.expires_at):
        raise StopProbe('CONTEXT_APPROVAL_REJECTED')
    return {'ignore_https_errors': True}


def marker_value(approval):
    if type(approval) is not GateApproval or approval.ignore_https_errors is not True:
        raise StopProbe('MARKER_APPROVAL_REQUIRED')
    return {'task': TASK, 'run_id': RUN_ID, 'candidate_sha256': approval.candidate_sha256,
        'profile_fingerprint': approval.profile_fingerprint,
        'activation_sha256': approval.activation_sha256, 'certificate_exception': True,
        'target': TARGET, 'context_limit': 1, 'navigation_limit': 1,
        'login_submission_limit': 0, 'business_write_limit': 0}


def claim_marker(path, approval, now=None):
    """Generic exclusive byte marker; offline checks use only a synthetic directory."""
    try:
        context_options(approval, now=now)
        save_new(path, marker_value(approval))
    except FileExistsError:
        raise StopProbe('ACTIVATION_ALREADY_CLAIMED') from None


def require_marker(name, approval):
    try:
        value = json.loads((LIVE_OUT / name).read_bytes())
    except (OSError, ValueError):
        raise StopProbe('PARENT_CLAIM_REQUIRED') from None
    if value != marker_value(approval):
        raise StopProbe('PARENT_CLAIM_MISMATCH')


def add_arguments(parser):
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--certificate-exception', action='store_true')
    parser.add_argument('--activation-file')
    parser.add_argument('--activation-sha256')
    parser.add_argument('--candidate-sha256')
    parser.add_argument('--profile-fingerprint')


def validate_cli_fields(args):
    """Pure rejection before even opening the activation file."""
    if (args.live is not True or args.certificate_exception is not True or
            not args.activation_file or not args.activation_sha256 or not args.candidate_sha256):
        raise StopProbe('EXPLICIT_ACTIVATION_REQUIRED')
    if args.activation_file != ACTIVATION_FILE.as_posix():
        raise StopProbe('ACTIVATION_PATH_REJECTED')
    for value in (args.activation_sha256, args.candidate_sha256, args.profile_fingerprint):
        if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
            raise StopProbe('EXPLICIT_LIVE_BINDING_REQUIRED')


def authorize_args(args):
    # Every CLI entry, including occupancy and worker, executes this gate first.
    validate_cli_fields(args)
    actual = candidate(args.candidate_sha256)
    try:
        require_plain_path(ACTIVATION_FILE)
        raw = Path(args.activation_file).read_bytes()
    except OSError:
        raise StopProbe('ACTIVATION_FILE_REQUIRED') from None
    return validate_activation(raw, args.activation_sha256, actual, args.profile_fingerprint,
        explicit_exception=args.certificate_exception, explicit_live=args.live)


def require_plain_path(path, missing_leaf=False):
    """Runtime path checks only, after the explicit field gate; no profile access."""
    for component in (path,) + tuple(path.parents):
        try:
            info = component.lstat()
        except FileNotFoundError:
            if component == path and missing_leaf:
                continue
            raise StopProbe('ACTIVATION_PATH_UNPROVEN') from None
        if component.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise StopProbe('ACTIVATION_REPARSE_REJECTED')


def activation_argv(args):
    return ['--live', '--certificate-exception', '--activation-file', args.activation_file,
        '--activation-sha256', args.activation_sha256, '--candidate-sha256', args.candidate_sha256,
        '--profile-fingerprint', args.profile_fingerprint]


def reported_stop(output):
    """Retain enumerated child gate failures without exporting arbitrary output."""
    try:
        error = json.loads(output)['error']
        if (type(error) is dict and set(error) == {'exception_type', 'codes'} and
                error['exception_type'] in ('StopProbe', 'OSError', 'Error', 'OTHER') and
                type(error['codes']) is list and 0 < len(error['codes']) < 10 and
                all(type(code) is str and re.fullmatch('[A-Z_]{1,80}', code) for code in error['codes'])):
            return error
    except (ValueError, TypeError, KeyError):
        pass
    return None


class NativePolicy:
    """Narrower than frozen A04: navigation/static/session only, no book data.

    Source: A04 6c8137a4... runtime/browser/guard.py _STATIC, _parts,
    RequestPolicy._api (only SESSION_PROFILE/PERMISSIONS/TEAMS retained).
    The reviewed OSS origin authorizes registered book images only; no such
    registration exists in this probe, so OSS and all other origins stay denied.
    """
    def __init__(self, fixture_origin=None):
        self.origin = fixture_origin or ORIGIN
        self.fixture = fixture_origin is not None

    def decide(self, method, url, resource_type):
        if method not in ('GET', 'HEAD'):
            return False, 'METHOD_BLOCKED'
        try:
            p = urlsplit(url)
            origin = p.scheme + '://' + p.netloc
            if (p.username is not None or p.password is not None or p.fragment or
                    any(ord(x) < 32 or ord(x) == 127 for x in url) or
                    '%' in p.path or '\\' in p.path or '//' in p.path or
                    any(x in ('.', '..') for x in p.path.split('/'))):
                return False, 'URL_BLOCKED'
            if origin != self.origin:
                return False, 'ORIGIN_BLOCKED'
            if self.fixture:
                return True, 'FIXTURE_GET'
            if p.scheme != 'https' or p.port not in (None, 443):
                return False, 'ORIGIN_BLOCKED'
            if p.query:
                return False, 'QUERY_BLOCKED'
            nav = p.path in ('/qieti', '/qieti/', '/qieti/login', '/qieti/annotateUnified')
            if resource_type == 'Document':
                return (True, 'NAVIGATION') if nav else (False, 'NAVIGATION_BLOCKED')
            if p.path in SESSION:
                return True, 'SESSION_GET'
            if '/api/' in p.path or p.path.endswith('/api'):
                return False, 'API_BLOCKED'
            if STATIC.fullmatch(p.path) or p.path in ('/favicon.ico', '/qieti/favicon.ico'):
                return True, 'STATIC'
            return False, 'PATH_BLOCKED'
        except (ValueError, TypeError):
            return False, 'URL_BLOCKED'


class NativeGuard:
    """Fetch Request-stage pauses include redirect hops; no route.fetch used.

    Context routing is an additional first-request barrier for unexpected pages,
    frames and workers. CDP Fetch is the native transport authority for every
    owned main-page hop. Related targets wait for debugger and are closed without
    resuming. WebSockets are mocked closed before any server connection.
    """
    def __init__(self, context, page, policy):
        self.context, self.page, self.policy = context, page, policy
        self.session = None
        self.events = []
        self.tasks = set()
        self.failure = None
        self.stopped = False
        self.terminal_stopped = False
        self.shutdown_started = False
        self.expected_block = False

    def record_failure(self, error):
        # Later callbacks or shutdown errors must never replace the first error.
        if self.failure is None:
            self.failure = safe_error(error)
        self.terminal_stopped = self.stopped = True

    def begin_shutdown(self):
        if not self.shutdown_started and self.stopped:
            self.terminal_stopped = True
        self.shutdown_started = True
        self.stopped = True

    def note(self, method, category, allowed, source, redirected=False):
        self.events.append({'time': utc(), 'method': method if method in
            ('GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'WEBSOCKET') else 'OTHER',
            'category': category, 'decision': 'ALLOW' if allowed else 'BLOCK',
            'source': source, 'redirect_hop': redirected})

    def schedule(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        def done(value):
            if not value.cancelled() and value.exception() is not None:
                self.record_failure(value.exception())
        task.add_done_callback(done)

    def block_seen(self):
        if not self.expected_block:
            self.terminal_stopped = self.stopped = True

    async def route(self, route):
        request = route.request
        try:
            owned = request.frame == self.page.main_frame
        except Exception:
            owned = False
        allowed, category = self.policy.decide(request.method, request.url,
                                               request.resource_type.title())
        if not owned:
            allowed, category = False, 'UNOWNED_TARGET_BLOCKED'
        if self.stopped:
            allowed, category = False, 'STOPPED'
        self.note(request.method, category, allowed, 'CONTEXT_FIRST_REQUEST')
        try:
            if allowed:
                # This does not enforce redirects; Fetch.requestPaused below does.
                await route.continue_()
            else:
                self.block_seen()
                await route.abort('blockedbyclient')
        except BaseException as error:
            self.record_failure(error)

    async def websocket(self, route):
        self.note('WEBSOCKET', 'WEBSOCKET_BLOCKED', False, 'PRECONNECT_WEBSOCKET_ROUTE')
        self.block_seen()
        # Do not call connect_to_server: Playwright's routed socket has no
        # server-side connection until explicitly requested.
        try:
            await route.close(code=1008, reason='A12 read only')
        except BaseException as error:
            self.record_failure(error)

    async def paused(self, event):
        request = event['request']
        allowed, category = self.policy.decide(request['method'], request['url'], event['resourceType'])
        if self.stopped:
            allowed, category = False, 'STOPPED'
        self.note(request['method'], category, allowed, 'FETCH_REQUEST_STAGE',
                  bool(event.get('redirectedRequestId')))
        if allowed:
            await self.session.send('Fetch.continueRequest', {'requestId': event['requestId']})
        else:
            self.block_seen()
            await self.session.send('Fetch.failRequest', {'requestId': event['requestId'],
                                                         'errorReason': 'BlockedByClient'})

    async def child_target(self, event):
        self.note('OTHER', 'RELATED_TARGET_BLOCKED', False, 'TARGET_PAUSED_BEFORE_RESUME')
        self.block_seen()
        # No Runtime.runIfWaitingForDebugger or resume message is ever sent.
        result = await self.session.send('Target.closeTarget', {'targetId': event['targetInfo']['targetId']})
        if not result.get('success'):
            raise StopProbe('CHILD_TARGET_CLOSE_UNPROVEN')

    async def install(self):
        await self.context.route_web_socket('**/*', self.websocket)
        await self.context.route('**/*', self.route)
        self.session = await self.context.new_cdp_session(self.page)
        self.session.on('Fetch.requestPaused', lambda event: self.schedule(self.paused(event)))
        self.session.on('Target.attachedToTarget', lambda event: self.schedule(self.child_target(event)))
        await self.session.send('Target.setAutoAttach', {'autoAttach': True,
            'waitForDebuggerOnStart': True, 'flatten': False})
        await self.session.send('Network.enable')
        await self.session.send('Network.setCacheDisabled', {'cacheDisabled': True})
        await self.session.send('Fetch.enable', {'patterns': [{'urlPattern': '*', 'requestStage': 'Request'}],
                                               'handleAuthRequests': False})


async def open_owned(profile, policy, state, approval=None):
    if approval is None:
        raise StopProbe('CONTEXT_APPROVAL_REQUIRED')
    context_options(approval)
    from playwright.async_api import async_playwright
    runtime = await async_playwright().start()
    state['runtime'] = runtime
    options = context_options(approval)
    context = await runtime.chromium.launch_persistent_context(str(profile), channel='msedge',
        headless=True, offline=True, service_workers='block', **options,
        accept_downloads=False, viewport={'width': 1440, 'height': 1000}, timeout=15000,
        args=['--disable-session-crashed-bubble', '--disable-extensions'])
    state['context'] = context
    state['release']['context_created'] = True
    pages = context.pages
    if len(pages) != 1 or pages[0].url != 'about:blank':
        raise StopProbe('STARTUP_PAGE_STATE_UNEXPECTED')
    page = pages[0]
    page.set_default_timeout(3000)
    page.on('dialog', lambda dialog: asyncio.create_task(dialog.dismiss()))
    guard = NativeGuard(context, page, policy)
    state['guard'] = guard
    await guard.install()
    # New page targets are denied by the context first-request barrier; close
    # only the exact new page handle, and never create a second page ourselves.
    context.on('page', lambda extra: guard.schedule(extra.close()))
    await context.set_offline(False)
    return page, guard


async def close_owned(state):
    release = state['release']
    if state.get('context') is not None:
        release['context_close_attempted'] = True
        try:
            await asyncio.wait_for(state['context'].close(), 5)
            release['context_closed'] = True
        except BaseException as error:
            release['errors'].append(safe_error(error))
    if state.get('runtime') is not None:
        release['runtime_stop_attempted'] = True
        try:
            await asyncio.wait_for(state['runtime'].stop(), 3)
            release['runtime_stopped'] = True
        except BaseException as error:
            release['errors'].append(safe_error(error))
    release['state'] = ('RELEASED' if release['context_closed'] and release['runtime_stopped']
                        and not release['errors'] else 'UNKNOWN')


def initial_release():
    return {'context_created': False, 'context_close_attempted': False, 'context_closed': False,
            'runtime_stop_attempted': False, 'runtime_stopped': False, 'errors': [], 'state': 'NOT_CREATED'}


def load_native():
    # Raw reviewed dependencies, never the former browser/driver entry points.
    sys.path.insert(0, str(EVIDENCE / 'reviewed-native'))
    from native_windows import WindowsAPI
    from process_check import count_profile
    return WindowsAPI, count_profile


def profile_binding():
    # Python 3.9's is_symlink alone does not cover every Windows junction.
    for component in (PROFILE_ROOT, PROFILE_ROOT.parent, PROFILE_ROOT.parent.parent):
        if component.is_symlink() or component.lstat().st_file_attributes & 0x400:
            raise StopProbe('PROFILE_ROOT_REPARSE_REJECTED')
    if not PROFILE_ROOT.is_dir() or str(PROFILE_ROOT.resolve()).lower() != str(PROFILE_ROOT).lower():
        raise StopProbe('PROFILE_ROOT_REJECTED')
    children = [p for p in PROFILE_ROOT.iterdir() if p.is_dir()]
    if len(children) != 1:
        raise StopProbe('PROFILE_COUNT_REJECTED')
    profile = children[0]
    if (profile.is_symlink() or profile.lstat().st_file_attributes & 0x400 or
            not re.fullmatch('[0-9a-f]{20}', profile.name) or
            profile.resolve().parent != PROFILE_ROOT.resolve()):
        raise StopProbe('PROFILE_IDENTITY_REJECTED')
    info = profile.stat()
    fingerprint = digest(('A12_PROFILE_V1\0' + profile.name + '\0' + str(info.st_dev) + '\0' + str(info.st_ino)).encode('utf-8'))
    return profile, fingerprint


def emit_occupancy_count(value):
    """One compact ASCII JSON record with binary LF, never Windows text CRLF."""
    if type(value) is not int or value < 0:
        raise StopProbe('PROFILE_OCCUPANCY_UNPROVEN')
    payload = (json.dumps({'count': value}, separators=(',', ':')) + '\n').encode('ascii')
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def accept_occupancy_zero(output, errors, exit_code):
    # This protocol deliberately permits only the canonical single zero record.
    if errors or exit_code != 0 or output != b'{"count":0}\n':
        raise StopProbe('PROFILE_OCCUPANCY_UNPROVEN')
    return 0


def occupancy(profile, approval, args):
    api_class, _ = load_native()
    api = api_class()
    environment = dict(os.environ)
    environment['A15_PRIVATE_PROFILE'] = str(profile)
    child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--_occupancy'] + activation_argv(args),
        env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=0x08000000)
    record = {'limit_seconds': 4, 'before': api.held_identity(int(child._handle)), 'timeout': False}
    try:
        output, errors = child.communicate(input=b'A15_OCCUPANCY\n', timeout=4)
        accept_occupancy_zero(output, errors, child.returncode)
        record['matching_processes'] = 0
    except subprocess.TimeoutExpired:
        record['timeout'] = True
        raise StopProbe('PROFILE_CHECK_TIMEOUT') from None
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=1)
        record['after'] = api.held_identity(int(child._handle))
        for stream in (child.stdin, child.stdout, child.stderr):
            if not stream.closed:
                stream.close()
        child._handle.Close()
        record['handle_closed'] = True
        save_new(LIVE_OUT / 'occupancy.json', record)
    # Known profile locks are never removed; ambiguous presence fails closed.
    if any((profile / name).exists() for name in ('SingletonLock', 'SingletonCookie', 'lockfile')):
        raise StopProbe('PROFILE_LOCK_PRESENT')


def initial_observation():
    return {'outcome': 'UNKNOWN', 'successors': 'NOT_RUN', 'navigation_intents': 0,
            'login_submissions': 0, 'business_writes': 0, 'navigation_limit_seconds': NAV_SECONDS,
            'started_at': utc(), 'error': None, 'observation_error': None, 'guard_failure': None}


def guard_snapshot(guard):
    return {'stopped': guard.stopped, 'shutdown_started': guard.shutdown_started,
            'terminal_stopped': guard.terminal_stopped or (guard.stopped and not guard.shutdown_started),
            'failure': guard.failure, 'pending_tasks': sum(not task.done() for task in guard.tasks)}


def require_running_guard(guard):
    if guard.stopped or guard.failure is not None:
        raise StopProbe('NETWORK_GUARD_STOPPED')


def apply_terminal_guard(result, snapshot):
    if snapshot['failure'] is not None and result['guard_failure'] is None:
        result['guard_failure'] = snapshot['failure']
    if snapshot['terminal_stopped'] or snapshot['failure'] is not None:
        result['outcome'] = 'ERROR'
        result['successors'] = 'NOT_RUN'
        if result['error'] is None:
            result['error'] = result['guard_failure'] or safe_error(StopProbe('NETWORK_GUARD_STOPPED'))
        elif (result['error']['codes'] == ['NETWORK_GUARD_STOPPED'] and
              result['guard_failure'] is not None):
            result['error'] = result['guard_failure']


def record_observation_error(result, state, error):
    result['observation_error'] = safe_error(error)
    if state.get('guard') is not None:
        apply_terminal_guard(result, guard_snapshot(state['guard']))
    result['outcome'] = 'ERROR'
    if result['error'] is None:
        result['error'] = result['observation_error']


async def observe_page(page, guard, result):
    # Shared by the real observer and the bounded in-memory delta driver.
    require_running_guard(guard)
    navigation_start = time.monotonic()
    result['navigation_intents'] = 1
    await page.goto(TARGET, wait_until='domcontentloaded', timeout=NAV_SECONDS * 1000)
    # One shared navigation/readiness deadline; no second navigation/reload.
    while time.monotonic() - navigation_start < NAV_SECONDS:
        require_running_guard(guard)
        password = await page.get_by_placeholder('请输入密码', exact=True).is_visible()
        require_running_guard(guard)
        if password:
            result['outcome'] = 'LOGIN_REQUIRED'
            break
        parts = urlsplit(page.url)
        route_ok = (parts.scheme == 'https' and parts.netloc == 'www.usense.com' and
                    parts.path == '/qieti/annotateUnified')
        viewer = await page.locator(VIEWER_MARKER).first.is_visible()
        require_running_guard(guard)
        if route_ok and viewer and not password:
            result['outcome'] = 'AUTHENTICATED_VIEWER'
            break
        await asyncio.sleep(0.1)
    else:
        raise StopProbe('VIEWER_OBSERVATION_TIMEOUT')


async def finalize_observation(state, result, output_path):
    guard = state.get('guard')
    if guard is not None:
        result['guard_state_pre_shutdown'] = guard_snapshot(guard)
        apply_terminal_guard(result, result['guard_state_pre_shutdown'])
        guard.begin_shutdown()
    await close_owned(state)
    if guard is not None:
        # Give completed guard callbacks their turn after the close awaits.
        await asyncio.sleep(0)
        for task in tuple(guard.tasks):
            if task.done() and not task.cancelled() and task.exception() is not None:
                guard.record_failure(task.exception())
            elif not task.done():
                guard.record_failure(StopProbe('NETWORK_GUARD_TASKS_PENDING'))
                task.cancel()
        await asyncio.sleep(0)
        result['network_audit'] = list(guard.events)
    result['release'] = state['release']
    result['finished_at'] = utc()
    # No await occurs between this authoritative check and serialization.
    if guard is not None:
        result['guard_state_at_serialization'] = guard_snapshot(guard)
        apply_terminal_guard(result, result['guard_state_at_serialization'])
    if result['release']['errors']:
        result['outcome'] = 'ERROR'
        if result['error'] is None:
            result['error'] = result['release']['errors'][0]
    save_new(output_path, result)
    return 0 if result['outcome'] in ('LOGIN_REQUIRED', 'AUTHENTICATED_VIEWER') else 2


async def observe_live(profile, approval):
    state = {'release': initial_release()}
    result = initial_observation()
    try:
        page, guard = await open_owned(profile, NativePolicy(), state, approval)
        await observe_page(page, guard, result)
    except BaseException as error:
        record_observation_error(result, state, error)
    finally:
        exit_code = await finalize_observation(state, result, LIVE_OUT / 'observation.json')
    return exit_code


class OwnedJob:
    """Windows Job contains only a gated Popen child and its descendants."""
    def __init__(self):
        if os.name != 'nt':
            raise StopProbe('WINDOWS_REQUIRED')
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        specs = {
            'CreateJobObjectW': ([c.c_void_p, w.LPCWSTR], w.HANDLE),
            'SetInformationJobObject': ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD], w.BOOL),
            'AssignProcessToJobObject': ([w.HANDLE, w.HANDLE], w.BOOL),
            'QueryInformationJobObject': ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p], w.BOOL),
            'TerminateJobObject': ([w.HANDLE, w.UINT], w.BOOL),
            'CloseHandle': ([w.HANDLE], w.BOOL)}
        for name, (args, restype) in specs.items():
            getattr(self.kernel, name).argtypes = args
            getattr(self.kernel, name).restype = restype
        class Basic(c.Structure):
            _fields_ = [('per_process', c.c_longlong), ('per_job', c.c_longlong),
                ('flags', w.DWORD), ('minimum', c.c_size_t), ('maximum', c.c_size_t),
                ('active', w.DWORD), ('affinity', c.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class IO(c.Structure):
            _fields_ = [(key, c.c_ulonglong) for key in ('read', 'write', 'other', 'readbytes', 'writebytes', 'otherbytes')]
        class Extended(c.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_mem', c.c_size_t), ('job_mem', c.c_size_t),
                        ('peak_process', c.c_size_t), ('peak_job', c.c_size_t)]
        limits = Extended()
        limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE; breakaway is not enabled.
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise StopProbe('OWNED_JOB_CREATE_FAILED')
        if not self.kernel.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)):
            self.close()
            raise StopProbe('OWNED_JOB_CONFIG_FAILED')

    def assign(self, child):
        if not self.kernel.AssignProcessToJobObject(self.handle, int(child._handle)):
            raise StopProbe('OWNED_JOB_ASSIGN_FAILED')

    def active(self):
        class Accounting(c.Structure):
            _fields_ = [('user', c.c_longlong), ('kernel', c.c_longlong), ('period_user', c.c_longlong),
                ('period_kernel', c.c_longlong), ('faults', w.DWORD), ('total', w.DWORD),
                ('active', w.DWORD), ('terminated', w.DWORD)]
        info = Accounting()
        if not self.kernel.QueryInformationJobObject(self.handle, 1, c.byref(info), c.sizeof(info), None):
            raise StopProbe('OWNED_JOB_QUERY_FAILED')
        return int(info.active)

    def terminate(self):
        if not self.kernel.TerminateJobObject(self.handle, 73):
            raise StopProbe('OWNED_JOB_TERMINATE_FAILED')

    def close(self):
        if self.handle:
            handle, self.handle = self.handle, None
            if not self.kernel.CloseHandle(handle):
                raise StopProbe('OWNED_JOB_CLOSE_FAILED')


def supervise(command, output_dir, limit=WORKER_SECONDS, hard_deadline=None):
    api_class, _ = load_native()
    api = api_class()
    started = time.monotonic()
    hard_deadline = started + HARD_SECONDS if hard_deadline is None else hard_deadline
    worker_deadline = min(started + limit, hard_deadline - 6)
    record = {'started_at': utc(), 'limit_seconds': limit, 'hard_limit_seconds': HARD_SECONDS,
              'gated_before_job_assignment': True, 'errors': [], 'job_assigned': False,
              'job_active_final': None, 'worker_handle_closed': False, 'job_closed': False}
    job = child = None
    try:
        job = OwnedJob()
        if time.monotonic() >= worker_deadline:
            raise StopProbe('PRODUCT_DEADLINE_EXPIRED')
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, creationflags=0x08000000, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        record['before'] = api.held_identity(int(child._handle))
        job.assign(child)
        record['job_assigned'] = True
        # Worker cannot touch browser, network or profile before this exact gate.
        child.stdin.write(b'GO\n')
        child.stdin.flush()
        output, errors = child.communicate(timeout=max(0.01, worker_deadline - time.monotonic()))
        record['stdout_bytes'] = len(output)
        record['stderr_bytes'] = len(errors)
        if output or errors:
            record['errors'].append({'codes': ['UNEXPECTED_WORKER_OUTPUT'],
                                     'reported_error': reported_stop(output)})
    except subprocess.TimeoutExpired:
        record['errors'].append({'codes': ['OWNED_WORKER_TIMEOUT']})
    except BaseException as error:
        record['errors'].append(safe_error(error))
    finally:
        if child is not None:
            try:
                if child.poll() is None:
                    if record['job_assigned']:
                        job.terminate()
                    else:
                        child.kill()
                    child.wait(timeout=2)
                record['after'] = api.held_identity(int(child._handle))
                if record['before']['created_filetime'] != record['after']['created_filetime']:
                    raise StopProbe('OWNED_WORKER_IDENTITY_MISMATCH')
            except BaseException as error:
                record['errors'].append(safe_error(error))
            finally:
                for stream in (child.stdin, child.stdout, child.stderr):
                    if stream is not None and not stream.closed:
                        stream.close()
                child._handle.Close()
                record['worker_handle_closed'] = True
        if job is not None:
            try:
                count = job.active()
                record['job_active_before_final_cleanup'] = count
                if count:
                    job.terminate()
                    deadline = time.monotonic() + 2
                    while count and time.monotonic() < deadline:
                        time.sleep(0.02)
                        count = job.active()
                record['job_active_final'] = count
            except BaseException as error:
                record['errors'].append(safe_error(error))
            finally:
                job.close()
                record['job_closed'] = True
        record['duration_ms'] = round((time.monotonic() - started) * 1000)
        record['hard_deadline_exceeded'] = time.monotonic() > hard_deadline
        record['finished_at'] = utc()
        record['state'] = ('RELEASED' if record['job_active_final'] == 0 and
            record['worker_handle_closed'] and record['job_closed'] and
            record.get('after', {}).get('exit_observed') else 'UNKNOWN')
        save_new(Path(output_dir) / 'worker-release.json', record)
    return record


def worker_main(approval, args, worker_deadline):
    if sys.stdin.readline() != 'GO\n':
        return 71
    try:
        approval = authorize_args(args)
        require_marker('live-started.json', approval)
        claim_marker(LIVE_OUT / 'worker-claimed.json', approval)
        if time.monotonic() >= worker_deadline - 10:
            raise StopProbe('WORKER_DEADLINE_EXPIRED')
        profile, fingerprint = profile_binding()
        if approval.profile_fingerprint != fingerprint:
            raise StopProbe('PROFILE_BINDING_MISMATCH')
        save_new(LIVE_OUT / 'profile-binding.json', {'fingerprint': fingerprint,
            'existing_directory_count': 1, 'origin': 'DEDICATED_PROFILE_ROOT', 'time': utc()})
        occupancy(profile, approval, args)
        for key in ('DEBUG', 'PWDEBUG'):
            os.environ.pop(key, None)
        async def bounded():
            return await asyncio.wait_for(observe_live(profile, approval),
                timeout=max(0.01, worker_deadline - time.monotonic() - 9))
        return asyncio.run(bounded())
    except BaseException as error:
        save_new(LIVE_OUT / 'preflight-failure.json', {'outcome': 'ERROR', 'error': safe_error(error),
            'navigation_intents': 0, 'successors': 'NOT_RUN', 'time': utc()})
        return 2


def main(argv=None):
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    parser.add_argument('--_launched', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--_worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--_occupancy', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not (args.live or args._worker or args._occupancy or args._launched):
        actual = candidate(args.candidate_sha256)
        print(json.dumps({'mode': 'STATIC_ONLY', 'candidate_sha256': actual,
            'ignore_https_errors': False, 'profile_read': False, 'browser_started': False,
            'network_started': False}))
        return 0
    approval = authorize_args(args)
    if args._occupancy:
        try:
            if sys.stdin.readline() != 'A15_OCCUPANCY\n':
                raise StopProbe('OCCUPANCY_PARENT_GATE_REQUIRED')
            approval = authorize_args(args)
            require_marker('worker-claimed.json', approval)
            claim_marker(LIVE_OUT / 'occupancy-claimed.json', approval)
            profile, fingerprint = profile_binding()
            if fingerprint != approval.profile_fingerprint or os.environ.pop('A15_PRIVATE_PROFILE', '') != str(profile):
                raise StopProbe('PROFILE_BINDING_MISMATCH')
            api_class, count = load_native()
            value = count(api_class(), str(profile))
            emit_occupancy_count(value)
            return 0
        except BaseException:
            return 2
    if args._worker:
        return worker_main(approval, args, started + WORKER_SECONDS)
    if not args._launched or sys.stdin.readline() != 'A15_LAUNCH\n':
        raise StopProbe('OUTER_LAUNCHER_REQUIRED')
    approval = authorize_args(args)
    require_marker('launcher-claimed.json', approval)
    claim_marker(LIVE_OUT / 'live-started.json', approval)
    record = supervise([sys.executable, '-B', str(Path(__file__).resolve()), '--_worker'] +
        activation_argv(args), LIVE_OUT, hard_deadline=started + HARD_SECONDS)
    print(json.dumps({'mode': 'LIVE_FINISHED', 'release': record['state'],
                     'worker_exit_code': record.get('after', {}).get('exit_code'),
                     'result_file': 'observation.json', 'errors': bool(record['errors'])}))
    return 0 if (record['state'] == 'RELEASED' and not record['errors'] and not record['hard_deadline_exceeded'] and
                 record.get('after', {}).get('exit_code') == 0) else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except StopProbe as error:
        print(json.dumps({'outcome': 'ERROR', 'error': safe_error(error)}))
        raise SystemExit(2)
