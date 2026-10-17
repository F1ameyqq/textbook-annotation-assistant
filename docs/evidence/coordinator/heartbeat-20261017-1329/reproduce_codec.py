"""Three coordinator-selected fixed cases through the frozen public API."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path('D:/1800')
COPY = ROOT/'docs/evidence/A03/review/P2-R7-readonly-codec/input/checkout'
sys.path.insert(0,str(COPY/'src'))
import annotation.contracts.a03_bridge as bridge

def sha(b): return hashlib.sha256(b).hexdigest()
assert Path(bridge.__file__).resolve() == (COPY/'src/annotation/contracts/a03_bridge/__init__.py').resolve()
fix = COPY/'tests/fixtures/a03/P2-R7-readonly-codec'
index = {r['id']:r for r in json.loads((fix/'index.json').read_bytes())['cases']}
results=[]
for name, code, path in [('registration-positive','STATIC_ACCEPTED',None),('target-tuple-negative','FRAME_REGISTRATION_TARGET','r4-static/target-tuple-negative/prefix.json/registration/target'),('r3-original-undeclared-evidence','UNDECLARED_REFERENCE','origin-a-SourceBundle')]:
    row=index[name]; b=(fix/row['bundle']).read_bytes()
    assert sha(b)==row['bundle_sha256']
    source=json.loads(b)
    context=bridge.open_static_context(asset_root=fix/row['asset_root'])
    try:
        result=bridge.validate_static_bundle(source,context=context)
    except bridge.StaticCodecError as err:
        assert (err.code,err.path)==(code,path)
        results.append(dict(case=name,input_sha256=sha(b),actual=err.code,path=err.path))
    else:
        assert code=='STATIC_ACCEPTED' and result.model_dump()==source
        assert result.selection.role=='STATIC_INSPECTION'
        canonical=json.dumps(source,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
        assert result.canonical_sha256==sha(canonical)
        snapshot=result.model_dump(); snapshot.clear()
        assert result.model_dump()==source
        results.append(dict(case=name,input_sha256=sha(b),actual=code,full_snapshot_preserved=True,canonical_sha256=result.canonical_sha256))
out=dict(status='PASS',product_file=bridge.__file__,product_sha256=sha(Path(bridge.__file__).read_bytes()),cases=results,scope='Frozen read-only codec only',native_calls=0,field_reset='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION')
Path(__file__).with_name('reproduction-result.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out))
