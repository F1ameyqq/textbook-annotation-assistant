from pathlib import Path
import sys,importlib.util,unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('new_continuation_entry',ROOT/'tools/customer_section_prepare_once.py')
entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)

class ContinuationEntryR1(unittest.TestCase):
 def test_separate_activation_and_exact_finite_limits_before_resources(self):
  with self.assertRaisesRegex(ValueError,'NEW_ACTIVATION_REQUIRED'):entry.activated({'schema':'A30ContinuationPreparationAuthority/v1','activated':False})
  value={'schema':'A30ContinuationPreparationAuthority/v1','activated':True,'executor':'01a16bf6-ed2d-7950-b2c9-9df30e7e6bd6',
    'maximum_additional_pages':2,'limits':{'api_gets':8,'original_gets':2,'contexts':2,'navigations':2,'new_ocr_pages':2,'saves':0,'login':0,'retries':0}}
  entry.activated(value)
  value['limits']['saves']=1
  with self.assertRaisesRegex(ValueError,'LIMITS_CHANGED'):entry.activated(value)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
