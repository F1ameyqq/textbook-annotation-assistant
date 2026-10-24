"""Source-bound fault injection against a frozen received B delivery; no producer use."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,shutil,sys,tempfile
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
for name in ('package','oracle','options','out'):p.add_argument('--'+name,required=True,type=Path)
args=p.parse_args();package=args.package.resolve();source=package/'delivery';oracle=args.oracle;options=args.options
args.out.parent.mkdir(parents=True,exist_ok=True)
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
consumer=module('b03fixed',R/'tools/consume_fixed_a24_c01_b.py')
pins_raw=(package/'consumer-pins.json').read_bytes();assert hashlib.sha256(pins_raw).hexdigest()==consumer.PINS_SHA
pins=json.loads(pins_raw);assert pins['a_commit']==consumer.A_COMMIT and len(pins['members'])==50
for m in pins['members']:
 raw=(package/'consumer-a'/m['path']).read_bytes();assert len(raw)==m['bytes'] and hashlib.sha256(raw).hexdigest()==m['sha256']
sys.path.insert(0,str(package/'consumer-a/src'));sys.addaudithook(consumer.guard);sys.meta_path.insert(0,consumer.Imports())
from annotation.contracts import load_bundle
quality=module('b03audit',R/'tools/audit_lesson_c01_b.py')
assert hashlib.sha256((source/'bundle.json').read_bytes()).hexdigest()=='55b404e4cfab3594f00d5d963347b0919666c049ad5353286d3ad65ad9666292'
load_bundle(source/'bundle.json',verify_assets=True)
assert quality.audit(source,oracle,options)['status']=='SOURCE_CONTENT_AND_PACKAGE_BINDINGS_MATCH'
v1=quality.load(source/'bundle.json')
next(a for a in v1['artifacts'] if a['kind']=='CheckReport')['payload']['subject']['content_hash']='0'*64
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canon=lambda o:json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
enc=lambda o:(json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode()
def save(p,o):p.write_bytes(enc(o))
def reseal(root):
 b=quality.load(root/'bundle.json');basis=quality.load(root/'basis.json');review=quality.load(root/'current-review.json');g=quality.load(root/'generation.json');d=quality.load(root/'delivery.json');review['items']=copy.deepcopy(basis['items']);save(root/'current-review.json',review)
 g['basis_sha256']=sha(root/'basis.json');g['current_review_sha256']=sha(root/'current-review.json');save(root/'generation.json',g)
 for ev in b['evidence']:
  path=root/ev['resource']['path'];ev['resource']['sha256']=sha(path)
 changed={}
 def refs(value):
  if isinstance(value,dict):
   if set(value)=={'artifact_id','revision','kind','content_hash'} and value['artifact_id'] in changed:value['content_hash']=changed[value['artifact_id']]
   for v in value.values():refs(v)
  elif isinstance(value,list):
   for v in value:refs(v)
 for a in b['artifacts']:
  refs(a);a['content_hash']=hashlib.sha256(canon({k:v for k,v in a.items() if k!='content_hash'})).hexdigest();changed[a['artifact_id']]=a['content_hash']
 graph=next(a for a in b['artifacts'] if a['kind']=='QuestionGraph');d['c01_graph_ref']={k:graph[k] for k in ('artifact_id','revision','kind','content_hash')};d['basis_sha256']=sha(root/'basis.json');d['current_review_sha256']=sha(root/'current-review.json');d['generation_sha256']=sha(root/'generation.json');save(root/'delivery.json',d);save(root/'bundle.json',b)
def text_change(root,key,field,new):
 basis=quality.load(root/'basis.json');side=quality.load(root/'delivery.json');bundle=quality.load(root/'bundle.json');ev=next(a for a in bundle['artifacts'] if a['kind']=='EvidenceBundle');item=next(i for i in basis['items'] if i['item_key']==key);item['fields'][field]=new
 matches=[v for v in basis['blocks'] if v['item_key']==key and v['field']==field and v.get('graph_fragment',True)];assert len(matches)==1;block=matches[0];block['text']=new;binding=next(v for v in side['bindings'] if v['block_id']==block['block_id']);binding['runs']=[{'format':'plain','text':new}];next(v for v in ev['payload']['regions'] if v['region_id']==binding['region_id'])['text']=new
 save(root/'basis.json',basis);save(root/'delivery.json',side);save(root/'bundle.json',bundle);reseal(root)
def mutate(root,case):
 b=quality.load(root/'bundle.json');side=quality.load(root/'delivery.json');graph=next(a for a in b['artifacts'] if a['kind']=='QuestionGraph');ev=next(a for a in b['artifacts'] if a['kind']=='EvidenceBundle')
 if case=='missing_original':(root/'assets/viewer-12.jpg').unlink();return
 if case=='missing_crop':(root/side['source_proofs'][0]['path']).unlink();return
 if case=='changed_crop_bytes':(root/side['source_proofs'][0]['path']).write_bytes(b'corrupted local fixture');return
 if case=='stale_check_report':b['artifacts']=[copy.deepcopy(next(a for a in v1['artifacts'] if a['kind']=='CheckReport')) if a['kind']=='CheckReport' else a for a in b['artifacts']]
 elif case=='missing_variant':graph['payload']['questions'].pop();graph['payload']['answer_relations'].pop()
 elif case=='duplicate_question_identity':graph['payload']['questions'][-1]['question_id']=graph['payload']['questions'][-2]['question_id']
 elif case=='missing_fragment':graph['payload']['fragments'].pop()
 elif case=='absolute_resource_path':b['evidence'][0]['resource']['path']='C:/outside-evidence.json'
 elif case=='escaping_resource_path':b['evidence'][0]['resource']['path']='../outside-evidence.json'
 elif case=='excluded_clue_claims_regions':ev['payload']['coverage_clues'][0]['disposition']='EXCLUDED'
 elif case=='resigned_printed_number_uses_native_order':
  basis=quality.load(root/'basis.json');basis['items'][0]['printed_number']='18';graph['payload']['questions'][0]['external_refs']['printed_number']='18';save(root/'basis.json',basis)
 elif case=='old_combined_window_as_fifth_option':
  basis=quality.load(root/'basis.json');block=next(v for v in basis['blocks'] if v['item_key']=='lesson2-q2' and v.get('graph_fragment') is False);block['graph_fragment']=True;binding=next(v for v in side['bindings'] if v['block_id']==block['block_id']);binding['fragment_id']='fragment-'+block['block_id'];region=next(v for v in ev['payload']['regions'] if v['region_id']==binding['region_id']);graph['payload']['fragments'].append({'fragment_id':binding['fragment_id'],'region_ids':[binding['region_id']],'role':'option','content_type':'text','reading_order':len(graph['payload']['fragments'])});question=next(q for q in graph['payload']['questions'] if q['question_id']=='bq-lesson2-q2');question['fragment_ids']=[v['fragment_id'] for v in side['bindings'] if v['item_key']=='lesson2-q2' and v['fragment_id'] is not None and v['role'] not in ('answer','explanation')];save(root/'basis.json',basis);save(root/'delivery.json',side)
 elif case=='resigned_wrong_source_answer':text_change(root,'lesson2-q3','answer','5');return
 elif case=='resigned_variant_context_missing':text_change(root,'lesson2-q8-variant1','question',quality.load(source/'basis.json')['items'][-1]['fields']['question'].replace('一辆高4.1 m、宽3 m的卡车','上题中的卡车'));return
 elif case=='resigned_wrong_q5_equation':
  item=next(i for i in quality.load(root/'basis.json')['items'] if i['item_key']=='lesson2-q5');text_change(root,'lesson2-q5','answer',item['fields']['answer'].replace('48²+20²=52²','48²+20²=53²'));return
 else:raise AssertionError(case)
 save(root/'bundle.json',b)
 if case not in ('stale_check_report','absolute_resource_path','escaping_resource_path'):reseal(root)
cases=('missing_original','missing_crop','changed_crop_bytes','stale_check_report','missing_variant','duplicate_question_identity','missing_fragment','absolute_resource_path','escaping_resource_path','excluded_clue_claims_regions','resigned_wrong_source_answer','resigned_variant_context_missing','resigned_wrong_q5_equation','resigned_printed_number_uses_native_order','old_combined_window_as_fifth_option');rows=[]
for name in cases:
 with tempfile.TemporaryDirectory(prefix='b03-negative-',dir=args.out.parent) as tmp:
  root=Path(tmp)/'delivery';shutil.copytree(source,root);mutate(root,name);a_error=q_error=None
  try:load_bundle(root/'bundle.json',verify_assets=True)
  except (ValueError,OSError,KeyError,TypeError) as error:a_error=type(error).__name__
  try:
   result=quality.audit(root,oracle,options)
   if result['status']!='SOURCE_CONTENT_AND_PACKAGE_BINDINGS_MATCH':q_error=result['status']
  except (ValueError,OSError,KeyError,TypeError) as error:q_error=str(error).splitlines()[0][:160]
  rows.append({'case':name,'fixed_a24_rejected':a_error is not None,'a24_error_type':a_error,'independent_content_rejected':q_error is not None,'independent_error':q_error,'rejected':a_error is not None or q_error is not None})
assert all(x['rejected'] for x in rows)
result={'schema':'B03IndependentC01NegativeCases/v1','status':'ALL_15_FAULTS_REJECTED','base_bundle_sha256':sha(source/'bundle.json'),'cases':rows,'producer_builder_or_producer_comparator_used':False,'resigned_semantic_faults_can_be_schema_valid':True,'platform_requests':0}
args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':result['status'],'rows':rows},ensure_ascii=False))
