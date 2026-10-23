"""Freeze this delta review; rehash inputs, never rerun product checks."""
import hashlib,json,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
PUB=Path(__file__).resolve().parent;STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/transport-review-20261023')
def sha(b):return hashlib.sha256(b).hexdigest()
def save(path,v):
 with path.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def main():
 intake=json.loads((PUB/'intake.json').read_bytes());n=0
 for e in intake['inputs']:
  raw=Path(e['copy']).read_bytes();assert len(raw)==e['bytes'] and sha(raw)==e['sha256'];n+=1
 for c in intake['commands']:
  assert c['exit_code']==0 and c['env']['GIT_NO_LAZY_FETCH']=='1' and c['argv'][:3]==['git','-c','core.longpaths=true']
  for label in ['stdout','stderr']:
   e=c[label];raw=Path(e['path']).read_bytes();assert len(raw)==e['bytes'] and sha(raw)==e['sha256']
 tests=json.loads((PUB/'test-commands.json').read_bytes());assert [c['exit_code'] for c in tests['records']]==[0,0]
 for c in tests['records']:
  for label in ['stdout','stderr']:
   e=c[label];raw=Path(e['path']).read_bytes();assert len(raw)==e['bytes'] and sha(raw)==e['sha256']
 supplement=json.loads((PUB/'supplement-input.json').read_bytes());raw=Path(supplement['copy']).read_bytes();assert sha(raw)==supplement['sha256'] and len(raw)==supplement['bytes']
 plan=json.loads((PUB/'plan-review.json').read_bytes());assert plan['result']=='ACCEPTED_BOUNDED_READONLY_PLAN_FOR_ROOT_BINDING' and plan['supplement_sha256']==supplement['sha256']
 oldraw=json.loads(Path('D:/1800/.local/stages/a25-independent-20261023/review-initial-20261023/raw-manifest.json').read_bytes());oldn=0
 for group,key in [('source_members','raw_path'),('private_evidence','frozen_path')]:
  for e in oldraw[group]:
   raw=Path(e[key]).read_bytes();assert sha(raw)==e['sha256'] and len(raw)==e['bytes'];oldn+=1
 for line in (PUB.parent/'review/review-files.sha256').read_text(encoding='ascii').splitlines():
  h,name=line.split('  ',1);assert sha((PUB.parent/'review'/name).read_bytes())==h
 result={'schema':'A25IndependentTransportReviewResult/v1','at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'reviewer_thread_id':'01a166e8-3f23-7192-a560-4724adca74b1','coordinator_thread_id':'01a166c5-f93f-76e3-baf4-a3545ccddebd','executor_thread_id':'01a166e7-cfd7-7da2-a76e-bcb612b9646b','parent_commit':intake['parent'],'product_commit':intake['product'],'final_commit':intake['final'],'manifest_sha256':intake['manifest_sha256'],'code_result':'ACCEPTED_OFFLINE_ONLY','specific_plan_result':plan['result'],'plan_sha256':plan['plan_sha256'],'required_supplement_sha256':supplement['sha256'],'implementation_sha256':plan['implementation_sha256'],'current_printed_questions':[1,2,3,4,5],'historical_global_orders_before_Q7_split':[17,18,19,20,21],'native_orders_to_verify':[18,19,20,21,22],'new_source_and_private_verified':[30,23],'additional_final_reports_verified':2,'input_copies_reverified':n,'old_source_and_private_reverified_unchanged':oldn,'old_review_members_unchanged':True,'tests':{'new_transport_and_two_new_batch_cases':{'passed':13,'ran':13,'exit':0,'seconds':1.773},'independent_transport_controls':{'passed':6,'ran':6,'exit':0,'seconds':2.276},'reviewer_helper_failures':0,'old16plus8':'NOT_RERUN','old194_first_lesson_OCR':'NOT_RERUN'},'interpreter':{'executable':sys.executable,'version':sys.version},'real_network_proxy_platform_browser_profile_OCR_model_calls':0,'active_author_worktree_reads':0,'root_dispatch_AGENTS_index_mutations':0,'ledger_directory_created':False,'new_live_activation':False,'old_round':{'spent':1,'remaining':0,'reopened':False,'root_cause':'UNKNOWN'},'historical_image_current_identity':'PENDING_FRESH_JSON_RELATION_VERIFICATION','fresh_source_candidates_save_readback_export':'NOT_RUN','findings_requiring_rework':[],'root_next_action':'Bind exact product/implementation, original plan plus label correction, fresh unique single-attempt authority/config/window/output/launch; recheck original profile exclusive ownership; then original executor may perform the bounded readonly round under current user authorization','allowed_plan':{'contexts':1,'inert_same_origin_navigations':1,'seconds':900,'business_json_gets':40,'transport':plan['proxy'],'save_attempts':0,'login_attempts':0,'new_business_origins':0,'image_downloads':0,'OCR_replays':0},'future_write_gate':'Fresh stable targets, current baseline and historical-source relation review, root-bound ledger reconciliation/initialization and specific five-target candidate/write-plan acceptance remain required','report':'D:/1800/docs/evidence/A25-independent/transport-review/report.md'}
 save(PUB/'result.json',result)
 files=[]
 for p in sorted(STAGE.rglob('*')):
  if p.is_file():
   raw=p.read_bytes();files.append({'path':str(p),'bytes':len(raw),'sha256':sha(raw)})
 save(PUB/'transport-review-raw-manifest.json',{'schema':'A25IndependentTransportRawArtifacts/v1','kind':'exact commit exports, frozen private copies, reviewer raw process outputs, offline guard and current label supplement','files':files,'count':len(files)})
 outputs=[p for p in sorted(PUB.iterdir()) if p.is_file() and p.name!='transport-review-files.sha256']
 with (PUB/'transport-review-files.sha256').open('xb') as f:f.write(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in outputs).encode('ascii'))
 print(json.dumps({'code_result':result['code_result'],'plan_result':result['specific_plan_result'],'input_copies':n,'raw_artifacts':len(files),'public_members':len(outputs),'manifest_sha256':sha((PUB/'transport-review-files.sha256').read_bytes()),'report_sha256':sha((PUB/'report.md').read_bytes()),'result_sha256':sha((PUB/'result.json').read_bytes())}))
if __name__=='__main__':main()
