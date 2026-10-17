import hashlib,json,subprocess
from pathlib import Path
root=Path('D:/1800');final='a1e5be00909172429d792b6c41bdaf384258694e';base='38aca9dcc8d027409b95193e9cc142c2336b76d3';parent='91e48498376bdafe606d8ac596da810abe3b5afd'
def git(*args,input=None):return subprocess.check_output(['git',*args],cwd=root,input=input,timeout=60)
assert git('rev-parse','HEAD').decode().strip()==parent
assert git('rev-parse','MERGE_HEAD').decode().strip()==final
assert not git('ls-files','-u').strip()
expected=sorted(x.decode() for x in git('diff','--name-only','-z',base,final).split(b'\0') if x)
actual=sorted(x.decode() for x in git('diff','--cached','--name-only','-z').split(b'\0') if x)
assert actual==expected and len(actual)==188
files=[];disk_differences=[]
for p in expected:
 staged=git('cat-file','blob',':'+p);frozen=git('cat-file','blob',final+':'+p);assert staged==frozen,p
 disk=(root/p).read_bytes()
 if disk!=staged:disk_differences.append(p)
 files.append({'path':p,'sha256':hashlib.sha256(staged).hexdigest(),'bytes':len(staged),'disk_equal':disk==staged})
assert not disk_differences,disk_differences
out=root/'.local/stages/coordinator/hb-0351-merge-check.json';out.write_text(json.dumps({'parent':parent,'final_commit':final,'changed_paths':len(actual),'merged_index_tree':git('write-tree').decode().strip(),'raw_git_index_disk_equal':len(files),'files':files,'unresolved_conflicts':0,'remote_push':False},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'changed_paths':len(actual),'raw_git_index_disk_equal':len(files),'conflicts':0}))
