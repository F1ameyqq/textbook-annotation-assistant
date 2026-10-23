"""Static supplement checks only; do not load copied Python/OpenSSL binaries."""
import ast,hashlib,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
PUB=Path(__file__).resolve().parent
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/revised-actual-supplement-review-20261023')
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):
 with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def main():
 read=lambda p:json.loads(p.read_bytes());a=STAGE/'copied/actual';s=STAGE/'copied/supplement'
 previous=read(PUB.parent/'revised-actual-review/result.json');assert previous['result']=='ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY'
 cfgraw=(a/'023-current-source-01.json').read_bytes();cfg=json.loads(cfgraw);binding=read(a/'016-config-binding-01.json');configured=read(a/'017-configure-01.process.json');stdout=(a/'019-configure-01.stdout').read_bytes();stderr=(a/'018-configure-01.stderr').read_bytes();out=json.loads(stdout)
 assert sha(cfgraw)==binding['config_sha256']==previous['config_sha256']==out['sha256'] and len(cfgraw)==out['bytes']
 assert cfg['run_id']==binding['run_id'] and cfg['implementation_sha256']==binding['implementation_sha256']==previous['implementation_sha256']
 assert binding['logical_gets']==40 and binding['numbering']=={'printed':[1,2,3,4,5],'historical_global':[17,18,19,20,21],'native':[18,19,20,21,22]}
 for label,raw in [('stdout',stdout),('stderr',stderr)]:assert len(raw)==configured[label]['bytes'] and sha(raw)==configured[label]['sha256']
 assert configured['exit_code']==0 and out['configuration_valid'] is True and out['platform_ready'] is False and out['save_authority_created'] is False and len(stderr)==0
 assert configured['job_active_processes_after']==0 and configured['errors']==[] and configured['owned_os_release_confirmed'] is True
 assert all(configured[k] is True for k in ['job_assigned_before_resume','launcher_exit_signaled','thread_handle_closed','process_handle_closed','job_handle_closed'])
 assert all(p['creation_filetime']>0 and p['exit_signaled'] is True and p['handle_closed'] is True for p in configured['observed_processes'])
 assert {p['pid'] for p in configured['observed_processes']}=={32296,56076}
 pre=read(a/'022-profile-prelaunch-01.json');launch=read(a/'026-single-launch.json');assert pre['matchingProcesses']==[] and pre['lockNamesPresent']==[] and pre['profileExclusive'] is True and datetime.fromisoformat(pre['at'])<datetime.fromisoformat(launch['at'])
 prep=read(a/'020-preparation-helper-first-errors.json');assert [v['tool_exit_code'] for v in prep['observed_failures']]==[1,1] and prep['raw_stdout_stderr']=='NOT_CAPTURED_BY_THE_PREPARATION_SHELL_WRAPPERS' and prep['configure_program_started'] is False and prep['live_started'] is False and prep['budget_spent']==0
 location=read(a/'028-error-location.json');assert location['network_root_cause']=='UNKNOWN' and location['missing_filename'] is None and location['local_missing_path_deterministically_identified'] is False
 for dependency,name in zip(location['dependencies'],['033-ssl.py','029-_ssl.pyd']):
  raw=(a/name).read_bytes();assert len(raw)==dependency['bytes'] and sha(raw)==dependency['sha256']
 assert b'self._sslobj.do_handshake()' in (a/'033-ssl.py').read_bytes().splitlines()[1309]
 assert (a/'029-_ssl.pyd').read_bytes()[:2]==b'MZ'
 audit=read(s/'000-local-call-path-audit.json');source=(STAGE/'copied/source/017-transport.py').read_bytes();assert sha(source)==audit['source_sha256'];tree=ast.parse(source)
 wrappers=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='wrap_socket'];assert len(wrappers)==1 and wrappers[0].lineno==76 and [k.arg for k in wrappers[0].keywords]==['server_hostname'] and len(wrappers[0].args)==1 and isinstance(wrappers[0].args[0],ast.Name) and wrappers[0].args[0].id=='sock'
 opens=sorted(node.lineno for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='open');assert opens==[53,67]
 log=(s/'002-proxy-target-window-matches.raw').read_bytes();search=read(s/'004-proxy-target-window-search.json');listener=read(s/'001-proxy-listener-metadata.json')
 assert len(log)==search['matches_bytes']==292 and sha(log)==search['matches_sha256']=='ffa8b8e0aac6a428fa1e868c856213b99c752ed3988f2c0cd655da0ee2b86604' and search['matching_lines']==1 and len(log.splitlines())==1
 assert b'13:12:14' in log and b'www.usense.com:443' in log and b'(python.exe)' in log and b'match GeoIP(cn) using DIRECT' in log
 assert search['exit_code']==0 and search['whole_logs_not_copied'] is True and search['subscription_or_control_configs_read'] is False and search['network_probe'] is False and (s/'003-proxy-target-window-search.stderr').stat().st_size==0
 assert datetime.fromisoformat(listener['at'])>datetime.fromisoformat(read(a/'013-capture-01.process.json')['finished_at']) and listener['networkProbePerformed'] is False
 outcome=read(s/'005-actual-outcome.json');assert outcome==read(STAGE/'public/evaluation/a25-revised-current-source-actual-20261023.json')
 assert outcome['checkpoint']['sha256']==previous['checkpoint_sha256'] and outcome['proxy_CONNECT_status']==200 and outcome['error']=='FileNotFoundError' and outcome['errno']==2 and outcome['spent']==1 and outcome['remaining']==0 and outcome['retry_allowed'] is False and outcome['business_responses']==0 and outcome['save_attempts']==0
 assert outcome['network_root_cause']=='UNKNOWN' and outcome['retained_proxy_log']['socket_pid_binding']=='NOT_RECORDED' and outcome['retained_proxy_log']['TLS_failure_cause_in_log']=='NOT_RECORDED' and outcome['product_code_changed'] is False and outcome['new_product_tests_run'] is False and outcome['post_failure_network_probe'] is False and outcome['proxy_rules_or_services_changed'] is False
 assert [t['printed_question'] for t in outcome['targets']]==list(range(1,6)) and all(t['save']==t['independent_readback']==t['export']=='NOT_RUN' for t in outcome['targets'])
 value={'schema':'A25IndependentRevisedActualSupplementResult/v1','at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'supplement_result':'ACCEPTED_STATIC_SUPPLEMENT_ONLY','retained_actual_result':previous['result'],'reviewer_thread_id':'01a166e8-3f23-7192-a560-4724adca74b1','complete_final_commit':'b864f413c8bf971153afcefcb78f9621b70ba95f','product_commit':previous['product_commit'],'launch_commit':previous['fixed_launch_commit'],'complete_manifest_sha256':'1634a45f71f7ce9c9feeabc81d3b3f0f641df12715fd337ff80a47e1fb3e3ebc','previous_checkpoint_sha256':previous['checkpoint_sha256'],'source_code_changed':False,'original_21_raw_and_previous_review_unchanged':True,'verified_groups':{'actual':34,'source':30,'supplement':6,'supervisor':1},'additional_actual_by_hash':12,'public_git_members':6,'configuration_success':True,'configure_held_process_ids':[32296,56076],'actual_capture_held_process_ids':previous['held_process_ids'],'prepare_failures':{'count':2,'source':'author retained observation record; original tool responses referenced in chat','raw_stdout_stderr':'NOT_CAPTURED_SEPARATELY','declared_live_started':False,'declared_budget_spent':0,'first_actual_TLS_error_unchanged':True},'runtime_record':{'python':location['python'],'openssl':location['openssl'],'ssl_py_and_ssl_pyd_bytes_verified':True,'copied_libraries_executed_or_loaded':False,'runtime_health_or_missing_file_cause_proven':False},'proxy_log':{'rows':1,'bytes':292,'sha256':sha(log),'local_time':'2026-10-23 13:12:14','rule':'GeoIP(cn)','outbound':'DIRECT','process_label':'python.exe','PID_or_probe_socket_binding':'NOT_RECORDED','causal_inference':'NOT_PROVEN','listener_observation_later_than_actual':True,'whole_logs_read_by_reviewer':False},'B_context':'Coordinator reports direct user confirmation that B success used a different computer/environment; no B inspection/contact or current-host qualification inferred','root_cause':'UNKNOWN','missing_file_path':'UNKNOWN_NOT_PRESENT_IN_TRACEBACK','budget':{'spent':1,'remaining':0,'retry':False},'business_responses':0,'save_attempts':0,'five_question_successors':'NOT_RUN','new_product_tests_platform_network_model_OCR_actions':0,'new_activation':False,'findings_requiring_rework':[],'scope':'Supplemental static completeness/consistency only; retain prior failure/own-release acceptance without adding root cause, live or save authority'}
 save(PUB/'result.json',value);print(json.dumps({'supplement_result':value['supplement_result'],'retained_actual_result':value['retained_actual_result'],'new_by_hash':12,'root_cause':'UNKNOWN','new_activation':False}))
if __name__=='__main__':main()
