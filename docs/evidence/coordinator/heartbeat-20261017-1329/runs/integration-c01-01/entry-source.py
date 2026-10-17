"""Relevant tests against the new main-checkout composition, once per suite."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

root=Path('D:/1800');sys.path.insert(0,str(root/'src'))
import annotation.contracts.a03_bridge as bridge
assert Path(bridge.__file__).resolve()==(root/'src/annotation/contracts/a03_bridge/__init__.py').resolve()
pattern=sys.argv[1]
assert pattern in ('test_a03_r7_readonly_codec.py','test_contracts*.py')
suite=unittest.defaultTestLoader.discover(str(root/'tests'),pattern=pattern)
result=unittest.TextTestRunner(verbosity=2).run(suite)
record=dict(pattern=pattern,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=[str(x[1]) for x in result.skipped],passed=result.wasSuccessful(),product_file=bridge.__file__,product_sha256=hashlib.sha256(Path(bridge.__file__).read_bytes()).hexdigest(),native_calls=0,field_reset='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION')
name='integration-r7-results.json' if 'a03' in pattern else 'integration-c01-results.json'
Path(__file__).with_name(name).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record));raise SystemExit(0 if result.wasSuccessful() else 1)
