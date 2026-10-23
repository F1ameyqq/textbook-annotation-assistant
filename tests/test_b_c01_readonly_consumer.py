"""Fresh-process consumption of the existing fixed bundle; no runtime dispatch."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / 'tests/fixtures/book46007447/a24-c01-readonly-pins-20261023.json'
TOOL = ROOT / 'tools/consume_b_c01_readonly.py'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


class FixedC01ReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.source = cls.root / 'a24-c01'
        cls.delivery = cls.root / 'delivery'
        pins = json.loads(PINS.read_bytes())
        archive = ROOT / 'handoffs/b/a24/a24-offline-replay-20261022-v2-final.zip'
        if sha(archive.read_bytes()) != 'c4ad1b298dd34a8b0a5ec8706a3514fefe19d9a33582cd27fa826ef1a94ec89e':
            raise ValueError('FIXED_A24_ARCHIVE_CHANGED')
        with zipfile.ZipFile(archive) as z:
            for member in pins['members']:
                target = cls.source / member['path']
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read('a24-offline-replay/baseline/' + member['path']))
        archive = ROOT / 'handoffs/b/46007447/B-46007447-Q16-reading-C01-v2-HOLD-2026-10-21.zip'
        if sha(archive.read_bytes()) != '4725523ec499a3074b268b12f0282ca795c13ddd98e97350078a50db89f7dc93':
            raise ValueError('FIXED_B_V2_ARCHIVE_CHANGED')
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if not name.startswith('delivery/') or name.endswith('/'):
                    continue
                target = cls.root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        self.out = self.run / 'readback.json'

    def consume(self, bundle=None, count=4, source=None):
        return subprocess.run([sys.executable, '-B', '-X', 'utf8', str(TOOL),
            '--a-source', str(source or self.source), '--pins', str(PINS), '--pins-sha256', sha(PINS.read_bytes()),
            '--bundle', str(bundle or self.delivery / 'bundle.json'), '--expected-questions', str(count),
            '--out', str(self.out)], cwd=self.run, capture_output=True, text=True, encoding='utf-8')

    def test_fixed_a24_reads_every_field_and_resource_from_unrelated_cwd(self):
        result = self.consume()
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(self.out.read_bytes())
        self.assertEqual(actual['questions'], 4)
        self.assertEqual(actual['fragments'], 26)
        self.assertTrue(actual['complete_object_equal'])
        self.assertEqual(actual['full_object'], json.loads((self.delivery / 'bundle.json').read_bytes()))
        self.assertFalse(actual['planning_or_dispatch'])

    def test_existing_four_questions_cannot_be_called_nine(self):
        result = self.consume(count=9)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('EXPECTED_QUESTION_SCOPE_COUNT', result.stderr)
        self.assertFalse(self.out.exists())

    def test_private_candidate_schema_is_not_accepted_as_c01(self):
        file = self.run / 'candidate.json'
        file.write_text(json.dumps({'schema': 'PrivateLessonSourceCandidateBundle/v1', 'items': []}), encoding='utf-8')
        result = self.consume(file, 9)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('EXPECTED_EXISTING_C01_NOT_PRIVATE_CANDIDATE_SCHEMA', result.stderr)
        self.assertFalse(self.out.exists())

    def test_tampered_original_resource_stops_consumption(self):
        delivery = self.run / 'delivery'
        shutil.copytree(self.delivery, delivery)
        bundle = json.loads((delivery / 'bundle.json').read_bytes())
        asset = next(a for a in bundle['artifacts'] if a['kind'] == 'SourceBundle')['payload']['assets'][0]
        path = delivery / asset['path']
        path.write_bytes(path.read_bytes() + b'SYNTHETIC_LOCAL_TAMPER')
        result = self.consume(delivery / 'bundle.json')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('RESOURCE_HASH', result.stderr)
        self.assertFalse(self.out.exists())

    def test_source_version_bytes_are_checked_before_import(self):
        source = self.run / 'source'
        shutil.copytree(self.source, source)
        (source / 'src/annotation/__init__.py').write_text('raise AssertionError("must not import")', encoding='utf-8')
        result = self.consume(source=source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('A24_SOURCE_BYTES_CHANGED', result.stderr)
        self.assertFalse(self.out.exists())

    def test_paths_are_parameters_and_not_personal_defaults(self):
        text = TOOL.read_text(encoding='utf-8')
        self.assertNotIn('C:/Users/', text)
        self.assertNotIn('C:\\Users\\', text)
        result = subprocess.run([sys.executable, '-B', str(TOOL), '--help'], cwd=self.run, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--a-source', result.stdout)


if __name__ == '__main__':
    unittest.main()
