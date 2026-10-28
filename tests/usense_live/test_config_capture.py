import asyncio
import base64
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from annotation.runtime.usense_live import core
from annotation.runtime.usense_live.config import configure, endpoints, capture_endpoints
from annotation.runtime.usense_live.capture import capture


class ConfigCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.tmp.name)
        self.profile = self.root/'project-browser'
        self.runs = self.root/'runs'
        self.profile.mkdir()
        self.runs.mkdir()
        self.config = self.root/'capture.json'

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, **extra):
        result = configure(profile=self.profile, output_root=self.runs, config_path=self.config,
            coordinator='test-coordinator', executor='test-executor', reviewer='test-reviewer',
            authorization_reference='SYNTHETIC_ONLY_NOT_LIVE_PERMISSION', **extra)
        return core.load_binding(self.config, result['sha256'])

    def test_three_orders_and_pages_roundtrip_exact(self):
        binding = self.make(orders=[3, 4, 5], pages=[10, 173])
        self.assertEqual(capture_endpoints(binding), endpoints([3, 4, 5], [10, 173]))
        self.assertEqual(len(capture_endpoints(binding)), 25)
        self.assertEqual(binding.data['tls'], {'mode': 'STRICT'})

    def test_batch_and_duplicate_limits(self):
        for orders in ([1, 2, 3, 4, 5, 6, 7], [3, 3], [True], [0]):
            with self.subTest(orders=orders), self.assertRaises(core.BindingError):
                endpoints(orders)

    def test_missing_one_zone_does_not_count_as_complete_q3(self):
        binding = self.make(orders=[3])
        data = copy.deepcopy(binding.data)
        data['allowed_get'] = data['allowed_get'][:-1]
        self.config.write_bytes(core.canonical(data))
        broken = core.load_binding(self.config, core.sha(self.config.read_bytes()))
        with self.assertRaisesRegex(core.BindingError, 'INCOMPLETE_OR_UNOBSERVED'):
            capture_endpoints(broken)

    def test_manual_login_has_no_order_read_scope(self):
        with self.assertRaisesRegex(core.BindingError, 'LOGIN_HAS_NO_BUSINESS_READS'):
            self.make(orders=[3], login=True)

    def test_capture_saves_byte_exact_bom_and_checks_both_layers(self):
        binding = self.make(orders=[3])
        bodies = b'\xef\xbb\xbf{"code":0,"message":"success","data":{"unknown":null}}'
        class Page:
            async def route(self, *args):
                pass
            async def evaluate(self, javascript, path):
                owner.policy.counts[('context', core.ORIGIN+path)] = 1
                owner.policy.counts[('native', core.ORIGIN+path)] = 1
                return {'status': 200, 'content_type': 'application/json',
                        'body_base64': base64.b64encode(bodies).decode()}
        class Owner:
            def __init__(self):
                self.page = Page()
                self.policy = type('Policy', (), {'counts': {}, 'blocked': False})()
                self.release = None
            async def __aenter__(self):
                binding.output.mkdir()
                return self
            async def navigate(self):
                pass
            async def __aexit__(self, *args):
                self.release = {'context_runtime_release_confirmed': True}
        owner = Owner()
        with patch('annotation.runtime.usense_live.capture.owned_readonly_context', return_value=owner):
            result = asyncio.run(capture(self.config, binding.raw_sha256))
        self.assertEqual(result['status'], 'NATIVE_GETS_CAPTURED')
        self.assertEqual((binding.output/'q3_question.json').read_bytes(), bodies)
        self.assertEqual(result['captures']['q3_question']['sha256'], core.sha(bodies))
        self.assertEqual(result['captures']['q3_question']['request_counts'], {'context': 1, 'native': 1})
        self.assertFalse(result['viewer_rendered'])


if __name__ == '__main__':
    unittest.main()
