"""Runs outside the repository using only unpacked wheel and two copied cases."""
import hashlib,json,os,sys
from pathlib import Path
from importlib import metadata
HERE=Path(__file__).resolve().parent;UNPACKED=HERE/'unpacked';sys.path.insert(0,str(UNPACKED))
assert'PYTHONPATH'not in os.environ
import annotation.contracts.a03_bridge as bridge
from annotation.contracts.a03_bridge import StaticCodecError
assert Path(bridge.__file__).resolve().is_relative_to(UNPACKED.resolve())
selection=bridge.select_static_codec();observations=[]
for name,expected in [('registration-positive','STATIC_ACCEPTED'),('target-tuple-negative','FRAME_REGISTRATION_TARGET')]:
    folder=HERE/'cases'/name;bundle=json.loads((folder/'bundle.json').read_bytes());context=bridge.open_static_context(asset_root=folder/'assets')
    try:
        result=bridge.validate_static_bundle(bundle,context=context);actual='STATIC_ACCEPTED';path=None
        assert result.model_dump()==bundle
    except StaticCodecError as e:actual=e.code;path=e.path
    assert actual==expected,(name,actual,path)
    observations.append({'case':name,'actual':actual,'path':path})
from annotation.contracts.a03_bridge._builtin import PINS
pins=[]
for name,expected in PINS:
    raw=(Path(bridge.__file__).parent/'data'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected;pins.append({'path':name,'sha256':expected})
dist=metadata.distribution('annotation-contracts')
print(json.dumps({'status':'OUTSIDE_REPOSITORY_WHEEL_IMPORT_PASSED','cwd':str(Path.cwd()),'product_module_file':bridge.__file__,'product_module_sha256':hashlib.sha256(Path(bridge.__file__).read_bytes()).hexdigest(),'distribution_version':dist.version,'distribution_files':[str(p)for p in dist.files],'data_pins':pins,'role':selection.role,'observations':observations,'PYTHONPATH_absent':True,'repository_examples_docs_git_used':False}))
