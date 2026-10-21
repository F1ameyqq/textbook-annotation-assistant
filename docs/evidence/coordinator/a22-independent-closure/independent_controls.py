"""Five finite controls chosen for the A22 change; all transport is fake."""
import ast
import asyncio
import copy
import hashlib
import json
import sys
from pathlib import Path
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

t = sys.modules['a22_independent_delta']
p, auth, gate, policy = t.p, t.auth, t.gate, t.policy
ROOT = Path(__file__).resolve().parents[4]
RECORDS = []


class FrozenBindings(TestCase):
    def test_01_exact_candidate_templates_profile_and_unchanged_region_digests(self):
        folder = ROOT / 'docs/evidence/A22/session-reuse'
        raw = (folder / 'candidate-manifest.json').read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(digest, '264e7fd8120efc8dd8f95f6c66b28693104d82f47e3d68e3a91fd0c422b38141')
        self.assertEqual(p.candidate(digest), digest)
        manifest = json.loads(raw)
        scope = gate.scope_binding(digest)
        self.assertEqual(len(scope), 50)
        self.assertEqual(len(manifest['members']), 28)
        for key, value in scope.items():
            if key != 'candidate_manifest_sha256':
                self.assertTrue(gate.same_typed(manifest.get(key), value), key)
        for name in ('decision', 'independent-report'):
            document = json.loads((folder / (name + '-template-NONEXECUTABLE.json')).read_bytes())
            for key, value in scope.items():
                self.assertTrue(gate.same_typed(document.get(key), value), (name, key))
        activation = json.loads((folder / 'activation-template-NONEXECUTABLE.json').read_bytes())
        for key, value in gate.fixed_fields(digest, gate.PROFILE_FINGERPRINT).items():
            self.assertTrue(gate.same_typed(activation.get(key), value), key)
        self.assertIsNone(activation['not_before']); self.assertIsNone(activation['expires_at'])
        decision = json.loads((folder / 'decision-template-NONEXECUTABLE.json').read_bytes())
        for key in ('live_authorized', 'certificate_exception_authorized', 'login_submission_authorized',
                'credential_transmission_authorized', 'credential_tls_exception_authorized',
                'local_credential_config_read_authorized'):
            self.assertIs(decision[key], False)
        self.assertEqual(hashlib.sha256((folder / 'authority/standing-permission.json').read_bytes()).hexdigest(),
            'f5ceacf9028f773ead882f3e6601004c2c3e28171be31abb85c5be99a1d67b46')
        profile = json.loads((ROOT / 'docs/evidence/A19/navigation-evidence/live-delivery/raw/profile-binding.json').read_bytes())
        self.assertEqual(profile['fingerprint'], gate.PROFILE_FINGERPRINT)
        text = (ROOT / 'tools/a16_current_state_probe.py').read_text(encoding='utf-8')
        lines = text.splitlines(keepends=True)
        regions = {node.name: ''.join(lines[node.lineno-1:node.end_lineno])
            for node in ast.parse(text).body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        unchanged = json.loads((folder / 'unchanged-regions.json').read_bytes())
        for item in unchanged['probe_exact_regions']:
            self.assertEqual(hashlib.sha256(regions[item['name']].encode()).hexdigest(), item['sha256'], item['name'])
        RECORDS.append({'case': 'fixed_candidate_templates_and_regions', 'scope_members': 50,
            'candidate_members': 28, 'templates': 3, 'current_region_hashes': len(unchanged['probe_exact_regions']),
            'baseline_equality_basis': 'Root verified frozen preservation plus frozen author region comparison; no old suite rerun'})

    def test_02_missing_scope_members_and_wrong_same_value_types_cannot_bind(self):
        count = 0
        for index in range(3):
            for key in gate.scope_binding('a' * 64):
                docs = t.authority()
                del docs[index][key]
                with self.assertRaises(gate.Stop): t.validate(*docs)
                count += 1
        for key in ('navigation_limit', 'session_phase_limit', 'local_credential_config_read_limit'):
            for index in range(3):
                docs = t.authority()
                docs[index][key] = float(docs[index][key])
                with self.assertRaises(gate.Stop): t.validate(*docs)
        RECORDS.append({'case': 'required_scope_members', 'missing_rejected': count, 'same_value_float_rejected': 9})


class AwaitAndAssociation(IsolatedAsyncioTestCase):
    async def test_03_no_native_network_id_and_wrong_response_frame_stop_without_admission(self):
        url = gate.ORIGIN + '/qieti/api/user_login/config/permissions'
        g = await t.installed(); g.auth = t.armed()
        ev = t.event(g, url); del ev['networkId']
        g.session.send.reset_mock()
        await g.paused(ev)
        self.assertTrue(g.stopped)
        self.assertEqual(g.failure['codes'], ['SESSION_NETWORK_ASSOCIATION_UNPROVEN'])
        self.assertFalse(g.auth.authenticated)
        self.assertFalse(any(call.args[0] == 'Fetch.continueRequest' for call in g.session.send.await_args_list))
        g = await t.installed(); g.auth = t.armed()
        await g.paused(t.event(g, url))
        g.native_response({'requestId': 'SYNTHETIC_NETWORK', 'frameId': 'OTHER_FAKE_FRAME',
            'type': 'Fetch', 'response': {'status': 200}})
        self.assertTrue(g.stopped)
        self.assertEqual(g.failure['codes'], ['AUTH_RESPONSE_FRAME_UNPROVEN'])
        self.assertFalse(g.auth.authenticated)
        RECORDS.append({'case': 'native_session_association', 'missing_network_and_wrong_frame': 'STOP_BEFORE_ADMISSION'})

    async def test_04_first_guard_failure_during_viewer_DOM_await_cannot_admit(self):
        g = await t.installed(); page = t.FakePage(g); g.auth = t.armed(); page.url = gate.TARGET
        url = gate.ORIGIN + '/qieti/api/user_login/config/permissions'
        await page.transport(url, t.encoded({'code': 0, 'data': {'view': True}}))
        original = page.locator
        def locator(selector):
            control = original(selector)
            if selector == auth.VIEWER:
                async def visible_then_fatal():
                    await asyncio.sleep(0)
                    g.record_failure(gate.Stop('API_BLOCKED'))
                    return True
                control.is_visible = visible_then_fatal
            return control
        page.locator = locator
        with self.assertRaises(gate.Stop): await p.admit_current_viewer(page, g)
        self.assertFalse(g.auth.authenticated)
        self.assertEqual(page.gets, [])
        self.assertEqual(g.failure['codes'], ['API_BLOCKED'])
        RECORDS.append({'case': 'viewer_DOM_await_failure', 'authenticated': False, 'business_gets': 0})

    async def test_05_pending_callback_marks_unknown_and_is_cancelled_with_no_waiter(self):
        g = await t.installed()
        blocker = asyncio.create_task(asyncio.Event().wait())
        g.tasks.add(blocker)
        settled = await p.settle_callbacks(g, seconds=0)
        await asyncio.gather(blocker, return_exceptions=True)
        self.assertFalse(settled)
        self.assertTrue(g.stopped)
        self.assertEqual(g.pending_at_settlement, 1)
        self.assertEqual(g.failure['codes'], ['NETWORK_GUARD_TASKS_PENDING'])
        self.assertTrue(blocker.cancelled())
        self.assertFalse(g.auth.authenticated)
        RECORDS.append({'case': 'pending_settlement', 'settled': False, 'pending': 1,
            'fatal': 'NETWORK_GUARD_TASKS_PENDING', 'synthetic_task_cancelled': True})
