"""Read retained copies and verify releases; never opens a primary SQLite DB."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
EVIDENCE=ROOT/'docs/evidence/A03/R1/execution'
spec=importlib.util.spec_from_file_location('m_driver',ROOT/'examples/a03/T3-closure/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def main():
    out=EVIDENCE/'verification';out.mkdir(exist_ok=False)
    business=EVIDENCE/'candidate-1/business';view=business/'runtime-view'
    env=dict(os.environ,PYTHONPATH=str(view/'src'),A03_M_EVIDENCE=str(business),PYTHONDONTWRITEBYTECODE='1')
    result=m.run_child(out/'M-assertions',[sys.executable,'-X','utf8','-B',str(view/'tests/test_a03_t3_closure.py')],
        cwd=ROOT,env=env,timeout=60)
    assert result['exit_code']==0 and not result['timeout']
    rows=[]
    for case in m.CASES:
        folder=business/'cases'/case
        copies=folder/'captures/after-release-finish/SQL.json'
        sql=json.loads(copies.read_bytes())
        runtime,target=sql['runtime']['tables'],sql['target']['tables']
        assert all(b['owner']is None and b['lease']==0 and b['phase']=='RELEASED'for b in runtime['books'])
        for phase in ('execute','finish'):
            release=json.loads((folder/('release-'+phase+'.json')).read_bytes())
            assert release['owned_threads']==['MainThread']
        rows.append(dict(case=case,dispatch=len(target['effects']),intents=len(runtime['intents']),permits=len(runtime['permits']),
            execute=json.loads((folder/'metrics-execute.json').read_bytes()),finish=json.loads((folder/'metrics-finish.json').read_bytes())))
    continued=EVIDENCE/'deltas-correction/L1/captures/after-release'
    sql=json.loads((continued/'SQL.json').read_bytes())
    assert all(b['owner']is None and b['lease']==0 and b['phase']=='RELEASED'for b in sql['runtime']['tables']['books'])
    source=business/'cases/M2-sufficient/runtime/runtime.sqlite3'
    assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256((continued/'runtime.sqlite3').read_bytes()).digest()
    # B failed before register/claim; the latest released state still has one registration.
    assert len(sql['runtime']['tables']['registrations'])==1
    processes=[]
    for path in sorted(business.rglob('completed.json')):
        value=json.loads(path.read_bytes())
        assert not value.get('alive',False),path
        processes.append(dict(path=str(path.relative_to(EVIDENCE)),value=value))
    m.write(out/'result.json',dict(M=rows,continued_ledger_release='PROVEN_FROM_T1_COPY_AND_RAW_PRIMARY_HASH',
        no_new_B_registration=True,processes=processes,primary_sqlite_opened=False,
        original_failure_scenes_opened=False,dispatch_sum=sum(r['dispatch']for r in rows)))
    print('M_ASSERTIONS_AND_RELEASES_ENDED',sum(r['dispatch']for r in rows))


if __name__=='__main__':main()
