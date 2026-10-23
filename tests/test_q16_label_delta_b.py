"""Three-label allowlist tests only; no new C01 content acceptance is claimed."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import review_four_task_c01_b as review
import verify_q16_label_delta_b as labels


class Q16OnlyLabelDelta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        archive=ROOT/'handoffs/b/46007447/B-46007447-Q16-reading-C01-v2-HOLD-2026-10-21.zip'
        with zipfile.ZipFile(archive) as z:
            cls.old=dict(bundle=json.loads(z.read('delivery/bundle.json')),sidecars={})
            for name in z.namelist():
                if name.startswith('delivery/') and name.count('/')==1 and name.endswith('.json') and name!='delivery/bundle.json':
                    cls.old['sidecars'][Path(name).name]=json.loads(z.read(name))

    def candidate(self,separate_runs=False):
        new=copy.deepcopy(self.old)
        def visit(value):
            if isinstance(value,list):
                for v in value:visit(v)
            elif isinstance(value,dict):
                block=value.get('region_id','').removeprefix('region-')
                if block in labels.LABELS and isinstance(value.get('text'),str):value['text']=labels.LABELS[block]+value['text']
                block=value.get('block_id')
                if block in labels.LABELS and 'runs' in value:
                    if separate_runs:value['runs'].insert(0,dict(format='plain',text=labels.LABELS[block]))
                    else:value['runs'][0]['text']=labels.LABELS[block]+value['runs'][0]['text']
                for v in value.values():visit(v)
        visit(new)
        return new

    def audit(self,new):return labels.audit_labels_only(self.old,new,review.diff)

    def test_exact_three_labels_accepts_inline_or_separate_plain_runs(self):
        for separate in [False,True]:
            result=self.audit(self.candidate(separate))
            self.assertEqual(result['status'],'Q16_THREE_LABELS_ONLY')
            self.assertEqual(len(result['source_bindings']),3)
            self.assertEqual(result['unauthorized_delta'],[])

    def test_one_missing_label_is_rejected_even_when_other_two_are_valid(self):
        new=self.candidate();region=next(r for r in review.parts(new['bundle'])['EvidenceBundle']['regions'] if r['region_id']=='region-q16-task2')
        region['text']=region['text'][3:]
        self.assertEqual(self.audit(new)['status'],'Q16_LABEL_DELTA_REJECTED')

    def test_duplicate_or_wrong_label_is_rejected(self):
        for prefix in ['（1）','（2）']:
            new=self.candidate();region=next(r for r in review.parts(new['bundle'])['EvidenceBundle']['regions'] if r['region_id']=='region-q16-task1')
            region['text']=prefix+region['text']
            self.assertTrue(self.audit(new)['unauthorized_delta'])

    def test_any_extra_answer_text_change_is_rejected(self):
        new=self.candidate();region=next(r for r in review.parts(new['bundle'])['EvidenceBundle']['regions'] if r['content_type']=='formula')
        region['text']+='X'
        self.assertEqual(self.audit(new)['status'],'Q16_LABEL_DELTA_REJECTED')

    def test_formula_blank_geometry_and_unknown_field_changes_are_rejected(self):
        for kind in ['formula','blank','geometry','extra']:
            new=self.candidate();side=new['sidecars']['delivery.json']
            if kind=='formula':side['q16_formula_slots'][0]['expected_latex']='invented'
            elif kind=='blank':next(r for b in side['bindings'] for r in b['runs'] if r['format']=='blank')['value']='filled'
            elif kind=='geometry':review.parts(new['bundle'])['EvidenceBundle']['regions'][0]['box']['bbox'][0]+=1
            else:side['extra_unapproved']=True
            self.assertTrue(self.audit(new)['unauthorized_delta'],kind)

    def test_legacy_reference_changes_are_not_hidden_as_publication_reseals(self):
        new=self.candidate()
        new['sidecars']['basis.json']['extra_legacy_ref']=dict(artifact_id='other',revision=3,kind='QuestionGraph',content_hash='0'*64)
        self.assertTrue(self.audit(new)['unauthorized_delta'])

    def test_publication_reseal_and_bound_graph_ref_are_separately_exempted(self):
        new=self.candidate()
        for a in new['bundle']['artifacts']:
            a['artifact_id']='new-'+a['artifact_id'];a['revision']=2;a['content_hash']='1'*64
        new['sidecars']['delivery.json']['c01_graph_ref']['content_hash']='1'*64
        # This tests classification only; real input still must pass fixed A24.
        self.assertEqual(self.audit(new)['status'],'Q16_THREE_LABELS_ONLY')

    def test_exempted_file_digest_must_match_actual_resource_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);(folder/'basis.json').write_bytes(b'{}')
            snapshot=dict(sidecars={'delivery.json':{'basis_sha256':'0'*64}})
            checks=labels.bound_digest_checks(folder,snapshot,lambda p:p.read_bytes(),review.sha)
            self.assertFalse(all(c['passed'] for c in checks))

    def test_other_plain_character_added_with_a_label_is_rejected(self):
        new=self.candidate()
        region=next(r for r in review.parts(new['bundle'])['EvidenceBundle']['regions'] if r['region_id']=='region-q16-task1')
        region['text']=region['text'].replace('（1）','（1）额外',1)
        self.assertTrue(self.audit(new)['unauthorized_delta'])


if __name__=='__main__':unittest.main()
