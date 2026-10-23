"""Static actual-evidence review; no product import or platform operation."""
import collections,copy,datetime,hashlib,json,re
from pathlib import Path,PureWindowsPath
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-actual-review-20261023')
OLD=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-readiness-review-20261023')
OB=OLD/'project/post-manual-login-source'
BASE='d:/1800/.local/stages/a25-lesson2-expansion-20261023/post-manual-login-source'
ZONES=['question','choice','answer','analysis','knowledge_point']
def sha(b):return hashlib.sha256(b).hexdigest()
def norm(p):return PureWindowsPath(str(p)).as_posix().lower()
def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError('Duplicate JSON key: '+k)
  d[k]=v
 return d
def loads(b):return json.loads(b,object_pairs_hook=unique,parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
def encode(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def put(p,v):
 with p.open('xb') as f:f.write(v)
def item(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def timestamp(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def deep_compare(a,b):
 """Record order differences AND recurse through all common fields, never early return on order."""
 diffs=[];orders=[];stats=collections.Counter()
 def walk(x,y,path):
  stats['nodes']+=1
  if type(x) is not type(y):diffs.append({'path':path,'kind':'type','expected':type(x).__name__,'actual':type(y).__name__});return
  if isinstance(x,dict):
   stats['objects']+=1
   if set(x)!=set(y):diffs.append({'path':path,'kind':'field_set','missing':sorted(set(x)-set(y)),'extra':sorted(set(y)-set(x))})
   if list(x)!=list(y):orders.append({'path':path,'expected_keys':list(x),'actual_keys':list(y)})
   for k in x:
    if k in y:walk(x[k],y[k],path+[k])
  elif isinstance(x,list):
   stats['arrays']+=1
   if len(x)!=len(y):diffs.append({'path':path,'kind':'array_length','expected':len(x),'actual':len(y)})
   for i,(u,v) in enumerate(zip(x,y)):walk(u,v,path+[i])
  else:
   stats['scalar_leaves']+=1
   if x!=y:diffs.append({'path':path,'kind':'value','expected_sha256':sha(encode(x)),'actual_sha256':sha(encode(y))})
 walk(a,b,[]);return {'field_type_value_or_array_differences':diffs,'object_order_differences':orders,'visited':dict(stats)}
def strict(a,b):
 d=deep_compare(a,b);return not d['field_type_value_or_array_differences'] and not d['object_order_differences']
def semantic(a,b):return not deep_compare(a,b)['field_type_value_or_array_differences']
def main():
 registry=loads((S/'registry.json').read_bytes())
 def path(original):return Path(registry[norm(original)])
 def get(original):return loads(path(original).read_bytes())
 def at(rel):return BASE+'/'+rel
 def raw(rel):return path(at(rel)).read_bytes()
 def read(rel):return loads(raw(rel))
 # Parse every declared JSON input with duplicate/nonfinite rejection.
 parsed_json=0
 for k,v in registry.items():
  if k.endswith('.json'):loads(Path(v).read_bytes());parsed_json+=1
 cp=read('checkpoint-five-save-actual.json');summary=read('five-save-live/batch-summary.json')
 authority_before_raw=raw('five-save-outer/authority-before-launch.raw.json');authority=loads(authority_before_raw)
 spent=get('d:/1800/.local/stages/a25-lesson2-expansion-20261023/five-save-authority.json')
 launch=read('five-save-outer/single-launch.json');outer=read('five-save-outer/outer-outcome.json');owned=read('five-save-outer/batch-01.process.json')
 aid='ab2ca4a8-08bb-44ad-b8a9-4154d08d0a74'
 assert cp['authority_id']==authority['authority_id']==spent['authority_id']==launch['authority_id']==outer['authority_id']==aid
 assert sha(authority_before_raw)==cp['authority_original_sha256']==launch['authority_original_sha256']=='0cd5627209de7c9041117f988fa885778b2c30ddd7d75e830c2c585964995dcf'
 assert (authority['limits']['attempts_spent'],authority['limits']['attempts_remaining'])==(0,1)
 assert (spent['limits']['attempts_spent'],spent['limits']['attempts_remaining'])==(1,0) and spent['limits']['retry_allowed'] is False
 assert launch['argv']==owned['argv'] and timestamp(launch['at'])<timestamp(owned['started_at'])
 assert timestamp(authority['at'])<=timestamp(launch['at'])<=timestamp(authority['latest_start_utc'])
 assert (timestamp(owned['finished_at'])-timestamp(owned['started_at'])).total_seconds()<900
 assert sha(raw('launch-five-save-once.py'))==authority['outer_launcher_sha256']=='940283e0336f2f3936f8f5d6372b90ef8294034e21d07177754077e49c5a5d62'
 assert sha(raw('five-candidates-v2/targets.json'))==cp['targets_manifest_sha256']=='eb3b29c28c80650674f7df24e523dcc7c05e27b6713eda78dec92910b074d792'
 assert summary['status']=='STOPPED_NO_RETRY' and summary['error_code']=='READBACK_ACCEPTANCE_FAILED'
 assert [x['status'] for x in summary['results']]==['ACCEPTED','ACCEPTED','FAILED_STOP','NOT_RUN','NOT_RUN']
 targets=read('five-candidates-v2/targets.json')['targets'];rows=[];total_get=0;network_rows=[];pids=[];metadata=[]
 baseline=OB/'runs/usense-readonly-20261023-103259-3becb927'
 for index,entry in enumerate(targets,1):
  target=entry['target'];q=target['question_order'];qout='five-save-live/target-'+sha(target['node_id'].encode())[:24]
  plan=read(qout+'/plan.json');materialized=raw(qout+'/plan.json')
  assert materialized==(OB/f'five-plan-validation/printed-{index}-materialized-plan.json').read_bytes()
  assert raw(f'five-candidates-v2/printed-{index}-plan.json')==(OB/f'five-candidates-v2/printed-{index}-plan.json').read_bytes()
  assert semantic(plan['target'],target) and plan['plan_sha256']==read(f'five-candidates-v2/printed-{index}-plan.json')['plan_sha256']
  if index>3:
   assert not any(k.startswith(at(qout)+'/') and (k.endswith('/writer-process-result.json') or k.endswith('/reader-process-result.json')) for k in registry)
   assert not any(k.endswith('/'+plan['ledger_key']+'.json') or k.endswith('/'+plan['ledger_key']+'.accepted.json') for k in registry)
   rows.append({'printed_question':index,'native_order':q,'decision':'NOT_RUN','post_attempts':0,'reader_attempts':0,'materialized_plan_only':True});continue
  sr=summary['results'][index-1];writer=read(qout+'/writer-process-result.json');reader=read(qout+'/reader-process-result.json');w=writer['result'];r=reader['result'];wr='five-save-live/'+w['run_id'];rr='five-save-live/'+r['run_id']
  for label,process in [('writer',writer),('reader',reader)]:
   record=qout+'/'+label+'-process-result'
   assert sha(raw(record+'.stdout'))==process['stdout_sha256'] and sha(raw(record+'.stderr'))==process['stderr_sha256']
   assert semantic(loads(raw(record+'.stdout').decode('utf-8').strip().splitlines()[-1]),process['result'])
   assert process['exit_code']==0 and process['timed_out'] is False;pids.append(process['pid'])
  assert semantic(w,read(wr+'/execution-result.json')) and semantic(r,read(rr+'/capture-summary.json'))
  assert w['status']=='RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK' and w['save_success'] is False
  assert r['status']=='NATIVE_GETS_CAPTURED' and r['save_attempts']==0
  assert w['post_attempts']==1 and w['post_layers']=={'context':1,'native':1}
  assert writer['pid']!=reader['pid'] and w['run_id']!=r['run_id'] and timestamp(reader['started_at'])>timestamp(writer['finished_at'])
  assert timestamp(writer['started_at'])<timestamp(w['send_intent_at'])<timestamp(writer['finished_at'])
  receipt=read(wr+'/native-receipt.json');assert sha(raw(wr+'/native-receipt.json'))==w['receipt_sha256']
  expected_receipt={'code':0,'message':'success','data':{'inserted':False,'question_order':q,'inserted_question_node':None,'success':True,'append_at_global_end':False}}
  assert semantic(receipt,expected_receipt) and w['http_status']==200 and w['response_code']==0
  assert w['plan_file_sha256']==sha(materialized) and w['plan_sha256']==plan['plan_sha256']
  expected_names=['directory','frames','source',f'q{q}_annotations',f'q{q}_info']+[f'q{q}_{z}' for z in ZONES]+['page_12','page_173']
  assert set(r['captures'])==set(expected_names) and len(expected_names)==12
  after={}
  for name in expected_names:
   assert strict(read(wr+'/before-'+name+'.json'),loads((baseline/(name+'.json')).read_bytes()))
   b=raw(rr+'/'+name+'.json');record=r['captures'][name]
   assert sha(b)==record['sha256'] and len(b)==record['bytes'] and record['status']==200 and record['request_counts']=={'context':1,'native':1}
   assert timestamp(record['observed_at'])>timestamp(writer['finished_at']);after[name]=loads(b)
  snapshot={'directory':after['directory'],'frames':after['frames'],'annotations':after[f'q{q}_annotations'],'info':after[f'q{q}_info'],'zones':{z:after[f'q{q}_{z}'] for z in ZONES}}
  expected=copy.deepcopy(plan['expected']);oldtime=expected['info']['data']['updated_at'];newtime=snapshot['info']['data']['updated_at']
  assert type(oldtime) is type(newtime) is str and re.sub(r'\d','#',oldtime)==re.sub(r'\d','#',newtime)
  assert timestamp(newtime)>timestamp(oldtime) and timestamp(newtime).utcoffset()==timestamp(oldtime).utcoffset() and bool(timestamp(newtime).tzinfo)==bool(timestamp(oldtime).tzinfo)
  expected['info']['data']['updated_at']=newtime;meta={'path':['info','data','updated_at'],'before':oldtime,'after':newtime};metadata.append(meta)
  comparison=deep_compare(expected,snapshot)
  assert comparison['field_type_value_or_array_differences']==[]
  assert comparison['object_order_differences']==([] if index<3 else [
   {'path':['zones','question','data'],'expected_keys':['rect_ids','ocr_result','success'],'actual_keys':['success','ocr_result','rect_ids']},
   {'path':['zones','answer','data'],'expected_keys':['rect_ids','ocr_result','success'],'actual_keys':['success','ocr_result','rect_ids']}])
  for name in ['source','page_12','page_173']:assert strict(after[name],loads((baseline/(name+'.json')).read_bytes()))
  for role,run,value in [('writer',wr,w),('reader',rr,r)]:
   release=value['release'];assert release['context_closed'] is True and release['runtime_stopped'] is True and release['context_runtime_release_confirmed'] is True and release['errors']==[] and release['pending_callbacks']==0
   cfg=read(qout+('/writer-config.json' if role=='writer' else '/independent-reader-config.json'))
   assert sha(raw(qout+('/writer-config.json' if role=='writer' else '/independent-reader-config.json')))==value['config_sha256']
   assert cfg['run_id']==value['run_id'] and cfg['transport']=={'mode':'DIRECT','proxy_server':None}
   assert cfg['implementation_sha256']=='5ddfe19c4cb0f2b98555c927a1d205f1165ab23ecac981896627445e29f3c2c8'
   assert norm(cfg['authorization_reference'])==norm(spent['launch_intent'].rsplit('post-manual-login-source',1)[0]+'five-save-authority.json')
   assert cfg['authorization_reference']==cfg['tls']['approval_reference']
   probe=read(run+'/tls-probe.json');assert probe['attempts']==1 and probe['status']=='EXACT_LEAF_CONFIRMED' and probe['leaf_sha256']=='52d8642145282846969a29b97c5c3aaae4c0203c4a6bc06906478f13445e3941' and probe['transport']==cfg['transport']
   events=read(run+'/network-events.json');assert all(e['allowed'] is True for e in events)
   native=[e for e in events if e['layer']=='native'];counts=collections.Counter((e['method'],e['url_sha256']) for e in native)
   assert all(counts[('GET',sha(a['url'].encode()))]==1 for a in cfg['allowed_get'])
   assert len(cfg['allowed_get'])==13 and sum(e['method']=='GET' for e in native)==13
   assert sum(e['method']=='POST' for e in native)==(1 if role=='writer' else 0)
   assert len(native)==(14 if role=='writer' else 13)
   total_get+=12;network_rows.append({'printed_question':index,'role':role,'business_gets':12,'inert_navigation':1,'post_attempts':1 if role=='writer' else 0,'tls_probes':1,'context_runtime_released':True})
  ledger=[k for k in registry if '/browser-profiles/usense-existing-ledger/' in k and k.endswith('/'+plan['ledger_key']+'.json')];assert len(ledger)==1
  intent=get(ledger[0]);send=read(wr+'/send-intent.json')
  assert intent['plan_sha256']==plan['plan_sha256'] and intent['run_id']==w['run_id'] and intent['native_body_sha256']==w['native_body_sha256']==send['native_body_sha256']
  assert intent['state']=='INTENT_REQUIRES_INDEPENDENT_READBACK' and intent['automatic_retry_allowed'] is False
  accepted_ledger=[k for k in registry if '/browser-profiles/usense-existing-ledger/' in k and k.endswith('/'+plan['ledger_key']+'.accepted.json')]
  if index<3:
   assert len(accepted_ledger)==1;accepted=get(accepted_ledger[0]);assert accepted['acceptance_sha256']==sha(raw(qout+'/acceptance.json'))
   assert accepted['writer_run']==w['run_id'] and accepted['reader_run']==r['run_id'] and accepted['plan_sha256']==plan['plan_sha256']
  else:assert accepted_ledger==[]
  row={'printed_question':index,'native_order':q,'node_id':target['node_id'],'info_id':target['info_id'],'post_attempts':1,'http_status':200,'response_code':0,'receipt':item(path(at(wr+'/native-receipt.json'))),'writer_pid':writer['pid'],'reader_pid':reader['pid'],'writer_run':w['run_id'],'reader_run':r['run_id'],'different_process_context_and_fresh_post_exit_reads_verified':True,'metadata_change':meta,'complete_recursive_comparison':comparison,'unknown_fields_included':True,'arrays_compared_positionally_with_exact_element_types':True,'decision':'ACCEPTED_REAL_SAVE_AND_INDEPENDENT_FULL_READBACK' if index<3 else 'ACCEPTED_FIXED_RECEIPT_AND_FRESH_READBACK_FACTS_ONLY_STRICT_FAIL_RETAINED','original_batch_status':sr['status'],'original_strict_match':index<3,'ledger_acceptance_present':index<3}
  if index==3:
   zone_details=[]
   for z in ['question','answer']:
    x=expected['zones'][z]['data'];y=snapshot['zones'][z]['data'];assert plan['before']['zones'][z]['data']['success'] is False
    zone_details.append({'zone':z,'before_state':'ABSENT','expected_key_order':list(x),'actual_key_order':list(y),'exact_field_set_and_types':True,'success_type':'bool','success_value':y['success'],'text_type':'str','text_utf8_sha256':sha(y['ocr_result'].encode()),'text_exact_match':x['ocr_result']==y['ocr_result'],'rect_ids':y['rect_ids'],'rect_array_exact_order_types_values':strict(x['rect_ids'],y['rect_ids']),'unknown_or_extra_fields':[]})
   row['absent_to_present_data_facts']=zone_details;row['strict_failure_not_reclassified_as_pass']=True;row['resend_or_ledger_repair_authorized']=False
  rows.append(row)
 assert total_get==72
 assert owned['job_assigned_before_resume'] is True and owned['resumed'] is True and owned['exit_code']==2 and owned['errors']==[]
 assert owned['job_active_processes_after']==0 and owned['owned_os_release_confirmed'] is True
 assert all(owned[k] is True for k in ['launcher_exit_signaled','thread_handle_closed','process_handle_closed','job_handle_closed'])
 ids=owned['observed_processes'];assert len(ids)==99 and len({(x['pid'],x['creation_filetime']) for x in ids})==99
 assert all(x['exit_signaled'] is True and x['handle_closed'] is True for x in ids) and set(pids)<={x['pid'] for x in ids}
 assert sha(raw('five-save-outer/batch-01.stdout'))==owned['stdout']['sha256'] and sha(raw('five-save-outer/batch-01.stderr'))==owned['stderr']['sha256']
 assert outer['outer_exit_code']==2 and outer['job_active_processes_after']==0 and outer['held_identities']==99 and outer['whole_batch_os_release_confirmed'] is True
 result={'schema':'A25IndependentFiveSaveActualResult/v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'ACCEPTED_FIXED_PARTIAL_TWO_SAVES_THIRD_STRICT_FAILURE_AND_WHOLE_BATCH_RELEASE_ONLY','reviewer_thread_id':'01a166e8-3f23-7192-a560-4724adca74b1','product_commit':'8990e1e3c7561bc7403eb29359f0d39ba3a54295','authority_id':aid,'manifest_sha256':'a72cc4a6d4f63c6eb2d3e5393ad031d38a9fb12d2d97cbf81771871dcd131eae','checkpoint_sha256':'1af6ad4a4e15081586c4057f51c286d34bc621d5db53937fdfe5189b7dce4504','raw_actual_members_verified':202,'parsed_json_members_no_duplicate_or_nonfinite':parsed_json,'prior_fixed_reused_members_verified':120,'attempts_spent':1,'attempts_remaining':0,'retry_allowed':False,'original_strict_third_failure_preserved':True,'new_semantic_policy_or_ledger_acceptance_created':False,'counts':{'commit_posts':3,'exact_success_receipts':3,'writer_business_gets':36,'reader_business_gets':36,'total_business_gets':72,'readers':3,'strict_complete_save_readback_accepts':2,'third_field_value_equal_but_original_key_order_fail':1,'not_run':2,'contexts':6,'inert_navigations':6,'tls_probes':6,'ledger_intents':3,'ledger_accepted_files':2},'targets':rows,'network_and_context_release':network_rows,'release':{'whole_batch_job_active_after':0,'held_identity_count':99,'all_99_unique_creation_identities_exit_signaled_handles_closed':True,'launcher_job_process_thread_handles_closed':True,'all_six_writer_reader_pids_in_held_identity_set':True,'context_runtime_releases':6,'individual_writer_descendant_os_release_before_reader':'NOT_SEPARATELY_PROVEN; final whole-batch Job0 only'},'limitations':['Third original strict FAIL remains unresolved under old contract; exact typed value equality is an additional frozen-evidence fact, not a new acceptance policy','No third resend, marker/ledger amendment, old authority restoration or new live authorized by this review','Actual total72 business GET comprises36 writer plus36 reader GET; audit layers are not summed','No new GET, platform action, product test or active correction read; original accepted product matrices reused unchanged'],'review_complete_and_released':True,'automation_1800_a':'PAUSED_UNCHANGED'}
 put(P/'result.json',encode(result))
 put(P/'third-deep-facts.json',encode({'schema':'A25ThirdQuestionDeepFrozenFacts/v1','source_result_sha256':sha((P/'result.json').read_bytes()),'target':rows[2],'recursive_algorithm':'On object key-order difference, continue through every common field and nested array/scalar; reject field-set/type/value/array differences separately. Only metadata updated_at follows existing monotonic rule. No product comparator imported or changed.','original_strict_failure_retained':True}))
 report='''# A25 固定实际有限验收

结论：接受首两题真实保存及不同进程/新context完整回读；接受第三题成功回执、已捕获新鲜回读的固定事实及原严格失败；接受六context/runtime及最终整批OS释放。整批保持STOPPED_NO_RETRY，第4、5题NOT_RUN，authority已消耗1/剩余0。

核202份根冻结原件，并复用已接受的8990产品/五计划120份隔离原件。未运行产品、访问平台、读取活动修正或触碰真实ledger。三次POST分别有200/code0完整成功原回执，三个reader均在各自writer退出后启动，PID/run_id不同，全部12响应的观察时间晚于writer结束、原始bytes/hash闭合。共72业务GET是writer36+reader36；双审计层不相加。

首两题完整目录、全部76框、题框、全部info/五区、source/两页均按原规则通过，只有目标info.updated_at允许推进。第三题除该既有更新时间规则外，递归遍历完整原生快照，遇键序差异仍继续核每一个字段；字段集、精确类型、每值、全部文字、数组长度/顺序/元素类型以及未知字段均一致。仅两处对象键序不同：zones.question.data和zones.answer.data，预期rect_ids,ocr_result,success，返回success,ocr_result,rect_ids。两区此前确实缺失；现success为bool true，题干文字逐字相同，答案字符串4，rect_ids数组和顺序逐项相同，无额外未知字段。详见third-deep-facts.json及result.json的遍历计数和逐区摘要。

这项原值事实不改写旧strict FAIL，不生成新规则或第三题accepted标记。冻结ledger是3个intent/2个accepted；后两题只有准备文件，没有writer/reader/intent。原批错误READBACK_ACCEPTANCE_FAILED、outer exit2和未执行后继全部保留。第三题不得重发，本报告不授权补改ledger或恢复额度。

最终整批Job active0，99个唯一PID+creation_filetime身份均退出并关闭持有handle，launcher/process/thread/Job handle关闭；六writer/reader PID均在持有身份集中，六context/runtime释放。只证明最终整批OS释放，不能提升为逐writer在下一reader之前所有子进程的OS释放。

实际发生于2026-10-23 19:17–19:18（Asia/Shanghai）；机器报告保留原UTC时间。独立验收完成并释放，sole1800-a保持PAUSED，未改产品、ledger、根JSON或Git。
'''
 put(P/'report.md',report.encode('utf-8'))
 print(json.dumps({'status':result['status'],'strict_accepted':2,'third_only_key_order_differences':len(rows[2]['complete_recursive_comparison']['object_order_differences']),'third_other_differences':len(rows[2]['complete_recursive_comparison']['field_type_value_or_array_differences']),'third_visited':rows[2]['complete_recursive_comparison']['visited'],'raw':202,'total_business_GET':72,'held_identities':99}))
if __name__=='__main__':main()
