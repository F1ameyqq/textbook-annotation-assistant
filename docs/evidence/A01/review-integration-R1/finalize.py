import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parent;REPORT=ROOT/'docs/tasks/A01-integration-R1-review-report.md'
MANIFEST=OUT/'sha256-manifest.json'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def dump(path,data):
 assert not path.exists(),path
 with path.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
assert not MANIFEST.exists()
integrity=read(OUT/'closeout-integrity.json');assert not integrity['issues']
assert all(not x['mismatches'] for x in integrity['groups'] if x['name']!='primary-tracked-and-preexisting-mermaid')
assert read(OUT/'review-summary.json')['outcome']=='REWORK'
assert read(OUT/'process-check.json')['matched_count']==0
receipts=[
 dict(script='bootstrap.initial.py',observed_exit_code=1,receipt='bootstrap-first-attempt.json'),
 dict(script='bootstrap.py',observed_exit_code=0,receipt='bootstrap.json'),
 dict(script='inventory-history.py',observed_exit_code=0,receipt='historical-before.json'),
 dict(script='run_forms.py',observed_exit_code=1,receipt='run_forms-launch.json'),
 dict(script='collect_runtime.py',observed_exit_code=0,receipt='runtime-observed-summary.json'),
 dict(script='git_availability_control.py',observed_exit_code=0,receipt='git-availability/summary.json'),
 dict(script='process-check.ps1',observed_exit_code=0,receipt='process-check.json'),
 dict(script='closeout.initial.py',observed_exit_code=1,receipt='closeout-first-attempt.json'),
 dict(script='closeout.attempt2.py',observed_exit_code=1,receipt='closeout-second-attempt.json'),
 dict(script='closeout.attempt3.py',observed_exit_code=1,receipt='closeout-third-attempt.json'),
 dict(script='closeout.py',observed_exit_code=0,receipt='closeout-integrity.json')]
dump(OUT/'collection-receipts.json',dict(note='Top-level exits observed in tool exec/write_stdin receipts. Root top-level stdout/stderr were returned by tools; do not treat this metadata as startup raw-byte redirection. All tested entry/subprocess raw outputs are retained separately.',receipts=receipts))
files=sorted([p for p in OUT.rglob('*') if p.is_file()]+[REPORT])
relative=[p.relative_to(ROOT).as_posix() for p in files]
ignore_input=('\0'.join(relative)+'\0').encode('utf-8')
proc=subprocess.run(['git','check-ignore','-z','--stdin'],cwd=ROOT,input=ignore_input,capture_output=True)
assert proc.returncode in (0,1),proc.stderr
ignored=[p.decode('utf-8') for p in proc.stdout.split(b'\0') if p]
assert set(ignored)<=set(relative)
dump(OUT/'git-ignored-paths.json',dict(argv=proc.args,exit_code=proc.returncode,input_paths=len(relative),stdin_sha256=hashlib.sha256(ignore_input).hexdigest(),ignored_paths=ignored,stderr=proc.stderr.decode('utf-8','replace'),policy='Included in this manifest and retained on disk; no implicit omission because Git ignores them.'))
for target in re.findall(r'\]\(([^)]+)\)',REPORT.read_text(encoding='utf-8')):
 if '://' not in target and (REPORT.parent/target).resolve()!=MANIFEST:assert (REPORT.parent/target).resolve().exists(),target
before=[p for p in OUT.rglob('*') if p.is_file()]+[REPORT]
dump(OUT/'final-integrity.json',dict(outcome='REWORK',report_sha256=sha(REPORT),expected_manifest_records=len(before)+1,ignored_paths=len(ignored),old_A01_files_preserved=2032,isolated_snapshots_preserved=True,mandatory_failure='I1-GIT-01',entry_exits=dict(checkout_with_git=0,raw_without_git=1,raw_with_git=0),owned_sessions_to_release=0,manifest_excludes_only_itself=True,issues=[]))
all_files=sorted([p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST]+[REPORT])
rows=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p),git_ignored=p.relative_to(ROOT).as_posix() in ignored) for p in all_files]
dump(MANIFEST,dict(kind='INDEPENDENT_REVIEW_ARCHIVE',outcome='REWORK',final_commit='5f872150a237b195f73c78e02e13a91d2f4f46a7',patch_commit='f8f2981a815f96147144d3747d26752b564cc9f7',main_parent='4946b8ab307f88bdc25c14ace5ead774e3119fc5',self_excluded=MANIFEST.relative_to(ROOT).as_posix(),other_exclusions=[],files=rows))
assert len(rows)==read(OUT/'final-integrity.json')['expected_manifest_records']
for row in rows:assert sha(ROOT/row['path'])==row['sha256']
print(json.dumps(dict(outcome='REWORK',records=len(rows),ignored_files=len(ignored),report_sha256=sha(REPORT),manifest_sha256=sha(MANIFEST),issues=[]),ensure_ascii=False))
