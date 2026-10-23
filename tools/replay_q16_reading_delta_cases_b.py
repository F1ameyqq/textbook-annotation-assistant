from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,sys,unittest
P=argparse.ArgumentParser(description="Source-bound four-task delta control and fault cases; not a CI suite.")
for key in ('old','new','out'):P.add_argument('--'+key,required=True,type=Path)
args=P.parse_args();spec=importlib.util.spec_from_file_location('q16delta',Path(__file__).with_name('q16_reading_delta_core.py'));q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
old=args.old;new=args.new
assert hashlib.sha256((old/'bundle.json').read_bytes()).hexdigest()=='95488a276535a7bee7094238b02c6b41574e37df19d7b946830c6c07f9a824d6'
assert hashlib.sha256((new/'bundle.json').read_bytes()).hexdigest()=='ed656b23e1c343a2d11d09f6006bb22ddb90fbe64120d75f38facdd154c17f38'
B=json.loads((old/'bundle.json').read_bytes());S=json.loads((old/'delivery.json').read_bytes());ACTUAL_B=json.loads((new/'bundle.json').read_bytes());ACTUAL_S=json.loads((new/'delivery.json').read_bytes())
class ExactFourTaskDeltaCases(unittest.TestCase):
 def setUp(self):self.b,self.s=copy.deepcopy((ACTUAL_B,ACTUAL_S))
 def reject(self):
  with self.assertRaises(q.Reject):q.check(B,S,self.b,self.s)
 def test_actual_final_bundle_control(self):self.assertEqual(q.check(B,S,self.b,self.s)['q16_printed_labels_restored'],3)
 def test_uncorrected_old_package_is_not_zero_gap(self):
  with self.assertRaises(q.Reject):q.check(B,S,B,S)
 def test_missing_each_printed_label(self):
  for n in (1,2,3):
   self.setUp();r=next(v for v in q.artifacts(self.b)['EvidenceBundle']['regions'] if v['region_id']=='region-q16-task'+str(n));r['text']=r['text'][3:];self.reject()
 def test_wrong_label_number(self):next(v for v in q.artifacts(self.b)['EvidenceBundle']['regions'] if v['region_id']=='region-q16-task1')['text']='（2）'+B['artifacts'][1]['payload']['regions'][1]['text'];self.reject()
 def test_label_missing_in_rich_runs(self):next(v for v in self.s['bindings'] if v['block_id']=='q16-task2')['runs'][0]['text']=next(v for v in S['bindings'] if v['block_id']=='q16-task2')['runs'][0]['text'];self.reject()
 def test_blank_filled(self):next(run for v in self.s['bindings'] for run in v['runs'] if run['format']=='blank')['value']='60';self.reject()
 def test_blank_dropped(self):v=next(v for v in self.s['bindings'] if v['block_id']=='q16-task1');v['runs']=[run for run in v['runs'] if run['format']!='blank'];self.reject()
 def test_formula_f9_sign_changed(self):self.s['q16_formula_slots'][8]['expected_latex']=self.s['q16_formula_slots'][7]['expected_latex'];self.reject()
 def test_formula_diagnostic_promoted_into_answers(self):q.artifacts(self.b)['QuestionGraph']['answer_relations'][0]['selected_fragment_ids'].append('fragment-q16-F11');self.reject()
 def test_shared_figure_lost(self):q.artifacts(self.b)['QuestionGraph']['questions'][2]['shared_fragment_ids'].remove('fragment-reading-figure2');self.reject()
 def test_answer_task2_task3_crossed(self):a=q.artifacts(self.b)['QuestionGraph']['answer_relations'];a[2]['selected_fragment_ids'],a[3]['selected_fragment_ids']=a[3]['selected_fragment_ids'],a[2]['selected_fragment_ids'];self.reject()
 def test_reading_task3_answer_diagram_lost(self):q.artifacts(self.b)['QuestionGraph']['answer_relations'][3]['selected_fragment_ids'].remove('fragment-task3-diagram');self.reject()
 def test_source_box_moved(self):q.artifacts(self.b)['EvidenceBundle']['regions'][0]['box']['bbox'][0]+=1;self.reject()
 def test_source_page15_relabelled14(self):q.artifacts(self.b)['SourceBundle']['assets'][1]['asset_id']='viewer-14';self.reject()
 def test_q16_positive_odd_condition_weakened(self):r=next(v for v in q.artifacts(self.b)['EvidenceBundle']['regions'] if v['region_id']=='region-q16-task2');r['text']=r['text'].replace('a≥3','a≥1');self.reject()
 def test_nonunique_note_removed(self):r=next(v for v in q.artifacts(self.b)['EvidenceBundle']['regions'] if v['region_id']=='region-task3-line4-continuation');r['text']='';self.reject()
 def test_false_human_confirmation(self):self.s['human_verified']=True;self.reject()
 def test_old_unresolved_status_not_current_source_selection(self):q.artifacts(self.b)['QuestionGraph']['answer_relations'][0]['status']='UNRESOLVED';self.reject()
 def test_all_four_tasks_misfiled_same_directory(self):g=q.artifacts(self.b)['QuestionGraph'];g['questions'][0]['directory_id']=g['questions'][1]['directory_id'];self.reject()
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExactFourTaskDeltaCases));result={'schema':'IndependentFourTaskActualDeltaCases/v1','status':'PASS' if r.wasSuccessful() else 'FAIL','tests_run':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'control':'Actual frozen final 1362c758 container delivery; independent old source input','actual_new_bundle_tested':True,'final_container_sha256':'1362c7582bacce796b518bdf12e421537ef69be768da39bed99209777a46d2fd','actual_bundle_sha256':'ed656b23e1c343a2d11d09f6006bb22ddb90fbe64120d75f38facdd154c17f38','platform_requests':0};args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result));raise SystemExit(not r.wasSuccessful())
