from pathlib import Path
import sys,json,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.store import Store,encoded,byte_hash,digest
from annotation.customer import recognition_cache as cache
from annotation.recognition.baseline import digest as source_digest

class MigrationR1(unittest.TestCase):
 def test_packaged_partial_observation_preserves_original_provenance_too(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);store=Store(root/'workspace');book='935727'
   payload={'source':{'sha256':'f'*64,'width':400,'height':600},'crop':{'bbox':[0,0,100,100],'sha256':'a'*64},
    'ocr_lines':[{'text':'旧局部观察','bbox':[10,20,80,45],'score':.99}]}
   value={'schema_version':'b-continuation-fixture-trial/0.1','book_id':book,'payload':payload,
    'content_hash':source_digest(payload),'producer':{'module':'rapidocr_onnxruntime.RapidOCR'}}
   first=root/'partial-original.json';first.write_bytes(encoded(value));cache.import_evidence(store,first)
   second=root/'packaged-partial.json';second.write_bytes(first.read_bytes());cache.import_evidence(store,second)
   record=store.get(store.operation('historic-partial-recognition',digest([book,'f'*64]))['output'])
   self.assertEqual(record['provenance']['path'],str(first));self.assertEqual(record['coverage'],'CROP_ONLY')
 def test_packaged_bootstrap_reuses_same_raw_observation_without_replacing_provenance(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);store=Store(root/'workspace');book='935726'
   payload={'pages':[{'source':{'sha256':'e'*64,'width':400,'height':600},'ocr_lines':[{'text':'17. New synthetic migration','bbox':[10,20,300,45],'score':.99}]}]}
   evidence={'schema_version':'b-evidence-trial/0.2','book_id':book,'artifact_id':'new-migration-17','payload':payload,
    'content_hash':source_digest(payload),'producer':{'ocr_enabled':True}}
   first=root/'original.json';first.write_bytes(encoded(evidence));cache.import_evidence(store,first)
   app=root/'app';package=app/'runtime/customer-recognition'/book;package.mkdir(parents=True)
   copy=package/'retained.json';copy.write_bytes(first.read_bytes());(package/'registry.json').write_bytes(encoded({'book_id':book,'files':[{'filename':copy.name,'sha256':byte_hash(copy.read_bytes())}]}))
   with patch.object(cache,'__file__',str(app/'src/annotation/customer/recognition_cache.py')):
    cache.bootstrap(store,book);cache.bootstrap(store,book)
   record=store.get(store.operation('historic-recognition',digest([book,'e'*64]))['output'])
   self.assertEqual(record['provenance']['path'],str(first));self.assertFalse(record['content_approved'])
   with store.connect() as db:self.assertEqual(db.execute("SELECT count(*) FROM operations WHERE kind='recognition-migration' AND state='COMPLETE'").fetchone()[0],1)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
