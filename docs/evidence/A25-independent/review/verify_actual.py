"""Static verification of the frozen, exhausted capture and owned release."""
import hashlib,json
from datetime import datetime
from pathlib import Path
ROOT=Path('D:/1800/.local/stages/a25-independent-20261023/review-initial-20261023')
PUB=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def main():
 p=ROOT/'private';run=p/'runs/usense-readonly-20261023-040635-f9e62810'
 read=lambda x:json.loads(x.read_bytes())
 cfgraw=(p/'configs/current-source-01.json').read_bytes();cfg=json.loads(cfgraw);summary=read(run/'capture-summary.json');release=read(run/'release.json');claim=read(run/'claim.json');holder=read(p/'evidence/current-source-capture-01.process.json');launch=read(p/'capture-launch-once.json');before=read(p/'authority-before-capture.raw.json');after=read(p/'authority.json')
 assert sha(cfgraw)==summary['config_sha256']==release['config_sha256']==launch['config_sha256']==claim['config_sha256']
 package=ROOT/'snapshot/src/annotation/runtime/usense_live'
 members=[{'path':x.name,'sha256':sha(x.read_bytes())} for x in sorted(package.glob('*.py'))]
 implementation=sha(canonical(members));assert implementation==cfg['implementation_sha256']==launch['implementation_sha256']
 assert sha((p/'authority-before-capture.raw.json').read_bytes())==launch['authority_original_sha256']
 assert before['initial_readonly_capture']['spent']==0 and after['initial_readonly_capture']['spent']==1
 assert launch['attempt']==launch['spent']==1 and launch['remaining']==0 and launch['retry_allowed'] is False and launch['write_attempts_authorized_for_this_launch']==0
 start=datetime.fromisoformat(holder['started_at']);end=datetime.fromisoformat(holder['finished_at'])
 assert datetime.fromisoformat(cfg['not_before'])<=start<end<=datetime.fromisoformat(cfg['expires_at'])
 assert (datetime.fromisoformat(cfg['expires_at'])-datetime.fromisoformat(cfg['not_before'])).total_seconds()<=900
 assert cfg['operation']=='READONLY_CAPTURE' and cfg['book_id']=='46007447' and len(cfg['allowed_get'])==41
 assert cfg['static_get']=={'max_requests':0,'mode':'DISABLED'} and cfg['tls']['mode']=='USER_APPROVED_EXACT_CERT'
 assert summary['status']=='CAPTURE_FAILED_NO_RETRY' and summary['error']=={'type':'SSLEOFError','code':'CAPTURE_ERROR'} and summary['captures']=={} and summary['save_attempts']==0 and summary['release'] is None
 assert read(run/'network-events.json')==[]
 stdout=(p/'evidence/current-source-capture-01.stdout').read_bytes();stderr=(p/'evidence/current-source-capture-01.stderr').read_bytes()
 assert len(stdout)==holder['stdout']['bytes'] and sha(stdout)==holder['stdout']['sha256'] and json.loads(stdout)==summary
 assert len(stderr)==holder['stderr']['bytes']==0 and sha(stderr)==holder['stderr']['sha256']
 assert release['context_closed'] is True and release['runtime_stopped'] is True and release['pending_callbacks']==0 and release['errors']==[] and release['context_runtime_release_confirmed'] is True
 assert release['automatic_login_performed'] is False and release['automatic_retry_allowed'] is False and release['save_attempts']==0
 assert holder['job_assigned_before_resume'] is True and holder['resumed'] is True and holder['exit_code']==2
 assert holder['job_active_processes_after']==0 and holder['launcher_exit_signaled'] is True and holder['errors']==[]
 assert all(holder[k] is True for k in ['thread_handle_closed','process_handle_closed','job_handle_closed','owned_os_release_confirmed'])
 assert len(holder['observed_processes'])==2 and len({v['pid'] for v in holder['observed_processes']})==2
 assert all(v['creation_filetime']>0 and v['image'] and v['exit_signaled'] is True and v['handle_closed'] is True for v in holder['observed_processes'])
 for name in ['profile-exclusivity-prelive-01.json','profile-exclusivity-postlive-01.json']:
  v=read(p/'evidence'/name);assert v['matchingProcesses']==[] and v['lockNamesPresent']==[]
 prelive=read(p/'evidence/prelive-frozen-implementation.json');differences=[]
 for name,h in prelive['files'].items():
  raw=(ROOT/'snapshot'/Path(name)).read_bytes()
  if sha(raw)!=h:differences.append(name.replace('\\','/'))
 assert differences==['tools/run_usense_reviewed_batch.py']
 initial=(p/'evidence/configure.stderr').read_bytes();assert len(initial)==1371 and sha(initial)=='6cf231091eb51eb51542f57bcb6ea11e15279c696e612688e3ab2d48483fbfed'
 out={'schema':'A25IndependentStaticActualReview/v1','result':'ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY','actual_error':'SSLEOFError','root_cause':'UNKNOWN','full_traceback':'NOT_RETAINED','capture_responses':0,'browser_context_created':False,'playwright_runtime_started':False,'context_runtime_claim_source':'separate release.json plus static before-runtime TLS call path; original capture-summary release remains null','owned_process_ids':[v['pid'] for v in holder['observed_processes']],'held_processes_signaled':2,'job_active_processes_after':0,'budget':{'spent':1,'remaining':0,'retry_allowed':False},'save_attempts':0,'implementation_sha256':implementation,'postlive_source_difference_from_prelive':differences,'runtime_entry_and_all_package_python_unchanged':True,'five_question_source_review_plan_save_readback_export':'NOT_RUN','acceptance_limit':'Recorded exhausted failure and exact owned release only; no current source, credentials, root cause, save or live eligibility claim','reviewer_live_calls':0}
 with (PUB/'actual-review.json').open('xb') as f:f.write((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
 print(json.dumps({'result':out['result'],'root_cause':'UNKNOWN','business_responses':0,'held_processes':2,'budget_remaining':0}))
if __name__=='__main__':main()
