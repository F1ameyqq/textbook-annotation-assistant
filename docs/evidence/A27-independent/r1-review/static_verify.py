import ast,hashlib,json
from pathlib import Path
PUBLIC=Path(__file__).resolve().parent
PRIVATE=Path('D:/1800/.local/stages/a27-independent-20261023')
old=PRIVATE/'candidate-23591811/product/tools/run_usense_postsave_readback.py'
new=PRIVATE/'candidate-ebca4c71/product/tools/run_usense_postsave_readback.py'
def functions(path):
    tree=ast.parse(path.read_bytes())
    return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
a,b=functions(old),functions(new)
unchanged=sorted(n for n in a if a[n]==b.get(n))
changed=sorted(n for n in a if a[n]!=b.get(n))
added=sorted(set(b)-set(a))
assert changed==['exclusive_profile']
assert added==['directory_identity','profile_arguments']
assert {'execute','preflight','prepare_request','main'}<=set(unchanged)
base=PUBLIC.parent/'fixed-review/independent_controls_v2.py'
adapted=PUBLIC/'original_counterexample.py'
expected=base.read_bytes().replace(b"PRIVATE/'candidate-23591811/product'",b"PRIVATE/'candidate-ebca4c71/product'").replace(b"PRIVATE/'candidate-23591811/delivery'",b"PRIVATE/'candidate-ebca4c71/delivery'")
assert adapted.read_bytes()==expected
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'schema':'A27IndependentR1StaticDelta/v1','unchanged_functions':unchanged,'changed_functions':changed,'added_functions':added,
        'original_I07_control_only_candidate_paths_changed':True,'old_runner_sha256':sha(old),'new_runner_sha256':sha(new),
        'prior_control_sha256':sha(base),'adapted_control_sha256':sha(adapted),'product_imported_or_executed':False}
(PUBLIC/'static-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
