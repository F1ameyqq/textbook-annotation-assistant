import sys
sys.path.insert(0,'D:/1800/docs/evidence/A28-independent/code-r1-review')
from control_support import *
import asyncio
from annotation.runtime.usense_live import insertion_writer as writer
ROOT=P/'independent-controls';ROOT.mkdir()
results=[]
def record(name,detail):
 dump(ROOT/(name+'.json'),detail);results.append({'name':name,'status':'PASS'})
def rejected(fn,expected):
 try:fn()
 except ValueError as e:
  assert expected in str(e),(expected,str(e));return str(e)
 raise AssertionError('EXPECTED_REJECTION:'+expected)
with frozen_io():
 prepared,profile,baseline=prepared_for(ROOT/'preflight')
 plan=prepared['first_plan'];after,receipt,window=witness(plan)
 normal=ins.compare_insert_readback(plan,after,receipt,ACTORS,window)
 assert normal['ok'],normal['differences']
 record('real-input-preflight-and-normal',{'normal':normal,'known_source_refs':len(batch.verify_known_info_evidence(plan['approved_new_content']['known_info_evidence'])),
  'candidates':len(prepared['targets']),'frames':sum(len(t['candidate']['frames']) for t in prepared['targets']),'implementation_methods_patched':False})
 # Reuse the ORIGINAL failed witness, changing only the R1 plan shape/evidence.
 old=P.parent/'code-v1-review/identity-control'
 original_after=json.loads((old/'aliased-after.json').read_bytes());oldreceipt=json.loads((old/'receipt.json').read_bytes())
 aw=json.loads((old/'actors-window.json').read_bytes())
 original=ins.compare_insert_readback(plan,original_after,oldreceipt,aw['actors'],aw['window'])
 assert not original['ok'] and original['differences']==[{'path':'new_identity.info_id','reason':'NEW_INFO_ID_ALIASES_OBSERVED_OLD_IDENTITY'}],original['differences']
 record('original-frozen-counterexample',{'original_witness_sha256':sha((old/'aliased-after.json').read_bytes()),'comparison':original})
 aliases=[]
 for order,ident in ins.OBSERVED_OLD_INFO_BY_ORDER.items():
  altered=copy.deepcopy(after);altered['q23_info']['data']['id']=ident
  r=ins.compare_insert_readback(plan,altered,receipt,ACTORS,window)
  assert not r['ok'] and any(d['reason']=='NEW_INFO_ID_ALIASES_OBSERVED_OLD_IDENTITY' for d in r['differences'])
  aliases.append({'baseline_order':order,'info_id':ident,'differences':r['differences']})
 record('all-eight-old-id-aliases',{'cases':aliases})
 proof=load('/known-old-info-r1/evidence.json');source_results=[]
 for row in proof['identities']:
  key=norm(row['source']['path']);mutation={key:data[key]+b' '}
  with frozen_io(mutation):
   err=rejected(lambda:batch.recheck(prepared),'A28_FIXED_EVIDENCE_CHANGED')
   err2=rejected(lambda:writer.verify_evidence(plan),'A28_FILE_CHANGED')
  source_results.append({'baseline_order':row['question_order'],'batch_recheck':err,'writer_evidence':err2})
 record('all-eight-sources-rechecked',{'cases':source_results,'actual_frozen_sources':True})
 # Mutate one actual source between page actor preparation and durable intent.
 active_key=norm(proof['identities'][-2]['source']['path']);events=[]
 with frozen_io() as active_values:
  class Page:
   async def evaluate(self,script,value):
    assert script==writer.PREPARE_LESSON
    events.append('prepare_actors');active_values[active_key]+=b' '
    return {'sha256':'a'*64,'created_by_bound':True,'seven_row_user_ids_bound':True,**ACTORS}
  class Binding:
   def check(self):events.append('binding_check')
  policy=writer.InsertPolicy(Binding(),[]);out=ROOT/'prewrite-source-mutation';out.mkdir();claim=out/'claim.json';state={}
  async def check():
   try:await writer.record_and_send(page=Page(),policy=policy,plan=plan,claim=claim,run=out,result=state)
   except ValueError as e:assert 'A28_FILE_CHANGED' in str(e);return str(e)
   raise AssertionError('MUTATION_REACHED_SEND')
  err=asyncio.run(check())
  assert events==['prepare_actors','binding_check'] and not claim.exists() and not policy.armed and not state
 record('prewrite-source-change-no-intent',{'events':events,'error':err,'claim_created':False,'send_calls':0})

def serial(case):
 root=ROOT/('serial-'+case);root.mkdir();out=root/'out';out.mkdir()
 with frozen_io():
  prepared,profile,baseline=prepared_for(root/'fixture')
  previous={};events=[];current={}
  def child(args,result_path):
   command=args[0];key=result_path.parent.name;index=batch.KEYS.index(key);order=23+index
   events.append({'order':order,'command':command})
   if command=='configure':
    orders=args[args.index('--orders')+1:args.index('--pages')]
    assert orders==([order] if 'writer-' in result_path.name else list(range(23,order+2)))
    return {'exit_code':0,'result':{'sha256':'b'*64}}
   if command=='--insert-writer':
    plan=json.loads((result_path.parent/'plan.json').read_bytes());ins.validate_insert_plan(plan)
    after,receipt,window=witness(plan);current.update(after=after,receipt=receipt,window=window)
    wd=out/('writer-'+str(order));wd.mkdir();ref=dump(wd/'native-receipt.json',receipt)
    dump(Path(prepared['ledger_root'])/(plan['ledger_key']+'.json'),{'synthetic_intent':order})
    if case=='unknown-second-writer' and index==1:return {'exit_code':2,'result':{'status':'UNKNOWN_DO_NOT_RETRY','post_attempts':1}}
    return {'exit_code':0,'pid':1000+order,'finished_at':f'2026-10-23T15:0{index}:02+00:00','result':{
     'run_id':wd.name,'receipt_exact_success':True,'release':{'context_runtime_release_confirmed':True},
     'post_attempts':1,'post_layers':{'context':1,'native':1},'runtime_actor_hashes':ACTORS,
     'send_intent_at':window['start'],'finished_at':window['end'],'receipt_sha256':ref['sha256']}}
   assert command=='capture'
   after={**copy.deepcopy(previous),**copy.deepcopy(current['after'])}
   if case=='duplicate-second-new-info' and index==1:after['q24_info']['data']['id']=after['q23_info']['data']['id']
   if case=='mutate-first-content-at-second' and index==1:after['q23_question']['data']['ocr_result']+='SYNTHETIC_MUTATION'
   rd=out/('reader-'+str(order));rd.mkdir();captures={}
   names=batch.endpoints(range(23,order+2),batch.PAGES,source=True);assert len(names)==(20,27,34,41)[index]
   for name in names:
    ref=dump(rd/(name+'.json'),after[name]);captures[name]={'status':200,'request_counts':{'context':1,'native':1},'sha256':ref['sha256'],'observed_at':f'2026-10-23T15:0{index}:04+00:00'}
   previous.update({f'q{order}_{s}':copy.deepcopy(after[f'q{order}_{s}']) for s in ins.SUFFIXES})
   return {'exit_code':0,'pid':2000+order,'started_at':f'2026-10-23T15:0{index}:03+00:00','result':{
    'status':'NATIVE_GETS_CAPTURED','run_id':rd.name,'save_attempts':0,'release':{'context_runtime_release_confirmed':True},'captures':captures}}
  result=batch.execute(prepared,out,baseline,profile,'SYNTHETIC-NO-LIVE-AUTHORITY','SYNTHETIC-TLS',child,None)
  if case=='normal':
   assert result['status']=='ALL_FOUR_ACCEPTED',result
   assert result['new_completed_count']==4 and result['lesson_cumulative_count']==9
   assert len(events)==16
   for row in result['results']:assert all(row['checks'].values())
  else:
   assert result['status']=='STOPPED_NO_RETRY' and result['new_completed_count']==1,result
   assert [r['status'] for r in result['results'][2:]]==['NOT_RUN','NOT_RUN']
   if case=='unknown-second-writer':assert [e['command'] for e in events if e['order']==24]==['configure','--insert-writer']
   else:
    checks=result['results'][1]['checks'];assert checks['full_comparison']
    assert not checks['new_info_distinct_from_prior_new' if case=='duplicate-second-new-info' else 'all_prior_new_native_content_unchanged']
  record('serial-'+case,{'summary':result,'events':events,'real_contract_functions_unmodified':True,'child_results_synthetic':True})
for case in ('normal','duplicate-second-new-info','unknown-second-writer','mutate-first-content-at-second'):serial(case)
dump(O/'independent-controls.json',{'schema':'A28IndependentR1Controls/v1','status':'PASS','controls':results,'platform_requests':0,
 'old_40_tests_rerun':0,'real_candidate_source_content_reassessment':False,'remaining':'LAUNCHER_DYNAMIC_PENDING'})
print(json.dumps({'status':'PASS','controls':len(results)}))
