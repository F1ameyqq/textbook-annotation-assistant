"""Finalize static R2 design review and verify exact inputs/old evidence unchanged."""
import argparse,hashlib,json,os,re,subprocess
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P1-R2';REPORT=ROOT/'docs/tasks/A03-P1-R2-review-report.md'
COMMIT='940a5de33a24b1a3a9ded6e69ade1dd0609ed83a';DESIGN='a250a76dc0b3f13b9dee3bcd2c3d7414032b9768'
BASE='ca4fba4f505467228a8164c3999e0cecc54ffc4e';STAGE=ROOT/'.local/stages/A03-review-P1-R2'/COMMIT
EXEC=Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800');MANIFEST=OUT/'sha256-manifest.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def load(p):return json.loads(p.read_bytes())
def write(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def git(*args):
 p=subprocess.run(['git',*args],cwd=ROOT,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'},capture_output=True,timeout=30)
 assert p.returncode==0,(args,p.returncode,p.stderr.decode('utf-8','replace'));return p.stdout.decode('utf-8','replace').strip()
def verify_inputs():
 idx=load(OUT/'input-index.json');paths=set()
 for x in idx['files']:
  if not x['exported']:continue
  p=(STAGE/x['path']).resolve();assert p.is_relative_to(STAGE);b=p.read_bytes()
  assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path'];paths.add(x['path'])
 actual={p.relative_to(STAGE).as_posix() for p in STAGE.rglob('*') if p.is_file()}
 assert actual==paths,{'extra':sorted(actual-paths),'missing':sorted(paths-actual)}
 for x in idx['protected_old_review_files']:
  b=(ROOT/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
 portable=load(OUT/'portable-check.json')
 for x in portable['input_files']:
  b=(OUT/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
 return len(paths),len(idx['protected_old_review_files'])
def verify_only():
 m=load(MANIFEST);listed=set()
 for x in m['files']:
  p=(ROOT/x['path']).resolve();assert p==REPORT or p.is_relative_to(OUT)
  b=p.read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path'];listed.add(rel(p))
 actual={rel(p) for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST}|{rel(REPORT)}
 assert actual==listed,{'extra':sorted(actual-listed),'missing':sorted(listed-actual)}
 n,protected=verify_inputs();assert m['conclusion']=='P1_DESIGN_ACCEPTED'
 print(json.dumps({'result':'R2_REVIEW_ARCHIVE_VERIFIED','conclusion':m['conclusion'],
  'manifest_files':len(listed),'bounded_git_inputs_unchanged':n,'protected_old_review_files':protected,
  'runtime_or_recovery':'NOT_EXECUTED','p2_authorized':False}))
def create():
 assert not MANIFEST.exists(),'preserve archive; use --verify-only'
 n,protected=verify_inputs();now=datetime.now(timezone(timedelta(hours=8))).isoformat()
 head=git('-C',str(EXEC),'rev-parse','HEAD');status=git('-C',str(EXEC),'status','--porcelain=v1','--untracked-files=all')
 assert head==COMMIT and not status
 assert not git('diff','--diff-filter=DMRTUXB','--name-only',BASE,COMMIT)
 assert not git('diff','--name-only',DESIGN,COMMIT,'--','examples/a03/P1-R2','docs/a03-recovery-contract-v1-r2-proposal.md')
 a=load(OUT/'author-reproduction/results.json');assert len(a['commands'])==6 and all(x['exit_code']==0 for x in a['commands'])
 design=a['commands'][0]['parsed'];assert design['case_count']==72 and design['static_expectations_match']
 assert all(x['semantic_actual']=='NOT_EXECUTED' for x in design['cases'])
 portable=load(OUT/'portable-check.json');assert portable['exit_code']==0 and portable['formal_package_files']==224
 mapping=load(OUT/'mapping-agent/mapping-summary.json');assert not mapping['mapping_failures']
 assert mapping['byte_equal_count']==54 and mapping['byte_changed_count']==15 and mapping['api_signatures_unchanged']
 neighbor=load(OUT/'mapping-agent/neighbors-results.json');assert neighbor['all_acceptance_matches']
 triggers=load(OUT/'mapping-agent/trigger-resource-results.json');assert triggers['all_15_primary_checks_pass'] and triggers['unchanged_case_resources_equal']
 bindings=load(OUT/'bindings-agent/independent-results-final.json');assert not bindings['positive_failures']
 for c in bindings['cases'].values():assert not c['closure']['issues'] and not c['bindings']['issues']
 prefix=load(OUT/'prefix-agent/independent-results.json');assert prefix['final_commit']==COMMIT
 diff=load(OUT/'diff-check-results.json');assert [r['exit_code'] for r in diff['commands']]==[2,0]
 text=REPORT.read_text(encoding='utf-8');assert '结论：**P1_DESIGN_ACCEPTED**' in text
 assert all(not line.endswith((' ','\t')) for line in text.splitlines())
 links=[]
 pending={OUT/'final-verification.json',OUT/'scope-declaration.json',MANIFEST}
 for label,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',text):
  p=(REPORT.parent/target.split('#',1)[0]).resolve()
  assert p.is_relative_to(ROOT) and (p.is_file() or p in pending),target
  links.append({'label':label,'target':target})
 write(OUT/'scope-declaration.json',{'captured_at':now,'conclusion':'P1_DESIGN_ACCEPTED','final_commit':COMMIT,'design_commit':DESIGN,
  'writes':[rel(REPORT),rel(OUT)+'/',str(STAGE)],'browser_network_platform_credentials_browser_profile_ocr_business_model_api':0,
  'paid_calls_and_model_service_cost':0,'real_quality_actual_model_cost':'NOT_RUN','candidate_profile_is_schema_metadata':True,
  'runtime_database_or_recovery_implementation_or_effects':False,'p2_started':False,'i01_released':False,
  'new_chats_b_tasks_or_executor_b_other_thread_messages':0,'code_contract_dependency_state_changes_commit_integration_push':False,
  'static_agents':[{'name':x,'status':'COMPLETED'} for x in ('r2_prefix_chain','r2_bindings','r2_mapping_neighbors')],
  'background_processes_created':0,'other_processes_terminated':0,'remaining_owned_background_os_processes':0,
  'release_basis':'bounded synchronous tool exits and completed static helper turns; no OS-wide process scan',
  'executor_release_basis':'frozen author report and coordinator completed handoff; not independently OS-scanned',
  'inherited_author_policy_denial':'preserved byte copy, not a current reviewer operation or permission request',
  'no_destruction_or_global_settings_change':True,'B_confirmation':'NOT_RECEIVED'})
 write(OUT/'final-verification.json',{'captured_at':now,'conclusion':'P1_DESIGN_ACCEPTED','final_commit':COMMIT,'design_commit':DESIGN,
  'bounded_export_unchanged':n,'all_added_files_Git_manifest_verified':787,'execution_manifest_entries':786,
  'old_git_paths_blobs_preserved':8923,'old_review_files_unchanged':protected,'executor_head':head,'executor_porcelain':status,
  'formal_design_unchanged_after_design_commit':True,'author_static_checks_exit_codes':[x['exit_code'] for x in a['commands']],
  'static_case_count':72,'runtime_semantic_actuals':'ALL_NOT_EXECUTED','original_case_mapping':69,'byte_exact':54,'derived':15,
  'prefix_positive_chain':'13->14; 8->9->10->11 with exact original obligation terminal suffix',
  'main_event14':'independently reconstructed for static hash equality, not an actual commit',
  'independent_resource_positive_cases':4,'candidate_profile_schema_pins':7,'portable_formal_files':224,
  'author_history_files_selected':portable['history_files_selected'],'portable_exit_code':0,
  'whitespace_exit_codes':[2,0],'raw_CRLF_bytes_preserved':True,'global_config_changed':False,
  'report_links':links,'full_JSON_Schema_standard_validation':'NOT_RUN; finite subset only',
  'P2_all_runtime_functionality':'NOT_RUN','p2_requires_separate_coordinator_approval':True,'i01_released':False})
 with (OUT/'finalization.log').open('x',encoding='utf-8',newline='\n') as f:
  f.write('conclusion=P1_DESIGN_ACCEPTED\nruntime_actual=NOT_EXECUTED\np2_authorized=false\n')
  f.write(json.dumps({'bounded_inputs':n,'protected_old_files':protected,'links':len(links),
   'author_exit_codes':[0]*6,'portable_exit':0,'diff_check_exits':[2,0]})+'\n')
 files=sorted([REPORT,*[p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST]],key=rel)
 p=subprocess.run(['git','check-ignore','--stdin','-z'],cwd=ROOT,
  input=('\0'.join(rel(p) for p in files)+'\0').encode(),capture_output=True,timeout=30,
  env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
 assert p.returncode in (0,1)
 write(MANIFEST,{'format_version':'a03-p1-r2-independent-review-sha256-1','captured_at':now,'conclusion':'P1_DESIGN_ACCEPTED',
  'final_commit':COMMIT,'design_commit':DESIGN,'scope':'frozen P1 static design only','self_excluded':rel(MANIFEST),
  'excluded_owned_files':[],'git_ignored_but_included':sorted(x.decode() for x in p.stdout.split(b'\0') if x),
  'not_copied_author_history':'intermediate data snapshots retained in exact Git and full added-file byte index, not duplicate review trees',
  'input_index':rel(OUT/'input-index.json'),'files':[{'path':rel(f),'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())} for f in files]})
 verify_only()
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
 verify_only() if args.verify_only else create()
