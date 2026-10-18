"""Independent static closeout; SQL only on our quiescent retained copies."""
import ctypes
from ctypes import wintypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

ROOT = Path('D:/1800-i01-review-01a14e1c')
OUT = Path('D:/1800/docs/evidence/I01-A/review')
RUN = ROOT/'docs/evidence/I01-A/execution/run'
RAW = ROOT/'docs/evidence/I01-A/execution/preparation/raw-view'
BASE = 'a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8'
CANDIDATE = 'be68b8d7c645de556d601458d1d493258f063721'
DELIVERY = '3fdc5d37e221fc73410f197605f5d7b8878182d5'
SOURCE = Path('D:/1800-worktrees/i01-a')
AUTHOR = OUT/'author-fixed/docs/evidence/I01-A/execution'
os.environ['GIT_NO_LAZY_FETCH']='1'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def load(p): return json.loads(p.read_bytes())
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f: f.write((json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n').encode())
def git(*args,repo=SOURCE):return subprocess.check_output(['git','-c','core.longpaths=true','-C',str(repo),*args])
def ref(a):return {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}

def semantic(result):
    artifacts=result['bundle']['artifacts']
    for a in artifacts:
        assert a['content_hash']==sha(canonical({k:v for k,v in a.items() if k!='content_hash'})),a['artifact_id']
    receipts=[dict(ref=ref(a),results=a['payload']['results']) for a in artifacts if a['kind']=='ExecutionReceipt']
    posts=[a for a in artifacts if a['kind']=='CheckReport' and a['payload']['stage']=='POST_APPLY']
    batches=[a for a in artifacts if a['kind']=='BatchReport']
    pres=[a for a in artifacts if a['kind']=='CheckReport' and a['payload']['stage']=='PRE_APPLY']
    for pre in pres:
        assert pre['payload']['decision']=='PASS'
        assert len(pre['payload']['checks'])==5
    for a in posts:
        p=a['payload']
        assert p['frame_structure']=='PASS' and p['content_check_status']=='PENDING' and p['submission_status']=='NOT_SUBMITTED'
    for a in batches:
        p=a['payload']
        assert p['total_expected']==len(p['scope_manifest'])==len(p['questions'])==1
        assert p['content_check_status']=='PENDING' and p['submission_status']=='NOT_SUBMITTED' and p['state']=='CONTENT_PENDING'
    return dict(receipts=receipts,pre_checks=len(pres),posts=len(posts),batches=[dict(ref=ref(a),payload=a['payload']) for a in batches],pending=result['status']['pending_count'],paused=result['status']['paused'],instance=result['target']['instance'])

def inspect_copy(folder):
    expected=load(folder/'SQL.json'); capture=load(folder/'capture.json')
    assert capture['status']=='RAW_COPIES_RETAINED'
    assert capture['cross_database_atomic'] is False
    assert all(not t['alive'] or t['name']=='MainThread' for t in capture['writer_boundary']['threads_quiet'])
    for record in capture['records']:
        assert not record['sidecars_after_writer_join']
        assert record['sha256']==record['source_sha256_after_copy']==record['source_sha256_after_copy_audit']
    hashes={}
    for label in ('runtime','target'):
        p=folder/(label+'.sqlite3'); before=p.read_bytes()
        db=sqlite3.connect(p.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
        db.row_factory=sqlite3.Row
        try:
            assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            actual=dict(application_id=db.execute('PRAGMA application_id').fetchone()[0],user_version=db.execute('PRAGMA user_version').fetchone()[0],tables={name:[dict(r) for r in db.execute('SELECT * FROM "'+name.replace('"','""')+'" ORDER BY rowid')] for name in names})
        finally:db.close()
        assert actual==expected[label] and p.read_bytes()==before
        hashes[label]=dict(bytes=len(before),sha256=sha(before))
    rt=expected['runtime']['tables'];target=expected['target']['tables']
    assert all(b['owner'] is None and b['pid'] is None and b['lease']==0 and b['phase']=='RELEASED' for b in rt['books'])
    events=[json.loads(x['body']) for x in rt['events']]
    previous='0'*64
    for number,event in enumerate(events,1):
        assert event['sequence']==number and event['previous_hash']==previous
        assert event['event_hash']==sha(canonical({k:v for k,v in event.items() if k!='event_hash'}))
        previous=event['event_hash']
    assert len(events)==rt['books'][0]['head_sequence'] and previous==rt['books'][0]['head_hash']
    types=[x['event'] for x in events]
    if 'DISPATCH_STARTED' in types:
        assert types.index('WRITE_INTENT_COMMITTED')<types.index('DISPATCH_PERMIT_ISSUED')<types.index('DISPATCH_PERMIT_CONSUMED')<types.index('DISPATCH_STARTED')<types.index('ACTION_RESULT_COMMITTED')
    state=json.loads(next(row['value'] for row in target['meta'] if row['key']=='state'))
    effects=[json.loads(x['body']) for x in target['effects']]
    observations=[json.loads(x['body']) for x in target['observations']]
    info=dict(path=str(folder.relative_to(RUN)).replace('\\','/'),raw_databases=hashes,events=len(events),event_head=previous,event_types=types,plans=len(rt['plans']),intents=len(rt['intents']),permits=len(rt['permits']),dispatch_events=types.count('DISPATCH_STARTED'),effects=len(effects),mutated=sum(e['mutated'] for e in effects),questions=len(state['target']['questions']),frames=len(state['target']['frames']),target_epoch=state['epoch'],native_pre_runs=len(rt['native_pre_runs']),report_reads=sum(x['reads'] for x in rt['native_report_reads']),recovery_calls=len(rt['calls']),recovery_attempts=len(rt['attempts']),resolutions=len(rt['resolutions']),persisted_target_reads=len(observations),read_statuses=[o['read_status'] for o in observations],owner_pid_empty=True,lease=0,hold=rt['books'][0]['hold'])
    return info,expected

def process_state(pid,completion_ns):
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
    handle=k.OpenProcess(0x1000,False,pid)
    if not handle:
        error=ctypes.get_last_error()
        assert error==87,(pid,error)
        return dict(pid=pid,original_alive=False,current_pid_occupied=False)
    try:
        created,ended,kernel,user=(wintypes.FILETIME() for _ in range(4))
        k.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
        assert k.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kernel),ctypes.byref(user))
        created_ns=(((created.dwHighDateTime<<32)|created.dwLowDateTime)-116444736000000000)*100
        exitcode=wintypes.DWORD();k.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        assert k.GetExitCodeProcess(handle,ctypes.byref(exitcode))
        reused=created_ns>completion_ns
        alive=exitcode.value==259 and not reused
        assert not alive, (pid,created_ns,completion_ns)
        return dict(pid=pid,original_alive=alive,current_pid_occupied=True,pid_reused=reused,current_creation_ns=created_ns,original_completed_ns=completion_ns,action='read-only; no termination')
    finally:
        k.CloseHandle.argtypes=[wintypes.HANDLE];k.CloseHandle(handle)

def main():
    assert load(OUT/'top-level/completed.json')['exit_code']==0
    matrix=load(RUN/'matrix.json')
    assert [m['phase'] for m in matrix]==['A01-C01','A01-consume','N','E','U-execute','U-recover']
    assert all(m['process']['exit_code']==0 and not m['process']['timeout'] and m['process']['waited'] for m in matrix)
    audit_author=load(AUTHOR/'audit.json')
    imports=[]
    for p in [*RUN.glob('public-imports/*.json'),*RUN.glob('cases/*/worker-ended.json')]:
        record=load(p)
        for name,row in record['imports'].items():
            module_path=Path(row['path']);relative=module_path.relative_to(RAW).as_posix()
            current=module_path.read_bytes();expected=git('show',BASE+':'+relative)
            assert current==expected and sha(current)==row['sha256'],(p,name)
            imports.append(dict(record=str(p.relative_to(ROOT)).replace('\\','/'),module=name,path=str(module_path),sha256=row['sha256']))
    author_imports=0
    for row in audit_author['imports']:
        relative=row['path'].replace('\\','/').split('/preparation/raw-view/',1)[1]
        assert sha((RAW/relative).read_bytes())==row['sha256']
        author_imports+=1
    assert author_imports==140
    for member in load(ROOT/'docs/evidence/I01-A/execution/frozen/invocation.json')['files']:
        p=ROOT/'docs/evidence/I01-A/execution/frozen/candidate-view'/member['path']
        assert p.read_bytes()==git('show',CANDIDATE+':'+member['path'])
        assert sha(p.read_bytes())==member['sha256']
    for path in ['examples/i01/run.py','examples/i01/driver.py','examples/i01/support.py','examples/i01/public.py']:
        assert git('show','3a7b5430659918d015a23fa2da722bfe3cec44af:'+path)==git('show',CANDIDATE+':'+path)
    public={mode:load(RUN/'processes'/phase/'stdout.txt') for mode,phase in [('C01','A01-C01'),('A01','A01-consume')]}
    assert public['C01']['resources_verified'] is True and public['C01']['valid'] is True
    assert public['A01']['coverage_eligible'] is False and public['A01']['full_image_decode']=='OK' and public['A01']['book_id']=='46007447'
    assert public==audit_author['public_consumption']
    results={p:load(RUN/'cases'/p/'result.json') for p in ('N','E','U-execute','U-recover')}
    semantics={p:semantic(d) for p,d in results.items()}
    author_semantics={p:semantic(load(AUTHOR/'run/cases'/p/'result.json')) for p in results}
    for phase in ('N','E','U-execute'):
        assert results[phase]['target']['instance'] != author_semantics[phase]['instance']
        assert results[phase]['status']['event_head']['hash'] != load(AUTHOR/'run/cases'/phase/'result.json')['status']['event_head']['hash']
    snapshot_infos=[];snapshots={}
    for folder in sorted(RUN.glob('cases/*/captures/*')):
        info,sql=inspect_copy(folder);snapshot_infos.append(info);snapshots[info['path']]=sql
    assert len(snapshot_infos)==5
    for info in snapshot_infos:
        old=info['path'].endswith('old-candidate-refused-released')
        expected=0 if old else 1
        assert info['dispatch_events']==info['effects']==info['mutated']==info['questions']==expected
        assert info['frames']==2*expected and info['intents']==info['permits']==expected
    for phase in ('N','E','U-recover'):
        assert semantics[phase]['pending']==0 and semantics[phase]['posts']==len(semantics[phase]['batches'])==1
    e=results['E']['correction'];assert e['old_dispatches']==0 and e['operator_changes']==1
    assert e['old_plan']['payload']['precheck']!=e['new_plan']['payload']['precheck']
    assert e['old_plan']['payload']['snapshot']!=e['new_plan']['payload']['snapshot']
    assert e['old_plan']['payload']['actions'][0]['action_id']!=e['new_plan']['payload']['actions'][0]['action_id']
    rejection=load(RUN/'cases/E/old-candidate-refusal.json')
    assert rejection.get('code')=='TARGET_CHANGED' or any(i['code']=='TARGET_CHANGED' for i in rejection.get('issues',[]))
    original=results['U-execute'];recovered=results['U-recover']
    assert original['status']['pending_count']==1 and original['status']['paused']
    assert semantics['U-execute']['posts']==len(semantics['U-execute']['batches'])==0
    before=original['bundle']['artifacts'];after=recovered['bundle']['artifacts']
    assert all(a in after for a in before)
    unknown=next(a for a in before if a['kind']=='ExecutionReceipt')
    assert unknown['payload']['results'][0]['outcome']=='UNKNOWN'
    resolution=next(a for a in after if a['kind']=='ReconciliationResult')
    assert resolution['payload']['original_receipt_ref']==ref(unknown)
    assert resolution['payload']['intent_ref']==unknown['payload']['results'][0]['intent_ref']
    assert resolution['payload']['recovery_call_id']=='I01-U-one-MATCH-call' and resolution['payload']['attempt_index']==1
    assert resolution['payload']['observation']=='MATCH' and resolution['payload']['replay_allowed'] is False
    assert recovered['reconcile']['attempt_count']==1 and recovered['reconcile']['target_effects_during_reconcile']==0
    u1=load(RUN/'cases/U-execute/worker-started.json');u2=load(RUN/'cases/U-recover/worker-started.json')
    assert u1['pid']!=u2['pid']
    assert (RUN/'cases/U-execute/worker-process/completed.json').stat().st_mtime_ns < (RUN/'cases/U-recover/worker-started.json').stat().st_mtime_ns
    effects_before=snapshots['cases/U-execute/captures/after-release']['target']['tables']['effects']
    effects_after=snapshots['cases/U-recover/captures/after-release']['target']['tables']['effects']
    assert effects_before==effects_after
    assert snapshots['cases/U-recover/captures/after-release']['runtime']['tables']['events'][:11]==snapshots['cases/U-execute/captures/after-release']['runtime']['tables']['events']
    final=[i for i in snapshot_infos if i['path'] in ['cases/N/captures/after-release','cases/E/captures/after-release','cases/U-recover/captures/after-release']]
    assert sum(i['dispatch_events'] for i in final)==3 and sum(i['report_reads'] for i in final)==3
    assert len(list(RUN.glob('cases/*/target-creation-attempt.json')))==3
    assert len(list(RUN.glob('cases/*/dispatch-attempt.json')))==3
    primary_hashes=[]
    for phase in ('N','E','U-recover'):
        state_phase='U-execute' if phase=='U-recover' else phase
        for db,filename in [('runtime','runtime.sqlite3'),('target','target.sqlite3')]:
            primary=RUN/'cases'/state_phase/db/filename;copy=RUN/'cases'/phase/'captures/after-release'/filename
            assert primary.read_bytes()==copy.read_bytes()
            primary_hashes.append(dict(path=str(primary.relative_to(ROOT)).replace('\\','/'),sha256=sha(primary.read_bytes())))
    completed=list(RUN.rglob('completed.json'))+[OUT/'top-level/completed.json']
    processes=[]
    for p in completed:
        row=load(p);assert row['exit_code']==0 and row['timeout'] is False and row['alive'] is False
        state=process_state(row['pid'],p.stat().st_mtime_ns)
        processes.append(dict(record=str(p),**row,live_check=state))
    assert len({p['pid'] for p in processes})==19
    timings=[]
    for phase in ('N','E','U-execute','U-recover'):
        p=RUN/'cases'/phase/'worker-ended.json';end=load(p)
        assert end['threads']==['MainThread'] and end['wall_seconds']<180
        timings.append(dict(phase=phase,pid=end['pid'],wall_seconds=end['wall_seconds'],cpu_seconds=end['cpu_seconds'],threads=end['threads']))
    index_before=load(OUT/'main-index-before.json');idx=Path(index_before['path'])
    assert sha(idx.read_bytes())==index_before['sha256']
    environment={package:importlib.metadata.version(package) for package in ('pydantic','Pillow')}
    audit=dict(status='FINITE_CHECKS_PASSED_PENDING_REPORT',candidate=CANDIDATE,delivery=DELIVERY,base=BASE,environment=environment,public_consumption=public,snapshots=snapshot_infos,results=semantics,author_fixed_json_semantics=author_semantics,imports=imports,actual_import_records=len(imports),author_import_records_compared=author_imports,unknown_ref=ref(unknown),resolution_ref=ref(resolution),resolution_payload=resolution['payload'],U_pids=[u1['pid'],u2['pid']],processes=processes,worker_timings=timings,phase_processes=matrix,final_primary_hashes=primary_hashes,targets=3,dispatches=3,annotation_effects=3,operator_changes=1,report_reads=3,reconcile_reads=1,persisted_target_reads_final=sum(x['persisted_target_reads'] for x in final),main_index_unchanged=True,author_sql_opened=False,business_reruns=0,business_failures=0,at_ns=time.time_ns())
    save(OUT/'audit.json',audit)
    save(OUT/'release.json',dict(status='RELEASED',all_original_processes_exited=True,registered_processes=len(processes),processes=[p['live_check'] for p in processes],keeper_threads_after_workers=['MainThread'],runtime_owner_pid_empty=True,runtime_lease=0,pending_before_U=1,pending_final=0,targets=3,dispatches=3,annotation_effects=3,operator_changes=1,main_index_unchanged=True,no_original_process_terminated_by_auditor=True))
    shutil.copytree(ROOT/'docs/evidence/I01-A/execution',OUT/'independent')
    save(OUT/'static-search-first-tool-failure.json',dict(kind='STATIC_SEARCH_PATH_ERROR',exit_code=1,attempted_files=['src/annotation/contracts/io.py','src/annotation/source/static.py'],stderr='rg: both guessed files do not exist (os error 2)',tool_receipt='functions exec chunk 974100',standalone_pid_or_raw_stream=False,correction='rg searched fixed contracts/source package directories and located validation.py and static/importer.py',business_calls=0,targets_created=0,dispatches=0))
    print(json.dumps(dict(status='FINITE_CHECKS_PASSED',targets=3,dispatches=3,effects=3,operator=1,raw_pairs=len(snapshot_infos),actual_imports=len(imports),processes=len(processes),U_original_unknown=ref(unknown),U_resolution=ref(resolution),main_index_unchanged=True)))

if __name__=='__main__':main()
