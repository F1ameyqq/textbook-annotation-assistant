# -*- coding: utf-8 -*-
"""Before-first-run classification, source review and explicit own driver freeze."""
import ast
import copy
import difflib
import json
from pathlib import Path
import sqlite3
from evidence import OUT,WORK,EV,TARGET,BASE,raw,text,document,canon,sha,ref,write
P='src/annotation/runtime/recovery/__init__.py';Q='src/annotation/runtime/recovery/native_quality.py'
profile_path='src/annotation/contracts/a03_native/data/profile.json';adoption_path='src/annotation/contracts/a03_native/data/adoption.json'
old,new=text(P,BASE),text(P);oq,nq=text(Q,BASE),text(Q)
legacy='    from .quality import build_quality_report'
assert old[old.index(legacy):old.index('\ndef claim_current')]==new[new.index(legacy):new.index('\ndef claim_current')]
expected=copy.deepcopy(document(profile_path,BASE))
for item in expected['implementation_pins']:
    if item[0] in ('@annotation/runtime/recovery/__init__.py','@annotation/runtime/recovery/native_quality.py'):item[1]=sha(raw('src/'+item[0][1:]))
assert expected==document(profile_path)
expected=copy.deepcopy(document(adoption_path,BASE));expected['profile_sha256']=sha(raw(profile_path));assert expected==document(adoption_path)
profile=document(profile_path)
for p,d in profile['schema_pins']:assert sha(raw('src/annotation/contracts/a03_native/data/'+p))==d
for p,d in profile['implementation_pins']:
    p='src/'+p[1:] if p.startswith('@') else 'src/annotation/contracts/a03_native/'+p;assert sha(raw(p))==d
assert 'quality = publish_quality(store, reg["id"], projection, owner_id=owner_id, generation=generation)' in new
assert 'claim = Handle(owner_id=owner_id, generation=generation) if borrowed else claim_current(store, observer, key)' in nq
assert "finally:\n        if not borrowed:\n            store.release" in nq and "owner_id is None or generation is None" in nq
function=next(n for n in ast.parse(nq).body if isinstance(n,ast.FunctionDef) and n.name=='publish_native_quality')
transactions=[n for n in ast.walk(function) if isinstance(n,ast.With) and any(isinstance(i.context_expr,ast.Call) and isinstance(i.context_expr.func,ast.Attribute) and i.context_expr.func.attr=='transaction' for i in n.items)]
assert len(transactions)==3
for node in transactions:
    call=node.body[0].value;assert isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='_lease'
    assert any(k.arg=='pending_ok' and isinstance(k.value,ast.Constant) and k.value.value is True for k in call.keywords)
assert 'observe_bounded(observer, timeout=2)' in nq and "actual['read_elapsed_seconds'] > 2" in nq
storage=text('src/annotation/runtime/storage/__init__.py')
assert 'except sqlite3.Error as error:\n            connection.rollback()\n            fail("STORAGE_TRANSACTION_FAILED", str(error), 5)' in storage
driver=text('tests/test_a03_p2_r9_r1_owner_lifecycle.py')
assert 'except sqlite3.IntegrityError as error:' in driver
trace=text(EV+'validation/owner-r1-01/processes/borrow-execute/stderr.txt')
for token in ('sqlite3.IntegrityError: UNIQUE constraint failed: native_report_reads.plan_id','fail("STORAGE_TRANSACTION_FAILED", str(error), 5)','line 141, in report'):assert token in trace
assert sha(trace.encode())=='bc895733e5e37d479f5da9c57f73b29f23694a30a5b09e02a833a11cc7436fb5'
clones=OUT/'classification-copies';clones.mkdir(exist_ok=False);dbs={}
for role in ('runtime','target'):
    source=EV+'validation/owner-r1-01/cases/borrow/'+role+'/'+role+'.sqlite3';b=raw(source);p=clones/(role+'.sqlite3');p.write_bytes(b)
    db=sqlite3.connect(p.resolve().as_uri()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row;queries=[]
    try:
        db.set_trace_callback(queries.append);db.execute('PRAGMA query_only=ON');assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows={n:[dict(r) for r in db.execute('SELECT * FROM "'+n.replace('"','""')+'"')] for n in names}
    finally:db.close()
    assert sha(p.read_bytes())==sha(b)==sha(raw(source));p.unlink()
    dbs[role]={'source':source,'sha256_before_after':sha(b),'copy_sha256_before_after':sha(b),'removed':True,'queries':queries,'counts':{n:len(v) for n,v in rows.items()},'rows':rows}
clones.rmdir();assert dbs['runtime']['counts']['native_report_reads']==dbs['target']['counts']['effects']==1
reg=dbs['runtime']['rows']['registrations'][0];prefix='C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800/'
bundle_path=reg['bundle_path'].replace('\\','/');assert bundle_path.startswith(prefix)
bundle=document(bundle_path[len(prefix):]);posts=[a for a in bundle['artifacts'] if a['kind']=='CheckReport' and a['payload']['stage']=='POST_APPLY'];batches=[a for a in bundle['artifacts'] if a['kind']=='BatchReport']
assert len(posts)==len(batches)==1
assert not any(r['path'].endswith('/borrowed-owner-proof.json') or '/cases/D2/' in r['path'] for r in __import__('evidence').INDEX if r['commit']==TARGET)
write(OUT/'author-failure-classification.json',{'status':'AUTHOR_BORROW_DRIVER_EXCEPTION_EXPECTATION_ERROR_CONFIRMED','original_borrow':'FAILED','original_D2':'NOT_RUN',
 'actual_outer_type':'RuntimeFailure','actual_code':'STORAGE_TRANSACTION_FAILED','actual_cause':'sqlite3.IntegrityError: UNIQUE constraint failed: native_report_reads.plan_id',
 'frozen_trace_sha256':sha(trace.encode()),'DB_copies':dbs,'POST_ref':ref(posts[0]),'Batch_ref':ref(batches[0]),'report_reads':1,'effects':1,
 'missing_original_borrow_proof_preserved':True,'product_calls_by_auditor':0,'candidate_test_modified':False})

# Every edit below is in a NEW reviewer-owned test file, not the frozen driver.
adapted=driver
def replace_once(before,after):
    global adapted
    assert adapted.count(before)==1,before;adapted=adapted.replace(before,after,1)
replace_once('import time\n','import time\nimport traceback\n')
replace_once('def state(store, case):', '''def target_read_counts(case):
    path = case / 'target/target.sqlite3'
    raw = path.read_bytes()
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        counts = {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            for name in ('effects', 'observations')}
    assert path.read_bytes() == raw
    return {'sha256': sha(raw), 'counts': counts}


def state(store, case):''')
replace_once("    return {'book': book, 'counts': counts, 'events': events,\n        'effect_count': original.effect_count(case), 'bundle': store.bundle(reg['id'])}",
 "    bundle = store.bundle(reg['id'])\n    return {'book': book, 'counts': counts, 'events': events,\n        'effect_count': original.effect_count(case), 'bundle': bundle, 'target': target_read_counts(case),\n        'report_artifact_counts': {'POST': sum(a['kind'] == 'CheckReport' and a['payload']['stage'] == 'POST_APPLY' for a in bundle['artifacts']),\n            'Batch': sum(a['kind'] == 'BatchReport' for a in bundle['artifacts'])}}")
replace_once('    from annotation.runtime.storage.common import plain\n','    from annotation.runtime.storage.common import plain, RuntimeFailure\n')
replace_once('                except Exception as error:\n','                except RuntimeFailure as error:\n')
replace_once("                assert start['counts'] == end['counts'] and start['events'] == end['events']\n", "                assert start['counts'] == end['counts'] and start['events'] == end['events']\n                assert start['target'] == end['target'] and start['bundle'] == end['bundle']\n")
replace_once('            # Existing durable single-read fence must fail before another read.\n',
 "            assert after['counts']['native_report_reads'] == 1 and after['report_artifact_counts'] == {'POST': 1, 'Batch': 1}\n            write(case / 'borrowed-owner-proof.json', {'before': before, 'after': after, 'controls': controls,\n                'quality': plain(quality), 'outer_keeper_alive': True, 'saved_before_read_limit_control': True})\n            # Existing durable single-read fence must fail before another read.\n")
replace_once("            except sqlite3.IntegrityError as error:\n                limit = {'type': type(error).__name__, 'message': str(error)}\n",
 "            except RuntimeFailure as error:\n                assert error.code == 'STORAGE_TRANSACTION_FAILED'\n                assert str(error) == 'UNIQUE constraint failed: native_report_reads.plan_id'\n                assert isinstance(error.__context__, sqlite3.IntegrityError)\n                assert str(error.__context__) == 'UNIQUE constraint failed: native_report_reads.plan_id'\n                limit = {'type': type(error).__name__, 'code': error.code, 'message': str(error),\n                    'context_type': type(error.__context__).__name__, 'context_message': str(error.__context__),\n                    'traceback': traceback.format_exc()}\n")
replace_once("            assert limited['counts'] == after['counts'] and limited['events'] == after['events']\n", "            assert limited['counts'] == after['counts'] and limited['events'] == after['events']\n            assert limited['target'] == after['target'] and limited['bundle'] == after['bundle']\n            assert limited['report_artifact_counts'] == after['report_artifact_counts'] == {'POST': 1, 'Batch': 1}\n            keeper.check()\n")
replace_once("            write(case / 'borrowed-owner-proof.json', {'before': before, 'after': after, 'after_read_limit_refusal': limited,", "            write(case / 'single-read-refusal-proof.json', {'before': before, 'after': after, 'after_read_limit_refusal': limited,")
own=WORK/'tests/review_a03_p2_r9_r1_owner_lifecycle.py';ast.parse(adapted,filename=str(own))
with own.open('xb') as f:f.write(adapted.encode())
for p in WORK.rglob('*.py'):ast.parse(p.read_bytes(),filename=str(p))
diff='\n'.join(difflib.unified_diff(driver.splitlines(),adapted.splitlines(),fromfile='frozen/'+str(Path('tests/test_a03_p2_r9_r1_owner_lifecycle.py')),tofile='reviewer/'+own.relative_to(WORK).as_posix(),lineterm=''))+'\n'
(OUT/'independent-driver.diff').write_text(diff,encoding='utf8')
write(OUT/'independent-driver.json',{'file':own.relative_to(OUT).as_posix(),'bytes':own.stat().st_size,'sha256':sha(own.read_bytes()),
 'derived_from':'tests/test_a03_p2_r9_r1_owner_lifecycle.py','derived_commit':TARGET,'original_sha256':sha(driver.encode()),
 'changes':'precise RuntimeFailure/constraint/cause assertion; proof before negative; read-only target/report/bundle before-after assertions; no product/input change',
 'expected_read_limit':{'type':'RuntimeFailure','code':'STORAGE_TRANSACTION_FAILED','message':'UNIQUE constraint failed: native_report_reads.plan_id','context_type':'IntegrityError'},
 'frozen_before_first_product_run':True,'product_calls_in_preparation':0,'candidate_original_modified':False})
write(OUT/'static-review.json',{'status':'READY_FOR_FOUR_BOUNDED_GROUPS_ONCE','modified_old_paths':__import__('evidence').load(OUT/'delivery-byte-index.json')['modified_old_paths'],
 'legacy_body_text_unchanged':True,'report_transactions_fenced':3,'schema_pins':len(profile['schema_pins']),'implementation_pins':len(profile['implementation_pins']),
 'recovery_diff':list(difflib.unified_diff(old.splitlines(),new.splitlines(),lineterm='')),'native_quality_diff':list(difflib.unified_diff(oq.splitlines(),nq.splitlines(),lineterm='')),
 'only_two_implementation_pins_and_adoption_chain_changed':True,'author_failure':'DRIVER_EXPECTATION_ERROR_ORIGINAL_FAILED_PRESERVED',
 'D2_attempt_semantics_static':'Existing _progress_attempt returns MAY_HAVE_BEEN_ATTEMPTED for an INTENT with no result fact; driver preserves persisted before/after value, not business-field rewriting.',
 'preparation_path_query_limit':'Initial rg named absent projection.py/reconciliation.py files; corrected to storage implementation. Rendered lookup errors only, no product call/PID claim.',
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print(json.dumps({'status':'READY_FOR_FOUR_BOUNDED_GROUPS_ONCE','author_error':'DRIVER_EXPECTATION_ERROR','new_driver_sha256':sha(own.read_bytes()),'candidate_calls':0}))
