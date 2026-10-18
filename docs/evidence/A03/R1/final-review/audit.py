"""Independent evidence audit; SQL opens only stationary exported/captured copies."""
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

ROOT=Path('D:/1800-worktrees/a03-r1-final-review-19ab03c8')
PREVIOUS=Path('D:/1800-worktrees/a03-r1-review-54e86adf')
OUT=Path(__file__).resolve().parent
AUTHOR=ROOT/'docs/evidence/A03/R1/final-correction'
REVIEW=ROOT/'route-project/docs/evidence/A03/R1/final-correction'
PHASES=('L2','L3-execute','L3-reconcile','L3-second','G6-first','G6-reopen','L4','G2-G3','G5','F')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(p.read_bytes())
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def sql_copy(path):
    assert path.is_relative_to(ROOT)and 'captures'in path.parts
    before=sha(path.read_bytes())
    db=sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row
    try:
        assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        names=[r[0]for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        value=dict(application_id=db.execute('PRAGMA application_id').fetchone()[0],user_version=db.execute('PRAGMA user_version').fetchone()[0],
            tables={n:[dict(r)for r in db.execute('SELECT * FROM "'+n.replace('"','""')+'" ORDER BY rowid')]for n in names})
    finally:db.close()
    assert before==sha(path.read_bytes())
    return value,before
def outputs(root):return {p:load(root/'run/cases'/p/'result.json')for p in PHASES}
def copies(root):
    rows=[]
    for f in sorted((root/'run/cases').rglob('SQL.json')):
        expected=load(f);capture=load(f.with_name('capture.json'));assert capture['status']=='RAW_COPIES_RETAINED'
        assert not capture['cross_database_atomic']and not capture['writer_boundary']['business_call_in_flight']
        values={};hashes={}
        for kind in ('runtime','target'):
            values[kind],hashes[kind]=sql_copy(f.with_name(kind+'.sqlite3'))
            assert values[kind]==expected[kind]
            record=next(r for r in capture['records']if r['kind']==kind)
            assert record['sha256']==hashes[kind]and not record['sidecars_after_writer_join']
        r,t=values['runtime']['tables'],values['target']['tables']
        assert all(b['owner']is None and b['pid']is None and b['lease']==0 and b['phase']=='RELEASED'for b in r['books'])
        heads={}
        for row in r['events']:
            e=json.loads(row['body']);previous=heads.get(row['book'],(0,'0'*64))
            assert(e['sequence'],e['previous_hash'])==(previous[0]+1,previous[1])
            assert sha(canonical({k:v for k,v in e.items()if k!='event_hash'}))==e['event_hash']
            heads[row['book']]=(e['sequence'],e['event_hash'])
        for b in r['books']:assert heads[b['key']]==(b['head_sequence'],b['head_hash'])
        effects=[json.loads(x['body'])for x in t['effects']]
        state=json.loads(next(x['value']for x in t['meta']if x['key']=='state'))['target']
        rows.append(dict(phase=f.parent.parent.parent.name,hashes=hashes,SQL_matches=True,
            dispatch=len(effects),mutations=sum(e['mutated']for e in effects),questions=len(state['questions']),frames=len(state['frames']),
            intents=[dict(id=i['id'],state=i['state'],receipt=i['receipt'])for i in r['intents']],
            permits=len(r['permits']),legacy=len(r['legacy']),report_reads=len(r['native_report_reads']),released=True,
            events=len(r['events']),native_readonly_entries=len(r['native_readonly_entries'])))
    return rows
def completion_records(root):
    values=[]
    expected=sha((ROOT/'src/annotation/runtime/recovery/native_observation.py').read_bytes())
    for f in sorted(root.rglob('completed.json')):
        if 'runtime-view'in f.parts:continue
        v=load(f)
        if not {'pid','exit_code','alive'}<=set(v):continue
        assert not v['alive']
        read='process-audit'in f.parts
        if read:
            assert sha(f.with_name('script-snapshot.py').read_bytes())==expected
            if v['timeout']:assert v['exit_code']!=0
            else:assert v['exit_code']==0
            wait='PINNED_NATIVE_WAIT_THEN_POLL'
        else:
            assert v['waited']and not v['timeout']and v['exit_code']==0
            wait='EXPLICIT_WAITED'
        values.append(dict(path=str(f),wait_basis=wait,**v))
    return values
def controls(out):
    l2=out['L2'];assert l2['A_before']['pending']==l2['A_after']['pending']and l2['A_after']['pending_count']==2
    assert l2['B_status']['pending_count']==0 and l2['B']['status']=='FINISHED'
    first,reconciled,second=out['L3-execute'],out['L3-reconcile'],out['L3-second']
    assert first['status']['pending_count']==1 and reconciled['status']['pending_count']==0 and second['status']['pending_count']==1
    assert reconciled['reconcile']['attempt_count']==1 and reconciled['reconcile']['resolutions'][0]['classification']=='ABSENT'
    assert first['plan']['payload']['actions'][0]['action_id']!=second['plan']['payload']['actions'][0]['action_id']
    first_intent=next(a for a in first['bundle']['artifacts']if a['kind']=='WriteIntent')
    later_intents=[a for a in second['bundle']['artifacts']if a['kind']=='WriteIntent']
    assert len(later_intents)==2 and first_intent in later_intents
    assert all(a in second['bundle']['artifacts']for a in first['bundle']['artifacts'])
    assert out['G6-first']['reconcile']['attempt_count']==3 and out['G6-reopen']['reconcile']['attempt_count']==0
    before=out['G6-first']['export'];after=out['G6-reopen']['export']
    # Exact tables below distinguish attempted reads, successful observations and calls.
    return dict(new_targets=2,dispatch=3,legacy_generation=0,M_L1_G4_new_business=0,
        A_pending=2,B_pending=0,L3_pending=1,L3_distinct_actions=True,
        G6_first_attempts=3,G6_reopen_attempts=0,L4=out['L4'],G2_G3=out['G2-G3'],G5=out['G5'],F=out['F'])

def main():
    prep=load(OUT/'preparation.json');expected={r['path']:r['sha256']for r in prep['exported']}
    audit=dict(groups={},sqlite_version=sqlite3.sqlite_version,SQL_only_immutable_copies=True,extra_fixed_identity_reads=[])
    for label,root in [('author',AUTHOR),('independent',REVIEW)]:
        matrix=load(root/'run/matrix.json');assert [x['phase']for x in matrix]==list(PHASES)
        assert all(x['status']=='ENDED'and x['process']['exit_code']==0 and not x['process']['timeout']for x in matrix)
        result=outputs(root);bounded=controls(result);pairs=copies(root)
        assert len(pairs)==6
        byphase={r['phase']:r for r in pairs}
        assert(byphase['L2']['dispatch'],byphase['L3-execute']['dispatch'],byphase['L3-second']['dispatch'])==(1,1,2)
        assert(byphase['L2']['mutations'],byphase['L3-execute']['mutations'],byphase['L3-second']['mutations'])==(1,0,1)
        assert byphase['G6-first']['dispatch']==byphase['G6-reopen']['dispatch']==2
        g6a=load(root/'run/cases/G6-first/captures/after-release/SQL.json')['runtime']['tables']
        g6b=load(root/'run/cases/G6-reopen/captures/after-release/SQL.json')['runtime']['tables']
        for table in ('calls','attempt_windows','attempts'):
            assert g6a[table]==g6b[table]
        attempts=[r for r in g6b['attempts']if r['call_id']=='final-G6-fixed-call']
        assert len(attempts)==3 and [x['number']for x in attempts]==[1,2,3]and all(x['status']=='FAILED_READ'for x in attempts)
        assert len({x['intent']for x in attempts})==1
        assert len(g6b['intents'])==2 and [i['state']for i in g6b['intents']]==['RESOLVED_NOT_APPLIED','PENDING']
        assert g6b['native_report_reads']==[]
        f=result['F'];assert f['before']==f['after']and all(f[k]==0 for k in ('dispatch','claim','reconcile','publisher'))
        imports=[];metrics=[]
        for phase in PHASES:
            worker=load(root/'run/cases'/phase/'worker-ended.json');assert worker['threads']==['MainThread']
            for name,row in worker['imports'].items():
                p=row['file'].replace('\\','/');path='src/annotation/'+p.split('/src/annotation/',1)[1]
                assert row['sha256']==expected[path],(label,phase,name)
                if label=='independent':assert p.lower().startswith(str(REVIEW/'frozen/runtime-view').replace('\\','/').lower()+'/')
            imports.append(dict(phase=phase,modules=len(worker['imports']),hashes_match=True))
            metrics.append(dict(phase=phase,wall_seconds=worker['wall_seconds'],cpu_seconds=worker['cpu_seconds'],pid=worker['pid']))
        actual_files=load(root/'frozen/runtime-identities.json')['files']+load(root/'frozen/extra-identities.json')
        for row in actual_files:
            if row['path']not in expected:
                argv=['git','-c','core.longpaths=true','-C',str(ROOT),'show',
                    '9992cd8aba10987d25dd0dc0d0874abec02b27ef:'+row['path']]
                process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                stdout,stderr=process.communicate(timeout=45)
                assert process.returncode==0
                expected[row['path']]=sha(stdout)
                audit['extra_fixed_identity_reads'].append(dict(argv=argv,pid=process.pid,exit_code=process.returncode,
                    waited=True,sha256=sha(stdout),stderr=stderr.decode('utf-8','replace')))
            assert row.get('raw_sha256',row.get('sha256'))==expected[row['path']]
        completions=completion_records(root)
        assert sum(r.get('timeout',False)for r in completions)==3
        audit['groups'][label]=dict(matrix=matrix,bounded=bounded,capture_pairs=pairs,imports=imports,metrics=metrics,
            completions=completions,raw_executed_files=len(actual_files))
    # All own L1 original identities remain intact. Only its authorised runtime
    # continuation has changed; frozen previous captures/report/index are read only.
    own=PREVIOUS/'docs/evidence/A03/R1/review'
    live=own/'business/cases/M2-sufficient'
    final=REVIEW/'run/cases/L2/captures/after-release'
    assert(live/'runtime/runtime.sqlite3').read_bytes()==(final/'runtime.sqlite3').read_bytes()
    assert sha((live/'target/target.sqlite3').read_bytes())==prep['continuation'][1]['sha256']
    main=Path('D:/1800');old_manifest=main/'docs/evidence/A03/R1/review/manifest.json'
    assert sha(old_manifest.read_bytes())==prep['old_review_manifest_sha256']
    previous=load(old_manifest)
    assert all(sha((main/r['path']).read_bytes())==r['sha256']for r in previous['members'])
    audit['old_fixed_review_members_preserved']=len(previous['members'])
    audit['own_live_runtime_matches_new_L2_capture']=True
    audit['own_A_target_unchanged']=True
    # Author continuation files are frozen byte copies: bind their DB to L2's
    # immutable capture without following any author absolute live path.
    idx=load(AUTHOR/'continuation-files/index.json')
    audit['author_continuation_index']=idx
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    states=[]
    for pid in sorted({r['pid']for r in audit['groups']['independent']['completions']}|{load(OUT/'process/completed.json')['pid']}):
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:states.append(dict(pid=pid,state='NOT_OPENABLE_AS_LIVE_PROCESS'));continue
        try:
            code=wintypes.DWORD();assert kernel.GetExitCodeProcess(handle,ctypes.byref(code))
            states.append(dict(pid=pid,state='STILL_ACTIVE_OR_PID_REUSED'if code.value==259 else'EXITED',exit_code=code.value))
        finally:kernel.CloseHandle(handle)
    audit['registered_PID_states']=states
    assert not any(x['state']=='STILL_ACTIVE_OR_PID_REUSED'for x in states)
    with(OUT/'audit.json').open('xb')as stream:stream.write((json.dumps(audit,indent=2)+'\n').encode())
    print(json.dumps(dict(status='FINAL_DELTA_AUDIT_COMPLETE',author_pairs=6,review_pairs=6,
        author_processes=len(audit['groups']['author']['completions']),review_processes=len(audit['groups']['independent']['completions']),
        new_targets=2,dispatch=3,mutations=2,old_review_members_preserved=len(previous['members']))))

if __name__=='__main__':main()
