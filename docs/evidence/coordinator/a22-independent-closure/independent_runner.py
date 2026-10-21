"""A22 designated independent delta; no product entry point or real resource."""
import asyncio
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import selectors
import socket
import subprocess
import sys
import time
import traceback
import unittest
import urllib.request
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
ATTEMPTS = []


def forbidden(*args, **kwargs):
    ATTEMPTS.append('FORBIDDEN_RESOURCE_CALL')
    raise AssertionError('A22_INDEPENDENT_REAL_RESOURCE_FORBIDDEN')


def audit(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system'):
        forbidden()
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = os.path.abspath(os.fsdecode(args[0])).replace('\\', '/').lower()
        if '/.local/' in path or '/a22-session-reuse/' in path:
            forbidden()
        flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            allowed = str(OUT).replace('\\', '/').lower() + '/'
            if not path.startswith(allowed):
                forbidden()


class MemorySelector(selectors.BaseSelector):
    def register(self, *args, **kwargs): forbidden()
    def unregister(self, *args, **kwargs): forbidden()
    def select(self, timeout=None):
        if timeout:
            time.sleep(min(timeout, 0.01))
        return []
    def get_map(self): return {}


class MemoryLoop(asyncio.SelectorEventLoop):
    def _make_self_pipe(self): self._ssock = self._csock = None
    def _close_self_pipe(self): pass
    def _write_to_self(self): pass


class MemoryPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self): return MemoryLoop(MemorySelector())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_group(module, name):
    folder = OUT / name
    folder.mkdir(exist_ok=False)
    result, fatal = None, None
    started = time.monotonic()
    with (folder / 'stdout.txt').open('x', encoding='utf-8', newline='\n') as stdout, \
            (folder / 'stderr.txt').open('x', encoding='utf-8', newline='\n') as stderr, \
            contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            runner = unittest.TextTestRunner(stream=stderr, verbosity=2, failfast=True)
            result = runner.run(unittest.defaultTestLoader.loadTestsFromModule(module))
        except BaseException:
            fatal = traceback.format_exc()
            stderr.write(fatal)
    summary = {'task': 'A22', 'group': name, 'mode': 'INDEPENDENT_OFFLINE_FAKE_ONLY',
        'tests_run': result.testsRun if result else 0,
        'failures': len(result.failures) if result else 0,
        'errors': len(result.errors) if result else 0,
        'success': bool(result and result.wasSuccessful() and fatal is None and not ATTEMPTS),
        'fatal': fatal, 'duration_ms': round((time.monotonic() - started) * 1000),
        'forbidden_resource_attempts': list(ATTEMPTS),
        'records': getattr(module, 'RECORDS', []),
        'old_suites_run': 0, 'real_product_children': 0, 'live_activated': False}
    (folder / 'result.json').write_bytes((json.dumps(summary, ensure_ascii=True, indent=2) + '\n').encode())
    print(json.dumps({k: v for k, v in summary.items() if k not in ('records', 'fatal')}))
    return summary['success']


sys.dont_write_bytecode = True
sys.addaudithook(audit)
asyncio.set_event_loop_policy(MemoryPolicy())
with patch.object(socket, 'create_connection', forbidden), \
        patch.object(socket.socket, 'connect', forbidden), \
        patch.object(socket.socket, 'connect_ex', forbidden), \
        patch.object(socket, 'getaddrinfo', forbidden), \
        patch.object(urllib.request, 'urlopen', forbidden), \
        patch.object(subprocess, 'Popen', forbidden):
    module = load('a22_independent_delta', ROOT / 'tests/a22_session_reuse/test_session_reuse.py')
    with patch.object(module.p, 'load_native', forbidden), \
            patch.object(module.p.native, 'load_native', forbidden), \
            patch.object(module.p.native, 'profile_binding', forbidden), \
            patch.object(module.p, 'occupancy', forbidden), \
            patch.object(module.p, 'open_owned', forbidden), \
            patch.object(module.p, 'supervise', forbidden):
        if not run_group(module, 'new-suite'):
            raise SystemExit(1)
        controls = load('a22_independent_controls', OUT / 'independent_controls.py')
        if not run_group(controls, 'controls'):
            raise SystemExit(1)
