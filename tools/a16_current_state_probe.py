"""A24 session reuse and grouped readonly reader; inert by default.

Live code requires coordinator activation bound to the standing readonly permission.
No credential values, profile files, browser or native APIs are touched on import.
"""
from __future__ import annotations
import argparse
import asyncio
import base64
import json
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from functools import wraps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
_spec = importlib.util.spec_from_file_location('a16_fixed_native_a15',
    ROOT / 'docs/evidence/A16/current-readonly/dependencies/a15_native_reference.py')
native = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = native
_spec.loader.exec_module(native)  # Fixed raw blob, not the CRLF checkout variant.
native.ROOT = ROOT
native.EVIDENCE = ROOT / 'docs/evidence/A15/certificate-exception'
from annotation.source.usense.current_readonly.gate import (
    TASK, WORKFLOW, SCOPE, OWNER, RUN_ID, BOOK, VIEWERS, ORIGIN, TARGET, OUTPUT, ACTIVATION,
    DECISION, REPORT, EXCLUDED_STATIC_LIMIT, VERSION_CHECK_LIMIT,
    Approval, Stop, sha, is_sha, unique_json, validate_activation, context_options, marker,
    scope_binding, same_typed, LOGIN, LOGIN_POST, PROFILE_FINGERPRINT)
from annotation.source.usense.current_readonly.auth import (
    AuthFlow, FORM, VIEWER, MAX_AUTH_BYTES,
    known_form, read_credentials, response_projection, safe_environment)
from annotation.source.usense.current_readonly.policy import (
    ReadPolicy, FIXED, key, diagnostic, EXCLUDED_STATIC, EXCLUDED_PATH, EXCLUDED_VERSION,
    EXCLUSIONS, excluded_static, excluded_same_origin, version_check, SESSION, scoped_json)
from annotation.source.usense.current_readonly.decode import (
    business, book_identity, inventory, source_page, original_info, response_facts)
from annotation.source.usense.current_readonly.context_query import BOOK_SLOT, PREPARE_JS, SEND_JS
from annotation.source.usense.current_readonly.source_contract import (
    endpoint_body, page_plan, plan_facts, oss_page_binding, frames_rows, legacy_page_data)

LIVE_OUT = Path(OUTPUT)
ACTIVATION_FILE = Path(ACTIVATION)
MANIFEST = ROOT / 'docs/evidence/A24/revisions/current-context-r1/candidate-manifest.json'
TOTAL_SECONDS, WORKER_SECONDS, HARD_SECONDS = 900, 870, 890
StopProbe, OwnedJob, load_native = Stop, native.OwnedJob, native.load_native
utc, save_new, require_plain_path = native.utc, native.save_new, native.require_plain_path
digest = sha


NET_CODES = ('ERR_CERT_COMMON_NAME_INVALID', 'ERR_CERT_AUTHORITY_INVALID',
    'ERR_CERT_DATE_INVALID', 'ERR_CONNECTION_RESET', 'ERR_CONNECTION_TIMED_OUT',
    'ERR_NAME_NOT_RESOLVED', 'ERR_BLOCKED_BY_CLIENT', 'ERR_FAILED', 'ERR_ABORTED',
    'ERR_PROXY_CONNECTION_FAILED', 'ERR_TUNNEL_CONNECTION_FAILED', 'ERR_SSL_PROTOCOL_ERROR',
    'ERR_HTTP_RESPONSE_CODE_FAILURE', 'ERR_CONNECTION_CLOSED', 'ERR_CONNECTION_REFUSED',
    'ERR_EMPTY_RESPONSE', 'ERR_NETWORK_CHANGED', 'ERR_INTERNET_DISCONNECTED',
    'ERR_ADDRESS_UNREACHABLE')
ERROR_TYPES = {'TimeoutError', 'Error', 'OSError', 'ValueError', 'ImportError',
    'ModuleNotFoundError', 'StopProbe', 'CheckFailure', 'CancelledError', 'TargetClosedError'}
BLOCKED_REASONS = {'other', 'csp', 'mixed-content', 'origin', 'inspector', 'subresource-filter',
    'content-type', 'coep-frame-resource-needs-coep-header', 'coop-sandboxed-iframe-cannot-navigate-to-coop-page',
    'corp-not-same-origin', 'corp-not-same-origin-after-defaulted-to-same-origin-by-coep', 'corp-not-same-site'}


SAFE_STOP_CODES = frozenset(('VIEWER_DOCUMENT_RESPONSE_UNPROVEN', 'BOOK_IDENTITY_REJECTED', 'BUSINESS_READ_FAILED', 'CREDENTIAL_READ_DISABLED_REUSE_ONLY', 'LOGIN_DISABLED_REUSE_ONLY', 'VIEWER_ORIGINAL_FRAME_UNPROVEN', 'CURRENT_CONTRACT_AND_FIRST_SAVE_PREPARATION_READONLY', 'ACCEPTED_NUMERIC_CODE', 'ACCEPTED_OFFLINE_ONLY', 'ACCEPTED_UNWRAPPED', 'ACTIVATION_ALREADY_CLAIMED', 'ACTIVATION_BINDING_MISMATCH', 'ACTIVATION_DIGEST_MISMATCH', 'ACTIVATION_DIGEST_REQUIRED', 'ACTIVATION_FIELDS_REJECTED', 'ACTIVATION_FILE_REQUIRED', 'ACTIVATION_JSON_REJECTED', 'ACTIVATION_PATH_REJECTED', 'ACTIVATION_PATH_UNPROVEN', 'ACTIVATION_REMAINING_TIME_INSUFFICIENT', 'ACTIVATION_REPARSE_REJECTED', 'ACTIVATION_TIME_REJECTED', 'ACTIVATION_WINDOW_REJECTED', 'ALLOW', 'API_BLOCKED', 'AUTHENTICATED_VIEWER', 'AUTHENTICATION_RECOVERY_STATIC_IMAGE_CLASSIFICATION', 'AUTH_BUSINESS_REJECTED', 'AUTH_HTTP_FAILED', 'AUTH_HTTP_REJECTED', 'AUTH_NAVIGATION_SEQUENCE_REJECTED', 'AUTH_OPERATION_TIMEOUT', 'AUTH_RESPONSE_FRAME_UNPROVEN', 'AUTH_RESPONSE_JSON_REJECTED', 'AUTH_RESPONSE_SHAPE_REJECTED', 'AUTH_RESPONSE_SIZE_REJECTED', 'BLOCK', 'BODY_UNKNOWN_SAMPLE_DISABLED', 'BOOK_PICKER_IDENTITY_UNPROVEN', 'BUSINESS_', 'BUSINESS_BEFORE_AUTHENTICATION_BLOCKED', 'BUSINESS_DUPLICATE_IN_FLIGHT_BLOCKED', 'CALLBACK_AFTER_SETTLEMENT', 'CANDIDATE_BINDING_REJECTED', 'CANDIDATE_DEPENDENCY_REQUIRED', 'CANDIDATE_DIGEST_MISMATCH', 'CANDIDATE_MEMBER_MISMATCH', 'CANDIDATE_PATH_REJECTED', 'CAPTURED_UNREVIEWED', 'CHILD_TARGET_CLOSE_UNPROVEN', 'COMMANDLINE_BUFFER_INVALID', 'COMMANDLINE_INVALID', 'COMMANDLINE_QUOTING', 'COMMANDLINE_SIZE_UNAVAILABLE', 'COMMANDLINE_UNREADABLE', 'COMPLETE', 'CONTEXT_APPROVAL_REJECTED', 'CONTEXT_APPROVAL_REQUIRED', 'CONTEXT_EXCEPTION', 'CONTEXT_FIRST_REQUEST', 'CREDENTIAL_CONFIG_REJECTED', 'CREDENTIAL_PROFILE_MISMATCH', 'CREDENTIAL_READ_NOT_AUTHORIZED', 'CURRENT_RESPONSE', 'CURRENT_SOURCE_RESPONSE', 'DEBUG', 'DEBUG_FILE', 'DEDICATED_PROFILE_ROOT', 'DELETE', 'DONE', 'DUPLICATE_JSON_KEY', 'ENUMERATION_CHANGED', 'ENUMERATION_INCOMPLETE', 'ENUMERATION_INVALID', 'ENUMERATION_UNAVAILABLE', 'ERROR', 'ERR_ABORTED', 'ERR_ADDRESS_UNREACHABLE', 'ERR_BLOCKED_BY_CLIENT', 'ERR_CERT_AUTHORITY_INVALID', 'ERR_CERT_COMMON_NAME_INVALID', 'ERR_CERT_DATE_INVALID', 'ERR_CONNECTION_CLOSED', 'ERR_CONNECTION_REFUSED', 'ERR_CONNECTION_RESET', 'ERR_CONNECTION_TIMED_OUT', 'ERR_EMPTY_RESPONSE', 'ERR_FAILED', 'ERR_HTTP_RESPONSE_CODE_FAILURE', 'ERR_INTERNET_DISCONNECTED', 'ERR_NAME_NOT_RESOLVED', 'ERR_NETWORK_CHANGED', 'ERR_PROXY_CONNECTION_FAILED', 'ERR_SSL_PROTOCOL_ERROR', 'ERR_TUNNEL_CONNECTION_FAILED', 'EXCLUDED_REQUEST_RESPONSE_OBSERVED', 'EXCLUDED_STATIC_CLASSIFICATION_UNPROVEN', 'EXCLUDED_STATIC_EVENT_LIMIT', 'EXCLUDED_STATIC_RESPONSE_OBSERVED', 'EXISTING_GET_RESPONSE_UNPROVEN', 'EXPECTED_EXCLUDED_SAME_ORIGIN_DENIAL', 'EXPECTED_EXCLUDED_STATIC_DENIAL', 'EXPECTED_EXCLUDED_VERSION_REPEAT', 'EXPECTED_PASSIVE_DENIAL', 'EXPLICIT_ACTIVATION_REQUIRED', 'EXPLICIT_LIVE_BINDING_REQUIRED', 'EXPLICIT_PUBLIC_SOURCE_FIELDS_ONLY', 'EXTRA_NAVIGATION_BLOCKED', 'FAILED', 'FETCH_REQUEST_STAGE', 'FINAL_NAVIGATION_IDENTITY_MISMATCH', 'FIXTURE_GET', 'GET', 'GUARD_STOPPED', 'HANDLE_CLOSE_FAILED', 'HEAD', 'HOLD_CONTENT_DIRECTORY_GEOMETRY_AND_SAVE_READBACK_REQUIRED', 'INDEPENDENT_PREFLIGHT_BINDING_REQUIRED', 'INSPECTION_INCOMPLETE', 'INVALID', 'JPEG', 'JSON_REJECTED', 'LIVE_FINISHED', 'LOCAL_CAPTURE_REUSE', 'LOGIN', 'LOGIN_DOCUMENT_ASSOCIATION_UNPROVEN', 'LOGIN_DOCUMENT_RESPONSE_UNPROVEN', 'LOGIN_FORM_OR_EXTRA_AUTH_UNPROVEN', 'LOGIN_INTENT_REJECTED', 'LOGIN_NOT_CONFIRMED', 'LOGIN_ORIGINAL_FRAME_UNPROVEN', 'LOGIN_ORIGIN_OR_PATH_MISMATCH', 'LOGIN_OR_AUTHENTICATED_MARKER_UNPROVEN', 'LOGIN_POST', 'LOGIN_POST_NOT_AUTHORIZED', 'LOGIN_POST_ORIGIN_UNPROVEN', 'LOGIN_POST_PAYLOAD_REJECTED', 'LOGIN_REQUIRED', 'LOGIN_RESPONSE_ASSOCIATION_UNPROVEN', 'LOGIN_RESULT_UNKNOWN', 'LOGIN_UI_REJECTED', 'MARKER_APPROVAL_REQUIRED', 'METHOD_BLOCKED', 'NATIVE_GET_CAPTURE_MISSING', 'NATIVE_MAIN_FRAME_IDENTITY_CHANGED', 'NATIVE_MAIN_FRAME_IDENTITY_UNPROVEN', 'NAVIGATION', 'NAVIGATION_BLOCKED', 'NETWORK_CALLBACK_CANCELLED', 'NETWORK_GUARD_STOPPED', 'NETWORK_GUARD_TASKS_PENDING', 'NEW_QUESTION_CONTENT_DIRECTORY_GEOMETRY_UNVERIFIED', 'NOT_CREATED', 'NOT_INSPECTED', 'NOT_RUN', 'NOT_STARTED', 'NO_ALLOWED_SCRIPT_CAPTURED', 'NO_NETWORK_FETCH_FULFILL', 'NO_NETWORK_FULFILL', 'OBSERVATION_ONLY_SCOPE', 'OBSERVATION_SCOPE_BINDING_REQUIRED', 'OCCUPANCY_PARENT_GATE_REQUIRED', 'OFFICIAL_UI_BUTTON', 'OPTIONS', 'ORIGINAL_FRAME_RESERVED_NETWORK_ID', 'ORIGINAL_GET_FAILED', 'ORIGINAL_MAIN_DOCUMENT_NETWORK_ID', 'ORIGINAL_SOURCE_BINDING_REJECTED', 'ORIGIN_BLOCKED', 'OTHER', 'OUTER_LAUNCHER_REQUIRED', 'OWNED_JOB_ASSIGN_FAILED', 'OWNED_JOB_CLOSE_FAILED', 'OWNED_JOB_CONFIG_FAILED', 'OWNED_JOB_CREATE_FAILED', 'OWNED_JOB_QUERY_FAILED', 'OWNED_JOB_TERMINATE_FAILED', 'OWNED_WORKER_IDENTITY_MISMATCH', 'OWNED_WORKER_IDENTITY_UNPROVEN', 'OWNED_WORKER_TIMEOUT', 'OWN_PROCESS_MONOTONIC', 'PARENT_CLAIM_MISMATCH', 'PARENT_CLAIM_REQUIRED', 'PATCH', 'PATH_BLOCKED', 'PNG', 'POST', 'PRECONNECT_WEBSOCKET_ROUTE', 'PROCESS_EXIT_UNPROVEN', 'PROCESS_GONE', 'PROCESS_IDENTITY_CHANGED', 'PROCESS_NAME_UNAVAILABLE', 'PROCESS_STATE_UNKNOWN', 'PROCESS_TIMES_UNAVAILABLE', 'PROCESS_UNREADABLE_OR_GONE', 'PRODUCT_DEADLINE_EXPIRED', 'PROFILE_ALIAS_UNPROVEN', 'PROFILE_ARGUMENT_DUPLICATE', 'PROFILE_ARGUMENT_MISSING', 'PROFILE_BINDING_MISMATCH', 'PROFILE_CHECK_TIMEOUT', 'PROFILE_COUNT_REJECTED', 'PROFILE_IDENTITY_REJECTED', 'PROFILE_LOCK_PRESENT', 'PROFILE_NOT_ABSOLUTE', 'PROFILE_OCCUPANCY_UNPROVEN', 'PROFILE_ROOT_REJECTED', 'PROFILE_ROOT_REPARSE_REJECTED', 'PROFILE_SYNTAX', 'PROTECTED_AUTHENTICATION_UNPROVEN', 'PUT', 'PWDEBUG', 'PYTHONIOENCODING', 'QUERY_BLOCKED', 'READONLY_REVIEW', 'READONLY_REVIEW_WITH_GAPS', 'READ_RESPONSE_FAILED', 'READ_SCHEMA_UNVERIFIED', 'REDACTED', 'REDIRECT_BLOCKED', 'REGISTERED_', 'REGISTERED_ORIGINAL', 'REGISTERED_READ_REDIRECT_BLOCKED', 'RELATED_TARGET_BLOCKED', 'RELEASED', 'RELEASE_UNPROVEN', 'RESPONSE_SIZE_LIMIT', 'RUNNING', 'SAMPLE_DISABLED_OBSERVATION_ONLY', 'SCRIPT_CONTROLLED_OUTPUT_REQUIRED', 'SEALED', 'SESSION_', 'SESSION_AUTOMATIC_RESEND_BLOCKED', 'SESSION_GET', 'SESSION_NETWORK_ASSOCIATION_UNPROVEN', 'SESSION_PATH_REJECTED', 'SESSION_RESPONSE_ASSOCIATION_UNPROVEN', 'SESSION_RESULT_UNKNOWN', 'SHUTDOWN', 'SOURCE_BOOK_MISMATCH', 'STARTED', 'STARTUP_PAGE_STATE_UNEXPECTED', 'STATIC', 'STATIC_ONLY', 'STOPPED', 'STOP_NO_RESEND', 'STRICT', 'TARGET_PAUSED_BEFORE_RESUME', 'TIME_REJECTED', 'UNEXPECTED_WORKER_OUTPUT', 'UNKNOWN', 'UNOWNED_TARGET_BLOCKED', 'UNREGISTERED_BUSINESS_GET', 'URL_BLOCKED', 'VERSION_CHECK', 'VERSION_CHECK_BLOCKED', 'VERSION_CHECK_CLASSIFICATION_UNPROVEN', 'VIEWER', 'VIEWER_OBSERVATION_TIMEOUT', 'VISIBLE_BOOK_IDENTITY_MISMATCH', 'VISIBLE_CONTAINER', 'VISIBLE_SOURCE_MAPPING_UNPROVEN', 'WEBP', 'WEBSOCKET', 'WEBSOCKET_BLOCKED', 'WINDOWS_REQUIRED', 'WORKER_DEADLINE_EXPIRED', 'WORKFLOW_MISMATCH', 'XHR'))


SAFE_STOP_CODES |= frozenset(('ACTIVE_SESSION_INTENT_REJECTED', 'SESSION_COMPLETION_TIMEOUT', 'SESSION_NETWORK_FAILED'))
SAFE_STOP_CODES |= frozenset(('BOOK_DATA_CONTAINER_REJECTED', 'BOOK_LIST_CONTAINER_REJECTED',
    'BOOK_LIST_ITEM_SCHEMA_REJECTED', 'BOOK_TARGET_ABSENT', 'BOOK_TARGET_CONFLICT', 'BOOK_TITLE_MISSING',
    'BUSINESS_RESPONSE_JSON_REJECTED'))
SAFE_STOP_CODES |= frozenset(('BOOK_CONTEXT_UNSUPPORTED', 'BOOK_CONTEXT_QUERY_REJECTED',
    'BOOK_CONTEXT_REBIND_BLOCKED', 'BOOK_CONTEXT_READ_INTENT_REJECTED', 'BOOK_CONTEXT_QUERY_BLOCKED',
    'BOOK_CONTEXT_ORIGINAL_FRAME_REQUIRED', 'BOOK_CONTEXT_PREPARATION_REJECTED',
    'BOOK_CONTEXT_UNAVAILABLE', 'BOOK_CONTEXT_MALFORMED', 'BOOK_CONTEXT_CHANGED',
    'BOOK_CONTEXT_GET_RESULT_UNKNOWN', 'BOOK_SLOT_ALREADY_RESERVED'))
SAFE_STOP_CODES |= frozenset(('ENDPOINT_BUSINESS_REJECTED', 'FRAME_ENVELOPE_REJECTED',
    'SOURCE_METADATA_REJECTED', 'SOURCE_TEMPLATE_URL_REJECTED', 'SOURCE_TEMPLATE_REJECTED',
    'SOURCE_TEMPLATE_AMBIGUOUS', 'SOURCE_BRANCH_UNSUPPORTED', 'SOURCE_PAGE_REBIND_BLOCKED',
    'SOURCE_PAGE_PLAN_REJECTED', 'SOURCE_PAGE_REQUEST_BLOCKED', 'OSS_PAGE_JSON_REJECTED',
    'SOURCE_PAGE_BINDING_REJECTED', 'SOURCE_BOOK_MISMATCH', 'DIRECTORY_SCHEMA_REJECTED',
    'FRAME_BOOK_MISMATCH', 'FRAME_ID_REJECTED', 'FRAME_FIELD_SHAPE_REJECTED', 'QUESTION_ORDER_REJECTED'))


def net_codes(value):
    # Finite output vocabulary, with token boundaries. Never echo an ERR_* match.
    text = value if isinstance(value, str) else ''
    return [code for code in NET_CODES if re.search(r'(?<![A-Z0-9_])' + code + r'(?![A-Z0-9_])', text)] or ['UNKNOWN']


def safe_error(error):
    if isinstance(error, (Stop, native.StopProbe)) and str(error) in SAFE_STOP_CODES:
        return {'exception_type': 'Stop' if isinstance(error, Stop) else 'StopProbe', 'codes': [str(error)]}
    kind = type(error).__name__
    return {'exception_type': kind if kind in ERROR_TYPES else 'OTHER', 'codes': net_codes(str(error))}


def http_status(value):
    return int(value) if type(value) in (int, float) and 100 <= value <= 599 and value == int(value) else None


class NavigationEvidence:
    """Only the original navigation, bounded synchronous telemetry; no I/O.

    CDP identities stay in memory. Missing association and missing events are
    unknown facts, never status zero or proof that no request was sent.
    """
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.started = None
        self.network_id = None
        self.frame_id = None
        self.data = {'clock': 'OWN_PROCESS_MONOTONIC', 'phase': 'NOT_STARTED',
            'goto': {'state': 'NOT_RUN', 'wait_until': 'domcontentloaded', 'timeout_ms': 45000,
                'elapsed_ms': None, 'response_returned': 'UNKNOWN', 'http_status': None, 'error': None},
            'readiness': {'state': 'NOT_RUN', 'wait_until': 'VISIBLE_CONTAINER', 'timeout_ms': 30000,
                'elapsed_ms': None, 'error': None},
            'domcontentloaded_observed': False, 'domcontentloaded_elapsed_ms': None,
            'association': 'UNKNOWN', 'response_received': {'observed': False, 'http_status': None},
            'loading_failed': {'observed': False}, 'root_cause': 'UNKNOWN'}

    def elapsed(self):
        return round(max(0, self.clock() - self.started) * 1000, 3)

    def begin(self, phase):
        if phase == 'goto':
            self.started = self.clock()
        self.data['phase'] = phase.upper()
        self.data[phase]['state'] = 'STARTED'
        return self.clock()

    def end(self, phase, since, error=None, response=None):
        record = self.data[phase]
        record.update(state='FAILED' if error is not None else 'DONE',
            elapsed_ms=round(max(0, self.clock() - since) * 1000, 3))
        if error is not None:
            record['error'] = safe_error(error)
        elif phase == 'goto':
            record['response_returned'] = response is not None
            record['http_status'] = http_status(response.status) if response is not None else None
        # Keep the failed phase for attribution, even through cleanup.
        if error is None and phase == 'readiness':
            self.data['phase'] = 'COMPLETE'

    def bind(self, event, main_frame):
        if self.started is None or self.network_id is not None:
            return
        identity = event.get('networkId')
        if (event.get('frameId') == main_frame and main_frame is not None and
                isinstance(identity, str) and identity):
            self.network_id, self.frame_id = identity, main_frame
            self.data['association'] = 'ORIGINAL_MAIN_DOCUMENT_NETWORK_ID'

    def domcontentloaded(self):
        if self.started is not None and not self.data['domcontentloaded_observed']:
            self.data['domcontentloaded_observed'] = True
            self.data['domcontentloaded_elapsed_ms'] = self.elapsed()

    def matches(self, event):
        return (self.network_id is not None and event.get('requestId') == self.network_id and
            event.get('type') == 'Document')

    def response(self, event, lifecycle):
        if (self.matches(event) and event.get('frameId') == self.frame_id and
                not self.data['response_received']['observed']):
            self.data['response_received'] = {'observed': True,
                'http_status': http_status(event.get('response', {}).get('status')),
                'elapsed_ms': self.elapsed(), 'lifecycle': lifecycle}

    def failed(self, event, lifecycle):
        if self.matches(event) and not self.data['loading_failed']['observed']:
            reason = event.get('blockedReason')
            self.data['loading_failed'] = {'observed': True, 'codes': net_codes(event.get('errorText')),
                'cancelled': event.get('canceled') if type(event.get('canceled')) is bool else 'UNKNOWN',
                'blocked_reason': reason if isinstance(reason, str) and reason in BLOCKED_REASONS else 'UNKNOWN',
                'elapsed_ms': self.elapsed(), 'lifecycle': lifecycle}

    def snapshot(self):
        # Copy only the explicitly safe structure, never the identity attributes.
        return json.loads(json.dumps(self.data))


def candidate(expected=None):
    raw = MANIFEST.read_bytes()
    actual = sha(raw)
    if expected is not None and expected != actual:
        raise Stop('CANDIDATE_DIGEST_MISMATCH')
    data = unique_json(raw)
    if (type(data) is not dict or data.get('schema') != 'A24-current-context-r1-candidate/v1' or
            data.get('task') != TASK or data.get('workflow_commit') != WORKFLOW or
            data.get('run_id') != RUN_ID or data.get('executor_thread_id') != OWNER or
            data.get('activation_path') != ACTIVATION or data.get('output_directory') != OUTPUT or
            data.get('decision_path') != DECISION or data.get('report_path') != REPORT or
            type(data.get('excluded_static_event_limit')) is not int or
            data['excluded_static_event_limit'] != EXCLUDED_STATIC_LIMIT or
            type(data.get('version_check_limit')) is not int or data['version_check_limit'] != VERSION_CHECK_LIMIT or
            data.get('scope') != SCOPE or type(data.get('sample_limit')) is not int or
            data['sample_limit'] != 0 or data.get('automatic_schema_confirmation') is not False or
            not data.get('members') or any(not same_typed(data.get(k), v)
                for k, v in scope_binding(actual).items() if k != 'candidate_manifest_sha256')):
        raise Stop('CANDIDATE_BINDING_REJECTED')
    seen = set()
    for item in data['members']:
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts or ':' in str(relative) or item['path'] in seen:
            raise Stop('CANDIDATE_PATH_REJECTED')
        seen.add(item['path'])
        member = ROOT / relative
        require_plain_path(member)
        content = member.read_bytes()
        if len(content) != item['size'] or sha(content) != item['sha256']:
            raise Stop('CANDIDATE_MEMBER_MISMATCH')
    required = {'src/annotation/__init__.py',
        'src/annotation/source/usense/current_readonly/__init__.py',
        'src/annotation/source/usense/current_readonly/gate.py',
        'src/annotation/source/usense/current_readonly/policy.py',
        'src/annotation/source/usense/current_readonly/auth.py',
        'src/annotation/source/usense/current_readonly/decode.py',
        'src/annotation/source/usense/current_readonly/context_query.py',
        'src/annotation/source/usense/current_readonly/source_contract.py',
        'tools/a16_current_state_probe.py', 'tools/a16_current_state_launcher.py',
        'docs/evidence/A16/current-readonly/dependencies/a15_native_reference.py',
        'docs/evidence/A15/certificate-exception/reviewed-native/native_windows.py',
        'docs/evidence/A15/certificate-exception/reviewed-native/process_check.py'}
    if not required <= seen:
        raise Stop('CANDIDATE_DEPENDENCY_REQUIRED')
    return actual


def add_arguments(parser):
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--certificate-exception', action='store_true')
    for option in ('activation-file', 'activation-sha256', 'candidate-sha256',
                   'profile-fingerprint', 'decision-file', 'report-file'):
        parser.add_argument('--' + option)


def authorize_args(args):
    if (args.live is not True or args.activation_file != ACTIVATION or
            not all(is_sha(v) for v in (args.activation_sha256, args.candidate_sha256, args.profile_fingerprint)) or
            args.decision_file != DECISION or args.report_file != REPORT):
        raise Stop('EXPLICIT_A24_ACTIVATION_REQUIRED')
    # All field checks precede filesystem access; no profile metadata is read here.
    actual = candidate(args.candidate_sha256)
    paths = [Path(args.activation_file), Path(args.decision_file), Path(args.report_file)]
    for p in paths:
        require_plain_path(p)
    return validate_activation(paths[0].read_bytes(), args.activation_sha256, actual,
        args.profile_fingerprint, paths[1].read_bytes(), paths[2].read_bytes(),
        explicit_live=args.live, exception=args.certificate_exception)


def activation_argv(args):
    result = ['--live']
    if args.certificate_exception:
        result.append('--certificate-exception')
    for name in ('activation-file', 'activation-sha256', 'candidate-sha256',
                 'profile-fingerprint', 'decision-file', 'report-file'):
        result += ['--' + name, getattr(args, name.replace('-', '_'))]
    return result


def claim_marker(path, approval):
    context_options(approval)
    try:
        save_new(path, marker(approval))
    except FileExistsError:
        raise Stop('ACTIVATION_ALREADY_CLAIMED') from None


def require_marker(name, approval):
    require_plain_path(LIVE_OUT / name)
    if json.loads((LIVE_OUT / name).read_bytes()) != marker(approval):
        raise Stop('PARENT_CLAIM_MISMATCH')


def reported_stop(output):
    return native.reported_stop(output)


def resource_type(value):
    return {'xhr': 'XHR', 'fetch': 'Fetch', 'websocket': 'WebSocket'}.get(value, value.title())


def tracked_callback(operation):
    """Track context callbacks as well as native scheduled tasks."""
    @wraps(operation)
    async def call(self, *args, **kwargs):
        task = asyncio.current_task()
        self.callbacks.add(task)
        if self.sealed:
            self.record_failure(Stop('CALLBACK_AFTER_SETTLEMENT'))
        try:
            return await operation(self, *args, **kwargs)
        except BaseException as error:
            self.record_failure(error)
            if operation.__name__ == 'paused' and args:
                event = args[0]
                request = event.get('request', {})
                code = safe_error(error)['codes'][0]
                self.audit(request.get('method'), request.get('url', ''), event.get('resourceType', 'Other'),
                    code, False, 'FETCH_REQUEST_STAGE', bool(event.get('redirectedRequestId')))
                await self.session.send('Fetch.failRequest', {'requestId': event['requestId'], 'errorReason': 'BlockedByClient'})
        finally:
            self.callbacks.discard(task)
    return call


class CurrentGuard(native.NativeGuard):
    """Retains native barriers with A24 classification and bounded settlement."""
    def __init__(self, context, page, policy):
        super().__init__(context, page, policy)
        self.sent = set()
        self.cache = {}  # Exact successful GET bytes, memory only, for UI reuse.
        self.capture_tasks = set()
        self.scripts = []
        self.output = None
        self.navigation_requests = 0
        self.excluded_static_events = 0
        self.excluded_static_denials_completed = 0
        self.callbacks = set()
        self.main_frame_id = None
        self.sealed = False
        self.pending_at_settlement = 0
        self.version_checks_sent = 0
        self.version_context_reservations = 0
        self.version_url = None
        self.denied_context_requests = set()
        self.denied_native_network_ids = set()
        self.navigation = NavigationEvidence()
        self.auth = AuthFlow()
        self.auth_frame = page.main_frame
        self.auth_network = {}
        self.auth_context_requests = {}
        self.auth_native_http = []
        self.session_native_success = set()
        self.active_profile_response = None
        self.business_facts = {}
        self.business_http = {}
        self.book_query_status = {'preparation': 'NOT_RUN', 'send_recheck': 'NOT_RUN',
            'binding_count': 0, 'read_intent_count': 0, 'query_values_exported': False,
            'logical_slot': 'BOOK'}
        self.profile = self.approval = None

    def schedule(self, coroutine):
        if self.sealed:
            self.record_failure(Stop('CALLBACK_AFTER_SETTLEMENT'))
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        def done(value):
            self.tasks.discard(value)
            if value.cancelled():
                self.record_failure(Stop('NETWORK_CALLBACK_CANCELLED'))
            elif value.exception() is not None:
                self.record_failure(value.exception())
        task.add_done_callback(done)
        return task

    async def install(self):
        # CDP session is attached to the original page; frame ID is bound while
        # still offline, before either request barrier can permit traffic.
        await self.context.route_web_socket('**/*', self.websocket)
        await self.context.route('**/*', self.route)
        self.session = await self.context.new_cdp_session(self.page)
        tree = await self.session.send('Page.getFrameTree')
        frame = tree.get('frameTree', {}).get('frame', {})
        identity = frame.get('id')
        if not isinstance(identity, str) or not identity or frame.get('parentId'):
            raise Stop('NATIVE_MAIN_FRAME_IDENTITY_UNPROVEN')
        self.main_frame_id = identity
        self.session.on('Fetch.requestPaused', lambda event: self.schedule(self.paused(event)))
        self.session.on('Target.attachedToTarget', lambda event: self.schedule(self.child_target(event)))
        self.session.on('Page.frameNavigated', self.frame_navigated)
        self.session.on('Network.responseReceived', self.native_response)
        self.session.on('Network.loadingFailed', self.native_loading_failed)
        self.page.on('domcontentloaded', self.navigation_domcontentloaded)
        await self.session.send('Page.enable')
        await self.session.send('Target.setAutoAttach', {'autoAttach': True,
            'waitForDebuggerOnStart': True, 'flatten': False})
        await self.session.send('Network.enable')
        await self.session.send('Network.setCacheDisabled', {'cacheDisabled': True})
        await self.session.send('Fetch.enable', {'patterns': [{'urlPattern': '*', 'requestStage': 'Request'}],
                                               'handleAuthRequests': False})

    def frame_navigated(self, event):
        frame = event.get('frame', {})
        if not frame.get('parentId') and frame.get('id') != self.main_frame_id:
            self.record_failure(Stop('NATIVE_MAIN_FRAME_IDENTITY_CHANGED'))

    def classify(self, method, url, kind, redirected, owned):
        allowed, category = self.policy.decide(method, url, kind, redirected)
        original_category = category
        if not owned:
            return False, 'UNOWNED_TARGET_BLOCKED', False
        if self.stopped:
            return False, 'STOPPED', False
        if redirected:
            return False, 'REDIRECT_BLOCKED', False
        if category == 'VERSION_CHECK' and (not allowed or not version_check(method, url, kind, redirected)):
            return False, 'VERSION_CHECK_CLASSIFICATION_UNPROVEN', False
        if category == 'PATH_BLOCKED' and excluded_same_origin(method, url, kind, redirected):
            category = EXCLUDED_PATH
        if category in (EXCLUDED_STATIC, EXCLUDED_PATH):
            proven = (excluded_static(method, url, kind, redirected) if category == EXCLUDED_STATIC
                else excluded_same_origin(method, url, kind, redirected))
            if allowed or not proven or category == EXCLUDED_PATH and original_category != 'PATH_BLOCKED':
                return False, 'EXCLUDED_STATIC_CLASSIFICATION_UNPROVEN', False
            return self.reserve_exclusion(category)
        return allowed, category, category == 'EXPECTED_PASSIVE_DENIAL'

    def reserve_exclusion(self, category):
        # One shared budget for CDN, denied paths and repeat version checks.
        # Both barriers reserve before await; a double observation costs two.
        self.excluded_static_events += 1
        if self.excluded_static_events > EXCLUDED_STATIC_LIMIT:
            return False, 'EXCLUDED_STATIC_EVENT_LIMIT', False
        return False, category, True

    def native_response(self, event):
        if event.get('requestId') in self.auth_network:
            self.navigation_callback_boundary()
            if event.get('frameId') != self.main_frame_id or event.get('type') not in ('XHR', 'Fetch'):
                self.record_failure(Stop('AUTH_RESPONSE_FRAME_UNPROVEN'))
                return
            route = self.auth_network[event['requestId']]
            status = http_status(event.get('response', {}).get('status'))
            self.auth_native_http.append({'route': route, 'http_status': status,
                'association': 'ORIGINAL_FRAME_RESERVED_NETWORK_ID'})
            if status != 200:
                self.record_failure(Stop('AUTH_HTTP_REJECTED' if status in (401, 403) else 'AUTH_HTTP_FAILED'))
            else:
                self.session_native_success.add(('VIEWER', ORIGIN + next(
                    p for p in SESSION if p.rsplit('/', 1)[-1] == route)))
        if event.get('requestId') in self.denied_native_network_ids:
            self.record_failure(Stop('EXCLUDED_REQUEST_RESPONSE_OBSERVED'))
        if self.navigation.matches(event):
            self.navigation_callback_boundary()
            self.navigation.response(event, self.navigation_lifecycle())

    def navigation_lifecycle(self):
        return ('SEALED' if self.sealed else 'SHUTDOWN' if self.shutdown_started
            else 'GUARD_STOPPED' if self.stopped else 'RUNNING')

    def navigation_callback_boundary(self):
        if self.sealed:
            self.record_failure(Stop('CALLBACK_AFTER_SETTLEMENT'))

    def native_loading_failed(self, event):
        if event.get('requestId') in self.auth_network:
            self.navigation_callback_boundary()
            self.record_failure(Stop('SESSION_NETWORK_FAILED'))
        if self.navigation.matches(event):
            self.navigation_callback_boundary()
            self.navigation.failed(event, self.navigation_lifecycle())

    def navigation_domcontentloaded(self):
        if self.navigation.started is not None:
            self.navigation_callback_boundary()
            self.navigation.domcontentloaded()

    def exclusion_summary(self):
        return {'combined_guard_events': self.excluded_static_events,
            'completed_denial_calls': self.excluded_static_denials_completed,
            'event_limit': EXCLUDED_STATIC_LIMIT, 'double_layer_events_count_separately': True,
            'http_send_count': 'UNKNOWN', 'dns_tcp_tls_activity': 'UNKNOWN',
            'script_necessity': 'UNKNOWN', 'pending_callbacks': self.pending_at_settlement}

    def read_id(self, url):
        try:
            return self.policy.request_urls.get(key(url), url)
        except (Stop, ValueError, TypeError):
            return url

    def record_failure(self, error):
        if self.failure is None:
            self.failure = safe_error(error)
        self.terminal_stopped = self.stopped = True

    def audit(self, method, url, kind, category, allowed, source, redirected=False):
        self.events.append({'time': utc(), 'method': method if method in
            ('GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'WEBSOCKET') else 'OTHER',
            **diagnostic(url, kind, category, allowed, source, redirected)})

    def denied(self, category):
        # A category string alone can never opt into A24 continuation.
        if category != 'EXPECTED_PASSIVE_DENIAL':
            self.record_failure(Stop(category))

    @tracked_callback
    async def route(self, route):
        request = route.request
        abort_attempted = False
        try:
            kind = resource_type(request.resource_type)
            redirected = request.redirected_from is not None
            try:
                owned = request.frame is self.auth_frame and self.page.main_frame is self.auth_frame
            except Exception:
                owned = False
            allowed, category, nonfatal = self.classify(request.method, request.url, kind, redirected, owned)
            if allowed and category == 'NAVIGATION':
                self.auth.reserve_navigation('context', request.url)
            if allowed and category == 'SESSION_GET':
                self.auth.reserve_session('context', request.url)
                self.auth_context_requests[id(request)] = (self.auth.phase, request.url)
            if allowed and scoped_json(category) and not self.auth.authenticated:
                raise Stop('BUSINESS_BEFORE_AUTHENTICATION_BLOCKED')
            read_id = self.read_id(request.url)
            if allowed and category == 'VERSION_CHECK':
                if self.version_context_reservations >= VERSION_CHECK_LIMIT:
                    allowed, category, nonfatal = self.reserve_exclusion(EXCLUDED_VERSION)
                else:
                    self.version_context_reservations += 1
            self.audit(request.method, request.url, kind, category, allowed, 'CONTEXT_FIRST_REQUEST', redirected)
            if allowed and read_id in self.cache and (scoped_json(category) or category.startswith('REGISTERED_')):
                if redirected:
                    raise Stop('REGISTERED_READ_REDIRECT_BLOCKED')
                entry = self.cache[read_id]
                self.audit('GET', request.url, kind, 'LOCAL_CAPTURE_REUSE', True, 'NO_NETWORK_FULFILL')
                await route.fulfill(status=200, body=entry['bytes'], headers=entry.get('headers', {}), content_type=entry['content_type'])
            elif allowed:
                await route.continue_()
            else:
                if not nonfatal:
                    self.denied(category)
                abort_attempted = True
                self.denied_context_requests.add(id(request))
                await route.abort('blockedbyclient')
                if category in EXCLUSIONS:
                    self.excluded_static_denials_completed += 1
        except BaseException as error:
            self.record_failure(error)
            if not abort_attempted:
                try:
                    await route.abort('blockedbyclient')
                except BaseException as abort_error:
                    self.record_failure(abort_error)

    @tracked_callback
    async def paused(self, event):
        request = event['request']
        redirected = bool(event.get('redirectedRequestId'))
        owned = (self.main_frame_id is not None and event.get('frameId') == self.main_frame_id
            and self.page.main_frame is self.auth_frame)
        allowed, category, nonfatal = self.classify(request['method'], request['url'], event['resourceType'], redirected, owned)
        if allowed and category == 'SESSION_GET':
            if not isinstance(event.get('networkId'), str) or not event['networkId']:
                raise Stop('SESSION_NETWORK_ASSOCIATION_UNPROVEN')
            self.auth.reserve_session('native', request['url'])
            self.auth_network[event['networkId']] = request['url'].rsplit('/', 1)[-1]
        if allowed and scoped_json(category) and not self.auth.authenticated:
            raise Stop('BUSINESS_BEFORE_AUTHENTICATION_BLOCKED')
        if allowed and category == 'VERSION_CHECK':
            # The installed native request barrier is the single send counter,
            # just as for the six business GETs. Context may run on either side.
            if self.version_checks_sent >= VERSION_CHECK_LIMIT:
                allowed, category, nonfatal = self.reserve_exclusion(EXCLUDED_VERSION)
            else:
                self.version_checks_sent += 1
                self.version_url = request['url']
        if allowed and event['resourceType'] == 'Document':
            self.auth.reserve_navigation('native', request['url'])
            self.navigation_requests += 1
            if request['url'] == TARGET:
                # The same approved, nonredirected, owned Document only. No ID
                # or URL is serialized; no request or listener is added here.
                self.navigation.bind(event, self.main_frame_id)
        read_id = self.read_id(request['url'])
        if allowed and (scoped_json(category) or category == 'REGISTERED_ORIGINAL'):
            if redirected:
                allowed, category = False, 'REGISTERED_READ_REDIRECT_BLOCKED'
            elif read_id in self.sent:
                # Even if native Fetch runs before the context route, replays
                # are fulfilled from the same captured bytes, never sent again.
                if read_id in self.cache:
                    entry = self.cache[read_id]
                    self.audit('GET', request['url'], event['resourceType'], 'LOCAL_CAPTURE_REUSE', True, 'NO_NETWORK_FETCH_FULFILL')
                    await self.session.send('Fetch.fulfillRequest', {'requestId': event['requestId'],
                        'responseCode': 200, 'responseHeaders': [{'name': 'Content-Type', 'value': entry['content_type']}] +
                            [{'name': k, 'value': v} for k, v in entry.get('headers', {}).items()],
                        'body': base64.b64encode(entry['bytes']).decode('ascii')})
                    return
                allowed, category = False, 'BUSINESS_DUPLICATE_IN_FLIGHT_BLOCKED'
            else:
                self.sent.add(read_id)
        self.audit(request['method'], request['url'], event['resourceType'], category, allowed, 'FETCH_REQUEST_STAGE', redirected)
        if allowed:
            await self.session.send('Fetch.continueRequest', {'requestId': event['requestId']})
        else:
            if not nonfatal:
                self.denied(category)
            if event.get('networkId'):
                self.denied_native_network_ids.add(event['networkId'])
            await self.session.send('Fetch.failRequest', {'requestId': event['requestId'], 'errorReason': 'BlockedByClient'})
            if category in EXCLUSIONS:
                self.excluded_static_denials_completed += 1

    @tracked_callback
    async def websocket(self, route):
        self.audit('WEBSOCKET', route.url, 'WebSocket', 'WEBSOCKET_BLOCKED', False, 'PRECONNECT_WEBSOCKET_ROUTE')
        self.denied('WEBSOCKET_BLOCKED')
        await route.close(code=1008, reason='A24 read only')

    @tracked_callback
    async def child_target(self, event):
        self.audit('OTHER', '', 'Other', 'RELATED_TARGET_BLOCKED', False, 'TARGET_PAUSED_BEFORE_RESUME')
        self.denied('RELATED_TARGET_BLOCKED')
        result = await self.session.send('Target.closeTarget', {'targetId': event['targetInfo']['targetId']})
        if not result.get('success'):
            raise Stop('CHILD_TARGET_CLOSE_UNPROVEN')

    @tracked_callback
    async def capture(self, response):
        url = response.url
        kind = resource_type(response.request.resource_type)
        if url == LOGIN_POST:
            raise Stop('LOGIN_DISABLED_REUSE_ONLY')
        if url in {ORIGIN + path for path in SESSION}:
            if (response.request.method != 'GET' or response.request.frame is not self.auth_frame or
                    self.page.main_frame is not self.auth_frame or
                    self.auth_context_requests.get(id(response.request)) != (self.auth.phase, url)):
                raise Stop('SESSION_RESPONSE_ASSOCIATION_UNPROVEN')
            if response.status != 200:
                raise Stop('AUTH_HTTP_REJECTED' if response.status in (401, 403) else 'AUTH_HTTP_FAILED')
            if self.auth.active_profile_intents and url == ORIGIN + ACTIVE_PROFILE_PATH:
                # The active body is decoded only in the original page; never
                # call response.body() or export a profile into Python.
                if self.active_profile_response is not None:
                    raise Stop('SESSION_RESPONSE_ASSOCIATION_UNPROVEN')
                self.active_profile_response = response.request
                return
            projection = response_projection(await response.body(), response.status,
                session_route=url.rsplit('/', 1)[-1])
            self.auth.record_session(url, projection)
            return
        if excluded_static(response.request.method, url, kind, False):
            self.record_failure(Stop('EXCLUDED_STATIC_RESPONSE_OBSERVED'))
            return  # Boundary not proven. Never read the excluded body.
        if self.excluded_response(response):
            self.record_failure(Stop('EXCLUDED_REQUEST_RESPONSE_OBSERVED'))
            return
        allowed, category = self.policy.decide('GET', url, kind)
        if not allowed or response.request.method != 'GET':
            return
        if not (scoped_json(category) or category == 'REGISTERED_ORIGINAL' or
                category == 'STATIC' and kind == 'Script'):
            return
        if scoped_json(category):
            name = self.policy.business[key(url)]
            if name not in self.business_http:
                header = {'schema': 'A24-finite-response-http/v1', 'endpoint': name,
                    'http_status': http_status(response.status), 'business_code': 'UNKNOWN_BEFORE_BODY'}
                save_new(self.output / ('response-http-' + name + '.json'), header)
                self.business_http[name] = header
        raw = await response.body()
        if len(raw) > 32 * 1024 * 1024:
            raise Stop('RESPONSE_SIZE_LIMIT')
        if scoped_json(category):
            # Retain whitelisted current facts before business/schema adapters.
            # Never persist response text, account fields or arbitrary key names.
            name = self.policy.business[key(url)]
            try:
                body = unique_json(raw)
                decoded = True
            except Stop:
                body = None
                decoded = False
            facts = response_facts(name, response.status, body)
            facts['json_decode'] = 'VALID_JSON' if decoded else 'INVALID_JSON'
            if name in ('page14', 'page173'):
                facts['raw_response_sha256'] = sha(raw)
                facts['response_representation'] = 'RAW_PAGE_JSON' if self.policy.page_modes.get(name) == 'OSS' else 'RAW_LEGACY_RESPONSE'
            if name not in self.business_facts:
                save_new(self.output / ('response-facts-' + name + '.json'), facts)
                self.business_facts[name] = facts
            if not decoded:
                raise Stop('BUSINESS_RESPONSE_JSON_REJECTED')
        if response.status != 200:
            raise Stop('LOGIN_REQUIRED' if response.status in (401, 403) else 'READ_RESPONSE_FAILED')
        content_type = response.headers.get('content-type', 'application/octet-stream').split(';')[0]
        headers = {}
        cors = response.headers.get('access-control-allow-origin')
        if cors in ('*', ORIGIN):
            headers['access-control-allow-origin'] = cors
        self.cache.setdefault(self.read_id(url), {'bytes': raw, 'content_type': content_type, 'status': 200, 'headers': headers})
        if category == 'STATIC' and kind == 'Script' and not any(a['url'] == url for a in self.scripts):
            if self.output != LIVE_OUT:
                raise Stop('SCRIPT_CONTROLLED_OUTPUT_REQUIRED')
            folder = self.output / 'static-assets'
            require_plain_path(folder, missing_leaf=True)
            folder.mkdir(exist_ok=True)
            ref = 'static-assets/' + str(len(self.scripts) + 1) + '-' + sha(raw) + '.bin'
            with (self.output / ref).open('xb') as stream:
                stream.write(raw)
            asset = {'ref': ref, 'sha256': sha(raw), 'size': len(raw),
                'source_url_sha256': sha(url.encode('utf-8')),
                'loaded_origin': diagnostic(url, kind, category, True, 'CURRENT_RESPONSE'),
                'http_status': 200, 'executed_by_collector': False}
            # Exact provenance stays with raw bytes in the private local folder.
            # Public results/events contain only hashes and sanitized origin.
            save_new(self.output / (ref + '.source.json'), {**asset, 'source_url': url})
            self.scripts.append({'url': url, **asset})

    def response(self, response):
        # Observe finite known auth HTTP failures synchronously, before a
        # readiness wait can hide them behind its full timeout.
        if response.url == LOGIN_POST or response.url in {ORIGIN + p for p in SESSION}:
            if response.status != 200:
                self.record_failure(Stop('AUTH_HTTP_REJECTED' if response.status in (401, 403) else 'AUTH_HTTP_FAILED'))
        if excluded_static(response.request.method, response.url,
                resource_type(response.request.resource_type), False):
            self.record_failure(Stop('EXCLUDED_STATIC_RESPONSE_OBSERVED'))
            return
        if self.excluded_response(response):
            self.record_failure(Stop('EXCLUDED_REQUEST_RESPONSE_OBSERVED'))
            return
        self.schedule(self.capture(response))

    def excluded_response(self, response):
        if id(response.request) in self.denied_context_requests:
            return True
        method, url = response.request.method, response.url
        kind = resource_type(response.request.resource_type)
        allowed, category = self.policy.decide(method, url, kind)
        return (not allowed and category == 'PATH_BLOCKED' and
            excluded_same_origin(method, url, kind)) or (
            version_check(method, url, kind) and url != self.version_url)


def require_running(guard):
    if guard.stopped or guard.failure is not None:
        raise Stop('NETWORK_GUARD_STOPPED')


async def open_owned(profile, approval, state):
    if type(approval) is not Approval:
        raise Stop('A24_CONTEXT_APPROVAL_REQUIRED')
    from playwright.async_api import async_playwright
    runtime = await async_playwright().start()
    state['runtime'] = runtime
    context = await runtime.chromium.launch_persistent_context(str(profile), channel='msedge',
        headless=True, offline=True, service_workers='block', **context_options(approval),
        accept_downloads=False, viewport={'width': 1440, 'height': 1000}, timeout=15000,
        args=['--disable-session-crashed-bubble', '--disable-extensions'])
    state['context'] = context
    state['release']['context_created'] = True
    if len(context.pages) != 1 or context.pages[0].url != 'about:blank':
        raise Stop('STARTUP_PAGE_STATE_UNEXPECTED')
    page = context.pages[0]
    page.set_default_timeout(5000)
    guard = CurrentGuard(context, page, ReadPolicy())
    guard.profile, guard.approval = profile, approval
    guard.output = LIVE_OUT
    state['guard'] = guard
    await guard.install()
    context.on('page', lambda extra: guard.schedule(extra.close()))
    page.on('dialog', lambda dialog: guard.schedule(dialog.dismiss()))
    page.on('response', guard.response)
    await context.set_offline(False)
    return page, guard


async def settle_callbacks(guard, seconds=10):
    """One fixed deadline, including callbacks arriving while settling.

    asyncio.wait does not indefinitely await cancellation-resistant callbacks.
    Their existence is an explicit failure and the outer owned worker deadline
    remains in force. No historical task-lifecycle code is rewritten.
    """
    deadline = time.monotonic() + seconds
    quiet = 0
    while quiet < 2:
        await asyncio.sleep(0)
        tasks = {t for t in guard.tasks | guard.callbacks
                 if t is not asyncio.current_task() and not t.done()}
        if not tasks:
            quiet += 1
            continue
        quiet = 0
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            guard.pending_at_settlement = len(tasks)
            guard.record_failure(Stop('NETWORK_GUARD_TASKS_PENDING'))
            for task in tasks:
                task.cancel()
            return False
        await asyncio.wait(tasks, timeout=remaining)
    return True


async def drain(guard):
    await settle_callbacks(guard)
    require_running(guard)


async def await_existing_response(guard, url, clock=time.monotonic):
    """Wait for an already sent GET; never issue a duplicate to resolve it."""
    if url not in guard.sent or url in guard.cache:
        return
    deadline = clock() + 20
    while url not in guard.cache:
        require_running(guard)
        if clock() >= deadline:
            raise Stop('EXISTING_GET_RESPONSE_UNPROVEN')
        await asyncio.sleep(0.02)
    require_running(guard)


async def guarded_wait(guard, operation, seconds):
    """Stop promptly on the first guard failure, even during DOM waits."""
    task = asyncio.create_task(operation)
    guard.tasks.add(task)
    deadline = time.monotonic() + seconds
    try:
        while not task.done():
            require_running(guard)
            if time.monotonic() >= deadline:
                raise Stop('AUTH_OPERATION_TIMEOUT')
            await asyncio.wait({task}, timeout=min(.02, max(.001, deadline - time.monotonic())))
        require_running(guard)
        return task.result()
    finally:
        if not task.done():
            task.cancel()
            await asyncio.wait({task}, timeout=.2)
        if task.done():
            guard.tasks.discard(task)
            # Retrieve cancellation/exception without exporting its text.
            if not task.cancelled():
                task.exception()


async def authenticate(*args, **kwargs):
    # Old entry point is inert before any navigation, I/O, fill, click or POST.
    raise Stop('LOGIN_DISABLED_REUSE_ONLY')


async def check_current_viewer(page, guard):
    require_running(guard)
    if page is not guard.page or page.main_frame is not guard.auth_frame:
        raise Stop('VIEWER_ORIGINAL_FRAME_UNPROVEN')
    if page.url != TARGET:
        raise Stop('FINAL_NAVIGATION_IDENTITY_MISMATCH')
    if (await page.locator(FORM).is_visible() or
            await page.locator('input[type="password"]').count()):
        raise Stop('LOGIN_REQUIRED')
    if not await page.locator(VIEWER).is_visible():
        raise Stop('PROTECTED_AUTHENTICATION_UNPROVEN')
    require_running(guard)


async def admit_current_viewer(page, guard):
    await check_current_viewer(page, guard)
    guard.auth.admit_viewer()


ACTIVE_PROFILE_PATH = '/qieti/api/user_login/profile'
SESSION_COMPLETION_SECONDS = 20
# Return only this fixed projection. No profile/body/user/token crosses evaluate.
SESSION_JSON = """async path => {
 if(path!=='/qieti/api/user_login/profile')return {http_status:0};
 const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),20000);
 try{
  const auth=JSON.parse(localStorage.getItem('user')||'{}');
  if(!auth.access_token)return {http_status:401};
  const r=await fetch(path,{method:'GET',redirect:'error',signal:ctl.signal,
   headers:{Authorization:'Bearer '+auth.access_token}});
  if(r.status!==200)return {http_status:r.status};
  const raw=await r.text();if(new TextEncoder().encode(raw).length>131072)return {http_status:200};
  const b=JSON.parse(raw),d=b?.data;
  if(!b||typeof b!=='object'||Array.isArray(b)||typeof b.code!=='number'||
     ![0,200].includes(b.code)||!d||typeof d!=='object'||Array.isArray(d))return {http_status:200};
  return {http_status:200,business_decode:'ACCEPTED_NUMERIC_CODE',
   credential_return_present:'NOT_INSPECTED',authenticated_profile_fields_present:
    ((typeof d.id==='string'||Number.isInteger(d.id))&&!!d.id&&typeof d.username==='string'&&!!d.username.trim())};
 }catch(e){return {http_status:0};}finally{clearTimeout(timer);}
}"""


async def complete_current_session(page, guard, clock=time.monotonic):
    """One deadline for the original request, native HTTP and body projection.

    Empty callback queues are not proof of network completion. A reservation in
    either barrier is sufficient to forbid an active replacement request.
    """
    deadline = clock() + SESSION_COMPLETION_SECONDS
    active = None
    projection = None
    async def bounded(operation):
        remaining = deadline - clock()
        if remaining <= 0:
            operation.close()
            raise Stop('SESSION_COMPLETION_TIMEOUT')
        return await guarded_wait(guard, operation, remaining)
    try:
        await bounded(check_current_viewer(page, guard))
        if not guard.auth.session_responses and not any(guard.auth.session_seen.values()):
            require_running(guard)
            guard.auth.arm_active_profile()  # No await between test and intent.
            active = asyncio.create_task(page.evaluate(SESSION_JSON, ACTIVE_PROFILE_PATH))
            guard.tasks.add(active)
        else:
            guard.auth.completion_mode = 'EXISTING_SESSION'
        while True:
            require_running(guard)
            if clock() >= deadline:
                raise Stop('SESSION_COMPLETION_TIMEOUT')
            await bounded(check_current_viewer(page, guard))
            if active is not None and active.done() and projection is None:
                projection = active.result()
                if type(projection) is not dict or projection.get('http_status') != 200:
                    status = projection.get('http_status') if type(projection) is dict else None
                    raise Stop('AUTH_HTTP_REJECTED' if status in (401, 403) else 'SESSION_RESULT_UNKNOWN')
                if (set(projection) != {'http_status', 'business_decode', 'credential_return_present',
                        'authenticated_profile_fields_present'} or
                        type(projection['http_status']) is not int or
                        projection['business_decode'] != 'ACCEPTED_NUMERIC_CODE' or
                        projection['credential_return_present'] != 'NOT_INSPECTED' or
                        projection['authenticated_profile_fields_present'] is not True):
                    raise Stop('SESSION_RESULT_UNKNOWN')
            item = ('VIEWER', ORIGIN + ACTIVE_PROFILE_PATH)
            if (projection is not None and item not in guard.auth.session_responses and
                    guard.active_profile_response is not None and item in guard.session_native_success):
                guard.auth.record_session(item[1], projection)
            proven = guard.auth.session_responses & guard.session_native_success
            if proven:
                # The original response body and both request reservations are
                # complete; outstanding callbacks still retain fatal authority.
                require_running(guard)
                return
            await asyncio.sleep(min(.02, max(0, deadline - clock())))
    finally:
        if active is not None:
            if not active.done():
                active.cancel()
                await asyncio.wait({active}, timeout=.2)
            if active.done():
                guard.tasks.discard(active)
                if not active.cancelled():
                    active.exception()


# Existing authenticated value stays in the protected page. It never leaves
# evaluate, enters an argument, request log, exception or saved response.
GET_JSON = """async path => {
 const auth=JSON.parse(localStorage.getItem('user')||'{}');
 if(!auth.access_token)return {http_status:401};
 const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),20000);
 try{const r=await fetch(path,{method:'GET',redirect:'error',signal:ctl.signal,
 headers:{Authorization:'Bearer '+auth.access_token}});
 return {http_status:r.status,body:await r.json()};}
 catch(e){return {http_status:0};}finally{clearTimeout(timer);}
}"""

PUBLIC_JSON = """async url => {
 const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),20000);
 try{const r=await fetch(url,{method:'GET',redirect:'error',credentials:'omit',signal:ctl.signal});
 return {http_status:r.status,body:await r.json()};}
 catch(e){return {http_status:0};}finally{clearTimeout(timer);}
}"""


async def get_once(page, guard, endpoint):
    require_running(guard)
    await drain(guard)
    url = endpoint if endpoint.startswith('https://') else ORIGIN + endpoint
    is_book = endpoint == guard.policy._book_endpoint
    if is_book:
        require_book_frame(page, guard)
        if BOOK_SLOT in guard.sent or BOOK_SLOT in guard.cache:
            raise Stop('BOOK_SLOT_ALREADY_RESERVED')
        guard.policy.begin_book_read(endpoint)
        guard.book_query_status['read_intent_count'] = 1
    allowed, category = guard.policy.decide('GET', url, 'Fetch')
    if not allowed or not scoped_json(category) or key(url) not in guard.policy.business:
        raise Stop('UNREGISTERED_BUSINESS_GET')
    read_id = guard.read_id(url)
    name = guard.policy.business[key(url)]
    def decode_result(result):
        return business(result) if name in ('book', 'directory') else endpoint_body(
            name, result, guard.policy.page_modes.get(name))
    await await_existing_response(guard, read_id)
    if read_id in guard.cache:
        body = decode_result({'http_status': 200, 'body': json.loads(guard.cache[read_id]['bytes'])})
    else:
        script = SEND_JS if is_book else PUBLIC_JSON if guard.policy.public_page(url) else GET_JSON
        result = await page.evaluate(script, endpoint)
        require_running(guard)
        if is_book:
            require_book_frame(page, guard)
            status = result.get('context_status') if type(result) is dict else None
            guard.book_query_status['send_recheck'] = (status if status in (
                'BOUND_CONTEXT_UNCHANGED', 'CONTEXT_CHANGED', 'CONTEXT_UNAVAILABLE',
                'CONTEXT_MALFORMED', 'CONTEXT_UNSUPPORTED', 'ORIGINAL_PAGE_CHANGED',
                'SESSION_TOKEN_UNAVAILABLE', 'GET_RESULT_UNKNOWN') else 'UNKNOWN')
            if status == 'SESSION_TOKEN_UNAVAILABLE':
                raise Stop('LOGIN_REQUIRED')
            if status != 'BOUND_CONTEXT_UNCHANGED':
                raise Stop('BOOK_CONTEXT_CHANGED' if status == 'CONTEXT_CHANGED' else 'BOOK_CONTEXT_GET_RESULT_UNKNOWN')
        await drain(guard)
        if read_id not in guard.cache:
            raise Stop('NATIVE_GET_CAPTURE_MISSING')
        body = decode_result(result)
    return body


def require_book_frame(page, guard):
    require_running(guard)
    if (page is not guard.page or page.main_frame is not guard.auth_frame or
            not guard.main_frame_id or page.url != TARGET or not guard.auth.authenticated):
        raise Stop('BOOK_CONTEXT_ORIGINAL_FRAME_REQUIRED')


async def prepare_current_book_query(page, guard):
    require_book_frame(page, guard)
    if guard.book_query_status['preparation'] != 'NOT_RUN':
        raise Stop('BOOK_CONTEXT_REBIND_BLOCKED')
    guard.book_query_status['preparation'] = 'STARTED'
    prepared = await page.evaluate(PREPARE_JS)
    require_book_frame(page, guard)
    status = prepared.get('status') if type(prepared) is dict else None
    if status != 'PREPARED' or set(prepared) != {'status', 'endpoint'}:
        guard.book_query_status['preparation'] = status if status in (
            'CONTEXT_UNAVAILABLE', 'CONTEXT_MALFORMED', 'CONTEXT_UNSUPPORTED', 'ORIGINAL_PAGE_CHANGED') else 'UNKNOWN'
        raise Stop({'CONTEXT_UNAVAILABLE': 'BOOK_CONTEXT_UNAVAILABLE',
            'CONTEXT_MALFORMED': 'BOOK_CONTEXT_MALFORMED',
            'CONTEXT_UNSUPPORTED': 'BOOK_CONTEXT_UNSUPPORTED'}.get(status, 'BOOK_CONTEXT_PREPARATION_REJECTED'))
    endpoint = prepared['endpoint']  # Ephemeral sensitive URL, never persisted.
    guard.policy.bind_book_query(endpoint)
    guard.book_query_status.update(preparation='BOUND_CURRENT_CONTEXT', binding_count=1)
    return endpoint


async def original_once(page, guard, binding):
    url = binding['url']
    require_running(guard)
    await await_existing_response(guard, url)
    if url not in guard.cache:
        # Fetch uses the same page/native guards. No APIRequestContext bypass.
        status = await page.evaluate("""async url=>{
          const c=new AbortController(),t=setTimeout(()=>c.abort(),20000);
          try{const r=await fetch(url,{method:'GET',redirect:'error',credentials:'omit',signal:c.signal});
            await r.arrayBuffer();return r.status;}finally{clearTimeout(t);}}
        """, url)
        if status != 200:
            raise Stop('ORIGINAL_GET_FAILED')
        await drain(guard)
    require_running(guard)
    raw = guard.cache[url]['bytes']
    info = original_info(raw)
    suffix = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}.get(info['format'], '.image')
    ref = 'original-viewer-' + str(binding['viewer']) + suffix
    with (LIVE_OUT / ref).open('xb') as stream:
        stream.write(raw)
    return {**info, 'ref': ref, 'book_id': BOOK, 'viewer': binding['viewer'],
        'resource_index': binding['resource_index'], 'source_url_sha256': sha(url.encode()),
        'origin': diagnostic(url, 'Image', 'REGISTERED_ORIGINAL', True, 'CURRENT_SOURCE_RESPONSE')}


async def visible_mapping(page, guard, binding, zone):
    """Passive current canvas check; never select a book or trigger UI GETs.

    Existing source responses prove request/resource mapping. They do not prove
    a displayed viewer or save-page conversion when the canvas is absent.
    """
    require_running(guard)
    script = """([zone,index,url])=>{
      const el=document.querySelectorAll('.pdf-zone')[zone],c=el?.querySelector('canvas');
      if(!c||!c.width||!c.height)return null;
      let vm=c.__vueParentComponent,found=null;
      while(vm){if(vm.type?.__name==='PdfViewerWithDivUnified'){found=vm;break;}vm=vm.parent;}
      if(!found){const seen=new Set(),stack=[document.querySelector('#app')?._vnode];
        while(stack.length){const n=stack.pop();if(!n||typeof n!=='object'||seen.has(n))continue;
          seen.add(n);const v=n.component;
          if(v?.type?.__name==='PdfViewerWithDivUnified'&&v.props.zone===(zone===0?'question_zone':'answer_zone')){found=v;break;}
          if(v?.subTree)stack.push(v.subTree);if(Array.isArray(n.children))stack.push(...n.children);}}
      if(!found||found.props.pages?.length!==1)return null;
      const p=found.props.pages[0];if(p.page_index!==index||p.image!==url)return null;
      try{const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
        let dark=0,light=0;for(let i=0;i<d.length;i+=64){if(d[i+3]&&d[i]<160)dark++;if(d[i+3]&&d[i]>220)light++;}
        if(dark<20||light<20)return null;
        return {resource_index:p.page_index,resource_matches:true,canvas_width:c.width,canvas_height:c.height,
          dark_samples:dark,light_samples:light};}catch(e){return null;}
    }"""
    args = [zone, binding['resource_index'], binding['url']]
    proof = await page.evaluate(script, args)
    require_running(guard)
    return {'viewer': binding['viewer'], 'book_id': BOOK,
        'resource_index': binding['resource_index'],
        'request_resource_binding': 'EXACT_SCOPED_RESPONSE',
        'save_page': None, 'save_page_status': 'UNKNOWN',
        'visible_status': 'MATCHED_CURRENT_CANVAS' if proof else 'UNKNOWN', **(proof or {})}


async def collect(page, guard, result):
    async def step(name, operation):
        require_running(guard)
        result['steps'][name] = 'STARTED'
        try:
            value = await operation()
            require_running(guard)
        except BaseException:
            result['steps'][name] = 'FAILED'
            raise
        result['steps'][name] = 'DONE'
        return value
    async def navigate():
        since = guard.navigation.begin('goto')
        try:
            response = await page.goto(TARGET, wait_until='domcontentloaded', timeout=45000)
        except BaseException as error:
            guard.navigation.end('goto', since, error)
            raise
        guard.navigation.end('goto', since, response=response)
        if response is None or response.status != 200:
            raise Stop('LOGIN_REQUIRED' if response is not None and response.status in (401, 403)
                else 'VIEWER_DOCUMENT_RESPONSE_UNPROVEN')
        return response
    guard.auth.arm_navigation(TARGET)
    await step('navigation', lambda: guarded_wait(guard, navigate(), 46))
    since = guard.navigation.begin('readiness')
    try:
        require_running(guard)
        if await page.get_by_placeholder('请输入密码', exact=True).is_visible():
            raise Stop('LOGIN_REQUIRED')
        await guarded_wait(guard, page.locator(VIEWER).first.wait_for(timeout=30000), 31)
        require_running(guard)
        if page.url != TARGET:
            raise Stop('FINAL_NAVIGATION_IDENTITY_MISMATCH')
    except BaseException as error:
        guard.navigation.end('readiness', since, error)
        raise
    guard.navigation.end('readiness', since)
    await step('session_completion', lambda: complete_current_session(page, guard))
    await admit_current_viewer(page, guard)
    result['viewer_access_confirmed'] = True
    result['account_identity_fields_available'] = guard.auth.snapshot()['account_identity_fields_available']
    async def read_book():
        endpoint = await prepare_current_book_query(page, guard)
        body = await get_once(page, guard, endpoint)
        return book_identity(body)
    book = await step('book', read_book)
    result['book'] = book
    result['book_identity_confirmed'] = True
    result['book_identity_basis'] = 'CANONICAL_LIST_TARGET_ID_AND_TITLE'
    # The current picker invokes extra context/summary/default-page GETs. Do
    # not run it under the six-GET plan or claim it as visible identity proof.
    result['book_picker_identity_confirmed'] = False
    directory = await step('directory', lambda: get_once(page, guard, FIXED['directory']))
    frames = await step('frames', lambda: get_once(page, guard, FIXED['frames']))
    # Endpoint names and matching counts alone do not prove full server coverage.
    save_new(LIVE_OUT / 'frame-envelope.json', frames_rows(frames)[1])
    target = inventory(book, directory, frames, all_responses_complete=False)
    result['book'], result['target'] = book, target
    save_new(LIVE_OUT / 'target-inventory.json', target)
    # Pre-adapter response-facts files already retain bounded whitelisted types.
    metadata = await step('source', lambda: get_once(page, guard, FIXED['source']))
    selected = page_plan(metadata, {v: ORIGIN + FIXED['page' + str(v)] for v in (14, 173)})
    guard.policy.bind_pages(selected)
    result['source_plan'] = plan_facts(selected)
    save_new(LIVE_OUT / 'source-metadata.json', result['source_plan'])
    for viewer, zone in ((14, 0), (173, 1)):
        page_url = selected['pages'][viewer]['url']
        body = await step('page' + str(viewer), lambda u=page_url: get_once(page, guard, u))
        response_sha = sha(guard.cache[guard.read_id(page_url)]['bytes'])
        if selected['branch'] == 'OSS':
            bound = oss_page_binding(body, viewer, selected, response_sha)
        else:
            data, envelope = legacy_page_data(body)
            bound = {**source_page({'data': data}, viewer), 'representation': 'SERVER_LEGACY_PAGE_FIELDS',
                'index_provenance': 'RETURNED_SERVER_PAGE_INDEX', 'legacy_envelope': envelope,
                'raw_page_response_sha256': response_sha}
        guard.policy.register_original(bound['url'], BOOK, viewer, bound['resource_index'], 'page' + str(viewer))
        # The derived representation is distinct from the actual response hash.
        # Even validated full template/image URLs remain transient memory only.
        save_new(LIVE_OUT / ('source-response-viewer' + str(viewer) + '.json'),
            {k: value for k, value in bound.items() if k != 'url'})
        original = await step('original' + str(viewer), lambda b=bound: original_once(page, guard, b))
        mapping = await step('mapping' + str(viewer), lambda b=bound, z=zone: visible_mapping(page, guard, b, z))
        result['sources'].append({'original': original, 'mapping': mapping})
    await drain(guard)
    result['static_assets'] = public_assets(guard)
    save_new(LIVE_OUT / 'static-assets-observation.json', {
        'status': 'CAPTURED_UNREVIEWED' if guard.scripts else 'NO_ALLOWED_SCRIPT_CAPTURED',
        'automatic_schema_confirmation': False, 'schema_status': 'UNKNOWN',
        'assets': result['static_assets']})
    result['gaps'].extend(['BODY_UNKNOWN_SAMPLE_DISABLED', 'READ_SCHEMA_UNVERIFIED',
        'NEW_QUESTION_CONTENT_DIRECTORY_GEOMETRY_UNVERIFIED'])
    if any(s['mapping']['visible_status'] != 'MATCHED_CURRENT_CANVAS' for s in result['sources']):
        result['gaps'].append('VISIBLE_SOURCE_MAPPING_UNPROVEN')
    result['outcome'] = 'READONLY_REVIEW_WITH_GAPS'
    result['scope'] = SCOPE
    result['sample_limit'] = 0
    result['sample'] = {'status': 'NOT_RUN', 'reason': 'OBSERVATION_ONLY_SCOPE',
        'content_acceptable': False}
    result['body_status'] = result['schema_status'] = 'UNKNOWN'
    result['automatic_schema_confirmation'] = False
    result['production_ready'] = result['write_eligible'] = False
    result['first_question_status'] = 'HOLD_CONTENT_DIRECTORY_GEOMETRY_AND_SAVE_READBACK_REQUIRED'


def public_assets(guard):
    return [{k: asset[k] for k in ('ref', 'sha256', 'size', 'source_url_sha256',
        'loaded_origin', 'http_status', 'executed_by_collector')} for asset in guard.scripts]


async def observe_live(profile, approval):
    state = {'release': native.initial_release()}
    steps = ('login_navigation', 'login_fill', 'login_submit', 'navigation', 'session_completion', 'book', 'directory', 'frames', 'source', 'page14', 'original14', 'mapping14',
        'page173', 'original173', 'mapping173', 'sample_frames', 'sample_info', 'content_question', 'content_choice', 'content_answer')
    result = {'task': TASK, 'run_id': RUN_ID, 'outcome': 'UNKNOWN', 'steps': dict.fromkeys(steps, 'NOT_RUN'),
        'sources': [], 'gaps': [], 'error': None, 'business_writes': 0, 'login_submissions': 0,
        'viewer_access_confirmed': False, 'account_identity_fields_available': 'NOT_OBSERVED',
        'book_identity_confirmed': False, 'local_credential_config_reads': 0,
        'started_at': utc(), 'production_ready': False, 'write_eligible': False,
        'scope': SCOPE, 'sample_limit': 0, 'automatic_schema_confirmation': False,
        'sample': {'status': 'NOT_RUN', 'reason': 'OBSERVATION_ONLY_SCOPE', 'content_acceptable': False},
        'body_status': 'UNKNOWN', 'schema_status': 'UNKNOWN',
        'navigation_diagnostics': NavigationEvidence().snapshot()}
    def first_error(fallback):
        recorded = result['error'] if result['error'] is not None else fallback
        guard = state.get('guard')
        if (guard is not None and guard.failure is not None and
                (recorded is None or recorded == safe_error(Stop('NETWORK_GUARD_STOPPED')))):
            return guard.failure
        return recorded
    try:
        page, guard = await open_owned(profile, approval, state)
        await collect(page, guard, result)
    except BaseException as error:
        if state.get('guard') is not None:
            state['guard'].record_failure(error)
        result['outcome'], result['error'] = 'ERROR', first_error(safe_error(error))
        for name, value in result['steps'].items():
            if value == 'STARTED':
                result['steps'][name] = 'FAILED'
    finally:
        guard = state.get('guard')
        if guard:
            try:
                await drain(guard)
            except BaseException as error:
                result['outcome'], result['error'] = 'ERROR', first_error(safe_error(error))
            result['guard_pre_shutdown'] = native.guard_snapshot(guard)
            guard.begin_shutdown()
        await native.close_owned(state)
        if guard:
            await settle_callbacks(guard, seconds=2)
            guard.sealed = True
            result['network_audit'] = guard.events
            result['excluded_static'] = guard.exclusion_summary()
            result['version_check'] = {'native_send_reservations': guard.version_checks_sent,
                'context_pass_reservations': guard.version_context_reservations,
                'send_limit': VERSION_CHECK_LIMIT, 'http_success': 'UNKNOWN'}
            result['guard_at_serialization'] = native.guard_snapshot(guard)
            result['navigation_diagnostics'] = guard.navigation.snapshot()
            result['authentication'] = guard.auth.snapshot()
            result['book_query_binding'] = dict(guard.book_query_status)
            result['authentication']['native_http_observations'] = guard.auth_native_http
            result['login_submissions'] = result['authentication']['actual_login_post_requests']
            if guard.terminal_stopped or guard.failure:
                result['outcome'] = 'ERROR'
                result['error'] = first_error(safe_error(Stop('NETWORK_GUARD_STOPPED')))
        result['release'] = state['release']
        if state['release']['state'] != 'RELEASED':
            result['outcome'] = 'ERROR'
            result['error'] = result['error'] or safe_error(Stop('RELEASE_UNPROVEN'))
        result['static_assets'] = public_assets(guard) if guard else []
        result['finished_at'] = utc()
        save_new(LIVE_OUT / 'current-state.json', result)
    return 0 if result['outcome'] in ('READONLY_REVIEW', 'READONLY_REVIEW_WITH_GAPS') else 2


def occupancy(profile, approval, args):
    """Same reviewed native counter, separate bounded A24 child and marker."""
    api_class, _ = load_native()
    api = api_class()
    env = {**safe_environment(os.environ), 'A24_CONTEXT_R1_PRIVATE_PROFILE': str(profile)}
    child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--_occupancy'] + activation_argv(args),
        env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000)
    record = {'before': api.held_identity(int(child._handle)), 'limit_seconds': 4}
    try:
        out, err = child.communicate(input=b'A24_CONTEXT_R1_OCCUPANCY\n', timeout=4)
        native.accept_occupancy_zero(out, err, child.returncode)
        record['matching_processes'] = 0
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=1)
        record['after'] = api.held_identity(int(child._handle))
        for stream in (child.stdin, child.stdout, child.stderr):
            if stream is not None and not stream.closed:
                stream.close()
        child._handle.Close()
        record['handle_closed'] = True
        save_new(LIVE_OUT / 'occupancy.json', record)
    if any((profile / name).exists() for name in ('SingletonLock', 'SingletonCookie', 'lockfile')):
        raise Stop('PROFILE_LOCK_PRESENT')


def supervise(command, output_dir, limit=WORKER_SECONDS, hard_deadline=None):
    api_class, _ = load_native()
    api = api_class()
    started = time.monotonic()
    hard_deadline = started + HARD_SECONDS if hard_deadline is None else hard_deadline
    worker_deadline = min(started + limit, hard_deadline - 6)
    record = {'started_at': utc(), 'limit_seconds': limit, 'hard_limit_seconds': HARD_SECONDS,
              'gated_before_job_assignment': True, 'errors': [], 'job_assigned': False,
              'job_active_final': None, 'worker_handle_closed': False, 'job_closed': False,
              'creation_identity_match': False}
    job = child = None
    try:
        job = OwnedJob()
        if time.monotonic() >= worker_deadline:
            raise StopProbe('PRODUCT_DEADLINE_EXPIRED')
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, creationflags=0x08000000, env={**safe_environment(os.environ), 'PYTHONIOENCODING': 'utf-8'})
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
                before, after = record.get('before', {}), record.get('after', {})
                if any(type(v.get(k)) is not int or v[k] <= 0
                        for v in (before, after) for k in ('pid', 'created_filetime')):
                    raise StopProbe('OWNED_WORKER_IDENTITY_UNPROVEN')
                if (before['created_filetime'], before['pid']) != (after['created_filetime'], after['pid']):
                    raise StopProbe('OWNED_WORKER_IDENTITY_MISMATCH')
                record['creation_identity_match'] = True
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
            record['creation_identity_match'] is True and
            record.get('after', {}).get('exit_observed') is True else 'UNKNOWN')
        save_new(Path(output_dir) / 'worker-release.json', record)
    return record


def worker_succeeded(record):
    return (record['state'] == 'RELEASED' and not record['errors'] and
        not record['hard_deadline_exceeded'] and record.get('after', {}).get('exit_code') == 0)


def worker_main(args, deadline):
    if sys.stdin.readline() != 'GO\n':
        return 71
    approval = authorize_args(args)
    require_marker('live-started.json', approval)
    claim_marker(LIVE_OUT / 'worker-claimed.json', approval)
    try:
        profile, fingerprint = native.profile_binding()
        if fingerprint != approval.profile_fingerprint or fingerprint != PROFILE_FINGERPRINT:
            raise Stop('PROFILE_BINDING_MISMATCH')
        save_new(LIVE_OUT / 'profile-binding.json', {'fingerprint': fingerprint, 'time': utc()})
        occupancy(profile, approval, args)
        for name in ('DEBUG', 'PWDEBUG', 'DEBUG_FILE'):
            os.environ.pop(name, None)
        async def bounded():
            return await asyncio.wait_for(observe_live(profile, approval), max(0.01, deadline - time.monotonic() - 10))
        return asyncio.run(bounded())
    except BaseException as error:
        save_new(LIVE_OUT / 'preflight-failure.json', {'outcome': 'ERROR', 'error': safe_error(error), 'successors': 'NOT_RUN'})
        return 2


def main(argv=None):
    for name in ('DEBUG', 'PWDEBUG', 'DEBUG_FILE'):
        os.environ.pop(name, None)
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    for name in ('launched', 'worker', 'occupancy'):
        parser.add_argument('--_' + name, action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not (args.live or args._launched or args._worker or args._occupancy):
        print(json.dumps({'mode': 'STATIC_ONLY', 'candidate_sha256': candidate(args.candidate_sha256),
            'ignore_https_errors': False, 'resources_created': False}))
        return 0
    approval = authorize_args(args)
    remaining = (approval.expires_at - datetime.now(timezone.utc)).total_seconds()
    if remaining <= 15:
        raise Stop('ACTIVATION_REMAINING_TIME_INSUFFICIENT')
    if args._occupancy:
        if sys.stdin.readline() != 'A24_CONTEXT_R1_OCCUPANCY\n':
            raise Stop('OCCUPANCY_PARENT_GATE_REQUIRED')
        require_marker('worker-claimed.json', approval)
        claim_marker(LIVE_OUT / 'occupancy-claimed.json', approval)
        profile, fingerprint = native.profile_binding()
        if fingerprint != approval.profile_fingerprint or fingerprint != PROFILE_FINGERPRINT or os.environ.pop('A24_CONTEXT_R1_PRIVATE_PROFILE', '') != str(profile):
            raise Stop('PROFILE_BINDING_MISMATCH')
        api_class, count = load_native()
        native.emit_occupancy_count(count(api_class(), str(profile)))
        return 0
    if args._worker:
        return worker_main(args, started + min(WORKER_SECONDS, remaining - 10))
    if not args._launched or sys.stdin.readline() != 'A24_CONTEXT_R1_LAUNCH\n':
        raise Stop('OUTER_LAUNCHER_REQUIRED')
    require_marker('launcher-claimed.json', approval)
    claim_marker(LIVE_OUT / 'live-started.json', approval)
    record = supervise([sys.executable, '-B', str(Path(__file__).resolve()), '--_worker'] +
        activation_argv(args), LIVE_OUT, limit=min(WORKER_SECONDS, remaining - 10),
        hard_deadline=started + min(HARD_SECONDS, remaining - 5))
    print(json.dumps({'mode': 'LIVE_FINISHED', 'release': record['state'],
        'worker_exit_code': record.get('after', {}).get('exit_code'), 'errors': bool(record['errors'])}))
    return 0 if worker_succeeded(record) else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Stop, native.StopProbe, OSError) as error:
        print(json.dumps({'outcome': 'ERROR', 'error': safe_error(error)}))
        raise SystemExit(2)
