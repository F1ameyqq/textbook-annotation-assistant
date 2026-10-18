"""Preserve ONLY the new diagnostic scene, then one normal owner-release path."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    with Path(path).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str)+'\n').encode('utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    case, output = args.case.resolve(), args.output.resolve()
    assert case == Path(os.environ['A03_DIAGNOSTIC_CASE']).resolve()
    assert case.name == 'case' and case.parent.name == 'run' and case.parent.parent.name == 'M1-diagnostic'
    assert output == case.parent / 'release'
    output.mkdir(exist_ok=False)
    write(output/'started.json', {'pid':os.getpid(),'argv':sys.argv,'cwd':str(Path.cwd()),
        'source_sha256':sha(Path(__file__).read_bytes()),'candidate':os.environ['A03_M_CANDIDATE'],
        'started_at_ns':time.time_ns(),'old_scene_access':False,'normal_claim_max':1})
    worker = json.loads((case/'processes/execute/completed.json').read_bytes())
    assert worker['alive'] is False and worker['waited'] is True
    observers = []
    for path in sorted((case/'target/process-audit').glob('*/started.json')):
        end = json.loads(path.with_name('completed.json').read_bytes())
        assert end['alive'] is False
        observers.append(end)
    records = []
    crash = output/'termination-bytes'
    crash.mkdir()
    for label, source in [('runtime',case/'runtime/runtime.sqlite3'),('target',case/'target/target.sqlite3')]:
        for suffix in ('','-journal','-wal','-shm'):
            path = Path(str(source)+suffix)
            if not path.exists():
                continue
            raw = path.read_bytes()
            destination = crash/(label+'.sqlite3'+suffix)
            with destination.open('xb') as stream:
                stream.write(raw)
            assert sha(path.read_bytes()) == sha(raw)
            records.append({'source':str(path),'retained':str(destination),'bytes':len(raw),'sha256':sha(raw)})
    write(output/'termination-index.json', {'worker':worker,'native_observers':observers,'files':records,
        'cross_database_atomic':False,'original_sqlite_opened_before_copy':False,'sidecars_deleted':False,
        'boundary':'Owned business worker kill/wait or natural wait complete; all registered observer children exited'})
    store = observer = None
    try:
        from capture import capture, Boundary
        from annotation.runtime.storage.native import open_native_state
        from annotation.runtime.storage.native_target import NativeTargetSession
        descriptor = json.loads((case/'anchor.json').read_bytes())
        write(output/'normal-open-started.json', {'pid':os.getpid(),'time_ns':time.time_ns(),'attempt':1})
        store = open_native_state(case/'anchor.json',expected_ledger_id=descriptor['ledger_id'],
            expected_target_store_id=descriptor['target_store_id'])
        reg = store.registration('registration-M');key = store.target_key('registration-M')
        observer = NativeTargetSession.open(reg['target_dir'],expected_store_id=store.target_store_id,
            expected_target_session_id=reg['session'],expected_target_key=key,expected_scope_id=reg['scope'],
            expected_source_ref=json.loads(reg['source']))
        before = store.status('registration-M');target_before = dict(observer.export_book_context(key))
        write(output/'before-owner-release.json', {'status':before,'target_public_context':target_before,
            'stage':'AFTER_NORMAL_OPEN_NOT_TERMINATION_SQL'})
        claimed = False
        if before['owner_id'] is not None:
            # No lease extension. One bounded wait for the existing 10s lease,
            # then one ordinary claim. Failure is preserved without retry.
            delay = max(0.0, before['lease_until']-time.time()+0.03)
            assert delay <= 10.1, ('Existing lease outside unchanged 10s bound', delay)
            write(output/'existing-lease-wait.json', {'seconds':delay,'lease_until':before['lease_until'],
                'lease_extended':False,'loops':0,'scope':'Cleanup only, after business watchdog ended'})
            if delay:
                time.sleep(delay)
            write(output/'normal-claim-started.json', {'time_ns':time.time_ns(),'attempt':1})
            claim = store.claim(key,observer=observer)
            claimed = True
            store.release(key,owner_id=claim.owner_id,generation=claim.generation)
        sql = capture(case,'after-diagnostic-owner-release',boundary=Boundary())
        after = store.status('registration-M');target_after = dict(observer.export_book_context(key))
        runtime, target = sql['runtime']['tables'],sql['target']['tables']
        write(output/'after-owner-release.json', {'status':after,'target_public_context':target_after,
            'runtime_counts':{k:len(v)for k,v in runtime.items()},'target_counts':{k:len(v)for k,v in target.items()},
            'books':runtime['books'],'plans':runtime['plans'],'actions':runtime['actions'],
            'stage':'CLEANUP_COMMITTED_SQL_FROM_RETAINED_COPIES',
            'imports':{'native':str(Path(sys.modules['annotation.runtime.storage.native'].__file__).resolve()),
                       'capture':str(Path(sys.modules['capture'].__file__).resolve())}})
        assert target_before['effect_log'] == target_after['effect_log']
        assert before['actions'] == after['actions']
        assert after['owner_id'] is None and after['owner_phase']=='RELEASED' and after['lease_until']==0
        write(output/'release-proof.json', {'owner_released':True,'claimed_once':claimed,
            'actions_and_effects_unchanged':True,'dispatch':0,'reconcile':0,'publish':0,'PRE':0,
            'threads':[{'name':t.name,'alive':t.is_alive()}for t in threading.enumerate()],
            'pid':os.getpid(),'finished_at_ns':time.time_ns()})
    except BaseException as error:
        write(output/'first-error.json', {'error':repr(error),'traceback':traceback.format_exc(),
            'no_retry':True,'pid':os.getpid()})
        if store is not None:
            write(output/'residual-status.json',store.status('registration-M'))
        raise


if __name__ == '__main__':
    main()
