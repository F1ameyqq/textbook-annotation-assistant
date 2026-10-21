"""Four bounded independent groups; frozen imports, synthetic transport only."""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tests/a24_current_contract'))
import fixtures as f
from fixtures import p, gate, policy
from annotation.source.usense.current_readonly import decode

RECORDS = []
ROW = {'id': gate.BOOK, 'title': 'INDEPENDENT_SYNTHETIC_TARGET'}


class PureControls(TestCase):
    def test_01_canonical_nonfirst_priority_truthiness_and_finite_projection(self):
        cases = [
            ({'records': [{'id': 'OTHER', 'title': 'OTHER'}, ROW]}, 'MATCHED_TARGET', 'records'),
            ({'records': [], 'books': [ROW]}, 'BOOK_TARGET_ABSENT', 'records'),
            ({'records': {}, 'books': [ROW]}, 'BOOK_LIST_CONTAINER_REJECTED', 'records'),
            ({'records': 0, 'books': [ROW]}, 'MATCHED_TARGET', 'books'),
            ({'records': False, 'books': '', 'list': [ROW]}, 'MATCHED_TARGET', 'list'),
            ({'records': None, 'books': [], 'list': [ROW]}, 'BOOK_TARGET_ABSENT', 'books'),
            ({'records': [ROW, dict(ROW)]}, 'BOOK_TARGET_CONFLICT', 'records'),
            ({'records': [{'file_id': gate.BOOK, 'title': 'ALIAS'}]}, 'BOOK_TARGET_ABSENT', 'records'),
            ({'records': [dict(ROW, title='\x00bad')]}, 'BOOK_TITLE_MISSING', 'records'),
            ({'records': [ROW, 0]}, 'BOOK_LIST_ITEM_SCHEMA_REJECTED', 'records'),
        ]
        for data, branch, selected in cases:
            body = {'code': 0, 'data': data}
            facts, row = decode.book_contract(body)
            self.assertEqual((facts['branch'], facts['selected_container']), (branch, selected))
            if branch == 'MATCHED_TARGET':
                self.assertEqual(decode.book_identity(body)['id'], gate.BOOK)
            else:
                with self.assertRaises(gate.Stop):
                    decode.book_identity(body)
        secret = 'INDEPENDENT_SECRET_VALUE_NOT_FOR_EXPORT'
        body = {'code': '403', 'data': {'records': [dict(ROW, password=secret, token=secret)],
            'books': [dict(ROW, title=secret)], secret: secret}, secret: secret}
        for name in policy.FIXED:
            projected = decode.response_facts(name, 403, body)
            text = json.dumps(projected)
            self.assertNotIn(secret, text)
            self.assertNotIn('password', text)
            self.assertNotIn('token', text)
            self.assertEqual((projected['http_status'], projected['business_code']), (403, '403'))
            self.assertFalse(projected['server_schema_confirmed'])
        duplicate = decode.book_contract({'data': {'records': [ROW] * 9}})[0]
        self.assertEqual((duplicate['target_match_count'], len(duplicate['target_fields'])), (9, 2))
        RECORDS.append({'group': 'canonical_and_projection', 'canonical_cases': len(cases),
            'projection_endpoints': 6, 'duplicate_count_exact_and_projection_cap': [9, 2]})

    def test_04_all_scope_fields_three_documents_types_deletions_and_templates(self):
        scope = gate.scope_binding('a' * 64)
        self.assertEqual(len(scope), 66)
        a, d, r = f.authority()
        self.assertEqual(f.validate(a, d, r).candidate_sha256, 'a' * 64)
        checks = 0
        for doc_index in range(3):
            for field, expected in scope.items():
                docs = [copy.deepcopy(x) for x in (a, d, r)]
                del docs[doc_index][field]
                with self.assertRaises(gate.Stop):
                    f.validate(*docs)
                checks += 1
                docs = [copy.deepcopy(x) for x in (a, d, r)]
                if type(expected) is bool:
                    wrong = int(expected)
                elif type(expected) is int:
                    wrong = bool(expected) if expected in (0, 1) else str(expected)
                elif type(expected) is list:
                    wrong = list(expected) + ['UNAUTHORIZED_EXTRA']
                else:
                    wrong = expected + '__WRONG'
                docs[doc_index][field] = wrong
                with self.assertRaises(gate.Stop):
                    f.validate(*docs)
                checks += 1
        real_candidate = 'd10e30b4567ba5c4a81b8aa53396e35619e05f191e457a40c371866499161753'
        real_scope = gate.scope_binding(real_candidate)
        templates = {}
        for name in ('activation', 'decision', 'independent-report'):
            document = json.loads((ROOT / ('docs/evidence/A24/current-contract/' + name +
                '-template-NONEXECUTABLE.json')).read_bytes())
            for field, expected in real_scope.items():
                self.assertTrue(gate.same_typed(document.get(field), expected), (name, field))
            templates[name] = document
        self.assertFalse(templates['decision']['live_authorized'])
        self.assertIsNone(templates['activation']['not_before'])
        self.assertEqual(templates['independent-report']['result'], 'NOT_REVIEWED')
        self.assertEqual(real_scope['book_request_plan'], 'FIXED_GET_PAGE1_SIZE10_TARGET_ID_NO_CONTEXT_ADDITION')
        self.assertEqual((real_scope['book_picker_action_limit'], real_scope['mapping_ui_actions_limit'],
            real_scope['business_write_limit'], real_scope['sample_limit']), (0, 0, 0, 0))
        RECORDS.append({'group': 'complete_typed_bindings', 'scope_fields': list(real_scope),
            'scope_count': 66, 'rejected_mutations': checks, 'templates_compared': 3,
            'real_scope': real_scope})


class AsyncControls(IsolatedAsyncioTestCase):
    async def test_02_HTTP_before_body_all_six_and_facts_before_adapter_failure(self):
        g = await f.installed()
        g.output = f.MemoryOutput()
        saved, order = {}, []

        def save(path, value):
            self.assertNotIn(path.name, saved)
            saved[path.name] = copy.deepcopy(value)
            order.append(path.name)

        for name, endpoint in policy.FIXED.items():
            url = gate.ORIGIN + endpoint
            async def read_body(current=name):
                self.assertIn('response-http-' + current + '.json', saved)
                self.assertNotIn('response-facts-' + current + '.json', saved)
                return f.encoded({'code': 0, 'data': {'records': [ROW], 'token': 'NEVER_EXPORT'}})
            response = NS(url=url, request=f.request(g, url), status=200,
                body=read_body, headers={})
            with patch.object(p, 'save_new', save):
                await g.capture(response)
            self.assertIn('response-facts-' + name + '.json', saved)
        self.assertNotIn('NEVER_EXPORT', json.dumps(saved))
        self.assertEqual(len(g.business_facts), 6)
        self.assertFalse(g.stopped)

        rejected_guard = await f.installed()
        page = f.FakePage(rejected_guard)
        memory = f.MemoryOutput()
        rejected_guard.output = memory
        result = {'steps': {}, 'sources': [], 'gaps': []}
        rejected_saved = {}
        def reject_adapter(body):
            self.assertIn('response-facts-book.json', rejected_saved)
            self.assertEqual(rejected_saved['response-facts-book.json']['book_contract']['target_match_count'], 1)
            raise gate.Stop('INDEPENDENT_SYNTHETIC_ADAPTER_STOP')
        with patch.object(p, 'LIVE_OUT', memory), \
                patch.object(p, 'save_new', lambda path, value: rejected_saved.update({path.name: copy.deepcopy(value)})), \
                patch.object(p, 'book_identity', reject_adapter):
            with self.assertRaisesRegex(gate.Stop, '^INDEPENDENT_SYNTHETIC_ADAPTER_STOP$'):
                await p.collect(page, rejected_guard, result)
        self.assertEqual(result['steps']['book'], 'FAILED')
        self.assertNotIn('directory', result['steps'])
        self.assertEqual(page.gets, [policy.FIXED['book']])
        RECORDS.append({'group': 'pre_adapter_evidence', 'six_endpoint_write_order': order,
            'adapter_failure_facts_retained': True, 'successor_reads': 0})

    async def test_03_zero_UI_unknown_mapping_auto_capture_reuse_and_pending_no_send(self):
        original_admit = p.admit_current_viewer
        original_evaluate = f.FakePage.evaluate
        async def admit_and_existing_book(page, g):
            await original_admit(page, g)
            await page.transport(gate.ORIGIN + policy.FIXED['book'], f.encoded({'code': 0,
                'data': {'records': [dict(ROW, question_count=1)]}}))
        async def absent_canvas(page, script, arg):
            if type(arg) is list:
                return None
            return await original_evaluate(page, script, arg)
        async def ui_forbidden(*args, **kwargs):
            raise AssertionError('ANY_UI_ACTION_FORBIDDEN_INDEPENDENT')
        with patch.object(p, 'admit_current_viewer', admit_and_existing_book), \
                patch.object(f.FakePage, 'evaluate', absent_canvas), \
                patch.object(f.FakeControl, 'click', ui_forbidden), \
                patch.object(f.FakeControl, 'fill', ui_forbidden), \
                patch.object(f.FakeControl, 'press', ui_forbidden):
            g, page, result, saved, images = await f.collect_fake()
        self.assertNotIn(policy.FIXED['book'], page.gets)
        self.assertEqual([x for x in page.gets if not x.startswith('https:')], list(policy.FIXED.values())[1:])
        self.assertEqual((len(g.sent), len(images)), (8, 2))
        self.assertEqual([x['mapping']['visible_status'] for x in result['sources']], ['UNKNOWN', 'UNKNOWN'])
        self.assertTrue(all(x['mapping']['save_page_status'] == 'UNKNOWN' for x in result['sources']))
        self.assertFalse(result['book_picker_identity_confirmed'])
        self.assertFalse(result['write_eligible'])
        before = len(g.sent)
        url = gate.ORIGIN + policy.FIXED['book']
        route = f.route(f.request(g, url))
        await g.route(route)
        self.assertEqual(route.continue_.await_count, 0)
        self.assertEqual(route.fulfill.await_count, 1)
        await g.paused(f.event(g, url, network='INDEPENDENT_REPLAY'))
        self.assertEqual(len(g.sent), before)

        pending = await f.installed()
        pending.sent.add(url)
        pending_page = f.FakePage(pending)
        original_wait = p.await_existing_response
        async def expired_existing_wait(current, current_url):
            times = iter((0, 21))
            return await original_wait(current, current_url, clock=lambda: next(times))
        with patch.object(p, 'await_existing_response', expired_existing_wait):
            with self.assertRaisesRegex(gate.Stop, '^EXISTING_GET_RESPONSE_UNPROVEN$'):
                await p.get_once(pending_page, pending, policy.FIXED['book'])
        self.assertEqual(pending_page.gets, [])
        self.assertEqual(pending.sent, {url})
        RECORDS.append({'group': 'zero_UI_shared_budget_passive_UNKNOWN',
            'actual_synthetic_business_and_image_sends': 8, 'automatic_book_sends': 1,
            'active_book_sends': 0, 'context_and_native_replay_new_sends': 0,
            'pending_UNKNOWN_new_sends': 0, 'all_UI_actions_trapped': True,
            'visible_and_save_mapping': 'UNKNOWN'})
