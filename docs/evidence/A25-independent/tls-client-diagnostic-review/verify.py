"""Static verification only. Never import or run the captured TLS client."""
import ast,hashlib,json,re
from datetime import datetime,timezone,timedelta
from pathlib import Path,PureWindowsPath
PUB=Path(__file__).resolve().parent
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/tls-client-diagnostic-review-20261023')
def sha(b):return hashlib.sha256(b).hexdigest()
def dt(v):return datetime.fromisoformat(re.sub(r'(\.\d{6})\d+(?=[+-]|Z|$)',r'\1',v))
def path(v):return PureWindowsPath(v).as_posix().lower()
def save(p,v):
 with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def main():
 r=STAGE/'raw';read=lambda p:json.loads(p.read_bytes());authority_raw=(r/'authority.json').read_bytes();authority=json.loads(authority_raw);launch_raw=(r/'launch.json').read_bytes();launch=json.loads(launch_raw);started=read(r/'matrix-started-once.json');matrix=read(r/'matrix-result.json');holder=read(r/'matrix-process.process.json');checkpoint=read(r/'checkpoint.json');script=(r/'tls_matrix.py').read_bytes()
 assert authority_raw==(r/'authority-before-matrix.raw.json').read_bytes()
 assert sha(authority_raw)==launch['authority_sha256']=='359b0358964df12446dac44106084479b27cb69379e687431d56188142587105'
 assert sha(script)==launch['script_sha256']=='8aa14b653a755d53ac3d1932a86345427783d452d627f4b4c0224b5faf7a845c'
 assert authority['authority_id']==launch['authority_id']==started['authority_id']==checkpoint['authority_id']=='9b092218-2a6a-4bf7-a1a5-5dc85e053982'
 assert started['launch_sha256']==sha(launch_raw) and started['pid']==holder['pid']==62472 and launch['argv']==holder['argv']
 assert path(authority['python'])==path(launch['argv'][0])==path(checkpoint['client']) and launch['argv'][1:3]==['-I','-B']
 assert authority['target_host']==authority['SNI']=='www.usense.com' and authority['target_port']==443 and authority['loopback_proxy']=='127.0.0.1:7897'
 assert authority['new_matrix_case_spent']==0 and authority['new_matrix_case_remaining']==3 and authority['historical_initial_A25_round']['remaining']==authority['historical_revised_A25_round']['remaining']==0
 assert authority['limits']['attempts_per_case']==authority['limits']['TCP_connections_per_case_max']==1 and authority['limits']['case_timeout_seconds']==10 and authority['limits']['supervised_process_seconds']==60
 assert dt(authority['at'])<=dt(launch['at'])<dt(holder['started_at'])<dt(started['at'])<dt(matrix['finished_at'])<=dt(holder['finished_at']) and dt(holder['started_at'])<dt(authority['latest_start_utc'])
 assert (dt(holder['finished_at'])-dt(holder['started_at'])).total_seconds()<60
 assert started['python'].startswith('3.12.14 ') and 'OpenSSL 3.5.8' in started['openssl'] and checkpoint['python']=='3.12.14' and checkpoint['openssl']=='3.5.8'
 rows=matrix['results'];assert [v['case']['id'] for v in rows]==['PY312_DIRECT_DEFAULT','PY312_CONNECT_DEFAULT','PY312_CONNECT_TLS12']
 expected='52d8642145282846969a29b97c5c3aaae4c0203c4a6bc06906478f13445e3941';assert authority['expected_leaf_der_sha256']==checkpoint['expected_leaf_der_sha256']==expected
 certs=[];facts=[]
 for v in rows[:2]:
  name=v['case']['id'];stored=read(r/name/'result.json');marker=read(r/name/'spent-once.json');assert stored==v and marker['case_id']==name and marker['spent']==1 and marker['remaining']==0
  cert=(r/name/'peer-leaf.der').read_bytes();assert len(cert)==915 and sha(cert)==expected==v['leaf_sha256'];certs.append(cert)
  assert v['status']=='EXPECTED_LEAF_TLS_SUCCESS' and v['phase']=='TLS_COMPLETE_NO_APPLICATION_DATA' and v['TCP_connect_attempts']==v['TLS_handshake_attempts']==1 and v['application_bytes_sent']==0 and v['socket_closed'] is True and v['resolver_thread_released'] is True and v['errors']==[]
  assert v['expected_leaf'] is True and v['protocol']=='TLSv1.3' and v['cipher']==['TLS_AES_256_GCM_SHA384','TLSv1.3',256]
  assert dt(v['started_at'])<=dt(marker['at'])<dt(v['finished_at']) and (dt(v['finished_at'])-dt(v['started_at'])).total_seconds()<10
  facts.append({'case_id':name,'TCP_attempts':1,'TLS_attempts':1,'TLS_protocol':v['protocol'],'leaf_bytes':len(cert),'leaf_sha256':sha(cert),'post_TLS_application_bytes':0,'socket_closed':True,'resolver_thread_released':True})
 assert certs[0]==certs[1] and rows[0]['peer_endpoint']==rows[0]['selected_system_DNS_address'] and rows[0]['peer_endpoint'][1]==443 and rows[1]['peer_endpoint']==['127.0.0.1',7897]
 assert dt(rows[0]['finished_at'])<=dt(rows[1]['started_at'])
 assert (r/'PY312_CONNECT_DEFAULT/CONNECT-request.raw').read_bytes()==b'CONNECT www.usense.com:443 HTTP/1.1\r\nHost: www.usense.com:443\r\n\r\n' and (r/'PY312_CONNECT_DEFAULT/CONNECT-response.raw').read_bytes()==b'HTTP/1.1 200 Connection established\r\n\r\n'
 assert rows[2]['status']=='NOT_RUN' and rows[2]['reason']=='DEFAULT_EXPECTED_LEAF_OBTAINED' and matrix['cases_spent']==2 and matrix['maximum_cases']==3 and matrix['automatic_retry'] is False and matrix['unexpected_stop'] is False
 assert checkpoint['cases_spent']==2 and checkpoint['third_case']=='NOT_RUN_DEFAULT_CASES_SUCCEEDED' and checkpoint['matrix_closed'] is True and checkpoint['additional_handshakes_authorized']==0
 assert matrix['application_HTTP_requests']==0 and matrix['profile_access'] is False and matrix['browser_started'] is False and checkpoint['application_HTTP_requests']==0 and checkpoint['credentials_or_profile_access'] is False
 for label in ['stdout','stderr']:
  raw=(r/('matrix-process.'+label)).read_bytes();assert len(raw)==holder[label]['bytes'] and sha(raw)==holder[label]['sha256']
 assert json.loads((r/'matrix-process.stdout').read_bytes())==matrix and (r/'matrix-process.stderr').stat().st_size==0
 assert holder['exit_code']==0 and holder['job_active_processes_after']==0 and holder['errors']==[] and holder['resumed'] is True
 assert all(holder[k] is True for k in ['job_assigned_before_resume','launcher_exit_signaled','thread_handle_closed','process_handle_closed','job_handle_closed','owned_os_release_confirmed'])
 assert {v['pid'] for v in holder['observed_processes']}=={62472,72948} and all(v['creation_filetime']>0 and v['image'] and v['exit_signaled'] is True and v['exit_code']==0 and v['handle_closed'] is True for v in holder['observed_processes'])
 tree=ast.parse(script);imports={alias.name.split('.')[0] for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom)) for alias in node.names} # Inspect only; never execute this tree.
 calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call)]
 def methods(name):return [node for node in calls if isinstance(node.func,ast.Attribute) and node.func.attr==name]
 assert len(methods('connect'))==len(methods('do_handshake'))==len(methods('sendall'))==len(methods('wrap_socket'))==1
 wrap=methods('wrap_socket')[0];assert any(k.arg=='do_handshake_on_connect' and isinstance(k.value,ast.Constant) and k.value.value is False for k in wrap.keywords)
 assert methods('sendall')[0].args[0].id=='request'
 assert b'address = addresses[0][4]' in script and b'socket.getaddrinfo(HOST, PORT, socket.AF_INET, socket.SOCK_STREAM)' in script and b'with path.open("xb")' in script
 assert not any(name in imports for name in ['playwright','requests','http','urllib','annotation','subprocess'])
 value={'schema':'A25IndependentTLSClientDiagnosticResult/v1','at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'result':'ACCEPTED_FIXED_TLS_ONLY_DIAGNOSTIC_AND_OWN_RELEASE_ONLY','reviewer_thread_id':'01a166e8-3f23-7192-a560-4724adca74b1','authority_id':authority['authority_id'],'checkpoint_sha256':'add532eb7a0e386bb452fd444f5195c71857df2cec684b33a6983628cd28c537','manifest_sha256':'c3bb08190dc000b8ba746a5aaa05860c4d083ea737bcba0d5f744ca907700810','script_sha256':sha(script),'raw_members_verified':18,'manifest_self':1,'python_reported':'3.12.14','openssl_reported':'3.5.8','fixed_interpreter_pin':'Recorded in authority and checked by captured script; reviewer does not reread executable outside the fixed packet','measured_cases':facts,'certificates_byte_identical':True,'third_case':'NOT_RUN_DEFAULT_CASES_SUCCEEDED','cases_spent':2,'matrix_closed':True,'additional_handshakes_authorized':0,'initial_authority_remaining3':'IMMUTABLE_PRE_EXECUTION_SNAPSHOT_NOT_CURRENT_BUDGET','application_HTTP_requests':0,'CONNECT_control_request_bytes':65,'browser_contexts':0,'credentials_or_profile_access':False,'held_process_ids':[62472,72948],'owned_os_release_confirmed':True,'job_active_processes_after':0,'historical_PY39_failure_root_cause':'UNKNOWN','runtime_causality_proven':False,'causal_limit':'Measurements occurred at a later time; no concurrent same-environment PY39 control. Runtime differences and time-varying network cannot be causally separated.','current_source_or_authentication_or_save_proven':False,'product_runtime_plan_review':'NOT_IN_THIS_PACKET; future same-chat review','reviewer_product_tests_network_TLS_model_OCR_actions':0,'new_activation':False,'findings_requiring_rework':[],'review_status':'COMPLETE_RELEASED'}
 save(PUB/'result.json',value);print(json.dumps({'result':value['result'],'cases_spent':2,'third_case':'NOT_RUN','additional_handshakes_authorized':0,'leaf_sha256':expected,'runtime_causality':'NOT_PROVEN'}))
if __name__=='__main__':main()
