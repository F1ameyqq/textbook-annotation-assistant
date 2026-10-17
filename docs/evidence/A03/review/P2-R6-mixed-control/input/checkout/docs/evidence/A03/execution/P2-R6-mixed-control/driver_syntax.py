"""Audit the parse-only failure and driver repair without loading any checker."""
import ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R6-mixed-control';sys.path.insert(0,str(EX))
from files import OUT,sha,write
failed=OUT/'runs/entry-01/registered-script.py';raw=failed.read_bytes()
try:ast.parse(raw.decode('utf8'));raise AssertionError('expected original driver parse failure')
except SyntaxError as error:failure={'line':error.lineno,'message':error.msg}
assert not(OUT/'entry-invocation.json').exists()and not(OUT/'entry-result.json').exists()
source=(EX/'entry.py').read_bytes();ast.parse(source.decode('utf8'))
for p in list(EX.glob('*.py'))+list(OUT.glob('*.py')):ast.parse(p.read_text(encoding='utf8'))
write(OUT/'driver-syntax-check.json',{'status':'DRIVER_AST_PASSED_BEFORE_FIRST_ACTUAL_PACKAGE_CALL','failed_launch':'entry-01','failed_script_sha256':sha(raw),'original_parse_failure':failure,'current_driver_sha256':sha(source),'Package_calls_before_syntax_repair':0,'basis':'Python failed parsing entire module before top-level execution; invocation guard/result absent at this recorded check','candidate_or_checker_or_loading_semantics_changed':False,'repair':'one whitespace separator in readonly trace predicate'})
print(json.dumps({'status':'DRIVER_AST_PASSED','Package_calls':0}))
