"""Static runtime-preparation and HTTP401 evidence checks; no product imports."""
import hashlib,json,re
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path,PureWindowsPath
PUB=Path(__file__).resolve().parent
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/modern-source-http401-review-20261023')
def sha(b):return hashlib.sha256(b).hexdigest()
def dt(v):return datetime.fromisoformat(re.sub(r'(\.\d{6})\d+(?=[+-]|Z|$)',r'\1',v))
def norm(v):return PureWindowsPath(v).as_posix().lower()
def read(p):return json.loads(p.read_bytes())
def save(p,v):
 with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def process(root,label,expected):
 v=read(root/'evidence'/(label+'.process.json'));assert v['exit_code']==expected
 for kind in ['stdout','stderr']:
  raw=(root/'evidence'/(label+'.'+kind)).read_bytes();assert len(raw)==v[kind]['bytes'] and sha(raw)==v[kind]['sha256']
 assert v['owned_os_release_confirmed'] is True and v['job_active_processes_after']==0 and v['errors']==[]
 assert all(v[k] is True for k in ['job_assigned_before_resume','launcher_exit_signaled','thread_handle_closed','process_handle_closed','job_handle_closed'])
 assert all(p['creation_filetime']>0 and p['image'] and p['exit_signaled'] is True and p['handle_closed'] is True for p in v['observed_processes'])
 return v
def main():
 a=STAGE/'actual/raw';r=STAGE/'runtime/raw';run=a/'runs/usense-readonly-20261023-060356-2eb4e596';checkpoint=read(a/'checkpoint-http401.json');runtime=read(r/'checkpoint.json');ready=read(r/'evidence/runtime-import-readiness-01.stdout');plan_raw=(r/'source40-plan.json').read_bytes();plan=json.loads(plan_raw)
 assert runtime['runtime']==ready==plan['runtime'] and sha(plan_raw)==runtime['source_plan_sha256']=='a22034a5b1654738c8940d7c48bee2496fbe17aa48bdb5f13f5656379608b23e'
 assert ready['python'].startswith('3.12.14 ') and 'OpenSSL 3.5.8' in ready['openssl'] and ready['versions']=={'playwright':'1.58.0','Pillow':'11.3.0','greenlet':'3.5.6','pyee':'13.0.1','typing_extensions':'4.16.0'}
 assert ready['has_route_web_socket'] is True and ready['import_current_read_and_writer'] is True and ready['browser_started'] is False and ready['platform_ready'] is False
 runtime_processes={name:process(r,name,exitcode) for name,exitcode in [('venv-create-01',0),('dependencies-install-01',1),('dependencies-install-02',0),('runtime-import-readiness-01',0)]}
 correction=read(r/'dependency-resolution-correction.json');assert correction['original_exact_greenlet_pin']=='3.2.5' and correction['first_install_exit_code']==1
 first_error=(r/'evidence/dependencies-install-01.stderr').read_bytes();assert b'No matching distribution found for greenlet==3.2.5' in first_error
 assert b'greenlet==3.2.5' in (r/'requirements-pinned.txt').read_bytes() and (r/'requirements-top-level.txt').read_bytes().splitlines()==[b'playwright==1.58.0',b'Pillow==11.3.0']
 for label in ['dependencies-install-01','dependencies-install-02']:
  argv=runtime_processes[label]['argv'];assert norm(argv[0])==norm(ready['executable']) and '--isolated' in argv and argv[argv.index('--retries')+1]=='0' and '--no-input' in argv and '--keyring-provider' in argv
 before_raw=(a/'authority-before-launch.raw.json').read_bytes();before=json.loads(before_raw);after=read(a/'authority.json');launch=read(a/'single-launch.json');cfg_raw=(a/'configs/current-source-01.json').read_bytes();cfg=json.loads(cfg_raw);cfgsha=sha(cfg_raw);binding=read(a/'evidence/config-binding-01.json');inputs=read(a/'evidence/input-bindings-01.json');bound_runtime=read(a/'evidence/runtime-binding-01.stdout')
 assert before['authority_id']==after['authority_id']==launch['authority_id']==checkpoint['authority_id']=='60d7e214-9db5-49e5-bd48-fd1747754750'
 assert before['runtime_checkpoint_sha256']==sha((r/'checkpoint.json').read_bytes()) and before['runtime_manifest_sha256']==sha((STAGE/'runtime/manifest.json').read_bytes())
 assert before['runtime']==ready and before['plan_sha256']==sha(plan_raw) and before['product_commit']==plan['product_commit']==checkpoint['product_commit']=='afc9d761294203e7cfb8086a82f1a7fdd8724372'
 assert sha(before_raw)==launch['authority_original_sha256']==binding['authority_original_sha256']==inputs['authority_sha256']
 assert cfgsha==launch['config_sha256']==binding['config_sha256']==checkpoint['config_sha256']=='0ce39a4342f7ead089caefd2e235ce4c26ce86e72df58b03a39edc73054f8abf'
 implementation='5ddfe19c4cb0f2b98555c927a1d205f1165ab23ecac981896627445e29f3c2c8';assert cfg['implementation_sha256']==ready['implementation_sha256']==bound_runtime['implementation_sha256']==launch['implementation_sha256']==checkpoint['implementation_sha256']==implementation
 assert bound_runtime['executable_sha256']==ready['exe_sha256']==launch['runtime_exe_sha256']==binding['runtime_exe_sha256'] and bound_runtime['versions']==ready['versions'] and bound_runtime['has_route_web_socket'] is True
 assert inputs['all_accepted_frozen_members_match'] is True and inputs['all_executed_python_sources_match'] is True and inputs['active_nonruntime_document_deltas']==['docs/status/a.md']
 assert before['limits']['attempts_spent']==0 and before['limits']['attempts_remaining']==1 and after['limits']['attempts_spent']==1 and after['limits']['attempts_remaining']==0 and after['launch_binding']==launch
 assert launch['attempts_spent']==1 and launch['attempts_remaining']==0 and launch['retry_allowed'] is False and launch['save_attempts_authorized']==0
 assert before['old_rounds']==after['old_rounds'] and all(before['old_rounds'][k]['remaining']==0 for k in ['initial_A25','revised_A25_9a6bed2d','TLS_diagnostic_9b092218']) and before['old_rounds']['reopened'] is False
 transport={'mode':'DIRECT','proxy_server':None};assert cfg['transport']==plan['transport']==launch['transport']==checkpoint['transport']==transport
 assert norm(cfg['profile']['directory'])==norm(before['profile'])==norm('D:/1800/.local/browser-profiles/937cbc0b7541861c7c68')
 assert before['printed_questions']==plan['scope']['printed_questions']==list(range(1,6)) and before['native_orders_pending_identity']==plan['scope']['native_orders']==list(range(18,23)) and before['viewer_pages']==[12,173]
 expected_leaf='52d8642145282846969a29b97c5c3aaae4c0203c4a6bc06906478f13445e3941';assert cfg['tls']['leaf_der_sha256']==before['tls']['leaf_der_sha256']==plan['exact_leaf_der_sha256']==expected_leaf and cfg['tls']['spki_sha256_base64']==plan['exact_SPKI']
 origin='https://www.usense.com';target=origin+'/qieti/annotateUnified';directory=origin+'/qieti/api/annotate_ocr/directory/get?file_id=46007447'
 assert cfg['target_url']==target and cfg['tls']['origin']==origin and len(cfg['allowed_get'])==41 and len({v['url'] for v in cfg['allowed_get']})==41 and all(v['max_requests']==1 and v['url'].startswith(origin+'/') for v in cfg['allowed_get'])
 summary=read(run/'capture-summary.json');release=read(run/'release.json');probe=read(run/'tls-probe.json');events=read(run/'network-events.json');claim=read(run/'claim.json');trace_meta=read(run/'capture-error.json');trace=(run/'capture-error.traceback.txt').read_bytes()
 assert cfgsha==summary['config_sha256']==release['config_sha256']==claim['config_sha256'] and probe['status']=='EXACT_LEAF_CONFIRMED' and probe['leaf_sha256']==expected_leaf and probe['phase']=='READY_TO_LAUNCH' and probe['attempts']==1 and probe['proxy_connect_sent'] is False and probe['fallback_allowed'] is False
 assert summary['status']=='CAPTURE_FAILED_NO_RETRY' and set(summary['captures'])=={'directory'} and summary['save_attempts']==0 and summary['transport']==transport and summary['viewer_rendered'] is False
 cap=summary['captures']['directory'];raw=(run/'directory.json').read_bytes();assert raw==b'' and cap['status']==401 and cap['bytes']==len(raw)==0 and cap['sha256']==sha(raw) and cap['filename']=='directory.json' and cap['request_counts']=={'context':1,'native':1}
 assert len(events)==3 and all(e['allowed'] is True and e['method']=='GET' and e['redirected'] is False for e in events)
 assert Counter((e['layer'],e['url_sha256']) for e in events)==Counter([('native',sha(target.encode())),('native',sha(directory.encode())),('context',sha(directory.encode()))])
 assert trace_meta==summary['error'] and trace_meta['code']=='CAPTURE_HTTP_FAILURE' and trace_meta['phase']=='GET_directory' and trace_meta['type']=='BindingError' and len(trace)==trace_meta['traceback_bytes']==455 and sha(trace)==trace_meta['traceback_sha256'] and b'CAPTURE_HTTP_FAILURE' in trace
 assert summary['release']==release and all(release[k] is True for k in ['context_created','runtime_started','context_closed','runtime_stopped','context_runtime_release_confirmed']) and release['pending_callbacks']==0 and release['errors']==[] and release['automatic_login_performed'] is False and release['automatic_retry_allowed'] is False and release['login_requests_per_layer']=={} and release['save_attempts']==0
 actual_processes={name:process(a,name,exitcode) for name,exitcode in [('runtime-binding-01',0),('configure-01',0),('capture-01',2)]};holder=actual_processes['capture-01'];assert norm(holder['argv'][0])==norm(ready['executable']) and holder['argv'][1:3]==['-I','-B'] and json.loads((a/'evidence/capture-01.stdout').read_bytes())==summary
 identities=holder['observed_processes'];assert len(identities)==len({p['pid'] for p in identities})==12 and holder['pid']==64836
 assert dt(launch['at'])<dt(holder['started_at'])<dt(cap['observed_at'])<dt(summary['finished_at'])<=dt(holder['finished_at']) and dt(cfg['not_before'])<=dt(launch['at']) and dt(holder['finished_at'])<=dt(cfg['expires_at']) and dt(holder['started_at'])<dt(before['latest_start_utc'])
 assert (dt(cfg['expires_at'])-dt(cfg['not_before'])).total_seconds()<=900
 for name in ['profile-prelaunch-01.json','profile-postrelease-01.json']:
  v=read(a/'evidence'/name);assert v['matchingProcesses']==[] and v['lockNamesPresent']==[]
 assert checkpoint['first_HTTP_status']==401 and checkpoint['business_responses_retained']==1 and checkpoint['successful_business_responses']==0 and checkpoint['remaining_39_GETs']=='NOT_RUN' and checkpoint['attempts_spent']==1 and checkpoint['attempts_remaining']==0 and checkpoint['login_attempts']==0
 assert [t['printed_question'] for t in checkpoint['targets']]==list(range(1,6)) and all(all(t[k]=='NOT_RUN' for k in ['source_binding','candidate','save_plan','save','independent_readback','export']) and t['stable_node'] is None and t['info_id'] is None and t['actual_parent'] is None for t in checkpoint['targets'])
 result={'schema':'A25IndependentModernSourceHTTP401Result/v1','at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'result':'ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY','failure_subtype':'FIRST_DIRECTORY_GET_HTTP401_EMPTY_BODY','runtime_preparation_result':'ACCEPTED_FIXED_RUNTIME_PREPARATION_EVIDENCE_ONLY','reviewer_thread_id':'01a166e8-3f23-7192-a560-4724adca74b1','authority_id':before['authority_id'],'actual_checkpoint_sha256':'0cc09b14db9f7cdd03e141e7b619a4dfc69c71615ff8cbce1610125fc6a20a22','actual_manifest_sha256':'8c6ee5e6de171ab537071c55406014667ac4e8f5c189176e51e7bd9644d319de','runtime_checkpoint_sha256':'bf68beff4671bed8890981829ced17a47769cd2ce049214fd8636b8752bef358','runtime_manifest_sha256':'0041f98318fad2200f4eb6cd817bd14621bd420e7d4ea87c033d4ef83a70ec2e','source_plan_sha256':sha(plan_raw),'raw_members':{'actual':26,'runtime':18,'manifest_self':2},'product_commit':before['product_commit'],'implementation_sha256':implementation,'config_sha256':cfgsha,'runtime':{'python':ready['python'],'openssl':ready['openssl'],'versions':ready['versions'],'exe_sha256':ready['exe_sha256'],'read_writer_imports_recorded':True,'first_pip_failure_retained':True,'first_pip_pin_file':'HISTORICAL_FAILED_REQUIREMENTS_NOT_FINAL_INSTALLED_LOCK','reproducible_wheel_environment_proof':False},'TLS_exact_leaf_check':'CONFIRMED_IN_PROBE_RECORD_AND_UNCHANGED_APPROVED_HELPER','TLS_leaf_sha256':expected_leaf,'TLS_raw_DER_retained_in_this_actual_packet':False,'TLS_protocol_for_this_actual_probe':'NOT_RECORDED','inert_navigation':'LOCAL_FULFILL_NOT_PLATFORM_RENDER_PROOF','first_business_GET':'directory','HTTP_status':401,'body_bytes':0,'dual_guard_counts':cap['request_counts'],'business_responses_retained':1,'successful_business_responses':0,'remaining_business_GETs':{'count':39,'status':'NOT_RUN'},'authentication_conclusion':'CURRENT_DIRECTORY_REQUEST_NOT_ACCEPTED_HTTP401','specific_token_or_session_cause':'UNKNOWN','token_expiry_proven':False,'context_created':True,'runtime_started':True,'context_runtime_release_confirmed':True,'held_process_ids':[p['pid'] for p in identities],'held_identity_count':12,'owned_os_release_confirmed':True,'job_active_processes_after':0,'budget':{'spent':1,'remaining':0,'retry_allowed':False},'save_attempts':0,'login_attempts':0,'five_question_successors':'NOT_RUN','ledger_initialization':'NOT_RUN','new_authentication_or_login_authorized_by_review':False,'author_active_authentication_preparation_reads':0,'reviewer_product_tests_TLS_network_platform_model_OCR_actions':0,'new_activation':False,'findings_requiring_rework':[],'review_status':'COMPLETE_RELEASED'}
 save(PUB/'result.json',result);print(json.dumps({'result':result['result'],'runtime_preparation_result':result['runtime_preparation_result'],'HTTP':401,'body_bytes':0,'held_identities':12,'budget':[1,0],'auth_cause':'UNKNOWN'}))
if __name__=='__main__':main()
