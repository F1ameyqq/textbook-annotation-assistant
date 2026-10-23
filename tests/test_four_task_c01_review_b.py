"""Focused negative mapping checks; local mutations are not new C01 deliveries."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('four_review',ROOT/'tools/review_four_task_c01_b.py')
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)


class FourTaskDeltaChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        file=ROOT/'handoffs/b/46007447/B-46007447-Q16-reading-C01-v2-HOLD-2026-10-21.zip'
        if hashlib.sha256(file.read_bytes()).hexdigest()!='4725523ec499a3074b268b12f0282ca795c13ddd98e97350078a50db89f7dc93':raise ValueError('HISTORICAL_ARCHIVE_CHANGED')
        with zipfile.ZipFile(file) as z:
            cls.bundle=json.loads(z.read('delivery/bundle.json'));cls.sidecar=json.loads(z.read('delivery/delivery.json'))
        cls.expected=review.expectations(cls.bundle,cls.sidecar)

    def selected_probe(self):
        bundle=copy.deepcopy(self.bundle);sidecar=copy.deepcopy(self.sidecar)
        for r in review.parts(bundle)['QuestionGraph']['answer_relations']:
            r['selected_fragment_ids']=list(r['candidate_fragment_ids']);r['status']='SELECTED'
        return bundle,sidecar

    def failures(self,bundle,sidecar):
        return [c['check'] for c in review.audit(bundle,sidecar,self.expected,True) if not c['passed']]

    def test_historical_unresolved_is_recorded_without_being_rewritten(self):
        self.assertTrue(all(c['passed'] for c in review.audit(self.bundle,self.sidecar,self.expected)))
        self.assertEqual(len([f for f in self.failures(self.bundle,self.sidecar) if f.startswith('selected_own_answers_')]),4)

    def test_four_selected_representation_does_not_require_human_or_platform_claim(self):
        bundle,sidecar=self.selected_probe()
        self.assertEqual(self.failures(bundle,sidecar),[])
        self.assertFalse(sidecar['human_verified'])
        self.assertFalse(sidecar['platform_actions'])

    def test_reading_material_attached_to_independent_q16_is_detected(self):
        bundle,sidecar=self.selected_probe();q=review.parts(bundle)['QuestionGraph']['questions'][0]
        q['shared_fragment_ids']=list(self.expected['shared_fragment_ids'])
        self.assertIn('q16_has_no_reading_shared_material',self.failures(bundle,sidecar))

    def test_selected_answer_swapped_between_reading_tasks_is_detected(self):
        bundle,sidecar=self.selected_probe();relations=review.parts(bundle)['QuestionGraph']['answer_relations']
        relations[1]['candidate_fragment_ids']=list(relations[2]['candidate_fragment_ids'])
        relations[1]['selected_fragment_ids']=list(relations[2]['selected_fragment_ids'])
        self.assertTrue(any(f.startswith('answer_candidate_identity_') for f in self.failures(bundle,sidecar)))
        self.assertTrue(any(f.startswith('source_binding_answer_ownership_') for f in self.failures(bundle,sidecar)))

    def test_filled_question_blank_is_detected(self):
        bundle,sidecar=self.selected_probe()
        blank=next(r for b in sidecar['bindings'] for r in b['runs'] if r['format']=='blank');blank['value']='invented'
        self.assertIn('all_question_blanks_still_null',self.failures(bundle,sidecar))

    def test_lost_formula_slot_is_detected(self):
        bundle,sidecar=self.selected_probe();sidecar['q16_formula_slots'].pop()
        self.assertIn('eleven_formula_slots_preserved',self.failures(bundle,sidecar))

    def test_region_text_cannot_disagree_with_blank_and_formula_runs(self):
        bundle,sidecar=self.selected_probe()
        regions=review.parts(bundle)['EvidenceBundle']['regions']
        region=next(r for r in regions if r['region_id']=='region-q16-task1')
        region['text']=region['text'].replace('____','invented',1)
        self.assertIn('bound_runs_match_region_region-q16-task1',self.failures(bundle,sidecar))

    def test_source_asset_rename_requires_explicit_identity_mapping(self):
        bundle,sidecar=self.selected_probe()
        for asset in review.parts(bundle)['SourceBundle']['assets']:
            asset['asset_id']='new-'+asset['asset_id']
        for region in review.parts(bundle)['EvidenceBundle']['regions']:
            region['box']['image']['asset_id']='new-'+region['box']['image']['asset_id']
        self.assertIn('original_image_hashes_preserved',self.failures(bundle,sidecar))
        mapping={'asset_ids':{old:'new-'+old for old in self.expected['originals']}}
        self.assertTrue(all(c['passed'] for c in review.audit(bundle,sidecar,self.expected,True,mapping)))

    def test_diff_keeps_extra_fields_array_order_and_scalar_types(self):
        changes=review.diff({'values':[1,2],'flag':True},{'values':[2,1],'flag':1,'extra':None})
        self.assertEqual({c['path'] for c in changes},{'/values/0','/values/1','/flag','/extra'})
        self.assertEqual(next(c for c in changes if c['path']=='/flag')['reason'],'type')


if __name__=='__main__':unittest.main()
