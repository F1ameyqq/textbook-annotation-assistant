import concurrent.futures,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent;info=json.loads((OUT/'bootstrap.json').read_text(encoding='utf-8'))
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def dump(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def environment(tree,temp,no_git):
 env=dict(os.environ,PYTHONPATH=str(tree/'src'),PYTHONDONTWRITEBYTECODE='1',TMP=str(temp),TEMP=str(temp),TMPDIR=str(temp))
 if no_git:
  env['PATH']=r'C:\Windows\System32;C:\Windows'
  for key in list(env):
   if key.startswith(('GIT_CONFIG','GIT_EXEC','GIT_DIR','GIT_WORK_TREE')):env.pop(key)
 return env
def command(folder,args,cwd,env):
 p=subprocess.run(args,cwd=cwd,env=env,capture_output=True)
 folder.mkdir(parents=True,exist_ok=False)
 (folder/'stdout.txt').write_bytes(p.stdout);(folder/'stderr.txt').write_bytes(p.stderr)
 record=dict(argv=args,cwd=str(cwd),exit_code=p.returncode,environment_selected={k:env[k] for k in ('PYTHONPATH','PATH','PYTHONDONTWRITEBYTECODE','TMP','TEMP','TMPDIR')},git_available=shutil.which('git',path=env['PATH']),stdout='stdout.txt',stderr='stderr.txt')
 dump(folder/'command.json',record)
 return p,record
def run(label):
 tree=Path(info[label]);folder=OUT/'runtime'/label;temp=Path(info['temporary'])/label;temp.mkdir()
 env=environment(tree,temp,label=='raw')
 if label=='raw':assert not (tree/'.git').exists() and shutil.which('git',path=env['PATH']) is None
 argv=[sys.executable,'-B',str(OUT/'trace_entry.py'),str(tree),str(folder/'entry'),str(folder/'imports')]
 # Trace creates its own directories; the command receipt directory is separate.
 p,receipt=command(folder/'launch',argv,temp,env)
 issues=[]
 if p.returncode:issues.append('entry nonzero '+str(p.returncode))
 result=read(folder/'entry/results.json')
 commands=result['commands']
 if len(commands)!=11 or not result['passed'] or any(c['exit_code'] for c in commands):issues.append('incomplete/failed full entry')
 expected_counts=[52,70,62,8]
 suite=[]
 for c,expected in zip(commands[:4],expected_counts):
  found=re.search(r'Ran (\d+) tests?',c['stderr']);count=int(found[1]) if found else None
  skipped=c['stderr'].count("skipped 'host cannot create file symlinks; WinError=1314'")
  suite.append(dict(label=c['label'],run=count,exit_code=c['exit_code'],permission_skips=skipped))
  if count!=expected:issues.append('wrong count '+c['label'])
 imports=[];traces=sorted((folder/'imports').glob('[0-9][0-9].json'))
 if len(traces)!=11:issues.append('trace count')
 expected_index=read(OUT/('checkout-input-index.json' if label=='checkout' else 'raw-input-index.json'))
 expected={r['path']:r.get('disk_sha256',r.get('sha256')) for r in expected_index}
 for trace in traces:
  data=read(trace);probe=data['git_probe']
  if label=='raw' and not (probe['which'] is None and probe.get('actual_OS_spawn_failed') and probe['exception']=='FileNotFoundError'):issues.append('raw child Git probe '+trace.name)
  for item in data['executed_modules']+data['loaded_annotation_modules']:
   if item['origin']=='GENERATED_IDENTITY_COPY':
    if item['sha256']!=expected['examples/a02/R1/identity.py']:issues.append('generated identity bytes')
   elif item['relative'].startswith('OUTSIDE:') or expected.get(item['relative'])!=item['sha256']:issues.append('outside/wrong actual import '+str(item))
   imports.append(dict(trace=trace.relative_to(OUT).as_posix(),**item))
 required=['src/annotation/source/static/importer.py','src/annotation/source/static/consistency.py','src/annotation/geometry/__init__.py','src/annotation/contracts/models.py','examples/a02/R1/identity.py','tests/test_a02_r1.py','tests/test_a02_portability_r2.py']
 required += [p.relative_to(tree).as_posix() for pattern in ('test_a01*.py','test_contracts*.py') for p in (tree/'tests').glob(pattern)]
 for relative in required:
  if not any(i['relative']==relative for i in imports):issues.append('missing actual execution '+relative)
 changes=[r['path'] for r in expected_index if not (tree/r['path']).is_file() or sha(tree/r['path'])!=expected[r['path']]]
 if changes:issues.append('input changed')
 summary=dict(label=label,entry_exit_code=p.returncode,full_entry_passed=result['passed'],child_count=len(commands),child_exits=[dict(label=c['label'],exit_code=c['exit_code']) for c in commands],suites=suite,actual_import_observations=len(imports),required_actual_files=required,generated_identity_copies=sum(i['origin']=='GENERATED_IDENTITY_COPY' for i in imports),input_files=len(expected_index),disk_changes=changes,git_available=receipt['git_available'],raw_has_dot_git=(tree/'.git').exists(),issues=issues)
 dump(folder/'actual-imports.json',dict(observations=imports));dump(folder/'summary.json',summary)
 return summary
def bare_case():
 tree=Path(info['raw']);temp=Path(info['temporary'])/'bare-case';temp.mkdir();env=environment(tree,temp,True);cwd=tree/'tests'
 probe,_=command(OUT/'bare-case/environment-probe',[sys.executable,'-B',str(OUT/'no_git_probe.py')],cwd,env)
 p,receipt=command(OUT/'bare-case/test',[sys.executable,'-B','-m','unittest','test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head','-v'],cwd,env)
 stderr=p.stderr.decode('utf-8','replace');found=re.search(r'Ran (\d+) tests?',stderr)
 result=dict(exit_code=p.returncode,run=int(found[1]) if found else None,skipped=bool(re.search(r'skipp?ed',stderr,re.I)),probe_exit_code=probe.returncode,git_available=receipt['git_available'],original_case='I1-GIT-01',observer='none; original unittest argv')
 result['passed']=result['exit_code']==0 and result['run']==1 and not result['skipped'] and result['probe_exit_code']==0 and result['git_available'] is None
 dump(OUT/'bare-case/summary.json',result);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 jobs=[pool.submit(run,'checkout'),pool.submit(run,'raw'),pool.submit(bare_case)]
 results=[job.result() for job in jobs]
passed=all(not item['issues'] for item in results[:2]) and results[2]['passed']
dump(OUT/'runtime-summary.json',dict(passed=passed,forms=results[:2],bare_case=results[2]))
print(json.dumps(dict(passed=passed,forms=results[:2],bare_case=results[2]),ensure_ascii=False))
raise SystemExit(0 if passed else 1)
