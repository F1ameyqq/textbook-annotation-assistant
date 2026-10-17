"""Owned headless session; no annotation or question logic lives here."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from .guard import BrowserSafetyError, NetworkAudit, RequestPolicy
from .lease import ProfileLease


class HeadlessSession:
    """Reuse the authorized login helper without copying its profile or secrets.

    The helper's credentials are read internally, never exposed through this API.
    Every browser request is routed before navigation. APIRequestContext reads
    must separately call policy.decide because Playwright routing excludes them.
    """

    def __init__(self, login_root, *, ignore_https_errors=False, timeout_ms=30000, init_script=None):
        self.login_root = Path(login_root).resolve()
        self.ignore_https_errors = ignore_https_errors
        self.timeout_ms = timeout_ms
        self.init_script = init_script
        self.policy = RequestPolicy()
        self.audit = NetworkAudit()
        self.lease = None
        self.context = None
        self.page = None
        self._pw = None
        self._helper = None
        self.auth_mode = "UNCONFIRMED"
        self.context_closed = False
        self.failure_stage = None
        self.empty_bootstrap_count = 0
        self._local_bootstraps = set()
        self.transport_failures = {}

    def _empty_bootstrap(self, request):
        # Selecting a book initializes both panes at page1. Abort would prevent
        # the app from assigning its page count. This local, explicitly empty
        # placeholder contains no source pixels or platform frames and is never
        # used as observed evidence. The disallowed request is never sent.
        from .guard import BOOK_ID
        p = urlsplit(request.url)
        pairs = parse_qsl(p.query, keep_blank_values=True)
        query = dict(pairs)
        return (request.method == "GET" and self.auth_mode != "UNCONFIRMED"
                and self.empty_bootstrap_count < 2
                and p.scheme == "https" and p.netloc == "www.usense.com" and not p.fragment
                and p.path == "/qieti/api/annotate_pic/pre_annotation/" + BOOK_ID
                and len(pairs) == len(query)
                and query in ({"pageNum":"1","annotationType":"none"},
                              {"pageNum":"1","annotationType":"mr_pre"}))

    def _route(self, route):
        request = route.request
        allowed, category = self.policy.decide(request.method, request.url)
        if not allowed and category == "API_BLOCKED" and self._empty_bootstrap(request):
            self.empty_bootstrap_count += 1
            self._local_bootstraps.add(id(request))
            self.audit.record("GET", "LOCAL_EMPTY_BOOTSTRAP", False)
            from .guard import BOOK_ID
            import json
            route.fulfill(status=200, content_type="application/json", body=json.dumps(
                {"code":0,"data":{"file_id":BOOK_ID,"pages":[]}}))
            return
        self.audit.record(request.method, category, allowed)
        if allowed:
            # Chromium may auto-follow a redirect without routing the next hop.
            # Fetch exactly one hop ourselves; never let 307 replay a login POST
            # or let an allowed GET cross into an unknown origin/path/page.
            try:
                response = route.fetch(max_redirects=0, max_retries=0, timeout=self.timeout_ms)
                if 300 <= response.status < 400:
                    self.audit.record(request.method, category, False, response.status)
                    route.abort("blockedbyclient")
                else:
                    route.fulfill(response=response)
            except Exception as error:
                # Fixed transport categories only; no raw URL/header/message.
                detail=str(error)
                failure=('CERTIFICATE' if 'ERR_CERT_' in detail else
                         'TIMEOUT' if type(error).__name__=='TimeoutError' or 'Timeout' in detail else
                         'CONNECTION' if 'ECONN' in detail or 'ERR_CONNECTION' in detail else 'TRANSPORT')
                self.transport_failures[failure]=self.transport_failures.get(failure,0)+1
                self.audit.record(request.method, category, False)
                route.abort("blockedbyclient")
        else:
            route.abort("blockedbyclient")

    def _response(self, response):
        # No response bodies, raw URLs, cookies or authorization enter the audit.
        if id(response.request) in self._local_bootstraps:
            self.audit.record("GET", "LOCAL_EMPTY_BOOTSTRAP", False)
            return
        allowed, category = self.policy.classify(response.request.method, response.url)
        self.audit.record(response.request.method, category, allowed, response.status)

    def _websocket(self, websocket):
        self.audit.record("WEBSOCKET", "METHOD_BLOCKED", False)
        websocket.close()

    def _load_helper(self):
        path = self.login_root / "tools" / "usense_login.py"
        if not path.is_file():
            raise BrowserSafetyError("LOGIN_HELPER_MISSING", "prepare")
        spec = importlib.util.spec_from_file_location("a04_authorized_login_helper", path)
        helper = importlib.util.module_from_spec(spec)
        # dataclasses evaluates its module namespace during import.
        import sys
        sys.modules[spec.name] = helper
        spec.loader.exec_module(helper)
        self._helper = helper
        return helper

    def __enter__(self):
        stage = "prepare"
        credentials = None
        try:
            for key in ("DEBUG", "PWDEBUG"):
                os.environ.pop(key, None)
            helper = self._load_helper()
            credentials = helper.load_credentials(self.login_root / ".local" / "usense-login.json")
            key = hashlib.sha256(credentials.username.encode("utf-8")).hexdigest()[:20]
            profile = self.login_root / ".local" / "browser-profiles" / key
            self.lease = ProfileLease(profile)
            self.lease.acquire()
            stage = "launch"
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self.context = self._pw.chromium.launch_persistent_context(
                str(profile), channel="msedge", headless=True,
                viewport={"width": 1440, "height": 1000},
                accept_downloads=False, service_workers="block",
                ignore_https_errors=self.ignore_https_errors, timeout=self.timeout_ms,
            )
            self.context.route("**/*", self._route)
            self.context.route_web_socket("**/*", self._websocket)
            self.context.on("response", self._response)
            if self.init_script is not None:
                self.context.add_init_script(self.init_script)
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            self.page.set_default_timeout(self.timeout_ms)
            self.page.on("dialog", lambda dialog: dialog.dismiss())
            stage = "open_viewer"
            self.page.goto(helper.VIEWER_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
            self.page.locator(helper.VIEWER_MARKER + ', input[placeholder="请输入密码"]:visible').first.wait_for(
                state="visible", timeout=self.timeout_ms)
            if helper.verify_viewer(self.page):
                self.auth_mode = "REUSED"
            else:
                stage = "login"
                self.page.goto(helper.LOGIN_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
                helper.require_login_origin(self.page)
                self.page.get_by_placeholder("请输入用户名", exact=True).fill(credentials.username)
                helper.require_login_origin(self.page)
                self.page.get_by_placeholder("请输入密码", exact=True).fill(credentials.password)
                helper.require_login_origin(self.page)
                self.policy.login_window = True
                try:
                    self.page.get_by_role("button", name="登录", exact=True).click()
                    self.page.wait_for_url(lambda url: helper.trusted_url(str(url))
                                           and str(url).split("?", 1)[0] != helper.LOGIN_URL,
                                           timeout=self.timeout_ms)
                finally:
                    self.policy.login_window = False
                self.page.goto(helper.VIEWER_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
                self.page.locator(helper.VIEWER_MARKER).first.wait_for(state="visible", timeout=self.timeout_ms)
                if not helper.verify_viewer(self.page):
                    raise BrowserSafetyError("LOGIN_REQUIRED", "verify")
                self.auth_mode = "SINGLE_LOGIN"
            return self
        except BrowserSafetyError:
            self.failure_stage = stage
            self.close()
            raise
        except Exception as exc:
            self.failure_stage = stage
            self.close()
            code = "TIMEOUT" if type(exc).__name__ == "TimeoutError" else "SESSION_FAILED"
            raise BrowserSafetyError(code, stage) from None
        finally:
            credentials = None

    def close(self):
        close_failed = False
        if self.context is not None:
            try:
                self.context.close()
                self.context_closed = True
            except Exception:
                close_failed = True
            self.context = None
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                close_failed = True
            self._pw = None
        if self.lease is not None:
            try:
                self.lease.release()
            except BrowserSafetyError:
                close_failed = True
        return not close_failed

    def __exit__(self, exc_type, exc, tb):
        if not self.close() and exc_type is None:
            raise BrowserSafetyError("PROFILE_NOT_RELEASED", "close")

    def report(self):
        return {"auth_mode": self.auth_mode, "context_closed": self.context_closed,
                "headless": True, "viewport": [1440, 1000],
                "ignore_https_errors_this_run": self.ignore_https_errors,
                "failure_stage": self.failure_stage,
                "local_empty_bootstrap_count": self.empty_bootstrap_count,
                "transport_failure_counts":dict(self.transport_failures),
                "lease": self.lease.report() if self.lease else {"acquired": False, "released": False}}
