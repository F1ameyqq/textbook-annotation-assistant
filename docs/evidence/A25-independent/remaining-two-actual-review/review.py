# -*- coding: utf-8 -*-
"""Fixed actual evidence only: no product import, tests, profile or network."""
import collections,datetime,hashlib,json
from pathlib import Path,PureWindowsPath
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/remaining-two-actual-review-20261023')
OLD=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-readiness-review-20261023')
PREP=Path('D:/1800/.local/stages/a25-independent-20261023/created-zone-reconciliation-review-20261023')
BASE='d:/1800/.local/stages/a25-lesson2-expansion-20261023/post-manual-login-source/'
def sha(b):return hashlib.sha256(b).hexdigest()
def norm(p):return PureWindowsPath(str(p)).as_posix().lower()
def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError('DUPLICATE_JSON_KEY')
  d[k]=v
 return d
def loads(b):return json.loads(b,object_pairs_hook=unique,parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
def enc(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def strict(a,b):
 if type(a) is not type(b):return False
 if isinstance(a,dict):return list(a)==list(b) and all(strict(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(strict(x,y) for x,y in zip(a,b))
 return a==b
def ts(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def put(p,b):
 with p.open('xb') as f:f.write(b)
def entry(p,kind):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b),'kind':kind}
def main():
 reg=loads((S/'registry.json').read_bytes());used={}
 def path(p):return Path(reg[norm(p)])
 def raw(rel):return path(BASE+rel).read_bytes()
 def read(rel):return loads(raw(rel))
 def reuse(p,digest=None):
  b=p.read_bytes()
  if digest:assert sha(b)==digest
  used[str(p)]=entry(p,'prior_accepted_fixed_dependency');return b
 for k,v in reg.items():
  if k.endswith('.json'):loads(Path(v).read_bytes())
 prior_result=Path('D:/1800/docs/evidence/A25-independent/created-zone-reconciliation-review/result.json')
 reuse(prior_result,'8a5af6d2e194794993c69a12968c5331c396c82682404db686df658bf79d9069')
 cp=read('checkpoint-remaining-two-actual.json');prep=read('checkpoint-created-zone-reconciliation.json');summary=read('remaining-two-live/batch-summary.json')
 assert summary['status']=='STOPPED_NO_RETRY' and summary['error_code']=='CHILD_FAILED_STOP_NO_RETRY'
 assert [x['status'] for x in summary['results']]==['STOPPED_NO_RETRY','NOT_RUN']
 targets=read('created-zone-reconciliation/remaining-two/targets.json');assert sha(raw('created-zone-reconciliation/remaining-two/targets.json'))=='769ea9b78906f689776613942799581966a9a0e690e62cc1af8e43117988f6c7'
 assert [x['printed_question'] for x in targets['targets']]==[4,5]
 qout='remaining-two-live/target-112796c22ae27340da45824a';wp=read(qout+'/writer-process-result.json');w=wp['result'];run='remaining-two-live/'+w['run_id'];cfg=read(qout+'/writer-config.json');plan=read(qout+'/plan.json')
 assert wp['pid']==63808 and wp['exit_code']==2 and wp['timed_out'] is False
 assert sha(raw(qout+'/writer-process-result.stdout'))==wp['stdout_sha256'] and sha(raw(qout+'/writer-process-result.stderr'))==wp['stderr_sha256']
 assert loads(raw(qout+'/writer-process-result.stdout').decode('utf-8').strip().splitlines()[-1])==w and read(run+'/execution-result.json')==w
 assert w['status']=='RELEASE_UNPROVEN_NO_RETRY' and w['save_success'] is False and w['independent_readback']=='PENDING'
 expected_release={'context_closed':False,'context_runtime_release_confirmed':False,'errors':[{'phase':'context_close','type':'TimeoutError'},{'phase':'runtime_stop','type':'TimeoutError'}],'pending_callbacks':0,'runtime_stopped':False}
 assert w['release']==expected_release
 assert w['target']==targets['targets'][0]['target'] and w['target']['question_order']==21 and w['target']['node_id']=='1792067074506' and w['target']['info_id']=='2110708409593016321'
 assert w['target']==plan['target'] and w['plan_sha256']==plan['plan_sha256']=='49ae1f7121f04ef3851528fd1f32c0dce5f1b8526aa8826285783f20a4dc62e1'
 assert sha(raw(qout+'/plan.json'))==w['plan_file_sha256']=='52f5a01be1d69e1c7ce398b4fe55998e4230bd80263aaf684f329315d82fd879'
 for i in [4,5]:
  old=OLD/f'project/post-manual-login-source/five-plan-validation/printed-{i}-materialized-plan.json'
  assert raw(f'created-zone-reconciliation/remaining-two/printed-{i}-plan.json')==reuse(old)
 assert [x['zone'] for x in plan['changes']]==['question'] and plan['payload_candidate']['is_new_question_insertion'] is False
 receipt_raw=raw(run+'/native-receipt.json');receipt=loads(receipt_raw)
 assert sha(receipt_raw)==w['receipt_sha256']==cp['printed4_native21']['receipt_sha256']=='6fec83f3eda636ca66b188cb3c91c0b78b92a45f7e8846af1068d42eae590d42'
 assert receipt=={'code':0,'message':'success','data':{'inserted':False,'question_order':21,'inserted_question_node':None,'success':True,'append_at_global_end':False}}
 assert w['http_status']==200 and w['response_code']==0 and w['post_attempts']==1 and w['post_layers']=={'context':1,'native':1}
 assert sha(raw(qout+'/writer-config.json'))==w['config_sha256'] and cfg['run_id']==w['run_id'] and cfg['implementation_sha256']=='1c222acdb9d442546cbcff99cde98031fa5ecb7646cc135bb1f30dc9a09cad17'
 assert cfg['transport']=={'mode':'DIRECT','proxy_server':None} and cfg['tls']['approval_reference']==cfg['authorization_reference']==w['authorization_reference']
 probe=read(run+'/tls-probe.json');assert probe['attempts']==1 and probe['leaf_sha256']=='52d8642145282846969a29b97c5c3aaae4c0203c4a6bc06906478f13445e3941' and probe['status']=='EXACT_LEAF_CONFIRMED'
 names=['directory','frames','source','q21_annotations','q21_info','q21_question','q21_choice','q21_answer','q21_analysis','q21_knowledge_point','page_12','page_173'];before_hashes={}
 for name in names:
  b=raw(run+'/before-'+name+'.json');prior=reuse(OLD/'project/post-manual-login-source/runs/usense-readonly-20261023-103259-3becb927'/(name+'.json'))
  assert strict(loads(b),loads(prior));before_hashes[name]=sha(b)
 events=read(run+'/network-events.json');assert all(e['allowed'] is True for e in events)
 native=[e for e in events if e['layer']=='native'];counts=collections.Counter((e['method'],e['url_sha256']) for e in native)
 assert len(cfg['allowed_get'])==13 and all(counts[('GET',sha(x['url'].encode()))]==1 for x in cfg['allowed_get'])
 posthash=sha(b'https://www.usense.com/qieti/api/annotate_pic/commit_unified_submit')
 assert len(native)==14 and counts[('POST',posthash)]==1
 assert sum(e['method']=='POST' and e['layer']=='context' and e['url_sha256']==posthash for e in events)==1
 ledger={k:v for k,v in reg.items() if '/browser-profiles/usense-existing-ledger/' in k};assert len(ledger)==6
 for original,digest in prep['ledger_original_file_sha256'].items():assert sha(Path(ledger[norm(original)]).read_bytes())==digest
 key=plan['ledger_key'];intent=loads(Path(ledger[next(k for k in ledger if k.endswith('/'+key+'.json'))]).read_bytes());send=read(run+'/send-intent.json')
 assert intent['run_id']==w['run_id']==send['run_id'] and intent['target']==w['target'] and intent['plan_sha256']==w['plan_sha256']==send['plan_sha256']
 assert intent['native_body_sha256']==w['native_body_sha256']==send['native_body_sha256'] and intent['intent_at']==w['send_intent_at']==send['send_intent_at']
 assert intent['state']=='INTENT_REQUIRES_INDEPENDENT_READBACK' and intent['automatic_retry_allowed'] is False
 assert not any(k.endswith('/'+key+'.accepted.json') for k in ledger)
 assert not any('/reader-process-result.' in k or '/independent-reader-config.json' in k for k in reg if '/remaining-two-live/' in k)
 fifth=read('created-zone-reconciliation/remaining-two/printed-5-plan.json');assert not any(fifth['ledger_key'] in k for k in ledger)
 fifth_prefix=BASE+'remaining-two-live/target-'+sha(fifth['target']['node_id'].encode())[:24]+'/'
 assert all(k.endswith('/plan.json') or k.endswith('/review-evidence-hashes.json') for k in reg if k.startswith(fifth_prefix))
 before_auth_raw=raw('remaining-two-outer/authority-before-launch.raw.json');authority=loads(before_auth_raw);spent=loads(Path(next(v for k,v in reg.items() if k.endswith('/remaining-two-authority.json'))).read_bytes())
 launch=read('remaining-two-outer/single-launch.json');owned=read('remaining-two-outer/batch-01.process.json');outcome=read('remaining-two-outer/outer-outcome.json')
 assert authority['authority_id']==spent['authority_id']==launch['authority_id']==owned.get('authority_id',authority['authority_id'])==cp['authority_id']=='8696ca2c-c95d-4a85-9029-7097b8b09b8c'
 assert sha(before_auth_raw)==cp['authority_original_sha256']==launch['authority_original_sha256']=='1b0be4367b314ac3c3601f0ab93f305eebf5b5b199ebd5b59b5817fd93fe99f1'
 assert authority['ledger_snapshot']==prep['ledger_original_file_sha256'] and authority['optional_existing_third_accepted_marker_sha256'] is None
 assert (authority['limits']['attempts_spent'],authority['limits']['attempts_remaining'])==(0,1) and (spent['limits']['attempts_spent'],spent['limits']['attempts_remaining'])==(1,0)
 assert sha(raw('launch-remaining-two-once.py'))==authority['outer_launcher_sha256']=='804bd183a4cf6bbb48bcc704e7355295164516c6d33eea7f7355891aced6736e'
 assert owned['argv']==launch['argv'] and cfg['authorization_reference']==str(Path(w['authorization_reference']))
 assert ts(authority['at'])<=ts(launch['at'])<=ts(authority['latest_start_utc'])
 chain=[launch['at'],owned['started_at'],summary['started_at'],wp['started_at'],w['send_intent_at'],w['finished_at'],wp['finished_at'],summary['finished_at'],owned['process_finished_at'],owned['finished_at'],outcome['finished_at']]
 assert all(ts(a)<=ts(b) for a,b in zip(chain,chain[1:])) and (ts(owned['finished_at'])-ts(owned['started_at'])).total_seconds()<900
 assert owned['exit_code']==outcome['outer_exit_code']==2 and owned['job_assigned_before_resume'] is True and owned['resumed'] is True and owned['errors']==[]
 assert owned['job_active_processes_after']==outcome['job_active_processes_after']==0 and owned['owned_os_release_confirmed'] is True and outcome['whole_batch_os_release_confirmed'] is True
 ids=owned['observed_processes'];assert len(ids)==23 and len({(x['pid'],x['creation_filetime']) for x in ids})==23
 assert all(x['exit_signaled'] is True and x['handle_closed'] is True for x in ids) and wp['pid'] in {x['pid'] for x in ids}
 assert all(owned[x] is True for x in ['launcher_exit_signaled','process_handle_closed','thread_handle_closed','job_handle_closed'])
 assert sha(raw('remaining-two-outer/batch-01.stdout'))==owned['stdout']['sha256'] and sha(raw('remaining-two-outer/batch-01.stderr'))==owned['stderr']['sha256']
 result={'schema':'A25IndependentRemainingTwoActualResult/v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'ACCEPTED_FIXED_FOURTH_EXACT_RECEIPT_RELEASE_FAILURE_NO_READBACK_AND_WHOLE_BATCH_OS_RELEASE_ONLY','reviewer_thread_id':'01a166e8-3f23-7192-a560-4724adca74b1','product_commit':'389d2e7a282d21efa25db8d01c02d115ce9e83b7','manifest_sha256':'1daeb71c2c88b9ff4d36b525b558572dd2de5a8244044cf7657649ccb5ac6c56','checkpoint_sha256':'ad819727e059a83662f7e5d934f6f26db73614fd33268813ca9d159c71de78d0','raw_members_verified':55,'authority_id':cp['authority_id'],'attempts_spent':1,'attempts_remaining':0,'retry_allowed':False,'fourth':{'printed_question':4,'native_order':21,'node_id':w['target']['node_id'],'info_id':w['target']['info_id'],'one_post_200_code0_exact_success_receipt':True,'receipt_sha256':sha(receipt_raw),'plan_sha256':w['plan_sha256'],'native_body_sha256_intent_and_execution_bound':w['native_body_sha256'],'raw_post_body_reconstructed':'NOT_AVAILABLE_NOT_ASSERTED; authenticated created_by intentionally unexported. Binding uses accepted unchanged writer guard and matching plan/config/send/ledger/receipt records.','business_gets':12,'inert_navigations':1,'tls_probes':1,'native_and_context_post_guard_counts_each':1,'writer_status':w['status'],'writer_exit_code':2,'writer_process_communicate_timeout':False,'original_framework_release':w['release'],'independent_reader':'NOT_RUN','complete_saved_state_and_independent_readback':'UNPROVEN_PENDING_READBACK','accepted_marker_present':False,'resend_authorized':False},'fifth':{'printed_question':5,'native_order':22,'status':'NOT_RUN','post_attempts':0,'readers':0,'ledger_identity_files':0},'ledger':{'original_five_file_hashes_unchanged':True,'original_five_snapshot':prep['ledger_original_file_sha256'],'one_new_fourth_unaccepted_intent':True,'frozen_file_count':6,'accepted_markers_created_this_batch':0,'third_original_intent_preserved':True},'release':{'whole_batch_job_active_after':0,'held_unique_creation_identities':23,'all_held_exit_signaled_and_handles_closed':True,'writer_pid_in_held_identity_set':True,'launcher_thread_process_job_handles_closed':True,'does_not_override_writer_context_runtime_false':True,'per_writer_descendant_release_before_reader':'NOT_APPLICABLE_READER_NOT_RUN; final whole-batch OS release only'},'original_errors_preserved':{'batch':'CHILD_FAILED_STOP_NO_RETRY','writer_framework':['context_close TimeoutError','runtime_stop TimeoutError'],'writer_stderr_sha256':wp['stderr_sha256'],'stderr_observed':['RuntimeError Event loop is closed in destructor','ValueError I/O operation on closed pipe in destructor'],'timeout_causal_chain':'UNKNOWN; destructor errors are retained, not assigned as cause'},'time_chain_utc':chain,'before_raw_hashes':before_hashes,'new_tests_product_runs_platform_GETs_or_real_profile_ledger_reads':0,'prior_two_successes_and_third_finite_reconciliation':'PRESERVED_NO_REPLAY','review_complete_and_released':True,'automation_1800_a':'PAUSED_UNCHANGED'}
 put(P/'result.json',enc(result))
 report='''# A25 最后两题固定实际有限验收

仅接受第4题一次提交的200/code0精确成功回执、原释放失败/未回读事实及最终整批OS释放。第4题完整保存状态和独立读回仍未证，第5题NOT_RUN。authority8696ca2c已消耗1/剩余0，不重发第4题、不建accepted marker，不伪造revision前驱。

55份原件独立隔离核hash。第4题native21/node1792067074506/info2110708409593016321的计划、config、send intent、新稳定ledger intent和execution摘要相互绑定，原回执question_order21、success=true、inserted=false，摘要6fec83f3。12份before原生响应与已验baseline严格相同；审计显示12业务GET+1惰性导航+1TLS探测，以及唯一commit POST，native/context两层各1不相加。实际POST原body未导出，含未导出的authenticated created_by，未声称重建原body；绑定由已接受未变writer守卫及完整固定记录支持。

writer原status为RELEASE_UNPROVEN_NO_RETRY、退出码2、communicate未超时；context_closed=false、runtime_stopped=false，两者分别TimeoutError。原stderr中的Event loop is closed及closed pipe析构异常保留，释放超时的完整因果仍UNKNOWN，不展开诊断。原reader配置/进程不存在于完整固定输出，流程在writer失败处停止；第5题只有计划/审查hash准备文件，无writer/reader/intent。

原五ledger文件逐hash保持；唯一新增第4题INTENT_REQUIRES_INDEPENDENT_READBACK，合计6文件，没有第3或第4accepted marker。唯一authority原字节、原子消费intent、监管进程、writer发送/结束、batch停止和最终释放的时间链相容；旧额度未恢复。

最终整批Job active0，23个唯一PID+creation_filetime持有身份均exit_signaled且handle关闭，含writer PID；launcher/process/thread/Job handle均关闭。只接受最终整批OS释放，不能覆盖原writer context/runtime false。首两题已证保存回读及第三有限对账保持，未重跑任何产品、平台或测试。后续只读补读计划需另行固定静态预检；本actual结果不等待或授权补读。独立完成并释放，sole1800-a保持PAUSED。
'''
 put(P/'report.md',report.encode('utf-8'))
 rows={}
 for p in sorted(S.rglob('*')):
  if p.is_file():rows[str(p)]=entry(p,'current_frozen_input_or_mapping')
 rows.update(used)
 for p in sorted(P.iterdir()):
  if p.is_file() and p.name not in ('raw-manifest.json','review-files.sha256'):rows[str(p)]=entry(p,'independent_public_report_or_helper')
 values=list(rows.values());put(P/'raw-manifest.json',enc({'schema':'A25IndependentRemainingTwoActualRawManifest/v1','self_and_checksum_excluded':True,'actual_inputs':55,'total_files':len(values),'members':values}))
 public=[p for p in sorted(P.iterdir()) if p.is_file() and p.name!='review-files.sha256'];put(P/'review-files.sha256',''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in public).encode())
 for x in values:assert sha(Path(x['path']).read_bytes())==x['sha256'] and len(Path(x['path']).read_bytes())==x['bytes']
 print(json.dumps({'status':result['status'],'raw_files':len(values),'public_files_plus_self':len(public)+1,'result':entry(P/'result.json','result'),'report':entry(P/'report.md','report'),'raw_manifest':entry(P/'raw-manifest.json','manifest'),'checksum':entry(P/'review-files.sha256','checksum')}))
if __name__=='__main__':main()
