"""Freeze reviewer artifacts and verify preserved inputs without rerunning tests."""
import hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
PUB=Path(__file__).resolve().parent
STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/review-initial-20261023')
PREP=PUB.parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):
 with path.open('xb') as f:f.write((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def main():
 intake=json.loads((PUB/'intake.json').read_bytes());verified=0
 for entry in intake['inputs']:
  raw=Path(entry['copy']).read_bytes();assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256'];verified+=1
 for cmd in intake['commands']:
  for label in ['stdout','stderr']:
   rec=cmd[label];raw=Path(rec['path']).read_bytes();assert len(raw)==rec['bytes'] and sha(raw)==rec['sha256']
 for line in (PREP/'preparation-files.sha256').read_text(encoding='ascii').splitlines():
  h,name=line.split('  ',1);assert sha((PREP/name).read_bytes())==h
 initial=json.loads((PUB/'test-commands.json').read_bytes());resumed=json.loads((PUB/'resumed-test-commands.json').read_bytes());fixed=json.loads((PUB/'controls-v2-process.json').read_bytes())
 commands=initial['commands']+resumed['commands']+[fixed]
 assert [x['exit_code'] for x in commands]==[1,0,1,0]
 for cmd in commands:
  for label in ['stdout','stderr']:
   rec=cmd[label];raw=Path(rec['path']).read_bytes();assert len(raw)==rec['bytes'] and sha(raw)==rec['sha256']
 actual=json.loads((PUB/'actual-review.json').read_bytes());assert actual['result']=='ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY'
 save(PUB/'result.json',{'schema':'A25IndependentReviewResult/v1','at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'reviewer_thread_id':'01a166e8-3f23-7192-a560-4724adca74b1','coordinator_thread_id':'01a166c5-f93f-76e3-baf4-a3545ccddebd','executor_thread_id':'01a166e7-cfd7-7da2-a76e-bcb612b9646b','model_registration':'gpt-6.1-sol','thinking_registration':'xhigh','base_commit':intake['base'],'product_commit':intake['product'],'final_delivery_commit':intake['final'],'delivery_manifest_sha256':intake['manifest_sha256'],'code_result':'ACCEPTED_OFFLINE_ONLY','actual_result':actual['result'],'scope':'Portable package resolution and finite new stable-manifest batch boundary checks; exhausted actual failure and own release only','source_external_private_verified':[27,3,47],'additional_final_reports_verified':3,'all_input_copies_reverified':verified,'original_preparation_hashes_preserved':True,'test_results':{'initial_final_author_file':{'ran':16,'passed':15,'harness_errors':1,'exit':1},'only_previously_blocked_portable_test':{'ran':1,'passed':1,'exit':0},'independent_fixture_initial':{'ran':1,'fixture_failures':1,'successors_not_run':7,'exit':1},'independent_controls_corrected':{'ran':8,'passed':8,'exit':0},'distinct_final_author_tests_with_passing_evidence':16,'distinct_independent_controls_with_passing_evidence':8,'all_original_errors_preserved':True,'product_changes_for_review':False},'interpreter':{'executable':sys.executable,'version':sys.version},'actual_error':'SSLEOFError','root_cause':'UNKNOWN','full_exception_traceback':'NOT_RETAINED','summary_release':None,'separate_release_and_exact_held_os_release_accepted':True,'business_responses':0,'capture_budget':{'spent':1,'remaining':0,'retry':False},'five_question_stable_real_identity':'NOT_BOUND','source_candidate_review_plan_save_readback_export':'NOT_RUN','old_first_lesson_and_old194_OCR':'NOT_REPLAYED','new_live_activation':False,'blockers':['Exhausted capture cannot be reopened; coordinator must bind a distinct authorized round/config/budget before any further acquisition','No fresh five-target stable identity, complete native baseline or source pages/candidates/reviews','No concrete reviewed five-target save plan or actual preservation/readback/export evidence'],'reviewer_live_platform_profile_model_OCR_operations':0,'author_active_worktree_reads':0,'root_json_AGENTS_or_shared_index_mutations':0,'other_chat_messages_or_new_agents':0,'code_findings_requiring_rework':[],'report':'D:/1800/docs/evidence/A25-independent/review/report.md'})
 records=[]
 for p in sorted(STAGE.rglob('*')):
  if p.is_file():
   raw=p.read_bytes();records.append({'path':str(p),'bytes':len(raw),'sha256':sha(raw)})
 save(PUB/'review-raw-manifest.json',{'schema':'A25IndependentRawArtifacts/v1','source':'Exact-commit copied inputs, Git raw command outputs, preserved original failures, offline reviewer process outputs and guards; no platform recapture','input_manifest_sha256':sha((PUB/'intake.json').read_bytes()),'files':records,'count':len(records)})
 public=[p for p in sorted(PUB.iterdir()) if p.is_file() and p.name!='review-files.sha256']
 content=''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in public)
 with (PUB/'review-files.sha256').open('xb') as f:f.write(content.encode('ascii'))
 print(json.dumps({'code_result':'ACCEPTED_OFFLINE_ONLY','actual_result':actual['result'],'copied_inputs_reverified':verified,'raw_artifact_files':len(records),'public_files_hashed':len(public),'review_manifest_sha256':sha((PUB/'review-files.sha256').read_bytes()),'report_sha256':sha((PUB/'report.md').read_bytes()),'result_sha256':sha((PUB/'result.json').read_bytes())}))
if __name__=='__main__':main()
