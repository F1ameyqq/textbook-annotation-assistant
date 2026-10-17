"""Fail-closed A04 request policy and deliberately small redacted audit.

This whitelist is specific to the authorized book and three viewer pages.  A
GET is not sufficient evidence of a read operation: unknown API paths fail.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Optional
import unicodedata
from urllib.parse import parse_qsl, urlsplit


BOOK_ID = "46007447"
VIEWER_PAGES = frozenset({14, 15, 173})
OSS_HOST = "oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com"
API_PREFIX = "/qieti/api/"
LOGIN_PATH = API_PREFIX + "user_login/login"

_CATEGORIES = frozenset({
    "NAVIGATION", "STATIC", "LOGIN", "SESSION_PROFILE", "SESSION_PERMISSIONS",
    "SESSION_TEAMS", "BOOK_LIST", "SOURCE_METADATA", "DIRECTORY",
    "SOURCE_INDEX", "SOURCE_PAGE", "ANNOTATIONS", "OCR_SUMMARY", "ORIGINAL_IMAGE",
    "API_BLOCKED", "METHOD_BLOCKED", "ORIGIN_BLOCKED", "URL_BLOCKED",
    "IMAGE_BLOCKED", "UNKNOWN", "LOCAL_EMPTY_BOOTSTRAP",
})
_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
_STATIC = re.compile(
    r"/(?:qieti/)?(?:assets|static)/[^%\\]*\.(?:js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|webp)$",
    re.IGNORECASE,
)
_ORIGINAL = re.compile(
    r"/upload_images/46007447/46007447_page_(13|14|172)\.(?:jpg|jpeg|png|webp)$",
    re.IGNORECASE,
)


class BrowserSafetyError(Exception):
    """Only fixed codes/stages may escape this boundary; no raw exception text."""

    _CODES = frozenset({
        "INVALID_IMAGE_URL", "INVALID_POLICY_INPUT", "PROFILE_PATH_UNAVAILABLE",
        "PROFILE_IN_USE", "PROFILE_LOCK_CONFLICT", "PROFILE_LEASE_CONFLICT",
        "PROCESS_CHECK_UNAVAILABLE", "PROCESS_CHECK_FAILED", "LEASE_WRITE_FAILED",
        "LEASE_OWNERSHIP_LOST", "LEASE_RELEASE_FAILED", "PROFILE_NOT_RELEASED",
        "LOGIN_HELPER_MISSING", "LOGIN_REQUIRED", "TIMEOUT", "SESSION_FAILED",
        "REQUEST_BLOCKED", "TARGET_MISMATCH", "RESOURCE_FAILED", "UI_MISMATCH",
        "STALE_STATE", "OUTPUT_EXISTS", "COLLECT_FAILED", "COORDINATE_FAILED",
    })
    _STAGES = frozenset({
        "policy", "acquire", "preflight", "release", "process_check", "prepare",
        "launch", "open_viewer", "login", "verify", "close", "collect", "fetch",
        "navigate", "download",
    })

    def __init__(self, code: str, stage: str):
        self.code = code if isinstance(code, str) and code in self._CODES else "INVALID_POLICY_INPUT"
        self.stage = stage if isinstance(stage, str) and stage in self._STAGES else "policy"
        super().__init__(f"{self.code}:{self.stage}")


def _parts(url: str):
    """Reject ambiguous paths/origins before any whitelist comparison."""
    if not isinstance(url, str) or any(ord(c) < 32 or ord(c) == 127 for c in url):
        return None
    try:
        parts = urlsplit(url)
        if (parts.scheme != "https" or parts.port not in (None, 443)
                or parts.username is not None or parts.password is not None
                or parts.fragment or "%" in parts.path or "\\" in parts.path
                or "//" in parts.path or any(s in {".", ".."} for s in parts.path.split("/"))):
            return None
        return parts
    except (ValueError, TypeError):
        return None


def _query(parts) -> Optional[dict]:
    if not parts.query:
        return {}
    try:
        pairs = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return None
    values = dict(pairs)
    if len(values) != len(pairs):
        return None
    return values


class RequestPolicy:
    """Policy decisions also consume the single, explicitly opened login slot.

    Signed image URLs are kept only in memory and must first be registered from
    a checked source response.  They never become audit records.
    """

    def __init__(self):
        self.login_window = False
        self._login_used = False
        self._images = set()

    @property
    def login_attempted(self) -> bool:
        return self._login_used

    def register_image(self, url: str) -> None:
        parts = _parts(url)
        if (parts is None or parts.hostname != OSS_HOST
                or _ORIGINAL.fullmatch(parts.path) is None):
            raise BrowserSafetyError("INVALID_IMAGE_URL", "policy")
        self._images.add(url)

    def decide(self, method: str, url: str) -> tuple:
        allowed, category = self.classify(method, url)
        if allowed and category == "LOGIN":
            if not self.login_window or self._login_used:
                return False, "METHOD_BLOCKED"
            self._login_used = True
        return allowed, category

    def classify(self, method: str, url: str) -> tuple:
        """Pure endpoint classification for response auditing.

        The LOGIN category identifies an eligible endpoint; only ``decide``
        enforces the opened one-attempt slot.  It must be used before sending.
        """
        if not isinstance(method, str) or method.upper() not in _METHODS:
            return False, "METHOD_BLOCKED"
        method = method.upper()
        parts = _parts(url)
        if parts is None:
            return False, "URL_BLOCKED"
        if parts.hostname == OSS_HOST:
            if method == "GET" and url in self._images:
                return True, "ORIGINAL_IMAGE"
            return False, "IMAGE_BLOCKED"
        if parts.hostname != "www.usense.com":
            return False, "ORIGIN_BLOCKED"
        query = _query(parts)
        if query is None:
            return False, "URL_BLOCKED"
        path = parts.path
        if path == LOGIN_PATH:
            if method == "POST" and not query:
                return True, "LOGIN"
            return False, "METHOD_BLOCKED"
        if method != "GET":
            return False, "METHOD_BLOCKED"
        if path in {"/qieti", "/qieti/", "/qieti/login", "/qieti/annotateUnified"} and not query:
            return True, "NAVIGATION"
        if path.startswith(API_PREFIX):
            return self._api(path, query)
        # An API-like path cannot bypass the API whitelist with a file extension.
        if "/api/" in path or "/api" == path:
            return False, "API_BLOCKED"
        if _STATIC.fullmatch(path) or path in {"/favicon.ico", "/qieti/favicon.ico"}:
            return True, "STATIC"
        return False, "URL_BLOCKED"

    @staticmethod
    def _api(path: str, query: dict) -> tuple:
        exact = {
            API_PREFIX + "user_login/profile": "SESSION_PROFILE",
            API_PREFIX + "user_login/config/permissions": "SESSION_PERMISSIONS",
            API_PREFIX + "user_login/config/teams": "SESSION_TEAMS",
            API_PREFIX + "annotate_ocr/structured-upload/import-id/" + BOOK_ID: "SOURCE_METADATA",
            API_PREFIX + "annotate_pic/get_manual_annotations_unified/" + BOOK_ID: "ANNOTATIONS",
        }
        if path in exact and not query:
            return True, exact[path]
        if path == API_PREFIX + "claim_book/books":
            list_filters = {"page", "pageSize", "status_list", "id", "title",
                            "team_name", "username", "role", "is_admin"}
            if (set(query) <= list_filters
                    and all(len(value) <= 256 and not any(unicodedata.category(c) == "Cc" for c in value)
                            for value in query.values())
                    and query.get("id", "") in {"", BOOK_ID}
                    and re.fullmatch(r"[1-9][0-9]{0,8}", query.get("page", "1"))
                    and re.fullmatch(r"[1-9][0-9]{0,2}", query.get("pageSize", "10"))
                    and int(query.get("pageSize", "10")) <= 100):
                return True, "BOOK_LIST"
        if path == API_PREFIX + "annotate_ocr/directory/get" and query == {"file_id": BOOK_ID}:
            return True, "DIRECTORY"
        if path == API_PREFIX + "verify_annotation/unified-ocr-task/summary" and query == {"file_id": BOOK_ID}:
            return True, "OCR_SUMMARY"
        if path == API_PREFIX + "annotate_pic/pre_annotation_source/" + BOOK_ID:
            if set(query) == {"annotationType"} and query["annotationType"] in {"mr_pre", "none"}:
                return True, "SOURCE_INDEX"
        if path == API_PREFIX + "annotate_pic/pre_annotation/" + BOOK_ID:
            if (set(query) == {"pageNum", "annotationType"}
                    and query["annotationType"] in {"mr_pre", "none"}
                    and query["pageNum"] in {str(p) for p in VIEWER_PAGES}):
                return True, "SOURCE_PAGE"
        return False, "API_BLOCKED"


class NetworkAudit:
    """Only these five fields can be recorded; no URL/header/body arguments."""

    def __init__(self, clock=None):
        self._records = []
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @property
    def records(self) -> list:
        return [dict(row) for row in self._records]

    def record(self, method: str, category: str, allowed: bool,
               status: Optional[int] = None) -> None:
        method = method.upper() if isinstance(method, str) else "UNKNOWN"
        method = method if method in _METHODS else "UNKNOWN"
        category = category if isinstance(category, str) and category in _CATEGORIES else "UNKNOWN"
        status = status if type(status) is int and 100 <= status <= 599 else None
        self._records.append({
            "method": method, "category": category,
            "decision": "ALLOW" if allowed is True else "BLOCK",
            "status": status, "time": self._clock().isoformat(),
        })
