# -*- coding: utf-8 -*-
"""Read fixed source/minimal records and inspect the one permitted N1 driver."""
import copy
import difflib
import json
from evidence import OUT,EV,BASE,raw,text,document,sha,write
P='src/annotation/runtime/storage/__init__.py';PROFILE='src/annotation/contracts/a03_native/data/profile.json';ADOPT='src/annotation/contracts/a03_native/data/adoption.json'
new,old=text(P),text(P,BASE)
assert 'def _progress_attempt(row, intent_ref, plan_ref, fact):' in new
for expression in ("fact.get('plan_ref') != plain(plan_ref)","fact.get('action_id') != row['id']","fact.get('action_digest') != row['digest']",
 "fact.get('intent_ref') != plain(intent_ref)","fact.get('result', {}).get('action_id') != row['id']","fact.get('result', {}).get('intent_ref') != plain(intent_ref)"):
    assert expression in new
assert "return fact['result']['attempt_fact'], copy.deepcopy(fact['result']['attempt_evidence_refs'])" in new
assert "if row['fact'] is None:" in new and "'MAY_HAVE_BEEN_ATTEMPTED' if row['state'] in ('INTENT', 'UNKNOWN') else 'ATTEMPTED'" in new
assert 'attempt_fact, attempt_evidence = self._progress_attempt(row, intent_ref, reference(plan), material)' in new
profile=document(PROFILE);expected=copy.deepcopy(document(PROFILE,BASE))
next(r for r in expected['implementation_pins'] if r[0]=='@annotation/runtime/storage/__init__.py')[1]=sha(raw(P));assert profile==expected
adoption=document(ADOPT);expected=copy.deepcopy(document(ADOPT,BASE));expected['profile_sha256']=sha(raw(PROFILE));assert adoption==expected
for p,d in profile['schema_pins']:assert sha(raw('src/annotation/contracts/a03_native/data/'+p))==d
for p,d in profile['implementation_pins']:
    source='src/'+p[1:] if p.startswith('@') else 'src/annotation/contracts/a03_native/'+p
    assert sha(raw(source))==d
minimal=document(EV+'runs/minimal/stdout.txt')
assert minimal=={'with_fact':'MAY_HAVE_BEEN_ATTEMPTED','attempt_evidence_copied':True,'no_fact_pending':'MAY_HAVE_BEEN_ATTEMPTED',
 'no_fact_reserved':'NOT_ATTEMPTED','foreign_intent':'RECOVERY_CHAIN_INVALID','SQL_rows_or_effects_created':0}
native=text('src/annotation/runtime/storage/native.py');trace=text(EV+'runs/N2/stderr.txt')
assert "book = self._lease(connection, reg['book'], owner_id, generation)" in native
assert native.index("book = self._lease(connection, reg['book'], owner_id, generation)",native.index('def begin_native_pre')) < native.index("kind == 'POST_HOLD'",native.index('def begin_native_pre'))
assert 'def _lease(self, connection, key, owner_id, generation, *, pending_ok=False)' in new
assert 'if not pending_ok and row["hold"]:' in new and 'fail("TARGET_DRIFT_HOLD", row["hold"], 3)' in new
assert 'line 318, in begin_native_pre' in trace and 'line 347, in _lease' in trace
driver=text('tests/test_a03_r8_r2_projection.py')
assert "EVIDENCE = BASE_EVIDENCE / 'validation' / os.environ.get('A03_R8_R2_RUN_ID', 'native-r2-01')" in driver
assert "if len(sys.argv) > 1 and sys.argv[1] == '--n1-child'" in driver
assert "self.assertEqual(code, 87" in driver and "self.assertIn(formal_receipt_ref, formal_refs)" in driver
assert "self.assertEqual(projected['attempt_evidence_refs'], material['result']['attempt_evidence_refs'])" in driver
assert "with self.assertRaises(Exception):" in driver
result={'status':'STATIC_READY_FOR_ONE_INDEPENDENT_N1','storage_diff':list(difflib.unified_diff(old.splitlines(),new.splitlines(),fromfile='base/storage',tofile='target/storage',lineterm='')),
 'storage_sha256':sha(raw(P)),'profile_sha256':sha(raw(PROFILE)),'adoption_sha256':sha(raw(ADOPT)),
 'profile_delta_only_storage_pin':True,'adoption_delta_only_profile_pin':True,'schema_pins_verified':len(profile['schema_pins']),
 'implementation_pins_verified':len(profile['implementation_pins']),'original_minimal_record':minimal,'minimal_rerun':False,
 'N2_blocker':'POST_HOLD begin_native_pre reaches default lease hold guard before kind branch',
 'N2_old_INITIAL_refusal_limit':'original driver catches any Exception; exact caught code is not separately logged',
 'driver_sha256':sha(driver.encode()),'driver_static_review':'normal src imports; fixed fixture; fresh case mkdir; product owns business SQL; single explicit test_N1 only',
 'candidate_runs_in_static_check':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'static-review.json',result)
print(json.dumps({'status':result['status'],'source_pins':len(profile['implementation_pins']),'driver_sha256':result['driver_sha256']}))
