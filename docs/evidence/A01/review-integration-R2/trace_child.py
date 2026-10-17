"""R2 external observer. Original child arguments, real __file__, and OS Git availability."""
import atexit,hashlib,json,os,runpy,shutil,subprocess,sys
from pathlib import Path
log=Path(sys.argv[1]);root=Path(sys.argv[2]).resolve();arguments=sys.argv[3:]
observed={};initial_sys_path=list(sys.path)
git_probe=dict(argv=['git','--version'],which=shutil.which('git'),PATH=os.environ.get('PATH'),cwd=os.getcwd())
try:
 p=subprocess.run(['git','--version'],capture_output=True)
 git_probe.update(exit_code=p.returncode,stdout=p.stdout.decode('utf-8','replace'),stderr=p.stderr.decode('utf-8','replace'))
except OSError as error:git_probe.update(exception=type(error).__name__,errno=error.errno,winerror=getattr(error,'winerror',None),actual_OS_spawn_failed=True)
def profile(frame,event,arg):
 if event!='call' or frame.f_code.co_name!='<module>':return
 name=str(frame.f_globals.get('__name__',''));value=frame.f_globals.get('__file__')
 if not value:return
 path=Path(value).resolve()
 try:relative=path.relative_to(root).as_posix();origin='FIXED_SNAPSHOT'
 except ValueError:
  if name=='annotation' or name.startswith('annotation.'):relative='OUTSIDE:'+str(path);origin='UNEXPECTED_ANNOTATION'
  elif path.name=='identity.py' and 'identity' in name:relative=None;origin='GENERATED_IDENTITY_COPY'
  else:return
 if path.is_file():observed[str(path)]=dict(module=name,actual___file__=str(value),resolved_path=str(path),relative=relative,origin=origin,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def finish():
 sys.setprofile(None);loaded=[]
 for name,module in list(sys.modules.items()):
  if name=='annotation' or name.startswith('annotation.'):
   value=getattr(module,'__file__',None)
   if not value:continue
   path=Path(value).resolve()
   try:relative=path.relative_to(root).as_posix()
   except ValueError:relative='OUTSIDE:'+str(path)
   loaded.append(dict(module=name,actual___file__=str(value),resolved_path=str(path),relative=relative,origin='SYS_MODULES',sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
 record=dict(original_python_arguments=arguments,root=str(root),cwd=os.getcwd(),sys_path_initial=initial_sys_path,sys_path_final=list(sys.path),git_probe=git_probe,executed_modules=list(observed.values()),loaded_annotation_modules=loaded)
 log.parent.mkdir(parents=True,exist_ok=True)
 with log.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
atexit.register(finish);sys.setprofile(profile)
if arguments[0]=='-m':
 sys.argv=[arguments[1],*arguments[2:]];sys.path[0]=os.getcwd();runpy.run_module(arguments[1],run_name='__main__',alter_sys=True)
else:
 script=Path(arguments[0]).resolve();sys.argv=[str(script),*arguments[1:]];sys.path[0]=str(script.parent);runpy.run_path(str(script),run_name='__main__')
