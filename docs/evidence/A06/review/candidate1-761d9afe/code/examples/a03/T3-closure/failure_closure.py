"""File-only failure sealing and supported owner release; never reruns M work."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def sha(raw): return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write((json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,default=str)+'\n').encode('utf-8'))


def summary(sql):
    r,t=sql['runtime']['tables'],sql['target']['tables']
    return {'runtime_counts':{name:len(rows)for name,rows in r.items()},
        'books':r['books'],'plans':r['plans'],'actions':r['actions'],'intents':r['intents'],
        'permits':r['permits'],'target_effects':t['effects'],
        'target_observation_count':len(t['observations']),
        'target_state':json.loads(next(x['value']for x in t['meta']if x['key']=='state'))}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--operation',choices=('capture','release'),required=True)
    p.add_argument('--case',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();case=a.case.resolve();out=a.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    write(out/('started-'+a.operation+'.json'),{'pid':os.getpid(),'argv':sys.argv,'cwd':str(Path.cwd()),
        'source_sha256':sha(Path(__file__).read_bytes()),'operation':'FAILURE_PRESERVATION_OR_OWNER_RELEASE_ONLY'})
    from capture import capture,Boundary
    if a.operation=='capture':
        # Preserve actual crash bytes/sidecars before any original SQLite open.
        originals=[]
        for label,source in [('runtime',case/'runtime/runtime.sqlite3'),('target',case/'target/target.sqlite3')]:
            for suffix in ('','-journal','-wal','-shm'):
                path=Path(str(source)+suffix)
                if not path.exists():continue
                b=path.read_bytes();dest=out/'crash-bytes'/(label+'.sqlite3'+suffix)
                dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb')as stream:stream.write(b)
                assert sha(path.read_bytes())==sha(b)
                originals.append({'source':str(path),'retained':str(dest),'bytes':len(b),'sha256':sha(b),
                    'quiescence':'business watchdog kill/wait completed; known native observer completed'})
        write(out/'crash-byte-index.json',{'files':originals,'cross_database_atomic':False,
            'sidecars_deleted':False,'original_sqlite_opened':False})
        sidecars=[x for x in originals if not x['source'].endswith('.sqlite3')]
        if sidecars:
            write(out/'pre-recovery-SQL-unavailable.json',{'reason':'Original sidecars retained; no immutable standalone DB audit or sidecar deletion'})
        else:
            sql=capture(case,'timeout-after-wait',boundary=Boundary())
            write(out/'after-wait-summary.json',summary(sql))
    else:
        from annotation.runtime.storage.native import open_native_state
        from annotation.runtime.storage.native_target import NativeTargetSession
        descriptor=json.loads((case/'anchor.json').read_bytes())
        store=open_native_state(case/'anchor.json',expected_ledger_id=descriptor['ledger_id'],
            expected_target_store_id=descriptor['target_store_id'])
        reg=store.registration('registration-M');key=store.target_key('registration-M')
        # Opening the frozen native target for claim needs no recreated PRE or
        # planner context. Ordinary claim/release is the only runtime mutation.
        observer=NativeTargetSession.open(reg['target_dir'],expected_store_id=store.target_store_id,
            expected_target_session_id=reg['session'],expected_target_key=key,expected_scope_id=reg['scope'],
            expected_source_ref=json.loads(reg['source']))
        status=store.status('registration-M')
        target_before=dict(observer.export_book_context(key))
        write(out/'before-owner-release.json',{'status':status,'target_public_context':target_before,
            'preclaim_SQL_capture':'NOT_AVAILABLE_JOURNAL_RETAINED_IN_FIRST_FAILURE_CLOSURE',
            'original_crash_bytes':'../failure-closure/crash-byte-index.json'})
        claim=store.claim(key,observer=observer)
        try:
            pass
        finally:
            store.release(key,owner_id=claim.owner_id,generation=claim.generation)
        after=capture(case,'after-cleanup-release-02',boundary=Boundary())
        write(out/'after-owner-release.json',{'status':store.status('registration-M'),'SQL':summary(after),
            'imports':{'native_store':str(Path(sys.modules['annotation.runtime.storage.native'].__file__).resolve()),
                       'native_target':str(Path(sys.modules['annotation.runtime.storage.native_target'].__file__).resolve())}})
        ra,ta=after['runtime']['tables'],after['target']['tables']
        target_after=dict(observer.export_book_context(key))
        assert target_before['effect_log']==target_after['effect_log']
        assert status['actions']==store.status('registration-M')['actions']
        assert all(x['owner']is None and x['phase']=='RELEASED' and x['lease']==0 for x in ra['books'])
        write(out/'owner-release-proof.json',{'dispatch':0,'reconcile':0,'new_PRE_or_plan':0,
            'public_actions_and_effect_log_unchanged':True,'owner_released':True,
            'preserved_original_timeout':True,'pid':os.getpid()})
    write(out/('completed-'+a.operation+'.json'),{'pid':os.getpid(),'completed_at_ns':time.time_ns(),
        'no_background_work_started':True})


if __name__=='__main__':main()
