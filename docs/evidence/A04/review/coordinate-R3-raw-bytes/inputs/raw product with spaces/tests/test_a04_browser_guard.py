"""Offline injected boundary checks; no network, browser, or login credentials."""
from datetime import datetime, timezone
import json
import unittest
from urllib.parse import urlencode

from annotation.runtime.browser.guard import (
    API_PREFIX, BrowserSafetyError, LOGIN_PATH, NetworkAudit, OSS_HOST, RequestPolicy,
)


ORIGIN = "https://www.usense.com"
API = ORIGIN + API_PREFIX
IMAGE = f"https://{OSS_HOST}/upload_images/46007447/46007447_page_13.jpg"


class RequestPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = RequestPolicy()

    def test_known_get_operations_and_target_pages(self):
        paths = {
            "claim_book/books?page=1&pageSize=10": "BOOK_LIST",
            "annotate_ocr/structured-upload/import-id/46007447": "SOURCE_METADATA",
            "annotate_ocr/directory/get?file_id=46007447": "DIRECTORY",
            "annotate_pic/pre_annotation_source/46007447?annotationType=mr_pre": "SOURCE_INDEX",
            "annotate_pic/get_manual_annotations_unified/46007447": "ANNOTATIONS",
            "verify_annotation/unified-ocr-task/summary?file_id=46007447": "OCR_SUMMARY",
            "user_login/profile": "SESSION_PROFILE",
            "user_login/config/permissions": "SESSION_PERMISSIONS",
            "user_login/config/teams": "SESSION_TEAMS",
        }
        for page in (14, 15, 173):
            paths[f"annotate_pic/pre_annotation/46007447?pageNum={page}&annotationType=mr_pre"] = "SOURCE_PAGE"
            paths[f"annotate_pic/pre_annotation/46007447?pageNum={page}&annotationType=none"] = "SOURCE_PAGE"
        paths["annotate_pic/pre_annotation_source/46007447?annotationType=none"] = "SOURCE_INDEX"
        for path, category in paths.items():
            with self.subTest(path=path):
                self.assertEqual((True, category), self.policy.decide("GET", API + path))

    def test_read_like_names_do_not_authorize_writes_or_unknown_get(self):
        paths = (
            "annotate_pic/save/46007447", "annotate_pic/delete/46007447",
            "annotate_pic/commit_unified_submit", "claim_book/submit-review/46007447",
            "claim_book/submit-delivery/46007447", "annotate_ocr/start/46007447",
            "verify_annotation/unified-ocr-task/start?file_id=46007447",
            "user_login/refresh-token", "user_login/anything",
            "annotate_pic/get_manual_annotations_unified_by_order_in_level/46007447/22",
            "get_image?file_id=46007447", "annotate_pic/save/image.png",
        )
        for path in paths:
            for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"):
                with self.subTest(path=path, method=method):
                    self.assertFalse(self.policy.decide(method, API + path)[0])

    def test_target_book_page_and_query_cannot_be_widened(self):
        paths = (
            "annotate_ocr/structured-upload/import-id/46006966",
            "annotate_ocr/directory/get?file_id=46006966",
            "annotate_ocr/directory/get?file_id=46007447&file_id=46006966",
            "annotate_ocr/directory/get?file_id=46007447&delete=true",
            "annotate_pic/pre_annotation/46007447?pageNum=1&annotationType=mr_pre",
            "annotate_pic/pre_annotation/46007447?pageNum=1&annotationType=none",
            "annotate_pic/pre_annotation/46007447?pageNum=16&annotationType=mr_pre",
            "annotate_pic/pre_annotation/46007447?pageNum=014&annotationType=mr_pre",
            "annotate_pic/pre_annotation/46007447?pageNum=14&annotationType=ocr",
            "annotate_pic/pre_annotation/46007447?pageNum=14&annotationType=mr_pre&all=true",
            "annotate_pic/pre_annotation_source/46007447?annotationType=mr_pre&book=46006966",
            "annotate_pic/pre_annotation_source/46007447?annotationType=ocr",
            "annotate_pic/pre_annotation_source/46007447?annotationType=none&ocr=true",
            "annotate_pic/pre_annotation/46006966?pageNum=14&annotationType=none",
            "annotate_pic/get_manual_annotations_unified/46007447?book=46006966",
            "claim_book/books?page=0&pageSize=10", "claim_book/books?page=1&pageSize=1000",
            "claim_book/books?page=1&pageSize=10&unknown=1",
            "user_login/profile?x=1",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(self.policy.decide("GET", API + path)[0])

    def test_login_requires_open_window_and_is_consumed_once(self):
        login = ORIGIN + LOGIN_PATH
        self.assertFalse(self.policy.decide("POST", login)[0])
        self.assertFalse(self.policy.login_attempted)
        self.policy.login_window = True
        self.assertEqual((True, "LOGIN"), self.policy.classify("POST", login))
        self.assertFalse(self.policy.login_attempted)
        self.assertEqual((True, "LOGIN"), self.policy.decide("POST", login))
        self.assertTrue(self.policy.login_attempted)
        self.assertEqual((True, "LOGIN"), self.policy.classify("POST", login))
        self.assertFalse(self.policy.decide("POST", login)[0])
        self.policy.login_window = False
        self.policy.login_window = True
        self.assertFalse(self.policy.decide("POST", login)[0])

    def test_book_list_known_read_filters_are_allowed_without_recording_values(self):
        values = {"page": "1", "pageSize": "100", "status_list": "标注中,已验重", "id": "46007447",
                  "title": "名校课堂八年级数学上册", "team_name": "synthetic team",
                  "username": "synthetic user", "role": "member", "is_admin": "false"}
        url = API + "claim_book/books?" + urlencode(values)
        self.assertEqual((True, "BOOK_LIST"), self.policy.decide("GET", url))
        self.assertFalse(self.policy.decide("POST", url)[0])
        values["id"] = ""
        values["status_list"] = ""
        self.assertEqual((True, "BOOK_LIST"), self.policy.decide("GET", API + "claim_book/books?" + urlencode(values)))
        audit = NetworkAudit()
        allowed, category = self.policy.decide("GET", url)
        audit.record("GET", category, allowed, 200)
        self.assertNotIn("synthetic", json.dumps(audit.records))
        self.assertNotIn("46007447", json.dumps(audit.records))

    def test_book_list_filter_widening_and_encoded_controls_are_blocked(self):
        cases = ({"id": "46006966"}, {"id": "46007447,46006966"}, {"title": "x" * 257},
                 {"username": "user\nsecret"}, {"team_name": "team\x00secret"},
                 {"title": "title\x85secret"}, {"status_list": "x" * 257},
                 {"pageSize": "101"}, {"pageSize": "0"}, {"page": "-1"},
                 {"page": "1" * 1000}, {"pageSize": "1" * 1000}, {"delete": "true"})
        for query in cases:
            with self.subTest(keys=list(query)):
                self.assertFalse(self.policy.decide("GET", API + "claim_book/books?" + urlencode(query))[0])
        self.assertFalse(self.policy.decide("GET", API + "claim_book/books?id=46007447&id=46006966")[0])
        self.assertFalse(self.policy.decide("GET", API + "user_login/profile?title=synthetic")[0])

    def test_login_path_aliases_and_query_are_blocked(self):
        self.policy.login_window = True
        for path in ("/qieti/api/login", LOGIN_PATH + "/", LOGIN_PATH + "?x=1"):
            self.assertFalse(self.policy.decide("POST", ORIGIN + path)[0])
        self.assertFalse(self.policy.decide("GET", ORIGIN + LOGIN_PATH)[0])
        self.assertFalse(self.policy.login_attempted)

    def test_navigation_and_static_origin_only(self):
        for path in ("/qieti/login", "/qieti/annotateUnified", "/qieti/assets/index-123.js",
                     "/assets/a.css", "/qieti/static/font.woff2", "/favicon.ico"):
            with self.subTest(path=path):
                self.assertTrue(self.policy.decide("GET", ORIGIN + path)[0])
                self.assertFalse(self.policy.decide("POST", ORIGIN + path)[0])
        for url in ("http://www.usense.com/qieti/login", "https://www.usense.com:444/qieti/login",
                    "https://www.usense.com.evil.test/qieti/login",
                    "https://user:secret@www.usense.com/qieti/login",
                    ORIGIN + "/qieti/assets/../api/save.js", ORIGIN + "/qieti/assets/%2e%2e/api/save.js",
                    ORIGIN + "/qieti/assets/a.js#x", ORIGIN + "/qieti//api/save.js",
                    ORIGIN + "/qieti/api/save.png", ORIGIN + "/save", ORIGIN + "/\nqieti/login"):
            with self.subTest(url=url):
                self.assertFalse(self.policy.decide("GET", url)[0])

    def test_images_require_explicit_registration_and_exact_signed_url(self):
        signed = IMAGE + "?Signature=secret&Expires=123"
        self.assertFalse(self.policy.decide("GET", signed)[0])
        self.policy.register_image(signed)
        self.assertEqual((True, "ORIGINAL_IMAGE"), self.policy.decide("GET", signed))
        self.assertFalse(self.policy.decide("GET", IMAGE)[0])
        self.assertFalse(self.policy.decide("POST", signed)[0])
        for index in (14, 172):
            url = IMAGE.replace("page_13", f"page_{index}")
            self.policy.register_image(url)
            self.assertTrue(self.policy.decide("GET", url)[0])

    def test_wrong_book_page_crop_or_host_image_is_rejected(self):
        images = (IMAGE.replace("46007447", "46006966"), IMAGE.replace("page_13", "page_15"),
                  IMAGE.replace("upload_images", "annotate_images"),
                  IMAGE.replace(OSS_HOST, "evil.test"), IMAGE.replace("https", "http"))
        for url in images:
            with self.subTest(url=url):
                with self.assertRaises(BrowserSafetyError) as error:
                    self.policy.register_image(url)
                self.assertEqual("INVALID_IMAGE_URL:policy", str(error.exception))
                self.assertNotIn(url, str(error.exception))

    def test_malformed_values_cannot_escape_exception_boundary(self):
        for method, url in ((None, IMAGE), ("SECRET_METHOD", IMAGE), ("GET", None),
                            ("GET", "https://www.usense.com:secret/qieti/login")):
            self.assertFalse(self.policy.decide(method, url)[0])


class AuditTests(unittest.TestCase):
    def test_audit_schema_redacts_even_bad_category_method_status(self):
        audit = NetworkAudit(clock=lambda: datetime(2026, 10, 16, tzinfo=timezone.utc))
        audit.record("GET", "SOURCE_PAGE", True, 200)
        audit.record("secret", "https://secret/?token=secret", False, "secret")
        audit.record(None, [], False, True)
        rows = audit.records
        self.assertEqual({"method", "category", "decision", "status", "time"}, set(rows[0]))
        self.assertEqual("UNKNOWN", rows[1]["method"])
        self.assertEqual("UNKNOWN", rows[1]["category"])
        self.assertIsNone(rows[1]["status"])
        self.assertNotIn("secret", json.dumps(rows))
        rows[0]["method"] = "modified"
        self.assertEqual("GET", audit.records[0]["method"])

    def test_safe_errors_accept_only_fixed_code_and_stage(self):
        self.assertEqual("INVALID_POLICY_INPUT:policy", str(BrowserSafetyError("secret", "secret")))
        self.assertEqual("SESSION_FAILED:open_viewer", str(BrowserSafetyError("SESSION_FAILED", "open_viewer")))
        self.assertEqual("INVALID_POLICY_INPUT:policy", str(BrowserSafetyError([], {})))


if __name__ == "__main__":
    unittest.main()
