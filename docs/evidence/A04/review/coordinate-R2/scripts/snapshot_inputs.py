"""R2 raw-Git inputs only. No product execution, network or credential access."""
import hashlib,io,json,subprocess,tarfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A04/review/coordinate-R2'
STAGE=ROOT/'.local/stages/A04-review/coordinate-R2';FROZEN=STAGE/'frozen source with spaces'
AUTHOR=Path('C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800')
TARGET='76898657e76ac2db071327e90c6ca5031d17571f';BASE='a86eca6ec87ced20dc3a8bcc8f2c87d329e87c39'
WORKFLOW='e7ff892776f53636fcddfe136d1659204c4ff738'
def git(*args):return subprocess.check_output(['git','-c','core.longpaths=true','-C',str(AUTHOR),*args])
def sha(data):return hashlib.sha256(data).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def blob(commit,path):return git('show',commit+':'+path)
def blobs(commit,paths):
    raw=subprocess.check_output(['git','-C',str(AUTHOR),'cat-file','--batch'],input=''.join(commit+':'+p+'\n' for p in paths).encode())
    f=io.BytesIO(raw);result={}
    for path in paths:
        header=f.readline().split();assert len(header)==3 and header[1]==b'blob',path
        data=f.read(int(header[2]));assert f.read(1)==b'\n';result[path]=data
    return result

if FROZEN.exists():
    assert (OUT/'inputs/frozen-tree-manifest.json').exists(),'Incomplete unrelated stage; stop'
OUT.mkdir(parents=True,exist_ok=True)
documents=['AGENTS.md','docs/coordination.md','docs/architecture.md','docs/contracts-v1.md',
 'docs/tasks/A04-coordinate-R2-review-handoff.md','docs/tasks/A04-coordinate-R2-rework.md',
 'docs/evidence/coordinator/heartbeat-20261017-0604/A04-delivery-preflight.json']
workflow=blobs(WORKFLOW,documents)
assert sha(workflow['docs/tasks/A04-coordinate-R2-review-handoff.md'])=='48c6cb8d41c3598c3fa10f438da0da9d00486c133bc4e97a161ed42518b8d468'
for path,data in workflow.items():
    dest=OUT/'inputs/workflow'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
report='docs/tasks/A04-coordinate-R2-execution-report.md';manifest_path='docs/evidence/A04/execution/coordinate-R2/sha256-manifest.json'
report_bytes=blob(TARGET,report);manifest_bytes=blob(TARGET,manifest_path)
assert sha(report_bytes)=='e3d5a31ac72640379ad249f074c31cbd453ee1ecc2822d623b1cabb28f1e4557'
assert sha(manifest_bytes)=='966926555fe1aa81aa3e16b87388ba47e6cc794b60c1b7a7e9ed84825d6dfbd5'
manifest=json.loads(manifest_bytes);frozen=blobs(TARGET,[e['path'] for e in manifest['files']])
disk_variants=[]
for entry in manifest['files']:
    data=frozen[entry['path']];assert sha(data)==entry['sha256'] and len(data)==entry['bytes'],entry['path']
    if (AUTHOR/entry['path']).read_bytes()!=data:disk_variants.append(entry['path'])
assert len(manifest['files'])==158 and not disk_variants
old_execution=[]
for mpath in ['docs/evidence/A04/execution/sha256-manifest.json','docs/evidence/A04/execution/coordinate-R1/sha256-manifest.json']:
    old=json.loads(blob(BASE,mpath));current=blobs(TARGET,[e['path'] for e in old['files']])
    for e in old['files']:assert sha(current[e['path']])==e['sha256'] and len(current[e['path']])==e['bytes'],e['path']
    old_execution.append({'manifest':mpath,'entries_unchanged':len(old['files'])})
archive=git('archive','--format=tar.gz',TARGET,'AGENTS.md','src','tests','config','examples/contracts',
 'tools/usense_login.py','tools/test_usense_login.py',report,'docs/evidence/A04/execution/coordinate-R2')
ap=OUT/'inputs/frozen-inputs.tar.gz'
if ap.exists():assert ap.read_bytes()==archive,'Never replace changed frozen archive'
else:ap.write_bytes(archive)
FROZEN.mkdir(parents=True,exist_ok=True)
inventory=[]
with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as t:
    for m in t.getmembers():
        dest=(FROZEN/m.name).resolve();dest.relative_to(FROZEN.resolve())
        if m.isdir():dest.mkdir(parents=True,exist_ok=True);continue
        assert m.isfile() and '.local/' not in m.name and not m.name.endswith(('.mp4','.webm','.har'))
        data=t.extractfile(m).read();dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():assert dest.read_bytes()==data,m.name
        else:dest.write_bytes(data)
        inventory.append({'path':m.name,'sha256':sha(data),'bytes':len(data)})
save(OUT/'inputs/frozen-tree-manifest.json',{'target_commit':TARGET,'archive_sha256':sha(archive),'files':inventory})
changed=git('diff','--name-only',BASE,TARGET).decode().splitlines()
allowed=('src/annotation/source/usense/','tests/test_a04','docs/evidence/A04/execution/coordinate-R2/',
 'docs/tasks/A04-coordinate-R2-execution-report.md','examples/a04/coordinate-R2/')
assert all(p.startswith(allowed) for p in changed),changed
public_paths=['src/annotation/contracts','src/annotation/geometry','src/annotation/source/static',
 'src/annotation/runtime/browser','src/annotation/delivery/usense_readonly','config','pyproject.toml',
 'src/annotation/__init__.py','src/annotation/source/__init__.py']
public=[]
for path in public_paths:
    old=git('ls-tree',BASE,'--',path).decode().strip();new=git('ls-tree',TARGET,'--',path).decode().strip()
    assert old==new,path;public.append({'path':path,'tree_entry':new,'absent_in_both':not new})
prior=[]
for p in [ROOT/'docs/tasks/A04-review-report.md',ROOT/'docs/tasks/A04-coordinate-R1-review-report.md',
 ROOT/'docs/evidence/A04/review/sha256-manifest.json',ROOT/'docs/evidence/A04/review/coordinate-R1/sha256-manifest.json']:
    data=p.read_bytes();prior.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(data),'bytes':len(data)})
for parent in ['docs/evidence/A04/review','docs/evidence/A04/review/coordinate-R1']:
    m=json.loads((ROOT/parent/'sha256-manifest.json').read_text(encoding='utf-8'))
    for e in m['files']:
        data=(ROOT/e['path']).read_bytes();assert sha(data)==e['sha256'] and len(data)==e['bytes'],e['path']
head=git('rev-parse','HEAD').decode().strip();status=git('status','--porcelain').decode()
assert head==TARGET and status==''
save(OUT/'snapshot-check.json',{'at':datetime.now(timezone.utc).isoformat(),'target_commit':TARGET,'base_commit':BASE,
 'workflow_commit':WORKFLOW,'implementation_commit':'45150b57f5ae6cc8f4c55ffc6f7e417a0957f32e',
 'raw_manifest_entries_verified':158,'disk_variants':disk_variants,'report_sha256':sha(report_bytes),
 'manifest_sha256':sha(manifest_bytes),'old_execution':old_execution,'changed_paths':changed,
 'public_and_dependency_paths_unchanged':public,'isolated_stage':str(FROZEN),
 'export_files':len(inventory),'archive_bytes':len(archive),'prior_review_files':prior,
 'prior_preparation_and_R1_manifests_verified':[5,227],
 'workflow_files':[{'path':p,'sha256':sha(b),'bytes':len(b)} for p,b in workflow.items()],
 'head':head,'worktree_status':status,'network_browser_model_or_profile_used':False})
print(json.dumps({'target_commit':TARGET,'verified_entries':158,'export_files':len(inventory),
 'archive_bytes':len(archive),'old_execution_entries_preserved':sum(e['entries_unchanged'] for e in old_execution)}))
