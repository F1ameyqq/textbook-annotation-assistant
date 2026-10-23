"""Independent static capture/identity audit; no product import, test or network."""
import hashlib,json,math,re
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path,PureWindowsPath
PUB=Path(__file__).resolve().parent
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/post-manual-login-source-review-20261023')
ZONES=('question','choice','answer','analysis','knowledge_point')
BOOK='46007447';ORIGIN='https://www.usense.com';TARGET=ORIGIN+'/qieti/annotateUnified'
def sha(b):return hashlib.sha256(b).hexdigest()
def unique(pairs):
 d={}
 for k,v in pairs:
  assert k not in d,'duplicate JSON key';d[k]=v
 return d
def read(p):return json.loads(p.read_bytes(),object_pairs_hook=unique,parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
def same(a,b):return json.dumps(a,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(b,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def dt(v):return datetime.fromisoformat(re.sub(r'(\.\d{6})\d+(?=[+-]|Z|$)',r'\1',v))
def norm(v):return PureWindowsPath(v).as_posix().lower()
def order(v):
 assert type(v) is int or type(v) is str and re.fullmatch(r'0|[1-9][0-9]*',v)
 return int(v)
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def process(r,label,expected):
 v=read(r/'evidence'/(label+'.process.json'));assert v['exit_code']==expected
 for name in ('stdout','stderr'):
  raw=(r/'evidence'/(label+'.'+name)).read_bytes();assert len(raw)==v[name]['bytes'] and sha(raw)==v[name]['sha256']
 assert v['owned_os_release_confirmed'] is True and v['job_active_processes_after']==0 and v['errors']==[]
 assert all(v[k] is True for k in ('job_assigned_before_resume','launcher_exit_signaled','thread_handle_closed','process_handle_closed','job_handle_closed'))
 assert all(p['creation_filetime']>0 and p['image'] and p['exit_signaled'] is True and p['handle_closed'] is True for p in v['observed_processes'])
 return v
def main():
 r=STAGE/'raw';run=r/'runs/usense-readonly-20261023-103259-3becb927';cp=read(r/'checkpoint-current-source.json');binding=read(r/'five-identity-binding.json');before=read(r/'authority-before-launch.raw.json');after=read(r/'authority.json');launch=read(r/'single-launch.json');cfgraw=(r/'configs/current-source-01.json').read_bytes();cfg=json.loads(cfgraw);summary=read(run/'capture-summary.json');release=read(run/'release.json');probe=read(run/'tls-probe.json');claim=read(run/'claim.json');configbinding=read(r/'evidence/config-binding-01.json')
 assert cp['authority_id']==before['authority_id']==after['authority_id']==launch['authority_id']==configbinding['authority_id']=='a2c3c02a-3f8c-419a-8390-36fe5d4bf60f'
 cfgsha=sha(cfgraw);assert cfgsha==cp['config_sha256']==launch['config_sha256']==configbinding['config_sha256']==summary['config_sha256']==release['config_sha256']==claim['config_sha256']
 assert sha((r/'authority-before-launch.raw.json').read_bytes())==launch['authority_original_sha256']==configbinding['authority_original_sha256']
 implementation='5ddfe19c4cb0f2b98555c927a1d205f1165ab23ecac981896627445e29f3c2c8';assert before['implementation_sha256']==cfg['implementation_sha256']==launch['implementation_sha256']==cp['implementation_sha256']==implementation
 assert before['product_commit']=='afc9d761294203e7cfb8086a82f1a7fdd8724372'
 assert before['limits']['attempts_spent']==0 and before['limits']['attempts_remaining']==1 and after['limits']['attempts_spent']==1 and after['limits']['attempts_remaining']==0 and after['launch_binding']==launch
 assert launch['attempts_spent']==1 and launch['attempts_remaining']==0 and launch['retry_allowed'] is False and launch['login_and_save_attempts_authorized']==0 and before['old_rounds']==after['old_rounds'] and before['old_rounds']['reopened'] is False
 assert all(v['remaining']==0 for v in before['old_rounds'].values() if type(v) is dict and 'remaining' in v)
 assert cfg['transport']==summary['transport']==probe['transport']==launch['transport']=={'mode':'DIRECT','proxy_server':None}
 assert norm(cfg['profile']['directory'])==norm(before['profile'])==norm('D:/1800/.local/browser-profiles/937cbc0b7541861c7c68')
 endpoints={'directory':'/qieti/api/annotate_ocr/directory/get?file_id='+BOOK,'frames':'/qieti/api/annotate_pic/get_manual_annotations_unified/'+BOOK,'source':'/qieti/api/annotate_pic/pre_annotation_source/'+BOOK+'?annotationType=mr_pre'}
 for q in range(18,23):
  endpoints[f'q{q}_annotations']=f'/qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level/{BOOK}/{q}';endpoints[f'q{q}_info']=f'/qieti/api/annotate_pic/get_question_info/{BOOK}/{q}'
  for z in ZONES:endpoints[f'q{q}_{z}']=f'/qieti/api/verify_annotation/get-ocr-annotation?file_id={BOOK}&question_order={q}&zone={z}'
 for p in (12,173):endpoints[f'page_{p}']=f'/qieti/api/annotate_pic/pre_annotation/{BOOK}?pageNum={p}&annotationType=mr_pre'
 assert len(endpoints)==40 and set(summary['captures'])==set(endpoints) and summary['status']=='NATIVE_GETS_CAPTURED' and summary['save_attempts']==0 and summary['viewer_rendered'] is False
 assert len(cfg['allowed_get'])==41 and {v['url'] for v in cfg['allowed_get']}=={TARGET}|{ORIGIN+p for p in endpoints.values()} and all(v['max_requests']==1 for v in cfg['allowed_get'])
 native={};raw_bindings={}
 for name in endpoints:
  raw=(run/(name+'.json')).read_bytes();cap=summary['captures'][name];assert cap['filename']==name+'.json' and cap['bytes']==len(raw) and cap['sha256']==sha(raw) and cap['status']==200 and cap['request_counts']=={'context':1,'native':1}
  native[name]=read(run/(name+'.json'));assert type(native[name]) is dict and type(native[name]['code']) is int and native[name]['code']==0
  raw_bindings[name]={'bytes':len(raw),'sha256':sha(raw)}
 events=read(run/'network-events.json');expected=Counter((layer,sha((ORIGIN+p).encode())) for p in endpoints.values() for layer in ('context','native'));expected[('native',sha(TARGET.encode()))]+=1
 assert len(events)==81 and all(e['allowed'] is True and e['method']=='GET' and e['redirected'] is False for e in events) and Counter((e['layer'],e['url_sha256']) for e in events)==expected
 nodes=[];seen=set()
 def walk(rows,parent=None):
  assert type(rows) is list
  for n in rows:
   assert type(n) is dict and type(n['id']) is str and n['id'] and n['id'] not in seen;seen.add(n['id']);children=n.get('children',[]);assert type(children) is list and type(n.get('isQuestion',False)) is bool
   if n.get('isQuestion',False):
    assert not children and parent is not None;nodes.append((n,parent));assert order(n['order_in_level'])==len(nodes)
   else:walk(children,n)
 walk(native['directory']['data']['directory_data']);assert len(nodes)==23
 first17=[n['id'] for n,parent in nodes[:17]];assert first17==binding['first17_node_ids']
 frames=native['frames']['data'];assert type(frames) is list and len(frames)==76 and len({f['rect_id'] for f in frames})==76 and all(f['file_id']==BOOK for f in frames)
 source=native['source']['data'];assert str(source['file_id'])==BOOK and source['source']=='legacy_db' and source['annotation_type']=='mr_pre' and source['total_pages']==214
 history_path=PUB.parent/'transport-review/plan-review.json';history=read(history_path);save(STAGE/'references/historical-page-reference.json',history)
 source_pages={}
 for viewer in (12,173):
  page=native[f'page_{viewer}']['data'];assert str(page['file_id'])==BOOK and page['source']=='legacy_db' and len(page['pages'])==1;row=page['pages'][0];historical=next(v for v in history['historical_images_verified'] if v['viewer']==viewer)
  assert row['page_index']==viewer-1 and sha(row['image'].encode())==historical['historical_url_sha256']
  source_pages[viewer]={'viewer':viewer,'server_page_index':row['page_index'],'source':'legacy_db','current_image_url_sha256':sha(row['image'].encode()),'historical_image_sha256':historical['sha256'],'historical_dimensions':historical['dimensions'],'remote_current_image_bytes_retrieved':False}
 assert sha((r/'five-identity-binding.json').read_bytes())==cp['five_identity_binding']['sha256'] and len((r/'five-identity-binding.json').read_bytes())==cp['five_identity_binding']['bytes'] and sha((run/'capture-summary.json').read_bytes())==binding['capture_summary_sha256']
 targets=[];keys=[];seen_info=set();target_frames=0
 for index,item in enumerate(binding['targets'],1):
  t=item['target'];q=17+index;assert item['printed_question']==index and item['historical_global_order']==16+index and t['book_id']==BOOK and t['question_order']==q
  node,parent=nodes[q-1];assert node['id']==t['node_id'] and parent['id']==t['lesson_directory_id'] and parent['label']==item['actual_parent_label'] and node['id'] not in first17
  info=native[f'q{q}_info']['data'];assert info['id']==t['info_id'] and info['file_id']==BOOK and order(info['order_in_level'])==q and all(k in info for k in ['tishi','tilei','tihao','updated_at']) and info['id'] not in seen_info;seen_info.add(info['id'])
  selected=[f for f in frames if f.get('belong_to_level')=='question_level' and order(f['order_in_level'])==q];ann=native[f'q{q}_annotations']['data'];assert same(selected,ann) and len(ann)==item['frames'] and len(ann)>0;target_frames+=len(ann)
  zone_facts={}
  for f in ann:
   assert f['directory_id']==parent['id'] and f['belong_to_level']=='question_level' and order(f['order_in_level'])==q and f['page_index'] in source_pages
   bbox=[float(x) for x in f['rect_bbox'].split(',')];w,h=source_pages[f['page_index']]['historical_dimensions'];assert len(bbox)==4 and all(math.isfinite(x) for x in bbox) and 0<=bbox[0]<bbox[2]<=w and 0<=bbox[1]<bbox[3]<=h
  for zone in ZONES:
   rows=[f for f in ann if f['type']==zone];orders=[order(f['image_order_in_annotation_zone']) for f in rows];assert len(orders)==len(set(orders));ids=[f['rect_id'] for f in sorted(rows,key=lambda f:order(f['image_order_in_annotation_zone']))]
   state=native[f'q{q}_{zone}']['data'];assert type(state['success']) is bool
   if state['success']:
    assert type(state['ocr_result']) is str and type(state['rect_ids']) is list and ids and same(state['rect_ids'],ids);chars=len(state['ocr_result'])
   else:assert state=={'success':False,'message':'未找到标注结果'};chars=0
   assert item['zone_states'][zone]['success']==state['success'] and item['zone_states'][zone]['text_chars']==chars and item['zone_states'][zone]['rect_ids']==state.get('rect_ids')
   zone_facts[zone]={'present':state['success'],'text_chars':chars,'rect_ids':state.get('rect_ids')}
  stable={'book_id':t['book_id'],'node_id':t['node_id'],'info_id':t['info_id']};key='usense-existing-'+sha(json.dumps(stable,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode());assert key==item['stable_ledger_key'];keys.append(key)
  subset={k:raw_bindings[k] for k in raw_bindings if k.startswith(f'q{q}_')}
  targets.append({'printed_question':index,'historical_global_order':16+index,'target':t,'actual_parent_label':parent['label'],'stable_ledger_key':key,'frames':len(ann),'zones':zone_facts,'original_seven_response_hashes':subset,'snapshot_identity_and_rect_binding':'VERIFIED_STATIC','source_content_review':'NEXT_FIXED_CANDIDATE_PACKAGE'})
 assert len(targets)==len(set(keys))==5 and target_frames==16 and cp['targets']==[{k:item[k] for k in ['printed_question','historical_global_order','target','stable_ledger_key','snapshot_valid']} for item in binding['targets']]
 assert all(t['target']['lesson_directory_id']=='dir-1792063578574-2a6vq8zom' for t in targets)
 assert summary['release']==release and all(release[k] is True for k in ['context_created','runtime_started','context_closed','runtime_stopped','context_runtime_release_confirmed']) and release['pending_callbacks']==0 and release['errors']==[] and release['automatic_login_performed'] is False and release['automatic_retry_allowed'] is False and release['login_requests_per_layer']=={} and release['save_attempts']==0
 assert probe['status']=='EXACT_LEAF_CONFIRMED' and probe['leaf_sha256']==cfg['tls']['leaf_der_sha256']=='52d8642145282846969a29b97c5c3aaae4c0203c4a6bc06906478f13445e3941' and probe['attempts']==1 and probe['fallback_allowed'] is False
 holders={name:process(r,name,0) for name in ['runtime-binding-01','configure-01','capture-01']};holder=holders['capture-01'];identities=holder['observed_processes'];assert len(identities)==len({p['pid'] for p in identities})==13 and all(p['exit_code']==0 for p in identities)
 assert read(r/'evidence/capture-01.stdout')==summary and norm(holder['argv'][0])==norm(before['runtime']['executable'])
 assert dt(launch['at'])<dt(holder['started_at'])<dt(summary['finished_at'])<=dt(holder['finished_at']) and dt(cfg['not_before'])<=dt(launch['at']) and dt(holder['finished_at'])<=dt(cfg['expires_at']) and (dt(cfg['expires_at'])-dt(cfg['not_before'])).total_seconds()<=900
 assert all(dt(holder['started_at'])<dt(v['observed_at'])<dt(summary['finished_at']) for v in summary['captures'].values())
 pre=read(r/'evidence/profile-prelaunch-observation.json');assert pre['matching_processes']==[] and pre['lock_names']==[] and pre['profile_contents_read'] is False
 assert cp['save_attempts']==cp['login_attempts']==0 and cp['attempts_spent']==1 and cp['attempts_remaining']==0 and cp['ledger_directory_exists'] is False and cp['ledger_initialization']=='ROOT_PENDING'
 save(PUB/'identity-review.json',{'schema':'A25IndependentFiveCurrentIdentityReview/v1','capture_manifest_sha256':'64e9da291eeaa24648b74231d5aba159b3e9c8d9e3bc22c962ada1b857bd3709','capture_summary_sha256':sha((run/'capture-summary.json').read_bytes()),'first17_current_node_ids':first17,'target_node_ids_disjoint_from_current_first17':True,'targets':targets,'stable_ledger_rule':'book_id,node_id,info_id in that insertion order; excludes native order, parent and plan hash','ledger_root':str(PureWindowsPath(before['profile']).parent/'usense-existing-ledger'),'ledger_initialization':'NOT_PERFORMED; root must bind existing-intent/predecessor reconciliation and exact five keys','first17_content_or_B_private_evidence_acceptance':False})
 result={'schema':'A25IndependentPostManualCurrentSourceResult/v1','at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'result':'ACCEPTED_FIXED_CURRENT_SOURCE_READ_FIVE_NATIVE_IDENTITIES_AND_OWN_RELEASE_ONLY','reviewer_thread_id':'01a166e8-3f23-7192-a560-4724adca74b1','authority_id':before['authority_id'],'manifest_sha256':'64e9da291eeaa24648b74231d5aba159b3e9c8d9e3bc22c962ada1b857bd3709','checkpoint_sha256':'16b48db5a0e5443d49c7a340e08cee34e63a541ca5c48fa145bdb6e39901f3ca','raw_members':62,'config_sha256':cfgsha,'implementation_sha256':implementation,'successful_GETs':40,'all_status_200_code_0':True,'dual_guard_each_one':True,'audit_events':81,'full_original_HTTP_bytes_preserved_and_hashed':True,'strict_JSON_duplicate_and_nonfinite_rejection':True,'current_business_session':'PROVEN_FOR_THESE_40_BOUNDED_GETS_ONLY','question_nodes':23,'all_frames':76,'five_target_frames':16,'five_native_identities':'VERIFIED_STATIC_FROM_RAW_DIRECTORY_FRAME_INFO_ZONE_BINDING','stable_ledger_keys':keys,'five_node_ids_disjoint_from_current_first17':True,'actual_parent_conflict_preserved':True,'source_pages':source_pages,'source_metadata_origin':'legacy_db; total_pages214; viewer12/173 map to server11/172','source_image_content_and_candidate_review':'NEXT_FIXED_PACKAGE; no new image download, no claim of remote image-byte equality','held_process_ids':[p['pid'] for p in identities],'held_process_count':13,'context_runtime_release_confirmed':True,'owned_os_release_confirmed':True,'job_active_processes_after':0,'budget':{'spent':1,'remaining':0,'retry':False},'save_attempts':0,'login_attempts':0,'ledger_initialization':'ROOT_PENDING_NOT_AUTHORIZED_OR_EXECUTED_BY_REVIEW','candidate_write_plan_actual_save_readback_export':'PENDING_NEXT_FIXED_PACKAGE_OR_DISPATCH','author_active_candidate_directory_reads':0,'reviewer_product_tests_platform_network_model_OCR_actions':0,'new_activation':False,'findings_requiring_rework':[],'review_status':'COMPLETE_RELEASED','static_reference':{'historical_page_reference_path':str(history_path),'sha256':sha(history_path.read_bytes())}}
 save(PUB/'result.json',result);print(json.dumps({'result':result['result'],'GETs':40,'nodes':23,'frames':76,'five_target_frames':16,'ledger_keys':5,'held_processes':13,'budget':[1,0]}))
if __name__=='__main__':main()
