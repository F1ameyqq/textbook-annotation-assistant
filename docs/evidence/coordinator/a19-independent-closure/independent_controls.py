"""Three finite A19 reviewer controls; all identities and effects are synthetic."""
import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import a16_current_state_probe as p
from annotation.source.usense.current_readonly import gate, policy

RECORDS = []
CANDIDATE = '2e94be09ff3d733bcf65b7fa556187280deb09574134866b110e3575dd233f7f'
SECRET = 'REVIEW_PRIVATE_QUERY_PROXY_PASSWORD'


def new_guard():
    g = p.CurrentGuard(None, NS(main_frame=object()), policy.ReadPolicy())
    g.main_frame_id = 'REVIEW_PRIVATE_FRAME'
    g.session = NS(send=AsyncMock(return_value={}))
    return g


def request():
    return {'requestId': 'REVIEW_FETCH', 'networkId': 'REVIEW_NETWORK',
        'frameId': 'REVIEW_PRIVATE_FRAME', 'resourceType': 'Document',
        'request': {'method': 'GET', 'url': gate.TARGET}}


def response(**changes):
    data = {'requestId': 'REVIEW_NETWORK', 'frameId': 'REVIEW_PRIVATE_FRAME',
        'type': 'Document', 'response': {'status': 503, 'url': SECRET,
        'headers': {'proxy-password': SECRET}}, 'loaderId': SECRET}
    data.update(changes)
    return data


def failure(**changes):
    data = {'requestId': 'REVIEW_NETWORK', 'type': 'Document', 'canceled': False,
        'blockedReason': SECRET, 'errorText': 'net::ERR_ABORTED ' + SECRET}
    data.update(changes)
    return data


class Binding(TestCase):
    def test_exact_29_binding_and_narrow_report_rejection(self):
        expected = {
            'task': 'A19',
            'run_id': 'A19-navigation-evidence-01a1597c-8eb9-7692-8279-685c4d9d105d',
            'workflow_commit': 'c4cfdb2012b36f47f13e633a24dafad6c3daa8ab',
            'scope': 'CURRENT_BOOK_SOURCE_INVENTORY_NAVIGATION_EVIDENCE_READONLY',
            'candidate_manifest_sha256': CANDIDATE, 'sample_limit': 0,
            'automatic_schema_confirmation': False, 'fixed_business_get_count': 6,
            'original_get_count': 2, 'new_live_limit': 1, 'context_limit': 1,
            'navigation_limit': 1, 'total_seconds': 900,
            'business_get_limit_per_url': 1, 'original_limit_per_viewer': 1,
            'login_submission_limit': 0, 'business_write_limit': 0,
            'upload_limit': 0, 'ocr_limit': 0, 'old_budgets_restored': False,
            'executor_thread_id': '01a1597c-8eb9-7692-8279-685c4d9d105d',
            'output_directory': 'D:/1800/.local/stages/a19-navigation-evidence-live',
            'activation_path': 'D:/1800/.local/stages/a19-navigation-evidence-activation.json',
            'decision_path': 'D:/1800/docs/approvals/A19-navigation-evidence-user-decision.json',
            'report_path': 'D:/1800/docs/evidence/coordinator/a19-independent-closure/independent-result.json',
            'excluded_static_event_limit': 16, 'version_check_limit': 1,
            'standing_tls_permission_path': 'D:/1800/docs/approvals/A17-excluded-static-user-decision.json',
            'standing_tls_permission_sha256': 'f5ceacf9028f773ead882f3e6601004c2c3e28171be31abb85c5be99a1d67b46'}
        self.assertEqual(len(expected), 29)
        self.assertEqual(gate.scope_binding(CANDIDATE), expected)
        folder = ROOT / 'docs/evidence/A19/navigation-evidence'
        template = json.loads((folder / 'independent-report-template-NONEXECUTABLE.json').read_bytes())
        self.assertEqual(template, {**expected, 'result': 'NOT_REVIEWED'})
        now = datetime(2026, 10, 20, 14, tzinfo=timezone.utc)
        decision = {**expected, 'tls_mode': 'CONTEXT_EXCEPTION',
            'live_authorized': True, 'certificate_exception_authorized': True}
        good = {**expected, 'result': 'ACCEPTED_OFFLINE_ONLY'}
        encode = lambda value: json.dumps(value, sort_keys=True).encode('utf-8')
        dr = encode(decision)
        def check(report):
            rr = encode(report)
            activation = {**gate.fixed_fields(CANDIDATE, 'f' * 64),
                'not_before': now.isoformat(), 'expires_at': (now + timedelta(seconds=900)).isoformat(),
                'tls_mode': 'CONTEXT_EXCEPTION', 'user_decision_sha256': gate.sha(dr),
                'independent_report_sha256': gate.sha(rr)}
            raw = encode(activation)
            return gate.validate_activation(raw, gate.sha(raw), CANDIDATE, 'f' * 64,
                dr, rr, explicit_live=True, exception=True, now=now)
        self.assertTrue(check(good).ignore_https_errors)
        removed = ['new_live_limit', 'context_limit', 'navigation_limit', 'total_seconds',
            'business_get_limit_per_url', 'original_limit_per_viewer', 'login_submission_limit',
            'business_write_limit', 'upload_limit', 'ocr_limit', 'old_budgets_restored']
        narrow = {k: v for k, v in good.items() if k not in removed}
        variants = [narrow, {**good, 'login_submission_limit': False},
            {**good, 'upload_limit': 1}, {**good, 'ocr_limit': 1},
            {**good, 'report_path': 'D:/1800/docs/evidence/coordinator/a18-independent-closure/independent-result.json'}]
        for bad in variants:
            with self.assertRaises(gate.Stop) as caught:
                check(bad)
            self.assertEqual(str(caught.exception), 'OBSERVATION_SCOPE_BINDING_REQUIRED')
        self.assertEqual(gate.context_options(), {'ignore_https_errors': False})
        RECORDS.append({'case': 'exact_29_binding', 'keys': sorted(expected),
            'golden_accepted_in_memory': True, 'negative_variants_rejected': len(variants),
            'activation_files_created': 0})


class Events(IsolatedAsyncioTestCase):
    async def test_http_event_failure_and_timeout_are_distinct_sources(self):
        g, saved = new_guard(), {}
        page = NS()
        async def goto(*args, **kwargs):
            await g.paused(request())
            g.native_response(response(requestId='UNRELATED'))
            g.native_response(response(frameId='IFRAME'))
            self.assertFalse(g.navigation.snapshot()['response_received']['observed'])
            g.native_response(response())
            g.native_loading_failed(failure())
            raise TimeoutError('net::ERR_TUNNEL_CONNECTION_FAILED ' + SECRET)
        page.goto = AsyncMock(side_effect=goto)
        async def opened(profile, approval, state):
            state['guard'] = g
            return page, g
        async def closed(state):
            g.record_failure(p.Stop('CLOSE_FAILED'))
            state['release']['state'] = 'RELEASED'
        def save(path, value):
            saved[path.name] = copy.deepcopy(value)
        with patch.object(p, 'open_owned', opened), patch.object(p.native, 'close_owned', closed), \
                patch.object(p, 'save_new', save), patch.object(p, 'get_once', AsyncMock()) as get:
            self.assertEqual(await p.observe_live(None, None), 2)
            get.assert_not_awaited()
        d = saved['current-state.json']
        n = d['navigation_diagnostics']
        self.assertEqual(d['error'], {'exception_type': 'TimeoutError', 'codes': ['ERR_TUNNEL_CONNECTION_FAILED']})
        self.assertEqual(n['response_received']['http_status'], 503)
        self.assertEqual(n['loading_failed']['codes'], ['ERR_ABORTED'])
        self.assertFalse(n['loading_failed']['cancelled'])
        self.assertEqual(n['loading_failed']['blocked_reason'], 'UNKNOWN')
        self.assertEqual(n['root_cause'], 'UNKNOWN')
        self.assertIsNone(n['goto']['http_status'])
        self.assertEqual(n['goto']['response_returned'], 'UNKNOWN')
        self.assertEqual(n['phase'], 'GOTO')
        self.assertEqual(d['guard_at_serialization']['failure']['codes'], ['CLOSE_FAILED'])
        self.assertEqual(d['steps']['navigation'], 'FAILED')
        self.assertTrue(all(v == 'NOT_RUN' for k, v in d['steps'].items() if k != 'navigation'))
        for value in (SECRET, 'REVIEW_NETWORK', 'REVIEW_PRIVATE_FRAME', 'networkId', 'loaderId', 'https://'):
            self.assertNotIn(value, json.dumps(n))
        self.assertNotIn(SECRET, json.dumps(d))
        self.assertFalse(d['write_eligible'] or d['production_ready'])
        RECORDS.append({'case': 'three_distinct_sources', 'navigation': n,
            'top_error': d['error'], 'cleanup_failure': d['guard_at_serialization']['failure'],
            'steps': d['steps']})

    async def test_missing_identity_and_sealed_events_do_not_reassign_navigation(self):
        g = new_guard()
        g.navigation.begin('goto')
        unbound = request()
        del unbound['networkId']
        await g.paused(unbound)
        g.native_response(response())
        g.native_loading_failed(failure())
        unknown = g.navigation.snapshot()
        self.assertEqual(unknown['association'], 'UNKNOWN')
        self.assertFalse(unknown['response_received']['observed'])
        self.assertFalse(unknown['loading_failed']['observed'])
        self.assertIsNone(unknown['goto']['http_status'])
        g = new_guard()
        g.navigation.begin('goto')
        await g.paused(request())
        sends = g.session.send.await_count
        g.record_failure(p.Stop('ORIGIN_BLOCKED'))
        g.begin_shutdown()
        self.assertTrue(await p.settle_callbacks(g, seconds=.2))
        g.sealed = True
        g.native_response(response(requestId='UNRELATED'))
        self.assertFalse(g.navigation.snapshot()['response_received']['observed'])
        g.native_loading_failed(failure())
        g.native_loading_failed(failure(errorText='net::ERR_FAILED'))
        n = g.navigation.snapshot()
        self.assertEqual(n['loading_failed']['lifecycle'], 'SEALED')
        self.assertEqual(n['loading_failed']['codes'], ['ERR_ABORTED'])
        self.assertEqual(g.failure['codes'], ['ORIGIN_BLOCKED'])
        self.assertTrue(g.terminal_stopped)
        self.assertEqual(g.tasks | g.callbacks, set())
        self.assertEqual(g.session.send.await_count, sends)
        RECORDS.append({'case': 'missing_and_sealed_identity', 'unknown': unknown,
            'sealed': n, 'first_error': g.failure, 'new_send_calls': 0})
