import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_reconcile', ROOT/'tools/reconcile_chapter_sources_b.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

class SourceReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = [tool.unpack_fixed(ROOT/path, pin) for path,pin in tool.PINS.values()]
        cls.report,cls.candidate = tool.build(*cls.inputs)

    def inputs_for_check(self):
        question=copy.deepcopy(self.candidate['question_snapshot'])
        answer=copy.deepcopy(self.candidate['answer_snapshot'])
        images={'viewer-15':self.inputs[1]['46007447_page_14.jpg'],
                'viewer-173':self.inputs[2]['staging/assets/viewer-173.jpg']}
        return question,answer,images

    def test_real_disconnected_question_is_linkable_without_promoting_or_rewriting(self):
        before=copy.deepcopy(self.inputs)
        report,candidate=tool.build(*self.inputs)
        self.assertEqual(self.inputs,before)
        self.assertEqual(report['local_original_count'],8)
        self.assertIsNone(report['chapter_expected_pages'])
        self.assertFalse(report['q16']['requires_A_to_resend_question_page'])
        self.assertEqual(candidate['question_id'],'q-457f1973a1426d29587d5752')
        self.assertEqual(candidate['answer_id'],'a-7302d4870826c53aea0bcd16')
        self.assertEqual(candidate['relationship_status'],'CANDIDATE_NOT_SELECTED')
        self.assertFalse(candidate['selected_relation_created'])
        self.assertFalse(candidate['human_verified'])
        self.assertFalse(candidate['platform_eligible'])
        self.assertEqual(report['q9']['question_source_status'],'NOT_LOCATED_IN_FIXED_LOCAL_SOURCE_SET')
        self.assertEqual(tool.build(*self.inputs),(report,candidate))

    def test_task_map_keeps_blank_questions_unfilled_and_binds_exact_answer_spans(self):
        candidate=self.candidate
        lines={line['content_fragment_id']:line for line in candidate['answer_snapshot']['content_fragments']}
        texts=[]
        for task in candidate['task_map']:
            texts.append('\n'.join(lines[r['content_fragment_id']]['text'][slice(*r['text_span'])]
                                  for r in task['answer_regions']))
        self.assertEqual(texts[0],'（1）60 61')
        self.assertEqual(texts[1],r'（2）\frac{a^{2}+1}{2}')
        self.assertTrue(texts[2].startswith('（3）∵a²+'))
        self.assertTrue(texts[2].endswith('是勾股数。'))
        blanks=[r for b in candidate['question_snapshot']['blocks'] for r in b['runs'] if r['format']=='blank']
        self.assertEqual(len(blanks),3)
        self.assertTrue(all(r['value'] is None for r in blanks))

    def test_same_number_from_another_question_identity_is_rejected(self):
        q,a,im=self.inputs_for_check();q['question_id']='same-number-moon-question'
        with self.assertRaisesRegex(ValueError,'STABLE_IDENTITY'):tool.validate_q16_inputs(q,a,im)

    def test_wrong_book_and_wrong_section_are_not_matches(self):
        q,a,im=self.inputs_for_check();a['book_id']='46006966'
        with self.assertRaisesRegex(ValueError,'BOOK_IDENTITY'):tool.validate_q16_inputs(q,a,im)
        q,a,im=self.inputs_for_check();a['section_path']=['第一章 勾股定理','第1课时 探索勾股定理']
        with self.assertRaisesRegex(ValueError,'SECTION_IDENTITY'):tool.validate_q16_inputs(q,a,im)

    def test_response_blanks_are_not_filled_from_answer(self):
        q,a,im=self.inputs_for_check()
        next(r for r in q['blocks'][1]['runs'] if r['format']=='blank')['value']='60'
        with self.assertRaisesRegex(ValueError,'NO_FILLED_QUESTION_BLANKS'):tool.validate_q16_inputs(q,a,im)

    def test_missing_formula_and_task_order_are_rejected(self):
        q,a,im=self.inputs_for_check()
        a['content_fragments'][0]['runs']=[r for r in a['content_fragments'][0]['runs'] if r['format']!='latex']
        with self.assertRaisesRegex(ValueError,'ANSWER_FORMULA_COVERAGE'):tool.validate_q16_inputs(q,a,im)
        q,a,im=self.inputs_for_check();q['blocks'][1],q['blocks'][2]=q['blocks'][2],q['blocks'][1]
        with self.assertRaisesRegex(ValueError,'QUESTION_TASK_ORDER'):tool.validate_q16_inputs(q,a,im)

    def test_changed_source_pixels_and_false_approval_are_rejected(self):
        q,a,im=self.inputs_for_check();im['viewer-15']=im['viewer-173']
        with self.assertRaisesRegex(ValueError,'QUESTION_SOURCE_SHA'):tool.validate_q16_inputs(q,a,im)
        q,a,im=self.inputs_for_check();a['content_fragments'][0]['transcription_verified']=True
        with self.assertRaisesRegex(ValueError,'NO_ANSWER_APPROVAL'):tool.validate_q16_inputs(q,a,im)

    def test_replaced_input_package_is_rejected_before_read(self):
        path,pin=tool.PINS['question']
        with self.assertRaisesRegex(ValueError,'FIXED_PACKAGE_SHA'):tool.unpack_fixed(ROOT/path,'0'*64)

if __name__=='__main__': unittest.main()
