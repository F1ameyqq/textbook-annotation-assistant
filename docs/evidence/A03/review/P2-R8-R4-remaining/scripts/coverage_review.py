# -*- coding: utf-8 -*-
"""Original criteria mapping only; never runs remaining or prior cases."""
import copy
import json
from evidence import OUT,WF,EV,load,document,write
prior=document('docs/evidence/A03/review/P2-R8-R3-post-hold/p2-independent-coverage-review.json',WF)
author=document(EV+'coverage-map.json');assert len(author['V'])==10 and len(author['R'])==18 and len(author['N1_to_N7'])==7
assert load(OUT/'independent-N6-review.json')['actual_create_plan_returns']==1
assert load(OUT/'independent-N7-initialization-review.json')['existing_hook_calls']==1
entries=[]
for row in prior['entries']:
    value=copy.deepcopy(row);value['R3_independent_status']=value.pop('independent_status')
    value['R3_remaining_historical']=value.pop('remaining_original_scope')
    value['independent_status']=value['R3_independent_status'];value['R4_added_coverage']='NONE; frozen R3 scope preserved'
    value['remaining_original_scope_current']=value['R3_remaining_historical']
    if value['id'] in ('V07','R02'):
        value['R4_added_coverage']='Full formal 20-artifact UNKNOWN history passed to verifier; real anchor-based plan/actions recomputed once; named PRE EvidenceRecord removal rejected at closure; dual DB bytes and permit/effect unchanged.'
    if value['id'] in ('V08','R14'):
        value['independent_status']='PARTIAL_RUNTIME_INIT_HOOK_ADDED_ORIGINAL_N7_FAILED_PRESERVED'
        value['R4_added_coverage']='One existing runtime before_completion hook controlled exception, same original exception propagated; absent anchor/completion; normal open once refused; empty runtime rows and target NOT_CREATED.'
        value['remaining_original_scope_current']='Original R3 N7 exact diagnostic assertion remains FAILED and its over-specific assertion classification unchanged; other runtime/target initialization cuts, corruption/replacement/I/O/migration controls not run.'
    if value['id'] in ('V01','R04','R17'):
        value['R4_added_coverage']='Fresh N1 prerequisite reran exact accepted method once; formal singleton receipt/progress/POST/Batch independently verified; no added general coverage.'
    value['no_criterion_waived']=True;entries.append(value)
assert len(entries)==28 and {r['id'] for r in entries}=={'V%02d'%i for i in range(1,11)}|{'R%02d'%i for i in range(1,19)}
ns=[]
for i in range(1,8):
    if i==1:state='R4_FRESH_N1_PREREQUISITE_ONCE_FORMAL_BOUNDARIES_VERIFIED';scope='fixed synthetic singleton recovery only'
    elif i in (2,3,4,5):state='R3_LIMITED_ACCEPTANCE_PRESERVED_NOT_RERUN';scope='exact prior R3 limits retained'
    elif i==6:state='R4_LIMITED_ACCEPTED';scope='one complete historical anchor recompute plus one named PRE dependency closure refusal'
    else:state='R4_INITIALIZATION_BRANCH_LIMITED_ACCEPTED_ORIGINAL_R3_N7_FAILED_PRESERVED';scope='one runtime same-process hook/open refusal; strict reopen/old entry boundaries static R3 references only'
    ns.append({'id':'N'+str(i),'status':state,'scope':scope})
write(OUT/'p2-independent-coverage-review.json',{'status':'ALL_28_ORIGINAL_CRITERIA_AND_N1_N7_MAPPED_NO_WAIVER','entries':entries,'N1_to_N7':ns,
 'author_map_checked_counts':{'V':10,'R':18,'N':7},'R3_original_N7':'FAILED_PRESERVED','R3_diagnostic_classification':'NEW_DRIVER_ASSERTION_MORE_SPECIFIC_THAN_EXISTING_WRITTEN_CONTRACT',
 'remaining_original_requirements':['Normal native multi-action and explicit-not-applied demonstrations; mixed action tail and sufficient/insufficient ABSENT.',
 'Native multiple same-book scope/run obligations and independent/mixed multi-book cases; two owner contenders and other crash cuts.',
 'Qualified hold clear, distinct hold-id replacement, fresh recheck/new plan after ABSENT, fork/cycle/wrong identity/hash/action/policy/capability/authorization matrices.',
 'Other initialization/damage/I/O/migration cuts; archive validator/conversion and legacy no-intent UNKNOWN behavior.',
 'Real/ORIGINAL/OBSERVED admission negatives, S01, B mapping confirmation and real platform acceptance.',
 'Old report reuse/VERIFIED tampering, zero/unknown denominator, skipped/exception/unmapped and max-attempt boundaries.'],
 'integration_limit':'No overall A03 acceptance, INTEGRATED write, I01 release or B dispatch; broad original requirements retained, not added to current execution.',
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print('{"status":"ALL_28_ORIGINAL_CRITERIA_AND_N1_N7_MAPPED_NO_WAIVER","V_R":28,"N":7}')
