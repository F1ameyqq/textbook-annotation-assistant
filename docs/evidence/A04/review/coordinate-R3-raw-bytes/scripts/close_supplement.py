"""Final binary cat-file comparison, old-material preservation and new manifest."""
import ast,hashlib,io,json,re,subprocess
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1];F=OUT/'inputs/raw product with spaces'
REPORT=ROOT/'docs/tasks/A04-coordinate-R3-raw-bytes-review-report.md'
AUTHOR=Path('C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800');TARGET='6c8137a4fadddc01a47906d564ab3460277c8958'
def sha(data):return hashlib.sha256(data).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def entry(p):
    b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'sha256':sha(b),'bytes':len(b)}
checks=[]
def check(name,ok,detail):assert ok,(name,detail);checks.append({'name':name,'status':'PASS','detail':detail})
before=read(OUT/'runtime-inputs-before.json');after=read(OUT/'runtime-inputs-after.json')
paths=[x['path'] for x in before['files']];assert len(paths)==212
command=['git','-C',str(AUTHOR),'cat-file','--batch']
proc=subprocess.run(command,input=''.join(TARGET+':'+p+'\n' for p in paths).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
stream=io.BytesIO(proc.stdout);rows=[]
for old in before['files']:
    header=stream.readline().split();assert header[1]==b'blob'
    blob=stream.read(int(header[2]));assert stream.read(1)==b'\n'
    oid=hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest();actual=(F/old['path']).read_bytes()
    assert oid==header[0].decode()==old['git_blob_oid'] and actual==blob and sha(actual)==old['git_sha256'],old['path']
    rows.append({'path':old['path'],'git_blob_oid':oid,'git_sha256':sha(blob),'git_bytes':len(blob),
      'runtime_sha256':sha(actual),'runtime_bytes':len(actual),'exact_bytes_equal':True})
save(OUT/'cat-file-final-verification.json',{'command':command,'returncode':proc.returncode,'stderr':proc.stderr.decode('utf-8','replace'),
 'target_commit':TARGET,'files':rows,'all_212_binary_equal':True,'normalization_used':False})
check('212_fresh_binary_cat_file_matches',len(rows)==212 and before['all_exact'] and after['all_exact'],212)
check('old_archive_claim_explicitly_corrected',read(OUT/'archive-vs-cat-file.json')['old_raw_git_claim']=='INCORRECT',59)
diff=read(OUT/'archive-vs-cat-file.json')
check('59_difference_breakdown',diff['different_count']==59 and diff['difference_types']=={'.py':55,'.gitattributes':1,'.pgm':3} and all(x['acceptance_uses_exact_bytes_not_normalization'] for x in diff['differences']),diff['difference_types'])
old=read(OUT/'old-preservation-before.json')
check('old_355_plus_manifest_intact',len(old['records'])==356 and all(entry(ROOT/x['path'])==x for x in old['records']),356)
check('old_after_preservation_record',read(OUT/'old-preservation-after.json')['all_unchanged'],356)
scripts=read(OUT/'replayed-scripts.json')['scripts']
check('six_original_check_scripts_unchanged',len(scripts)==6 and all(sha((OUT/x['copy']).read_bytes())==x['sha256'] and (OUT/x['copy']).stat().st_size==x['bytes'] for x in scripts),6)
bootstrap=read(OUT/'runtime-harness-bootstrap.json')
check('separate_reviewer_bootstrap',bootstrap['not_target_product_file'] and sha(Path(bootstrap['path']).read_bytes())==bootstrap['sha256'],bootstrap)
exact=read(OUT/'exact-replay/result.json');reg=read(OUT/'regression-result.json');ind=read(OUT/'independent-cases/results.json')
check('exact_original_case_rejected',exact['sha256']=='205543876fb32bb14f003bfeec32279e9fd4886bd1949eee9810999e468969bd' and exact['public_cli_returncode']==2 and not exact['defect_reproduced'] and not (OUT/'exact-replay/output').exists(),exact)
check('new_raw_regression_70',reg['tests_run']==70 and reg['status']=='PASS' and not reg['errors'] and not reg['failures'],reg)
check('new_raw_independent_26',ind['passed']==26 and ind['failed']==0,26)
check('separate_not_combined_runs',not read(OUT/'separate-run-comparison.json')['combined_or_double_counted'],True)
pgm=read(OUT/'pgm-resource-bindings.json')
check('three_raw_PGM_binding_chains',len(pgm['bindings'])==3 and not pgm['normalization_used'] and all(x['git_sha256']==x['published_sha256']==x['relocated_sha256']==x['asset_sha256'] and x['dimensions']==[4,3] for x in pgm['bindings']),pgm['bindings'])
check('PGM_raw_vs_archive_difference_and_pixel_identity',all(x['git_sha256']!=x['old_archive_sha256'] and x['old_and_new_pixels_equal'] for x in pgm['bindings']),True)
check('actual_import_paths_and_hashes',read(OUT/'actual-imports.json')['all_match_cat_file'],read(OUT/'actual-imports.json')['imports'])
release=read(OUT/'self-release.json')
check('28_own_original_process_identities_exited',len(release['observations'])==28 and all(x['original_process_exited'] for x in release['observations']),28)
check('27_guard_exits',len(release['guard_records'])==27,27)
check('no_forbidden_actions',release['browser_network_platform_profile_credentials_model_book_actions']==0,0)
v=read(OUT/'review-verdict.json')
check('bounded_supplement_conclusion',v['RAW_BYTE_SUPPLEMENT']=='PASS' and v['OFFLINE_R3']=='ACCEPTED' and v['A04_OVERALL']=='BLOCKED' and not v['integration_or_dependency_release'],v['scope'])
check('real_six_remain_blocked',len(v['real_scenarios'])==6 and all(s=='BLOCKED_NOT_RUN' for s in v['real_scenarios'].values()),v['real_scenarios'])
head=subprocess.check_output(['git','-C',str(AUTHOR),'rev-parse','HEAD']).decode().strip()
status=subprocess.check_output(['git','-c','core.longpaths=true','-C',str(AUTHOR),'status','--porcelain']).decode()
check('author_target_unchanged_clean',head==TARGET and status=='',{'head':head,'status':status})
links=[];pending={OUT/'closure-checks.json',OUT/'sha256-manifest.json'}
for doc in [REPORT,OUT/'README.md']:
    text=doc.read_text(encoding='utf-8');check('whitespace:'+doc.name,all(line==line.rstrip() for line in text.splitlines()),len(text.splitlines()))
    for target in re.findall(r'\]\(([^)]+)\)',text):
        path=(doc.parent/target).resolve();check('link:'+doc.name+':'+target,path.exists() or path in pending,str(path.relative_to(ROOT)))
        links.append({'source':doc.relative_to(ROOT).as_posix(),'target':target})
for p in OUT.rglob('*.json'):read(p)
check('all_new_evidence_JSON_parse',True,len(list(OUT.rglob('*.json'))))
review_scripts=list((OUT/'scripts').glob('*.py'))+list((OUT/'inputs/replay-scripts').rglob('*.py'))
for p in review_scripts:ast.parse(p.read_text(encoding='utf-8'))
check('review_script_syntax',True,len(review_scripts))
paths=[p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file()]+[REPORT.relative_to(ROOT).as_posix()]
ignored=subprocess.run(['git','-C',str(ROOT),'check-ignore','--stdin'],input='\n'.join(paths)+'\n',text=True,capture_output=True)
assert ignored.returncode in (0,1)
save(OUT/'closure-checks.json',{'at':datetime.now(timezone.utc).isoformat(),'checks':checks,'links':links,
 'RAW_BYTE_SUPPLEMENT':'PASS','OFFLINE_R3':'ACCEPTED','A04_OVERALL':'BLOCKED','old_356_preserved':True,
 'ignored_files_included':ignored.stdout.splitlines(),'products_dependencies_state_or_old_evidence_changed':False,
 'submitted_pushed_integrated_or_messaged_others':False,
 'scope':'Single requested raw-byte evidence supplement, no expanded matrix or functionality changes',
 'source_correction':'Prior full raw-Git-byte claim invalid; archive results retained separately; new 212 runtime inputs compared binary to cat-file before/after and final fresh read'})
files=[REPORT]+[p for p in sorted(OUT.rglob('*')) if p.is_file() and p!=OUT/'sha256-manifest.json']
save(OUT/'sha256-manifest.json',{'algorithm':'sha256','path_base':'D:/1800 repository root','target_commit':TARGET,
 'review_workflow_commit':'9317efcdb734b081075c56f6557838d591959e8f','RAW_BYTE_SUPPLEMENT':'PASS','OFFLINE_R3':'ACCEPTED',
 'A04_OVERALL':'BLOCKED','self_excluded':True,'report_included':True,'files':[entry(p) for p in files]})
m=read(OUT/'sha256-manifest.json');assert all(entry(ROOT/x['path'])==x for x in m['files'])
assert all((ROOT/x['source']).parent.joinpath(x['target']).resolve().exists() for x in links)
print(json.dumps({'RAW_BYTE_SUPPLEMENT':'PASS','OFFLINE_R3':'ACCEPTED','A04_OVERALL':'BLOCKED','checks':len(checks),
 'manifest_entries':len(files),'manifest_bytes':sum(x['bytes'] for x in m['files']),
 'manifest_sha256':sha((OUT/'sha256-manifest.json').read_bytes()),'report_sha256':sha(REPORT.read_bytes()),
 'old_records_preserved':356,'runtime_raw_files_binary_equal':212,'own_original_processes_exited':28}))
