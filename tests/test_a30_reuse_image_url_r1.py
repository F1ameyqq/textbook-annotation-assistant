from pathlib import Path
import copy,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import test_a30_customer as fixtures
from annotation.customer.store import Hold
from annotation.customer.native_plan import make_plan
from annotation.customer.legacy_ledger import existing_candidate
from annotation.customer.review import CustomerReviewWorkspace
from annotation.customer.rich_content import zone_html

class ImageUrlR1(unittest.TestCase):
 setUp=fixtures.OrdinaryInputs.setUp
 image_job=fixtures.ImageAndProduction.image_job
 def test_native_image_url_origin_crop_and_extra_query_are_source_bound(self):
  job,empty=self.image_job();q=job['candidates'][0];ws=CustomerReviewWorkspace(self.store,job['id']);state=ws.state()
  state=ws.bind_region({'expected_head':state['head'],'answer_id':q['key'],'asset_id':q['frames'][0]['asset_id'],
   'bbox':[330,32,448,72],'zone':'question','source_checked':True})
  ws.confirm({'expected_head':state['head'],'answer_id':q['key'],'source_checked':True,'content_checked':True})
  candidate=self.store.job(job['id'])[0]['candidates'][0];current,_=fixtures.apply_native(empty,make_plan(empty,candidate,job['lesson']),713)
  self.assertEqual(existing_candidate(current,candidate)['node_id'],'server-node-713')
  for change in [lambda u:u.replace('.aliyuncs.com/','.different.example/'),lambda u:u.replace('w_118','w_117'),lambda u:u+'&another=1']:
   altered=copy.deepcopy(current);record=altered['questions']['server-node-713']
   frames=record['annotations']['data'];figure=next(f for f in frames if f['content_type']=='image')
   figure['image_path']=change(figure['image_path'])
   next(f for f in altered['frames']['data'] if f['rect_id']==figure['rect_id'])['image_path']=figure['image_path']
   record['zones']['question']['data']['ocr_result']=zone_html(candidate['zones']['question'],[figure])
   with self.assertRaisesRegex(Hold,'图片地址|裁剪地址'):existing_candidate(altered,candidate)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
