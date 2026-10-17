"""Inspect pins, code, comparison and prepared bytes before the seven calls."""
import ast,difflib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R5-registration-context';sys.path.insert(0,str(EX))
from common import OUT,h,load,sha,write,raw_write
index=load(OUT/'input-index.json');checked=0
for row in index['inputs']:
    p=ROOT/row.get('copy',row['path']);raw=p.read_bytes();assert len(raw)==row['bytes']and sha(raw)==row['sha256'];checked+=1
for p in list(EX.glob('*.py'))+list(OUT.glob('*.py')):ast.parse(p.read_text(encoding='utf8'))
source=(ROOT/'examples/a03/P2-R2-proposal/check.py').read_text(encoding='utf8');tree=ast.parse(source);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='Package');scan=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='scan')
new=(EX/'registration.py').read_text(encoding='utf8');patch=''.join(difflib.unified_diff(ast.get_source_segment(source,scan).splitlines(True),new.splitlines(True),fromfile='fixed-R2/Package.scan (comparison only)',tofile='new-R5/registration.py'))
raw_write(OUT/'source-difference.patch',patch.encode('utf8'))
cases=load(EX/'case-index.json');assert len(cases['cases'])==7
for row in cases['cases']:
    raw=(ROOT/row['case']).read_bytes();assert sha(raw)==row['case_sha256'];case=json.loads(raw);assert sha((ROOT/case['bundle']).read_bytes())==case['bundle_sha256']
    for r in case['resources']:assert sha((ROOT/r['file']).read_bytes())==r['raw_sha256']
    bundle=load(ROOT/case['bundle']);assert all(h({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash']for a in bundle['artifacts'])
write(OUT/'pre-execution-static-audit.json',{'status':'CODE_AND_INPUT_PINS_CHECKED_BEFORE_SEVEN_CALLS','raw_inputs':checked,'fixed_cases':7,'new_overlay_sha256':sha(new.encode('utf8')),'diff_sha256':sha(patch.encode('utf8')),'checker_imports_or_calls':0,'scope':'only prefix traversal mode/formal global refs/registration target; fixed R3 consumer closure and R2 full validation tail inherited','profile_schema_api_changed':False,'product_calls':0})
print(json.dumps({'status':'STATIC_READY_FOR_SEVEN_CASES','checker_calls':0,'raw_inputs':checked}))
