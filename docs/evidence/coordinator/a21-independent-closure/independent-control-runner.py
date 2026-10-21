"""Append-only A21 delta runner; no old suite and no real transport permitted."""
import sys
import contextlib
import asyncio
import importlib.util
import json
from pathlib import Path
import socket
import selectors
import subprocess
import time
import traceback
import unittest
import urllib.request
from unittest.mock import patch

ROOT = Path('D:/1800-worktrees/a21-independent-fixed')
OUT = ROOT / 'docs/evidence/A21/independent-static-image-review/control-runs'
OUT.mkdir(parents=True, exist_ok=True)
number = 1
while (OUT / ('run%02d' % number)).exists():
    number += 1
folder = OUT / ('run%02d' % number)
folder.mkdir(exist_ok=False)
def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = str(args[0]).replace('\\', '/').lower()
        if path.endswith('/.local/usense-login.json') or '/.local/browser-profiles' in path:
            raise AssertionError('REAL_PRIVATE_PATH_FORBIDDEN_A21_OFFLINE')
sys.addaudithook(audit)
started = time.monotonic()
result, fatal, records = None, None, []
def forbidden(*args, **kwargs):
    raise AssertionError('REAL_RESOURCE_FORBIDDEN_A21_OFFLINE')


class MemorySelector(selectors.BaseSelector):
    """Timer/future scheduling only. No sockets, handles or I/O registrations."""
    def register(self, *args, **kwargs):
        forbidden()
    def unregister(self, *args, **kwargs):
        forbidden()
    def select(self, timeout=None):
        if timeout:
            time.sleep(min(timeout, 0.01))
        return []
    def get_map(self):
        return {}


class MemoryLoop(asyncio.SelectorEventLoop):
    def _make_self_pipe(self):
        self._ssock = self._csock = None
    def _close_self_pipe(self):
        pass
    def _write_to_self(self):
        pass


class MemoryPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):
        return MemoryLoop(MemorySelector())


asyncio.set_event_loop_policy(MemoryPolicy())
with (folder / 'stdout.txt').open('x', encoding='utf-8', newline='\n', buffering=1) as stdout, \
        (folder / 'stderr.txt').open('x', encoding='utf-8', newline='\n', buffering=1) as stderr, \
        contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
    try:
        spec = importlib.util.spec_from_file_location('a21_new_controls', ROOT / 'docs/evidence/A21/independent-static-image-review/independent-controls.py')
        module = importlib.util.module_from_spec(spec)
        with patch.object(socket, 'create_connection', forbidden), \
                patch.object(socket.socket, 'connect', forbidden), \
                patch.object(socket.socket, 'connect_ex', forbidden), \
                patch.object(urllib.request, 'urlopen', forbidden), patch.object(subprocess, 'Popen', forbidden):
            spec.loader.exec_module(module)
            with patch.object(module.p, 'load_native', forbidden), \
                    patch.object(module.p.native, 'load_native', forbidden), \
                    patch.object(module.p.native, 'profile_binding', forbidden), \
                    patch.object(module.p, 'occupancy', forbidden):
                runner = unittest.TextTestRunner(stream=stderr, verbosity=2, failfast=True)
                result = runner._makeResult()
                runner._makeResult = lambda: result
                runner.run(unittest.defaultTestLoader.loadTestsFromModule(module))
        records = module.RECORDS
    except BaseException:
        fatal = traceback.format_exc()
        stderr.write(fatal)
summary = {'task': 'A21', 'run': number, 'mode': 'OFFLINE_IN_MEMORY_FAKE_TRANSPORT',
    'tests_run': result.testsRun if result else 0, 'failures': len(result.failures) if result else 0,
    'errors': len(result.errors) if result else 0, 'success': bool(result and result.wasSuccessful() and not fatal),
    'fatal': fatal, 'duration_ms': round((time.monotonic() - started) * 1000),
    'browser_network_profile_native_occupancy_login_business_calls': 0, 'product_child_processes': 0,
    'old_suites_run': 0, 'live_activated': False, 'records': records}
(folder / 'result.json').write_bytes((json.dumps(summary, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
print(json.dumps({k: v for k, v in summary.items() if k not in ('records', 'fatal')}))
raise SystemExit(0 if summary['success'] else 1)
