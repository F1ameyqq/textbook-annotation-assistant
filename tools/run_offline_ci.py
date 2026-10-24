"""Run public Usense unit tests with only the Python standard library.

Start with -I -S. The test interpreter denies network, browser/model imports and
process creation before importing tests. No install, self-spawn or model download.
This is a regression gate, never evidence of platform or business acceptance.
"""
from __future__ import annotations

import argparse
import importlib.abc
import json
from pathlib import Path
import socket
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUITES = {
    "content": ("tests", "test_usense_live*.py", 143),
    "runtime": ("tests/usense_live", "test_*.py", 51),
    "quality": ("tests/quality", "test_*.py", 28),
}
BLOCKED_IMPORTS = frozenset({
    "playwright", "rapidocr_onnxruntime", "rapid_latex_ocr", "onnxruntime",
    "torch", "paddle", "paddleocr", "transformers", "huggingface_hub",
})


def install_offline_guard():
    """Audit hooks survive socket mocks; fake modules in sys.modules still work."""
    socketpair_code = getattr(getattr(socket, "_fallback_socketpair", None), "__code__", None)

    def audit(event, args):
        # CPython on Windows implements its private socketpair with loopback
        # TCP. asyncio needs this self-pipe even when every browser is fake.
        # Permit only the captured stdlib function, never arbitrary loopback.
        if (event == "socket.connect" and socketpair_code is not None
                and sys._getframe(1).f_code is socketpair_code
                and args[1][0] in {"127.0.0.1", "::1"}):
            return
        if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo",
                     "socket.gethostbyname", "socket.gethostbyaddr", "socket.sendto",
                     "socket.sendmsg", "subprocess.Popen", "os.system",
                     "os.posix_spawn", "os.spawn", "os.exec", "os.fork",
                     "os.startfile", "os.startfile/2"}:
            raise RuntimeError("OFFLINE_CI_FORBIDDEN: " + event)

    class NoBrowserOrModel(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in BLOCKED_IMPORTS:
                raise ImportError("OFFLINE_CI_FORBIDDEN_IMPORT: " + fullname)
            return None

    sys.addaudithook(audit)
    sys.meta_path.insert(0, NoBrowserOrModel())


def run_suite(name):
    start, pattern, minimum = SUITES[name]
    suite = unittest.TestLoader().discover(str(ROOT / start), pattern=pattern)
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = (result.wasSuccessful() and count >= minimum and not result.skipped
              and not result.expectedFailures)
    record = {
        "suite": name, "status": "PASS" if passed else "FAIL",
        "tests_run": result.testsRun, "minimum_tests": minimum,
        "failures": [{"test": t.id(), "traceback": tb} for t, tb in result.failures],
        "errors": [{"test": t.id(), "traceback": tb} for t, tb in result.errors],
        "skipped": [{"test": t.id(), "reason": reason} for t, reason in result.skipped],
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
        "isolated_interpreter": bool(sys.flags.isolated),
        "site_disabled": bool(sys.flags.no_site),
    }
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["all", *SUITES], default="all")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if not (sys.flags.isolated and sys.flags.no_site):
        parser.error("start directly with: python -I -S tools/run_offline_ci.py")
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
    install_offline_guard()
    names = list(SUITES) if args.suite == "all" else [args.suite]
    records = [run_suite(name) for name in names]
    result = {
        "schema": "UsenseOfflineCI/v1", "python": sys.version.split()[0],
        "status": "PASS" if all(r["status"] == "PASS" for r in records) else "FAIL",
        "suites": records, "tests_run": sum(r["tests_run"] for r in records),
        "scope": "Public synthetic Usense tests only; full legacy suite is separate",
        "network_and_process_launch_denied": True,
        "network_exception": "CPython stdlib socketpair loopback IPC only (asyncio self-pipe)",
        "platform_acceptance_claimed": False, "remote_ci_run_claimed": False,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "suites"}), flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
