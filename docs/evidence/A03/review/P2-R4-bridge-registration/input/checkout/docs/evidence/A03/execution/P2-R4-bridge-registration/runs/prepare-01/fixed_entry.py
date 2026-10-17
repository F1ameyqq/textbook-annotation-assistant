"""Load exact fixed R3 static semantics, redirecting ONLY its output assignment."""
import ast,hashlib,json,os,sys,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/evidence/A03/execution/P2-R4-bridge-registration'
RUN=os.environ.get('A03_R4_RUN_ID','manual');assert RUN.replace('-','').isalnum()
PATH=ROOT/'examples/a03/P2-R3-evidence-closure/closure.py'
raw=PATH.read_bytes();expected='ff650507bca971f8c9418a09e6e4f8df7c7691016841ffe7bd15ff66382579a5'
assert hashlib.sha256(raw).hexdigest()==expected
tree=ast.parse(raw.decode('utf8'));before=ast.dump(next(x for x in tree.body if isinstance(x,ast.ClassDef)and x.name=='Package'),include_attributes=True)
changed=[]
for node in tree.body:
    if isinstance(node,ast.Assign)and any(isinstance(t,ast.Attribute)and isinstance(t.value,ast.Name)and t.value.id=='base'and t.attr=='EVID'for t in node.targets):
        changed.append(ast.get_source_segment(raw.decode('utf8'),node));node.value=ast.copy_location(ast.Name(id='R4_OUTPUT',ctx=ast.Load()),node.value)
assert len(changed)==1
after=ast.dump(next(x for x in tree.body if isinstance(x,ast.ClassDef)and x.name=='Package'),include_attributes=True);assert before==after
module=types.ModuleType('_r4_fixed_r3');module.__file__=str(PATH);module.__dict__['R4_OUTPUT']=OUT/'static-output'/RUN
sys.modules[module.__name__]=module;exec(compile(ast.fix_missing_locations(tree),str(PATH),'exec'),module.__dict__)
c=module
ROUTING={'source':PATH.relative_to(ROOT).as_posix(),'source_sha256':expected,'changed_assignment_only':changed,
         'replacement':'base.EVID = R4_OUTPUT (new R4 output directory)','package_class_ast_unchanged':True,
         'package_class_ast_sha256':hashlib.sha256(before.encode()).hexdigest(),'no_package_semantic_changes':True,
         'r2_main_called':False,'old_36_matrix_called':False}
