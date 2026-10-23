"""Independent B03 checks of a received C01 delivery, never a producer builder."""
import argparse,hashlib,json,re
from pathlib import Path,PurePosixPath,PureWindowsPath
from PIL import Image
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError('DUPLICATE_JSON_KEY')
   d[k]=v
  return d
 return json.loads(Path(p).read_bytes(),object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
def need(ok,code):
 if not ok:raise ValueError(code)
def audit(root,oracle_path,option_path=None):
 root=Path(root).resolve();oracle=load(oracle_path);bundle=load(root/'bundle.json');side=load(root/'delivery.json');basis=load(root/'basis.json');review=load(root/'current-review.json');generation=load(root/'generation.json')
 need(bundle['format_version']=='c01-exchange-1','C01_FORMAT');artifacts={a['kind']:a for a in bundle['artifacts']};need(len(artifacts)==len(bundle['artifacts'])==4 and set(artifacts)=={'SourceBundle','EvidenceBundle','QuestionGraph','CheckReport'},'EXACT_FOUR_ARTIFACTS')
 source=artifacts['SourceBundle'];evidence=artifacts['EvidenceBundle'];graph=artifacts['QuestionGraph'];check=artifacts['CheckReport'];ref=lambda a:{k:a[k] for k in ('artifact_id','revision','kind','content_hash')}
 need(side['c01_graph_ref']==check['payload']['subject']==check['payload']['graph']==ref(graph),'CURRENT_GRAPH_CHECK_BINDING')
 need(side['basis_sha256']==generation['basis_sha256']==sha(root/'basis.json') and side['current_review_sha256']==generation['current_review_sha256']==sha(root/'current-review.json') and side['generation_sha256']==sha(root/'generation.json'),'SIDECAR_REFERENCE_HASH')
 need(review['items']==basis['items'] and review['independent_human_acceptance'] is False and review['a_owner_acceptance'] is False,'REVIEW_ITEMS_OR_SIGNATURE')
 need([i['item_key'] for i in basis['items']]==oracle['keys']==side['confirmed_item_keys'],'NINE_SCOPE_IDENTITIES')
 resources={}
 def local(rel):
  need(type(rel) is str and '\\' not in rel and ':' not in rel and not PureWindowsPath(rel).drive and not PurePosixPath(rel).is_absolute() and '..' not in PurePosixPath(rel).parts,'NONPORTABLE_PATH')
  p=(root/rel).resolve();need(p.is_relative_to(root) and p.is_file(),'RESOURCE_MISSING_OR_ESCAPE');return p
 def walk(v):
  if isinstance(v,dict):
   if 'path' in v:
    p=local(v['path'])
    if 'sha256' in v:need(sha(p)==v['sha256'],'RESOURCE_HASH_CHANGED');resources[v['path']]=sha(p)
   for x in v.values():walk(x)
  elif isinstance(v,list):
   for x in v:walk(x)
 for value in (bundle,side,basis,review,generation):walk(value)
 assets={a['asset_id']:a for a in source['payload']['assets']};need(set(assets)=={'viewer-'+p for p in oracle['source_sha256']},'SOURCE_PAGE_SCOPE')
 images={}
 for aid,a in assets.items():
  page=aid.split('-')[-1];need(a['sha256']==oracle['source_sha256'][page]==sha(local(a['path'])),'INDEPENDENT_FIXED_SOURCE_HASH')
  images[aid]=Image.open(local(a['path'])).convert('RGB');need(list(images[aid].size)==[a['width'],a['height']],'SOURCE_IMAGE_DIMENSIONS')
 regions={v['region_id']:v for v in evidence['payload']['regions']};frags={v['fragment_id']:v for v in graph['payload']['fragments']};questions=graph['payload']['questions'];relations={v['question_id']:v for v in graph['payload']['answer_relations']};blocks={v['block_id']:v for v in basis['blocks']};binds={v['block_id']:v for v in side['bindings']};proofs={v['region_id']:v for v in side['source_proofs']}
 need(len(regions)==len(proofs)==len(blocks)==len(binds),'REGION_PROOF_BLOCK_SCOPE');need(len(questions)==len(relations)==9,'NINE_QUESTION_RELATIONS')
 need(all(not c['region_ids'] for c in evidence['payload']['coverage_clues'] if c['disposition'] in ('EXCLUDED','UNASSIGNED')),'EXCLUDED_CLUE_HAS_REGIONS')
 qmap={q['question_id']:q for q in questions};need([q['question_id'] for q in questions]==['bq-'+k for k in oracle['keys']],'GRAPH_QUESTION_IDENTITIES')
 active=set();all_owned=[];options={};content={};diagram_count=0;blank_count=0
 for item,q in zip(basis['items'],questions):
  key=item['item_key'];owned=[b for b in side['bindings'] if b['item_key']==key and b['fragment_id'] is not None];need(item['human_verified'] is False,'FALSE_HUMAN_CLAIM');need(q['external_refs']['platform_question_id'] is None and q['external_refs']['platform_order'] is None,'FALSE_PLATFORM_ID')
  want_parent='bq-'+oracle['variant_parent'] if key==oracle['keys'][-1] else None;need(q['parent_question_id']==want_parent,'VARIANT_PARENT')
  fields={name:''.join(regions[b['region_id']]['text'] or '' for b in owned if b['field']==name) for name in ('question','choice','answer','analysis')}
  need(all(fields[k]==(item['fields'][k] or '') for k in fields),'GRAPH_CONTENT_FIELD_LOSS')
  need(q['fragment_ids']==[b['fragment_id'] for b in owned if b['role'] not in ('answer','explanation')],'QUESTION_FRAGMENT_OWNERSHIP')
  answer=[b['fragment_id'] for b in owned if b['role'] in ('answer','explanation')];relation=relations[q['question_id']];need(relation['status']=='SELECTED' and relation['candidate_fragment_ids']==relation['selected_fragment_ids']==answer,'ANSWER_RELATION_OWNERSHIP')
  need(answer,'ANSWER_MISSING');all_owned+=q['fragment_ids']+answer
  for field,value in fields.items():
   if field in ('question','choice'):expected_pages={'viewer-12','viewer-13'}
   else:expected_pages={'viewer-173'}
   need(all(regions[b['region_id']]['box']['image']['asset_id'] in expected_pages for b in owned if b['field']==field),'QUESTION_ANSWER_WRONG_PAGE')
  if key in oracle['answer_exact']:need(fields['answer']==oracle['answer_exact'][key],'INDEPENDENT_SOURCE_ANSWER_MISMATCH')
  for field,anchors in oracle.get('formula_anchors',{}).get(key,{}).items():
   for anchor in anchors:need(anchor in fields[field],'INDEPENDENT_SOURCE_FORMULA_MISMATCH')
  if key in oracle['no_printed_analysis_keys']:need(not fields['analysis'],'UNSOURCED_ANALYSIS')
  for number in oracle['number_anchors'].get(key,[]):need(re.search(r'(?<![\d.])'+re.escape(number)+r'(?![\d.])',fields['question']) is not None,'INDEPENDENT_SOURCE_STEM_NUMBER')
  if key in oracle['option_numbers']:
   choices=[b for b in owned if b['role']=='option'];options[key]=len(choices);texts=[regions[b['region_id']]['text'].strip() for b in choices]
   if len(choices)==4:
    for label,num,text in zip('ABCD',oracle['option_numbers'][key],texts):need(re.match(re.escape(label)+r'[.、]\s*'+re.escape(num)+r'(?![\d.])',text) is not None,'OPTION_SOURCE_LABEL_OR_VALUE')
    if option_path:
     pin={v['label']:v for row in load(option_path)['questions'] if row['item_key']==key for v in row['options']}
     need(all(regions[b['region_id']]['box']['bbox']==pin[label]['bbox_xyxy_pixels'] for b,label in zip(choices,'ABCD')),'OPTION_SOURCE_WINDOW_BINDING')
   else:need(len(choices)==1,'UNEXPECTED_OPTION_FRAGMENT_COUNT')
  else:need(not fields['choice'],'EXTRA_CHOICE')
  if key=='lesson2-q1':need(len(re.findall('_{2,}',fields['question']))==oracle['q1_question_blanks'],'Q1_QUESTION_BLANKS')
  if key=='lesson2-q5':
   for n in oracle['q5_solution_numbers']:need(n in fields['answer'],'Q5_WORKED_SOLUTION_LOSS')
  if key=='lesson2-q8':need(oracle['q8_clearance_squared'] in fields['analysis'] and '能通过' in fields['answer'] and '不能' not in fields['answer'],'Q8_ANSWER_OR_ANALYSIS')
  if key==oracle['keys'][-1]:need(oracle['variant_clearance_squared'] in fields['analysis'] and '不能通过' in fields['answer'] and '上题' not in fields['question'],'VARIANT_CONTEXT_OR_ANSWER')
  content[key]=fields
 need(len(all_owned)==len(set(all_owned)) and set(all_owned)==set(frags),'UNOWNED_OR_SHARED_DUPLICATE_FRAGMENTS')
 for bid,b in binds.items():
  block=blocks[bid];region=regions[b['region_id']];proof=proofs[b['region_id']];box=region['box'];aid=box['image']['asset_id'];coords=box['bbox'];need(coords==block['bbox'] and aid==block['asset_id'] and region['text']==block['text'],'BLOCK_REGION_MISMATCH')
  need(all(type(x) in (int,float) and float(x).is_integer() for x in coords),'SOURCE_COORDINATE_TYPE');coords=[int(x) for x in coords];im=images[aid];need(0<=coords[0]<coords[2]<=im.width and 0<=coords[1]<coords[3]<=im.height,'SOURCE_BOUNDS')
  with Image.open(local(proof['path'])) as crop:actual=crop.convert('RGB');want=im.crop(coords);need(actual.size==want.size and actual.tobytes()==want.tobytes() and hashlib.sha256(want.tobytes()).hexdigest()==proof['rgb_sha256'],'CROP_SOURCE_PIXELS_MISMATCH')
  if b['fragment_id'] is not None:
   f=frags[b['fragment_id']];need(f['region_ids']==[b['region_id']] and f['role']==b['role']==block['role'] and f['content_type']==region['content_type'],'FRAGMENT_REGION_ROLE')
   active.add(b['fragment_id'])
   if b['field']=='diagram':diagram_count+=1;need(region['content_type']=='image' and region['text'] is None,'DIAGRAM_TYPE')
  for run in b['runs']:
   if run['format']=='blank':need(run['value'] is None,'QUESTION_BLANK_FILLED');blank_count+=1
 need(active==set(frags) and diagram_count==oracle['required_diagram_groups'],'FRAGMENT_OR_DIAGRAM_SCOPE')
 pending=[key for key,count in options.items() if count!=4]
 return {'schema':'B03IndependentC01ContentAudit/v1','status':'SOURCE_CONTENT_AND_PACKAGE_BINDINGS_MATCH' if not pending else 'SOURCE_CONTENT_MATCH_SEPARATE_OPTIONS_PENDING','review_kind':'INDEPENDENT_MODEL_NOT_HUMAN','bundle_sha256':sha(root/'bundle.json'),'questions':9,'selected_answer_relations':9,'source_images':len(assets),'source_regions':len(regions),'graph_fragments':len(frags),'derived_crops_pixel_verified':len(proofs),'relative_resources_hash_verified':len(resources),'diagram_groups':diagram_count,'unfilled_question_blanks':blank_count,'option_fragments':options,'pending_separate_options':pending,'platform_requests':0,'a_owner_acceptance':False,'human_acceptance':False,'whole_chapter_acceptance':False,'full_object_content_sha256':hashlib.sha256(json.dumps(content,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('delivery','oracle','out'):p.add_argument('--'+name,required=True)
 p.add_argument('--options');a=p.parse_args()
 try:result=audit(a.delivery,a.oracle,a.options);code=0
 except (ValueError,KeyError,TypeError,OSError) as error:result={'status':'REJECTED','error':str(error),'platform_requests':0};code=2
 with Path(a.out).open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
 print(json.dumps(result,ensure_ascii=False));raise SystemExit(code)
