"""Static consistency checks over the copied immutable failure; no product import."""
import hashlib,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
PUB=Path(__file__).resolve().parent;STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/revised-actual-review-20261023')
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def save(p,v):
 with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def main():
 root=STAGE/'raw';read=lambda p:json.loads(p.read_bytes());checkpoint=read(STAGE/'checkpoint-fixed-failure.json');run=root/'runs/usense-readonly-20261023-051137-85bff5bc'
 before=read(root/'authority-before-launch.raw.json');after=read(root/'authority.json');launch=read(root/'single-launch.json');cfgraw=(root/'configs/current-source-01.json').read_bytes();cfg=json.loads(cfgraw);summary=read(run/'capture-summary.json');release=read(run/'release.json');probe=read(run/'tls-probe.json');holder=read(root/'evidence/capture-01.process.json');claim=read(run/'claim.json')
 cfgsha=sha(cfgraw);assert cfgsha==checkpoint['config_sha256']==launch['config_sha256']==summary['config_sha256']==release['config_sha256']==claim['config_sha256']
 authority=checkpoint['authority_id'];assert authority==before['authority_id']==after['authority_id']==launch['authority_id']
 assert sha((root/'authority-before-launch.raw.json').read_bytes())==launch['authority_original_sha256']
 assert before['limits']['attempts_spent']==0 and before['limits']['attempts_remaining']==1 and after['limits']['attempts_spent']==1 and after['limits']['attempts_remaining']==0
 assert after['launch_binding']==launch and launch['attempts_spent']==1 and launch['attempts_remaining']==0 and launch['retry_allowed'] is False and launch['save_attempts_authorized']==0
 plan=read(PUB.parent/'transport-review/plan-review.json');assert before['plan_sha256']==plan['plan_sha256'] and before['numbering_correction_sha256']==plan['supplement_sha256']
 assert before['review_manifest_sha256']==sha((PUB.parent/'transport-review/transport-review-files.sha256').read_bytes()) and before['review_result_sha256']==sha((PUB.parent/'transport-review/result.json').read_bytes())
 assert before['product_commit']==checkpoint['product_commit']=='afc9d761294203e7cfb8086a82f1a7fdd8724372' and before['final_commit']==checkpoint['fixed_launch_commit']=='fef3638d5793347a2b70f21108f6c03ee7856bbc'
 package=Path('D:/1800/.local/stages/a25-independent-20261023/transport-review-20261023/snapshot/src/annotation/runtime/usense_live');digest=sha(canonical([{'path':p.name,'sha256':sha(p.read_bytes())} for p in sorted(package.glob('*.py'))]));assert digest==cfg['implementation_sha256']==launch['implementation_sha256']==plan['implementation_sha256']
 assert cfg['schema']=='UsenseLiveReadConfig/v2' and cfg['operation']=='READONLY_CAPTURE' and cfg['book_id']=='46007447' and len(cfg['allowed_get'])==41
 assert cfg['transport']==before['transport']==probe['transport']==summary['transport']=={'mode':'HTTP_CONNECT_PROXY','proxy_server':'http://127.0.0.1:7897'}
 assert cfg['tls']['origin']==before['tls']['origin']==probe['origin']=='https://www.usense.com' and cfg['tls']['leaf_der_sha256']==before['tls']['leaf_der_sha256'] and cfg['tls']['spki_sha256_base64']==before['tls']['spki_sha256_base64']
 assert cfg['profile']['directory'].replace('\\','/').lower()==before['profile'].lower()
 start=datetime.fromisoformat(holder['started_at']);end=datetime.fromisoformat(holder['finished_at']);at=datetime.fromisoformat(launch['at'])
 assert at<start<end and datetime.fromisoformat(cfg['not_before'])<=at and end<=datetime.fromisoformat(cfg['expires_at']) and start<=datetime.fromisoformat(before['latest_start_utc'])
 assert (datetime.fromisoformat(cfg['expires_at'])-datetime.fromisoformat(cfg['not_before'])).total_seconds()<=900
 request=(run/'proxy-connect-request.raw').read_bytes();response=(run/'proxy-connect-response.raw').read_bytes();assert request==b'CONNECT www.usense.com:443 HTTP/1.1\r\nHost: www.usense.com:443\r\n\r\n' and response==b'HTTP/1.1 200 Connection established\r\n\r\n'
 assert sha(response)==probe['proxy_response_sha256']==checkpoint['proxy_connect_response_sha256']
 assert probe['attempts']==1 and probe['proxy_connect_sent'] is True and probe['phase']=='TLS_HANDSHAKE' and probe['status']=='FAILED_NO_RETRY' and probe['fallback_allowed'] is False and probe['leaf_sha256'] is None
 traces=[]
 for name,phase in [('tls-probe-error','TLS_HANDSHAKE'),('startup-error','TLS_PREFLIGHT'),('capture-error','TLS_PREFLIGHT')]:
  meta=read(run/(name+'.json'));raw=(run/meta['traceback_file']).read_bytes();assert meta['type']=='FileNotFoundError' and meta['phase']==phase and len(raw)==meta['traceback_bytes'] and sha(raw)==meta['traceback_sha256'];assert b'self._sslobj.do_handshake()' in raw and raw.rstrip().endswith(b'FileNotFoundError: [Errno 2] No such file or directory');traces.append({'metadata_file':name+'.json','traceback_file':meta['traceback_file'],'bytes':len(raw),'sha256':sha(raw),'phase':phase})
 assert summary['error']==read(run/'capture-error.json') and probe['error']==read(run/'tls-probe-error.json')
 assert summary['status']=='CAPTURE_FAILED_NO_RETRY' and summary['captures']=={} and summary['save_attempts']==0 and read(run/'network-events.json')==[]
 assert summary['release']==release and release['context_created'] is False and release['runtime_started'] is False and release['context_closed'] is True and release['runtime_stopped'] is True and release['context_runtime_release_confirmed'] is True and release['pending_callbacks']==0 and release['errors']==[] and release['automatic_retry_allowed'] is False and release['automatic_login_performed'] is False
 for label in ['stdout','stderr']:
  raw=(root/'evidence'/('capture-01.'+label)).read_bytes();assert len(raw)==holder[label]['bytes'] and sha(raw)==holder[label]['sha256']
 assert json.loads((root/'evidence/capture-01.stdout').read_bytes())==summary and (root/'evidence/capture-01.stderr').stat().st_size==0
 assert holder['exit_code']==2 and holder['job_assigned_before_resume'] is True and holder['resumed'] is True and holder['job_active_processes_after']==0 and holder['errors']==[]
 assert all(holder[k] is True for k in ['launcher_exit_signaled','thread_handle_closed','process_handle_closed','job_handle_closed','owned_os_release_confirmed'])
 identities=holder['observed_processes'];assert len(identities)==2 and {p['pid'] for p in identities}=={52748,20684}
 assert all(p['creation_filetime']>0 and p['image'] and p['exit_signaled'] is True and p['handle_closed'] is True for p in identities)
 post=read(root/'evidence/profile-postrelease-01.json');assert post['matchingProcesses']==[] and post['lockNamesPresent']==[]
 targets=checkpoint['targets'];assert [x['printed_question'] for x in targets]==list(range(1,6)) and [x['historical_global_order'] for x in targets]==list(range(17,22)) and [x['reported_native_order'] for x in targets]==list(range(18,23))
 assert all(all(t[k] is None for k in ['node_id','info_id','ledger_key','actual_parent']) and all(t[k]=='NOT_RUN' for k in ['source_binding','candidate','save_plan','save','independent_readback','export']) for t in targets)
 value={'schema':'A25IndependentRevisedActualResult/v1','at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'result':'ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY','reviewer_thread_id':'01a166e8-3f23-7192-a560-4724adca74b1','checkpoint_sha256':'1b1a98a1a4ac1fa90e74d9dc79aec521531cda461106affe7424d8340e4ab22b','authority_id':authority,'product_commit':checkpoint['product_commit'],'fixed_launch_commit':checkpoint['fixed_launch_commit'],'config_sha256':cfgsha,'implementation_sha256':digest,'proxy_connect_status':200,'proxy_connect_response_sha256':sha(response),'exact_failure_phase':'TLS_HANDSHAKE / ssl.do_handshake()','outer_capture_phase':'TLS_PREFLIGHT','error_type':'FileNotFoundError','errno':2,'missing_file_path':'UNKNOWN_NOT_PRESENT_IN_TRACEBACK','root_cause':'UNKNOWN','local_code_or_missing_file_cause_proven':False,'leaf_obtained':False,'traces':traces,'budget':{'spent':1,'remaining':0,'retry_allowed':False},'business_responses':0,'save_attempts':0,'context_created':False,'runtime_started':False,'separate_release_equals_summary_release':True,'context_runtime_release_confirmed':True,'held_process_ids':[p['pid'] for p in identities],'owned_os_release_confirmed':True,'job_active_processes_after':0,'target_count':5,'five_question_successors':'NOT_RUN','ledger_initialization':'NOT_RUN_NO_CURRENT_ID','prepared_mkdir_errors':'Reported separately by coordinator, outside these 21 raw members; not reclassified as first TLS failure or a spent live round','product_tests':0,'reviewer_platform_network_profile_OCR_model_actions':0,'new_live_activation':False,'findings_requiring_rework':[],'scope':'Exact fixed failure and two held process identities/Job/context-runtime release only; no current source, credentials, TLS success, root cause or save acceptance'}
 save(PUB/'result.json',value);print(json.dumps({'result':value['result'],'raw_members':21,'phase':value['exact_failure_phase'],'errno':2,'root_cause':'UNKNOWN','budget':[1,0],'held_processes':len(identities)}))
if __name__=='__main__':main()
