"""Unchanged combined entry, externally observed Python children; no source edits."""
import json,runpy,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();destination=Path(sys.argv[2]).resolve();logs=Path(sys.argv[3]).resolve()
logs.mkdir(parents=True,exist_ok=False);observer=Path(__file__).with_name('trace_child.py').resolve()
original_run=subprocess.run;launches=[]
def run(args,*pos,**kw):
 original=list(map(str,args));actual=original
 if Path(original[0]).resolve()==Path(sys.executable).resolve():
  assert original[1]=='-B'
  trace=logs/('%02d.json'%(len(launches)+1))
  actual=[sys.executable,'-B',str(observer),str(trace),str(root),*original[2:]]
  launches.append(dict(original_argv=original,executed_argv=actual,cwd=str(kw.get('cwd')),trace=str(trace)))
 return original_run(actual,*pos,**kw)
subprocess.run=run
sys.argv=[str(root/'examples/a01/integration-R1/verify.py'),str(destination)]
try:runpy.run_path(sys.argv[0],run_name='__main__')
finally:
 with (logs/'launches.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(launches,ensure_ascii=False,indent=2)+'\n')
