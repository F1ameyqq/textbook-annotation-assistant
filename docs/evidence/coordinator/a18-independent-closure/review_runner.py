"""One A18 new-suite run and four finite independent controls; memory only."""
import asyncio
import contextlib
import copy
import importlib.util
import json
from pathlib import Path
import selectors
import socket
import subprocess
import time
import traceback
import unittest
import urllib.request
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, patch

ROOT = Path('D:/1800-worktrees/a18-independent-fixed')
OUT = Path(__file__).resolve().parent
START = time.monotonic()


def forbidden(*args, **kwargs):
    raise AssertionError('REAL_RESOURCE_FORBIDDEN_INDEPENDENT_A18')


class MemorySelector(selectors.BaseSelector):
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
spec = importlib.util.spec_from_file_location('fixed_a18_delta', ROOT / 'tests/a18_current_frontend/test_current_frontend.py')
module = importlib.util.module_from_spec(spec)
control_records = []


class IndependentGateControl(unittest.TestCase):
    def test_exact_candidate_template_and_report_semantic_bindings(self):
        p, gate = module.p, module.gate
        expected = 'c0f7ea30ee5a3484544524b5e8c609125113a474d901bd24fc600529509ae8e8'
        self.assertEqual(p.candidate(expected), expected)
        template = json.loads((ROOT / 'docs/evidence/A18/current-frontend/independent-report-template-NONEXECUTABLE.json').read_bytes())
        self.assertEqual({k: template[k] for k in gate.scope_binding(expected)}, gate.scope_binding(expected))
        a, d, r, _, profile, now, encode = module.activation_documents()
        binding = gate.scope_binding(expected)
        report = {**template, 'result': 'ACCEPTED_OFFLINE_ONLY', 'acceptance_basis': 'BOUNDED_READONLY_PREFLIGHT'}
        decision = {**binding, 'tls_mode': 'CONTEXT_EXCEPTION', 'live_authorized': True,
                    'certificate_exception_authorized': True}
        d, r = encode(decision), encode(report)
        a.update(gate.fixed_fields(expected, profile), user_decision_sha256=gate.sha(d),
                 independent_report_sha256=gate.sha(r))
        raw = encode(a)
        gate.validate_activation(raw, gate.sha(raw), expected, profile, d, r,
                                 explicit_live=True, exception=True, now=now)
        rejected = []
        for key, value in binding.items():
            bad = copy.deepcopy(report)
            bad[key] = ('OLD_A17' if isinstance(value, str) else value + 1 if type(value) is int else True)
            bad_raw = encode(bad)
            adjusted = {**a, 'independent_report_sha256': gate.sha(bad_raw)}
            activation_raw = encode(adjusted)
            with self.assertRaises(gate.Stop):
                gate.validate_activation(activation_raw, gate.sha(activation_raw), expected,
                    profile, d, bad_raw, explicit_live=True, exception=True, now=now)
            rejected.append(key)
        control_records.append({'control': 'C1', 'actual_candidate_verified': True,
            'template_binding_match': True, 'report_semantic_mutations_rejected': rejected,
            'activation_created': False})


class IndependentAsyncControls(unittest.IsolatedAsyncioTestCase):
    async def test_C2_native_denied_version_response_stops_without_body_capture(self):
        g = module.guard()
        first = module.event(url=module.VERSION, kind='Fetch')
        first.update(requestId='version-first', networkId='network-first')
        second = module.event(url=module.VERSION, kind='Fetch')
        second.update(requestId='version-repeat', networkId='network-repeat')
        await g.paused(first)
        await g.paused(second)
        self.assertEqual(g.version_checks_sent, 1)
        self.assertFalse(g.stopped)
        g.native_response({'requestId': 'network-repeat'})
        self.assertTrue(g.terminal_stopped)
        value = module.response(module.route(g, url=module.VERSION, kind='fetch').request)
        # Native response identity alone must already stop; no body extraction is needed.
        value.body.assert_not_awaited()
        control_records.append({'control': 'C2', 'native_send_reservations': g.version_checks_sent,
            'denials': [c.args[0] for c in g.session.send.await_args_list], 'failure': g.failure,
            'body_reads': 0})

    async def test_C3_version_fatal_during_close_survives_final_serialization(self):
        p, g, saved = module.p, module.guard(), {}
        first = module.event(url=module.VERSION, kind='Fetch')
        first.update(requestId='version-first', networkId='network-first')
        repeat = module.event(url=module.VERSION, kind='Fetch')
        repeat.update(requestId='version-repeat', networkId='network-repeat')
        await g.paused(first)
        await g.paused(repeat)
        async def opened(profile, approval, state):
            state['guard'] = g
            return g.page, g
        async def collected(page, actual, result):
            result['outcome'] = 'READONLY_REVIEW_WITH_GAPS'
        async def closed(state):
            g.native_response({'requestId': 'network-repeat'})
            state['release']['state'] = 'RELEASED'
        with patch.object(p, 'open_owned', opened), patch.object(p, 'collect', collected), \
                patch.object(p.native, 'close_owned', closed), \
                patch.object(p, 'save_new', lambda path, value: saved.update({path.name: copy.deepcopy(value)})):
            code = await p.observe_live(None, None)
        result = saved['current-state.json']
        self.assertEqual(code, 2)
        self.assertEqual(result['outcome'], 'ERROR')
        self.assertIn('EXCLUDED_REQUEST_RESPONSE_OBSERVED', result['error']['codes'])
        self.assertEqual(result['body_status'], 'UNKNOWN')
        self.assertEqual(result['schema_status'], 'UNKNOWN')
        self.assertFalse(result['production_ready'])
        self.assertFalse(result['write_eligible'])
        self.assertTrue(all(v == 'NOT_RUN' for v in result['steps'].values()))
        control_records.append({'control': 'C3', 'exit_code': code, 'result': result,
                                'transport': 'FAKE_ONLY', 'files_saved_by_product': 0})

    async def test_C4_install_frame_identity_and_changed_identity_stop(self):
        gate, p = module.gate, module.p
        outcomes = []
        for invalid in ({}, {'id': 'main', 'parentId': 'foreign'}):
            session = NS(send=AsyncMock(return_value={'frameTree': {'frame': invalid}}), on=lambda *a: None)
            context = NS(route_web_socket=AsyncMock(), route=AsyncMock(), new_cdp_session=AsyncMock(return_value=session))
            guard = p.CurrentGuard(context, NS(main_frame=object()), module.policy.ReadPolicy())
            with self.assertRaisesRegex(gate.Stop, 'NATIVE_MAIN_FRAME_IDENTITY_UNPROVEN'):
                await guard.install()
            self.assertEqual([c.args[0] for c in session.send.await_args_list], ['Page.getFrameTree'])
            outcomes.append({'frame': invalid, 'fetch_enabled': False})
        session = NS(send=AsyncMock(return_value={'frameTree': {'frame': {'id': 'main'}}}), on=lambda *a: None)
        context = NS(route_web_socket=AsyncMock(), route=AsyncMock(), new_cdp_session=AsyncMock(return_value=session))
        guard = p.CurrentGuard(context, NS(main_frame=object()), module.policy.ReadPolicy())
        await guard.install()
        guard.frame_navigated({'frame': {'id': 'replacement'}})
        self.assertTrue(guard.terminal_stopped)
        self.assertIn('NATIVE_MAIN_FRAME_IDENTITY_CHANGED', guard.failure['codes'])
        control_records.append({'control': 'C4', 'invalid_identities': outcomes,
            'replacement_failure': guard.failure, 'real_native_calls': 0})


def run_suite(suite, stream):
    runner = unittest.TextTestRunner(stream=stream, verbosity=2, failfast=True)
    result = runner.run(suite)
    return {'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
            'success': result.wasSuccessful(), 'skipped': len(result.skipped)}


summary = {'task': 'A18', 'mode': 'INDEPENDENT_OFFLINE_IN_MEMORY', 'suite': None,
           'controls': None, 'fatal': None, 'old_suites_run': 0,
           'real_browser_network_profile_native_occupancy_login_business_calls': 0,
           'product_child_processes': 0, 'live_activated': False}
with (OUT / 'stdout.txt').open('x', encoding='utf-8', newline='\n') as stdout, \
        (OUT / 'stderr.txt').open('x', encoding='utf-8', newline='\n') as stderr, \
        contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
    try:
        with patch.object(socket, 'create_connection', forbidden), \
                patch.object(socket.socket, 'connect', forbidden), patch.object(socket.socket, 'connect_ex', forbidden), \
                patch.object(urllib.request, 'urlopen', forbidden), patch.object(subprocess, 'Popen', forbidden):
            spec.loader.exec_module(module)
            with patch.object(module.p, 'load_native', forbidden), \
                    patch.object(module.p.native, 'load_native', forbidden), \
                    patch.object(module.p.native, 'profile_binding', forbidden), \
                    patch.object(module.p, 'occupancy', forbidden):
                start = time.monotonic()
                summary['suite'] = run_suite(unittest.defaultTestLoader.loadTestsFromModule(module), stderr)
                summary['suite']['duration_ms'] = round((time.monotonic() - start) * 1000)
                if summary['suite']['success']:
                    start = time.monotonic()
                    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(IndependentGateControl),
                                                unittest.defaultTestLoader.loadTestsFromTestCase(IndependentAsyncControls)])
                    summary['controls'] = run_suite(suite, stderr)
                    summary['controls']['duration_ms'] = round((time.monotonic() - start) * 1000)
                else:
                    summary['controls'] = {'status': 'NOT_RUN', 'reason': 'NEW_SUITE_FAILED'}
    except BaseException:
        summary['fatal'] = traceback.format_exc()
        stderr.write(summary['fatal'])
summary.update(duration_ms=round((time.monotonic()-START)*1000),
    suite_records=getattr(module, 'RECORDS', []), independent_records=control_records)
summary['success'] = bool(not summary['fatal'] and summary['suite'] and summary['suite']['success']
                          and summary['controls'] and summary['controls'].get('success'))
with (OUT / 'delta-result.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(summary, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('suite_records','independent_records','fatal')}))
raise SystemExit(0 if summary['success'] else 1)
