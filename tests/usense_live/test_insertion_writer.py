"""Transport boundary tests. No browser, sockets, profile or account is used."""
import asyncio
import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from annotation.runtime.usense_live import insertion_writer as module


class FakeBinding:
    def check(self):
        return self


class BoundaryTests(unittest.TestCase):
    def policy(self):
        policy = module.InsertPolicy(FakeBinding(), [module.TARGET])
        policy.body_sha = module.sha(b'{}')
        return policy

    def test_unarmed_post_blocked(self):
        self.assertFalse(self.policy().allow('context', 'POST', module.POST, '{}'))

    def test_exact_one_per_layer_then_duplicate_rejected(self):
        p = self.policy(); p.armed = True
        for layer in ('context', 'native'):
            self.assertTrue(p.allow(layer, 'POST', module.POST, '{}'))
        self.assertFalse(p.allow('context', 'POST', module.POST, '{}'))
        self.assertTrue(p.blocked)

    def test_body_endpoint_method_redirect_and_unknown_layer_blocked(self):
        for layer, method, url, body, redirect in (
            ('context', 'POST', module.POST, '{"extra":1}', False),
            ('context', 'POST', module.POST + '?x=1', '{}', False),
            ('context', 'PUT', module.POST, '{}', False),
            ('native', 'POST', module.POST, '{}', True),
            ('fallback', 'POST', module.POST, '{}', False),
            ('context', 'GET', module.POST, None, False)):
            p = self.policy(); p.armed = True
            self.assertFalse(p.allow(layer, method, url, body, redirect))

    def test_seal_blocks_all_network(self):
        p = self.policy(); p.armed = True; p.sealed = True
        self.assertFalse(p.allow('context', 'POST', module.POST, '{}'))
        self.assertFalse(p.allow('native', 'GET', module.TARGET))

    def test_full_read_scope_exact_book_only(self):
        paths = module.full_endpoints()
        self.assertEqual(len(paths), 161)
        self.assertEqual({name.split('_')[0] for name in paths if name.startswith('q')}, {f'q{n}' for n in range(1,23)})
        self.assertEqual(len(set(paths.values())), 161)
        self.assertTrue(all('46007447' in p for p in paths.values()))

    def test_native_types_and_unknown_metadata_are_not_normalized(self):
        self.assertFalse(module.same({'id':'1'}, {'id':1}))
        self.assertFalse(module.same({'a':1,'b':2}, {'b':2,'a':1}))
        self.assertFalse(module.same({'a':1}, {'a':1,'metadata':None}))


class FakeComparator:
    def decode_receipt(self, plan, receipt):
        # Test transport propagation of a strict decoder; schema tests live with insertion.py.
        if receipt != {'code':0,'message':'success','data':{'server_node_id':'observed'}}:
            raise ValueError('UNRECOGNIZED_RECEIPT')
        return {'ok':True,'status':'VALID_INSERT_RECEIPT','node_id':receipt['data']['server_node_id']}


class FakePage:
    def __init__(self, policy, claim, *, receipt=None, error=None, status=200):
        self.policy, self.claim, self.error, self.status = policy, claim, error, status
        self.receipt = receipt if receipt is not None else {'code':0,'message':'success','data':{'server_node_id':'observed'}}
        self.sent = 0

    async def evaluate(self, script, value):
        if script == module.PREPARE:
            return {'sha256': module.sha(b'{}'), 'created_by_bound':True, 'seven_row_user_ids_bound':True,
                'runtime_actor_sha256':module.sha(b'fake-username'), 'runtime_user_id_sha256':module.sha(b'fake-user-id')}
        if script == module.SEND:
            if not self.claim.exists():
                raise AssertionError('NETWORK_BEFORE_DURABLE_INTENT')
            self.sent += 1
            for layer in ('context', 'native'):
                if not self.policy.allow(layer, 'POST', module.POST, '{}'):
                    raise AssertionError('EXACT_POST_WAS_NOT_ALLOWED')
            if self.error:
                raise self.error
            return {'status':self.status, 'body_base64':base64.b64encode(json.dumps(self.receipt).encode()).decode()}
        raise AssertionError('UNEXPECTED_JS')


class SendTests(unittest.IsolatedAsyncioTestCase):
    async def attempt(self, *, receipt=None, error=None, status=200):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); run = root/'run'; run.mkdir(); claim = root/'stable-intent.json'
            policy = module.InsertPolicy(FakeBinding(), [])
            page = FakePage(policy, claim, receipt=receipt, error=error, status=status)
            result = {'post_attempts':0}
            plan = {'payload_candidate':{}, 'ledger_key':'stable-intent', 'plan_sha256':'a'*64}
            failed = None
            with patch.object(module, 'verify_evidence'), patch.object(module, 'comparator', return_value=FakeComparator()):
                try:
                    await module.record_and_send(page=page, policy=policy, plan=plan, claim=claim, run=run, result=result)
                except Exception as exc:
                    failed = exc
                self.assertTrue(claim.exists())
                self.assertEqual(result['post_attempts'], 1)
                self.assertEqual(page.sent, 1)
                self.assertFalse(policy.armed)
                self.assertTrue(policy.sealed)
                # A new process/policy and a different plan hash cannot reuse stable intent.
                new_policy = module.InsertPolicy(FakeBinding(), [])
                other = FakePage(new_policy, claim)
                plan['plan_sha256'] = 'b'*64
                with self.assertRaises(FileExistsError):
                    await module.record_and_send(page=other, policy=new_policy, plan=plan, claim=claim, run=run, result={})
                self.assertEqual(other.sent, 0)
            return result, failed

    async def test_success_remains_unaccepted_until_independent_readback(self):
        result, failed = await self.attempt()
        self.assertIsNone(failed)
        self.assertEqual(result['status'], 'INSERT_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK')
        self.assertNotIn('save_success', result)

    async def test_timeout_preserves_once_intent(self):
        _, failed = await self.attempt(error=asyncio.TimeoutError())
        self.assertIsInstance(failed, asyncio.TimeoutError)

    async def test_unknown_receipt_metadata_preserves_once_intent(self):
        _, failed = await self.attempt(receipt={'code':0,'message':'success','data':{'server_node_id':'observed'},'unknown':1})
        self.assertIsInstance(failed, ValueError)

    async def test_non200_preserves_once_intent(self):
        _, failed = await self.attempt(status=500)
        self.assertIsNotNone(failed)


if __name__ == '__main__':
    unittest.main()
