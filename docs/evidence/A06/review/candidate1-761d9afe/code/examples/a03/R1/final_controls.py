"""Only the remaining finite G2/G3/G5 controls; no business effects."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
PROJECT=Path(os.environ['A03_R1_PROJECT'])
OLD=PROJECT/'docs/evidence/A03/R1/execution'
FINAL=PROJECT/'docs/evidence/A03/R1/final-correction'
VIEW=Path(os.environ['A03_R1_RAW_VIEW'])


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


d=module(HERE/'deltas.py','final_controls_delta')


def refused(call):
    try:return d.reject(call)
    except OSError as error:return dict(layer='FILESYSTEM_IO',error=type(error).__name__,errno=error.errno,message=str(error))


def storage_roles(out):
    from annotation.runtime.storage import RuntimeStore
    from annotation.runtime.storage.native import NativeRuntimeStore,NativeRegistry,open_native_state
    from annotation.runtime.storage.native_target import NativeTargetSession
    from annotation.runtime.storage.common import exclusive_bytes
    from annotation.contracts import load_archive_bundle,convert_synthetic_fixture
    source=OLD/'candidate-1/business/cases/M1'
    capture=source/'captures/after-release-finish'
    sql=json.loads((capture/'SQL.json').read_bytes())
    desc=json.loads(next(r['value']for r in sql['target']['tables']['meta']if r['key']=='descriptor'))
    anchor=json.loads((source/'anchor.json').read_bytes())
    rows=[]
    def keep(key,call):
        result=refused(call);rows.append(dict(key=key,result=result));d.write(out/'G2-G3.json',rows)
    def rt_copy(name):
        p=out/name;p.mkdir();state=p/'runtime';state.mkdir()
        shutil.copyfile(capture/'runtime.sqlite3',state/'runtime.sqlite3')
        a=p/'anchor.json';value=dict(anchor,state_dir=str(state.resolve()),anchor_path=str(a.resolve()))
        d.write(a,value);return a,value
    a,_=rt_copy('directory-binding')
    keep('G2-runtime-directory-binding',lambda:open_native_state(a,expected_ledger_id=anchor['ledger_id'],expected_target_store_id=anchor['target_store_id']))
    a,value=rt_copy('runtime-unknown');value['db_version']='unknown-final-runtime';d.write(a,value)
    keep('G2-unknown-runtime-format',lambda:open_native_state(a,expected_ledger_id=anchor['ledger_id'],expected_target_store_id=anchor['target_store_id']))
    kwargs=dict(expected_store_id=desc['store_id'],expected_target_session_id=desc['target_session_id'],
        expected_target_key=desc['target_key'],expected_scope_id=desc['fixed_scope_id'],expected_source_ref=desc['fixed_source_ref'])
    for label,alter in [('target-unknown',True),('target-directory',False)]:
        p=out/label;p.mkdir();raw=(capture/'target.sqlite3').read_bytes()
        if alter:raw=raw[:60]+(0x1020304).to_bytes(4,'big')+raw[64:]
        (p/'target.sqlite3').write_bytes(raw)
        keep('G2-'+label,lambda p=p:NativeTargetSession.open(p,**kwargs))
    store=NativeRuntimeStore.__new__(NativeRuntimeStore);store.native_registry=NativeRegistry(store)
    fixture=VIEW/'examples/a03/T3-closure/inputs/single';data=json.loads((fixture/'initial.json').read_bytes())
    data['format_version']='unknown-final-exchange'
    keep('G2-unknown-exchange',lambda:store._validate(data,asset_root=fixture))
    blocker=out/'write-blocker';blocker.write_bytes(b'controlled negative file')
    keep('G2-file-write-IO',lambda:exclusive_bytes(blocker/'child',b'cannot create under a file'))
    negative=out/'transaction-copy.sqlite3';shutil.copyfile(capture/'runtime.sqlite3',negative)
    before=hashlib.sha256(negative.read_bytes()).hexdigest()
    transaction=RuntimeStore.__new__(RuntimeStore);transaction.database=negative
    def transaction_error():
        with transaction.transaction()as connection:connection.execute('SELECT final_deliberately_absent_column FROM meta').fetchall()
    keep('G2-SQL-rollback-wrapper',transaction_error)
    assert before==hashlib.sha256(negative.read_bytes()).hexdigest()
    legacy=VIEW/'examples/a03/P2-R12-R1-unknown-projection/legacy-recovery/bundle.json'
    archive=load_archive_bundle(legacy)
    rows.append(dict(key='G3-1.1-archive-read',version=archive['bundle']['format_version'],native_authority=hasattr(archive,'bridge_context')))
    keep('G3-1.1-as-native',lambda:store._validate(archive['bundle'],asset_root=legacy.parent))
    source=VIEW/'tests/fixtures/a03/R1/final/conversion-failure/input.json'
    dest=out/'interrupted-conversion'
    keep('G3-post-marker-conversion-IO',lambda:convert_synthetic_fixture(source,dest,conversion_id='final-interrupted',
        expected_input_sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    marker=json.loads((dest/'conversion-incomplete.json').read_bytes())
    assert marker['status']=='INCOMPLETE'and not(dest/'bundle.json').exists()
    keep('G3-reopen-incomplete',lambda:load_archive_bundle(dest/'bundle.json'))
    assert json.loads((dest/'conversion-incomplete.json').read_bytes())==marker
    d.write(out/'result.json',dict(controls=rows,conversion_marker=marker,transaction_bytes_unchanged=True,
        negative_database_copies=5,G2_calls=7,G3_calls=4,new_business_targets=0,dispatch=0,
        note='transaction wrapper uses a deliberate invalid SELECT on its own stationary negative copy; no positive authority inferred'))


def report_values(out):
    from annotation.contracts import artifact_ref,recovery
    from annotation.contracts.a03_native import NativeSchemas,VERSION,_reports
    c=module(HERE/'controls.py','final_report_seal')
    oldsql=json.loads((OLD/'deltas-correction/L1/captures/after-release/SQL.json').read_bytes())
    reg=oldsql['runtime']['tables']['registrations'][0]
    original=json.loads(Path(reg['bundle_path']).read_bytes());assets=Path(reg['package_root'])
    resolution=next(a for a in original['artifacts']if a['kind']=='ReconciliationResult')
    value=copy.deepcopy(original);value['artifacts']=[a for a in value['artifacts']if a['kind']!='BatchReport']
    post=next(a for a in value['artifacts']if a['kind']=='CheckReport'and a['payload']['stage']=='POST_APPLY')
    post['payload']['report_snapshot_ref']=resolution['payload']['observed_snapshot_ref']
    post['payload']['report_observation']=resolution['payload']['readback'];c.seal_all(value)
    ctx=recovery._Closure(value,assets,schema_version=VERSION,schemas=NativeSchemas());ctx.native=True
    heads=recovery._resolutions(ctx)
    old_report=d.reject(lambda:_reports(ctx,heads))
    newer=json.loads((FINAL/'run/cases/L3-second/result.json').read_bytes())['bundle']
    foreign=next(a for a in newer['artifacts']if a['kind']=='ReconciliationResult')
    combined=dict(original,artifacts=original['artifacts']+newer['artifacts'])
    multi=recovery._Closure(combined,assets,schema_version=VERSION,schemas=NativeSchemas());multi.native=True
    post=next(a for a in original['artifacts']if a['kind']=='CheckReport'and a['payload']['stage']=='POST_APPLY')
    p=resolution['payload'];q=foreign['payload']
    wrong_heads={recovery.canonical_hash(p['intent_ref']):foreign,recovery.canonical_hash(q['intent_ref']):foreign}
    assert p['observed_snapshot_ref']!=q['observed_snapshot_ref']
    wrong_head=d.reject(lambda:recovery._consumer_resolution_head(multi,post,artifact_ref(resolution),wrong_heads,
        intent_ref=p['intent_ref'],plan_ref=p['plan_ref'],action_id=p['action_id']))
    d.write(out/'result.json',dict(G5_calls=2,old_report_read=old_report,foreign_head_different_snapshot=wrong_head,
        real_heads=[artifact_ref(resolution),artifact_ref(foreign)],snapshots=[p['observed_snapshot_ref'],q['observed_snapshot_ref']],
        layer='PURE_VALUE_GUARDS; no new POST/Batch, mixed-native qualification or runtime effects',dispatch=0,new_targets=0))


def run(phase,out):
    if phase=='G2-G3':storage_roles(out)
    elif phase=='G5':report_values(out)
    else:raise ValueError(phase)
