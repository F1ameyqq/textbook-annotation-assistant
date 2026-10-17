"""Final R2 document/input preservation checks and complete evidence manifest."""
import ast,hashlib,io,json,os,re,subprocess,sys,tarfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1];REPORT=ROOT/'docs/tasks/A04-coordinate-R2-review-report.md'
STAGE=ROOT/'.local/stages/A04-review/coordinate-R2';FROZEN=STAGE/'frozen source with spaces'
AUTHOR=Path('C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800')
checks=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def entry(p):
    b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b)}
def check(name,ok,detail):
    assert ok,(name,detail);checks.append({'name':name,'status':'PASS','detail':detail})
snapshot=read(OUT/'snapshot-check.json');verdict=read(OUT/'review-verdict.json');release=read(OUT/'self-release.json')
check('fixed_workflow_and_handoff',snapshot['workflow_commit']=='e7ff892776f53636fcddfe136d1659204c4ff738' and
 sha((OUT/'inputs/workflow/docs/tasks/A04-coordinate-R2-review-handoff.md').read_bytes())=='48c6cb8d41c3598c3fa10f438da0da9d00486c133bc4e97a161ed42518b8d468',snapshot['workflow_commit'])
check('raw_manifest_verified',snapshot['raw_manifest_entries_verified']==158 and not snapshot['disk_variants'],158)
check('prior_execution_preserved',sum(x['entries_unchanged'] for x in snapshot['old_execution'])==148,snapshot['old_execution'])
frozen=read(OUT/'inputs/frozen-tree-manifest.json');supplement=read(OUT/'inputs/history-supplement-manifest.json')
for name,inventory in [('frozen',frozen),('history',supplement)]:
    check('input_bytes_unchanged:'+name,all(sha((FROZEN/e['path']).read_bytes())==e['sha256'] and (FROZEN/e['path']).stat().st_size==e['bytes'] for e in inventory['files']),len(inventory['files']))
check('harness_bootstrap_separate',sha((FROZEN/'src/sitecustomize.py').read_bytes())==sha((OUT/'scripts/offline_guard.py').read_bytes()) and all(e['path']!='src/sitecustomize.py' for e in frozen['files']),sha((OUT/'scripts/offline_guard.py').read_bytes()))
for archive in OUT.glob('inputs/*.tar.gz'):
    with tarfile.open(fileobj=io.BytesIO(archive.read_bytes()),mode='r:gz') as t:names=[m.name for m in t.getmembers() if m.isfile()]
    forbidden=[n for n in names if '.local/' in n or '.git/' in n or '/browser-profiles/' in n or n.endswith(('.mp4','.webm','.har','/usense-login.json'))]
    check('private_media_exclusions:'+archive.name,not forbidden,{'files':len(names),'forbidden':forbidden})
for parent,count in [('docs/evidence/A04/review',5),('docs/evidence/A04/review/coordinate-R1',227)]:
    old=read(ROOT/parent/'sha256-manifest.json')
    check('old_review_preserved:'+parent,len(old['files'])==count and all(entry(ROOT/e['path'])==e for e in old['files']),count)
check('prior_reports_and_manifests_unchanged',all(entry(ROOT/e['path'])==e for e in snapshot['prior_review_files']),len(snapshot['prior_review_files']))
head=subprocess.check_output(['git','-C',str(AUTHOR),'rev-parse','HEAD']).decode().strip()
status=subprocess.check_output(['git','-c','core.longpaths=true','-C',str(AUTHOR),'status','--porcelain']).decode()
check('executor_still_frozen_and_clean',head==snapshot['target_commit'] and not status,{'head':head,'status':status})
minimal=read(OUT/'minimal-repro/result.json');diagnostic=read(OUT/'pixel-diagnostics-cases/short-row-observation.json')
check('defect_at_public_boundary',minimal['defect_reproduced'] and minimal['public_cli_returncode']==0 and minimal['public_loader_accepted'],minimal)
row=diagnostic['independent_row_check']
check('row_integrity_independently_incomplete',row['chunk_CRCs_valid'] and row['zlib_decompression_completed'] and row['actual_scanline_bytes']==112 and row['expected_scanline_bytes']==3248,row)
check('second_decoder_rejects',diagnostic['decoders']['opencv_full_decode']=='REJECTED' and diagnostic['decoders']['pillow_full_load']=='PASS',diagnostic['decoders'])
check('reported_decisions_do_not_accept_A04',verdict['R2_offline']=='REWORK' and verdict['whole_A04']=='BLOCKED' and not verdict['integration_or_dependency_release'],{'R2':verdict['R2_offline'],'A04':verdict['whole_A04']})
check('real_six_not_run',len(verdict['real_scenarios'])==6 and all(v=='BLOCKED_NOT_RUN' for v in verdict['real_scenarios'].values()),verdict['real_scenarios'])
check('six_handoff_clauses_accounted',sorted(x['clause'] for x in verdict['handoff_clause_matrix'])==list(range(1,7)),verdict['handoff_clause_matrix'])
check('raw_failure_counts_preserved',verdict['raw_independent_results']=={'initial':{'PASS':11,'FAIL':4},'targeted':{'PASS':3,'FAIL':1}},verdict['raw_independent_results'])
check('corrected_unique_regression_counts',verdict['regression_unique_results']=={'A04':{'PASS':151,'SKIPPED':1},'contracts':{'PASS':69,'SKIPPED':1}},verdict['regression_unique_results'])
check('only_own_pids_observed_and_exited',release['all_recorded_workers_exited'] and len(release['worker_pid_observations'])==35 and all(not p['running'] for p in release['worker_pid_observations']),35)
check('guard_records_exited',len(release['guard_exit_records'])==30,30)
check('no_browser_profile_network_model',not release['browser_started'] and not release['actual_authorized_profile_opened_or_inspected'] and not release['authorized_credentials_read'] and release['network_or_platform_requests']==release['model_calls']==0,release['inspection_scope'])
check('no_own_test_lease_left',not list(STAGE.rglob('.a04-readonly.lease')),'Own stage only; authorized profile not inspected')
pending={OUT/'closure-checks.json',OUT/'sha256-manifest.json'};links=[]
for doc in [REPORT,OUT/'README.md']:
    text=doc.read_text(encoding='utf-8')
    check('whitespace:'+doc.name,all(s==s.rstrip() for s in text.splitlines()),len(text.splitlines()))
    for target in re.findall(r'\]\(([^)]+)\)',text):
        path=(doc.parent/target).resolve();check('link:'+doc.name+':'+target,path.exists() or path in pending,str(path.relative_to(ROOT)))
        links.append({'source':doc.relative_to(ROOT).as_posix(),'target':target})
json_count=0
for p in OUT.rglob('*.json'):read(p);json_count+=1
check('evidence_json_parse',True,json_count)
python_files=list((OUT/'scripts').glob('*.py'))+list((OUT/'harness-notes').glob('*.py'))
for p in python_files:ast.parse(p.read_text(encoding='utf-8'))
check('review_scripts_parse',True,len(python_files))
files_for_ignore=[p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file()]+[REPORT.relative_to(ROOT).as_posix()]
ignored=subprocess.run(['git','-C',str(ROOT),'check-ignore','--stdin'],input='\n'.join(files_for_ignore)+'\n',text=True,capture_output=True)
assert ignored.returncode in (0,1)
save(OUT/'closure-checks.json',{'at':datetime.now(timezone.utc).isoformat(),'checks':checks,'links':links,
 'R2_offline':'REWORK','whole_A04':'BLOCKED','open_finding':'A04-CR2-01',
 'ignored_files_included_in_manifest':ignored.stdout.splitlines(),'no_files_staged_or_committed':True,
 'executor_frozen':True,'product_contract_dependencies_or_state_modified':False,
 'notes':['Copied workflow/source documents are exact inputs; only new report and evidence README link checks apply.',
 'Initial audit/harness errors and original independent failures preserved; corrected interpretation in review-verdict.json.',
 'D01 installation acceptance is coordinator-owned and separately integrated; not rerun or downgraded by this task.',
 'No periodic polling, messages to others, browser/profile/network/model actions, integration or dependency release.']})
files=[REPORT]+[p for p in sorted(OUT.rglob('*')) if p.is_file() and p!=OUT/'sha256-manifest.json']
save(OUT/'sha256-manifest.json',{'algorithm':'sha256','path_base':'D:/1800 repository root',
 'target_commit':snapshot['target_commit'],'review_workflow_commit':snapshot['workflow_commit'],
 'R2_offline':'REWORK','whole_A04':'BLOCKED','report_included':True,'self_excluded':True,
 'files':[entry(p) for p in files]})
manifest=read(OUT/'sha256-manifest.json')
assert all(entry(ROOT/e['path'])==e for e in manifest['files'])
assert all((ROOT/x['source']).parent.joinpath(x['target']).resolve().exists() for x in links)
print(json.dumps({'R2_offline':'REWORK','whole_A04':'BLOCKED','checks_passed':len(checks),
 'manifest_entries':len(files),'manifest_bytes':sum(e['bytes'] for e in manifest['files']),
 'manifest_sha256':sha((OUT/'sha256-manifest.json').read_bytes()),
 'report_sha256':sha(REPORT.read_bytes()),'self_recorded_workers_exited':35},ensure_ascii=False))
