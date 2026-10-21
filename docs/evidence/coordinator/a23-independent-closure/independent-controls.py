"""Finite A23 independent controls; only frozen fake transports and memory."""
import ast
import asyncio
import copy
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

ROOT = Path('D:/1800-worktrees/a23-independent-fixed')
sys.path.insert(0, str(ROOT / 'tests/a23_session_completion'))
import fixtures as f
from fixtures import p, gate, auth

RECORDS = []
EVIDENCE = ROOT / 'docs/evidence/A23/session-completion'
PROFILE = gate.ORIGIN + p.ACTIVE_PROFILE_PATH


class IndependentControls(IsolatedAsyncioTestCase):
    async def test_01_full_typed_scope_templates_and_unchanged_regions(self):
        candidate_raw = (EVIDENCE / 'candidate-manifest.json').read_bytes()
        digest = hashlib.sha256(candidate_raw).hexdigest()
        self.assertEqual(digest, '18921b3335809c0c0722dc1bf8bf1495d8628bab780ce95045079c82c1f615ad')
        expected = gate.scope_binding(digest)
        self.assertEqual(len(expected), 53)
        documents = ['candidate-manifest.json', 'activation-template-NONEXECUTABLE.json',
                     'decision-template-NONEXECUTABLE.json', 'independent-report-template-NONEXECUTABLE.json']
        for name in documents:
            document = json.loads((EVIDENCE / name).read_bytes())
            for key, value in expected.items():
                self.assertTrue(gate.same_typed(document.get(key), value), (name, key))
        activation, decision, report = f.authority()
        f.validate(activation, decision, report)
        rejected = []
        for key in gate.scope_binding('a' * 64):
            changed = copy.deepcopy(report)
            changed[key] = None
            with self.assertRaises(gate.Stop):
                f.validate(activation, decision, changed)
            rejected.append(key)
        source = (ROOT / 'tools/a16_current_state_probe.py').read_bytes().decode('utf-8')
        regions = {node.name: ast.get_source_segment(source, node).encode('utf-8')
                   for node in ast.parse(source).body
                   if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))}
        unchanged = json.loads((EVIDENCE / 'unchanged-regions.json').read_bytes())
        for entry in unchanged['probe_exact_regions']:
            self.assertEqual(hashlib.sha256(regions[entry['name']]).hexdigest(), entry['sha256'])
        RECORDS.append({'case': '53_typed_scope_and_template_closure', 'scope_fields': list(expected),
                        'documents_checked': documents, 'report_mutations_rejected': rejected,
                        'unchanged_region_hashes_verified': len(unchanged['probe_exact_regions']),
                        'base_comparison_basis': 'Coordinator fixed raw preflight and frozen preservation evidence; no Git or old suite run'})

    async def test_02_cross_barrier_interleaving_never_sends_twice(self):
        observations = []
        for suspended_layer in ('native', 'context'):
            guard = await f.installed()
            guard.auth = f.armed()
            guard.auth.arm_active_profile()
            first = f.route(f.request(guard, PROFILE))
            second = f.route(f.request(guard, PROFILE))
            entered, release = asyncio.Event(), asyncio.Event()
            methods = []

            async def send(method, params=None):
                methods.append(method)
                if method == 'Fetch.continueRequest' and suspended_layer == 'native':
                    entered.set()
                    await release.wait()
                return {}

            guard.session.send = AsyncMock(side_effect=send)
            if suspended_layer == 'native':
                await guard.route(first)
                in_flight = asyncio.create_task(guard.paused(f.event(guard, PROFILE, network='FIRST')))
            else:
                await guard.paused(f.event(guard, PROFILE, network='FIRST'))

                async def context_continue():
                    entered.set()
                    await release.wait()

                first.continue_ = AsyncMock(side_effect=context_continue)
                in_flight = asyncio.create_task(guard.route(first))
            try:
                await asyncio.wait_for(entered.wait(), timeout=1)
                await asyncio.gather(guard.route(second),
                                     guard.paused(f.event(guard, PROFILE, network='SECOND')))
            finally:
                release.set()
                await in_flight
            self.assertTrue(guard.stopped)
            self.assertEqual(methods.count('Fetch.continueRequest'), 1)
            first.continue_.assert_awaited_once()
            second.continue_.assert_not_awaited()
            self.assertEqual(len(guard.auth.session_seen['native']), 1)
            self.assertEqual(len(guard.auth.session_seen['context']), 1)
            with self.assertRaises(gate.Stop):
                guard.auth.arm_active_profile()
            observations.append({'suspended_layer': suspended_layer, 'native_fake_continues': 1,
                                 'context_fake_continues': 1, 'second_request_continues': 0,
                                 'guard_failure': guard.failure, 'active_intents': guard.auth.active_profile_intents})
        RECORDS.append({'case': 'cross_barrier_interleaving', 'observations': observations})

    async def test_03_delayed_failed_body_preserves_first_cause_and_no_replacement(self):
        guard = await f.installed()
        page = f.FakePage(guard)
        page.url = gate.TARGET
        guard.auth = f.armed()
        url = gate.ORIGIN + '/qieti/api/user_login/config/teams'
        request = f.request(guard, url)
        await guard.route(f.route(request))
        await guard.paused(f.event(guard, url, network='BODY_PENDING'))
        guard.native_response({'requestId': 'BODY_PENDING', 'frameId': guard.main_frame_id,
                               'type': 'Fetch', 'response': {'status': 200}})
        secret = 'INDEPENDENT_SYNTHETIC_SECRET_DO_NOT_EXPORT'

        async def failed_body():
            await asyncio.sleep(.03)
            return f.encoded({'code': 401, 'data': {'username': secret, 'id': secret, 'token': secret}})

        page.evaluate = AsyncMock(side_effect=AssertionError('NO_FALLBACK_GET'))
        guard.response(NS(url=url, request=request, status=200, body=failed_body))
        with self.assertRaises(gate.Stop):
            await p.complete_current_session(page, guard)
        page.evaluate.assert_not_awaited()
        self.assertEqual(guard.auth.active_profile_intents, 0)
        self.assertFalse(guard.auth.session_responses)
        self.assertEqual(guard.failure['codes'], ['AUTH_BUSINESS_REJECTED'])
        self.assertNotIn(secret, json.dumps([guard.auth.snapshot(), guard.failure]))
        finite = auth.response_projection(f.encoded({'code': 0, 'data': {
            'id': secret, 'username': secret, 'access_token': secret, 'extra': secret}}), 200,
            session_route='profile')
        self.assertEqual(set(finite), {'http_status', 'business_decode', 'credential_return_present',
                                     'authenticated_profile_fields_present'})
        self.assertNotIn(secret, json.dumps(finite))
        RECORDS.append({'case': 'failed_body_and_finite_projection', 'failure': guard.failure,
                        'active_intents': 0, 'finite_projection': finite, 'secret_exported': False})

    async def test_04_single_deadline_spans_viewer_rechecks_without_refill(self):
        guard = await f.installed()
        page = f.FakePage(guard)
        page.url = gate.TARGET
        guard.auth = f.armed()
        request = f.request(guard, PROFILE)
        await guard.route(f.route(request))
        await guard.paused(f.event(guard, PROFILE, network='STILL_PENDING'))
        page.evaluate = AsyncMock(side_effect=AssertionError('NO_REPLACEMENT_GET'))
        observed = {'clock': 0, 'viewer_checks': 0}
        original_check = p.check_current_viewer

        async def delayed_checks(page_arg, guard_arg):
            await original_check(page_arg, guard_arg)
            observed['viewer_checks'] += 1
            observed['clock'] = 19 if observed['viewer_checks'] == 1 else 21

        with patch.object(p, 'check_current_viewer', delayed_checks):
            with self.assertRaisesRegex(gate.Stop, 'SESSION_COMPLETION_TIMEOUT'):
                await p.complete_current_session(page, guard, clock=lambda: observed['clock'])
        self.assertEqual(observed['viewer_checks'], 2)
        page.evaluate.assert_not_awaited()
        self.assertEqual(guard.auth.active_profile_intents, 0)
        self.assertFalse(guard.auth.authenticated)
        RECORDS.append({'case': 'one_20_second_deadline', 'synthetic_clock': observed,
                        'active_intents': 0, 'authenticated': False, 'timeout': 'SESSION_COMPLETION_TIMEOUT'})
