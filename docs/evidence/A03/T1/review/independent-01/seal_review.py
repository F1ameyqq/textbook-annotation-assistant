"""Hash-only final review inventory and independent copy/link readback."""
import json
from pathlib import Path
import re
from bootstrap import ROOT,SNAP,EV,sha,save,TARGET,CODE,BASE,WORKFLOW

report=Path('D:/1800/docs/tasks/A03-T1-review-report.md')
source=SNAP/'docs/evidence/A03/T1/execution/validation/independent-01'
copied=EV/'validation/independent-01'
paths=sorted(p for p in source.rglob('*') if p.is_file())
assert {p.relative_to(source).as_posix() for p in paths}=={p.relative_to(copied).as_posix() for p in copied.rglob('*') if p.is_file()}
for p in paths:assert p.read_bytes()==(copied/p.relative_to(source)).read_bytes()
assert len(list(copied.glob('cases/*/captures/*/*.sqlite3')))==56
raw=report.read_bytes();text=raw.decode('utf-8',errors='strict')
assert text.endswith('\n') and not any(line.rstrip()!=line for line in text.splitlines())
for label,path,expected in re.findall(r'\| \[([^\]]+)\]\(([^)]+)\) \| `([a-f0-9]{64})` \|',text):
    p=(report.parent/path).resolve();assert sha(p.read_bytes())==expected,label
save(EV/'seal_review.py',Path(__file__).read_bytes())
save(EV/'final-static-readback.json',dict(independent_run_files_copied=len(paths),all_raw_copy_members_match=True,
    business_stage_db_originals=56,fixture_originals=1,report_UTF8=True,report_hash_table_matches=True,
    product_business_reruns=0,known_author_seal_invocations=0,index_commit_mutations=0))
files=[p for p in EV.rglob('*') if p.is_file()]+[report]
assert not any('__pycache__' in p.parts for p in files)
workspace=Path('D:/1800')
index={p.relative_to(workspace).as_posix():dict(size=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(files)}
manifest_path=EV/'manifest.json'
manifest=dict(status='REVIEWER_RECOMMENDS_ACCEPTED_T1_CAPTURE_AND_SIX_SCENES_ONLY',target_commit=TARGET,code_commit=CODE,
    product_base=BASE,workflow_commit=WORKFLOW,excluded=[manifest_path.relative_to(workspace).as_posix()],files=index)
save(manifest_path,manifest)
for p,e in index.items():assert sha((workspace/p).read_bytes())==e['sha256']
for link in re.findall(r'\]\(([^)]+)\)',text):assert (report.parent/link).resolve().is_file(),link
print(json.dumps(dict(manifest_members=len(index),report_sha256=sha(raw),manifest_sha256=sha(manifest_path.read_bytes()),
    release_sha256=sha((EV/'release-proof.json').read_bytes()),copy_files=len(paths),links='PASS',raw_readback='PASS'),indent=2))
