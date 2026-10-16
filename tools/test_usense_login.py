"""Offline checks for secret handling and login-origin validation."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import usense_login as login


class LoginConfigTests(unittest.TestCase):
    def config(self, raw):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "login.json"
        path.write_text(raw, encoding="utf-8")
        return path

    def test_unicode_bom_and_password_preserved_without_repr_leak(self):
        password = '  demo%$#\\"密  '
        path = self.config("\ufeff" + json.dumps({"username": "示例账号", "password": password}))
        creds = login.load_credentials(path)
        self.assertEqual(creds.password, password)
        self.assertNotIn(password, repr(creds))
        self.assertNotIn(creds.username, repr(creds))

    def test_malformed_json_does_not_echo_input(self):
        path = self.config('{"password": "PRIVATE_SENTINEL", BROKEN}')
        with self.assertRaises(login.LoginError) as caught:
            login.load_credentials(path)
        self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))

    def test_missing_empty_and_wrong_types_rejected(self):
        for data in ({}, [], {"username": 5, "password": "demo"},
                     {"username": "demo", "password": ""},
                     {"username": " ", "password": "demo"}):
            with self.subTest(data=data), self.assertRaises(login.LoginError):
                login.load_credentials(self.config(json.dumps(data)))

    def test_origin_guard(self):
        self.assertTrue(login.trusted_url(login.LOGIN_URL, login_only=True))
        for url in ("http://www.usense.com/qieti/login", "https://www.usense.com.evil.test/qieti/login",
                    "https://www.usense.com:444/qieti/login", "https://user@www.usense.com/qieti/login",
                    "https://www.usense.com/qieti/annotateUnified", "https://www.usense.com:bad/qieti/login"):
            with self.subTest(url=url):
                self.assertFalse(login.trusted_url(url, login_only=True))

    def test_check_never_starts_browser_or_echoes_values(self):
        output = io.StringIO()
        with patch.object(login, "load_credentials", return_value=login.Credentials("PRIVATE_USER", "PRIVATE_PASS")), \
             patch.object(login, "login") as browser, contextlib.redirect_stdout(output):
            self.assertEqual(login.main(["--check"]), 0)
        browser.assert_not_called()
        self.assertNotIn("PRIVATE_USER", output.getvalue())
        self.assertNotIn("PRIVATE_PASS", output.getvalue())

    def test_certificate_failure_is_reported_before_credentials(self):
        error = RuntimeError("net::ERR_CERT_COMMON_NAME_INVALID PRIVATE_SENTINEL")
        message = str(login.browser_failure(
            error, "open_viewer", credentials_started=False, submission_attempted=False))
        self.assertIn("证书域名", message)
        self.assertIn("尚未填写、尚未提交", message)
        self.assertNotIn("PRIVATE_SENTINEL", message)

    def test_submit_failure_does_not_claim_no_submission_or_echo_secret(self):
        error = RuntimeError("fill PRIVATE_SENTINEL net::ERR_CERT_COMMON_NAME_INVALID")
        message = str(login.browser_failure(
            error, "submit", credentials_started=True, submission_attempted=True))
        self.assertIn("提交结果需要核实", message)
        self.assertNotIn("尚未提交", message)
        self.assertNotIn("证书域名", message)
        self.assertNotIn("PRIVATE_SENTINEL", message)

    def test_certificate_override_is_explicit_and_not_default(self):
        credentials = login.Credentials("PRIVATE_USER", "PRIVATE_PASS")
        for arguments, expected in (([], False), (["--ignore-https-errors"], True)):
            with self.subTest(arguments=arguments), \
                 patch.object(login, "load_credentials", return_value=credentials), \
                 patch.object(login, "login", return_value="状态已确认") as browser, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(login.main(arguments), 0)
                browser.assert_called_once_with(
                    credentials, headed=False, ignore_https_errors=expected)


if __name__ == "__main__":
    unittest.main()
