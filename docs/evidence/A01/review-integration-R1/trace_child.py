"""External observation only: execute original Python arguments and record real module globals."""
import atexit,hashlib,json,os,runpy,sys
from pathlib import Path

log=Path(sys.argv[1]);root=Path(sys.argv[2]).resolve();args=sys.argv[3:]
executed={}
initial_path=list(sys.path)
def profile(frame,event,arg):
 if event=='call' and frame.f_code.co_name=='<module>':
  file=frame.f_globals.get('__file__')
  if file:
   path=Path(file).resolve()
   try:rel=path.relative_to(root).as_posix()
   except ValueError:
    if str(frame.f_globals.get('__name__','')).startswith('annotation'):rel='OUTSIDE:'+str(path)
    else:return
   executed[str(path)]=dict(module=frame.f_globals.get('__name__'),actual___file__=str(file),resolved_path=str(path),relative=rel,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def finish():
 sys.setprofile(None)
 modules=[]
 for name,module in list(sys.modules.items()):
  if name=='annotation' or name.startswith('annotation.'):
   value=getattr(module,'__file__',None)
   if value:
    p=Path(value).resolve()
    try:relative=p.relative_to(root).as_posix()
    except ValueError:relative='OUTSIDE:'+str(p)
    modules.append(dict(module=name,actual___file__=str(value),resolved_path=str(p),relative=relative,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 data=dict(original_python_arguments=args,root=str(root),cwd=os.getcwd(),sys_path_initial=initial_path,sys_path_final=list(sys.path),executed_modules=list(executed.values()),loaded_annotation_modules=modules)
 log.parent.mkdir(parents=True,exist_ok=True)
 with log.open('x',encoding='utf-8',newline='\n') as handle:handle.write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
atexit.register(finish)
sys.setprofile(profile)
if args[0]=='-m':
 sys.argv=[args[1],*args[2:]];sys.path[0]=os.getcwd();runpy.run_module(args[1],run_name='__main__',alter_sys=True)
else:
 script=Path(args[0]).resolve();sys.argv=[str(script),*args[1:]];sys.path[0]=str(script.parent);runpy.run_path(str(script),run_name='__main__')
