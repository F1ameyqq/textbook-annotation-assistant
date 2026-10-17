"""Audit new host/build drivers; unchanged product is not retested here."""
import ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R7-readonly-codec';sys.path.insert(0,str(EX))
from ops import OUT,PRODUCT,load,sha,write
for p in list(EX.glob('*.py'))+list(OUT.glob('*.py'))+[ROOT/'tests/test_a03_r7_readonly_codec.py']:ast.parse(p.read_text(encoding='utf8'))
before=load(OUT/'pre-execution-static-audit.json')['product_source']
assert before==[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p.read_bytes())}for p in sorted(PRODUCT.glob('*.py'))]
write(OUT/'phase-two-static-audit.json',{'status':'BUILD_AND_HOST_DRIVERS_AST_CHECKED','product_unchanged_since_initial_product_suite':True,'path_test_adaptation':'fallback to ordinary temporary Windows directory junction if symlink privilege unavailable','only_supplemental_test':'PathTests.test_resolved_symlink_escape','product_tests_rerun':0})
print(json.dumps({'status':'PHASE_TWO_DRIVERS_STATIC_READY','product_unchanged':True}))
