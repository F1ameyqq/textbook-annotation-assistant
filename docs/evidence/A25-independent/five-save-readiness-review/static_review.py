"""Static closure of declared frozen plans and seven unstarted outer inputs.

No product function, launcher, subprocess, profile or network is invoked here.
"""
import ast,copy,hashlib,json,re
from pathlib import Path,PureWindowsPath
PUB=Path(__file__).resolve().parent
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-readiness-review-20261023')
BASE=STAGE/'project/post-manual-login-source'
PACK=BASE/'five-candidates-v2'
NATIVE=BASE/'runs/usense-readonly-20261023-103259-3becb927'
OUTER=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/five-save-outer-root-frozen')
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def read(p):return json.loads(p.read_bytes())
def same(a,b):
 if type(a)!=type(b):return False
 if isinstance(a,dict):return list(a)==list(b) and all(same(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
 return a==b
def norm(p):return PureWindowsPath(str(p)).as_posix().lower()
def main():
 registry=read(STAGE/'registry.json')
 def ref(p):
  target=Path(registry[norm(p)]);assert target.is_relative_to(STAGE);return target
 mraw=(OUTER/'manifest.json').read_bytes();iraw=(OUTER/'root-index.json').read_bytes()
 assert sha(mraw)=='e0f8f59981006cf6d729cc6eabb771a691c1e51ada99972c44dd98b41885abe5'
 assert sha(iraw)=='d0b279302d296ba2b35d72a0f14c693999d46aa26469954a6fe232696b178c0a'
 m=json.loads(mraw);ix=json.loads(iraw);assert len(m['members'])==len(ix['members'])==7
 outercopy=STAGE/'outer';outercopy.mkdir(exist_ok=True)
 def copy_exact(path,raw):
  if path.exists():assert path.read_bytes()==raw
  else:put(path,raw)
 copy_exact(outercopy/'manifest.json',mraw);copy_exact(outercopy/'root-index.json',iraw);inputs=[]
 for item,entry in zip(m['members'],ix['members']):
  assert all(entry[k]==v for k,v in item.items())
  source=Path(entry['root_frozen_path']);assert source.parent==OUTER
  raw=source.read_bytes();assert sha(raw)==entry['sha256'] and len(raw)==entry['bytes']
  target=outercopy/source.name;copy_exact(target,raw)
  inputs.append({'original':entry['source_path'],'root_frozen_source':str(source),'copy':str(target),'bytes':len(raw),'sha256':sha(raw)})
 launcher=outercopy/'raw-01-launch-five-save-once.py';text=launcher.read_text(encoding='utf-8');tree=ast.parse(text)
 assert sha(launcher.read_bytes())=='940283e0336f2f3936f8f5d6372b90ef8294034e21d07177754077e49c5a5d62'
 assert text.index("os.replace(temporary, authority_path)")<text.index('result = holder.run(')
 assert "command[command.index('--authorization-reference') + 1] = str(authority_path)" in text
 assert "command[command.index('--tls-approval-reference') + 1] = str(authority_path)" in text
 template=read(outercopy/'raw-03-authority-fields.NOT-ACTIVATED.json');binding=read(outercopy/'raw-04-binding.json')
 assert template['status']=='NOT_ACTIVATED_TEMPLATE_NOT_AUTHORITY' and binding['actual_process_starts']==binding['actual_saves']==0
 assert template['limits']['attempts_spent']==0 and template['limits']['attempts_remaining']==1
 checkpoint=read(BASE/'checkpoint-five-save-readiness.json');targets=read(PACK/'targets.json');source=read(PACK/'source-binding.json');identity=read(BASE/'five-identity-binding.json')
 assert same(template['five_candidates_and_plans'],read(PACK/'five-save-plans.json')['plans'])
 assert template['readiness_checkpoint_sha256']==sha((BASE/'checkpoint-five-save-readiness.json').read_bytes())
 assert template['targets_manifest_sha256']==sha((PACK/'targets.json').read_bytes())
 assert checkpoint['implementation_sha256']==template['implementation_sha256']=='5ddfe19c4cb0f2b98555c927a1d205f1165ab23ecac981896627445e29f3c2c8'
 runtime=STAGE/'snapshot/src/annotation/runtime/usense_live'
 members=[{'path':p.name,'sha256':sha(p.read_bytes())} for p in sorted(runtime.glob('*.py'))]
 assert len(members)==19 and sha(json.dumps(members,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode())==template['implementation_sha256']
 assert sha((STAGE/'project/owned_process.py').read_bytes())==template['fixed_supervisor']['sha256']=='a1582782024994d841ddeadc0e2df6c8ef29a35bc8e428dcb4dd8b8cdc589ee8'
 for key in ['targets_manifest','source_binding','validation']:
  assert sha(ref(checkpoint[key]['path']).read_bytes())==checkpoint[key]['sha256']
 baseline=targets['baseline'];assert sha((NATIVE/'capture-summary.json').read_bytes())==baseline['capture_summary_sha256']==source['capture_summary_sha256']==identity['capture_summary_sha256']
 for name,digest in baseline['files'].items():assert sha((NATIVE/(name+'.json')).read_bytes())==digest
 historical=STAGE/'project/transport-revision/inputs/historical-source-url-bindings.json';historical_binding=read(historical)
 for page in source['pages']:
  assert sha(ref(page['image_ref']).read_bytes())==page['image_sha256']
  assert sha(historical.read_bytes())==page['historical_url_binding_sha256']
  nativepage=NATIVE/('page_'+str(page['viewer_page'])+'.json');assert sha(nativepage.read_bytes())==page['current_page_response_sha256']
  data=read(nativepage)['data']['pages'];assert len(data)==1 and data[0]['page_index']==page['returned_page_index']
  digest=sha(data[0]['image'].encode());assert digest==page['current_url_sha256']
  historical_match=[x for x in historical_binding['inputs'] if any(u['url_sha256']==digest for u in x['image_urls'])];assert len(historical_match)==1
  # Original A05 paths are reference strings; the bounded packet exports copies
  # under transport-revision/inputs, resolved only by their declared raw hash.
  command_hash=historical_match[0]['command_sha256']
  matches=[Path(v) for k,v in registry.items() if 'command' in k and sha(Path(v).read_bytes())==command_hash]
  assert len(matches)==1
 assert len(targets['targets'])==5 and [x['printed_question'] for x in targets['targets']]==list(range(1,6))
 assert {x['target']['node_id'] for x in targets['targets']}.isdisjoint(identity['first17_node_ids'])
 rows=[]
 for index,item in enumerate(targets['targets'],1):
  candidate=read(ref(item['candidate']['path']));assert sha(ref(item['candidate']['path']).read_bytes())==item['candidate']['sha256']
  for path,digest in item['review_evidence'].items():assert sha(ref(path).read_bytes())==digest
  planpath=PACK/f'printed-{index}-plan.json';plan=read(planpath);review=read(PACK/f'printed-{index}-source-review.json');target=item['target'];q=target['question_order']
  assert q==index+17 and same(target,plan['target']) and same(target,candidate['target']) and same(target,source['targets'][index-1]['target'])
  assert target['lesson_directory_id']=='dir-1792063578574-2a6vq8zom' and target['book_id']=='46007447'
  assert same(candidate['approved_changes'],plan['approved_changes'])
  before=plan['before'];expected=plan['expected']
  for key,name in [('directory','directory'),('frames','frames'),('annotations',f'q{q}_annotations'),('info',f'q{q}_info')]:
   assert same(before[key],read(NATIVE/(name+'.json')));assert same(before[key],expected[key])
  assert len(before['frames']['data'])==76 and len(before['annotations']['data'])==[3,4,3,4,2][index-1]
  assert str(before['info']['data']['id'])==target['info_id']
  assert same(before['zones'],{z:read(NATIVE/f'q{q}_{z}.json') for z in ['question','choice','answer','analysis','knowledge_point']})
  rebuilt=copy.deepcopy(before);changed=list(plan['approved_changes']);assert changed==(['question'] if index in (1,4) else ['question','answer'])
  for zone,change in plan['approved_changes'].items():
   assert '\ufffd' not in change['text'] and change['reviewed_text_sha256']==sha(change['text'].encode())
   assert sha(ref(change['source_ref']).read_bytes())==change['source_sha256']
   assert ref(change['review_ref'])==PACK/f'printed-{index}-source-review.json'
   assert review['reviewed_zones'][zone]['text']==change['text'] and review['reviewed_zones'][zone]['text_sha256']==change['reviewed_text_sha256']
   old=rebuilt['zones'][zone]['data'];zone_frames=[a for a in before['annotations']['data'] if a['type']==zone]
   rects=[a['rect_id'] for a in sorted(zone_frames,key=lambda a:int(a['image_order_in_annotation_zone']))]
   if old['success'] is True:old['ocr_result']=change['text']
   else:rebuilt['zones'][zone]['data']={'rect_ids':rects,'ocr_result':change['text'],'success':True}
  assert same(rebuilt,expected)
  diagram=source['targets'][index-1]['diagram'];assert same(diagram,review['diagram_binding'])
  frame=[x for x in before['annotations']['data'] if x['rect_id']==diagram['rect_id']];assert len(frame)==1
  for key in ['page_index','rect_bbox','image_path']:assert frame[0][key]==diagram[key]
  assert sha(diagram['image_path'].encode())==diagram['image_path_sha256']
  assert re.findall(r'<img src="([^"]+)"',candidate['approved_changes']['question']['text'])==[diagram['image_path']]
  assert same(review['source_pages'],source['pages'])
  payload=plan['payload_candidate'];assert payload['annotations_upsert']==payload['annotations_delete_rect_ids']==payload['ocr_delete_zones']==[]
  assert payload['is_new_question_insertion'] is False and payload['insert_after_order'] is None and payload['created_by'] is None
  assert same(payload['question_info'],{k:before['info']['data'][k] for k in ['tishi','tilei','tihao']})
  assert plan['mutation_required'] is True and plan['write_authorized_by_this_module'] is False
  stable={k:target[k] for k in ['book_id','node_id','info_id']};assert plan['ledger_key']=='usense-existing-'+sha(json.dumps(stable,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())
  rows.append({'printed_question':index,'native_order':q,'plan_file_sha256':sha(planpath.read_bytes()),'plan_sha256':plan['plan_sha256'],'changed_zones':changed,'all76frames_and_complete_directory_annotations_info_preserved':True,'untouched_zones_preserved':True,'existing_image_by_rect_identity_preserved':True,'no_upload_frame_or_directory_mutation':True,'current_remote_crop_availability':'NOT_FETCHED_NOT_ASSERTED'})
 # Explicit content conclusions were reached by manual viewing of both frozen JPEGs.
 answers=['(a+b), c; (a+b)^2=4*(ab/2)+c^2; c^2=a^2+b^2','D; sqrt(1.5^2+2^2)=2.5 m','4 m; sqrt((8-3)^2-3^2)=4','100 mm; sqrt(80^2+60^2)=100','52 km; sqrt((24*2)^2+(10*2)^2)=52']
 for row,answer in zip(rows,answers):row['independent_manual_content_and_math']='ACCEPT';row['answer_check']=answer
 assert read(PACK/'printed-2-candidate.json')['approved_changes']['answer']['text']=='D'
 assert read(PACK/'printed-3-candidate.json')['approved_changes']['answer']['text']=='4'
 assert checkpoint['actual']=={'writers':0,'readers':0,'posts':0,'ledger_entries':0}
 put(PUB/'plans-review.json',enc({'schema':'A25IndependentFivePlanStaticClosure/v1','status':'PASS_OFFLINE_ONLY','targets_manifest_sha256':sha((PACK/'targets.json').read_bytes()),'runtime_members':members,'implementation_unchanged':True,'stable_nodes_disjoint_from_first17':True,'source_pages':'Two frozen historical JPEGs manually viewed; current metadata URL/index/hash binding verified; remote pixels freshness not asserted','rows':rows,'answer1_answer4_and_choice2_preserved':True,'question1_question5_existing_full_text_and_diagrams_image_retained':True,'historical_incomplete_plans_record_retained_not_current_readiness':'five-save-plans.json entry_defect_status is historical; frozen checkpoint, fixed runner, raw validation and independent disk boundary establish this review','helper_errors_retained':'Author records initial wrong PLAN_TAMPERED expectation AssertionError and quoting SyntaxError; original initial error stdout/stderr not separately frozen; no root-cause inference beyond actual sorted-plan OCR_ABSENCE_NOT_PROVEN counterexample','real_ledger_profile_network_browser_access':0}))
 lines=text.splitlines()
 markers=['def verify_fixed','def main','EVIDENCE.mkdir(exist_ok=False)',"write_new(EVIDENCE / 'single-launch.json'",'os.replace(temporary, authority_path)','result = holder.run(']
 positions={marker:next(i+1 for i,line in enumerate(lines) if marker in line) for marker in markers}
 put(PUB/'outer-review.json',enc({'schema':'A25IndependentOuterStaticReview/v1','status':'ACCEPTED_STATIC_LAUNCH_CONDITIONS_ONLY','manifest_sha256':sha(mraw),'root_index_sha256':sha(iraw),'inputs':inputs,'launcher_sha256':sha(launcher.read_bytes()),'line_references':positions,'verified_conditions':['120 fixed original and frozen member hashes; checkpoint and delivery hash','clean product HEAD 8990e1e3; unchanged 19-member implementation; Python executable and accepted supervisor hashes','fresh output and exclusive outer directory; empty ledger and profile LOCKS','root fresh ACTIVE unique authority; product/checkpoint/targets/implementation/launcher hashes; original profile/ledger; DIRECT; exact original leaf/SPKI','one unspent batch; exact five writers/readers and 10 contexts/navigations/probes; 120 business GET; no login/image/upload/OCR/frame/directory actions','both write and TLS references replaced with same new root authority','intent saved and atomic authority spend before one holder.run, whole-batch timeout <=900s; no retry'], 'template_not_authority':True,'launcher_describe_only_record':'Author frozen exit0 record only, not rerun independently; no live execution', 'profile_process_query':'NOT_IMPLEMENTED_BY_LAUNCHER. Root must observe zero matching original-profile processes before activation. Coordinator reports Win32_Process exact-path msedge count0 at 2026-10-23T11:07:17.0006414Z; root-side observation, not independently repeated here.','formal_report_binding':'Root must bind this final report and root receipt path+raw SHA in unique new authority; launcher does not validate their report content itself.','release_scope':'Final whole-batch Job/held-identity release only; runner proves writer process exit then fresh separate reader plus individual context/runtime release. Final Job0 cannot establish per-writer sequential OS descendant release.','new_tests_or_live_executions':0}))
 print(json.dumps({'static_plans':5,'outer_raw_members':7,'implementation_members':19,'status':'PASS_OFFLINE_ONLY','new_product_tests_or_live':0}))
if __name__=='__main__':main()
