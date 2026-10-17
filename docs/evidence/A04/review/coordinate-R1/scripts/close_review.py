"""Finalize this review's evidence, without staging or modifying product/state."""
import hashlib,io,json,os,re,subprocess,sys,tarfile
from pathlib import Path
from datetime import datetime,timezone
OUT=Path(__file__).resolve().parents[1];ROOT=Path('D:/1800')
REPORT=ROOT/'docs/tasks/A04-coordinate-R1-review-report.md'
STAGE=ROOT/'.local/stages/A04-review/coordinate-R1';FROZEN=STAGE/'frozen input with spaces'
AUTHOR=Path('C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800')
checks=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(name,ok,detail):
    assert ok,(name,detail)
    checks.append({'name':name,'status':'PASS','detail':detail})
def entry(p):
    b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'sha256':sha(b),'bytes':len(b)}

inventory=json.loads((OUT/'inputs/frozen-tree-manifest.json').read_text(encoding='utf-8'))
check('frozen_raw_inputs_unchanged',all(sha((FROZEN/r['path']).read_bytes())==r['sha256'] for r in inventory['files']),len(inventory['files']))
supplement=json.loads((OUT/'reproduction/contracts-after-input-supplement.json').read_text(encoding='utf-8'))
check('contract_supplement_unchanged',all(sha((FROZEN/r['path']).read_bytes())==r['sha256'] for r in supplement['new_input_files']),3)
check('source_archive_identity',sha((OUT/'inputs/frozen-inputs.tar.gz').read_bytes())==inventory['archive_sha256'],inventory['archive_sha256'])
for archive in OUT.glob('inputs/*.tar.gz'):
    with tarfile.open(fileobj=io.BytesIO(archive.read_bytes()),mode='r:gz') as t:
        names=[m.name for m in t.getmembers() if m.isfile()]
    forbidden=[p for p in names if '.local/' in p or '.git/' in p or p.endswith(('.mp4','.webm','.har')) or p.endswith('/usense-login.json') or '/browser-profiles/' in p]
    check('input_archive_exclusions:'+archive.name,not forbidden,{'files':len(names),'forbidden':forbidden})
old=json.loads((OUT.parent/'sha256-manifest.json').read_text(encoding='utf-8'))
check('old_preparation_preserved',all(entry(ROOT/r['path'])==r for r in old['files']),len(old['files']))
snapshot=json.loads((OUT/'snapshot-check.json').read_text(encoding='utf-8'))
check('executor_manifest_raw_git_verified',snapshot['raw_manifest_verified']==67 and snapshot['old_manifest_entries_preserved']==81,{'current':67,'old':81})
check('no_out_of_scope_executor_delta',not snapshot['out_of_scope_paths'],snapshot['out_of_scope_paths'])
head=subprocess.check_output(['git','-C',str(AUTHOR),'rev-parse','HEAD']).decode().strip()
status=subprocess.check_output(['git','-C',str(AUTHOR),'-c','core.longpaths=true','status','--porcelain']).decode()
check('executor_unchanged_and_clean',head==snapshot['target_commit'] and status=='',{'head':head,'status':status})

pending={OUT/'closure-checks.json',OUT/'sha256-manifest.json'}
links=[]
for doc in [REPORT,OUT/'README.md']:
    text=doc.read_text(encoding='utf-8')
    check('no_trailing_whitespace:'+doc.name,all(line==line.rstrip() for line in text.splitlines()),len(text.splitlines()))
    for dest in re.findall(r'\]\(([^)]+)\)',text):
        if dest.startswith(('https://','http://')):continue
        p=(doc.parent/dest).resolve()
        check('local_link:'+doc.name+':'+dest,p.exists() or p in pending,str(p.relative_to(ROOT)))
        links.append({'source':doc.relative_to(ROOT).as_posix(),'target':dest})
matrix=json.loads((OUT/'scenario-matrix.json').read_text(encoding='utf-8'))
check('scenario_28_complete',len(matrix['scenarios'])==28 and len({s['id'] for s in matrix['scenarios']})==28,matrix['counts'])
check('scenario_counts_honest',matrix['counts']=={'PASS':21,'REWORK':1,'BLOCKED':6},matrix['counts'])
ind=json.loads((OUT/'independent/results.json').read_text(encoding='utf-8'))
check('independent_failures_preserved',ind['passed']==47 and ind['failed']==2,{'passed':ind['passed'],'failed':ind['failed']})
minimum=json.loads((OUT/'minimal-repro/result.json').read_text(encoding='utf-8'))
check('public_defect_reproduced',minimum['defect_reproduced'] and minimum['public_cli_returncode']==0 and minimum['public_loader_accepted'],minimum)
render=json.loads((OUT/'independent-renderer/result.json').read_text(encoding='utf-8'))
release=render['release']
check('own_browser_server_and_pids_released',render['status']=='PASS' and not release['owned_descendant_pids_alive_after'] and all(release[k] for k in ['context_closed','browser_closed','playwright_stopped','local_server_closed']),release)
check('no_authorized_profile_or_platform',not release['persistent_context_opened'] and not release['authorized_profile_accessed'] and render['network']['actual_platform_requests']==0,render['network']['actual_platform_requests'])
check('no_test_lease_remaining',not list(STAGE.rglob('.a04-readonly.lease')),'Only own synthetic stage inspected')
check('mutation_server_receives_zero',render['network']['server_counts'].get('mutation_received',0)==0,render['network']['server_counts'])
check('reference_and_negative_counts',len(render['cases'])==4 and all(len(c['checks'])==3 and len(c['negative_probes'])==3 for c in render['cases']),{'references':12,'negative_mappings':12})
malformed=[]
for f in OUT.rglob('*.json'):
    try:json.loads(f.read_text(encoding='utf-8-sig'))
    except json.JSONDecodeError:
        relative=f.relative_to(OUT).as_posix()
        assert relative=='independent/cases/F03-json/input/capture.json',relative
        malformed.append(relative)
check('intentionally_malformed_negative_input_preserved',malformed==['independent/cases/F03-json/input/capture.json'],malformed)
import cv2,numpy,importlib.metadata
versions={'python':sys.version,'executable':sys.executable,'OpenCV':cv2.__version__,'NumPy':numpy.__version__,
 'Pillow':importlib.metadata.version('Pillow'),'Playwright':importlib.metadata.version('playwright'),
 'Pydantic':importlib.metadata.version('pydantic')}
paths=[p.relative_to(ROOT).as_posix() for p in sorted(OUT.rglob('*')) if p.is_file()]+[REPORT.relative_to(ROOT).as_posix()]
ignored=subprocess.run(['git','-C',str(ROOT),'check-ignore','--stdin'],input='\n'.join(paths)+'\n',text=True,capture_output=True)
assert ignored.returncode in [0,1]
ignored_paths=ignored.stdout.splitlines()
save(OUT/'closure-checks.json',{'at':datetime.now(timezone.utc).isoformat(),'scope':'A04_COORDINATE_R1_REVIEW_ONLY',
 'decision':'REWORK','real_platform_required_items':'BLOCKED','checks':checks,'links':links,
 'environment':versions,'ignored_files_in_manifest':ignored_paths,
 'required_archival_note':'Ignored logs are included in the SHA256 manifest; reviewer did not force-add or commit anything',
 'allowed_review_write_roots':['docs/tasks/A04-coordinate-R1-review-report.md','docs/evidence/A04/review/coordinate-R1/','.local/stages/A04-review/coordinate-R1/'],
 'product_state_or_dependencies_modified':False,'commit_merge_push_performed':False,
 'paid_model_calls':0,'paid_model_cost':0,
 'fresh_real_book_facts_asserted':False,
 'test_input_correction':'Initial contract consumer export omission fixed by exact-commit supplement; old failure preserved',
 'renderer_harness_correction':'Missing optional psutil before launch; old script/log preserved, no install; own PID-only Windows probe used',
 'closure_harness_correction':'First blanket JSON parse encountered intentionally truncated F03 input; now checks that only this exact preserved negative fixture is malformed',
 'independent_original_shell_wrapper':'Tail Get-Content masked Python exit at outer shell; results.json records two failures; separate minimal reproducer explicitly returns exit1'})
files=[REPORT]+[p for p in sorted(OUT.rglob('*')) if p.is_file() and p!=OUT/'sha256-manifest.json']
save(OUT/'sha256-manifest.json',{'algorithm':'sha256','path_base':'D:/1800 repository root',
 'target_commit':snapshot['target_commit'],'review_workflow_commit':'2ef3bfda20476dff3bdd23912d5bf2d1e3eb5ce1',
 'self_excluded':True,'report_included':True,'files':[entry(p) for p in files]})
m=json.loads((OUT/'sha256-manifest.json').read_text(encoding='utf-8'))
assert all(entry(ROOT/e['path'])==e for e in m['files'])
assert all((ROOT/x['source']).parent.joinpath(x['target']).resolve().exists() for x in links)
print(json.dumps({'decision':'REWORK','real_required':'BLOCKED','checks':len(checks),
 'manifest_files':len(files),'manifest_bytes':sum(e['bytes'] for e in m['files']),
 'ignored_files_included':len(ignored_paths),'author_tree_clean':True,'owned_browser_pids_alive':0,
 'manifest_sha256':sha((OUT/'sha256-manifest.json').read_bytes())},ensure_ascii=False))
