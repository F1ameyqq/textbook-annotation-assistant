# -*- coding: utf-8 -*-
"""Read the N7 failure and existing contracts/callers; do not replay any opener."""
import json
import subprocess
from evidence import OUT,ROOT,TARGET,EV,text,raw,sha,write
persistent=text('src/annotation/delivery/mock/persistent.py');contract=text('src/annotation/contracts/validation.py')
trace=text(EV+'runs/N7/stderr.txt');driver=text('tests/test_a03_r8_r3_post_hold.py')
opening=persistent[persistent.index('    def open(cls,'):persistent.index('    def _connect(self):')]
assert 'class ContractError(ValueError):' in contract
assert 'except (sqlite3.Error, ValueError, TypeError, KeyError) as exc:' in opening
assert opening.index('reject("TARGET_STORE_VERSION_UNSUPPORTED"')<opening.index('except (sqlite3.Error, ValueError, TypeError, KeyError)')
assert 'reject("TARGET_STORE_CORRUPT", str(exc))' in opening
assert 'mode=rw' in opening and 'INSERT ' not in opening and 'UPDATE ' not in opening and 'DELETE ' not in opening and 'DROP ' not in opening
assert "'TARGET_STORE_CORRUPT' != 'TARGET_STORE_VERSION_UNSUPPORTED'" in trace
assert driver.index("refusal(self, 'TARGET_STORE_VERSION_UNSUPPORTED'")<driver.index("incomplete = EVIDENCE / 'cases/N7-incomplete'")
scope=['src','tests','docs/contracts-v1.md','docs/architecture.md','docs/tasks/A03-runtime-recovery.md','docs/tasks/A03-independent-review.md','docs/tasks/A03-P2-R8-native-bridge-implementation.md']
argv=['git','-c','core.longpaths=true','grep','-n','-E','TARGET_STORE_VERSION_UNSUPPORTED|TARGET_STORE_CORRUPT',TARGET,'--',*scope]
matches=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.decode().splitlines()
assert all(':src/annotation/delivery/mock/persistent.py:' in r or ':tests/test_a03_r8_r3_post_hold.py:' in r for r in matches)
ordinary=text('src/annotation/runtime/recovery/__init__.py');start=ordinary.index('def open_observer(');end=ordinary.find('\ndef ',start+1)
caller=ordinary[start:end]
assert 'PersistentMockSession.open' in caller and 'bridge_context=' in caller
requirements={p:text('docs/tasks/'+p) for p in ('A03-runtime-recovery.md','A03-independent-review.md')}
assert all('TARGET_STORE_VERSION_UNSUPPORTED' not in v and 'TARGET_STORE_CORRUPT' not in v for v in requirements.values())
value={'N7_original_status':'FAILED_EXACT_OUTER_CODE_ASSERTION','classification':'NEW_DRIVER_ASSERTION_MORE_SPECIFIC_THAN_EXISTING_WRITTEN_CONTRACT',
 'actual_rejection':True,'inner_code':'TARGET_STORE_VERSION_UNSUPPORTED','outer_code':'TARGET_STORE_CORRUPT',
 'cause':'ContractError inherits ValueError; business version rejection occurs inside broad ValueError catch',
 'source_and_trace_sha256':{'persistent.py':sha(persistent.encode()),'ContractError_source':sha(contract.encode()),'N7_stderr':sha(trace.encode())},
 'existing_requirement':'V08/R14 require fail-closed format rejection and locatable errors/history, not this exact outer symbol',
 'existing_source_test_contract_search':{'argv':argv,'matches':matches},
 'repository_caller_impact':'No branch on either symbol outside persistent.py or the new N7 test was found in the searched source/tests/contracts. Native normal observer uses the explicit native bridge.',
 'observable_diagnostic_effect':'Outer classification is CORRUPT while inner VERSION_UNSUPPORTED remains in the message; this is not proof that native bytes are damaged.',
 'state_effect_boundary':'Actual failure precedes session construction and every write statement in open; post-run DB identity must still be checked. No N7-specific before/after hash pair is claimed.',
 'open_is_not_a_readonly_API':'It uses mode=rw; reviewer did not invoke it.',
 'product_change_required_by_this_failed_assertion':False,'driver_change_decision':'Coordinator should settle the diagnostic assertion against the contract; no product or test changed in this review.',
 'strict_reopen_and_old_runtime_rejection':'Reached before the failed assertion in original test control flow',
 'incomplete_initialization':'NOT_REACHED','N6':'NOT_RUN','N7_replays_or_variants':0,
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'N7-readonly-classification.json',value)
print(json.dumps({'classification':value['classification'],'N7_status':value['N7_original_status'],'product_change_predecided':False,'N7_runs':0}))
