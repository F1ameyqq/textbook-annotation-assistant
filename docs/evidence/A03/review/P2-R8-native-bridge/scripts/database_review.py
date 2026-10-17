# -*- coding: utf-8 -*-
"""Read three exact SQLite blob copies using standard-library immutable connections."""
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from evidence import OUT,EV,INDEX,file,raw,sha,write

sources=sorted(r['path'] for r in INDEX if r['path'].startswith(EV+'validation/') and r['path'].endswith('.sqlite3'))
assert len(sources)==3
temp=Path(tempfile.mkdtemp(prefix='a03-r8-independent-immutable-')).resolve()
results=[]
try:
    for i,source in enumerate(sources):
        frozen=raw(source);digest=sha(frozen)
        copy=temp/('%02d.sqlite3'%i)
        with copy.open('xb') as f:f.write(frozen)
        before=sha(copy.read_bytes());assert before==digest
        sql=[]
        db=sqlite3.connect(copy.as_uri()+'?mode=ro&immutable=1',uri=True)
        try:
            db.set_trace_callback(sql.append)
            db.execute('PRAGMA query_only=ON')
            app=db.execute('PRAGMA application_id').fetchone()[0]
            version=db.execute('PRAGMA user_version').fetchone()[0]
            assert db.execute('PRAGMA quick_check').fetchone()==('ok',)
            tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            counts={name:db.execute('SELECT count(*) FROM "'+name.replace('"','""')+'"').fetchone()[0] for name in tables}
            runs=[]
            if 'native_pre_runs' in tables:
                columns=[r[1] for r in db.execute('PRAGMA table_info(native_pre_runs)')]
                selected=[c for c in ('run_id','status','reads','pre_ref','run_sha','registration_id','kind') if c in columns]
                runs=[dict(zip(selected,row)) for row in db.execute('SELECT '+','.join('"'+c+'"' for c in selected)+' FROM native_pre_runs')]
            metadata={}
            for table in ('meta','native_meta'):
                if table in tables:
                    metadata[table]=[list(r) for r in db.execute('SELECT * FROM '+table)]
        finally:db.close()
        after=sha(copy.read_bytes());assert before==after
        assert sha(file(source).read_bytes())==digest
        results.append({'source':source,'source_sha256':digest,'copy_path':str(copy),
         'connection':'file URI mode=ro&immutable=1; query_only=ON','application_id':app,'user_version':version,
         'counts':counts,'native_pre_runs':runs,'meta_rows':metadata,'sql':sql,
         'copy_sha256_before':before,'copy_sha256_after':after,'source_sha256_after':digest,'quick_check':'ok'})
    first=next(r for r in results if '/bounded-01/' in r['source'])
    second=next(r for r in results if '/bounded-02/' in r['source'] and '/runtime/' in r['source'])
    target=next(r for r in results if '/target/' in r['source'])
    assert all(first['counts'][name]==0 for name in ('books','registrations','plans','intents','permits','native_pre_runs'))
    assert second['counts']['books']==second['counts']['registrations']==second['counts']['native_pre_runs']==1
    assert all(second['counts'][name]==0 for name in ('plans','intents','permits'))
    assert len(second['native_pre_runs'])==1
    run=second['native_pre_runs'][0]
    assert run['status']=='OBSERVED' and run['reads']==1 and run['pre_ref'] is None and run['run_sha'] is None
    assert target['counts']['observations']==1 and target['counts']['effects']==0
finally:
    assert temp.parent==Path(tempfile.gettempdir()).resolve() and temp.name.startswith('a03-r8-independent-immutable-') and not temp.is_symlink()
    shutil.rmtree(temp)
value={'status':'THREE_FROZEN_DATABASES_IMMUTABLY_VERIFIED','copies':results,
 'temporary_root':str(temp),'removed':not temp.exists(),'candidate_native_api_calls':0,
 'runtime_originals_opened':False,'new_target_effects':0,
 'final_boundary':'one OBSERVED read with null pre_ref/run_sha; no plans/intents/permits/effects',
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'database-review.json',value)
print(json.dumps({'status':value['status'],'databases':len(results),
 'second_runtime_counts':second['counts'],'second_native_runs':second['native_pre_runs'],
 'target_counts':target['counts'],'temporary_root_removed':value['removed']}))
