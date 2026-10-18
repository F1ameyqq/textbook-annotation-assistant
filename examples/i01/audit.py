"""Post-run static closure only; SQL touches retained immutable copies only."""
import ctypes
import json
import os
from pathlib import Path
from support import ROOT, EVIDENCE, BASE, PRODUCT, git, load, sha, canonical, write, module


def ref(a): return {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}


def main():
    raw=EVIDENCE/'preparation/raw-view'
    capture=module(raw/'examples/a03/T1-capture/capture.py','i01_fixed_capture')
    prep=load(EVIDENCE/'preparation/identity.json')
    identities=[]
    # Compare every exported original, not just the pinned implementation subset.
    for row in prep['files']:
        assert sha((raw/row['path']).read_bytes())==row['sha256'], row['path']
        assert sha(git(['show',BASE+':'+row['path']]))==row['sha256'], row['path']
        identities.append(row)
    assert not git(['diff','--name-only',BASE,'HEAD','--','src','pyproject.toml','requirements.txt'])
    fixture_root=EVIDENCE/'frozen/candidate-view'
    for row in load(EVIDENCE/'frozen/invocation.json')['files']:
        assert sha((fixture_root/row['path']).read_bytes())==row['sha256']
    process_records=[]
    for path in sorted(EVIDENCE.rglob('completed.json')):
        d=load(path)
        assert d['exit_code']==0 and d['alive'] is False and d['timeout'] is False, path
        start=load(path.parent/'started.json')
        assert start['pid']==d['pid']
        assert (path.parent/'stdout.txt').is_file() and (path.parent/'stderr.txt').is_file()
        process_records.append(dict(path=str(path.relative_to(ROOT)),**d))
    imports=[]
    import_records=list((EVIDENCE/'run/cases').glob('*/worker-ended.json'))+list((EVIDENCE/'run/public-imports').glob('*.json'))
    for file in import_records:
        entry=load(file)
        if 'threads' in entry: assert entry['threads']==['MainThread']
        for name, identity in entry['imports'].items():
            path=Path(identity['path'])
            relative=path.relative_to(raw).as_posix()
            assert sha(path.read_bytes())==identity['sha256']
            assert any(row['path']==relative and row['sha256']==identity['sha256'] for row in identities)
            imports.append(dict(record=str(file.relative_to(ROOT)),module=name,**identity))
    snapshots=[]
    for path in sorted((EVIDENCE/'run/cases').glob('*/captures/*/SQL.json')):
        folder=path.parent
        original=load(path)
        actual={name:capture.sql_copy(folder/(name+'.sqlite3')) for name in ('runtime','target')}
        assert original==actual
        meta=load(folder/'capture.json')
        assert meta['status']=='RAW_COPIES_RETAINED' and meta['cross_database_atomic'] is False
        for row in meta['records']:
            assert sha((folder/(row['kind']+'.sqlite3')).read_bytes())==row['sha256']
            assert row['sidecars_after_writer_join']=={}
        rt,tg=actual['runtime']['tables'],actual['target']['tables']
        events=[json.loads(r['body']) for r in rt['events']]
        head='0'*64
        for index,event in enumerate(events,1):
            assert event['sequence']==index and event['previous_hash']==head
            assert event['event_hash']==sha(canonical({k:v for k,v in event.items() if k!='event_hash'}))
            head=event['event_hash']
        for book in rt['books']:
            assert book['owner'] is None and book['pid'] is None and book['lease']==0 and book['phase']=='RELEASED'
            assert book['head_hash']==head and book['head_sequence']==len(events)
        state=json.loads(next(row['value'] for row in tg['meta'] if row['key']=='state'))
        effects=[json.loads(row['body']) for row in tg['effects']]
        snapshots.append(dict(path=str(folder.relative_to(ROOT)),events=len(events),event_head=head,
            plans=len(rt['plans']),intents=len(rt['intents']),permits=len(rt['permits']),
            dispatch_events=sum(e['event']=='DISPATCH_STARTED' for e in events),
            effects=len(effects),mutated=sum(e['mutated'] for e in effects),
            questions=len(state['target']['questions']),frames=len(state['target']['frames']),
            target_epoch=state['epoch'],persisted_target_reads=len(tg['observations']),
            native_pre_runs=len(rt['native_pre_runs']),report_reads=len(rt['native_report_reads']),
            recovery_calls=len(rt['calls']),recovery_attempts=len(rt['attempts']),owner_pid_empty=True,lease=0))
    assert len(snapshots)==5
    results={phase:load(EVIDENCE/'run/cases'/phase/'result.json') for phase in ('N','E','U-execute','U-recover')}
    rows=[]
    for phase,result in results.items():
        artifacts=result['bundle']['artifacts']
        pre=[a for a in artifacts if a['kind']=='CheckReport' and a['payload']['stage']=='PRE_APPLY']
        for a in pre:
            assert a['payload']['decision']=='PASS'
            assert {c['check_id'] for c in a['payload']['checks']}=={'source_integrity','structure','answer_matching','coverage','policy'}
            assert all(c['outcome']=='PASS' for c in a['payload']['checks'])
        receipts=[a for a in artifacts if a['kind']=='ExecutionReceipt']
        posts=[a for a in artifacts if a['kind']=='CheckReport' and a['payload']['stage']=='POST_APPLY']
        batches=[a for a in artifacts if a['kind']=='BatchReport']
        if phase=='U-execute':
            assert len(receipts)==1 and receipts[0]['payload']['results'][0]['outcome']=='UNKNOWN'
            assert result['status']['pending_count']==1 and result['status']['paused']
            assert not posts and not batches
        else:
            assert result['status']['pending_count']==0 and not result['status']['paused']
            assert len(posts)==len(batches)==1
            assert receipts[-1]['payload']['results'][0]['outcome']=='APPLIED'
            assert posts[0]['payload']['frame_structure']=='PASS'
            assert posts[0]['payload']['content_check_status']=='PENDING' and posts[0]['payload']['submission_status']=='NOT_SUBMITTED'
            batch=batches[0]['payload']
            assert batch['total_expected']==len(batch['scope_manifest'])==len(batch['questions'])==1
            assert batch['content_check_status']=='PENDING' and batch['submission_status']=='NOT_SUBMITTED'
        rows.append(dict(phase=phase,pending=result['status']['pending_count'],
            receipts=[dict(ref=ref(a),outcome=a['payload']['results'][0]['outcome'],attempt_fact=a['payload']['results'][0]['attempt_fact']) for a in receipts],
            PRE_checks=len(pre),posts=len(posts),batches=len(batches)))
    old=next(s for s in snapshots if s['path'].endswith('old-candidate-refused-released'))
    assert old['intents']==old['permits']==old['effects']==old['dispatch_events']==old['plans']==0
    assert old['native_pre_runs']==1 and old['questions']==old['frames']==0 and old['target_epoch']==1
    E=results['E']['correction']
    assert E['old_dispatches']==0 and E['operator_changes']==1
    assert E['old_plan']['payload']['snapshot']!=E['new_plan']['payload']['snapshot']
    assert E['old_plan']['payload']['precheck']!=E['new_plan']['payload']['precheck']
    unknown=next(a for a in results['U-execute']['bundle']['artifacts'] if a['kind']=='ExecutionReceipt')
    final=results['U-recover']
    assert unknown in final['bundle']['artifacts']
    resolutions=[a for a in final['bundle']['artifacts'] if a['kind']=='ReconciliationResult']
    assert len(resolutions)==1 and resolutions[0]['payload']['original_receipt_ref']==ref(unknown)
    assert final['reconcile']['attempt_count']==1 and final['reconcile']['resolutions'][0]['classification']=='MATCH'
    assert final['execution_pid']!=load(EVIDENCE/'run/cases/U-recover/worker-started.json')['pid']
    # Compare only current released primaries; older U capture remains a historic original.
    primary=[]
    for tag,phase in [('N','N'),('E','E'),('U-execute','U-recover')]:
        case=EVIDENCE/'run/cases'/tag
        last=EVIDENCE/'run/cases'/phase/'captures/after-release'
        for kind in ('runtime','target'):
            source=case/kind/(kind+'.sqlite3')
            assert sha(source.read_bytes())==sha((last/(kind+'.sqlite3')).read_bytes())
            primary.append(dict(path=str(source.relative_to(ROOT)),sha256=sha(source.read_bytes())))
        retained=load(last/'SQL.json')['runtime']['tables']
        for row in retained['files']:
            path=case/'runtime'/row['path']
            assert path.stat().st_size==row['size'] and sha(path.read_bytes())==row['sha']
    pids=sorted({r['pid'] for r in process_records})
    # Check OS process liveness without opening any store or target.
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.restype=ctypes.c_void_p
    process_status=[]
    for pid in pids:
        handle=kernel.OpenProcess(0x1000,False,pid)
        alive=False
        if handle:
            code=ctypes.c_ulong()
            assert kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code))
            alive=code.value==259
            kernel.CloseHandle(ctypes.c_void_p(handle))
        assert not alive, pid
        process_status.append(dict(pid=pid,alive=False))
    targets=list((EVIDENCE/'run/cases').glob('*/target-creation-attempt.json'))
    assert len(targets)==3
    final_sql=[s for s in snapshots if s['path'].endswith('after-release') and 'U-execute' not in Path(s['path']).parts]
    assert sum(s['dispatch_events'] for s in final_sql)==3
    assert sum(s['mutated'] for s in final_sql)==3
    public={m:load(EVIDENCE/'run/processes'/p/'stdout.txt') for m,p in [('C01','A01-C01'),('A01','A01-consume')]}
    write(EVIDENCE/'audit.json',dict(status='AUTHOR_STATIC_CLOSURE_ONLY_REVIEW',base=BASE,product=PRODUCT,
        raw_originals=len(identities),implementation_pins=30,import_records=len(imports),imports=imports,
        processes=process_records,process_status=process_status,snapshots=snapshots,results=rows,
        public_consumption=public,targets=3,dispatches=3,annotation_effects=3,operator_changes=1,
        U_original_unknown=ref(unknown),U_resolution=ref(resolutions[0]),released_primaries=primary,
        product_business_reruns=0,content_check_status='PENDING',submission_status='NOT_SUBMITTED'))
    print('AUTHOR_AUDIT_OK; targets=3 dispatch=3 effects=3 operator=1; no business calls')


if __name__=='__main__': main()
