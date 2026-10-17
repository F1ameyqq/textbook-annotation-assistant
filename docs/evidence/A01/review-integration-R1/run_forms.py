import concurrent.futures,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
info=json.loads((OUT/'bootstrap.json').read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def run(label):
 tree=Path(info[label]);evidence=OUT/'runtime'/label;evidence.mkdir(parents=True,exist_ok=False)
 temp=Path(info['temporary'])/label;temp.mkdir()
 env=dict(os.environ,PYTHONPATH=str(tree/'src'),PYTHONDONTWRITEBYTECODE='1',TMP=str(temp),TEMP=str(temp),TMPDIR=str(temp))
 if label=='raw':env['PATH']=r'C:\Windows\System32;C:\Windows'
 available_git=shutil.which('git',path=env['PATH'])
 if label=='raw':assert available_git is None and not (tree/'.git').exists()
 argv=[sys.executable,'-B',str(OUT/'trace_entry.py'),str(tree),str(evidence/'entry'),str(evidence/'imports')]
 process=subprocess.run(argv,cwd=temp,env=env,capture_output=True)
 (evidence/'stdout.txt').write_bytes(process.stdout);(evidence/'stderr.txt').write_bytes(process.stderr)
 dump(evidence/'command.json',dict(argv=argv,cwd=str(temp),environment_selected={k:env[k] for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE','TMP','TEMP','TMPDIR','PATH')},git_available=available_git,exit_code=process.returncode,stdout='stdout.txt',stderr='stderr.txt',observation='Unchanged entry via runpy; original Python child arguments wrapped by external trace_child.py, no snapshot files modified.'))
 assert process.returncode==0,process.stderr.decode('utf-8','replace')
 result=json.loads((evidence/'entry/results.json').read_text(encoding='utf-8'))
 assert result['passed'] and len(result['commands'])==11 and all(c['exit_code']==0 for c in result['commands'])
 imported=[]
 for path in sorted((evidence/'imports').glob('[0-9][0-9].json')):
  record=json.loads(path.read_text(encoding='utf-8'))
  for item in record['executed_modules']+record['loaded_annotation_modules']:
   assert not item['relative'].startswith('OUTSIDE:'),item
   assert sha(Path(item['resolved_path']))==item['sha256'],item
   imported.append(dict(trace=str(path.relative_to(OUT)),**item))
 needed=('src/annotation/source/static/importer.py','src/annotation/source/static/consistency.py','src/annotation/geometry/__init__.py','src/annotation/contracts/models.py','tests/test_a01_rework_r3.py','tests/test_a01_integration_r1.py')
 for relative in needed:assert any(x['relative']==relative for x in imported),relative
 original_index=json.loads((OUT/('checkout-input-index.json' if label=='checkout' else 'raw-input-index.json')).read_text(encoding='utf-8'))
 changes=[]
 for row in original_index:
  expected=row.get('disk_sha256',row.get('sha256'));p=tree/row['path']
  if not p.is_file() or sha(p)!=expected:changes.append(row['path'])
 assert not changes,changes
 summary=dict(label=label,exit_code=process.returncode,child_commands=len(result['commands']),all_child_exit_zero=True,import_observations=len(imported),required_actual_files=list(needed),input_files=len(original_index),disk_changes=changes,git_available=available_git)
 dump(evidence/'actual-imports.json',dict(observations=imported));dump(evidence/'summary.json',summary)
 return summary
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,('checkout','raw')))
dump(OUT/'runtime-summary.json',results)
print(json.dumps(results,ensure_ascii=False))
