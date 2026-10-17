"""R3 archive closure; all mutation limited to the new review evidence."""
import ast,hashlib,io,json,re,subprocess,tarfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1];REPORT=ROOT/'docs/tasks/A04-coordinate-R3-review-report.md'
F=ROOT/'.local/stages/A04-review/coordinate-R3/frozen source with spaces';AUTHOR=Path('C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def entry(p):
    b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'sha256':sha(b),'bytes':len(b)}
checks=[]
def check(name,ok,detail):assert ok,(name,detail);checks.append({'name':name,'status':'PASS','detail':detail})
s=read(OUT/'snapshot-check.json');v=read(OUT/'review-verdict.json');release=read(OUT/'self-release.json');ind=read(OUT/'independent-cases/results.json')
check('fixed_input_identity',s['target_commit']=='6c8137a4fadddc01a47906d564ab3460277c8958' and s['review_workflow_commit']=='d834bf531f95abac7ed30b89b3ca55105fa6f491',s['target_commit'])
check('852_raw_and_disk_checks',s['raw_and_disk_manifest_entries_verified']==852 and not s['disk_variants'],852)
check('853_allowed_paths',len(s['changed_paths'])==853 and not s['out_of_scope'],853)
inventory=read(OUT/'inputs/frozen-tree-manifest.json')
check('frozen_product_inputs_unchanged',all(sha((F/e['path']).read_bytes())==e['sha256'] and (F/e['path']).stat().st_size==e['bytes'] for e in inventory['files']),len(inventory['files']))
check('original_archive_unchanged',sha((OUT/'inputs/frozen-inputs.tar.gz').read_bytes())==inventory['archive_sha256'],inventory['archive_sha256'])
for e in s['workflow_inputs']:
    p=OUT/'inputs/workflow'/e['path'];check('workflow:'+e['path'],sha(p.read_bytes())==e['sha256'],e['sha256'])
for e in s['unchanged_repro_files']:
    p=OUT/'inputs/unchanged-R2-repro'/e['path'];check('unchanged_reproducer:'+e['path'],sha(p.read_bytes())==e['sha256'] and p.stat().st_size==e['bytes'],e['sha256'])
with tarfile.open(fileobj=io.BytesIO((OUT/'inputs/frozen-inputs.tar.gz').read_bytes()),mode='r:gz') as t:
    names=[m.name for m in t.getmembers() if m.isfile()]
forbidden=[p for p in names if '.local/' in p or '.git/' in p or '/browser-profiles/' in p or p.endswith(('.mp4','.webm','.har','/usense-login.json'))]
check('archive_excludes_private_material',not forbidden,{'files':len(names),'forbidden':forbidden})
for old in s['old_review_preservation']:
    p=ROOT/old['path'];m=read(p)
    check('preserved_old_review:'+old['path'],sha(p.read_bytes())==old['sha256'] and all(entry(ROOT/e['path'])==e for e in m['files']),len(m['files']))
check('old_execution_306_preserved',sum(x['entries'] for x in s['old_execution_preservation'])==306,s['old_execution_preservation'])
head=subprocess.check_output(['git','-C',str(AUTHOR),'rev-parse','HEAD']).decode().strip()
status=subprocess.check_output(['git','-c','core.longpaths=true','-C',str(AUTHOR),'status','--porcelain']).decode()
check('author_frozen_and_clean',head==s['target_commit'] and not status,{'head':head,'status':status})
exact=read(OUT/'exact-replay/result.json');reg=read(OUT/'initial/regression-result.json')
check('exact_counterexample_resolved',exact['sha256']=='205543876fb32bb14f003bfeec32279e9fd4886bd1949eee9810999e468969bd' and exact['public_cli_returncode']==2 and not exact['defect_reproduced'] and not (OUT/'exact-replay/output').exists() and not (OUT/'exact-replay/input/evidence').exists(),exact)
check('scoped_regression_70',reg['status']=='PASS' and reg['tests_run']==70 and not reg['errors'] and not reg['failures'],reg)
check('independent_26_pass',ind['passed']==26 and ind['failed']==0 and len(ind['results'])==26,26)
check('seven_independent_layouts',ind['layout_count']==7,7)
check('twenty_python_children_reaped',len(ind['children'])==20 and ind['all_children_reaped'],20)
check('finite_scope_decisions',v['OFFLINE_R3']=='ACCEPTED' and v['A04_OVERALL']=='BLOCKED' and not v['release_downstream_or_integrate'],{'OFFLINE_R3':v['OFFLINE_R3'],'A04_OVERALL':v['A04_OVERALL']})
check('real_six_still_blocked',len(v['real_scenarios'])==6 and all(x=='BLOCKED_NOT_RUN' for x in v['real_scenarios'].values()),v['real_scenarios'])
check('all_five_handoff_clauses',sorted(x['clause'] for x in v['handoff_clauses'])==list(range(1,6)),v['handoff_clauses'])
check('own_27_process_identities_exited',release['recorded_identities']==27 and all(x['original_process_exited'] for x in release['observations']),27)
check('PID_reuse_recognized_not_stopped',sum(x['observation']=='PID_REUSED_LATER_NO_ACTION' for x in release['observations'])==1,release['PID_reuse_policy'])
check('25_guard_exit_records',len(release['guard_exit_records'])==25,25)
check('no_forbidden_actions',release['browser_network_platform_login_profile_credentials_model_book_actions']==0,0)
check('own_stage_no_lease_left',not list(F.parent.rglob('.a04-readonly.lease')),'Own stage only')
check('harness_bootstrap_not_product',sha((F/'src/sitecustomize.py').read_bytes())==sha((OUT/'scripts/offline_guard.py').read_bytes()) and all(e['path']!='src/sitecustomize.py' for e in inventory['files']),sha((F/'src/sitecustomize.py').read_bytes()))
pending={OUT/'closure-checks.json',OUT/'sha256-manifest.json'};links=[]
for doc in [REPORT,OUT/'README.md']:
    text=doc.read_text(encoding='utf-8');check('whitespace:'+doc.name,all(line==line.rstrip() for line in text.splitlines()),len(text.splitlines()))
    for target in re.findall(r'\]\(([^)]+)\)',text):
        p=(doc.parent/target).resolve();check('link:'+doc.name+':'+target,p.exists() or p in pending,str(p.relative_to(ROOT)))
        links.append({'source':doc.relative_to(ROOT).as_posix(),'target':target})
json_files=list(OUT.rglob('*.json'))
for p in json_files:read(p)
check('all_json_evidence_parse',True,len(json_files))
scripts=list((OUT/'scripts').glob('*.py'))+list((OUT/'inputs/unchanged-R2-repro').glob('*.py'))
for p in scripts:ast.parse(p.read_text(encoding='utf-8'))
check('review_scripts_parse',True,len(scripts))
paths=[p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file()]+[REPORT.relative_to(ROOT).as_posix()]
ignored=subprocess.run(['git','-C',str(ROOT),'check-ignore','--stdin'],input='\n'.join(paths)+'\n',text=True,capture_output=True)
assert ignored.returncode in (0,1)
save(OUT/'closure-checks.json',{'at':datetime.now(timezone.utc).isoformat(),'checks':checks,'links':links,
 'OFFLINE_R3':'ACCEPTED','A04_OVERALL':'BLOCKED','ignored_files_included':ignored.stdout.splitlines(),
 'product_contract_dependencies_or_state_modified':False,'stage_commit_merge_push_or_messages':False,
 'scope_limits':['Only fixed R3 offline repair','No full resource stress','No old full matrix rerun','No real R01-R06/S01 acceptance','D01 not reverified'],
 'harness_note':'Initial archive assumed nonexistent optional README; corrected before product run. Old evidence unchanged.',
 'runtime_actions':'Only local Python; Git local-object/integrity metadata tooling; no network/browser/profile/model/book actions'})
files=[REPORT]+[p for p in sorted(OUT.rglob('*')) if p.is_file() and p!=OUT/'sha256-manifest.json']
save(OUT/'sha256-manifest.json',{'algorithm':'sha256','path_base':'D:/1800 repository root','target_commit':s['target_commit'],
 'review_workflow_commit':s['review_workflow_commit'],'OFFLINE_R3':'ACCEPTED','A04_OVERALL':'BLOCKED',
 'self_excluded':True,'report_included':True,'files':[entry(p) for p in files]})
m=read(OUT/'sha256-manifest.json');assert all(entry(ROOT/e['path'])==e for e in m['files'])
assert all((ROOT/x['source']).parent.joinpath(x['target']).resolve().exists() for x in links)
print(json.dumps({'OFFLINE_R3':'ACCEPTED','A04_OVERALL':'BLOCKED','checks':len(checks),'manifest_entries':len(files),
 'manifest_bytes':sum(e['bytes'] for e in m['files']),'manifest_sha256':sha((OUT/'sha256-manifest.json').read_bytes()),
 'report_sha256':sha(REPORT.read_bytes()),'own_process_identities_exited':27},ensure_ascii=False))
