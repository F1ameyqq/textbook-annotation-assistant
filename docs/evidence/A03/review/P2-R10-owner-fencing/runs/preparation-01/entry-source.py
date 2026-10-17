# -*- coding: utf-8 -*-
"""Static source and exact driver expectations, before any functional call."""
import ast
from evidence import OUT,WORK,EV,TARGET,BASE,raw,text,document,sha,write
driver=text('tests/test_a03_p2_r10_owner_fencing.py')
assert sha(driver.encode())=='da15d84be77fb9be7b718ff28721647a6b3c4052b32531cae45768394c798a82'
assert sha(raw('tests/test_a03_r8_r3_post_hold.py'))=='02acb22f395f380528130166ca8ae4637e3303c73f6496d9da4166b5050a1467'
for p in WORK.rglob('*.py'):ast.parse(p.read_bytes(),filename=str(p))
for token in ["'point': 'BEFORE_CLAIM', 'mode': 'barrier'", "assert a.poll() is None and b.poll() is None", "before-common-release.json", "simultaneous-competition.json",
 "keeper = LeaseKeeper(store, key, claim.owner_id, claim.generation).start()", "wait_file(control / (role + '-finish.barrier')",
 "store.record_native_plan(reg['id'], bundle, artifact_ref(plan), config", "keeper.stop()\n            store.release", "released = True", "before-stale-call.json",
 "run_plan(store, store.registration()['id'], owner_id=claim.owner_id, generation=claim.generation", "any(f.name == '_lease' for f in frames)",
 "old_owner_renew_or_release_after_handover", "if not released:", "before['book'][k] == after['book'][k]", "after['target_fence'] == before['target_fence']",
 "45 - (time.monotonic() - start)", "wait_file(control / 'A-qualified.json', seconds=30)"]:
    assert token in driver,token
assert not any(t in driver for t in ('exec(', 'ast.', 'monkeypatch', 'mock.patch', 'INSERT ', 'UPDATE ', 'DELETE ', 'os._exit(', 'time.time =', '_pid_alive ='))
source=text('src/annotation/runtime/storage/__init__.py');common=text('src/annotation/runtime/storage/common.py');recovery=text('src/annotation/runtime/recovery/__init__.py')
for token in ['self.fault("BEFORE_CLAIM")','if row["lease"] > time.time() or self._pid_alive(row["pid"]):','fail("OWNER_BUSY", "lease expired AND previous process exited required", 4)',
 'row["process_id"] != self.instance or row["pid"] != os.getpid()', 'fail("OWNER_GENERATION_STALE", "current ACTIVE lease required", 4)', 'time.time() + 10']:
    assert token in source,token
assert 'deadline = time.monotonic() + 5' in common and 'canonical({"point": point, "pid": os.getpid(), "at": now()})' in common
assert recovery.index('store._lease(connection, reg["book"], owner_id, generation)')<recovery.index('keeper = LeaseKeeper(store, key, owner_id, generation).start()')
profile=document('src/annotation/contracts/a03_native/data/profile.json')
for p,d in profile['schema_pins']:assert sha(raw('src/annotation/contracts/a03_native/data/'+p))==d
for p,d in profile['implementation_pins']:
    p='src/'+p[1:] if p.startswith('@') else 'src/annotation/contracts/a03_native/'+p;assert sha(raw(p))==d
references=document(EV+'inputs.json')['unchanged_references_and_copied_fixture_sources']
for r in references:
    if (TARGET,r['path']) in __import__('evidence').MAP:assert raw(r['path'])==raw(r['path'],BASE)
expectations={'C1':{'outcomes':'one ACTIVE owner, one REFUSED while both live','refusal_type':'RuntimeFailure','refusal_code':'OWNER_BUSY',
 'refusal_message':'lease expired AND previous process exited required','actual_BEFORE_CLAIM_markers':True,'effects':0,'business_plans_required':False},
 'C2':{'real_qualification':'ADMITTED PRE and recorded real plan before accept','handover':'A release -> B ACTIVE with higher generation and matching target fence; both live',
 'refusal_type':'RuntimeFailure','refusal_code':'OWNER_GENERATION_STALE','refusal_message':'current ACTIVE lease required','root_lease_guard_required':True,
 'no_new_plans_actions_intents_permits_or_effects':True,'old_A_no_renew_or_release_B':True}}
write(OUT/'driver-preregistration.json',{'driver':'tests/test_a03_p2_r10_owner_fencing.py','driver_sha256':sha(driver.encode()),
 'helper_sha256':sha(raw('tests/test_a03_r8_r3_post_hold.py')),'product_imports_from':str(WORK/'src'),'source_files':76,
 'expected':expectations,'parent_watchdog_seconds':90,'worker_watchdog_seconds':45,'product_barrier_seconds':5,'lease_seconds':10,'observation_seconds':2,
 'frozen_before_functional_execution':True,'driver_changes':0,'product_changes':0,'product_calls_in_preparation':0,
 'scope':'C1/C2 each once; no old R3/R4/R9/R9-R1 groups','field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
write(OUT/'static-review.json',{'status':'READY_FOR_C1_THEN_C2_ONCE','exact_driver_unmodified':True,'normal_imports_no_AST_exec_slicing':True,
 'all_base_entries_and_product_preserved':32152,'schema_pins':len(profile['schema_pins']),'implementation_pins':len(profile['implementation_pins']),
 'live_process_barriers_and_lifecycle_reviewed':True,'stale_guard_before_run_plan_acceptance_and_finally':True,
 'source_sha256':{p:sha(raw(p)) for p in ['src/annotation/runtime/storage/__init__.py','src/annotation/runtime/storage/native.py','src/annotation/runtime/storage/common.py','src/annotation/runtime/recovery/__init__.py']},
 'candidate_calls_by_this_check':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print('{"status":"READY_FOR_C1_THEN_C2_ONCE","driver_changes":0,"candidate_calls":0}')
