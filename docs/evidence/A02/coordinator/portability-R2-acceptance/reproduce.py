"""Bounded pre-acceptance reproduction on fresh, verified raw Git blobs."""
import hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
root=Path('D:/1800');repo=Path('C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800')
commit='a1e5be00909172429d792b6c41bdaf384258694e';out=Path(__file__).resolve().parent
stage=root/'.local/stages/A02-coordinator-portability-R2';stage.mkdir(exist_ok=False)
rawroot=stage/'raw source';rawroot.mkdir();empty=stage/'empty-bin';empty.mkdir()
selection=['src/annotation','examples/a02','tests/fixtures/a02','tests/fixtures/contracts/unknown','tests/test_a02.py','tests/test_a02_r1.py','tests/test_a02_portability_r2.py','pyproject.toml']
rows=subprocess.check_output(['git','ls-tree','-r','-z',commit,*selection],cwd=repo).split(b'\0');entries=[]
for row in rows:
 if not row:continue
 meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert mode in (b'100644',b'100755') and kind==b'blob'
 path=name.decode('utf-8');raw=subprocess.check_output(['git','cat-file','blob',oid.decode()],cwd=repo)
 dest=rawroot/path;dest.resolve().relative_to(rawroot.resolve());dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 entries.append({'path':path,'oid':oid.decode(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
for key in list(env):
 if key.startswith('GIT_'):env.pop(key)
receipts=[]
for mode,no_git,expected in [('original',True,0),('binding-noGit',True,1),('normal-and-second-failure',False,0)]:
 child=env.copy()
 if no_git:child['PATH']=str(empty)
 argv=[sys.executable,'-B',str(out/'probe.py'),str(rawroot),mode,str(repo),commit,str(empty)]
 run=subprocess.run(argv,cwd=stage,env=child,capture_output=True,timeout=60)
 for channel in ('stdout','stderr'):(out/(mode+'-'+channel+'.txt')).write_bytes(getattr(run,channel))
 receipts.append({'mode':mode,'argv':argv,'cwd':str(stage),'no_git_path':no_git,'exit_code':run.returncode,'expected_exit_code':expected,'stdout':mode+'-stdout.txt','stderr':mode+'-stderr.txt'})
 assert run.returncode==expected,(mode,run.returncode)
 if mode=='binding-noGit':assert b'identity repository must be an actual Git top-level' in run.stderr
for e in entries:assert hashlib.sha256((rawroot/e['path']).read_bytes()).hexdigest()==e['sha256']
result={'at':datetime.now(timezone.utc).isoformat(),'target_commit':commit,'result':'BOUNDED_REPRODUCTION_PASS','raw_source_root':str(rawroot),'raw_source_files':entries,'commands':receipts,'original_single_test_without_git':{'run':1,'skipped':0,'exit_code':0},'binding_without_git_rejected':True,'normal_identity_and_second_real_spawn_failure_verified':True,'full_suite_rerun':False,'own_synchronous_children_returned':True,'background_helpers_or_browser_started':False,'platform_model_calls':0,'scope':'Exact A02 portability patch only; no A01 combined entry, recovery or platform acceptance.'}
with (out/'coordinator-check.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'result':result['result'],'raw_files':len(entries),'exit_codes':[x['exit_code'] for x in receipts]}))
