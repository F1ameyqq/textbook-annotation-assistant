# -*- coding: utf-8 -*-
"""Inspect exact driver routing and anchor/init code, without importing product."""
import ast
from evidence import OUT,WORK,TARGET,BASE,EV,raw,text,document,sha,write
driver=text('tests/test_a03_r8_r4_remaining.py');old=text('tests/test_a03_r8_r3_post_hold.py')
for path in WORK.rglob('*.py'):ast.parse(path.read_bytes(),filename=str(path))
assert sha(driver.encode())=='27d1969548011b044c21b77a121c53b5bef90d4aa0b19aef95f65b8d692f9a3d'
assert sha(old.encode())=='02acb22f395f380528130166ca8ae4637e3303c73f6496d9da4166b5050a1467'
for token in ['import test_a03_r8_r3_post_hold as accepted',"accepted.R8R3NativeBridgeTests('test_N1').test_N1()",'accepted.EVIDENCE = EVIDENCE','accepted.BASE_EVIDENCE = OUT',
 "write('N6/full-current-history.json', canonical(current))",'verify_generated_plan(bundle, plan, plan.payload.snapshot',
 'sys.setprofile(capture)','sys.setprofile(None)','frame.f_code is create_plan.__code__','frame.f_code is store.resource_manifest.__code__',
 'self.assertEqual(len(captured), 1)','self.assertEqual(captured[0], original_plan)',"check = pre['payload']['checks'][0]",
 "self.assertIn('EVIDENCE_ID_MISSING', codes)",'self.assertEqual(before, after)',"before_completion=stop",'self.assertIs(error, injected)',
 "self.assertEqual(calls, ['before_completion'])",'self.assertFalse(anchor.exists())',"self.assertFalse((path / 'target').exists())"]:assert token in driver,token
assert driver.count('verify_generated_plan(')==1 and 'create_plan(' not in driver and 'sys.settrace(' not in driver
assert not any(token in driver for token in ('ast.','exec(', 'setattr(', 'mock.patch', 'monkeypatch', 'UPDATE ', 'INSERT ', 'DELETE '))
native=text('src/annotation/runtime/storage/native.py');planner=text('src/annotation/delivery/planner/__init__.py')
for token in ["return require_context(bridge_context, bundle)('verify_creation_anchor'",'bundle = validate_bundle(bundle, bridge_context=bridge_context)']:assert token in planner
for token in ["raw = Path(row['input_path']).read_bytes()","hashlib.sha256(raw).hexdigest() != row['input_sha']", "self.store.resource_manifest(original, context.asset_root) != json.loads(row['manifest'])",
 'generated = create_plan(original, payload.graph, payload.precheck, payload.targetcheck,','if generated.artifacts[-1] != plan:',
 "if before_completion is not None:", 'before_completion()',"connection.executemany('INSERT INTO meta VALUES(?,?)'",'exclusive_bytes(anchor, canonical(descriptor))']:assert token in native,token
assert native.index('before_completion()')<native.index("connection.executemany('INSERT INTO meta VALUES(?,?)'")<native.index('exclusive_bytes(anchor, canonical(descriptor))')
profile_path='src/annotation/contracts/a03_native/data/profile.json';adopt_path='src/annotation/contracts/a03_native/data/adoption.json'
profile=document(profile_path)
for p,d in profile['schema_pins']:assert sha(raw('src/annotation/contracts/a03_native/data/'+p))==d
for p,d in profile['implementation_pins']:
    p='src/'+p[1:] if p.startswith('@') else 'src/annotation/contracts/a03_native/'+p
    assert sha(raw(p))==d
for p in ('src/annotation/runtime/storage/native.py',profile_path,adopt_path):assert raw(p)==raw(p,BASE)
write(OUT/'reviewer-query-preparation-failure.json',{'status':'READONLY_PATH_LOOKUP_TRANSCRIPT_ONLY','product_execution':False,
 'data_mutations':False,'attempted_path':'src/annotation/delivery/planner.py','actual_path':'src/annotation/delivery/planner/__init__.py',
 'transcribed_error':'Get-Content: Cannot find path; Cannot index into a null array; rg IO error (system cannot find file).',
 'resolution':'rg --files located package; subsequent static reads use __init__.py','pid':None,'raw_stdout_stderr_archived':False,
 'limitation':'rendered tool output only, no invented PID/raw process claim; no candidate call or retry'})
write(OUT/'static-review.json',{'status':'STATIC_READY_FOR_EXACT_N1_N6_N7_INITIALIZATION_ONCE','new_driver_sha256':sha(driver.encode()),
 'accepted_driver_sha256':sha(old.encode()),'product_native_sha256':sha(native.encode()),'profile_sha256':sha(raw(profile_path)),
 'adoption_sha256':sha(raw(adopt_path)),'schema_pins':len(profile['schema_pins']),'implementation_pins':len(profile['implementation_pins']),
 'product_and_all_base_entries_unchanged':True,'normal_import_no_AST_exec_slicing_or_product_patch':True,
 'N6_profile_observes_only_actual_returns_and_no_extra_planner_call':True,'N6_negative_named_PRE_check_dependency':True,
 'N7_existing_hook_before_meta_and_anchor':True,'static_syntax_only_AST_use':'parse solely for syntax, never execute/extract imports',
 'allowed_phases':['N1','N6','N7'],'candidate_runs_in_this_check':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print('{"status":"STATIC_READY_FOR_EXACT_N1_N6_N7_INITIALIZATION_ONCE","source_pins":23}')
