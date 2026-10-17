"""Binding retry behavior without opening a socket or starting a server."""
import errno
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from annotation.recognition import content_review_server


class ReviewServerBindingTests(unittest.TestCase):
    def test_automatic_port_survives_sixty_excluded_allocations(self):
        failures = [PermissionError(errno.EACCES, "excluded automatic port")
                    for _ in range(60)]
        expected = SimpleNamespace(server_address=("127.0.0.1", 60019))
        with patch.object(content_review_server, "ThreadingHTTPServer",
                          side_effect=[*failures, expected]) as factory:
            actual = content_review_server.make_server(object())

        self.assertIs(actual, expected)
        self.assertEqual(factory.call_count, 61)
        for call in factory.call_args_list:
            self.assertEqual(call.args[0], ("127.0.0.1", 0))
            self.assertTrue(issubclass(call.args[1], BaseHTTPRequestHandler))
        self.assertTrue(actual.daemon_threads)
        self.assertTrue(actual.review_token)
        self.assertEqual(dict(actual.request_counts), {})

    def test_automatic_port_exhaustion_is_bounded_at_128_attempts(self):
        failures = [PermissionError(errno.EACCES, "excluded allocation " + str(i))
                    for i in range(128)]
        with patch.object(content_review_server, "ThreadingHTTPServer",
                          side_effect=failures) as factory:
            with self.assertRaises(PermissionError) as raised:
                content_review_server.make_server(object())

        self.assertEqual(factory.call_count, 128)
        self.assertIs(raised.exception, failures[-1])
        self.assertTrue(all(call.args[0] == ("127.0.0.1", 0)
                            for call in factory.call_args_list))

    def test_explicit_port_permission_failure_is_not_retried(self):
        failure = PermissionError(errno.EACCES, "explicit port unavailable")
        with patch.object(content_review_server, "ThreadingHTTPServer",
                          side_effect=failure) as factory:
            with self.assertRaises(PermissionError) as raised:
                content_review_server.make_server(object(), port=60020)

        self.assertIs(raised.exception, failure)
        factory.assert_called_once()
        self.assertEqual(factory.call_args.args[0], ("127.0.0.1", 60020))

    def test_automatic_port_non_eacces_errors_are_not_retried(self):
        failures = [PermissionError(errno.EPERM, "not an excluded-port failure"),
                    OSError(errno.EADDRINUSE, "address already in use")]
        for failure in failures:
            with self.subTest(errno=failure.errno):
                with patch.object(content_review_server, "ThreadingHTTPServer",
                                  side_effect=failure) as factory:
                    with self.assertRaises(OSError) as raised:
                        content_review_server.make_server(object())
                self.assertIs(raised.exception, failure)
                factory.assert_called_once()


if __name__ == "__main__":
    unittest.main()
