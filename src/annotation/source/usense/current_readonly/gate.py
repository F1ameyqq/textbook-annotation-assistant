"""Pure A24 current-contract authorization; credentials and login are forbidden."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re

TASK = 'A24'
WORKFLOW = '2574b9be93886494ce0b7b91798e65f83ce00341'
SCOPE = 'CURRENT_OFFICIAL_CONTEXT_SOURCE_AND_FIRST_SAVE_PREPARATION_READONLY'
OWNER = '01a15cf8-0c63-70d3-b374-ce85e6f29fd7'
COORDINATOR = '01a15768-1e2d-7781-b29f-1f7376270216'
RUN_ID = 'A24-current-context-r1-' + OWNER
BOOK = '46007447'
VIEWERS = [14, 173]
ORIGIN = 'https://www.usense.com'
TARGET = ORIGIN + '/qieti/annotateUnified'
LOGIN = ORIGIN + '/qieti/login'
LOGIN_POST = ORIGIN + '/qieti/api/user_login/login'
PROFILE_FINGERPRINT = 'b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00'
OUTPUT = 'D:/1800/.local/stages/a24-current-context-r1-live'
ACTIVATION = 'D:/1800/.local/stages/a24-current-context-r1-activation.json'
DECISION = 'D:/1800/docs/approvals/A24-current-context-r1-user-decision.json'
REPORT = 'D:/1800/docs/evidence/coordinator/a24-current-context-r1-independent-closure/independent-result.json'
EXCLUDED_STATIC_LIMIT = 16
VERSION_CHECK_LIMIT = 1
STANDING_PERMISSION = 'D:/1800/docs/approvals/A17-excluded-static-user-decision.json'
STANDING_PERMISSION_SHA = 'f5ceacf9028f773ead882f3e6601004c2c3e28171be31abb85c5be99a1d67b46'
STATIC_IMAGE_PATH_PATTERN = r'/(?:qieti/)?assets/[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)*\.(?i:png|jpg|jpeg|gif|svg|ico|webp)'


class Stop(Exception):
    """Only enumerated codes may be serialized, never arbitrary exception text."""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_sha(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def same_typed(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same_typed(a, e) for a, e in zip(actual, expected))
    return actual == expected


def unique_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Stop('DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
    except (ValueError, UnicodeError, AttributeError):
        raise Stop('JSON_REJECTED') from None


def parse_utc(value):
    if not isinstance(value, str) or not re.fullmatch(
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)', value):
        raise Stop('TIME_REJECTED')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise Stop('TIME_REJECTED') from None


@dataclass(frozen=True)
class Approval:
    candidate_sha256: str
    profile_fingerprint: str
    activation_sha256: str
    not_before: datetime
    expires_at: datetime
    ignore_https_errors: bool = False


def fixed_fields(candidate, profile):
    return {'schema': 'A24-current-context-r1-activation/v1', 'task': TASK,
        'workflow_commit': WORKFLOW, 'executor_thread_id': OWNER,
        'coordinator_thread_id': COORDINATOR, 'run_id': RUN_ID, 'book_id': BOOK,
        'viewers': VIEWERS, 'target': TARGET, 'candidate_manifest_sha256': candidate,
        'profile_fingerprint': profile, 'output_directory': OUTPUT,
        'activation_path': ACTIVATION, 'decision_path': DECISION, 'report_path': REPORT,
        'excluded_static_event_limit': EXCLUDED_STATIC_LIMIT,
        'version_check_limit': VERSION_CHECK_LIMIT,
        'standing_tls_permission_path': STANDING_PERMISSION,
        'standing_tls_permission_sha256': STANDING_PERMISSION_SHA,
        'new_live_limit': 1, 'context_limit': 1, 'navigation_limit': 1,
        'business_get_limit_per_url': 1, 'original_limit_per_viewer': 1,
        'scope': SCOPE, 'sample_limit': 0, 'automatic_schema_confirmation': False,
        'fixed_business_get_count': 4, 'selected_page_get_count': 2,
        'total_logical_json_get_count': 6, 'original_get_count': 2,
        'excluded_sample_orders': [22], 'total_seconds': 900,
        **auth_scope(), **static_image_scope(), **contract_scope(), 'login_submission_limit': 0, 'business_write_limit': 0,
        'upload_limit': 0, 'ocr_limit': 0, 'old_budgets_restored': False,
        'independent_preflight': 'ACCEPTED_OFFLINE_ONLY'}


def scope_binding(candidate):
    return {'task': TASK, 'run_id': RUN_ID, 'workflow_commit': WORKFLOW,
        'scope': SCOPE, 'candidate_manifest_sha256': candidate,
        'sample_limit': 0, 'automatic_schema_confirmation': False,
        'fixed_business_get_count': 4, 'selected_page_get_count': 2,
        'total_logical_json_get_count': 6, 'original_get_count': 2,
        'new_live_limit': 1, 'context_limit': 1, 'navigation_limit': 1, 'total_seconds': 900,
        'business_get_limit_per_url': 1, 'original_limit_per_viewer': 1,
        **auth_scope(), **static_image_scope(), **contract_scope(), 'login_submission_limit': 0, 'business_write_limit': 0, 'upload_limit': 0, 'ocr_limit': 0,
        'old_budgets_restored': False,
        'executor_thread_id': OWNER, 'output_directory': OUTPUT,
        'activation_path': ACTIVATION, 'decision_path': DECISION, 'report_path': REPORT,
        'excluded_static_event_limit': EXCLUDED_STATIC_LIMIT,
        'version_check_limit': VERSION_CHECK_LIMIT,
        'standing_tls_permission_path': STANDING_PERMISSION,
        'standing_tls_permission_sha256': STANDING_PERMISSION_SHA}


def contract_scope():
    from .context_query import KEYS, ADMIN_STATUS, OTHER_STATUS, MAX_CONTEXT_UNITS
    return {'book_request_plan': 'OFFICIAL_NINE_KEY_EXISTING_PAGE_CONTEXT_TARGET_QUERY',
        'book_query_key_order': list(KEYS),
        'book_query_context_source': 'ORIGINAL_PAGE_LOCALSTORAGE_USER_USERNAME_ROLE',
        'book_query_prepare_limit': 1, 'book_query_recheck_limit': 1,
        'book_query_bind_limit': 1, 'book_query_logical_slot': 'BOOK',
        'book_context_max_utf16_units': MAX_CONTEXT_UNITS,
        'book_context_missing_or_change': 'STOP_ZERO_SEND_NO_FALLBACK',
        'book_status_admin_roles': ['admin', 'delivery_admin'],
        'book_status_admin_literal': ADMIN_STATUS, 'book_status_other_literal': OTHER_STATUS,
        'book_is_admin_semantics': 'RAW_ROLE_STRICT_EQUALS_ADMIN',
        'book_query_encoder': 'ENCODE_URI_COMPONENT_AXIOS_COLON_DOLLAR_COMMA_SPACE_PLUS',
        'book_query_URL_normalization_change': 'STOP_UNSUPPORTED_NO_APPROXIMATION',
        'book_query_account_memory': 'EPHEMERAL_URL_IN_PAGE_AND_PYTHON_NATIVE_MEMORY',
        'query_value_export_limit': 0, 'account_fingerprint_export_limit': 0,
        'book_list_precedence': ['records', 'books', 'list'],
        'book_identity_field': 'id', 'book_duplicate_target_limit': 1,
        'response_projection': 'A24_FINITE_WHITELIST_BEFORE_ADAPTATION',
        'business_response_body_export_limit': 0, 'unknown_response_key_export_limit': 0,
        'book_context_parameter_addition_limit': 6, 'pagination_limit': 1,
        'book_picker_action_limit': 0, 'mapping_ui_actions_limit': 0,
        'mapping_semantics': 'RESPONSE_RESOURCE_WITH_PASSIVE_CANVAS_CHECK',
        'save_page_mapping': 'UNKNOWN_UNTIL_CURRENT_PROOF',
        'prior_readonly_allocation_remaining': 0, 'new_revised_checkpoint_limit': 1,
        'source_contract_supplement_sha256': '34a2f98a22d8e62e192ef0dfdb58601a3b76edfea7f213256bf62eb10f00c4b1',
        'source_contract_supplement_workflow': 'cd591394db393b8f27d9f45d1e1890725d95d800',
        'logical_json_slot_names': ['book', 'directory', 'frames', 'source', 'page14', 'page173'],
        'logical_json_send_limit_per_slot': 1,
        'frame_envelope_policy': 'ENDPOINT_LOCAL_HN_0_200_OR_EXPLICIT_TOP_ANNOTATIONS',
        'source_identity_policy': 'RETURNED_MATCH_IF_PRESENT_REQUEST_BINDING_DISTINCT',
        'page_request_branch': 'EXCLUSIVE_LEGACY_OR_OSS_FROM_CURRENT_SOURCE_NO_FALLBACK',
        'page_origins': [ORIGIN, 'https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com'],
        'oss_path_namespace': '/upload_images/' + BOOK + '/',
        'oss_public_authorization_header_limit': 0, 'token_query_append_limit': 0,
        'source_template_operation': 'FIRST_PERCENT_D_THEN_FIRST_PAGE_INDEX_VIEWER_MINUS_ONE',
        'source_page_rebind_limit': 0, 'source_page_fallback_limit': 0,
        'directory_order_policy': 'RAW_PLUS_SEPARATE_FRONTEND_DFS_NO_SAVE_ORDER',
        'oss_page_representation': 'FRONTEND_DERIVED_NOT_RAW_SERVER_RESPONSE'}


def auth_scope():
    return {'navigation_sequence': [TARGET], 'session_phase_limit': 1,
        'session_completion_timeout_seconds': 20,
        'active_session_get_path': '/qieti/api/user_login/profile',
        'active_session_get_limit': 1,
        'local_credential_config_read_limit': 0, 'login_form_fill_limit': 0,
        'login_ui_click_limit': 0, 'required_profile_fingerprint': PROFILE_FINGERPRINT,
        'session_get_limit_per_path_per_phase': 1, 'session_get_limit_total': 3,
        'session_get_paths': ['/qieti/api/user_login/profile',
            '/qieti/api/user_login/config/permissions', '/qieti/api/user_login/config/teams'],
        'refresh_post_limit': 0, 'automatic_request_resend_limit': 0,
        'existing_session_token_usage': 'IN_PAGE_APPROVED_GET_ONLY', 'token_export_limit': 0}


def static_image_scope():
    return {'static_image_path_pattern': STATIC_IMAGE_PATH_PATTERN,
        'static_image_method': 'GET', 'static_image_resource_type': 'Image',
        'static_image_origin': ORIGIN, 'static_image_query_allowed': False,
        'static_image_redirect_allowed': False,
        'static_image_original_main_frame_required': True,
        'static_image_precedes_basename_protection': True}


def validate_activation(raw, expected_sha, candidate, profile, decision_raw,
                        report_raw, *, explicit_live=False, exception=False, now=None):
    """No I/O. Decisions and independent report are bound by raw-byte digest."""
    if explicit_live is not True or not all(is_sha(v) for v in (expected_sha, candidate, profile)):
        raise Stop('EXPLICIT_A24_ACTIVATION_REQUIRED')
    if profile != PROFILE_FINGERPRINT:
        raise Stop('A24_FIXED_PROFILE_REQUIRED')
    if not isinstance(raw, bytes) or sha(raw) != expected_sha:
        raise Stop('ACTIVATION_DIGEST_MISMATCH')
    data = unique_json(raw)
    fixed = fixed_fields(candidate, profile)
    extras = {'not_before', 'expires_at', 'tls_mode', 'user_decision_sha256', 'independent_report_sha256'}
    if type(data) is not dict or set(data) != set(fixed) | extras:
        raise Stop('ACTIVATION_FIELDS_REJECTED')
    for key, value in fixed.items():
        if not same_typed(data[key], value):
            raise Stop('ACTIVATION_BINDING_MISMATCH')
    if (not isinstance(decision_raw, bytes) or not isinstance(report_raw, bytes) or
            sha(decision_raw) != data['user_decision_sha256'] or
            sha(report_raw) != data['independent_report_sha256']):
        raise Stop('A24_DECISION_REPORT_BINDING_REQUIRED')
    decision, report = unique_json(decision_raw), unique_json(report_raw)
    for document in (decision, report):
        if type(document) is not dict or any(
                not same_typed(document.get(k), v) for k, v in scope_binding(candidate).items()):
            raise Stop('OBSERVATION_SCOPE_BINDING_REQUIRED')
    mode = 'CONTEXT_EXCEPTION' if exception is True else 'STRICT'
    if (data['tls_mode'] != mode or decision.get('task') != TASK or
            decision.get('run_id') != RUN_ID or decision.get('tls_mode') != mode or
            decision.get('live_authorized') is not True or
            decision.get('certificate_exception_authorized') is not exception):
        raise Stop('A24_TLS_DECISION_REQUIRED')
    if (decision.get('login_submission_authorized') is not False or
            decision.get('credential_transmission_authorized') is not False or
            decision.get('credential_tls_exception_authorized') is not False or
            decision.get('local_credential_config_read_authorized') is not False or
            decision.get('authorization_basis') != 'A17_STANDING_READONLY_TLS_PERMISSION_BOUND_TO_A24_CURRENT_CONTEXT_R1'):
        raise Stop('A24_READONLY_DECISION_REQUIRED')
    if (report.get('task') != TASK or report.get('candidate_manifest_sha256') != candidate or
            report.get('result') != 'ACCEPTED_OFFLINE_ONLY'):
        raise Stop('A24_INDEPENDENT_PREFLIGHT_REQUIRED')
    start, end = parse_utc(data['not_before']), parse_utc(data['expires_at'])
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or not 0 < (end - start).total_seconds() <= 900 or not start <= now < end:
        raise Stop('ACTIVATION_WINDOW_REJECTED')
    return Approval(candidate, profile, expected_sha, start, end, exception)


def context_options(approval=None, now=None):
    if approval is None:
        return {'ignore_https_errors': False}
    now = datetime.now(timezone.utc) if now is None else now
    if type(approval) is not Approval or not approval.not_before <= now < approval.expires_at:
        raise Stop('CONTEXT_APPROVAL_REJECTED')
    return {'ignore_https_errors': approval.ignore_https_errors}


def marker(approval):
    if type(approval) is not Approval:
        raise Stop('A24_MARKER_APPROVAL_REQUIRED')
    return {'task': TASK, 'run_id': RUN_ID, 'candidate_sha256': approval.candidate_sha256,
        'workflow_commit': WORKFLOW, 'scope': SCOPE, 'sample_limit': 0,
        'activation_sha256': approval.activation_sha256,
        'profile_fingerprint': approval.profile_fingerprint,
        'certificate_exception': approval.ignore_https_errors}
