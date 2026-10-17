# -*- coding: utf-8 -*-
"""Future reproduction in a NEW case only. Exits1 when required positive fails.

Not run during archive verification; does not reuse/reset any existing scene.
"""
import argparse,json,re,traceback
from owned_process import OUT,OWN,make,cli,inspect,write
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case-id',required=True);args=p.parse_args()
assert re.fullmatch('[a-z0-9][a-z0-9-]{0,60}',args.case_id)
case=OUT/'cases'/args.case_id
assert not case.exists(),'Never reset or reuse an existing state directory.'
code=1
try:
 case,common,init=make(args.case_id)
 crash=cli(case,'03-before-intent-exit',{**common,'operation':'run','fault_point':'BEFORE_INTENT_COMMIT'})
 assert crash['exit_code']==90
 before=inspect(case,'04-independent-before')
 assert not before['runtime']['tables']['intents'] and not before['runtime']['tables']['permits']
 assert before['independent']['target_effect_count']==0
 actual=cli(case,'05-dedicated-readonly',{**common,'operation':'tail-absence','action_id':init['action_ids'][0]})
 after=inspect(case,'06-independent-after')
 record={'required_positive_success':actual['exit_code']==0,'actual':actual['parsed_json'][-1],
  'actual_exit_code':actual['exit_code'],'target_effects_before':before['independent']['target_effect_count'],
  'target_effects_after':after['independent']['target_effect_count'],'prohibited_field_reset':'NOT_EXECUTED'}
 write(case/'independent-result.json',record);print(json.dumps(record),flush=True)
 code=0 if record['required_positive_success'] else 1
except BaseException as e:
 if case.exists():write(case/'reproduction-tool-error.json',{'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()})
 raise
finally:
 for child in OWN:
  if child.poll() is None:child.kill();child.wait(timeout=10)
 if case.exists():write(case/'process-release.json',{'pids':[c.pid for c in OWN],'remaining_owned_direct_processes':sum(c.poll() is None for c in OWN),
  'job_accounting':'each completion records bounded owned descendant release','other_processes_signalled':0})
raise SystemExit(code)
