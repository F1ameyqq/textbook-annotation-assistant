"""New minimal original-condition regression; never runs a historical control entry."""
import asyncio
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
import urllib.request
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests/a24_first_save_wire_r1'))
tempfile.tempdir = str(OUT / 'temporary')
os.environ['TEMP'] = os.environ['TMP'] = tempfile.tempdir


def forbidden(*args, **kwargs):
    raise AssertionError('INDEPENDENT_REAL_RESOURCE_FORBIDDEN')


def audit(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system'):
        forbidden()


sys.addaudithook(audit)
from noio_loop import MemoryPolicy
asyncio.set_event_loop_policy(MemoryPolicy())
from test_r1 import authority_fixture
from annotation.runtime.live_pilot import owner
from annotation.quality.live_pilot import PilotError

records = []


class OriginalConditions(unittest.TestCase):
    def test_original_unknown_unreleased_null_schema_reopen_is_denied_before_capability(self):
        with tempfile.TemporaryDirectory(prefix='independent-gate-') as temp:
            root = Path(temp)
            unknown = {'schema': 'SYNTHETIC_UNKNOWN_AUTHOR', 'status': 'UNKNOWN',
                'frozen_author_inputs': {'release': {'released': False}, 'receipt': None}}
            error_code = None
            with patch.object(owner, 'WindowsBackend', side_effect=forbidden) as native:
                try:
                    authority_fixture(root, {}, None, unbound=True, author_release=unknown)
                except PilotError as error:
                    error_code = error.code
                native.assert_not_called()
            self.assertEqual(error_code, 'REOPEN_QUALIFIED_PREDECESSOR_REQUIRED')
            records.append({'case': 'original_unknown_unreleased_null_schema_reopen',
                'capability_returned': False, 'code': error_code, 'native_constructor_calls': 0,
                'profile_context_acquisitions': 0, 'business_GETs': 0, 'effects': 0})

    def test_direct_independent_acquisition_denied_before_current_page_io(self):
        with patch('annotation.delivery.live_pilot.usense.CurrentPageIO', side_effect=forbidden) as io_class:
            with self.assertRaises(PilotError) as captured:
                asyncio.run(owner.acquire_current_schema(SimpleNamespace(role='INDEPENDENT_REOPEN'), None, None, None, {}))
            io_class.assert_not_called()
        self.assertEqual(captured.exception.code, 'CURRENT_SCHEMA_ACQUISITION_AUTHOR_ONLY')
        records.append({'case': 'direct_independent_acquisition', 'code': captured.exception.code,
            'current_page_io_constructors': 0, 'business_GETs': 0, 'effects': 0})


stream = io.StringIO()
tick = time.monotonic()
with patch.object(socket, 'create_connection', forbidden), patch.object(socket.socket, 'connect', forbidden), \
     patch.object(subprocess, 'Popen', forbidden), patch.object(urllib.request, 'urlopen', forbidden):
    result = unittest.TextTestRunner(stream=stream, verbosity=2, failfast=True).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(OriginalConditions))
report = {'schema': 'A24MinimumGateIndependentControls/v1', 'mode': 'SYNTHETIC_ONLY',
    'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'duration_ms': round((time.monotonic() - tick) * 1000), 'passed': result.wasSuccessful(),
    'raw_output': stream.getvalue(), 'records': records, 'real_resources': 0,
    'historical_failed_control_entry_rerun': False, 'historical_failure_reclassified': False}
with (OUT / 'independent-control-result.json').open('xb') as handle:
    handle.write((json.dumps(report, indent=2) + '\n').encode())
print(json.dumps({k: v for k, v in report.items() if k != 'raw_output'}))
raise SystemExit(0 if result.wasSuccessful() else 1)
