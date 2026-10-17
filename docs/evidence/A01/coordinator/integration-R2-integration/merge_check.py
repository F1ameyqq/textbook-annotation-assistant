"""Verify scoped A01 integration against the accepted combination before commit."""
import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path('D:/1800');out=Path(__file__).resolve().parent
delivery='5f872150a237b195f73c78e02e13a91d2f4f46a7'
accepted_main='2d1dc8b97713ee06ec5bf35febe0b894ece584b2'
accepted_tree='0645ac862f79fb4e232e4cfbd5f6bb5055a68d62'
def git(*args):return subprocess.check_output(['git',*args],cwd=root,timeout=90)
def tree(rev):
 result={}
 for row in git('ls-tree','-r','-z',rev).split(b'\0'):
  if row:
   meta,p=row.split(b'\t',1);result[p.decode('utf-8')]=meta.decode('ascii')
 return result
parent=git('rev-parse','HEAD').decode().strip()
state=json.loads((root/'docs/coordination-state.json').read_bytes())
assert state['tasks']['A01']['status']=='ACCEPTED'
assert not git('diff','--name-only').strip() and not git('diff','--cached','--name-only').strip()
fixed,original,live=map(tree,[accepted_tree,accepted_main,parent])
delta={p for p in set(fixed)|set(original) if fixed.get(p)!=original.get(p)}
assert len(delta)==464
predicted=git('merge-tree','--write-tree',parent,delivery).decode().strip()
candidate=tree(predicted)
changed={p for p in set(live)|set(candidate) if live.get(p)!=candidate.get(p)}
assert changed==delta
assert all(candidate.get(p)==fixed.get(p) for p in delta)
assert all(candidate.get(p)==live[p] for p in live if p not in delta)
assert all(candidate[p]==fixed[p] for p in fixed if p.startswith(('src/','tests/','examples/','tools/','config/')))
proc=subprocess.run(['git','merge','--no-commit','--no-ff',delivery],cwd=root,capture_output=True,timeout=120)
(out/'merge-stdout.txt').write_bytes(proc.stdout);(out/'merge-stderr.txt').write_bytes(proc.stderr)
assert proc.returncode==0,proc.stderr
assert git('rev-parse','MERGE_HEAD').decode().strip()==delivery and not git('ls-files','-u').strip()
assert git('write-tree').decode().strip()==predicted
actual={x.decode('utf-8') for x in git('diff','--cached','--name-only','-z').split(b'\0') if x}
assert actual==delta
files=[];representations=[]
for p in sorted(delta):
 blob=git('cat-file','blob',':'+p);assert blob==git('cat-file','blob',accepted_tree+':'+p)
 disk=(root/p).read_bytes();exact=b'\r' not in blob and blob.replace(b'\n',b'\r\n')==disk
 assert disk==blob or exact,p
 if disk!=blob:representations.append(p)
 files.append({'path':p,'git_sha256':hashlib.sha256(blob).hexdigest(),'git_bytes':len(blob),'disk_sha256':hashlib.sha256(disk).hexdigest(),'disk_bytes':len(disk),'disk_equal':disk==blob,'exact_lf_to_crlf':exact})
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'parent':parent,'delivery':delivery,'accepted_main':accepted_main,'accepted_tree':accepted_tree,'actual_index_tree':predicted,'changed_paths':len(delta),'files':files,'exact_lf_to_crlf_paths':representations,'preserved_parent_paths':len(live)-len(set(live)&delta),'same_fixed_production_test_example_tool_config_blobs':True,'merge_exit':proc.returncode,'conflicts':0,'remote_push':False}
with (out/'merge-index-check.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'index_tree':predicted,'changed_paths':len(delta),'CRLF_paths':len(representations),'conflicts':0}))
