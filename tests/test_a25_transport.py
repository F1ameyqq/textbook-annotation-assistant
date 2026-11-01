"""Offline A25 transport/pin/failure tests. Every socket and browser is fake."""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import ssl
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from annotation.runtime.usense_live import core, transport
from annotation.runtime.usense_live.capture import capture
from annotation.runtime.usense_live.config import configure, capture_endpoints


class Socket:
    def __init__(self, header=b"HTTP/1.1 200 Connection established\r\n\r\n"):
        self.header = bytearray(header)
        self.sent = []
        self.closed = False
    def __enter__(self): return self
    def __exit__(self, *args): self.closed = True
    def settimeout(self, seconds):
        if not 0 < seconds <= 10: raise AssertionError("unbounded timeout")
    def sendall(self, raw): self.sent.append(raw)
    def recv(self, size):
        if size != 1: raise AssertionError("read beyond proxy header")
        return bytes([self.header.pop(0)]) if self.header else b""


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / "tests")
        self.root = Path(self.tmp.name)
        self.profile = self.root / "synthetic-profile"
        self.output = self.root / "runs"
        self.profile.mkdir(); self.output.mkdir()
        self.server = "http://127.0.0.1:7897"
        self.setting = {"mode": "USER_APPROVED_EXACT_CERT", "origin": core.ORIGIN,
            "leaf_der_sha256": core.APPROVED_CERT_DER, "spki_sha256_base64": core.APPROVED_SPKI,
            "approval_reference": "SYNTHETIC_ONLY_NOT_AUTHORITY"}

    def tearDown(self): self.tmp.cleanup()

    def binding(self, proxy=True):
        return SimpleNamespace(data={"transport": {"mode": "HTTP_CONNECT_PROXY" if proxy else "DIRECT",
            "proxy_server": self.server if proxy else None}, "tls": copy.deepcopy(self.setting)}, output=self.output)

    def secure(self, certificate=b"synthetic-der"):
        secure = Mock()
        secure.getpeercert.return_value = certificate
        context = Mock()
        context.wrap_socket.return_value.__enter__ = Mock(return_value=secure)
        context.wrap_socket.return_value.__exit__ = Mock(return_value=False)
        return context

    def positive_pin(self, binding):
        # Positive deterministic branch substitutes only the fixed test pin.
        # Production DER and SPKI constants are unchanged and separately tested.
        pin = hashlib.sha256(b"synthetic-der").hexdigest()
        binding.data["tls"]["leaf_der_sha256"] = pin
        return patch.object(transport, "APPROVED_CERT_DER", pin)

    def test_new_config_roundtrip_binds_proxy_without_any_probe(self):
        path = self.root / "config.json"
        with patch.object(transport.socket, "create_connection", side_effect=AssertionError("network forbidden")):
            result = configure(profile=self.profile, output_root=self.output, config_path=path,
                coordinator="coordinator", executor="executor", reviewer="reviewer", authorization_reference="SYNTHETIC_ONLY",
                orders=[18, 19, 20, 21, 22], pages=[12, 173], source=True, proxy_server=self.server,
                tls_approval_reference="SYNTHETIC_ONLY")
            bound = core.load_binding(path, result["sha256"])
        self.assertEqual(bound.data["schema"], "UsenseLiveReadConfig/v2")
        self.assertEqual(bound.data["transport"], {"mode": "HTTP_CONNECT_PROXY", "proxy_server": self.server})
        self.assertEqual(len(capture_endpoints(bound)), 40)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_credential_remote_pac_socks_and_fallback_proxy_values_rejected(self):
        for server in ("http://user:password@127.0.0.1:7897", "http://remote.invalid:7897", "socks5://127.0.0.1:7897",
                       "http://127.0.0.1:7897/path", "http://127.0.0.1:7897?x=1", "http://127.0.0.1:0",
                       "http://127.0.0.1:7897,direct://", "http://127.0.0.1:65536"):
            with self.subTest(server=server), self.assertRaises(core.BindingError):
                transport.validate_transport({"mode": "HTTP_CONNECT_PROXY", "proxy_server": server})
        for value in (None, {"mode": "SYSTEM", "proxy_server": None}, {"mode": "DIRECT", "proxy_server": self.server}):
            with self.subTest(value=value), self.assertRaises(core.BindingError):
                transport.validate_transport(value)

    def test_direct_probe_and_browser_explicitly_use_direct(self):
        binding, sock = self.binding(False), Socket()
        context = self.secure()
        with self.positive_pin(binding), patch.object(transport.socket, "create_connection", return_value=sock) as connect, \
                patch.object(transport.ssl, "SSLContext", return_value=context):
            args = transport.launch_arguments(binding)
        connect.assert_called_once_with(("www.usense.com", 443), timeout=10)
        self.assertEqual(sock.sent, [])
        self.assertEqual(args, ["--no-proxy-server", "--ignore-certificate-errors-spki-list=" + core.APPROVED_SPKI])
        self.assertTrue(sock.closed)

    def test_proxy_probe_uses_one_fixed_connect_and_same_browser_proxy(self):
        binding, sock = self.binding(), Socket()
        context = self.secure()
        with self.positive_pin(binding), patch.object(transport.socket, "create_connection", return_value=sock) as connect, \
                patch.object(transport.ssl, "SSLContext", return_value=context):
            args = core.tls_launch_arguments(binding)
        connect.assert_called_once_with(("127.0.0.1", 7897), timeout=10)
        self.assertEqual(sock.sent, [b"CONNECT www.usense.com:443 HTTP/1.1\r\nHost: www.usense.com:443\r\n\r\n"])
        self.assertEqual((self.output / "proxy-connect-request.raw").read_bytes(), sock.sent[0])
        self.assertEqual((self.output / "proxy-connect-response.raw").read_bytes(), b"HTTP/1.1 200 Connection established\r\n\r\n")
        context.wrap_socket.assert_called_once_with(sock, server_hostname="www.usense.com")
        self.assertEqual(args, ["--proxy-server=" + self.server, "--proxy-bypass-list=<-loopback>",
                               "--ignore-certificate-errors-spki-list=" + core.APPROVED_SPKI])
        self.assertEqual(json.loads((self.output / "tls-probe.json").read_bytes())["status"], "EXACT_LEAF_CONFIRMED")

    def test_proxy_auth_failure_never_tries_tls_or_direct(self):
        sock = Socket(b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n")
        with patch.object(transport.socket, "create_connection", return_value=sock) as connect, \
                patch.object(transport.ssl, "SSLContext") as context, \
                self.assertRaisesRegex(core.BindingError, "PROXY_CONNECT_NOT_200_NO_FALLBACK"):
            transport.launch_arguments(self.binding())
        connect.assert_called_once(); context.assert_not_called()
        self.assertTrue(sock.closed)
        self.assertNotIn(b"Authorization", sock.sent[0])
        self.assertEqual((self.output / "proxy-connect-response.raw").read_bytes(), b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n")
        error = json.loads((self.output / "tls-probe-error.json").read_bytes())
        self.assertEqual(error["phase"], "PROXY_CONNECT")

    def test_proxy_eof_is_once_only_and_original_error_is_retained(self):
        with patch.object(transport.socket, "create_connection", return_value=Socket(b"")) as connect, \
                self.assertRaisesRegex(core.BindingError, "PROXY_CONNECT_EOF"):
            transport.launch_arguments(self.binding())
        connect.assert_called_once()
        self.assertIn(b"PROXY_CONNECT_EOF", (self.output / "tls-probe-error.traceback.txt").read_bytes())
        self.assertFalse(json.loads((self.output / "tls-probe.json").read_bytes())["fallback_allowed"])

    def test_changed_leaf_is_rejected_before_browser_arguments(self):
        with patch.object(transport.socket, "create_connection", return_value=Socket()) as connect, \
                patch.object(transport.ssl, "SSLContext", return_value=self.secure(b"wrong-certificate")), \
                self.assertRaisesRegex(core.BindingError, "APPROVED_CERTIFICATE_CHANGED"):
            transport.launch_arguments(self.binding())
        connect.assert_called_once()
        self.assertEqual(json.loads((self.output / "tls-probe.json").read_bytes())["phase"], "LEAF_CERTIFICATE_CHECK")

    def test_handshake_eof_retains_phase_and_exact_original_exception(self):
        context = Mock()
        context.wrap_socket.side_effect = ssl.SSLEOFError("synthetic handshake EOF exact text")
        with patch.object(transport.socket, "create_connection", return_value=Socket()) as connect, \
                patch.object(transport.ssl, "SSLContext", return_value=context), self.assertRaises(ssl.SSLEOFError):
            transport.launch_arguments(self.binding())
        connect.assert_called_once()
        self.assertIn(b"synthetic handshake EOF exact text", (self.output / "tls-probe-error.traceback.txt").read_bytes())
        self.assertEqual(json.loads((self.output / "tls-probe.json").read_bytes())["phase"], "TLS_HANDSHAKE")

    def test_strict_tls_has_explicit_proxy_without_certificate_exception_or_probe(self):
        binding = self.binding()
        binding.data["tls"] = {"mode": "STRICT"}
        with patch.object(transport.socket, "create_connection") as connect:
            args = transport.launch_arguments(binding)
        connect.assert_not_called()
        self.assertEqual(args, ["--proxy-server=" + self.server, "--proxy-bypass-list=<-loopback>"])

    def test_unapproved_origin_or_spki_never_connects(self):
        for key, value in (("origin", "https://other.invalid"), ("spki_sha256_base64", "other-pin")):
            binding = self.binding(); binding.data["tls"][key] = value
            with patch.object(transport.socket, "create_connection") as connect, self.assertRaises(core.BindingError):
                transport.launch_arguments(binding)
            connect.assert_not_called()

    def test_pre_context_failure_reaches_summary_and_independent_release(self):
        path = self.root / "capture.json"
        result = configure(profile=self.profile, output_root=self.output, config_path=path,
            coordinator="coordinator", executor="executor", reviewer="reviewer", authorization_reference="SYNTHETIC_ONLY",
            orders=[18], pages=[12, 173], source=True, proxy_server=self.server, tls_approval_reference="SYNTHETIC_ONLY")
        bound = core.load_binding(path, result["sha256"])
        factory = Mock(side_effect=AssertionError("browser/runtime forbidden"))
        with patch.dict(sys.modules, {"playwright.async_api": SimpleNamespace(async_playwright=factory)}), \
                patch.object(core, "tls_launch_arguments", side_effect=ssl.SSLEOFError("synthetic pre-enter EOF")):
            captured = asyncio.run(capture(path, result["sha256"]))
        factory.assert_not_called()
        self.assertEqual(captured["status"], "CAPTURE_FAILED_NO_RETRY")
        self.assertEqual(captured["captures"], {})
        self.assertTrue(captured["release"]["context_runtime_release_confirmed"])
        self.assertFalse(captured["release"]["context_created"])
        self.assertFalse(captured["release"]["runtime_started"])
        self.assertEqual(captured["error"]["phase"], "TLS_PREFLIGHT")
        self.assertEqual(json.loads((bound.output / "capture-summary.json").read_bytes()), captured)
        self.assertIn(b"synthetic pre-enter EOF", (bound.output / "startup-error.traceback.txt").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
