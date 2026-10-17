"""Load SHA-pinned R3/R2 static classes without their output-directory setup."""
import ast,sys,types
from common import ROOT,OUT,sha
SOURCE=ROOT/'examples/a03/P2-R3-evidence-closure/closure.py'
PINS=ROOT/'docs/evidence/A03/execution/P2-R3-evidence-closure/r2-input-pins.json'
raw=SOURCE.read_bytes();assert sha(raw)=='ff650507bca971f8c9418a09e6e4f8df7c7691016841ffe7bd15ff66382579a5'
assert sha(PINS.read_bytes())=='d5f7c779ca0da7fdecd606402df649fbd593faf42b5fe3ded934d6c804c74d48'
tree=ast.parse(raw.decode('utf8'));before=ast.dump(next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='Package'),include_attributes=True)
changes=[]
for n in list(tree.body):
    if isinstance(n,ast.Assign)and any(isinstance(t,ast.Attribute)and isinstance(t.value,ast.Name)and t.value.id=='base'and t.attr=='EVID'for t in n.targets):
        changes.append(ast.get_source_segment(raw.decode('utf8'),n));n.value=ast.copy_location(ast.Name(id='R5_UNUSED_OUTPUT',ctx=ast.Load()),n.value)
    if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Attribute)and ast.unparse(n.value.func)=='base.EVID.mkdir':
        changes.append(ast.get_source_segment(raw.decode('utf8'),n));tree.body.remove(n)
assert len(changes)==2
after=ast.dump(next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='Package'),include_attributes=True);assert before==after
module=types.ModuleType('_r5_fixed_r3');module.__file__=str(SOURCE);module.__dict__['R5_UNUSED_OUTPUT']=OUT/'unused-output'
sys.modules[module.__name__]=module;exec(compile(ast.fix_missing_locations(tree),str(SOURCE),'exec'),module.__dict__)
r3=module;base=module.base
LOADER={'source':SOURCE.relative_to(ROOT).as_posix(),'source_sha256':sha(raw),'output_setup_only':changes,'replacement':'redirect unused EVID and omit mkdir; no validator/helper/main statement changed','fixed_R3_Package_AST_unchanged':True,'fixed_R3_Package_AST_sha256':sha(before.encode()),'product_imports':0,'main_or_oracle_calls':0}
