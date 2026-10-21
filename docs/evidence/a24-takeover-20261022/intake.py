"""Local A24 intake: verify selected publication, copy once; no site/model calls."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import ast, hashlib, json, shutil, sys

ORIGIN=Path('C:/Users/LIHAOYANG/Documents/Codex/2026-10-21/new-chat/work/a24-review')
HERE=Path(__file__).resolve().parent
SOURCE=ORIGIN/'selected'
TARGET=HERE/'source'
OUT=HERE/'intake.json'
COMMIT='c5aefbc8e995c410b3babf74a251f05a7724a1c2'
PREFIX='docs/handoff/a24-b-takeover-20261021/'
MANIFEST_SHA='a927a201988a277520275509791401e00cc45fdd9edcde140056bf85060633a9'
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(p.read_bytes())

assert not OUT.exists() and not TARGET.exists(), 'NEW_WORKSPACE_REQUIRED'
tree=read(ORIGIN/'tree.json')
assert tree['sha']==COMMIT and tree['truncated'] is False
blobs={x['path']:x for x in tree['tree'] if x['type']=='blob'}
raw=(SOURCE/(PREFIX+'manifest.json')).read_bytes()
assert sha(raw)==MANIFEST_SHA
manifest=json.loads(raw)
paths=[m['path'] for m in manifest['members']]
assert len(paths)==len(set(p.casefold() for p in paths))==manifest['member_count']==522
syntax=0
for m in manifest['members']:
 p=m['path'];posix=PurePosixPath(p)
 assert not posix.is_absolute() and '..' not in posix.parts and ':' not in p and '\\' not in p
 f=SOURCE/p
 assert SOURCE.resolve() in f.resolve().parents and not f.is_symlink()
 b=f.read_bytes();blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 assert len(b)==m['bytes'] and sha(b)==m['sha256'] and blob==m['blob']==blobs[p]['sha'],p
 if p.startswith('src/') and p.endswith('.py'):
  ast.parse(b,filename=p);syntax+=1
source_paths={p for p in blobs if p.startswith('src/')}
assert source_paths==set(manifest['source_tree_paths'])
nested=[]
for spec in manifest['frozen_manifests']:
 b=(SOURCE/spec['path']).read_bytes();assert sha(b)==spec['sha256']
 rows=json.loads(b)['members']
 for row in rows:
  path=SOURCE/(spec.get('member_base','')+row['path']);b=path.read_bytes()
  assert len(b)==row['bytes'] and sha(b)==row['sha256']
 nested.append({'path':spec['path'],'member_checks':len(rows),'passed':True})
state=read(SOURCE/(PREFIX+'state.json'));formal=state['formal_actual']
for file,key in [('machine-result.json','machine_sha256'),('root-disposition.json','root_sha256'),('output-manifest.json','output_manifest_sha256')]:
 assert sha((SOURCE/formal['path']/file).read_bytes())==formal[key]
private=read(SOURCE/(PREFIX+'private-artifact-index.json'))
all_available=[];minimum={}
for row in private['members']:
 candidates=[Path(row['path'])]+([Path(row['snapshot_path'])] if row.get('snapshot_path') else [])
 available=[f for f in candidates if f.is_file()]
 if available:
  all_available.append({'name':available[0].name,'matches':len(available[0].read_bytes())==row['bytes'] and sha(available[0].read_bytes())==row['sha256']})
 name=Path(row['path']).name
 if name in {'directory-snapshot.bin','frames-snapshot.bin','export-snapshot.bin','reviewed-candidate-v1.json','request-accepted-content-v2.json'} or (name.startswith('rect-') and name.endswith('.jpg')):
  key=(name,row['sha256'])
  minimum[key]={'name':name,'bytes':row['bytes'],'sha256':row['sha256'],'available_at_declared_path':bool(available)}
assert len(minimum)==11
for p in paths+[PREFIX+'manifest.json']:
 dest=TARGET/p;dest.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(SOURCE/p,dest)
 assert dest.read_bytes()==(SOURCE/p).read_bytes()
result={
 'schema':'BTemporaryATakeoverIntake/v1','recorded_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
 'publication_branch':'codex/a24-b-takeover-20261021','publication_commit':COMMIT,
 'parent_commit':'edf125961be9cdc1642652c038d99872b1c8cdc7','manifest_sha256':MANIFEST_SHA,
 'selected_publication_members_verified':522,'manifest_self_excluded':True,'local_files_copied_including_manifest':523,
 'source_tree_files_verified':len(source_paths),'python_source_ast_parsed':syntax,
 'nested_manifests_verified':nested,'formal_actual_receipt_hashes_match':True,
 'verification_method':'Raw SHA256, length, Git blob SHA1 against cached full Git tree; live branch head separately checked. Not a full Git checkout or a rerun of the historical actual round.',
 'private_refs_checked':len(private['members']),'private_originals_found_at_declared_paths':all_available,
 'minimal_private_inputs':sorted(minimum.values(),key=lambda x:x['name']),
 'current_schema_bound':False,'local_write_ready':False,'historical_actual_save':state['actual_save'],
 'new_model_calls':0,'new_site_requests':0,'new_site_writes':0,'old_authorities_reused':False,
 'source_machine_runtime':'Python 3.9.13 / Playwright 1.58.0',
 'local_intake_runtime':sys.version,'new_independent_acceptance':False,
 'decision':'CODE_RECEIVED_PRIVATE_INPUTS_MISSING_HOLD',
 'takeover_scope':'Interim A+B engineering owner per current human request; historical A records remain immutable; no automatic activation or inherited site-write permission.'}
OUT.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps({k:result[k] for k in ('publication_commit','selected_publication_members_verified','source_tree_files_verified','python_source_ast_parsed','decision')}))
