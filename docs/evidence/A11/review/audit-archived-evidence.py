"""Read/archive the completed unique run. No imports or calls into product/tests."""
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path

REPORT = Path('D:/1800-worktrees/a11-r')
RUN = Path('D:/1800-worktrees/a11-rr')
E = REPORT/'docs/evidence/A11/review'
SOURCE = RUN/'docs/evidence/A11/execution/independent-attempt-1'
TARGET = E/'independent-attempt-1'

def read(path):
    return json.loads(path.read_bytes())

def save(path,value):
    path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))

assert not TARGET.exists()
archive=[]
for source in sorted(SOURCE.rglob('*')):
    if not source.is_file(): continue
    relative=source.relative_to(SOURCE)
    target=TARGET/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    raw=source.read_bytes()
    target.write_bytes(raw)
    assert target.read_bytes()==raw
    archive.append({'path':target.relative_to(REPORT).as_posix(),'source_path':source.relative_to(RUN).as_posix(),
                    'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
save(E/'run-archive-copy-manifest.json',{'members':archive,'raw_bytes_identical':True})
export=read(E/'run-export-manifest.json')
for item in export['members']:
    raw=(RUN/item['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==item['sha256'] and len(raw)==item['bytes']
result=read(TARGET/'result.json')
assert result['candidate_commit']==export['product'] and result['tests_run']==17
assert set(result['case_results'].values())=={'PASS'}

def process_audit(root):
    events=[json.loads(line) for line in (root/'process-events.jsonl').read_text(encoding='utf-8').splitlines()]
    created=[x for x in events if x['event']=='created']
    exited=[x for x in events if x['event']=='exited']
    assert len(created)==len(exited)==12
    assert Counter(x['pid'] for x in created)==Counter(x['pid'] for x in exited)
    assert all(x['exit_code'] in (2,73) for x in exited)
    subprocess_records=[]
    for p in sorted((root/'runtime').rglob('*.json')):
        if p.name not in ('first.json','restart.json','one.json','two.json'): continue
        data=read(p)
        assert any(x['pid']==data['pid'] and x['exit_code']==data['exit_code'] for x in exited)
        subprocess_records.append({'path':p.relative_to(root).as_posix(),'pid':data['pid'],
                                   'exit_code':data['exit_code'],'stderr_empty':not data['stderr']})
    assert len(subprocess_records)==12
    return {'created':created,'exited':exited,'child_archives':subprocess_records,
            'owned_popen_communicate_completed':True,
            'source':'tests/test_live_pilot_journal.py:16-32 uses the same owned Popen object for spawn, communicate and returncode',
            'os_creation_time_recorded':False,'posthoc_empty_pid_lookup_used_as_identity':False,
            'cli_children_count':5,'cli_children_pid_recorded':False,
            'cli_completion_evidence':'five subprocess.run calls returned; frozen suite checked return codes and retained stdout; no independent PID log'}

processes=process_audit(TARGET)
author_processes=process_audit(REPORT/'docs/evidence/A11/execution/attempt-2')
save(E/'process-release-audit.json',{'independent':processes,'author':author_processes,
    'suite_process_created':read(E/'suite-process-created.json'),
    'suite_process_exited':read(E/'suite-process-exited.json'),
    'network_or_browser_created':False,'foreign_process_killed':False,'lock_file_deleted':False,
    'release_scope':'12 controlled workers + unique suite exited via their own process objects; CLI completion only, not exact PID identity; fake closed flags are retained synthetic state'})
runtime=TARGET/'runtime'
def journal(root):
    return [read(p) for p in sorted(root.glob('event-*.json'))]

normal_root=runtime/'test_T7_normal_two_question_strict_readback'
normal_events=journal(normal_root/'journal')
backend=read(normal_root/'backend/fake-backend.json')
expected_roles=['Q','W','W','W','W','A']
expected_text=['OFFLINE: 1 + 1 = ?','A. 1','B. 2','C. 3','D. 4','B']
normal_checks=[]
intents={x['data']['question_id']:x['data'] for x in normal_events if x['kind']=='INTENT'}
for qid,intent in intents.items():
    assert [f['platform_role'] for f in intent['plan']['frames']]==expected_roles
    assert [p['text'] for p in intent['plan']['approved_parts']]==expected_text
    reads=[x['data'] for x in normal_events if x['kind']=='READBACK' and x['data']['question_id']==qid]
    assert [x['phase'] for x in reads]==['get','refresh','reopen']
    for entry in reads:
        after=entry['observation']; baseline=intent['baseline']; pid=entry['comparison']['platform_question_id']
        frames=[f for f in after['view']['target']['frames'] if f['platform_question_id']==pid]
        assert [f['platform_role'] for f in frames]==expected_roles
        assert [p['text'] for p in after['view']['question_content'][pid]['parts']]==expected_text
        assert baseline['directory_details']==after['directory_details']
        for field,key in (('questions','platform_question_id'),('frames','platform_frame_id')):
            actual={x[key]:x for x in after['view']['target'][field]}
            assert all(actual[x[key]]==x for x in baseline['view']['target'][field])
        assert all(after['view']['question_content'][k]==v for k,v in baseline['view']['question_content'].items())
    normal_checks.append({'question_id':qid,'plan_roles':expected_roles,'approved_and_observed_text':expected_text,
       'plan_order':intent['plan']['action']['expected_after']['platform_order'],
       'phases':[x['phase'] for x in reads],'source_refs':[x['observation']['source_ref'] for x in reads],
       'session_ids':[x['observation']['session_id'] for x in reads],
       'reopen_predecessor':reads[-1]['observation']['predecessor_session_id'],
       'old_state_preserved_in_archived_reads':True})
assert [x['plan_order'] for x in normal_checks]==[10,11]
assert [x['order'] for x in backend['new']]==[10,11] and backend['sends']==2
outcomes=[]
for root in sorted(runtime.rglob('journal')):
    events=journal(root)
    if not events: continue
    outcomes.append({'path':root.relative_to(TARGET).as_posix(),
        'results':[x['data'] for x in events if x['kind']=='RESULT'],
        'readbacks':[{'question_id':x['data']['question_id'],'phase':x['data']['phase']} for x in events if x['kind']=='READBACK'],
        'reconciliations':[{'question_id':x['data']['question_id'],'effect_match':x['data']['effect_match'],
                           'resend_allowed':x['data']['resend_allowed']} for x in events if x['kind']=='RECONCILIATION']})
backends=[]
for path in sorted(runtime.rglob('fake-backend.json')):
    data=read(path)
    backends.append({'path':path.relative_to(TARGET).as_posix(),'sends':data['sends'],'fake_session_closed':data['closed']})
assert len(backends)==26 and sum(x['sends'] for x in backends)==22
save(E/'archived-outcome-audit.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'kind':'POST_RUN_STATIC_EVIDENCE_AUDIT_NOT_NEW_CASES','suite_invocations':1,
    'run_raw_file_count':len(archive),'run_raw_bytes':sum(x['bytes'] for x in archive),
    'runtime_source_members_unchanged':len(export['members']),'case_results':result['case_results'],
    'normal_semantic_rule_source':'raw author baseline 项目交接说明.md:71-74,87-90,97-100',
    'normal':normal_checks,'retained_backend_counts':backends,'journal_outcomes':outcomes,
    'fake_sends':22,'real_sends':0,'submission_status':'NOT_SUBMITTED'})
print(json.dumps({'archived_files':len(archive),'archived_bytes':sum(x['bytes'] for x in archive),
    'runtime_members_unchanged':len(export['members']),'normal_orders':[10,11],'worker_exits':12,
    'fake_backends':len(backends),'fake_sends':22,'new_suite_runs':0}))
