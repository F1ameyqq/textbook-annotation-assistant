"""Independent A04 offline boundary probes; no browser or HTTP connection.

Node, when installed, executes the actual evaluate function with fake fetch and
fake localStorage only. Its process has a bounded fallback deadline. All values
are synthetic; neither the authorized login helper nor credentials are read.
"""
import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from contextlib import redirect_stdout
from urllib.parse import parse_qs, urlsplit

from annotation.runtime.browser.guard import BrowserSafetyError, BOOK_ID, NetworkAudit, RequestPolicy
from annotation.runtime.browser.session import HeadlessSession
from annotation.source.usense import collector, parse_capture
from annotation.source.usense import cli


REPOSITORY = Path(__file__).resolve().parents[1]
FIXTURE = REPOSITORY / "tests/fixtures/a04/source"
ORIGIN = "https://www.usense.com"
NODE = shutil.which("node")


def fake_route(method="GET", path="/qieti/annotateUnified", status=200):
    request = SimpleNamespace(method=method, url=ORIGIN + path)
    route = MagicMock()
    route.request = request
    route.fetch.return_value = SimpleNamespace(status=status)
    return route


class RouteBoundaryTests(unittest.TestCase):
    def setUp(self):
        # __init__ is inert; this fake path is never opened by a helper/browser.
        self.session = HeadlessSession("unused-synthetic-login-root", timeout_ms=50)

    def test_allowed_browser_request_fetches_one_hop_then_fulfills(self):
        route = fake_route()
        self.session._route(route)
        options = route.fetch.call_args.kwargs
        self.assertEqual(options["max_redirects"], 0)
        self.assertEqual(options["max_retries"], 0)
        self.assertGreater(options["timeout"], 0)
        route.fulfill.assert_called_once_with(response=route.fetch.return_value)
        route.continue_.assert_not_called()
        route.abort.assert_not_called()

    def test_all_browser_redirects_are_blocked_without_fulfill(self):
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status):
                route = fake_route(status=status)
                self.session._route(route)
                route.abort.assert_called_once()
                route.fulfill.assert_not_called()
                route.continue_.assert_not_called()
                self.assertEqual(self.session.audit.records[-1]["decision"], "BLOCK")

    def test_allowed_login_post_cannot_redirect_or_be_replayed(self):
        self.session.policy.login_window = True
        route = fake_route("POST", "/qieti/api/user_login/login", 307)
        self.session._route(route)
        self.assertEqual(route.fetch.call_args.kwargs["max_redirects"], 0)
        route.abort.assert_called_once()
        route.fulfill.assert_not_called()
        second = fake_route("POST", "/qieti/api/user_login/login", 200)
        self.session._route(second)
        second.fetch.assert_not_called()
        second.abort.assert_called_once()

    def test_unknown_mutating_request_never_reaches_fetch(self):
        route = fake_route("POST", "/qieti/api/annotate_pic/commit_unified_submit")
        self.session._route(route)
        route.fetch.assert_not_called()
        route.continue_.assert_not_called()
        route.abort.assert_called_once()

    def test_transport_failure_aborts_and_records_only_safe_fields(self):
        route = fake_route()
        route.fetch.side_effect = RuntimeError("SYNTHETIC-SECRET-DO-NOT-EMIT")
        self.session._route(route)
        route.abort.assert_called_once()
        route.fulfill.assert_not_called()
        audit = json.dumps(self.session.audit.records)
        self.assertNotIn("SECRET", audit)
        self.assertNotIn("https", audit)
        self.assertEqual(self.session.audit.records[-1]["decision"], "BLOCK")

    def test_response_audit_does_not_mark_forbidden_response_allowed(self):
        request = SimpleNamespace(method="POST", url=ORIGIN + "/qieti/api/annotate_pic/save")
        self.session._response(SimpleNamespace(request=request, url=request.url, status=200))
        self.assertEqual(self.session.audit.records[-1]["decision"], "BLOCK")

    def test_websocket_guard_is_installed_before_navigation(self):
        helper = MagicMock()
        helper.load_credentials.return_value = SimpleNamespace(username="synthetic-user", password="synthetic-password")
        helper.VIEWER_URL = ORIGIN + "/qieti/annotateUnified"
        helper.VIEWER_MARKER = ".synthetic-marker"
        helper.verify_viewer.return_value = True
        page, context, driver, lease = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        context.pages = [page]
        driver.chromium.launch_persistent_context.return_value = context
        events = []
        context.route_web_socket.side_effect = lambda *args, **kwargs: events.append("socket_guard")
        page.goto.side_effect = lambda *args, **kwargs: events.append("navigation")
        with patch.object(self.session, "_load_helper", return_value=helper), \
                patch("annotation.runtime.browser.session.ProfileLease", return_value=lease), \
                patch("playwright.sync_api.sync_playwright") as start:
            start.return_value.start.return_value = driver
            with self.session:
                pass
        context.route_web_socket.assert_called_once()
        self.assertLess(events.index("socket_guard"), events.index("navigation"))
        websocket = MagicMock()
        context.route_web_socket.call_args.args[1](websocket)
        websocket.close.assert_called_once()
        websocket.connect_to_server.assert_not_called()


class CollectorParsingReviewTests(unittest.TestCase):
    def test_equal_book_aliases_describe_one_target(self):
        book = {"id": BOOK_ID, "title": "SYNTHETIC target", "status": "SYNTHETIC"}
        result = collector._book({"code": 0, "data": {
            "records": [book], "books": [copy.deepcopy(book)], "list": [copy.deepcopy(book)]}})
        self.assertEqual(result, book)

    def test_conflicting_book_aliases_still_fail_closed(self):
        book = {"id": BOOK_ID, "question_count": 22}
        other = {"id": BOOK_ID, "question_count": 23}
        with self.assertRaises(BrowserSafetyError) as error:
            collector._book({"code": 0, "data": {"records": [book], "books": [other]}})
        self.assertEqual(error.exception.code, "TARGET_MISMATCH")

    def test_current_state_book_list_is_scoped_to_authorized_id(self):
        def response(session, endpoint):
            if "claim_book/books" in endpoint:
                return {"code": 0, "data": [{"id": BOOK_ID}]}
            if "directory/get" in endpoint:
                return {"code": 0, "data": {"directory_data": []}}
            return {"code": 0, "data": []}
        with patch.object(collector, "get_business", side_effect=response) as get:
            collector._current(SimpleNamespace())
        endpoint = get.call_args_list[0].args[1]
        self.assertEqual(parse_qs(urlsplit(endpoint).query).get("id"), [BOOK_ID])

    def test_business_login_expiry_codes_survive_http_200(self):
        for code in (401, 403, "401", "403"):
            with self.subTest(code=code), self.assertRaises(BrowserSafetyError) as error:
                collector._business({"http_status": 200, "body": {"code": code, "token": "SYNTHETIC-SECRET"}})
            self.assertEqual(error.exception.code, "LOGIN_REQUIRED")
            self.assertNotIn("SECRET", str(error.exception))

    def test_offline_sanitization_removes_unlisted_sensitive_fields(self):
        data = json.loads((FIXTURE / "capture.json").read_text(encoding="utf-8"))
        secret = "SYNTHETIC-SECRET-DO-NOT-EMIT"
        data["cookie"] = secret
        data["book"]["token"] = secret
        data["annotations"]["data"][0]["image_path"] = "https://invalid.test/?Signature=" + secret
        data["source_metadata"]["data"]["auth"] = secret
        data["pages"][0]["mapping_evidence"]["localStorage"] = secret
        self.assertNotIn(secret, json.dumps(collector.sanitized_capture(data)))

    def test_optional_unvalidated_nested_value_cannot_leak_into_capture(self):
        data = json.loads((FIXTURE / "capture.json").read_text(encoding="utf-8"))
        secret = "SYNTHETIC-SECRET-NESTED-VALUE"
        data["annotations"]["data"][0]["content_type"] = {"token": secret}
        # The source parser intentionally ignores this optional platform field.
        parse_capture(data, FIXTURE, now=data["observed_at"])
        try:
            safe = collector.sanitized_capture(data)
        except BrowserSafetyError:
            return  # Rejecting the malformed capture before writing is safe too.
        self.assertNotIn(secret, json.dumps(safe))

    def test_failure_details_do_not_copy_unvalidated_book_rows(self):
        secret = "SYNTHETIC-SECRET-NESTED-VALUE"
        data = {"code": 0, "data": {"books": [
            {"id": BOOK_ID, "title": {"token": secret}},
            {"id": BOOK_ID, "title": "SYNTHETIC conflict"}]}}
        with self.assertRaises(BrowserSafetyError) as error:
            collector._book(data)
        self.assertNotIn(secret, json.dumps(getattr(error.exception, "safe_details", None)))

    def test_fault_after_session_entry_closes_and_keeps_release_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "failure package"
            session = MagicMock()
            session.__enter__.return_value = session
            session.audit = NetworkAudit()
            session.report.return_value = {"context_closed": True, "lease": {"acquired": True, "released": True}}
            with patch.object(collector, "HeadlessSession", return_value=session), \
                    patch.object(collector, "_current", side_effect=BrowserSafetyError("TIMEOUT", "fetch")):
                with self.assertRaises(BrowserSafetyError) as error:
                    collector.collect_live(output, "unused-synthetic-login-root")
            self.assertEqual(error.exception.code, "TIMEOUT")
            session.__exit__.assert_called_once()
            failure = json.loads((output / "evidence/failure.json").read_text(encoding="utf-8"))
            release = json.loads((output / "evidence/session-release.json").read_text(encoding="utf-8"))
            self.assertEqual(failure["operation"], "read_current_state")
            self.assertTrue(release["lease"]["released"])
            self.assertFalse((output / "capture.json").exists())

    def test_profile_conflict_keeps_safe_evidence_without_entering_browser(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "conflict package"
            session = MagicMock()
            session.__enter__.side_effect = BrowserSafetyError("PROFILE_IN_USE", "acquire")
            session.audit = NetworkAudit()
            session.report.return_value = {"context_closed": False, "lease": {"acquired": False, "released": False}}
            with patch.object(collector, "HeadlessSession", return_value=session):
                with self.assertRaises(BrowserSafetyError) as error:
                    collector.collect_live(output, "unused-synthetic-login-root")
            self.assertEqual(error.exception.code, "PROFILE_IN_USE")
            session.__exit__.assert_not_called()
            self.assertTrue((output / "evidence/session-release.json").exists())

    def test_failed_api_context_original_get_still_has_an_audit_attempt(self):
        session = SimpleNamespace(policy=RequestPolicy(), audit=NetworkAudit(), context=MagicMock())
        session.context.request.get.side_effect = RuntimeError("SYNTHETIC-SECRET-TRANSPORT")
        url = "https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com/upload_images/46007447/46007447_page_13.jpg?Signature=SYNTHETIC-SECRET"
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(BrowserSafetyError) as error:
            collector._original(session, url, Path(folder) / "unused.jpg")
        self.assertEqual(error.exception.code, "RESOURCE_FAILED")
        self.assertTrue(any(row["category"] == "ORIGINAL_IMAGE" and row["method"] == "GET"
                            for row in session.audit.records))
        self.assertNotIn("SECRET", json.dumps(session.audit.records))


@unittest.skipUnless(NODE, "Optional local Node runtime is unavailable")
class FetchDeadlineReviewTests(unittest.TestCase):
    def test_actual_page_function_aborts_a_never_resolving_fetch(self):
        class FakeJavaScriptPage:
            def evaluate(self, script, argument):
                harness = """
global.location = {origin:'https://www.usense.com'};
global.localStorage = {getItem: () => JSON.stringify({access_token:'synthetic-token'})};
global.fetch = (path, options) => new Promise((resolve, reject) => {
  if (options.signal) options.signal.addEventListener('abort', () => {
    const error = new Error('synthetic abort'); error.name = 'AbortError'; reject(error);
  }, {once:true});
});
const fallback = setTimeout(() => {process.stdout.write(JSON.stringify({unsettled:true})); process.exit(0);}, 600);
(SCRIPT)(ARGUMENT).then(value => {
  clearTimeout(fallback); process.stdout.write(JSON.stringify(value));
}).catch(() => {clearTimeout(fallback); process.stdout.write(JSON.stringify({unhandled:true}));});
""".replace("SCRIPT", script).replace("ARGUMENT", json.dumps(argument))
                result = subprocess.run([NODE, "-"], input=harness, text=True, capture_output=True, timeout=3)
                if result.returncode != 0:
                    raise AssertionError("Synthetic JavaScript harness failed")
                return json.loads(result.stdout)
        session = SimpleNamespace(policy=RequestPolicy(), audit=NetworkAudit(),
                                  page=FakeJavaScriptPage(), timeout_ms=30)
        with self.assertRaises(BrowserSafetyError) as error:
            collector.get_business(session, "/qieti/api/annotate_ocr/directory/get?file_id=" + BOOK_ID)
        self.assertEqual(error.exception.code, "TIMEOUT")


class CLIReviewTests(unittest.TestCase):
    def test_offline_entry_builds_public_bundle_without_collecting_live(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "portable output with spaces"
            capture = json.loads((FIXTURE / "capture.json").read_text(encoding="utf-8"))
            stream = io.StringIO()
            with patch.object(cli, "collect_live", side_effect=AssertionError("live collection forbidden")) as live, redirect_stdout(stream):
                result = cli.main(["offline", "--input", str(FIXTURE), "--output", str(output),
                                   "--as-of", capture["observed_at"]])
            self.assertEqual(result, 0, stream.getvalue())
            live.assert_not_called()
            self.assertTrue((output / "bundle.json").is_file())
            entry = json.loads((output / "evidence/entry-result.json").read_text(encoding="utf-8"))
            self.assertFalse(entry["network_used"])
            self.assertEqual(entry["acceptance"], "NOT_ASSERTED")


if __name__ == "__main__":
    unittest.main()
