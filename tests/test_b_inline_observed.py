"""Frozen real failures must survive candidate projection and handoff packaging."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from annotation.recognition.inline_candidates import build_inline_candidates

class RealInlineObservations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=ROOT/'tests/fixtures/book46007447'
        cls.archive=zipfile.ZipFile(cls.folder/'inline-observed.zip')
        cls.read=staticmethod(lambda name:json.loads(cls.archive.read(name)))
        cls.observed=cls.read('formula-observed-trials/formal-warm-observations.json')
        cls.candidates=build_inline_candidates(cls.observed)

    @classmethod
    def tearDownClass(cls):cls.archive.close()

    def test_exact_observed_bundle_and_all_members_are_frozen(self):
        manifest=json.loads((self.folder/'inline-observed-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((self.folder/'inline-observed.zip').read_bytes()).hexdigest(),manifest['archive']['sha256'])
        internal=self.read('MANIFEST.json')
        self.assertEqual(internal['members'],manifest['members'])
        self.assertEqual(set(self.archive.namelist()),set(manifest['members'])|{'MANIFEST.json'})
        for name,entry in manifest['members'].items():
            raw=self.archive.read(name)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),entry['sha256'],name)
            self.assertEqual(len(raw),entry['bytes'],name)
        self.assertFalse(manifest['original_images_included'])
        self.assertFalse(manifest['model_weights_included'])

    def test_real_partial_resume_warm_keep_all_84_calls(self):
        for name,new,done,cached,pending in [('formal-partial8',8,8,0,76),('formal-resumed',76,84,8,0),('formal-warm',0,84,84,0)]:
            r=self.read('formula-observed-trials/'+name+'.json')
            self.assertEqual(r['counts']['declared_calls'],84)
            self.assertEqual(r['counts']['done'],done)
            self.assertEqual(r['counts']['cache_hits'],cached)
            self.assertEqual(r['counts']['pending'],pending)
            self.assertEqual(r['profiled_encoder_decoder_entries'],new)
            self.assertTrue(r['integrity_accepted'])
        self.assertEqual(self.read('formula-observed-trials/formal-resumed.json')['observations_ref'],
                         self.read('formula-observed-trials/formal-warm.json')['observations_ref'])

    def test_every_formula_outcome_survives_including_41_unparsed(self):
        calls=self.observed['payload']['calls'];values=self.candidates['payload']['candidates']
        self.assertEqual(len(calls),84)
        self.assertEqual(len(values),84)
        self.assertEqual([c['observation']['payload']['raw_latex']for c in calls],[v['raw_latex']for v in values])
        self.assertEqual(sum(v['parse_result']['supported']for v in values),43)
        self.assertEqual(sum(not v['parse_result']['supported']for v in values),41)
        self.assertEqual(len(self.observed['payload']['requested_line_ids']),9)
        self.assertFalse(self.candidates['payload']['entire_answer_reconstructed'])
        self.assertEqual(self.candidates['payload']['selected_candidate_refs'],[])
        self.assertTrue(all(not v['selected']for v in values))

    def test_actual_two_identical_hallucinated_final_ones_are_not_approved(self):
        values=[v for v in self.candidates['payload']['candidates']if any(
            b['unit_id']=='inline-math-unit-f2ea347f7aea2d5a07bbf68a'and b['region_variant']=='CORE_CONTEXT_PAD2'
            for b in v['unit_bindings'])]
        self.assertEqual(len(values),2)
        self.assertEqual([v['raw_latex']for v in values],['A B^{2}=10^{2}+25^{2}=1']*2)
        self.assertTrue(all(v['parse_result']['supported']for v in values))
        self.assertEqual(values[0]['parse_result']['normalized_ast'],values[1]['parse_result']['normalized_ast'])
        self.assertTrue(all(not v['transcription_verified']and not v['business_acceptance']and not v['selected']for v in values))

    def test_power_recovery_coexists_with_all_wrong_context_variants(self):
        values=[v for v in self.candidates['payload']['candidates']if any(
            b['unit_id']=='inline-math-unit-f5ecfb30c908e4c5ab5156d9'for b in v['unit_bindings'])]
        self.assertEqual(len(values),4)
        self.assertEqual(sum(v['raw_latex']=='625=25^{2}'for v in values),2)
        self.assertTrue(any('25^{4}'in v['raw_latex']for v in values))
        self.assertTrue(all(not v['selected']for v in values))
        ordinary=self.read('observations.json')
        row=next(r for r in ordinary['payload']['rows']if r['line_id']=='resource-173/ocr/4')
        self.assertTrue(all('10十5'in v['raw_call_result'][0][0][1]for v in row['variants']))
        review=json.loads((self.folder/'continuation-content-review-v2.json').read_text(encoding='utf-8'))
        self.assertIn('25²',json.dumps(review,ensure_ascii=False))
        self.assertFalse(self.candidates['payload']['expected_text_consumed'])

if __name__=='__main__':unittest.main()
