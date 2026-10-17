"""Real source/CPU receipt integration; replay must not use OCR or the network."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/book46007447'
sys.path.insert(0, str(ROOT / 'src'))
from annotation.recognition.baseline import digest


class MathReadingCLIRegression(unittest.TestCase):
    def invoke(self, *args):
        # Reject engine imports before loading any project code. Run the real CLI
        # in a fresh interpreter so no cached engine can evade this assertion.
        bootstrap = '''
import builtins,runpy,socket,sys
original_import=builtins.__import__
def guarded_import(name,*args,**kwargs):
    if name.split('.')[0] in {'rapidocr_onnxruntime','onnxruntime','paddleocr','torch'}:
        raise AssertionError('OCR runtime import during cached replay: '+name)
    return original_import(name,*args,**kwargs)
builtins.__import__=guarded_import
def no_network(*args,**kwargs):raise AssertionError('network during cached replay')
socket.socket.connect=no_network
runpy.run_path(sys.argv.pop(1),run_name='__main__')
'''
        return subprocess.run([sys.executable, '-c', bootstrap,
                               str(ROOT / 'tools/replay_math_reading_b.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=30)

    def test_actual_44_cpu_receipts_replay_without_engine_or_network_and_keep_missing_exponent(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'replayed'
            result = self.invoke('--out', out)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
            self.assertTrue(summary['independent_audit_accepted'])
            self.assertEqual((summary['source_roles'], summary['recorded_cpu_passes']), (22, 44))
            self.assertEqual((summary['new_ocr_calls'], summary['platform_actions']), (0, 0))
            self.assertEqual(summary['decision'], 'HOLD')
            self.assertFalse(summary['transcription_verified'])
            reading = json.loads((out / 'math-reading.json').read_text(encoding='utf-8'))['payload']
            last = reading['fractions'][-1]['numerator']
            self.assertEqual(last['consensus_text'], 'a+1')
            self.assertTrue(last['exact_two_pass_agreement'])
            self.assertTrue(last['pixel_risks'])
            self.assertTrue(last['raised_symbol_slots'])
            self.assertFalse(last['transcription_verified'])
            self.assertEqual(last['selected_candidate_refs'], [])
            # New role observations do not rewrite the archived layout omissions.
            layout = json.loads((out / 'math-layout.json').read_text(encoding='utf-8'))['payload']
            self.assertEqual(sum(f[r]['missing_ocr'] for f in layout['fraction_candidates']
                                 for r in ('numerator', 'denominator')), 11)
            self.assertFalse(reading['visual_formula_references_consumed'])
            self.assertFalse(reading['graph_modified'])

    def test_original_cached_receipt_preserved_exactly_and_visual_review_not_consumed(self):
        original = json.loads((FIXTURE / 'math-role-evidence.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'replayed'
            result = self.invoke('--out', out)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(original, json.loads((out / 'math-role-evidence.json').read_text(encoding='utf-8')))
            reading = json.loads((out / 'math-reading.json').read_text(encoding='utf-8'))
            self.assertEqual(reading['payload']['role_evidence_ref']['content_hash'], original['content_hash'])
            self.assertNotIn('observed_text', json.dumps(reading))

    def test_coordinated_receipt_candidate_rewrite_without_raw_change_is_rejected(self):
        evidence = json.loads((FIXTURE / 'math-role-evidence.json').read_text(encoding='utf-8'))
        evidence['payload']['roles'][-2]['variants'][0]['candidates'][0]['text'] = 'a²+1'
        evidence['content_hash'] = digest(evidence['payload'])
        with tempfile.TemporaryDirectory() as directory:
            receipt, out = Path(directory) / 'changed.json', Path(directory) / 'rejected'
            receipt.write_text(json.dumps(evidence, ensure_ascii=False), encoding='utf-8')
            result = self.invoke('--role-evidence', receipt, '--out', out)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(out.exists())

    def test_rehashed_changed_preprocessing_pixels_are_rejected(self):
        evidence = json.loads((FIXTURE / 'math-role-evidence.json').read_text(encoding='utf-8'))
        evidence['payload']['roles'][0]['variants'][0]['transformed_bgr_sha256'] = '0' * 64
        evidence['content_hash'] = digest(evidence['payload'])
        with tempfile.TemporaryDirectory() as directory:
            receipt, out = Path(directory) / 'changed.json', Path(directory) / 'rejected'
            receipt.write_text(json.dumps(evidence), encoding='utf-8')
            result = self.invoke('--role-evidence', receipt, '--out', out)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(out.exists())

    def test_existing_output_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            marker = out / 'keep.txt'
            marker.write_text('existing work', encoding='utf-8')
            result = self.invoke('--out', out)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(encoding='utf-8'), 'existing work')
            self.assertEqual(list(out.iterdir()), [marker])

    def test_explicit_cpu_and_cache_choices_conflict_without_running_ocr(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'not-created'
            result = self.invoke('--recognize', '--role-evidence', FIXTURE / 'math-role-evidence.json', '--out', out)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(out.exists())
            self.assertIn('choose cached evidence or explicit CPU', result.stderr)


if __name__ == '__main__':
    unittest.main()
