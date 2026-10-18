# -*- coding: utf-8 -*-
"""One file-only closure, without candidate imports or SQLite connections."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
from datetime import datetime

ROOT=Path('D:/1800')
OUT=Path(__file__).resolve().parents[1]
OLD=ROOT/'docs/evidence/A03/review/P2-R11-crash-cuts'
REPORT=ROOT/'docs/tasks/A03-P2-R11-R1-archive-closure-review-report.md'
OLD_REPORT=ROOT/'docs/tasks/A03-P2-R11-crash-cuts-review-report.md'
WF='188fed05cd51789521b27efb04b2426f630571d0'
TARGET='cc5966dc58c62017a27266c40ca0cedc5c68485c'
BASE='1c26b4a8eb378af33e57668472d2071e9ea6afff'
TASK='docs/tasks/A03-P2-R11-R1-archive-closure.md'
OLD_REL=OLD.relative_to(ROOT).as_posix()+'/'
RESET='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'
EXPECTED={
 TASK:'9565f3e8cd86373ddda5cdf728cf5e07ec07347dfa1824319a53b20fcc5cf7c1',
 OLD_REPORT.relative_to(ROOT).as_posix():'a964ef76d836c9935dd391ad72e073f49395196ffbcd5aa43040a8cd5498127c',
 OLD_REL+'sha256-manifest.json':'eff77340f2577d1cf66eaa3c69ad4609b2673b87002951333d7f856b158f494c',
 OLD_REL+'process-release.json':'eded396dddfa7b46d1b4e0c35bd5ed9af9853ba9d2ad89ce955e36c5d6c98d4a'}
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(value if isinstance(value,bytes) else (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def load(p):return json.loads(p.read_bytes())
def ref(a):return {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}
git_counter=0
def git(*args,data=b''):
    global git_counter
    git_counter+=1;d=OUT/'git-processes'/('%02d'%git_counter);d.mkdir(parents=True,exist_ok=False)
    argv=['git','-c','core.longpaths=true',*args]
    write(d/'stdin.bin',data)
    write(d/'preregistered.json',{'argv':argv,'cwd':str(ROOT),'timeout_seconds':15,'registered_at_ns':time.time_ns(),
      'source_sha256':sha(Path(__file__).read_bytes()),'stdin_sha256':sha(data)})
    with (d/'stdout.bin').open('xb') as stdout,(d/'stderr.bin').open('xb') as stderr:
        p=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr)
        write(d/'started.json',{'pid':p.pid,'started_at_ns':time.time_ns()});timed=False
        try:p.communicate(input=data,timeout=15)
        except subprocess.TimeoutExpired:timed=True;p.kill();p.communicate()
    write(d/'completed.json',{'pid':p.pid,'exit_code':p.returncode,'timed_out':timed,'alive':p.poll() is None,
      'ended_at_ns':time.time_ns(),'stdout_sha256':sha((d/'stdout.bin').read_bytes()),'stderr_sha256':sha((d/'stderr.bin').read_bytes())})
    assert p.returncode==0 and not timed
    return (d/'stdout.bin').read_bytes()

critical=[TASK,*EXPECTED.keys(),
 OLD_REL+'case-and-boundary-review.json',OLD_REL+'process-and-import-review.json',
 OLD_REL+'driver-preregistration.json',OLD_REL+'input-index.json',OLD_REL+'isolated-source-index.json',
 OLD_REL+'post-functional-metadata-correction.json',OLD_REL+'final-verification.json',OLD_REL+'final-outcome.json',
 OLD_REL+'runs/report-01/registration.json',OLD_REL+'runs/report-01/completion.json',
 OLD_REL+'runs/report-01/stderr.log',OLD_REL+'runs/report-01/entry-source.py',
 OLD_REL+'scripts/write_report.py',OLD_REL+'runs/process-audit-01/stderr.log',
 'docs/tasks/A03-P2-R11-crash-cuts-review-handoff.md',
 'docs/tasks/A03-P2-R11-crash-cut-validation.md']
critical=sorted(set(critical))
tree={}
for row in git('ls-tree','-rz','--full-tree',WF,'--',OLD_REL,OLD_REPORT.relative_to(ROOT).as_posix(),*critical).split(b'\0'):
    if row:
        meta,path=row.split(b'\t',1);mode,kind,oid=meta.decode().split();tree[path.decode()]={'mode':mode,'kind':kind,'oid':oid}
specs=[WF+':'+p for p in critical]
batch=git('cat-file','--batch',data=('\n'.join(specs)+'\n').encode())
pos=0;raw={};raw_index=[]
for spec,path in zip(specs,critical):
    end=batch.index(b'\n',pos);head=batch[pos:end].decode().split();pos=end+1
    assert len(head)==3 and head[1]=='blob'
    size=int(head[2]);body=batch[pos:pos+size];pos+=size;assert batch[pos:pos+1]==b'\n';pos+=1
    oid=hashlib.sha1(b'blob '+str(size).encode()+b'\0'+body).hexdigest()
    assert oid==head[0]==tree[path]['oid'];raw[path]=body
    if path in EXPECTED:assert sha(body)==EXPECTED[path]
    raw_index.append({'commit':WF,'path':path,'raw_git_sha1':oid,'bytes':size,'sha256':sha(body),'record':'git-processes/02/stdout.bin'})
assert pos==len(batch)
write(OUT/'raw-input-index.json',{'workflow':WF,'target':TARGET,'files':raw_index,'historical_corpus_copied':False})
write(OUT/'inputs/closure-task.md',raw[TASK])
old_manifest=json.loads(raw[OLD_REL+'sha256-manifest.json'])
assert len(old_manifest['files'])==1208
manifest_map={r['path']:r for r in old_manifest['files']}
manifest_path=OLD_REL+'sha256-manifest.json'
expected_paths=set(manifest_map)|{manifest_path}
actual_paths={p.relative_to(ROOT).as_posix() for p in OLD.rglob('*') if p.is_file()}|{OLD_REPORT.relative_to(ROOT).as_posix()}
assert expected_paths==actual_paths and len(expected_paths)==1209
old_rows=[]
for path in sorted(expected_paths):
    p=ROOT/path;body=p.read_bytes();digest=sha(body);oid=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
    assert tree[path]['kind']=='blob' and tree[path]['mode']=='100644' and oid==tree[path]['oid']
    if path in manifest_map:assert len(body)==manifest_map[path]['bytes'] and digest==manifest_map[path]['sha256']
    else:assert digest==EXPECTED[path]
    old_rows.append({'path':path,'bytes':len(body),'sha256':digest,'workflow_git_blob':oid})
for path,body in raw.items():
    if path.startswith(OLD_REL) or path==OLD_REPORT.relative_to(ROOT).as_posix():assert body==(ROOT/path).read_bytes()
write(OUT/'original-preservation-before.json',{'workflow':WF,'files':old_rows,'count':len(old_rows),
 'total_bytes':sum(r['bytes'] for r in old_rows),'inventory_sha256':sha(canon(old_rows)),
 'method':'Every local raw SHA256 and Git blob SHA1 equals the fixed workflow; no old bodies copied except necessary raw input records.'})

def frozen_doc(name):return json.loads(raw[OLD_REL+name])
input_index=frozen_doc('input-index.json');assert input_index['target']==TARGET and input_index['base']==BASE
assert len(input_index['exports'])==677
input_map={(r['commit'],r['path']):r for r in input_index['exports']}
for r in input_index['exports']:
    path=OLD_REL+r['file'];assert manifest_map[path]['sha256']==r['sha256'] and manifest_map[path]['bytes']==r['bytes']
source_index=frozen_doc('isolated-source-index.json');assert len(source_index['files'])==77 and not source_index['author_DB_or_validation_copied']
for r in source_index['files']:assert manifest_map[OLD_REL+r['file']]['sha256']==r['sha256']
audit=frozen_doc('case-and-boundary-review.json');proc=frozen_doc('process-and-import-review.json')
if 'target' in audit:assert audit['target']==TARGET
assert len(audit['all_SQL_audits'])==64 and audit['independent_stage_raw_files']==32 and audit['auditor_product_calls']==0
assert audit['author_active_database_connections']==0 and not audit['author_missing_intermediate_binaries_reconstructed']
assert proc['author_process_count']==19 and proc['independent_nested_count']==14 and proc['actual_import_module_records']==492
assert proc['auditor_product_calls']==0 and proc['crash_exit_finally_imports_absent_not_fabricated']
old_final=frozen_doc('final-verification.json');assert old_final['status']=='REWORK' and old_final['archive_failures_retained']==2
assert old_final['static_metadata_corrections']==1 and not old_final['second_archive_error_corrected_or_retried']
correction=frozen_doc('post-functional-metadata-correction.json');assert correction['correction_count']==1 and correction['functional_reruns']==0
old_release=frozen_doc('process-release.json')
assert old_release['known_registered_child_count']==33
original_processes=old_release['review_and_functional_parents']+old_release['git_children']+old_release['nested_business_and_observation_children']+[old_release['seal_recorder_wrapper']]
assert len(original_processes)==33
for r in original_processes:assert not r['alive'] and not r['timed_out'] and r['exit_code'] in (0,1,90)
assert sum(r['exit_code']==1 for r in original_processes)==2 and sum(r['exit_code']==90 for r in original_processes)==4

identity=load(OLD/'independent-run.json');run_root=Path(identity['run_root']).resolve();work=Path(identity['workspace']).resolve()
assert run_root.is_relative_to(OLD) and not identity['author_DB_or_validation_copied']
def old_path(value):
    p=Path(value);p=p if p.is_absolute() else work/p;p=p.resolve()
    assert p.is_relative_to(OLD);path=p.relative_to(ROOT).as_posix();assert path in manifest_map
    return p
def old_doc(value):return load(old_path(value))
def original_db_path(r):
    if r['label'].startswith('author-'):
        key=r['source'].replace('\\','/');prefix='C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800/'
        if key.startswith(prefix):key=key[len(prefix):]
        return OLD_REL+input_map[(TARGET,key)]['file']
    return old_path(r['source']).relative_to(ROOT).as_posix()
db_refs=[]
for r in audit['all_SQL_audits']:
    path=original_db_path(r);assert r['quick_check']=='ok' and r['copy_removed'] and not r['original_connection']
    assert manifest_map[path]['sha256']==r['sha256_before_after']
    db_refs.append({'completed_audit_label':r['label'],'file':path,'sha256':r['sha256_before_after'],'old_quick_check':'ok',
      'SQL_audit_repeated_this_round':False})
write(OUT/'completed-audit-reference-index.json',{'completed_SQL_audits_referenced':64,'new_SQL_connections':0,'records':db_refs,
 'old_processes_referenced':33,'old_author_processes':19,'old_independent_nested':14,'old_import_module_records':492})

bad=raw[OLD_REL+'scripts/write_report.py'];bad_snapshot=raw[OLD_REL+'runs/report-01/entry-source.py']
assert bad==bad_snapshot
bad_text=bad.decode('utf8',errors='strict');line35=bad_text.splitlines()[34]
stderr=raw[OLD_REL+'runs/report-01/stderr.log'].decode('utf8',errors='strict')
assert 'SyntaxError: Non-UTF-8 code' in stderr
old_record=frozen_doc('runs/report-01/completion.json');old_pre=frozen_doc('runs/report-01/registration.json')
assert old_record['exit_code']==1 and sha(bad)==old_pre['entry_sha256']
assert not (OLD/'coverage-map.json').exists()
write(OUT/'encoding-and-output-gap.json',{'original_script_sha256':sha(bad),'same_as_preregistered_snapshot':True,
 'strict_UTF8_decode_of_frozen_bytes':'PASS','original_script_executed_or_compiled_this_round':False,
 'historical_stderr':stderr,'historical_exit_code':1,'historical_pid':old_record['pid'],
 'historical_diagnostic_line':35,'line35_UTF8_bytes':len(line35.encode('utf8')),
 'causal_limit':'The frozen bytes decode as UTF-8. The historical interpreter reported a source-decoding SyntaxError. A claim that the retained file is invalid UTF-8 is not established; the exact interpreter-level cause is not reproduced or inferred.',
 'output_gap':'Normal report/coverage-map was not generated by report-01; the manual REWORK report remains unchanged.',
 'treatment':'New explicitly UTF-8 decoded/compiled file-only closure; no execution, repair or retry of the old script.'})

cases=[c for c in audit['cases'] if c['label']=='independent']
assert {c['group'] for c in cases}=={'F1','F2','F3','F4'}
stage_index=[];coverage=[]
for c in cases:
    g=c['group'];case=run_root/'cases'/g
    before=old_doc(case/'before-run.json');cut=old_doc(run_root/(g+'-after-exit90-before-reopen.json'))
    final=old_doc(run_root/(g+'-final-SQL.json'));result=old_doc(case/'result.json')
    assert result==c['result'] and result['POST_count']==result['Batch_count']==result['report_read_count']==0
    r=final['runtime']['tables'];t=final['target']['tables'];cr=cut['runtime']['tables'];ct=cut['target']['tables']
    reg=r['registrations'][0];bundle=old_doc(reg['bundle_path']);lookup={canon(ref(a)):a for a in bundle['artifacts']}
    plan=lookup[canon(before['plan_ref'])];action=plan['payload']['actions'][0]
    assert len(plan['payload']['actions'])==1 and action['operation']=='CREATE_FRAMES'
    assert plan['payload']['precheck']==before['pre_ref'] and plan['payload']['snapshot']==before['snapshot_ref']
    assert r['actions'][0]['id']==action['action_id'] and r['actions'][0]['digest']==sha(canon(action))
    assert r['native_pre_runs'][0]['status']=='ADMITTED' and r['native_pre_runs'][0]['id']==before['native_pre_run_id']
    assert {canon(json.loads(v['ref'])) for v in r['artifacts']}==set(lookup)
    effect=0 if g in ('F1','F2') else 1
    assert c['effects']==len(ct['effects'])==len(t['effects'])==effect and ct['effects']==t['effects']
    assert c['plan_status']==r['plans'][0]['status']==result['actual_plan_status']
    processes=c['processes'];assert processes['crash']['exit_code']==90 and processes['query']['exit_code']==0
    assert processes['crash']['pid']!=processes['query']['pid'] and processes['crash']['end']<processes['query']['start']
    marker=old_doc(case/'crash.marker.json');assert marker==c['marker'] and marker['pid']==processes['crash']['pid']
    assert c['original_instance']!=c['query_instance']
    events=[json.loads(v['body']) for v in r['events']];cut_events=[json.loads(v['body']) for v in cr['events']]
    assert events[:len(cut_events)]==cut_events
    row={'group':g,'verdict':'ACCEPTED_CASE_WITHIN_FOUR_CUT_SCOPE','fault_point':marker['point'],
      'existing_functional_rounds':1,'new_functional_calls':0,'effects_before_after':[effect,effect],
      'actual_plan_state':c['plan_status'],'original_owner':c['original_owner'],'original_instance':c['original_instance'],
      'query_instance':c['query_instance'],'existing_processes':processes,'plan_ref':ref(plan),'PRE_ref':before['pre_ref'],
      'intent_ref':None,'receipt_ref':None,'resolution_ref':None,'observation_ref':None,
      'reconcile_calls_in_original_run':result['reconcile_calls'],'POST':0,'Batch':0,'native_report_reads':0,
      'sources':[str(case/'result.json'),str(run_root/(g+'-after-exit90-before-reopen.json')),str(run_root/(g+'-final-SQL.json'))]}
    expected_stages=['pre-fault','cut-after-wait']+(['pending-before-projection','UNKNOWN-before-reconcile'] if g in ('F2','F3') else [])+['after-query-or-recovery']
    assert [s['stage'] for s in c['stage_captures']]==expected_stages
    for s in c['stage_captures']:
        capture=case/'stages'/s['stage']/'capture.json';assert old_doc(capture)==s
        assert s['own_writer_keeper_active']==(s['stage']=='pre-fault')
        for name,v in s['databases'].items():
            p=old_path(v['copy']);path=p.relative_to(ROOT).as_posix();assert manifest_map[path]['sha256']==v['sha256'] and manifest_map[path]['bytes']==v['bytes']
            assert v['SQL']['quick_check']=='ok' and v['SQL']['raw_sha256_before']==v['SQL']['raw_sha256_after']==v['sha256']
            completed=next(x for x in audit['all_SQL_audits'] if x['label']=='independent-'+g+'-'+s['stage']+'-'+name)
            assert completed['SQL']==v['SQL']['tables'] and completed['sha256_before_after']==v['sha256']
            stage_index.append({'group':g,'stage':s['stage'],'database':name,'file':path,'bytes':v['bytes'],'sha256':v['sha256'],
              'capture_file':capture.relative_to(ROOT).as_posix(),'capture_sha256':manifest_map[capture.relative_to(ROOT).as_posix()]['sha256'],
              'capturing_pid':s['pid'],'own_writer_keeper_active':s['own_writer_keeper_active'],
              'read_started_at_ns':v['read_started_at_ns'],'read_ended_at_ns':v['read_ended_at_ns'],
              'completed_SQL_audit_label':completed['label'],'SQL_audit_repeated':False})
    if g in ('F1','F4'):
        assert result['open_status_query_only'] and result['reconcile_calls']==0 and not r['calls'] and not r['attempts'] and not r['resolutions']
        for name in ('runtime','target'):assert cut[name]['raw_sha256_before']==final[name]['raw_sha256_after']
        assert r['books'][0]['phase']=='ACTIVE' and r['books'][0]['generation']==1
    if g=='F1':
        assert len(cr['plans'])==len(cr['actions'])==1 and not cr['intents'] and not cr['permits'] and result['attempt_fact'] is None
        assert not any(a['kind'] in ('WriteIntent','ExecutionReceipt','ExecutionProgress','ReconciliationResult') for a in bundle['artifacts'])
        row['attempt_fact']=None;row['attempt_limit']='No formal result; no NOT_ATTEMPTED receipt fabricated.'
    else:
        intent=r['intents'][0];ir=json.loads(intent['ref']);fact=c['terminal']['fact'];receipt=c['terminal']['receipt_ref']
        assert json.loads(intent['receipt'])==receipt and canon(receipt) in lookup and canon(ir) in lookup
        assert fact['plan_ref']==ref(plan) and fact['intent_ref']==ir and fact['action_id']==action['action_id'] and fact['action_digest']==r['actions'][0]['digest']
        assert lookup[canon(receipt)]['payload']['action_fact_refs']==[c['terminal']['fact_resource']]
        factpath=old_path(Path(reg['package_root'])/c['terminal']['fact_resource']['path'])
        assert manifest_map[factpath.relative_to(ROOT).as_posix()]['sha256']==c['terminal']['fact_resource']['sha256']
        assert old_doc(factpath)==fact
        row.update(intent_ref=ir,receipt_ref=receipt,attempt_fact=fact['result']['attempt_fact'],fact_resource=c['terminal']['fact_resource'])
        assert len(cr['permits'])==1 and cr['permits'][0]['state']=='CONSUMED'
        assert [e['event'] for e in events].count('DISPATCH_STARTED')==1
        if g=='F4':
            assert fact['result']['outcome']=='APPLIED' and fact['result']['attempt_fact']=='ATTEMPTED'
            assert 'ACTION_RESULT_COMMITTED' in [e['event'] for e in cut_events]
        else:
            assert cr['intents'][0]['state']=='PENDING' and cr['intents'][0]['receipt'] is None and cr['actions'][0]['fact'] is None
            assert 'ACTION_RESULT_COMMITTED' not in [e['event'] for e in cut_events]
            unknown=old_doc(case/'pre-reconcile-UNKNOWN.json');assert unknown['projection']['receipt_ref'] is None
            assert unknown['projection']['actions'][0]['effective_outcome']=='UNKNOWN'
            unknown_ref=c['terminal']['UNKNOWN_ref'];assert canon(unknown_ref) in lookup
            assert len(r['calls'])==len(r['attempts'])==len(r['resolutions'])==result['max_attempts']==result['reconcile_calls']==1
            fresh=old_doc(case/'fresh-terminal-readback.json');resolution=fresh['resolution'];p=resolution['payload'];readback=fresh['readback']
            assert ref(resolution)==c['terminal']['resolution_ref']==result['resolution_ref'] and lookup[canon(ref(resolution))]==resolution
            assert p['plan_ref']==ref(plan) and p['intent_ref']==ir and p['action_id']==action['action_id'] and p['action_digest']==r['actions'][0]['digest']
            assert p['original_receipt_ref'] is None and not p['replay_allowed']
            assert p['observation']==('ABSENT' if g=='F2' else 'MATCH') and p['resolution']==('RESOLVED_NOT_APPLIED' if g=='F2' else 'RESOLVED_APPLIED')
            assert p['read_sequence']==readback['read_sequence']==result['new_read_sequence']>result['old_max_read_sequence']
            assert readback['read_status']=='OK' and readback['scope_complete'] is True
            assert readback['target_session_id']==reg['session'] and readback['scope_id']==reg['scope'] and readback['source_ref']==json.loads(reg['source'])
            assert readback['target_key']==json.loads(r['books'][0]['target_key']) and readback['observation_id']==p['observation_id']
            observed=next(json.loads(x['body']) for x in t['observations'] if x['observation_id']==p['observation_id'])
            assert observed==readback and len(t['observations'])==len(ct['observations'])+1
            assert result['attempt_fact_before']==result['attempt_fact_after']==fact['result']['attempt_fact']=='MAY_HAVE_BEEN_ATTEMPTED'
            assert r['books'][0]['generation']==2 and r['books'][0]['phase']=='RELEASED'
            row.update(resolution_ref=ref(resolution),UNKNOWN_ref=unknown_ref,observation_ref={k:p[k] for k in ('observation_id','read_sequence','observed_snapshot_ref','readback')},
              original_receipt_ref=None,replay_allowed=False,observation=p['observation'],resolution=p['resolution'],
              old_max_read_sequence=result['old_max_read_sequence'],new_read_sequence=result['new_read_sequence'])
    coverage.append(row)
assert len(stage_index)==32
write(OUT/'stage-file-index.json',{'actual_independent_stage_files':32,'files':stage_index,
 'snapshot_limit':'Sequential raw copies of two different databases; not an atomic cross-database snapshot.',
 'new_SQL_audits':0,'author_missing_stage_files_reconstructed':False})
write(OUT/'coverage-map.json',{'status':'ACCEPTED_FOUR_CRASH_CUTS_ONLY','target':TARGET,'base':BASE,'workflow':WF,
 'judgment_basis':'File-only clause checks of the already completed frozen first runs, exact refs/rows/stage records; no reliance on the case-audit status alone.',
 'cases':coverage,'functional_calls_this_round':0,'new_SQL_connections':0,
 'author_F2_F3_missing_intermediate_binaries':'LIMIT_REMAINS; new independent originals do not retrospectively repair author originals.',
 'old_R11_verdict':'REWORK_UNCHANGED','old_archive_failures':2,'old_static_corrections':1,
 'new_closure_rounds':1,'new_corrections_or_retries':0,'whole_A03':'REWORK','I01_released':False,
 'B_mapping_jointly_confirmed':False,'field_reset':RESET})

def old_link(label,path):return '['+label+']('+str(Path('../evidence/A03/review/P2-R11-crash-cuts')/path).replace('\\','/')+')'
def new_link(label,path):return '['+label+']('+str(Path('../evidence/A03/review/P2-R11-R1-archive-closure')/path).replace('\\','/')+')'
def fmt(r):return 'none' if r is None else '`'+r['artifact_id']+'` / `'+r['content_hash']+'` (revision '+str(r['revision'])+', '+r['kind']+')'
lines=['# A03 P2-R11-R1 archive closure review','',
 '2026-10-18 (Asia/Shanghai). Verdict: **ACCEPTED_FOUR_CRASH_CUTS_ONLY**.',
 'This is the one separately authorized file-only closure of the completed R11 independent run. Functional calls: **0**. New SQLite connections/audits: **0**. No old scripts, tests, PRE/POST, run_plan or reconcile were executed.', '',
 'Target `'+TARGET+'`; base `'+BASE+'`; closure workflow `'+WF+'`.',
 'Closure task raw SHA256 `'+EXPECTED[TASK]+'`.',
 'The original R11 REWORK report, both archive failures and its one correction remain unchanged. This new verdict closes only the four original V02/R03 singleton crash cuts. Whole A03, product integration and I01 remain unreleased; B mapping is not jointly confirmed.', '',
 '## Basis and separate historical outcomes','',
 '[Original REWORK report](A03-P2-R11-crash-cuts-review-report.md)',
 'has SHA256 `'+EXPECTED[OLD_REPORT.relative_to(ROOT).as_posix()]+'`. The original manifest is `'+EXPECTED[manifest_path]+'`; original release record is `'+EXPECTED[OLD_REL+'process-release.json']+'`.',
 'All1209 original package/report files are bound to workflow raw Git blobs and their original SHA256 manifest. All677 original raw inputs and77 source seeds remain byte-identical. New files reference the old package; no historical corpus or database seeds are copied.',
 'The decision uses the original handoff/execution criteria, four actual case results, complete recorded SQL/event/formal-reference boundaries, actual process/import records and stage binary digests. It does not adopt an internal audit status as acceptance by itself. '+new_link('Detailed coverage','coverage-map.json')+' and '+new_link('Completed audit references','completed-audit-reference-index.json')+'.','',
 '## Four bounded conclusions','',
 '| Case | Original cut | Existing crash/query PID | Effect | Result | Actual plan state |',
 '|---|---|---|---|---|---|']
for c in coverage:
    g=c['group'];description={'F1':'Query only; no intent/permit/formal result','F2':'One reconcile; ABSENT / NOT_APPLIED','F3':'One reconcile; MATCH / APPLIED','F4':'Query only; durable APPLIED receipt retained'}[g]
    lines.append('| '+g+' | '+c['fault_point']+' | '+str(c['existing_processes']['crash']['pid'])+'/90 then '+str(c['existing_processes']['query']['pid'])+'/0 | '+str(c['effects_before_after'][0])+' to '+str(c['effects_before_after'][1])+' | '+description+' | '+c['actual_plan_state']+' |')
lines+=['',
 'Each original case ran once from a fresh isolated path. The same legitimate owner/PRE context reached the existing FaultController cut through normal run_plan and real os._exit90. Parent wait preceded the different reopened PID; original marker, persisted facts, instance and owner/generation agree. No new process competed for business ownership in this closure.',
 'F1 distinguishes accepted/reserved plan/action from no committed intent/permit/effect. It did not fabricate UNKNOWN or a NOT_ATTEMPTED receipt. F4 preserves the durable plan/action/intent/fact/receipt binding and ATTEMPTED fact; no project/reconcile/resolution or replay was performed. Query bytes are unchanged in both cases, and their original dead generation1 ACTIVE rows were not cleared.',
 'F2/F3 preserve pending intent, consumed permit and DISPATCH_STARTED before any formal result. Each saved a formal UNKNOWN before its single original max_attempts=1 reconcile. Fresh read sequences are2 to3 and3 to4, with exact source/target/scope/store/session/plan/action/digest/intent/observation/snapshot/readback bindings. The original UNKNOWN and MAY_HAVE_BEEN_ATTEMPTED fact remain. Effects stay0 and1; an absent effect is not treated as proof of no call. Generation2 was normally released. No old action was replayed.',
 'All four recorded POST/Batch/native_report_reads counts are0. Reports were not generated to conceal their absence. Parent90-second, business45-second, observation2-second, barrier5-second, lease10-second and original recovery bounds were unchanged in the frozen runs. None were invoked again here.', '',
 '## Exact formal references','']
for c in coverage:
    lines+=['### '+c['group'],'','Plan: '+fmt(c['plan_ref'])+'.','PRE: '+fmt(c['PRE_ref'])+'.',
      'Intent: '+fmt(c['intent_ref'])+'.','Receipt: '+fmt(c['receipt_ref'])+'.','Resolution: '+fmt(c['resolution_ref'])+'.',
      'Actual attempt fact: `'+str(c['attempt_fact'])+'`.']
    if c['observation_ref']:
        o=c['observation_ref'];lines+=['Observation `'+o['observation_id']+'`, sequence '+str(o['read_sequence'])+'; snapshot '+fmt(o['observed_snapshot_ref'])+'.',
          'Readback Resource `'+o['readback']['path']+'`, SHA256 `'+o['readback']['sha256']+'`. Original receipt is null; replay_allowed=false.']
    lines.append('')
lines+=['## Actual stage originals and author limit','',
 new_link('Stage file index','stage-file-index.json')+' lists all32 actual independent stage SQLite files with paths, SHA256, capture-file digests, capture PID, writer/keeper flag and times. Every case has pre-fault, cut-after-wait and after-query/recovery; F2/F3 additionally have pending-before-projection and UNKNOWN-before-reconcile. Original capture records and completed immutable-copy SQL rows agree. This round reads frozen records/hashes only and does not repeat the64 completed SQL audits.',
 'Pre-fault capture had its own keeper active; later captures had no active writer/keeper. The two databases were read sequentially, not as an atomic cross-database snapshot. No missing database was constructed.',
 '**Author F2/F3 intermediate binary originals remain absent.** Their full SQL rows, contemporaneous hashes, event chains and immutable artifacts/Resources support only their declared layer of evidence. Their missing intermediate raw hashes cannot be rederived from nonexistent files. Author pre-run/final originals and F1/F4 unchanged cut/final bytes exist. The32 new independent stage originals satisfy the independent review stage-preservation requirement; they cannot retrospectively repair the author package.',
 'This limitation is preserved separately from the four independent runtime conclusions and is not waived or relabeled complete. '+old_link('Author declaration','input/target/docs/evidence/A03/execution/P2-R11-crash-cuts/stage-binary-preservation.json')+'.','',
 '## Archive failure and this authorized closure','',
 'Original process-audit-01 exited1 because the returned observation wrapper was compared directly with its persisted body. Its single permitted static correction compared all body fields and validated the four extra Resource/path fields against actual bytes. Process-audit-02 exited0. Both versions, original stderr and the correction record remain unchanged.',
 'Original report-01 PID54900 exited1 before the normal report/coverage-map output, with a source-decoding SyntaxError recorded at line35. Static inspection now establishes that the retained script and preregistered snapshot are identical and strictly decode as UTF-8. Therefore the statement that the retained file is invalid UTF-8 is not established. The historical interpreter diagnostic is retained verbatim; its exact interpreter-level cause is not reproduced or inferred. This difference in diagnostic description does not change or contradict any recorded crash-cut, transaction, observation, process or database criterion. '+new_link('Encoding facts and output gap','encoding-and-output-gap.json')+'.',
 'The original round correctly stopped at its correction limit and remains REWORK. This separately registered one-round closure supplies a new explicitly UTF-8 decoded/compiled generator, this report and coverage map from already frozen evidence. It does not fix or retry either old script or change any old byte. No new metadata correction or retry is made.',
 'The new '+new_link('Source preflight','source-preflight.json')+' records strict UTF-8 decoding and compile-only validation before the single file-only child started. Git commands and that child are preregistered with actual source/input SHA, argv/cwd, timeout, raw streams and waits; every child limit is at most45 seconds.', '',
 '## Preservation, scope and delivery','',
 new_link('Original package byte preservation','original-preservation.json')+' covers all1209 original files before and after this closure, including the old report, manifest, failed script/snapshot and outputs. '+new_link('Release proof','process-release.json')+' records only actual current-round Popen children; historical33 waits remain historical evidence, not a scan of possibly reused PIDs. '+new_link('New manifest','sha256-manifest.json')+' covers this report and all new files, excluding only itself.',
 'The old AFTER_INTENT_COMMIT, lost-receipt N1, R9/R10, old R3 N7, other fault cuts, full suites, multi-action/mixed-tail cases and all other original gaps were not rerun or waived. No product/source/schema/profile/adoption/pin/oracle/producer/verifier/dependency/author/old-evidence/state files were modified. No integration, INTEGRATED registration, commit or push was performed. Coordinator functional acceptance/registration is still separate.',
 'Functional calls0; new SQL connections0; closure rounds1; corrections/retries0. No agents/delegation, network, platform/browser/profile/credentials, OCR/paid models, installation, B contact, A05 question22 or book submission. User model/thinking preserved.',
 'Field reset: `'+RESET+'`. No execution, variant, delegation or retest recommendation.','']
write(REPORT,('\n'.join(lines)).encode('utf8'))
write(OUT/'closure-result.json',{'status':'ACCEPTED_FOUR_CRASH_CUTS_ONLY','target':TARGET,'base':BASE,'workflow':WF,
 'report_sha256':sha(REPORT.read_bytes()),'coverage_map_sha256':sha((OUT/'coverage-map.json').read_bytes()),
 'stage_file_index_sha256':sha((OUT/'stage-file-index.json').read_bytes()),'original_package_files_verified':1209,
 'functional_calls':0,'SQL_connections':0,'closure_rounds':1,'corrections_or_retries':0,
 'old_REWORK_and_two_failures_unchanged':True,'author_limit_remains':True,'whole_A03':'REWORK','I01_released':False,
 'field_reset':RESET})
print(json.dumps({'status':'ACCEPTED_FOUR_CRASH_CUTS_ONLY','report_sha256':sha(REPORT.read_bytes()),'functional_calls':0,
 'new_SQL_connections':0,'stage_references':len(stage_index),'original_package_files':len(old_rows),'owned_git_children':git_counter}))
