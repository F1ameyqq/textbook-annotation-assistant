# -*- coding: utf-8 -*-
"""Independent read-only SQLite/source/trace audit. No candidate imports."""
import json
from pathlib import Path
import sqlite3
from evidence import OUT,EV,TARGET,BASE,INDEX,MAP,load,raw,text,document,sha,canon,ref,author_read,author_key,write
prefix=EV+'validation/r9-01/cases/D1/'
paths={'before_runtime':prefix+'before-run-runtime.sqlite3','before_target':prefix+'before-run-target.sqlite3',
 'after_runtime':prefix+'runtime/runtime.sqlite3','after_target':prefix+'target/target.sqlite3'}
expected={'before_runtime':'21a04c566e9c989f0696a6449af0b339774e91574254ac611eeedaeb99b75ac9',
 'before_target':'d544641e1dddf3797d0a48e1916452426de5280fcdeb3e222456ee722cc352ec',
 'after_runtime':'192cea9caee1b34223045beb5fa016b7735f64ae32ecbf179ebb42bd08869b61',
 'after_target':'44ba882aecab97831995c12d21fa728c034c0ab42e66114d6799bbe415b628ec'}
copies=OUT/'immutable-copies';copies.mkdir(exist_ok=False);results={}
for role,source in paths.items():
    body=raw(source);digest=sha(body);assert digest==expected[role];p=copies/(role+'.sqlite3')
    with p.open('xb') as f:f.write(body)
    db=sqlite3.connect(p.resolve().as_uri()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row;queries=[]
    try:
        db.set_trace_callback(queries.append);db.execute('PRAGMA query_only=ON');assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        tables={name:[dict(r) for r in db.execute('SELECT * FROM "'+name.replace('"','""')+'"')] for name in names}
        app=db.execute('PRAGMA application_id').fetchone()[0];version=db.execute('PRAGMA user_version').fetchone()[0]
    finally:db.close()
    assert sha(p.read_bytes())==digest==sha(raw(source));p.unlink()
    results[role]={'source':source,'source_sha256_before':digest,'source_sha256_after':sha(raw(source)),
      'copy_sha256_before_after':digest,'copy_removed':True,'mode':'mode=ro&immutable=1; query_only=ON',
      'quick_check':'ok','application_id':app,'user_version':version,'counts':{k:len(v) for k,v in tables.items()},'tables':tables,'queries':queries}
copies.rmdir();before=results['before_runtime']['tables'];after=results['after_runtime']['tables'];target=results['after_target']['tables']
assert all(results['before_runtime']['counts'][n]==0 for n in ('plans','actions','intents','permits'))
assert results['before_target']['counts']['effects']==0
assert all(results['after_runtime']['counts'][n]==1 for n in ('plans','actions','intents','permits','native_pre_runs','native_creation_anchors'))
assert results['after_runtime']['counts']['artifacts']==14 and results['after_runtime']['counts']['resolutions']==results['after_runtime']['counts']['native_report_reads']==0
assert results['after_target']['counts']['effects']==1 and results['after_target']['counts']['observations']==3
first=document(EV+'validation/r9-01/D1-first-failure-SQL.json')
assert first['runtime']['tables']==after and first['target']['tables']==target
reg=after['registrations'][0];book=after['books'][0];planrow=after['plans'][0];action=after['actions'][0];intent=after['intents'][0];permit=after['permits'][0]
bundle=json.loads(author_read(reg['bundle_path']));lookup={canon(ref(a)):a for a in bundle['artifacts']}
assert len(lookup)==14 and {canon(json.loads(a['ref'])) for a in after['artifacts']}==set(lookup)
for a in bundle['artifacts']:assert sha(canon({k:v for k,v in a.items() if k!='content_hash'}))==a['content_hash']
planref=json.loads(planrow['ref']);plan=lookup[canon(planref)];intentref=json.loads(intent['ref']);receiptref=json.loads(intent['receipt']);receipt=lookup[canon(receiptref)]
assert planrow['id']==sha(canon(planref))==action['plan']==intent['plan']
assert len(plan['payload']['actions'])==1 and plan['payload']['actions'][0]['operation']=='CREATE_FRAMES'
planned=plan['payload']['actions'][0];assert planned['action_id']==action['id']==intent['action']
assert sha(canon(planned))==action['digest'] and action['intent']==intent['id']==permit['intent']
assert planrow['status']=='FINISHED' and action['state']==intent['state']=='APPLIED' and permit['state']=='CONSUMED'
package=reg['package_root'].replace('\\','/');resources=[]
def resource(item):
    b=author_read(package+'/'+item['path']);assert sha(b)==item['sha256'];resources.append({'ref':item,'bytes':len(b),'actual_sha256':sha(b)});return json.loads(b)
factref=json.loads(action['fact']);fact=resource(factref)
assert fact['origin_phase']=='EXECUTION' and fact['resolution_ref'] is None
assert fact['plan_ref']==planref and fact['intent_ref']==intentref and fact['action_id']==action['id'] and fact['action_digest']==action['digest']
assert fact['result']['outcome']=='APPLIED' and fact['result']['attempt_fact']=='ATTEMPTED' and not fact['result']['replay_allowed']
assert receipt['payload']['plan']==planref and receipt['payload']['action_fact_refs']==[factref] and receipt['payload']['results']==[fact['result']]
assert canon(receiptref) in {canon(json.loads(a['ref'])) for a in after['artifacts']}
for r in [fact['prepared_before'],fact['readback'],*fact['result']['attempt_evidence_refs']]:resource(r)
effect=json.loads(target['effects'][0]['body']);assert effect['plan_ref']==planref and effect['action_id']==action['id'] and effect['action_digest']==action['digest'] and effect['mutated']
assert effect['generation']==intent['generation'] and effect['owner_id']==intent['owner']
progress=[]
for a in bundle['artifacts']:
    if a['kind']=='ExecutionProgress':
        for item in a['payload']['actions']:
            if item.get('result_fact') is not None:
                assert a['payload']['plan_ref']==planref and item['action_id']==action['id'] and item['intent_ref']==intentref
                assert item['attempt_fact']=='ATTEMPTED' and item['result_fact']==factref and item['receipt_ref']==receiptref
                assert item['attempt_evidence_refs']==fact['result']['attempt_evidence_refs'];progress.append(ref(a))
assert progress
assert not any(a['kind']=='BatchReport' or (a['kind']=='CheckReport' and a['payload']['stage']=='POST_APPLY') for a in bundle['artifacts'])
assert book['phase']=='RELEASED' and book['owner'] is None and book['pid'] is None and book['lease']==0 and book['hold'] is None
before_run=document(prefix+'before-run.json');oldbook=before['books'][0]
assert oldbook['phase']=='ACTIVE' and oldbook['pid']==61832 and oldbook['owner']==before_run['owner']['owner_id']==intent['owner']
assert oldbook['generation']==before_run['owner']['generation']==intent['generation']==book['generation']
events=[json.loads(r['body']) for r in after['events']];assert events[-1]['event']=='OWNER_RELEASED'
assert events[-1]['owner_id']==intent['owner'] and events[-1]['generation']==intent['generation']
validation=EV+'validation/r9-01/'
assert not any(r['commit']==TARGET and (r['path'].startswith(validation+'cases/D2/') or r['path'].startswith(validation+'processes/D1-restart/') or r['path']==prefix+'normal-run-result.json') for r in INDEX)

release=document(EV+'process-release.json');records=[];expected_exit={42924:1,61832:1,21684:0,22652:0}
for row in release['records']:
    directory=row['path'].rsplit('/',1)[0];p=EV+directory+'/'
    pre=document(p+'preregistered.json');start=document(p+'started.json');end=document(p+'completed.json')
    assert row['pid']==start['pid']==end['pid'] and row['exit_code']==end['exit_code']==expected_exit[row['pid']]
    assert pre['argv'] and pre['cwd'] and 0<pre['timeout_seconds']<=90
    assert not row['alive'] and not row['timed_out'] and not end['alive'] and not end.get('timed_out',end.get('timeout',True))
    streams={name:raw(p+name+'.txt') for name in ('stdout','stderr')}
    for name,b in streams.items():
        if name+'_sha256' in end:assert sha(b)==end[name+'_sha256']
    if 'script_pins' in pre:
        for source,digest in pre['script_pins'].items():
            rev=TARGET if (TARGET,source) in MAP else BASE
            assert sha(raw(source,rev))==digest==sha(raw(p+'script-snapshots/'+Path(source).name))
    else:
        source='tests/test_a03_p2_r9_minimal_demos.py' if row['pid']==61832 else 'src/annotation/runtime/recovery/native_observation.py'
        assert pre['script_sha256']==sha(raw(source))==sha(raw(p+'script-snapshot.py'))
        if 'input_sha256' in pre:assert sha(raw(p+'request.json'))==pre['input_sha256']
    records.append({'record':directory,'pid':end['pid'],'exit_code':end['exit_code'],'argv':pre['argv'],'cwd':pre['cwd'],
      'timeout_seconds':pre['timeout_seconds'],'alive':False,'timed_out':False,'stdout_sha256':sha(streams['stdout']),'stderr_sha256':sha(streams['stderr']),
      'classification':'FIRST_REAL_FAILURE' if end['exit_code'] else 'COMPLETED'})
assert len(records)==4 and {r['pid'] for r in records}==set(expected_exit)
trace=text(EV+'validation/r9-01/processes/D1-execute/stderr.txt')
for token in ['line 123, in run_plan','line 30, in publish_quality','line 21, in publish_native_quality','line 64, in claim_current','line 416, in claim','lease expired AND previous process exited required']:assert token in trace
assert sha(trace.encode())=='0db6947c2321a6a6fe42b68486f7dc0f0cd7e5340a50a6f412f013fe9fc4852d'
metadata=document(EV+'metadata/first-seal-preparation/tool-transcript.json')
assert metadata['exit_code']==1 and metadata['product_calls']==0 and 'TypeError' in metadata['combined_tool_output'] and 'newline' in metadata['combined_tool_output']
assert 'write_text(' in text(EV+'metadata/first-seal-preparation/stdin-script.py.txt')

CRLF={'src/annotation/__init__.py','src/annotation/contracts/__main__.py','src/annotation/contracts/cli.py','src/annotation/contracts/integrity.py','src/annotation/contracts/models.py'}
def identity(source,digest):
    rev=TARGET if (TARGET,source) in MAP else BASE;b=raw(source,rev)
    if sha(b)==digest:return 'RAW_GIT_BYTES'
    assert source in CRLF and b'\r\n' not in b and sha(b.replace(b'\n',b'\r\n'))==digest
    return 'EXPLICIT_PREEXISTING_LF_TO_CRLF'
source_index=document(EV+'runs/D1/product-source-index.json');assert len(source_index)==65
representations=[{'source':r['path'],'actual_sha256':r['sha256'],'representation':identity(r['path'],r['sha256'])} for r in source_index]
assert {r['source'] for r in representations if r['representation']!='RAW_GIT_BYTES'}==CRLF
module_identity=[]
for name,r in document(validation+'imports/D1-execute.json')['modules'].items():
    source=author_key(r['path']);module_identity.append({'module':name,'actual_file':r['path'],'sha256':r['sha256'],'representation':identity(source,r['sha256'])})

recovery=text('src/annotation/runtime/recovery/__init__.py');quality=text('src/annotation/runtime/recovery/native_quality.py');storage=text('src/annotation/runtime/storage/__init__.py');driver=text('tests/test_a03_p2_r9_minimal_demos.py')
assert 'quality = publish_quality(store, reg["id"], projection)' in recovery and 'return publish_native_quality(store, registration_id, projection)' in recovery
assert recovery.index('keeper = LeaseKeeper(store, key, owner_id, generation).start()')<recovery.index('quality = publish_quality(')<recovery.index('keeper.stop()')
assert quality.index('claim = claim_current(store, observer, key)')<quality.index('INSERT INTO native_report_reads')
assert 'if row["lease"] > time.time() or self._pid_alive(row["pid"]):' in storage and 'if pid == os.getpid():\n            return True' in storage
assert "fault = None if label == 'D1'" in driver and 'owner_id=claim.owner_id, generation=claim.generation' in driver
profile=document('src/annotation/contracts/a03_native/data/profile.json')
affected=[r for r in profile['implementation_pins'] if r[0] in ('@annotation/runtime/recovery/__init__.py','@annotation/runtime/recovery/native_quality.py')];assert len(affected)==2
for source,digest in affected:assert sha(raw('src/'+source[1:]))==digest
excerpts=[]
for source,ranges in [('src/annotation/runtime/recovery/__init__.py',[(26,30),(75,96),(117,131)]),
 ('src/annotation/runtime/recovery/native_quality.py',[(12,28),(69,75)]),('src/annotation/runtime/storage/__init__.py',[(340,347),(378,380),(405,416),(454,459)]),
 ('tests/test_a03_p2_r9_minimal_demos.py',[(63,97)])]:
    lines=text(source).splitlines()
    for lo,hi in ranges:excerpts.append({'path':source,'start':lo,'end':hi,'raw_source_sha256':sha(raw(source)),'lines':[{'line':i,'text':lines[i-1]} for i in range(lo,hi+1)]})
write(OUT/'database-review.json',{'status':'IMMUTABLE_OWN_COPIES_AND_FORMAL_FAILURE_BINDINGS_VERIFIED','copies':results,
 'before_copies_limit':'two sequential file copies while keeper existed; not a cross-database atomic backup',
 'plan_ref':planref,'intent_ref':intentref,'receipt_ref':receiptref,'receipt_three_way_registration':True,
 'action_id':action['id'],'action_digest':action['digest'],'fact_ref':factref,'fact':fact,'resources':resources,'material_progress_refs':progress,
 'effects_before_after':[0,1],'attempt_fact':'ATTEMPTED','POST_Batch_report_reads':[0,0,0],
 'owner_before':oldbook,'owner_final':book,'effect':effect,'native_API_calls':0,'original_DB_connections':0})
write(OUT/'process-and-source-review.json',{'status':'FOUR_FROZEN_PROCESS_RECORDS_RECONCILED','records':records,'actual_module_identity':module_identity,
 'source_index_identity':representations,'original_TypeError_transcript':metadata,'metadata_failure_PID_raw_stream_limit_preserved':True,
 'D1_restart_and_D2':'NOT_RUN_AFTER_FIRST_D1_FAILURE','product_calls_by_reviewer':0,'OS_profile_scan':False})
write(OUT/'fault-review.json',{'status':'PRODUCT_OWNERSHIP_LIFECYCLE_DEFECT_CONFIRMED_NO_REEXECUTION',
 'classification':'Native run_plan reports while holding its own ACTIVE lease; publisher reacquires same book. OWNER_BUSY gate is correct; driver uses supported valid ownership. No contract ambiguity needed to explain failure.',
 'driver_extra_keeper':'The setup helper also renews this same lease. It is redundant, but run_plan starts and retains its own keeper, so removing the extra keeper does not remove the self-claim control-flow conflict.',
 'source_excerpts':excerpts,'affected_existing_implementation_pins':affected,
 'minimal_fix_boundary':['Pass current owner_id/generation through run_plan -> publish_quality -> publish_native_quality.',
 'Publisher validates and borrows the current lease without claim/release/keeper-stop; outer existing run_plan finally retains lifecycle responsibility.',
 'Standalone publish with no borrowed pair keeps its own claim/release; partial/stale/foreign ownership is refused without releasing caller ownership.',
 'Retain instance/PID/generation/ACTIVE/lease fencing and existing report-context pending/hold semantics; no ordinary-write authority from report-read reuse; retain durable single report read and two-second observation.',
 'Product changes touch the two existing pinned recovery modules, with corresponding two implementation digests/profile/adoption chain updated in a future authorized delivery; no schema/producer/oracle or shared claim relaxation.'],
 'necessary_future_revalidation_only':['Original D1 normal return and formal POST/Batch PENDING/NOT_SUBMITTED, fresh process reopen and supported duplicate protection with effect remaining one.',
 'Standalone publish on a complete formal receipt with unconsumed report-read slot acquires/releases its own lease.',
 'Borrowed valid ownership succeeds without an extra claim/generation or premature release; partial/stale/foreign ownership refuses and does not release caller lease; existing read-budget/fencing unchanged.',
 'Original R9 D2 once: real after-intent exit and bounded ABSENT recovery/old-plan no replay, preserve actual attempt facts.'],
 'D1_D2':'NOT_ACCEPTED','overall_A03':'REWORK','I01_released':False,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print(json.dumps({'status':'PRODUCT_OWNERSHIP_LIFECYCLE_DEFECT_CONFIRMED_NO_REEXECUTION','DB_copies':4,'effect':1,'attempt':'ATTEMPTED','POST_Batch_report_reads':[0,0,0],'original_processes':4,'product_calls':0}))
