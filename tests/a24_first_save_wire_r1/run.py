"""New suite only. Exclusive result files preserve every attempt and traceback."""
import argparse
import asyncio
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
import unittest
import urllib.request
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))


def forbidden(*args, **kwargs):
    raise AssertionError("A24_TEST_REAL_IO_FORBIDDEN")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--test")
    args = parser.parse_args()
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit("Refusing to overwrite a previous test attempt")
    output = io.StringIO()
    started = time.monotonic()
    from noio_loop import MemoryPolicy
    asyncio.set_event_loop_policy(MemoryPolicy())
    with patch.object(socket, "create_connection", forbidden), patch.object(socket.socket, "connect", forbidden), \
         patch.object(subprocess, "Popen", forbidden), patch.object(urllib.request, "urlopen", forbidden):
        try:
            suite = (unittest.defaultTestLoader.loadTestsFromName(args.test) if args.test else
                     unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern="test_r1.py"))
            result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
        except BaseException:
            with path.open("xb") as handle:
                handle.write((json.dumps({"schema": "A24R1FocusedWireHelperFailure/v1", "passed": False,
                    "raw_output": output.getvalue() + traceback.format_exc(), "old_suites_run": 0}, indent=2) + "\n").encode("utf-8"))
            raise
    report = {"schema": "A24R1FocusedWireTestAttempt/v1", "mode": "SYNTHETIC_ONLY", "tests": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors), "duration_ms": round((time.monotonic()-started)*1000),
              "raw_output": output.getvalue(), "real_resources": 0, "old_suites_run": 0,
              "passed": result.wasSuccessful()}
    with path.open("xb") as handle:
        handle.write((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({k: v for k, v in report.items() if k != "raw_output"}))
    if not result.wasSuccessful():
        # Full original output is preserved in the exclusive report, not truncated stdout.
        print(output.getvalue()[-6500:])
        raise SystemExit(1)
