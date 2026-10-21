"""Real frozen A consumer + source/content mutation regressions, no website/model."""
from pathlib import Path
import copy,hashlib,importlib.util,json,subprocess,sys,tempfile,unittest,zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import export_q16_reading_b as producer
import verify_q16_reading_b as consumer

class DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.basis,cls.images=producer.load_basis();cls.review=producer.read_review(ROOT/producer.REVIEW_PATH)
        cls.blobs=producer.build_delivery(cls.basis,cls.review,cls.images)
        cls.a_tmp=tempfile.TemporaryDirectory();cls.a_root=Path(cls.a_tmp.name)
        archive=ROOT/'handoffs/b/46007447/B-46007447-A08-A09-Q4-B-adoption-2026-10-19.zip'
        if producer.sha(archive.read_bytes())!='6a0ead03c95299049c5f113a1de647ef6c28f72703430b80451ccb93775c535b':raise ValueError('A_FIXED_ARCHIVE')
        pins=json.loads((ROOT/'tests/fixtures/book46007447/a08-c01-consumer-pins-20261021.json').read_bytes())
        with zipfile.ZipFile(archive) as z:
            for m in pins['members']:
                path=cls.a_root/m['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read('fixed-source/'+m['path']))

    @classmethod
    def tearDownClass(cls):cls.a_tmp.cleanup()

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.folder=self.root/'delivery'
        producer.write_delivery(self.folder,self.blobs)

    def tearDown(self):self.tmp.cleanup()

    def json_mutate(self,name,mutation):
        path=self.folder/name;value=json.loads(path.read_bytes());mutation(value);path.write_bytes(producer.encode(value))

    def a_run(self):
        return subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/consume_q16_reading_a.py'),
            '--a-source',str(self.a_root),'--pins',str(ROOT/'tests/fixtures/book46007447/a08-c01-consumer-pins-20261021.json'),
            '--delivery',str(self.folder),'--out',str(self.root/'receipt.json')],capture_output=True,text=True,encoding='utf-8')

    def test_actual_a_reads_all_four_and_full_content_is_lossless(self):
        result=self.a_run();self.assertEqual(result.returncode,0,result.stderr)
        receipt=json.loads((self.root/'receipt.json').read_bytes())
        self.assertEqual(receipt['content_audit']['regions'],37);self.assertEqual(len(receipt['readback']),4)
        self.assertTrue(receipt['producer_vs_consumer_full_object_equal']);self.assertFalse(receipt['planning_or_simulation_executed'])
        self.assertEqual(receipt['decision'],'HOLD')

    def test_source_bound_review_preserves_null_blanks_and_unknown_chapter(self):
        audit=consumer.verify(self.folder);self.assertEqual(audit['unfilled_question_blanks'],6)
        self.assertEqual(audit['independent_human_pending'],18)
        self.assertIsNone(json.loads((self.folder/'delivery.json').read_bytes())['chapter_denominator'])

    def test_resigned_wrong_formula_cannot_pass_source_readback(self):
        def change(b):
            ev=next(a for a in b['artifacts'] if a['kind']=='EvidenceBundle')
            region=next(r for r in ev['payload']['regions'] if r['region_id']=='region-q16-F9')
            region['text']=region['text'].replace('+1','-1')
            ev.update(producer.seal(ev))
        self.json_mutate('bundle.json',change)
        with self.assertRaisesRegex(ValueError,'SOURCE_TRANSCRIPTION_READBACK'):consumer.verify(self.folder)

    def test_same_formula_at_another_pixel_position_is_rejected(self):
        def change(d):d['q16_formula_slots'][9]['source_bbox']=d['q16_formula_slots'][7]['source_bbox']
        self.json_mutate('delivery.json',change)
        with self.assertRaisesRegex(ValueError,'Q16_SOURCE_SPANS'):consumer.verify(self.folder)

    def test_reading_two_three_answer_swap_is_rejected_even_resigned(self):
        def change(b):
            g=next(a for a in b['artifacts'] if a['kind']=='QuestionGraph');rels=g['payload']['answer_relations']
            rels[2]['candidate_fragment_ids'],rels[3]['candidate_fragment_ids']=rels[3]['candidate_fragment_ids'],rels[2]['candidate_fragment_ids']
            g.update(producer.seal(g));d=json.loads((self.folder/'delivery.json').read_bytes());d['c01_graph_ref']=producer.ref(g)
            pending=json.loads((self.folder/'pending-review.json').read_bytes());pending['c01_graph_ref']=producer.ref(g)
            (self.folder/'pending-review.json').write_bytes(producer.encode(pending));d['pending_review_sha256']=producer.sha(producer.encode(pending))
            (self.folder/'delivery.json').write_bytes(producer.encode(d))
        self.json_mutate('bundle.json',change)
        with self.assertRaisesRegex(ValueError,'ANSWER_TASK_PAIRING'):consumer.verify(self.folder)

    def test_missing_whole_answer_diagram_is_rejected(self):
        self.json_mutate('bundle.json',lambda b:next(a for a in b['artifacts'] if a['kind']=='EvidenceBundle')['payload']['regions'].pop(25))
        with self.assertRaises(ValueError):consumer.verify(self.folder)

    def test_same_size_wrong_asset_bytes_rejected_by_actual_a(self):
        path=self.folder/'assets/viewer-173.jpg';raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        result=self.a_run();self.assertNotEqual(result.returncode,0);self.assertIn('RESOURCE_HASH',result.stderr)

    def test_stale_graph_reference_rejected_by_actual_a(self):
        self.json_mutate('bundle.json',lambda b:b['artifacts'][-1]['payload']['graph'].update(content_hash='0'*64))
        result=self.a_run();self.assertNotEqual(result.returncode,0)

    def test_integer_coordinate_hash_regression_detected_by_actual_a(self):
        def change(b):
            ev=next(a for a in b['artifacts'] if a['kind']=='EvidenceBundle')
            ev['payload']['regions'][0]['box']['bbox']=[int(x) for x in ev['payload']['regions'][0]['box']['bbox']]
            ev.update(producer.seal(ev))
        self.json_mutate('bundle.json',change)
        result=self.a_run();self.assertNotEqual(result.returncode,0);self.assertIn('HASH_MISMATCH',result.stderr)

    def test_filled_question_blank_cannot_hide_in_sidecar(self):
        def change(d):next(r for b in d['bindings'] for r in b['runs'] if r['format']=='blank')['value']='60'
        self.json_mutate('delivery.json',change)
        with self.assertRaises(ValueError):consumer.verify(self.folder)

    def test_fake_human_approval_and_scope_promotion_rejected(self):
        self.json_mutate('delivery.json',lambda d:d.update(human_verified=True,chapter_denominator=4))
        with self.assertRaisesRegex(ValueError,'NO_SCOPE_PROMOTION'):consumer.verify(self.folder)

    def test_edited_review_cannot_be_resigned_into_current_content(self):
        self.json_mutate('current-review.json',lambda d:d['reading']['tasks'].reverse())
        with self.assertRaisesRegex(ValueError,'FIXED_SOURCE_REVIEW'):consumer.verify(self.folder)

    def test_reading_task_one_missing_expansion_formula_is_rejected(self):
        def change(b):
            ev=next(a for a in b['artifacts'] if a['kind']=='EvidenceBundle')
            r=next(r for r in ev['payload']['regions'] if r['region_id']=='region-reading-task1-right')
            r['text']=r['text'].replace(r'c^2=4\times\frac{1}{2}ab+(a-b)^2=2ab+a^2-2ab+b^2','')
            ev.update(producer.seal(ev))
        self.json_mutate('bundle.json',change)
        with self.assertRaisesRegex(ValueError,'SOURCE_TRANSCRIPTION_READBACK'):consumer.verify(self.folder)

    def test_independent_queue_cannot_claim_human_acceptance_after_resign(self):
        self.json_mutate('pending-review.json',lambda q:q['items'][0].update(human_disposition='APPROVED'))
        self.json_mutate('delivery.json',lambda d:d.update(pending_review_sha256=producer.sha((self.folder/'pending-review.json').read_bytes())))
        with self.assertRaisesRegex(ValueError,'INDEPENDENT_REVIEW_BINDING'):consumer.verify(self.folder)

    def test_resigned_review_subject_must_still_match_current_content(self):
        def change(q):
            q['items'][9]['subject']['expected_latex']=r'\frac{a^{2}-1}{2}'
            q['items'][9]['subject_sha256']=producer.sha(producer.canonical(q['items'][9]['subject']))
        self.json_mutate('pending-review.json',change)
        self.json_mutate('delivery.json',lambda d:d.update(pending_review_sha256=producer.sha((self.folder/'pending-review.json').read_bytes())))
        with self.assertRaisesRegex(ValueError,'INDEPENDENT_REVIEW_BINDING'):consumer.verify(self.folder)

    def test_extra_valid_source_rejected_by_actual_readonly_harness(self):
        def change(b):
            extra=copy.deepcopy(b['artifacts'][0]);extra['artifact_id']+='-unreviewed'
            b['artifacts'].append(producer.seal(extra))
        self.json_mutate('bundle.json',change)
        result=self.a_run();self.assertNotEqual(result.returncode,0);self.assertIn('READONLY_ARTIFACTS',result.stderr)

    def test_unreviewed_policy_and_evidence_rejected_by_actual_readonly_harness(self):
        for key in ('policies','evidence'):
            with self.subTest(extra=key):
                bundle=json.loads(self.blobs['bundle.json']);extra=copy.deepcopy(bundle[key][0])
                if key=='policies':
                    extra['policy_id']+='-unreviewed';extra=producer.seal(extra)
                else:extra['evidence_id']+='-unreviewed'
                bundle[key].append(extra);(self.folder/'bundle.json').write_bytes(producer.encode(bundle))
                result=self.a_run();self.assertNotEqual(result.returncode,0);self.assertIn('READONLY_ARTIFACTS',result.stderr)

    def test_generation_timestamp_and_immutable_run_are_bound(self):
        generation=json.loads(self.blobs['generation.json']);other=copy.deepcopy(generation)
        other['created_at']='2026-10-21T23:59:59+00:00'
        rebuilt=producer.build_delivery(self.basis,self.review,self.images,generation)
        changed=producer.build_delivery(self.basis,self.review,self.images,other)
        self.assertEqual(rebuilt,self.blobs)
        before=json.loads(rebuilt['bundle.json']);after=json.loads(changed['bundle.json'])
        self.assertNotEqual(before['artifacts'][0]['run_id'],after['artifacts'][0]['run_id'])
        self.assertNotEqual(before['artifacts'][2]['artifact_id'],after['artifacts'][2]['artifact_id'])
        self.assertEqual(before['artifacts'][2]['payload']['questions'],after['artifacts'][2]['payload']['questions'])

    def test_resigned_false_created_at_rejected(self):
        def change(b):
            b['artifacts'][0]['created_at']='2026-10-21T00:00:00+08:00'
            b['artifacts'][0]=producer.seal(b['artifacts'][0])
        self.json_mutate('bundle.json',change)
        with self.assertRaisesRegex(ValueError,'IMMUTABLE_GENERATION_IDENTITIES'):consumer.verify(self.folder)

    def test_swapped_reading_order_rejected_even_with_new_graph_digest(self):
        def change(b):
            graph=next(a for a in b['artifacts'] if a['kind']=='QuestionGraph');f=graph['payload']['fragments']
            f[0]['reading_order'],f[1]['reading_order']=f[1]['reading_order'],f[0]['reading_order']
            graph.update(producer.seal(graph));d=json.loads((self.folder/'delivery.json').read_bytes());d['c01_graph_ref']=producer.ref(graph)
            pending=json.loads((self.folder/'pending-review.json').read_bytes());pending['c01_graph_ref']=producer.ref(graph)
            (self.folder/'pending-review.json').write_bytes(producer.encode(pending));d['pending_review_sha256']=producer.sha(producer.encode(pending))
            (self.folder/'delivery.json').write_bytes(producer.encode(d))
        self.json_mutate('bundle.json',change)
        with self.assertRaisesRegex(ValueError,'GRAPH_FRAGMENT_READBACK'):consumer.verify(self.folder)

    def test_wrong_declared_a_version_rejected(self):
        self.json_mutate('delivery.json',lambda d:d.update(a_consumer_commit='0'*40))
        with self.assertRaisesRegex(ValueError,'GENERATION_CONTEXT_BINDING'):consumer.verify(self.folder)

if __name__=='__main__':unittest.main()
