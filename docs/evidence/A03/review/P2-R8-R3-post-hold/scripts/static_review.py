# -*- coding: utf-8 -*-
import copy
import difflib
import json
from evidence import OUT,EV,BASE,raw,text,document,sha,write
P='src/annotation/runtime/storage/native.py';PROFILE='src/annotation/contracts/a03_native/data/profile.json';ADOPT='src/annotation/contracts/a03_native/data/adoption.json'
new,old=text(P),text(P,BASE)
assert new.count('self.store._pre_lease(')==2 and new.count('self._pre_lease(')==1
for token in ("pending_ok=accepted or post_hold", "if self._pending(connection, reg['book']):", "if context['hold_id'] != book['hold']:",
 "self.read_resource(context['hold_ref'], reg['id']) != event", "book['head_sequence'], book['head_hash']) != expected_head",
 "payload.get('source_ref') != json.loads(reg['source'])", "payload.get('target_store_id') != self.target_store_id", "payload.get('target_session_id') != reg['session']"):
    assert token in new,token
assert 'time.time() > row[\'created\'] + 60' in new and 'actual[\'read_elapsed_seconds\'] > 2' in new
assert "kind=binding['context']['kind'], context=binding['context']" in new
expected=copy.deepcopy(document(PROFILE,BASE));next(r for r in expected['implementation_pins'] if r[0]=='@annotation/runtime/storage/native.py')[1]=sha(raw(P));assert document(PROFILE)==expected
expected=copy.deepcopy(document(ADOPT,BASE));expected['profile_sha256']=sha(raw(PROFILE));assert document(ADOPT)==expected
profile=document(PROFILE)
for p,d in profile['schema_pins']:assert sha(raw('src/annotation/contracts/a03_native/data/'+p))==d
for p,d in profile['implementation_pins']:
    p='src/'+p[1:] if p.startswith('@') else 'src/annotation/contracts/a03_native/'+p
    assert sha(raw(p))==d
driver=text('tests/test_a03_r8_r3_post_hold.py');local=text('tests/test_a03_r8_r3_local.py')
assert "os.environ.get('A03_R8_R3_RUN_ID', 'native-r3-01')" in driver
assert "class R8R3LocalControls" in local and 'test_no_hold_owner_and_pending' in local
assert "deadline = second[4]['created'] + 60.1" in driver and 'while time.time() < deadline:' in driver
assert 'test.assertEqual(code, expected)' in local and "'NATIVE_PRE_DEADLINE_EXCEEDED'" in driver
value={'status':'STATIC_READY_FOR_BOUNDED_LOCAL_N1_N2_N3_N4_N5',
 'native_diff':list(difflib.unified_diff(old.splitlines(),new.splitlines(),fromfile='base/native.py',tofile='target/native.py',lineterm='')),
 'native_sha256':sha(raw(P)),'profile_sha256':sha(raw(PROFILE)),'adoption_sha256':sha(raw(ADOPT)),
 'three_call_sites_verified':True,'shared_lease_contract_and_schemas_preserved_by_raw_tree':True,
 'schema_pins':len(profile['schema_pins']),'implementation_pins':len(profile['implementation_pins']),
 'driver_sha256':sha(driver.encode()),'local_driver_sha256':sha(local.encode()),
 'static_scope':'normal APIs and imports; fresh source fixture, exact-code refusals, real 60-second wait; no SQL fabrication',
 'candidate_runs_in_static_review':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'static-review.json',value)
print(json.dumps({'status':value['status'],'source_pins':len(profile['implementation_pins']),'call_sites':3}))
