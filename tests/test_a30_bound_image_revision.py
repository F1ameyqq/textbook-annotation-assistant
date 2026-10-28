"""Fresh ordinary-review integration for revising an image without duplication."""
from pathlib import Path
import copy,hashlib,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.store import Store,Hold
from annotation.customer.prepare import prepare
from annotation.customer.review import CustomerReviewWorkspace
from annotation.recognition.content_review import ReviewConflict

class BoundImageRevision(unittest.TestCase):
 def test_revision_keeps_prior_pixels_provenance_and_requires_current_unsaved_image(self):
  from PIL import Image,ImageDraw
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);question=root/'fresh-square.png';answer=root/'fresh-square-answer.png'
   image=Image.new('RGB',(800,960),'white');draw=ImageDraw.Draw(image)
   draw.rectangle((265,255,420,420),outline='black',width=3);image.save(question)
   Image.new('RGB',(800,960),'white').save(answer)
   raw_hash=hashlib.sha256(question.read_bytes()).hexdigest();store=Store(root/'workspace')
   def lines(store,page,book,**kwargs):
    return [{'text':'1. 观察右图并说明边的关系。' if page['role']=='question' else '1. 四边相等。',
      'bbox':[35,40,650,75],'score':.99}],'SYNTHETIC_ONLY_NO_MODEL'
   with patch('annotation.customer.prepare.ocr_page',side_effect=lines):
    job=prepare(store,book='9913042',lesson='Fresh bound-image revision',question_files=[question],answer_files=[answer],question_first_page=57,answer_first_page=138)
   ws=CustomerReviewWorkspace(store,job['id']);state=ws.state();key=state['answers'][0]['answer_id']
   self.assertTrue(state['customer']['source_occupancy'])
   self.assertIn('formula_regions',state['answers'][0])
   aid=state['answers'][0]['figures'][0]['asset_id']
   req={'expected_head':state['head'],'answer_id':key,'asset_id':aid,'zone':'question','bbox':[275,265,410,410],'source_checked':True}
   state=ws.bind_region(req);before=copy.deepcopy(store.job(job['id'])[0]['candidates'][0])
   region=next(f for f in state['answers'][0]['figures'] if f['content_type']=='image')
   update={**req,'expected_head':state['head'],'replace_region_id':region['region_id'],'bbox':[250,240,440,440]}
   with self.assertRaises(Hold):ws.bind_region({**update,'replace_region_id':'source-0'})
   with self.assertRaises(ReviewConflict):ws.bind_region({**update,'expected_head':req['expected_head']})
   self.assertEqual(store.job(job['id'])[0]['candidates'][0],before)
   result=ws.bind_region(update);after=store.job(job['id'])[0]['candidates'][0]
   self.assertEqual(len(after['frames']),len(before['frames']))
   images=[f for f in after['frames'] if f.get('content_type')=='image'];self.assertEqual(len(images),1)
   self.assertEqual(images[0]['bbox'],update['bbox'])
   self.assertEqual(images[0]['previous_bound_image'],next(f for f in before['frames'] if f.get('content_type')=='image'))
   self.assertEqual(after['content_status'],'NEEDS_REVIEW');self.assertIsNone(after['review'])
   self.assertEqual(after['zones'],before['zones']);self.assertEqual(hashlib.sha256(question.read_bytes()).hexdigest(),raw_hash)
   current,head=store.job(job['id']);current['candidates'][0]['platform_status']='ACCEPTED';current['candidates'][0]['acceptance_ref']='a'*64
   store.save_job(current,head,'SYNTHETIC_ACCEPTED_FIXTURE');held=store.job(job['id'])[1]
   with self.assertRaises(Hold):ws.bind_region({**update,'expected_head':held,'bbox':[245,235,445,445]})
   self.assertEqual(store.job(job['id'])[1],held)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
