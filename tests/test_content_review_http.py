"""Actual loopback requests through the offline review API; no platform calls."""
import http.client
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import urlencode

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
from annotation.recognition.content_revision import make_revision_plan
from annotation.recognition.content_review import ReviewWorkspace
from annotation.recognition.content_review_server import make_server
from content_revision_fixture import make_content_fixture
from test_content_region import region_operation


class ReviewHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.d = make_content_fixture(self.root/'input')
        self.op = region_operation(self.d['evidence'], self.d['graph'])
        self.author = dict(kind='MODEL_DRAFT', id='http-development-test', note='Generated source; not content approval')
        self.plan = make_revision_plan(self.d['evidence'], self.d['graph'], self.d['check'], [self.op], self.author)
        self.workspace = ReviewWorkspace(self.d['evidence'], self.d['graph'], self.d['check'], self.d['review'],
            self.plan, self.root/'workspace', [self.d['source_path']])
        self.server = make_server(self.workspace)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)
        self.port = self.server.server_address[1]
        status, _, raw = self.request('GET', '/api/state')
        self.assertEqual(status, 200, raw)
        self.state = json.loads(raw)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, method, path, value=None, *, headers=None, raw=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=20)
        hs = dict(headers or {})
        if value is not None:
            raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
            hs.setdefault('Content-Type', 'application/json')
        if method == 'POST':
            hs.setdefault('X-Review-Token', getattr(self, 'state', {}).get('csrf_token', ''))
        try:
            conn.request(method, path, body=raw, headers=hs)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def save_body(self):
        answer = next(a for a in self.state['answers'] if a['answer_id'] == self.op['target']['answer_id'])
        block = next(b for b in answer['blocks'] if b['kind'] == 'REGION')
        return dict(expected_head=self.state['head'], answer_id=answer['answer_id'], author=self.author,
                    changes=[dict(key=block['key'], runs=[dict(format='latex', text=r'\frac{x^{2}+1}{2}')])])

    def test_state_and_static_resources_do_not_depend_on_external_runtime(self):
        self.assertEqual(self.state['decision'], 'HOLD')
        self.assertFalse(self.state['transcription_verified'])
        self.assertEqual(self.state['platform_actions'], [])
        math = [r for a in self.state['answers'] for b in a['blocks'] for r in b['runs'] if r['format'] == 'latex']
        self.assertTrue(math)
        self.assertTrue(all('math_preview' in r for r in math))
        for path in ('/', '/review.js', '/review.css'):
            with self.subTest(path=path):
                status, headers, raw = self.request('GET', path)
                self.assertEqual(status, 200, raw)
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
                self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
                self.assertNotIn('Access-Control-Allow-Origin', headers)

    def test_save_checks_content_and_stale_tab_cannot_clobber_it(self):
        request = self.save_body()
        status, _, raw = self.request('POST', '/api/save', request)
        self.assertEqual(status, 200, raw)
        result = json.loads(raw)['state']
        self.assertNotEqual(result['head'], self.state['head'])
        self.assertEqual(result['plan_revision'], self.state['plan_revision']+1)
        self.assertEqual(result['decision'], 'HOLD')
        status, _, raw = self.request('POST', '/api/save', request)
        self.assertEqual(status, 409, raw)
        self.assertEqual(json.loads(raw)['error']['code'], 'STALE_HEAD')
        self.assertEqual(self.workspace.state()['head'], result['head'])

    def test_restore_creates_new_revision_and_export_matches_current_plan(self):
        status, _, raw = self.request('POST', '/api/save', self.save_body())
        self.assertEqual(status, 200, raw)
        saved = json.loads(raw)['state']
        request = dict(expected_head=saved['head'], revision_head=self.state['head'], author=self.author)
        status, _, raw = self.request('POST', '/api/restore', request)
        self.assertEqual(status, 200, raw)
        restored = json.loads(raw)['state']
        self.assertNotEqual(restored['head'], self.state['head'])
        self.assertEqual(restored['plan_revision'], saved['plan_revision']+1)
        status, headers, raw = self.request('GET', '/api/export/plan')
        self.assertEqual(status, 200)
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertEqual(json.loads(raw), self.workspace.documents()['plan'])

    def test_real_original_crop_pixels_and_path_traversal_rejection(self):
        aid = self.op['source_region']['asset_id']
        status, _, raw = self.request('GET', '/api/source?' + urlencode(dict(asset_id=aid, bbox='10,10,20,20')))
        self.assertEqual(status, 200, raw)
        with Image.open(io.BytesIO(raw)) as crop:
            self.assertEqual(crop.size, (10,10))
        status, _, raw = self.request('GET', '/api/source?' + urlencode(dict(asset_id='../../private')))
        self.assertEqual(status, 400, raw)
        status, _, raw = self.request('GET', '/../content_review.py')
        self.assertEqual(status, 404, raw)

    def test_foreign_origins_hosts_and_missing_or_nonascii_tokens_do_not_mutate(self):
        for headers in ({'Origin':'https://unrelated.example'}, {'Host':'unrelated.example'},
                        {'X-Review-Token':''}, {'X-Review-Token':'é'}):
            with self.subTest(headers=headers):
                status, _, raw = self.request('POST','/api/save', self.save_body(), headers=headers)
                self.assertEqual(status, 403, raw)
                self.assertEqual(self.workspace.state()['head'], self.state['head'])

    def test_duplicate_json_fields_and_unknown_approval_fields_are_rejected(self):
        status, _, raw = self.request('POST', '/api/save', raw=b'{"expected_head":"a","expected_head":"b"}',
                                      headers={'Content-Type':'application/json'})
        self.assertEqual(status, 400, raw)
        request = self.save_body()
        request['transcription_verified'] = True
        status, _, raw = self.request('POST', '/api/save', request)
        self.assertEqual(status, 400, raw)
        self.assertEqual(self.workspace.state()['head'], self.state['head'])

    def test_preview_preserves_unknown_math_and_never_changes_head(self):
        raw_text = r'\unknown{<script>alert(1)</script>}'
        status, _, raw = self.request('POST', '/api/preview', dict(text=raw_text))
        self.assertEqual(status, 200, raw)
        value = json.loads(raw)['preview']
        self.assertFalse(value['supported'])
        self.assertEqual(value['raw_latex'], raw_text)
        self.assertEqual(self.workspace.state()['head'], self.state['head'])

    def test_source_mutation_is_rejected_instead_of_displaying_new_pixels(self):
        source = json.loads(self.d['source_path'].read_text(encoding='utf-8'))
        aid = self.op['source_region']['asset_id']
        asset = next(a for a in source['assets'] if a['asset_id'] == aid)
        path = self.d['source_path'].parent / asset['path']
        path.write_bytes(path.read_bytes() + b'changed-source')
        status, _, raw = self.request('GET', '/api/source?' + urlencode(dict(asset_id=aid)))
        self.assertEqual(status, 409, raw)
        self.assertEqual(json.loads(raw)['error']['code'], 'SOURCE_CHANGED')

    def test_non_loopback_binding_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'only to 127.0.0.1'):
            make_server(self.workspace, host='0.0.0.0')

    def test_cli_preparation_in_fresh_process_forbids_models_and_network(self):
        values = [self.d['evidence'],self.d['graph'],self.d['check'],self.d['review'],self.plan]
        args = []
        for name,value in zip(('evidence','graph','base-check','review','plan'), values):
            path = self.root/(name+'.json')
            path.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
            args += ['--'+name,str(path)]
        args += ['--source',str(self.d['source_path']),'--workdir',str(self.root/'cli-workspace'),'--check-only']
        script = '''import importlib.abc,runpy,socket,sys
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0]in{'onnxruntime','rapidocr_onnxruntime','rapid_latex_ocr','torch','paddle'}:raise AssertionError('model imported')
def deny(*a,**kw):raise AssertionError('network used')
socket.socket.connect=socket.socket.connect_ex=socket.create_connection=deny
sys.meta_path.insert(0,NoModels())
sys.argv=[sys.argv[1]]+sys.argv[2:]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        r = subprocess.run([sys.executable,'-X','utf8','-c',script,str(ROOT/'tools/review_content_b.py'),*args],
                           capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        result = json.loads(r.stdout)
        self.assertTrue(result['ready'])
        self.assertEqual(result['new_model_calls'], 0)
        self.assertEqual(result['platform_actions'], [])


if __name__ == '__main__':
    unittest.main()
