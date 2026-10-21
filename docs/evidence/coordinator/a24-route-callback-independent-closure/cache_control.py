"""One material callback-cache identity control, actual helper and fake route only."""
import asyncio
import inspect
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]


def forbidden(*args, **kwargs):
    raise AssertionError('INDEPENDENT_REAL_IO_FORBIDDEN')


def audit(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system'):
        forbidden()


sys.addaudithook(audit)
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests/a24_route_callback'))
sys.path.insert(0, str(ROOT / 'tests/a24_first_save_wire_r1'))
from noio_loop import MemoryPolicy
asyncio.set_event_loop_policy(MemoryPolicy())
from test_dispatch import DispatchTests, Route
from playwright._impl._impl_to_api_mapping import ImplToApiMapping
from playwright._impl._helper import RouteHandler

records = []


class CacheIdentity(unittest.TestCase):
    def test_paused_first_mapping_does_not_replace_route_handler(self):
        guard = DispatchTests().guard()
        mapping = ImplToApiMapping()
        paused_wrapper = mapping.wrap_handler(guard.paused)
        route_wrapper = mapping.wrap_handler(guard.route)
        self.assertIsNot(paused_wrapper, route_wrapper)
        self.assertIs(mapping.wrap_handler(guard.route), route_wrapper)
        self.assertIs(mapping.wrap_handler(guard.paused), paused_wrapper)
        self.assertEqual(guard.route.__name__, 'route')
        self.assertEqual(guard.paused.__name__, 'paused')
        self.assertEqual(list(inspect.signature(guard.route).parameters), ['route'])
        self.assertEqual(list(inspect.signature(guard.paused).parameters), ['event'])
        route = Route(guard, 'https://www.usense.com/synthetic-bootstrap')
        guard.expected_request = route.request
        handler = RouteHandler(None, '**/*', route_wrapper, False)
        async def dispatch():
            return await handler.handle(route)
        self.assertTrue(asyncio.run(dispatch()))
        self.assertEqual(route.actions, ['continue'])
        self.assertEqual(guard.seen, [{'same_request': True, 'tracking': True}])
        self.assertFalse(guard.callbacks)
        self.assertFalse(handler._active_invocations)
        records.append({'case': 'paused_mapped_before_route', 'cache_wrappers_distinct': True,
            'same_method_cache_reused': True, 'route_signature': ['route'], 'paused_signature': ['event'],
            'actual_RouteHandler_dispatch': 'PASS_FAKE_ROUTE', 'same_request_identity': True,
            'callback_and_active_invocations_settled': True, 'real_resources': 0})


stream = io.StringIO()
tick = time.monotonic()
with patch.object(socket, 'create_connection', forbidden), patch.object(socket.socket, 'connect', forbidden), \
     patch.object(subprocess, 'Popen', forbidden), patch.object(urllib.request, 'urlopen', forbidden):
    result = unittest.TextTestRunner(stream=stream, verbosity=2, failfast=True).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(CacheIdentity))
report = {'schema': 'A24IndependentCallbackCacheIdentity/v1', 'tests': result.testsRun,
    'failures': len(result.failures), 'errors': len(result.errors), 'passed': result.wasSuccessful(),
    'duration_ms': round((time.monotonic() - tick) * 1000), 'raw_output': stream.getvalue(),
    'records': records, 'real_resources': 0, 'old_suite_runs': 0}
with (OUT / 'cache-control-result.json').open('xb') as handle:
    handle.write((json.dumps(report, indent=2) + '\n').encode())
print(json.dumps({k: v for k, v in report.items() if k != 'raw_output'}))
raise SystemExit(0 if result.wasSuccessful() else 1)
