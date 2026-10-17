# -*- coding: utf-8 -*-
"""Frozen source, schema and original minimal evidence only; no candidate execution."""
import copy
import difflib
import json
from evidence import OUT,EV,BASE,raw,text,document,sha,write
P='src/annotation/quality/synthetic_precheck.py';PROFILE='src/annotation/contracts/a03_native/data/profile.json';ADOPTION='src/annotation/contracts/a03_native/data/adoption.json'
old,new=text(P,BASE),text(P)
assert 'coverage, complete = coverage_for(bundle, graph)' in new
assert "checked['coverage'] = 'FAIL'" in new
assert "'PASS' if complete and all(value == 'PASS' for value in checked.values()) else 'HOLD'" in new
assert "'receipt': None, 'coverage': coverage," in new and "'decision': decision," in new
assert 'coverage, results, decision = _pre_coverage_decision(bundle, graph, results)' in new
assert "'coverage': coverage_for(bundle, graph)" in old and "'coverage': coverage_for(bundle, graph)" not in new
diff=list(difflib.unified_diff(old.splitlines(),new.splitlines(),fromfile='base/producer',tofile='target/producer',lineterm=''))
profile=document(PROFILE);before=document(PROFILE,BASE);expected=copy.deepcopy(before)
producer_pin=next(row for row in expected['implementation_pins'] if row[0]=='@annotation/quality/synthetic_precheck.py')
producer_pin[1]=sha(raw(P));assert profile==expected
adoption=document(ADOPTION);prior=document(ADOPTION,BASE);expected=copy.deepcopy(prior)
assert expected['profile_sha256']==sha(raw(PROFILE,BASE));expected['profile_sha256']=sha(raw(PROFILE));assert adoption==expected
for p,d in profile['schema_pins']:assert sha(raw('src/annotation/contracts/a03_native/data/'+p))==d
for p,d in profile['implementation_pins']:
    source='src/'+p[1:] if p.startswith('@') else 'src/annotation/contracts/a03_native/'+p
    assert sha(raw(source))==d
schema=document('src/annotation/contracts/a03_native/data/schemas/exchange.json')
assert schema['$defs']['Coverage']['type']=='object'
assert schema['$defs']['AmendedCheckReport']['properties']['payload']['oneOf'][0]['properties']['coverage']=={'$ref':'#/$defs/Coverage'}
minimal=document(EV+'runs/minimal/stdout.txt')['minimal_cases'];assert len(minimal)==2
pgm_sha=sha(raw('tests/fixtures/a03/P2-R8-R1-producer/assets/page.pgm'))
for row in minimal:
    incomplete=row['incomplete'];assert row['complete']==(not incomplete) and row['coverage_type']=='dict'
    assert row['decision']==('HOLD' if incomplete else 'PASS')
    assert row['actual_checks']['coverage']==('FAIL' if incomplete else 'PASS')
    assert all(v=='PASS' for k,v in row['actual_checks'].items() if k!='coverage')
    assert row['actual_pgm_sha256']==pgm_sha and row['runtime_admission_claim'] is False
test=text('tests/test_a03_r8_r1_minimal.py')
assert "actual_checks = compare_synthetic_inputs(" in test and '_pre_coverage_decision(bundle, graph, actual_checks)' in test
assert "disposition'] = 'UNASSIGNED'" in test and "document['$defs']['Coverage']" in test
assert 'mock' not in test.lower()
runtime=text('src/annotation/runtime/storage/__init__.py');native=text('src/annotation/runtime/storage/native.py');guard=text('src/annotation/contracts/recovery.py')
assert '''"attempt_fact": "NOT_ATTEMPTED" if not intent else "MAY_HAVE_BEEN_ATTEMPTED" if row["state"] in ("INTENT", "UNKNOWN") else "ATTEMPTED"''' in runtime
assert "'attempt_fact': 'MAY_HAVE_BEEN_ATTEMPTED'" in native
assert "(canonical(resource).decode(), outcome, reg['book'], intent['action'])" in native
assert "self.project_plan(reg['id'], plan)" in native
assert "fact['plan_ref'] != p['plan_ref'] or fact['action_id'] != item['action_id'] or fact['result']['attempt_fact'] != item['attempt_fact'] or fact['intent_ref'] != item['intent_ref']" in guard
assert 'connection.rollback()' in runtime and 'connection.commit()' in runtime
trace=text(EV+'runs/N1/stderr.txt')
assert 'line 663, in _receipts_progress' in trace and 'progress fact/action/attempt differs' in trace
assert 'line 806, in _project_plan_locked' in trace and 'line 285, in commit_reconciliation' in trace
value={'status':'PRODUCER_GAP_CLOSED_WITH_FROZEN_EVIDENCE_RUNTIME_BLOCKER_CONFIRMED_STATICALLY',
 'producer_unified_diff':diff,'producer_sha256':sha(raw(P)),'profile_sha256':sha(raw(PROFILE)),'adoption_sha256':sha(raw(ADOPTION)),
 'profile_delta_only_producer_pin':True,'adoption_delta_only_profile_pin':True,
 'schema_pins_verified':len(profile['schema_pins']),'implementation_pins_verified':len(profile['implementation_pins']),
 'minimal_original_cases':minimal,'minimal_original_script_sha256':sha(test.encode()),'minimal_checks_rerun':0,
 'runtime_source_sha256':{'storage/__init__.py':sha(runtime.encode()),'storage/native.py':sha(native.encode()),'contracts/recovery.py':sha(guard.encode())},
 'static_guard_fields':['plan_ref','action_id','attempt_fact','intent_ref'],
 'guard_trace_sha256':sha(trace.encode()),'projection_value_is_static_inference_not_a_persisted_progress':True,
 'candidate_imports_native_API_or_tests':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'static-review.json',value)
print(json.dumps({'status':value['status'],'minimal_original_cases':len(minimal),'schema_pins':len(profile['schema_pins']),
 'implementation_pins':len(profile['implementation_pins']),'candidate_runs':0}))
