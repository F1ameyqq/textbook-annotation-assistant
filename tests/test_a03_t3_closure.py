"""M evidence assertions plus opt-in eight R1 contract controls without SQL.

Set A03_M_EVIDENCE to the completed new batch directory. Assertions inspect
retained immutable-copy SQL rows produced by the accepted capture module.
"""
import json
import os
from pathlib import Path
import unittest
import copy
from dataclasses import replace
import hashlib
import shutil
import sys


class MValidationR1Controls(unittest.TestCase):
    """Eight named contract deltas; genuine registry, no DB/target/dispatch."""
    @classmethod
    def setUpClass(cls):
        from annotation.contracts.a03_native import validate_native_bundle
        from annotation.runtime.storage.native import NativeRegistry, NativeRuntimeStore
        cls.output = Path(os.environ['A03_R1_CONTROLS']).resolve()
        cls.output.mkdir(exist_ok=False)
        cls.fixture = Path(__file__).resolve().parents[1]/'examples/a03/T3-closure/inputs/single'
        cls.store = NativeRuntimeStore.__new__(NativeRuntimeStore)
        cls.store.native_registry = NativeRegistry(cls.store)
        cls.rows = []
        cls.goodroot = cls.output/'qualified'
        shutil.copytree(cls.fixture,cls.goodroot)
        cls.good = json.loads((cls.goodroot/'initial.json').read_bytes())
        new = cls.store._validate(cls.good,asset_root=cls.goodroot)
        oldctx = cls.store.bridge_for(cls.good,cls.goodroot)
        old = validate_native_bundle(cls.good,bridge_context=oldctx,asset_root=cls.goodroot)
        assert new.model_dump()==old.model_dump()
        assert new.bridge_context.resource_manifest==oldctx.resource_manifest
        assert new.bridge_context.canonical_sha256==oldctx.canonical_sha256
        assert new.bridge_context.asset_root==oldctx.asset_root==cls.goodroot.resolve()
        assert new.bridge_context._registry is cls.store.native_registry
        cls.positive = {'data_manifest_digest_root_registry':'MATCH_OLD_STRICT_ENTRY',
            'root_registered':cls.goodroot.resolve() in cls.store.native_registry.roots,
            'new_context_is_fresh':new.bridge_context is not oldctx}

    @classmethod
    def tearDownClass(cls):
        from annotation.contracts import a03_native
        data={'positive':cls.positive,'controls':cls.rows,'target_starts':0,'dispatch':0,
            'sqlite_connections':0,'product_module':str(Path(a03_native.__file__).resolve()),
            'product_sha256':hashlib.sha256(Path(a03_native.__file__).read_bytes()).hexdigest()}
        with(cls.output/'results.json').open('xb')as f:
            f.write((json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode())

    def setUp(self):
        self.case=self.output/self._testMethodName
        shutil.copytree(self.fixture,self.case)
        self.value=json.loads((self.case/'initial.json').read_bytes())

    def reject(self, label, code, call):
        from annotation.contracts import ContractError
        with self.assertRaises(ContractError)as raised:
            call()
        actual=raised.exception.issues[0]
        self.rows.append({'control':self._testMethodName,'assertion':label,'expected':code,'actual':actual})
        self.assertEqual(code,actual['code'])

    def private(self,value=None,root=None):
        return self.store._validate(self.value if value is None else value,asset_root=root or self.case)

    def reseal(self,a):
        from annotation.contracts.a03_bridge._json import digest
        a['content_hash']=digest({k:v for k,v in a.items()if k!='content_hash'})

    def nested(self,missing=False):
        from annotation.contracts import artifact_ref
        graph=next(a for a in self.value['artifacts']if a['kind']=='QuestionGraph')
        snapshot=self.value['artifacts'][-1]
        ref=artifact_ref(graph)
        if missing:ref=dict(ref,artifact_id='missing-formal-graph')
        raw=(json.dumps({'nested_ref':ref},sort_keys=True)+'\n').encode()
        (self.case/'assets/inner.json').write_bytes(raw)
        resource={'path':'assets/inner.json','sha256':hashlib.sha256(raw).hexdigest(),
            'media_type':'application/json','origin':'SYNTHETIC'}
        self.value['evidence'].append({'evidence_id':'nested-r1','resource':resource,
            'description':'Existing nested-reference control adapted to native input','mode':'SYNTHETIC'})
        snapshot['payload']['evidence_refs'].append('nested-r1')
        snapshot['input_refs'].append(artifact_ref(graph))
        self.reseal(snapshot)
        return snapshot,graph

    def test_01_missing_nested_formal_reference(self):
        self.nested(missing=True)
        self.reject('new_private_nested_closure','EXACT_REF',self.private)

    def test_02_second_consumer_cannot_borrow_declaration(self):
        from annotation.contracts import artifact_ref
        snapshot,graph=self.nested()
        self.private()  # First consumer is actually qualified before cloning.
        second=copy.deepcopy(snapshot);second['artifact_id']='second-consumer-r1'
        second['input_refs'].remove(artifact_ref(graph));self.reseal(second)
        self.value['artifacts'].append(second)
        self.reject('new_private_each_consumer','UNDECLARED_REFERENCE',self.private)

    def test_03_wrong_book(self):
        self.value['artifacts'][-1]['book_id']='foreign-book-r1'
        self.reseal(self.value['artifacts'][-1])
        self.reject('new_private_book','FOREIGN_BOOK',self.private)

    def test_04_wrong_scope(self):
        self.value['artifacts'][-1]['scope_id']='foreign-scope-r1'
        self.reseal(self.value['artifacts'][-1])
        self.reject('new_private_scope','ORDINARY_SCOPE',self.private)

    def test_05_resource_bytes_change_after_success(self):
        from annotation.contracts.a03_native import validate_native_bundle
        self.nested();good=self.private();file=self.case/'assets/inner.json';raw=file.read_bytes()
        try:
            file.write_bytes(b'{}\n')
            self.reject('new_private_rereads_bytes','RESOURCE_HASH',lambda:self.private(good))
            self.reject('old_context_public_rereads_bytes','RESOURCE_HASH',lambda:validate_native_bundle(
                good,bridge_context=good.bridge_context,asset_root=self.case))
        finally:file.write_bytes(raw)

    def test_06_implementation_bytes_change_after_success(self):
        from annotation.contracts import a03_native
        good=self.private();file=Path(a03_native.__file__).resolve()
        assert Path(os.environ['A03_R1_DISPOSABLE']).resolve() in file.parents
        raw=file.read_bytes()
        try:
            file.write_bytes(raw+b'\n# disposable pin negative\n')
            self.reject('new_private_current_pins','NATIVE_IMPLEMENTATION_PIN',self.private)
            self.reject('old_context_public_current_pins','NATIVE_IMPLEMENTATION_PIN',lambda:a03_native.validate_native_bundle(
                good,bridge_context=good.bridge_context,asset_root=self.case))
        finally:file.write_bytes(raw)

    def test_07_wrong_root(self):
        wrong=self.case/'empty-root';wrong.mkdir()
        self.reject('new_private_actual_root_resources','RESOURCE_READ',lambda:self.private(root=wrong))

    def test_08_unregistered_registry_and_context(self):
        from annotation.contracts import a03_native
        from annotation.runtime.storage.native import NativeRegistry
        fake=NativeRegistry.__new__(NativeRegistry)
        self.reject('new_private_unregistered_registry','NATIVE_REGISTRY_REQUIRED',lambda:
            a03_native._validate_native_for_registry(fake,self.value,self.case))
        good=self.private();fake_context=replace(good.bridge_context)
        self.reject('public_unregistered_context','NATIVE_CONTEXT_REQUIRED',lambda:
            a03_native.validate_native_bundle(good,bridge_context=fake_context,asset_root=self.case))


class MRetainedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(os.environ['A03_M_EVIDENCE']).resolve()

    def load(self, case, relative):
        return json.loads((self.root / 'cases' / case / relative).read_bytes())

    def final(self, case):
        sql = self.load(case, 'captures/after-release-finish/SQL.json')
        return sql['runtime']['tables'], sql['target']['tables']

    def common(self, case, action_count, dispatch_count, report_reads):
        runtime, target = self.final(case)
        self.assertEqual(action_count, len(runtime['actions']))
        self.assertEqual(dispatch_count, len(target['effects']))
        self.assertEqual(report_reads, len(runtime['native_report_reads']))
        self.assertTrue(all(b['owner'] is None and b['phase']=='RELEASED' and b['lease']==0 for b in runtime['books']))
        for phase in ('execute','finish'):
            result = self.load(case,'processes/'+phase+'/completed.json')
            self.assertEqual(0,result['exit_code']); self.assertFalse(result['timeout']); self.assertFalse(result['alive'])
        for artifact in self.load(case,'phase-finish-result.json')['artifacts']:
            if artifact['kind']=='BatchReport':
                self.assertEqual('PENDING',artifact['payload']['content_check_status'])
                self.assertEqual('NOT_SUBMITTED',artifact['payload']['submission_status'])
        return runtime,target

    def test_M1_three_actions_durable_reports_and_replay(self):
        r,t=self.common('M1',3,3,1)
        self.assertEqual(['APPLIED']*3,[a['state'] for a in r['actions']])
        self.assertEqual(3,len(r['intents'])); self.assertEqual(3,len(r['permits']))
        self.assertEqual('REPLAY_FORBIDDEN',self.load('M1','replay-refusal.json')['code'])
        state=json.loads(next(x['value'] for x in t['meta'] if x['key']=='state'))
        self.assertEqual(3,len(state['target']['questions'])); self.assertEqual(6,len(state['target']['frames']))

    def test_M2_sufficient_three_reads_no_tail_intent(self):
        r,t=self.common('M2-sufficient',3,2,0)
        self.assertEqual(['APPLIED','UNKNOWN','NOT_APPLIED'],[a['state'] for a in r['actions']])
        self.assertIsNone(r['actions'][2]['intent']); self.assertIsNotNone(r['actions'][2]['fact'])
        self.assertEqual(2,len(r['intents'])); self.assertEqual(2,len(r['permits']))
        self.assertEqual([1,2,3],[x['ordinal'] for x in r['native_readonly_reads']])
        self.assertEqual(3,r['native_readonly_entries'][0]['used_count'])
        self.assertEqual('COMMITTED',r['native_readonly_entries'][0]['state'])
        artifacts=self.load('M2-sufficient','phase-finish-result.json')['artifacts']
        receipts=[a for a in artifacts if a['kind']=='ExecutionReceipt']
        self.assertEqual(1,len(receipts)); self.assertEqual('NOT_ATTEMPTED',receipts[0]['payload']['results'][2]['attempt_fact'])
        self.assertTrue(self.load('M2-sufficient','phase-finish-result.json')['status']['paused'])

    def test_M2_insufficient_progress_and_consumed_entry(self):
        r,t=self.common('M2-insufficient',3,2,0)
        self.assertEqual(['APPLIED','UNKNOWN','RESERVED'],[a['state'] for a in r['actions']])
        self.assertIsNone(r['actions'][2]['intent']); self.assertIsNone(r['actions'][2]['fact'])
        self.assertEqual('ABORTED',r['native_readonly_entries'][0]['state'])
        self.assertEqual(2,r['native_readonly_entries'][0]['used_count'])
        self.assertEqual('READONLY_ENTRY_CONSUMED',self.load('M2-insufficient','entry-reopen-refusal.json')['code'])
        artifacts=self.load('M2-insufficient','phase-finish-result.json')['artifacts']
        self.assertFalse(any(a['kind'] in ('ExecutionReceipt','BatchReport') for a in artifacts))
        self.assertTrue(self.load('M2-insufficient','phase-finish-result.json')['status']['paused'])

    def test_M3_new_initial_after_readonly_candidate_clear(self):
        r,t=self.common('M3-new-plan',2,2,1)
        self.assertEqual(['NOT_APPLIED','APPLIED'],[a['state'] for a in r['actions']])
        self.assertIsNotNone(r['native_hold_candidates'][0]['cleared_event'])
        artifacts=self.load('M3-new-plan','phase-finish-result.json')['artifacts']
        plans=[a for a in artifacts if a['kind']=='ApplyPlan']
        self.assertEqual(3,len(plans)); self.assertEqual(2,len(r['plans']))
        candidate=self.load('M3-new-plan','hold-candidate.json')
        fresh=self.load('M3-new-plan','new-plan.json')
        self.assertNotEqual(candidate['payload']['precheck'],fresh['payload']['precheck'])
        self.assertFalse(any(json.loads(p['ref'])['artifact_id']==candidate['artifact_id'] for p in r['plans']))
        self.assertIsNone(r['books'][0]['hold'])

    def test_M3_final_drift_preserves_hold_no_new_dispatch(self):
        r,t=self.common('M3-final-drift',1,1,0)
        self.assertEqual('TARGET_CHANGED',self.load('M3-final-drift','final-drift-refusal.json')['code'])
        self.assertIsNotNone(r['books'][0]['hold']); self.assertIsNone(r['native_hold_candidates'][0]['cleared_event'])
        self.assertEqual(1,len(r['plans'])); self.assertEqual(1,len(r['intents']))
        self.assertFalse((self.root/'cases/M3-final-drift/new-execution.json').exists())


if __name__=='__main__':
    if '--validation-controls' in sys.argv:
        sys.argv.remove('--validation-controls')
        unittest.main(defaultTest='MValidationR1Controls')
    else:
        unittest.main(defaultTest='MRetainedEvidenceTests')
