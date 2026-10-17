"""Materialize a wheel probe outside this Git checkout, record, then clean own temp."""
import json,os,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R7-readonly-codec';sys.path.insert(0,str(EX))
from ops import FIX,OUT,load,sha,write
from child_audit import install
wheel_info=load(OUT/'wheel-result.json')
if wheel_info['status']=='NOT_RUN':
    write(OUT/'isolation-result.json',{'status':'NOT_RUN','reason':'wheel unavailable; no installation attempted'});sys.exit(0)
wheel=ROOT/wheel_info['wheel'];assert sha(wheel.read_bytes())==wheel_info['wheel_sha256']
folder=Path(tempfile.mkdtemp(prefix='a03-r7-isolation-')).resolve();temp_root=Path(tempfile.gettempdir()).resolve();assert folder.is_relative_to(temp_root)and not folder.is_relative_to(ROOT)
shutil.copyfile(wheel,folder/wheel.name)
with zipfile.ZipFile(folder/wheel.name)as z:z.extractall(folder/'unpacked')
for name in('registration-positive','target-tuple-negative'):shutil.copytree(FIX/name,folder/'cases'/name)
probe=folder/'probe.py';shutil.copyfile(EX/'isolated_probe.py',probe)
write(OUT/'isolation-launch-context.json',{'outside_directory':str(folder),'outside_repository':True,'wheel_sha256':sha(wheel.read_bytes()),'probe_sha256':sha(probe.read_bytes()),'cwd':str(folder),'PYTHONPATH':'removed','temporary_cleanup':'only owned directory after completion'})
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
children,restore=install(os.environ['A03_R7_RUN_ID'])
try:completed=subprocess.run([sys.executable,'-X','utf8','-B',str(probe)],cwd=folder,env=env,capture_output=True,timeout=30)
finally:restore()
assert all(p.poll()is not None for p in children)
if completed.returncode:
    write(OUT/'isolation-result.json',{'status':'FAILED','exit_code':completed.returncode,'outside_directory_retained':str(folder)});sys.stdout.buffer.write(completed.stdout);sys.stderr.buffer.write(completed.stderr);sys.exit(1)
result=json.loads(completed.stdout);write(OUT/'isolation-result.json',result)
assert folder.resolve().is_relative_to(temp_root)and not folder.resolve().is_relative_to(ROOT)and folder.name.startswith('a03-r7-isolation-');shutil.rmtree(folder)
print(json.dumps({'status':result['status'],'product_module_file':result['product_module_file'],'outside_temporary_directory_removed':True,'cases':len(result['observations'])}))
