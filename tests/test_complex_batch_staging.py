"""Fixed Q9 evidence semantics: a corrupt self-comparison must still reject."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_complex_batch_b import build, load_package, rejection_checks, validate_batch


class FixedQ9StagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = ROOT / 'handoffs/b/46007447/B-46007447-Q15-revision9-current-baseline-HOLD-2026-10-18.zip'
        cls.batch, cls.files = build(load_package(package))

    def assert_rejects_own_snapshot(self, bad, code):
        # A new baseline/hash cannot make missing fixed source content acceptable.
        with self.assertRaisesRegex(ValueError, '^' + code + '$'):
            validate_batch(bad, copy.deepcopy(bad))

    def test_fixed_source_stays_answer_evidence_without_question_identity(self):
        q9 = self.batch['cases'][2]
        self.assertEqual(q9['answer_id'], 'a-9a6c21dd0fe88b1059b7919e')
        self.assertIsNone(q9['question_id'])
        self.assertIsNone(q9['question_snapshot'])
        self.assertFalse(q9['joint_accepted'])
        self.assertFalse(q9['platform_eligible'])
        self.assertEqual(q9['decision'], 'HOLD')
        self.assertEqual(len(q9['answer_snapshot']['fragments']), 33)
        self.assertEqual(len(q9['answer_snapshot']['render_regions']), 15)
        validate_batch(self.batch, self.batch)

    def test_each_missing_figure_rejects_even_with_corrupt_baseline(self):
        for figure in ('3', '4', '5', '6', '7'):
            with self.subTest(figure=figure):
                bad = copy.deepcopy(self.batch)
                answer = bad['cases'][2]['answer_snapshot']
                answer['render_regions'] = [r for r in answer['render_regions'] if r.get('figure_number') != figure]
                self.assert_rejects_own_snapshot(bad, 'Q9_EXACT_RENDER_PLAN')

    def test_cross_page_reordering_rejects_even_when_counts_match(self):
        bad = copy.deepcopy(self.batch)
        regions = bad['cases'][2]['answer_snapshot']['render_regions']
        regions[0], regions[3] = regions[3], regions[0]
        self.assertEqual(len(regions), 15)
        self.assert_rejects_own_snapshot(bad, 'Q9_EXACT_RENDER_PLAN')

    def test_continuation_cannot_drop_line_change_tail_or_repeat(self):
        for change in ('drop-last-line', 'wrong-tail', 'wrong-page', 'duplicate-link'):
            with self.subTest(change=change):
                bad = copy.deepcopy(self.batch)
                links = bad['cases'][2]['answer_snapshot']['continuations']
                if change == 'drop-last-line':
                    links[0]['target_line_ids'].pop()
                elif change == 'wrong-tail':
                    links[0]['source_tail_line_id'] = 'viewer-173/ocr/155'
                elif change == 'wrong-page':
                    links[0]['to_asset_id'] = 'viewer-173'
                else:
                    links.append(copy.deepcopy(links[0]))
                code = 'Q9_CONTINUATION_CARDINALITY' if change == 'duplicate-link' else 'Q9_CONTINUATION_BINDING'
                self.assert_rejects_own_snapshot(bad, code)

    def test_truncated_final_answer_is_rejected_even_with_all_regions(self):
        bad = copy.deepcopy(self.batch)
        answer = bad['cases'][2]['answer_snapshot']
        answer['text'] = answer['text'].rsplit('\n', 1)[0]
        self.assertEqual(len(answer['render_regions']), 15)
        self.assert_rejects_own_snapshot(bad, 'Q9_TEXT_CONTINUATION')

    def test_nine_embedded_mutations_reject_at_their_expected_layer(self):
        checks = rejection_checks(self.batch)
        self.assertEqual(len(checks), 9)
        self.assertTrue(all(c['rejected'] for c in checks))
        self.assertIn('spliced-other-printed-q9', {c['case'] for c in checks})


if __name__ == '__main__':
    unittest.main()
