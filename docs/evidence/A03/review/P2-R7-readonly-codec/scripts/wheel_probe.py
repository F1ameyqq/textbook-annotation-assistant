# -*- coding: utf-8 -*-
"""Copied to an outside temporary root; only imports the extracted frozen wheel."""
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;UNPACKED=HERE/'unpacked';sys.path.insert(0,str(UNPACKED))
assert 'PYTHONPATH'not in os.environ
import annotation.contracts.a03_bridge as bridge
from annotation.contracts.a03_bridge._builtin import PINS
from annotation.contracts.a03_bridge._rules import StaticPackage
assert Path(bridge.__file__).resolve().is_relative_to(UNPACKED.resolve())
inputs=json.loads((HERE/'probe-inputs.json').read_bytes());observations=[]
for row in inputs['cases']:
    folder=HERE/'cases'/row['id'];raw=(folder/'bundle.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==row['bundle_sha256']
    instances=[]
    def trace(frame,event,arg):
        if event=='call'and frame.f_code is StaticPackage.validate.__code__:instances.append(frame.f_locals['self'])
        return trace
    sys.settrace(trace)
    try:
        try:r=bridge.validate_static_bundle(json.loads(raw),context=bridge.open_static_context(asset_root=folder/'assets'));actual='STATIC_ACCEPTED';error=None;assert r.model_dump()==json.loads(raw)
        except bridge.StaticCodecError as e:actual=e.code;error={'code':e.code,'path':e.path}
    finally:sys.settrace(None)
    assert actual==row['expected']and len(instances)==1
    observations.append({'id':row['id'],'actual':actual,'error':error,'stages':instances[0].stages,'complete_API_calls':1})
data=[]
for name,expected in PINS:
    b=(Path(bridge.__file__).parent/'data'/name).read_bytes();assert hashlib.sha256(b).hexdigest()==expected;data.append({'path':name,'sha256':expected})
dist=metadata.distribution('annotation-contracts');assert Path(dist.locate_file('')).resolve()==UNPACKED.resolve()and dist.version=='0.1.0'
assert not any(name in sys.modules for name in ['data_check','load_static','registration','schema_check','oracle_verifier'])
print(json.dumps({'status':'OUTSIDE_FROZEN_WHEEL_CHECKS_PASSED','cwd':str(Path.cwd()),'module_file':bridge.__file__,
 'module_sha256':hashlib.sha256(Path(bridge.__file__).read_bytes()).hexdigest(),'distribution_root':str(dist.locate_file('')),'distribution_version':dist.version,
 'distribution_files':[str(p)for p in dist.files],'data_pins':data,'observations':observations,'PYTHONPATH_absent':True,
 'role':bridge.select_static_codec().role,'adoption_scope':bridge.select_static_codec().adoption_scope,'repository_source_fallback_or_old_static_imports':False}))
