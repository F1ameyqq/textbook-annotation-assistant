"""Run the conventional entry once on the actual locally merged checkout."""
import datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path('D:/1800');out=Path(__file__).resolve().parent
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
parents=subprocess.check_output(['git','show','-s','--format=%P',head],cwd=root,text=True).split()
assert len(parents)==2 and parents[1]=='5f872150a237b195f73c78e02e13a91d2f4f46a7'
merge=json.loads((out/'merge-index-check.json').read_bytes())
assert parents[0]==merge['parent']
before={r['path']:hashlib.sha256((root/r['path']).read_bytes()).hexdigest() for r in merge['files']}
env=os.environ.copy();env.update(PYTHONPATH=str(root/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
argv=[sys.executable,'-B',str(root/'examples/a01/integration-R1/verify.py'),str(out/'entry')]
p=subprocess.run(argv,cwd=root,env=env,capture_output=True,timeout=240)
for name in ['stdout','stderr']:(out/(name+'.txt')).write_bytes(getattr(p,name))
receipt={'argv':argv,'cwd':str(root),'exit_code':p.returncode,'head':head}
(out/'command.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
result=json.loads((out/'entry/results.json').read_bytes())
assert p.returncode==0 and result['passed'] and len(result['commands'])==11
assert all(x['exit_code']==0 for x in result['commands'])
expected=[('A01 conventional regression',52),('C01',70),('A02',62),('login offline',8)]
for label,count in expected:
 row=next(x for x in result['commands'] if x['label']==label)
 assert 'Ran '+str(count)+' tests' in row['stderr']
 if label=='A01 conventional regression':assert 'skipped=1' in row['stderr']
 else:assert 'skipped' not in row['stderr']
for path,sha in before.items():assert hashlib.sha256((root/path).read_bytes()).hexdigest()==sha
for path in result['source_files']:
 assert Path(result['source_files'][path]['path']).resolve()==(root/path).resolve()
checks={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'ACTUAL_LOCAL_INTEGRATION_PASS','merge_commit':head,'merge_parents':parents,'argv':argv,'exit_code':p.returncode,'commands':len(result['commands']),'A01':{'run':52,'pass':51,'skip':1,'skip_reason':'Windows file symlink WinError 1314'},'C01':70,'A02':62,'login':8,'URL_cases':5,'consumers':6,'changed_paths_unchanged_after_run':len(before),'scope':'One conventional full entry on actual merged checkout; historical frozen R3 release-byte gate and unchanged 630 geometry matrix not rerun. Offline only.','all_synchronous_children_returned':True,'sessions_to_release':0,'remote_push':False}
with (out/'checks.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(checks,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'merge_commit':head,'result':checks['result'],'commands':11}))
