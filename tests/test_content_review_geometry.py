"""Current Q4/Q9/Q15/Q16 review compatibility on published original pixels."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
from annotation.recognition.content_review import ReviewWorkspace, ReviewConflict, SourceChanged
from annotation.recognition import content_revision as revision
from content_review_q15_fixture import inputs, TARGET

AUTHOR = dict(kind='MODEL_DRAFT', id='offline-ui-regression', note='Temporary punctuation edit; no approval')


class GeometryReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.values, cls.sources, cls.graph = inputs(cls.root/'inputs')

    def open(self, name, values=None):
        return ReviewWorkspace(*(values or self.values), self.root/name, self.sources)

    def test_current_plan_edit_recheck_restore_and_reopen_preserve_geometry_and_others(self):
        w = self.open('roundtrip')
        before = w.state()
        self.assertEqual(before['counts'], dict(questions=34, answers=66, issues=137, unassigned=19))
        self.assertEqual(w.documents()['graph'], self.graph)
        answer = next(a for a in before['answers'] if a['answer_id'] == TARGET)
        self.assertEqual(len(answer['blocks']), 4)
        self.assertEqual(sum(len(b.get('source_geometry_revisions', [])) for b in answer['blocks']), 1)
        block = answer['blocks'][0]
        runs = copy.deepcopy(block['runs'])
        runs[0]['text'] += ' '
        request = dict(expected_head=before['head'], answer_id=TARGET, author=AUTHOR,
                       changes=[dict(key=block['key'], runs=runs)])
        saved = w.save(request)
        self.assertEqual(saved['plan_revision'], 10)
        self.assertNotEqual(saved['head'], before['head'])
        self.assertEqual(w.state(), saved)  # Independent pixel/content recheck.
        with self.assertRaises(ReviewConflict):
            w.save(request)
        docs = w.documents()
        self.assertEqual(docs['graph']['schema_version'], 'b-graph-trial/0.8')
        for old, new in zip(self.values[-1]['payload']['operations'], docs['plan']['payload']['operations']):
            self.assertEqual(old.get('source_geometry_revisions'), new.get('source_geometry_revisions'))
        for old, new in zip(self.graph['payload']['answers'], docs['graph']['payload']['answers']):
            self.assertEqual(old['fragments'], new['fragments'])
        for old, new in zip(before['answers'], saved['answers']):
            if old['answer_id'] != TARGET:
                self.assertEqual({k:v for k,v in old.items() if k != 'issue_ids'},
                                 {k:v for k,v in new.items() if k != 'issue_ids'})
        restored = w.restore(dict(expected_head=saved['head'], revision_head=before['head'], author=AUTHOR))
        self.assertEqual(restored['plan_revision'], 11)
        self.assertEqual(w.documents()['plan']['payload']['operations'], self.values[-1]['payload']['operations'])
        self.assertEqual(self.open('roundtrip').state(), restored)
        self.assertFalse(restored['business_acceptance'])
        self.assertEqual(restored['decision'], 'HOLD')
        self.assertFalse(list((self.root/'roundtrip').glob('.geometry-*')))

    def test_forged_trim_receipt_rejected_at_initialization(self):
        values = copy.deepcopy(self.values)
        ops = values[-1]['payload']['operations']
        op = next(o for o in ops if o.get('target', {}).get('answer_id') == TARGET and o.get('source_geometry_revisions'))
        op['source_geometry_revisions'][0]['trimmed_crop_rgb_sha256'] = '0'*64
        values[-1] = revision.make_revision_plan(*values[:3], ops, AUTHOR)
        with self.assertRaisesRegex(ValueError, 'zero-dark'):
            self.open('bad-receipt', values)

    def test_source_change_blocks_state_save_restore_and_reopen(self):
        w = self.open('source-change')
        state = w.state()
        image = w._paths['viewer-173']
        raw = image.read_bytes()
        try:
            image.write_bytes(raw+b'changed')
            for action in (w.state, lambda: w.save(dict(expected_head=state['head'], answer_id=TARGET, changes=[], author=AUTHOR)),
                           lambda: w.restore(dict(expected_head=state['head'], revision_head=state['head'], author=AUTHOR)),
                           lambda: self.open('source-change')):
                with self.assertRaises(SourceChanged):
                    action()
        finally:
            image.write_bytes(raw)
        self.assertEqual(w.state()['head'], state['head'])

    def test_recheck_uses_independent_pixel_audits_without_producer(self):
        w = self.open('independent')
        with patch.object(revision, 'apply_content_revision', side_effect=AssertionError('producer called')):
            self.assertEqual(w.state()['counts']['issues'], 137)


if __name__ == '__main__':
    unittest.main()
