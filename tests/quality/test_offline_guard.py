"""Prove the runner's barriers without making an actual connection or process."""
import importlib.util
from pathlib import Path
import socket
import subprocess
import sys
import unittest

PATH = Path(__file__).resolve().parents[2] / "tools/run_offline_ci.py"
SPEC = importlib.util.spec_from_file_location("offline_ci_guard_under_test", PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class OfflineGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runner.install_offline_guard()

    def test_dns_is_denied_before_resolution(self):
        with self.assertRaisesRegex(RuntimeError, "OFFLINE_CI_FORBIDDEN: socket.getaddrinfo"):
            socket.getaddrinfo("synthetic.invalid", 443)

    def test_even_loopback_connect_is_denied_before_send(self):
        with socket.socket() as sock:
            with self.assertRaisesRegex(RuntimeError, "OFFLINE_CI_FORBIDDEN: socket.connect"):
                sock.connect(("127.0.0.1", 9))

    def test_stdlib_socketpair_ipc_still_works_for_asyncio(self):
        left, right = socket.socketpair()
        try:
            left.send(b"synthetic local IPC")
            self.assertEqual(right.recv(64), b"synthetic local IPC")
        finally:
            left.close()
            right.close()

    def test_subprocess_launch_cannot_escape_network_guard(self):
        with self.assertRaisesRegex(RuntimeError, "OFFLINE_CI_FORBIDDEN: subprocess.Popen"):
            subprocess.run([sys.executable, "-c", "raise SystemExit(99)"], check=False)

    def test_browser_and_model_imports_are_denied(self):
        for name in ("playwright", "onnxruntime", "torch", "huggingface_hub"):
            with self.subTest(module=name), self.assertRaisesRegex(ImportError, "OFFLINE_CI_FORBIDDEN_IMPORT"):
                __import__(name)


if __name__ == "__main__":
    unittest.main()
