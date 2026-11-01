import asyncio
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from annotation.runtime.usense_live import core as runtime


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.tmp.name)
        self.profile = self.root / "dedicated-test-browser"
        self.profile.mkdir()
        self.outputs = self.root / "runs"
        self.outputs.mkdir()
        now = datetime.now(timezone.utc)
        self.data = {"schema": runtime.SCHEMA, "book_id": "46007447", "operation": "READONLY_CAPTURE",
            "run_id": "usense-readonly-synthetic-test", "actors": {"coordinator": "test-coordinator",
                "executor": "test-executor", "reviewer": "test-reviewer"}, "target_url": runtime.TARGET,
            "profile": {"directory": str(self.profile), "fingerprint": runtime.profile_identity(str(self.profile))[1],
                        "usage": "DEDICATED_PROJECT"}, "output_root": str(self.outputs),
            "not_before": (now-timedelta(seconds=2)).isoformat(), "expires_at": (now+timedelta(minutes=5)).isoformat(),
            "headless": True, "allowed_get": [{"url": runtime.TARGET, "resource_types": ["document"], "max_requests": 1},
                {"url": runtime.ORIGIN + "/qieti/api/annotate_ocr/directory/get?file_id=46007447", "resource_types": ["fetch"], "max_requests": 1}],
            "static_get": {"mode": "SAME_ORIGIN_ASSETS", "max_requests": 8},
            "tls": {"mode": "STRICT"},
            "transport": {"mode": "DIRECT", "proxy_server": None},
            "implementation_sha256": runtime.implementation_digest(),
            "authorization_reference": "SYNTHETIC_TEST_ONLY_NOT_A_USER_AUTHORIZATION"}
        self.path = self.root / "config.json"

    def tearDown(self):
        self.tmp.cleanup()

    def binding(self, data=None):
        raw = runtime.canonical(data or self.data)
        self.path.write_bytes(raw)
        return runtime.load_binding(self.path, runtime.sha(raw))

    def test_frozen_draft_does_not_grant_write_or_create_run(self):
        self.path.write_bytes(runtime.canonical(self.data))
        result = runtime.freeze(self.path, self.root / "frozen.json")
        self.assertFalse(result["platform_ready"])
        self.assertFalse(result["save_authority_created"])
        self.assertEqual(list(self.outputs.iterdir()), [])

    def test_wrong_scope_and_actor_collision_rejected(self):
        for update in ({"book_id": "46007448"}, {"operation": "SAVE"},
                       {"actors": dict(self.data["actors"], reviewer="test-executor")}):
            with self.subTest(update=update), self.assertRaises(runtime.BindingError):
                self.binding(dict(self.data, **update))

    def test_expired_and_modified_config_rejected(self):
        binding = self.binding()
        with self.assertRaisesRegex(runtime.BindingError, "WINDOW_EXPIRED"):
            binding.check(now=datetime.now(timezone.utc)+timedelta(hours=1))
        self.path.write_bytes(self.path.read_bytes()+b" ")
        with self.assertRaisesRegex(runtime.BindingError, "CONFIG_CHANGED"):
            binding.check()

    def test_profile_lock_or_changed_fingerprint_rejected(self):
        binding = self.binding()
        (self.profile / "SingletonLock").write_bytes(b"")
        with self.assertRaisesRegex(runtime.BindingError, "PROFILE_LOCK_PRESENT"):
            binding.check(profile=True)
        (self.profile / "SingletonLock").unlink()
        data = copy.deepcopy(self.data)
        data["profile"]["fingerprint"] = "0"*64
        binding = self.binding(data)
        with self.assertRaisesRegex(runtime.BindingError, "PROFILE_IDENTITY_CHANGED"):
            binding.check(profile=True)

    def test_book_substring_and_token_query_are_rejected(self):
        for suffix in ("?file_id=460074470", "?file_id=46007447&token=secret"):
            data = copy.deepcopy(self.data)
            data["allowed_get"][1]["url"] = runtime.ORIGIN+"/qieti/api/annotate_ocr/directory/get"+suffix
            with self.subTest(suffix=suffix), self.assertRaises(runtime.BindingError):
                self.binding(data)

    def test_post_denied_on_both_layers_and_guard_stops(self):
        for layer in ("native", "context"):
            policy = runtime.ReadonlyPolicy(self.binding())
            url = self.data["allowed_get"][1]["url"]
            self.assertFalse(policy.decide(layer, "POST", url, "fetch"))
            self.assertFalse(policy.decide(layer, "GET", runtime.TARGET, "document"))

    def test_business_get_exact_and_one_per_layer(self):
        policy = runtime.ReadonlyPolicy(self.binding())
        url = self.data["allowed_get"][1]["url"]
        self.assertTrue(policy.decide("context", "GET", url, "fetch"))
        self.assertTrue(policy.decide("native", "GET", url, "Fetch"))
        self.assertFalse(policy.decide("context", "GET", url, "fetch"))

    def test_static_policy_cannot_allow_api_external_or_encoded_traversal(self):
        for url in (runtime.ORIGIN+"/assets/api/x.js", runtime.ORIGIN+"/assets/%2e%2e/api/x.js",
                    runtime.ORIGIN+"/assets/x.js?file_id=46007447", "https://evil.example/assets/x.js"):
            policy = runtime.ReadonlyPolicy(self.binding())
            self.assertFalse(policy.decide("context", "GET", url, "script"))
        policy = runtime.ReadonlyPolicy(self.binding())
        self.assertTrue(policy.decide("context", "GET", runtime.ORIGIN+"/qieti/assets/app-hash.js", "script"))

    def fake_playwright(self, *, fail_online=False):
        calls = []
        class Page:
            url = "about:blank"
            def on(self, *_):
                pass
        class CDP:
            def on(self, *_):
                pass
            async def send(self, name, payload):
                calls.append(name)
        class Context:
            pages = [Page()]
            def on(self, *_):
                pass
            async def route(self, *_):
                calls.append("context-route")
            async def route_web_socket(self, *_):
                calls.append("websocket-route")
            async def new_cdp_session(self, *_):
                return CDP()
            async def set_offline(self, offline):
                calls.append("online")
                if fail_online:
                    raise ValueError("simulated startup failure")
            async def close(self):
                calls.append("context-close")
        class Browser:
            async def launch_persistent_context(self, _, **options):
                self.options = options
                calls.append("launch-offline" if options["offline"] else "launch-online")
                return Context()
        class Runtime:
            chromium = Browser()
            async def stop(self):
                calls.append("runtime-stop")
        class API:
            async def start(self):
                return Runtime()
        return types.SimpleNamespace(async_playwright=API), calls

    def test_open_installs_two_guards_before_online_and_consumes_run(self):
        binding = self.binding()
        module, calls = self.fake_playwright()
        async def scenario():
            async with runtime.owned_readonly_context(binding) as owned:
                self.assertIn("Fetch.enable", calls)
                self.assertLess(calls.index("context-route"), calls.index("online"))
                self.assertLess(calls.index("Fetch.enable"), calls.index("online"))
            self.assertTrue(owned.release["context_runtime_release_confirmed"])
            self.assertEqual(owned.release["os_process_release"], "REQUIRES_OUTER_HOLDER")
            with self.assertRaises(FileExistsError):
                async with runtime.owned_readonly_context(binding):
                    pass
        with patch.dict("sys.modules", {"playwright.async_api": module}):
            asyncio.run(scenario())
        self.assertEqual(calls[-2:], ["context-close", "runtime-stop"])

    def test_partial_startup_releases_acquired_context_and_runtime(self):
        binding = self.binding()
        module, calls = self.fake_playwright(fail_online=True)
        async def scenario():
            with self.assertRaisesRegex(ValueError, "simulated"):
                async with runtime.owned_readonly_context(binding):
                    pass
        with patch.dict("sys.modules", {"playwright.async_api": module}):
            asyncio.run(scenario())
        self.assertEqual(calls[-2:], ["context-close", "runtime-stop"])
        self.assertTrue(json.loads((binding.output/"release.json").read_bytes())["context_runtime_release_confirmed"])

    def test_readonly_rejects_manual_login_configuration(self):
        data = copy.deepcopy(self.data)
        data["schema"] = "UsenseLiveManualLoginConfig/v1"
        with self.assertRaises(runtime.BindingError):
            self.binding(data)

    def test_manual_login_single_post_and_business_post_blocked(self):
        data = copy.deepcopy(self.data)
        data.update(schema="UsenseLiveManualLoginConfig/v1", operation="MANUAL_LOGIN_ONLY", run_id="usense-login-test",
                    target_url=runtime.LOGIN, headless=False)
        data["allowed_get"][0]["url"] = runtime.LOGIN
        raw = runtime.canonical(data)
        self.path.write_bytes(raw)
        binding = runtime.load_login_binding(self.path, runtime.sha(raw))
        policy = runtime.ManualLoginPolicy(binding)
        policy.login_armed = True
        self.assertTrue(policy.decide("native", "POST", runtime.LOGIN_POST, "XHR"))
        self.assertTrue(policy.decide("context", "POST", runtime.LOGIN_POST, "xhr"))
        self.assertFalse(policy.decide("context", "POST", runtime.LOGIN_POST, "xhr"))
        policy = runtime.ManualLoginPolicy(binding)
        policy.login_armed = True
        self.assertFalse(policy.decide("context", "POST", runtime.ORIGIN+"/qieti/api/annotate_ocr/save", "xhr"))

    def test_tls_exception_cannot_switch_certificate_or_origin(self):
        for value in ({"mode": "USER_APPROVED_EXACT_CERT", "origin": "https://evil.example",
                       "leaf_der_sha256": runtime.APPROVED_CERT_DER, "spki_sha256_base64": runtime.APPROVED_SPKI,
                       "approval_reference": "SYNTHETIC_TEST"}, {"mode": "IGNORE_ALL"}):
            with self.assertRaises(runtime.BindingError):
                self.binding(dict(self.data, tls=value))


if __name__ == "__main__":
    unittest.main()
