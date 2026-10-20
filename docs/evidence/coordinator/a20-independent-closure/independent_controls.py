"""Five independent A20 controls; fixed fake fixture, no product subprocess."""
import asyncio
import copy
import importlib.util
import json
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location('a20_fixed_fake_fixture',
    ROOT / 'tests/a20_authenticated_source/test_authenticated_source.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
p, gate, auth = f.p, f.gate, f.auth
RECORDS = []


class IndependentControls(unittest.IsolatedAsyncioTestCase):
    async def test_C01_both_orders_then_concurrent_duplicate_POSTs_stop(self):
        for native_first in (True, False):
            g = f.guard()
            f.arm(g)
            first = f.route(f.request(g))
            if native_first:
                await g.paused(f.event())
                await g.route(first)
            else:
                await g.route(first)
                await g.paused(f.event())
            second = f.route(f.request(g))
            await asyncio.gather(g.paused(f.event(requestId='SECOND_FAKE_POST',
                networkId='SECOND_FAKE_NETWORK')), g.route(second))
            continued = [v.args[0] for v in g.session.send.await_args_list].count('Fetch.continueRequest')
            self.assertEqual(continued, 1)
            first.continue_.assert_awaited_once()
            second.continue_.assert_not_awaited()
            self.assertEqual(g.auth.login_counts, {'native': 1, 'context': 1})
            self.assertTrue(g.stopped)
            RECORDS.append({'case': 'C01', 'native_first': native_first,
                'native_continues': continued, 'reservations': g.auth.login_counts,
                'first_error': g.failure, 'second_context_continues': 0})

    async def test_C02_prior_phase_session_response_never_admits_viewer(self):
        g = f.guard()
        url = gate.ORIGIN + '/qieti/api/user_login/profile'
        req = f.request(g, method='GET', url=url)
        await g.route(f.route(req))
        await g.paused(f.event(method='GET', url=url))
        g.auth.arm_navigation(gate.LOGIN)
        for layer in ('native', 'context'):
            g.auth.reserve_navigation(layer, gate.LOGIN)
        g.auth.reused = True
        g.auth.arm_navigation(gate.TARGET)
        body = AsyncMock(return_value=f.encoded({'code': 0,
            'data': {'id': 7, 'username': f.SECRET}}))
        await g.capture(NS(url=url, request=req, status=200, body=body))
        body.assert_not_awaited()
        self.assertEqual(g.failure['codes'], ['SESSION_RESPONSE_ASSOCIATION_UNPROVEN'])
        self.assertFalse(g.auth.session_receipts)
        self.assertFalse(g.auth.authenticated)
        RECORDS.append({'case': 'C02', 'late_phase': 'LOGIN_TO_VIEWER',
            'body_reads': 0, 'viewer_authenticated': False, 'first_error': g.failure})

    async def test_C03_origin_changes_after_username_fill_stop_before_password(self):
        page = f.LoginPage()
        original = page.locator
        def locator(selector):
            value = original(selector)
            if selector == auth.USER:
                fill = value.fill
                async def changed(text):
                    await fill(text)
                    page.url = 'https://different.invalid/qieti/login'
                value.fill = changed
            return value
        page.locator = locator
        with patch.object(p, 'read_credentials', return_value=f.CREDS) as read, \
                patch.object(p, 'save_new') as save:
            with self.assertRaisesRegex(gate.Stop, 'LOGIN_ORIGINAL_FRAME_UNPROVEN'):
                await p.authenticate(page, page.g, {'steps': {}})
        read.assert_called_once()
        save.assert_not_called()
        self.assertEqual(page.fills, [auth.USER])
        self.assertEqual(page.clicks, 0)
        self.assertFalse(page.g.auth.intent)
        RECORDS.append({'case': 'C03', 'fake_reads': 1, 'password_fills': 0,
            'submit_clicks': 0, 'intent': False})

    async def test_C04_expired_approval_refuses_before_private_file_read(self):
        a, d, r = f.authority()
        approval = f.validate(a, d, r)
        flow = auth.AuthFlow()
        flow.form_validated = True
        with patch.object(auth, 'context_options',
                lambda value: gate.context_options(value, now=f.NOW + timedelta(seconds=901))), \
                patch.object(Path, 'read_bytes', side_effect=AssertionError('NO_PRIVATE_READ')) as read:
            with self.assertRaisesRegex(gate.Stop, 'CONTEXT_APPROVAL_REJECTED'):
                auth.read_credentials(approval, flow, Path('FAKE_PROFILE'), lambda path: None)
        read.assert_not_called()
        RECORDS.append({'case': 'C04', 'private_reads': 0, 'expired_approval_rejected': True})

    async def test_C05_durable_intent_failure_prevents_click_and_redacts_exception(self):
        page = f.LoginPage()
        saved = {}
        async def opened(profile, approval, state):
            state['guard'] = page.g
            return page, page.g
        async def closed(state):
            state['release']['state'] = 'RELEASED'
        def save(path, value):
            name = Path(path).name
            if name == 'login-submit-intent.json':
                raise FileExistsError(f.SECRET)
            saved[name] = copy.deepcopy(value)
        with patch.object(p, 'open_owned', opened), patch.object(p.native, 'close_owned', closed), \
                patch.object(p, 'read_credentials', return_value=f.CREDS), patch.object(p, 'save_new', save):
            code = await p.observe_live('FAKE_PROFILE', None)
        result = saved['current-state.json']
        self.assertEqual(code, 2)
        self.assertEqual(page.clicks, 0)
        self.assertTrue(page.g.auth.intent)
        self.assertEqual(result['login_submissions'], 0)
        self.assertEqual(result['steps']['navigation'], 'NOT_RUN')
        self.assertEqual(result['steps']['book'], 'NOT_RUN')
        self.assertTrue(result['guard_at_serialization']['terminal_stopped'])
        self.assertEqual(result['release']['state'], 'RELEASED')
        self.assertNotIn(f.SECRET, json.dumps(result))
        RECORDS.append({'case': 'C05', 'result': result, 'submit_clicks': 0,
            'fake_release_only': True})
