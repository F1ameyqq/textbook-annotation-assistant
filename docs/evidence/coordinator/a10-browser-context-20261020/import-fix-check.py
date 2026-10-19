from pathlib import Path
import ast,hashlib,json,sys
p=Path('D:/1800/docs/evidence/A10/system-proxy-observation-import-fix')
tree=ast.parse((p/'probe.py').read_bytes())
f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='supervise')
t=next(n for n in f.body if isinstance(n,ast.Try))
start=next(i for i,n in enumerate(t.body) if isinstance(n,ast.ImportFrom) and n.module=='importlib.util')
end=next(i for i,n in enumerate(t.body) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='OwnedJob' for x in n.targets))
ns={'HERE':p}
exec(compile(ast.Module(body=t.body[start:end+1],type_ignores=[]),'<exact-import-block>','exec'),ns)
assert isinstance(ns['OwnedJob'],type)
assert sys.flags.isolated==1
assert str(p) not in sys.path
report={'status':'PASS_LOCAL_IMPORT_ONLY','checks':['isolated_mode_active','script_directory_not_in_sys_path','exact_new_import_block_loads_bound_OwnedJob_class'],'job_constructed':False,'child_started':False,'probe_worker_or_supervise_called':False,'network':0,'browser_profile_login_business':0,'probe_sha256':hashlib.sha256((p/'probe.py').read_bytes()).hexdigest(),'owned_job_sha256':hashlib.sha256((p/'owned_job.py').read_bytes()).hexdigest()}
with (p/'static-check.json').open('xb') as out:out.write((json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report))
