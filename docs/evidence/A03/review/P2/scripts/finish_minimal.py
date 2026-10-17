# -*- coding: utf-8 -*-
"""Continue the preserved no-intent scene after a reviewer release-check error."""
import json,traceback
from owned_process import OUT,OWN,cli,inspect,write
case=OUT/'cases/no-intent-absence'
def load(p):return json.loads(p.read_bytes())
results=[load(OUT/'cases/normal-control/independent-result.json')]
try:
 # The completed stdlib read succeeded; its outer driver stopped before this
 # dedicated API call. Reuse original inputs and state without recreating them.
 before=load(case/'commands/04-independent-before/completion.json')['parsed_json'][-1]
 init=load(case/'commands/02-init/completion.json')['parsed_json'][-1]['result']
 request=load(case/'commands/02-init/request.json')
 common={k:request[k] for k in ('anchor_path','expected_ledger_id','expected_target_store_id')}
 common['registration_id']=init['registration_id']
 actions=before['runtime']['tables']['actions']
 assert actions and all(a['intent'] is None and a['fact'] is None for a in actions)
 assert not before['runtime']['tables']['intents'] and not before['runtime']['tables']['permits']
 assert before['independent']['target_effect_count']==0
 accepted=[e for e in before['independent']['all_runtime_events'] if e['event']=='PLAN_ACCEPTED']
 assert len(accepted)==1 and accepted[0]['sequence']==3
 attempted=cli(case,'05-dedicated-readonly',{**common,'operation':'tail-absence','action_id':init['action_ids'][0]})
 actual=attempted['parsed_json'][-1]
 after=inspect(case,'06-independent-after')
 assert after['independent']['target_effect_count']==0
 assert before['independent']['business_sha256']==after['independent']['business_sha256']
 assert not after['runtime']['tables']['intents'] and not after['runtime']['tables']['permits']
 assert all(x['fact'] is None for x in after['runtime']['tables']['actions'])
 assert any(p['status']=='INTERRUPTED' for p in after['runtime']['tables']['plans'])
 result={'id':'A03-P2-UNATTEMPTED-01','result':'FAIL_REQUIRED_POSITIVE_PATH',
  'expected':'dedicated entry performs two new complete reads and can commit sufficient ABSENT for first reserved never-called action, with no business effect/intent/obligation/permit',
  'actual_exit_code':attempted['exit_code'],'actual':actual,'accepted_plan_event_sequence':3,
  'reserved_actions':len(actions),'before_effects':0,'after_effects':0,
  'target_reads_before':before['independent']['target_read_sequence'],'target_reads_after':after['independent']['target_read_sequence'],
  'unattempted_fact_events':sum(e['event']=='UNATTEMPTED_ABSENCE_COMMITTED' for e in after['independent']['all_runtime_events']),
  'input_preconditions':'genuine atomic acceptance/permanent reservations; BEFORE_INTENT_COMMIT exit90; fixed current source/scope/target; first action no predecessor; CLI obtains current ACTIVE claim and marks plan INTERRUPTED before dedicated API',
  'limits':'No two-read fact was actually attempted because the entry is an unconditional contract-gap stub. This is not an APPLIED/B UNKNOWN/C partial-path functional pass. Full matrix not run.',
  'review_tool_failure_preserved':'run_review.attempt-01.py and review-run-failure.json; original case was continued, not regenerated',
  'prohibited_authorization_field_reset':'NOT_EXECUTED'}
 assert attempted['exit_code']==2 and actual['code']=='EVENT_PREFIX_CONTRACT_GAP'
 write(case/'independent-result.json',result);results.append(result)
 write(OUT/'independent-results.json',{'conclusion':'REWORK','cases':results,'other_functional_checks':'NOT_RUN_IN_THIS_REVIEW'})
 print(json.dumps({'result':'BOUNDED_REVIEW_COMPLETE','conclusion':'REWORK','actual_code':actual['code'],'target_effects':0}),flush=True)
except BaseException as e:
 write(OUT/'review-run02-failure.json',{'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()})
 raise
finally:
 for p in OWN:
  if p.poll() is None:p.kill();p.wait(timeout=10)
 write(OUT/'process-release-run02.json',{'owned_direct_processes':[{'pid':p.pid,'exit_code':p.returncode,'alive':p.poll() is None} for p in OWN],
  'remaining_owned_direct_processes':sum(p.poll() is None for p in OWN),'descendants':'per-command Windows Job Object accounting; wait up to2s for owned descendant release, kill-on-close as final containment',
  'other_processes_signalled':0,'prohibited_field_reset':'NOT_EXECUTED'})
