import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('b_replay', Path(__file__).resolve().parents[1] / 'tools/replay_lesson_c01_b.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


class ReplayClosureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'asset').write_bytes(b'original')
        self.manifest = {'members': [{'path': 'asset', 'bytes': 8, 'sha256': hashlib.sha256(b'original').hexdigest()}]}
        self.save()

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def test_complete_member_set_passes(self):
        self.assertEqual(replay.verify_manifest(self.root), 1)

    def test_extra_unlisted_file_rejected(self):
        (self.root / 'unlisted').write_bytes(b'x')
        with self.assertRaisesRegex(ValueError, 'MEMBER_SET'):
            replay.verify_manifest(self.root)

    def test_changed_same_length_bytes_rejected(self):
        (self.root / 'asset').write_bytes(b'changed!')
        with self.assertRaisesRegex(ValueError, 'MEMBER_CHANGED'):
            replay.verify_manifest(self.root)

    def test_path_escape_and_duplicate_members_rejected(self):
        for name in ('../asset', '/asset', 'C:/asset', 'a\\asset', 'a//asset'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'UNSAFE_MEMBER'):
                replay.safe_member(name)
        self.manifest['members'].append(self.manifest['members'][0])
        self.save()
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_MANIFEST'):
            replay.verify_manifest(self.root)


if __name__ == '__main__':
    unittest.main()
