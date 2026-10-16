"""Local graph application/rollback CLI integration, without network or OCR."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def command(arguments):
    # Prohibit hidden site or OCR work in a fresh interpreter. The graph pipeline
    # must replay only retained source evidence and local image captures.
    bootstrap=("import builtins,runpy,sys,socket; original=builtins.__import__; "
               "\ndef guarded(name,*a,**k):\n"
               " if name.split('.')[0] in {'rapidocr_onnxruntime','onnxruntime'}: raise RuntimeError('OCR forbidden')\n"
               " return original(name,*a,**k)\n"
               "builtins.__import__=guarded\n"
               "def blocked(*a,**k): raise RuntimeError('network forbidden')\n"
               "socket.socket.connect=blocked\n"
               "sys.argv=['replay_apply_b.py']+sys.argv[1:]\n"
               f"runpy.run_path({str(ROOT/'tools/replay_apply_b.py')!r},run_name='__main__')")
    return [sys.executable,'-c',bootstrap,*arguments]


def invoke(arguments):
    return subprocess.run(command(arguments),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=False)


class LocalContinuationCommand(unittest.TestCase):
    def test_fresh_process_applies_and_restores_using_saved_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            applied=Path(temporary)/'applied'; restored=Path(temporary)/'restored'
            first=invoke(['--out',str(applied)])
            self.assertEqual(first.returncode,0,first.stdout+first.stderr)
            summary=json.loads(first.stdout)
            self.assertEqual(summary['schema'],'b-graph-trial/0.4')
            self.assertTrue(summary['independent_audit_accepted'])
            self.assertTrue(summary['rollback_verified'])
            self.assertEqual((summary['source_trace_fragments'],summary['render_regions']),(33,15))
            self.assertEqual(summary['platform_actions'],0)
            self.assertFalse(summary['business_acceptance'])
            self.assertFalse(summary['ocr_rerun'])
            second=invoke(['--rollback-from',str(applied/'question-graph.json'),
                           '--evidence',str(applied/'evidence.json'),'--receipt',str(applied/'application-receipt.json'),
                           '--out',str(restored)])
            self.assertEqual(second.returncode,0,second.stdout+second.stderr)
            base=json.loads((applied/'base-question-graph.json').read_text(encoding='utf-8'))
            rolled_back=json.loads((restored/'question-graph.json').read_text(encoding='utf-8'))
            self.assertEqual(rolled_back,base)

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)/'existing';out.mkdir()
            sentinel=out/'keep.txt';sentinel.write_text('keep',encoding='utf-8')
            result=invoke(['--out',str(out)])
            self.assertNotEqual(result.returncode,0)
            self.assertIn('new directory',result.stderr)
            self.assertEqual({p.name for p in out.iterdir()},{'keep.txt'})
            self.assertEqual(sentinel.read_text(encoding='utf-8'),'keep')

    def test_rollback_requires_separately_saved_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)/'must-not-exist'
            result=invoke(['--rollback-from','unused.json','--evidence','unused-evidence.json','--out',str(out)])
            self.assertNotEqual(result.returncode,0)
            self.assertIn('--receipt',result.stderr)
            self.assertFalse(out.exists())

    def test_later_graph_edit_cannot_be_silently_erased(self):
        with tempfile.TemporaryDirectory() as temporary:
            applied=Path(temporary)/'applied'; restored=Path(temporary)/'restored'
            first=invoke(['--out',str(applied)])
            self.assertEqual(first.returncode,0,first.stderr)
            path=applied/'question-graph.json'
            graph=json.loads(path.read_text(encoding='utf-8'))
            graph['payload']['new_review_note']='A later local edit must not be discarded by rollback.'
            sys.path.insert(0,str(ROOT/'src'))
            from annotation.recognition.baseline import digest
            graph['content_hash']=digest(graph['payload'])
            graph['rollback_guard']['expected_payload_hash']=graph['content_hash']
            path.write_text(json.dumps(graph,ensure_ascii=False,indent=2),encoding='utf-8')
            edited=path.read_bytes()
            result=invoke(['--rollback-from',str(path),'--evidence',str(applied/'evidence.json'),
                           '--receipt',str(applied/'application-receipt.json'),'--out',str(restored)])
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(restored.exists())
            self.assertEqual(path.read_bytes(),edited)


if __name__=='__main__':unittest.main()
