# -*- coding: utf-8 -*-
"""Extract the frozen wheel outside the repository, no build/install/network."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath,PureWindowsPath
import shutil
import subprocess
import sys
import tempfile
import zipfile
from nested_rest import install

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout';EV=ROOT/'docs/evidence/A03/execution/P2-R7-readonly-codec';FIX=ROOT/'tests/fixtures/a03/P2-R7-readonly-codec'
wheel=EV/'distribution/annotation_contracts-0.1.0-py3-none-any.whl'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
assert sha(wheel.read_bytes())=='c22c1bcae684d36bf0d39c1fd4c357409e093648157e8132f7b305245b7d02c7'
temp=Path(tempfile.mkdtemp(prefix='a03-r7-review-wheel-')).resolve();records,restore=install('wheel-outside')
try:
    unpacked=temp/'unpacked';unpacked.mkdir()
    with zipfile.ZipFile(wheel)as z:
        assert len(z.namelist())==len(set(z.namelist()))
        for name in z.namelist():
            p=PurePosixPath(name);assert not p.is_absolute()and '..'not in p.parts and not PureWindowsPath(name).drive and '\\'not in name
            dest=unpacked/name;assert dest.resolve().is_relative_to(unpacked)
            if name.endswith('/'):dest.mkdir(parents=True,exist_ok=True)
            else:
                dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb')as f:f.write(z.read(name))
    selected=[]
    for row in json.loads((FIX/'index.json').read_bytes())['cases']:
        if row['id']not in ['registration-positive','target-tuple-negative']:continue
        folder=temp/'cases'/row['id'];folder.mkdir(parents=True)
        shutil.copyfile(FIX/row['bundle'],folder/'bundle.json');shutil.copytree(FIX/row['asset_root'],folder/'assets')
        assert sha((folder/'bundle.json').read_bytes())==row['bundle_sha256'];selected.append({'id':row['id'],'bundle_sha256':row['bundle_sha256'],'expected':row['expected']})
    write(temp/'probe-inputs.json',{'cases':selected})
    source=OUT/'scripts/wheel_probe.py';shutil.copyfile(source,temp/'probe.py')
    assert sha((temp/'probe.py').read_bytes())==sha(source.read_bytes())
    write(OUT/'wheel-launch.json',{'wheel_sha256':sha(wheel.read_bytes()),'probe_sha256':sha(source.read_bytes()),'input_cases':selected,
      'temporary_root':str(temp),'input_json_sha256':sha((temp/'probe-inputs.json').read_bytes()),'PYTHONPATH':'removed','wheel_rebuilt_or_installed':False})
    env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
    cp=subprocess.run([sys.executable,'-X','utf8','-B',str(temp/'probe.py')],cwd=temp,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    assert cp.returncode==0,(cp.returncode,cp.stdout,cp.stderr)
    result=json.loads(cp.stdout);assert result['status']=='OUTSIDE_FROZEN_WHEEL_CHECKS_PASSED'
    write(OUT/'wheel-outside-results.json',result)
finally:
    restore();assert temp.parent==Path(tempfile.gettempdir()).resolve()and temp.name.startswith('a03-r7-review-wheel-')and not temp.is_symlink()
    shutil.rmtree(temp)
assert all(p.logged and p.returncode==0 and not p.record['alive']and not p.record['timed_out']for p in records)
write(OUT/'wheel-cleanup.json',{'temporary_root':str(temp),'removed':not temp.exists(),'all_owned_children_exited':True})
print(json.dumps({'status':'OUTSIDE_FROZEN_WHEEL_CHECKS_PASSED','cases':2,'actual_module_file':result['module_file'],'data_pins':len(result['data_pins']),'temporary_root_removed':not temp.exists()}))
