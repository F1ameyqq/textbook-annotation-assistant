"""Frozen delivery identity/scope preflight only; no functionality execution."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path('D:/1800');W=Path('C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800')
BASE='38aca9dcc8d027409b95193e9cc142c2336b76d3';PATCH='ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8';FINAL='a1e5be00909172429d792b6c41bdaf384258694e'
MANIFEST='docs/evidence/A02/execution/portability-R2/sha256-manifest.json';REPORT='docs/tasks/A02-portability-R2-execution-report.md'
def sha(x):return hashlib.sha256(x).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=W,timeout=30)
def tree(commit):
 result={}
 for row in git('ls-tree','-r','-z',commit).split(b'\0'):
  if not row:continue
  meta,path=row.split(b'\t',1);result[path.decode('utf-8')]=meta.split()[2].decode()
 return result
def blobs(commit,names):
 raw=subprocess.check_output(['git','cat-file','--batch'],cwd=W,input=''.join(commit+':'+p+'\n' for p in names).encode('utf-8'),timeout=30)
 offset=0;out={}
 for path in names:
  end=raw.index(b'\n',offset);size=int(raw[offset:end].split()[2]);out[path]=raw[end+1:end+1+size];offset=end+size+2
 return out
assert git('rev-parse','HEAD').decode().strip()==FINAL
assert not git('status','--porcelain=v1','--untracked-files=all').strip()
git('merge-base','--is-ancestor',BASE,PATCH);git('merge-base','--is-ancestor',PATCH,FINAL)
b,p,f=tree(BASE),tree(PATCH),tree(FINAL)
assert set(b)<=set(f)
modified=[x for x in b if b[x]!=f[x]];assert modified==['examples/a02/R1/identity.py'],modified
changed=sorted(x for x in f if x not in b or f[x]!=b[x])
def allowed(x):return x in ('examples/a02/R1/identity.py','tests/test_a02_portability_r2.py',REPORT) or x.startswith(('examples/a02/portability-R2/','docs/evidence/A02/execution/portability-R2/'))
assert all(allowed(x) for x in changed)
packaging=[x for x in f if x not in p or f[x]!=p[x]]
assert all(x==REPORT or x.startswith('docs/evidence/A02/execution/portability-R2/') for x in packaging)
data=blobs(FINAL,changed);m=json.loads(data[MANIFEST]);expected={**m['files_sha256'],**m['patch_source_sha256']}
assert set(expected)|{MANIFEST}==set(changed)
disk_git=[]
for path,h in expected.items():
 assert sha(data[path])==h,('Git hash',path)
 disk=(W/path).read_bytes();assert sha(disk)==h,('disk hash',path)
 disk_git.append({'path':path,'bytes':len(disk),'sha256':h})
assert data[MANIFEST]==(W/MANIFEST).read_bytes()
assert sha(data[REPORT])=='afb339fda44156cbb2ba1aaf4589b65e0746afedc3b2f3aa2a88403eae9b1a34'
before=data['examples/a02/R1/identity.py'];old=git('cat-file','blob',BASE+':examples/a02/R1/identity.py')
assert before.split(b'def source_binding',1)[1]==old.split(b'def source_binding',1)[1]
ignored=subprocess.run(['git','check-ignore','--no-index','--stdin','-z'],cwd=W,input=('\0'.join(changed)+'\0').encode(),capture_output=True,timeout=30)
assert ignored.returncode in (0,1)
result={'observed_at':datetime.now(timezone.utc).isoformat(),'status':'READY_FOR_INDEPENDENT_REVIEW','base_commit':BASE,'patch_commit':PATCH,'final_commit':FINAL,'working_tree_clean':True,
 'only_existing_changed':modified,'changed_paths':len(changed),'packaging_only_paths':len(packaging),'old_git_files_preserved':len(b)-1,
 'manifest_entries':len(expected),'manifest_sha256':sha(data[MANIFEST]),'report_sha256':sha(data[REPORT]),'manifest_and_changed_path_coverage_exact':True,'disk_git_sha_equal':len(disk_git),
 'source_binding_function_raw_unchanged':True,'changed_total_bytes':sum(map(len,data.values())),'ignored_but_tracked_paths':[x.decode() for x in ignored.stdout.split(b'\0') if x],
 'verified_files':disk_git,'session_release_basis':'Frozen completed report: all synchronous child processes returned, no own background helpers/browser; not an independent OS scan',
 'tests_or_functional_acceptance_run':False,'production_source_changed':False,'A01_A04_released':False,'remote_push':False}
out=Path(__file__).with_name('audit.json')
with out.open('x',encoding='utf-8',newline='\n') as handle:json.dump(result,handle,ensure_ascii=False,indent=2);handle.write('\n')
print(json.dumps({k:result[k] for k in ('status','changed_paths','manifest_entries','manifest_sha256','old_git_files_preserved','disk_git_sha_equal','changed_total_bytes')}))
