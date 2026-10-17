"""Read-only closure over saved R2 execution and unchanged historical artifacts."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parent
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,value):
 with path.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
info=read(OUT/'bootstrap.json');before=read(OUT/'primary-before.json');issues=[];commands=[];groups=[]
def git(*args):
 p=subprocess.run(['git',*args],cwd=ROOT,capture_output=True)
 commands.append(dict(argv=p.args,exit_code=p.returncode,stdout=p.stdout.decode('utf-8','replace'),stderr=p.stderr.decode('utf-8','replace')))
 assert p.returncode==0
 return p.stdout
live=git('rev-parse','HEAD').decode().strip()
delta=git('diff','--name-status',before['live_HEAD'],live).decode('utf-8')
committed_changed={line.split('\t')[-1] for line in delta.splitlines()}
primary_changed=[];external=[]
for row in before['files']:
 path=ROOT/row['path']
 if not path.is_file() or sha(path)!=row['sha256']:
  primary_changed.append(row['path'])
  critical=row['path'].startswith(('docs/evidence/A01/','docs/evidence/A02/')) or (row['path'].startswith('docs/tasks/A01') and row['path'].endswith('report.md'))
  if row['path'] not in committed_changed or critical or not path.is_file():issues.append('unexpected primary preservation change:'+row['path']);continue
  blob=git('show',live+':'+row['path']);disk=path.read_bytes()
  kind='GIT_RAW' if disk==blob else 'EXACT_LF_TO_CRLF' if b'\r' not in blob and disk==blob.replace(b'\n',b'\r\n') else 'OTHER'
  if kind=='OTHER':issues.append('uncommitted primary bytes:'+row['path'])
  external.append(dict(path=row['path'],representation=kind,current_sha256=sha(path),HEAD_blob_sha256=hashlib.sha256(blob).hexdigest()))
groups.append(dict(name='primary-existing-files-including-old-A01-A02-and-ignored-logs',files=len(before['files']),changed_paths=primary_changed,externally_committed_reconciliations=external))
for label,key,indexfile in (('checkout','disk_sha256','checkout-input-index.json'),('raw','sha256','raw-input-index.json')):
 rows=read(OUT/indexfile);bad=[]
 for row in rows:
  path=Path(info[label])/row['path']
  if not path.is_file() or sha(path)!=row[key]:bad.append(row['path'])
 groups.append(dict(name=label,files=len(rows),mismatches=bad));issues.extend(label+':'+path for path in bad)
old_report=ROOT/'docs/tasks/A01-integration-R1-review-report.md';old_manifest=ROOT/'docs/evidence/A01/review-integration-R1/sha256-manifest.json'
assert sha(old_report)=='2aaed84505799509319cab8e99a94eba818b69fd301caf4d3be89fe48c6a3caf'
assert sha(old_manifest)=='a331ad8a039408f2225f9e9842cc0a4d0860af7a0ece67f3fafa527f0c6600ad'
prior=read(old_manifest);old_bad=[]
for row in prior['files']:
 path=ROOT/row['path']
 if not path.is_file() or sha(path)!=row['sha256'] or path.stat().st_size!=row['bytes']:old_bad.append(row['path'])
groups.append(dict(name='R1-independent-manifest-full-closure',files=len(prior['files']),mismatches=old_bad));issues.extend('old R1:'+p for p in old_bad)
runtime=read(OUT/'runtime-summary.json');assert runtime['passed']
for form in runtime['forms']:
 assert form['entry_exit_code']==0 and form['child_count']==11 and not form['issues'] and not form['disk_changes']
 assert [s['run'] for s in form['suites']]==[52,70,62,8]
 original=read(OUT/'runtime'/form['label']/'entry/results.json')
 for i,c in enumerate(original['commands'][:4]):
  match=re.search(r'OK \(skipped=(\d+)\)',c['stderr']);skips=int(match[1]) if match else 0
  assert skips==(1 if i==0 else 0),(c['label'],skips)
 assert all(c['exit_code']==0 for c in original['commands'])
assert runtime['bare_case']['exit_code']==0 and runtime['bare_case']['run']==1 and not runtime['bare_case']['skipped'] and runtime['bare_case']['probe_exit_code']==0
collector=read(OUT/'collector-runtime/command.json');assert collector['exit_code']==0 and collector['script_sha256_before']==collector['script_sha256_after']
static=read(OUT/'static/summary.json')
boundary=read(OUT/'boundary/final.json')
assert boundary.get('passed') is True,boundary
summary=dict(outcome='ACCEPTED',workflow=info['workflow'],main_parent=info['main_parent'],A01_delivery=info['A01_delivery'],A01_patch=info['A01_patch'],combined_tree=info['integration_tree'],temporary_commit=info['temporary_commit'],I1_GIT_01='CLOSED_FOR_THIS_FIXED_COMBINATION',I04='UNAUTHENTICATED_REDUNDANT_LABEL_LIMIT_RETAINED',forms=runtime['forms'],bare_case=runtime['bare_case'],historical_negative_reuse='OID-bound only; no functional replay',geometry_630_rerun=False,main_A01_integrated=False,A04_released=False,D01_released=False,network_platform_browser_credentials_OCR_model_calls=0)
dump(OUT/'review-summary.json',summary)
dump(OUT/'closeout-integrity.json',dict(groups=groups,initial_live_HEAD=before['live_HEAD'],current_live_HEAD=live,fixed_integration_parent_is_separate=info['main_parent'],committed_live_delta=delta,status=git('status','--short','--branch').decode('utf-8'),commands=commands,issues=issues))
print(json.dumps(dict(outcome='ACCEPTED' if not issues else 'INTEGRITY_ISSUES',groups=groups,issues=issues),ensure_ascii=False))
raise SystemExit(0 if not issues else 1)
