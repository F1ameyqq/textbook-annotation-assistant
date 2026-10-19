"""Static audit/copy of the completed six-case run; no product/test invocation."""
import datetime,hashlib,json,os,subprocess
from pathlib import Path
REPORT=Path('D:/1800-worktrees/a11-delta-review')
RUN=Path('D:/1800-worktrees/a11-delta-run')
E=REPORT/'docs/evidence/A11/review-delta-independent'
SOURCE=RUN/'docs/evidence/A11/review-delta-execution/independent-attempt-1'
TARGET=E/'independent-attempt-1'
BASE='c580ca63ada9e452fd5ee71e5272cf0d047d4574'
ARCHIVE='docs/evidence/A11/execution/attempt-2/runtime/test_T6_response_frame_and_read_failure/http_only'
ENV=dict(os.environ,GIT_NO_LAZY_FETCH='1')
def read(p): return json.loads(p.read_bytes())
def digest(v): return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
def git(*args,input=None):
    return subprocess.check_output(['git','-c','core.longpaths=true',*args],cwd=REPORT,env=ENV,input=input)
def save(name,value):
    (E/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
assert not TARGET.exists()
archive=[]
for p in sorted(SOURCE.rglob('*')):
    if not p.is_file(): continue
    relative=p.relative_to(SOURCE); dest=TARGET/relative; raw=p.read_bytes()
    dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(raw)
    assert dest.read_bytes()==raw
    archive.append({'source_path':p.relative_to(RUN).as_posix(),'path':dest.relative_to(REPORT).as_posix(),
                    'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
save('run-archive-copy-manifest.json',{'raw_bytes_identical':True,'members':archive})
exports=read(E/'run-export-manifest.json')
for m in exports['members']:
    raw=(RUN/m['path']).read_bytes()
    assert len(raw)==m['bytes'] and hashlib.sha256(raw).hexdigest()==m['sha256']
result=read(TARGET/'result.json')
assert result['tests_run']==6 and set(result['case_results'].values())=={'PASS'}
created=read(TARGET/'process-created.json'); released=read(TARGET/'process-release.json')
super_created=read(E/'supervisor-created.json'); super_released=read(E/'supervisor-release.json')
assert created['pid']==released['pid']==result['pid']
assert created['supervisor_pid']==super_created['pid']==super_released['pid']
assert created['product_commit']==exports['product_commit']
assert not released['timed_out']
for r in (released,super_released):
    assert r['returncode']==0 and all(r[k] for k in ('original_popen_wait_completed','stdout_pipe_closed','stderr_pipe_closed'))
save('release-audit.json',{'worker':{'created':created,'released':released},
    'supervisor':{'created':super_created,'released':super_released},
    'evidence_basis':'same original Popen objects waited by communicate, no posthoc PID absence used',
    'scope':'worker and supervisor processes; synthetic release failures are retained evidence, not live browser sessions',
    'new_process_probes':0,'foreign_processes_terminated':0,'lock_files_deleted':0})
source_members=[]
for line in git('ls-tree','-r','-z',BASE,ARCHIVE).split(b'\0'):
    if not line: continue
    meta,path=line.split(b'\t',1); mode,kind,oid=meta.decode().split(); path=path.decode('utf-8')
    assert kind=='blob'
    raw=git('cat-file','blob',oid)
    source_members.append({'source_commit':BASE,'source_path':path,'mode':mode,'type':kind,'blob':oid,
                           'copy_path':path[len(ARCHIVE)+1:],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
                           '_raw':raw})
assert len(source_members)==15
reconciles=[]
for name,mode in [('test_D04_reconcile_close_exception','exception'),('test_D05_reconcile_close_false','false'),
                  ('test_D06_reconcile_close_normal','normal')]:
    root=TARGET/'cases'/name; copy=read(root/'copy-manifest.json'); outcome=read(root/'result.json')
    assert len(copy['members'])==15
    for m in source_members:
        assert (root/'archive-copy'/m['copy_path']).read_bytes()==m['_raw']
        recorded=next(x for x in copy['members'] if x['source_path']==m['source_path'])
        assert all(recorded[k]==m[k] for k in ('source_commit','blob','copy_path','sha256','bytes'))
    initial=outcome['initial_report']; returned=outcome['reconcile_return']; report=outcome['standard_report']
    assert report['questions']==initial['questions']
    assert report['questions']['a11-new-alpha']['state']=='UNKNOWN'
    assert report['questions']['a11-new-beta']['state']=='NOT_RUN'
    assert returned['effect_match']=='MATCH'
    assert returned['status']==report['status']==('REVIEW' if mode=='normal' else 'HOLD')
    assert returned['apply_release']==report['apply_release']==initial['apply_release']
    assert returned['apply_release']['released'] is True
    assert returned['reconcile_release']==report['reconcile_release']
    assert returned['release']['released']==report['release']['released']==(mode=='normal')
    assert returned['resend_allowed'] is report['resend_allowed'] is False
    assert returned['write_disposition']=='HOLD'
    backend=read(root/'archive-copy/backend/fake-backend.json')
    assert backend['sends']==1
    assert outcome['book_gate_released'] is True
    old_paths={m['copy_path'] for m in source_members}
    new_paths=sorted(p.relative_to(root/'archive-copy').as_posix() for p in (root/'archive-copy').rglob('*')
                     if p.is_file() and p.relative_to(root/'archive-copy').as_posix() not in old_paths)
    assert len(new_paths)==6
    new_events=[read(root/'archive-copy'/p) for p in new_paths if '/event-' in p]
    assert [x['kind'] for x in new_events]==['RECONCILE_CLAIM','RECONCILE_RELEASE','RECONCILIATION']
    assert all('intent-' not in p and '/claim-' not in p for p in new_paths)
    if mode=='false':
        assert returned['reconcile_release']['reason']=='synthetic returned false'
        assert returned['reconcile_release']['session_id']=='review-delta-readonly-session'
    if mode=='exception': assert returned['reconcile_release']['reason']=='OSError'
    reconciles.append({'case':name,'mode':mode,'preserved_raw_source_members':15,'new_files':new_paths,
        'new_event_kinds':[x['kind'] for x in new_events],'original_send_count':1,'archived_send_count_after':backend['sends'],
        'original_questions':initial['questions'],'current_status':report['status'],
        'original_apply_release':returned['apply_release'],'current_reconcile_release':returned['reconcile_release'],
        'current_report_release':report['release'],'write_disposition':returned['write_disposition'],'resend_allowed':False,
        'book_gate_released':outcome['book_gate_released']})
save('source-copy-audit.json',{'source_commit':BASE,'source_path':ARCHIVE,
    'source_members':[{k:v for k,v in x.items() if k!='_raw'} for x in source_members],
    'independent_copies':reconciles,'new_product_invocations_during_audit':0})
assets=RUN/'tests/fixtures/live_pilot'
inputs=[]
for name in ('valid','multiple-answer','explicit-multiple'):
    req=read(assets/'review_delta'/(name+'.json'))
    bundle=req['bundle']; graph=next(x for x in bundle['artifacts'] if x['kind']=='QuestionGraph')['payload']
    source=next(x for x in bundle['artifacts'] if x['kind']=='SourceBundle')['payload']
    evidence=next(x for x in bundle['artifacts'] if x['kind']=='EvidenceBundle')['payload']
    regions={x['region_id']:x for x in evidence['regions']}
    facts=[]
    for question,approved in zip(graph['questions'],req['approval']['questions']):
        selected=next(x['selected_fragment_ids'] for x in graph['answer_relations'] if x['question_id']==question['question_id'])
        wanted=question['fragment_ids']+selected
        fragments=sorted((x for x in graph['fragments'] if x['fragment_id'] in wanted),key=lambda x:x['reading_order'])
        frames=[]; parts=[]
        for f in fragments:
            for rid in f['region_ids']:
                r=regions[rid]
                frames.append({'fragment_id':f['fragment_id'],'region_id':rid,'box':r['box'],
                               'platform_role':{'stem':'Q','option':'W','answer':'A'}[f['role']],
                               'platform_type':f['content_type']})
                parts.append({'fragment_id':f['fragment_id'],'role':f['role'],'text':r['text']})
        assert parts==approved['approved_parts'] and [x['platform_role'] for x in frames]==['Q','W','W','W','W','A']
        qualification=approved['choice_qualification']; resource=qualification['resource']
        assert any(h['resource']==resource and h['quality']=='REVIEWED' for h in source['history'])
        raw=(assets/resource['path']).read_bytes(); classification=json.loads(raw)
        assert hashlib.sha256(raw).hexdigest()==resource['sha256']
        assert classification['source_frames_hash']==digest(frames) and classification['source_parts_hash']==digest(parts)
        assert classification['book_id']=='46007447' and classification['question_id']==question['question_id']
        assert classification['classification']==qualification['classification']
        facts.append({'question_id':question['question_id'],'classification':classification['classification'],
            'source_resource':resource,'source_frames_hash_verified':True,'source_parts_hash_verified':True,
            'roles':['Q','W','W','W','W','A'],'answer_text':parts[-1]['text'],'stem_text':parts[0]['text']})
    inputs.append({'fixture':name,'question_bindings':facts})
save('source-approval-semantic-audit.json',{'kind':'static data audit of existing frozen inputs; no additional cases',
    'inputs':inputs,'rule_source':'项目交接说明.md:71-74,88-90,97-100',
    'D02_actual_gate':read(TARGET/'cases/test_D02_resealed_BC/result.json')['actual_code'],
    'D03_actual_gate':read(TARGET/'cases/test_D03_explicit_multiple_with_B/result.json')['actual_code'],
    'D03_is_classification_gate_not_stem_regex':True,
    'scope':'synthetic source-and-approval closure, not human source classification or platform facts'})
save('audit-summary.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'decision':'PASS_R01_R02_LIMITED_OFFLINE_DELTA','runtime_product':exports['product_commit'],
    'actual_delta_runs':1,'actual_tests_run':6,'status':'6/6 PASS','old_suite_runs':0,
    'postrun_product_invocations':0,'runtime_export_members_unchanged':len(exports['members']),
    'archived_output_files':len(archive),'archived_output_bytes':sum(x['bytes'] for x in archive),
    'source_archive_members':15,'independent_source_copies':3,'old_member_preservation_checks':45,
    'each_copy_new_events':['RECONCILE_CLAIM','RECONCILE_RELEASE','RECONCILIATION'],
    'zero_count_evidence':'driver summary counters are constants; conclusion additionally uses static call graph, transport send guard/counter assertions, unchanged backend bytes and absence of new intent/send-claim records',
    'worker_pid':created['pid'],'supervisor_pid':super_created['pid'],'worker_and_supervisor_waited':True,
    'platform_status':'BLOCKED','submission_status':'NOT_SUBMITTED','coordinator_acceptance':'PENDING'})
print(json.dumps({'archived_files':len(archive),'archived_bytes':sum(x['bytes'] for x in archive),
    'runtime_unchanged':len(exports['members']),'source_raw_checks':45,'delta_suite_runs':1,'postrun_calls':0,
    'worker_pid':created['pid'],'supervisor_pid':super_created['pid']}))
