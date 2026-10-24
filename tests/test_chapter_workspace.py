import copy
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import build_chapter_workspace_b as module

class ChapterWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=module.load_inputs()
        cls.view=module.build_workspace(cls.inputs)

    def audit(self,view):return module.audit_workspace(view,self.inputs)
    def rejected(self,change):
        forged=copy.deepcopy(self.view);change(forged['payload'])
        forged['content_hash']=module.sha(module.canonical(forged['payload']))
        self.assertFalse(self.audit(forged)['source_and_structure_accepted'])

    def test_three_lanes_and_all_native_records_are_preserved(self):
        before=copy.deepcopy(self.inputs)
        second=module.build_workspace(self.inputs)
        self.assertEqual(before,self.inputs);self.assertEqual(second,self.view)
        self.assertTrue(self.audit(second)['source_and_structure_accepted'])
        p=second['payload'];self.assertEqual(p['counts'],dict(question_candidates=42,legacy_answers=66,materials=1,material_tasks=3,new_material_answer_drafts=3,legacy_unassigned=19,candidate_assembled_rows=5,rows_without_current_candidate=14))
        self.assertEqual(len({q['question_id']for q in p['questions']}),42)
        self.assertIsNone(p['chapter_denominator'])

    def test_consumer_does_not_rebuild_expected_output_with_producer(self):
        with patch.object(module,'build_workspace',side_effect=AssertionError('producer forbidden')):
            self.assertTrue(self.audit(self.view)['source_and_structure_accepted'])

    def test_q16_eleven_formula_slots_and_three_exact_subpart_regions(self):
        p=self.view['payload'];q=p['q16_relationship']
        self.assertEqual(q['question_id'],'q-457f1973a1426d29587d5752')
        self.assertEqual(q['answer_id'],'a-7302d4870826c53aea0bcd16')
        self.assertEqual(len(q['task_map']),3);self.assertEqual(len(p['q16_formula_review']),11)
        self.assertEqual([r['slot']for r in p['q16_formula_review']],[f'F{i}'for i in range(1,12)])
        self.assertFalse(q['selected_relation_created'])
        self.assertIn('60 61',q['answer_snapshot']['text'])

    def test_five_rows_form_three_answers_not_five(self):
        p=self.view['payload'];rows={r['line_id']:r for r in p['current_unassigned_work_queue']}
        self.assertEqual(len(rows['viewer-173/ocr/108']['material_answer_ids']),2)
        self.assertEqual(rows['viewer-173/ocr/112']['source_binding']['candidate_role'],'TASK_3_SINGLE_DIAGRAM_LABEL_ONLY')
        self.assertEqual(len(p['material_answer_drafts']),3)
        task3=p['material_answer_drafts'][2]
        self.assertTrue(task3['text'].endswith('案不唯一）'))
        self.assertEqual(sum(r['content_type']=='image'for r in task3['source_regions']),1)
        self.assertEqual(p['material_answer_drafts'][0]['blank_responses'],['a-b',r'\frac{1}{2}ab','(a-b)^2'])

    def test_dropped_lane_stale_branch_and_changed_native_answer_rejected(self):
        for change in [lambda p:p['questions'].pop(),lambda p:p['branch_refs']['base'].update(revision=999),
                       lambda p:p['legacy_answers'][0]['native'].update(text='wrong answer')]:
            self.rejected(change)

    def test_same_number_q16_substitution_is_rejected(self):
        self.rejected(lambda p:p['q16_relationship'].update(question_id='same-number-other-section'))

    def test_formula_missing_wrong_power_and_reordered_slots_rejected(self):
        for change in [lambda p:p['q16_formula_review'].pop(),
                       lambda p:p['q16_formula_review'][2].update(expected_latex=r'\frac{a^{2}+2a^{2}+1}{4}'),
                       lambda p:p['q16_formula_review'].reverse(),
                       lambda p:p['q16_formula_review'][8].update(source_bbox=p['q16_formula_review'][9]['source_bbox'])]:
            self.rejected(change)

    def test_source_row_108_cannot_be_atomic_or_wrongly_split(self):
        def atomic(p):
            r=next(r for r in p['current_unassigned_work_queue']if r['line_id'].endswith('/108'))
            r['material_answer_ids']=r['material_answer_ids'][:1]
        self.rejected(atomic)
        self.rejected(lambda p:p['source_regions'][3]['bbox_xyxy'].__setitem__(2,300))

    def test_lone_numerator_and_diagram_label_cannot_expand_to_full_answers(self):
        def expand(p):
            row=next(r for r in p['current_unassigned_work_queue']if r['line_id'].endswith('/104'))
            row['source_binding']['candidate_role']='COMPLETE_PROOF'
        self.rejected(expand)
        self.rejected(lambda p:p['material_answer_drafts'][2]['source_regions'].pop())

    def test_supplement_text_changes_and_task_order_rejected(self):
        self.rejected(lambda p:p['source_regions'][2].update(text='invented proof'))
        self.rejected(lambda p:p['material_answer_drafts'].reverse())
        self.rejected(lambda p:p['material_answer_drafts'][0]['blank_responses'].reverse())

    def test_original_ledger_and_approval_cannot_be_promoted(self):
        for change in [lambda p:p['legacy_answer_coverage'][0].update(status='APPROVED'),
                       lambda p:p.update(human_verified=True),lambda p:p.update(decision='PASS'),
                       lambda p:p.update(chapter_denominator=42),
                       lambda p:p['material_answer_drafts'][0].update(verification_status='VERIFIED'),
                       lambda p:p['current_unassigned_work_queue'][-1].update(current_status='RESOLVED')]:
            self.rejected(change)

    def test_json_duplicate_key_and_wrong_schema_rejected(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_JSON_KEY'):module.unique_object('{"a":1,"a":2}')
        view=copy.deepcopy(self.view);view['schema_version']='public-contract/1'
        self.assertFalse(self.audit(view)['source_and_structure_accepted'])

    def test_git_lf_and_windows_crlf_bind_same_text_but_changed_json_is_rejected(self):
        raw=b'{\n"x":1\n}\n';pin=module.sha(raw)
        self.assertEqual(module.fixed_json(raw,pin),module.fixed_json(raw.replace(b'\n',b'\r\n'),pin))
        with self.assertRaisesRegex(ValueError,'FIXED_JSON_LF_SHA'):
            module.fixed_json(raw.replace(b':1',b':2'),pin)

if __name__=='__main__':unittest.main()
