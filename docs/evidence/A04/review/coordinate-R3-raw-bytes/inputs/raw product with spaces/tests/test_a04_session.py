"""Offline HeadlessSession fault injection; no credentials or live browser.

The real lease writes only inside a temporary directory and its process count is
injected. Playwright and the authorized helper are replaced before entry.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from annotation.runtime.browser.guard import BrowserSafetyError, LOGIN_PATH
from annotation.runtime.browser.lease import LEASE_NAME, ProfileLease
from annotation.runtime.browser.session import HeadlessSession


SECRET = "synthetic-sensitive-value-never-print"
VIEWER = "https://www.usense.com/qieti/annotateUnified"
LOGIN = "https://www.usense.com/qieti/login"


class HeadlessSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a04 session offline ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    @contextmanager
    def rig(self, *, verify=(True,), checker=lambda _: 0, ignore=False):
        session = HeadlessSession(self.root, ignore_https_errors=ignore, timeout_ms=5)
        page = Mock()
        context = Mock(pages=[page])
        runtime = Mock()
        runtime.chromium.launch_persistent_context.return_value = context
        manager = Mock()
        manager.start.return_value = runtime
        helper = SimpleNamespace(
            load_credentials=Mock(return_value=SimpleNamespace(username="offline-test", password=SECRET)),
            verify_viewer=Mock(side_effect=list(verify)), require_login_origin=Mock(),
            trusted_url=Mock(return_value=True), VIEWER_URL=VIEWER,
            LOGIN_URL=LOGIN, VIEWER_MARKER=".offline-viewer:visible",
        )
        lease_instances = []
        def lease_factory(profile):
            lease = ProfileLease(profile, process_checker=checker)
            lease_instances.append(lease)
            return lease
        playwright = ModuleType("playwright")
        playwright.__path__ = []
        sync_api = ModuleType("playwright.sync_api")
        sync_api.sync_playwright = Mock(return_value=manager)
        with patch.dict(sys.modules, {"playwright": playwright, "playwright.sync_api": sync_api}), \
             patch.object(session, "_load_helper", return_value=helper), \
             patch("annotation.runtime.browser.session.ProfileLease", side_effect=lease_factory):
            yield SimpleNamespace(session=session, page=page, context=context,
                                  runtime=runtime, helper=helper, leases=lease_instances)

    def assert_released(self, rig):
        self.assertTrue(rig.session.report()["lease"]["released"])
        self.assertFalse(rig.session.report()["lease"]["owned_lease_present"])
        self.assertEqual([], list(self.root.rglob(LEASE_NAME)))
        self.assertNotIn(SECRET, json.dumps(rig.session.report()))

    def test_reuse_verifies_protected_ui_without_filling_or_submitting(self):
        with self.rig() as rig:
            with rig.session:
                self.assertEqual("REUSED", rig.session.auth_mode)
                rig.page.get_by_placeholder.assert_not_called()
                rig.page.get_by_role.assert_not_called()
                self.assertFalse(rig.session.policy.login_attempted)
                kwargs = rig.runtime.chromium.launch_persistent_context.call_args.kwargs
                self.assertTrue(kwargs["headless"])
                self.assertFalse(kwargs["ignore_https_errors"])
                self.assertEqual("block", kwargs["service_workers"])
                self.assertFalse(kwargs["accept_downloads"])
            rig.context.close.assert_called_once()
            rig.runtime.stop.assert_called_once()
            self.assertTrue(rig.session.context_closed)
            self.assert_released(rig)

    def test_fresh_login_clicks_once_and_guard_allows_only_one_login_post(self):
        with self.rig(verify=(False, True)) as rig:
            routes = []
            def login_click():
                for _ in range(2):  # A second browser request is blocked locally.
                    route = Mock(request=SimpleNamespace(method="POST", url="https://www.usense.com" + LOGIN_PATH))
                    route.fetch.return_value = SimpleNamespace(status=200)
                    rig.session._route(route)
                    routes.append(route)
            rig.page.get_by_role.return_value.click.side_effect = login_click
            with rig.session:
                self.assertEqual("SINGLE_LOGIN", rig.session.auth_mode)
                self.assertTrue(rig.session.policy.login_attempted)
                self.assertFalse(rig.session.policy.login_window)
                rig.page.get_by_role.return_value.click.assert_called_once()
                self.assertEqual(3, rig.helper.require_login_origin.call_count)
                self.assertEqual(["ALLOW", "BLOCK"], [r["decision"] for r in rig.session.audit.records])
                routes[0].fetch.assert_called_once_with(max_redirects=0, max_retries=0, timeout=5)
                routes[0].fulfill.assert_called_once_with(response=routes[0].fetch.return_value)
                routes[0].continue_.assert_not_called()
                routes[1].fetch.assert_not_called()
                routes[1].abort.assert_called_once_with("blockedbyclient")
                self.assertNotIn(SECRET, json.dumps(rig.session.audit.records))
            self.assert_released(rig)

    def test_login_timeout_never_retries_and_resets_window_before_release(self):
        with self.rig(verify=(False,)) as rig:
            rig.page.wait_for_url.side_effect = TimeoutError(SECRET)
            with self.assertRaises(BrowserSafetyError) as error:
                rig.session.__enter__()
            self.assertEqual("TIMEOUT:login", str(error.exception))
            self.assertNotIn(SECRET, str(error.exception))
            rig.page.get_by_role.return_value.click.assert_called_once()
            self.assertFalse(rig.session.policy.login_window)
            self.assertEqual("login", rig.session.report()["failure_stage"])
            rig.context.close.assert_called_once()
            rig.runtime.stop.assert_called_once()
            self.assert_released(rig)

    def test_launch_failure_stops_driver_and_releases_lease(self):
        with self.rig() as rig:
            rig.runtime.chromium.launch_persistent_context.side_effect = RuntimeError(SECRET)
            with self.assertRaises(BrowserSafetyError) as error:
                rig.session.__enter__()
            self.assertEqual("SESSION_FAILED:launch", str(error.exception))
            rig.context.close.assert_not_called()
            rig.runtime.stop.assert_called_once()
            self.assert_released(rig)

    def test_navigation_failure_releases_and_next_session_reacquires(self):
        with self.rig() as rig:
            rig.page.goto.side_effect = RuntimeError(SECRET)
            with self.assertRaises(BrowserSafetyError) as error:
                rig.session.__enter__()
            self.assertEqual("SESSION_FAILED:open_viewer", str(error.exception))
            rig.context.close.assert_called_once()
            self.assert_released(rig)
        with self.rig() as next_rig:
            with next_rig.session:
                self.assertEqual("REUSED", next_rig.session.auth_mode)
            self.assert_released(next_rig)

    def test_helper_failure_escapes_only_fixed_prepare_error(self):
        with self.rig() as rig:
            rig.helper.load_credentials.side_effect = RuntimeError(SECRET)
            with self.assertRaises(BrowserSafetyError) as error:
                rig.session.__enter__()
            self.assertEqual("SESSION_FAILED:prepare", str(error.exception))
            self.assertEqual([], rig.leases)
            rig.runtime.chromium.launch_persistent_context.assert_not_called()

    def test_profile_conflict_preserves_error_and_never_launches(self):
        with self.rig(checker=lambda _: 1) as rig:
            with self.assertRaises(BrowserSafetyError) as error:
                rig.session.__enter__()
            self.assertEqual("PROFILE_IN_USE:preflight", str(error.exception))
            rig.runtime.chromium.launch_persistent_context.assert_not_called()
            self.assertFalse(rig.session.report()["lease"]["released"])
            self.assertEqual([], list(self.root.rglob(LEASE_NAME)))

    def test_context_close_failure_is_fixed_error_and_driver_stop_is_attempted(self):
        with self.rig() as rig:
            rig.session.__enter__()
            rig.context.close.side_effect = RuntimeError(SECRET)
            with self.assertRaises(BrowserSafetyError) as error:
                rig.session.__exit__(None, None, None)
            self.assertEqual("PROFILE_NOT_RELEASED:close", str(error.exception))
            self.assertFalse(rig.session.report()["context_closed"])
            rig.runtime.stop.assert_called_once()
            self.assertFalse(rig.session.report()["lease"]["owned_lease_present"])

    def test_driver_stop_failure_does_not_skip_profile_release(self):
        with self.rig() as rig:
            rig.session.__enter__()
            rig.runtime.stop.side_effect = RuntimeError(SECRET)
            with self.assertRaises(BrowserSafetyError) as error:
                rig.session.__exit__(None, None, None)
            self.assertEqual("PROFILE_NOT_RELEASED:close", str(error.exception))
            rig.context.close.assert_called_once()
            self.assert_released(rig)

    def test_unreleased_process_proof_prevents_successful_exit(self):
        count = [0]
        def checker(_):
            count[0] += 1
            return 1 if count[0] >= 3 else 0
        with self.rig(checker=checker) as rig:
            rig.session.__enter__()
            with self.assertRaises(BrowserSafetyError) as error:
                rig.session.__exit__(None, None, None)
            self.assertEqual("PROFILE_NOT_RELEASED:close", str(error.exception))
            self.assertFalse(rig.session.report()["lease"]["released"])
            self.assertEqual(1, rig.session.report()["lease"]["post"]["process_count"])

    def test_missing_helper_is_fixed_prepare_error(self):
        session = HeadlessSession(self.root)
        with self.assertRaises(BrowserSafetyError) as error:
            session.__enter__()
        self.assertEqual("LOGIN_HELPER_MISSING:prepare", str(error.exception))
        self.assertIsNone(session.context)
        self.assertIsNone(session.lease)

    def test_explicit_certificate_option_is_per_context(self):
        with self.rig(ignore=True) as rig:
            with rig.session:
                kwargs = rig.runtime.chromium.launch_persistent_context.call_args.kwargs
                self.assertTrue(kwargs["ignore_https_errors"])
                self.assertTrue(rig.session.report()["ignore_https_errors_this_run"])
            self.assert_released(rig)

    def test_unknown_write_route_aborts_and_response_audit_has_no_raw_url(self):
        session = HeadlessSession(self.root)
        route = Mock(request=SimpleNamespace(method="POST", url="https://www.usense.com/qieti/api/save?token=" + SECRET))
        session._route(route)
        route.abort.assert_called_once_with("blockedbyclient")
        route.continue_.assert_not_called()
        route.fetch.assert_not_called()
        route.fulfill.assert_not_called()
        response = SimpleNamespace(request=Mock(method="GET"),
                                   url="https://www.usense.com/qieti/api/claim_book/books?title=" + SECRET,
                                   status=200)
        session._response(response)
        self.assertEqual(["BLOCK", "ALLOW"], [r["decision"] for r in session.audit.records])
        self.assertNotIn(SECRET, json.dumps(session.audit.records))
        self.assertEqual({"method", "category", "decision", "status", "time"}, set(session.audit.records[0]))

    def test_get_redirects_are_blocked_without_fetching_location_or_fulfilling(self):
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status):
                session = HeadlessSession(self.root, timeout_ms=5)
                route = Mock(request=SimpleNamespace(method="GET", url=VIEWER))
                route.fetch.return_value = SimpleNamespace(
                    status=status, headers={"location": "https://other.example/save?token=" + SECRET})
                session._route(route)
                route.fetch.assert_called_once_with(max_redirects=0, max_retries=0, timeout=5)
                route.abort.assert_called_once_with("blockedbyclient")
                route.fulfill.assert_not_called()
                route.continue_.assert_not_called()
                self.assertEqual(["ALLOW", "BLOCK"], [r["decision"] for r in session.audit.records])
                self.assertEqual(status, session.audit.records[-1]["status"])
                self.assertNotIn(SECRET, json.dumps(session.audit.records))

    def test_login_redirect_is_blocked_and_still_consumes_single_attempt(self):
        session = HeadlessSession(self.root, timeout_ms=5)
        session.policy.login_window = True
        first = Mock(request=SimpleNamespace(method="POST", url="https://www.usense.com" + LOGIN_PATH))
        first.fetch.return_value = SimpleNamespace(status=307)
        session._route(first)
        second = Mock(request=first.request)
        session._route(second)
        first.fetch.assert_called_once_with(max_redirects=0, max_retries=0, timeout=5)
        first.abort.assert_called_once_with("blockedbyclient")
        first.fulfill.assert_not_called()
        second.fetch.assert_not_called()
        second.abort.assert_called_once_with("blockedbyclient")
        self.assertTrue(session.policy.login_attempted)
        self.assertEqual(["ALLOW", "BLOCK", "BLOCK"], [r["decision"] for r in session.audit.records])

    def test_fetch_failure_aborts_with_redacted_audit(self):
        session = HeadlessSession(self.root)
        route = Mock(request=SimpleNamespace(method="GET", url=VIEWER))
        route.fetch.side_effect = RuntimeError(SECRET)
        session._route(route)
        route.abort.assert_called_once_with("blockedbyclient")
        route.fulfill.assert_not_called()
        self.assertEqual(["ALLOW", "BLOCK"], [r["decision"] for r in session.audit.records])
        self.assertNotIn(SECRET, json.dumps(session.audit.records))

    def test_confirmed_empty_bootstrap_is_local_exact_empty_and_limited_to_two(self):
        session = HeadlessSession(self.root)
        session.auth_mode = "REUSED"
        base = "https://www.usense.com/qieti/api/annotate_pic/pre_annotation/46007447?pageNum=1&annotationType="
        for index, annotation_type in enumerate(("none", "mr_pre"), start=1):
            request = Mock(method="GET", url=base + annotation_type)
            self.assertFalse(session.policy.decide(request.method, request.url)[0])
            route = Mock(request=request)
            session._route(route)
            route.fetch.assert_not_called()
            route.continue_.assert_not_called()
            route.abort.assert_not_called()
            route.fulfill.assert_called_once()
            kwargs = route.fulfill.call_args.kwargs
            self.assertEqual(200, kwargs["status"])
            self.assertEqual("application/json", kwargs["content_type"])
            self.assertEqual({"code": 0, "data": {"file_id": "46007447", "pages": []}},
                             json.loads(kwargs["body"]))
            self.assertEqual(index, session.report()["local_empty_bootstrap_count"])
            session._response(SimpleNamespace(request=request, url=request.url, status=200))
            for row in session.audit.records:
                self.assertEqual("BLOCK", row["decision"])
                self.assertEqual("LOCAL_EMPTY_BOOTSTRAP", row["category"])
        third = Mock(request=Mock(method="GET", url=base + "none"))
        session._route(third)
        third.abort.assert_called_once_with("blockedbyclient")
        third.fetch.assert_not_called()
        third.continue_.assert_not_called()
        third.fulfill.assert_not_called()
        self.assertEqual(2, session.report()["local_empty_bootstrap_count"])

    def test_empty_bootstrap_requires_confirmed_login(self):
        session = HeadlessSession(self.root)
        request = Mock(method="GET", url="https://www.usense.com/qieti/api/annotate_pic/pre_annotation/46007447?pageNum=1&annotationType=none")
        route = Mock(request=request)
        session._route(route)
        route.abort.assert_called_once_with("blockedbyclient")
        route.fetch.assert_not_called()
        route.continue_.assert_not_called()
        route.fulfill.assert_not_called()
        self.assertEqual(0, session.report()["local_empty_bootstrap_count"])

    def test_empty_bootstrap_never_applies_to_wrong_target_method_or_query(self):
        base = "https://www.usense.com/qieti/api/annotate_pic/pre_annotation/46007447?pageNum=1&annotationType=none"
        cases = (("POST", base), ("GET", base.replace("46007447", "46006966")),
                 ("GET", base + "&save=true"), ("GET", base + "&pageNum=1"),
                 ("GET", base.replace("pageNum=1", "pageNum=2")),
                 ("GET", base.replace("annotationType=none", "annotationType=ocr")),
                 ("GET", base.replace("https://", "http://")),
                 ("GET", base.replace("www.usense.com", "www.usense.com.other.example")))
        for method, url in cases:
            with self.subTest(method=method, url=url):
                session = HeadlessSession(self.root)
                session.auth_mode = "SINGLE_LOGIN"
                route = Mock(request=Mock(method=method, url=url))
                session._route(route)
                route.abort.assert_called_once_with("blockedbyclient")
                route.fetch.assert_not_called()
                route.continue_.assert_not_called()
                route.fulfill.assert_not_called()
                self.assertEqual(0, session.report()["local_empty_bootstrap_count"])

    def test_authorized_page_uses_network_response_and_no_local_bootstrap(self):
        session = HeadlessSession(self.root)
        session.auth_mode = "REUSED"
        request = Mock(method="GET", url="https://www.usense.com/qieti/api/annotate_pic/pre_annotation/46007447?pageNum=14&annotationType=none")
        route = Mock(request=request)
        route.fetch.return_value = SimpleNamespace(status=200)
        session._route(route)
        route.fetch.assert_called_once()
        route.fulfill.assert_called_once_with(response=route.fetch.return_value)
        route.abort.assert_not_called()
        self.assertEqual(0, session.report()["local_empty_bootstrap_count"])

    def test_websocket_is_closed_with_blocked_audit(self):
        session = HeadlessSession(self.root)
        websocket = Mock()
        session._websocket(websocket)
        websocket.close.assert_called_once()
        self.assertEqual("BLOCK", session.audit.records[-1]["decision"])


if __name__ == "__main__":
    unittest.main()
