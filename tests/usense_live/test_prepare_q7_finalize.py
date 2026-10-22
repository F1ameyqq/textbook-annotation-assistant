import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('prepare_q7_finalize_tool', ROOT / 'tools/prepare_q7_finalize.py')
entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entry)


class PrepareFinalizeTests(unittest.TestCase):
    def inputs(self, root):
        refs = {name: {'path': str(root / (name + '.json')), 'sha256': 'a' * 64}
                for name in ('plan', 'receipt', 'comparison', 'outer_acceptance')}
        file = root / 'refs.json'
        file.write_text(json.dumps(refs), encoding='utf-8')
        out = root / 'generated-plan.json'
        args = ['--baseline', str(root / 'after23'), '--candidate', str(root / 'main-candidate.json'),
                '--crop-proof', str(root / 'crop-proof.json'), '--visual-review', str(root / 'review.json'),
                '--predecessor-refs', str(file), '--out', str(out)]
        return refs, file, out, args

    def invoke(self, args, materialize):
        fake = types.ModuleType('annotation.runtime.usense_live.finalize_files')
        fake.materialize_main = materialize
        output = io.StringIO()
        with patch.dict(sys.modules, {'annotation.runtime.usense_live.finalize_files': fake}), contextlib.redirect_stdout(output):
            result = entry.main(args)
        return result, output.getvalue()

    def test_passes_only_four_refs_to_frozen_materializer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); refs, _, out, args = self.inputs(root)
            plan = {'plan_sha256': 'b' * 64, 'ledger_key': 'fixed-once', 'question': '第7题', 'unknown': None}
            materialize = Mock(return_value=plan)
            code, printed = self.invoke(args, materialize)
            self.assertEqual(code, 0)
            materialize.assert_called_once_with(str(root / 'main-candidate.json'), str(root / 'crop-proof.json'),
                str(root / 'review.json'), str(root / 'after23'), refs)
            self.assertEqual(json.loads(out.read_bytes()), plan)
            record = json.loads(printed)
            self.assertEqual(record['platform_requests'], 0)
            self.assertFalse(record['outer_acceptance_created'])
            self.assertFalse(record['prior_unknown_rewritten'])

    def test_rejects_embedded_or_incomplete_predecessor_without_materializing(self):
        for mode in ('missing', 'embedded'):
            with tempfile.TemporaryDirectory() as d:
                root = Path(d); refs, file, out, args = self.inputs(root)
                if mode == 'missing':refs.pop('outer_acceptance')
                else:refs['observed_resolution'] = {'status': 'invented'}
                file.write_text(json.dumps(refs), encoding='utf-8')
                materialize = Mock()
                with self.assertRaises(ValueError):self.invoke(args, materialize)
                materialize.assert_not_called(); self.assertFalse(out.exists())

    def test_rejects_relative_ref_and_bad_digest_before_materializing(self):
        for field, value in (('path', 'relative.json'), ('sha256', 'not-a-hash')):
            with tempfile.TemporaryDirectory() as d:
                root = Path(d); refs, file, out, args = self.inputs(root)
                refs['receipt'][field] = value; file.write_text(json.dumps(refs), encoding='utf-8')
                materialize = Mock()
                with self.assertRaises(ValueError):self.invoke(args, materialize)
                materialize.assert_not_called(); self.assertFalse(out.exists())

    def test_existing_plan_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); _, _, out, args = self.inputs(root)
            original = b'original immutable plan'; out.write_bytes(original)
            materialize = Mock(return_value={'plan_sha256': 'b' * 64, 'ledger_key': 'fixed-once'})
            with self.assertRaises(FileExistsError):self.invoke(args, materialize)
            self.assertEqual(out.read_bytes(), original)

    def test_failed_predecessor_evidence_creates_no_plan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); _, _, out, args = self.inputs(root)
            materialize = Mock(side_effect=ValueError('AUDIT_MANIFEST_NOT_VERIFIED'))
            with self.assertRaisesRegex(ValueError, 'AUDIT_MANIFEST_NOT_VERIFIED'):
                self.invoke(args, materialize)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
