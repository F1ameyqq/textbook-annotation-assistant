# -*- coding: utf-8 -*-
"""Only the two original C01 methods interrupted by reviewer setup errors."""
import json
from pathlib import Path
import sys
import unittest
from nested_resume import install

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout'
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
first=json.loads((OUT/'c01-compatibility-results.json').read_bytes());assert first['tests_run']==70 and first['failures']==2 and first['errors']==1
names=['test_contracts.ContractTests.test_copied_sample_cli_and_public_consumer_work_from_another_cwd',
       'test_contracts.ContractTests.test_relative_symlink_may_not_escape_the_sample_root']
records,restore=install('c01-review-environment-completion')
try:result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
finally:restore()
assert all(r.logged and not r.record['alive']and not r.record['timed_out']for r in records)
value={'status':'C01_AFFECTED_REVIEW_ENVIRONMENT_COMPLETED'if result.wasSuccessful()else'REWORK','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
 'skips':[{'test':str(t),'reason':reason}for t,reason in result.skipped],'methods':names,'nested_children':len(records),'child_exits':[r.returncode for r in records],
 'full_C01_matrix_rerun':False,'passed_methods_rerun':False,'product_or_wheel_changed':False,
 'first_failed_round_retained':'c01-compatibility-results.json + runs/c01-compatibility-01 + nested/c01-compatibility',
 'reviewer_changes_only':['raw unchanged build_fixtures.py dependency for consume.summary','native cmd text decode uses OEM; all raw bytes retained'],
 'old_A03_tests_or_generators_run':0}
with(OUT/'c01-affected-completion-results.json').open('x',encoding='utf8',newline='\n')as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(value))
assert result.testsRun==2 and result.wasSuccessful()
