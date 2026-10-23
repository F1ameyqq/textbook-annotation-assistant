"""Finite verification of frozen actual bytes; no platform or suite execution."""
import copy,hashlib,json,sys,traceback
from collections import Counter
from datetime import datetime
from pathlib import Path
P=Path('D:/1800/.local/stages/a28-independent-20261023/actual-v1-review')
O=Path('D:/1800/docs/evidence/A28-independent/actual-v1-review')
R1=Path('D:/1800/.local/stages/a28-independent-20261023/code-r1-review')
sys.path.insert(0,str(R1/'workspace/src'))
from annotation.runtime.usense_live import lesson_insert as ins, update as u
from annotation.runtime.usense_live.config import endpoints
from annotation.runtime.usense_live.writer import POST
def audit(event,args):
 if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):raise RuntimeError('OFFLINE_REVIEW_DENIED:'+event)
 if event=='open' and isinstance(args[0],str) and ('browser-profiles' in args[0].lower() or 'worktrees/b-latest' in args[0].replace('\\','/').lower()):raise RuntimeError('ACTIVE_RESOURCE_READ_DENIED')
sys.addaudithook(audit)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def put(p,value):
 p.parent.mkdir(parents=True,exist_ok=True);raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')
 with p.open('xb') as f:f.write(raw)
 return {'path':str(p),'bytes':len(raw),'sha256':sha(raw)}
def dt(value):return datetime.fromisoformat(value.replace('Z','+00:00'))
def norm(p):return str(p).replace('\\','/').lower()
members=json.loads((O/'intake.json').read_bytes())['members']
def pick(suffix):
 rows=[r for r in members if norm(r['source_path']).endswith(suffix.lower())];assert len(rows)==1,suffix
 return rows[0]
def raw(suffix):
 r=pick(suffix);b=Path(r['copy']).read_bytes();assert sha(b)==r['sha256'];return b
def read(suffix):return u.loads(raw(suffix))
def check_release(r):
 assert r['context_closed'] is True and r['runtime_stopped'] is True and r['context_runtime_release_confirmed'] is True
 assert r['errors']==[] and r['pending_callbacks']==0 and r.get('unfinished_cleanup_tasks',0)==0
checked=[]
try:
 root=Path('D:/1800/.local/stages/a28-complete-lesson-production-20261023/root-production-actual-01')
 index_raw=(root/'root-index.json').read_bytes();assert sha(index_raw)=='faf288875e625d8331992641a264e533bb9d32d9b3c9d451c04202585cf81d77'
 index=json.loads(index_raw);assert len(index['members'])==306
 copied={norm(m['source_path']):Path(m['copy']) for m in members}
 copied[norm('D:/1800/.local/stages/a28-complete-lesson-production-20261023/production-actual-fixed.json')]=P/'production-actual-fixed.json'
 copied[norm('D:/1800/.local/stages/a28-complete-lesson-production-20261023/fixed-production-actual-01/raw-manifest.json')]=P/'raw-manifest.json'
 for row in index['members']:
  path=Path(row['root_frozen']);assert path.parent==root
  b=path.read_bytes();assert b==copied[norm(row['source_path'])].read_bytes() and sha(b)==row['sha256'] and len(b)==row['bytes']
 assert (P/'root-index.json').read_bytes()==index_raw
 assert json.loads((O/'root-binding.json').read_bytes())['root_raw_pairs']==306
 actual=u.loads((P/'production-actual-fixed.json').read_bytes());authority=read('/production-authority-r1.json')
 fixed=read('/fixed-delivery-r1.json');preflight=read('/live-01/batch-preflight.json');batch=read('/live-01/batch-summary.json')
 assert sha(raw('/production-authority-r1.json'))==actual['authority']['sha256']=='a42385ce6b9d416284292a2a9e11d2ed9da57677c953a3555ff1e368fc770727'
 assert sha(raw('/fixed-delivery-r1.json'))==actual['fixed_delivery_r1_sha256']==authority['fixed_delivery_sha256']=='98b99b1257bcf5669745a7cc7efe93949dea6930fe5486c85c7bd996464d9825'
 assert authority['formal_result_sha256']==sha(Path('D:/1800/docs/evidence/A28-independent/code-r1-review/result.json').read_bytes())
 assert authority['commit']==fixed['commit']==actual['commit']=='4658243f2055c38846713d2292e5f3ac44cc216e'
 assert authority['targets_manifest_sha256']==preflight['manifest_sha256']==fixed['targets_manifest']['sha256']
 assert authority['limits']==fixed['production_limits']=={'writers':4,'readers':4,'contexts':8,'posts':4,'business_gets':174,'login':0,'retries':0,'whole_process_seconds':900}
 assert preflight['ledger_files']==fixed['ledger_before']
 assert batch['status']=='ALL_FOUR_ACCEPTED' and batch['new_completed_count']==4 and batch['lesson_cumulative_count']==batch['lesson_denominator']==9
 assert batch['old_question_content_updates']==batch['human_interventions']==batch['ocr_calls']==0
 outer=read('/production-outer-01/process.process.json');once=read('/production-outer-01/launch-once.json')
 assert once['attempts_spent']==1 and once['attempts_remaining']==0 and once['authority_id']==authority['authority_id']
 assert once['authority_sha256']==actual['authority']['sha256'] and once['fixed_delivery_sha256']==authority['fixed_delivery_sha256']
 assert dt(authority['not_before'])<=dt(once['at'])<=dt(outer['started_at'])<dt(outer['finished_at'])<dt(authority['expires_at'])
 assert outer['job_assigned_before_resume'] and outer['resumed'] and outer['exit_code']==0 and outer['errors']==[]
 assert outer['job_active_processes_after']==0 and outer['owned_os_release_confirmed']
 for key in ('launcher_exit_signaled','thread_handle_closed','process_handle_closed','job_handle_closed'):assert outer[key] is True
 for name in ('stdout','stderr'):
  b=raw('/production-outer-01/process.'+name);assert sha(b)==outer[name]['sha256'] and len(b)==outer[name]['bytes']
 assert u.loads(raw('/production-outer-01/process.stdout'))=={'status':batch['status'],'results':batch['results']}
 observed=outer['observed_processes'];assert len({(r['pid'],r['creation_filetime']) for r in observed})==len(observed)
 assert all(r['exit_signaled'] and r['handle_closed'] and r['creation_filetime']>0 and dt(outer['started_at'])<=dt(r['observed_at'])<=dt(outer['finished_at']) for r in observed)
 observed_pids={r['pid'] for r in observed};assert outer['pid'] in observed_pids
 seconds=(dt(outer['finished_at'])-dt(outer['started_at'])).total_seconds()
 assert seconds==actual['timings']['production_wall_clock_seconds']==42.639465
 assert (dt(batch['finished_at'])-dt(batch['started_at'])).total_seconds()==actual['timings']['inner_batch_seconds']
 code_intake=json.loads(Path('D:/1800/docs/evidence/A28-independent/code-r1-review/intake.json').read_bytes())
 old_sources={norm(m['source_path']):m for m in code_intake['members']}
 source_provenance=[]
 for path,digest in preflight['evidence_file_sha256'].items():
  assert norm(path) in old_sources,path
  m=old_sources[norm(path)];assert m['sha256']==digest and sha(Path(m['copy']).read_bytes())==digest
  source_provenance.append({'source_path':path,'sha256':digest})
 prev={name:u.loads(Path(old_sources[norm(Path(fixed['baseline'])/(name+'.json'))]['copy']).read_bytes()) for name in ins.full_endpoints(tail_order=23)};assert prev==preflight['before'];prior_new={};newids=set();nodeids=set();runs=set();pids=set();wg=rg=0
 last_end=dt(outer['started_at']);original=copy.deepcopy(prev)
 for index,key in enumerate(('q6','q7','q8','q8-variant')):
  base='/live-01/'+key+'/'
  plan=read(base+'plan.json');planbytes=raw(base+'plan.json');ins.validate_insert_plan(plan)
  assert u.json_same(plan['before_full'],prev)
  approved=preflight['targets'][index];assert approved['logical_key']==key
  assert plan['candidate']==approved['candidate'] and plan['approved_new_content']==approved['approved_new_content']; assert u.json_same(plan['candidate'],u.loads(Path(old_sources[norm(plan['approved_new_content']['candidate_ref'])]['copy']).read_bytes()))
  order=23+index;assert plan['new_order']==order and plan['insert_after_order']==order-1
  wp=read(base+'writer-process-result.json');rp=read(base+'reader-process-result.json');w=wp['result'];r=rp['result']
  assert wp['exit_code']==rp['exit_code']==0 and wp['timed_out'] is False and rp['timed_out'] is False
  assert wp['pid']!=rp['pid'] and w['run_id']!=r['run_id']
  assert not {wp['pid'],rp['pid']} & pids and not {w['run_id'],r['run_id']} & runs
  pids.update((wp['pid'],rp['pid']));runs.update((w['run_id'],r['run_id']))
  assert {wp['pid'],rp['pid'],w['process_id']}<=observed_pids
  assert last_end<dt(wp['started_at'])<dt(w['send_intent_at'])<=dt(w['finished_at'])<=dt(wp['finished_at'])<dt(rp['started_at'])<dt(r['finished_at'])<=dt(rp['finished_at'])
  last_end=dt(rp['finished_at'])
  for kind,proc in [('writer',wp),('reader',rp)]:
   for stream in ('stdout','stderr'):assert sha(raw(base+kind+'-process-result.'+stream))==proc[stream+'_sha256']
   assert u.loads(raw(base+kind+'-process-result.stdout'))==proc['result']
  wd='/live-01/'+w['run_id']+'/';rd='/live-01/'+r['run_id']+'/'
  assert read(wd+'execution-result.json')==w and read(rd+'capture-summary.json')==r
  assert sha(raw(wd+'plan.json'))==sha(planbytes)==w['plan_file_sha256']
  for label,result in [('writer',w),('independent-reader',r)]:
   config=read(base+label+'-config.json');assert sha(raw(base+label+'-config.json'))==result['config_sha256']
   assert config['profile']['directory']==authority['profile'] and config['profile']['fingerprint']==authority['profile_fingerprint']
   assert config['implementation_sha256']==fixed['implementation_sha256'] and config['transport']==authority['transport']
   for field in ('origin','leaf_der_sha256','spki_sha256_base64'):assert config['tls'][field]==authority['tls'][field]
   check_release(result['release'])
  assert r['release']['automatic_login_performed'] is False and r['release']['automatic_retry_allowed'] is False and r['release']['login_requests_per_layer']=={}
  assert r['status']=='NATIVE_GETS_CAPTURED' and r['save_attempts']==0 and w['post_attempts']==1 and w['post_layers']=={'context':1,'native':1}
  assert w['http_status']==200 and w['receipt_exact_success'] is True
  before={name:read(wd+'before-'+name+'.json') for name in ins.full_endpoints(plan)}
  prewrite=ins.check_prewrite(plan,before);assert prewrite['ok'] and len(before)==13 and set(before)==set(w['prewrite_responses'])
  for name,cap in w['prewrite_responses'].items():
   b=raw(wd+'before-'+name+'.json');assert sha(b)==cap['sha256'] and len(b)==cap['bytes'] and cap['request_counts']=={'context':1,'native':1}
   assert dt(wp['started_at'])<dt(cap['observed_at'])<dt(w['send_intent_at'])
  wg+=len(before)
  names=endpoints(range(23,order+2),(12,13,173),source=True);assert set(names)==set(r['captures']) and len(names)==(20,27,34,41)[index]
  after={name:read(rd+name+'.json') for name in names}
  for name,cap in r['captures'].items():
   b=raw(rd+name+'.json');assert sha(b)==cap['sha256'] and len(b)==cap['bytes'] and cap['status']==200 and cap['request_counts']=={'context':1,'native':1}
   assert dt(wp['finished_at'])<dt(rp['started_at'])<=dt(cap['observed_at'])<=dt(r['finished_at'])
  rg+=len(after);receipt=read(wd+'native-receipt.json');assert sha(raw(wd+'native-receipt.json'))==w['receipt_sha256']
  decoded=ins.decode_receipt(plan,receipt);assert decoded['ok']
  subset={name:after[name] for name in endpoints((order,order+1),(12,13,173),source=True)}
  comparison=ins.compare_insert_readback(plan,subset,receipt,w['runtime_actor_hashes'],{'start':w['send_intent_at'],'end':w['finished_at']})
  put(P/'comparisons'/(key+'.json'),comparison);assert comparison['ok'],comparison['differences']
  ident=comparison['new_identity'];assert ident['info_id'] not in newids and ident['node_id'] not in nodeids
  newids.add(ident['info_id']);nodeids.add(ident['node_id'])
  assert all(u.json_same(value,after[name]) for name,value in prior_new.items())
  acceptance=read(base+'acceptance.json');assert acceptance['status']=='ACCEPTED_LESSON_INSERT' and all(acceptance['checks'].values())
  assert acceptance['comparison']==comparison and actual['results'][index]['new_identity']==ident
  network=read(wd+'network-events.json')
  posts=[e for e in network if e['method']=='POST'];assert len(posts)==2
  assert {e['layer'] for e in posts}=={'native','context'} and all(e['allowed'] and e['url_sha256']==sha(POST.encode()) for e in posts)
  assert all(e['method'] in ('GET','POST') and e['allowed'] for e in network)
  intent=read(wd+'send-intent.json');claim=read('/usense-existing-ledger/book46007447-lesson2-'+key+'.json')
  assert claim['automatic_retry_allowed'] is False and claim['intent_at']==w['send_intent_at'] and claim['plan_sha256']==plan['plan_sha256']
  assert claim['run_id']==w['run_id'] and claim['native_body_sha256']==w['native_body_sha256']==intent['native_body_sha256']
  assert claim['ledger_key']==plan['ledger_key']==w['ledger_key']
  checked.append({'logical_key':key,'new_identity':ident,'writer_pid':wp['pid'],'writer_runtime_pid':w['process_id'],'reader_pid':rp['pid'],
   'writer_run':w['run_id'],'reader_run':r['run_id'],'writer_gets':13,'reader_gets':len(after),'posts':1,'prewrite':prewrite['status'],
   'comparison_status':comparison['status'],'full_prior_new_content_preserved':True,'framework_release':True,'owned_process_ids_observed':True})
  prior_new.update({f'q{order}_{s}':after[f'q{order}_{s}'] for s in ins.SUFFIXES})
  prev={name:after[name] for name in ins.full_endpoints(tail_order=order+1)}
 assert wg==52 and rg==122 and wg+rg==174
 assert last_end<dt(outer['finished_at']) and len(newids)==len(nodeids)==4
 original_rows={r['rect_id']:r for r in original['frames']['data']};final_rows={r['rect_id']:r for r in prev['frames']['data']}
 old_non_tail=[ident for ident,row in original_rows.items() if str(row['order_in_level'])!='23']
 assert all(u.json_same(original_rows[i],final_rows[i]) for i in old_non_tail)
 old5=[i for i in old_non_tail if 18<=int(original_rows[i]['order_in_level'])<=22]
 assert all(u.json_same(original_rows[i],final_rows[i]) for i in old5)
 assert len(final_rows)==90 and len(original_rows)==76
 assert prev['q27_info']['data']['id']==ins.TAIL_INFO
 for zone in u.ZONES:assert u.json_same(original['q23_'+zone],prev['q27_'+zone])
 put(O/'verification.json',{'schema':'A28IndependentActualVerification/v1','status':'PASS_FIXED_FOUR_SAVES_FRESH_READBACKS_AND_OWN_RELEASE',
  'commit':authority['commit'],'authority_id':authority['authority_id'],'root_pairs':306,'actual_raw_members':304,'results':checked,
  'source_references_bound_to_accepted_R1':len(source_provenance),'posts':4,'writer_gets':wg,'reader_gets':rg,'business_gets':wg+rg,
  'new_frames':14,'final_frames':90,'old_non_tail_frames_raw_semantics_unchanged':len(old_non_tail),'old_five_frames_unchanged':len(old5),
  'old_five_native_content':'A25_A26_ACCEPTED_HISTORY_REUSED_NOT_FRESHLY_REFETCHED_IN_THIS_SCOPE',
  'tail_native_order_after':27,'tail_stable_node_and_info_preserved':True,'tail_original_zone_responses_preserved':True,
  'lesson_cumulative_units':9,'new_units':4,'previously_accepted_units':5,'excluded_next_section':'漫话勾股世界',
  'timings':{'production_wall_clock_seconds':seconds,'inner_batch_seconds':actual['timings']['inner_batch_seconds'],
   'production_start_local':dt(outer['started_at']).isoformat(),'production_finish_local':dt(outer['finished_at']).isoformat(),
   'whole_task_to_final_artifact':'NOT_YET_ACCEPTED'},
  'release':{'framework_contexts':8,'held_process_identities':len(observed),'all_observed_exit_signaled_and_handles_closed':True,
   'job_active_processes_after':0,'whole_job_release_confirmed':True,'actual_browser_process_images_observed':dict(Counter(Path(r['image']).name for r in observed))},
  'interventions':{'batch_launch_commands':1,'per_question_continuation_commands':0,'user_actions_or_logins_reported':0,
   'evidence_scope':'single fixed owned command and serial automatic process timestamps; no independent user activity telemetry'},
  'old_ledger_preservation':'accepted batch final recheck plus author fixed post-run hash-check declaration; no separate post-run copies of eight old ledger files',
  'native_export_and_display':'NOT_RUN_AT_THIS_ACTUAL_FREEZE_REVIEW_SEPARATE_INCREMENT',
  'platform_calls_by_reviewer':0,'offline_test_suites_rerun':0})
 print(json.dumps({'status':'PASS','four_actual_results':len(checked),'posts':4,'business_gets':174,'seconds':seconds,'observed_held_identities':len(observed)}))
except BaseException as exc:
 put(O/'verification-failure-corrected2.json',{'status':'STOPPED_FIRST_REVIEW_FAILURE','error_type':type(exc).__name__,'error':str(exc),
  'traceback':traceback.format_exc(),'completed_actual_questions':checked,'successors':'NOT_RUN','platform_calls':0})
 raise
