"""Static A16 fixed-live evidence audit. Reads JSON/raw/Git only; never imports product."""
from collections import Counter
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path,PureWindowsPath
import re
import subprocess

REPO=Path('D:/1800');ROOT=Path('D:/1800-worktrees/a16-live-review')
OUT=ROOT/'docs/evidence/A16/independent-live-review'
E=ROOT/'docs/evidence/A16/current-readonly/revisions/observation-only/live-delivery';R=E/'runtime-raw'
FINAL='003f862065a2d630e666323c0d158e33bcee91e9';PARENT='2453c71c070c153a22a49b772bb2696b3858f5d4'
CANDIDATE='e66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f'
env=dict(os.environ,GIT_NO_LAZY_FETCH='1')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(p.read_bytes())
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
def git(*args):
    allowed={'ls-tree','cat-file','rev-parse','show'}
    assert args[0] in allowed
    return subprocess.check_output(['git','-c','core.longpaths=true']+list(args),cwd=str(REPO),env=env)
def tree(commit):
    result={}
    for row in git('ls-tree','-rz',commit).split(b'\0'):
        if row:
            header,path=row.split(b'\t',1);result[path.decode()]=header.decode().split()
    return result
def stamp(text):
    """Exact fractional UTC epoch, including seven-digit fractions; no raw rewriting."""
    m=re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})',text)
    assert m,text
    whole=datetime.fromisoformat(m[1]+('+00:00' if m[3]=='Z' else m[3]))
    delta=whole-datetime(1970,1,1,tzinfo=timezone.utc)
    return Decimal(delta.days*86400+delta.seconds)+Decimal('0.'+(m[2] or '0'))
def local(text):
    value=stamp(text);seconds=int(value);fraction=value-Decimal(seconds)
    whole=datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(seconds=seconds)
    suffix=format(fraction,'f')[1:] if fraction else ''
    return whole.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')+suffix+' +08:00'
def filetime_epoch(ticks):
    offset=datetime(1970,1,1,tzinfo=timezone.utc)-datetime(1601,1,1,tzinfo=timezone.utc)
    return Decimal(ticks)/Decimal(10000000)-Decimal(offset.days*86400)

raw=(REPO/'docs/evidence/coordinator/a16-live-delivery/input-raw-manifest.json').read_bytes()
assert sha(raw)=='d4dbf2cfa3a98d3ed549353e3676cb1d20601d2bf89b12f995bb4546fb59865b'
with (OUT/'input-raw-manifest.coordinator.json').open('xb') as stream:stream.write(raw)
items=json.loads(raw)['members'];assert len(items)==42
parent,final=tree(PARENT),tree(FINAL)
assert git('rev-parse',FINAL+'^').decode().strip()==PARENT
assert len(parent)==31454 and all(final.get(p)==v for p,v in parent.items())
added=sorted(set(final)-set(parent));assert len(added)==25
prefix='docs/evidence/A16/current-readonly/revisions/observation-only/live-delivery/'
assert all(p.startswith(prefix) for p in added)
verified=[]
for item in items:
    path=item['path'];content=(ROOT/path).read_bytes();mode,kind,blob=final[path]
    assert len(content)==item['size'] and sha(content)==item['sha256'] and blob==item['blob'],path
    assert content==git('cat-file','blob',blob),path
    verified.append({**item,'mode':mode,'type':kind})
digests={'delivery-manifest.json':'d9dad82dda3bf959eb1b6f354157569c34e2ef32b2097447e5f661866f3e8014',
    'author-report.json':'85fcf48838d625f8d47cae8543abe576528b773cb0ccfbf6f8e90fbc9bbc3364',
    'REPORT.md':'a3ac87ad44fcf5b6c194325d16f3ec22e5d7d558e63c5f8246a7bd6b6ff38e1c',
    'activation.json':'f4893ca664e181118a7a347eadbdbcea724483d3626e9cecf4cde8ba6efe86a7',
    'user-decision.json':'01ee143549fa0c047ba0a939d3b9164ebaef2cb93b5e438c135b5d881093c022',
    'independent-preflight.json':'d536d9b2552586a0e1838384a1b2775df1b14023d3e7ad901ac1a2b991e06a0c'}
for name,expected in digests.items():assert sha((E/name).read_bytes())==expected,name
delivery=load(E/'delivery-manifest.json');assert len(delivery['members'])==24
for item in delivery['members']:
    content=(ROOT/item['path']).read_bytes()
    assert len(content)==item['size'] and sha(content)==item['sha256'] and final[item['path']][2]==item['blob']
candidate=load(ROOT/'docs/evidence/A16/current-readonly/revisions/observation-only/candidate-manifest.json')
assert len(candidate['members'])==16
for item in candidate['members']:
    content=(ROOT/item['path']).read_bytes()
    assert len(content)==item['size'] and sha(content)==item['sha256'] and parent[item['path']]==final[item['path']]
assert sha((ROOT/'docs/evidence/A16/current-readonly/revisions/observation-only/candidate-manifest.json').read_bytes())==CANDIDATE
local_manifest=load(E/'local-output-manifest.json');assert len(local_manifest['members'])==12
assert set(p.name for p in R.iterdir())=={Path(i['delivery_ref']).name for i in local_manifest['members']}
for item in local_manifest['members']:
    content=(E/item['delivery_ref']).read_bytes()
    assert item['copied_to_git'] is True and len(content)==item['size'] and sha(content)==item['sha256']
assert local_manifest['static_bytes_and_full_source_sidecars_copied'] is False
assert not any(p.endswith(('.bin','.js','.jpg','.png','.mp4','.webm','.source.json')) for p in added)
dispatch=git('show','6041eecb7ad0a7da4954d18b5a0dc871c33951bc:docs/tasks/A16-single-live-fixed-independent-review.md')
assert sha(dispatch)=='4a30250bdc6a38502c51bfa885c669fbdc95ba8190669a1e6adf5a99eabb1a31'
with (OUT/'dispatch.raw.md').open('xb') as stream:stream.write(dispatch)
save('input-raw-manifest.independent.json',{'task':'A16','final':FINAL,'parent':PARENT,'members':verified})
save('raw-preservation.json',{'result':'PASS_RAW_ONLY','input_members':42,'new_delivery_members':25,
    'previous31454_members_preserved':True,'candidate16_members_and_manifest_unchanged':True,
    'delivery24_members_verified':True,'runtime12_original_bytes_verified':True,
    'static_code_images_video_source_sidecars_added':0,'product_or_old_evidence_modified':False,
    'local_root_not_accessed':True,'product_import_or_execution':False,'git_lazy_fetch':False})

a=load(E/'activation.json');d=load(E/'user-decision.json');pre=load(E/'independent-preflight.json')
dispatch_live=load(E/'dispatch-intent.json');intent=load(E/'author-launch-intent.json')
started=load(E/'author-launch-started.json');wait=load(E/'author-tool-wait.json')
state=load(R/'current-state.json');worker=load(R/'worker-release.json');product=load(R/'launcher-release.json');occupancy=load(R/'occupancy.json')
assert sha((E/'dispatch-intent.json').read_bytes())==wait['dispatch_intent_sha256']==started['dispatch_intent_sha256']==intent['dispatch_intent_sha256']
assert a['user_decision_sha256']==digests['user-decision.json'] and a['independent_report_sha256']==digests['independent-preflight.json']
scope_keys=('task','run_id','workflow_commit','scope','candidate_manifest_sha256','sample_limit',
    'automatic_schema_confirmation','fixed_business_get_count','original_get_count')
for key in scope_keys:assert a[key]==d[key]==pre[key],key
assert a['candidate_manifest_sha256']==CANDIDATE and a['book_id']=='46007447' and a['viewers']==[14,173]
assert a['sample_limit']==0 and a['automatic_schema_confirmation'] is False
assert a['tls_mode']==d['tls_mode']=='CONTEXT_EXCEPTION' and d['live_authorized'] is True and d['certificate_exception_authorized'] is True
assert d['answer_verbatim']=='批准，仅此轮有界只读观测' and d['retry_authorized'] is False and d['later_stage_authorized_by_this_record'] is False
assert pre['result']=='ACCEPTED_OFFLINE_ONLY' and pre['scope']==a['scope']
assert a['new_live_limit']==a['context_limit']==a['navigation_limit']==1 and a['total_seconds']==900
assert a['fixed_business_get_count']==6 and a['original_get_count']==2
assert a['login_submission_limit']==a['business_write_limit']==a['upload_limit']==a['ocr_limit']==0
assert intent['launch_calls']==0 and started['launch_calls']==wait['launch_calls']==1
assert intent['retries']==started['retries']==wait['retries']==0
assert wait['wait_completed'] is True and wait['exit_code']==2 and wait['launcher_pid']==started['launcher_pid']
assert dispatch_live['status']=='READY_TO_SEND' and dispatch_live['actual_started'] is False
assert dispatch_live['argv']==intent['argv']==started['argv']==wait['argv']
assert dispatch_live['workspace']==wait['cwd']==started['cwd']==intent['cwd']
argv=wait['argv']
assert argv[1:5]==['-B','tools/a16_current_state_launcher.py','--live','--certificate-exception']
flags={argv[i]:argv[i+1] for i in range(5,len(argv),2)}
assert flags['--candidate-sha256']==CANDIDATE and flags['--activation-sha256']==digests['activation.json']
assert flags['--profile-fingerprint']==a['profile_fingerprint']
child_intent=load(R/'launcher-intent.json')
assert PureWindowsPath(child_intent['argv'][2])==PureWindowsPath(wait['cwd'])/'tools/a16_current_state_probe.py'
assert child_intent['argv'][3]=='--_launched' and child_intent['argv'][4:]==argv[3:]
assert child_intent['shell'] is False and child_intent['candidate_sha256']==CANDIDATE
for name in ['launcher-claimed.json','live-started.json','worker-claimed.json','occupancy-claimed.json']:
    marker=load(R/name)
    assert marker['task']==a['task'] and marker['run_id']==a['run_id'] and marker['workflow_commit']==a['workflow_commit']
    assert marker['scope']==a['scope'] and marker['sample_limit']==0 and marker['candidate_sha256']==CANDIDATE
    assert marker['activation_sha256']==digests['activation.json'] and marker['certificate_exception'] is True
    assert marker['profile_fingerprint']==a['profile_fingerprint']
assert load(R/'profile-binding.json')['fingerprint']==a['profile_fingerprint']
stdout=(R/'author-tool-stdout.raw').read_bytes();stderr=(R/'author-tool-stderr.raw').read_bytes()
assert len(stdout)==wait['stdout_size'] and sha(stdout)==wait['stdout_sha256'] and stderr==b'' and sha(stderr)==wait['stderr_sha256']
outer_print=json.loads(stdout);assert outer_print['product_exit_code']==2 and outer_print['release']=='RELEASED'
assert outer_print['launcher_own_os_exit_identity']=='UNKNOWN'
save('authorization-and-single-call.json',{'task':'A16','result':'MATCHED_FIXED_BINDINGS_ONLY',
    'candidate':CANDIDATE,'activation_sha256':digests['activation.json'],'decision_sha256':digests['user-decision.json'],
    'independent_preflight_sha256':digests['independent-preflight.json'],'scope':a['scope'],'sample_limit':0,
    'past_context_exception_explicitly_approved':True,'reusable_exception':False,'one_intent_started_wait_chain':True,
    'dispatch_snapshot_is_pre_call_only':True,'actual_launch_calls':1,'retry_count':0,'marker_bindings':4,
    'matching_profile_fingerprint_record':'Hash binding only; no current profile read or authentication proof',
    'original_argv_cwd_unchanged':True,'live_used':1,'live_remaining':0,'new_launch_or_permission_granted':False})

audit=state['network_audit'];assert len(audit)==8
assert [e['time'] for e in audit]==sorted(e['time'] for e in audit)
blocked=next((i,e) for i,e in enumerate(audit) if e['decision']=='BLOCK')
index,first=blocked
assert index==4 and first['hostname']=='cdn.bootcdn.net' and first['port']==443 and first['scheme']=='https'
assert first['resource_type']=='Script' and first['method']=='GET' and first['source']=='FETCH_REQUEST_STAGE'
assert first['category']=='ORIGIN_BLOCKED' and not first['expected_passive_denial'] and not first['redirect_hop']
assert state['guard_pre_shutdown']['failure']['codes']==['ORIGIN_BLOCKED']
assert state['guard_at_serialization']['failure']['codes']==['ORIGIN_BLOCKED']
assert state['guard_at_serialization']['pending_tasks']==0 and state['guard_at_serialization']['terminal_stopped'] is True
assert state['error']['codes']==['NETWORK_GUARD_STOPPED'] and state['outcome']=='ERROR'
assert state['steps']['navigation']=='FAILED' and all(v=='NOT_RUN' for k,v in state['steps'].items() if k!='navigation')
assert all(not e['business_read'] and not e['category'].startswith('BUSINESS_') and e['category']!='REGISTERED_ORIGINAL' for e in audit)
assert state['sources']==state['static_assets']==[] and 'target' not in state and 'book' not in state
assert state['body_status']==state['schema_status']=='UNKNOWN' and state['sample']['status']=='NOT_RUN'
assert state['sample']['content_acceptable'] is False and state['production_ready'] is False and state['write_eligible'] is False
assert state['business_writes']==state['login_submissions']==0
sources=Counter(e['source'] for e in audit)
assert sources=={'FETCH_REQUEST_STAGE':5,'CONTEXT_FIRST_REQUEST':3}
assert sum(e['category']=='NAVIGATION' and e['source']=='FETCH_REQUEST_STAGE' for e in audit)==1
assert sum(e['category']=='NAVIGATION' and e['source']=='CONTEXT_FIRST_REQUEST' for e in audit)==1
save('network-and-counts.json',{'task':'A16','actual_outcome':'LIVE_FAILED_GUARD_STOPPED','first_block_event_number':5,
    'first_block_original':first,'first_block_beijing':local(first['time']),
    'terminal_code':'NETWORK_GUARD_STOPPED','guard_first_code':'ORIGIN_BLOCKED',
    'basis':'Actual raw current-state events/steps and fixed policy/call path; not author summary alone',
    'counts':{'launcher_calls':1,'created_contexts':1,'main_navigation_attempts':1,'fixed_business_GETs':0,
        'original_GETs':0,'sample_GETs':0,'static_originals_saved':0,'login_submissions':0,'business_writes':0,
        'audit_events':8,'native_request_stage_events':5,'context_route_events':3},
    'auxiliary_actual_send_total':'UNKNOWN','navigation_HTTP_status':'UNKNOWN',
    'dual_navigation_events_are_not_two_attempts':True,
    'allowed_native_static_events_not_successful_responses':'Subsequent context STOPPED blocks; no retained HTTP status/response identity',
    'audit_request_correlations':'No per-request IDs/full URLs retained; do not derive unique network request totals',
    'UI_request_limit':'NOT_RUN alone is not global traffic proof; all retained guard events show no business/original/sample allowance',
    'not_platform_authentication_or_source_pass':True,'no_CDN_allowance_or_root_cause_inference':True})

begin,end=stamp(a['not_before']),stamp(a['expires_at']);assert end-begin==Decimal(900)
time_sources=[('author_launch',started['started_at']),('launcher_started',product['started_at']),
    ('product_supervision_started',worker['started_at']),('profile_binding',load(R/'profile-binding.json')['time']),
    ('context_observation_started',state['started_at'])]+[(f'audit_{i+1}',e['time']) for i,e in enumerate(audit)]+[
    ('context_result_finished',state['finished_at']),('worker_release_finished',worker['finished_at']),
    ('product_release_finished',product['finished_at']),('author_wait_finished',wait['finished_at'])]
assert all(begin<=stamp(t)<end for _,t in time_sources)
wall_ms=(stamp(wait['finished_at'])-stamp(wait['started_at']))*1000
assert stamp(started['started_at'])<stamp(state['started_at'])<stamp(first['time'])<stamp(state['finished_at'])<stamp(worker['finished_at'])<stamp(product['finished_at'])<stamp(wait['finished_at'])
save('timeline.json',{'task':'A16','timezone_display':'Asia/Shanghai +08:00','approval_window_original':
    {'not_before':a['not_before'],'expires_at':a['expires_at']},'window_seconds_exact':str(end-begin),
    'entries':[{'event':name,'original_time':text,'beijing':local(text),'epoch_seconds_exact':str(stamp(text))} for name,text in time_sources],
    'all_recorded_events_inside_window':True,'author_reported_duration_ms':wait['duration_ms'],
    'author_duration_clock_source':'NOT_SPECIFIED_IN_FIXED_WAIT_RECORD',
    'wall_timestamp_difference_ms_exact':str(wall_ms),
    'difference_explanation':'Archive has duration and wall timestamp fields; exact reason for3.598ms difference is not established. Retain10469ms and exact wall10472.598ms separately.',
    'fraction_handling':'Regex separates whole seconds/timezone and Decimal arbitrary fraction; original strings untouched; FILETIME int ticks kept exact',
    'no_cross_process_monotonic_comparison':True})

context=state['release']
assert context['context_created'] and context['context_close_attempted'] and context['context_closed']
assert context['runtime_stop_attempted'] and context['runtime_stopped'] and context['errors']==[] and context['state']=='RELEASED'
release_rows=[]
for role,record,expected_exit,handle in [('occupancy',occupancy,0,'handle_closed'),
    ('worker',worker,2,'worker_handle_closed'),('product',product,2,'product_handle_closed')]:
    b,c=record['before'],record['after']
    assert all(type(r[k]) is int and r[k]>0 for r in [b,c] for k in ['pid','created_filetime'])
    assert b['pid']==c['pid'] and b['created_filetime']==c['created_filetime']
    assert b['exit_observed'] is False and c['exit_observed'] is True and c['exit_code']==expected_exit
    assert type(c['exited_filetime']) is int and c['exited_filetime']>c['created_filetime']
    assert record[handle] is True
    created,exited=filetime_epoch(c['created_filetime']),filetime_epoch(c['exited_filetime'])
    assert begin<created<exited<end
    release_rows.append({'resource':role,'pid':c['pid'],'created_filetime_exact':str(c['created_filetime']),
        'exited_filetime_exact':str(c['exited_filetime']),'creation_identity_match':True,
        'exit_observed':True,'exit_code':c['exit_code'],'handle_closed':True,
        'process_lifetime_seconds_exact':str((Decimal(c['exited_filetime'])-Decimal(c['created_filetime']))/10000000),
        'streams_closed':'Derived from fixed cleanup continuation before handle_closed flag; no separate per-stream runtime bool',
        'acceptance':'ACCEPTED_EXACT_HELD_CHILD_RELEASE_ONLY'})
assert occupancy['matching_processes']==0
for record in [worker,product]:
    assert record['job_assigned'] and record['job_active_before_final_cleanup']==1 and record['job_active_final']==0
    assert record['job_closed'] and record['errors']==[] and record['state']=='RELEASED'
assert worker['creation_identity_match'] is True and worker['hard_deadline_exceeded'] is False
assert product['total_deadline_exceeded'] is False
assert product['launcher_own_os_exit_identity'].startswith('UNKNOWN') and wait['launcher_own_os_creation_identity'].startswith('UNKNOWN')
assert outer_print['errors'] is False
save('owned-release-ledger.json',{'task':'A16','scope':'Fixed records plus exact retained source cleanup; no new resource check',
    'context_runtime':{'record':context,'acceptance':'ACCEPTED_OWN_CONTEXT_AND_RUNTIME_CLOSE'},
    'held_processes':release_rows,
    'jobs':[{'owner':'product→worker','active_before_final_cleanup':1,'active_final':0,'job_closed':True},
        {'owner':'launcher→product','active_before_final_cleanup':1,'active_final':0,'job_closed':True}],
    'job_scope':'Fixed OwnedJob assigns only gated held Popen child and descendants; KILL_ON_JOB_CLOSE and owned TerminateJobObject, no global kill',
    'outer_launcher':{'pid':wait['launcher_pid'],'wait_completed':True,'exit_code':2,'OS_creation_identity':'UNKNOWN_NOT_CAPTURED'},
    'prior_occupancy_matching_processes':0,'post_run_or_global_process_absence':'NOT_CHECKED_NOT_PROVEN',
    'source_refs':['tools/a16_current_state_probe.py:occupancy/supervise','tools/a16_current_state_launcher.py:finally',
        'docs/evidence/A15/certificate-exception/reviewed-native/native_windows.py:held_identity',
        'docs/evidence/A16/current-readonly/dependencies/a15_native_reference.py:OwnedJob/close_owned'],
    'raw_child_stdout_limit':'Product stdout90bytes/hash retained by parent; its raw stream not separately archived. Outer author stdout135bytes/hash verified; worker stdout/stderr0.'})

save('review-result.json',{'task':'A16','result':'ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY',
    'review_thread_id':'01a15841-0d44-7272-9740-40d013839869',
    'dispatch_workflow':'6041eecb7ad0a7da4954d18b5a0dc871c33951bc','author_final':FINAL,'run_from_final':PARENT,
    'product_commit':'dd22193a30e969aaf90043365f31f84a5a50df59','candidate_manifest_sha256':CANDIDATE,
    'scope':a['scope'],'actual_live_result':'FAILED_ORIGIN_BLOCKED_NETWORK_GUARD_STOPPED','live_used':1,'live_remaining':0,
    'failure_archive':'LIMITED_ACCEPTED','context_runtime_release':'LIMITED_ACCEPTED',
    'owned3_child_identity_exit_handle_release':'LIMITED_ACCEPTED','owned2_job_release':'LIMITED_ACCEPTED',
    'outer_launcher_OS_creation_identity':'UNKNOWN','outer_launcher_wait_exit':2,
    'auxiliary_network_send_total':'UNKNOWN','navigation_HTTP_status':'UNKNOWN','authentication':'NOT_PROVEN',
    'current_book_directory_frames_source_originals_mapping':'NOT_RUN','current_static_assets':0,
    'body_schema':'UNKNOWN','sample':'NOT_RUN','production_ready':False,'write_eligible':False,
    'old_R02':'REWORK_CAPABILITY_DISABLED','first_question_save_refresh_reopen':'NOT_RUN',
    'new_product_or_suite_or_launcher_or_import_execution':0,'new_platform_connection':0,
    'new_TLS_exception_or_activation_granted':False,'CDN_whitelist_changed':False,'retry_authorized':False,
    'next_dependency':'Coordinator may prepare a separately authorized bounded adaptation; this live attempt cannot be reopened or retried.'})
save('review-checks.json',{'task':'A16','result':'STATIC_EVIDENCE_CHECKS_COMPLETE','input42':True,'old31454':True,
    'candidate16_unchanged':True,'runtime12_raw':True,'approval_marker_argv_scope_bindings':True,
    'exact_window_and_timeline':True,'first_block_and_stop_successors':True,'counts_not_audit_totals':True,
    'context_runtime_and_held_child_Job_release_fields':True,'unknowns_retained':True,
    'non_sensitive_runtime_scope':'Reviewed explicit fields; no loaded script/image/crop/source sidecar/credential value added',
    'product_execution_or_import':False,'local_path_access':False,'live_or_suite_replay':False})
print(json.dumps({'result':'ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY','raw42_preserved':True,'old31454_preserved':True,
    'first_block_host':first['hostname'],'audit_events':8,'held_children':3,'owned_jobs':2,
    'outer_launcher_identity':'UNKNOWN','live_used':1,'live_remaining':0,'wall_ms_exact':str(wall_ms)}))
