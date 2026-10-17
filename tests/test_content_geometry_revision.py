"""Explicit zero-dark source geometry revisions remain draft-only and source-bound."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from annotation.recognition import content_revision as producer
from annotation.recognition import content_revision_quality as consumer
from annotation.recognition.baseline import digest
from content_revision_observed import observed_inputs


Q4='a-35b5bc7421c65d9fcaa47e33'
FRAGMENTS=['af-9d41c7320e8c2393f9f7828c','af-53dc3afbfa2772a721251e6f','af-a93723edaa95a143cca80ce0']
HANDOFF=ROOT/'handoffs/b/46007447/B-46007447-Q16-offline-HOLD-2026-10-17.zip'
IMAGE_MEMBER='source/assets/46007447_viewer_173.jpg'


def resign(value):
    body={k:v for k,v in value.items()if k not in {'artifact_id','content_hash'}}
    value['content_hash']=digest(value['payload']);value['artifact_id']='content-revision-plan-'+digest(body)[:24]


class GeometryRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        docs,_=observed_inputs();cls.e,cls.g,cls.c,cls.review=[docs[k]for k in ('evidence','graph','base-check','review')]
        cls.author=dict(kind='MODEL_DRAFT',id='geometry-test-author',note='Explicit generated geometry draft; not human approval')
        temporary=tempfile.TemporaryDirectory();cls.addClassCleanup(temporary.cleanup);root=Path(temporary.name)
        asset=root/'q4-viewer-173.jpg'
        with zipfile.ZipFile(HANDOFF)as archive:asset.write_bytes(archive.read(IMAGE_MEMBER))
        manifest=dict(schema_version='b-source-trial/0.1',artifact_id='q4-geometry-test-source',book_id='46007447',scope_id='q4-geometry-test',
            assets=[dict(asset_id='viewer-173',path=asset.name,sha256='a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be',
                width=1148,height=1621,reading_order=0)])
        cls.source=root/'source.json';cls.source.write_text(json.dumps(manifest),encoding='utf-8')
        with Image.open(asset)as source:
            crop=source.convert('RGB').crop((663,1051,690,1055));cls.trim_sha=hashlib.sha256(crop.tobytes()).hexdigest()
            cls.trim_dark=sum(1 for r,g,b in crop.get_flattened_data()if 299*r+587*g+114*b<170000)
            crop2=source.convert('RGB').crop((663,1088,690,1089));cls.bottom_sha=hashlib.sha256(crop2.tobytes()).hexdigest()

    def operation(self):
        return dict(operation_id='q4-explicit-geometry',kind='REBUILD_TEXT_REGION',reason='Source-bound Q4 draft with explicit top-padding revision',
            target=dict(answer_id=Q4,role='answer',source_fragment_ids=FRAGMENTS),
            source_region=dict(asset_id='viewer-173',source_sha256='a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be',source_size=[1148,1621],bbox=[620,1055,690,1088]),
            source_geometry_revisions=[dict(revision_id='q4-numerator-top-padding-v1',fragment_id=FRAGMENTS[1],
                source_sha256='a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be',
                original_bbox=[663,1051,690,1071],revised_bbox=[663,1055,690,1071],trimmed_bbox=[663,1051,690,1055],
                trimmed_crop_rgb_sha256=self.trim_sha,dark_threshold=170,trimmed_dark_pixels=0,
                affected_fragment_overlaps=[dict(owner_kind='answer',owner_id='a-a8e80d06772625ffc1c269f3',fragment_id='af-708daf38470772a4a8bde06c',original_bbox=[599,1032,979,1054])],
                affected_ocr_overlaps=[dict(asset_id='viewer-173',line_id='viewer-173/ocr/103',original_bbox=[599,1032,979,1054],coverage_status='CONSUMED')],
                reason='Fixed threshold 170 finds zero dark pixels in only the removed top-edge strip; still unverified.',verification_status='UNVERIFIED'),
                dict(revision_id='q4-denominator-bottom-padding-v1',fragment_id=FRAGMENTS[2],
                source_sha256='a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be',
                original_bbox=[663,1071,690,1089],revised_bbox=[663,1071,690,1088],trimmed_bbox=[663,1088,690,1089],
                trimmed_crop_rgb_sha256=self.bottom_sha,dark_threshold=170,trimmed_dark_pixels=0,affected_fragment_overlaps=[],
                affected_ocr_overlaps=[dict(asset_id='viewer-173',line_id='viewer-173/ocr/109',original_bbox=[603,1088,1051,1113],coverage_status='EXCLUDED')],
                reason='Fixed threshold 170 finds zero dark pixels in only the removed bottom-edge row; still unverified.',verification_status='UNVERIFIED')],
            blocks=[dict(block_id='q4-answer',bbox=[620,1055,690,1088],source_fragment_ids=FRAGMENTS,
                runs=[dict(format='plain',text='2或'),dict(format='latex',text=r'\frac{25}{8}')],note='Explicit source-inspected draft, not human verified')])

    def test_real_q4_geometry_revision_replays_pixels_in_apply_quality_and_independent_audit(self):
        self.assertEqual(self.trim_dark,0)
        before=copy.deepcopy((self.e,self.g,self.c));plan=producer.make_revision_plan(self.e,self.g,self.c,[self.operation()],self.author)
        app=producer.apply_content_revision(self.e,self.g,self.c,plan,source_path=self.source)
        check=producer.build_content_quality(self.e,self.g,self.c,plan,app,self.review,source_path=self.source)
        self.assertEqual((plan['schema_version'],app['schema_version'],app['payload']['graph']['schema_version'],check['schema_version']),
            ('b-content-revision-plan-trial/0.3','b-content-revision-application-trial/0.3','b-graph-trial/0.8','b-check-trial/0.8'))
        answer=next(a for a in app['payload']['graph']['payload']['answers']if a['answer_id']==Q4)
        original=next(a for a in self.g['payload']['answers']if a['answer_id']==Q4)
        self.assertEqual(answer['text'],r'2或\frac{25}{8}');self.assertEqual(answer['fragments'],original['fragments'])
        self.assertEqual(app['payload']['source_geometry_receipts'][0]['trimmed_crop_rgb_sha256'],self.trim_sha)
        issues=[i for i in check['payload']['issues']if i['code']=='CONTENT_REGION_SOURCE_GEOMETRY_DRAFT_UNVERIFIED']
        self.assertEqual(len(issues),1);self.assertEqual(issues[0]['scope_id'],Q4);self.assertFalse(check['payload']['transcription_verified'])
        self.assertTrue(consumer.audit_content_application(self.e,self.g,self.c,plan,app,source_path=self.source)['payload']['accepted'])
        self.assertTrue(consumer.audit_content_quality(self.e,self.g,self.c,plan,app,self.review,check,source_path=self.source)['payload']['accepted'])
        self.assertEqual((self.e,self.g,self.c),before)
        self.assertFalse(consumer.audit_content_application(self.e,self.g,self.c,plan,app)['payload']['accepted'])

    def test_fixed_policy_arbitrary_trim_incomplete_conflict_and_old_schema_reject(self):
        faults=[]
        def threshold(op):op['source_geometry_revisions'][0]['dark_threshold']=0
        def float_threshold(op):op['source_geometry_revisions'][0]['dark_threshold']=170.0
        def bool_dark(op):op['source_geometry_revisions'][0]['trimmed_dark_pixels']=False
        def arbitrary(op):op['source_geometry_revisions'][0]['revised_bbox']=[664,1055,690,1071]
        def incomplete(op):op['source_geometry_revisions'][0]['affected_fragment_overlaps']=[]
        def original(op):op['source_geometry_revisions'][0]['original_bbox'][1]=1050
        faults=[threshold,float_threshold,bool_dark,arbitrary,incomplete,original]
        for fault in faults:
            op=self.operation();fault(op)
            with self.subTest(fault=fault.__name__),self.assertRaises(ValueError):producer.make_revision_plan(self.e,self.g,self.c,[op],self.author)
        plan=producer.make_revision_plan(self.e,self.g,self.c,[self.operation()],self.author)
        plan['schema_version']='b-content-revision-plan-trial/0.2';resign(plan)
        with self.assertRaises(ValueError):producer.validate_revision_plan(plan,self.e,self.g,self.c)

    def test_forged_zero_dark_receipt_is_rejected_by_execution_and_independent_audit(self):
        op=self.operation();op['source_geometry_revisions'][0]['trimmed_crop_rgb_sha256']='0'*64
        plan=producer.make_revision_plan(self.e,self.g,self.c,[op],self.author)
        with self.assertRaisesRegex(ValueError,'zero-dark'):producer.apply_content_revision(self.e,self.g,self.c,plan,source_path=self.source)
        valid=producer.make_revision_plan(self.e,self.g,self.c,[self.operation()],self.author)
        app=producer.apply_content_revision(self.e,self.g,self.c,valid,source_path=self.source)
        audit=consumer.audit_content_application(self.e,self.g,self.c,plan,app,source_path=self.source)
        self.assertFalse(audit['payload']['accepted']);self.assertTrue(any('zero-dark' in str(i['detail'])for i in audit['payload']['issues']))

    def test_geometry_audit_reopens_pixels_without_producer_validation(self):
        plan=producer.make_revision_plan(self.e,self.g,self.c,[self.operation()],self.author)
        app=producer.apply_content_revision(self.e,self.g,self.c,plan,source_path=self.source)
        check=producer.build_content_quality(self.e,self.g,self.c,plan,app,self.review,source_path=self.source)
        with patch.object(producer,'validate_revision_plan',side_effect=AssertionError('producer validator')), \
                patch.object(producer,'apply_content_revision',side_effect=AssertionError('producer apply')), \
                patch.object(producer,'build_content_quality',side_effect=AssertionError('producer quality')):
            self.assertTrue(consumer.audit_content_application(self.e,self.g,self.c,plan,app,source_path=self.source)['payload']['accepted'])
            self.assertTrue(consumer.audit_content_quality(self.e,self.g,self.c,plan,app,self.review,check,source_path=self.source)['payload']['accepted'])

    def test_independent_consumer_rejects_geometry_faults(self):
        valid=producer.make_revision_plan(self.e,self.g,self.c,[self.operation()],self.author)
        app=producer.apply_content_revision(self.e,self.g,self.c,valid,source_path=self.source)
        faults=[]
        def missing_ocr(op):op['source_geometry_revisions'][1]['affected_ocr_overlaps']=[]
        def arbitrary(op):op['source_geometry_revisions'][0]['revised_bbox']=[664,1055,690,1071]
        def ink(op):
            op['source_geometry_revisions'][0]['trimmed_bbox']=[663,1051,690,1056]
            op['source_geometry_revisions'][0]['revised_bbox']=[663,1056,690,1071]
        def original(op):op['source_geometry_revisions'][0]['original_bbox'][1]=1050
        def duplicate(op):op['source_geometry_revisions'].append(copy.deepcopy(op['source_geometry_revisions'][0]))
        def empty(op):op['source_geometry_revisions']=[]
        def bool_dark(op):op['source_geometry_revisions'][0]['trimmed_dark_pixels']=False
        def float_threshold(op):op['source_geometry_revisions'][0]['dark_threshold']=170.0
        for fault in (missing_ocr,arbitrary,ink,original,duplicate,empty,bool_dark,float_threshold):
            op=self.operation();fault(op);plan=copy.deepcopy(valid);plan['payload']['operations'][-1]=op;resign(plan)
            audit=consumer.audit_content_application(self.e,self.g,self.c,plan,app,source_path=self.source)
            with self.subTest(fault=fault.__name__):self.assertFalse(audit['payload']['accepted'])

    def test_malformed_boxes_fail_with_value_error(self):
        op=self.operation();op['source_geometry_revisions'][0]['original_bbox']=[]
        with self.assertRaises(ValueError):producer.make_revision_plan(self.e,self.g,self.c,[op],self.author)


if __name__=='__main__':unittest.main()
