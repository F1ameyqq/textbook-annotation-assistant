"""Single material synthetic counterexample; never calls a platform transport."""
import contextlib
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import unittest
import urllib.request
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
tempfile.tempdir = str(OUT / 'temporary')
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests/a24_first_save_wire')]
RECORDS = []


def forbidden(*args, **kwargs):
    raise AssertionError('REAL_IO_FORBIDDEN_INDEPENDENT_CONTROL')


with patch.object(socket, 'create_connection', forbidden), patch.object(socket.socket, 'connect', forbidden), \
        patch.object(socket.socket, 'connect_ex', forbidden), patch.object(subprocess, 'Popen', forbidden), \
        patch.object(urllib.request, 'urlopen', forbidden):
    from fixture import fixture, FakeIO
    from annotation.delivery.live_pilot.usense import UsenseTransport
    from annotation.runtime.live_pilot.journal import Journal
    from annotation.runtime.live_pilot.runner import apply

    class UnprojectedReceipt(FakeIO):
        def request_once(self, method, path, *, params, payload, phase):
            response = super().request_once(method, path, params=params, payload=payload, phase=phase)
            if method == 'POST':
                body = json.loads(response['body'])
                body['unapproved_session_material'] = 'INDEPENDENT_SYNTHETIC_PRIVATE_RECEIPT_SENTINEL'
                response['body'] = json.dumps(body)
            return response

    class ReceiptPrivacy(unittest.TestCase):
        def test_unapproved_response_value_must_not_enter_durable_journal(self):
            with tempfile.TemporaryDirectory(prefix='independent-receipt-') as folder:
                root = Path(folder)
                with patch.object(Path, 'home', return_value=root / 'isolated-home'):
                    request, initial, fact, profile = fixture(root)
                    io = UnprojectedReceipt(initial, fact)
                    journal = Journal(root / 'journal', offline=True)
                    result = apply(request, root, journal, UsenseTransport(io))
                    state = result['questions'][fact['question_id']]['state']
                    self.assertEqual(state, 'APPLIED_SYNTHETIC_WIRE')
                    leaks = []
                    for file in sorted(journal.root.glob('*.json')):
                        raw = file.read_bytes()
                        if b'INDEPENDENT_SYNTHETIC_PRIVATE_RECEIPT_SENTINEL' in raw:
                            leaks.append(file.name)
                            with (OUT / ('counterexample-' + file.name)).open('xb') as stream:
                                stream.write(raw)
                    RECORDS.append({'case': 'unprojected_receipt_journal', 'effect_state': state,
                        'synthetic_commit_count': len([call for call in io.calls if call['method'] == 'POST']),
                        'leaked_journal_files': leaks, 'raw_synthetic_evidence_preserved': True,
                        'real_upload_save_calls': 0})
                    self.assertFalse(leaks, 'UNAPPROVED_RESPONSE_FIELD_WRITTEN_TO_JOURNAL')

    started = time.monotonic()
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2, failfast=True).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ReceiptPrivacy))
    report = {'schema': 'A24IndependentWireCounterexample/v1', 'mode': 'SYNTHETIC_ONLY',
        'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'passed': result.wasSuccessful(), 'duration_ms': round((time.monotonic() - started) * 1000),
        'raw_output': output.getvalue(), 'records': RECORDS, 'real_resources': 0,
        'further_controls': 'NOT_RUN_AFTER_FIRST_MATERIAL_CONTROL_FAILURE'}
    with (OUT / 'privacy-control-result.json').open('xb') as stream:
        stream.write((json.dumps(report, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({key: report[key] for key in ('tests', 'failures', 'errors', 'passed', 'duration_ms')}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
