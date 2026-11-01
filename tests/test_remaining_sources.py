import copy,sys
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import process_remaining_sources_b as mod

class RemainingSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=mod.load_inputs();cls.parent=mod.base.build_workspace(cls.inputs)
        cls.view=mod.build_processing(cls.inputs,cls.parent)
    def audit(self,view):return mod.audit_processing(view,self.inputs)
    def rejected(self,change):
        view=copy.deepcopy(self.view);change(view['payload']);view['content_hash']=mod.sha(mod.canonical(view['payload']))
        self.assertFalse(self.audit(view)['source_and_structure_accepted'])
    def test_all_fourteen_rows_processed_as_eight_answer_evidence_items(self):
        before=copy.deepcopy(self.parent);view=mod.build_processing(self.inputs,self.parent)
        self.assertEqual(before,self.parent);self.assertEqual(view,self.view)
        self.assertTrue(self.audit(view)['source_and_structure_accepted'])
        p=view['payload'];self.assertEqual(len(p['answer_evidence_candidates']),8)
        self.assertEqual(p['counts']['rows_with_answer_evidence_only'],14)
        self.assertEqual(p['counts']['rows_without_source_processing'],0)
        self.assertEqual(p['counts']['missing_question_identity_rows'],14)
        self.assertEqual(p['base_workspace'],self.parent)
    def test_consumer_never_calls_new_producer(self):
        with patch.object(mod,'build_processing',side_effect=AssertionError('producer forbidden')):
            self.assertTrue(self.audit(self.view)['source_and_structure_accepted'])
    def test_mixed_training_rows_and_denominators_are_not_primary_numbers(self):
        rows={r['line_id']:r for r in self.view['payload']['current_source_queue']}
        self.assertEqual(len(rows['viewer-173/ocr/122']['evidence_candidate_ids']),2)
        self.assertEqual(len(rows['viewer-173/ocr/123']['evidence_candidate_ids']),2)
        candidates=self.view['payload']['answer_evidence_candidates']
        self.assertEqual(candidates[4]['source']['runs'][0]['text'],r'\frac{10}{3}')
        self.assertEqual(candidates[6]['source']['runs'][0]['text'],r'\frac{13}{6}')
        self.assertEqual(candidates[6]['source']['formula_occurrences'][0]['denominator_source'],'PIXEL_SUPPLEMENT_NO_NEW_OCR')
        self.assertIsNone(candidates[2]['source']['printed_number'])
        self.assertEqual(candidates[2]['source']['label'],'【例】')
    def test_repeated_fractions_have_separate_source_occurrences(self):
        candidates=self.view['payload']['answer_evidence_candidates']
        first=candidates[0]['source']['formula_occurrences'];proof=candidates[2]['source']['formula_occurrences']
        self.assertEqual(len(first),2);self.assertNotEqual(first[0]['region'],first[1]['region'])
        self.assertEqual(first[0]['raw_support_row_ids'],['viewer-173/ocr/86'])
        self.assertEqual(first[1]['raw_support_row_ids'],[])
        self.assertEqual(proof[0]['raw_support_row_ids'],[])
        self.assertEqual(proof[1]['raw_support_row_ids'],['viewer-173/ocr/115','viewer-173/ocr/117'])
    def test_acceptance_queue_has_current_scopes_and_no_human_approvals(self):
        queue=self.view['payload']['acceptance_queue'];self.assertEqual(len(queue['items']),18)
        self.assertEqual(queue['pending_count'],18);self.assertEqual(queue['approved_count'],0)
        for item in queue['items']:
            scopes=[mod.pointer(self.parent,p) for p in item['scope_paths']]
            self.assertEqual(item['subject_sha256'],mod.sha(mod.canonical(scopes)))
            self.assertIsNone(item['reviewer']);self.assertIsNone(item['disposition'])
            self.assertTrue(item['required_action'])
    def test_fake_question_and_unnumbered_example_one_are_rejected(self):
        for change in [lambda p:p['answer_evidence_candidates'][2]['source'].update(printed_number=1),
                       lambda p:p['answer_evidence_candidates'][0].update(question_id='same-number-first-lesson-1'),
                       lambda p:p['answer_evidence_candidates'][0].update(relation_status='SELECTED')]:self.rejected(change)
    def test_repeated_55_over_16_raw_support_cannot_be_copied_or_swapped(self):
        self.rejected(lambda p:p['answer_evidence_candidates'][2]['source']['formula_occurrences'][0].update(raw_support_row_ids=['viewer-173/ocr/115']))
        self.rejected(lambda p:p['answer_evidence_candidates'][2]['source']['formula_occurrences'].reverse())
    def test_table_cells_cannot_swap_roles_or_rewrite_original_garbled_ocr(self):
        self.rejected(lambda p:p['answer_evidence_candidates'][0]['source'].update(column_roles=['length','equation','x','answer']))
        self.rejected(lambda p:p['answer_evidence_candidates'][0]['source']['cells'].reverse())
        self.rejected(lambda p:p['answer_evidence_candidates'][1]['raw_rows'][0].update(text='clean replacement'))
    def test_split_row_cannot_be_atomically_assigned_and_no_missing_row(self):
        def atomic(p):
            row=next(r for r in p['current_source_queue']if r['line_id'].endswith('/123'))
            row['evidence_candidate_ids']=row['evidence_candidate_ids'][:1]
        self.rejected(atomic);self.rejected(lambda p:p['current_source_queue'].pop())
    def test_pending_review_cannot_self_approve_or_bind_stale_content(self):
        for change in [lambda p:p['acceptance_queue']['items'][0].update(status='APPROVED',reviewer='model'),
                       lambda p:p['acceptance_queue']['items'][3].update(subject_sha256='0'*64),
                       lambda p:p['answer_evidence_candidates'][0].update(human_verified=True)]:self.rejected(change)
    def test_old_five_reading_rows_and_original_ledger_are_immutable(self):
        old=self.parent['payload']['current_unassigned_work_queue'];new=self.view['payload']['current_source_queue']
        self.assertEqual([r for r in old if r['current_status']=='CANDIDATE_ASSEMBLED_REVIEW_PENDING'],
                         [r for r in new if r['current_status']=='CANDIDATE_ASSEMBLED_REVIEW_PENDING'])
        self.rejected(lambda p:p['base_workspace']['payload']['legacy_answer_coverage'][0].update(status='APPROVED'))
    def test_bounded_scan_is_not_whole_computer_absence_or_chapter_completeness(self):
        scan=self.inputs['local_search'];self.assertEqual(scan['distinct_archive_bytes'],27)
        self.assertEqual(len(scan['archive_raw_page_shas']),8);self.assertEqual(scan['new_raw_page_shas'],[])
        self.assertFalse(scan['whole_computer_absence_proven'])
        self.rejected(lambda p:p['local_source_search'].update(whole_computer_absence_proven=True))
        self.rejected(lambda p:p['counts'].update(missing_question_identity_rows=0))
    def test_current_source_pixels_and_formula_values_are_bound(self):
        self.rejected(lambda p:p['answer_evidence_candidates'][4]['source']['runs'][0].update(text=r'\frac{10}{6}'))
        self.rejected(lambda p:p['answer_evidence_candidates'][6]['source']['region']['bbox'].__setitem__(0,619))
        self.rejected(lambda p:p['answer_evidence_candidates'].pop())

if __name__=='__main__':unittest.main()
