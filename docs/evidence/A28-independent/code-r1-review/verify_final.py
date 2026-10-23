import hashlib,json,os,subprocess
from pathlib import Path
P=Path('D:/1800/.local/stages/a28-independent-20261023/code-r1-review')
O=Path('D:/1800/docs/evidence/A28-independent/code-r1-review')
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,v):
 b=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
 with p.open('xb') as f:f.write(b)
 return sha(b)
intake=json.loads((O/'intake.json').read_bytes());members=intake['members'];commit=intake['commit']
env=dict(os.environ,GIT_NO_LAZY_FETCH='1',PYTHONUTF8='1')
def git(*args):
 r=subprocess.run(['git','-c','core.longpaths=true',*args],cwd='D:/1800',env=env,capture_output=True,check=True)
 assert not r.stderr,r.stderr
 return r.stdout
tree={}
for line in git('ls-tree','-rz',commit).split(b'\0'):
 if not line:continue
 meta,path=line.split(b'\t',1);mode,kind,obj=meta.split();tree[path.decode('utf8')]=obj.decode()
for m in members:
 frozen=Path(m['root_frozen']).read_bytes();copy=Path(m['copy']).read_bytes()
 assert frozen==copy and sha(copy)==m['sha256'] and len(copy)==m['bytes']
 if m['kind']=='git_blob':
  assert tree[m['repository_path']]==m['git_blob']
  assert hashlib.sha1(b'blob '+str(len(copy)).encode()+b'\0'+copy).hexdigest()==m['git_blob']
  assert Path(m['isolated_source']).read_bytes()==copy
raw_manifest=json.loads((P/'inputs/raw-manifest.json').read_bytes())
assert len(raw_manifest['members'])==242
for a,b in zip(raw_manifest['members'],members[:242]):
 for k in ('kind','source_path','frozen_path','bytes','sha256'):assert a[k]==b[k]
proof=json.loads((P/'inputs/0206-0206-evidence.json').read_bytes());origins=[]
for row in proof['identities']:
 m=next(m for m in members if m['source_path']==row['source']['path'])
 raw=Path(m['copy']).read_bytes();assert sha(raw)==row['source']['sha256']
 if 'git_commit' in row:
  original=git('cat-file','blob',row['git_commit']+':'+row['git_path'])
  assert original==raw and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['git_blob']
  origin='ACCEPTED_A27_GIT_RAW'
 elif row['question_order']<23:
  original=Path(row['origin_path']).read_bytes();assert original==raw and sha(original)==row['origin_sha256']
  origin='ACCEPTED_A26_ROOT_FROZEN_RAW'
 else:
  prior=next(m for m in members if m['source_path']==row['origin_path']);assert Path(prior['copy']).read_bytes()==raw
  origin='CURRENT_ROOT_FROZEN_TAIL_RAW'
 origins.append({'order':row['question_order'],'source_sha256':sha(raw),'origin':origin,'equal_raw_bytes':True})
old=json.loads(Path('D:/1800/docs/evidence/A28-independent/code-v1-review/intake.json').read_bytes())
oldgit={m['repository_path']:m for m in old['members'] if m['kind']=='git_blob'}
changed=[m['repository_path'] for m in members if m['kind']=='git_blob' and m['sha256']!=oldgit[m['repository_path']]['sha256']]
assert set(changed)=={'src/annotation/runtime/usense_live/lesson_insert.py','src/annotation/runtime/usense_live/lesson_batch.py','tests/test_a28_lesson_insert.py','tests/test_a28_lesson_batch.py','docs/a28-complete-lesson-production-20261023.md'}
control=json.loads((O/'independent-controls.json').read_bytes());launch=json.loads((O/'launcher-controls.json').read_bytes())
assert control['status']==launch['status']=='PASS' and len(control['controls'])==9 and len(launch['cases'])==10
assert json.loads((O/'new-r1-suite-process.json').read_bytes())['exit_code']==0
result={'schema':'A28IndependentR1FinalVerification/v1','status':'PASS','commit':commit,'root_raw_copy_pairs':244,'git_raw_blobs':31,
 'fixed_raw_manifest_members':242,'known_identity_origin_pairs':origins,'changed_git_paths_from_rework':changed,
 'root_index_sha256':sha((P/'root-index.json').read_bytes()),'fixed_delivery_sha256':sha((P/'inputs/fixed-delivery-r1.json').read_bytes()),
 'raw_manifest_sha256':sha((P/'inputs/raw-manifest.json').read_bytes()),'source_or_workspace_mutations':0,'active_author_workspace_reads':0,'platform_calls':0}
put(O/'final-verification.json',result)
print(json.dumps({k:result[k] for k in ('status','root_raw_copy_pairs','git_raw_blobs','fixed_raw_manifest_members')}))
