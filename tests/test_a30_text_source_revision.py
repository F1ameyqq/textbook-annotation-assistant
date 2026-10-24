"""New synthetic boundary repair: ordinary UI, preserved source and saved peer."""
from pathlib import Path
import copy,hashlib,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
import test_a30_customer as fixtures
from annotation.customer.review import CustomerReviewWorkspace
from annotation.customer.prepare import candidate_hash
from annotation.customer.native_plan import make_plan
from annotation.customer.store import Hold
from annotation.recognition.content_review import ReviewConflict

class TextSourceRevision(unittest.TestCase):
    setUp=fixtures.OrdinaryInputs.setUp
    image_job=fixtures.ImageAndProduction.image_job
    def test_native_overlap_message_locates_customer_review_target(self):
        job,current=self.image_job();first,second=job['candidates']
        current,_=fixtures.apply_native(current,make_plan(current,first,job['lesson']),916)
        frame=next(f for f in second['frames'] if f['zone']=='answer');frame['bbox']=[30,58,300,100]
        second['content_hash']=candidate_hash(second);second['review']['content_hash']=second['content_hash']
        with self.assertRaisesRegex(Hold,'第5题.*答案.*来源页109.*来源框2.*返回本题审校'):
            make_plan(current,second,job['lesson'])

    def test_correction_within_initial_bounds_retains_both_adjustments(self):
        job,current=self.image_job();first,second=job['candidates']
        current,_=fixtures.apply_native(current,make_plan(current,first,job['lesson']),915)
        index=next(i for i,f in enumerate(second['frames']) if f['zone']=='answer')
        second['frames'][index]['bbox']=[30,58,300,100]
        second['content_hash']=candidate_hash(second);second['review']['content_hash']=second['content_hash']
        _,head=self.store.job(job['id']);self.store.save_job(job,head,'SYNTHETIC_INITIAL_BOUNDS_FIXTURE')
        ws=CustomerReviewWorkspace(self.store,job['id']);state=ws.state();original=copy.deepcopy(second['frames'][index])
        request={'expected_head':state['head'],'answer_id':second['key'],'asset_id':original['asset_id'],'zone':'answer',
            'bbox':[30,63,300,98],'replace_text_region_id':'source-'+str(index),'source_checked':True,'text_complete_checked':True}
        state=ws.bind_region(request)
        for bad in ([29,61,300,100],[30,59,300,100],[30,61,301,100]):
            with self.assertRaises(Hold):ws.bind_region({**request,'expected_head':state['head'],'bbox':bad})
            self.assertEqual(self.store.job(job['id'])[1],state['head'])
        state=ws.bind_region({**request,'expected_head':state['head'],'bbox':[30,61,300,100]})
        revised=self.store.job(job['id'])[0]['candidates'][1];frame=revised['frames'][index]
        self.assertEqual(frame['bbox'],[30,61,300,100]);self.assertEqual(len(frame['text_source_adjustment_history']),2)
        self.assertEqual(frame['text_source_adjustment_history'][0]['previous_source_frame'],original)
        self.assertEqual(frame['text_source_adjustment_history'][1]['previous_source_frame']['bbox'],[30,63,300,98])
        self.assertEqual(revised['zones'],second['zones']);self.assertIsNone(revised['review'])
        with self.assertRaises(Hold):make_plan(current,revised,job['lesson'])
        ws.confirm({'expected_head':state['head'],'answer_id':second['key'],'source_checked':True,'content_checked':True,
                    'author':{'kind':'SYNTHETIC_TEST','id':'initial-boundary-correction'}})
        make_plan(current,self.store.job(job['id'])[0]['candidates'][1],job['lesson'])

    def test_tightening_clears_overlap_only_after_explicit_reconfirmation(self):
        job,current=self.image_job();first,second=job['candidates']
        current,_=fixtures.apply_native(current,make_plan(current,first,job['lesson']),914)
        first['platform_status']='SAVED_AND_INDEPENDENTLY_READ_BACK';first['acceptance_ref']='synthetic-protected-peer'
        index=next(i for i,f in enumerate(second['frames']) if f['zone']=='answer')
        second['frames'][index]['bbox']=[30,58,300,100]
        second['content_hash']=candidate_hash(second);second['review']['content_hash']=second['content_hash']
        _,head=self.store.job(job['id']);self.store.save_job(job,head,'SYNTHETIC_COARSE_SOURCE_FIXTURE')
        peer=copy.deepcopy(first);original=copy.deepcopy(second);evidence_hash=job['evidence_ref']
        source_hashes={p['raw_path']:hashlib.sha256(Path(p['raw_path']).read_bytes()).hexdigest() for p in job['pages']}
        with self.assertRaises(Hold):make_plan(current,second,job['lesson'])
        ws=CustomerReviewWorkspace(self.store,job['id']);state=ws.state()
        request={'expected_head':state['head'],'answer_id':second['key'],'asset_id':second['frames'][index]['asset_id'],
            'zone':'answer','bbox':[30,62,300,100],'replace_text_region_id':'source-'+str(index),
            'source_checked':True,'text_complete_checked':True}
        for delta in ({'bbox':[30,58,300,100]},{'bbox':[29,62,300,100]}, {'bbox':[30,59,300,100]},
                      {'text_complete_checked':False},{'zone':'question'},{'replace_region_id':'source-0'},
                      {'source_transfers':[]},{'replace_text_region_id':'source-99'}):
            with self.subTest(delta=delta),self.assertRaises(Hold):ws.bind_region({**request,**delta})
            self.assertEqual(self.store.job(job['id'])[1],state['head'])
        with self.assertRaises(ReviewConflict):ws.bind_region({**request,'expected_head':'stale-head'})
        revised_state=ws.bind_region(request);revised=self.store.job(job['id'])[0];candidate=revised['candidates'][1]
        self.assertEqual(revised['candidates'][0],peer);self.assertEqual(candidate['zones'],original['zones'])
        self.assertEqual(candidate['frames'][index]['source_fragment_ids'],original['frames'][index]['source_fragment_ids'])
        self.assertEqual(candidate['frames'][index]['text_source_adjustment_history'][-1]['previous_source_frame'],original['frames'][index])
        self.assertEqual(candidate['content_status'],'NEEDS_REVIEW');self.assertIsNone(candidate['review'])
        self.assertEqual(revised['evidence_ref'],evidence_hash)
        with self.assertRaises(Hold):make_plan(current,candidate,job['lesson'])
        ws.confirm({'expected_head':revised_state['head'],'answer_id':second['key'],'source_checked':True,'content_checked':True,
            'author':{'kind':'SYNTHETIC_TEST','id':'text-source-boundary-control'}})
        final,head=self.store.job(job['id']);plan=make_plan(current,final['candidates'][1],job['lesson'])
        self.assertEqual(plan['schema'],'CustomerNativeInsertPlan/v1')
        self.assertIn('30,62,300,100',[f['rect_bbox'] for f in plan['payload']['annotations_upsert']])
        self.assertEqual(final['candidates'][0],peer)
        with self.assertRaises(Hold):ws.bind_region({**request,'expected_head':head,'answer_id':first['key'],'bbox':[30,42,300,59]})
        self.assertEqual(self.store.job(job['id'])[1],head)
        self.assertEqual(source_hashes,{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in source_hashes})

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
