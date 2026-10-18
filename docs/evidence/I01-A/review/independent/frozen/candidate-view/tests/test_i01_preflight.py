"""Static composition checks only: no runtime, DB, target or business dispatch."""
import hashlib
import inspect
import json
import os
from pathlib import Path
import unittest

ROOT = Path(os.environ['I01_PROJECT'])
VIEW = ROOT/'docs/evidence/I01-A/execution/preparation/raw-view'


def read(path): return json.loads(path.read_bytes())
def sha(raw): return hashlib.sha256(raw).hexdigest()
def digest(value): return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8'))


class StaticComposition(unittest.TestCase):
    def test_all_thirty_pins_and_normal_imports(self):
        from annotation.contracts.a03_native import select_native_codec
        from annotation.runtime.recovery import run_plan, reconcile, publish_quality
        from annotation.runtime.storage.native import NativeRuntimeStore, init_native_state, open_native_state
        from annotation.runtime.storage.native_target import NativeTargetSession
        from annotation.quality.synthetic_precheck import produce_a03_pre_run, admit_a03_pre_run
        from annotation.quality.targetcheck import check_target
        from annotation.delivery.planner import create_plan
        selected=select_native_codec()
        self.assertEqual(len(selected.implementation_pins),30)
        self.assertEqual(selected.artifact_version,'1.4.0-a03-native-proposal')
        self.assertIn('max_attempts',inspect.signature(reconcile).parameters)
        self.assertIn('read_fault',inspect.signature(run_plan).parameters)
        self.assertTrue(callable(NativeTargetSession.synthetic_external_add_directory))
        self.assertIn('observer',inspect.signature(NativeRuntimeStore.begin_native_pre).parameters)

    def test_derived_inputs_closed_references_and_resources(self):
        identities=[]
        for tag in ('N','E','U'):
            folder=ROOT/'tests/fixtures/i01'/tag
            data=read(folder/'initial.json'); byid={a['artifact_id']:a for a in data['artifacts']}
            self.assertEqual(data['format_version'],'a03-exchange-4-proposal')
            def walk(value):
                if isinstance(value,dict):
                    if {'path','sha256','media_type'} <= set(value): self.assertEqual(sha((folder/value['path']).read_bytes()),value['sha256'])
                    if set(value)=={'artifact_id','revision','kind','content_hash'}:
                        self.assertEqual(value,{k:byid[value['artifact_id']][k] for k in value})
                    for item in value.values(): walk(item)
                elif isinstance(value,list):
                    for item in value: walk(item)
            walk(data)
            for a in data['artifacts']:
                self.assertEqual(a['content_hash'],digest({k:v for k,v in a.items() if k!='content_hash'}))
                self.assertEqual(a['producer']['evidence_mode'],'SYNTHETIC')
            source,evidence,graph,snap=data['artifacts']
            self.assertEqual(len(source['payload']['assets']),1)
            self.assertEqual(len(graph['payload']['questions']),1)
            self.assertEqual([f['role'] for f in graph['payload']['fragments']],['stem','answer'])
            self.assertEqual(len(evidence['payload']['regions']),2)
            self.assertEqual(read(folder/'assets/inventory.json')['book_id'],source['book_id'])
            identities.append((source['book_id'],source['scope_id'],snap['payload']['target_id']))
            self.assertEqual((folder/'assets/page-1.pgm').read_bytes(),(VIEW/'examples/a03/T3-closure/inputs/single/assets/page-1.pgm').read_bytes())
        for index in range(3): self.assertEqual(len({v[index] for v in identities}),3)

    def test_a01_copy_entire_raw_git_package(self):
        origin=VIEW/'examples/a01/R3/bundles/46007447'
        copy=ROOT/'tests/fixtures/i01/source-copy'
        originals={p.relative_to(origin).as_posix():sha(p.read_bytes()) for p in origin.rglob('*') if p.is_file()}
        copies={p.relative_to(copy).as_posix():sha(p.read_bytes()) for p in copy.rglob('*') if p.is_file()}
        self.assertEqual(originals,copies)
        self.assertFalse(read(copy/'limitations.json')['coverage_eligible'])
        self.assertEqual(read(copy/'exchange.json')['artifacts'][0]['book_id'],'46007447')


if __name__=='__main__': unittest.main(verbosity=2)
