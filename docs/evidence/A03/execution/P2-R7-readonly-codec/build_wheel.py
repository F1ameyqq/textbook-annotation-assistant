"""Use the installed backend offline in an isolated local staging directory."""
import json,os,shutil,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R7-readonly-codec';sys.path.insert(0,str(EX))
from ops import OUT,PRODUCT,load,sha,write
tools=load(OUT/'local-build-tools.json')
if not tools['versions']['setuptools']or not tools['versions']['wheel']:
    write(OUT/'wheel-result.json',{'status':'NOT_RUN','reason':'local setuptools/wheel unavailable; no installation attempted'})
    print(json.dumps({'status':'NOT_RUN'}));sys.exit(0)
stage=Path(tempfile.mkdtemp(prefix='build-',dir=OUT/'temporary')).resolve();assert stage.is_relative_to((OUT/'temporary').resolve())
shutil.copytree(ROOT/'src',stage/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
shutil.copyfile(ROOT/'pyproject.toml',stage/'pyproject.toml')
out=(OUT/'distribution').resolve();out.mkdir(exist_ok=False)
previous=Path.cwd()
try:
    os.chdir(stage)
    from setuptools import build_meta
    filename=build_meta.build_wheel(str(out))
finally:os.chdir(previous)
wheel=out/filename
with zipfile.ZipFile(wheel)as z:
    files=z.namelist();data=[]
    for row in load(OUT/'packaged-data-index.json')['data']:
        logical='annotation/contracts/a03_bridge/data/'+row['name'];raw=z.read(logical);assert sha(raw)==row['sha256'];data.append({'path':logical,'sha256':sha(raw),'bytes':len(raw)})
write(OUT/'wheel-result.json',{'status':'OFFLINE_WHEEL_BUILT','wheel':wheel.relative_to(ROOT).as_posix(),'wheel_sha256':sha(wheel.read_bytes()),'files':files,'data_pins':data,'setuptools_version':tools['versions']['setuptools'],'wheel_version':tools['versions']['wheel'],'network_or_install':False})
assert stage.resolve().is_relative_to((OUT/'temporary').resolve());shutil.rmtree(stage)
print(json.dumps({'status':'OFFLINE_WHEEL_BUILT','wheel':filename,'data_files':len(data)}))
