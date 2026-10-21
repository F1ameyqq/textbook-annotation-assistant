"""Static frozen-record comparisons; never execute product or captured script."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
A=ROOT/'docs/evidence/A24/controlled-capture-current-body-actual'
AUTH='411ec3757822ed374ed7f4c13e6a0becc571609d2d2b4117991c8acc20c4e244'
def load(path):return json.loads(path.read_bytes())
def sha(raw):return hashlib.sha256(raw).hexdigest()
def ft(value):return datetime.fromtimestamp(value/10000000-11644473600,timezone.utc)

m=load(OUT/'input-raw-manifest.json');private=load(A/'private-raw-manifest.json')['members']
a=load(A/'inputs/authority.json');decision=load(A/'inputs/decision.json');accepted=load(A/'inputs/prewrite-acceptance-binding.json')
claimed=load(A/'raw/outer/outer-claimed.json');outer=load(A/'raw/outer/outer-result.json')
w=load(A/'raw/run/worker-result.json');actual=load(A/'actual-result.json')
start=datetime.fromisoformat(a['not_before']);end=datetime.fromisoformat(a['expires_at'])
checks={}
checks['exact_authority_and_ref_hashes']=sha((A/'inputs/authority.json').read_bytes())==AUTH and all(sha((A/'inputs'/name).read_bytes())==a['refs'][key]['sha256'] for key,name in [('decision','decision.json'),('independent_report','prewrite-acceptance-binding.json')])
checks['exact_null_schema_scope']=a['refs']['schema_profile'] is None and a['role']=='AUTHOR_SAVE' and decision['effective_current_branch']==accepted['effective_current_branch'] and decision['effective_current_branch']['business_get']==4 and not accepted['conditional_save_admitted'] and not accepted['independent_reopen_admitted']
checks['single_claim_chain_within_900s']=(end-start).total_seconds()==900 and claimed['attempt_limit']==1 and claimed['authority_sha256']==outer['authority_sha256']==AUTH and claimed['run_id']==outer['run_id']==a['run_id'] and start<=datetime.fromisoformat(claimed['at'])<=datetime.fromisoformat(outer['at'])<=end
checks['frozen_pre_import_158_and_four_source_checks']=claimed['dependencies_verified']==158 and claimed['resources_before_verification']==0 and actual['library_preflight']['before_product_import'] is True and actual['library_preflight']['candidate_dependencies_hash_verified']==158 and actual['library_preflight']['installed_source_hashes_verified']==4 and sha((A/'raw/outer/held_launcher_once.py').read_bytes())==claimed['wrapper_sha256']
checks['bootstrap_session_admission_completed']=all(w['bootstrap_steps'].get(k)=='DONE' for k in ('runtime_start','context_launch','guard_install','online','navigation','session_completion','viewer_admission')) and w['first_error'] is None
reads=w['prewrite']['reads']
checks['four_fixed_http200_records']=reads==actual['reads'] and [r['slot'] for r in reads]==['book','directory','frames','export'] and all(r['http_status']==200 for r in reads) and actual['business_get_count']==4
checks['unbound_terminal_no_effect']=w['status']=='PREWRITE_BLOCKED_NO_EFFECT' and w['prewrite']['status']=='CURRENT_SCHEMA_UNBOUND' and w['prewrite']['write_allowed'] is False and w['prewrite']['successors']=='NOT_RUN' and w['steps']['adapter']=='NOT_RUN' and all(actual[k]=='NOT_RUN' for k in ('signature','upload','commit','refresh','reopen')) and w['resend_allowed'] is False
checks['book_only_reported_length_hash']=reads[0]['bytes']==4186 and reads[0]['sha256']=='5cb2c703c7d4910fa277003c7f58e6a75c4b54614f2fe4be11c556ad15ebb8a6' and 'controlled_raw_ref' not in reads[0] and actual['book_raw_body']=='NOT_PERSISTED_BY_FROZEN_COLLECTOR_FINITE_HASH_ONLY'
current=[]
for row in private:
    match=[r for r in m['private_references'] if r.get('bound_original_path',r.get('source_path'))==row['path'] and r['bytes']==row['bytes'] and r['sha256']==row['sha256']]
    assert len(match)==1
    current.append({**row,'snapshot_path':match[0]['snapshot_path']})
checks['sixteen_current_reference_categories']=len(current)==16 and dict(Counter(r['kind'] for r in current))==dict(BODY_SNAPSHOT=3,STREAM=8,CAPTURE_OWNER_MARKER=1,SCRIPT_RAW=1,SCRIPT_PROVENANCE=1,OUTER_LAUNCHER_STREAM_COPY=2)
checks['three_body_snapshot_bytes_bound']=all(any(r['kind']=='BODY_SNAPSHOT' and all(r[k]==read['controlled_raw_ref'][k] for k in ('path','bytes','sha256')) for r in current) for read in reads[1:])
capture=w['private_capture_evidence'];binding=capture['owner_binding']
marker=next(r for r in current if r['kind']=='CAPTURE_OWNER_MARKER')
marker_doc=load(Path(marker['snapshot_path']))
checks['capture_marker_exact_current_authority']=marker_doc==binding and binding['authority_sha256']==AUTH and binding['run_id']==a['run_id'] and binding['candidate_sha256']==a['refs']['candidate']['sha256'] and binding['scope_sha256']==a['scope_sha256'] and Path(binding['directory'])==Path(a['output_directory'])/'private/source-capture'
asset=capture['assets'][0]
provenance_ref=next(r for r in current if r['kind']=='SCRIPT_PROVENANCE');provenance=load(Path(provenance_ref['snapshot_path']))
checks['script_raw_provenance_private_and_bound']=capture['status']=='BOUND_PRIVATE_CAPTURE' and capture['source_urls_exported'] is False and capture['captured_code_executed_by_collector'] is False and len(capture['assets'])==1 and asset['executed_by_collector'] is False and all(any(r['kind']==kind and all(r[k]==asset[key][k] for k in ('path','bytes','sha256')) for r in current) for kind,key in [('SCRIPT_RAW','private_raw_ref'),('SCRIPT_PROVENANCE','private_provenance_ref')]) and sha(provenance['source_url'].encode())==asset['source_url_sha256'] and provenance['sha256']==asset['sha256'] and provenance['size']==asset['size']==3065996 and provenance['executed_by_collector'] is False and 'source_url' not in capture and 'source_url' not in asset and 'source_url' not in asset['loaded_origin']
for key in ('guard_evidence_before_release','guard_evidence_after_release'):
    s=w[key];events=s['events']
    checks[key+'_finite_complete_no_failure']=s['status']=='PROJECTED' and len(events)==s['total_events']==s['retained_events']==14 and s['complete'] is True and s['truncated'] is False and s['first_failure'] is None and [e['index'] for e in events]==list(range(14)) and s['exclusions']['combined_guard_events']==s['exclusions']['completed_denial_calls']==1 and s['exclusions']['pending_callbacks']==0 and all(s['exclusions'][k]=='UNKNOWN' for k in ('http_send_count','dns_tcp_tls_activity','script_necessity'))
checks['context_runtime_callback_release']=w['release']['released'] is True and w['release']['context_closed'] is True and w['release']['runtime_stopped'] is True and w['release']['callback_pending']==0 and w['release']['errors']==[] and w['release']['guard_failure'] is None and w['guard_evidence_after_release']['settlement']==dict(pending_callbacks=0,sealed=True,shutdown_started=True,stopped=True)
held_summary={}
for stage in ('launcher','product','worker','occupancy'):
    held=load(A/('raw/run/'+stage+'-held-release.json'));claim=load(A/('raw/run/'+stage+'-claimed.json'));before,after=held['before'],held['after']
    valid=(held['authority_sha256']==claim['authority_sha256']==AUTH and claim['run_id']==a['run_id'] and before['pid']==after['pid'] and before['created_filetime']==after['created_filetime'] and not before['exit_observed'] and after['exit_observed'] is True and after['exit_code']==0 and start<=ft(before['created_filetime'])<=ft(after['exited_filetime'])<=end and held['creation_identity_match'] is True and held['job_assigned'] is True and held['stdin_token_sent_after_job_assignment'] is True and held['job_active_final']==0 and held['job_closed'] is True and held['handle_closed'] is True and held['errors']==[] and held['released'] is True and held['stderr_bytes']==0)
    checks[stage+'_held_identity_exit_and_release']=valid
    checks[stage+'_opaque_stream_refs_bound']=all(any(r['kind']=='STREAM' and all(r[k]==ref[k] for k in ('path','bytes','sha256')) for r in current) for ref in held['controlled_raw_output_refs'].values())
    held_summary[stage]=dict(pid=before['pid'],created_filetime=before['created_filetime'],exited_filetime=after['exited_filetime'],exit_code=after['exit_code'],verified=valid)
checks['external_holder_launcher_exit_not_self_proof']=outer['held_launcher']==load(A/'raw/run/launcher-held-release.json') and outer['helper_own_exit_identity']=='NOT_SELF_CERTIFIED'
raw_capture=load(A/'raw/outer/raw-capture.json')
checks['outer_launcher_stream_copies_bound']=raw_capture['complete'] is True and all(any(r['kind']=='OUTER_LAUNCHER_STREAM_COPY' and r['bytes']==raw_capture[k]['bytes'] and r['sha256']==raw_capture[k]['sha256'] for r in current) for k in ('stdout','stderr'))
checks['round_spent_no_retry_profile_uninspected']=actual['new_dispatch_attempts_spent']==1 and actual['new_dispatch_remaining']==0 and actual['retry_or_extension_allowed'] is False and actual['browser_profile_effects']=='NOT_INSPECTED'
value=dict(schema='A24ControlledBodyActualIndependentStaticChecks/v1',at=datetime.now(timezone.utc).isoformat(),
    result='PASS_BOUNDED_ACQUISITION_RECORDS_AND_RELEASE_ONLY' if all(checks.values()) else 'REVIEW_INCOMPLETE_PRESERVE_FIRST_MISMATCH',
    checks=checks,held_identities=held_summary,book_original='NOT_RETAINED_LENGTH_HASH_OBSERVATION_ONLY',
    retained_body_snapshot_metadata=[{k:r[k] for k in ('slot','bytes','sha256')} for r in reads[1:]],
    private_current_refs=16,private_streams_and_script_decoded=False,private_provenance_parsed_in_memory_only=True,
    schema_body_identity_or_write_qualification=False,product_tests=0,real_resources=0,captured_script_execution=0,
    old_code_model_content_history_review_repeated=False,active_author_reads=False)
with (OUT/'static-checks.json').open('xb') as h:h.write((json.dumps(value,indent=2)+'\n').encode())
print(json.dumps({'result':value['result'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v],'tests':0,'real_resources':0}))
