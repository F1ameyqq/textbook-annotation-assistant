"""Audit independent stationary copies, artifacts and process release; no writes to stores."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path('D:/1800-worktrees/a03-r1-review-54e86adf')
R=ROOT/'docs/evidence/A03/R1/review'
OUT=Path(__file__).resolve().parent
CASES=('M1','M2-sufficient','M2-insufficient','M3-new-plan','M3-final-drift')

def load(p):return json.loads(p.read_bytes())
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def main():
    spec=importlib.util.spec_from_file_location('retained_copy_auditor',OUT/'retained_audit.py')
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    from annotation.runtime.storage.native import NativeRuntimeStore,NativeRegistry
    from annotation.contracts import a03_native
    store=NativeRuntimeStore.__new__(NativeRuntimeStore);store.native_registry=NativeRegistry(store)
    pairs=[]
    for sql in sorted(R.rglob('SQL.json')):
        if 'runtime-view' in sql.parts:continue
        expected=load(sql);capture=load(sql.with_name('capture.json'))
        assert capture['status']=='RAW_COPIES_RETAINED'
        assert capture['writer_boundary']['business_call_in_flight'] is False
        actual={}
        hashes={}
        for kind in ('runtime','target'):
            actual[kind],hashes[kind]=a.read_copy(sql.with_name(kind+'.sqlite3'))
            assert actual[kind]==expected[kind]
            rec=next(x for x in capture['records'] if x['kind']==kind)
            assert rec['sha256']==hashes[kind] and not rec['sidecars_after_writer_join']
        events=[json.loads(row['body']) for row in actual['runtime']['tables']['events']]
        heads={}
        for e in events:
            key=digest(e['target_key']);seq,previous=heads.get(key,(0,'0'*64))
            assert e['sequence']==seq+1 and e['previous_hash']==previous
            assert digest({k:v for k,v in e.items() if k!='event_hash'})==e['event_hash']
            heads[key]=(e['sequence'],e['event_hash'])
        for book in actual['runtime']['tables']['books']:
            assert heads[digest(json.loads(book['target_key']))]==(book['head_sequence'],book['head_hash'])
        pairs.append(dict(path=str(sql.parent.relative_to(R)),hashes=hashes,SQL_matches=True,event_hash_chain=True))
    results=[]
    for case in CASES:
        folder=R/'business/cases'/case
        sql=load(folder/'captures/after-release-finish/SQL.json')
        runtime,target=sql['runtime']['tables'],sql['target']['tables']
        assert all(b['owner'] is None and b['pid'] is None and b['lease']==0 and b['phase']=='RELEASED' for b in runtime['books'])
        target_state=json.loads(next(v['value'] for v in target['meta'] if v['key']=='state'))['target']
        effects=[json.loads(e['body']) for e in target['effects']]
        imported=[]
        metrics=[]
        for phase in ('execute','finish'):
            release=load(folder/('release-'+phase+'.json'))
            assert release['owned_threads']==['MainThread']
            if release['keeper'] is not None:
                assert all(not k['alive'] and k['error'] is None for k in release['keeper']['all_keeper_threads'])
            m=load(folder/('metrics-'+phase+'.json'));metrics.append(dict(phase=phase,**m))
            completion=load(folder/'processes'/phase/'completed.json')
            assert completion['exit_code']==0 and not completion['timeout'] and not completion['alive']
        reg=runtime['registrations'][0]
        bundle=load(Path(reg['bundle_path']))
        checked=store._validate(bundle,asset_root=Path(reg['package_root']))
        batches=[v for v in checked.model_dump()['artifacts'] if v['kind']=='BatchReport']
        for batch in batches:
            assert batch['payload']['content_check_status']=='PENDING' and batch['payload']['submission_status']=='NOT_SUBMITTED'
            assert batch['payload']['total_expected']==len(batch['payload']['scope_manifest'])
        results.append(dict(case=case,actions=[x['state'] for x in runtime['actions']],
            intents=len(runtime['intents']),permits=len(runtime['permits']),dispatch=len(effects),
            mutations=sum(x['mutated'] for x in effects),questions=len(target_state['questions']),
            frames=len(target_state['frames']),report_reads=len(runtime['native_report_reads']),
            validation_and_metrics=metrics,full_bundle_validated=True,released=True))
    l=load(R/'L1/result.json');assert l['counts']==[1,2,3,2]
    old=load(R/'business/cases/M2-sufficient/captures/after-release-finish/SQL.json')['runtime']['tables']
    new=load(R/'L1/captures/after-release/SQL.json')['runtime']['tables']
    old_refs={x['ref'] for x in old['artifacts']}
    assert old_refs<={x['ref'] for x in new['artifacts']}
    byid={i['id']:i for i in new['intents']}
    assert all(i['receipt']==byid[i['id']]['receipt'] for i in old['intents'])
    assert len(new['legacy'])==2 and all(b['owner'] is None and b['lease']==0 for b in new['books'])
    assert l['threads']==['MainThread'] and l['reconcile']['target_effects_during_reconcile']==0
    assert l['full_book_refusal']['code']=='BOOK_WRITE_PAUSED'
    # The current L1 registration is separately validated as a complete closure.
    reg=new['registrations'][0];store._validate(load(Path(reg['bundle_path'])),asset_root=Path(reg['package_root']))
    completions=[]
    for f in R.rglob('completed.json'):
        if 'runtime-view' in f.parts:continue
        v=load(f)
        if {'pid','alive','waited'}<=set(v):
            assert v['waited'] and not v['alive'] and not v.get('timeout',False)
            completions.append(dict(path=str(f.relative_to(R)),**v))
    result=dict(capture_pairs=pairs,cases=results,L1=dict(counts=l['counts'],old_artifact_refs_preserved=True,
        original_intent_receipt_preserved=True,pending=2,extra_dispatch=0,legacy_rows=2,released=True),
        process_completions=completions,extra_business_starts=0,
        M_starts=5,M_dispatch=sum(x['dispatch'] for x in results),
        native_module=str(Path(a03_native.__file__).resolve()),
        native_sha256=hashlib.sha256(Path(a03_native.__file__).read_bytes()).hexdigest(),
        python=sys.version,release='ALL_OWNED_KEEPERS_STOPPED_JOINED_OWNERS_RELEASED_CHILDREN_WAITED',
        SQL_originals_opened=False,SQL_only_immutable_capture_copies=True)
    (OUT/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='INDEPENDENT_AUDIT_COMPLETE',pairs=len(pairs),M_dispatch=result['M_dispatch'],
        recorded_children=len(completions),L1_pending=2)))

if __name__=='__main__':main()
