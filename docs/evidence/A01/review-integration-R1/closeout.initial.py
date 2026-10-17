import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parent;REPORT=ROOT/'docs/tasks/A01-integration-R1-review-report.md'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def dump(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
issues=[];groups=[]
def inventory(name,base,rows,key):
 bad=[]
 for row in rows:
  path=base/row['path']
  if not path.is_file() or sha(path)!=row[key]:bad.append(row['path'])
 groups.append(dict(name=name,files=len(rows),mismatches=bad));issues.extend(name+':'+p for p in bad)
info=read(OUT/'bootstrap.json')
inventory('primary-tracked-and-preexisting-mermaid',ROOT,read(OUT/'primary-before.json')['files'],'sha256')
inventory('all-prior-A01-material-including-ignored-logs',ROOT,read(OUT/'historical-before.json')['files'],'sha256')
for name,key in (('checkout','disk_sha256'),('raw','sha256'),('frozen','sha256'),('delivery','sha256')):
 index_name=dict(checkout='checkout-input-index.json',raw='raw-input-index.json',frozen='frozen-input-index.json',delivery='delivery-input-index.json')[name]
 inventory('isolated-'+name,Path(info[name]),read(OUT/index_name),key)
expected=[0,1];observed=read(OUT/'runtime-observed-summary.json')
assert [x['entry_exit_code'] for x in observed]==expected
for item in observed:assert item['disk_changes']==[] and item['actual_import_observations']==185
controls=read(OUT/'git-availability/summary.json');assert [c['exit_code'] for c in controls]==[0,1,0]
assert controls[0]['has_dot_git'] is False and controls[1]['git_executable'] is None
full=read(OUT/'git-availability/raw-full-with-git/entry/results.json');assert full['passed'] and all(c['exit_code']==0 for c in full['commands'])
neg=read(OUT/'negative/summary.json');assert [x['actual_exit_code'] for x in neg['focused']]==[0,1,1,1,0,1]
assert neg['focused_expected_failures']==['I04-root-reference-identity']
assert all(c['expected_matched'] for c in neg['auxiliary'])
assert [x['actual_exit_code'] for x in neg['original_release']]==[0,1,1]
static=read(OUT/'static/summary.json');boundary=read(OUT/'boundary/result.json')
assert boundary['git_free_entry_dependency']['blocking']
assert all(r['status']=='checked' for r in boundary['runtime'])
assert read(OUT/'process-check.json')['matched_count']==0
links=[]
for target in re.findall(r'\]\(([^)]+)\)',REPORT.read_text(encoding='utf-8')):
 if '://' in target:continue
 path=(REPORT.parent/target).resolve()
 if path==OUT/'sha256-manifest.json':continue
 links.append(dict(target=target,exists=path.exists()))
 if not path.exists():issues.append('missing report link:'+target)
report_text=REPORT.read_text(encoding='utf-8')
assert 'REWORK' in report_text and 'I1-GIT-01' in report_text
if any(line.rstrip()!=line for line in report_text.splitlines()):issues.append('report trailing whitespace')
git_commands=[]
def git(*args,allowed=(0,)):
 proc=subprocess.run(['git',*args],cwd=ROOT,capture_output=True)
 git_commands.append(dict(argv=proc.args,exit_code=proc.returncode,stdout=proc.stdout.decode('utf-8','replace'),stderr=proc.stderr.decode('utf-8','replace')))
 assert proc.returncode in allowed
 return proc.stdout
head=git('rev-parse','HEAD').decode().strip();assert head==info['main_parent']
status=git('status','--short','--branch').decode('utf-8')
git('diff','--check','--','docs/tasks/A01-integration-R1-review-report.md','docs/evidence/A01/review-integration-R1')
# Preserve only minimal additional reproducer inputs, not another historical evidence tree.
saved=[]
for relative in ('examples/a02/R1/identity.py','tests/test_a02_r1.py'):
 source=Path(info['raw'])/relative;target=OUT/'git-availability/inputs'/relative
 target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
 saved.append(dict(path=str(target.relative_to(OUT)),source=relative,sha256=sha(target)))
dump(OUT/'minimal-reproducer-inputs.json',saved)
summary=dict(outcome='REWORK',blocking_findings=['I1-GIT-01'],nonblocking_findings=['I04 redundant top-level reference_commit label not asserted; true fixed content/entry/manifest identity remains bound'],final_commit=info['final'],patch_commit=info['patch'],main_parent=info['main_parent'],integration_tree=info['integration_tree'],temporary_commit=info['temporary_commit'],normal_checkout_entry_exit=0,raw_entry_without_git_exit=1,raw_entry_with_git_exit=0,actual_import_provenance_verified=True,old_971_allowlist_unchanged=True,old_630_geometry_cases_rerun=False,platform_browser_network_credentials_model_calls=0,fees=0,main_integration_performed=False,A04_released=False,owned_sessions_to_release=0)
dump(OUT/'review-summary.json',summary)
dump(OUT/'closeout-integrity.json',dict(groups=groups,report_links=links,issues=issues,primary_head=head,primary_status=status,status_note='A03 review/P1-R2 untracked material appeared concurrently; it is outside this review and untouched. Only new A01 report/evidence and authorized temporary paths were written.',git_commands=git_commands,assessment='Integrity assertions validate retained evidence, not a successful full Git-free entry.'))
assert not issues,issues
print(json.dumps(dict(outcome='REWORK',integrity_groups=groups,issues=issues,report_sha256=sha(REPORT)),ensure_ascii=False))
