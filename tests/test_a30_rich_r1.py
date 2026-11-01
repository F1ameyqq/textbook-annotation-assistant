"""New source image and TeX authoring controls, synthetic only."""
from pathlib import Path
import sys,copy,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import test_a30_customer as fixtures
from annotation.customer.store import Hold
from annotation.customer.review import CustomerReviewWorkspace
from annotation.customer.native_plan import make_plan
from annotation.customer.rich_content import zone_html

class RichR1(unittest.TestCase):
 setUp=fixtures.OrdinaryInputs.setUp
 image_job=fixtures.ImageAndProduction.image_job
 def test_ui_region_and_tex_flow_into_native_plan_with_source_identity(self):
  job,current=self.image_job();q=job['candidates'][0];ws=CustomerReviewWorkspace(self.store,job['id'])
  state=ws.state();state=ws.save({'expected_head':state['head'],'answer_id':q['key'],
   'changes':[{'key':q['key']+':question','text':'如图，计算 $x^2+4=13$。','format':'plain'}]})
  frame=q['frames'][0]
  state=ws.bind_region({'expected_head':state['head'],'answer_id':q['key'],'asset_id':frame['asset_id'],
    'bbox':[320,30,450,70],'zone':'question','source_checked':True})
  state=ws.confirm({'expected_head':state['head'],'answer_id':q['key'],'source_checked':True,'content_checked':True,
    'author':{'kind':'SYNTHETIC_TEST','id':'new-rich-control'}})
  updated=self.store.job(job['id'])[0]['candidates'][0];plan=make_plan(current,updated,job['lesson'])
  submitted=next(z for z in plan['payload']['ocr_submissions'] if z['zone']=='question')
  self.assertIn('$x^2+4=13$',submitted['ocr_result']);self.assertIn('<img src=',submitted['ocr_result'])
  image=next(f for f in plan['payload']['annotations_upsert'] if f['content_type']=='image')
  self.assertEqual(image['rect_bbox'],'320,30,450,70');self.assertIn(image['rect_id'],submitted['rect_ids'])
  self.assertEqual(updated['review']['operator']['kind'],'SYNTHETIC_TEST')
 def test_cross_question_image_and_unsafe_or_unbalanced_tex_block(self):
  job,_=self.image_job();q=job['candidates'][0];other=job['candidates'][1]['frames'][0]
  ws=CustomerReviewWorkspace(self.store,job['id'])
  with self.assertRaises(Hold):ws.bind_region({'expected_head':ws.state()['head'],'answer_id':q['key'],
   'asset_id':other['asset_id'],'bbox':other['bbox'],'zone':'question','source_checked':True})
  for text in ('$x','test \\frac{1}{2}',r'$\href{https://x}{y}$',r'$\frac{1}{2$'):
   with self.subTest(text=text),self.assertRaises(Hold):zone_html(text)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
