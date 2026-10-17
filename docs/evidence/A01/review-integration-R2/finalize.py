"""Package already completed checks; no functional entry is rerun."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parent
REPORT=ROOT/'docs/tasks/A01-integration-R2-review-report.md';MANIFEST=OUT/'sha256-manifest.json'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,value):
 assert not p.exists(),p
 with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
assert not MANIFEST.exists()
info=read(OUT/'bootstrap.json');runtime=read(OUT/'runtime-summary.json')
assert runtime['passed'] and all(f['entry_exit_code']==0 and f['child_count']==11 for f in runtime['forms'])
assert runtime['bare_case']['passed']
assert read(OUT/'static/summary.json')['passed'] and read(OUT/'boundary/final.json')['passed']
assert read(OUT/'review-summary.json')['outcome']=='ACCEPTED'
assert not read(OUT/'closeout-integrity.json')['issues']
assert read(OUT/'process-check.json')['matched_count']==0
assert read(OUT/'collector-runtime/command.json')['script_sha256_after']==sha(OUT/'run_forms.py')
report=REPORT.read_text(encoding='utf-8');links=[]
assert 'ACCEPTED' in report and info['integration_tree'] in report
assert all(line.rstrip()==line for line in report.splitlines())
for target in re.findall(r'\]\(([^)]+)\)',report):
 if '://' in target:continue
 path=(REPORT.parent/target).resolve()
 if path==MANIFEST:continue
 assert path.exists(),target
 links.append(dict(target=target,exists=True))
dump(OUT/'report-validation.json',dict(links=links,trailing_whitespace=False,issues=[],scope='Saved report/link/evidence validation only; no functional rerun.'))
dump(OUT/'root-collection-receipts.json',dict(note='Observed top-level tool receipts. Bootstrap/closeout/process-check stdout were returned by tools, not separately redirected startup raw-byte logs. Runtime collector and all verifier/OS/singleton subprocess original output bytes were captured at startup and are retained.',receipts=[dict(argv=['python','-B',str(OUT/'bootstrap.py')],cwd='D:/1800',observed_exit_code=0,output='bootstrap.json; bootstrap-commands.json'),dict(argv=['python','-B',str(OUT/'launch_runtime.py')],cwd='D:/1800',observed_exit_code=0,output='collector-runtime/command.json; stdout.log; stderr.log'),dict(argv=['python','-B',str(OUT/'closeout_audit.py')],cwd='D:/1800',observed_exit_code=0,output='closeout-integrity.json'),dict(argv=['PowerShell','process-check.ps1'],observed_exit_code=0,output='process-check.json'),dict(argv=['git','diff','--check','--','docs/tasks/A01-integration-R2-review-report.md','docs/evidence/A01/review-integration-R2'],cwd='D:/1800',observed_exit_code=0)]))
files=sorted([p for p in OUT.rglob('*') if p.is_file()]+[REPORT])
relative=[p.relative_to(ROOT).as_posix() for p in files]
stdin=('\0'.join(relative)+'\0').encode('utf-8')
p=subprocess.run(['git','check-ignore','-z','--stdin'],cwd=ROOT,input=stdin,capture_output=True)
assert p.returncode in (0,1)
ignored=[part.decode('utf-8') for part in p.stdout.split(b'\0') if part]
assert set(ignored)<=set(relative)
dump(OUT/'git-ignored-paths.json',dict(argv=p.args,cwd=str(ROOT),exit_code=p.returncode,input_paths=len(relative),stdin_sha256=hashlib.sha256(stdin).hexdigest(),ignored_paths=ignored,stderr=p.stderr.decode('utf-8','replace'),policy='All ignored files included in this SHA256 manifest and retained; no silent omission.'))
before=[p for p in OUT.rglob('*') if p.is_file()]+[REPORT]
dump(OUT/'final-integrity.json',dict(outcome='ACCEPTED',main_parent=info['main_parent'],A01_delivery=info['A01_delivery'],combination_tree=info['integration_tree'],report_sha256=sha(REPORT),expected_manifest_records=len(before)+1,ignored_files=len(ignored),prior_R1_manifest_records_verified=226,root_functional_collection_exit_code=0,both_full_entries_exit_code=0,raw_bare_case=dict(exit_code=0,run=1,skipped=0),own_process_path_matches=0,main_A01_integrated=False,A04_released=False,D01_released=False,manifest_excludes_only_itself=True,issues=[]))
all_files=sorted([p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST]+[REPORT])
rows=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p),git_ignored=p.relative_to(ROOT).as_posix() in ignored) for p in all_files]
dump(MANIFEST,dict(kind='INDEPENDENT_A01_INTEGRATION_R2_REVIEW',outcome='ACCEPTED',workflow=info['workflow'],main_parent=info['main_parent'],A01_delivery=info['A01_delivery'],combination_tree=info['integration_tree'],temporary_commit=info['temporary_commit'],self_excluded=MANIFEST.relative_to(ROOT).as_posix(),other_exclusions=[],files=rows))
assert len(rows)==read(OUT/'final-integrity.json')['expected_manifest_records']
for row in rows:assert sha(ROOT/row['path'])==row['sha256']
assert MANIFEST.exists()
print(json.dumps(dict(outcome='ACCEPTED',records=len(rows),ignored_files=len(ignored),report_sha256=sha(REPORT),manifest_sha256=sha(MANIFEST),issues=[])))
