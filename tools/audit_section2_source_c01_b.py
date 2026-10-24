"""Read-only section-2 source/C01 consumer; expected pins predate C01 output."""
import hashlib,json,re
from pathlib import Path
class Reject(ValueError):pass
def need(ok,code):
 if not ok:raise Reject(code)
def strict(path):
 def pairs(items):
  d={}
  for k,v in items:
   need(k not in d,'DUPLICATE_JSON_KEY');d[k]=v
  return d
 return json.loads(Path(path).read_bytes(),object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(Reject('NONFINITE_JSON')))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def text_hash(text):need(type(text) is str,'TEXT_TYPE');return hashlib.sha256(re.sub(r'\s+','',text).encode()).hexdigest()
def equal(a,b,code):need(json.dumps(a,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)==json.dumps(b,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False),code)
def inverse_atom(latex):
 need(type(latex) is str,'MATH_LATEX_TYPE')
 value=re.sub(r'\\frac\{([0-9]+)\}\{([0-9]+)\}',lambda m:m[1]+'/'+m[2],latex)
 value=re.sub(r'\\sqrt\{([0-9]+)\}',lambda m:'√'+m[1],value)
 supers=dict(zip('0123456789','⁰¹²³⁴⁵⁶⁷⁸⁹'));subs=dict(zip('0123456789','₀₁₂₃₄₅₆₇₈₉'))
 value=re.sub(r'\^\{([0-9]+)\}',lambda m:''.join(supers[c] for c in m[1]),value)
 value=re.sub(r'_\{([0-9]+)\}',lambda m:''.join(subs[c] for c in m[1]),value)
 need('\\' not in value and '{' not in value and '}' not in value,'UNREVIEWED_MATH_ATOM');return value
def audit(delivery,pins_path,bundle=None,side=None,basis=None):
 root=Path(delivery).resolve();pins=strict(pins_path);bundle=strict(root/'bundle.json') if bundle is None else bundle;side=strict(root/'delivery.json') if side is None else side;basis=strict(root/'basis.json') if basis is None else basis
 def file(rel):
  need(type(rel) is str and '\\' not in rel and ':' not in rel and not Path(rel).is_absolute() and '..' not in Path(rel).parts,'NONPORTABLE_RESOURCE')
  p=(root/rel).resolve();need(p.is_relative_to(root) and p.is_file(),'MISSING_OR_ESCAPING_RESOURCE');return p
 resources=set()
 def resource(value):
  p=file(value['path']);need(sha(p)==value['sha256'],'RESOURCE_HASH_MISMATCH');resources.add(value['path']);return p
 need(bundle['format_version']=='c01-exchange-1','C01_FORMAT');a={v['kind']:v for v in bundle['artifacts']};need(len(a)==len(bundle['artifacts'])==4 and set(a)=={'SourceBundle','EvidenceBundle','QuestionGraph','CheckReport'},'FOUR_ACTIVE_ARTIFACTS');source=a['SourceBundle']['payload'];evidence=a['EvidenceBundle']['payload'];graph=a['QuestionGraph']['payload'];check=a['CheckReport']['payload'];gref={k:a['QuestionGraph'][k] for k in ('artifact_id','revision','kind','content_hash')};equal(side['c01_graph_ref'],gref,'SIDECAR_GRAPH_BINDING');equal(check['subject'],gref,'STALE_CHECK_SUBJECT');equal(check['graph'],gref,'STALE_CHECK_GRAPH')
 need(side['basis_sha256']==sha(root/'basis.json') and side['current_review_sha256']==sha(root/'current-review.json') and side['generation_sha256']==sha(root/'generation.json'),'SIDECAR_FILE_HASH_BINDING')
 for ev in bundle['evidence']:resource(ev['resource'])
 for obj in (bundle,side,basis,strict(root/'current-review.json'),strict(root/'generation.json')):
  serialized=json.dumps(obj,ensure_ascii=False);need(re.search(r'(?i)[a-z]:[/\\]Users[/\\][^/\\]+|/home/[^/]+/',serialized) is None,'PRIVATE_LOCAL_PATH_IN_DELIVERY')
 asset_pins={str(v['viewer_page']):v['source_image_sha256'] for v in pins['regions']};assets={v['asset_id']:v for v in source['assets']};need(len(assets)==3 and set(assets)=={'viewer-14','viewer-15','viewer-173'},'SOURCE_ASSET_SCOPE')
 for aid,asset in assets.items():resource(asset);need(asset['sha256']==asset_pins[aid.split('-')[-1]],'INDEPENDENT_SOURCE_HASH')
 region_pins={v['region_id']:v for v in pins['regions']};regions={v['region_id']:v for v in evidence['regions']};frags={v['fragment_id']:v for v in graph['fragments']};bindings={v['block_id']:v for v in side['bindings']};proofs={v['region_id']:v for v in side['source_proofs']};need(len(regions)==len(frags)==len(bindings)==len(proofs)==65 and set(bindings)==set(region_pins),'SOURCE_REGION_OR_FRAGMENT_SCOPE')
 need(all(c['disposition'] not in ('EXCLUDED','UNASSIGNED') or not c['region_ids'] for c in evidence['coverage_clues']),'EXCLUDED_CLUE_ASSIGNED')
 orders=[v['reading_order'] for v in frags.values()];need(all(type(v) is int for v in orders) and len(orders)==len(set(orders)),'AMBIGUOUS_FRAGMENT_ORDER')
 mapped={};math_runs=0;blank_runs=0
 roles={'question':'stem','choice':'option','diagram':'stem','answer':'answer'}
 for rid,expected in region_pins.items():
  binding=bindings[rid];need(binding['item_key']==expected['item_key'] and binding['field'] in (('diagram','figure') if expected['role']=='diagram' else (expected['role'],)) and binding['role']==roles[expected['role']],'SOURCE_REGION_ROLE_OR_ITEM')
  reg=regions[binding['region_id']];frag=frags[binding['fragment_id']];mapped[rid]=binding;need(frag['region_ids']==[binding['region_id']] and frag['role']==binding['role'] and frag['content_type']==reg['content_type'],'FRAGMENT_REGION_BINDING')
  image=reg['box']['image'];need(image['asset_id']=='viewer-'+str(expected['viewer_page']) and image['sha256']==expected['source_image_sha256'] and [image['width'],image['height']]==expected['source_dimensions'],'REGION_SOURCE_IMAGE')
  coords=reg['box']['bbox'];need(len(coords)==4 and all(type(x) in (int,float) and float(x).is_integer() for x in coords) and coords==expected['bbox'],'SOURCE_BOX_CHANGED')
  proof=proofs[binding['region_id']];p=resource(proof);need(proof['sha256']==expected['crop']['sha256'] and proof['rgb_sha256']==expected['crop']['rgb_sha256'],'SOURCE_CROP_PROOF_CHANGED')
  if expected['role']=='diagram':need(reg['content_type']=='image' and reg['text'] is None and not binding['runs'],'DIAGRAM_CONTENT');continue
  need(reg['content_type']=='text','TEXT_REGION_TYPE');reconstructed=[]
  for run in binding['runs']:
   if run['format']=='plain':reconstructed.append(run['text'])
   elif run['format']=='blank':need(run['value'] is None and type(run['token']) is str and bool(re.fullmatch('_{2,}',run['token'])),'QUESTION_BLANK_FILLED_OR_INVALID');reconstructed.append(run['token']);blank_runs+=1
   elif run['format']=='latex':need(inverse_atom(run['text'])==run['source_text'],'MATH_RENDERING_SOURCE_MISMATCH');reconstructed.append(run['source_text']);math_runs+=1
   else:raise Reject('UNSUPPORTED_RICH_RUN')
  need(''.join(reconstructed)==reg['text'],'RICH_RUN_SOURCE_TEXT_LOSS')
 need({v['region_id'] for v in bindings.values()}==set(regions) and {v['fragment_id'] for v in bindings.values()}==set(frags),'UNBOUND_EXTRA_REGIONS_OR_FRAGMENTS')
 need(len(graph['questions'])==len(graph['answer_relations'])==15,'FIFTEEN_ITEM_SCOPE');relations={v['question_id']:v for v in graph['answer_relations']};all_owned=[];option_count=0;diagram_count=0;answer_count=0
 need(side['confirmed_item_keys']==[v['item_key'] for v in pins['items']],'CONFIRMED_SCOPE_KEYS')
 for expected,q in zip(pins['items'],graph['questions']):
  key=expected['item_key'];need(q['question_id']=='bq-'+key and q['external_refs']=={'printed_number':str(expected['printed_number']),'platform_question_id':None,'platform_order':None} and q['parent_question_id'] is None and q['shared_fragment_ids']==[] and q['cross_page'] is False,'QUESTION_IDENTITY_TYPE_OR_SCOPE')
  need(q['question_type']==('ordinary_choice' if expected['choices'] else 'free_response'),'QUESTION_TYPE')
  qids=expected['question_region_ids_in_reading_order'];cids=[v['source_region_id'] for v in expected['choices']];dids=expected['diagram_region_ids'];aids=expected['answer_region_ids_in_reading_order'];question_fragments=[mapped[rid]['fragment_id'] for rid in qids+cids+dids];answer_fragments=[mapped[rid]['fragment_id'] for rid in aids];equal(q['fragment_ids'],question_fragments,'QUESTION_FRAGMENT_OWNERSHIP_OR_ORDER')
  relation=relations[q['question_id']];need(relation['status']=='SELECTED' and relation['candidate_fragment_ids']==relation['selected_fragment_ids']==answer_fragments,'ANSWER_OWNERSHIP_OR_COLUMN_ORDER');all_owned+=question_fragments+answer_fragments
  for ids in (qids,cids,aids):need([frags[mapped[rid]['fragment_id']]['reading_order'] for rid in ids]==sorted(frags[mapped[rid]['fragment_id']]['reading_order'] for rid in ids),'SOURCE_READING_ORDER_CHANGED')
  need(text_hash(''.join(regions[mapped[rid]['region_id']]['text'] for rid in qids))==expected['question_sha256'],'SOURCE_QUESTION_TEXT_MISMATCH:'+key);need(text_hash(''.join(regions[mapped[rid]['region_id']]['text'] for rid in aids))==expected['answer_sha256'],'SOURCE_ANSWER_TEXT_MISMATCH:'+key)
  for choice in expected['choices']:need(text_hash(regions[mapped[choice['source_region_id']]['region_id']]['text'])==choice['text_sha256'],'SOURCE_OPTION_LABEL_OR_MATH_MISMATCH')
  option_count+=len(cids);diagram_count+=len(dids);answer_count+=len(aids)
 for rid,digest in pins['critical_component_text_sha256'].items():need(text_hash(regions[mapped[rid]['region_id']]['text'])==digest,'CRITICAL_CROSS_COLUMN_COMPONENT:'+rid)
 need(len(all_owned)==len(set(all_owned))==65 and set(all_owned)==set(frags),'FRAGMENT_OWNERSHIP_CLOSURE');need(option_count==28 and diagram_count==5 and answer_count==16 and blank_runs==5,'CONTENT_COUNTS')
 need(side['human_verified'] is False and side['a_owner_acceptance'] is False and side['business_acceptance'] is False and side['platform_actions']==[],'FALSE_ACCEPTANCE_OR_PLATFORM_CLAIM');need(side['b_content_ready'] is True and side['b_content_issues']==[] and side['pending_option_geometry']==[] and side['unfilled_question_blanks']==5,'CONTENT_READINESS_MISMATCH')
 need(all(v['severity']=='info' and 'COMPLETE' not in v['blocks'] for v in check['issues']),'UNRESOLVED_CONTENT_GATE')
 return {'schema':'IndependentSection2C01SourceAudit/v1','status':'SOURCE_CONTENT_BINDINGS_RICH_MATH_AND_OWNERSHIP_MATCH','questions':15,'source_regions':65,'graph_fragments':65,'independent_options':28,'diagrams':5,'answer_fragments':16,'selected_answer_relations':15,'unfilled_blanks':blank_runs,'math_runs_source_and_rendering_checked':math_runs,'critical_cross_column_components_checked':4,'resource_files_hash_verified':len(resources),'source_geometry_checked':65,'intentionally_wrong_q7_question_preserved':True,'q9_squared_distractor_preserved':True,'q13_fraction_distractor_preserved':True,'public_path_privacy_check':'PASS','platform_requests':0,'human_acceptance':False,'a_owner_acceptance':False}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('delivery','pins','out'):p.add_argument('--'+key,required=True)
 args=p.parse_args()
 try:result=audit(args.delivery,args.pins);code=0
 except (ValueError,KeyError,TypeError,OSError) as error:result={'status':'REJECTED','error':str(error),'platform_requests':0};code=2
 with Path(args.out).open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
 print(json.dumps(result,ensure_ascii=False));raise SystemExit(code)
