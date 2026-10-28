from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.store import Store,Hold,encoded,byte_hash,digest
from annotation.customer.source import ocr_page

class EngineHistoryR1(unittest.TestCase):
 def test_upgrade_reconciles_complete_failed_and_interrupted_original_source(self):
  for status in ['COMPLETE','FAILED_NO_RETRY','INTENT']:
   with self.subTest(status=status),tempfile.TemporaryDirectory() as temp:
    store=Store(Path(temp)/'workspace');book='993037';raw=b'unique synthetic OCR history source 20261024'
    sha=byte_hash(raw);engine={'name':'original-test-engine','version':'previous'};key=digest([book,sha,engine])
    page={'raw_sha256':sha,'width':300,'height':500,'asset_id':'test-engine-upgrade-page'}
    directory=store.root/'recognition'/key;directory.mkdir(parents=True)
    (directory/'original.png').write_bytes(raw)
    source={'schema_version':'b-source-trial/0.1','artifact_id':'customer-source-'+key[:24],
     'book_id':book,'scope_id':'image-'+sha,'assets':[{'path':'original.png','sha256':sha,'width':300,'height':500}]}
    (directory/'source.json').write_bytes(encoded(source));store.begin('recognition',key)
    lines=[{'text':'保留旧引擎的有效观察','bbox':[10,20,200,50],'score':.99}]
    if status=='COMPLETE':store.finish('recognition',key,status,{'raw_sha256':sha,'engine':engine,'lines':lines})
    elif status=='FAILED_NO_RETRY':store.finish('recognition',key,status,{'type':'OriginalFailure','message':'retained'})
    previous=store.operation('recognition',key)
    with patch('annotation.customer.source.engine_identity',side_effect=AssertionError('new engine must not gate old lookup')),patch('annotation.recognition.baseline.recognize',side_effect=AssertionError('OCR must remain zero')):
     if status=='COMPLETE':
      result,mode=ocr_page(store,page,book,allow_local_ocr=True);self.assertEqual(result,lines);self.assertEqual(mode,'CACHE')
      self.assertEqual(page['recognition_provenance']['engine'],engine)
      result[0]['text']='caller mutation';self.assertEqual(store.get(previous['output'])['lines'],lines)
     else:
      with self.assertRaisesRegex(Hold,'未完成或失败'):ocr_page(store,page,book,allow_local_ocr=True)
    self.assertEqual(store.operation('recognition',key),previous)
    with store.connect() as db:self.assertEqual(db.execute("SELECT count(*) FROM operations WHERE kind='recognition'").fetchone()[0],1)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
