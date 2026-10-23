# -*- coding: utf-8 -*-
"""Independently verify fixed actual data; do not import product code or run tests."""
import collections,copy,datetime,hashlib,json,re
from pathlib import Path,PureWindowsPath
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/final-recovery-actual-review-20261023')
OLD=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-readiness-review-20261023')
A1=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-actual-review-20261023')
A4=Path('D:/1800/.local/stages/a25-independent-20261023/remaining-two-actual-review-20261023')
BASE='d:/1800/.local/stages/a25-lesson2-expansion-20261023/post-manual-login-source/'
Z=['question','choice','answer','analysis','knowledge_point']
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
def digest(x):return sha(json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8'))
def strict(a,b):
 if type(a)!=type(b):return False
 if isinstance(a,dict):return list(a)==list(b) and all(strict(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(strict(x,y) for x,y in zip(a,b))
 return a==b
def ts(v):return datetime.datetime.fromisoformat(v.replace('Z','+00:00'))
def put(p,b):
 with p.open('xb') as f:f.write(b)
def item(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def main():
 reg=loads((S/'registry.json').read_bytes());old1=loads((A1/'registry.json').read_bytes());old4=loads((A4/'registry.json').read_bytes());used={}
 def path(rel):return Path(reg[norm(BASE+rel)])
 def read(rel):return loads(path(rel).read_bytes())
 def raw(rel):return path(rel).read_bytes()
 def reuse(p,expected=None):
  b=p.read_bytes()
  if expected:assert sha(b)==expected
  used[str(p)]=item(p);return b
 def prior(report,expected):return loads(reuse(Path('D:/1800/docs/evidence/A25-independent')/report/'result.json',expected))
 first=prior('five-save-actual-review','d4e226f886cf23063f73258f7178778746cf48a22fa8e13af92a6c89e4a8e65b')
 recon=prior('created-zone-reconciliation-review','8a5af6d2e194794993c69a12968c5331c396c82682404db686df658bf79d9069')
 fourth=prior('remaining-two-actual-review','d74a0705832d8fda580fa9c90707e813517689316c38f5379864aec72e516db5')
 prepared=prior('final-recovery-preparation-review','389900bb1bf79070c05e5d77d2141a287210881ab4558d9c51ab6866e7df25db')
 cp=read('checkpoint-final-recovery-actual.json');plan=read('final-recovery-preparation/recovery-plan.json');summary=read('final-recovery-live/recovery-summary.json');q4=read('final-recovery-live/q4-later-readback.json')
 assert summary['status']=='Q4_LATER_READBACK_AND_Q5_SAVE_READBACK_COMPLETE_PENDING_FORMAL_ACTUAL_REVIEW' and summary['q4_resends']==0
 assert sha(raw('run-final-recovery.py'))==prepared['runner_sha256'] and sha(raw('launch-final-recovery-once.py'))==prepared['outer_sha256'] and sha(raw('final-recovery-preparation/recovery-plan.json'))==prepared['recovery_plan_sha256']
 for k,v in reg.items():
  if k.endswith('.json'):loads(Path(v).read_bytes())
 oldwp=loads(reuse(Path(old4[norm(plan['original_q4_writer_process']['path'])]),plan['original_q4_writer_process']['sha256']));oldw=oldwp['result'];oldholder=loads(reuse(Path(old4[norm(plan['original_whole_batch_holder']['path'])]),plan['original_whole_batch_holder']['sha256']))
 oldplan=loads(reuse(Path(old4[norm(plan['original_q4_plan']['path'])]),plan['original_q4_plan']['sha256']));oldreceipt=loads(reuse(Path(old4[norm(plan['original_q4_native_receipt']['path'])]),plan['original_q4_native_receipt']['sha256']))
 lastdir='final-recovery-live/last-question-batch/target-5dd1634226fd0f0185903349';wp=read(lastdir+'/writer-process-result.json');w=wp['result'];rp4=read('final-recovery-live/q4-reader-process-result.json');rp5=read(lastdir+'/reader-process-result.json');r4=rp4['result'];r5=rp5['result']
 wr='final-recovery-live/last-question-batch/'+w['run_id'];rr4='final-recovery-live/'+r4['run_id'];rr5='final-recovery-live/last-question-batch/'+r5['run_id'];p5=read(lastdir+'/plan.json')
 for record,process in [('final-recovery-live/q4-reader-process-result',rp4),(lastdir+'/writer-process-result',wp),(lastdir+'/reader-process-result',rp5)]:
  assert process['exit_code']==0 and process['timed_out'] is False and sha(raw(record+'.stdout'))==process['stdout_sha256'] and sha(raw(record+'.stderr'))==process['stderr_sha256']
  assert loads(raw(record+'.stdout').decode('utf-8').strip().splitlines()[-1])==process['result']
 assert w==read(wr+'/execution-result.json') and r4==read(rr4+'/capture-summary.json') and r5==read(rr5+'/capture-summary.json')
 assert w['status']=='RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK' and w['post_attempts']==1 and w['post_layers']=={'context':1,'native':1}
 receipt5=read(wr+'/native-receipt.json');assert sha(raw(wr+'/native-receipt.json'))==w['receipt_sha256']
 def receipt_expected(q):return {'code':0,'message':'success','data':{'inserted':False,'question_order':q,'inserted_question_node':None,'success':True,'append_at_global_end':False}}
 assert strict(oldreceipt,receipt_expected(21)) and strict(receipt5,receipt_expected(22)) and oldw['http_status']==w['http_status']==200
 assert oldw['post_attempts']==1 and oldw['release']==fourth['fourth']['original_framework_release'] and oldw['release']['context_runtime_release_confirmed'] is False
 assert raw(lastdir+'/plan.json')==reuse(OLD/'project/post-manual-login-source/five-plan-validation/printed-5-materialized-plan.json') and w['plan_sha256']==p5['plan_sha256']
 assert ts(rp4['started_at'])>ts(oldholder['finished_at']) and ts(wp['started_at'])>ts(rp4['finished_at']) and ts(rp5['started_at'])>ts(wp['finished_at'])
 assert oldwp['pid']!=rp4['pid'] and wp['pid']!=rp5['pid'] and oldw['run_id']!=r4['run_id'] and w['run_id']!=r5['run_id']
 for name in ['directory','frames','source','q22_annotations','q22_info',*[f'q22_{z}' for z in Z],'page_12','page_173']:
  assert strict(read(wr+'/before-'+name+'.json'),loads(reuse(OLD/'project/post-manual-login-source/runs/usense-readonly-20261023-103259-3becb927'/(name+'.json'))))
 reader_results=[];reader_maps={}
 for i,p,rp,r,rr,oldproc,threshold,recorded in [(4,oldplan,rp4,r4,rr4,oldwp,oldholder['finished_at'],q4['comparison']),(5,p5,rp5,r5,rr5,wp,wp['finished_at'],read(lastdir+'/acceptance.json')['comparison'])]:
  q=p['target']['question_order'];names=['directory','frames','source',f'q{q}_annotations',f'q{q}_info',*[f'q{q}_{z}' for z in Z],'page_12','page_173'];assert set(r['captures'])==set(names) and r['status']=='NATIVE_GETS_CAPTURED' and r['save_attempts']==0;after={}
  for name in names:
   b=raw(rr+'/'+name+'.json');cap=r['captures'][name];assert sha(b)==cap['sha256'] and len(b)==cap['bytes'] and cap['status']==200 and cap['request_counts']=={'context':1,'native':1}
   assert ts(cap['observed_at'])>ts(threshold) and ts(rp['started_at'])<ts(cap['observed_at'])<ts(r['finished_at'])<=ts(rp['finished_at']);after[name]=loads(b)
  snapshot={'directory':after['directory'],'frames':after['frames'],'annotations':after[f'q{q}_annotations'],'info':after[f'q{q}_info'],'zones':{z:after[f'q{q}_{z}'] for z in Z}}
  expect=copy.deepcopy(p['expected']);a=expect['info']['data']['updated_at'];b=snapshot['info']['data']['updated_at'];assert type(a) is type(b) is str and re.sub(r'\d','#',a)==re.sub(r'\d','#',b) and ts(b)>ts(a) and ts(a).utcoffset()==ts(b).utcoffset() and bool(ts(a).tzinfo)==bool(ts(b).tzinfo);expect['info']['data']['updated_at']=b
  assert strict(expect,snapshot) and digest(snapshot)==recorded['after_sha256'] and recorded['match'] is True and recorded['differences']==[]
  for name in ['source','page_12','page_173']:assert strict(after[name],loads(reuse(OLD/'project/post-manual-login-source/runs/usense-readonly-20261023-103259-3becb927'/(name+'.json'))))
  assert r['release']==read(rr+'/release.json')
  reader_results.append({'printed_question':i,'native_order':q,'target':p['target'],'writer_run':oldproc['result']['run_id'],'writer_pid':oldproc['pid'],'reader_run':r['run_id'],'reader_pid':rp['pid'],'post_attempts':1,'independent_raw_reads':12,'full_strict_snapshot_match':True,'after_sha256':digest(snapshot),'metadata_updated_at':{'before':a,'after':b},'reader_finished_at':rp['finished_at'],'source_and_pages_match':True,'raw_response_hashes':{n:r['captures'][n]['sha256'] for n in names}});reader_maps[str(i)]={'run_prefix':BASE+rr,'plan_target':p['target']}
 assert q4['status']=='MATCHED' and all(v is True for v in q4['checks'].values()) and q4['new_accepted_marker_created'] is False and q4['revision_predecessor_claim'] is False
 accept=read(lastdir+'/acceptance.json');assert accept['status']=='ACCEPTED' and all(x is True for x in accept['checks'].values())
 network=[]
 for label,run,value,cfgpath in [('q4reader',rr4,r4,'final-recovery-live/q4-independent-reader-config.json'),('q5writer',wr,w,lastdir+'/writer-config.json'),('q5reader',rr5,r5,lastdir+'/independent-reader-config.json')]:
  cfg=read(cfgpath);assert sha(raw(cfgpath))==value['config_sha256'] and cfg['run_id']==value['run_id'] and cfg['transport']=={'mode':'DIRECT','proxy_server':None} and cfg['implementation_sha256']=='1c222acdb9d442546cbcff99cde98031fa5ecb7646cc135bb1f30dc9a09cad17'
  assert cfg['authorization_reference']==cfg['tls']['approval_reference'];release=value['release'];assert release['context_closed'] is True and release['runtime_stopped'] is True and release['context_runtime_release_confirmed'] is True and release['errors']==[] and release['pending_callbacks']==0
  events=read(run+'/network-events.json');assert all(x['allowed'] is True for x in events);native=[x for x in events if x['layer']=='native'];counts=collections.Counter((x['method'],x['url_sha256']) for x in native)
  assert len(cfg['allowed_get'])==13 and all(counts[('GET',sha(x['url'].encode()))]==1 for x in cfg['allowed_get']);posts=1 if label=='q5writer' else 0
  assert len(native)==13+posts and sum(x['method']=='POST' for x in native)==posts
  probe=read(run+'/tls-probe.json');assert probe['attempts']==1 and probe['status']=='EXACT_LEAF_CONFIRMED' and probe['leaf_sha256']=='52d8642145282846969a29b97c5c3aaae4c0203c4a6bc06906478f13445e3941';network.append({'role':label,'business_gets':12,'navigation':1,'tls_probe':1,'posts':posts,'context_runtime_release':True})
 ledger={k:v for k,v in reg.items() if '/browser-profiles/usense-existing-ledger/' in k};assert len(ledger)==8
 for original,h in plan['ledger_snapshot'].items():assert sha(Path(ledger[norm(original)]).read_bytes())==h
 key=p5['ledger_key'];li=loads(Path(ledger[next(k for k in ledger if k.endswith('/'+key+'.json'))]).read_bytes());la=loads(Path(ledger[next(k for k in ledger if k.endswith('/'+key+'.accepted.json'))]).read_bytes());send=read(wr+'/send-intent.json')
 assert li['plan_sha256']==w['plan_sha256']==la['plan_sha256'] and li['run_id']==la['writer_run']==w['run_id'] and la['reader_run']==r5['run_id'] and la['acceptance_sha256']==sha(raw(lastdir+'/acceptance.json'))
 assert li['native_body_sha256']==w['native_body_sha256']==send['native_body_sha256'] and li['intent_at']==w['send_intent_at']==send['send_intent_at']
 assert not any(k.endswith('2cd3c0d25c14d89391a5b7e496bbf53dd890020531b1fbf8a4b4b5b7a687a50d.accepted.json') or k.endswith('07d8c7023207b8d0892e1720b9bab58dd755cd4160b88739903fea52d3abdd08.accepted.json') for k in ledger)
 launch=read('final-recovery-outer/single-launch.json');owned=read('final-recovery-outer/batch-01.process.json');outcome=read('final-recovery-outer/outer-outcome.json');abraw=raw('final-recovery-outer/authority-before-launch.raw.json');ab=loads(abraw);spent=loads(Path(next(v for k,v in reg.items() if k.endswith('/final-recovery-authority.json'))).read_bytes())
 assert ab['authority_id']==spent['authority_id']==cp['authority_id']==launch['authority_id']=='05b17ac0-450b-4181-9ecc-5eaa64062120' and sha(abraw)==cp['authority_original_sha256']==launch['authority_original_sha256']
 assert (ab['limits']['attempts_spent'],ab['limits']['attempts_remaining'])==(0,1) and (spent['limits']['attempts_spent'],spent['limits']['attempts_remaining'])==(1,0) and ab['limits']['business_json_gets']==36 and ab['limits']['save_attempts']==1
 assert owned['argv']==launch['argv'] and ts(launch['at'])<ts(owned['started_at'])<ts(rp4['started_at']) and ts(ab['at'])<=ts(launch['at'])<=ts(ab['latest_start_utc'])
 assert owned['exit_code']==outcome['outer_exit_code']==0 and owned['job_active_processes_after']==outcome['job_active_processes_after']==0 and owned['owned_os_release_confirmed'] is True and owned['errors']==[] and owned['job_assigned_before_resume'] is True
 identities=owned['observed_processes'];assert len(identities)==47 and len({(x['pid'],x['creation_filetime']) for x in identities})==47 and all(x['exit_signaled'] is True and x['handle_closed'] is True for x in identities)
 assert {rp4['pid'],wp['pid'],rp5['pid']}<={x['pid'] for x in identities} and all(owned[x] is True for x in ['launcher_exit_signaled','process_handle_closed','thread_handle_closed','job_handle_closed'])
 assert sha(raw('final-recovery-outer/batch-01.stdout'))==owned['stdout']['sha256'] and sha(raw('final-recovery-outer/batch-01.stderr'))==owned['stderr']['sha256'] and (ts(owned['finished_at'])-ts(owned['started_at'])).total_seconds()<900
 cumulative=[]
 for i in range(1,4):
  row=first['targets'][i-1];targetpath=BASE+'five-save-live/target-'+sha(row['node_id'].encode())[:24]+'/plan.json';p=loads(reuse(Path(old1[norm(targetpath)])));receipt=loads(reuse(Path(row['receipt']['path']),row['receipt']['sha256']));assert strict(receipt,receipt_expected(i+17))
  cumulative.append({'printed_question':i,'native_order':i+17,'target':p['target'],'writer_run':row['writer_run'],'reader_run':row['reader_run'],'writer_pid':row['writer_pid'],'reader_pid':row['reader_pid'],'post_attempts':1,'receipt_sha256':row['receipt']['sha256'],'readback_acceptance':'STRICT_FULL_MATCH' if i<3 else 'ACCEPTED_EXACT_CREATED_ZONE_KEY_ORDER_RECONCILIATION','original_failure_preserved':i==3});reader_maps[str(i)]={'run_prefix':BASE+'five-save-live/'+row['reader_run'],'plan_target':p['target']}
 assert recon['third_original_strict_failure']=='PRESERVED_FAIL' and recon['third_ledger_marker_created'] is False
 for row,h in zip(reader_results,[plan['original_q4_native_receipt']['sha256'],w['receipt_sha256']]):cumulative.append({**{k:row[k] for k in ['printed_question','native_order','target','writer_run','reader_run','writer_pid','reader_pid','post_attempts']},'receipt_sha256':h,'readback_acceptance':'STRICT_FULL_MATCH','original_framework_release_failure_preserved':row['printed_question']==4})
 assert len({r['target']['node_id'] for r in cumulative})==len({r['target']['info_id'] for r in cumulative})==len({r['writer_run'] for r in cumulative})==len({r['reader_run'] for r in cumulative})==5
 root_error=Path('D:/1800/docs/evidence/coordinator/a25-final-recovery-actual-intake/root-output-helper-error.json');reb=reuse(root_error);put(S/'root-output-helper-error.json',reb)
 facts={'schema':'A25IndependentFinalActualFacts/v1','status':'PASS_FIXED_ACTUAL','actual_raw_members':110,'this_recovery':{'posts':1,'readers':2,'contexts':3,'business_gets':36,'tls_probes':3,'whole_batch_exit':0,'whole_batch_job_active_after':0,'held_identities_released':47},'full_strict_reader_results':reader_results,'network_records':network,'original_six_ledger_unchanged':True,'final_ledger_files':8,'fifth_only_new_intent_and_accepted':True,'third_fourth_no_marker':True,'cumulative':cumulative,'reader_source_maps':reader_maps,'cumulative_counts':{'posts':5,'exact_success_receipts':5,'fresh_postsave_readers':5,'strict_full_matches':4,'limited_created_zone_matches':1,'contexts':10,'business_gets':120,'framework_context_runtime_release_true':9,'old_q4_framework_release_false':1},'preserved_original_q3_strict_FAIL':True,'preserved_original_q4_framework_release_false':True,'third_fourth_future_revision_predecessor_not_created':True,'reused_fixed_files':used,'author_freeze_helper_failure':{'type':'AttributeError str object has no read_bytes','stderr':item(path('freeze-final-recovery-actual.stderr')),'initial_helper':item(path('freeze-final-recovery-actual.initial-path-error.py')),'effect':'Initial offline freeze helper failed; original error kept; fixed v2 bytes verified without platform replay'},'root_output_helper_error':json.loads(reb),'new_product_tests_or_platform_resources':0}
 put(P/'actual-facts.json',enc(facts));print(json.dumps({'status':facts['status'],'cumulative_posts':5,'cumulative_readers':5,'new_strict_matches':2,'ledger_files':8,'released_identities':47}))
if __name__=='__main__':main()
