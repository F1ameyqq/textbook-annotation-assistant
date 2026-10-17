"""Export exact frozen Git bytes. Does not run product code or access profile."""
import hashlib, io, json, subprocess, tarfile
from pathlib import Path
from datetime import datetime, timezone

REPO=Path('C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800')
OUT=Path('D:/1800/docs/evidence/A04/review/coordinate-R1')
STAGE=Path('D:/1800/.local/stages/A04-review/coordinate-R1')
TARGET='a86eca6ec87ced20dc3a8bcc8f2c87d329e87c39'
DEPENDENCY='c6bebdf43eb93f7a6ae21e96ec07ed155686777d'
WORKFLOW='2ef3bfda20476dff3bdd23912d5bf2d1e3eb5ce1'
FROZEN=STAGE/'frozen input with spaces'
def git(*args):
    return subprocess.check_output(['git','-c','core.longpaths=true','-C',str(REPO),*args])
def blob(commit,path):return git('show',commit+':'+path)
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

OUT.mkdir(parents=True,exist_ok=True)
assert not FROZEN.exists(), 'Use a fresh stage, never overwrite prior input'
manifest_path='docs/evidence/A04/execution/coordinate-R1/sha256-manifest.json'
report_path='docs/tasks/A04-coordinate-R1-execution-report.md'
mbytes=blob(TARGET,manifest_path);rbytes=blob(TARGET,report_path)
assert sha(mbytes)=='0f4cc216aa3c91a0557dec3a32f4cd8e41797404708395834c73d5dff7a5aa1c'
assert sha(rbytes)=='31586c911151d6dbc51e075455bfa1a1e593b09f0f41a0762604fa29d5e8a00e'
manifest=json.loads(mbytes)
verified=[]
for entry in manifest['files']:
    data=blob(TARGET,entry['path'])
    assert sha(data)==entry['sha256'] and len(data)==entry['bytes'],entry['path']
    verified.append(entry)
assert len(verified)==67
# Sufficient frozen public code/tests and historical image inputs for A04 only.
paths=['AGENTS.md','src','tests','config','tools/usense_login.py','tools/test_usense_login.py',
       'docs/evidence/A04','docs/evidence/A05','docs/tasks/A04-execution-report.md',report_path]
archive=git('archive','--format=tar.gz',TARGET,*paths)
apath=OUT/'inputs/frozen-inputs.tar.gz';apath.parent.mkdir(parents=True,exist_ok=True);apath.write_bytes(archive)
FROZEN.mkdir(parents=True)
inventory=[]
with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
    for member in tar.getmembers():
        destination=(FROZEN/member.name).resolve()
        destination.relative_to(FROZEN.resolve())
        if member.isdir():destination.mkdir(parents=True,exist_ok=True);continue
        assert member.isfile(),member.name
        data=tar.extractfile(member).read();destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(data)
        inventory.append({'path':member.name,'sha256':sha(data),'bytes':len(data)})
save(OUT/'inputs/frozen-tree-manifest.json',{'commit':TARGET,'archive_sha256':sha(archive),'files':inventory})
workflow_docs=['AGENTS.md','docs/coordination.md','docs/contracts-v1.md','docs/architecture.md',
 'docs/local-login.md','docs/tasks/A04-independent-review.md','docs/tasks/A04-coordinate-R1-dispatch.md',
 'docs/tasks/A04-coordinate-R1-review-handoff.md']
wfs=[]
for path in workflow_docs:
    data=blob(WORKFLOW,path);dest=OUT/'inputs/workflow'/path
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    wfs.append({'path':path,'sha256':sha(data),'bytes':len(data)})
changed=git('diff','--name-only','3d4d10a0e12faa1af8d47e9f180d086ce401509c',TARGET).decode().splitlines()
allowed=('src/annotation/source/usense/','src/annotation/delivery/usense_readonly/',
 'src/annotation/runtime/browser/','tests/test_a04_','tests/fixtures/a04/',
 'docs/evidence/A04/execution/coordinate-R1/','docs/tasks/A04-coordinate-R1-execution-report.md')
outside=[p for p in changed if not p.startswith(allowed)]
assert not outside,outside
public={}
for name in ['src/annotation/geometry','src/annotation/contracts','config','requirements.txt','pyproject.toml']:
    try:
        public[name]={'target':git('rev-parse',TARGET+':'+name).decode().strip(),
                      'dependency':git('rev-parse',DEPENDENCY+':'+name).decode().strip()}
    except subprocess.CalledProcessError:
        public[name]={'exists':False};continue
    assert public[name]['target']==public[name]['dependency'],name
old=json.loads(blob('3e4dba5676c2dc4a71d7826827a76df11017a68b','docs/evidence/A04/execution/sha256-manifest.json'))
preserved=[]
for entry in old['files']:
    data=blob(TARGET,entry['path'])
    assert sha(data)==entry['sha256'] and len(data)==entry['bytes'],entry['path']
    preserved.append(entry)
save(OUT/'snapshot-check.json',{'at':datetime.now(timezone.utc).isoformat(),
 'target_commit':TARGET,'workflow_commit':WORKFLOW,'dependency_commit':DEPENDENCY,
 'head':git('rev-parse','HEAD').decode().strip(), 'worktree_status':git('status','--porcelain').decode(),
 'raw_manifest_verified':len(verified),'raw_manifest_sha256':sha(mbytes),'raw_report_sha256':sha(rbytes),
 'archive_bytes':len(archive),'extracted_files':len(inventory),'frozen_stage':str(FROZEN),
 'changed_paths':changed,'out_of_scope_paths':outside,'public_trees':public,
 'old_manifest_entries_preserved':len(preserved),'workflow_inputs':wfs,
 'profile_accessed':False,'browser_started':False})
print(json.dumps({'raw_manifest_verified':len(verified),'old_preserved':len(preserved),
 'extracted_files':len(inventory),'archive_bytes':len(archive),'frozen_stage':str(FROZEN)}))
