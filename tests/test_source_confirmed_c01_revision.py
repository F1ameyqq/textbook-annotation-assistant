"""Synthetic shared-material revisions; no private book text or source images."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0,str(TOOLS))


def load(name):
    spec=importlib.util.spec_from_file_location(name,TOOLS/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


p=load('export_lesson_c01_b');r=load('revise_source_confirmed_c01_b');v=load('verify_source_confirmed_c01_b')


class SourceConfirmationRevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)/'revision'
        stream=io.BytesIO();Image.new('RGB',(80,180),'#ddd').save(stream,format='JPEG');raw=stream.getvalue()
        items=[];blocks=[]
        for i in range(4):
            key='task'+str(i);parts=['fill ____ ____ ','next ____ ____ ','last ____ ____ ']
            stem=''.join(parts) if i==0 else 'task '+str(i)
            items.append(dict(item_key=key,printed_number='16' if i==0 else None,parent_item_key=None,
                review_kind='B_MODEL_SOURCE_CONFIRMED',human_verified=False,fields=dict(question=stem,answer='answer '+str(i),choice=None,analysis=None)))
            for field,text,role,dy in (('question',stem,'stem',0),('answer','answer '+str(i),'answer',8)):
                if i==0 and field=='question':
                    for j,part in enumerate(parts,1):
                        blocks.append(dict(block_id='q16-task'+str(j),item_key=key,asset_id='image',bbox=[1,j,60,7+j],
                            content_type='text',text=part,field=field,role=role))
                    continue
                blocks.append(dict(block_id=key+'-'+field,item_key=key,asset_id='image',bbox=[1,1+i*18+dy,60,8+i*18+dy],
                    content_type='text',text=text,field=field,role=role))
        for i in range(8):
            blocks.append(dict(block_id='shared'+str(i),item_key=None,asset_id='image',bbox=[1,80+i*9,60,87+i*9],
                content_type='text',text='shared '+str(i),field='shared',role='shared_material'))
        spec=dict(schema='b-private-lesson-source-export-input/0.1',book_id='synthetic',scope_id='four-local-tasks',source_label='Synthetic source',
            source_input_sha256='1'*64,root_review_sha256='2'*64,crop_manifest_sha256='3'*64,evidence_mode='SYNTHETIC',
            review_kind='B_MODEL_SOURCE_CONFIRMED',assets=[dict(asset_id='image',viewer_page=1,path='unused',sha256=p.sha(raw),width=80,height=180)],
            items=items,blocks=blocks,exclusions=[],scope_notes=['Synthetic fixture only.'])
        self.old=p.build_delivery(spec,{'image':raw})
        b=json.loads(self.old['bundle.json']);d=json.loads(self.old['delivery.json']);k={a['kind']:a for a in b['artifacts']}
        graph=k['QuestionGraph'];shared=[f['fragment_id'] for f in graph['payload']['fragments'] if f['role']=='shared_material']
        for q in graph['payload']['questions'][1:]:q['shared_fragment_ids']=shared
        for relation in graph['payload']['answer_relations']:relation.update(status='UNRESOLVED',selected_fragment_ids=[])
        k['QuestionGraph']=p.seal(graph);check=k['CheckReport'];check['payload'].update(graph=p.ref(k['QuestionGraph']),subject=p.ref(k['QuestionGraph']))
        check['input_refs']=[p.ref(k[a['kind']]) for a in check['input_refs']];k['CheckReport']=p.seal(check)
        b['artifacts']=list(k.values());d['c01_graph_ref']=p.ref(k['QuestionGraph'])
        for binding in d['bindings']:binding['owner_id']='bq-'+binding['item_key'] if binding['item_key'] else 'material-local'
        self.old['bundle.json']=p.encode(b);self.old['delivery.json']=p.encode(d)
        graph=k['QuestionGraph']['payload'];src=k['SourceBundle']['payload'];ev=k['EvidenceBundle']['payload']
        self.review=dict(review_kind='B_MODEL_SOURCE_CONFIRMED',human_verified=False,a_owner_acceptance=False,content_issues=[],
            predecessor_bundle_sha256=p.sha(self.old['bundle.json']),
            predecessor_members=[dict(path=n,bytes=len(b),sha256=p.sha(b)) for n,b in sorted(self.old.items())],
            source_asset_sha256={a['asset_id']:a['sha256'] for a in src['assets']},confirmed_region_ids=[x['region_id'] for x in ev['regions']],
            answer_confirmations=[dict(question_id=a['question_id'],selected_fragment_ids=a['candidate_fragment_ids'],
                disposition='B_MODEL_SOURCE_CONFIRMED',source_reason='Synthetic source-bound review fixture.') for a in graph['answer_relations']],
            local_directories=[dict(directory_id='local',parent_id=None,label='Synthetic local directory')],
            question_directories={q['question_id']:'local' for q in graph['questions']},asset_directories={'image':'local'})
        self.review['source_text_changes']=[]
        regions={x['region_id']:x for x in ev['regions']};proofs={x['region_id']:x for x in d['source_proofs']}
        for binding in d['bindings']:
            if binding['block_id'] not in r.LABEL_RESTORATIONS:continue
            prefix=r.LABEL_RESTORATIONS[binding['block_id']];reg=regions[binding['region_id']];proof=proofs[binding['region_id']]
            runs=copy.deepcopy(binding['runs']);runs[0]['text']=prefix+runs[0]['text']
            self.review['source_text_changes'].append(dict(operation='RESTORE_PRINTED_SUBQUESTION_LABEL',block_id=binding['block_id'],
                region_id=binding['region_id'],prefix=prefix,before_text=reg['text'],after_text=prefix+reg['text'],
                before_runs=binding['runs'],after_runs=runs,asset_id='image',source_sha256=reg['box']['image']['sha256'],
                bbox=reg['box']['bbox'],crop_path=proof['path'],crop_png_sha256=proof['sha256'],crop_rgb_sha256=proof['rgb_sha256']))

    def write(self,blobs=None):
        blobs=r.revise(self.old,self.review) if blobs is None else blobs
        p.write_delivery(self.folder,blobs)
        return blobs

    def test_four_selected_three_users_share_eight_fragments_and_null_blanks(self):
        self.write();result=v.verify(self.folder)
        self.assertEqual((result['questions'],result['selected_answer_relations'],result['shared_fragments'],result['shared_material_users'],result['null_blanks']),(4,4,8,3,6))
        self.assertEqual(result['source_bound_label_restorations'],3)

    def test_frozen_revision_rebuilds_byte_for_byte(self):
        blobs=self.write();reconstructed=r.predecessor_files(blobs)
        self.assertEqual(reconstructed,self.old)
        self.assertEqual(blobs,r.revise(reconstructed,json.loads(blobs['current-review.json']),json.loads(blobs['generation.json'])))

    def test_wrong_predecessor_rejected(self):
        self.review['predecessor_bundle_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'PREDECESSOR'):r.revise(self.old,self.review)

    def test_cross_question_answer_rejected(self):
        self.review['answer_confirmations'][0]['selected_fragment_ids']=self.review['answer_confirmations'][1]['selected_fragment_ids']
        with self.assertRaisesRegex(ValueError,'OWNED_ANSWER'):r.revise(self.old,self.review)

    def test_missing_region_confirmation_rejected(self):
        self.review['confirmed_region_ids'].pop()
        with self.assertRaisesRegex(ValueError,'REGION_CONFIRMATION'):r.revise(self.old,self.review)

    def test_duplicate_confirmation_rejected(self):
        self.review['answer_confirmations'][1]=copy.deepcopy(self.review['answer_confirmations'][0])
        with self.assertRaisesRegex(ValueError,'CONFIRMATION_SCOPE'):r.revise(self.old,self.review)

    def test_fake_human_acceptance_rejected(self):
        self.review['human_verified']=True
        with self.assertRaisesRegex(ValueError,'MODEL_CONTENT'):r.revise(self.old,self.review)

    def test_unresolved_content_cannot_be_declared_ready(self):
        self.review['content_issues']=['actual missing text']
        with self.assertRaisesRegex(ValueError,'MODEL_CONTENT'):r.revise(self.old,self.review)

    def test_original_image_tamper_rejected(self):
        self.write();(self.folder/'assets/image.jpg').write_bytes(b'not original')
        with self.assertRaisesRegex(ValueError,'PREDECESSOR_MEMBER_HASH'):v.verify(self.folder)

    def test_history_overwrite_rejected(self):
        self.write();(self.folder/'history/v2/bundle.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'PREDECESSOR_MEMBER_HASH'):v.verify(self.folder)

    def test_rich_blank_value_mutation_rejected(self):
        self.write();d=v.read(self.folder/'delivery.json')
        blank=next(x for b in d['bindings'] for x in b['runs'] if x['format']=='blank');blank['value']='filled'
        (self.folder/'delivery.json').write_bytes(p.encode(d))
        with self.assertRaisesRegex(ValueError,'RICH_TEXT'):v.verify(self.folder)

    def test_frozen_path_escape_rejected(self):
        blobs=self.write();review=json.loads(blobs['current-review.json']);review['predecessor_members'][0]['path']='../escape'
        blobs['current-review.json']=p.encode(review)
        with self.assertRaisesRegex(ValueError,'PREDECESSOR_PATH'):r.predecessor_files(blobs)

    def test_missing_printed_label_fix_is_a_real_content_gap(self):
        self.review['source_text_changes'].pop()
        with self.assertRaisesRegex(ValueError,'MISSING_LABEL'):r.revise(self.old,self.review)

    def test_label_whitelist_cannot_change_words_or_formulas(self):
        self.review['source_text_changes'][0]['after_text']+='arbitrary addition'
        with self.assertRaisesRegex(ValueError,'LABEL_ONLY_DELTA'):r.revise(self.old,self.review)

    def test_label_whitelist_cannot_fill_blank_or_alter_later_run(self):
        change=self.review['source_text_changes'][0]
        blank=next(run for run in change['after_runs'] if run['format']=='blank');blank['value']='filled'
        with self.assertRaisesRegex(ValueError,'LABEL_ONLY_DELTA'):r.revise(self.old,self.review)

    def test_label_change_must_bind_the_original_crop_digest(self):
        self.review['source_text_changes'][0]['crop_png_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'LABEL_ONLY_DELTA'):r.revise(self.old,self.review)


if __name__=='__main__':unittest.main()
