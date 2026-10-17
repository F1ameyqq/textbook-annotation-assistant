"""Finalize and read-only verify P1-R1 review evidence, never business behavior."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path('D:/1800')
OUT=ROOT/'docs/evidence/A03/review/P1-R1'
REPORT=ROOT/'docs/tasks/A03-P1-R1-review-report.md'
COMMIT='ca4fba4f505467228a8164c3999e0cecc54ffc4e'
DESIGN='095ed4aa18a56100ce3aabc4a0d6885ad37ab520'
STAGE=ROOT/'.local/stages/A03-review-P1-R1'/COMMIT
EXEC=Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
MANIFEST=OUT/'sha256-manifest.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def rel(p):return p.relative_to(ROOT).as_posix()
def write(p,x):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def git(*args):
 p=subprocess.run(['git',*args],cwd=ROOT,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'},capture_output=True,timeout=30)
 assert p.returncode==0,(args,p.returncode,p.stderr.decode('utf-8','replace'))
 return p.stdout.decode('utf-8','replace').strip()
def check_inputs():
 export=load(OUT/'export-manifest.json'); seen=set()
 for x in export['files']:
  p=(STAGE/x['path']).resolve();assert p.is_relative_to(STAGE)
  raw=p.read_bytes();assert len(raw)==x['bytes'] and sha(raw)==x['sha256'],x['path'];seen.add(x['path'])
 actual={p.relative_to(STAGE).as_posix() for p in STAGE.rglob('*') if p.is_file()}
 assert seen==actual,{'extra':sorted(actual-seen),'missing':sorted(seen-actual)}
 protected=load(OUT/'freeze-checks.json')['protected_old_review_files']
 for x in protected:
  raw=(ROOT/x['path']).read_bytes();assert len(raw)==x['bytes'] and sha(raw)==x['sha256'],x['path']
 return len(seen),len(protected)
def verify_only():
 m=load(MANIFEST);paths=set()
 for x in m['files']:
  p=(ROOT/x['path']).resolve();assert p==REPORT or p.is_relative_to(OUT)
  raw=p.read_bytes();assert len(raw)==x['bytes'] and sha(raw)==x['sha256'],x['path'];paths.add(rel(p))
 actual={rel(p) for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST}|{rel(REPORT)}
 assert actual==paths,{'extra':sorted(actual-paths),'missing':sorted(paths-actual)}
 n,old=check_inputs()
 assert m['conclusion']=='REWORK'
 print(json.dumps({'result':'REVIEW_ARCHIVE_VERIFIED','conclusion':m['conclusion'],'files':len(paths),
  'frozen_git_inputs_unchanged':n,'protected_old_review_files':old,'functional_recovery':'NOT_EXECUTED'}))
def create():
 assert not MANIFEST.exists(),'preserve final archive; use --verify-only'
 n,old=check_inputs();now=datetime.now(timezone(timedelta(hours=8))).isoformat()
 head=git('-C',str(EXEC),'rev-parse','HEAD')
 status=git('-C',str(EXEC),'status','--porcelain=v1','--untracked-files=all')
 assert head==COMMIT and status==''
 assert git('diff','--name-only',DESIGN,COMMIT,'--','docs/a03-recovery-contract-v1-r1-proposal.md','examples/a03/P1-R1')==''
 author=load(OUT/'author-reproduction/results.json');portable=load(OUT/'portable-check.json')
 assert all(c['returncode']==0 for c in author['commands'])
 assert author['commands'][0]['parsed']['case_count']==69
 assert all(c['semantic_actual']=='NOT_EXECUTED' for c in author['commands'][0]['parsed']['cases'])
 assert portable['returncode']==0 and len(portable['copied_files'])==781
 for x in portable['copied_files']:
  p=OUT/'inputs/frozen-R1'/x['path'];raw=p.read_bytes()
  assert len(raw)==x['bytes'] and sha(raw)==x['sha256'],x['path']
 refs=load(OUT/'ref-agent/resource-audit-summary.json')
 assert refs['all_mapping_checks_pass'] and refs['counterexample_expectations_match']
 assert not refs['author_expected_pass_with_independent_closure_errors']
 mapping=load(OUT/'mapping-agent/audit-results.json')
 assert mapping['summary']['all_mapping_bytes_layers_codes_sources_match']
 assert mapping['summary']['all_case_and_referenced_fact_basis_shape_expectations_match']
 assert mapping['summary']['profile_hashes_match']
 triggers=load(OUT/'mapping-agent/trigger-retention-results.json')
 assert triggers['summary']['core_trigger_cases']==42 and triggers['summary']['core_triggers_retained']==42
 assert triggers['summary']['unclassified_changes']==0
 api=load(OUT/'api-agent/independent-api-static.json')
 assert api['static_positive_field_checks_all_pass']
 assert not api['finding']['contains_required_PLAN_ACCEPTED']
 assert api['finding']['applied_actions_without_DISPATCH_STARTED']
 assert not api['finding']['separate_complete_event_resource_or_summary_marker_found']
 text=REPORT.read_text(encoding='utf-8');assert '结论：**REWORK**' in text
 assert not any(line.endswith((' ','\t')) for line in text.splitlines())
 links=[]
 for label,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',text):
  p=(REPORT.parent/target.split('#',1)[0]).resolve()
  assert p.is_relative_to(ROOT) and (p.is_file() or p in (OUT/'final-verification.json',OUT/'scope-declaration.json',MANIFEST)),target
  links.append({'label':label,'target':target})
 write(OUT/'scope-declaration.json',{'captured_at':now,'conclusion':'REWORK','reviewed_commit':COMMIT,'design_commit':DESIGN,
  'owned_write_scope':[rel(REPORT),rel(OUT)+'/',str(STAGE)],
  'network_browser_platform_credentials_browser_profile_ocr_model_service_api_paid_calls_book_submissions':0,
  'candidate_schema_profile_json_read':True,'candidate_profile_is_not_browser_profile':True,
  'model_service_cost':0,'real_quality_and_actual_model_cost':'NOT_RUN',
  'new_chats_b_tasks_executor_or_b_messages':0,'integration_push_commits_or_coordination_state_changes':False,
  'p2_started':False,'i01_released':False,'b_confirmation':'NOT_RECEIVED',
  'candidate_api_business_database_or_recovery_execution':False,
  'static_review_agents':[{'name':x,'status':'COMPLETED'} for x in ('r1_api_semantics','r1_resource_closure','r1_mapping_profile')],
  'tools':'bounded synchronous Git/PowerShell/Python static commands only; no detached processes/services',
  'background_processes_started':0,'other_processes_terminated':0,'remaining_owned_background_os_processes':0,
  'release_evidence':'synchronous commands exited and static subagent completion; no OS-wide process scan',
  'executor_release':'frozen author declaration and coordinator completed-turn handoff; not independently OS-scanned'})
 write(OUT/'final-verification.json',{'captured_at':now,'conclusion':'REWORK','reviewed_commit':COMMIT,
  'stage_raw_git_files_unchanged':n,'old_git_files_preserved':8142,'protected_old_review_preparation_files_unchanged':old,
  'new_allowed_delivery_files':781,'execution_manifest_entries_verified':780,
  'execution_worktree_head':head,'execution_worktree_porcelain':status,'ignored_execution_files':'NOT_INSPECTED',
  'design_files_unchanged_after_design_commit':True,'author_static_exit_codes':[0,0],'author_cases':69,
  'portable_check_exit_code':0,'portable_frozen_R1_files':781,'all_semantic_results':'NOT_EXECUTED',
  'independent_mapping_cases':42,'independent_core_triggers_retained':42,'unclassified_mapping_changes':0,
  'independent_resource_cases':69,'independent_resource_neighbors':9,
  'full_standards_jsonschema':'NOT_RUN; local assertion subset only',
  'original_findings':{'A03-P1-API-01':'PUBLIC_RULES_CLOSED_WITH_NEW_SUCCESS_FIXTURE_DEFECT',
   'A03-P1-REF-01':'STATIC_REFERENCE_REPAIR_CONFIRMED'},
  'remaining_design_findings':['A03-P1-R1-PREFIX-01'],'report_local_links':links,
  'all_p2_runtime_functionality':'NOT_RUN'})
 with (OUT/'finalization.log').open('x',encoding='utf-8',newline='\n') as f:
  f.write('conclusion=REWORK\nfunctional_recovery=NOT_EXECUTED\n')
  f.write(json.dumps({'frozen_git_inputs_unchanged':n,'protected_old_review_files':old,
   'local_links':len(links),'author_static_exit_codes':[0,0],'portable_exit_code':0,
   'remaining_finding':'A03-P1-R1-PREFIX-01'},ensure_ascii=False)+'\n')
 files=sorted([REPORT,*[p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST]],key=rel)
 p=subprocess.run(['git','check-ignore','--stdin','-z'],cwd=ROOT,
  env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'},input=('\0'.join(rel(p) for p in files)+'\0').encode(),capture_output=True,timeout=30)
 assert p.returncode in (0,1)
 ignored=sorted(x.decode() for x in p.stdout.split(b'\0') if x)
 write(MANIFEST,{'format_version':'a03-p1-r1-independent-review-sha256-1','captured_at':now,
  'conclusion':'REWORK','reviewed_commit':COMMIT,'design_commit':DESIGN,'scope':'P1-R1 static design only',
  'algorithm':'SHA256','self_excluded':rel(MANIFEST),'excluded_owned_files':[],
  'git_ignored_but_included':ignored,'isolated_input_index':rel(OUT/'export-manifest.json'),
  'files':[{'path':rel(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in files]})
 verify_only()
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify-only',action='store_true');a=parser.parse_args()
 verify_only() if a.verify_only else create()
