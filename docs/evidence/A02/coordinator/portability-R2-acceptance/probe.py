"""Coordinator bounded probe; uses actual subprocess calls and records imports."""
import hashlib,importlib.util,json,os,shutil,subprocess,sys,unittest
from pathlib import Path
root=Path(sys.argv[1]).resolve(); mode=sys.argv[2]; repo=Path(sys.argv[3]).resolve(); commit=sys.argv[4]
path=root/'examples/a02/R1/identity.py'
spec=importlib.util.spec_from_file_location('coordinator_identity',path); helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
def emit(x):print(json.dumps(x,ensure_ascii=True),flush=True)
emit({'mode':mode,'cwd':str(Path.cwd()),'root':str(root),'git_executable':shutil.which('git'),'identity_import':helper.__file__,'identity_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
if mode in ('original','suite'):
 sys.path[:0]=[str(root/'src'),str(root/'tests')]
 loader=unittest.defaultTestLoader
 suite=loader.loadTestsFromName('test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head') if mode=='original' else loader.discover(str(root/'tests'),pattern='test_a02*.py')
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 imports={}
 for name,module in list(sys.modules.items()):
  p=getattr(module,'__file__',None)
  if p and (name.startswith('annotation') or name.startswith('test_a02')):
   p=Path(p).resolve();p.relative_to(root);imports[name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 emit({'event':'test-result','run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'imports':imports})
 assert result.testsRun==(1 if mode=='original' else 62) and not result.skipped and result.wasSuccessful()
elif mode=='binding-noGit':
 assert shutil.which('git') is None
 try:subprocess.run(['git','--version'],capture_output=True,check=True)
 except FileNotFoundError:emit({'actual_os_spawn':'FileNotFoundError'})
 else:raise AssertionError('Git unexpectedly runnable')
 helper.source_binding(root,commit,repo)
 raise AssertionError('unexpected successful binding')
elif mode=='normal-and-second-failure':
 assert helper.git_identity(repo)['checkout_commit']==commit
 emit({'normal_identity':commit})
 actual_run=subprocess.run;events=[]
 def recording_run(argv,*a,**kw):
  try:value=actual_run(argv,*a,**kw)
  except OSError as error:events.append({'argv':argv,'error':type(error).__name__});raise
  events.append({'argv':argv,'returncode':value.returncode})
  if argv==['git','rev-parse','--show-toplevel'] and value.returncode==0:os.environ['PATH']=sys.argv[5]
  return value
 subprocess.run=recording_run
 value=helper.git_identity(repo)
 emit({'second_identity':value,'actual_calls':events,'git_after':shutil.which('git')})
 assert value['checkout_commit'] is None and 'unknown' in value['status']
 assert len(events)==2 and events[0]['returncode']==0 and events[1]['error']=='FileNotFoundError'
else:raise ValueError(mode)
