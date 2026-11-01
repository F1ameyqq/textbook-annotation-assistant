from pathlib import Path
import copy,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.quality import assess
from annotation.customer.prepare import candidate_hash
from annotation.customer.section_scope import heading

class LayoutR1(unittest.TestCase):
 def test_plain_image_quality_and_exceptions(self):
  from PIL import Image,ImageDraw
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'p.png';image=Image.new('L',(100,80),255);draw=ImageDraw.Draw(image);draw.rectangle((10,10,29,19),fill=0);image.save(path)
   pages=[{'asset_id':'p','kind':'image','raw_path':str(path)}]
   fragment={'fragment_id':'f','role':'stem','bbox':[10,10,30,20],'evidence_refs':['l']}
   graph={'payload':{'questions':[{'question_id':'q','selected_answer_id':'a','fragments':[fragment]}],
      'answers':[{'answer_id':'a','fragments':[]}]}}
   evidence={'content_hash':'bound','payload':{'pages':[{'ocr_lines':[{'line_id':'l','text':'Clear text','bbox':[10,10,30,20],'score':.99}]}]}}
   candidate={'key':'k','printed_number':'1','section_path':['Lesson'],'zones':{'question':'Clear text','answer':'Yes'},
      'frames':[{'asset_id':'p','zone':'question','bbox':[0,0,60,40],'source_fragment_ids':['f']}],
      'source_kind':'IMAGE_OCR','question_id':'q','issues':['IMAGE_TRANSCRIPTION_AND_FIGURES_REVIEW']}
   candidate['content_hash']=candidate_hash(candidate)
   for mode in ('normal','low','math','ink'):
    c=copy.deepcopy(candidate);e=copy.deepcopy(evidence)
    if mode=='low':e['payload']['pages'][0]['ocr_lines'][0]['score']=.8
    if mode=='math':c['zones']['question']='x² + 1 = 2';c['content_hash']=candidate_hash(c)
    if mode=='ink':draw.rectangle((40,10,49,19),fill=0);image.save(path)
    assess(c,graph,e,pages)
    self.assertEqual(c['content_status'],'READY_SOURCE_CHECKED' if mode=='normal' else 'NEEDS_REVIEW')
    self.assertFalse(c['quality']['human_transcription_verified'])
 def test_numbered_heading_alias_is_unique_target(self):
  self.assertEqual(heading('2 Ordinary triangle heading',['2 Ordinary triangle heading','Ordinary triangle heading','Ordinary triangle']), '2 Ordinary triangle heading')
 def test_detail_corroboration_requires_exact_old_coarse_text(self):
  from PIL import Image,ImageDraw
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'p.png';image=Image.new('L',(100,80),255);ImageDraw.Draw(image).rectangle((10,10,29,19),fill=0);image.save(path)
   pages=[{'asset_id':'p','kind':'image','raw_path':str(path)}]
   fragment={'fragment_id':'f','role':'stem','bbox':[10,10,30,20],'evidence_refs':['detail']}
   graph={'payload':{'questions':[{'question_id':'q','selected_answer_id':'a','fragments':[fragment]}],'answers':[{'answer_id':'a','fragments':[]}]}}
   c={'key':'k','printed_number':'1','section_path':['Lesson'],'zones':{'question':'Clear','answer':'A'},'frames':[{'asset_id':'p','zone':'question','bbox':[0,0,60,40],'source_fragment_ids':['f']}],
      'source_kind':'IMAGE_OCR','question_id':'q','issues':['IMAGE_TRANSCRIPTION_AND_FIGURES_REVIEW']};c['content_hash']=candidate_hash(c)
   for parent_text in ('1.A2.B','1.C2.B'):
    candidate=copy.deepcopy(c)
    e={'content_hash':'h','payload':{'pages':[{'ocr_lines':[{'line_id':'parent','text':parent_text,'score':.99}],
       'answer_detail_lines':[{'line_id':'detail','parent_line_id':'parent','text':'1.A','score':.94}]}]}}
    assess(candidate,graph,e,pages)
    self.assertEqual(candidate['content_status'],'READY_SOURCE_CHECKED' if parent_text=='1.A2.B' else 'NEEDS_REVIEW')

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
