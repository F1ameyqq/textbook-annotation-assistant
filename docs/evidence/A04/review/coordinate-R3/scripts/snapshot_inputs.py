"""Exact R3 Git inputs, integrity and prior-evidence preservation only."""
import hashlib,io,json,subprocess,tarfile
from pathlib import Path
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A04/review/coordinate-R3'
STAGE=ROOT/'.local/stages/A04-review/coordinate-R3';FROZEN=STAGE/'frozen source with spaces'
AUTHOR=Path('C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800')
TARGET='6c8137a4fadddc01a47906d564ab3460277c8958';BASE='76898657e76ac2db071327e90c6ca5031d17571f';WF='d834bf531f95abac7ed30b89b3ca55105fa6f491'
def git(*a):return subprocess.check_output(['git','-c','core.longpaths=true','-C',str(AUTHOR),*a])
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def blobs(commit,paths):
    stream=io.BytesIO(subprocess.check_output(['git','-C',str(AUTHOR),'cat-file','--batch'],input=''.join(commit+':'+p+'\n' for p in paths).encode()))
    found={}
    for p in paths:
        head=stream.readline().split();assert len(head)==3 and head[1]==b'blob',p
        found[p]=stream.read(int(head[2]));assert stream.read(1)==b'\n'
    return found
assert not FROZEN.exists(),'Fresh stage required'
docs=['AGENTS.md','docs/coordination.md','docs/architecture.md','docs/contracts-v1.md',
 'docs/tasks/A04-coordinate-R3-review-handoff.md','docs/tasks/A04-coordinate-R3-rework.md',
 'docs/evidence/coordinator/heartbeat-20261017-0649/A04-delivery-preflight.json']
workflow=blobs(WF,docs)
for p,b in workflow.items():
    dest=OUT/'inputs/workflow'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
manifest_path='docs/evidence/A04/execution/coordinate-R3/sha256-manifest.json'
report_path='docs/tasks/A04-coordinate-R3-execution-report.md'
main=blobs(TARGET,[manifest_path,report_path]);m=json.loads(main[manifest_path])
assert sha(main[manifest_path])=='634c254021f91ec2f6ed2b0737a3b234f4fb382c4e8878490abedf3b428d1b92'
assert sha(main[report_path])=='9e80fb8e715da518b1e999c951b9798ad5cb0b7dbfc12c09d325ea0f5f850334'
raw=blobs(TARGET,[e['path'] for e in m['files']]);variants=[]
for e in m['files']:
    b=raw[e['path']];assert sha(b)==e['sha256'] and len(b)==e['bytes'],e['path']
    if (AUTHOR/e['path']).read_bytes()!=b:variants.append(e['path'])
assert len(m['files'])==852 and not variants
old_exec=[]
for path in ['docs/evidence/A04/execution/sha256-manifest.json','docs/evidence/A04/execution/coordinate-R1/sha256-manifest.json','docs/evidence/A04/execution/coordinate-R2/sha256-manifest.json']:
    old=json.loads(blobs(BASE,[path])[path]);now=blobs(TARGET,[e['path'] for e in old['files']])
    assert all(sha(now[e['path']])==e['sha256'] and len(now[e['path']])==e['bytes'] for e in old['files'])
    assert blobs(BASE,[path])[path]==blobs(TARGET,[path])[path]
    old_exec.append({'manifest':path,'entries':len(old['files'])})
fixed_prefix='docs/evidence/A04/execution/coordinate-R3/fixed-inputs/'
fixed=[fixed_prefix+'repro_incomplete_rows.py',fixed_prefix+'offline_guard.py']
fixed_data=blobs(TARGET,fixed)
for name in ['repro_incomplete_rows.py','offline_guard.py']:
    path='docs/evidence/A04/review/coordinate-R2/scripts/'+name
    original=blobs(WF,[path])[path]
    assert fixed_data[fixed_prefix+name]==original,name
    dest=OUT/'inputs/unchanged-R2-repro'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(original)
selection=['AGENTS.md','src','tests','config','examples/contracts',report_path,
 manifest_path,
 'docs/evidence/A04/execution/coordinate-R3/process-release.json']
# Six historical files are required by tests only; keep as explicit offline input.
selection += ['docs/evidence/A05/execution/'+n for n in ['reopen-book.json','source-metadata.json','reopen-directory.json','reopen-annotations.json','source-viewer14.jpg','source-viewer173.jpg']]
archive=git('archive','--format=tar.gz',TARGET,*selection)
(OUT/'inputs/frozen-inputs.tar.gz').write_bytes(archive);FROZEN.mkdir(parents=True);inventory=[]
with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as t:
    for member in t.getmembers():
        dest=(FROZEN/member.name).resolve();dest.relative_to(FROZEN.resolve())
        if member.isdir():dest.mkdir(parents=True,exist_ok=True);continue
        assert member.isfile() and '.local/' not in member.name
        b=t.extractfile(member).read();dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
        inventory.append({'path':member.name,'sha256':sha(b),'bytes':len(b)})
save(OUT/'inputs/frozen-tree-manifest.json',{'target_commit':TARGET,'archive_sha256':sha(archive),'files':inventory})
changed=git('diff','--name-only',BASE,TARGET).decode().splitlines()
allowed=('src/annotation/source/usense/','tests/test_a04','docs/evidence/A04/execution/coordinate-R3/','docs/tasks/A04-coordinate-R3-execution-report.md','examples/a04/coordinate-R3/')
assert len(changed)==853 and all(p.startswith(allowed) for p in changed)
unchanged=[]
for p in ['src/annotation/contracts','src/annotation/geometry','src/annotation/source/static','src/annotation/delivery','src/annotation/runtime','config','pyproject.toml','src/annotation/__init__.py','src/annotation/source/__init__.py']:
    before=git('ls-tree',BASE,'--',p);after=git('ls-tree',TARGET,'--',p);assert before==after,p
    unchanged.append({'path':p,'tree_entry':after.decode().strip()})
old_review=[]
for directory,expected in [('docs/evidence/A04/review',5),('docs/evidence/A04/review/coordinate-R1',227),('docs/evidence/A04/review/coordinate-R2',333)]:
    path=ROOT/directory/'sha256-manifest.json';old=json.loads(path.read_text(encoding='utf-8'))
    assert len(old['files'])==expected
    for e in old['files']:
        b=(ROOT/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'],e['path']
    old_review.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes()),'entries':expected})
head=git('rev-parse','HEAD').decode().strip();status=git('status','--porcelain').decode();assert head==TARGET and status==''
save(OUT/'snapshot-check.json',{'target_commit':TARGET,'base_commit':BASE,'implementation_commit':'81d62255b545b88f344849d08011a2a859c49c5e',
 'review_workflow_commit':WF,'raw_and_disk_manifest_entries_verified':852,'manifest_self_sha256':sha(main[manifest_path]),
 'report_sha256':sha(main[report_path]),'disk_variants':variants,'changed_paths':changed,'out_of_scope':[],
 'public_unchanged':unchanged,'old_execution_preservation':old_exec,'old_review_preservation':old_review,
 'unchanged_repro_files':[{'path':p.rsplit('/',1)[1],'sha256':sha(b),'bytes':len(b)} for p,b in fixed_data.items()],
 'workflow_inputs':[{'path':p,'sha256':sha(b),'bytes':len(b)} for p,b in workflow.items()],
 'stage':str(FROZEN),'exported_files':len(inventory),'archive_bytes':len(archive),'author_head':head,'author_status':status,
 'platform_browser_network_profile_or_model_actions':0})
print(json.dumps({'verified_entries':852,'changed_paths':853,'old_execution_entries':sum(e['entries'] for e in old_exec),
 'old_review_entries':sum(e['entries'] for e in old_review),'exported_files':len(inventory),'archive_bytes':len(archive)}))
