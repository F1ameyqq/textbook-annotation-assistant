"""Independently query only the raw exported stationary capture copies."""
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT=Path('D:/1800-worktrees/a03-r1-review-54e86adf')
OUT=Path(__file__).resolve().parent
E=ROOT/'docs/evidence/A03/R1/execution'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(path.read_bytes())
def read_copy(path):
    assert 'captures' in path.parts and path.is_relative_to(ROOT)
    before=sha(path.read_bytes())
    db=sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)
    db.row_factory=sqlite3.Row
    try:
        assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        value=dict(application_id=db.execute('PRAGMA application_id').fetchone()[0],
                   user_version=db.execute('PRAGMA user_version').fetchone()[0],
                   tables={name:[dict(r) for r in db.execute('SELECT * FROM "'+name.replace('"','""')+'" ORDER BY rowid')]
                           for name in names})
    finally:db.close()
    assert before==sha(path.read_bytes())
    return value,before

def main():
    rows=[]
    cases=('M1','M2-sufficient','M2-insufficient','M3-new-plan','M3-final-drift')
    stages=[(case,E/'candidate-1/business/cases'/case/'captures/after-release-finish') for case in cases]
    stages.append(('L1',E/'deltas-correction/L1/captures/after-release'))
    for label,folder in stages:
        expected=load(folder/'SQL.json');capture=load(folder/'capture.json')
        assert capture['status']=='RAW_COPIES_RETAINED' and not capture['cross_database_atomic']
        values={};hashes={}
        for kind in ('runtime','target'):
            values[kind],hashes[kind]=read_copy(folder/(kind+'.sqlite3'))
            assert values[kind]==expected[kind]
            rec=next(r for r in capture['records'] if r['kind']==kind)
            assert rec['sha256']==hashes[kind] and not rec['sidecars_after_writer_join']
        r,t=values['runtime']['tables'],values['target']['tables']
        assert all(b['owner'] is None and b['pid'] is None and b['lease']==0 and b['phase']=='RELEASED' for b in r['books'])
        effects=[json.loads(x['body']) for x in t['effects']]
        events=[json.loads(x['body']) for x in r['events']]
        target_state=json.loads(next(x['value'] for x in t['meta'] if x['key']=='state'))['target']
        for effect in effects:
            intent=next(i for i in r['intents'] if i['action']==effect['action_id'])
            assert intent['owner']==effect['owner_id'] and intent['generation']==effect['generation']
            relevant=[e for e in events if e.get('plan_ref')==effect['plan_ref']]
            writes=[e for e in relevant if e['event']=='WRITE_INTENT_COMMITTED' and e['payload'].get('action_id')==effect['action_id']]
            starts=[e for e in relevant if e['event']=='DISPATCH_STARTED' and e['payload'].get('action_id')==effect['action_id']]
            assert len(writes)==len(starts)==1 and writes[0]['sequence']<starts[0]['sequence']
            assert starts[0]['recorded_at']<=effect['recorded_at']
        metrics=[]
        if label!='L1':
            for phase in ('execute','finish'):
                m=load(folder.parents[1]/('metrics-'+phase+'.json'))
                metrics.append(dict(phase=phase,wall_seconds=m['wall_seconds'],cpu_seconds=m['cpu_seconds'],validation=m['validation']))
        rows.append(dict(case=label,sql_matches=True,hashes=hashes,
            action_states=[a['state'] for a in r['actions']],intents=len(r['intents']),permits=len(r['permits']),
            dispatch=len(effects),mutations=sum(e['mutated'] for e in effects),questions=len(target_state['questions']),
            frames=len(target_state['frames']),report_reads=len(r['native_report_reads']),
            released=True,metrics=metrics))
    l=load(E/'deltas-correction/L1/result.json')
    assert l['counts']==[1,2,3,2] and l['full_book_refusal']['code']=='BOOK_WRITE_PAUSED'
    assert l['reconcile']['target_effects_during_reconcile']==0 and l['reconcile']['attempt_count']==1
    assert l['status']['paused'] and l['status']['pending_count']==2
    records=[]
    for f in E.rglob('completed.json'):
        v=load(f)
        if {'pid','exit_code','waited','alive'}<=set(v):
            assert v['waited'] and not v['alive']
            records.append(dict(path=str(f.relative_to(ROOT)),**v))
    result=dict(sqlite_version=sqlite3.sqlite_version,capture_pairs=rows,process_completions=records,
        native_M_starts=5,native_M_dispatch=sum(x['dispatch'] for x in rows if x['case']!='L1'),
        legacy_calls_first_failed=1,legacy_calls_corrected=2,L2_dispatch=0,
        author_original_databases_opened=False,SQL_only_stationary_raw_export_copies=True)
    (OUT/'retained-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='RETAINED_COPIES_MATCH',pairs=len(rows),M_dispatch=result['native_M_dispatch'],processes=len(records))))

if __name__=='__main__':main()
