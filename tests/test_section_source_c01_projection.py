"""Synthetic local source projection, math and column-flow boundary tests."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

TOOLS=Path(__file__).resolve().parents[1]/'tools'


def load(name):
    s=importlib.util.spec_from_file_location(name,TOOLS/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


p=load('export_lesson_c01_b');v=load('verify_lesson_c01_b');j=load('project_section_source_c01_b')


class SectionProjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        (self.root/'assets').mkdir();(self.root/'crops').mkdir();(self.root/'observations').mkdir()
        im=Image.new('RGB',(200,200),'#cbd3da');im.putpixel((2,2),(255,0,0));stream=io.BytesIO();im.save(stream,format='JPEG');self.raw=stream.getvalue()
        (self.root/'assets/viewer-14.jpg').write_bytes(self.raw)
        with Image.open(io.BytesIO(self.raw)) as saved:self.image=saved.convert('RGB')
        for name in ('ocr.json','native.json'):(self.root/'observations'/name).write_bytes(b'{"private":"SHOULD_NOT_LEAK"}')
        (self.root/'file-manifest.json').write_bytes(b'{"members":[]}')
        self.manifest_sha=j.sha((self.root/'file-manifest.json').read_bytes())
        observations=dict(relative_path='observations/ocr.json',sha256=j.sha((self.root/'observations/ocr.json').read_bytes()),observation='SYNTHETIC')
        source=dict(viewer_page=14,source_image_index=13,printed_page_label=6,dimensions=[200,200],
            image=dict(path='C:/Private/source.jpg',relative_path='assets/viewer-14.jpg',sha256=j.sha(self.raw),bytes=len(self.raw)),
            existing_OCR=observations,native_metadata=dict(relative_path='observations/native.json',sha256=j.sha((self.root/'observations/native.json').read_bytes())))
        self.spec=dict(schema='Section2Q1Q15CompleteSourceSpec/v1',book_id='synthetic',section_title='Synthetic section',item_count=5,
            unresolved_source_uncertainties=[],sources=[source],regions=[],items=[],source_transcription_convention='Synthetic fixture only.',excluded_items=['Q16','reading tasks'])
        self.splits={}
        self.add('section2-q7',['Given 3/2.\n','Wrong work: a²+b²≠c².'],['Correct: a²+c²=b².'],wrong=True)
        self.add('section2-q9',['Choose squared values.'],['D'],choices=['A. 1','B. 0.3','C. 8²，15²，17²','D. 5'])
        self.add('section2-q13',['Choose false distance.'],['D'],choices=['A. 1','B. 2','C. 3','D. 5/2'],diagram=True)
        self.add('section2-q15',['CF=(1/4)CD.'],['Proof ∠B=∠C=','∠D=90°; AE²+EF²=AF².'],diagram=True)
        self.add('section2-q4',['S₁=3, S₂=2, S₃=1, result ____°.'],['90'],blank=True)
        (self.root/'source-spec.json').write_bytes(j.encode(self.spec))

    def add(self,key,questions,answers,choices=None,diagram=False,wrong=False,blank=False):
        regions=[]
        def region(role,index,text):
            rid=key+'.'+role+'.'+str(index);y=1+len(self.spec['regions'])*7;box=[1,y,80,y+6]
            crop=self.image.crop(box);stream=io.BytesIO();crop.save(stream,format='PNG');raw=stream.getvalue();path='crops/'+rid+'.png';(self.root/path).write_bytes(raw)
            r=dict(region_id=rid,item_key=key,viewer_page=14,source_image_index=13,role=role,bbox=box,source_image_sha256=j.sha(self.raw),
                source_dimensions=[200,200],crop=dict(relative_path=path,sha256=j.sha(raw),dimensions=list(crop.size),rgb_sha256=j.sha(crop.tobytes())),
                existing_raw_observations=[dict(raw_text='unapproved synthetic row',row_index=len(self.spec['regions']))],model_reviewed_text=text if role=='choice' else None)
            self.spec['regions'].append(r);return rid
        qids=[region('question',i,t) for i,t in enumerate(questions,1)]
        aids=[region('answer',i,t) for i,t in enumerate(answers,1)]
        options=[dict(label='ABCD'[i],text=text,region_id=region('choice',i,text)) for i,text in enumerate(choices or [])]
        diagrams=[region('diagram',1,None)] if diagram else []
        self.spec['items'].append(dict(item_key=key,printed_number=int(key.split('q')[-1]),question_type='single_choice' if choices else 'fill_blank' if blank else 'free_response',
            question_text=''.join(questions),answer_text=''.join(answers),analysis_text=None,choices=options,native_identity=None,unresolved_source_uncertainties=[],
            question_region_ids_in_reading_order=qids,answer_region_ids_in_reading_order=aids,diagram_region_ids=diagrams,
            blank_slots=[dict(blank_id=key+'-blank',value=None)] if blank else [],intentional_wrong_solution_in_question=wrong,
            source_flow_note='left bottom to right top' if len(questions)>1 or len(answers)>1 else None,model_corrections_against_existing_OCR=['Synthetic review.']))
        for field,ids,texts in (('question',qids,questions),('answer',aids,answers)):
            if len(texts)>1:self.splits[key+'.'+field]=dict(region_ids=ids,original_full_text=''.join(texts),texts=texts,source_reason='Synthetic column binding.')

    def project(self):
        result=j.project(self.spec,self.root,self.splits,'1'*64,self.manifest_sha)
        result['evidence_mode']='SYNTHETIC'
        return result

    def build(self,spec=None):
        blobs=p.build_delivery(self.project() if spec is None else spec,{'viewer-14':self.raw})
        target=self.root/'delivery';p.write_delivery(target,blobs);return target,blobs

    def test_lossless_source_projection_and_independent_readback(self):
        root,blobs=self.build();result=v.verify(root)
        self.assertEqual((result['questions'],result['selected_answer_relations'],result['unfilled_question_blanks']),(5,5,1))
        self.assertTrue(all(b'SHOULD_NOT_LEAK' not in raw and b'C:/Private' not in raw for name,raw in blobs.items() if name.endswith('.json')))

    def test_question_wrong_solution_and_answer_columns_remain_distinct(self):
        spec=self.project();q7=next(i for i in spec['items'] if i['item_key']=='section2-q7')
        self.assertIn('a²+b²≠c²',q7['fields']['question']);self.assertIn('a²+c²=b²',q7['fields']['answer'])
        self.assertEqual([b['block_id'] for b in spec['blocks'] if b['item_key']=='section2-q15' and b['field']=='answer'],self.spec['items'][3]['answer_region_ids_in_reading_order'])

    def test_source_squares_and_fraction_have_explicit_semantics(self):
        spec=self.project();runs=[r for b in spec['blocks'] for r in b['rich_runs'] if r['format']=='latex']
        self.assertIn(dict(format='latex',source_text='8²',text='8^{2}'),runs)
        self.assertIn(dict(format='latex',source_text='5/2',text=r'\frac{5}{2}'),runs)

    def test_missing_cross_column_evidence_rejected(self):
        self.splits.pop('section2-q7.question')
        with self.assertRaisesRegex(ValueError,'CROSS_COLUMN'):self.project()

    def test_reversed_column_text_rejected(self):
        self.splits['section2-q15.answer']['texts'].reverse()
        with self.assertRaisesRegex(ValueError,'LOSSLESS'):self.project()

    def test_changed_original_crop_rejected(self):
        target=self.root/self.spec['regions'][0]['crop']['relative_path']
        with Image.open(target) as image:changed=image.convert('RGB')
        changed.putpixel((0,0),(0,255,0));changed.save(target,format='PNG')
        with self.assertRaisesRegex(ValueError,'ORIGINAL_REGION_CROP_PIXELS'):self.project()

    def test_source_role_cannot_be_reassigned(self):
        self.spec['regions'][0]['item_key']='different-owner'
        with self.assertRaisesRegex(ValueError,'OWNER_ROLE'):self.project()

    def test_source_blank_cannot_be_filled(self):
        self.spec['items'][-1]['blank_slots'][0]['value']='90'
        with self.assertRaisesRegex(ValueError,'BLANKS_MUST_BE_NULL'):self.project()

    def test_no_native_identity_promotion(self):
        self.spec['items'][0]['native_identity']='server-id'
        with self.assertRaisesRegex(ValueError,'WITHOUT_NATIVE'):self.project()

    def test_math_run_cannot_drop_a_square(self):
        spec=self.project();run=next(r for b in spec['blocks'] for r in b['rich_runs'] if r.get('source_text')=='8²');run['text']='8'
        with self.assertRaisesRegex(ValueError,'MATH_SEMANTICS'):self.build(spec)

    def test_math_run_cannot_invert_fraction(self):
        spec=self.project();run=next(r for b in spec['blocks'] for r in b['rich_runs'] if r.get('source_text')=='5/2');run['text']=r'\frac{2}{5}'
        with self.assertRaisesRegex(ValueError,'MATH_SEMANTICS'):self.build(spec)

    def test_independent_verifier_checks_formula_not_just_c01_digest(self):
        root,blobs=self.build();side=json.loads((root/'delivery.json').read_bytes());run=next(r for b in side['bindings'] for r in b['runs'] if r.get('source_text')=='5/2');run['text']=r'\frac{2}{5}'
        (root/'delivery.json').write_bytes(p.encode(side))
        with self.assertRaisesRegex(ValueError,'FORMULA_SEMANTICS'):v.verify(root)

    def test_frozen_semantic_delivery_byte_identity(self):
        root,blobs=self.build();basis=json.loads(blobs['basis.json']);generation=json.loads(blobs['generation.json'])
        self.assertEqual(blobs,p.build_delivery(basis,{'viewer-14':self.raw},generation))

    def test_original_manifest_hash_required(self):
        self.manifest_sha='0'*64
        with self.assertRaisesRegex(ValueError,'MANIFEST_HASH'):self.project()


if __name__=='__main__':unittest.main()
