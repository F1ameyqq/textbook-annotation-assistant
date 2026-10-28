"""New integrated delta cases, fresh synthetic inputs, no platform/model calls."""
from pathlib import Path
import copy,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.store import Store,Hold,encoded,digest
from annotation.customer.selection import select
from annotation.customer.native_delivery import check_display
from annotation.customer.production import produce,export_local
import test_a30_customer as fixtures
from annotation.customer.native_plan import make_plan


class FlowR1(unittest.TestCase):
 setUp=fixtures.OrdinaryInputs.setUp
 image_job=fixtures.ImageAndProduction.image_job
 def test_selected_ready_item_keeps_unrelated_exception_and_reuses_current_once(self):
  job,current=self.image_job();chosen=job['candidates'][0]
  plan=make_plan(current,chosen,job['lesson']);current,_=fixtures.apply_native(current,plan,301)
  job,head=self.store.job(job['id']);job['candidates'][1]['issues']=['LOW_OR_MISSING_OCR_CONFIDENCE']
  job['candidates'][1]['content_status']='NEEDS_REVIEW';job['status']='NEEDS_REVIEW'
  self.store.save_job(job,head)
  class Reader:
   processes=[]
   def capture(self,*a,**k):return current,{}
   def write_once(self,*a):raise AssertionError('existing record must not save')
  reader=Reader()
  produce(self.store,job['id'],{},selected_keys=[chosen['key']],transport_factory=lambda *a:reader)
  result,_=self.store.job(job['id']);self.assertEqual(result['remaining_unaccepted_count'],1)
  self.assertEqual(result['candidates'][1]['platform_status'],'NOT_RUN')
  self.assertEqual(result['candidates'][0]['platform_status'],'REUSED_CURRENT_EXISTING')
  produce(self.store,job['id'],{},selected_keys=[chosen['key']],transport_factory=lambda *a:(_ for _ in ()).throw(AssertionError('must reuse durable current read')))
  self.assertEqual(self.store.job(job['id'])[0]['candidates'][0]['platform_status'],'REUSED_ACCEPTED')
 def test_orphan_geometry_is_scoped_but_unknown_and_overlap_block(self):
  job,_=self.image_job();q=job['candidates'][0];frame=next(f for f in q['frames'] if f['zone']=='answer')
  evidence={'payload':{'pages':[{'asset_id':frame['asset_id'],'page_role':'answer','ocr_lines':[
    {'line_id':'unassigned-new','bbox':[30,400,150,425],'location':{'section_path':q['section_path']}}]}]}}
  job['evidence_ref']=self.store.put(evidence);job['issues']=[{'code':'UNASSIGNED_ANSWER_OCR_LINE','evidence_refs':['unassigned-new']}]
  self.assertEqual(select(self.store,job,[q['key']]),[q])
  evidence['payload']['pages'][0]['ocr_lines'][0]['bbox']=frame['bbox'];job['evidence_ref']=self.store.put(evidence)
  with self.assertRaises(Hold):select(self.store,job,[q['key']])
  job['issues']=[{'code':'UNSCOPED_SOURCE_LINES','evidence_refs':[]}]
  with self.assertRaises(Hold):select(self.store,job,[q['key']])
 def test_display_failure_recheck_does_not_export_or_save(self):
  job,_=self.image_job();job,head=self.store.job(job['id']);delivery=self.root/'new-delivery';delivery.mkdir()
  (delivery/'index.html').write_text('synthetic',encoding='utf-8')
  job['native_export_ref']=self.store.put({'output':str(delivery)});self.store.save_job(job,head)
  calls=[]
  def failure(*args):calls.append(args);return {'status':'DISPLAY_CHECK_FAILED','owned_os_release_confirmed':True}
  with self.assertRaises(Hold):check_display(self.store,job['id'],inspector=failure)
  with self.assertRaises(Hold):check_display(self.store,job['id'],inspector=failure)
  self.assertEqual(len(calls),1)
  def success(*args):calls.append(args);return {'status':'AUTOMATED_DISPLAY_CHECK_PASSED','owned_os_release_confirmed':True}
  self.assertEqual(check_display(self.store,job['id'],explicit_recheck=True,inspector=success),delivery)
  self.assertEqual(export_local(self.store,job['id']),delivery)
  self.assertEqual(check_display(self.store,job['id'],inspector=failure),delivery)
  self.assertEqual(len(calls),2)
 def test_dense_cached_number_anchors_split_only_at_observed_gutter(self):
  from PIL import Image,ImageDraw
  from annotation.customer.dense_answers import partition
  p=self.root/'new-dense.png';im=Image.new('L',(200,60),255);d=ImageDraw.Draw(im)
  for box in [(10,20,15,35),(25,20,35,35),(80,20,90,35),(100,20,120,35)]:d.rectangle(box,fill=0)
  im.save(p)
  page={'kind':'image','role':'answer','raw_path':str(p),'raw_sha256':'synthetic-sha'}
  line={'line_id':'new-row','text':'21.B22.36','bbox':[10,20,121,36],'score':.99,'location':{'column':0}}
  tokens=[{'line_id':'anchor1','parent_line_id':'new-row','text':'21','bbox':[10,20,16,36],'score':.99},
          {'line_id':'anchor2','parent_line_id':'new-row','text':'22','bbox':[80,20,91,36],'score':.99}]
  result,records=partition(page,[line],tokens)
  self.assertEqual([x['text'] for x in result],['21.B','22.36']);self.assertEqual(len(records),1)
  self.assertEqual(result[0]['bbox'][2],result[1]['bbox'][0])
  line['text']='21.B24.36';unchanged,records=partition(page,[line],tokens)
  self.assertEqual(unchanged,tokens);self.assertEqual(records,[])

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
