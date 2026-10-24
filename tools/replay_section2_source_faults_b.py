"""Adversarial copies of the fixed section-2 bundle; no producer comparator."""
import argparse,copy,hashlib,importlib.abc,importlib.util,json,shutil,sys,tempfile
from pathlib import Path

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def guard(event,args):
 if event in {'socket.connect','socket.connect_ex','socket.getaddrinfo','socket.gethostbyname','socket.sendto','socket.sendmsg','subprocess.Popen','os.system','os.posix_spawn','os.spawn','os.exec','os.fork','os.startfile','os.startfile/2'}:raise RuntimeError('SECTION2_OFFLINE_FORBIDDEN:'+event)
class LocalImports(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.startswith(('annotation.runtime','annotation.delivery','annotation.recognition','playwright','torch','paddle','onnxruntime','transformers')):raise ImportError('SECTION2_OFFLINE_IMPORT:'+fullname)
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def payload(b,kind):return next(v for v in b['artifacts'] if v['kind']==kind)['payload']
def region(b,key):return next(v for v in payload(b,'EvidenceBundle')['regions'] if v['region_id']=='region-'+key)
def binding(s,key):return next(v for v in s['bindings'] if v['block_id']==key)
def question(b,n):return next(v for v in payload(b,'QuestionGraph')['questions'] if v['question_id']=='bq-section2-q'+str(n))
def relation(b,n):return next(v for v in payload(b,'QuestionGraph')['answer_relations'] if v['question_id']=='bq-section2-q'+str(n))
def set_text(b,s,key,text):region(b,key)['text']=text;binding(s,key)['runs']=[] if not text else [{'format':'plain','text':text}]
def replace_text(b,s,key,old,new):
 r=region(b,key);assert old in r['text'];r['text']=r['text'].replace(old,new)
 for run in binding(s,key)['runs']:
  if run['format']=='plain':run['text']=run['text'].replace(old,new)
  elif run['format']=='latex' and old in run['source_text']:
   text=run['source_text'].replace(old,new);run.clear();run.update(format='plain',text=text)
def reseal(b,s):
 changed={}
 def refs(v):
  if isinstance(v,dict):
   if set(v)=={'artifact_id','revision','kind','content_hash'} and v['artifact_id'] in changed:v['content_hash']=changed[v['artifact_id']]
   for x in v.values():refs(x)
  elif isinstance(v,list):
   for x in v:refs(x)
 for a in b['artifacts']:
  refs(a);a['content_hash']=sha(canonical({k:v for k,v in a.items() if k!='content_hash'}));changed[a['artifact_id']]=a['content_hash']
 a=next(v for v in b['artifacts'] if v['kind']=='QuestionGraph');s['c01_graph_ref']={k:a[k] for k in ('artifact_id','revision','kind','content_hash')}
def mutate(b,s,name):
 if name=='q7_wrong_solution_autocorrected':replace_text(b,s,'section2-q7.question.2','不是直角三角形','是直角三角形')
 elif name=='q7_wrong_solution_removed':set_text(b,s,'section2-q7.question.2','')
 elif name=='q7_wrong_solution_moved_to_answer':
  wrong=region(b,'section2-q7.question.2')['text'];set_text(b,s,'section2-q7.question.2','');set_text(b,s,'section2-q7.answer.1',region(b,'section2-q7.answer.1')['text']+wrong)
 elif name=='q7_question_columns_reversed':question(b,7)['fragment_ids'].reverse()
 elif name=='q7_correct_answer_angle_wrong':replace_text(b,s,'section2-q7.answer.1','∠B','∠C')
 elif name=='q9_squares_removed':replace_text(b,s,'section2-q9.choice.C','²','')
 elif name=='q9_decimal_integer_gate_lost':replace_text(b,s,'section2-q9.choice.B','0.','')
 elif name=='q13_fraction_inverted':next(v for v in binding(s,'section2-q13.choice.D')['runs'] if v['format']=='latex')['text']='\\frac{2}{5}'
 elif name=='q13_distractor_autocorrected':replace_text(b,s,'section2-q13.choice.D','5/2','2')
 elif name=='q15_answer_tail_missing':set_text(b,s,'section2-q15.answer.2','')
 elif name=='q15_answer_columns_reversed':relation(b,15)['candidate_fragment_ids'].reverse();relation(b,15)['selected_fragment_ids'].reverse()
 elif name=='q15_fraction_wrong':replace_text(b,s,'section2-q15.question.1','1/4','1/2')
 elif name=='q15_target_angle_wrong':replace_text(b,s,'section2-q15.question.1','∠AEF','∠AFE')
 elif name=='q6_direction_swapped':replace_text(b,s,'section2-q6.question.1','南偏东','东偏南')
 elif name=='blank_prefilled':next(v for v in binding(s,'section2-q10.question.1')['runs'] if v['format']=='blank')['value']='25'
 elif name=='same_letter_answer_owner_swapped':
  x,y=relation(b,1),relation(b,2)
  for key in ('candidate_fragment_ids','selected_fragment_ids'):x[key],y[key]=y[key],x[key]
 elif name=='option_source_identity_swapped':
  x,y=region(b,'section2-q2.choice.A'),region(b,'section2-q2.choice.B')
  for key in ('box','crop_transform'):x[key],y[key]=y[key],x[key]
 elif name=='diagram_missing':question(b,15)['fragment_ids'].remove('fragment-section2-q15.diagram.1')
 elif name=='scope_q16_or_reading_added':
  q=copy.deepcopy(question(b,15));q['question_id']='bq-section2-q16';q['external_refs']['printed_number']='16';payload(b,'QuestionGraph')['questions'].append(q)
 elif name=='source_region_geometry_changed':region(b,'section2-q9.choice.C')['box']['bbox'][1]+=4
 elif name=='unsourced_analysis_added':
  r=copy.deepcopy(region(b,'section2-q7.answer.1'));r['region_id']='region-unsourced-explanation';r['text']='新增的无原书来源解析';payload(b,'EvidenceBundle')['regions'].append(r);g=payload(b,'QuestionGraph');g['fragments'].append({'fragment_id':'fragment-unsourced-explanation','region_ids':[r['region_id']],'role':'explanation','content_type':'text','reading_order':65});answer=relation(b,7);answer['candidate_fragment_ids'].append('fragment-unsourced-explanation');answer['selected_fragment_ids'].append('fragment-unsourced-explanation')
 elif name not in ('missing_source_file','missing_derived_crop'):raise AssertionError(name)
 reseal(b,s)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('package','pins','out'):p.add_argument('--'+name,required=True,type=Path)
 args=p.parse_args();package=args.package.resolve();delivery=package/'delivery';args.out.parent.mkdir(parents=True,exist_ok=True)
 core=module('section2_independent_core',Path(__file__).with_name('audit_section2_source_c01_b.py'))
 assert sha((delivery/'bundle.json').read_bytes())=='6d629a6e138991c2959d4fbdb9d718e3baf6f1f771719250adaa2852832c9d35'
 pins_raw=(package/'consumer-pins.json').read_bytes();assert sha(pins_raw)=='e52b3d88f344d7873859f609c78d41e6c5421ac6bb363c83e81061dcf772a006';pins=json.loads(pins_raw);assert pins['a_commit']=='c5aefbc8e995c410b3babf74a251f05a7724a1c2' and len(pins['members'])==50
 for member in pins['members']:
  raw=(package/'consumer-a'/member['path']).read_bytes();assert len(raw)==member['bytes'] and sha(raw)==member['sha256']
 sys.dont_write_bytecode=True;sys.path.insert(0,str(package/'consumer-a/src'));sys.addaudithook(guard);sys.meta_path.insert(0,LocalImports())
 from annotation.contracts import validate_bundle
 B=core.strict(delivery/'bundle.json');S=core.strict(delivery/'delivery.json');baseline=core.audit(delivery,args.pins);assert baseline['status']=='SOURCE_CONTENT_BINDINGS_RICH_MATH_AND_OWNERSHIP_MATCH';actual=validate_bundle(B,delivery).model_dump(mode='json');assert sha(canonical(actual))=='67a0e4d942f8465336763d0ba73af6befeb346dfa09ad694cf20ac065f888655'
 cases=('q7_wrong_solution_autocorrected','q7_wrong_solution_removed','q7_wrong_solution_moved_to_answer','q7_question_columns_reversed','q7_correct_answer_angle_wrong','q9_squares_removed','q9_decimal_integer_gate_lost','q13_fraction_inverted','q13_distractor_autocorrected','q15_answer_tail_missing','q15_answer_columns_reversed','q15_fraction_wrong','q15_target_angle_wrong','q6_direction_swapped','blank_prefilled','same_letter_answer_owner_swapped','option_source_identity_swapped','diagram_missing','scope_q16_or_reading_added','source_region_geometry_changed','unsourced_analysis_added','missing_source_file','missing_derived_crop')
 rows=[]
 for name in cases:
  b,s=copy.deepcopy(B),copy.deepcopy(S);mutate(b,s,name);temp=None;root=delivery
  if name in ('missing_source_file','missing_derived_crop'):
   temp=tempfile.TemporaryDirectory(prefix='section2-fault-',dir=args.out.parent.resolve());assert Path(temp.name).resolve().is_relative_to(args.out.parent.resolve());root=Path(temp.name)/'delivery';shutil.copytree(delivery,root)
   rel=payload(b,'SourceBundle')['assets'][0]['path'] if name=='missing_source_file' else s['source_proofs'][0]['path'];target=(root/rel).resolve();assert target.is_relative_to(root.resolve());target.unlink()
  try:
   a_error=q_error=None
   try:validate_bundle(b,root)
   except ValueError as error:a_error=type(error).__name__
   try:core.audit(root,args.pins,bundle=b,side=s)
   except core.Reject as error:q_error=str(error)
   assert q_error is not None,('FAULT_ACCEPTED',name)
   rows.append({'case':name,'outer_artifact_hashes_recomputed':True,'fixed_a24_structurally_accepted':a_error is None,'fixed_a24_error_type':a_error,'independent_source_rejected':True,'independent_rejection':q_error})
  finally:
   if temp is not None:temp.cleanup()
 result={'schema':'IndependentSection2ActualFaultCopies/v1','status':'ALL_23_FAULTS_REJECTED','normal_control':'Actual final section2 bundle, checked against independent pre-C01 source pins','base_bundle_sha256':sha((delivery/'bundle.json').read_bytes()),'fault_cases':23,'source_rejections':len(rows),'structurally_accepted_faults':sum(v['fixed_a24_structurally_accepted'] for v in rows),'faults_are_counterfactual_not_real_source_observations':True,'producer_builder_or_comparator_used':False,'cases':rows,'platform_requests':0}
 with args.out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
 print(json.dumps({'status':result['status'],'fault_cases':23,'structurally_accepted_faults':result['structurally_accepted_faults'],'platform_requests':0}));return 0
if __name__=='__main__':raise SystemExit(main())
